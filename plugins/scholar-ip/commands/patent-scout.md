---
id: patent-scout
title: "Discover patentable candidates in the codebase and docs"
kind: command
slash: /scholar:patent-scout
phase: patent
outputs:
  - path: .evidraft/patent/invention_candidates.md
  - path: .evidraft/evidence/evidence.jsonl   # appended
allowed_tools: [Read, Glob, Grep, Write, Edit]
hooks: [scope-required, evidence-consistency, sensitive-file-guard]
subagents: [codebase-analyst, patent-engineer, novelty-critic]
references:
  - doc: ../skills/patent-disclosure/SKILL.md
  - doc: ../skills/codebase-audit/SKILL.md
---

# /scholar:patent-scout

Read the code and docs to surface **candidate** inventions. Output is a structured list; nothing in this command makes a legal judgement.

## Steps

1. **Repo scan.** Walk top-level modules and `README*`, `DESIGN*`, `RFC*`, `MODEL_CARD*`. Identify non-obvious technical mechanisms: novel algorithms, optimisations, data structures, system architectures, training schemes, pipelines, hardware/software co-designs.
2. **Cluster candidates.** Group related code into one candidate where appropriate. Drop trivial or library-level wrappers.
3. **Write `.evidraft/patent/invention_candidates.md`.** One H2 section per candidate, with:
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
- Respect `sensitive-file-guard`.
- If the code includes obvious third-party copies (e.g. vendored library), flag and exclude.
- Provide **at least** `file_path` (line range when possible) for every candidate.

## Done criteria

- `invention_candidates.md` has ≥ 1 candidate.
- Each candidate has code evidence and an inventor-input checklist.
- Chat output recommends `/scholar:patent-prior-art` next.
