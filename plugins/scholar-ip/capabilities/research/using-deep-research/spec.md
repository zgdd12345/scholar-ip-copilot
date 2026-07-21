---
id: using-deep-research
title: Using workflow:research.deep
kind: skill
phase: shared
description: >
  Orient users in the resumable deep-research workflow, its fast and full modes,
  adaptive delegation, optional inputs, and evidence-boundary degradation behavior.
triggers:
  - "workflow:research.deep"
  - "deep literature review"
  - "PRISMA-style review"
  - "comprehensive literature review"
provides:
  - deep-research-modes
  - resume-protocol
  - output-artefact-map
  - degradation-contract
allowed_tools: [Read, Glob, Grep, Write, Edit]
references:
  - doc: capability:deep-literature-review
  - doc: capability:scholar-search
  - doc: workflow:research.deep
---

# Using deep research

`workflow:research.deep` can start from an explicit topic in any safe workspace. A paper
project, scope file, evidence store, and existing BibTeX are useful optional inputs, not
prerequisites. Scope is advisory: use it when present and record its absence as context.

## Modes and stages

The default is `mode=fast`:

1. Frame -> `plan.yaml`
2. Retrieve -> `candidates.jsonl`
3. Screen -> `screening_log.csv`
4. Cluster -> `clusters.yaml`, `evidence_map.json`
5. Critique -> `critique/` only in explicit `mode=full`
6. Synthesise -> `related_work.draft.md`, optional `citation_audit.json`

Mode fast skips Stage 5 critique entirely and does not dispatch `paper-critic`. Mode full
requires critique for the papers selected for full review before synthesis. Both modes
preserve stage artefacts so `resume_from` can continue a partial run.

## Inputs and budget

- `topic` falls back to project metadata only when omitted.
- `breadth` and `depth` are ceilings for retrieval fan-out, not required worker counts.
- Existing stage artefacts may be reused only when their recorded input summary matches.
- Dispatch according to task independence, with no fixed cardinality, waves, or retry
  count. Stop delegating when another check would not materially improve the result.

## Degradation

Network failure falls back to readable local PDFs and BibTeX. Missing local material,
full text, evidence store, or optional audit is recorded in an evidence-boundary section
and in `plan.yaml.notes`; never invent metadata or unseen paper content.

A missing or failed citation audit does not discard a useful draft. Preserve unresolved
claims as findings, label the run `complete_with_gaps`, and give a concrete recovery
action. Use `blocked` only when workspace safety prevents every useful output or no topic
can be resolved from the request or project state.

## Resume and reporting

On `resume_from=<stage>`, validate only the artefacts required before that stage for the
selected mode. A fast run does not require `critique/` to resume synthesis. Report the
run id, mode, stages completed or skipped, retrieval boundary, audit counts when
available, output paths, and one status from `complete | complete_with_gaps | blocked`.
