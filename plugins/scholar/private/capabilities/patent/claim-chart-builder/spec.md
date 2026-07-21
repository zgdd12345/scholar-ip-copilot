---
id: claim-chart-builder
title: "Claim chart builder: (claim, element) x prior-art overlap matrix with spec/code support and risk roll-up"
kind: skill
phase: patent
description: >
  Consumes the structured claim form `claims_parsed.json` (from sibling skill
  `claim-parser`) and `prior_art_map.md`, then emits a populated claim chart
  in both human-readable markdown and structured JSON. Walks every
  (claim, element) pair, attaches spec_support + code_support, scores
  per-element overlap against every prior-art entry, rolls up risk, and
  drafts narrowing `suggested_revision` lines. Advisory only — never edits
  claim text; the chart is reviewer convenience.
triggers:
  - "command:workflow:patent.review"
  - "command:workflow:patent.prior-art"
  - "subagent:patent-engineer"
  - "subagent:claim-drafter"
provides:
  - claim-element-prior-art-chart
  - overlap-scoring
  - risk-assignment
  - suggested-revision-recipe
  - spec-support-resolution
  - code-support-resolution
allowed_tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - "Bash:grep*"
policies: [evidence-integrity]
references:
  - doc: capability:claim-parser
  - doc: capability:novelty-heuristics
  - doc: role-mode:claim-drafter
  - doc: ../../../docs/legal-and-ethics.md
---

# claim-chart-builder

## When to use

Runs whenever `workflow:patent.prior-art` or `workflow:patent.review` has a fresh `.evidraft/patent/claims_parsed.json` (produced by `claim-parser`) **and** a populated `.evidraft/patent/prior_art_map.md`. Replaces the previous "fill the chart by hand" pattern in the `claim-drafter` agent with an automated, structured build that any reviewer can re-run after editing the claims or the prior-art map.

Two callers, two reasons:

- `workflow:patent.prior-art` — first construction, immediately after the prior-art map gets new entries. The chart shows attorneys which elements are exposed.
- `workflow:patent.review` / `patent-engineer` — re-build after the drafter narrowed a high-risk element; confirms the risk dropped and no new gaps opened.

Skip the run if `claims_parsed.json` is missing or `claims` is empty (the chart has no rows to build); print one chat line explaining why and stop. Also skip if `prior_art_map.md` has zero bullet-list entries under any candidate — without prior art there is no overlap to score (still emit an empty chart so the audit trail shows the run happened).

## Inputs

- `.evidraft/patent/claims_parsed.json` — canonical claim form, from `claim-parser`. Shape:
  ```json
  {"run_id":"...","ts":"...",
   "claims":[{"id":"c1","number":1,"kind":"independent","depends_on":null,
              "preamble":"A method comprising:","transition":"comprising",
              "elements":[{"label":"a","text":"...",
                           "antecedents_introduced":[...],
                           "antecedents_referenced":[...]}],
              "terminus":"."}],
   "antecedent_chain":{...},"warnings":[...],"summary":{...}}
  ```
- `.evidraft/patent/prior_art_map.md` — H2 per candidate (`### Patent prior art` and `### Academic prior art` subsections, each a bulleted list of `- US-1234567-B2 (assignee, date) — relevance: <high/med/low>, summary, why-different`).
- (optional) `.evidraft/patent/invention_disclosure.md` — used for the `spec_support` column. If absent, `spec_support` cells stay empty and risk roll-up applies the no-support override.
- (optional) `.evidraft/code/method_to_code.md` — used for the `code_support` column. Same fallback as above when missing.

The skill never reads source code directly; it relies on `method_to_code.md` for the code surface mapping. That keeps the chart deterministic and audit-friendly.

## Outputs

Two files per run under `.evidraft/patent/`:
- `claim_chart.md` — populated human-readable chart.
- `claim_chart-<ts>.json` — structured form for downstream consumption (review subagents, change-impact diffs).

Full JSON schema, field rules, and the `claim_chart.md` table shape live in [references/schemas.md](references/schemas.md).

## Build procedure

The build is a five-stage pipeline. Each stage's detailed contract loads on demand from `references/`:

| Stage | Reference | Owns |
|---|---|---|
| 1 — Setup | [procedure-setup.md](references/procedure-setup.md) | read inputs, mint prior-art ids, map candidates to claims |
| 2 — Walk + support | [procedure-walk-and-support.md](references/procedure-walk-and-support.md) | iterate (claim, element) pairs; spec support pass; code support pass |
| 3 — Overlap | [procedure-overlap.md](references/procedure-overlap.md) | per-(element, prior-art) overlap scoring (none / low / medium / high / identical) |
| 4 — Risk + revise | [procedure-risk-and-revise.md](references/procedure-risk-and-revise.md) | overlap-driven risk + no-support override; narrowing-only `suggested_revision` |
| 5 — Write | [procedure-write.md](references/procedure-write.md) | render `claim_chart.md` + `claim_chart-<ts>.json`; chat summary line |

Anti-patterns: [anti-patterns.md](references/anti-patterns.md).

## Quality checklist

- [ ] Every (claim, element) pair in `claims_parsed.json` appears as exactly one row; row count equals `sum(len(claim.elements) for claim in claims)`.
- [ ] No row is silently dropped because `spec_support` or `code_support` is empty — the row stays, the empty cells show, and the no-support override is applied (`risk = high`).
- [ ] No row carries `overlap_score: identical` without a verbatim quote in `overlap_passage` (the skill self-checks via substring match against the prior-art bullet text).
- [ ] `suggested_revision` populated **iff** `risk ∈ {medium, high}`; never for `risk == low`.
- [ ] `suggested_revision` never widens scope (substring self-check passed).
- [ ] `overlap_score` values strictly within `{none, low, medium, high, identical}`.
- [ ] `risk` values strictly within `{low, medium, high}`.
- [ ] `summary.rows_total == sum(len(c.rows) for c in candidates)`.
- [ ] `summary.rows_high_risk + summary.rows_medium_risk + summary.rows_low_risk == summary.rows_total`.
- [ ] `summary.rows_no_spec_support` counts rows whose `spec_support == []`; `summary.rows_no_code_support` counts rows whose `code_support == []`.
- [ ] Every prior-art passage cited in any `overlap_passage` traces back to a bullet in `prior_art_map.md` (no invented citations).
- [ ] `claim_chart.md` ends with the verbatim "Advisory-only framing" paragraph below.
- [ ] When called with a `run_id`, the value lands at the top level of `claim_chart-<ts>.json`.

## Advisory-only framing

The following paragraph is **mandatory and verbatim** at the end of every emitted `claim_chart.md`:

> The `claim-chart-builder` skill produces a structured claim chart for **reviewer convenience**. Overlap scores reflect a heuristic semantic comparison and are **advisory only** — they help an attorney spot the strongest prior-art hits earlier but are not a substitute for an examiner-grade rejection analysis. A registered patent agent / attorney must review every row before any filing decision; `suggested_revision` cells are starting points, not final claim language.
