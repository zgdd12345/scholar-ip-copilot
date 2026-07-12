# Stage 6 — Synthesise + audit

**Preconditions.** `critique/<cluster-id>.md` exists for every cluster.

**Procedure.** Dispatch `literature-reviewer` for drafting, then `evidence-auditor` for the citation audit.

1. Draft `related_work.draft.md` — one paragraph per cluster (or per tight pair of clusters when a single family would otherwise become a wall of citations).
2. Every paragraph must cite ≥ 2 `citation_key`s and end with a contrast sentence that names our angle, backed by at least one `evidence_id`. `policy:evidence-integrity` and `policy:evidence-integrity` block silently otherwise.
3. Append every synthesised position to `.evidraft/evidence/evidence.jsonl` as `type=note` records with `verified=false` (the auditor flips them later).
4. **Citation-audit pass (mandatory).** Walk every claim in `related_work.draft.md`. For each:
   - Resolve to a `citation_key` (must exist in `references.bib`; when the draft only has a free-text claim, invoke `capability:scholar-search` with the free-text title to discover the canonical paper and then `capability:bib-manager` to land the entry under the right key).
   - Resolve to ≥ 1 `evidence_id` (must exist in `evidence.jsonl`).
   - Record the resolution in `citation_audit.json`. If any claim fails to resolve, the audit fails — do **not** proceed; the orchestrator must surface the failing claims and stop.

**Citation audit rules.**

For every claim in `related_work.draft.md`:

1. Resolve to one or more `citation_key`s — each must already exist in `.evidraft/literature/references.bib`. For free-text matches, use the `scholar-search` skill's resolution recipe (query a candidate title against arXiv/Semantic Scholar/OpenAlex via `WebSearch` + `WebFetch`, then map to an existing BibTeX entry); otherwise look up by hand.
2. Resolve to one or more `evidence_id`s — each must already exist in `.evidraft/evidence/evidence.jsonl`.
3. Append a row to `citation_audit.json.claims[]` with `paragraph, claim, citation_keys, evidence_ids, status, resolver, confidence`.
4. If `status=failed` for any claim, the run does not complete. Surface the failing claims and tell the user which stage to re-run.

Strong-claim verbs in the draft (SOTA, novel, first, outperform, significant, superior, …) require a `\cite{}` or `ev_NNNN` within 30 chars. Run the declared strong-claim scan and reject failing text before write.

**Artefact schema — `citation_audit.json`.**

```json
{
  "run_id": "...",
  "total_claims": <int>,
  "resolved": <int>,
  "failed": <int>,
  "claims": [
    {"paragraph": 1, "claim": "...", "citation_keys": ["smith2023foo"],
     "evidence_ids": ["ev_0123"], "status": "resolved",
     "resolver": "resolve_citation | manual", "confidence": 0.91}
  ]
}
```

**Failure mode.** If `capability:scholar-search` cannot resolve a free-text claim (network down, all providers 429), fall back to manual lookup against `references.bib` + `evidence.jsonl`. If a claim still cannot be resolved, leave the claim in the draft but flag `status: failed` and refuse to mark the run complete. Full catalog in [failure-modes.md](failure-modes.md).

**Handoff.** The draft is **not** copied into `manuscript/sections/related_work.tex` by this command — that remains the job of `workflow:paper.review`, which will consume `related_work.draft.md` as its outline.
