# Verdict matrix (Pursue / Refine / Kill)

Apply *after* the question schema and the Carlini test are complete. The verdict is a function of internal consistency, not enthusiasm.

| Verdict | Condition |
|---|---|
| `pursue` | One-sentence contribution is concrete; ≥ 1 contrasted prior reference per novelty claim; an evaluation / disclosure plan exists; no unresolved hard constraint blocks the timeline; riskiest assumption is identified and the fallback is acceptable. |
| `refine` | The contribution is real but at least one of: prior-work contrast is missing, evaluation plan is hand-waved, claim type is undecided, disclosure status is unclear. Another `/scholar:brainstorming` round is needed before downstream work. |
| `kill` | The contribution collapses under the Carlini test (no concrete output, no contrast, or a hard constraint makes the project infeasible). The scope file is still written so the decision is traceable. |

A `pursue` verdict is **not** automatic in fast mode — it is the default assumption, but if the three fast-mode answers fail any condition above, the verdict flips to `refine` or `kill`.
