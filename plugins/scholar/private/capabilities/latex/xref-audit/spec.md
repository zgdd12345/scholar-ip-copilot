---
id: xref-audit
title: "Cross-reference audit: \\ref / \\eqref / \\cite / \\label graph validation"
kind: skill
phase: paper
description: >
  Static analysis of the LaTeX cross-reference graph. After `latex-build`
  reports a clean (or near-clean) compile, walk `manuscript/main.tex` +
  `sections/*.tex` and validate every `\label{}`, `\ref{}`, `\eqref{}`,
  `\autoref{}`, `\nameref{}`, and `\cite{}` against the resolved graph and
  the bib key set. Detects duplicates, orphans, broken refs, prefix-drift,
  caption/label placement, and float order. Read-only.
triggers:
  - "command:workflow:paper.check"
  - "command:workflow:paper.venue"
  - "subagent:latex-editor"
provides:
  - xref-graph-validation
  - label-hygiene
  - reference-hygiene
  - cite-bib-cross-check
  - float-order-check
  - autoref-consistency
allowed_tools:
  - Read
  - Glob
  - Grep
  - "Bash:grep*"
  - "Bash:awk*"
policies: [evidence-integrity]
references:
  - doc: capability:latex-build
  - doc: capability:latex-style-audit
  - doc: references/rule-taxonomy.md
  - doc: references/output-schemas.md
  - doc: references/procedure.md
  - doc: references/anti-patterns.md
---

# xref-audit

## When to use

Cross-reference auditing **requires a successful (or near-successful) compile** — a missing `\label{}` is already a LaTeX error and `latexmk` will catch it. This skill runs as a **sub-pass** of `workflow:paper.check` between `latex-build` (compile + error taxonomy) and `latex-style-audit` (prose). Its job is to validate the **cross-reference graph**:

- which labels are defined (and where);
- which labels are referenced (and from where);
- which `\cite{}` keys resolve into `references.bib`;
- whether prefix convention (`fig:`, `tab:`, `eq:`, `sec:`, `alg:`) is followed;
- whether labels sit in the right place relative to captions and floats.

It is **static analysis** — it does **not** read `.aux` files (those are compile artefacts and may be stale).

## Inputs

- `manuscript/main.tex` plus everything it `\input{}`s (recursively): `manuscript/sections/*.tex`, `manuscript/preamble.tex`.
- For `workflow:paper.venue`: `submissions/<venue>/main.tex` + sections instead.
- `references.bib` (path resolved via `\bibliography{...}` or `\addbibresource{...}`, or default `.evidraft/literature/references.bib`).
- (Optional, **context only** — never authoritative) `.evidraft/manuscript/compile-<ts>.log` from a recent `latex-build` run.

## Outputs

Two files per run under `.evidraft/manuscript/`:

- `xref_audit-<ts>.log` — one finding per line (human-readable).
- `xref_audit-<ts>.findings.json` — machine, with `labels` / `refs` / `cites` tally blocks and a `findings[]` array.

Full schema in [output-schemas.md](references/output-schemas.md). No edits to `.tex` or `references.bib`.

## How to navigate this skill

Load only the reference you need.

| Concern | Reference | Owns |
|---|---|---|
| What to look for | [rule-taxonomy.md](references/rule-taxonomy.md) | 14 rules in 4 groups (5 label-hygiene, 4 reference-hygiene, 2 counter/float, 3 style); per-rule detection / example / suggested fix / explanation |
| What to write | [output-schemas.md](references/output-schemas.md) | `xref_audit-<ts>.log` row format + `xref_audit-<ts>.findings.json` schema (labels/refs/cites tallies + findings array) |
| How to run | [procedure.md](references/procedure.md) | 9 steps — discover sources, strip non-LaTeX regions (with original-line-number preservation), build label set, build ref set, build cite set + bib resolve, caption/label placement, float order, style passes, emit |
| What to avoid | [anti-patterns.md](references/anti-patterns.md) | the 7 anti-patterns (reading `.aux`, auto-fix, consistency-vs-choice confusion, verbatim false positives, cite-key renaming, re-implementing `latex-build`'s `MISSING_REF` parser) |

## Quality checklist

- [ ] Comments (`% ...`) and verbatim / lstlisting envs excluded from every Grep pass (verified by the `LABEL_INSIDE_VERBATIM` self-test rule).
- [ ] `\input` / `\include` chain followed; cross-file references resolve.
- [ ] Source line numbers in findings refer to the **original** file, not a masked view.
- [ ] `labels.defined + labels.duplicated` ≥ unique label count; sums in the JSON header reconcile with the per-rule findings.
- [ ] `CITE_BROKEN` cross-checked against `references.bib` (not against `.aux`).
- [ ] When called with `run_id`, the value lands at the top level of `findings.json`.
