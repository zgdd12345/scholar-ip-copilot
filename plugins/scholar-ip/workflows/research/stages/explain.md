# workflow:research.explain

Load the private [paper-explanation](../../../capabilities/research/paper-explanation/spec.md)
and [scholar-search](../../../capabilities/research/scholar-search/spec.md) specs before
starting. They define the source, evidence, external-retrieval, collision, and failure
contracts for this stage.

## Phase 1: Resolve source and output

1. Classify `source` as a local PDF path, arXiv identifier or URL, DOI, or paper URL.
   Resolve exactly one paper and verify its title, authors, year, venue, canonical URL,
   and research problem against the source or a canonical record. Stop and request a
   more precise identifier when the identity is ambiguous.
2. Obtain readable full text and verify that its sections, equations, figures, and
   tables can be inspected. An abstract alone is not full text. If a PDF has no usable
   text layer or materially broken equation extraction, request a readable copy; any
   explicitly requested OCR draft remains incomplete.
3. Select `mode`, defaulting to `graduate`. Derive `<paper-slug>` from the verified title
   as deterministic ASCII: transliterate when possible, lowercase, replace each run of
   non-alphanumeric characters with one hyphen, trim hyphens, and fall back to a verified
   paper identifier if the title yields no characters. Resolve `out` or the default
   `.evidraft/notes/paper-explanations/<paper-slug>.md` to a concrete relative path.
4. If that path is a non-empty existing note, resolve one choice before writing:
   `reuse` keeps it and stops; `augment` preserves it and selects a unique dated sibling
   (adding a numeric suffix on collision); `overwrite` requires explicit user
   confirmation. Recommend `augment` for refreshed related-work requests.
5. Run `evidraft workflow prepare-output research.explain --target <resolved-output>`
   with the final concrete collision-safe path. Never pass an unresolved placeholder.
   This deterministic command applies workspace preflight to that one target and creates
   only its confined parent directory; it does not create the output file or
   `.evidraft/project.yaml`. Complete it before the final write.

## Phase 2: Load and validate the task graph

1. Load `task-graph.yaml`, `paper-map.schema.json`, and
   `analysis-packet.schema.json` from the private paper-explanation capability bundle.
   Require `max_parallel: 4`, `max_attempts: 2`, forbidden nested delegation, and
   canonical result order by task ID. Stop if any resource or graph reference is
   missing or invalid; do not improvise a replacement graph or packet shape.
2. Select exactly one graph profile from `mode`:
   - `beginner`: `I0`, then the ready wave `B1`, `B2`, `B3`, then `S0`;
   - `graduate`: `I0`, then the ready wave `E1`, `L1`, `M1`, `R1`, `R2`, `X1`,
     then `S0`; or
   - `reviewer`: `I0`, then the ready wave `C1`, `E1`, `L1`, `M1`, `R1`, `R2`,
     `X1`, then `A1`, then `S0`.
3. Before dispatch, confirm that the host can create independent subagents. If
   delegation is unavailable, report `incomplete: delegation unavailable` and stop.
   The coordinator must not run a monolithic fallback or merge worker scopes into one
   invocation.

## Phase 3: Dispatch adaptive dependency waves

Dispatch `I0` first and validate its returned PaperMap. If I0 fails after attempt two,
stop without dispatching any analysis task, A1, or S0 and write no note. Otherwise,
dispatch each selected profile's dependency-ready tasks in lexical `task_id` order with
effective concurrency `min(host capacity, 4)`. Wait for every dependency to become
terminal before opening the next wave. In `reviewer` mode, dispatch `A1` only after
`C1`, `E1`, `L1`, `M1`, `R1`, `R2`, and `X1` are terminal. Dispatch `S0` only after
terminal status and its bounded synthesis input have been calculated. Workers cannot
delegate further.

### IndexerInput contract

Dispatch `I0` with exactly `task_id`, `attempt`, `mode`, `source_identity`,
`full_text_ref`, and its graph-declared `budget`. It receives neither a PaperMap nor
dependency packets. Its return must validate against `paper-map.schema.json` and must
map the readable full text's section structure, research question, prerequisites,
contributions, assumptions, method steps, key equations and symbols, figures, tables,
datasets, baselines, metrics, ablations, results, limitations, conclusion boundaries,
implementation details, and reproduction gaps to precise source-paper locations.

### WorkerInput contract

Dispatch every analysis, reasoning, or audit task with exactly `task_id`, `attempt`,
graph-declared `task_scope`, `mode`, the immutable validated PaperMap, `full_text_ref`,
immutable validated `dependency_packets`, and the graph-declared `budget`. First-wave
dependency packets are empty; `A1` receives the seven terminal first-wave packets.
Every return must validate against `analysis-packet.schema.json`.

The workers never receive `out`, a resolved output path, collision state, output-file
ownership, or another worker's mutable state. Only `paper-explainer` receives the
resolved output path. External tasks use the bounded scholar-search contract, open a
canonical source for each candidate, verify title and authorship, and retain queries,
providers, cutoff date, rejection reasons, and abstract-only evidence scope. Workers
never receive collision state and never create or modify the final note.

### Retry contract

For every timeout, execution failure, or schema-invalid PaperMap or AnalysisPacket,
record the attempt reason. When attempt one fails, dispatch attempt two to a fresh
subagent with identical immutable input, scope, and budget except `attempt`, which is
set to `2`. Never
repair an invalid packet, broaden scope, or increase a source or finding budget. After
a second failure, record a terminal failed packet and preserve both attempt reasons for
status calculation and recovery reporting.

## Phase 4: Calculate terminal status and synthesize

Calculate the pre-synthesis status deterministically from terminal graph results:

- `complete`: every enabled pre-synthesis task is complete and any reviewer audit has
  no blocking finding.
- `partial`: every mandatory task is complete, including enabled external tasks and any
  required audit, but at least one optional analysis task failed or remained partial.
- `incomplete`: delegation is unavailable, any mandatory task is not complete, a
  required audit failed, or synthesis cannot satisfy the evidence or output contract.
  A mandatory task that returns partial is incomplete, not partial.

`complete` requires A1 `status: complete` and `blocking: false` in reviewer mode.
`partial` requires A1 `status: complete` and `blocking: false` in reviewer mode.
`blocking: true` on A1 always produces `incomplete`.

An `I0` terminal failure writes no note. A mandatory external-research failure may
continue only to a prominently marked incomplete source-analysis draft. Every partial
or incomplete note includes a status banner, failed task IDs, both attempt reasons,
missing sections, and recovery actions.

Pass to `S0` only the selected mode, resolved output ownership, validated PaperMap,
validated packets in canonical task-ID order, failure history and failed IDs, optional
validated audit packet, and the calculated status. Exclude raw invalid packets and
completion-order state. Only `paper-explainer` may write the final note; neither worker
may race on or create a competing final file. The `paper-explainer`
writes exactly one Markdown note at the resolved output path using all twelve headings
below, in this order:

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

Use all applicable evidence labels exactly: `[Paper section 3.2]`, `[Equation 4]`,
`[Figure 2]`, and `[Table 1]` for source-paper evidence; `[External: citation]` for a
verified related paper; `[External: official-code]` for an official repository or
project page; `[Interpretation]` for a derivation, analogy, or assessment; and
`[abstract-only]` when only a verified external abstract was available. Define every
symbol in each explained key equation. Never use abstract-only evidence for unobserved
equations, experiments, implementation details, figures, or tables.

Include three to five verified similar or contemporary methods and three to five
verified subsequent, improved, or newest-found related methods when enough candidates
exist. For every included work record title, year, canonical link, relationship to the
source, and a concrete methodological difference. If either target cannot be met,
preserve the shortfall rather than weakening verification. Section 12 records all
queries, providers, search scope, execution-date cutoff, included counts, rejected
count, and each rejection reason. Describe results as the "newest verified methods found
in this search", never as an absolute latest method or state of the art.

Apply the selected-mode emphasis without removing any heading or external research:

- `beginner`: emphasize terminology, intuition, prerequisites, and careful analogies;
  retain equations and explain them conceptually.
- `graduate`: balance equation-level reasoning, method mechanics, experiments,
  limitations, and reproduction guidance.
- `reviewer`: emphasize assumptions, novelty boundaries, experimental validity,
  missing controls, statistical support, and overclaiming risk.

For conflicting numeric results, re-check the referenced table, figure, or text and
retain every unresolved value with an explicit conflict label. Present external
evidence alongside, never as a replacement for, the authors' conclusion. Exclude a
factual finding without evidence references or mark it uncertain. When `A1` flags an
unsupported strong claim, downgrade it, label it `[Interpretation]`, or exclude it.

## Phase 5: Validate and report

Validate the source identity, readable-full-text status, twelve headings, evidence
labels, equation symbol definitions, related-work verification and target counts,
search metadata, collision decision, retry history, and calculated status. A synthesis
contract failure changes the final status to `incomplete`. Report the concrete output
path when one was written, selected mode, full-text status, search cutoff,
similar-method included count, subsequent/improved/newest-found included count,
rejected count, failed task IDs, and final status. If source full text or mandatory
external retrieval failed, report the action as incomplete and provide recovery
options; do not claim a completed explanation even if temporary work exists.

## Constraints

- Produce one Markdown output only. Do not modify BibTeX, evidence records, manuscript
  files, project status, or a non-empty existing note without confirmed overwrite.
- Never fabricate paper identity, metadata, section labels, equations, figures, tables,
  results, external works, authors, dates, venues, DOIs, code, or URLs.
- Do not present `[Interpretation]` as an author claim or discovery-only search results
  as verified evidence.
- Mandatory external research cannot be disabled, and its cutoff cannot be omitted.
- Keep dispatch bounded to the selected validated task-graph profile. Preserve sole
  final-file ownership with `paper-explainer`; no worker can write an intermediate file.

## Done criteria

- Source identity and readable full text are verified.
- The collision-safe concrete output passed preflight and exactly one note was written.
- All twelve headings, applicable evidence labels, and symbol-by-symbol key-equation
  explanations are present with the selected-mode emphasis.
- Three to five verified similar methods and three to five verified subsequent,
  improved, or newest-found methods are included, or the evidenced shortfall records
  queries, providers, cutoff, and rejection reasons.
- Every included external work has a title, year, canonical link, relationship, and
  concrete methodological difference.
- The final report states path when written, mode, full-text status, cutoff, both
  included counts, rejected count, failed IDs, and an accurate `complete`, `partial`,
  or `incomplete` status.
