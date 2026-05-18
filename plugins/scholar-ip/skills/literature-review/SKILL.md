---
id: literature-review
title: "Literature review discipline: BibTeX hygiene, extraction, clustering"
kind: skill
phase: paper
description: >
  Load when any literature-touching command runs (/scholar:paper-lit, /scholar:paper-review,
  /scholar:paper-draft's related_work section, /scholar:paper-idea novelty matrix). Produces
  citation-key conventions, per-paper extraction recipes, method-family
  clustering rules, and the related_work outline pattern that downstream
  drafting depends on.
triggers:
  - "/scholar:paper-lit"
  - "/scholar:paper-review"
  - "/scholar:paper-idea"
  - "drafting related_work"
  - "building literature matrix"
  - "adding BibTeX entry"
provides:
  - citation-key-convention
  - bibtex-hygiene-rules
  - per-paper-extraction-recipe
  - method-family-clustering
  - related-work-outline-pattern
allowed_tools: [Read, Glob, Grep, Write, Edit]
hooks: [citation-guard, evidence-consistency]
references:
  - doc: ../evidence-check/SKILL.md
  - doc: ../../../../docs/data-model.md
  - doc: ../../../../packages/mcp/scholar-search-mcp/
---

# literature-review

## When to use

Pull this skill whenever you are about to add a paper to `.evidraft/literature/`, write a row in `matrix.md`, append a `type=paper` evidence record, or draft a related_work / survey paragraph. It is also loaded by `/scholar:paper-idea` because the novelty matrix consumes the same matrix and citation keys.

If `scholar-search-mcp` (see `packages/mcp/scholar-search-mcp/`) is available, search via that interface; otherwise operate only on user-supplied PDFs and notes.

## Inputs

- `.evidraft/literature/references.bib` (canonical BibTeX, source of truth)
- `.evidraft/literature/matrix.md`
- `.evidraft/evidence/evidence.jsonl` (filter `type=paper`)
- user PDFs under `references/`, `papers/`, or wherever the project keeps them
- optional `scholar-search-mcp` tools: `search_papers`, `get_paper_metadata`, `download_pdf`, `extract_references`

## Outputs

- new / updated lines in `references.bib`
- new rows in `matrix.md`
- new `type=paper` records appended to `evidence.jsonl`
- optional `related_work_outline.md`

## Procedure

### 1. Citation-key convention

Format: `firstauthorYEARkeyword` — all lowercase, no punctuation, ASCII only.

- `firstauthor` = lowercased family name of the first author, stripped of accents (`Müller` -> `muller`). Drop particles only if the canonical bibliographic form does (`van der Berg` -> `vanderberg`).
- `YEAR` = 4-digit publication year of the venue the paper appeared in (preprint year if only on arXiv).
- `keyword` = one short, distinctive content word from the title (lowercase, no hyphens). Prefer the noun that identifies the method, not a stop-word.

Examples:

| Title | Citation key |
|---|---|
| He et al., "Deep Residual Learning…", CVPR 2016 | `he2016resnet` |
| Vaswani et al., "Attention Is All You Need", NeurIPS 2017 | `vaswani2017attention` |
| Dosovitskiy et al., "An Image is Worth 16x16 Words", ICLR 2021 | `dosovitskiy2021vit` |

Rules:

- Keys are **stable**: once written they never get renamed. Downstream `\cite{}` and evidence records depend on them.
- If two papers collide on key, append `a`, `b`, `c`: `he2016resneta`, `he2016resnetb`.
- Never use BibTeX-default keys like `Smith:2021ab` that depend on a tool's hash.

### 2. BibTeX hygiene

Every entry in `references.bib` must:

- declare the correct entry type (`@inproceedings`, `@article`, `@misc` for arXiv, `@inbook` for chapters, `@techreport`, `@phdthesis`).
- have non-empty `author`, `title`, `year`. If unknown, write `TODO` literally — never invent.
- braces around `title` words that must keep capitalisation (`{ResNet}`, `{BERT}`).
- venue field matches entry type: `booktitle` for `@inproceedings`, `journal` for `@article`.
- include `doi` or `url` when known; arXiv preprints get `eprint = {arxiv-id}`, `archivePrefix = {arXiv}`.
- one blank line between entries.

Forbidden:

- duplicate keys (run `bib-manager-mcp:dedupe_bib` or grep manually before commit).
- non-ASCII characters outside braces; prefer `{\"u}` over raw `ü` to keep latexmk happy on all systems.
- empty fields without `TODO`.

### 3. Per-paper extraction recipe

For every paper you commit to (existing or new), produce exactly this set of artefacts in this order:

1. **BibTeX entry** in `references.bib` (see hygiene above).
2. **Matrix row** in `matrix.md`:

   ```
   | citation_key | Year | Venue | Problem | Method | Datasets | Key Result | Gap | Evidence ids |
   ```
   Each cell is short (≤ 12 words). "Key Result" carries one concrete number with units when available (`81.3 mAP on COCO val2017`).
3. **Evidence record(s)** appended to `evidence.jsonl` — one per non-trivial claim you intend to reuse downstream. Minimum shape:

   ```json
   {"id":"ev_NNNN","type":"paper","source":"arxiv:2103.xxxx","claim":"<one sentence>","support":"Section 4.2 / Table 3 / Eq. (7)","citation_key":"<key>","file_path":null,"line_range":null,"confidence":"high","verified":false}
   ```

   `verified=false` until a human auditor flips it. See `../evidence-check/SKILL.md` for full field rules.

Never write a matrix row without at least one matching evidence record. Never write an evidence record with a `citation_key` that is missing from `references.bib`.

### 4. Method-family clustering

After the matrix has ≥ 5 papers, cluster them into 3–6 method families. Families are defined by the **technical mechanism**, not the application:

- Good families: "two-stage detectors", "DETR-style set prediction", "contrastive pretraining", "diffusion posterior sampling".
- Bad families: "good papers", "recent work", "computer vision".

Each paper belongs to at most one family. Borderline cases get a sub-bullet noting the secondary family.

Write the clustering at the bottom of `matrix.md` as:

```
## Method families

### Family A: <name>
- <citation_key>, <one-line why it belongs here>
- ...

### Family B: <name>
...
```

Re-cluster when a new paper would create a 7th family — that is a signal that two existing families collapse.

### 5. Related-work outline pattern

Before writing prose in `related_work.tex`, produce `.evidraft/literature/related_work_outline.md`:

```
## Paragraph 1: <family A>
- citations: he2016resnet, dosovitskiy2021vit
- evidence: ev_0003, ev_0007
- contrast with our angle: <one sentence>

## Paragraph 2: <family B>
- citations: ...
- evidence: ...
- contrast with our angle: ...
```

Rules:

- One paragraph per family (or per tightly-related pair of families).
- Every paragraph cites ≥ 2 papers, otherwise merge it into another paragraph.
- Every paragraph ends with a contrast bullet that names our angle. If you cannot write that bullet, you do not have enough evidence to write the paragraph yet.
- Orphan citations (cited but no matching evidence record) are forbidden — either add the record or drop the citation.

When rendering the outline into LaTeX (in `/scholar:paper-review` or `/scholar:paper-draft`), every `\cite{...}` key must already exist in `references.bib`; every contrast sentence must be backed by an evidence id that the section's `*.plan.md` lists.

## Quality checklist

- [ ] Every citation key matches `firstauthorYEARkeyword`.
- [ ] No duplicate keys in `references.bib`.
- [ ] Every matrix row has ≥ 1 evidence record.
- [ ] Every evidence record's `citation_key` resolves in `references.bib`.
- [ ] Method-family section exists once `matrix.md` has ≥ 5 papers.
- [ ] `related_work_outline.md` has ≥ 3 paragraphs covering ≥ 3 families before drafting prose.
- [ ] No `TODO` fields remain in entries that the manuscript actually cites.

## Anti-patterns

- Inventing a paper, author, year, venue, or number to "fill out" a matrix row.
- Renaming a citation key after it has been used in `evidence.jsonl` or `\cite{}`.
- Paraphrasing an abstract you have not opened.
- Writing related_work paragraphs as a list of citations with no contrast to our work.
- Using strong-claim verbs (`SOTA`, `first`, `outperforms`) about prior work without an evidence id — that triggers `citation-guard` and is also factually risky.
- Letting the matrix and `evidence.jsonl` drift: any row in the matrix without a record, or any record without a row, is a bug.
