# EviDraft -> Codex CLI adapter

Status: **MVP (skills-based plugin).**

Codex CLI exposes user content through **skills** (`SKILL.md` bundles under
`.agents/skills/`, walked from cwd up to the worktree). It has no
user-defined slash commands, no subagent dispatch, and no workflow file
convention. This adapter therefore flattens every source artefact into a
skill:

* each source command → `skills/scholar-<command-id>/SKILL.md`
* each source skill → `skills/scholar-skill-<skill-id>/SKILL.md` (the
  `-skill-` infix disambiguates ids that exist as both a command and a skill,
  e.g. `brainstorming`)
* source subagents → inlined into the rendering command's body
* source hooks → inlined as `## Guardrails` blocks
* source workflows → inlined into the README's `## Workflows` section

## Output shape

```
<out>/                              # plugin root
├── .codex-plugin/
│   └── plugin.json                 # Codex plugin manifest
├── README.md
└── skills/
    ├── scholar-<command-id>/SKILL.md
    └── scholar-skill-<source-skill-id>/SKILL.md
```

Each `SKILL.md` has frontmatter:

```yaml
---
name: scholar-<id>            # or scholar-skill-<id>
description: <trigger text>   # what the skill is for; the model uses this
                              # for implicit matching
---
```

Body keeps the rich Inputs/Outputs/Instructions/Guardrails sections (for
command-skills) or the Triggers/Provides/body (for source-skills).

## Installing into a project

There are two paths, and you should know about both.

### Path A — direct skill drop (works today)

Codex auto-discovers skills under **`.agents/skills/`** (walked from cwd up
to the worktree root). For now this is the only path that actually causes
Codex to *load* the skills:

```bash
python -m packages.adapters.codex_cli.generate \
    --plugin plugins/scholar-ip \
    --out /tmp/scholar-codex
mkdir -p <your-project>/.agents/skills
cp -R /tmp/scholar-codex/skills/* <your-project>/.agents/skills/
```

Restart Codex. `/skills` will list every `scholar-*` and `scholar-skill-*`
entry. Implicit matching also works because each `description` line is
written as a trigger phrase.

### Path B — marketplace install (forward-looking)

The rendered plugin under `--out` is a valid Codex plugin (`.codex-plugin/
plugin.json` + `skills/`). You can register a local marketplace pointing at
it:

```jsonc
// <repo-root>/.agents/plugins/marketplace.json
{
  "name": "scholar-ip-copilot",
  "interface": { "displayName": "scholar-ip-copilot" },
  "plugins": [{
    "name": "scholar",
    "source": { "source": "local", "path": "./.codex/plugins/scholar" },
    "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
    "category": "Productivity"
  }]
}
```

Then `codex plugin marketplace add <repo-root>` and enable in
`~/.codex/config.toml`:

```toml
[plugins."scholar@scholar-ip-copilot"]
enabled = true
```

**Caveat (Codex 0.130.0):** local-source marketplaces are recognised by
`codex plugin marketplace add` but Codex does not currently sync their
plugins into the loader cache — only the curated openai-curated marketplace
under `~/.codex/.tmp/plugins/` is walked at startup. The marketplace is
registered for forward compatibility, but you still need Path A today.

## Caveats

* No slash commands: every source command becomes a skill. Users invoke
  them through `/skills` selection or by typing `$scholar-paper-init`,
  not by typing `/scholar:paper-init`.
* No subagent dispatch: source subagent definitions are inlined as
  `## Inline subagent roles` at the bottom of the corresponding command
  body — the model reads them as a system-prompt suffix.
* Hooks are advisory only — they appear in `## Guardrails` and rely on the
  model honouring them. Codex's only first-class hook surface is JS
  callbacks inside a plugin module (out of scope for this adapter).
