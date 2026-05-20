# Output schemas

Two files per run, both under `.evidraft/patent/`:

- `claim_chart.md` — human-readable, **replaces the previous flat-template version** (the template at `plugins/scholar-ip/templates/patent-project/.evidraft/patent/claim_chart.md` is a stub; this skill writes the live, populated file).
- `claim_chart-<ts>.json` — structured form for downstream consumption (review subagents, change-impact diffs).

`<ts>` is UTC iso-basic (`20260518T143000Z`). When called from a command with a `run_id` in its `plan.yaml`, embed the `run_id` as the top-level field of the JSON.

## `claim_chart-<ts>.json` schema

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

- `overlap_score` enum: `none | low | medium | high | identical`. `identical` **requires a verbatim claim-language match** in `overlap_passage` (a quoted fragment that appears word-for-word in the prior-art bullet's summary or in the identified prior-art document text reproduced in the map). Every non-`identical` score is an LLM judgement and is **advisory only**.
- `risk` enum: `low | medium | high`. Computed per [procedure-risk-and-revise.md](procedure-risk-and-revise.md).
- `spec_support` / `code_support` are arrays — possibly empty. Empty arrays are preserved (they are not omitted); the `summary` counters depend on it.
- `prior_art_overlap` covers **every** prior-art entry for the candidate the row belongs to. Score `none` rows stay in the array (they are evidence the comparison was made).
- `suggested_revision` is `null` (or omitted) when `risk == low`; populated as a one-line narrowing string when `risk ∈ {medium, high}`.

## `claim_chart.md` shape

One H2 per candidate (`## C-001 — <candidate title from prior_art_map.md>`), one big markdown table per H2 with columns:

| Claim | Element | Spec support | Code support | Prior art overlap | Risk | Suggested revision |

Plus a trailing H2 `## Summary` block that renders the JSON `summary` counters. The mandatory advisory-only paragraph from the SKILL.md "Advisory-only framing" section appears at the bottom of the file, verbatim.
