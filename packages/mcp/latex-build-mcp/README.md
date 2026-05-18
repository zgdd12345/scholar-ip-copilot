# latex-build-mcp

**Status:** `stub` — interfaces only, all tools raise `NotImplementedError`.
**Roadmap:** see [`docs/roadmap.md`](../../../docs/roadmap.md).

MCP server that compiles the EviDraft manuscript and reports errors back to
the agent. Fed by the `latex-compile` hook and by `/scholar:paper-check`.

## v0.2 implementation plan

- Wrap `latexmk -pdf` (or `tectonic` where available) via
  :mod:`subprocess`. Stay strictly local; never call the network.
- Parse `.log` lines for `! ... ` errors, `LaTeX Warning: ...`, and
  `Overfull/Underfull \hbox` messages into structured records.
- Render previews with `pdftoppm` (poppler) or, if installed,
  `pdf2image`. Single-page PNG only in v0.2.

## Tools

| Name | Signature | Returns |
|---|---|---|
| `compile_latex` | `compile_latex(project_path: str, main_tex: str = "main.tex")` | `dict` — `{success: bool, pdf_path: str \| None, log_path: str}` |
| `parse_latex_errors` | `parse_latex_errors(log_path: str)` | `list[dict]` — each `{file, line, kind, message}` |
| `render_pdf_preview` | `render_pdf_preview(pdf_path: str, page: int = 1)` | `str` — local PNG path |

### Error record shape

```text
{file: str, line: int | None, kind: "error"|"warning"|"badbox"|"info", message: str}
```

## Roadmap

- **v0.1** — this stub.
- **v0.2** — `latexmk` subprocess wrapper, log parsing, single-page PNG
  previews, hooked into `latex-compile`.
- **v0.3** — incremental builds, diagnostic-to-source-line mapping that
  survives `\input` / `\include` indirection.

## Enable in `.evidraft/project.yaml`

```yaml
mcp:
  latex-build:
    enabled: true
    engine: latexmk   # or: tectonic
```
