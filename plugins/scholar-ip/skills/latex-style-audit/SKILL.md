---
id: latex-style-audit
title: "LaTeX style audit: caption / ref / math / microtypography rules over a clean-compiling manuscript"
kind: skill
phase: paper
description: >
  Runs after `latex-build` reports a clean compile. Sweeps the manuscript
  for style violations a human reviewer would mark — caption punctuation,
  `\eqref` vs `\ref`, booktabs hygiene, bare-URL usage, dash consistency,
  footnote placement, and more. Emits a structured findings JSON for the
  orchestrator and a human-readable log; never auto-fixes prose.
triggers:
  - "command:/scholar:paper-check"
  - "command:/scholar:paper-venue"
  - "subagent:latex-editor"
  - "auditing manuscript style"
  - "running style audit after clean compile"
provides:
  - latex-style-rule-set
  - latex-style-findings-schema
  - latex-style-regex-recipes
  - latex-style-severity-policy
  - latex-style-human-report
allowed_tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - "Bash:grep*"
  - "Bash:awk*"
hooks: [latex-compile]
references:
  - doc: ../latex-build/SKILL.md
  - doc: ../latex-writing/SKILL.md
  - doc: ../venue-formatting/SKILL.md
  - doc: ../scholar-search/SKILL.md
  - doc: ../../hooks/citation-guard.md
  - doc: ../../hooks/latex-compile.md
  - doc: ../../agents/latex-editor.md
  - doc: ../../commands/paper-check.md
  - doc: references/rule-taxonomy.md
  - doc: references/output-schemas.md
  - doc: references/procedure.md
  - doc: references/anti-patterns.md
---

# latex-style-audit

## When to use

Runs as a sub-pass of `/scholar:paper-check` **after** `latex-build` reports a clean (or merely warning-level) compile. The skill is observational: it never edits `.tex`.

Also fires implicitly when the `latex-editor` subagent stages a manuscript revision — it lets the agent see the same style backlog a reviewer would, before the agent applies fixes on a separate pass.

Skip the run if `compile` from the preceding `latex-build` invocation is `FAIL` (style findings on a non-building manuscript would be noise) — exception: `/scholar:paper-venue` may still run the audit on the canonical `manuscript/` while the venue copy fails, because the upstream prose is what the venue pass will copy.

## Shared cache + run_id convention

Style artefacts live alongside `latex-build` artefacts under `.evidraft/manuscript/`:

- `.evidraft/manuscript/style_audit-<ts>.log` — human-readable, one row per finding.
- `.evidraft/manuscript/style_audit-<ts>.findings.json` — structured rows for the orchestrator.

`<ts>` is UTC iso-basic (`20260518T143000Z`), matching `compile-<ts>` so the two files pair up trivially. When called from a command with a `run_id` in its `plan.yaml`, record the `run_id` as the top-level `run_id` field inside `style_audit-<ts>.findings.json`. The literature retrieval cache (`.evidraft/literature/.cache/`) is **not** touched.

## Inputs

- `manuscript/main.tex` and `manuscript/sections/*.tex` (canonical tree), **or** `submissions/<venue>/main.tex` + `submissions/<venue>/sections/*.tex` (venue tree, when the caller passes a `--root submissions/<venue>/` flag).
- `.evidraft/manuscript/compile-<ts>.log` — most recent compile log, to know which symbols / files are in scope. Optional: if missing, scan everything `\input`-reachable from `main.tex`.
- `.evidraft/manuscript/compile-<ts>.errors.json` — optional; used only to skip the audit when `compile == "FAIL"` (see When to use).

## How to navigate this skill

Load only the reference you need.

| Concern | Reference | Owns |
|---|---|---|
| What to look for | [rule-taxonomy.md](references/rule-taxonomy.md) | 28 rules in 7 groups (captions, cross-references, math, tables&figures, bib proximity, microtypography, common misuses); severity policy; per-rule patterns + examples + suggested fixes + known false-positive notes; citation-guard echo recipe |
| What to write | [output-schemas.md](references/output-schemas.md) | `style_audit-<ts>.log` row format; `style_audit-<ts>.findings.json` schema; severity-totals semantics |
| How to run | [procedure.md](references/procedure.md) | 6 steps — enumerate, universal pre-filter (with line-offset preservation), run rules, aggregate, emit, surface |
| What to avoid | [anti-patterns.md](references/anti-patterns.md) | the 8 anti-patterns (auto-rewrite, comment false-positives, re-implementing citation-guard, rule inflation, severity creep, skipping empty findings.json, running on FAIL compile, verbatim hacks) |

## Quality checklist

- [ ] Every finding carries a `rule_id` from [rule-taxonomy.md](references/rule-taxonomy.md) (UPPER_SNAKE, stable across runs).
- [ ] Severities follow the policy: `fail` only when the issue makes the paper objectively wrong (`INCLUDEGRAPHICS_PATH`, `EQ_LABEL_PREFIX`, `DUPLICATE_LABEL`, `PERCENT_UNESCAPED`, `STRONG_CLAIM_VERB_NO_CITE`); `warn` for reviewer-visible style violations; `info` for matters of taste.
- [ ] Universal pre-filter applied — no comment / verbatim / lstlisting false positives.
- [ ] Reported `line` matches the original source line (pre-filter preserves offsets).
- [ ] No `.tex` file edited. The skill writes only under `.evidraft/manuscript/`.
- [ ] `findings.json` emitted even when zero findings (empty `findings`, zero `summary` — part of the audit trail).
- [ ] Rules whose precondition is absent are silently skipped (not reported as "0 findings").
- [ ] When `compile == "FAIL"` from the preceding `latex-build`, the skill skips the run (with one chat line explaining why) unless the caller is `/scholar:paper-venue`.
