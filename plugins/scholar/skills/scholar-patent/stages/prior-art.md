# workflow:patent.prior-art

Build a prior-art map for each candidate invention. **Online retrieval uses the host-native `WebSearch` + `WebFetch` tools driven by `../../.evidraft-private/capabilities/research/patent-search/spec.md` (Google Patents / USPTO PatentsView / EPO OPS); if the host has no network, operate on user-supplied PDFs / patent numbers / BibTeX.**

This action is best effort. Use every verifiable candidate and prior-art source that
is available, and record missing candidates, full text, network access, or source
metadata in each candidate's `Notes / gaps`. Missing inputs never justify invented
prior art and do not block a partial map. Delegate retrieval and critique
adaptively according to source diversity and risk, with no fixed worker count,
waves, or retry count.

## Steps

1. **Collect.** Gather inputs:
   - `invention_candidates.md` (the targets),
   - `references.bib` (academic prior art),
   - user-supplied patent numbers / pdfs / urls,
   - patent rows fetched via `../../.evidraft-private/capabilities/research/patent-search/spec.md` (URL templates, rate-limit policy, cache, and ethics disclaimer live in the skill),
   - academic rows fetched via `../../.evidraft-private/capabilities/research/scholar-search/spec.md` for any adjacent papers.
2. **Per-candidate map.** Use the `literature-reviewer` subagent to summarise and contrast each academic-prior-art row, and the `patent-engineer` subagent to summarise each patent-prior-art row in attorney-readable language. For each candidate, write a section in `prior_art_map.md`:
   ```
   ## C-001 <name>
   ### Patent prior art
   - US-1234567-B2 (assignee, date) — relevance: <high/med/low>, summary, why-different
   ### Academic prior art
   - smith2021methodx — relevance, summary, why-different
   ### Notes / gaps
   ```
3. **Claim chart skeleton.** Update `.evidraft/patent/claim_chart.md`:
   | Claim element | Specification support | Code support | Prior art overlap | Risk | Suggested revision |
   - Pre-populate one row per high-level element of the proposed claim (placeholders are fine; `workflow:patent.claims` will fill them).
4. **Risk lines.** Use the `novelty-critic` subagent to challenge each `Suggested revision` so the chart is not optimistic about distance from prior art. Mark `high` on any element where prior art looks very close; suggest a revision angle.

## Constraints

- Do not declare a candidate "patentable" or "non-patentable" — risk levels only.
- For each prior-art reference, record the source (patent number, doi, url) so reviewers can verify.
- Citation discipline applies: claims of novelty here also need evidence.

## Done criteria

- `prior_art_map.md` has one section per candidate from `invention_candidates.md`.
- `claim_chart.md` has at least one row per candidate.
- Chat output recommends `workflow:patent.disclosure` next.
- Status is `complete`, `complete_with_gaps` when coverage or verification remains
  incomplete, or `blocked` only when workspace safety prevents every useful output.
