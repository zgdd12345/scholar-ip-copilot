---
id: novelty-heuristics
title: "Novelty heuristics: per-element prior-art overlap scoring with advisory verdict hints"
kind: skill
phase: patent
description: >
  Per-claim-element novelty heuristics for the `/scholar:patent-review` 5-role
  panel. Walks every (claim, element) x (prior-art-entry) pair, scores
  semantic overlap on a 5-step ladder, and emits a structured findings file
  plus a human log for the `novelty-critic` agent. **Advisory only — not a
  patentability opinion, not a freedom-to-operate analysis, not legal advice.**
  Verdict hints (`novel`, `narrow`, `redraft`, `withdraw`) are attorney-triage
  labels with no legal weight; a registered patent agent / attorney must
  review every finding before any filing or amendment decision.
triggers:
  - "command:/scholar:patent-review"
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
hooks: [evidence-consistency]
references:
  - doc: ../claim-parser/SKILL.md
  - doc: ../claim-chart-builder/SKILL.md
  - doc: ../../agents/novelty-critic.md
  - doc: ../../../docs/legal-and-ethics.md
---

# novelty-heuristics

## 1. When to use

Runs as a sub-pass of `/scholar:patent-review` (the existing 5-role panel) to
give the `novelty-critic` agent **structured data instead of free-text prose**.
The findings file is **advisory** — it scores per-element prior-art overlap so
an attorney can triage the strongest hits, but it does **not** produce a
patentability verdict, and the per-claim `verdict_hint` is an attorney-triage
label, never a legal conclusion.

Load it from:

- `/scholar:patent-review` — automatically, before the `novelty-critic`
  subagent assembles its report section.
- the `novelty-critic` subagent directly — when the agent wants the same
  taxonomy a reviewer would see, before challenging the chart rows.
- the `patent-engineer` subagent — when scoping enablement gaps next to
  overlap risks.

Skip the run if `.evidraft/patent/claims_parsed.json` is missing — without a
parsed claim tree the skill has nothing to score; emit a one-line chat notice
naming the missing input and stop.

## 2. Inputs

- `.evidraft/patent/claims_parsed.json` — canonical claim tree (from
  `claim-parser`). Required.
- `.evidraft/patent/prior_art_map.md` — H2 section per candidate, with
  `### Patent prior art` and `### Academic prior art` subsections holding
  bulleted entries (`summary`, `relevance`, optional URL). Required.
- `.evidraft/patent/claim_chart-<ts>.json` — optional, from
  `claim-chart-builder`. When present **and** carrying the same `run_id` as
  the current command invocation, reuse its `prior_art_overlap` rows
  verbatim — do not re-score.
- `.evidraft/patent/invention_disclosure.md` — source for spec-side
  differentiation language (drives `differentiator_hint` text and the
  `DIFFERENTIATOR_MISSING_IN_SPEC` rule).

## 3. Outputs

Two files per run, both under `.evidraft/patent/`:

- `.evidraft/patent/novelty_audit-<ts>.log` — human-readable, one row per
  finding plus a verdict block per claim. **Every log file's first line is
  verbatim:**

  ```
  # novelty_audit log — advisory only; not legal advice; attorney review required.
  ```

- `.evidraft/patent/novelty_audit-<ts>.findings.json` — structured:

```json
{
  "run_id": "...",
  "ts": "20260518T143000Z",
  "claims_analysed": ["c1", "c2", "c3"],
  "findings": [
    {
      "rule_id": "PRIOR_ART_HIGH_OVERLAP",
      "severity": "warn",
      "claim_id": "c1",
      "element_label": "a",
      "element_text": "obtaining a query and a set of candidate documents;",
      "prior_art_id": "pa_001",
      "prior_art_title": "US-1234567-B2 ...",
      "overlap_score": "high",
      "overlap_passage": "claim 1 step (a) of US-1234567 reads...",
      "differentiator_required": true,
      "differentiator_hint": "The prior art uses a serial scan over the document set; our element relies on a Bloom-filter pre-filter (see invention_disclosure.md §Technical solution para 3). Make this explicit in claim language.",
      "explanation": "Element (a) overlaps materially with the prior art's step (a). Without explicit differentiator language in the claim, an examiner is likely to assert anticipation.",
      "advisory_note": "Advisory only; an attorney must judge whether this overlap defeats novelty under the relevant jurisdiction's rules."
    }
  ],
  "per_claim_summary": {
    "c1": {"novel_elements": 2, "low_overlap": 1, "medium_overlap": 0, "high_overlap": 1, "identical": 0, "verdict_hint": "narrow"},
    "c2": {"novel_elements": 3, "low_overlap": 0, "medium_overlap": 0, "high_overlap": 0, "identical": 0, "verdict_hint": "novel"}
  },
  "summary": {"info": 0, "warn": 0, "fail": 0, "advisory": true}
}
```

`<ts>` is UTC iso-basic (`20260518T143000Z`). When the calling command passes
a `run_id` via `plan.yaml`, embed it as the top-level `run_id`.

### Enums

`severity` is one of `info | warn | fail`.

`overlap_score` is one of `none | low | medium | high | identical`:

- `none` — the prior-art entry does not address this element.
- `low` — the prior art teaches something tangentially related.
- `medium` — the same goal is achieved by a structurally similar mechanism.
- `high` — the verb-object structure matches; only naming differs.
- `identical` — a **verbatim or near-verbatim claim-language match** exists.
  This score MUST NOT be assigned without a verbatim quote in
  `overlap_passage`.

`verdict_hint` per claim is one of `novel | narrow | redraft | withdraw` —
explicitly an **advisory** label, never a legal conclusion. Deterministic
roll-up from per-element `overlap_score` values for that claim:

- `novel` — every element has `overlap_score ∈ {none, low}`.
- `narrow` — at least one element has `overlap_score ∈ {medium, high}` but
  the differentiator language can plausibly close the gap (i.e. the
  differentiator IS present in `invention_disclosure.md`).
- `redraft` — at least one element has `overlap_score: high` **and** the
  differentiator is not present in the spec (`DIFFERENTIATOR_MISSING_IN_SPEC`
  fired).
- `withdraw` — at least one element has `overlap_score: identical`.

Roll-up precedence is `withdraw > redraft > narrow > novel`: the most
adverse-applicable label wins. The label is **advisory only**; it does not
gate any downstream action and is never surfaced as a legal conclusion.

No edits to `claims_parsed.json`, `prior_art_map.md`, `claim_chart-*.json`,
`invention_disclosure.md`, or any claim text. Findings only.

## 4. Analysis procedure

1. **Read inputs.** Load `claims_parsed.json`, `prior_art_map.md`, and
   `invention_disclosure.md`. If `claim_chart-<ts>.json` is present **and
   fresh** (same `run_id` as the current command invocation), reuse its
   `prior_art_overlap` rows verbatim — do not re-score. Otherwise parse
   `prior_art_map.md` yourself: split on H2 (candidate), then on
   `### Patent prior art` / `### Academic prior art`, then on bulleted
   entries; carry the entry's `summary` and `relevance` fields as the
   comparison surface.
2. **Walk every (claim, element) x (prior-art-entry) pair.** For each
   independent and dependent claim in `claims_parsed.json`, enumerate its
   elements (`[a]`, `[b]`, `[c]`, …) and cross with every prior-art entry
   resolved in step 1.
3. **Per pair, run the overlap classifier.** This is an LLM-driven recipe;
   the steps are:
   - Extract the **verb-object structure** of the claim element (e.g.
     `obtaining a query and a set of candidate documents`).
   - Extract the matching passage from the prior art. Use the
     `summary` and `relevance` fields from `prior_art_map.md`; if the
     prior-art entry has a publicly readable abstract / claim-text URL the
     user has populated, use that text too — never fetch the network.
   - Score per the `overlap_score` enum (§ 3). Score `identical` **only**
     when a verbatim or near-verbatim claim-language match exists and you
     can quote it into `overlap_passage`; otherwise the highest score
     available is `high`.
   - Emit a `differentiator_hint`: cite where the differentiating language
     lives in `invention_disclosure.md` (section + paragraph), and append a
     one-line narrowing recipe. If no differentiator exists in the spec,
     say so explicitly — that absence triggers `DIFFERENTIATOR_MISSING_IN_SPEC`.
4. **Per claim, roll up to `verdict_hint`** per § 3 (deterministic).
5. **Emit findings + log** per § 3.

For each emitted finding, populate `advisory_note` with a one-line reminder
that the score is heuristic and not a legal opinion. The
`CLAIM_FULLY_NOVEL_HEURISTIC` finding carries the explicit
"absence of evidence is not evidence of absence" form (see § 5).

## 5. Rule taxonomy

Each rule below carries: `rule_id` (UPPER_SNAKE, stable across runs),
severity, when it fires, and the `advisory_note` template.

| `rule_id` | sev | When it fires | `advisory_note` |
|---|---|---|---|
| `PRIOR_ART_IDENTICAL` | fail | A `(claim, element, prior-art-entry)` pair scores `overlap_score = identical` (verbatim quote available in `overlap_passage`). | "Advisory only; verbatim match suggests strong anticipation risk — attorney must confirm whether the cited passage qualifies as anticipating prior art under the relevant jurisdiction." |
| `PRIOR_ART_HIGH_OVERLAP` | warn | Pair scores `overlap_score = high`: verb-object structure matches; only naming differs. | "Advisory only; an attorney must judge whether this overlap defeats novelty under the relevant jurisdiction's rules." |
| `PRIOR_ART_MEDIUM_OVERLAP` | warn | Pair scores `overlap_score = medium`: same goal achieved via a structurally similar mechanism. | "Advisory only; medium overlap may or may not anticipate — attorney triage required." |
| `PRIOR_ART_LOW_OVERLAP` | info | Pair scores `overlap_score = low`: tangentially related; flagged for completeness. | "Advisory only; flagged so the attorney can decide whether to distinguish proactively." |
| `DIFFERENTIATOR_MISSING_IN_SPEC` | warn | A `(claim, element)` has at least one `high` (or `identical`) overlap, AND `invention_disclosure.md` contains no spec-side differentiator language for that element. Escalates the claim's `verdict_hint` from `narrow` to `redraft`. | "Advisory only; the spec must enable the differentiator before any narrowing amendment — attorney must verify enablement." |
| `ELEMENT_NO_PRIOR_ART_FOUND` | info | No prior-art entry in `prior_art_map.md` meaningfully addresses this element (every pair scored `none`). Informational; suggests the prior-art search may be incomplete. **Do NOT treat as evidence of novelty.** | "Advisory only; absence of an identified overlap is NOT evidence of novelty — broader prior-art search may surface anticipating references." |
| `CLAIM_FULLY_NOVEL_HEURISTIC` | info | Every element of the claim has `overlap_score ∈ {none, low}` (i.e. `verdict_hint = novel`). This is the most permissive verdict the skill ever gives. | "Advisory only; absence of evidence is not evidence of absence — broader prior-art search may surface anticipating references the skill did not see. Attorney review required." |

**Rule count: 7** — `PRIOR_ART_IDENTICAL`, `PRIOR_ART_HIGH_OVERLAP`,
`PRIOR_ART_MEDIUM_OVERLAP`, `PRIOR_ART_LOW_OVERLAP`,
`DIFFERENTIATOR_MISSING_IN_SPEC`, `ELEMENT_NO_PRIOR_ART_FOUND`,
`CLAIM_FULLY_NOVEL_HEURISTIC`.

## 6. Advisory-only framing

> The `novelty-heuristics` skill is **advisory only**. Its overlap scores reflect a heuristic semantic comparison performed by an LLM; they are **not patentability opinions, not freedom-to-operate analyses, and not legal advice**. The `verdict_hint` labels (`novel`, `narrow`, `redraft`, `withdraw`) are convenience labels for an attorney's triage and have no legal weight. A registered patent agent / attorney must review every finding before any filing or amendment decision. Absence of identified prior art does NOT establish novelty under any jurisdiction's rules — broader prior-art search may surface anticipating references the skill did not see.

Operational consequences of this framing — non-negotiable:

- Every emitted log file's first line is verbatim:

  ```
  # novelty_audit log — advisory only; not legal advice; attorney review required.
  ```

- Every emitted finding carries an `advisory_note` field (see § 5
  templates).
- The top-level `summary` block of `findings.json` carries `"advisory": true`.
- The skill never emits a binary "this claim is novel / not novel"
  verdict; only the `verdict_hint` labels of § 3.

## 7. Quality checklist

- [ ] Every finding carries a `rule_id` from § 5 (UPPER_SNAKE, stable
  across runs) and an `advisory_note`.
- [ ] `overlap_score = identical` only when `overlap_passage` contains a
  verbatim or near-verbatim quote of the matching prior-art text.
- [ ] `verdict_hint` per claim is computed deterministically from per-element
  `overlap_score` values per the § 3 roll-up; never assigned by judgement.
- [ ] `DIFFERENTIATOR_MISSING_IN_SPEC` fires before `verdict_hint`
  escalates from `narrow` to `redraft`.
- [ ] `CLAIM_FULLY_NOVEL_HEURISTIC` always carries the
  "absence of evidence is not evidence of absence" `advisory_note`.
- [ ] When `claim_chart-<ts>.json` is fresh (same `run_id`), the skill
  reuses its `prior_art_overlap` rows and emits a chat line stating the
  reuse, instead of re-scoring.
- [ ] `claims_analysed` lists every claim from `claims_parsed.json`, in the
  same order; `per_claim_summary` has one entry per listed claim.
- [ ] `summary.advisory == true` and `summary.{info,warn,fail}` equal the
  per-severity counts in `findings`.
- [ ] When called with a `run_id`, the value lands at the top level of
  `findings.json`.
- [ ] The `.log` file's first line is the verbatim advisory banner of § 6.
- [ ] No edits to `claims.md`, `claim_chart.md`, `claims_parsed.json`,
  `prior_art_map.md`, `invention_disclosure.md`, or any other file outside
  `.evidraft/patent/novelty_audit-<ts>.{log,findings.json}`.

## 8. Anti-patterns

- **Producing a final "this claim is novel" verdict.** The skill only
  produces `verdict_hint`, never a yes/no. A yes/no would be a legal opinion.
- **Scoring `identical` without a verbatim quote.** `identical` is reserved
  for verbatim or near-verbatim matches; without a quote in
  `overlap_passage` the highest allowable score is `high`.
- **Treating an empty prior-art set as evidence of novelty.** Empty means
  the prior-art search is incomplete; `CLAIM_FULLY_NOVEL_HEURISTIC` carries
  the disclaimer in its `advisory_note` and `ELEMENT_NO_PRIOR_ART_FOUND`
  fires per element to keep this honest.
- **Re-scoring overlap rows that `claim-chart-builder` already produced**
  unless the user explicitly requests a re-run. When
  `claim_chart-<ts>.json` is fresh, reuse — do not duplicate work or risk
  drift between the chart and the audit.
- **Editing the claim text or the prior-art map.** Findings only. The
  `claim-drafter` agent and the attorney decide on amendments.
- **Inventing prior-art entries or overlap passages.** Every
  `prior_art_id`, `prior_art_title`, and `overlap_passage` must trace to a
  real entry in `prior_art_map.md` (or its publicly readable source the
  user populated). No hallucinated citations.
- **Promoting a `verdict_hint` to legal weight.** The labels are attorney
  triage; surfacing them as patentability conclusions in chat, in the
  `patent_review_report.md`, or anywhere else violates the advisory-only
  framing and § 6 of this skill.
- **Skipping the `findings.json` write because nothing fired.** The empty
  file is the audit-trail proof that the audit ran; emit it with
  `findings: []`, `summary.advisory: true`, and zero severity counts.
