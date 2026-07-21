# workflow:research.explain

Load the private [paper-explanation](../../.evidraft-private/capabilities/research/paper-explanation/spec.md)
contract and execute its validated graph. The coordinator must map public `mode` to internal
`explanation_mode` without changing `beginner`, `graduate`, or `reviewer`.
For external tasks, load the private
[scholar-search](../../.evidraft-private/capabilities/research/scholar-search/spec.md) contract.

## Phase 1: Resolve source and output

1. Accept one local PDF path, arXiv identifier or URL, DOI, or paper URL. For a local PDF,
   run `evidraft workflow preflight research.explain --read-target <source>`
   before reading it. Do not pass a DOI, arXiv identifier or URL, or paper URL as
   a local read target.
2. Resolve one unique source identity and verify title, authors, year, venue, and
   canonical URL. Try to obtain readable full text without inventing unavailable
   sections, equations, figures, tables, or results.
3. Resolve `out` or `.evidraft/notes/paper-explanations/<paper-slug>.md`. Never
   overwrite a non-empty note silently. Offer `reuse`, `augment`, or `overwrite`;
   replacement requires explicit confirmation and `augment` uses a unique dated sibling.
4. Run `evidraft workflow prepare-output research.explain --target <resolved-output>`
   only after the concrete collision-safe path is known. Workspace confinement,
   sensitive paths, unsafe symlinks, overwrite authority, and external publication
   authority are hard safety boundaries. For the explicitly confirmed `overwrite`
   decision, run `evidraft workflow prepare-output research.explain --target
   <resolved-output> --approve-overwrite` instead.

## Phase 2: Load and validate the task graph

1. Load `task-graph.yaml`, `paper-map.schema.json`, and
   `analysis-packet.schema.json` from the private paper-explanation bundle. Require
   `max_parallel: 15`, `max_attempts: 2`, forbidden nested delegation, and canonical
   result order by task ID. Do not improvise a graph or packet shape.
2. Select exactly one graph profile:
   - `beginner`: `I0 -> [B1, B2, B3] -> S0`;
   - `graduate`: `I0 -> [E1, L1, M1, R1, R2, X1] -> S0`;
   - `reviewer`: `I0 -> [C1, E1, L1, M1, R1, R2, X1] -> A1 -> S0`.
3. Every profile schedules external research. `B3` always attempts both
   `similar-methods` and `current-methods`; `R1` always attempts `similar-methods`
   and `R2` always attempts `current-methods`.
4. The four worker modes are `paper-indexer`, `paper-analysis-worker`,
   `paper-reasoning-worker`, and `explanation-evidence-auditor`.
   `paper-explainer` is the sole final-note writer.

## Phase 3: Dispatch bounded dependency waves

Claude and OpenCode dispatch each I0, analysis, reasoning, and audit task through
the mode-specific agent whose identifier exactly matches the task graph. Codex does
not expose per-agent allowed_tools in this projection, so attach the complete private
mode spec and enforce it as contract enforcement, not a hard tool sandbox.

Dispatch ready tasks in lexical task-ID order with effective concurrency exactly
`min(host_capacity, 15, ready_task_count)`. Wait for dependencies to become terminal
before opening the next wave. Workers cannot receive the output path, write files, or
dispatch a nested subagent.

### IndexerInput

Dispatch I0 with exactly `task_id`, `attempt`, `explanation_mode`, `source_identity`,
`full_text_ref`, and graph-declared `budget`. Its complete return validates against
`paper-map.schema.json`.

### WorkerInput

Dispatch analysis, reasoning, and audit tasks with exactly `task_id`, `attempt`,
graph-declared `task_scope`, `explanation_mode`, immutable validated PaperMap,
`full_text_ref`, immutable `dependency_packets`, and graph-declared `budget`.
Every return validates against `analysis-packet.schema.json`.

After every I0, analysis, reasoning, or audit return, run
`evidraft paper-explanation validate-return --bundle <paper-explanation-bundle> --task-id <task-id> --attempt <attempt>`
and send the exact returned JSON on stdin. Do not serialize a return through a
temporary project file. A schema-invalid return consumes that attempt.

### Retry contract

Record a reason for every timeout, execution failure, or schema-invalid return.
After attempt one fails, dispatch a fresh worker with identical immutable input,
scope, dependencies, and budget except `attempt: 2`. After attempt two fails,
record a terminal failed packet and preserve both attempt reasons. Never repair a
packet, broaden scope, or invent fallback prose.

## Phase 4: Calculate terminal status and synthesize

S0 still runs after terminal failures. Only `paper-explainer` receives the resolved
output path, validated values in canonical task order, failure history, failed IDs,
optional advisory audit, and calculated status.

| Condition | Final behavior |
|---|---|
| Every selected task returns a valid complete packet | Write one note with `status: complete`. |
| Any selected task fails, is unavailable, or has incomplete external coverage | Write one note with `status: partial`, named gaps, failed task IDs, and both attempt reasons. |
| I0 cannot map readable full text | Write a limited `status: partial` identity/evidence-boundary note locally; do not invent analysis. |
| Auditor reports any finding or fails | Preserve warnings/recovery guidance and continue synthesis; audit alone does not change complete to partial when all analysis packets are valid. |
| Workspace, sensitive-path, unsafe-symlink, overwrite, or output-write safety fails | Return `status: error` and do not write. |

The auditor runs only in reviewer mode. Its findings have severity `info`, `warning`,
or `error`, are correction guidance, and never carry a blocking control flag.
The contract is explicit: auditor findings cannot suppress synthesis. Scope and evidence-integrity are advisory;
workspace confinement, sensitive paths, unsafe symlink checks, overwrite authority,
output-write safety, and external publication authority remain hard.

Immediately before dispatching `S0`, re-check the resolved target. If it became
non-empty, repeat the `reuse`, `augment`, or `overwrite` decision and run
`evidraft workflow prepare-output research.explain --target <resolved-output>` again,
adding `--approve-overwrite` only after explicit confirmation of `overwrite`.
A narrow race remains between this final check and the single write and must be reported.

Render these headings in order, naming unavailable coverage rather than inventing it:

```markdown
## 1. Paper identity and one-sentence takeaway
## 2. Research problem and background
## 3. Core contributions
## 4. Method walkthrough
## 5. Key equations and symbol-by-symbol explanations
## 6. Experimental setup and results
## 7. Limitations, failure modes, and conclusion boundaries
## 8. Reproduction notes
## 9. Similar methods
## 10. Subsequent improvements and latest related methods
## 11. Learning-check questions
## 12. Sources and verification record
```

Use `[Paper section ...]`, `[Equation ...]`, `[Figure ...]`, `[Table ...]`,
`[External: citation]`, `[External: official-code]`, `[Interpretation]`, and
`[abstract-only]` according to the capability contract. Define every equation symbol.

## Phase 5: Validate and report

Validate source identity, full-text boundary, headings, labels, symbols, external
search metadata, collision decision, retry history, failed IDs, and calculated status.
Report output path when written, mode, search cutoff, both external included counts,
rejected count, failed IDs, both attempt reasons, and final `complete`, `partial`, or
`error` status.

## Constraints

- Produce at most one Markdown note and never modify BibTeX, evidence records,
  manuscript files, project status, or a non-empty note without overwrite authority.
- Never fabricate identity, metadata, locators, equations, figures, tables, results,
  external works, authors, dates, venues, DOIs, code, or URLs.
- Always attempt the selected profile's similar/current external research.
- Keep dispatch bounded to the validated task graph and preserve sole file ownership.

## Done criteria

- All selected tasks became terminal within `max_attempts: 2`.
- External scopes record queries, providers, cutoff, opened canonical sources,
  rejected candidates, and failure reasons.
- The note has the twelve headings and accurate evidence boundaries.
- Terminal failures are visible as `status: partial` with failed IDs and both attempt reasons.
- Auditor findings remain advisory and cannot suppress synthesis.
- Hard path, sensitive-file, symlink, overwrite, output-write, and publication safety held.
