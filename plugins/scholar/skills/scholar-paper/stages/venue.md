# workflow:paper.venue

Convert the arXiv-style manuscript under `manuscript/` into a **target venue's template**, producing a parallel `submissions/<venue>/` tree. The original `manuscript/` stays untouched so the working draft never breaks.

This command is **submission-time only**. Until the venue is decided, work in `manuscript/` against the neutral arXiv style.

Read the latest paper check when available and carry its single verdict forward as
`readiness: PASS | WARN | FAIL`. Continue building the venue bundle when readiness
is `WARN` or `FAIL`; preserve the findings in the manifest and chat summary so the
user can decide whether to submit. Only workspace-safety violations block output.

## Steps

1. **Resolve the venue.** Look up the venue spec in `../../.evidraft-private/capabilities/latex/venue-formatting/venues/`. Required spec fields:
   - `documentclass`, `class_files_url` (or local path),
   - column layout, page limit, font size,
   - bib style (`natbib`, `biblatex`, `IEEEtran`, …),
   - anonymous-review requirements (`anonymize` toggle),
   - figure / table caption conventions.
2. **Copy the manuscript.** Mirror `manuscript/` into `submissions/<venue>/` without modifying the arXiv-side files.
3. **Rewrite `main.tex`.** Use the `latex-editor` subagent to handle the preamble swap, package list, and compile-error triage:
   - Swap `\documentclass{...}` and preamble to the venue style.
   - Insert / remove `\usepackage{...}` entries the venue mandates.
   - Re-link `references.bib` (copy or symlink).
   - Adjust math / theorem environments if the venue dictates.
4. **Anonymisation pass.** Use the `evidence-auditor` subagent to confirm every stripped self-citation or repo link is still backed by an alternative evidence id (so anonymisation does not silently invalidate a claim). If `anonymize=true` (default for double-blind venues — `cvpr`, `iccv`, `eccv`, `neurips`, `icml`, `iclr`, `emnlp`, `acl`):
   - Replace author block with `\author{Anonymous}`.
   - Strip funding / acknowledgements (move to a separate `acknowledgements.tex` excluded from `main.tex`).
   - Comment out any url, repo link, or self-citation marker that reveals identity.
   - Replace "our previous work [12]" patterns with neutral language.
5. **Compile sanity check.** Drive via `../../.evidraft-private/capabilities/latex/latex-build/spec.md`: run `latexmk -pdf -interaction=nonstopmode -file-line-error submissions/<venue>/main.tex`, parse the log into the six-entry taxonomy, and write `.evidraft/manuscript/compile-<ts>.errors.json`. If `latexmk` is not on `$PATH`, mark compile `SKIPPED`. Compile failure does not block bundle creation: preserve the failed source and findings, continue every check that can still run, and write the manifest with compile status `FAIL`.
6. **Page-limit check.** If the venue declares a page limit, compute the compiled length and warn if over.
7. **Write `submissions/<venue>/MANIFEST.md`:**
   - source: `manuscript/main.tex`
   - venue spec resolved from `../../.evidraft-private/capabilities/latex/venue-formatting/venues/<venue>.yaml`
   - anonymisation: on/off
   - compile status
   - page count vs limit
   - list of changes vs `manuscript/`
   - readiness: `PASS`, `WARN`, or `FAIL`, with unresolved check findings and a
     statement that bundle creation is not submission approval

## Constraints

- **Never edit `manuscript/`** here. This command produces a copy only.
- If a venue's class file is not bundled, write a `MANIFEST.md` instruction telling the user where to download it (publisher site / overleaf template).
- Do **not** auto-submit anywhere.
- Readiness and compile results are advisory for packaging. They are never treated
  as permission to submit and never suppress the submission bundle.
- If the venue forbids supplementary material to disclose author info during double-blind review, also anonymise `submissions/<venue>/supplement/` if present.

## Done criteria

- The submission tree and `MANIFEST.md` exist with every source file that could be
  copied, the resolved venue spec, readiness, and compile status. A compile failure
  remains in the bundle as an explicit finding rather than preventing output.
- Chat output prints: venue, page count, anonymisation status, missing class files (if any), and next-step recommendation (`latexmk`, overleaf upload, etc).
- Chat output also prints readiness and the count of unresolved findings. Status is
  `complete_with_gaps` when readiness is `WARN` or `FAIL`, or compilation fails or
  is skipped. Status is `blocked` only when workspace safety prevents writing the
  bundle; no status performs submission.
