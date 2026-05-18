# scholar-search-mcp

**Status:** `stub` — interfaces only, all tools raise `NotImplementedError`.
**Roadmap:** see [`docs/roadmap.md`](../../../docs/roadmap.md).

MCP server that surfaces scholarly papers for EviDraft's paper workflow
(`/scholar:paper-lit`, `/scholar:paper-review`, `/scholar:paper-check`). The plugin must remain
usable with this server disabled; in that mode commands degrade to
human-supplied PDFs and local BibTeX.

## Target providers

v0.2 will pick **one** of the following as the primary backend (the others
may be added behind a uniform interface later):

- [arXiv](https://arxiv.org/) — open metadata + PDFs, no auth.
- [Semantic Scholar](https://api.semanticscholar.org/) — rich graph,
  rate-limited.
- [OpenAlex](https://openalex.org/) — open metadata, citation graph, no auth.

No network code lives in this package today.

## Tools

| Name | Signature | Returns |
|---|---|---|
| `search_papers` | `search_papers(query: str, year_range: tuple[int,int] \| None = None, venue: str \| None = None, top_k: int = 20, provider: str = "arxiv")` | `list[dict]` — ranked paper records (each carries `source`) |
| `get_paper_metadata` | `get_paper_metadata(paper_id: str)` | `dict` — normalised metadata record |
| `download_pdf` | `download_pdf(url: str, dest: str)` | `str` — local path of the written PDF |
| `extract_references` | `extract_references(pdf_path: str)` | `list[dict]` — structured reference records |
| `get_paper_references` | `get_paper_references(paper_id: str, provider: str = "semantic-scholar")` | `list[dict]` — works that `paper_id` cites (ancestors) |
| `get_paper_citations` | `get_paper_citations(paper_id: str, provider: str = "semantic-scholar")` | `list[dict]` — works that cite `paper_id` (follow-on) |
| `resolve_citation` | `resolve_citation(claim: str, candidates: list[dict])` | `dict` — `{citation_key, confidence, evidence_id_hint}` |

### Record shapes (informal)

```text
paper record       ::= {paper_id, title, authors, year, venue?, url?, abstract?, source}
metadata record    ::= paper record + {doi?, citation_key?}
reference record   ::= {raw, title?, authors?, year?, doi?}
citation match     ::= {citation_key, confidence: float in [0,1], evidence_id_hint?}
```

## Multi-provider support (v0.2)

`search_papers`, `get_paper_references`, and `get_paper_citations` all take a
`provider` kwarg. Callers must record the chosen `provider` as the row's
`source` field and must never blend metadata from two providers into one row
silently; cross-provider variants belong under `aliases`.

| Provider | Auth | Rate limit | Licence caveat |
|---|---|---|---|
| `arxiv` | none | 1 req/3s recommended (no hard cap) | metadata CC0; PDFs per-paper licence (often arXiv non-exclusive). No forward-citation graph — `get_paper_citations` must raise here. |
| `semantic-scholar` | optional API key (higher tier) | ~100 req/5min unauthenticated; ~1 req/s authenticated | Metadata under ODC-BY; respect S2 API terms; do not redistribute bulk dumps. |
| `openalex` | none (polite email recommended) | ~10 req/s with mailto in User-Agent | Metadata CC0; abstracts are inverted-index, not full text. |

Selecting a provider:

```python
search_papers("retrieval-augmented generation", provider="semantic-scholar")
get_paper_references("arxiv:2401.01234", provider="openalex")
get_paper_citations("doi:10.1109/CVPR...", provider="semantic-scholar")
```

`/scholar:deepresearch` calls each provider in the order declared in
`plan.yaml.providers` (default `[arxiv, semantic-scholar, openalex]`) and
records the `source` per `candidates.jsonl` row.

## Roadmap

- **v0.1** — this stub. Interfaces frozen, every tool raises
  `NotImplementedError("scheduled for v0.2 — see roadmap.md")`.
- **v0.2** — pick one provider, implement `search_papers` +
  `get_paper_metadata` against it, add basic on-disk cache.
- **v0.3** — `download_pdf` with rate-limit + licence-respecting policy.
- **v0.4** — `extract_references` via a PDF parser (e.g. `pdfminer.six` +
  GROBID where available).

## Enable in `.evidraft/project.yaml`

Until the implementation lands the server stays disabled. When v0.2 ships,
opt in with:

```yaml
mcp:
  scholar-search:
    enabled: true
    provider: arxiv   # or: semantic-scholar | openalex
```
