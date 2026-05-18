---
id: paper-lit
title: "Literature retrieval and matrix"
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
outputs:
  - path: .evidraft/literature/references.bib
  - path: .evidraft/literature/matrix.md
  - path: .evidraft/evidence/evidence.jsonl  # append-only
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
2. **Online retrieval (optional).** If the user supplies a topic, load the `scholar-search` skill and request up to N (default 20) candidate papers per the URL templates / rate-limit policy in `skills/scholar-search/SKILL.md` (arXiv, Semantic Scholar, OpenAlex). For each candidate produce a structured stub (title, authors, year, venue, abstract, why-relevant). All bib edits go through `skills/bib-manager/SKILL.md` for dedup + key normalisation.
3. **Per-paper extraction.** For every paper you commit to (existing or new):
   - Add a clean BibTeX entry to `.evidraft/literature/references.bib`. Citation key: `firstauthorYEARkeyword` (lowercase).
   - Add one or more rows to `.evidraft/literature/matrix.md`:
     | citation_key | Year | Venue | Problem | Method | Datasets | Key Result | Gap | Evidence ids |
   - Append one evidence record per *non-trivial* claim to `.evidraft/evidence/evidence.jsonl` with `type=paper`, `citation_key`, `claim`, `support` ("Section 4.2", "Table 3", …), and `verified=false` (auditor flips later).
4. **Cluster.** At the end, write a brief "Method family" summary into the bottom of `matrix.md` grouping papers into 3–6 method families.

## Constraints

- **Never** invent a paper, author, year, or result. If you cannot verify a field, leave it blank with `TODO`.
- **Never** include a strong claim verb (SOTA / first / novel / outperforms) without a `citation_key` (citation-guard).
- BibTeX keys are stable — once written, do not rename.
- The matrix is markdown, not HTML; keep it grep-friendly.

## Done criteria

- `references.bib` parses with a standard BibTeX validator (e.g. `bibtexparser`).
- `matrix.md` has ≥ 1 row per cited paper.
- `evidence.jsonl` has ≥ 1 `type=paper` record per cited paper.
- Chat output recommends `/scholar:paper-idea` or `/scholar:paper-review` next.
