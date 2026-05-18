---
id: evidence-consistency
title: "Evidence consistency"
kind: hook
phase: shared
triggers:
  - "write:manuscript/sections/*.tex"
  - "write:manuscript/main.tex"
  - "write:.evidraft/patent/invention_disclosure.md"
  - "write:.evidraft/patent/claims.md"
  - "write:.evidraft/patent/claim_chart.md"
  - "write:.evidraft/code/paper_code_audit.md"
behaviour: "Every literature claim traces to evidence.jsonl; every number to experiments/; every code claim carries file_path + line_range."
failure_mode: block
references:
  - doc: ../../../docs/data-model.md
  - doc: ../../../docs/legal-and-ethics.md
  - doc: ../skills/evidence-check/SKILL.md
---

# evidence-consistency

## When it fires

Any write or edit that lands in:

- the manuscript tree (`manuscript/sections/*.tex`, `manuscript/main.tex`),
- the patent disclosure or claim tree (`.evidraft/patent/invention_disclosure.md`, `claims.md`, `claim_chart.md`),
- the code-audit document (`.evidraft/code/paper_code_audit.md`).

The hook scans the diff and classifies each new factual span into one of three buckets.

## Rules

1. **Literature claims** — any sentence that names a method / dataset / result not produced in this project. Must trace to `evidence.jsonl` via either a `\cite{key}` (where `key` also tags a `type=paper` row) or an inline `ev_NNNN` marker. A bare author–year string (`Smith et al., 2021`) without a corresponding BibTeX entry counts as missing.
2. **Numeric claims** — any digit-bearing token in scientific context (`81.3 mAP`, `+2.4 pts`, `n=128`, `p < 0.05`). Must trace to `.evidraft/experiments/result_analysis.md` (or an `ev_NNNN` row of `type=experiment`) with a resolvable `file_path` and `row/col` or `line_range`. Round numbers in prose ("about ten times faster") still require the underlying source.
3. **Code claims** — any sentence that describes what the project's code does ("we implement X via a custom CUDA kernel"). Must include or reference a `file_path` and a `line_range`, either inline or via a `type=code` evidence row.

A claim that does not fit any of the three buckets (e.g. a definitional sentence, a problem statement) is not flagged.

## Failure mode

`block` by default — the write is rejected with:

```
evidence-consistency: BLOCKED
  file: <path>
  line: <n>
  span: "<offending text>"
  category: literature | numeric | code
  reason: no evidence row resolves this claim
  suggestion: add ev_NNNN or \cite{key}; or remove the claim
```

Downgradable in `.evidraft/project.yaml` per category:

```yaml
hooks:
  evidence_consistency: enabled    # block
rules:
  require_citation_for_claims: true
  require_experiment_source_for_numbers: true
  require_code_trace_for_code_claims: true
```

Toggling any sub-rule to `false` flips that category from `block` to `warn`; the violation is logged in `paper_check_report.md`.

## Adapter notes

- **Claude Code** — register as a `PreToolUse` hook on `Write` / `Edit` for the listed paths. The hook reads `.evidraft/evidence/evidence.jsonl` and `references.bib` once per invocation, then validates the diff.
- **Codex CLI** — inline as a prompt-level rule in every `/paper-*` and `/patent-*` command, plus the evidence-check skill. Codex prompts must explicitly call `evidence-auditor` before declaring done.
- **OpenCode** — planned; the rule will hook into the host's diff-apply event.
