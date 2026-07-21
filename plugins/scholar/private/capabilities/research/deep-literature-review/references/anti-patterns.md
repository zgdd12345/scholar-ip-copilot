# Anti-patterns

- Running `workflow:research.deep` when `workflow:paper.lit` would suffice. The deep command is for survey-grade reviews; light projects pay a real cost in time and tokens.
- Blending metadata from two providers into one `candidates.jsonl` row.
- Re-scoring screened candidates after seeing later ones.
- Writing a SWOT bullet that paraphrases the abstract.
- Skipping `Delta vs our angle` for "obviously different" papers.
- Marking a run done while `citation_audit.failed > 0`.
- Editing `manuscript/sections/related_work.tex` directly — that file is owned by `workflow:paper.review`, which consumes `related_work.draft.md` as its outline.
- Silently exceeding the `breadth * 50` candidate ceiling instead of refusing and logging — see [breadth-depth-budget.md](breadth-depth-budget.md).
- Inventing a section / figure / table / equation reference in a SWOT bullet because the PDF was unavailable — use `[abstract-only]` instead. See [failure-modes.md](failure-modes.md).
