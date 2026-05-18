---
id: paper-venue
title: "Convert the arXiv-style manuscript into a target venue's template"
kind: command
slash: /scholar:paper-venue
phase: paper
inputs:
  - name: venue
    type: enum
    values: [arxiv, cvpr, iccv, eccv, neurips, icml, iclr, emnlp, acl, aaai, ieee, acm-generic, generic]
    optional: false
  - name: anonymize
    type: boolean
    optional: true
    default: true
  - name: out_dir
    type: path
    optional: true
    default: submissions/<venue>/
outputs:
  - path: submissions/<venue>/main.tex
  - path: submissions/<venue>/sections/
  - path: submissions/<venue>/references.bib
  - path: submissions/<venue>/MANIFEST.md
allowed_tools: [Read, Glob, Grep, Write, Edit, "Bash:cp*", "Bash:latexmk*"]
hooks: [latex-compile, citation-guard, evidence-consistency]
subagents: [latex-editor, evidence-auditor]
references:
  - doc: ../skills/venue-formatting/SKILL.md
  - doc: ../skills/latex-writing/SKILL.md
---

# /scholar:paper-venue

Convert the arXiv-style manuscript under `manuscript/` into a **target venue's template**, producing a parallel `submissions/<venue>/` tree. The original `manuscript/` stays untouched so the working draft never breaks.

This command is **submission-time only**. Until the venue is decided, work in `manuscript/` against the neutral arXiv style.

## Steps

1. **Resolve the venue.** Look up the venue spec in `skills/venue-formatting/`. Required spec fields:
   - `documentclass`, `class_files_url` (or local path),
   - column layout, page limit, font size,
   - bib style (`natbib`, `biblatex`, `IEEEtran`, …),
   - anonymous-review requirements (`anonymize` toggle),
   - figure / table caption conventions.
2. **Copy the manuscript.** Mirror `manuscript/` into `submissions/<venue>/` without modifying the arXiv-side files.
3. **Rewrite `main.tex`.**
   - Swap `\documentclass{...}` and preamble to the venue style.
   - Insert / remove `\usepackage{...}` entries the venue mandates.
   - Re-link `references.bib` (copy or symlink).
   - Adjust math / theorem environments if the venue dictates.
4. **Anonymisation pass.** If `anonymize=true` (default for double-blind venues — `cvpr`, `iccv`, `eccv`, `neurips`, `icml`, `iclr`, `emnlp`, `acl`):
   - Replace author block with `\author{Anonymous}`.
   - Strip funding / acknowledgements (move to a separate `acknowledgements.tex` excluded from `main.tex`).
   - Comment out any url, repo link, or self-citation marker that reveals identity.
   - Replace "our previous work [12]" patterns with neutral language.
5. **Compile sanity check.** Try `latexmk -pdf -interaction=nonstopmode submissions/<venue>/main.tex`. If `latex-build-mcp` is unavailable, mark as `SKIPPED`.
6. **Page-limit check.** If the venue declares a page limit, compute the compiled length and warn if over.
7. **Write `submissions/<venue>/MANIFEST.md`:**
   - source: `manuscript/main.tex`
   - venue spec resolved from `skills/venue-formatting/<venue>.yaml`
   - anonymisation: on/off
   - compile status
   - page count vs limit
   - list of changes vs `manuscript/`

## Constraints

- **Never edit `manuscript/`** here. This command produces a copy only.
- If a venue's class file is not bundled, write a `MANIFEST.md` instruction telling the user where to download it (publisher site / overleaf template).
- Do **not** auto-submit anywhere.
- If the venue forbids supplementary material to disclose author info during double-blind review, also anonymise `submissions/<venue>/supplement/` if present.

## Done criteria

- `submissions/<venue>/main.tex` compiles (or compile is `SKIPPED` with a documented reason).
- `MANIFEST.md` exists with the resolved venue spec.
- Chat output prints: venue, page count, anonymisation status, missing class files (if any), and next-step recommendation (`latexmk`, overleaf upload, etc).
