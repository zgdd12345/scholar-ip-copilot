# Rule taxonomy

Each rule carries: `rule_id` (UPPER_SNAKE, stable across runs), severity, when it fires, and the `advisory_note` template.

| `rule_id` | sev | When it fires | `advisory_note` |
|---|---|---|---|
| `PRIOR_ART_IDENTICAL` | fail | A `(claim, element, prior-art-entry)` pair scores `overlap_score = identical` (verbatim quote available in `overlap_passage`). | "Advisory only; verbatim match suggests strong anticipation risk — attorney must confirm whether the cited passage qualifies as anticipating prior art under the relevant jurisdiction." |
| `PRIOR_ART_HIGH_OVERLAP` | warn | Pair scores `overlap_score = high`: verb-object structure matches; only naming differs. | "Advisory only; an attorney must judge whether this overlap defeats novelty under the relevant jurisdiction's rules." |
| `PRIOR_ART_MEDIUM_OVERLAP` | warn | Pair scores `overlap_score = medium`: same goal achieved via a structurally similar mechanism. | "Advisory only; medium overlap may or may not anticipate — attorney triage required." |
| `PRIOR_ART_LOW_OVERLAP` | info | Pair scores `overlap_score = low`: tangentially related; flagged for completeness. | "Advisory only; flagged so the attorney can decide whether to distinguish proactively." |
| `DIFFERENTIATOR_MISSING_IN_SPEC` | warn | A `(claim, element)` has at least one `high` (or `identical`) overlap, AND `invention_disclosure.md` contains no spec-side differentiator language for that element. Escalates the claim's `verdict_hint` from `narrow` to `redraft`. | "Advisory only; the spec must enable the differentiator before any narrowing amendment — attorney must verify enablement." |
| `ELEMENT_NO_PRIOR_ART_FOUND` | info | No prior-art entry in `prior_art_map.md` meaningfully addresses this element (every pair scored `none`). Informational; suggests the prior-art search may be incomplete. **Do NOT treat as evidence of novelty.** | "Advisory only; absence of an identified overlap is NOT evidence of novelty — broader prior-art search may surface anticipating references." |
| `CLAIM_FULLY_NOVEL_HEURISTIC` | info | Every element of the claim has `overlap_score ∈ {none, low}` (i.e. `verdict_hint = novel`). This is the most permissive verdict the skill ever gives. | "Advisory only; absence of evidence is not evidence of absence — broader prior-art search may surface anticipating references the skill did not see. Attorney review required." |

**Rule count: 7** — `PRIOR_ART_IDENTICAL`, `PRIOR_ART_HIGH_OVERLAP`, `PRIOR_ART_MEDIUM_OVERLAP`, `PRIOR_ART_LOW_OVERLAP`, `DIFFERENTIATOR_MISSING_IN_SPEC`, `ELEMENT_NO_PRIOR_ART_FOUND`, `CLAIM_FULLY_NOVEL_HEURISTIC`.
