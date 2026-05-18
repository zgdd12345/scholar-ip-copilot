# Data Model

Everything EviDraft produces lives on disk under the project's `.evidraft/` directory (plus `manuscript/` for the LaTeX project). On-disk files are the source of truth; the plugin reads and writes them, and the user can diff them.

```
<your-project>/
├── .evidraft/
│   ├── project.yaml           project type, status, rules, hooks, scope/style/reviewers/lit_deep
│   ├── scope/                 /scholar:brainstorming output (dated, gated by scope-required hook)
│   │   └── YYYY-MM-DD-<slug>.md
│   ├── evidence/evidence.jsonl
│   ├── literature/
│   │   ├── references.bib
│   │   ├── matrix.md
│   │   └── (deepresearch artefacts: plan.yaml, candidates.jsonl,
│   │        screening_log.csv, clusters.yaml, critique/, citation_audit.json,
│   │        related_work.draft.md)
│   ├── ideas/
│   │   ├── novelty_matrix.md
│   │   ├── risk_matrix.md
│   │   └── experiment_to_validate.md
│   ├── code/
│   │   ├── repo_summary.md
│   │   ├── method_to_code.md
│   │   └── paper_code_audit.md
│   ├── experiments/
│   │   ├── result_analysis.md
│   │   └── tables/
│   ├── style/                 /scholar:polish humanize output
│   │   ├── humanize-<ts>.log
│   │   └── humanize-<ts>.report.md
│   ├── reviews/               /scholar:xreview external-agent reviews (write zone locked here)
│   │   ├── <agent>-<persona>-<ts>.md
│   │   └── .last.yaml
│   └── patent/                # only if project_type ∈ patent, mixed
│       ├── invention_disclosure.md     # 技术交底书 / TID — primary deliverable
│       ├── invention_candidates.md
│       ├── prior_art_map.md
│       ├── claim_chart.md
│       ├── claims.md
│       └── patent_review_report.md
└── manuscript/                # only if project_type ∈ paper, mixed
    ├── main.tex
    ├── references.bib -> ../.evidraft/literature/references.bib
    └── sections/*.tex
```

All schemas live in `packages/core/schemas/` and are validated where possible (`pyyaml` + `jsonschema`).

---

## `.evidraft/project.yaml`

```yaml
project_type: paper           # paper | patent | mixed
title: "Example Paper Title"
field: "computer vision"
target_venue: "arXiv"
language: "en"
authors:
  - name: "Alba"
    affiliation: ""
    orcid: ""
status:
  literature: not_started     # not_started | in_progress | done
  idea: not_started
  codebase: not_started
  experiments: not_started
  manuscript: not_started
  patent: not_started
artifacts:
  evidence: ".evidraft/evidence/evidence.jsonl"
  bib: ".evidraft/literature/references.bib"
  manuscript: "manuscript/main.tex"
  invention_disclosure: ".evidraft/patent/invention_disclosure.md"
rules:
  require_citation_for_claims: true
  require_experiment_source_for_numbers: true
  require_code_trace_for_code_claims: true
  allow_unverified_claims: false
hooks:
  citation_guard: enabled
  evidence_consistency: enabled
  latex_compile: enabled
  sensitive_file_guard: enabled
```

Validated by [`packages/core/schemas/project.schema.json`](../packages/core/schemas/project.schema.json).

---

## `.evidraft/evidence/evidence.jsonl`

One JSON object per line. The "lingua franca" for every downstream draft.

```json
{"id":"ev_0001","type":"paper","source":"arxiv:2103.xxxx","claim":"Method X achieves 81.3 mAP on COCO.","support":"Table 3 of the cited paper.","citation_key":"smith2021methodx","file_path":null,"line_range":null,"confidence":"high","verified":true}
{"id":"ev_0017","type":"experiment","source":"experiments/runs/exp_2026_03_01.csv","claim":"Our model attains 82.6 mAP on COCO val2017.","support":"Row 4, column 'map_5095' of the cited csv.","citation_key":null,"file_path":"experiments/runs/exp_2026_03_01.csv","line_range":"4:4","confidence":"high","verified":true}
{"id":"ev_0042","type":"code","source":"src/models/detector.py","claim":"Anchor-free head implemented via the FCOSHead class.","support":"Class definition and forward pass.","citation_key":null,"file_path":"src/models/detector.py","line_range":"118:204","confidence":"high","verified":true}
```

Field meanings:

| Field | Required | Notes |
|---|---|---|
| `id` | yes | `ev_` + 4-digit zero-padded counter |
| `type` | yes | `paper` / `experiment` / `code` / `patent` / `note` |
| `source` | yes | URI-ish: `arxiv:…`, `doi:…`, file path, patent number, URL |
| `claim` | yes | one sentence, no hedging |
| `support` | yes | where in the source the claim is backed up |
| `citation_key` | conditional | required if `type=paper`; BibTeX key in `references.bib` |
| `file_path` | conditional | required if `type=code` or numeric experiment row |
| `line_range` | conditional | `"start:end"` (inclusive) when applicable |
| `confidence` | yes | `high` / `medium` / `low` |
| `verified` | yes | boolean; auditor sets this after manual check |

Validated by [`packages/core/schemas/evidence.schema.json`](../packages/core/schemas/evidence.schema.json).

---

## `.evidraft/literature/matrix.md`

A markdown table that is friendly to both humans and grep. Columns:

| Paper (citation_key) | Year | Venue | Problem | Method | Datasets | Key Result | Gap | Evidence ids |

---

## `.evidraft/ideas/novelty_matrix.md`

| Idea | Problem | Prior Work | Novelty | Evidence | Experiment Needed | Patent Potential | Risk |

---

## `.evidraft/code/method_to_code.md`

| Method component | Source files | Entry points | Configs | Key functions/classes | Evidence | Gaps |

`method-to-code.md` is the **bridge** between the paper's "Method" section and the source tree. Every method component must list at least one `file_path` (and ideally a line range).

---

## `.evidraft/code/paper_code_audit.md`

| Paper claim | Where in paper | Code evidence (file:lines) | Verdict | Notes |

`Verdict` ∈ { `CONFIRMED`, `PARTIAL`, `MISSING`, `MISMATCH`, `NOT_AUDITABLE` }.

---

## `.evidraft/experiments/result_analysis.md`

| Metric | Setting | Number | Source (file:row/col) | Evidence id | Notes |

LaTeX tables go in `.evidraft/experiments/tables/*.tex` and are `\input`ed from `manuscript/`.

---

## `.evidraft/patent/claim_chart.md`

| Claim element | Specification support | Code support | Prior art overlap | Risk | Suggested revision |

---

## `.evidraft/patent/invention_disclosure.md`

A long-form markdown with the sections required by an attorney intake. See `plugins/scholar-ip/templates/patent-project/.evidraft/patent/invention_disclosure.md`.

---

## Path conventions

- Relative paths are relative to the project root.
- `line_range` is 1-indexed and inclusive on both ends.
- All file paths use forward slashes; Windows users still see forward slashes in artefacts.
- `evidence.jsonl` is append-mostly. Old entries are kept; new entries get new ids; updates re-emit with a new id and a `supersedes` pointer if needed (planned in v0.2).

---

## Validation

```bash
python -m packages.core.validate \
    --project .evidraft/project.yaml \
    --evidence .evidraft/evidence/evidence.jsonl
```

Validation script is part of v0.2; in MVP, the schemas are present and adapters can lint against them.
