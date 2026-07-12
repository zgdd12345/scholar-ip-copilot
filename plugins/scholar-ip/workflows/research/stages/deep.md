# workflow:research.deep

Heavyweight 6-stage literature workflow: **Frame → Retrieve → Screen → Cluster → Critique → Synthesise**. Complements `workflow:paper.lit` (which stays the light single-pass command); does **not** replace it. Every stage emits a durable artefact under `.evidraft/literature/` so partial runs are resumable via `resume_from`.

All retrieval flows through the `scholar-search` skill (`../../../capabilities/research/scholar-search/spec.md`), which drives host-native `WebSearch` + `WebFetch` against arXiv / Semantic Scholar / OpenAlex. When the host has no network, every stage degrades to local PDFs + BibTeX — see `../../../capabilities/research/deep-literature-review/references/failure-modes.md`.

The orchestration is owned by `deep-research-orchestrator`; this command is the executable contract. **Procedure detail lives in `../../../capabilities/research/deep-literature-review/spec.md`** which links out to one file per stage under `references/`.

## Stage map

| # | Stage | Artefact | Procedure |
|---|---|---|---|
| 1 | Frame | `plan.yaml` | [stage-1-frame](../../../capabilities/research/deep-literature-review/references/stage-1-frame.md) |
| 2 | Retrieve | `candidates.jsonl` | [stage-2-retrieve](../../../capabilities/research/deep-literature-review/references/stage-2-retrieve.md) |
| 3 | Screen | `screening_log.csv` | [stage-3-screen](../../../capabilities/research/deep-literature-review/references/stage-3-screen.md) |
| 4 | Cluster | `clusters.yaml`, `evidence_map.json` | [stage-4-cluster](../../../capabilities/research/deep-literature-review/references/stage-4-cluster.md) |
| 5 | Critique | `critique/<id>.md` | [stage-5-critique](../../../capabilities/research/deep-literature-review/references/stage-5-critique.md) |
| 6 | Synthesise | `related_work.draft.md`, `citation_audit.json` | [stage-6-synthesise](../../../capabilities/research/deep-literature-review/references/stage-6-synthesise.md) |

Budget knobs (`breadth`, `depth`, `mode`): see [breadth-depth-budget](../../../capabilities/research/deep-literature-review/references/breadth-depth-budget.md).
Resume protocol (`resume_from=<stage>`): see [resume-protocol](../../../capabilities/research/deep-literature-review/references/resume-protocol.md).
PRISMA flow + final chat output: see [prisma-recipe](../../../capabilities/research/deep-literature-review/references/prisma-recipe.md).
Failure / degradation catalog: see [failure-modes](../../../capabilities/research/deep-literature-review/references/failure-modes.md).

## Constraints

- Never invent a paper, author, year, venue, DOI, or section number.
- Never blend two providers' metadata into one `candidates.jsonl` row; record one `source` and stash variants under `aliases`.
- `breadth` / `depth` are the only fan-out knobs the user controls. Do not silently exceed them.
- Strong-claim verbs in `related_work.draft.md` need a `\cite{}` or `ev_NNNN` within 30 chars (`policy:evidence-integrity`).
- The synthesis stage never proceeds past a failed citation audit.

## Done criteria

- All 6 artefacts under `.evidraft/literature/` exist for the current `run_id`.
- `citation_audit.json` reports `failed=0`.
- PRISMA summary printed to chat (format in [prisma-recipe](../../../capabilities/research/deep-literature-review/references/prisma-recipe.md)).
- Chat output recommends `workflow:paper.review` next (to render the draft into LaTeX) or `workflow:paper.idea` (to feed the novelty matrix).
