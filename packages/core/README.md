# `@scholar-ip/core`

Platform-neutral schemas and (planned) helpers shared by every adapter, MCP server, and plugin file.

## Layout

```
packages/core/
├── README.md
├── schemas/
│   ├── project.schema.json    # .evidraft/project.yaml
│   ├── evidence.schema.json   # one line of evidence.jsonl
│   ├── paper.schema.json      # manuscript metadata
│   ├── patent.schema.json     # invention disclosure + claim chart metadata
│   └── command.schema.json    # platform-neutral command / agent / skill / hook
└── src/
    └── (planned) python helpers: validate.py, evidence_io.py
```

## Schemas

All schemas are JSON Schema Draft 2020-12.

| Schema | Files governed |
|---|---|
| `project.schema.json` | `.evidraft/project.yaml` |
| `evidence.schema.json` | each JSON object in `.evidraft/evidence/evidence.jsonl` |
| `paper.schema.json` | manuscript metadata stored alongside `manuscript/` |
| `patent.schema.json` | patent metadata stored alongside `.evidraft/patent/` |
| `command.schema.json` | the **frontmatter** of every command / agent / skill / hook file under `plugins/scholar-ip/` |

## Validation (planned, v0.2)

```bash
python -m packages.core.validate \
    --project .evidraft/project.yaml \
    --evidence .evidraft/evidence/evidence.jsonl
```

For the MVP, the schemas are reference documents and adapters can lint against them when generating outputs.

## Why JSON Schema

- Host-agnostic: same schemas verified by python, node, or rust adapters.
- IDE friendly: YAML editors can pull schemas via `yaml-language-server: $schema`.
- Reusable in MCP servers as input/output contracts.
