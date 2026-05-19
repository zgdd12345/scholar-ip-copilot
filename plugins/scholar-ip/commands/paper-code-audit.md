---
id: paper-code-audit
title: "Audit paper claims against the source code"
description: >
  Audit every paper claim against the source code: produce `repo_summary.md`,
  `method_to_code.md`, and `paper_code_audit.md` with per-claim verdicts
  (CONFIRMED / PARTIAL / MISSING / MISMATCH / NOT_AUDITABLE) and trustworthy
  `file:line` citations. Use when verifying that the manuscript description
  matches the actual implementation, after any method or ablation change,
  or before submission.
kind: command
slash: /scholar:paper-code-audit
phase: paper
inputs:
  - name: claims_source
    type: enum
    values: [novelty_matrix, draft_method, manual_list]
    optional: true
    default: novelty_matrix
outputs:
  - path: .evidraft/code/repo_summary.md
  - path: .evidraft/code/method_to_code.md
  - path: .evidraft/code/paper_code_audit.md
allowed_tools: [Read, Glob, Grep, Write, Edit, "Bash:git*", "Bash:ls*", "Bash:tree-sitter*"]
hooks: [evidence-consistency, sensitive-file-guard]
subagents: [codebase-analyst, methodology-reviewer, evidence-auditor]
references:
  - doc: ../skills/codebase-audit/SKILL.md
  - doc: ../skills/code-intel/SKILL.md
---

# /scholar:paper-code-audit

Verify that each claim about the method or implementation **actually exists in the code**.

## Steps

1. **Repo summary (refresh).** Drive via `skills/code-intel/SKILL.md`. Use the `codebase-analyst` subagent to produce the grounded summary. Update `.evidraft/code/repo_summary.md`:
   - language(s), build/run commands, entry points (CLI, training script, server),
   - directory map (top-level only),
   - configs (e.g. `configs/*.yaml`),
   - test command, CI file paths,
   - any `README*`, `MODEL_CARD*`, `DATASHEET*` files.
2. **Method-to-code mapping.** Drive via `skills/code-intel/SKILL.md` (Grep / Glob defaults; `tree-sitter` when on `$PATH`). Update `.evidraft/code/method_to_code.md`:
   | Method component | Source files | Entry points | Configs | Key functions/classes | Evidence | Gaps |
   - "Method component" is a row per planned section/sub-section of the Method.
   - "Evidence" lists evidence ids of `type=code`; create new ones as needed with `file_path` + `line_range`.
   - "Gaps" describes what is described in the method but missing in code.
3. **Audit table.** Use the `methodology-reviewer` subagent to assign each per-claim verdict; the `evidence-auditor` subagent then verifies the `file:line` citations on every `CONFIRMED` / `PARTIAL` / `MISMATCH` row. Write `.evidraft/code/paper_code_audit.md`:
   | Paper claim | Where in paper | Code evidence (file:lines) | Verdict | Notes |
   - For each row select exactly one **Verdict** ∈ { `CONFIRMED`, `PARTIAL`, `MISSING`, `MISMATCH`, `NOT_AUDITABLE` }.
   - `CONFIRMED`: matches the code at the cited file:line.
   - `PARTIAL`: matches part of the claim (e.g., feature exists but no ablation switch).
   - `MISSING`: claim has no code evidence.
   - `MISMATCH`: code contradicts the claim (e.g., paper says β=0.5, code default β=0.9).
   - `NOT_AUDITABLE`: claim is empirical/theoretical and cannot be checked from code alone.
4. **Append evidence.** Each `CONFIRMED` / `PARTIAL` / `MISMATCH` row appends one record to `evidence.jsonl` (`type=code`, with `file_path` + `line_range`).

## Constraints

- Respect `sensitive-file-guard`: do not open `.env`, `secrets/`, etc.
- Do not modify source code. This is read-only auditing.
- A `Verdict` of `CONFIRMED` requires both `file_path` and a line range; otherwise downgrade to `PARTIAL`.

## Done criteria

- All three artefacts updated.
- Every paper claim has exactly one Verdict.
- Chat output flags counts: `n CONFIRMED, n PARTIAL, n MISSING, n MISMATCH, n NOT_AUDITABLE`.
