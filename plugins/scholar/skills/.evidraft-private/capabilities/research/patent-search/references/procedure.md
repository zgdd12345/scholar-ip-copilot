# Procedure — 7 steps

## 1. Build the URL

Pick the provider per the routing table in [provider-matrix.md](provider-matrix.md). URL-encode the query. For PatentsView, JSON-encode the `q` argument and then URL-encode the whole.

## 2. Check the cache

Same recipe as `scholar-search`: `sha1` of the canonical URL; look up `.evidraft/literature/.cache/<provider>/<sha1>.json`; delete if older than 14 days.

## 3. Fetch

Call `WebFetch`. For Google Patents (HTML), the prompt asks the host to extract the relevant blocks (result list with patent number + title + assignee + date for search pages; abstract + claims + CPC for detail pages). For PatentsView (JSON) and EPO OPS (XML), capture the body and parse.

Respect the per-provider sleep budget (see [provider-matrix.md](provider-matrix.md) §rate-limit-policy).

## 4. Parse the response shape

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

## 5. Dedup recipe

After all providers respond:

1. **By normalised patent number** — group rows sharing the same `<jurisdiction>-<number>-<kind>` after stripping spaces / dashes (`US 1,234,567 B2` -> `US1234567B2`).
2. **By (normalised title, first-assignee, filing year)** for rows without a normalisable number.
3. Keep the row from the primary provider per the routing table; demote others to `aliases` (the row schema mirrors `scholar-search`'s alias convention).
4. Never merge field values across providers — record one provider's view as the row.

## 6. Write the prior-art map

Append a section to `.evidraft/patent/prior_art_map.md` per candidate invention. Always lead with the ethics disclaimer (copy from the block in capability specification). Then:

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

## 7. Append evidence records

For each prior-art row, append a `type=patent` record to `.evidraft/evidence/evidence.jsonl`. The `support` field cites the paragraph / claim number / figure of the patent (e.g., `"para. [0034] of US1234567B2"`), never a bare patent number alone.
