# Provider matrix — URLs, routing, rate limits

Three providers. Use the URL templates verbatim; route per the input form; respect the per-provider rate-limit policy.

## URL templates

### Google Patents (no public API — HTML scraping politely)

- Search:
  ```
  https://patents.google.com/?q=<query>&num=<top_k>
  ```
- Per-patent detail:
  ```
  https://patents.google.com/patent/<patent_no>
  ```
- Response is HTML. Extract per result card: patent number, title, assignee, filing/publication date, snippet. Detail page exposes the full abstract, claims, CPC classes, and figure list.
- Polite use: identify the user-agent (the host adapter handles this); 1 req/sec; never scrape > 50 result pages in a single run.

### USPTO PatentsView (JSON API, no auth required)

- Search:
  ```
  https://search.patentsview.org/api/v1/patent/?q=<json_query>
  ```
- The `q` value is a URL-encoded JSON object. Minimal DSL:
  - `{"_text_any":{"patent_abstract":"<query>"}}` — full-text "any of these words"
  - `{"_and":[{"_gte":{"patent_date":"2020-01-01"}},{"_text_any":{"patent_title":"<term>"}}]}` — date filter + title term
  - `{"_eq":{"assignee_organization":"<name>"}}` — exact assignee
- Append a `f` (fields) parameter to select returned columns; default fields are sparse.
- Response is JSON. Extract per `patents[i]`: `patent_number`, `patent_title`, `patent_abstract`, `patent_date`, `assignees[*].assignee_organization`, `cpcs[*].cpc_subgroup_id`.

### EPO OPS (OAuth — v0.3+ optional)

- Search:
  ```
  https://ops.epo.org/3.2/rest-services/published-data/search?Range=1-<top_k>&CQL=<query>
  ```
- OAuth client credentials required: `EPO_OPS_KEY` and `EPO_OPS_SECRET` (env). Token endpoint: `https://ops.epo.org/3.2/auth/accesstoken`.
- Flag as **v0.3+ optional**: when `EPO_OPS_KEY` is unset, log "EPO OPS skipped (no key)" and continue with Google Patents + PatentsView only. Never inline the key — read from env.
- Response is XML (Atom-like). Per `<ops:biblio-search><ops:search-result><ops:publication-reference>`: extract `<document-id>` (patent_no), `<invention-title>`, `<applicants><applicant>` (assignee), `<publication-reference><document-id><date>` (publication date), `<classifications-cpc>` (CPC classes), `<abstract>` when present.

## Provider routing

| Input form | Primary | Fallback |
|---|---|---|
| `<patent_no>` (US/USA*) | Google Patents detail | PatentsView by `patent_number` |
| `<patent_no>` (EP*) | Google Patents detail | EPO OPS (if `EPO_OPS_KEY`) |
| free-text invention | Google Patents search **and** PatentsView search (union, dedup); EPO OPS if key present | n/a |
| `cpc:<class>` | PatentsView (`_eq` on `cpc_subgroup_id`) | Google Patents (`?q=CPC:<class>`) |
| `assignee:<name>` | PatentsView (`_eq` on `assignee_organization`) | Google Patents (`?q=assignee:<name>`) |

## Rate-limit policy

| Provider | Limit | Hard rule |
|---|---|---|
| Google Patents | ~1 req/sec polite (no public quota) | Serialise; sleep 1 s between calls. Cap at 50 result pages per run. User-agent identifies the caller. |
| PatentsView | community rate (~45 req/min when fair) | Sleep 1.5 s between calls; max 3 retries on 429. |
| EPO OPS | 4 req/sec authenticated | Sleep 300 ms; respect `X-RateLimit-Remaining` header. |

On HTTP 429:

1. Sleep `min(60, 2 ** attempt)` seconds.
2. Retry up to 3 times.
3. After three failures, record the row with `confidence="low"`, `verify_note="rate-limited by <provider>"`, and continue.

Never run two providers in parallel within one sub-query.
