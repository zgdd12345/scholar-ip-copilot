# Procedure — setup (read inputs, mint ids, map candidates)

## Read inputs

1. Read `.evidraft/patent/claims_parsed.json`. If the file is missing or `claims == []`, skip with a chat line and stop.
2. Read `.evidraft/patent/prior_art_map.md`. Build the in-memory structure:
   ```python
   {"C-001": {"title": "...",
              "prior_art": [{"id":"pa_001","raw":"- US-1234567-B2 ...",
                             "title":"US-1234567-B2 (Acme, 2019)",
                             "relevance":"high","summary":"...","why_different":"..."},
                            ...]},
    "C-002": {...}, ...}
   ```
3. Read `.evidraft/patent/invention_disclosure.md` if present (else mark `spec_support_available = False`).
4. Read `.evidraft/code/method_to_code.md` if present (else mark `code_support_available = False`).

## Mint prior-art ids

If the bullet line in `prior_art_map.md` does not already carry a stable id, mint one deterministically: walk candidates in source order, walk their `### Patent prior art` bullets first then `### Academic prior art` bullets in source order, assign `pa_001`, `pa_002`, … globally. Record the mapping `(file_offset → pa_id)` so a second run on the same map produces identical ids.

If the bullet already carries an id (e.g. the line begins `- [pa_017] US-...`), adopt it verbatim and skip minting for that bullet.

## Map candidates to claims

`claims_parsed.json` does not declare which candidate each claim belongs to. Resolve via either (a) a `candidate_id` field on the claim if `claim-parser` supplied one, or (b) the natural ordering: claim `c1` belongs to the first candidate's first independent claim; subsequent claims attach to the same candidate until a new independent claim starts a new candidate. Record `claims_covered` per candidate exactly as resolved.

**Handoff.** Setup yields the in-memory structures consumed by [procedure-walk-and-support.md](procedure-walk-and-support.md).
