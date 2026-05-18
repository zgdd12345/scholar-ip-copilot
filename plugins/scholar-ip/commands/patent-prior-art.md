---
id: patent-prior-art
title: "Collect prior art and build a comparison chart"
kind: command
slash: /scholar:patent-prior-art
phase: patent
inputs:
  - name: seed_patents
    type: list
    optional: true
  - name: seed_papers
    type: list
    optional: true
outputs:
  - path: .evidraft/patent/prior_art_map.md
  - path: .evidraft/patent/claim_chart.md
allowed_tools: [Read, Glob, Grep, Write, Edit]
hooks: [evidence-consistency]
subagents: [literature-reviewer, patent-engineer, novelty-critic]
references:
  - doc: ../skills/patent-disclosure/SKILL.md
  - doc: ../skills/evidence-check/SKILL.md
---

# /scholar:patent-prior-art

Build a prior-art map for each candidate invention. **Online retrieval requires
`patent-search-mcp`; if absent, operate on user-supplied PDFs / patent numbers
/ BibTeX.**

## Steps

1. **Collect.** Gather inputs:
   - `invention_candidates.md` (the targets),
   - `references.bib` (academic prior art),
   - user-supplied patent numbers / pdfs / urls,
   - any output from `patent-search-mcp` if available.
2. **Per-candidate map.** For each candidate, write a section in `prior_art_map.md`:
   ```
   ## C-001 <name>
   ### Patent prior art
   - US-1234567-B2 (assignee, date) — relevance: <high/med/low>, summary, why-different
   ### Academic prior art
   - smith2021methodx — relevance, summary, why-different
   ### Notes / gaps
   ```
3. **Claim chart skeleton.** Update `.evidraft/patent/claim_chart.md`:
   | Claim element | Specification support | Code support | Prior art overlap | Risk | Suggested revision |
   - Pre-populate one row per high-level element of the proposed claim (placeholders are fine; `/scholar:patent-claims` will fill them).
4. **Risk lines.** Mark `high` on any element where prior art looks very close; suggest a revision angle.

## Constraints

- Do not declare a candidate "patentable" or "non-patentable" — risk levels only.
- For each prior-art reference, record the source (patent number, doi, url) so reviewers can verify.
- Citation discipline applies: claims of novelty here also need evidence.

## Done criteria

- `prior_art_map.md` has one section per candidate from `invention_candidates.md`.
- `claim_chart.md` has at least one row per candidate.
- Chat output recommends `/scholar:patent-disclosure` next.
