#!/usr/bin/env python3
"""
LangGraph-based Gemini workflow with tool-calling.

Seeds the model with git status/diff, repo tree, and architecture.md.
The model can call read-only tools (ls/cat/rg) to fetch more context.

Requirements:
- pip install google-generativeai langgraph
- GEMINI_API_KEY must be set in the environment.
"""
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Union

import google.generativeai as genai
from google.ai.generativelanguage import (
    Content,
    FunctionDeclaration,
    FunctionResponse,
    Part,
    Schema,
    Tool,
    Type,
)
from langgraph.graph import END, StateGraph

ROOT = Path(__file__).resolve().parent
ARTIFACTS_DIR = ROOT / "reports"


def run_git(*args: str) -> str:
    allow_non_zero = args and args[0] == "diff"
    result = subprocess.run(["git", *args], capture_output=True, text=True)
    if result.returncode not in (0, 1) or (result.returncode == 1 and not allow_non_zero):
        raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
    return result.stdout.strip()


def gather_repo_tree() -> str:
    tracked = run_git("ls-files")
    return tracked if tracked else "<no tracked files>"


def gather_git_context() -> tuple[str, str, List[str]]:
    status = run_git("status", "-sb")
    diff_output = run_git("diff", "--no-color")

    untracked = run_git("ls-files", "--others", "--exclude-standard")
    if untracked:
        pieces: list[str] = [diff_output] if diff_output else []
        for path in untracked.splitlines():
            file_diff = run_git("diff", "--no-color", "--", "/dev/null", path)
            if file_diff:
                pieces.append(file_diff)
        diff_output = "\n\n".join(pieces)

    changed_files = run_git("diff", "--name-only").splitlines()
    if untracked:
        changed_files.extend(untracked.splitlines())

    changed_files = sorted({path for path in changed_files if path})
    return status, diff_output.strip(), changed_files


def safe_resolve(path: str) -> Path:
    target = (ROOT / path).resolve()
    if ROOT not in target.parents and target != ROOT:
        raise ValueError("Access outside repo root is not allowed")
    return target


def tool_list_dir(path: str = ".") -> str:
    try:
        p = safe_resolve(path)
        entries = sorted(x.name + ("/" if x.is_dir() else "") for x in p.iterdir())
        return "\n".join(entries)
    except Exception as exc:  # pragma: no cover - defensive
        return f"<ls error: {exc}>"


def tool_read_file(path: str, start: int = 0, length: int = 4000) -> str:
    try:
        p = safe_resolve(path)
        data = p.read_text(errors="ignore")
        return data[start : start + length]
    except Exception as exc:  # pragma: no cover - defensive
        return f"<cat error: {exc}>"


def tool_search_text(pattern: str, path: str = ".") -> str:
    try:
        p = safe_resolve(path)
        result = subprocess.run(
            ["rg", "-n", pattern, str(p)],
            capture_output=True,
            text=True,
        )
        if result.returncode not in (0, 1):
            return f"<rg error: {result.stderr.strip() or result.stdout.strip()}>"
        return (result.stdout or "").strip()[:8000]
    except FileNotFoundError:
        return "<rg not installed>"
    except Exception as exc:  # pragma: no cover - defensive
        return f"<rg error: {exc}>"


TOOLS: list[Any] = [
    Tool(
        function_declarations=[
            FunctionDeclaration(
                name="list_dir",
                description="List files in a directory relative to repo root.",
                parameters=Schema(
                    type=Type.OBJECT,
                    properties={
                        "path": Schema(
                            type=Type.STRING,
                            description="Path to list (relative to repo root).",
                        )
                    },
                ),
            ),
            FunctionDeclaration(
                name="read_file",
                description="Read a slice of a text file.",
                parameters=Schema(
                    type=Type.OBJECT,
                    properties={
                        "path": Schema(
                            type=Type.STRING,
                            description="File path relative to repo root",
                        ),
                        "start": Schema(
                            type=Type.INTEGER,
                            description="Byte/char offset (default 0)",
                        ),
                        "length": Schema(
                            type=Type.INTEGER,
                            description="Max chars to return (default 4000)",
                        ),
                    },
                    required=["path"],
                ),
            ),
            FunctionDeclaration(
                name="search_text",
                description="ripgrep search with line numbers.",
                parameters=Schema(
                    type=Type.OBJECT,
                    properties={
                        "pattern": Schema(
                            type=Type.STRING, description="Regex/pattern to search for"
                        ),
                        "path": Schema(
                            type=Type.STRING,
                            description="Directory or file to search (relative to repo root)",
                        ),
                    },
                    required=["pattern"],
                ),
            ),
        ]
    )
]


def build_seed_prompt(prompt_template: str, repo_tree: str, changed_files: List[str], status: str, diff: str) -> str:
    changed_files_block = "\n".join(changed_files) if changed_files else "<none>"
    status_block = status or "<clean>"
    diff_block = diff or "<empty diff>"
    return (
        f"{prompt_template}\n\n"
        f"Repository structure:\n{repo_tree}\n\n"
        f"Changed files:\n{changed_files_block}\n\n"
        f"<status>\n{status_block}\n</status>\n\n"
        f"<diff>\n{diff_block}\n</diff>\n"
    )


def make_model(system_instruction: str, model_name: str) -> genai.GenerativeModel:
    return genai.GenerativeModel(model_name, tools=TOOLS, system_instruction=system_instruction)


def model_node(state: Dict[str, Any]) -> Dict[str, Any]:
    model: genai.GenerativeModel = state["model"]
    raw_messages: List[Any] = state.get("messages", [])
    
    # Track iterations to prevent infinite loops
    iteration_count = state.get("iteration_count", 0)
    MAX_ITERATIONS = 15
    
    if iteration_count >= MAX_ITERATIONS:
        print(f"Warning: Maximum iteration limit ({MAX_ITERATIONS}) reached. Forcing completion.")
        state["final_text"] = "Analysis incomplete: Maximum tool call limit reached. Please try with a more focused query."
        return state
    
    state["iteration_count"] = iteration_count + 1

    # Normalize messages into Content objects
    contents: List[Content] = []
    for m in raw_messages:
        if isinstance(m, Content):
            contents.append(m)
            continue
        if isinstance(m, dict):
            role = m.get("role", "user")
            parts_raw = m.get("parts")
            if parts_raw is None and "content" in m:
                parts_raw = [m["content"]]
            parts: List[Part] = []
            for p in parts_raw or []:
                if isinstance(p, Part):
                    parts.append(p)
                else:
                    parts.append(Part(text=str(p)))
            contents.append(Content(role=role, parts=parts))
            continue
        # fallback: treat as user text
        contents.append(Content(role="user", parts=[Part(text=str(m))]))

    response = model.generate_content(contents)
    state["last_response"] = response

    # Detect tool call
    tool_call = None
    for part in response.parts:
        if hasattr(part, "function_call") and part.function_call is not None:
            tool_call = part.function_call
            break

    if tool_call:
        state["tool_call"] = tool_call
    else:
        # Only try to access .text if there's no function_call
        try:
            state["final_text"] = response.text
        except ValueError as e:
            # If we still can't get text, log and return empty
            print(f"Warning: Could not extract text from response: {e}")
            state["final_text"] = ""
    return state


def route_after_model(state: Dict[str, Any]) -> str:
    if "tool_call" in state:
        return "tools"
    return END


def apply_tool_node(state: Dict[str, Any]) -> Dict[str, Any]:
    tool_call = state.pop("tool_call")
    name = tool_call.name
    args = dict(tool_call.args)
    result = dispatch_tool_call(name, args)
    tool_response = Part(function_response=FunctionResponse(name=name, response={"result": result}))

    # Append tool response to history and loop back to model
    messages: List[Any] = state.get("messages", [])
    messages.append(Content(role="function", parts=[tool_response]))
    state["messages"] = messages
    return state


def dispatch_tool_call(name: str, args: dict[str, Any]) -> str:
    if name == "list_dir":
        return tool_list_dir(args.get("path", "."))
    if name == "read_file":
        return tool_read_file(args["path"], args.get("start", 0), args.get("length", 4000))
    if name == "search_text":
        return tool_search_text(args["pattern"], args.get("path", "."))
    return f"<unknown tool: {name}>"


def write_artifact(filename: str, content: str) -> Path:
    ARTIFACTS_DIR.mkdir(exist_ok=True)
    path = ARTIFACTS_DIR / filename
    path.write_text(content, encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt-file", type=Path, default=Path("prompts/default_impact_prompt.txt"))
    parser.add_argument("--model", default="gemini-2.5-flash")
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY must be set")
    genai.configure(api_key=api_key)

    prompt_template = args.prompt_file.read_text(encoding="utf-8")
    repo_tree = gather_repo_tree()
    status, diff, changed_files = gather_git_context()
    architecture_path = ROOT / "architecture.md"
    architecture = architecture_path.read_text(encoding="utf-8") if architecture_path.exists() else "<none>"

    seed_prompt = build_seed_prompt(prompt_template, repo_tree, changed_files, status, diff)
    seed_message = (
        f"{seed_prompt}\n\n"
        f"Architecture:\n{architecture}\n"
    )

    model = make_model(prompt_template, args.model)

    # Build graph
    graph = StateGraph(dict)
    graph.add_node("model", model_node)
    graph.add_node("tools", apply_tool_node)
    graph.set_entry_point("model")
    graph.add_edge("tools", "model")
    graph.add_conditional_edges("model", route_after_model)
    app = graph.compile()

    # Initial state: include user message as history
    state: Dict[str, Any] = {
        "model": model,
        "messages": [Content(role="user", parts=[Part(text=seed_message)])],
        "iteration_count": 0,
    }

    final_state = app.invoke(state)
    final_text = final_state.get("final_text")
    if final_text:
        print(final_text)
        saved = write_artifact("langgraph_last_response.txt", final_text)
        print(f"\nSaved Gemini response to {saved}")
    else:
        print("<no final text>")


if __name__ == "__main__":
    main()
