# Analysis procedure

1. **Read inputs.** Load `claims_parsed.json`, `prior_art_map.md`, and `invention_disclosure.md`. If `claim_chart-<ts>.json` is present **and fresh** (same `run_id` as the current command invocation), reuse its `prior_art_overlap` rows verbatim — do not re-score. Otherwise parse `prior_art_map.md` yourself: split on H2 (candidate), then on `### Patent prior art` / `### Academic prior art`, then on bulleted entries; carry the entry's `summary` and `relevance` fields as the comparison surface.

2. **Walk every (claim, element) x (prior-art-entry) pair.** For each independent and dependent claim in `claims_parsed.json`, enumerate its elements (`[a]`, `[b]`, `[c]`, …) and cross with every prior-art entry resolved in step 1.

3. **Per pair, run the overlap classifier.** This is an LLM-driven recipe; the steps are:
   - Extract the **verb-object structure** of the claim element (e.g. `obtaining a query and a set of candidate documents`).
   - Extract the matching passage from the prior art. Use the `summary` and `relevance` fields from `prior_art_map.md`; if the prior-art entry has a publicly readable abstract / claim-text URL the user has populated, use that text too — never fetch the network.
   - Score per the `overlap_score` enum (see [output-schema.md](output-schema.md)). Score `identical` **only** when a verbatim or near-verbatim claim-language match exists and you can quote it into `overlap_passage`; otherwise the highest score available is `high`.
   - Emit a `differentiator_hint`: cite where the differentiating language lives in `invention_disclosure.md` (section + paragraph), and append a one-line narrowing recipe. If no differentiator exists in the spec, say so explicitly — that absence triggers `DIFFERENTIATOR_MISSING_IN_SPEC` (see [rule-taxonomy.md](rule-taxonomy.md)).

4. **Per claim, roll up to `verdict_hint`** per the `verdict_hint` enum (deterministic).

5. **Emit findings + log** per the output schema.

For each emitted finding, populate `advisory_note` with a one-line reminder that the score is heuristic and not a legal opinion. The `CLAIM_FULLY_NOVEL_HEURISTIC` finding carries the explicit "absence of evidence is not evidence of absence" form (see [rule-taxonomy.md](rule-taxonomy.md)).
