# Workflow Impact Analysis Demo
<!--
Quick git helpers:
  git status -sb          # list changed files concisely
  git diff                # show full diff for current branch
  git diff --name-only    # show only file names in the diff
-->

This repository contains a toy Python codebase that can be used to explore prompts
for LLM-based impact analysis. Several workflows are available:
- `workflow.py`: one-shot prompt + diff to Gemini CLI.
- `agent_workflow.py`: tool-calling loop (ls/cat/rg) using the Gemini SDK.
- `langgraph_workflow.py`: LangGraph tool-calling agent with the same tools.

## Workflow execution (one-shot CLI)

1. Hack on files (usually under `src/`). Use `git status -sb` to see what changed.
2. Run the workflow (prints the prompt preview *and* calls Gemini in one go):
   ```bash
   python3 workflow.py --model gemini-2.5-flash
   ```
   The script prints the compiled prompt, saves it to `reports/last_prompt.txt`,
   invokes Gemini, and stores the response in `reports/last_response.txt`.
3. If you only want to preview the prompt without invoking Gemini, add `--dry-run`.
4. Iterate by editing code or `prompts/default_impact_prompt.txt` and rerun the command above.

## Usage

1. Modify files in `src/` to create the scenario you want to analyze. The repo
   now includes `OrderService` orchestrating pricing, fraud screening, payment,
   inventory, shipping, loyalty points, and auditing. Shared services (`PricingService`,
   `FraudService`, `ShippingService`, `PromotionService`, `LoyaltyService`, `TaxService`,
   `CatalogService`, `AuditLogger`, `ReturnService`) give you cross-file impact
   paths to test, e.g., shipping costs depend on product weight/fragility (catalog)
   and promo codes can toggle free shipping (promotions) while tax varies by region/category.
   There is also an unrelated email helper for noise.
2. Edit `prompts/default_impact_prompt.txt` (or add a new prompt file) to control
   how the LLM should respond.
3. Run the workflow:

   ```bash
   python3 workflow.py --model gemini-2.5-flash
   ```

   The prompt preview is always shown; add `--dry-run` if you do not want to invoke Gemini.

Run artifacts are saved under `reports/`:
- `reports/last_prompt.txt` stores the full prompt (status + diff) for each run.
- `reports/last_response.txt` captures the Gemini CLI output for easier reading.

## Tool-calling workflows (SDK)

Prereqs (create a venv if you prefer):
```bash
pip install google-generativeai langgraph
brew install ripgrep   # for search_text tool
export GEMINI_API_KEY=your_key
export OPENAI_API_KEY=your_key
```

- `agent_workflow.py`: simple tool loop. Seeds context with repo tree, diff, changed file contents, and `architecture.md`, then lets Gemini call `list_dir`, `read_file`, `search_text`.
  ```bash
  python3 agent_workflow.py
  ```
- `langgraph_workflow.py`: same tools, orchestrated with LangGraph.
  ```bash
  python3 langgraph_workflow.py
  ```
  Saves the final response to `reports/langgraph_last_response.txt`.

## Context helpers

- `prompts/default_impact_prompt.txt`: generic impact/QA prompt template.
- `architecture.md`: module/dependency map to help the model reason about downstream effects.
