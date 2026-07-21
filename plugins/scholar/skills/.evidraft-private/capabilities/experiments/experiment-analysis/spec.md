---
id: experiment-analysis
title: "Experiment ingestion, table generation, figure suggestion, leakage checks"
kind: skill
phase: paper
description: >
  Load when workflow:paper.experiment runs. Provides csv/jsonl ingestion patterns,
  mean±std rules (n>=3 seeds), \input-clean booktabs table recipe with
  provenance header comments, the figure-suggestion template, and how to
  spot test-set leakage into validation rows.
triggers:
  - "workflow:paper.experiment"
  - "writing result_analysis.md"
  - "generating LaTeX table from experiment outputs"
  - "suggesting paper figures"
provides:
  - csv-jsonl-ingestion
  - aggregation-rules
  - booktabs-table-recipe
  - figure-suggestion-template
  - leakage-detection
allowed_tools: [Read, Glob, Grep, Write, Edit, "Bash:ls*", "Bash:cat*"]
policies: [evidence-integrity]
references:
  - doc: capability:evidence-check
  - doc: capability:latex-writing
  - doc: ../../../docs/data-model.md
---

# experiment-analysis

## When to use

Pull this skill whenever you turn raw experiment outputs (csv, jsonl, tensorboard, logs) into a number that the manuscript will quote. The output goes into `.evidraft/experiments/result_analysis.md` and `.evidraft/experiments/tables/*.tex`, and every number that lands in the paper traces back through here.

Read raw outputs directly with `Read` and `Glob`; aggregate with small Bash one-liners or, when needed, a short Python script the user can review. Every number that lands in the paper must trace back to a file path + row identifier captured in `evidence.jsonl`.

## Inputs

- `experiments/` (default; `results_dir` input can override)
- per-run subfolders: `runs/<exp_name>/seed_<n>/<metric>.csv`, `summary.json`, `metrics.jsonl`
- optional `experiments/index.yaml` listing canonical runs
- `.evidraft/code/method_to_code.md` (to know which configs map to which method components)

## Outputs

- `.evidraft/experiments/result_analysis.md`
- `.evidraft/experiments/tables/<table_id>.tex` (one file per table the manuscript will `\input`)
- new `type=experiment` records in `evidence.jsonl`

## Procedure

### 1. csv / jsonl ingestion patterns

Treat the experiments tree as a set of (run, seed, metric, value) tuples. Common layouts:

**Layout A — per-run csv:**
```
experiments/runs/<exp_name>/seed_<n>/metrics.csv
# columns: step, loss, acc, map_5095, ...
# last row is the final epoch
```
Use the last completed row per seed unless `index.yaml` says otherwise.

**Layout B — flat jsonl log:**
```
experiments/runs/<exp_name>/log.jsonl
# one json per step; final summary record has {"split":"val","final":true,...}
```
Filter to `split=="val"` and `final==true`.

**Layout C — single summary json per run:**
```
experiments/runs/<exp_name>/seed_<n>/summary.json
```
Read directly; one tuple per file.

Ingestion rules:

- Always group by (exp_name, split) before any aggregation.
- Record the source as `file_path` and `line_range` (`row:col` for csv, line number for jsonl).
- If a run is incomplete (no `final` record / loss diverged / NaN), exclude it from aggregation and list it under "Excluded runs" in `result_analysis.md`.
- Never average across splits, datasets, or metrics.

### 2. Aggregation rules (mean ± std)

- Report `mean ± std` only when n_seeds ≥ 3 (and all seeds are complete on the same config hash).
- Use sample standard deviation (`ddof=1`) when n ≥ 3. Document the formula in the table header comment.
- For n < 3, report the single-seed number and append a footnote in `result_analysis.md` flagging the seed count.
- When the metric is bounded (`accuracy in [0,1]`) and the mean is near a boundary, also report min/max — std alone is misleading near 0 or 1.
- Round consistently: pick one decimal precision per metric and stick to it across all tables.

### 3. result_analysis.md table

Persist the human-readable inventory as:

```
| Metric | Setting | Number | Source (file:row/col) | Evidence id | Notes |
```

One row per number that **will appear** in the paper. Background numbers (sanity checks, debugging runs) go in a separate "Background runs" section at the end.

### 4. `\input`-clean booktabs LaTeX tables

Each table file in `.evidraft/experiments/tables/<table_id>.tex` is a standalone `tabular` fragment plus a provenance header comment. It must `\input` into `manuscript/` without errors and without changing rendered numbers.

Template:

```latex
% Table: <human title>
% id: <table_id>
% generated_from:
%   - experiments/runs/<exp>/seed_0/metrics.csv (final row)
%   - experiments/runs/<exp>/seed_1/metrics.csv (final row)
%   - experiments/runs/<exp>/seed_2/metrics.csv (final row)
% evidence: ev_0017, ev_0018, ev_0019
% aggregation: mean +- sample std over 3 seeds, ddof=1
% updated: <iso datetime>
\begin{tabular}{lcc}
\toprule
Method & Acc (\%) & mAP \\
\midrule
Baseline       & 76.2 \(\pm\) 0.3 & 41.5 \(\pm\) 0.4 \\
Ours           & 79.1 \(\pm\) 0.2 & 44.7 \(\pm\) 0.3 \\
\bottomrule
\end{tabular}
```

Rules:

- Use `booktabs` rules only (`\toprule`, `\midrule`, `\bottomrule`). No vertical bars.
- Do **not** include `\begin{table}`, `\caption`, or `\label` here. The manuscript section wraps the file in `\begin{table}` and adds caption/label.
- Provenance header is mandatory. It lists every source file, the evidence ids, and the aggregation rule.
- Never compute at LaTeX compile time. All numbers are baked in.
- One file per logical table — do not concatenate.

### 5. Figure-suggestion template

Add a "Figure suggestions" H2 to `result_analysis.md`. Each suggestion is a bullet block:

```
### F-001 <short title>
- kind: line | bar | scatter | violin | heatmap
- x-axis: <quantity, unit>
- y-axis: <quantity, unit>
- source: experiments/runs/<exp>/seed_*/metrics.csv  (which rows / columns)
- seeds: <list>, aggregate as mean band
- log_scale: <x|y|none>
- evidence: ev_NNNN, ...
- why: <one sentence on what the figure shows>
```

Rules:

- Do not generate the figure here; just specify it.
- One source per figure unless explicitly comparing — overlaying unrelated runs is a leakage smell.
- "Aggregate as mean band" implies n ≥ 3 seeds; otherwise specify `seeds: single` and flag.
- Log scale only when the quantity spans ≥ 2 decades.

### 6. Leakage detection

Before any number is committed, check these signals. Any hit blocks the write until resolved.

- **Test in val column.** A metric named `val_*` whose value matches the `test_*` value at the same step — likely a copy from the wrong split.
- **Best-of-N val number being quoted as final.** If the val number is `max` over epochs but the corresponding test number is the final-epoch value, the val number is selection-biased — quote final-epoch on both, or selection-on-val/report-on-test consistently.
- **Per-seed test access.** Look for code paths that compute test metrics every epoch and any logic that picks seeds by test performance. Either is leakage.
- **Tuning artefacts.** Hyperparameters chosen by inspecting test set (grep configs for `test_*` thresholds; check if `tune.py` reads from test split).
- **Mismatched n.** A row claiming `mean±std` over 3 seeds while only 2 seed folders are present. Recount before reporting.
- **Stale rows.** A row whose source file has changed mtime since the evidence record was written — re-ingest.

If a leakage signal is hit, write the row to a "Quarantined" section in `result_analysis.md` and do **not** create the table or evidence record yet.

## Quality checklist

- [ ] Every number in a table has an evidence id in the table's header comment.
- [ ] Every `mean ± std` is over ≥ 3 complete seeds.
- [ ] Incomplete runs listed under "Excluded runs".
- [ ] Tables compile via `\input{...}` with no `\caption` / `\label` inside.
- [ ] No metric averaged across splits.
- [ ] Leakage signals checked; none open.
- [ ] Figure suggestions name explicit source files and seed lists.

## Anti-patterns

- Quoting a max-over-epochs val score next to a final-epoch test score in the same row.
- Writing `mean ± std` over 2 seeds.
- Inventing a number to "fill" a missing ablation cell. Use `TODO` instead.
- Putting `\caption` or `\label` inside the table file — those belong in the manuscript wrapping `\begin{table}` block.
- Generating a figure by computing at LaTeX time (`\pgfplotsfromfile{...}` over the live experiments dir). The plot must be a static asset committed to the manuscript.
- Re-using a table id when its source data has changed — issue a new id and supersede.
- Hiding excluded runs. Excluded runs go in `result_analysis.md` so reviewers can see what was dropped and why.
