# `packages/mcp/` — MCP server stubs

EviDraft (`scholar-ip-copilot`) is designed so that the plugin remains
fully usable when every MCP server in this directory is **disabled**. The
stubs in this folder define the **interfaces** that adapters and commands
may call once real implementations land; in v0.1 each tool raises
`NotImplementedError("scheduled for v0.X — see roadmap.md")`.

See [`docs/architecture.md`](../../docs/architecture.md) for how this
layer fits in, and [`docs/roadmap.md`](../../docs/roadmap.md) for the
implementation schedule.

## Servers

| Server | Path | Tools | Status |
|---|---|---|---|
| `scholar-search` | [`scholar-search-mcp/`](scholar-search-mcp/) | `search_papers`, `get_paper_metadata`, `download_pdf`, `extract_references` | `stub` |
| `bib-manager` | [`bib-manager-mcp/`](bib-manager-mcp/) | `dedupe_bib`, `normalize_citation_keys`, `check_missing_entries`, `check_unused_references` | `stub` |
| `latex-build` | [`latex-build-mcp/`](latex-build-mcp/) | `compile_latex`, `parse_latex_errors`, `render_pdf_preview` | `stub` |
| `code-intel` | [`code-intel-mcp/`](code-intel-mcp/) | `summarize_repo`, `find_entrypoints`, `extract_config_schema`, `map_method_to_code`, `search_code` | `stub` |
| `experiment` | [`experiment-mcp/`](experiment-mcp/) | `load_results`, `summarize_metrics`, `generate_latex_table`, `suggest_figures`, `check_number_sources` | `stub` |
| `patent-search` | [`patent-search-mcp/`](patent-search-mcp/) | `search_patents`, `extract_claims`, `build_prior_art_chart`, `compare_claim_elements` | `stub` |

Each server folder ships:

```
<id>-mcp/
├── README.md     purpose, tools, status, roadmap pointer
├── __init__.py   re-exports the tool functions
└── server.py     tool functions + a minimal __main__ hint
```

## Enabling a server when its implementation lands

When a server graduates from `stub` to `mvp` (or higher), opt in from your
project's `.evidraft/project.yaml`. The exact knobs are documented in each
server's README; the pattern is:

```yaml
# .evidraft/project.yaml
mcp:
  scholar-search:
    enabled: true
    provider: arxiv
  bib-manager:
    enabled: true
    citation_key_pattern: firstauthorYEARkeyword
  latex-build:
    enabled: true
    engine: latexmk
  code-intel:
    enabled: true
    semantic_index: false
  experiment:
    enabled: true
    parquet: false
  patent-search:
    enabled: true
    provider: uspto-patentsview
    jurisdictions: [US, EP, CN]
```

If a server is not listed or `enabled: false`, the corresponding command
degrades gracefully — for example `/scholar:paper-lit` falls back to
human-supplied PDFs and the local `references.bib`, and
`/scholar:paper-experiment` falls back to whatever the user already has in
`experiments/tables/`.

## Quality bar for these stubs

- Every `server.py` starts with `from __future__ import annotations` and
  has full type hints.
- Every tool function has a docstring documenting purpose, args, returns,
  and that it raises `NotImplementedError` in v0.1.
- No network code, no subprocess calls, no side effects — only
  `pyyaml` and the stdlib are permitted dependencies.
- Patent outputs are framed as **advisory** in every README and in
  `patent-search-mcp/server.py`'s module docstring.
