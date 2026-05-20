# EviDraft adapters

Each adapter under this folder is a small Python module that reads the
platform-neutral plugin at `plugins/scholar-ip/` and renders it into a
host-specific layout. Author once, render many.

## Adapter matrix

| Adapter | Module | Status | Output target | CLI |
|---|---|---|---|---|
| Claude Code | `packages.adapters.claude_code.generate` | First-class | `.claude/plugins/scholar-ip/` | `python -m packages.adapters.claude_code.generate --plugin plugins/scholar-ip --out <dest>` |
| Codex CLI | `packages.adapters.codex_cli.generate` | First-class (flattened, commands + skills land under `skills/`) | `.codex/plugins/scholar/` | `python -m packages.adapters.codex_cli.generate --plugin plugins/scholar-ip --out <dest>` |
| OpenCode | `packages.adapters.opencode.generate` | First-class (commands renamed `scholar-<id>` since OpenCode has no slash-namespacing) | `.opencode/{commands,agents,skills}/` | `python -m packages.adapters.opencode.generate --plugin plugins/scholar-ip --out <dest>` |

## Common API

Each `generate.py` exposes the same four entry points:

| Function | Purpose |
|---|---|
| `load_plugin(plugin_dir)` | Parse `plugin.yaml` + every `*.md` frontmatter under `commands/ agents/ skills/ hooks/`. |
| `validate(plugin, schema_path)` | Validate every frontmatter doc against `packages/core/schemas/command.schema.json`. Uses `jsonschema` if available, else a minimal required-fields check. Returns a list of error strings. |
| `render(plugin, out_dir)` | Write the host-specific tree. Returns the list of paths written. |
| `main()` | CLI entry: `--plugin <path>` `--out <path>` `[--dry-run]`. |

Shared modules under `_shared/`:
- `loader.py` — YAML/frontmatter parser; one-skill-per-directory discovery via `_load_skill_dir` (records `bundle_dir` on each `FrontmatterDoc`).
- `bundle.py` — `copy_skill_bundle(doc, dest_skill_dir)` propagates every non-`SKILL.md` sibling (e.g. `references/`, `assets/`, `scripts/`) from the source bundle into each adapter's rendered skill directory, preserving sub-paths. All three adapters call this after writing their `SKILL.md`.

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

# 3. render Codex CLI plugin into your project
python -m packages.adapters.codex_cli.generate \
    --plugin plugins/scholar-ip \
    --out ~/your-project/.codex/plugins/scholar

# 4. render OpenCode plugin (auto-discovered from .opencode/{commands,agents,skills}/)
python -m packages.adapters.opencode.generate \
    --plugin plugins/scholar-ip \
    --out ~/your-project/.opencode

# Or render all three at once:
make render
```

## Dependencies

- Python 3.10+
- `pyyaml`
- `jsonschema` (optional — adapters degrade gracefully if missing)

No network, no shell-out, no other runtime dependencies.
