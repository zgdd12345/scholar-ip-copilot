# patent-search-mcp

**Status:** `stub` — interfaces only, all tools raise `NotImplementedError`.
**Roadmap:** see [`docs/roadmap.md`](../../../docs/roadmap.md).

MCP server that surfaces patent prior art and structures claim comparisons
for EviDraft's patent workflow (`/scholar:patent-prior-art`, `/scholar:patent-claims`,
`/scholar:patent-review`).

## Advisory only — not legal advice

Everything this server returns is **advisory**. It supports the production
of an attorney-reviewable **技术交底书 (Technical Invention Disclosure)**;
it does not produce legal conclusions, FTO opinions, validity opinions, or
filing-ready claim text. See [`docs/legal-and-ethics.md`](../../../docs/legal-and-ethics.md).

The agent integrating this server must keep that framing in every user-
facing output.

## Target providers

v0.2 will pick one of the following as the primary backend:

- [USPTO PatentsView](https://patentsview.org/apis/api-endpoints) — US
  bulk data + REST API.
- [EPO OPS](https://developers.epo.org/) — European Patent Office Open
  Patent Services, requires registration.
- [Google Patents](https://patents.google.com/) — broad coverage, no
  official API; use is bounded by Google's terms.

No network code lives in this package today.

## Tools

| Name | Signature | Returns |
|---|---|---|
| `search_patents` | `search_patents(query: str, top_k: int = 20, jurisdictions: list[str] \| None = None)` | `list[dict]` — patent records |
| `extract_claims` | `extract_claims(patent_text: str)` | `list[dict]` — each `{id, kind, text, depends_on}` |
| `build_prior_art_chart` | `build_prior_art_chart(invention: dict, prior_art: list[dict])` | `dict` — advisory chart skeleton |
| `compare_claim_elements` | `compare_claim_elements(claims: list[dict], prior_art: list[dict])` | `list[dict]` — advisory element-by-element comparison |

### Record shapes (informal)

```text
patent record   ::= {patent_id, title, assignee?, filed?, granted?,
                     jurisdiction, abstract?, url?}
claim record    ::= {id, kind: independent|dependent, text, depends_on?}
chart           ::= {rows, columns, advisory: True}
comparison row  ::= {claim_id, element,
                     matches: [{patent_id, evidence, confidence}],
                     advisory: True}
```

## Roadmap

- **v0.1** — this stub.
- **v0.2** — pick one provider, implement `search_patents` and
  `extract_claims`, with on-disk cache.
- **v0.3** — `build_prior_art_chart` + `compare_claim_elements` driven by
  the extracted claim element index.
- **v0.4** — multi-jurisdiction merging and de-duplication of family
  members.

## Enable in `.evidraft/project.yaml`

```yaml
mcp:
  patent-search:
    enabled: true
    provider: uspto-patentsview   # or: epo-ops | google-patents
    jurisdictions: [US, EP, CN]
```
