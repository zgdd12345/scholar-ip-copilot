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
