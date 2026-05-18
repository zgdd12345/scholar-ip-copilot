# experiment-mcp

**Status:** `stub` — interfaces only, all tools raise `NotImplementedError`.
**Roadmap:** see [`docs/roadmap.md`](../../../docs/roadmap.md).

MCP server that turns the user's `experiments/` directory into LaTeX
tables, figure suggestions, and a number-source audit. Feeds
`/scholar:paper-experiment` and `/scholar:paper-check`.

## v0.2 implementation plan

- Use `pandas` to normalise CSV / JSON / JSONL into the result schema.
- `pyarrow` is an **optional extra** that adds Parquet support
  (`pip install evidraft-experiment-mcp[parquet]`).
- LaTeX table rendering targets the `booktabs` style by default; columns
  are inferred from the row schema and may be overridden via the
  `style` argument.
- Figure suggestion is rule-based in v0.2: pick `(x, y, group_by)` from
  metric cardinality and dtype. No plot is drawn — the user / agent is
  expected to consume the spec.
- `check_number_sources` scans the text with a number regex and looks up
  each candidate in the loaded results to label it `MATCH` / `MISMATCH` /
  `MISSING`.

No network code in this package.

## Tools

| Name | Signature | Returns |
|---|---|---|
| `load_results` | `load_results(path: str)` | `dict` — normalised `{schema, rows, source}` |
| `summarize_metrics` | `summarize_metrics(path: str)` | `list[dict]` — each `{metric, setting, value, source}` |
| `generate_latex_table` | `generate_latex_table(results: list[dict], style: str = "booktabs")` | `str` — LaTeX source |
| `suggest_figures` | `suggest_figures(results: list[dict])` | `list[dict]` — each `{kind, x, y, group_by, source, seeds, rationale}` |
| `check_number_sources` | `check_number_sources(text: str, results_path: str)` | `list[dict]` — each `{number, kind: MATCH\|MISMATCH\|MISSING, source}` |

## Roadmap

- **v0.1** — this stub.
- **v0.2** — `pandas`-backed loaders, booktabs renderer, rule-based figure
  suggester, number-source audit.
- **v0.3** — multi-seed aggregation (mean / std / CI) baked into table
  generation.

## Enable in `.evidraft/project.yaml`

```yaml
mcp:
  experiment:
    enabled: true
    parquet: false   # set true once pyarrow extra is installed
```
