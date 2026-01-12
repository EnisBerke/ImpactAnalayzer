#!/usr/bin/env python3
"""
LangGraph-like tool-calling workflow using the OpenAI API.

Seeds the model with repo context (status/diff/tree/architecture) and allows
the model to call read-only tools (ls/cat/rg) to fetch more context.

Env:
  OPENAI_API_KEY must be set.
"""
from __future__ import annotations

import argparse
import os
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from openai import OpenAI

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


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files in a directory relative to repo root.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory to list (relative to repo root).",
                        "default": ".",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a slice of a text file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to repo root"},
                    "start": {"type": "integer", "description": "Byte/char offset", "default": 0},
                    "length": {"type": "integer", "description": "Max chars to return", "default": 4000},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_text",
            "description": "ripgrep search with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex/pattern to search for"},
                    "path": {"type": "string", "description": "Directory or file to search", "default": "."},
                },
                "required": ["pattern"],
            },
        },
    },
]


def dispatch_tool_call(name: str, args: Dict[str, Any]) -> str:
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
    parser.add_argument("--model", default="gpt-5.1")
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY must be set")

    client = OpenAI()

    prompt_template = args.prompt_file.read_text(encoding="utf-8")
    repo_tree = gather_repo_tree()
    status, diff, changed_files = gather_git_context()
    architecture_path = ROOT / "architecture.md"
    architecture = architecture_path.read_text(encoding="utf-8") if architecture_path.exists() else "<none>"

    seed_message = (
        f"{prompt_template}\n\n"
        f"Repository structure:\n{repo_tree}\n\n"
        f"Changed files:\n" + ("\n".join(changed_files) if changed_files else "<none>") + "\n\n"
        f"<status>\n{status or '<clean>'}\n</status>\n\n"
        f"Architecture:\n{architecture}\n\n"
        f"<diff>\n{diff or '<empty diff>'}\n</diff>\n"
    )

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": prompt_template},
        {"role": "user", "content": seed_message},
    ]

    while True:
        response = client.chat.completions.create(
            model=args.model,
            messages=messages,
            tools=TOOLS,
        )
        msg = response.choices[0].message
        tool_calls = msg.tool_calls

        if tool_calls:
            messages.append({"role": msg.role, "content": msg.content or "", "tool_calls": [tc.to_dict() for tc in tool_calls]})
            for tc in tool_calls:
                name = tc.function.name
                args_dict = tc.function.arguments or {}
                result = dispatch_tool_call(name, args_dict)
                messages.append(
                    {"role": "tool", "name": name, "tool_call_id": tc.id, "content": result}
                )
            continue

        final_text = msg.content or ""
        print(final_text)
        saved = write_artifact("openai_last_response.txt", final_text or "<no output>")
        print(f"\nSaved OpenAI response to {saved}")
        break


if __name__ == "__main__":
    main()
