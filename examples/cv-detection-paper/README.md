# Example: cv-detection-paper (illustrative)

> **All content in this directory is illustrative and fictional.** Author
> names, BibTeX keys (`smith2024examplekey`, `chen2023anchorfreebaseline`),
> venues, and result numbers are synthetic. The directory exists only to
> show what an EviDraft paper project looks like after running the full
> `/paper-*` workflow on a small computer-vision codebase.

## What this example shows

A complete EviDraft paper project after the user has already run:

```
/scholar:paper-init
/scholar:paper-lit          (literature matrix + bib + literature evidence)
/scholar:paper-code-audit
/scholar:paper-experiment
/scholar:paper-draft
/scholar:paper-check
```

The project is configured with `target_venue: arXiv`, in line with the
EviDraft default of drafting in a venue-neutral arXiv style first.
Venue-specific conversion would happen later via `/scholar:paper-venue`.

## Layout

```
cv-detection-paper/
├── src/models/detector.py             synthetic AnchorFreeHead class (Method X)
├── configs/base.yaml                  fictional hyper-params
├── experiments/runs/
│   ├── exp_2026_03_01.csv             main run, 3 seeds x 2 datasets
│   └── exp_2026_03_02.csv             ablation: IoU-aware off
├── .evidraft/
│   ├── project.yaml
│   ├── evidence/evidence.jsonl        6 records (2 paper, 2 experiment, 2 code)
│   ├── literature/
│   │   ├── references.bib
│   │   └── matrix.md
│   ├── code/
│   │   ├── repo_summary.md
│   │   ├── method_to_code.md
│   │   └── paper_code_audit.md
│   └── experiments/
│       ├── result_analysis.md
│       └── tables/main_results.tex
└── manuscript/
    ├── main.tex                        arXiv-style draft
    ├── references.bib                  -> ../.evidraft/literature/references.bib
    └── sections/{introduction,related_work,method,experiments,conclusion}.tex
```

## Walk-through (what each command produces in this example)

### 1. `/scholar:paper-init`

Scaffolds `.evidraft/` and `manuscript/`. After running it the project
looks like the `generic-paper/` example (statuses all `not_started`,
manuscript is the placeholder skeleton, evidence file is empty).
In this `cv-detection-paper` directory the statuses have already
advanced and `manuscript/` is populated.

Chat output ends with:

```
Next:
  /scholar:paper-lit         start literature work
  /scholar:paper-code-audit  map your code to the planned method
  /scholar:paper-experiment  analyse experiment outputs (if any)
```

### 2. `/scholar:paper-code-audit`

Writes three files:

- `.evidraft/code/repo_summary.md` -- a fast scan of the synthetic repo.
- `.evidraft/code/method_to_code.md` -- maps each method component
  (anchor-free head, distribution-focal decoding, shared per-level
  tower, IoU-aware classification) to `src/models/detector.py` lines
  and an evidence id.
- `.evidraft/code/paper_code_audit.md` -- five rows with verdicts.
  In this example: 3 `CONFIRMED`, 1 `PARTIAL` (decoder is a stub),
  1 `NOT_AUDITABLE` (novelty claim).

Chat output prints the count summary:

```
3 CONFIRMED, 1 PARTIAL, 0 MISSING, 0 MISMATCH, 1 NOT_AUDITABLE
```

### 3. `/scholar:paper-experiment`

Reads `experiments/runs/*.csv`, computes seed means, and writes:

- `.evidraft/experiments/result_analysis.md` -- per-metric table with
  evidence ids (ev_0017 for the main run, ev_0018 for the ablation).
- `.evidraft/experiments/tables/main_results.tex` -- a booktabs LaTeX
  table `\input`able from the manuscript.

It also appends `ev_0017` and `ev_0018` to `evidence.jsonl`.

### 4. `/scholar:paper-draft`

Generates `manuscript/main.tex` and the five section files under
`manuscript/sections/`. The introduction cites `smith2024examplekey`
and `chen2023anchorfreebaseline`. The experiments section
`\input`s `../.evidraft/experiments/tables/main_results.tex`. Every
number in the draft traces back to an `ev_*` id in `evidence.jsonl`.

### 5. `/scholar:paper-check`

In a real run this would produce `paper_check_report.md` covering
citation completeness, LaTeX compilation, figure/table references,
claim-evidence linkage, and number-source provenance. For this
example we have not committed the report file -- the audit
artefacts above already demonstrate the format.

## Consistency notes

- The headline number 0.418 in the abstract is the seed-mean of rows
  2-4 (`map_5095`) of `exp_2026_03_01.csv`.
- The ablation delta -1.6 in the experiments section is
  $0.418 - 0.402 = 0.016$ (rounded to 1.6 points).
- All `file_path` + `line_range` pairs in `evidence.jsonl` correspond
  to real lines in `src/models/detector.py`.
- BibTeX keys cited in the manuscript exist in
  `.evidraft/literature/references.bib`.
