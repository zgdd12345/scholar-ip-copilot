# code-intel-mcp

**Status:** `stub` — interfaces only, all tools raise `NotImplementedError`.
**Roadmap:** see [`docs/roadmap.md`](../../../docs/roadmap.md).

MCP server that gives EviDraft a structured view of the user's repository.
Powers `/scholar:paper-code-audit`, the `repo_summary.md` and `method_to_code.md`
artefacts, and the codebase-grounded principle of the project.

## v0.2 — symbol / grep / tree-sitter

- Language detection by file extension + shebang.
- Symbol extraction via [`tree-sitter`](https://tree-sitter.github.io/)
  grammars where available; fall back to ripgrep.
- Configuration parsing: PyYAML for YAML, `tomllib` for TOML, `json` for
  JSON, plus light argparse / Hydra / OmegaConf heuristics.
- `search_code` ranks by lexical hits.

## v0.5 — semantic vector index

- Add an embedding-based index over functions, classes, and config keys.
- `map_method_to_code` and `search_code` switch to hybrid lexical +
  semantic ranking.
- Index is local-only; no embeddings leave the machine unless the user
  opts in.

## Tools

| Name | Signature | Returns |
|---|---|---|
| `summarize_repo` | `summarize_repo(path: str)` | `dict` — `{languages, modules, entrypoints, configs, tests}` |
| `find_entrypoints` | `find_entrypoints(path: str)` | `list[str]` — repo-relative paths |
| `extract_config_schema` | `extract_config_schema(path: str)` | `dict` — merged config surface |
| `map_method_to_code` | `map_method_to_code(method_description: str, path: str)` | `list[dict]` — each `{file, line_range, symbol, why}` |
| `search_code` | `search_code(query: str, path: str, top_k: int = 20)` | `list[dict]` — each `{file, line, snippet, score}` |

## Roadmap

- **v0.1** — this stub.
- **v0.2** — symbol / grep / tree-sitter implementation.
- **v0.5** — semantic vector index, hybrid ranking.

## Enable in `.evidraft/project.yaml`

```yaml
mcp:
  code-intel:
    enabled: true
    semantic_index: false   # flip to true in v0.5
```
