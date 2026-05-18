# EviDraft adapters

Each adapter under this folder is a small Python module that reads the
platform-neutral plugin at `plugins/scholar-ip/` and renders it into a
host-specific layout. Author once, render many.

## Adapter matrix

| Adapter | Module | Status | Output target | CLI |
|---|---|---|---|---|
| Claude Code | `packages.adapters.claude_code.generate` | MVP, first-class | `.claude/plugins/scholar-ip/` | `python -m packages.adapters.claude_code.generate --plugin plugins/scholar-ip --out <dest>` |
| Codex CLI | `packages.adapters.codex_cli.generate` | MVP, flattened prompts | `.codex/prompts/scholar-ip/` | `python -m packages.adapters.codex_cli.generate --plugin plugins/scholar-ip --out <dest>` |
| OpenCode | `packages.adapters.opencode.generate` | Planned (lint-only stub) | `.opencode/plugins/scholar-ip/` | `python -m packages.adapters.opencode.generate --plugin plugins/scholar-ip --out <dest>` |

## Common API

Each `generate.py` exposes the same four entry points:

| Function | Purpose |
|---|---|
| `load_plugin(plugin_dir)` | Parse `plugin.yaml` + every `*.md` frontmatter under `commands/ agents/ skills/ hooks/`. |
| `validate(plugin, schema_path)` | Validate every frontmatter doc against `packages/core/schemas/command.schema.json`. Uses `jsonschema` if available, else a minimal required-fields check. Returns a list of error strings. |
| `render(plugin, out_dir)` | Write the host-specific tree. Returns the list of paths written. |
| `main()` | CLI entry: `--plugin <path>` `--out <path>` `[--dry-run]`. |

Shared YAML/frontmatter loading lives in `_shared/loader.py`.

## CLI options (all adapters)

```
--plugin PATH    path to plugins/scholar-ip
--out PATH       destination directory
--dry-run        print files that would be written; do not write
--schema PATH    override path to command.schema.json
```

## Quick start

```bash
# 1. dry-run any adapter
python -m packages.adapters.claude_code.generate \
    --plugin plugins/scholar-ip \
    --out /tmp/scholar-ip-cc \
    --dry-run

# 2. render Claude Code plugin into your project
python -m packages.adapters.claude_code.generate \
    --plugin plugins/scholar-ip \
    --out ~/your-project/.claude/plugins/scholar-ip

# 3. render Codex CLI prompts into your project
python -m packages.adapters.codex_cli.generate \
    --plugin plugins/scholar-ip \
    --out ~/your-project/.codex/prompts/scholar-ip

# 4. lint against the OpenCode target (no files written yet)
python -m packages.adapters.opencode.generate \
    --plugin plugins/scholar-ip \
    --out /tmp/scholar-ip-opencode
```

## Dependencies

- Python 3.10+
- `pyyaml`
- `jsonschema` (optional — adapters degrade gracefully if missing)

No network, no shell-out, no other runtime dependencies.
