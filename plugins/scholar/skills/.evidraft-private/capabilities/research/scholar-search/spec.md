---
id: scholar-search
title: "Scholar search: arXiv / Semantic Scholar / OpenAlex retrieval via WebSearch + WebFetch"
kind: skill
phase: paper
description: >
  Query arXiv, Semantic Scholar, and OpenAlex with the built-in `WebSearch`
  and `WebFetch` tools to fetch paper metadata; dedup, rate-limit, cache,
  and emit rows that conform to the `candidates.jsonl` schema declared in
  `workflow:research.deep`. Use when fetching paper metadata, resolving
  an arXiv id or DOI, building a literature matrix from a topic, or running
  `workflow:paper.lit` or `workflow:research.deep`.
triggers:
  - "workflow:paper.lit"
  - "workflow:research.deep"
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
policies: [evidence-integrity, workspace-safety]
references:
  - doc: capability:literature-review
  - doc: capability:deep-literature-review
  - doc: capability:evidence-check
  - doc: workflow:paper.lit
  - doc: workflow:research.deep
  - url: "https://info.arxiv.org/help/api/user-manual.html"
  - url: "https://api.semanticscholar.org/api-docs/"
  - url: "https://docs.openalex.org/"
---

# scholar-search

## When to use

Load whenever a command needs to **retrieve paper metadata or abstracts** from the open web:

- `workflow:paper.lit` building or expanding `.evidraft/literature/`
- `workflow:research.deep` Stage 2 (Retrieve) and Stage 4 lineage hops
- any time the user pastes an arXiv id, DOI, or OpenAlex Work id and asks "what is this?"

If the calling command provides a `run_id` (from its `plan.yaml`), every row written by this skill MUST carry it.

## On-disk layout: disposable cache vs. durable snapshots

Two storage tiers, intentionally separate. **Read this before every WebFetch call.**

### Tier 1 — Provider JSON cache (disposable)

Structured retrieval responses from arXiv / Semantic Scholar / OpenAlex. Nothing in `evidence.jsonl` pins these files; they are pure speedup for repeat retrievals.

- Path: `.evidraft/literature/.cache/<provider>/<sha1(url)>.json`
- TTL: 14 days. Stale entries are **deleted on encounter**, not refreshed in the background.
- The host's `.gitignore` covers `**/.evidraft/cache/`; the dotted `.cache/` form may not be covered — flagged separately in the migration report.
- Every retrieval row records `run_id` (from the calling command's `plan.yaml`).
- Path-construction recipe:
  1. canonicalise the URL (sort query params alphabetically, lowercase scheme + host),
  2. `sha1` it (`shasum -a 1 <<< "$url"` or `sha1sum`),
  3. write the parsed JSON response to `.evidraft/literature/.cache/<provider>/<sha1>.json` with two extra top-level keys: `_fetched_at` (UTC iso) and `_url` (the canonical URL).

### Tier 2 — `webfetch` snapshots (durable evidence backing)

For sources that downstream evidence rows cite line-by-line (blog posts, vendor docs, engineering reports, tutorials, specs), store the rendered body as markdown so the line numbers are stable. **These files are evidence backing, not cache** — they live OUTSIDE `.cache/` and are NEVER auto-deleted.

- Body: `.evidraft/literature/snapshots/<sha256(raw_body)>.md` — the exact fetched body bytes, with no LLM rewriting.
- Reciprocal contract: any evidence record with `source` starting `http://` / `https://` MUST carry `source_kind != "paper"` and a `file_path` pointing at the `.md` above; see `capability:evidence-check §1.1` for the row shape.
- **No TTL. No auto-delete.** A snapshot referenced by any `evidence.jsonl` row is provenance — losing it invalidates every claim that cited it. Stale snapshots stay on disk; `evidence-auditor` re-reads them as-is.
- **Refresh recipe**: when the upstream page has materially changed, store the new body. Different bytes produce a new SHA-256 path even for the same URL. Emit a fresh evidence row whose `supersedes` points at the prior row. Never overwrite or delete the prior snapshot.
- Tracking: `.evidraft/literature/snapshots/` is intentionally outside `.gitignore`'s `**/.evidraft/.cache/` ignore. In user projects it is committed alongside `references.bib` and `evidence.jsonl`; in this plugin's own repo the root-level `/.evidraft/` is ignored for trial scaffolds only.

Recipe:

1. `WebFetch` the canonical URL and preserve the returned body exactly in an input file.
2. Run `evidraft --root <project> snapshot store <url> <raw-body-file>`.
3. Use the path returned by the deterministic kernel; it is based on `sha256(raw_body)`.
4. Return `{snapshot_path: ".evidraft/literature/snapshots/<sha256>.md", title, content_type}` so the caller (`paper-lit`) can build the evidence row directly.

## Inputs

- a free-text query, or one of: `arxiv:<id>`, `doi:<id>`, `openalex:<W...>`, `s2:<paperId>`
- optional filters: year range (`from`, `to`), venue allow-list, language, `top_k`
- the calling command's `run_id`

## Outputs

- A list of dicts conforming to the `candidates.jsonl` row schema in `workflow:research.deep` Stage 2:

  ```json
  {"id":"cand_NNNN","title":"...","abstract":"...","venue":"...","year":2023,
   "authors":["..."],"doi":"...","source":"arxiv|semantic-scholar|openalex",
   "provider_id":"arxiv:2401.01234","sub_query_ids":["q1","q3"],
   "depth":0,"aliases":[{"source":"openalex","provider_id":"W..."}],
   "run_id":"...","verified":false,"confidence":"medium","verify_note":""}
  ```

- Cache files under `.evidraft/literature/.cache/<provider>/<sha1>.json`.
- (`workflow:paper.lit` callers) BibTeX + matrix rows + evidence records derived from the candidate list — built by `literature-review`, not this skill.

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
- Never invent: a missing `venue` stays empty and a missing year is `null`. The evidence reviewer must reject any downstream claim that depends on a fabricated field.

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
