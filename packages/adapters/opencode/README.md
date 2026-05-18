# EviDraft -> OpenCode adapter

Status: **planned (v0.2).**

The v0.1 adapter is a deliberate stub: it loads `plugins/scholar-ip/`,
validates every frontmatter doc against
`packages/core/schemas/command.schema.json`, and prints a friendly
"not yet implemented" banner. That way you can already lint the plugin
source against the contract OpenCode will consume.

## Intended output shape (v0.2 target)

```
<out>/                            # e.g. ~/your-project/.opencode/plugins/scholar-ip/
├── plugin.toml                   # OpenCode plugin manifest
├── commands/<id>.md              # OpenCode slash command files
├── agents/<id>.md                # OpenCode subagent files (if supported)
├── skills/<id>/SKILL.md          # OpenCode skill folders (if supported)
└── hooks/<id>.{md,sh,py}         # OpenCode hook files
```

The exact schema is pinned to the OpenCode plugin spec at v0.2 time —
see the upstream OpenCode plugin docs for the source of truth.

## Why not just symlink the Claude Code output?

OpenCode's frontmatter keys, tool naming, and hook semantics differ from
Claude Code's. Specifically we expect to need:

- a TOML manifest instead of JSON
- a different `tools:` namespace (e.g. `read,write,bash:git` vs Claude's
  `Read,Write,Bash:git*`)
- a different hook trigger vocabulary

So the renderer will be its own translation layer, not a shim.

## CLI (v0.1: lint-only)

```bash
python -m packages.adapters.opencode.generate \
    --plugin plugins/scholar-ip \
    --out /tmp/scholar-ip-opencode
```

Exit code is `0` when validation passes, `1` when there are schema errors.

## Roadmap

See `docs/roadmap.md` for the milestone in which OpenCode rendering becomes
real.
