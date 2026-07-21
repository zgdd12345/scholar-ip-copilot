# Data Model

Everything EviDraft produces lives on disk under the project's `.evidraft/` directory (plus `manuscript/` for the LaTeX project). On-disk files are the source of truth; the plugin reads and writes them, and the user can diff them.

```
<your-project>/
├── .evidraft/
│   ├── project.yaml           format_version, project type, status, rules, scope and safety
│   ├── scope/                 scope workflow output; created on demand
│   │   └── YYYY-MM-DD-<slug>.md
│   ├── evidence/evidence.jsonl
│   ├── literature/
│   │   ├── references.bib
│   │   ├── matrix.md
│   │   ├── lit_run.yaml             paper.lit run metadata (last-write wins)
│   │   ├── related_work_outline.md  paper.lit draft-outline output
│   │   ├── related_work.md          paper.review Markdown output
│   │   ├── .cache/<provider>/<sha1>.json   disposable structured-retrieval cache (arxiv / s2 / openalex); 14d TTL
│   │   ├── snapshots/<sha256>.md           durable raw-body content-addressed snapshot
│   │   └── (research.deep artefacts: plan.yaml, candidates.jsonl,
│   │        screening_log.csv, clusters.yaml, critique/, citation_audit.json,
│   │        evidence_map.json, related_work.draft.md)
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
│   ├── style/                 polish.run output; created on demand
│   │   ├── humanize-<ts>.log
│   │   └── humanize-<ts>.report.md
│   ├── reviews/               xreview.run output (write zone locked here)
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
format_version: 2
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
scope:
  required: true
  staleness_days: 14
safety:
  forbidden_paths: []
```

Validated by [`packages/core/schemas/project.schema.json`](../packages/core/schemas/project.schema.json).

---

## `.evidraft/evidence/evidence.jsonl`

One JSON object per line. The "lingua franca" for every downstream draft.

```json
{"id":"ev_0001","type":"paper","source":"arxiv:2103.xxxx","claim":"Method X achieves 81.3 mAP on COCO.","support":"Table 3 of the cited paper.","citation_key":"smith2021methodx","file_path":null,"line_range":null,"confidence":"high","verified":true}
{"id":"ev_0017","type":"experiment","source":"experiments/runs/exp_2026_03_01.csv","claim":"Our model attains 82.6 mAP on COCO val2017.","support":"Row 4, column 'map_5095' of the cited csv.","citation_key":null,"file_path":"experiments/runs/exp_2026_03_01.csv","line_range":"4:4","confidence":"high","verified":true}
{"id":"ev_0042","type":"code","source":"src/models/detector.py","claim":"Anchor-free head implemented via the FCOSHead class.","support":"Class definition and forward pass.","citation_key":null,"file_path":"src/models/detector.py","line_range":"118:204","confidence":"high","verified":true}
{"id":"ev_0055","type":"paper","source_kind":"blog","source":"https://example.org/engineering/report","claim":"The reported system uses a two-stage validation pass.","support":"Section 'Validation design'.","citation_key":"example2025validation","file_path":".evidraft/literature/snapshots/3a7f...e9.md","line_range":"42:58","confidence":"medium","verified":false}
```

Field meanings:

| Field | Required | Notes |
|---|---|---|
| `id` | yes | `ev_` + 4-digit zero-padded counter |
| `type` | yes | `paper` / `experiment` / `code` / `patent` / `note` / `invention` / `number` |
| `source_kind` | optional | sub-type within `type=paper`; one of `paper` (default) / `blog` / `engineering_report` / `docs` / `tutorial` / `spec`. Non-paper kinds require `file_path` + `line_range` pointing at a `.evidraft/literature/snapshots/<sha256>.md` snapshot. Legacy URL-hash snapshots remain readable after migration. |
| `source` | yes | URI-ish: `arxiv:…`, `doi:…`, file path, patent number, URL |
| `claim` | yes | one sentence, no hedging |
| `support` | yes | where in the source the claim is backed up |
| `citation_key` | conditional | required if `type=paper` (any `source_kind`); BibTeX key in `references.bib`. For non-paper `source_kind`, the entry is `@misc` |
| `file_path` | conditional | required if `type=code`; if `type=experiment`/`type=number` points at a specific row; or if `type=paper` AND `source_kind` is non-paper |
| `line_range` | conditional | `"start:end"` (inclusive); required whenever `file_path` points at a specific row/range |
| `confidence` | yes | `high` / `medium` / `low` |
| `verified` | yes | boolean; auditor sets this after manual check |
| `supersedes` | optional | `ev_NNNN` id of a prior record this one corrects (append-only history) |
| `tags` | optional | string array; free-form labels (e.g. `[entity]`, `[v0.2]`) |
| `added_by` | optional | who or what added the row (`paper.lit`, `evidence-reviewer`, etc.) |
| `added_at` | optional | ISO-8601 timestamp |

Validated by [`packages/core/schemas/evidence.schema.json`](../packages/core/schemas/evidence.schema.json).

---

## `.evidraft/literature/matrix.md`

A markdown table that is friendly to both humans and grep. Columns:

| Paper (citation_key) | Source kind | Year | Venue | Problem | Method | Datasets | Key Result | Gap | Evidence ids |

`Source kind` is `paper` (default — formal publication) / `blog` / `engineering_report` / `docs` / `tutorial` / `spec`. For non-paper kinds, `Venue` carries the publisher/site (e.g. `Anthropic Engineering Blog`, `OpenAI Cookbook`); never invent a venue. `Key Result` may be qualitative when the source has no number.

The first non-blank lines are a fixed banner `<!-- paper-lit: single-pass seed matrix. NOT a PRISMA review. -->` (inserted by `paper lit`) so a seeded matrix is not mistaken for a completed systematic review.

---

## `.evidraft/literature/lit_run.yaml`

Run metadata for the latest `paper lit` action. Overwritten on every run (history lives in `git log`). It lets `paper review` and `paper check` identify which run produced the current matrix.

```yaml
run_id: 2026-05-22T02:21:00Z       # UTC ISO-8601, shared with scholar-search retrieval rows
operation: paper.lit
topic: "<resolved topic>"
topic_source: explicit-arg | scope.research_question | project.yaml.title | user-prompted
mode: single_pass | draft_outline
source_limit: 20
retrieval: web | offline
validator_used: bibtex-tidy | hand-roll
draft_outline_path: .evidraft/literature/related_work_outline.md   # null when mode=single_pass
bib_link: symlink | snapshot
bib_sync: noop | resynced
```

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
- `evidence.jsonl` is append-only. Old entries are kept; corrections re-emit with a new id and a `supersedes` pointer at the prior id.

---

## Validation

```bash
.venv/bin/evidraft --root . migrate
.venv/bin/evidraft --root . workflow preflight paper.draft
```

The deterministic core validates project and evidence data before mutation. Repository
schema fixtures are exercised by `python -m pytest tests/test_schema_fixtures.py`.
