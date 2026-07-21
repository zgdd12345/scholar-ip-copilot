# Breadth / depth budget

| Knob | Default | Meaning | Hard ceiling |
|---|---|---|---|
| `breadth` | 6 | max sub-queries at Stage 1; multiplies into per-query `top_k = breadth * 5` at Stage 2; max clusters at Stage 4 capped at `min(6, breadth)`. | total candidates ≤ `breadth * 50`. |
| `depth` | 2 | recursion depth for `get_paper_references` / `get_paper_citations`; `depth=1` skips the lineage hop entirely. | `depth ≤ 3` in `full` mode; `depth ≤ 2` in `fast` mode. |

Mode=fast skips Stage 5 Critique entirely and does not dispatch `paper-critic`. It may
halve breadth and depth, rounded up. Mode full enables selected full-text critiques.
The budget is tracked in `plan.yaml.budget_log[]`; an over-budget fan-out is stopped and
logged without discarding completed work.

This is the same control surface used by **dzhng/deep-research** — two knobs, both user-facing, both visible in the artefact. See [upstream-credits.md](upstream-credits.md) for the full credit list.
