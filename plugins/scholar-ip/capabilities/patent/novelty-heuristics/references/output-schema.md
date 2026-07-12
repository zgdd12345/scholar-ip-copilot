# Output schema + enums

Two files per run, both under `.evidraft/patent/`:

- `.evidraft/patent/novelty_audit-<ts>.log` — human-readable, one row per finding plus a verdict block per claim. **Every log file's first line is verbatim:**

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

`<ts>` is UTC iso-basic (`20260518T143000Z`). When the calling command passes a `run_id` via `plan.yaml`, embed it as the top-level `run_id`.

## Enums

`severity` is one of `info | warn | fail`.

`overlap_score` is one of `none | low | medium | high | identical`:

- `none` — the prior-art entry does not address this element.
- `low` — the prior art teaches something tangentially related.
- `medium` — the same goal is achieved by a structurally similar mechanism.
- `high` — the verb-object structure matches; only naming differs.
- `identical` — a **verbatim or near-verbatim claim-language match** exists. This score MUST NOT be assigned without a verbatim quote in `overlap_passage`.

`verdict_hint` per claim is one of `novel | narrow | redraft | withdraw` — explicitly an **advisory** label, never a legal conclusion. Deterministic roll-up from per-element `overlap_score` values for that claim:

- `novel` — every element has `overlap_score ∈ {none, low}`.
- `narrow` — at least one element has `overlap_score ∈ {medium, high}` but the differentiator language can plausibly close the gap (i.e. the differentiator IS present in `invention_disclosure.md`).
- `redraft` — at least one element has `overlap_score: high` **and** the differentiator is not present in the spec (`DIFFERENTIATOR_MISSING_IN_SPEC` fired).
- `withdraw` — at least one element has `overlap_score: identical`.

Roll-up precedence is `withdraw > redraft > narrow > novel`: the most adverse-applicable label wins. The label is **advisory only**; it does not gate any downstream action and is never surfaced as a legal conclusion.

No edits to `claims_parsed.json`, `prior_art_map.md`, `claim_chart-*.json`, `invention_disclosure.md`, or any claim text. Findings only.
