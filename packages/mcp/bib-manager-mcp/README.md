# bib-manager-mcp

**Status:** `stub` — interfaces only, all tools raise `NotImplementedError`.
**Roadmap:** see [`docs/roadmap.md`](../../../docs/roadmap.md).

MCP server that maintains the canonical `references.bib` for an EviDraft
project. Used by `/scholar:paper-lit`, `/scholar:paper-draft`, and `/scholar:paper-check` to keep
the bibliography consistent with the manuscript.

## v0.2 implementation plan

- Use [`bibtexparser`](https://pypi.org/project/bibtexparser/) for parsing
  and writing.
- Dedup by DOI first, then fall back to a normalised `title + first author`
  hash.
- For missing / unused checks, run a `\cite{}` / `\citep{}` / `\citet{}`
  regex pass over the `.tex` tree and diff against the parsed `.bib`
  keyset.

No network code in this package today.

## Tools

| Name | Signature | Returns |
|---|---|---|
| `dedupe_bib` | `dedupe_bib(path: str)` | `dict` — `{removed: int, kept: int}` |
| `normalize_citation_keys` | `normalize_citation_keys(path: str, pattern: str = "firstauthorYEARkeyword")` | `dict[str, str]` — `{old_key: new_key}` rename map |
| `check_missing_entries` | `check_missing_entries(tex_path: str, bib_path: str)` | `list[str]` — citation keys used in `.tex` but missing from `.bib` |
| `check_unused_references` | `check_unused_references(tex_path: str, bib_path: str)` | `list[str]` — entries in `.bib` that are never cited |

## Roadmap

- **v0.1** — this stub. Interfaces frozen, every tool raises
  `NotImplementedError("scheduled for v0.2 — see roadmap.md")`.
- **v0.2** — full `bibtexparser`-backed implementation, in-place rewrites,
  unit tests against fixture `.bib` files.
- **v0.3** — pluggable citation-key patterns and DOI repair via
  `scholar-search-mcp`.

## Enable in `.evidraft/project.yaml`

```yaml
mcp:
  bib-manager:
    enabled: true
    citation_key_pattern: firstauthorYEARkeyword
```
