# Usage feedback: EviDraft paper workflow trial

Date: 2026-05-22

This note records product and implementation feedback from a hands-on trial of the
paper workflow for the topic "Harness Engineering for Reliable AI Coding Agents".
The run exercised:

- `/scholar:using-deep-research`
- `/scholar:deepresearch` precondition handling
- `/scholar:paper-init`
- `/scholar:paper-lit`
- the generated `.evidraft/` paper scaffold

The workflow is usable, but several rough edges made the expected path unclear.
The main theme is that command intent, guardrail state, and generated artefacts
should be more explicit at the point where the user needs to decide what happens
next.

## Summary

### What worked

- `paper-init` produced the expected project skeleton and a schema-valid
  `.evidraft/project.yaml`.
- The paper template, evidence store, literature matrix, and manuscript skeleton
  were easy to inspect and diff.
- `paper-lit` mapped naturally to a single-pass seed bibliography. It produced a
  useful literature matrix, BibTeX file, and one evidence record per source.
- The separation between `paper-lit` and `deepresearch` is conceptually sound:
  the former seeds a matrix; the latter should produce a PRISMA-style review
  with durable intermediate artefacts.
- Guardrails are strict enough to prevent accidental unsupported deep-research
  synthesis.

### What caused friction

- `/scholar:using-deep-research` explains the workflow but does not itself create
  the review document. A user can reasonably expect "帮我调研..." to produce a
  document, while the skill's done criteria only require proposing the next
  command.
- `/scholar:deepresearch` is blocked by `scope-required`, but the recovery path
  is interactive and multi-step. For ad-hoc literature review, this feels heavier
  than necessary.
- The scope-stub fast path documented in `using-deep-research` conflicts with
  the stricter `scope-required` hook text: the entry skill says a non-empty
  `.md` may be enough, while the hook requires YAML frontmatter with
  `status: approved` and a fresh `approved_date`.
- `paper-init` asks the agent to infer or ask for metadata. In practice, a
  reasonable default topic can be inferred from the recent conversation, but the
  command does not define how to persist that provenance.
- The template creates `manuscript/references.bib` as a regular file when copied
  with a normal recursive copy. The command spec asks for a symlink where
  possible.
- `paper-lit` allows web posts and engineering blogs, but its field names and
  subagent descriptions are paper-centric. This creates awkward evidence records
  for sources that are not papers.
- Evidence records store "fetched lines" in free text. Those line numbers are
  not reproducible unless the fetched page snapshot is cached.
- `references.bib` was structurally checkable, but the local project environment
  did not include `bibtexparser`; the done criteria name a standard validator
  without ensuring one is available.

## Recommendations

## 1. Add an explicit "survey document" output for ad-hoc reviews

Problem: Users asking "write a systematic review" expect a concrete document.
Today, `paper-lit` produces `matrix.md`; `deepresearch` produces
`related_work.draft.md`; `using-deep-research` produces only guidance.

Recommendation:

- Add a lightweight command or mode:
  - `/scholar:paper-survey`
  - or `/scholar:paper-lit --draft-outline`
- It should write:
  - `.evidraft/literature/related_work_outline.md`
  - `.evidraft/literature/related_work.draft.md`
- It should be clearly lower-rigor than `/scholar:deepresearch`, with no PRISMA
  claims unless the full six-stage pipeline ran.

Acceptance criteria:

- After a user asks for a review, the chat response names the exact file path of
  the generated draft.
- The draft cites only keys present in `.evidraft/literature/references.bib`.
- Strong claims are backed by an evidence id or toned down.

### Status — 2026-05-22 (P1-1 CLOSED with deviation)

Shipped in commit `2bf754f`:

- `/scholar:paper-lit --draft-outline=true` → `.evidraft/literature/related_work_outline.md`
  (banner-tagged "NOT /scholar:deepresearch Stage 6").

Deliberately **not** shipped: `related_work.draft.md`. After triage, the original
two-file ask conflates two artefacts the architecture treats as different rigor
tiers:

| Artefact | Owner command | Gating |
|---|---|---|
| `related_work_outline.md` | `/scholar:paper-lit --draft-outline=true` | None beyond `citation-guard`; lightweight survey aid. |
| `related_work.draft.md` | `/scholar:deepresearch` Stage 6 | PRISMA screening + cluster critique + final citation audit (`citation_audit.json`). |
| `related_work.md` (markdown mid-tier) | `/scholar:paper-review --format=md` (shipped 2026-05-22, see `docs/lite-mode-plan-2026-05-22.md` §P3 status block) | Pandoc `[@key]` citations; no PRISMA; default is still `--format=tex`. |
| `manuscript/sections/related_work.tex` | `/scholar:paper-review` (default) | Full audit chain at `/scholar:paper-check` time. |

Emitting `related_work.draft.md` from `paper-lit` would re-blur the lite/heavy
boundary this trial spent P0/P1/P2 tightening. The dogfood concern that the lite
output looks PRISMA-rigorous is exactly what the rigor-tier separation guards
against. The lite-mode-plan §P3 covers the user-visible "I want a markdown
related-work draft without LaTeX" niche through `paper-review --format=md`
without smuggling PRISMA semantics back into `paper-lit`.

Acceptance criteria, updated: chat response names the outline path; outline
sentences cite only keys in `references.bib`; strong-claim verbs gated by
`citation-guard`. The "draft" wording in the original acceptance is satisfied
by the outline for the `paper-lit` scope.

## 2. Reconcile the scope-stub fast path with `scope-required`

Problem: `using-deep-research` documents a stub `.md` without frontmatter, but
the hook requires `status: approved`, `approved_date`, and freshness.

Recommendation:

- Update the fast-path stub template to include valid frontmatter:

  ```yaml
  ---
  kind: paper
  status: approved
  verdict: pursue
  riskiest_assumption: "Ad-hoc scope; needs later refinement."
  evidence_seeds: []
  approved_date: 2026-05-22
  staleness_until: 2026-06-05
  ---
  ```

- Make the fast path append an audit note to the scope body:
  "Created via scope-stub fast path; not a substitute for brainstorming."
- Keep the hook strict, but make recovery copy-pasteable.

Acceptance criteria:

- The documented scope-stub path actually passes `scope-required`.
- The generated stub is visibly marked as ad-hoc.
- `/scholar:deepresearch` can proceed after the stub without weakening hook
  policy globally.

### Status — 2026-05-22 (§2 CLOSED)

Shipped in commit `3ee4b72`:

- `skills/using-deep-research/SKILL.md:81` carries the corrected
  scope-stub template with valid YAML frontmatter (`status: approved`,
  `verdict: pursue`, `approved_date`, `staleness_until`) so the stub
  passes the runtime hook without ad-hoc patching.
- `hooks/scope-required.sh:80` parses the same frontmatter — the .sh
  was lifted from existence-only to status+freshness checking in the
  same commit, closing the spec/impl drift the trial surfaced.

All three acceptance criteria met; no global hook weakening needed.

## 3. Make blocked command recovery action-oriented

Problem: The block message says to run `/scholar:brainstorming`, but users who
want a quick survey need a direct next step.

Recommendation:

- When `scope-required` blocks `/scholar:deepresearch`, include two recovery
  paths:
  - "Full path" with `/scholar:brainstorming "<topic>"`
  - "Fast path" with `/scholar:using-deep-research "<topic>"` or a generated
    scope-stub command
- If `.evidraft/project.yaml` is missing, include `/scholar:paper-init` first.

Acceptance criteria:

- Block output includes the current missing condition and the next executable
  command.
- The wording distinguishes "approved scope missing" from "scope file missing".

### Status — 2026-05-22 (§3 CLOSED)

Shipped in commit `3ee4b72`:

- `hooks/scope-required.sh:121` builds a copy-pasteable suggestion
  block keyed off the failure mode: `no-project` → run
  `/scholar:paper-init` first; `missing` → both full path
  (`/scholar:brainstorming`) and fast path
  (`/scholar:using-deep-research`); `draft-only` → edit the latest
  scope file and set `status: approved`; `stale` → re-scope or refresh
  `approved_date`. The four failure modes are distinct first-class
  branches with their own wording — no more single generic suggestion.

Both acceptance criteria met. `scope-required.md` was also updated in
the same commit so the spec mirrors the implementation.

## 4. Add first-class support for blogs, engineering posts, and reports

Problem: Harness engineering is currently documented heavily in blog posts and
vendor engineering articles. Treating every source as `type=paper` is serviceable
but semantically weak.

Recommendation:

- Extend the evidence schema with a source subtype or field:
  - `source_kind: paper | blog | engineering_report | docs | tutorial`
- Keep `type=paper` for compatibility, or add `type=literature` if the data
  model can tolerate it.
- Add matrix columns that work for non-paper sources:
  - `Source type`
  - `Evidence basis`
  - `Reproducibility`

Acceptance criteria:

- Blog/source records no longer need to pretend to have sections or venues.
- `/scholar:paper-review` can still cite them correctly.
- BibTeX entries use appropriate `@misc` fields and no invented venue.

### Status — 2026-05-22 (§4 CLOSED)

Shipped in commit `2804eda`:

- `packages/core/schemas/evidence.schema.json:19` introduces
  `source_kind ∈ {paper, blog, engineering_report, docs, tutorial, spec}`
  as a sub-type within `type=paper` — chose option (a) "keep
  `type=paper` for compatibility" rather than adding a new top-level
  `type=literature`, matching the recommendation's preferred path.
- `commands/paper-lit.md:73` describes the non-paper retrieval flow:
  use the `scholar-search` `webfetch` variant, store the snapshot
  under `.evidraft/literature/snapshots/<sha1>.md` (per the §5 P2-2
  closure), emit the evidence row with the matching `source_kind`,
  and write a `@misc{...}` BibTeX entry with real `howpublished` / `url`
  (no invented venue).
- `/scholar:paper-review` cites them via the same `citation_key`
  mechanism as papers — no special-casing needed downstream.

All three acceptance criteria met. The matrix column changes from the
recommendation were folded into the existing matrix schema via the
`Source kind` field rather than adding three new columns.

## 5. Cache fetched web snapshots used by evidence records

Problem: Evidence records cite source URLs plus "fetched line" ranges, but line
numbers from live web fetches are not stable.

Recommendation:

- When `paper-lit` uses web content, write normalized snapshots under:
  - `.evidraft/literature/.cache/web/<sha1>.md`
- Evidence records should include:
  - `file_path`
  - `line_range`
  - `source`
- For arXiv pages, cache the abstract metadata JSON or rendered text.

Acceptance criteria:

- Evidence auditor can verify a claim without re-fetching the live web page.
- A stale or changed web page does not invalidate prior evidence pointers.

### Status — 2026-05-22 (P2-2 CLOSED)

Shipped in commit (this series): WebFetch snapshots split into a two-tier
on-disk model and made durable.

- **Tier 1 — Provider JSON cache** (`.evidraft/literature/.cache/<provider>/<sha1>.json`):
  unchanged. 14-day TTL, delete-on-encounter. These files are not cited by
  any `evidence.jsonl` row, so disposability is safe.
- **Tier 2 — Snapshot store** (`.evidraft/literature/snapshots/<sha1>.{md,json}`):
  new path. **No TTL, no auto-delete**. A snapshot referenced by any
  `evidence.jsonl` row is immutable provenance. To refresh a snapshot whose
  upstream page has changed, fetch a NEW `<sha1>` and emit a fresh evidence
  row carrying `supersedes` at the prior row's id; never overwrite or delete
  the prior snapshot.

Surface area updated: `scholar-search` (SKILL + procedure + anti-patterns),
`evidence-check` (validator accepts new path; legacy `.cache/webfetch/`
tolerated for pre-2026-05-22 rows), `paper-lit` step 2 / step 3,
`literature-review` example row, `evidence.schema.json` description,
`docs/architecture.md`, `docs/data-model.md` tree + row example + field
description. `.gitignore` was already permissive (only `**/.evidraft/.cache/`
and `**/.evidraft/tmp/` are ignored, so `snapshots/` is committed alongside
`references.bib` and `evidence.jsonl` in real user projects).

Acceptance criteria, met:

- Auditor reads snapshot files directly (unchanged from before).
- TTL no longer deletes snapshots pinned by evidence rows — the second
  acceptance criterion ("A stale or changed web page does not invalidate
  prior evidence pointers") is now structurally satisfied.

## 6. Fix `manuscript/references.bib` symlink behavior

Problem: A recursive template copy produced `manuscript/references.bib` as a
regular file, while the command spec asks for a symlink to
`../.evidraft/literature/references.bib` when possible.

Recommendation:

- After template materialization, explicitly check:

  ```text
  manuscript/references.bib -> ../.evidraft/literature/references.bib
  ```

- If the platform supports symlinks, replace the copied file with the symlink.
- If not, record in chat that it is a snapshot and must be synced after BibTeX
  edits.

Acceptance criteria:

- On Unix-like systems the scaffold creates a symlink.
- On fallback copy, `paper-lit` always re-syncs the manuscript BibTeX and reports
  it did so.

### Status — 2026-05-22 (§6 CLOSED)

Shipped in commit `3ee4b72`:

- `commands/paper-init.md:63` explicitly checks the
  `manuscript/references.bib → ../.evidraft/literature/references.bib`
  symlink and creates it on POSIX (with the snapshot-copy fallback path
  documented for platforms without symlinks).
- `commands/paper-lit.md:93` re-syncs the manuscript copy on every run
  when the symlink is absent and reports `bib_sync: noop | resynced` in
  the chat summary.

Both acceptance criteria met. The fallback-copy resync runs on every
`paper-lit` invocation; the symlink is created once at `paper-init` time
and verified on each subsequent `paper-lit`.

## 7. Add a bundled BibTeX validation fallback

Problem: The done criteria mention a standard BibTeX validator, but the default
venv may not include `bibtexparser`.

Recommendation:

- Either add `bibtexparser` to the project dependencies, or ship a simple local
  validator for required fields, duplicate keys, balanced braces, and entry
  boundaries.
- Make `/scholar:paper-lit` report which validator was used.

Acceptance criteria:

- `paper-lit` does not finish with an unmet "validator unavailable" caveat.
- Validation failures name the key and field.

### Status — 2026-05-22 (§7 CLOSED)

Shipped in commit `3ee4b72` with the second of the two paths from the
recommendation — a hand-rolled local fallback rather than a hard
dependency on `bibtexparser`:

- `commands/paper-lit.md:126` declares the validator chain as
  `bibtex-tidy | hand-roll` (prefer the binary if present; otherwise
  fall through to the awk/sed local recipe).
- `skills/bib-manager/SKILL.md:135` ships the hand-rolled fallback
  recipe so the run never finishes with an unmet "validator
  unavailable" caveat.

`bibtexparser` was intentionally NOT added to dependencies — keeping
the project zero-Python-dep beyond the venv was a design goal of the
v0.2 lite-mode work.

## 8. Clarify `paper-lit` topic selection

Problem: The user invoked `/scholar:paper-lit` without an explicit topic. The
agent inferred the topic from `project.yaml`, which was reasonable but implicit.

Recommendation:

- Define topic precedence:
  1. explicit command topic
  2. latest approved scope research question
  3. `.evidraft/project.yaml.title`
  4. ask the user
- Log the selected topic in `matrix.md` metadata.

Acceptance criteria:

- `matrix.md` states where the topic came from.
- The chat summary says "used project title as topic" or equivalent.

### Status — 2026-05-22 (§8 CLOSED)

Shipped in commit `2804eda`:

- `commands/paper-lit.md:56` declares the 4-step topic precedence
  (explicit arg → latest approved scope research question →
  `project.yaml.title` → user-prompted) and pins the resolved value
  plus a `topic_source` discriminant into `lit_run.yaml`.
- `commands/paper-lit.md:101` requires the run-metadata file to carry
  `topic_source ∈ {explicit-arg, scope.research_question,
  project.yaml.title, user-prompted}` — the chat summary reads the
  same field so the user always sees which precedence step won.

## 9. Distinguish `paper-lit` from `deepresearch` in final output

Problem: Users can mistake a seeded matrix for a completed systematic review.

Recommendation:

- End `/scholar:paper-lit` with a standard note:
  "This is a single-pass seed matrix, not a PRISMA deep review."
- Recommend:
  - `/scholar:paper-review` for prose
  - `/scholar:deepresearch` for PRISMA-style screening

Acceptance criteria:

- The final chat output never implies that `paper-lit` completed deep research.

### Status — 2026-05-22 (§9 CLOSED)

Shipped in commit `2bf754f`:

- `commands/paper-lit.md:67` requires a fixed banner pinned at the
  top of `matrix.md` declaring the file is a single-pass seed, NOT
  a PRISMA review.
- `commands/paper-lit.md:132` requires the chat summary to end with
  a fixed three-line footer that names `/scholar:deepresearch` for
  PRISMA screening and `/scholar:paper-review` for prose, so the
  user can never silently mistake the matrix for a completed review.

## 10. Record command run metadata

Problem: The generated artefacts do not currently record enough command-level
metadata for later audit.

Recommendation:

- Add a small run block to `matrix.md` or a separate
  `.evidraft/literature/lit_run.yaml`:

  ```yaml
  run_id: 2026-05-22T02:xx:xx+08:00
  command: /scholar:paper-lit
  topic: Harness Engineering for Reliable AI Coding Agents
  mode: single_pass
  source_limit: 20
  retrieval: web
  validator: structural-fallback
  ```

Acceptance criteria:

- Later `/scholar:paper-review` and `/scholar:paper-check` can identify which
  literature run produced the current matrix.

### Status — 2026-05-22 (§10 CLOSED)

Shipped in commits `2804eda` (schema + initial keys) and `2bf754f`
(precedence pins added):

- `commands/paper-lit.md:101` defines the on-disk shape of
  `.evidraft/literature/lit_run.yaml` with required keys `run_id`,
  `command`, `topic`, `topic_source`, `mode`, `source_limit`,
  `retrieval`, `validator_used`. Overwrite semantics (last-write
  wins; earlier runs recoverable via `git log`).
- `docs/data-model.md:144` documents the same shape as part of the
  literature-tree schema, so downstream `paper-review` and
  `paper-check` can locate it by convention.

Both acceptance criteria met: any subsequent command can read
`lit_run.yaml` to identify which literature run produced the current
matrix.

## Suggested priority

1. Reconcile scope-stub with `scope-required`.
2. Add explicit survey-draft output for ad-hoc review requests.
3. Fix `manuscript/references.bib` symlink/sync behavior.
4. Cache web snapshots used by evidence records.
5. Add non-paper source metadata.
6. Bundle or require a BibTeX validator.
7. Add run metadata to `paper-lit`.

These changes would make the happy path clearer: initialize, scope, retrieve,
review, draft. They would also reduce ambiguity when the user wants a pragmatic
one-shot survey rather than the full PRISMA-style deep-research pipeline.
