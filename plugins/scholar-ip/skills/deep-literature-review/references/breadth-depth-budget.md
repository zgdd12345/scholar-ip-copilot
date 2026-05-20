# Breadth / depth budget

| Knob | Default | Meaning | Hard ceiling |
|---|---|---|---|
| `breadth` | 6 | max sub-queries at Stage 1; multiplies into per-query `top_k = breadth * 5` at Stage 2; max clusters at Stage 4 capped at `min(6, breadth)`. | total candidates ≤ `breadth * 50`. |
| `depth` | 2 | recursion depth for `get_paper_references` / `get_paper_citations`; `depth=1` skips the lineage hop entirely. | `depth ≤ 3` in `full` mode; `depth ≤ 2` in `fast` mode. |

`mode=fast` halves both, rounded up, and skips Stage 5 SWOT bullets that require the full PDF. The budget is tracked in `plan.yaml.budget_log[]`; over-budget fan-outs are refused and logged.

This is the same control surface used by **dzhng/deep-research** — two knobs, both user-facing, both visible in the artefact. See [upstream-credits.md](upstream-credits.md) for the full credit list.
