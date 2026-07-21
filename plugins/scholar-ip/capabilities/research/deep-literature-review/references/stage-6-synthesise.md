# Stage 6 - Synthesise and optionally audit

**Preconditions.** `clusters.yaml` exists. Mode full also consumes available selected
critique files; mode fast has no critique precondition.

1. Draft `related_work.draft.md` from verified candidate fields, clusters, readable
   source material, and full-mode critiques when enabled.
2. Keep unsupported or abstract-only coverage explicit. Downgrade or remove strong
   claims that lack adequate support; never invent a citation or evidence id.
3. Run the citation audit when its store and audit capability are available. Record each
   claim's citation keys, evidence ids, status, resolver, and confidence.
4. A missing or failed citation audit preserves the useful draft. Add an `## Evidence
   boundary` section naming unresolved claims and recovery actions and return
   `complete_with_gaps`.

```json
{
  "run_id": "...",
  "total_claims": 0,
  "resolved": 0,
  "failed": 0,
  "claims": []
}
```

When the audit cannot resolve a free-text claim, fall back to existing BibTeX and
evidence records. If resolution still fails, retain the finding as failed, weaken or
remove the unsupported draft wording, and report the boundary. The audit is a check on
the draft, not permission to fabricate or a reason to discard useful supported prose.

**Handoff.** `workflow:paper.review` may consume the draft; this stage does not write
manuscript sections.
