# Host adapters

The three adapter modules are compatibility console-entry wrappers over
`evidraft.render.render_plugin`. Workflow loading, validation, host projection, atomic
writes, and ownership cleanup live in the shared renderer.

| Host | Console script | Destination | Public syntax |
|---|---|---|---|
| Claude Code | `evidraft-claude-code` | `.claude/plugins/scholar-ip/` | `/scholar:<workflow> [action]` |
| Codex | `evidraft-codex-cli` | `.codex/plugins/scholar/` | `$scholar-<workflow> [action]` |
| OpenCode | `evidraft-opencode` | `.opencode/` | `/scholar-<workflow> [action]` |

Each wrapper accepts the same options:

```text
--plugin PATH    host-neutral source plugin
--out PATH       destination root
--dry-run        validate and list output without modifying the destination
```

Examples:

```bash
.venv/bin/evidraft-claude-code --plugin plugins/scholar-ip --out /tmp/evidraft-claude
.venv/bin/evidraft-codex-cli --plugin plugins/scholar-ip --out /tmp/evidraft-codex
.venv/bin/evidraft-opencode --plugin plugins/scholar-ip --out /tmp/evidraft-opencode
```

All profiles expose seven workflow entries and copy stages, roles, policies, and
capabilities as private resources. Host profiles may change invocation syntax and model
projection; they may not change action contracts, policy results, retention, or project
output paths.

Every render records owned files in `.evidraft-render-manifest.json`. Subsequent renders
remove only paths in that manifest or exact known v1-owned paths. Similar user-created
names are never selected through a wildcard.

The installable implementation is under `src/evidraft/`; adapter modules must remain thin
and must not acquire a second loader or renderer.
