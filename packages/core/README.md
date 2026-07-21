# Core schemas

`packages/core/schemas/` is the repository-facing schema set. Runtime implementation
lives in the installable `src/evidraft/` package; this directory is not a second core.

All schemas use JSON Schema Draft 2020-12:

| Schema | Governs |
|---|---|
| `plugin.schema.json` | EviDraft 3.0 product manifest |
| `workflow.schema.json` | Seven workflow action contracts |
| `project.schema.json` | `.evidraft/project.yaml` with `format_version: 2` |
| `evidence.schema.json` | Each append-only evidence JSONL record |
| `paper.schema.json` | Paper metadata |
| `patent.schema.json` | Patent metadata |
| `command.schema.json` | Legacy v1 fixtures used by migration-contract tests only |

The deterministic runtime provides migration, workflow preflight/finalize, evidence
append/resolve, content-addressed snapshots, render, and ownership-safe install commands:

```bash
.venv/bin/evidraft --help
.venv/bin/evidraft --root /path/to/project migrate
.venv/bin/evidraft --root /path/to/project workflow preflight paper.draft
```

The wheel embeds runtime copies of project, evidence, and workflow schemas under
`src/evidraft/schemas/` so console scripts also work outside the repository.
