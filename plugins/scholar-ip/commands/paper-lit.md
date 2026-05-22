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
  - path: .evidraft/literature/lit_run.yaml  # run metadata (one per invocation, last-write wins)
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

0. **Resolve the topic and pin a `run_id`.** Topic precedence (first hit wins; record which one in `lit_run.yaml`):
   1. explicit command argument (`topic_source: explicit-arg`)
   2. latest approved scope file's `# Research question` line (`topic_source: scope.research_question`)
   3. `.evidraft/project.yaml.title` (`topic_source: project.yaml.title`)
   4. ask the user (`topic_source: user-prompted`)

   Generate `run_id` as the current UTC ISO-8601 timestamp (`date -u +%Y-%m-%dT%H:%M:%SZ`). Pass `run_id` to the `scholar-search` skill so every retrieval row carries it.

1. **Inventory existing material.**
   - Look for `references.bib`, `references/*.pdf`, `papers/*.pdf`.
   - Read `.evidraft/literature/matrix.md` (may be empty).
   - Ensure the first non-blank lines of `matrix.md` are the fixed banner below (insert if missing, do not duplicate):
     ```markdown
     <!-- paper-lit: single-pass seed matrix. NOT a PRISMA review.
          For systematic screening + cluster critique, run /scholar:deepresearch. -->
     ```
2. **Online retrieval (optional).** If the user supplies a topic, load the `scholar-search` skill and request up to N (default 20) candidate papers per the URL templates / rate-limit policy in `skills/scholar-search/SKILL.md` (arXiv, Semantic Scholar, OpenAlex). For each candidate produce a structured stub (title, authors, year, venue, abstract, why-relevant). All bib edits go through `skills/bib-manager/SKILL.md` for dedup + key normalisation.
   - **Non-paper sources** (blog posts, vendor docs, engineering reports, tutorials, specs): use the `scholar-search` `webfetch` variant (`skills/scholar-search/SKILL.md` §Tier 2). It writes the page body to `.evidraft/literature/snapshots/<sha1>.md` plus a metadata stub. The `snapshots/` tree is durable evidence backing — files there are never auto-deleted; refreshes go through new `<sha1>` + `supersedes`. Record the snapshot path — step 3 will reference it.
3. **Per-paper extraction.** Use the `literature-reviewer` subagent to curate the matrix rows, then use the `evidence-auditor` subagent to spot-check each appended `type=paper` evidence row against `references.bib`. For every source you commit to (existing or new):
   - Add a clean BibTeX entry to `.evidraft/literature/references.bib`. Citation key: `firstauthorYEARkeyword` (lowercase). Non-paper sources use `@misc{...}` with real `howpublished` / `url` — never invent a venue.
   - Add one or more rows to `.evidraft/literature/matrix.md`:
     | citation_key | Source kind | Year | Venue | Problem | Method | Datasets | Key Result | Gap | Evidence ids |
     `Source kind` is `paper` (default) / `blog` / `engineering_report` / `docs` / `tutorial` / `spec`.
   - Append one evidence record per *non-trivial* claim to `.evidraft/evidence/evidence.jsonl`:
     - Formal paper: `type=paper`, default `source_kind=paper`, `citation_key`, `support` (`"Section 4.2"`, `"Table 3"`).
     - URL source: `type=paper`, `source_kind` ∈ {`blog`, `engineering_report`, `docs`, `tutorial`, `spec`}, `citation_key` (the `@misc` key), `source` is the canonical URL, `file_path` points at the `snapshots/<sha1>.md` from step 2, `line_range` is 1-indexed inclusive into that snapshot, `support` describes the section heading. See `skills/evidence-check/SKILL.md` §1.1.
     - Always `verified=false` (auditor flips later).
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
7. **Write run metadata.** Persist `.evidraft/literature/lit_run.yaml` (overwrite any prior file; last-write wins — earlier runs are recoverable through `git log`):
   ```yaml
   run_id: 2026-05-22T02:21:00Z         # the run_id pinned in step 0
   command: /scholar:paper-lit
   topic: "<resolved topic>"
   topic_source: explicit-arg | scope.research_question | project.yaml.title | user-prompted
   mode: single_pass | draft_outline    # draft_outline iff input.draft_outline=true
   source_limit: 20                     # the N from step 2
   retrieval: web | offline             # offline iff host has no network or user opted out
   validator_used: bibtex-tidy | hand-roll   # from done criteria
   draft_outline_path: .evidraft/literature/related_work_outline.md  # null when mode=single_pass
   bib_link: symlink | snapshot         # mirrors paper-init step 4 / step 6 sync
   bib_sync: noop | resynced            # from step 6
   ```
   `/scholar:paper-review`, `/scholar:paper-check`, and a future `/scholar:paper-experiment` may read this file to identify which literature run produced the current matrix.

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
- `.evidraft/literature/lit_run.yaml` exists with all required keys from step 7; `topic_source` accurately reflects which precedence step resolved the topic.
- When `draft_outline=true`: `.evidraft/literature/related_work_outline.md` exists, starts with the outline banner, and every sentence carries a `[citation_key]` resolving in `references.bib`.
- Chat summary ends with this fixed line, verbatim:

      paper-lit: single-pass seed matrix, NOT a PRISMA deep review.
      For systematic screening + cluster critique, run /scholar:deepresearch.
      For prose (related-work section), run /scholar:paper-review.

- Chat output recommends `/scholar:paper-idea` or `/scholar:paper-review` next.
