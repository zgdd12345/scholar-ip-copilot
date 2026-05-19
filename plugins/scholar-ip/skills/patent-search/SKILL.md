---
id: patent-search
title: "Patent search: Google Patents / USPTO PatentsView / EPO OPS via WebFetch"
kind: skill
phase: patent
description: >
  Retrieve prior-art candidates from Google Patents, USPTO PatentsView, and
  EPO OPS using `WebSearch` + `WebFetch`; extract patent_no, title, abstract,
  assignee, dates, claims, and CPC classes; dedup, rate-limit, cache, and
  append rows to `prior_art_map.md` plus `type=patent` evidence records. Use
  when fetching patent metadata, resolving a patent number, building the
  prior-art map, or running `/scholar:patent-scout` or
  `/scholar:patent-prior-art`. Advisory only — not a freedom-to-operate
  analysis.
triggers:
  - "/scholar:patent-scout"
  - "/scholar:patent-prior-art"
  - "fetching patent metadata"
  - "resolving patent number"
  - "building prior-art map"
provides:
  - patent-search-url-templates
  - patent-detail-url-templates
  - patent-row-shape
  - rate-limit-policy
  - cache-convention
  - ethics-disclaimer
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
  - "Bash:mkdir*"
hooks: [evidence-consistency, sensitive-file-guard]
references:
  - doc: ../patent-disclosure/SKILL.md
  - doc: ../patent-claims/SKILL.md
  - doc: ../evidence-check/SKILL.md
  - doc: ../../commands/patent-scout.md
  - doc: ../../commands/patent-prior-art.md
  - url: "https://patents.google.com/"
  - url: "https://search.patentsview.org/docs/"
  - url: "https://developers.epo.org/ops-v3-2"
---

# patent-search

## When to use

Load whenever a command needs to **retrieve patent metadata or build a prior-art set** from public patent databases:

- `/scholar:patent-scout` — surface candidate inventions with adjacent prior art.
- `/scholar:patent-prior-art` — build `prior_art_map.md` and feed `claim_chart.md`.

## Ethics block — read every time

> Prior-art retrieval is **advisory**, not a freedom-to-operate (FTO) analysis. Absence of search hits means **"not found by this query"**, not **"does not exist"**. The decision to file, license, or design around a patent rests with a qualified attorney. This skill produces a search artefact; it never declares a candidate "patentable" or "non-infringing".

Mirror this disclaimer at the top of every `prior_art_map.md` section the skill emits.

## Shared cache + run_id convention

- Cache root: `.evidraft/literature/.cache/<provider>/<sha1(url)>.json` (yes — the **literature** cache root is the shared retrieval cache; provider subdirs `google-patents/`, `patentsview/`, `epo-ops/` keep them separate from arXiv / S2 / OpenAlex).
- TTL: 14 days, delete-on-staleness (same rule as `scholar-search`).
- Every row carries `run_id` from the calling command's `plan.yaml`.
- Cache content: parsed JSON + `_fetched_at` (UTC iso) + `_url` (canonical).
- The `.gitignore` flag is the same as for `scholar-search` — `.cache/` form may need adding (flagged in the migration report).

## Inputs

- a free-text query, a candidate-invention description, or one of: `<patent_no>` (e.g. `US-1234567-B2`, `EP1234567A1`), `cpc:<class>`, `assignee:<name>`
- optional filters: date range, jurisdiction (US / EP / WO / CN / JP), `top_k`
- the calling command's `run_id`

## Outputs

- rows appended to `.evidraft/patent/prior_art_map.md` (one H2 / H3 per candidate)
- `type=patent` records appended to `.evidraft/evidence/evidence.jsonl`:

  ```json
  {"id":"ev_NNNN","type":"patent","source":"google-patents|patentsview|epo-ops",
   "claim":"<one sentence describing what the patent teaches that overlaps>",
   "support":"<patent_no, paragraph / claim / figure>","citation_key":"<patent_no>",
   "file_path":null,"line_range":null,"confidence":"medium","verified":false,
   "run_id":"..."}
  ```

## URL templates (verbatim)

These are the only URLs this skill issues via `WebFetch` / `WebSearch`.

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

## Procedure

### 1. Build the URL

Pick the provider per the routing table. URL-encode the query. For PatentsView, JSON-encode the `q` argument and then URL-encode the whole.

### 2. Check the cache

Same recipe as `scholar-search`: `sha1` of the canonical URL; look up `.evidraft/literature/.cache/<provider>/<sha1>.json`; delete if older than 14 days.

### 3. Fetch

Call `WebFetch`. For Google Patents (HTML), the prompt asks the host to extract the relevant blocks (result list with patent number + title + assignee + date for search pages; abstract + claims + CPC for detail pages). For PatentsView (JSON) and EPO OPS (XML), capture the body and parse.

Respect the per-provider sleep budget.

### 4. Parse the response shape

Per provider, extract exactly:

| Field | Google Patents | PatentsView | EPO OPS |
|---|---|---|---|
| `patent_no` | header (`<h1>` on detail; result card on search) | `patent_number` | `<document-id>` |
| `title` | `<h1>` / search snippet | `patent_title` | `<invention-title>` |
| `abstract` | `<section itemprop="abstract">` | `patent_abstract` | `<abstract>` |
| `assignee` | `<dd itemprop="assigneeOriginal">` | `assignees[*].assignee_organization` | `<applicants><applicant>` |
| `filing_date` | `<dd itemprop="filingDate">` | `patent_date` (publication date — filing is a separate field) | `<application-reference><date>` |
| `publication_date` | `<dd itemprop="publicationDate">` | `patent_date` | `<publication-reference><date>` |
| `claims` (detail) | `<section itemprop="claims">` | `_claims` query needed (separate endpoint) | `<claims>` (separate endpoint) |
| `cpc_classes` | `<span itemprop="Code">` | `cpcs[*].cpc_subgroup_id` | `<classifications-cpc>` |

### 5. Dedup recipe

After all providers respond:

1. **By normalised patent number** — group rows sharing the same `<jurisdiction>-<number>-<kind>` after stripping spaces / dashes (`US 1,234,567 B2` -> `US1234567B2`).
2. **By (normalised title, first-assignee, filing year)** for rows without a normalisable number.
3. Keep the row from the primary provider per the routing table; demote others to `aliases` (the row schema mirrors `scholar-search`'s alias convention).
4. Never merge field values across providers — record one provider's view as the row.

### 6. Write the prior-art map

Append a section to `.evidraft/patent/prior_art_map.md` per candidate invention. Always lead with the ethics disclaimer (copy from the block above). Then:

```
## C-001 <candidate name>

> Advisory prior-art search; not an FTO analysis. Absence of hits = "not
> found by this query", not "does not exist". Confirm with counsel.

### Patent prior art
- <patent_no> (<assignee>, <filing_date>) — relevance: <high|med|low>
  - summary: <one sentence>
  - what overlaps: <one sentence>
  - why-different: <one sentence>
  - evidence_id: <ev_NNNN>
  - source: <google-patents|patentsview|epo-ops>

### Academic prior art (from scholar-search)
- ...

### Notes / gaps
- ...
```

### 7. Append evidence records

For each prior-art row, append a `type=patent` record to `.evidraft/evidence/evidence.jsonl`. The `support` field cites the paragraph / claim number / figure of the patent (e.g., `"para. [0034] of US1234567B2"`), never a bare patent number alone.

## Quality checklist

- [ ] Every section in `prior_art_map.md` starts with the ethics disclaimer.
- [ ] Every emitted row carries `run_id` and `source`.
- [ ] Cache file written for every successful WebFetch.
- [ ] No fields merged across providers (use `aliases`).
- [ ] Rate-limit sleeps respected per provider.
- [ ] `EPO_OPS_KEY` read from env if set; never inlined; skipped cleanly if unset.
- [ ] Patent numbers normalised (uppercase, no spaces / dashes).
- [ ] Every evidence record's `support` cites a paragraph / claim / figure.

## Anti-patterns

- Claiming novelty because the search returned zero hits — that means "not found", not "does not exist". Always include the ethics disclaimer.
- Declaring a candidate "patentable" or "non-infringing". This skill writes prior art; the attorney writes verdicts.
- Hammering Google Patents faster than 1 req/sec or scraping > 50 result pages — both risk a polite-block from the host.
- Inlining `EPO_OPS_KEY` in a URL or shell argument; always read from env.
- Merging two providers' field values into one row (use `aliases`).
- Treating a 429 as "no results" — that is a transient failure; retry per the policy above.
- Skipping the cache check (re-fetching the same patent number across runs wastes the polite-pool budget).
- Reading a patent PDF behind a paywall — public patent databases already publish the metadata; use them, not the paywall.
