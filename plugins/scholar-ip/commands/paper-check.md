---
id: paper-check
title: "Audit the manuscript for citations, LaTeX, refs, and number provenance"
kind: command
slash: /scholar:paper-check
phase: paper
outputs:
  - path: .evidraft/manuscript/paper_check_report.md
allowed_tools: [Read, Glob, Grep, Write, Edit, "Bash:latexmk*", "Bash:bibtex-tidy*"]
hooks: [citation-guard, evidence-consistency, latex-compile]
subagents: [evidence-auditor, methodology-reviewer, latex-editor]
references:
  - doc: ../skills/evidence-check/SKILL.md
  - doc: ../skills/latex-writing/SKILL.md
  - doc: ../skills/latex-build/SKILL.md
  - doc: ../skills/bib-manager/SKILL.md
---

# /scholar:paper-check

Produce a single audit report covering everything that can break a paper before submission.

## Steps

1. **Citation audit.** Drive via `skills/bib-manager/SKILL.md`:
   - List `\cite{}` keys with no entry in `references.bib`.
   - List `references.bib` entries that are never cited.
   - Flag strong-claim verbs not within 30 chars of a `\cite{}` or `evidence_id` marker.
2. **LaTeX audit.** Drive via `skills/latex-build/SKILL.md`:
   - Compile with `latexmk -pdf -interaction=nonstopmode -file-line-error manuscript/main.tex`.
   - Parse `manuscript/main.log` into the six-entry error taxonomy (MISSING_CITE, MISSING_REF, UNDEFINED_COMMAND, UNBALANCED_BRACES, PACKAGE_NOT_FOUND, OTHER) and write `.evidraft/manuscript/compile-<ts>.errors.json`.
   - Report errors and warnings.
   - Catch unresolved `\ref{}`, `\eqref{}`, and `\label{}` collisions.
3. **Figure/Table audit.**
   - Every `\includegraphics{}` and every `\input{*.tex}` table is reachable.
   - Every figure/table has a `\caption{}` and a `\label{}`.
   - Every figure/table is referenced at least once.
4. **Claim-evidence audit.**
   - For each section, walk the prose for numeric tokens and strong-claim verbs.
   - Cross-check each match against the section's `*.plan.md` and `evidence.jsonl`.
   - Flag any claim without an evidence id.
5. **Number-source audit.**
   - Every number in tables should come from `.evidraft/experiments/result_analysis.md` (or an evidence record).
   - Numbers that don't match the source row flagged as `MISMATCH`.

## Output

Write `.evidraft/manuscript/paper_check_report.md`:

```
# Paper check report

Generated: <iso datetime>
Manuscript: manuscript/main.tex

## Citation
- Missing keys: ...
- Unused keys: ...
- Strong claims without citation: ...

## LaTeX
- Compile: PASS / FAIL
- Errors: ...
- Warnings: ...

## Figures & tables
- Unreached figures: ...
- Missing captions/labels: ...

## Claim-evidence
- Claims without evidence: ...

## Numbers
- Numbers without source: ...
- Mismatches: ...
```

## Constraints

- Read-only: do not silently fix issues here. If a fix is obvious, recommend it, do not apply it.
- If `latexmk` is unavailable on `$PATH`, mark "Compile" as `SKIPPED` and continue (per `skills/latex-build/SKILL.md`).

## Done criteria

- Report file exists and ends with an overall verdict line: `PASS` / `WARN` / `FAIL`.
- Chat output prints the verdict and counts per section.
