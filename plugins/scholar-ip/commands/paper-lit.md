---
id: paper-lit
title: "Literature retrieval and matrix"
description: >
  Build a single-pass literature matrix for an EviDraft paper project:
  query arXiv, Semantic Scholar, and OpenAlex via the `scholar-search`
  skill; dedup candidates; populate matrix rows with method-family
  clusters; and append `type=paper` evidence records. For multi-pass
  heavyweight reviews use `/scholar:deepresearch` instead. Use when
  seeding references for a new paper, refreshing a stale matrix, or
  right after `/scholar:brainstorming` produces a new scope.
kind: command
slash: /scholar:paper-lit
phase: paper
inputs:
  - name: topic
    type: string
    optional: true
  - name: seed_pdfs
    type: list
    optional: true
  - name: seed_bibtex
    type: path
    optional: true
  - name: draft_outline
    type: boolean
    optional: true
    default: false
    description: >
      When true, also write a method-family outline to
      .evidraft/literature/related_work_outline.md. This is a lightweight
      survey aid for ad-hoc review requests — NOT a PRISMA review and not the
      `related_work.draft.md` produced by /scholar:deepresearch Stage 6.
outputs:
  - path: .evidraft/literature/references.bib
  - path: .evidraft/literature/matrix.md
  - path: .evidraft/evidence/evidence.jsonl  # append-only
  - path: .evidraft/literature/related_work_outline.md  # only when draft_outline=true
allowed_tools: [Read, Glob, Grep, Write, Edit, WebSearch, WebFetch, "Bash:cat*"]
hooks: [citation-guard, evidence-consistency]
subagents: [literature-reviewer, evidence-auditor]
references:
  - doc: ../skills/literature-review/SKILL.md
  - doc: ../skills/scholar-search/SKILL.md
  - doc: ../skills/bib-manager/SKILL.md
  - doc: ../skills/evidence-check/SKILL.md
---

# /scholar:paper-lit

Build a literature foundation for the paper. Online retrieval uses the host-native `WebSearch` + `WebFetch` tools driven by the `scholar-search` skill (`skills/scholar-search/SKILL.md`); **if the host has no network, operate only on what the user already provided** (PDFs in `references/`, BibTeX in `references.bib`, notes in `.evidraft/literature/`).

## Steps

1. **Inventory existing material.**
   - Look for `references.bib`, `references/*.pdf`, `papers/*.pdf`.
   - Read `.evidraft/literature/matrix.md` (may be empty).
   - Ensure the first non-blank lines of `matrix.md` are the fixed banner below (insert if missing, do not duplicate):
     ```markdown
     <!-- paper-lit: single-pass seed matrix. NOT a PRISMA review.
          For systematic screening + cluster critique, run /scholar:deepresearch. -->
     ```
2. **Online retrieval (optional).** If the user supplies a topic, load the `scholar-search` skill and request up to N (default 20) candidate papers per the URL templates / rate-limit policy in `skills/scholar-search/SKILL.md` (arXiv, Semantic Scholar, OpenAlex). For each candidate produce a structured stub (title, authors, year, venue, abstract, why-relevant). All bib edits go through `skills/bib-manager/SKILL.md` for dedup + key normalisation.
3. **Per-paper extraction.** Use the `literature-reviewer` subagent to curate the matrix rows, then use the `evidence-auditor` subagent to spot-check each appended `type=paper` evidence row against `references.bib`. For every paper you commit to (existing or new):
   - Add a clean BibTeX entry to `.evidraft/literature/references.bib`. Citation key: `firstauthorYEARkeyword` (lowercase).
   - Add one or more rows to `.evidraft/literature/matrix.md`:
     | citation_key | Year | Venue | Problem | Method | Datasets | Key Result | Gap | Evidence ids |
   - Append one evidence record per *non-trivial* claim to `.evidraft/evidence/evidence.jsonl` with `type=paper`, `citation_key`, `claim`, `support` ("Section 4.2", "Table 3", …), and `verified=false` (auditor flips later).
4. **Cluster.** At the end, write a brief "Method family" summary into the bottom of `matrix.md` grouping papers into 3–6 method families.
5. **Outline (only when `draft_outline=true`).** Write `.evidraft/literature/related_work_outline.md` — a lightweight survey aid, **not** a PRISMA review:
   - One H2 per method family from step 4 (`## <family name>`).
   - Each family gets 2–4 sentences that read as a paragraph outline (not bullets). Every sentence must end with `[citation_key]` resolving to an entry already in `references.bib`. Strong-claim verbs (SOTA / first / novel / outperforms) need a citation_key in the same sentence — citation-guard enforces this.
   - End the file with a final H2 `## Gaps` listing 2–4 sentences describing what no included paper does — same citation rules.
   - The file's first line must be the banner:
     ```markdown
     <!-- paper-lit --draft-outline: lightweight survey aid. NOT /scholar:deepresearch Stage 6 (related_work.draft.md). -->
     ```
   - If `draft_outline=false` (default), skip this step entirely; do **not** write `related_work_outline.md`.
6. **Sync manuscript bibliography.** The canonical BibTeX lives at `.evidraft/literature/references.bib`. If `manuscript/references.bib` is a symlink to it (the `/scholar:paper-init` happy path), the manuscript side is already current — skip. Otherwise:
   ```bash
   if [ ! -L manuscript/references.bib ]; then
     cp .evidraft/literature/references.bib manuscript/references.bib
     echo "manuscript/references.bib: re-synced from canonical (snapshot mode)"
   fi
   ```
   Report `bib_sync: noop | resynced` in the chat summary.

## Constraints

- **Never** invent a paper, author, year, or result. If you cannot verify a field, leave it blank with `TODO`.
- **Never** include a strong claim verb (SOTA / first / novel / outperforms) without a `citation_key` (citation-guard).
- BibTeX keys are stable — once written, do not rename.
- The matrix is markdown, not HTML; keep it grep-friendly.

## Done criteria

- `references.bib` passes the validation chain described in `skills/bib-manager/SKILL.md §5` and `skills/bib-audit/SKILL.md §5.1` (prefer `bibtex-tidy`; fall back to the hand-rolled parser the same skills use). Chat output reports `validator_used: bibtex-tidy | hand-roll`.
- `matrix.md` has ≥ 1 row per cited paper and starts with the "NOT a PRISMA review" banner from step 1.
- `evidence.jsonl` has ≥ 1 `type=paper` record per cited paper.
- `manuscript/references.bib` is in sync with the canonical file (step 6). Chat reports `bib_sync: noop | resynced`.
- When `draft_outline=true`: `.evidraft/literature/related_work_outline.md` exists, starts with the outline banner, and every sentence carries a `[citation_key]` resolving in `references.bib`.
- Chat summary ends with this fixed line, verbatim:

      paper-lit: single-pass seed matrix, NOT a PRISMA deep review.
      For systematic screening + cluster critique, run /scholar:deepresearch.
      For prose (related-work section), run /scholar:paper-review.

- Chat output recommends `/scholar:paper-idea` or `/scholar:paper-review` next.
