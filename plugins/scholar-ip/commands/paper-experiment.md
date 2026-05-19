---
id: paper-experiment
title: "Analyse experiment outputs and produce LaTeX tables"
description: >
  Aggregate raw experiment outputs under `experiments/` into
  `result_analysis.md`, LaTeX tables under `.evidraft/experiments/tables/`,
  and `type=number` evidence rows. Every number that lands in the
  manuscript traces back through here; the `evidence-consistency` hook
  refuses unsourced numbers. Use when new runs land, before the next draft
  cycle, or whenever the manuscript needs a fresh number.
kind: command
slash: /scholar:paper-experiment
phase: paper
inputs:
  - name: results_dir
    type: path
    optional: true
    default: experiments/
outputs:
  - path: .evidraft/experiments/result_analysis.md
  - path: .evidraft/experiments/tables/
  - path: .evidraft/evidence/evidence.jsonl   # appended
allowed_tools: [Read, Glob, Grep, Write, Edit, "Bash:ls*", "Bash:cat*"]
hooks: [evidence-consistency]
subagents: [experiment-analyst, evidence-auditor]
references:
  - doc: ../skills/experiment-analysis/SKILL.md
  - doc: ../skills/evidence-check/SKILL.md
---

# /scholar:paper-experiment

Turn raw experiment outputs into a trustworthy `result_analysis.md` and LaTeX tables ready to `\input` from `manuscript/`.

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
