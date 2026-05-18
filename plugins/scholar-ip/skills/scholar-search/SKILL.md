---
id: scholar-search
title: "Scholar search: arXiv / Semantic Scholar / OpenAlex retrieval via WebSearch + WebFetch"
kind: skill
phase: paper
description: >
  Host-native retrieval recipe replacing scholar-search-mcp. Tells the LLM how
  to query arXiv, Semantic Scholar, and OpenAlex with the built-in WebSearch
  and WebFetch tools, how to dedup, rate-limit, cache, and emit rows that
  conform to the candidates.jsonl row schema declared in commands/deepresearch.md.
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

## URL templates (verbatim — do not paraphrase)

These are the only URLs this skill issues via `WebFetch` / `WebSearch`. Substitute parameters by string interpolation; URL-encode the query.

### arXiv (free, no auth)

- Search:
  ```
  https://export.arxiv.org/api/query?search_query=all:<query>&start=<start>&max_results=<top_k>&sortBy=submittedDate&sortOrder=descending
  ```
- Detail by id:
  ```
  https://export.arxiv.org/abs/<arxiv_id>
  ```
- Response is Atom XML. Extract per `<entry>`: `<title>`, `<summary>` (abstract), `<author><name>`, `<published>` (year via first 4 chars), `<arxiv:primary_category term=...>`, `<id>` (full URL — strip `https://arxiv.org/abs/` for `provider_id`), `<arxiv:doi>` when present.

### Semantic Scholar (free anon; api key optional)

- Search:
  ```
  https://api.semanticscholar.org/graph/v1/paper/search?query=<query>&limit=<top_k>&fields=title,abstract,year,venue,authors,externalIds,referenceCount,citationCount
  ```
- Detail by id (S2 paperId, DOI, or arXiv id — S2 accepts all three):
  ```
  https://api.semanticscholar.org/graph/v1/paper/<id>?fields=title,abstract,year,venue,authors,externalIds,referenceCount,citationCount,references,citations
  ```
- Response is JSON. Extract per `data[i]`: `title`, `abstract`, `year`, `venue`, `authors[*].name`, `externalIds.DOI` / `externalIds.ArXiv`, `externalIds.OpenAlex`, `paperId` (-> `provider_id`).

### OpenAlex (free, polite-pool requires a mailto)

- Search:
  ```
  https://api.openalex.org/works?search=<query>&filter=from_publication_date:<from>,to_publication_date:<to>&per-page=<top_k>
  ```
- Detail by id (OpenAlex Work id, DOI, MAG, PMID, PMCID):
  ```
  https://api.openalex.org/works/<id>
  ```
- Polite-pool: append `&mailto=<user-supplied-email>` when one is configured in `.evidraft/project.yaml`.
- Response is JSON. Extract per `results[i]`: `title`, `abstract_inverted_index` (must be **reconstructed** to a plain string — sort positions, join tokens), `publication_year`, `host_venue.display_name`, `authorships[*].author.display_name`, `doi`, `ids.openalex`.

## Provider routing rules

When the input is a direct identifier:

| Input form | Primary provider | Fallback chain |
|---|---|---|
| `arxiv:<id>` | arXiv | S2 (by `ArXiv:<id>`) -> OpenAlex (by DOI if known) |
| `doi:<id>` | Semantic Scholar | OpenAlex -> arXiv (only if the DOI corresponds to an arXiv preprint) |
| `openalex:<W...>` | OpenAlex | S2 (by OpenAlex external id) -> arXiv |
| `s2:<paperId>` | Semantic Scholar | OpenAlex -> arXiv |
| free-text topic | S2 first, then arXiv, then OpenAlex (union, dedup) | n/a |

For free-text retrieval: query **all three** providers in the order above, take the union, then dedup. Prefer arXiv for very recent (last 60 days) topics, where S2 metadata may lag.

## Rate-limit policy

| Provider | Soft limit | Hard rule |
|---|---|---|
| arXiv | ~3 req/sec | Serialise per-provider; sleep 350 ms between calls. |
| Semantic Scholar (anon) | 100 req / 5 min | Serialise; sleep 3 s between calls. With an `x-api-key`, raise to 10 req/sec. |
| OpenAlex (polite pool) | 10 req/sec | Sleep 100 ms between calls. |

On HTTP 429:

1. Sleep `min(60, 2 ** attempt)` seconds (cap at 60).
2. Retry up to **3** times total.
3. After the third 429, mark the row `verified=false`, `confidence="low"`, `verify_note="rate-limited by <provider>"` and continue. Do **not** drop the query silently.

Never run two providers' calls in parallel within a single `/scholar:deepresearch` Stage 2 sub-query; cross-provider parallelism is the orchestrator's job, this skill is per-call.

## Procedure

### Two retrieval paths

The host offers two complementary tools and the skill picks one per call:

| Path | Tool | When |
|---|---|---|
| **A. Direct API fetch** | `WebFetch` against the verbatim URL templates above | Default for known `arxiv_id` / `doi` lookups, OpenAlex queries, and any case where structured JSON / XML is preferred. Returns LLM-summarised content from the host (not raw bytes), which is acceptable for fields we extract (title / authors / abstract / venue / year). |
| **B. Domain-filtered web search** | `WebSearch` with `allowed_domains: ["arxiv.org", "openaccess.thecvf.com", ...]` | Default for free-text discovery (sub-queries like "training-time auxiliary branch dropped at inference"). Returns Google-indexed result lists with arXiv-style URLs that path A then resolves for metadata. Better recall than direct API queries that need exact keywords. |

Most real retrieve passes interleave both: B for discovery → A for metadata resolution.

### 1. Build the URL (path A) or query (path B)

Path A: pick the provider per the routing rules above. URL-encode the query (`%20` for spaces, `%22` for quotes, etc.). For OpenAlex, append `&mailto=` if the project supplies one.

Path B: form a natural-language query that includes domain-specific terminology; restrict via `allowed_domains` to keep the result list focused (arxiv.org + openaccess.thecvf.com cover most CS venues; add openreview.net for ICLR/NeurIPS workshops; add aclanthology.org for NLP).

### 2. Check the cache

Compute `sha1` of the canonical URL (path A) or the `(query, allowed_domains)` tuple (path B). If `.evidraft/literature/.cache/<provider>/<sha1>.json` exists **and** is < 14 days old (compare `_fetched_at` to now), load it instead of fetching. If stale, **delete** the file and fall through to the fetch.

### 3. Fetch

Path A: call `WebFetch` with the URL. For arXiv (XML), pass a prompt like "extract entries". For S2 / OpenAlex (JSON), pass a prompt asking the host to return the body verbatim, then parse.

Path B: call `WebSearch` with the query and `allowed_domains`. Iterate the result list; for each promising entry, queue a path-A `WebFetch` against its arxiv abs / cvf paper URL to extract metadata.

Respect the per-provider sleep budget. Treat HTTP 5xx the same as 429 (exponential backoff, max 3 retries). Path B is rate-limited by the host's WebSearch quota, not by arXiv / S2 — be conservative.

### 4. Parse the response shape

Per provider, extract exactly:

| Field | arXiv | Semantic Scholar | OpenAlex |
|---|---|---|---|
| `title` | `<entry><title>` | `title` | `title` |
| `abstract` | `<entry><summary>` | `abstract` | reconstructed from `abstract_inverted_index` |
| `year` | first 4 of `<published>` | `year` | `publication_year` |
| `venue` | `<arxiv:primary_category>` (preprint category) | `venue` | `host_venue.display_name` |
| `authors` | list of `<author><name>` | `authors[*].name` | `authorships[*].author.display_name` |
| `doi` | `<arxiv:doi>` | `externalIds.DOI` | `doi` (strip `https://doi.org/`) |
| `provider_id` | strip `https://arxiv.org/abs/` from `<id>` | `paperId` | `ids.openalex` (strip prefix) |
| `references` (detail only) | n/a (use S2) | `references[*].paperId` | `referenced_works[*]` |
| `citations` (detail only) | n/a | `citations[*].paperId` | (separate `/works?filter=cites:<id>` call) |

### 5. Write cache + emit rows

Persist the parsed response to the cache path. Then emit one `candidates.jsonl` row per result, populating:

- `id`: assign `cand_NNNN` within the calling command's namespace (the orchestrator owns the counter).
- `source` ∈ `{"arxiv", "semantic-scholar", "openalex"}`.
- `provider_id` per the table above.
- `sub_query_ids`: the originating sub-query ids from `plan.yaml`.
- `depth`: 0 for direct hits; +1 per `get_paper_references` / `get_paper_citations` hop.
- `aliases`: when the same paper is recovered from multiple providers in step 6 (dedup), the loser becomes an alias.
- `run_id`: the caller's `run_id`.
- `verified=false`, `confidence="medium"` by default. Bump to `"high"` only when ≥ 2 providers agree on title + year + first author.
- `verify_note`: empty unless a rate-limit / parse-failure / abstract-unavailable note applies.

### 6. Dedup recipe

After all providers have responded for a sub-query:

1. **By DOI** — group rows that share a non-empty normalised DOI (lowercase, strip `https://doi.org/`). Keep the row from the **primary** provider per the routing table; demote the others to `aliases`.
2. **By (normalised title, first-author surname, year)** — for rows without DOI:
   - normalise title: lowercase, strip non-alphanumerics, collapse whitespace.
   - first-author surname: last whitespace-separated token of `authors[0]`, lowercased, accent-stripped.
   - year: int.
3. When two rows from different providers collide but disagree on `year` by ≤ 1 (arXiv preprint year vs. published year), prefer the **published** year (S2/OpenAlex) and stash the preprint year in `aliases[i].year`.
4. Never **merge** field values across providers into a single row — record one provider's view as the row, others as `aliases`. (Mirrors the `deepresearch.md` constraint.)

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

## Anti-patterns

- Inventing a paper, author, year, venue, or DOI that the API did not return.
- Skipping the cache check — every fetch must consult `.evidraft/literature/.cache/<provider>/`.
- Running providers in parallel within one sub-query (race-condition on the rate-limit budget).
- Blending two providers' metadata into a single emitted row (use `aliases` instead).
- Using `WebSearch` against a publisher paywall page (Springer / Elsevier / IEEE) — they do not honour API contracts; route to S2 / OpenAlex which already aggregate the metadata.
- Treating a 429 as "no results" — that is a transient failure, not an empty set.
- Refreshing a stale cache entry without first deleting it (the convention is delete-on-staleness).
