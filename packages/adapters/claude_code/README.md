# EviDraft -> Claude Code adapter

Status: **MVP (first-class).** Renders the platform-neutral plugin at
`plugins/scholar-ip/` into the layout Claude Code expects under
`.claude/plugins/<id>/`.

## Output shape

```
<out>/
├── plugin.json              # Claude Code plugin manifest
├── commands/<id>.md         # one slash command per file
├── agents/<id>.md           # one subagent per file
└── skills/<id>/SKILL.md     # one skill folder per skill
```

`plugin.json` is intentionally minimal:

```json
{
  "name": "EviDraft",
  "id": "scholar-ip",
  "version": "0.0.1",
  "description": "...",
  "homepage": "...",
  "commands": [ { "id": "paper-init", "slash": "/scholar:paper-init", "file": "commands/scholar:paper-init.md" } ],
  "agents":   [ { "id": "literature-reviewer", "file": "agents/literature-reviewer.md" } ],
  "skills":   [ { "id": "evidence-check", "file": "skills/evidence-check/SKILL.md" } ],
  "hooks":    [ { "id": "citation-guard", "trigger": [...], "failure_mode": "warn", "file": "hooks/citation-guard.md" } ]
}
```

> The exact Claude Code plugin manifest schema is still evolving across
> releases. The fields above are deliberately conservative; downstream tooling
> may add fields without breaking this renderer. If a future Claude Code
> release renames a key, only the translators in `generate.py` need updating.

## Frontmatter translation

| Source (platform-neutral) | Claude Code command frontmatter |
|---|---|
| `description` or `title` | `description` |
| `inputs[]` | `argument-hint` (e.g. `[project_type] <title>`) |
| `allowed_tools` | `allowed-tools` |
| `slash` | passed through |

| Source (platform-neutral) | Claude Code agent frontmatter |
|---|---|
| `id` | `name` |
| `description` / `role` / `title` | `description` |
| `allowed_tools` | `tools` |

| Source (platform-neutral) | Claude Code Skill frontmatter |
|---|---|
| `id` | `name` |
| `description` / `title` | `description` |
| `triggers` | `triggers` |

The markdown body is copied verbatim — Claude Code reads it as the system
prompt for the command / agent / skill.

## CLI

```bash
python -m packages.adapters.claude_code.generate \
    --plugin plugins/scholar-ip \
    --out ~/your-project/.claude/plugins/scholar-ip

# Inspect without writing:
python -m packages.adapters.claude_code.generate \
    --plugin plugins/scholar-ip \
    --out /tmp/scholar-ip-cc \
    --dry-run
```

Exit code is `0` on success. Validation problems (per
`packages/core/schemas/command.schema.json`) are printed to stderr but do not
stop the render in MVP — fix them and re-run.

## Caveats

- Hooks are surfaced inside `plugin.json` but Claude Code's executable-hook
  schema is still in flux. Treat them as documentation hints until upstream
  stabilises.
- The renderer is idempotent: re-running over the same `--out` overwrites
  generated files but never deletes adjacent user files.
