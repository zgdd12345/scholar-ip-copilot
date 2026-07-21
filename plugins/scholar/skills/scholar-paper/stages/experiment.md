# workflow:paper.experiment

Turn raw experiment outputs into a trustworthy `result_analysis.md` and LaTeX tables ready to `\input` from `manuscript/`.

## Best-effort reuse

This action is best effort. Build an `Input summary` from `results_dir`, selected
files, and their source fingerprints. If the existing analysis' `Input summary`
matches the current normalized inputs and source fingerprints, reuse its verified
rows and tables and process only changed sources. Put the current `Input summary`
in `result_analysis.md` and generated table headers. Missing runs, seeds, metrics,
or evidence become `TODO` gaps with reduced confidence, not a reason to suppress
analysis of available results.

## Steps

1. **Inventory.** Walk `results_dir` (default `experiments/`). Identify:
   - per-run subfolders or csv/jsonl files,
   - run names, seeds, config hashes,
   - metric files (csv, json, jsonl, tensorboard summary, etc).
2. **Load and normalise.** Use the `experiment-analyst` subagent to turn raw outputs into a trustworthy table. Build a flat table per (experiment, setting, metric, value, source_file, source_row). Store this conceptually; persist the human-readable version into `.evidraft/experiments/result_analysis.md`:
   | Metric | Setting | Number | Source (file:row/col) | Evidence id | Notes |
3. **Append evidence.** Use the `evidence-auditor` subagent to spot-check each appended record against its source file. For each *numerical claim* you intend to use in the paper:
   - append a record with `type=experiment`, `file_path`, `line_range` (or `row:col`), `claim` (a one-sentence number-bearing claim), `support`.
4. **Generate LaTeX tables.** For each table the paper will need, write a `.tex` file under `.evidraft/experiments/tables/<table_id>.tex`. Use `booktabs` (`\toprule \midrule \bottomrule`). Add a comment header inside the file pointing to evidence ids and source paths.
5. **Suggest figures.** In `result_analysis.md`, add a "Figure suggestions" section: which plot, which axes, which source files, which seed range. Do not generate the figure here.

## Constraints

- **Never** invent a number. If a metric is missing, write `TODO` instead of a value.
- Report mean ± std only when you have ≥ 3 seeds. Otherwise report the single-seed number and flag it.
- Tables must `\input` cleanly into the manuscript without runtime computation.

## Done criteria

- `result_analysis.md` exists.
- At least one LaTeX table file under `.evidraft/experiments/tables/`.
- New `type=experiment` evidence records appended for every numeric paper claim.
- Chat output lists the figure suggestions.
- Status is `complete`, `complete_with_gaps` when requested comparisons or sources
  are missing, or `blocked` only when workspace safety prevents every useful output.
