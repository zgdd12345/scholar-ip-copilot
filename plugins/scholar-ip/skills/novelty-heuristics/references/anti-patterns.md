# Anti-patterns

- **Producing a final "this claim is novel" verdict.** The skill only produces `verdict_hint`, never a yes/no. A yes/no would be a legal opinion.
- **Scoring `identical` without a verbatim quote.** `identical` is reserved for verbatim or near-verbatim matches; without a quote in `overlap_passage` the highest allowable score is `high`. See [output-schema.md](output-schema.md) Enums.
- **Treating an empty prior-art set as evidence of novelty.** Empty means the prior-art search is incomplete; `CLAIM_FULLY_NOVEL_HEURISTIC` carries the disclaimer in its `advisory_note` and `ELEMENT_NO_PRIOR_ART_FOUND` fires per element to keep this honest. See [rule-taxonomy.md](rule-taxonomy.md).
- **Re-scoring overlap rows that `claim-chart-builder` already produced** unless the user explicitly requests a re-run. When `claim_chart-<ts>.json` is fresh, reuse — do not duplicate work or risk drift between the chart and the audit.
- **Editing the claim text or the prior-art map.** Findings only. The `claim-drafter` agent and the attorney decide on amendments.
- **Inventing prior-art entries or overlap passages.** Every `prior_art_id`, `prior_art_title`, and `overlap_passage` must trace to a real entry in `prior_art_map.md` (or its publicly readable source the user populated). No hallucinated citations.
- **Promoting a `verdict_hint` to legal weight.** The labels are attorney triage; surfacing them as patentability conclusions in chat, in the `patent_review_report.md`, or anywhere else violates the advisory-only framing of this skill.
- **Skipping the `findings.json` write because nothing fired.** The empty file is the audit-trail proof that the audit ran; emit it with `findings: []`, `summary.advisory: true`, and zero severity counts.
