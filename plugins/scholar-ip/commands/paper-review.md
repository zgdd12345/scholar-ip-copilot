---
id: paper-review
title: "Draft Related Work / survey section"
kind: command
slash: /scholar:paper-review
phase: paper
inputs:
  - name: target_section
    type: enum
    values: [related_work, survey]
    optional: true
    default: related_work
  - name: target_length
    type: string
    optional: true
    default: "1.5 pages"
outputs:
  - path: manuscript/sections/related_work.tex
  - path: .evidraft/literature/related_work_outline.md
allowed_tools: [Read, Glob, Grep, Write, Edit]
hooks: [citation-guard, evidence-consistency]
subagents: [literature-reviewer, evidence-auditor, consistency-checker]
references:
  - doc: ../skills/literature-review/SKILL.md
---

# /scholar:paper-review

Draft a `related_work` (or `survey`) section grounded **only** in the evidence store.

## Steps

1. **Load context.**
   - Parse `.evidraft/literature/matrix.md`.
   - Parse `.evidraft/evidence/evidence.jsonl` (filter `type=paper`).
   - Parse `.evidraft/project.yaml` for `field` and `target_venue`.
2. **Outline first.** Write `.evidraft/literature/related_work_outline.md` with paragraph-level bullets. Each bullet must list the `citation_key`s it will cite and the `evidence_id`s it leans on.
3. **Critique the outline.** Self-check:
   - Are there at least 3 method families covered?
   - Is each family contrasted against our angle?
   - Are there orphan citations (cited but no evidence record)? Add them or drop.
4. **Write LaTeX.** Render the outline into `manuscript/sections/related_work.tex`. Every `\cite{...}` key must exist in `references.bib`. Every paragraph ends with a one-sentence "and how our work differs" only if backed by an evidence record (otherwise omit).
5. **Update evidence.jsonl** with any new note records (`type=note`) summarising synthesised positions.

## Constraints

- No strong claim without an `evidence_id`. (citation-guard)
- No reference to a method we did not include in the matrix.
- Keep length within `target_length`; if you overshoot, prefer cutting the weakest paragraph rather than chopping mid-thought.

## Done criteria

- `related_work.tex` compiles when wrapped in the template's `main.tex`.
- All `\cite{}` keys resolve in `references.bib`.
- Outline file lists each paragraph's evidence ids.
