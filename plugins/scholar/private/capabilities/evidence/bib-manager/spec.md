---
id: bib-manager
title: "BibTeX manager: dedup, citation-key normalisation, missing + unused detection"
kind: skill
phase: paper
description: >
  Manage an EviDraft project's `references.bib`: dedup entries, normalise
  citation keys to the `firstauthorYEARkeyword` convention, detect `\cite{}`
  keys with no matching entry, and flag entries the manuscript never cites.
  Works on `.evidraft/literature/references.bib` plus `manuscript/references.bib`
  when the manuscript inlines its own copy. Use when adding a BibTeX entry,
  auditing `references.bib`, renaming a citation key, or running
  `workflow:paper.lit` or `workflow:paper.check`.
triggers:
  - "workflow:paper.lit"
  - "workflow:paper.check"
  - "adding BibTeX entry"
  - "auditing references.bib"
  - "renaming citation key"
provides:
  - citation-key-convention
  - bibtex-dedup-recipe
  - missing-cite-detection
  - unused-entry-detection
  - bibtex-tidy-invocation
allowed_tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - "Bash:bibtex-tidy*"
  - "Bash:grep*"
policies: [evidence-integrity]
references:
  - doc: capability:literature-review
  - doc: capability:evidence-check
  - doc: workflow:paper.lit
  - doc: workflow:paper.check
---

# bib-manager

## When to use

Load whenever `.evidraft/literature/references.bib` (or `manuscript/references.bib`) is about to be **read for audit**, **written to**, or **diffed against the manuscript**. Specifically:

- `workflow:paper.lit` — every new BibTeX entry passes through this skill before being committed.
- `workflow:paper.check` — missing-cite and unused-entry passes.
- Any one-off "is this key consistent?" question from the user.

## Shared cache + run_id convention

This skill is read+edit only; it does not retrieve from the web and writes no cache files. It **does** participate in the shared run_id convention: when called from `workflow:paper.check` or `workflow:paper.lit`, every audit row this skill emits to chat carries the caller's `run_id` (from the caller's `plan.yaml`) so the report can be cross-referenced.

The cache root reserved for retrieval skills is `.evidraft/literature/.cache/<provider>/`; this skill never writes there.

## Inputs

- `.evidraft/literature/references.bib` (the canonical bib — source of truth)
- `manuscript/references.bib` (only if the manuscript pins a separate copy; if both exist, the manuscript copy is treated as a snapshot and re-synced from `.evidraft/literature/references.bib`)
- `manuscript/sections/*.tex`, `manuscript/main.tex` (for `\cite{}` extraction)
- `.evidraft/evidence/evidence.jsonl` (records carry `citation_key`; never rename keys that appear here)

## Outputs

- in-place edits to `references.bib` (dedup, key normalisation)
- a chat-surfaced report:
  - **Missing keys**: `\cite{}` keys with no entry
  - **Unused keys**: entries never `\cite{}`d
  - **Renames proposed** (must be confirmed by the user before applying, never auto-applied)
- (`workflow:paper.check`) the corresponding sections of `.evidraft/manuscript/paper_check_report.md`

## Procedure

### 1. Citation-key convention (carried from `literature-review`)

Format: `firstauthorYEARkeyword` — all lowercase, ASCII only, no punctuation.

- `firstauthor` = lowercased family name of the first author, accent-stripped (`Müller` -> `muller`). Particles follow the canonical bibliographic form (`van der Berg` -> `vanderberg`).
- `YEAR` = 4-digit publication year (preprint year if arXiv-only).
- `keyword` = one short distinctive content word from the title — prefer the noun naming the method, not a stop-word.

Collisions append `a`, `b`, `c`: `he2016resneta`, `he2016resnetb`.

### 2. Dedup recipe

1. **Parse** `references.bib`. Treat each `@<type>{<key>, ... }` block as one entry; preserve comments and blank lines between entries.
2. **Group rows** by (in this order):
   - normalised DOI (lowercase, strip `https://doi.org/`), then
   - (normalised title, first-author surname, year) for entries without DOI.
3. **Within a group**:
   - Keep the entry with the **longer abstract** (or, if neither has an abstract, the one with more populated fields).
   - If years differ by ≤ 1 (preprint year vs. published year), keep the **published** year and stash the preprint year in a comment `% arXiv preprint: <year>`.
   - Reconcile field-by-field: prefer the **non-empty** value; if both non-empty and they disagree on `author`, flag the row for human review with `% TODO: author mismatch` and do not overwrite.
4. **Surface the merge plan to chat before applying any deletion.** Never delete an entry silently.
5. **Never rename a `citation_key`** that is referenced in `manuscript/sections/*.tex` or appears as `citation_key` on any row in `.evidraft/evidence/evidence.jsonl`.

### 3. Missing-cite detection

Detect `\cite{}` keys in the manuscript that have no matching entry in `references.bib`:

```
grep -rhoE '\\(?:cite|citet|citep|citeauthor|citeyear)\{[^}]+\}' manuscript/sections/*.tex manuscript/main.tex \
  | sed -E 's/\\(cite|citet|citep|citeauthor|citeyear)\{//; s/\}$//' \
  | tr ',' '\n' \
  | sed 's/^ *//; s/ *$//' \
  | sort -u
```

(Use the host's `Grep` tool with regex `\\(?:cite|citet|citep|citeauthor|citeyear)\{[^}]+\}` against `manuscript/sections/*.tex` and `manuscript/main.tex`. Split multi-key cites on `,` and trim whitespace.)

Cross-check the resulting key set against the `@<type>{<key>, ...}` keys in `references.bib`. Emit:

```
Missing keys:
  - <key>     (cited in <file>:<line>)
  - ...
```

For each missing key, recommend either (a) adding the entry via `literature-review` skill + `scholar-search` skill, or (b) removing the orphan `\cite{}`. Do **not** invent a bib entry.

### 4. Unused-entry detection

Inverse pass. For every `@<type>{<key>, ...}` key in `references.bib`, check whether `\cite*{...<key>...}` appears in `manuscript/sections/*.tex` or `manuscript/main.tex`. Emit:

```
Unused entries:
  - <key>     (defined in references.bib:<line>)
  - ...
```

Unused entries are **flagged, never auto-deleted**. The author may keep an entry for an upcoming draft section. The `workflow:paper.check` report includes the list under "Unused keys".

### 5. Optional `bibtex-tidy` invocation

If the `bibtex-tidy` binary is available on `$PATH` (Node.js: `npm i -g bibtex-tidy`), prefer it for whitespace + duplicate normalisation:

```
bibtex-tidy --curly --duplicates=key,doi,citation --no-align --no-modify --trailing-commas references.bib
```

Flags:

- `--curly` — wrap field values in `{...}` (consistent with the `literature-review` hygiene rule).
- `--duplicates=key,doi,citation` — detect by key, by DOI, and by full citation.
- `--no-align` — do not column-align field names (keeps diffs readable).
- `--no-modify` — first run is **dry**: print diff only, await user confirmation.
- After the user confirms, drop `--no-modify` and re-run to apply.

If `bibtex-tidy` is not on `$PATH`, hand-roll the dedup using the procedure in §2. Never silently skip dedup.

### 6. Re-sync `manuscript/references.bib`

If a separate `manuscript/references.bib` exists, after every edit to `.evidraft/literature/references.bib`:

1. Diff the two files.
2. Copy `.evidraft/literature/references.bib` to `manuscript/references.bib` (canonical source wins).
3. Run `latex-build` (if loaded) on `manuscript/main.tex` to confirm the manuscript still compiles.

## Quality checklist

- [ ] No duplicate keys in `references.bib` (grep `^@\w+\{[^,]+,` and sort -u; counts must match).
- [ ] Every entry has non-empty `author`, `title`, `year` (else `TODO` literally).
- [ ] No entry was deleted without surfacing the deletion to chat.
- [ ] No key was renamed if it appears in `manuscript/sections/` or `evidence.jsonl`.
- [ ] Missing-cite list and unused-entry list both empty (or the user accepted them).
- [ ] If `bibtex-tidy` was used, the first run was `--no-modify`.

## Anti-patterns

- Renaming a `citation_key` that the manuscript or `evidence.jsonl` already references.
- Deleting an "unused" entry without asking the user — the author may be drafting a section that hasn't been written yet.
- Auto-merging two different papers because their titles happen to match (always require DOI or (title, first-author, year) consensus).
- Running `bibtex-tidy` without `--no-modify` on the first pass (silent destructive edit).
- Inventing a missing entry. Missing means "go fetch it via `scholar-search`", not "make one up".
- Editing a `manuscript/references.bib` directly without re-syncing from the canonical `.evidraft/literature/references.bib`.
