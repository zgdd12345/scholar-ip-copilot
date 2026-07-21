---
id: evidence-check
title: "Evidence record discipline and cross-artefact consistency"
kind: skill
phase: shared
description: >
  Load whenever any paper section, TID section, or patent claim is being
  written or edited. Provides per-type required fields for evidence.jsonl,
  deterministic id allocation, the verified lifecycle, supersedes linkage,
  and the cross-reference contract between evidence.jsonl,
  references.bib, method_to_code.md, and experiments tables.
triggers:
  - "writing paper section"
  - "writing TID section"
  - "writing patent claim"
  - "appending evidence record"
  - "auditing claims against evidence"
provides:
  - evidence-record-shape
  - evidence-id-allocation
  - verified-lifecycle
  - supersedes-linkage
  - cross-reference-rules
allowed_tools: [Read, Glob, Grep, Write, Edit]
policies: [evidence-integrity]
references:
  - doc: ../../../docs/data-model.md
  - doc: ../../../schemas/evidence.schema.json
  - doc: capability:literature-review
  - doc: capability:codebase-audit
  - doc: capability:experiment-analysis
---

# evidence-check

## When to use

Pull this skill whenever you touch `.evidraft/evidence/evidence.jsonl` (read or write), or whenever a downstream artefact (paper section, TID section, claim, claim chart row, results table) introduces a claim that needs to be traced back to a record. Every other skill in this plugin defers to this one for the actual on-disk shape.

## Inputs

- `.evidraft/evidence/evidence.jsonl`
- `.evidraft/literature/references.bib`
- `.evidraft/code/method_to_code.md`
- `.evidraft/experiments/result_analysis.md` and tables under `.evidraft/experiments/tables/`
- `.evidraft/patent/claim_chart.md` (when in patent phase)

## Outputs

- new records appended through `evidraft evidence append`
- verified correction records carrying a `supersedes` pointer to the record they replace

## Procedure

### 1. Record shape — required fields by type

Every record is a single line of compact JSON. Fields common to all types:

| Field | Required | Notes |
|---|---|---|
| `id` | yes | `ev_NNNN`, 4-digit zero-padded, globally monotonic in the file |
| `type` | yes | one of `paper`, `experiment`, `code`, `patent`, `note` |
| `source` | yes | URI-ish: `arxiv:…`, `doi:…`, file path, patent number, URL |
| `source_kind` | no (default `paper`) | sub-type within `type=paper`: `paper` (formal publication) / `blog` / `engineering_report` / `docs` / `tutorial` / `spec` — see §1.1 |
| `claim` | yes | one declarative sentence, no hedging, no marketing |
| `support` | yes | where in the source the claim is backed up |
| `confidence` | yes | `high` / `medium` / `low` |
| `verified` | yes | boolean; the auditor flips this after manual check |

Type-specific required fields:

| `type` | Additional required | Forbidden / must be null |
|---|---|---|
| `paper` (`source_kind=paper`) | `citation_key` (must exist in `references.bib`) | `file_path`, `line_range` |
| `paper` (`source_kind` in {`blog`, `engineering_report`, `docs`, `tutorial`, `spec`}) | `citation_key` (BibTeX `@misc`), `file_path` (cache snapshot), `line_range` | — |
| `experiment` | `file_path` (csv/jsonl/log path), `line_range` (`row:col` or `start:end`) | `citation_key` |
| `code` | `file_path`, `line_range` (`start:end`, 1-indexed, inclusive) | `citation_key` |
| `patent` | `source` is a patent number (`US10000000B2`, `EP1234567A1`, `CN111111111A`) | `citation_key` (use `source` instead) |
| `note` | `support` describes the synthesised position; cite other `ev_NNNN` ids in `support` if it summarises them | none structurally; mark `confidence:low` unless the note merely restates a verified record |

Pre-flight checks before appending:

- Omit `id` from the proposed record; the deterministic append command allocates it while holding the evidence-store lock.
- For `paper`: `citation_key` resolves in `references.bib` (grep first).
- For `paper` with non-default `source_kind`: `file_path` resolves under `.evidraft/literature/snapshots/` and exists on disk. Legacy rows pointing at `.evidraft/literature/.cache/webfetch/` (pre-2026-05-22) are still accepted by the validator; new rows MUST use the `snapshots/` path.
- For `experiment` / `code`: `file_path` exists on disk and `line_range` is in bounds.
- `claim` is one sentence and contains no strong-claim verb unless backed by another record.

### 1.1 URL-sourced evidence (blog, docs, engineering reports)

Live web pages do not have stable line numbers. When the evidence is a blog post, vendor doc, engineering report, or any non-paper web source, the row is still `type=paper` but with a non-default `source_kind`. The citation must point at a local **snapshot** (durable evidence backing under `.evidraft/literature/snapshots/`), not the live URL:

```json
{"id":"ev_0042","type":"paper","source_kind":"blog","source":"https://example.com/post",
 "citation_key":"acme2025harness","file_path":".evidraft/literature/snapshots/<sha256>.md",
 "line_range":"42:58","claim":"...","support":"§ 'Guardrails'","confidence":"medium","verified":false}
```

Snapshots are immutable: once an `evidence.jsonl` row points at a `<sha256>.md`, the file is provenance and is never deleted or overwritten (see `capability:scholar-search` §Tier 2). To replace one whose upstream page has materially changed, store the new raw body and append a fresh evidence row carrying `supersedes` with the prior row's id. Keep the old snapshot on disk.

Recipe (the `scholar-search` skill `webfetch` variant emits the snapshot files; this skill only validates):

- `source_kind` must be one of the non-paper enum values, and `source` must be the original URL.
- `file_path` must start with `.evidraft/literature/snapshots/` (preferred) or `.evidraft/literature/.cache/webfetch/` (legacy, accepted for pre-2026-05-22 rows) and exist on disk.
- `line_range` follows the same `start:end` rule as `type=code`.
- `citation_key` must resolve in `references.bib` as an `@misc{…}` entry whose `howpublished` / `url` matches `source`.

The evidence-auditor verifies the claim by opening the cache snapshot at the cited line range — never by re-fetching the live URL.

### 2. Atomic append and `id` allocation

- Submit each record without `id` through `evidraft --root <project> evidence append '<json>'`.
- The deterministic kernel holds a cross-process lock, validates the complete graph, allocates the next `ev_NNNN`, and atomically replaces the store. Agents never read the last line to allocate IDs themselves.
- IDs and rows are append-only. If a record is wrong, append a corrected record with `supersedes` rather than editing or removing history.

### 3. `verified` lifecycle

- Drafting records start with `verified: false`.
- After an evidence reviewer or human opens the cited source and confirms the claim, append a `verified: true` record that supersedes the draft record. Never edit a committed JSONL line in place.
- `verified: false` records are **draftable but not citable**: they may inform an outline, but `policy:evidence-integrity` blocks publish actions and final numbers that rely on them.
- `verified: true` is historical fact about the completed check. If later found wrong, append a correction with `supersedes`; do not rewrite the old row.

### 4. `supersedes` linkage

When a record needs to be replaced (wrong claim, wrong support pointer, wrong citation_key):

```json
{"id":"ev_0123","type":"paper","source":"...","claim":"...","support":"...","citation_key":"...","confidence":"high","verified":true,"supersedes":"ev_0042"}
```

Rules:

- `supersedes` references exactly one prior `id`.
- The superseded record stays in the file. Downstream tools (policy:evidence-integrity, claim-chart) treat the latest record in a chain as authoritative but keep the chain visible for audit.
- A `supersedes` chain must not loop. Each id appears as `supersedes` at most once.

The deterministic append command rejects dangling targets, ambiguous successors, and cycles.

### 5. Cross-reference rules

Evidence records are the spine that ties artefacts together. The contract is bidirectional:

```
references.bib  <-- citation_key -->  evidence.jsonl (type=paper)
                                             ▲
                                             │ evidence_id
                                             │
manuscript/sections/*.tex   <-- evidence_id (in *.plan.md) -->
                                             │
                                             ▼
method_to_code.md (Evidence column)  --  evidence.jsonl (type=code)
                                             ▲
                                             │
experiments/tables/*.tex (header comment) -- evidence.jsonl (type=experiment)
                                             ▲
                                             │
patent/claim_chart.md (Specification + Code support) -- evidence.jsonl (any type)
```

Concretely:

- Every `\cite{key}` in a section -> `key` must be in `references.bib` AND the section's `*.plan.md` must list the matching `ev_NNNN` whose `citation_key == key`.
- Every number in an experiments table -> the table's header comment lists `ev_NNNN` and the comment's `file_path:line_range` matches the record's.
- Every method-to-code row -> the `Evidence` column lists ≥ 1 `ev_NNNN` of `type=code` whose `file_path:line_range` falls inside the row's source files.
- Every patent claim element -> the `claim_chart.md` row lists a Specification support (section in `invention_disclosure.md`) and a Code support (`ev_NNNN` of `type=code`).

If any of these links is missing, `policy:evidence-integrity` blocks the write.

See `examples/evidence.jsonl.snippet` for a concrete excerpt.

## Quality checklist

- [ ] Every record has all required fields for its `type`.
- [ ] `id`s are monotonic, no gaps from deletion.
- [ ] No `paper` record without a resolvable `citation_key`.
- [ ] No `code` / `experiment` record without `file_path` + `line_range`.
- [ ] `claim` is one sentence, no hedging.
- [ ] `verified=true` was set by a human or the evidence-auditor agent, not by the drafting agent.
- [ ] No orphan: every artefact reference (`\cite`, table, claim element) resolves to a record.
- [ ] No widow: every `verified=true` record is referenced by at least one artefact, or marked as background.

## Anti-patterns

- Appending a record "just in case" with `confidence:low, verified:false` to bypass `policy:evidence-integrity`. Verify the underlying claim or drop it.
- Reusing an `id` after a failed write.
- Editing the `claim` of an existing record in place. Instead, append a new record with `supersedes`.
- Flipping `verified` from `true` back to `false`. Use `supersedes` and lower `confidence` on the old record.
- Writing `type=paper` without `citation_key`, or `type=code` without `line_range`.
- Letting `references.bib` and `evidence.jsonl` drift: a key added in one and not the other will be caught by `policy:evidence-integrity` and block downstream drafting.
- Storing prose explanations inside `claim`. The claim is one declarative sentence; rationale lives in `support` and the section's `*.plan.md`.
