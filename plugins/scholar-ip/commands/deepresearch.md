---
id: deepresearch
title: "Deep literature research (6-stage pipeline)"
kind: command
slash: /scholar:deepresearch
phase: paper
description: >
  Heavyweight 6-stage literature workflow (Frame → Retrieve → Screen →
  Cluster → Critique → Synthesise) with PRISMA-style screening log and a
  mandatory final citation-audit pass. Multi-provider retrieval (arxiv /
  semantic-scholar / openalex). breadth/depth knobs bound the budget;
  resume_from skips earlier stages. Procedure detail in
  skills/deep-literature-review/SKILL.md.
inputs:
  - name: topic
    type: string
    optional: true
    description: "Free-text research focus. Falls back to project.yaml.topic when omitted."
  - name: breadth
    type: integer
    optional: true
    default: 6
    description: "Maximum sub-queries per fan-out at every stage."
  - name: depth
    type: integer
    optional: true
    default: 2
    description: "Recursion depth for follow-up queries (citations / references)."
  - name: providers
    type: list
    optional: true
    default: [arxiv, semantic-scholar, openalex]
    description: "Ordered retrieval backends consumed by skills/scholar-search/SKILL.md. Records `source` per row; never blends silently."
  - name: mode
    type: enum
    values: [fast, full]
    optional: true
    default: full
    description: "`fast` halves breadth+depth and skips per-paper SWOT; `full` runs all 6 stages."
  - name: resume_from
    type: enum
    values: [frame, retrieve, screen, cluster, critique, synthesise]
    optional: true
    description: "Skip all earlier stages and resume at the named stage."
outputs:
  - path: .evidraft/literature/plan.yaml
  - path: .evidraft/literature/candidates.jsonl
  - path: .evidraft/literature/screening_log.csv
  - path: .evidraft/literature/clusters.yaml
  - path: .evidraft/literature/evidence_map.json
  - path: .evidraft/literature/critique/
  - path: .evidraft/literature/related_work.draft.md
  - path: .evidraft/literature/citation_audit.json
allowed_tools: [Read, Glob, Grep, Write, Edit, WebSearch, WebFetch, "Bash:cat*", "Bash:ls*"]
hooks: [scope-required, citation-guard, evidence-consistency]
subagents: [deep-research-orchestrator, screener, paper-critic, literature-reviewer, evidence-auditor]
references:
  - doc: ../skills/deep-literature-review/SKILL.md
  - doc: ../skills/literature-review/SKILL.md
  - doc: ../skills/scholar-search/SKILL.md
  - doc: ../skills/bib-manager/SKILL.md
  - doc: ../skills/evidence-check/SKILL.md
---

# /scholar:deepresearch

Heavyweight 6-stage literature workflow: **Frame → Retrieve → Screen → Cluster → Critique → Synthesise**. Complements `/scholar:paper-lit` (which stays the light single-pass command); does **not** replace it. Every stage emits a durable artefact under `.evidraft/literature/` so partial runs are resumable via `resume_from`.

All retrieval flows through the `scholar-search` skill (`../skills/scholar-search/SKILL.md`), which drives host-native `WebSearch` + `WebFetch` against arXiv / Semantic Scholar / OpenAlex. When the host has no network, every stage degrades to local PDFs + BibTeX — see `../skills/deep-literature-review/references/failure-modes.md`.

The orchestration is owned by `deep-research-orchestrator`; this command is the executable contract. **Procedure detail lives in `../skills/deep-literature-review/SKILL.md`** which links out to one file per stage under `references/`.

## Stage map

| # | Stage | Artefact | Procedure |
|---|---|---|---|
| 1 | Frame | `plan.yaml` | [stage-1-frame](../skills/deep-literature-review/references/stage-1-frame.md) |
| 2 | Retrieve | `candidates.jsonl` | [stage-2-retrieve](../skills/deep-literature-review/references/stage-2-retrieve.md) |
| 3 | Screen | `screening_log.csv` | [stage-3-screen](../skills/deep-literature-review/references/stage-3-screen.md) |
| 4 | Cluster | `clusters.yaml`, `evidence_map.json` | [stage-4-cluster](../skills/deep-literature-review/references/stage-4-cluster.md) |
| 5 | Critique | `critique/<id>.md` | [stage-5-critique](../skills/deep-literature-review/references/stage-5-critique.md) |
| 6 | Synthesise | `related_work.draft.md`, `citation_audit.json` | [stage-6-synthesise](../skills/deep-literature-review/references/stage-6-synthesise.md) |

Budget knobs (`breadth`, `depth`, `mode`): see [breadth-depth-budget](../skills/deep-literature-review/references/breadth-depth-budget.md).
Resume protocol (`resume_from=<stage>`): see [resume-protocol](../skills/deep-literature-review/references/resume-protocol.md).
PRISMA flow + final chat output: see [prisma-recipe](../skills/deep-literature-review/references/prisma-recipe.md).
Failure / degradation catalog: see [failure-modes](../skills/deep-literature-review/references/failure-modes.md).

## Constraints

- Never invent a paper, author, year, venue, DOI, or section number.
- Never blend two providers' metadata into one `candidates.jsonl` row; record one `source` and stash variants under `aliases`.
- `breadth` / `depth` are the only fan-out knobs the user controls. Do not silently exceed them.
- Strong-claim verbs in `related_work.draft.md` need a `\cite{}` or `ev_NNNN` within 30 chars (`citation-guard`).
- The synthesis stage never proceeds past a failed citation audit.

## Done criteria

- All 6 artefacts under `.evidraft/literature/` exist for the current `run_id`.
- `citation_audit.json` reports `failed=0`.
- PRISMA summary printed to chat (format in [prisma-recipe](../skills/deep-literature-review/references/prisma-recipe.md)).
- Chat output recommends `/scholar:paper-review` next (to render the draft into LaTeX) or `/scholar:paper-idea` (to feed the novelty matrix).
