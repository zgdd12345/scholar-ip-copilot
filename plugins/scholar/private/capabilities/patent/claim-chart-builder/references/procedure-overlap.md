# Procedure — prior-art overlap pass

For each (element, prior-art entry) pair belonging to the element's candidate:

1. Read the prior-art bullet's `summary` and `why_different` fields.
2. Semantic comparison (LLM judgement): does the prior art teach this element?
3. Emit `overlap_score ∈ {none, low, medium, high, identical}`:
   - `identical` — requires a verbatim quote in `overlap_passage` that appears **word-for-word** in the prior-art bullet (or in claim text reproduced in the prior-art summary). The skill must include the quoted string in `overlap_passage`. If a verbatim match is not available, downgrade to `high`.
   - `high` — paraphrased near-match (same operations, same operands, same order); LLM judgement; **advisory only**.
   - `medium` — partial overlap (same operation, different operand; or same operand, different operation).
   - `low` — tangential overlap (same domain, no operational overlap on this element).
   - `none` — the prior art does not address this element at all.
4. `overlap_passage` is a one-line quote (≤ 240 chars) from the prior-art bullet summary. For `identical` it is verbatim; for other scores it is the closest paraphrase available in the bullet.
5. `differentiator_note` is a one-line description (≤ 240 chars) of what makes our element different — inherit from the bullet's `why_different` when available, otherwise synthesize from the element's antecedents.

**Handoff.** Each row's `prior_art_overlap` array is now populated (including `none`-scored rows as evidence the comparison was made). [procedure-risk-and-revise.md](procedure-risk-and-revise.md) rolls these up into a per-row `risk` and (if needed) a `suggested_revision`.
