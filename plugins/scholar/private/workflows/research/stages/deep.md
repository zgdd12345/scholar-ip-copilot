# workflow:research.deep

Resumable literature workflow: **Frame → Retrieve → Screen → Cluster → [Critique] →
Synthesise**. Fast mode skips the bracketed critique stage; full mode enables it. Every
stage that runs emits a durable artefact under `.evidraft/literature/`.

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
- Scope is advisory. Missing scope, evidence, network, or an optional audit becomes a
  named gap rather than a generation gate.
- Dispatch according to task independence, with no fixed cardinality, waves, or retry
  count. `mode=fast` skips Stage 5 Critique and does not dispatch `paper-critic`.

## Done criteria

- In every mode, the useful artefacts supported by available input are written and every
  omitted artefact is named in `plan.yaml.notes` and the chat report.
- Fast mode does not require `critique/`; skipping per-paper SWOT is its declared
  lightweight behavior.
- Only `mode=full` requires `critique/` entries for the papers selected for critique.
- A missing or failed citation audit yields `complete_with_gaps` with unresolved claims
  and recovery actions; it does not suppress the draft.
- PRISMA summary printed to chat (format in [prisma-recipe](../../../capabilities/research/deep-literature-review/references/prisma-recipe.md)).
- Chat output recommends `workflow:paper.review` next (to render the draft into LaTeX) or `workflow:paper.idea` (to feed the novelty matrix).
