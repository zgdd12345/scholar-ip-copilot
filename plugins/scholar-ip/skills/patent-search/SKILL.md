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
  - doc: references/provider-matrix.md
  - doc: references/procedure.md
  - doc: references/anti-patterns.md
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

- rows appended to `.evidraft/patent/prior_art_map.md` (one H2 / H3 per candidate — section template in [procedure.md](references/procedure.md) §6)
- `type=patent` records appended to `.evidraft/evidence/evidence.jsonl`:

  ```json
  {"id":"ev_NNNN","type":"patent","source":"google-patents|patentsview|epo-ops",
   "claim":"<one sentence describing what the patent teaches that overlaps>",
   "support":"<patent_no, paragraph / claim / figure>","citation_key":"<patent_no>",
   "file_path":null,"line_range":null,"confidence":"medium","verified":false,
   "run_id":"..."}
  ```

## How to navigate this skill

Load only the reference for the layer you are in:

| Layer | Reference | Owns |
|---|---|---|
| Provider details (URLs / routing / rate limits) | [provider-matrix.md](references/provider-matrix.md) | per-provider URL templates (Google Patents / PatentsView / EPO OPS), input → primary-provider routing table, polite-use / rate-limit policy, 429 retry/backoff rules |
| Retrieval procedure (7 steps) | [procedure.md](references/procedure.md) | build URL → cache check → fetch → parse field-by-provider → dedup → write `prior_art_map.md` section template → append evidence |
| Anti-patterns | [anti-patterns.md](references/anti-patterns.md) | what NOT to do |

## Quality checklist

- [ ] Every section in `prior_art_map.md` starts with the ethics disclaimer.
- [ ] Every emitted row carries `run_id` and `source`.
- [ ] Cache file written for every successful WebFetch.
- [ ] No fields merged across providers (use `aliases`).
- [ ] Rate-limit sleeps respected per provider.
- [ ] `EPO_OPS_KEY` read from env if set; never inlined; skipped cleanly if unset.
- [ ] Patent numbers normalised (uppercase, no spaces / dashes).
- [ ] Every evidence record's `support` cites a paragraph / claim / figure.
