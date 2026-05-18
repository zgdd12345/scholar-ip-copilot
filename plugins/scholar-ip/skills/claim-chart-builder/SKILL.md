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
  - "command:/scholar:patent-review"
  - "command:/scholar:patent-prior-art"
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
hooks: [evidence-consistency]
references:
  - doc: ../claim-parser/SKILL.md
  - doc: ../novelty-heuristics/SKILL.md
  - doc: ../../agents/claim-drafter.md
  - doc: ../../../../docs/legal-and-ethics.md
---

# claim-chart-builder

## 1. When to use

Runs whenever `/scholar:patent-prior-art` or `/scholar:patent-review` has a fresh
`.evidraft/patent/claims_parsed.json` (produced by `claim-parser`) **and** a populated
`.evidraft/patent/prior_art_map.md`. Replaces the previous "fill the chart by hand"
pattern in the `claim-drafter` agent with an automated, structured build that any
reviewer can re-run after editing the claims or the prior-art map.

Two callers, two reasons:

- `/scholar:patent-prior-art` — first construction, immediately after the prior-art
  map gets new entries. The chart shows attorneys which elements are exposed.
- `/scholar:patent-review` / `patent-engineer` — re-build after the drafter narrowed
  a high-risk element; confirms the risk dropped and no new gaps opened.

Skip the run if `claims_parsed.json` is missing or `claims` is empty (the chart has
no rows to build); print one chat line explaining why and stop. Also skip if
`prior_art_map.md` has zero bullet-list entries under any candidate — without prior
art there is no overlap to score (still emit an empty chart so the audit trail
shows the run happened).

## 2. Inputs

- `.evidraft/patent/claims_parsed.json` — canonical claim form, from `claim-parser`.
  Shape:
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
- `.evidraft/patent/prior_art_map.md` — H2 per candidate (`### Patent prior art` and
  `### Academic prior art` subsections, each a bulleted list of
  `- US-1234567-B2 (assignee, date) — relevance: <high/med/low>, summary, why-different`).
- (optional) `.evidraft/patent/invention_disclosure.md` — used for the `spec_support`
  column. If absent, `spec_support` cells stay empty and risk roll-up applies the
  no-support override.
- (optional) `.evidraft/code/method_to_code.md` — used for the `code_support` column.
  Same fallback as above when missing.

The skill never reads source code directly; it relies on `method_to_code.md` for the
code surface mapping. That keeps the chart deterministic and audit-friendly.

## 3. Outputs

Two files per run, both under `.evidraft/patent/`:

- `claim_chart.md` — human-readable, **replaces the previous flat-template version**
  (the template at `plugins/scholar-ip/templates/patent-project/.evidraft/patent/claim_chart.md`
  is a stub; this skill writes the live, populated file).
- `claim_chart-<ts>.json` — structured form for downstream consumption (review
  subagents, change-impact diffs).

`<ts>` is UTC iso-basic (`20260518T143000Z`). When called from a command with a
`run_id` in its `plan.yaml`, embed the `run_id` as the top-level field of the JSON.

### 3.1 `claim_chart-<ts>.json` schema

```json
{
  "run_id": "...",
  "ts": "20260518T143000Z",
  "candidates": [
    {
      "candidate_id": "C-001",
      "claims_covered": ["c1", "c2"],
      "rows": [
        {
          "claim_id": "c1",
          "element_label": "a",
          "element_text": "obtaining a query and a set of candidate documents;",
          "spec_support": [{"section": "Technical solution", "loc": "para 3"}],
          "code_support": [{"file": "src/retriever.py", "lines": "12-45", "symbol": "Retriever.retrieve"}],
          "prior_art_overlap": [
            {"prior_art_id": "pa_001",
             "title": "US-1234567-B2 (Acme, 2019)",
             "overlap_score": "high",
             "overlap_passage": "claim 1 step (a) of US-1234567 reads: 'receiving a query and a candidate document set'.",
             "differentiator_note": "Ours uses a Bloom-filter index; theirs uses a serial scan."}
          ],
          "risk": "medium",
          "suggested_revision": "Narrow `set of candidate documents` to `set of candidate documents retrieved by a Bloom-filter pre-filter`."
        }
      ]
    }
  ],
  "summary": {
    "rows_total": 0,
    "rows_high_risk": 0,
    "rows_medium_risk": 0,
    "rows_low_risk": 0,
    "rows_no_spec_support": 0,
    "rows_no_code_support": 0
  }
}
```

Field rules:

- `overlap_score` enum: `none | low | medium | high | identical`. `identical`
  **requires a verbatim claim-language match** in `overlap_passage` (a quoted
  fragment that appears word-for-word in the prior-art bullet's summary or in the
  identified prior-art document text reproduced in the map). Every non-`identical`
  score is an LLM judgement and is **advisory only**.
- `risk` enum: `low | medium | high`. Computed per § 4.7.
- `spec_support` / `code_support` are arrays — possibly empty. Empty arrays are
  preserved (they are not omitted); the `summary` counters depend on it.
- `prior_art_overlap` covers **every** prior-art entry for the candidate the row
  belongs to. Score `none` rows stay in the array (they are evidence the comparison
  was made).
- `suggested_revision` is `null` (or omitted) when `risk == low`; populated as a
  one-line narrowing string when `risk ∈ {medium, high}`.

### 3.2 `claim_chart.md` shape

One H2 per candidate (`## C-001 — <candidate title from prior_art_map.md>`), one
big markdown table per H2 with columns:

| Claim | Element | Spec support | Code support | Prior art overlap | Risk | Suggested revision |

Plus a trailing H2 `## Summary` block that renders the JSON `summary` counters. The
mandatory advisory-only paragraph from § 6 appears at the bottom of the file,
verbatim.

## 4. Build procedure

### 4.1 Read inputs

1. Read `.evidraft/patent/claims_parsed.json`. If the file is missing or
   `claims == []`, skip with a chat line and stop.
2. Read `.evidraft/patent/prior_art_map.md`. Build the in-memory structure:
   ```python
   {"C-001": {"title": "...",
              "prior_art": [{"id":"pa_001","raw":"- US-1234567-B2 ...",
                             "title":"US-1234567-B2 (Acme, 2019)",
                             "relevance":"high","summary":"...","why_different":"..."},
                            ...]},
    "C-002": {...}, ...}
   ```
3. Read `.evidraft/patent/invention_disclosure.md` if present (else mark
   `spec_support_available = False`).
4. Read `.evidraft/code/method_to_code.md` if present (else mark
   `code_support_available = False`).

### 4.2 Mint prior-art ids

If the bullet line in `prior_art_map.md` does not already carry a stable id, mint one
deterministically: walk candidates in source order, walk their `### Patent prior art`
bullets first then `### Academic prior art` bullets in source order, assign
`pa_001`, `pa_002`, … globally. Record the mapping `(file_offset → pa_id)` so a
second run on the same map produces identical ids.

If the bullet already carries an id (e.g. the line begins `- [pa_017] US-...`),
adopt it verbatim and skip minting for that bullet.

### 4.3 Map candidates to claims

`claims_parsed.json` does not declare which candidate each claim belongs to. Resolve
via either (a) a `candidate_id` field on the claim if `claim-parser` supplied one, or
(b) the natural ordering: claim `c1` belongs to the first candidate's first
independent claim; subsequent claims attach to the same candidate until a new
independent claim starts a new candidate. Record `claims_covered` per candidate
exactly as resolved.

### 4.4 Walk every (claim, element) pair

For each `claim ∈ claims_parsed.claims`, for each `element ∈ claim.elements`, create
one chart row scaffold `{claim_id, element_label, element_text}`. **No element is
skipped** — even elements with empty support and no overlap stay in the table (the
gap is the signal).

### 4.5 Spec support pass

For each element:

1. Extract the noun set from `element.antecedents_introduced + element.antecedents_referenced`.
2. Extract verbs from `element.text` (heuristic: tokens whose normalised form ends in
   `-ing` or appears in a small verb stop-list — `obtaining`, `computing`, `storing`,
   `retrieving`, `comparing`, `outputting`, …).
3. For each H2 / H3 section in `invention_disclosure.md`, count noun + verb hits in
   that section's body (Grep `-c -F -i -- <token>`).
4. Emit one `{section, loc}` per section whose hit-count is ≥ 2 distinct tokens; cap
   at the top 3 sections to keep cells short. `loc` is the nearest preceding
   heading-relative anchor (`para N` where N counts non-empty paragraphs from the
   section start) or a code-block marker (`fenced block 1`).
5. If no section meets the threshold, `spec_support = []`.

### 4.6 Code support pass

For each element:

1. Same noun + verb extraction.
2. Walk `method_to_code.md` rows (typically a markdown table mapping
   `method step → file:lines → symbol`). For each row, score by noun + verb overlap
   against the row's `method step` cell.
3. Emit `{file, lines, symbol}` for every row whose overlap is ≥ 2 distinct tokens;
   cap at top 3 rows.
4. If no row meets the threshold, `code_support = []`.

### 4.7 Prior-art overlap pass

For each (element, prior-art entry) pair belonging to the element's candidate:

1. Read the prior-art bullet's `summary` and `why_different` fields.
2. Semantic comparison (LLM judgement): does the prior art teach this element?
3. Emit `overlap_score ∈ {none, low, medium, high, identical}`:
   - `identical` — requires a verbatim quote in `overlap_passage` that appears
     **word-for-word** in the prior-art bullet (or in claim text reproduced in the
     prior-art summary). The skill must include the quoted string in
     `overlap_passage`. If a verbatim match is not available, downgrade to `high`.
   - `high` — paraphrased near-match (same operations, same operands, same order);
     LLM judgement; **advisory only**.
   - `medium` — partial overlap (same operation, different operand; or same operand,
     different operation).
   - `low` — tangential overlap (same domain, no operational overlap on this element).
   - `none` — the prior art does not address this element at all.
4. `overlap_passage` is a one-line quote (≤ 240 chars) from the prior-art bullet
   summary. For `identical` it is verbatim; for other scores it is the closest
   paraphrase available in the bullet.
5. `differentiator_note` is a one-line description (≤ 240 chars) of what makes our
   element different — inherit from the bullet's `why_different` when available,
   otherwise synthesize from the element's antecedents.

### 4.8 Risk roll-up

Per row, compute risk in two stages:

1. **Overlap-driven risk** = max over `prior_art_overlap[*].overlap_score` mapped as
   `identical → high, high → high, medium → medium, low → low, none → low`. An empty
   `prior_art_overlap` array (no prior art on the candidate at all) maps to `low`.
2. **No-support override**: if `spec_support == [] AND code_support == []`, force
   `risk = high` regardless of the overlap-driven value. An element with no support
   is its own risk: it is unenforceable and unanchored.

The two stages combine by `risk = max(overlap_driven, no_support_override)` where
`high > medium > low`.

### 4.9 Suggested-revision recipe

Populated **only** when `risk ∈ {medium, high}`; for `risk == low` the field is
omitted (or set to `null`). For each populated row:

1. Pick the highest-scoring `prior_art_overlap` entry (ties broken by source order).
2. Read its `differentiator_note`.
3. Synthesize a one-line narrowing string of the form
   `Narrow \`<element fragment>\` to \`<fragment + differentiator>\`.` (See the
   example in § 3.1.)
4. The string **must inherit a real differentiator** — never invent one not present
   in the prior-art bullet or the element's own support cells. If no
   differentiator is available, emit
   `Cannot auto-suggest revision; differentiator absent from prior_art_map.md.` and
   leave the row at its current risk.
5. **Never widens scope.** The suggested rewrite must contain the original fragment
   as a substring (or a strict refinement of it). The skill self-checks this: if the
   proposed string drops a noun present in the original element, abort and emit the
   "Cannot auto-suggest" fallback.

### 4.10 Write outputs

Render `claim_chart.md` (markdown table per candidate; § 6 advisory paragraph at the
end). Write `claim_chart-<ts>.json` next to it. Print one chat summary line:

```
claim-chart-builder: <C> candidates, <R> rows  (high=<h>, medium=<m>, low=<l>)
  .evidraft/patent/claim_chart.md
  .evidraft/patent/claim_chart-<ts>.json
```

## 5. Quality checklist

- [ ] Every (claim, element) pair in `claims_parsed.json` appears as exactly one
      row; row count equals `sum(len(claim.elements) for claim in claims)`.
- [ ] No row is silently dropped because `spec_support` or `code_support` is empty
      — the row stays, the empty cells show, and the no-support override is applied
      (`risk = high`).
- [ ] No row carries `overlap_score: identical` without a verbatim quote in
      `overlap_passage` (the skill self-checks via substring match against the
      prior-art bullet text).
- [ ] `suggested_revision` populated **iff** `risk ∈ {medium, high}`; never for
      `risk == low`.
- [ ] `suggested_revision` never widens scope (substring self-check passed).
- [ ] `overlap_score` values strictly within `{none, low, medium, high, identical}`.
- [ ] `risk` values strictly within `{low, medium, high}`.
- [ ] `summary.rows_total == sum(len(c.rows) for c in candidates)`.
- [ ] `summary.rows_high_risk + summary.rows_medium_risk + summary.rows_low_risk
      == summary.rows_total`.
- [ ] `summary.rows_no_spec_support` counts rows whose `spec_support == []`;
      `summary.rows_no_code_support` counts rows whose `code_support == []`.
- [ ] Every prior-art passage cited in any `overlap_passage` traces back to a bullet
      in `prior_art_map.md` (no invented citations).
- [ ] `claim_chart.md` ends with the verbatim § 6 advisory paragraph.
- [ ] When called with a `run_id`, the value lands at the top level of
      `claim_chart-<ts>.json`.

## 6. Advisory-only framing

The following paragraph is **mandatory and verbatim** at the end of every emitted
`claim_chart.md`:

> The `claim-chart-builder` skill produces a structured claim chart for **reviewer
> convenience**. Overlap scores reflect a heuristic semantic comparison and are
> **advisory only** — they help an attorney spot the strongest prior-art hits
> earlier but are not a substitute for an examiner-grade rejection analysis. A
> registered patent agent / attorney must review every row before any filing
> decision; `suggested_revision` cells are starting points, not final claim
> language.

## 7. Anti-patterns

- **Scoring `identical` on paraphrased prior art.** `identical` requires a verbatim
  quote in `overlap_passage`. When in doubt, downgrade to `high`.
- **Widening claim scope in `suggested_revision`.** Suggested rewrites are
  narrowing-only; the self-check refuses any rewrite that drops a noun present in
  the original element.
- **Auto-fixing the claim text.** This skill emits a chart; it never edits
  `claims.md` or `claims_parsed.json`. The drafter (`claim-drafter` agent) or
  the human applies revisions on a separate pass.
- **Silently dropping rows when spec/code support is missing.** The row stays, the
  empty cells stay, and the no-support override flips the row to `risk = high` so
  the gap is visible in the summary counters.
- **Citing prior-art passages that don't appear in `prior_art_map.md`.** Every
  `overlap_passage` must be a substring of the prior-art bullet's `summary` (or the
  bullet itself); inventing supporting quotes is a citation fabrication.
- **Re-implementing `claim-parser`'s element extraction.** The chart consumes
  `claims_parsed.json` as-is; if the parser is wrong the parser gets fixed, not
  patched here.
- **Probing the live patent record for the prior-art document.** The skill works
  entirely off `prior_art_map.md`; network probes would be slow, flaky, and would
  pull in claim text the map curator chose not to include.
- **Treating the chart as a patentability opinion.** It is reviewer convenience.
  The advisory paragraph in § 6 is not optional decoration.
