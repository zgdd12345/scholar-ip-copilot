# Claude Code host profile

The Claude Code adapter is a thin wrapper over the shared v2 renderer:

```bash
.venv/bin/evidraft-claude-code \
  --plugin plugins/scholar-ip \
  --out .claude/plugins/scholar-ip
```

Use `--dry-run` to validate and list output without changing the destination.

## Public interface

Claude receives exactly seven slash commands under `commands/`: `using`, `scope`,
`research`, `paper`, `patent`, `polish`, and `xreview`. Action workflows use the form
`/scholar:<workflow> <action>`, for example `/scholar:paper draft`.

The six semantic roles render as native agent files. Semantic tiers map as follows:

| EviDraft tier | Claude model |
|---|---|
| `fast` | Haiku |
| `standard` | Sonnet |
| `deep` | Opus |

Stages, policies, and capabilities are private resources and are loaded by routers as
needed. They are not additional slash commands or skills.

## Validation

```bash
claude plugin validate .claude/plugins/scholar-ip
```

Every render writes an ownership manifest and removes only output previously recorded as
owned. User files adjacent to the plugin are preserved.
