---
id: novelty-heuristics
title: "Novelty heuristics: per-element prior-art overlap scoring with advisory verdict hints"
kind: skill
phase: patent
description: >
  Per-claim-element novelty heuristics for the `workflow:patent.review` 5-role
  panel. Walks every (claim, element) x (prior-art-entry) pair, scores
  semantic overlap on a 5-step ladder, and emits a structured findings file
  plus a human log for the `novelty-critic` agent. **Advisory only — not a
  patentability opinion, not a freedom-to-operate analysis, not legal advice.**
  Verdict hints (`novel`, `narrow`, `redraft`, `withdraw`) are attorney-triage
  labels with no legal weight; a registered patent agent / attorney must
  review every finding before any filing or amendment decision.
triggers:
  - "command:workflow:patent.review"
  - "subagent:novelty-critic"
  - "subagent:patent-engineer"
provides:
  - per-element-novelty-score
  - prior-art-overlap-classification
  - differentiator-suggestion
  - claim-amendment-hint
  - per-claim-verdict-hint
  - novelty-heuristics-findings-schema
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
  - doc: capability:claim-chart-builder
  - doc: role-mode:novelty-critic
  - doc: ../../../docs/legal-and-ethics.md
---

# novelty-heuristics

## When to use

Runs as a sub-pass of `workflow:patent.review` (the existing 5-role panel) to give the `novelty-critic` agent **structured data instead of free-text prose**. The findings file is **advisory** — it scores per-element prior-art overlap so an attorney can triage the strongest hits, but it does **not** produce a patentability verdict, and the per-claim `verdict_hint` is an attorney-triage label, never a legal conclusion.

Load it from:

- `workflow:patent.review` — automatically, before the `novelty-critic` subagent assembles its report section.
- the `novelty-critic` subagent directly — when the agent wants the same taxonomy a reviewer would see, before challenging the chart rows.
- the `patent-engineer` subagent — when scoping enablement gaps next to overlap risks.

Skip the run if `.evidraft/patent/claims_parsed.json` is missing — without a parsed claim tree the skill has nothing to score; emit a one-line chat notice naming the missing input and stop.

## Inputs

- `.evidraft/patent/claims_parsed.json` — canonical claim tree (from `claim-parser`). Required.
- `.evidraft/patent/prior_art_map.md` — H2 section per candidate, with `### Patent prior art` and `### Academic prior art` subsections holding bulleted entries (`summary`, `relevance`, optional URL). Required.
- `.evidraft/patent/claim_chart-<ts>.json` — optional, from `claim-chart-builder`. When present **and** carrying the same `run_id` as the current command invocation, reuse its `prior_art_overlap` rows verbatim — do not re-score.
- `.evidraft/patent/invention_disclosure.md` — source for spec-side differentiation language (drives `differentiator_hint` text and the `DIFFERENTIATOR_MISSING_IN_SPEC` rule).

## Outputs

Two files per run under `.evidraft/patent/`:

- `novelty_audit-<ts>.log` — human-readable, one row per finding plus a verdict block per claim. First line is the verbatim advisory banner (see "Advisory-only framing" below).
- `novelty_audit-<ts>.findings.json` — structured findings + per-claim summary + top-level summary.

Full JSON schema, `overlap_score` / `verdict_hint` / `severity` enums, and the verdict roll-up rules live in [references/output-schema.md](references/output-schema.md).

## How to navigate this skill

Load only the reference for the step you are executing:

| Stage | Reference | Owns |
|---|---|---|
| Analysis procedure (5 steps) | [analysis-procedure.md](references/analysis-procedure.md) | read inputs (reuse chart when fresh); walk pairs; overlap classifier; per-claim verdict roll-up; emit log + findings |
| Rule taxonomy (7 rules) | [rule-taxonomy.md](references/rule-taxonomy.md) | per-rule `severity`, when-it-fires, `advisory_note` template |
| Output schema + enums | [output-schema.md](references/output-schema.md) | `findings.json` shape, `severity` / `overlap_score` / `verdict_hint` enums, deterministic verdict roll-up |
| Anti-patterns | [anti-patterns.md](references/anti-patterns.md) | what NOT to do |

## Advisory-only framing

> The `novelty-heuristics` skill is **advisory only**. Its overlap scores reflect a heuristic semantic comparison performed by an LLM; they are **not patentability opinions, not freedom-to-operate analyses, and not legal advice**. The `verdict_hint` labels (`novel`, `narrow`, `redraft`, `withdraw`) are convenience labels for an attorney's triage and have no legal weight. A registered patent agent / attorney must review every finding before any filing or amendment decision. Absence of identified prior art does NOT establish novelty under any jurisdiction's rules — broader prior-art search may surface anticipating references the skill did not see.

Operational consequences of this framing — non-negotiable:

- Every emitted log file's first line is verbatim:

  ```
  # novelty_audit log — advisory only; not legal advice; attorney review required.
  ```

- Every emitted finding carries an `advisory_note` field (see [rule-taxonomy.md](references/rule-taxonomy.md) templates).
- The top-level `summary` block of `findings.json` carries `"advisory": true`.
- The skill never emits a binary "this claim is novel / not novel" verdict; only the `verdict_hint` labels.

## Quality checklist

- [ ] Every finding carries a `rule_id` from [rule-taxonomy.md](references/rule-taxonomy.md) (UPPER_SNAKE, stable across runs) and an `advisory_note`.
- [ ] `overlap_score = identical` only when `overlap_passage` contains a verbatim or near-verbatim quote of the matching prior-art text.
- [ ] `verdict_hint` per claim is computed deterministically from per-element `overlap_score` values per the [output-schema.md](references/output-schema.md) roll-up; never assigned by judgement.
- [ ] `DIFFERENTIATOR_MISSING_IN_SPEC` fires before `verdict_hint` escalates from `narrow` to `redraft`.
- [ ] `CLAIM_FULLY_NOVEL_HEURISTIC` always carries the "absence of evidence is not evidence of absence" `advisory_note`.
- [ ] When `claim_chart-<ts>.json` is fresh (same `run_id`), the skill reuses its `prior_art_overlap` rows and emits a chat line stating the reuse, instead of re-scoring.
- [ ] `claims_analysed` lists every claim from `claims_parsed.json`, in the same order; `per_claim_summary` has one entry per listed claim.
- [ ] `summary.advisory == true` and `summary.{info,warn,fail}` equal the per-severity counts in `findings`.
- [ ] When called with a `run_id`, the value lands at the top level of `findings.json`.
- [ ] The `.log` file's first line is the verbatim advisory banner above.
- [ ] No edits to `claims.md`, `claim_chart.md`, `claims_parsed.json`, `prior_art_map.md`, `invention_disclosure.md`, or any other file outside `.evidraft/patent/novelty_audit-<ts>.{log,findings.json}`.
