# Paper Explanation Multi-Subagent Design

**Date:** 2026-07-13
**Status:** Approved for implementation planning
**Extends:** `2026-07-13-paper-explanation-design.md`
**Public action:** `workflow:research.explain`

## Purpose

Refactor single-paper explanation from two coarse work streams into an explicit,
mode-adaptive task graph executed by independent subagents. Each analysis task
has one bounded objective, immutable inputs, a strict structured return value,
and an independent retry boundary. One synthesizer remains the sole writer of
the final academic reading note.

This design supersedes the base design's two-stream processing flow, internal
role allocation, failure aggregation, and related tests. It does not change the
public command, accepted sources, explanation modes, required note sections,
evidence labels, mandatory external research, collision behavior, or output
path.

## Problem Statement

The current implementation declares only two roles:

- `paper-explainer` owns source mapping, method analysis, equation explanation,
  experiment analysis, limitation analysis, and final synthesis.
- `literature-reviewer` owns similar methods, subsequent work, newest-found
  methods, and official project material.

Those boundaries are too broad. A failure in equation interpretation cannot be
retried independently from method analysis. Similar-method search can interfere
with frontier search. Experiment and limitation analysis share one context even
though they consume different evidence. The stage says work may run in parallel
but does not define a machine-readable task graph, dependency waves, concurrency
limit, task-specific return contract, or deterministic partial-failure rule.

## Design Principles

- Parent orchestration owns identity, output collision, scheduling, retry, and
  final status; it does not perform specialist analysis.
- Every subagent invocation receives one closed task scope and may not expand it.
- All workers are read-only and return structured values in conversation; they
  never receive the output path or collision state.
- Workers may not dispatch nested subagents.
- Task completion order never changes deterministic synthesis order.
- One fresh subagent performs the single allowed retry for a failed task.
- `paper-explainer` is the sole synthesizer and sole final-note writer.
- Unsupported delegation is an explicit incomplete outcome, not a silent
  fallback to one monolithic parent agent.

## Public Contract

The command remains:

```text
workflow:research.explain <source> [--mode beginner|graduate|reviewer] [--out PATH]
```

Codex continues to expose it as:

```text
$scholar-research explain <source> --mode graduate
```

The default output remains:

```text
.evidraft/notes/paper-explanations/<paper-slug>.md
```

## Runtime Resources

The paper-explanation capability becomes a bundle with machine-readable
orchestration resources:

```text
plugins/scholar-ip/capabilities/research/paper-explanation/
|- spec.md
|- task-graph.yaml
|- paper-map.schema.json
`- analysis-packet.schema.json
```

`spec.md` explains the workflow and human-readable contracts.
`task-graph.yaml` is authoritative for tasks, dependencies, role modes,
mandatory status, attempts, concurrency, and mode profiles.
`paper-map.schema.json` validates the indexer's immutable source map.
`analysis-packet.schema.json` validates every later worker return before the
packet enters retry, audit, or synthesis.

## Roles

### Parent Workflow Coordinator

The research router and stage remain the coordinator. They:

1. resolve and verify source identity;
2. obtain readable full text;
3. resolve mode, output path, and collision choice;
4. run deterministic output preparation;
5. load and validate `task-graph.yaml`;
6. schedule ready tasks in deterministic order;
7. validate packets and retry failed tasks once;
8. calculate `complete`, `partial`, or `incomplete`; and
9. dispatch the synthesizer with validated packets and final status.

The coordinator never performs a specialist task to conceal a failed worker.

### `paper-indexer` - Researcher, Standard

Consumes verified full text and canonical metadata. Returns an immutable
`PaperMap` containing:

- source identity and full-text reference;
- ordered sections and source locators;
- equations and defined symbols;
- figures and tables;
- datasets, baselines, metrics, ablations, and result locations;
- author claims, assumptions, limitations, and conclusion locations; and
- implementation and reproduction references.

It writes no file. All downstream analysis depends on its successful packet.

### `paper-analysis-worker` - Researcher, Standard

Executes standard task scopes:

- `M1`: problem, contributions, assumptions, and method flow;
- `X1`: experiments, results, ablations, and reproduction;
- `L1`: limitations, failure modes, and conclusion boundaries;
- `R1`: verified similar and contemporary methods; and
- `R2`: verified subsequent, improved, critical, or newest-found methods.

For beginner mode it may receive one of three declared combined scopes. A
combined scope is still closed and appears explicitly in `task-graph.yaml`.
External scopes use canonical-source verification and preserve query,
provider, cutoff, rejection, and abstract-only information.

### `paper-reasoning-worker` - Researcher, Deep

Executes reasoning-heavy scopes:

- `E1`: equation interpretation, symbol definitions, derivation boundaries,
  and intuitive explanation; and
- `C1`: claim boundaries, novelty limits, missing controls, statistical
  support, and overclaiming risk.

It distinguishes source statements from `[Interpretation]` and never invents a
derivation that the paper does not support.

### `explanation-evidence-auditor` - Evidence Reviewer, Standard

Runs only in reviewer mode after all first-wave packets reach a terminal state.
It checks:

- claim-to-evidence locator resolution;
- conflicting numbers or conclusions across packets;
- unsupported strong claims;
- abstract-only scope violations;
- missing canonical links for external work; and
- required task or section coverage.

It returns findings and severity but writes no file.

### `paper-explainer` - Researcher, Deep

The existing native mode is narrowed to synthesis. It receives:

- the final collision-safe output path;
- selected explanation mode;
- verified `PaperMap`;
- validated packets in canonical task order;
- retry history and failed task identifiers;
- reviewer audit packet when applicable; and
- calculated final status.

It resolves conflicts, applies the requested communication style, writes the
single twelve-section note, and reports the final status. No other role receives
the output path.

## Task Graph

### Global Scheduler Settings

```yaml
format_version: 1
scheduler:
  max_parallel: 4
  max_attempts: 2
  nested_delegation: forbidden
  result_order: task_id
```

The effective concurrency is the smaller of host capacity and `max_parallel`.
Ready tasks are queued in lexical `task_id` order. Attempt two uses a fresh
subagent with the exact same `WorkerInput`, task scope, and budget as attempt
one.

### Wave 0 - Required Foundation

| Task | Mode | Mandatory | Depends on | Output |
|---|---|---:|---|---|
| `I0` | `paper-indexer` | yes | none | `PaperMap` packet |

If `I0` fails after two attempts, no analytical task or final note is produced.
The action reports `incomplete` with recovery instructions.

### Beginner Profile

| Task | Worker | Scope | Mandatory | Depends on |
|---|---|---|---:|---|
| `B1` | analysis | `M1` plus intuitive `E1` | no | `I0` |
| `B2` | analysis | `X1` plus `L1` | no | `I0` |
| `B3` | analysis | `R1` plus `R2` | yes | `I0` |
| `S0` | synthesizer | final note | yes | `B1`, `B2`, `B3` terminal |

Beginner mode uses five subagent invocations on the no-retry path: indexer,
three analysis workers, and synthesizer. It preserves all twelve note sections
but lowers analysis granularity and emphasizes intuition.

### Graduate Profile

| Task | Worker | Scope | Mandatory | Depends on |
|---|---|---|---:|---|
| `M1` | analysis | method | no | `I0` |
| `E1` | reasoning | equations | no | `I0` |
| `X1` | analysis | experiments | no | `I0` |
| `L1` | analysis | limitations | no | `I0` |
| `R1` | analysis | similar methods | yes | `I0` |
| `R2` | analysis | frontier methods | yes | `I0` |
| `S0` | synthesizer | final note | yes | all six terminal |

Graduate mode uses eight subagent invocations on the no-retry path. The six
analysis tasks have no dependency on one another and are scheduled in bounded
batches.

### Reviewer Profile

Reviewer mode runs the six graduate tasks plus:

| Task | Worker | Scope | Mandatory | Depends on |
|---|---|---|---:|---|
| `C1` | reasoning | claim boundaries | no | `I0` |
| `A1` | evidence auditor | cross-packet audit | yes | `M1`, `E1`, `X1`, `L1`, `R1`, `R2`, `C1` terminal |
| `S0` | synthesizer | final note | yes | `A1` terminal |

Reviewer mode uses ten subagent invocations on the no-retry path.

## Immutable Input Contracts

### `IndexerInput`

The indexer receives only:

```yaml
task_id: I0
attempt: 1
explanation_mode: graduate
source_identity: <verified canonical metadata>
full_text_ref: <verified local or fetched full-text reference>
budget:
  max_sections: 100
```

It cannot receive `PaperMap`, dependency packets, an output path, or collision
state. Its return must validate against `paper-map.schema.json`; invalid maps
consume an attempt exactly like invalid analysis packets.

### `WorkerInput`

Every post-index analysis or audit worker receives:

```yaml
task_id: M1
attempt: 1
task_scope: [method]
explanation_mode: graduate
paper_map: <immutable PaperMap value>
full_text_ref: <verified local or fetched full-text reference>
dependency_packets: []
budget:
  max_sources: 0
  max_findings: 12
```

External tasks receive a non-zero `max_sources`. Inputs never contain `out`, a
resolved output path, collision state, or another worker's mutable state.

`dependency_packets` contains immutable validated packets only when the task
graph declares dependencies. It is empty for every first-wave analysis task and
contains the seven terminal first-wave packets for reviewer audit `A1`.

The public action maps `mode` to `explanation_mode`; role-mode selection remains
the graph task's separate `mode` field. `task_id`, `task_scope`, and `budget` must exactly match the selected task-graph
entry. A worker may not broaden a query, read unrelated project material, or
delegate further.

## Structured Return Contract

Every post-index analysis or audit worker returns one `AnalysisPacket`:

```json
{
  "task_id": "M1",
  "attempt": 1,
  "status": "complete",
  "findings": [
    {
      "claim": "The method replaces recurrence with self-attention.",
      "evidence_refs": ["Paper section 3.2"],
      "confidence": "high",
      "label": "paper"
    }
  ],
  "uncertainties": [],
  "rejections": [],
  "retry_reason": null
}
```

The JSON Schema uses `additionalProperties: false`. Required top-level fields
are:

- `task_id`;
- `attempt`;
- `status`, one of `complete`, `partial`, or `failed`;
- `findings`;
- `uncertainties`;
- `rejections`; and
- `retry_reason`, which is required to be non-empty when status is `failed`.

Each finding requires a claim, at least one evidence reference for factual
claims, confidence, and evidence label. Invalid packets are treated as failed
attempts rather than repaired by the coordinator.

## Retry and Failure Semantics

1. A failed execution, timeout, or invalid packet records the error and consumes
   the current attempt.
2. If `attempt < max_attempts`, dispatch a fresh subagent with identical input
   except for the incremented attempt number.
3. Attempt two may not expand task scope, source budget, or finding budget.
4. A second failure emits a terminal failed packet.

Final status is deterministic:

- `complete`: every enabled task is complete and reviewer audit has no blocking
  finding.
- `partial`: `I0`, all enabled external tasks, and any required audit completed,
  but at least one non-mandatory analysis task failed or remained partial.
- `incomplete`: delegation is unavailable; an enabled mandatory external task
  failed; a required audit failed; or synthesis could not satisfy evidence and
  output contracts.

Any mandatory task whose terminal status is not `complete` produces
`incomplete`, including a mandatory task that returns `partial`.

An `incomplete` external-research outcome may still write a source-analysis
draft with a prominent incomplete banner. An `I0` failure produces no note
because no grounded source map exists. Partial or incomplete outputs list failed
task IDs, both attempt reasons, missing sections, and recovery actions.

## Conflict Resolution

The synthesizer applies these rules in order:

1. For conflicting numeric results, re-check source table, figure, or text
   locators. If unresolved, retain both values and label the conflict.
2. When external evidence challenges an author conclusion, retain both with
   distinct evidence labels; do not rewrite the author's claim as consensus.
3. A factual finding without evidence references cannot become a factual note
   claim. It moves to uncertainties or is excluded.
4. An audit finding about an unsupported strong claim causes wording downgrade,
   explicit `[Interpretation]`, or exclusion.
5. Packet order is canonical task order, never completion order.

## Host Execution Contract

Claude Code, Codex, and OpenCode render the same task graph, schemas, role modes,
and stage instructions.

- Claude Code and OpenCode render and dispatch four mode-specific worker agents
  with hard tool frontmatter matching the selected private mode.
- Codex uses its available collaboration/subagent facility and loads the same
  private mode for every task. Its current plugin surface has no per-agent
  `allowed_tools`, so this is explicit contract enforcement rather than a hard
  tool sandbox; this limitation alone is not delegation unavailability.
- The coordinator must not claim `complete` when the host cannot create
  independent subagents. It reports `incomplete: delegation unavailable`.
- Workers never dispatch child subagents.
- Host-specific concurrency below four is allowed; host-specific task omission,
  scope merging beyond the selected profile, or schema relaxation is forbidden.

## Changes to Existing Components

- `workflow:research.explain` replaces the two-role stage with the declared
  task-graph scheduler.
- The action declares the indexer, standard analysis worker, deep reasoning
  worker, evidence auditor, and synthesizer modes.
- `literature-reviewer` is removed from this native action and remains unchanged
  for reading-list and paper workflows.
- `paper-explainer` is narrowed from broad analysis to synthesis.
- The paper-explanation capability digest is refreshed after adding bundle
  resources.
- Renderer validation counts and native mode expectations expand without
  modifying frozen v1 role bodies or their hashes.

## Test Strategy

Implementation follows strict Red-Green-Refactor. Focused tests are observed
failing for missing task-graph behavior before production specifications change.

### Task Graph and Schema

- Parse and validate `task-graph.yaml` as a closed contract.
- Validate complete and malformed PaperMap fixtures against
  `paper-map.schema.json`.
- Assert exact mode profiles, task IDs, dependencies, mandatory flags, worker
  modes, `max_parallel: 4`, `max_attempts: 2`, and forbidden nesting.
- Validate complete, partial, failed, malformed, missing-field, and extra-field
  AnalysisPacket fixtures.
- Reject cycles, unknown dependencies, undeclared role modes, or a synthesizer
  that is not the sole writer.

### Workflow Semantics

- Assert beginner has three analysis dispatches and covers all twelve sections.
- Assert graduate has six mutually independent analysis tasks.
- Assert reviewer audit depends on every first-wave packet and synthesis depends
  on the audit.
- Assert workers never receive output or collision fields.
- Assert the retry input is identical except for attempt number.
- Assert required task failure, optional task failure, delegation absence, and
  successful completion map to the correct final status.
- Assert partial and incomplete notes carry the required banner and recovery
  metadata.

### Roles and Rendering

- Register every new native mode at one valid tier and resolve its private spec.
- Preserve all 15 frozen v1 mode hashes.
- Render identical task graph and schemas for Claude Code, Codex, and OpenCode.
- Assert rendered roles have the minimum tools their scopes require and no
  forbidden tools.
- Assert only `paper-explainer` receives output ownership.
- Assert all host routers explicitly refuse monolithic fallback when delegation
  is unavailable.

### Verification

Run focused tests, the complete test suite, Ruff, all three renderers, Codex
plugin validation, Claude plugin validation when available, final diff review,
and a sensitive-data scan.

## Acceptance Criteria

- Every successful single-paper run executes the selected profile through
  independent subagent invocations.
- Beginner, graduate, and reviewer use exactly the approved task allocations.
- No analysis worker receives or writes the final output path.
- Every returned packet validates or consumes a failed attempt.
- No task exceeds two attempts or broadens scope on retry.
- External search remains mandatory and split into similar and frontier tasks
  except for the approved beginner combined landscape task.
- Partial and incomplete outcomes are explicit and recoverable.
- The synthesizer is the only writer and produces the unchanged twelve-section
  note contract.
- All supported hosts consume the same machine-readable task graph and schemas.
- The public command, output path, frozen migration fixture, and frozen legacy
  role behavior remain stable.
