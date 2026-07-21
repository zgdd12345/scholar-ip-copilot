---
id: using-scholar-ip-copilot
title: Using the scholar (EviDraft) plugin
kind: skill
phase: shared
description: >
  Orient users in the seven public EviDraft workflows and route a concrete request by
  intent without imposing a fixed lifecycle.
triggers:
  - "workflow:using.run"
  - "user asks what EviDraft can do"
  - "user asks which workflow handles a request"
provides:
  - current-workflow-map
  - direct-intent-routing
  - advisory-project-state-orientation
allowed_tools: [Read, Glob, Grep]
policies: []
references:
  - doc: ../../../README.md
  - doc: ../../../docs/architecture.md
  - doc: ../../../plugin.yaml
---

# Using EviDraft

The workflow YAML files are authoritative. EviDraft exposes seven public workflows and
22 actions: `using.run`, `scope.run`, `research.{reading-list,explain,deep}`, nine paper
actions, six patent actions, `polish.run`, and `xreview.run`.

## Route by intent

1. Route unambiguous intent directly to the matching public action and do not ask for
   confirmation. Preserve arguments the user already supplied.
2. Ask one clarifying question only when the request is ambiguous between materially
   different workflows. Route immediately after the answer.
3. Output collision handling belongs to the selected action. An explicit output
   replacement may require confirmation for that concrete path; a default-path collision
   follows the action's automatic sibling rule. Do not add a separate routing confirmation.
4. For a general tour, read current workflow sources and visible project artefacts, then
   name the shortest useful next action without implying that optional stages are gates.

Common routes:

| Intent | Action |
|---|---|
| Explain one identifiable paper | `workflow:research.explain` |
| Personal topic reading list | `workflow:research.reading-list` |
| Broad or systematic literature review | `workflow:research.deep` |
| Clarify goals or contribution boundaries | `workflow:scope.run` |
| Draft or check a paper | matching `workflow:paper.*` action |
| Draft or review patent material | matching `workflow:patent.*` action |
| Preserve-checked prose editing | `workflow:polish.run` |
| External second opinion | `workflow:xreview.run` |

## Advisory project state

Scope is advisory. Missing, draft, or stale scope can be reported as context but cannot
block draft-first work. Existing trustworthy artefacts may be reused when their input
summary matches; missing optional artefacts become named gaps. Only workspace safety can
hard-block ordinary workflow preparation.

Paper and patent actions are independently invocable. Recommend upstream work when it
would materially improve the result, but do not require `paper.init`, approved scope,
evidence, disclosure, or review merely because it appears earlier in a conventional
lifecycle. Patent claims must retain their attorney-review footer, and venue packaging
never submits anything.

## Reporting

- Report only workflow and action names present in current YAML.
- Distinguish visible completed artefacts from recommendations.
- Use `complete`, `complete_with_gaps`, or `blocked` for execution status; paper checks
  and patent reviews additionally report `PASS`, `WARN`, or `FAIL`.
- Do not expose internal policy mechanics in ordinary onboarding text.
