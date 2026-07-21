---
id: paper-explanation
title: Evidence-grounded single-paper explanation
kind: skill
phase: shared
description: >
  Read one identified paper at beginner, graduate, or reviewer depth using a
  bounded validated graph and produce one evidence-labelled note.
triggers:
  - "workflow:research.explain"
  - "explain this paper"
  - "close-read this paper"
  - "explain the equations in this paper"
provides:
  - paper-source-resolution
  - three-mode-explanation
  - bounded-worker-graph
  - mandatory-related-method-attempts
allowed_tools: [Read, Glob, Grep, Write, Edit, WebSearch, WebFetch]
policies: [workspace-safety, evidence-integrity]
references:
  - doc: capability:scholar-search
---

# paper-explanation

## Source and mode contract

Accept a local PDF path, arXiv identifier or URL, DOI, or paper URL. Resolve one
unique source identity and check readable full text. The coordinator must map public `mode` to internal
`explanation_mode` without changing `beginner`, `graduate`, or `reviewer`; default to
`graduate`. Mode changes emphasis only and never disables external research:

- `beginner` emphasizes terminology, intuition, prerequisites, and analogies;
- `graduate` balances equations, method mechanics, experiments, and reproduction;
- `reviewer` emphasizes claim boundaries, validity, missing controls, and overclaiming.

If full text is unavailable, write a limited evidence-boundary note from verified
identity and readable canonical material. Do not infer unseen methods, equations,
figures, tables, or results. The result is a `status: partial`
identity/evidence-boundary note; do not invent analysis.

## Validated runtime bundle

Load `task-graph.yaml`, `paper-map.schema.json`, and `analysis-packet.schema.json`.
The scheduler is `max_parallel: 15`, `max_attempts: 2`, nested delegation forbidden,
and canonical result order by `task_id`. Effective concurrency is exactly
`min(host_capacity, 15, ready_task_count)`.

The graph has five ordered runtime roles:

1. `paper-indexer` returns the immutable PaperMap.
2. `paper-analysis-worker` returns bounded paper or external AnalysisPackets.
3. `paper-reasoning-worker` returns equation or claim-boundary AnalysisPackets.
4. `explanation-evidence-auditor` returns advisory reviewer findings.
5. `paper-explainer` is the sole final-note writer.

Profiles are `I0 -> [B1, B2, B3] -> S0` for beginner,
`I0 -> [E1, L1, M1, R1, R2, X1] -> S0` for graduate, and
`I0 -> [C1, E1, L1, M1, R1, R2, X1] -> A1 -> S0` for reviewer.
The auditor runs in reviewer mode only.

Every profile always attempts external research. B3 covers both `similar-methods`
and `current-methods`; R1 covers `similar-methods`; R2 covers `current-methods`.
External workers record queries, providers, cutoff, every canonical source opened,
rejected candidates, and failure reason. Search-result snippets are discovery only.
For external work, verify a canonical page before inclusion and record title, year,
link, relationship, concrete methodological difference, search date, and search scope.

## Invocation and return contracts

Indexer input contains exactly `task_id`, `attempt`, `explanation_mode`,
`source_identity`, `full_text_ref`, and graph-declared `budget`. It returns one value
validated against `paper-map.schema.json`.

Worker input contains exactly `task_id`, `attempt`, graph-declared `task_scope`,
`explanation_mode`, immutable PaperMap, `full_text_ref`, immutable
`dependency_packets`, and graph-declared `budget`. It returns one value validated
against `analysis-packet.schema.json`.

Workers never receive `out`, a resolved output path, collision state, write tools, or
mutable state. Claude and OpenCode project four mode-specific read-only agents. Codex
attaches the complete private mode contract because it does not expose per-agent
allowed_tools; that limitation does not disable independent workers.

Every returned packet is checked with
`evidraft paper-explanation validate-return --bundle <paper-explanation-bundle> --task-id <task-id> --attempt <attempt>`
using the exact JSON on stdin, without a temporary project file.

## Retry and degradation contract

A timeout, execution failure, or schema-invalid return records an attempt reason.
After attempt one, dispatch a fresh worker with identical immutable input, scope,
dependencies, and budget except `attempt: 2`. After the second failure, return a
failed packet and preserve both attempt reasons; never invent fallback prose.

S0 still runs after terminal failures. Apply this decision table exactly:

| Condition | Final behavior |
|---|---|
| Every selected task returns a valid complete packet | Write one note with `status: complete`. |
| Any selected task fails, is unavailable, or has incomplete external coverage | Write one note with `status: partial`, named gaps, failed task IDs, and both attempt reasons. |
| I0 cannot map readable full text | Write a limited `status: partial` identity/evidence-boundary note locally; do not invent analysis. |
| Auditor reports any finding or fails | Preserve warnings/recovery guidance and continue synthesis; audit alone does not change complete to partial when all analysis packets are valid. |
| Workspace, sensitive-path, unsafe-symlink, overwrite, or output-write safety fails | Return `status: error` and do not write. |

Auditor findings use severity `info`, `warning`, or `error`. They are correction
guidance and never include a blocking control flag. The contract is explicit: auditor findings cannot suppress
synthesis. Scope and evidence-integrity are advisory. Workspace confinement,
sensitive paths, unsafe symlink checks, overwrite authority, output-write safety, and
external publication authority remain hard.

## Sole-writer and collision contract

Only `paper-explainer` receives the collision-safe resolved output path, validated
values in canonical task order, retry history, failed IDs, optional advisory audit,
and calculated status. It does not map, analyze, retrieve, repair, retry, or delegate.

Never overwrite a non-empty note silently. Offer reuse, a unique dated sibling, or
explicitly confirmed replacement. These choices map to `reuse`, `augment`, and
`overwrite`; overwrite requires explicit confirmation. Re-check the path immediately before S0.
If it became non-empty, repeat collision handling and output preparation. Write at
most one note.

## Required note schema

Every note contains these headings, with unavailable coverage named explicitly:

1. Paper identity and one-sentence takeaway
2. Research problem and background
3. Core contributions
4. Method walkthrough
5. Key equations and symbol-by-symbol explanations
6. Experimental setup and results
7. Limitations, failure modes, and conclusion boundaries
8. Reproduction notes
9. Similar methods
10. Subsequent improvements and latest related methods
11. Learning-check questions
12. Sources and verification record

Use paper locators, external citation/code labels, `[Interpretation]`, and
`[abstract-only]` accurately. Define every symbol in each explained equation. Present
external evidence alongside, never as a replacement for, the authors' conclusion.

## Completion checklist

- Confirm the source identity and readable-full-text boundary.
- Confirm every graph task became terminal within two attempts.
- Confirm both external scopes were attempted and search metadata is complete.
- Confirm advisory audit findings did not suppress synthesis.
- Confirm the status is `complete`, `partial`, or hard-safety `error` by the table.
- Confirm a partial note records named gaps, failed IDs, and both attempt reasons.
- Confirm all workspace, sensitive-path, symlink, overwrite, output, and publication safety.
