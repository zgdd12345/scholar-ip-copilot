# Procedure — walk every element + resolve spec / code support

## Walk every (claim, element) pair

For each `claim ∈ claims_parsed.claims`, for each `element ∈ claim.elements`, create one chart row scaffold `{claim_id, element_label, element_text}`. **No element is skipped** — even elements with empty support and no overlap stay in the table (the gap is the signal).

## Spec support pass

For each element:

1. Extract the noun set from `element.antecedents_introduced + element.antecedents_referenced`.
2. Extract verbs from `element.text` (heuristic: tokens whose normalised form ends in `-ing` or appears in a small verb stop-list — `obtaining`, `computing`, `storing`, `retrieving`, `comparing`, `outputting`, …).
3. For each H2 / H3 section in `invention_disclosure.md`, count noun + verb hits in that section's body (Grep `-c -F -i -- <token>`).
4. Emit one `{section, loc}` per section whose hit-count is ≥ 2 distinct tokens; cap at the top 3 sections to keep cells short. `loc` is the nearest preceding heading-relative anchor (`para N` where N counts non-empty paragraphs from the section start) or a code-block marker (`fenced block 1`).
5. If no section meets the threshold, `spec_support = []`.

## Code support pass

For each element:

1. Same noun + verb extraction as the spec pass.
2. Walk `method_to_code.md` rows (typically a markdown table mapping `method step → file:lines → symbol`). For each row, score by noun + verb overlap against the row's `method step` cell.
3. Emit `{file, lines, symbol}` for every row whose overlap is ≥ 2 distinct tokens; cap at top 3 rows.
4. If no row meets the threshold, `code_support = []`.

**Handoff.** Each row now has its `element_*`, `spec_support`, `code_support` cells. [procedure-overlap.md](procedure-overlap.md) fills in `prior_art_overlap`.
