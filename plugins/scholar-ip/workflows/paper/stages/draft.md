# workflow:paper.draft

Write the LaTeX paper. **Outline → section plan → LaTeX**, never straight to prose.

## Steps

1. **Sanity-check the evidence store.**
   - Refuse to draft if `evidence.jsonl` is empty.
   - Refuse to draft if no `method_to_code.md` exists when `project_type=paper`.
2. **Outline pass.** Use the `evidence-auditor` subagent to verify every promise has an evidence id before drafting prose. Produce `.evidraft/manuscript/outline.md` listing every section, every subsection, and 1–3 bullet "promises" per subsection. Each promise is annotated with the evidence ids it will rely on.
3. **Section-plan pass.** Use the `methodology-reviewer` subagent to sanity-check that the planned equations and figures match `method_to_code.md`. For each section file under `manuscript/sections/`, write a `<section>.plan.md` next to it (e.g. `method.plan.md`) describing equation placeholders, figure/table inserts, and claim → evidence map.
4. **LaTeX pass.** Use the `latex-editor` subagent to own structure, style consistency, and compile-error triage. Now write `.tex` content:
   - `manuscript/main.tex` orchestrates with `\input{sections/...}`.
   - Each section file contains the actual prose plus `\cite{}` / `\ref{}` / `\input{<table>}`.
   - Tables `\input{../.evidraft/experiments/tables/<id>.tex}`.
5. **Self-checks** (do these before declaring done):
   - Every `\cite{}` key exists in `references.bib`.
   - Every `\ref{}` resolves to a `\label{}` somewhere in the manuscript.
   - Every numeric claim has an evidence id in the matching `*.plan.md`.
   - Citation-guard verbs are gated.
6. **Optional compile.** Call the `latex-build` skill on `manuscript/main.tex` (it wraps `latexmk -pdf -interaction=nonstopmode` and writes a structured `errors.json`). If `latexmk` is not installed in this environment, describe the command to the user instead.

## Constraints

- Strong-claim verbs (SOTA, first, novel, outperform, significant, state-of-the-art) require an `evidence_id` or `citation_key` in the matching plan. (policy:evidence-integrity)
- No numbers without provenance. (policy:evidence-integrity)
- No code claim without `file_path` + line range. (policy:evidence-integrity)
- Style preset only changes preamble and column count, not content rules.

## Done criteria

- `outline.md` exists.
- `*.plan.md` exists for every section that has prose.
- `main.tex` includes all selected sections.
- The chat output ends with the compile command and any unresolved `\cite{}` / `\ref{}` warnings.

