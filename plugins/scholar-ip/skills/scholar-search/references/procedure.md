# Retrieval procedure

## Two retrieval paths

The host offers two complementary tools and the skill picks one per call:

| Path | Tool | When |
|---|---|---|
| **A. Direct API fetch** | `WebFetch` against the verbatim URL templates in [provider-matrix.md](provider-matrix.md) | Default for known `arxiv_id` / `doi` lookups, OpenAlex queries, and any case where structured JSON / XML is preferred. Returns LLM-summarised content from the host (not raw bytes), which is acceptable for fields we extract (title / authors / abstract / venue / year). |
| **B. Domain-filtered web search** | `WebSearch` with `allowed_domains: ["arxiv.org", "openaccess.thecvf.com", ...]` | Default for free-text discovery (sub-queries like "training-time auxiliary branch dropped at inference"). Returns Google-indexed result lists with arXiv-style URLs that path A then resolves for metadata. Better recall than direct API queries that need exact keywords. |

Most real retrieve passes interleave both: B for discovery → A for metadata resolution.

## 1. Build the URL (path A) or query (path B)

Path A: pick the provider per the routing rules in [provider-matrix.md](provider-matrix.md). URL-encode the query (`%20` for spaces, `%22` for quotes, etc.). For OpenAlex, append `&mailto=` if the project supplies one.

Path B: form a natural-language query that includes domain-specific terminology; restrict via `allowed_domains` to keep the result list focused (arxiv.org + openaccess.thecvf.com cover most CS venues; add openreview.net for ICLR/NeurIPS workshops; add aclanthology.org for NLP).

## 2. Check the cache

Compute `sha1` of the canonical URL (path A) or the `(query, allowed_domains)` tuple (path B). If `.evidraft/literature/.cache/<provider>/<sha1>.json` exists **and** is < 14 days old (compare `_fetched_at` to now), load it instead of fetching. If stale, **delete** the file and fall through to the fetch.

## 3. Fetch

Path A: call `WebFetch` with the URL. For arXiv (XML), pass a prompt like "extract entries". For S2 / OpenAlex (JSON), pass a prompt asking the host to return the body verbatim, then parse.

Path B: call `WebSearch` with the query and `allowed_domains`. Iterate the result list; for each promising entry, queue a path-A `WebFetch` against its arxiv abs / cvf paper URL to extract metadata.

Respect the per-provider sleep budget (see [provider-matrix.md](provider-matrix.md) §Rate-limit policy). Treat HTTP 5xx the same as 429 (exponential backoff, max 3 retries). Path B is rate-limited by the host's WebSearch quota, not by arXiv / S2 — be conservative.

## 4. Parse the response shape

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

## 5. Write cache + emit rows

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

## 6. Dedup recipe

After all providers have responded for a sub-query:

1. **By DOI** — group rows that share a non-empty normalised DOI (lowercase, strip `https://doi.org/`). Keep the row from the **primary** provider per the routing table; demote the others to `aliases`.
2. **By (normalised title, first-author surname, year)** — for rows without DOI:
   - normalise title: lowercase, strip non-alphanumerics, collapse whitespace.
   - first-author surname: last whitespace-separated token of `authors[0]`, lowercased, accent-stripped.
   - year: int.
3. When two rows from different providers collide but disagree on `year` by ≤ 1 (arXiv preprint year vs. published year), prefer the **published** year (S2/OpenAlex) and stash the preprint year in `aliases[i].year`.
4. Never **merge** field values across providers into a single row — record one provider's view as the row, others as `aliases`. (Mirrors the `deepresearch.md` constraint.)
