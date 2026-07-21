---
id: deep-literature-review
title: Resumable deep literature review
kind: skill
phase: paper
description: >
  Provide mode-aware Frame, Retrieve, Screen, Cluster, optional Critique, and Synthesise
  procedures with bounded retrieval and explicit evidence boundaries.
triggers:
  - "workflow:research.deep"
  - "resuming a deep research run"
provides:
  - resumable-stage-spec
  - fast-and-full-mode-contract
  - prisma-flow-recipe
  - evidence-boundary-degradation
allowed_tools: [Read, Glob, Grep, Write, Edit]
policies: [evidence-integrity]
references:
  - doc: capability:literature-review
  - doc: capability:scholar-search
  - doc: capability:evidence-check
---

# deep-literature-review

Use this capability for `workflow:research.deep`. The workflow is resumable and
best-effort. Scope is advisory; a topic argument is sufficient to begin. Network,
full-text, evidence-store, and optional-audit gaps are recorded instead of invented.

## Mode-aware stages

| Stage | Artefact | Mode |
|---|---|---|
| Frame | `plan.yaml` | fast, full |
| Retrieve | `candidates.jsonl` | fast, full |
| Screen | `screening_log.csv` | fast, full |
| Cluster | `clusters.yaml`, `evidence_map.json` | fast, full |
| Critique | `critique/<cluster-id>.md` | full only |
| Synthesise | `related_work.draft.md`, optional `citation_audit.json` | fast, full |

Mode fast skips Stage 5 Critique entirely and does not dispatch `paper-critic`. Mode full
requires critique for the selected full-review papers. Stage 6 reads clusters directly
in fast mode and reads both clusters and critique in full mode.

## Adaptive work

Use the coordinator directly when it can complete a bounded task. Delegate only when an
independent screen, critique, synthesis, or audit materially improves the result.
Dispatch according to task independence, with no fixed cardinality, waves, or retry
count. User `breadth` and `depth` limit retrieval work, not worker quantity.

## Evidence boundary

- Verify metadata against a canonical source before presenting it as verified.
- When network access fails, reuse readable local PDFs and BibTeX. If none are available,
  write the planned boundary and recovery action without candidate-shaped guesses.
- Tag abstract-only support and never infer unseen equations, experiments, or sections.
- A missing or failed citation audit preserves the draft, lists unresolved claims, and
  returns `complete_with_gaps`.
- Use `blocked` only when workspace safety prevents every useful write or no topic can be
  resolved.

## Navigation

Load only the relevant reference:

- [Stage 1](references/stage-1-frame.md)
- [Stage 2](references/stage-2-retrieve.md)
- [Stage 3](references/stage-3-screen.md)
- [Stage 4](references/stage-4-cluster.md)
- [Stage 5](references/stage-5-critique.md), full mode only
- [Stage 6](references/stage-6-synthesise.md)
- [Budget](references/breadth-depth-budget.md)
- [Resume](references/resume-protocol.md)
- [Failures](references/failure-modes.md)
- [PRISMA report](references/prisma-recipe.md)

## Completion

Report `complete` when requested coverage and enabled checks succeed,
`complete_with_gaps` when useful artefacts contain named retrieval, full-text, evidence,
or audit boundaries, and `blocked` only under the conditions above. Fast completion does
not require `critique/`; full completion requires the selected critiques.
