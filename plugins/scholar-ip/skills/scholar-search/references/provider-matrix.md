# Provider matrix — URL templates, routing, rate limits

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
