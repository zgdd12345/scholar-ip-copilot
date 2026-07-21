# Stage 2 — Retrieve

**Preconditions.** `plan.yaml` exists and validates.

**Procedure.**

1. For every sub-query, invoke `capability:scholar-search` with `query`, `year_range`, `venue`, `top_k=breadth*5`, once per provider in `plan.yaml.providers`. The skill issues the appropriate `WebFetch` against arXiv / S2 / OpenAlex (URL templates verbatim in the skill), parses the response, dedups, and emits rows conforming to the `candidates.jsonl` schema below. Record `provider` as the `source` field of each row.
2. For `depth > 1`: for each retained paper, fan out via the skill's per-paper detail URLs to enumerate references (S2 `/paper/<id>?fields=references`) and citations (S2 `/paper/<id>?fields=citations` or OpenAlex `/works?filter=cites:<id>`) — one hop per depth level beyond 1. Cap total candidates at `breadth * 50` to prevent runaway expansion.
3. Deduplicate by DOI, then by (normalised title, first author, year). Keep the most authoritative `source` per dedup cluster, but preserve all variants under `aliases`.
4. Append rows to `candidates.jsonl`. Never blend metadata from two providers into one row without explicit reconciliation (see orchestrator constraints).

**Concurrency.** The `sub_query × provider` matrix in step 1 is fully independent — fan out concurrently with `min(breadth, lit_deep.max_concurrency)` in flight (default `lit_deep.max_concurrency: 8`, configurable in `.evidraft/project.yaml`). The `depth > 1` hops in step 2 are serial (they depend on step 1's retained set), but each hop's per-paper fan-out is again independent. Dedup (step 3) is single-threaded.

**Artefact schema — `candidates.jsonl`** (one JSON object per line):

```json
{"id":"cand_NNNN","title":"...","abstract":"...","venue":"...","year":2023,
 "authors":["..."],"doi":"...",
 "arxiv_id":"2308.09534",                     // optional convenience field; null when not arXiv
 "source":"arxiv|semantic-scholar|openalex|local-bib|local-pdf|llm-seed-unverified|superseded",
 "provider_id":"arxiv:2401.01234","sub_query_ids":["q1","q3"],
 "depth":0,"aliases":[{"source":"openalex","provider_id":"W..."}],
 "run_id":"...","verified":true,"confidence":"high|medium|low",
 "verify_note":"how the row's metadata was verified"}
```

**Cross-sub-query dedup** is mandatory: a candidate retrieved by both `q1` and `q3` collapses to ONE row whose `sub_query_ids` is the union `["q1", "q3"]`. The dedup key is DOI first, then (normalised title, first-author surname, year). Never emit two rows that would both `cite` the same paper.

The `source` enum carries provenance, not config: in addition to the web-retrieval providers, it accepts `local-bib` / `local-pdf` (when MCP/network unavailable; see [failure-modes.md](failure-modes.md)), `llm-seed-unverified` (initial LLM seed before WebSearch verification — every such row MUST have `verified: false`), and `superseded` (audit trail for rows replaced by a later, verified row).

**Failure mode.** Network/provider degradation falls back to local `.evidraft/literature/references.bib` and `references/` / `papers/` PDFs — full rules in [failure-modes.md](failure-modes.md). Note: `local-bib` / `local-pdf` only ever appear as `source:` on `candidates.jsonl` rows; they are **not** legal values for `project.yaml.lit_deep.providers` (the config enum is web-retrieval providers only).

**Handoff.** Stage 3 reads `candidates.jsonl` and `plan.yaml.inclusion_keywords` / `exclusion_keywords`.
