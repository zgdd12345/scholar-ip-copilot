# workflow:paper.review

Draft a `related_work` (or `survey`) section grounded **only** in the evidence store.

## Steps

1. **Load context.**
   - Parse `.evidraft/literature/matrix.md`.
   - Parse `.evidraft/evidence/evidence.jsonl` (filter `type=paper`).
   - Parse `.evidraft/project.yaml` for `field` and `target_venue`.
2. **Outline first.** Use the `literature-reviewer` subagent to cluster the matrix into method families before bullet-writing. Write `.evidraft/literature/related_work_outline.md` with paragraph-level bullets. Each bullet must list the `citation_key`s it will cite and the `evidence_id`s it leans on.
3. **Critique the outline.** Use the `evidence-auditor` subagent to surface any orphan citations (cited but no evidence record) and the `consistency-checker` subagent to flag terminology / method-family drift across paragraphs. Self-check:
   - Are there at least 3 method families covered?
   - Is each family contrasted against our angle?
   - Are there orphan citations (cited but no evidence record)? Add them or drop.
4. **Render the prose.** Branch on `format`:

   - **`format=tex` (default).** Render the outline into `manuscript/sections/<target_section>.tex`. Use `\cite{key}` / `\citet{key}` / `\citep{key}`. Every `\cite{...}` key must exist in `references.bib`. Every paragraph ends with a one-sentence "and how our work differs" only if backed by an evidence record (otherwise omit).
   - **`format=md`.** Render the outline into `.evidraft/literature/<target_section>.md`. Use Pandoc-style inline citations: `[@key]` for a single citation, `[@key1; @key2]` for multiple, `@key` (no brackets) for narrative citations. Every key must exist in `references.bib`. The first line must be the banner:
     ```markdown
     <!-- paper-review --format=md: prose preview, not LaTeX. For the manuscript-ready version run `workflow:paper.review` (default format=tex). -->
     ```
     Section heading is `## <Title-cased target_section>` (e.g. `## Related Work`). Same paragraph discipline as the tex branch — one closing "how our work differs" sentence per paragraph, only when backed by an evidence record.

   `policy:evidence-integrity` enforces the same strong-claim ↔ citation rule on both files (`\cite{}`, `ev_NNNN`, and `[@key]` are all accepted markers; see `policy:evidence-integrity`).

5. **Update evidence.jsonl** with any new note records (`type=note`) summarising synthesised positions.

## Constraints

- No strong claim without an `evidence_id` or matching `citation_key`. (policy:evidence-integrity)
- No reference to a method we did not include in the matrix.
- Keep length within `target_length`; if you overshoot, prefer cutting the weakest paragraph rather than chopping mid-thought.
- Switching `format` does **not** invalidate the outline — re-render only the chosen file. Re-running with the same `format` overwrites the previous render (last-write wins; recover via `git log` if needed).

## Done criteria

- `format=tex`: `related_work.tex` compiles when wrapped in the template's `main.tex`; all `\cite{}` keys resolve in `references.bib`.
- `format=md`: `related_work.md` starts with the banner; every paragraph has at least one `[@key]` / `@key` whose key resolves in `references.bib`; Pandoc can render it without errors (smoke: `pandoc related_work.md -o /tmp/check.html --bibliography references.bib` exits 0 — informational only, not required).
- Outline file lists each paragraph's evidence ids (both branches).

