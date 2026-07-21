# workflow:patent.scout

Read the code and docs to surface **candidate** inventions. Output is a structured list; nothing in this command makes a legal judgement.

This action is best effort. Scan whatever code and documentation is safely
available, and record missing repository context, line ranges, inventor input, or
retrieval access as explicit gaps. Missing inputs reduce confidence but do not
block a useful candidate inventory. Delegate analysis adaptively based on repository
size and candidate risk, with no fixed worker count, waves, or retry count.

## Steps

1. **Repo scan.** Drive via `../../.evidraft-private/capabilities/code/code-intel/spec.md`. Use the `codebase-analyst` subagent to walk top-level modules and `README*`, `DESIGN*`, `RFC*`, `MODEL_CARD*`. Identify non-obvious technical mechanisms: novel algorithms, optimisations, data structures, system architectures, training schemes, pipelines, hardware/software co-designs. (Optionally cross-check each candidate against public patent databases via `../../.evidraft-private/capabilities/research/patent-search/spec.md` before recording the novelty hypothesis.)
2. **Cluster candidates.** Group related code into one candidate where appropriate. Drop trivial or library-level wrappers.
3. **Write `.evidraft/patent/invention_candidates.md`.** Use the `patent-engineer` subagent to author each candidate block in attorney-readable language, and the `novelty-critic` subagent to challenge each `Novelty hypothesis` before it lands on disk. One H2 section per candidate, with:
   ```
   ## C-001 <short name>
   - Technical problem: ...
   - Proposed solution: ...
   - Code evidence: src/foo/bar.py:120-180 ; evidence_id ev_0123
   - Novelty hypothesis: ...
   - Patentability risk: low/medium/high  (advisory)
   - Required inventor input:
     - [ ] confirm inventors
     - [ ] confirm earliest public disclosure date
     - [ ] confirm any third-party dependencies
   ```
4. **Append evidence.** For each candidate, append one or more `type=code` records to `evidence.jsonl`.

## Constraints

- Do not claim "patentable" — only "candidate". The decision is the attorney's.
- Respect `policy:workspace-safety`.
- If the code includes obvious third-party copies (e.g. vendored library), flag and exclude.
- Provide **at least** `file_path` (line range when possible) for every candidate.

## Done criteria

- `invention_candidates.md` has ≥ 1 candidate.
- Each candidate has code evidence and an inventor-input checklist.
- Chat output recommends `workflow:patent.prior-art` next.
- Status is `complete`, `complete_with_gaps` when candidate support or inventor
  input is missing, or `blocked` only when workspace safety prevents every useful
  output.
