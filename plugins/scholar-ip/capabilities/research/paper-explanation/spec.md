---
id: paper-explanation
title: Evidence-grounded single-paper explanation
kind: skill
phase: shared
description: >
  Read one paper at full-text level, explain it at beginner, graduate, or
  reviewer depth, and produce a durable academic note with mandatory verified
  similar, subsequent, and newest-found related methods.
triggers:
  - "workflow:research.explain"
  - "explain this paper"
  - "close-read this paper"
  - "explain the equations in this paper"
provides:
  - paper-source-resolution
  - three-mode-explanation
  - evidence-labelled-note-schema
  - mandatory-related-method-landscape
allowed_tools: [Read, Glob, Grep, Write, Edit, WebSearch, WebFetch]
policies: [workspace-safety]
references:
  - doc: capability:scholar-search
---

# paper-explanation

## Source resolution

1. Accept a local PDF path, arXiv URL or identifier, DOI, or paper URL.
2. Resolve one unique source paper before analysis. If the source cannot be
   uniquely identified, stop and request a more precise identifier.
3. Verify title, authors, year, venue, canonical URL, and the paper's research
   problem against the source or a canonical record.
4. Obtain readable full text and map its sections, equations, figures, and
   tables. A source-paper abstract alone cannot satisfy this requirement.

## Mode contract

All modes produce the same required sections and external research. They vary
only in emphasis:

- `beginner`: prioritises terminology, intuition, prerequisites, and careful
  analogies; equations remain present but are explained conceptually.
- `graduate`: balances equation-level explanation, method mechanics,
  experiments, limitations, and reproduction guidance.
- `reviewer`: prioritises assumptions, novelty boundaries, experimental
  validity, missing controls, statistical support, and overclaiming risk.

Use `graduate` when no mode is supplied. Do not drop a required note section or
mandatory external research for any mode.

## Adaptive runtime bundle

The coordinator loads `task-graph.yaml`, `paper-map.schema.json`, and
`analysis-packet.schema.json` from this capability bundle before dispatch. The closed
scheduler contract is `max_parallel: 4`, `max_attempts: 2`, nested delegation
forbidden, and lexical `task_id` dispatch and result order.

The action projects five ordered runtime modes:

1. `paper-indexer` returns the immutable PaperMap.
2. `paper-analysis-worker` returns bounded method, experiment, limitation, or external
   AnalysisPackets.
3. `paper-reasoning-worker` returns equation or claim-boundary AnalysisPackets.
4. `explanation-evidence-auditor` returns the reviewer audit AnalysisPacket.
5. `paper-explainer` synthesizes validated values and is the sole final-note writer.

The approved profile allocations are:

- `beginner`: `I0 -> [B1, B2, B3] -> S0`;
- `graduate`: `I0 -> [E1, L1, M1, R1, R2, X1] -> S0`; and
- `reviewer`: `I0 -> [C1, E1, L1, M1, R1, R2, X1] -> A1 -> S0`.

Brackets denote a dependency-ready wave dispatched in lexical task-ID order with
effective concurrency `min(host capacity, 4)`, not a merged worker invocation.

## Invocation and return contracts

`IndexerInput` contains exactly `task_id`, `attempt`, `mode`, `source_identity`,
`full_text_ref`, and the graph-declared `budget`. It never contains a PaperMap,
dependency packets, output path, or collision state. `I0` returns one value that
validates against `paper-map.schema.json`.

`WorkerInput` contains exactly `task_id`, `attempt`, graph-declared `task_scope`,
`mode`, immutable validated `paper_map`, `full_text_ref`, immutable validated
`dependency_packets`, and graph-declared `budget`. Workers cannot delegate and never
receive `out`, a resolved output path, collision state, Write/Edit ownership, or
mutable state. Each analysis, reasoning, or audit worker returns exactly one value that
validates against `analysis-packet.schema.json`.

Only `paper-explainer` receives the collision-safe resolved output path. Its bounded
input is the selected mode, output ownership, validated PaperMap, validated packets in
canonical task-ID order, retry history and failed IDs, optional validated audit, and
calculated status. It performs no source mapping, specialist analysis, retrieval,
packet repair, retry, or nested delegation and writes at most one note.

## Retry and terminal status

A timeout, execution failure, or schema-invalid return records one attempt reason. A
second attempt uses a fresh subagent with identical immutable input, scope, and budget
except for `attempt: 2`. A second failure becomes a terminal failed packet; both attempt
reasons remain in recovery metadata.

| Status | Deterministic condition |
|---|---|
| `complete` | Every enabled task completed and any reviewer audit has no blocking finding. |
| `partial` | Every mandatory task completed, but at least one optional analysis task failed or remained partial. |
| `incomplete` | Delegation is unavailable, a mandatory task is not complete, a required audit failed, or synthesis violated evidence or output contracts. |

`complete` requires A1 `status: complete` and `blocking: false` in reviewer mode.
`partial` requires A1 `status: complete` and `blocking: false` in reviewer mode.
`blocking: true` on A1 always produces `incomplete`.

Any non-complete mandatory result is `incomplete`, including a mandatory packet with
status partial. If I0 fails after attempt two, dispatch no analysis task, `A1`, or
`S0`; stop and write no note. A mandatory external-task failure may produce only a
prominently marked incomplete source-analysis draft. Every partial or incomplete note
records a banner, failed task IDs, both attempt reasons, missing sections, and recovery
actions.

If the host cannot create independent subagents, report `incomplete: delegation
unavailable` and stop. The coordinator must not run a monolithic fallback, merge task
scopes, or relax the schemas.

## Required note schema

Every completed note contains these sections:

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

For every explained key equation, define each symbol and label any derivation
or analogy that is not stated by the authors.

## Evidence labels

Technical statements use explicit evidence labels:

- `[Paper section 3.2]`, `[Equation 4]`, `[Figure 2]`, or `[Table 1]` for
  source-paper evidence;
- `[External: citation]` for a verified related paper;
- `[External: official-code]` for an official repository or project page;
- `[Interpretation]` for the explainer's derivation, analogy, or assessment;
- `[abstract-only]` when only a verified abstract was available.

An abstract-only external source may support bibliographic facts and claims
stated in its abstract. It must not support claims about unobserved equations,
experiments, implementation details, figures, or tables. Interpretations must
not be presented as author claims.

## Mandatory external research

External research cannot be disabled. It searches for:

- cited or contemporary methods similar to the source paper;
- work that directly extends, improves, applies, or criticises the source;
- the newest verified related methods found as of the execution date; and
- official code, project pages, and author material when available.

The external landscape must contain, when enough verified candidates exist:

- three to five similar or contemporary methods; and
- three to five subsequent, improved, or latest related methods.

Fewer entries are acceptable only when the note records the queries, providers,
cutoff date, and rejection reasons showing that the target count could not be
met without weakening verification.

Each included external work records title, year, canonical link, relationship
to the source paper, and a concrete methodological difference.

Preferred sources are the paper full text, DOI or publisher records, arXiv,
official project pages, and official repositories. Search results are candidate
discovery only; a canonical page must be opened and checked before inclusion.
The note records the search cutoff date and scope and uses wording such as
"newest verified methods found in this search," not an unqualified "latest" or
"state of the art."

## Collision protocol

An existing non-empty output file is never overwritten silently. The action
offers:

- `reuse`: keep the existing note and stop;
- `augment`: write a dated sibling note containing a refreshed external
  landscape while preserving the original; or
- `overwrite`: replace the file only after explicit user confirmation.

`augment` is the default recommendation when the user asks for newer related
methods. If the derived sibling path exists, append a numeric suffix until it
is unique.

## Failure contract

- If the source paper cannot be uniquely identified, stop and request a more
  precise identifier.
- If readable full text is unavailable, do not produce a completed explanation
  from the abstract. Report recovery options instead.
- If a PDF lacks a usable text layer or equation extraction is materially
  broken, request a readable copy. An OCR-derived draft is allowed only when
  clearly marked incomplete and must not satisfy the action's done criteria.
- If mandatory external retrieval is unavailable, preserve any explicitly
  marked temporary work but report the action as incomplete.
- Reject an external candidate whose title and authorship cannot be verified
  against a canonical source.
- Never fabricate a section, equation, figure, table, paper, author, date,
  venue, DOI, result, or URL.

## Completion checklist

- Confirm the source identity and readable full text are verified.
- Confirm all twelve required note headings are present.
- Confirm technical statements carry the correct evidence labels.
- Confirm every explained key equation defines its symbols.
- Confirm three to five verified similar methods and three to five verified
  subsequent, improved, or newest-found methods are included, or evidence the
  shortfall with queries, providers, cutoff date, and rejection reasons.
- Confirm every included external work has a title, year, canonical link,
  relationship, and concrete methodological difference.
- Confirm the search cutoff date and scope are recorded without an absolute
  state-of-the-art claim.
- Confirm collision handling preserved every non-empty existing note unless
  overwrite was explicitly approved.
- Report incomplete when readable source full text or mandatory external
  retrieval is unavailable.
