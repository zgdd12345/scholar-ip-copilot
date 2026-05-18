# Fixture: cv-detection-paper

This fixture is the worked example at
[`examples/cv-detection-paper/`](../../examples/cv-detection-paper/).
It is used as a regression input for the paper workflow:

- `/scholar:paper-init` template render
- `/scholar:paper-code-audit` outputs
- `/scholar:paper-experiment` table generation
- `/scholar:paper-draft` evidence-grounded section assembly
- `/scholar:paper-check` citation + number-source + claim-evidence checks

## What it exercises

- All five evidence types via `.evidraft/evidence/evidence.jsonl`
  (paper, experiment, code).
- A populated literature matrix and bib file.
- A booktabs LaTeX table `\input`ed from `manuscript/experiments.tex`.
- Cross-file line-range consistency (every `file_path` + `line_range`
  in evidence resolves to real lines in
  `src/models/detector.py`).

## Planned use in v0.2

- `pytest` will load `examples/cv-detection-paper/.evidraft/` as a
  read-only fixture and run schema validation.
- The adapter renderer will produce host-specific output for this
  fixture and snapshot-diff against committed baselines.
- The citation-guard hook will be exercised against
  `manuscript/sections/introduction.tex` (which contains explicit
  `\citep{...}` calls).
