---
id: latex-writing
title: "LaTeX writing pipeline, neutral arXiv preamble, label conventions, error triage"
kind: skill
phase: paper
description: >
  Load when /scholar:paper-draft, /scholar:paper-venue, or /scholar:paper-check run. Provides the
  outline -> section-plan -> LaTeX pipeline, a neutral arXiv preamble template,
  equation / figure / table label conventions, the manuscript-vs-venue
  decoupling rule, and a triage table for common latexmk errors.
triggers:
  - "/scholar:paper-draft"
  - "/scholar:paper-venue"
  - "/scholar:paper-check"
  - "writing manuscript/main.tex"
  - "writing manuscript section"
  - "fixing latexmk error"
provides:
  - draft-pipeline
  - arxiv-preamble-template
  - label-conventions
  - manuscript-venue-decoupling
  - latexmk-error-triage
allowed_tools: [Read, Glob, Grep, Write, Edit, "Bash:latexmk*"]
hooks: [citation-guard, evidence-consistency, latex-compile]
references:
  - doc: ../evidence-check/SKILL.md
  - doc: ../venue-formatting/SKILL.md
  - doc: ../experiment-analysis/SKILL.md
  - doc: ../latex-build/SKILL.md
---

# latex-writing

## When to use

Load whenever LaTeX source under `manuscript/` is being created, edited, or compiled. The skill is also the reference for `/scholar:paper-venue` (which copies a manuscript and rewrites the preamble) and `/scholar:paper-check` (which audits compile output).

Compile and error-parsing are owned by the sibling `latex-build` skill (which wraps `latexmk` and parses `main.log` into a structured error taxonomy). Call into it instead of invoking `latexmk` ad hoc — the error categories the `latex-compile` hook consumes are defined there.

## Inputs

- `.evidraft/manuscript/outline.md`
- `manuscript/sections/*.plan.md`
- `.evidraft/literature/references.bib` (symlinked or copied into `manuscript/`)
- `.evidraft/experiments/tables/*.tex`
- `.evidraft/code/method_to_code.md` (for method-section structure)

## Outputs

- `manuscript/main.tex`
- `manuscript/sections/*.tex`
- `manuscript/preamble.tex` (split from main when useful)

## Procedure

### 1. Pipeline: outline -> section plan -> LaTeX

Never go straight from "I need to write the method" to `\section{Method} ...`. Always:

1. **Outline pass.** Write `.evidraft/manuscript/outline.md`. Every section and subsection gets 1-3 "promise" bullets, each annotated with the evidence ids it will rely on.

   ```
   ## 3. Method
   ### 3.1 Backbone
   - We adopt a transformer encoder. (ev_0042, ev_0001)
   - We modify the attention to use rotary embeddings. (ev_0044)
   ```

2. **Section-plan pass.** For each section file `manuscript/sections/<name>.tex`, write a sibling `<name>.plan.md` listing:
   - equations to introduce (with target label names),
   - figures and tables to `\input` (with file paths),
   - claim -> evidence map (one row per claim that needs grounding).

3. **LaTeX pass.** Only after the plan is in place, write `.tex` content. Each sentence in prose that makes a claim must be traceable back to a row in `*.plan.md`.

Going out of order (writing LaTeX first, retrofitting the outline) is the single biggest source of evidence drift.

### 2. Neutral arXiv preamble template

The default style is arXiv-neutral: `\documentclass{article}`, single column, no venue assumptions. Keep `manuscript/main.tex` style-stable so `/scholar:paper-venue` can swap the preamble without touching prose.

```latex
% manuscript/main.tex
\documentclass[11pt]{article}

% Geometry: arXiv-friendly, generous margins. Venue conversion overrides.
\usepackage[a4paper, margin=1in]{geometry}

% Encoding and language (TeX Live recent defaults).
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{microtype}

% Math.
\usepackage{amsmath, amssymb, amsthm, mathtools}

% Tables and figures.
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{caption}
\usepackage{subcaption}

% Citations: natbib for author-year by default; venues swap to biblatex / IEEEtran.
\usepackage[numbers,sort&compress]{natbib}

% Hyperlinks last (after most packages).
\usepackage[hidelinks]{hyperref}
\usepackage{cleveref}

% Project-local commands.
\input{macros}  % optional

\title{TITLE}
\author{Author One \and Author Two}
\date{}

\begin{document}
\maketitle

\begin{abstract}
\input{sections/abstract}
\end{abstract}

\input{sections/introduction}
\input{sections/related_work}
\input{sections/method}
\input{sections/experiments}
\input{sections/conclusion}

\bibliographystyle{plainnat}
\bibliography{references}

\end{document}
```

Rules:

- Keep `\usepackage` lines minimal. Every package is a venue-conversion risk.
- Project-local macros live in `manuscript/macros.tex` and are `\input`-ed. Do not redefine standard control sequences.
- The preamble is the **only** thing `/scholar:paper-venue` should rewrite. Section prose should not break under a different preamble.

### 3. Label conventions

Labels are the spine of cross-references. Predictable label names keep `\ref{}`, `\cref{}`, and `\eqref{}` deterministic.

| Kind | Pattern | Example |
|---|---|---|
| Equation | `eq:<section-tag>-<thing>` | `eq:method-loss`, `eq:method-grad-step` |
| Figure | `fig:<section-tag>-<thing>` | `fig:method-architecture` |
| Table | `tab:<section-tag>-<thing>` | `tab:experiments-coco` |
| Section | `sec:<short>` | `sec:method` |
| Algorithm | `alg:<short>` | `alg:training` |
| Theorem / Lemma | `thm:<short>` / `lem:<short>` | `thm:convergence` |

Rules:

- `<section-tag>` is the section's short id (`method`, `experiments`, `intro`, `related`), not the section number.
- Kebab-case after the prefix. No underscores in labels — they are easy to typo and clash with BibTeX keys.
- Every `\caption{}` is immediately followed by `\label{}`. The label without a caption is harmless but the inverse breaks `\cref`.
- One label per object. Two figures sharing a label is silent breakage; `/scholar:paper-check` flags it.

### 4. Keeping manuscript style decoupled from venue style

The `manuscript/` tree is **always** arXiv-style. The `submissions/<venue>/` tree is the venue-style copy. Rules to keep them decoupled:

- Don't write venue-specific commands (`\cvprfinalcopy`, `\acmConference`, `\IEEEspecialpapernotice`) anywhere in `manuscript/`.
- Don't hard-code page limits in the prose (no "in this 8-page paper"). Length is a `/scholar:paper-venue` concern.
- Don't anonymise in `manuscript/`. Anonymisation is applied during venue conversion when the venue is double-blind.
- Don't `\input` files outside `manuscript/` except for `.evidraft/experiments/tables/*.tex` (via a stable relative path).
- Use `\citep{}` / `\citet{}` (natbib) in prose; venues that need a different citation style get rewritten by the venue pass, not retyped.

If a venue forces a structural change (e.g. ACM CCS concepts block), put that in `submissions/<venue>/` only.

### 5. latexmk error triage

When `latexmk -pdf -interaction=nonstopmode manuscript/main.tex` fails, parse the log and map to one of the following families. Do not silently retry; report the family and the fix.

| Error signal | Family | Typical cause | Fix |
|---|---|---|---|
| `! Missing $ inserted.` | unbalanced math | text mode operator like `_` or `^`, or an unmatched `$` | wrap in `$...$` or escape `\_`; check the line with `grep -n` near the reported line number |
| `! Undefined control sequence. l.<n> \foo` | missing package / typo | package not included or command misspelled | add `\usepackage{<pkg>}`; or fix spelling; never `\let\foo\relax` to silence |
| `! LaTeX Error: File ``<x>.tex'' not found.` | missing input | `\input{sections/<x>}` path wrong or file not committed | check `ls manuscript/sections/`; correct the path; make `\input` relative to `main.tex` |
| `Package biblatex Warning: ...` or `bibtex: I found no \citation commands` | bib pipeline | `\bibliography{references}` not run; using natbib but file expects biblatex | run `bibtex` / `biber`; ensure `\bibliographystyle` matches; check `latexmk` is configured for the right backend |
| `Package natbib Error: Bibliography not compatible with author-year citations.` | bib style mismatch | `plainnat` not selected | set `\bibliographystyle{plainnat}` (or appropriate venue style) |
| `! Package inputenc Error: Unicode character ... not set up.` | input encoding | raw unicode without `inputenc utf8` | add `\usepackage[utf8]{inputenc}`; or replace with TeX accents in `references.bib` |
| `Citation `xxx' on page Y undefined` | missing bib key | `\cite{xxx}` but `xxx` not in `references.bib` | add the entry (via `literature-review` skill); never delete the cite silently |
| `Reference `xxx' on page Y undefined` | unresolved label | `\ref{xxx}` but no `\label{xxx}` exists | add the label, or fix the ref to match an existing label |
| `LaTeX Warning: Label multiply defined.` | duplicate label | two captions share a label | rename one — `/scholar:paper-check` will list both |
| `Overfull \hbox (... too wide)` | box overflow | long word / URL not breakable | `\sloppy` locally, or `\url{}` for URLs, or break the word |
| `! Emergency stop.` after the last error | terminal | preceded by a real error above | scroll up; never act on `Emergency stop.` alone |

Triage workflow:

1. Run with `-interaction=nonstopmode` and capture full log.
2. Match the first error against the table.
3. Fix one error at a time and recompile — fixing several at once obscures which fix did what.
4. After `0 errors, 0 warnings (or only overfull \hbox warnings)`, move on. Stop trying to silence overfull boxes unless `/scholar:paper-check` flags them at submission.

## Quality checklist

- [ ] `outline.md` exists before any `*.tex` prose.
- [ ] Each `manuscript/sections/<name>.tex` has a matching `<name>.plan.md`.
- [ ] Every claim in prose has an evidence id in the matching plan.
- [ ] Every `\cite{}` resolves in `references.bib`.
- [ ] Every `\ref{}` and `\cref{}` resolves to exactly one `\label{}`.
- [ ] All tables are `\input`ed from `.evidraft/experiments/tables/`; none authored inline.
- [ ] Preamble is the arXiv-neutral template; no venue-specific commands in `manuscript/`.
- [ ] `latexmk` returns 0 errors (warnings triaged or accepted).

## Anti-patterns

- Writing `\section{...} <prose>` before the section plan exists.
- Hard-coding venue commands in `manuscript/`.
- Anonymising `manuscript/` "to be safe" — that's venue-conversion's job.
- Putting `\caption` and `\label` inside the `.evidraft/experiments/tables/` files (those wrap in the section).
- Silencing `Citation undefined` by deleting the `\cite{}` instead of adding the bib entry.
- Editing the preamble per section. Preamble lives once, in `main.tex` (or `preamble.tex` it `\input`s).
- Letting `latexmk` warnings accumulate. Triage and resolve before declaring a section done.
