---
id: scholar-search
title: "Scholar search: arXiv / Semantic Scholar / OpenAlex retrieval via WebSearch + WebFetch"
kind: skill
phase: paper
description: >
  Query arXiv, Semantic Scholar, and OpenAlex with the built-in `WebSearch`
  and `WebFetch` tools to fetch paper metadata; dedup, rate-limit, cache,
  and emit rows that conform to the `candidates.jsonl` schema declared in
  `commands/deepresearch.md`. Use when fetching paper metadata, resolving
  an arXiv id or DOI, building a literature matrix from a topic, or running
  `/scholar:paper-lit` or `/scholar:deepresearch`.
triggers:
  - "/scholar:paper-lit"
  - "/scholar:deepresearch"
  - "fetching paper metadata"
  - "resolving arxiv id"
  - "resolving doi"
  - "building literature matrix from a topic"
provides:
  - paper-search-url-templates
  - paper-detail-url-templates
  - provider-routing-rules
  - rate-limit-policy
  - cache-convention
  - candidate-row-shape
  - dedup-recipe
allowed_tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - WebSearch
  - WebFetch
  - "Bash:sha1sum*"
  - "Bash:shasum*"
  - "Bash:ls*"
  - "Bash:mkdir*"
hooks: [citation-guard, evidence-consistency, sensitive-file-guard]
references:
  - doc: ../literature-review/SKILL.md
  - doc: ../deep-literature-review/SKILL.md
  - doc: ../evidence-check/SKILL.md
  - doc: ../../commands/paper-lit.md
  - doc: ../../commands/deepresearch.md
  - url: "https://info.arxiv.org/help/api/user-manual.html"
  - url: "https://api.semanticscholar.org/api-docs/"
  - url: "https://docs.openalex.org/"
---

# scholar-search

## When to use

Load whenever a command needs to **retrieve paper metadata or abstracts** from the open web:

- `/scholar:paper-lit` building or expanding `.evidraft/literature/`
- `/scholar:deepresearch` Stage 2 (Retrieve) and Stage 4 lineage hops
- any time the user pastes an arXiv id, DOI, or OpenAlex Work id and asks "what is this?"

If the calling command provides a `run_id` (from its `plan.yaml`), every row written by this skill MUST carry it.

## Shared cache + run_id convention

All retrieval skills share one cache convention. **Read this before every WebFetch call.**

- Cache root: `.evidraft/literature/.cache/<provider>/<sha1(url)>.json`
- TTL: 14 days. Stale entries are **deleted on encounter**, not refreshed in the background.
- The host's `.gitignore` covers `**/.evidraft/cache/`; the dotted `.cache/` form may not be covered — flagged separately in the migration report.
- Every retrieval row records `run_id` (from the calling command's `plan.yaml`).
- Path-construction recipe:
  1. canonicalise the URL (sort query params alphabetically, lowercase scheme + host),
  2. `sha1` it (`shasum -a 1 <<< "$url"` or `sha1sum`),
  3. write the parsed JSON response to `.evidraft/literature/.cache/<provider>/<sha1>.json` with two extra top-level keys: `_fetched_at` (UTC iso) and `_url` (the canonical URL).

## Inputs

- a free-text query, or one of: `arxiv:<id>`, `doi:<id>`, `openalex:<W...>`, `s2:<paperId>`
- optional filters: year range (`from`, `to`), venue allow-list, language, `top_k`
- the calling command's `run_id`

## Outputs

- A list of dicts conforming to the `candidates.jsonl` row schema in `commands/deepresearch.md` Stage 2:

  ```json
  {"id":"cand_NNNN","title":"...","abstract":"...","venue":"...","year":2023,
   "authors":["..."],"doi":"...","source":"arxiv|semantic-scholar|openalex",
   "provider_id":"arxiv:2401.01234","sub_query_ids":["q1","q3"],
   "depth":0,"aliases":[{"source":"openalex","provider_id":"W..."}],
   "run_id":"...","verified":false,"confidence":"medium","verify_note":""}
  ```

- Cache files under `.evidraft/literature/.cache/<provider>/<sha1>.json`.
- (`/scholar:paper-lit` callers) BibTeX + matrix rows + evidence records derived from the candidate list — built by `literature-review`, not this skill.

## How to navigate this skill

Load only the reference for the layer you are in:

| Layer | Reference | Owns |
|---|---|---|
| Provider details (URLs / routing / rate limits) | [provider-matrix.md](references/provider-matrix.md) | per-provider URL templates (arXiv / S2 / OpenAlex), input → primary-provider routing table, soft + hard rate-limit policy, 429 retry/backoff rules |
| Retrieval procedure (6 steps) | [procedure.md](references/procedure.md) | path A vs. B selection, build URL/query → cache check → fetch → parse → write cache + emit rows → dedup recipe |
| Anti-patterns | [anti-patterns.md](references/anti-patterns.md) | what NOT to do |

## Field-completeness rules

- If `abstract` is missing on a candidate the screener will need, retry with **S2 detail** (`/paper/<id>?fields=abstract`) before declaring `abstract_unavailable`.
- If `authors` is empty, retry with **OpenAlex detail** (`/works/<id>`); if still empty, the row is suspect — mark `confidence="low"`.
- Never invent: a missing `venue` stays empty, a missing year is `null`. The `citation-guard` hook will catch any downstream claim that depends on a fabricated field.

## Resolving `arxiv:<id>` and `doi:<id>` shortcuts

- `arxiv:2401.01234` -> `https://export.arxiv.org/abs/2401.01234`. Parse the Atom entry inside.
- `doi:10.1000/xyz` -> `https://api.semanticscholar.org/graph/v1/paper/DOI:10.1000/xyz?fields=...`. On 404, try OpenAlex: `https://api.openalex.org/works/doi:10.1000/xyz`.

## Quality checklist

- [ ] Every emitted row carries `run_id`.
- [ ] Cache file written for every successful WebFetch.
- [ ] No two providers' fields merged into one row.
- [ ] Dedup happened after retrieval, not during.
- [ ] Rate-limit sleeps respected per provider.
- [ ] `abstract_inverted_index` correctly reconstructed for OpenAlex rows.
- [ ] DOIs normalised (lowercase, no `https://doi.org/` prefix).
