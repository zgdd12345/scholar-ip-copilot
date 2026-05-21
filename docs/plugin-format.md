# Plugin Format

`scholar-ip-copilot` authors **once** and **renders many**. This doc specifies the platform-neutral format under `plugins/scholar-ip/` and how each adapter consumes it.

## Top-level manifest: `plugin.yaml`

```yaml
manifest_version: "1.0.0"   # required since the v1.0 close-out; see § Manifest versioning
id: scholar
name: EviDraft
version: 0.0.1
description: >
  Evidence-grounded academic and patent copilot for codebases,
  experiments, literature, LaTeX papers, and invention disclosures.
license: MIT
homepage: https://github.com/<you>/scholar-ip-copilot

entrypoints:
  commands:   commands/
  agents:     agents/
  skills:     skills/
  hooks:      hooks/
  templates:  templates/

# Hosts the plugin is known to render cleanly into.
adapters:
  - id: claude-code
    status: mvp
    out:    .claude/plugins/scholar-ip/
  - id: codex-cli
    status: mvp
    out:    .codex/prompts/scholar-ip/   # + sync into .agents/skills/scholar-skill-<id>/
  - id: opencode
    status: mvp                          # commands / agents / skills shipped; hooks not rendered
    out:    .opencode/{commands,agents,skills}/

# Default tool / file safety policy. Adapters apply these where the host supports it.
safety:
  forbidden_paths:
    - .env
    - "**/.env*"
    - secrets/
    - credentials.json
    - "**/*.pem"
    - "**/*.key"
  forbidden_tool_patterns:
    - "Bash:rm -rf*"
  default_allowed_tools:
    - Read
    - Glob
    - Grep
    - Edit
    - Write
    - Bash:git*
    - Bash:ls*
    - Bash:cat*
    - Bash:latexmk*
```

## Manifest versioning

`plugin.yaml` carries two semver fields and they mean different things:

| Field | What it is | Example | Who bumps it |
|---|---|---|---|
| `manifest_version` | Semver of the **manifest format** — i.e. this schema and the on-disk plugin layout. | `"1.0.0"` | Plugin-format maintainers, on any breaking change to a top-level field or to commands/agents/skills/hooks frontmatter. |
| `version` | The plugin's **product version**. | `0.0.1` | The plugin author, on any user-visible release. |

`manifest_version` MUST be a quoted string (`"1.0.0"`) so YAML does not coerce it to a float and so the value round-trips through every parser without surprise.

### When to bump `manifest_version`

- Any breaking change to a top-level field in `plugin.yaml` (rename, removal, type change).
- Any schema-incompatible change to the frontmatter of commands / agents / skills / hooks (governed by `command.schema.json`).
- Any change to the canonical on-disk layout under `plugins/<id>/`.

Additive, optional fields do **not** require a bump.

### How to migrate

The migration framework lives at `packages/core/src/migrate.py` and ships with the v0 -> v1 step that adds `manifest_version` to any pre-v1 plugin:

```bash
# Inspect the plan without writing
python -m packages.core.src.migrate \
    --plugin plugins/scholar-ip/plugin.yaml --to 1.0.0 --dry-run

# Apply in place (writes plugin.yaml and a migrate-<ts>.log next to it)
python -m packages.core.src.migrate \
    --plugin plugins/scholar-ip/plugin.yaml --to 1.0.0
```

A plugin that already carries `manifest_version: "1.0.0"` is a no-op; the CLI prints `no migrations needed (already at 1.0.0)` and exits 0.

### Change log

| `manifest_version` | Notable changes |
|---|---|
| `1.0.0` | First versioned manifest format. Introduces the `manifest_version` field itself (Module J / v1.0). |

## Per-command file

Each file under `commands/` is a single markdown document with YAML frontmatter:

```yaml
---
id: paper-init
title: "Initialize an EviDraft paper project"
kind: command                   # command | agent | skill | hook
slash: /scholar:paper-init              # what the user types
phase: paper                    # paper | patent | shared
inputs:
  - name: project_type
    type: enum
    values: [paper, patent, mixed]
    optional: true
  - name: field
    type: string
    optional: true
outputs:
  - path: .evidraft/project.yaml
  - path: manuscript/
allowed_tools: [Read, Write, Edit, Bash:git*, Glob, Grep]
forbidden_tools: [Bash:rm -rf*]
hooks: [sensitive-file-guard]
references:
  - doc: ../../docs/data-model.md
  - doc: ../skills/evidence-check/SKILL.md
---

# /scholar:paper-init

(then the actual agent instruction, in plain prose)
```

Frontmatter is the **contract**. The prose is the prompt. Adapters render both.

## Per-agent file

Same frontmatter, plus a `role`, `responsibilities`, `inputs`, `outputs`, `constraints`, and `review_checklist`. See `plugins/scholar-ip/agents/*.md`.

## Per-skill folder (skill bundles)

> Adding a new skill? Start with the hands-on walkthrough in [`docs/authoring-a-skill.md`](authoring-a-skill.md). This section is the reference spec.

`SKILL.md` is the entry point; the parent directory is the **skill bundle**. Any sibling files or sub-directories under the skill folder propagate to every adapter output by `packages/adapters/_shared/bundle.py`. The canonical bundle subdirs:

- `references/` — markdown deep-dives loaded on demand (per-stage spec, schemas, failure-mode catalog, etc.). Used heavily by `skills/deep-literature-review/` which ships 12 references files (one per pipeline stage + 6 cross-cutting).
- `assets/` — templates, fixtures, sample data shipped alongside the skill.
- `scripts/` — executable helpers (not loaded into the prompt by the adapters; available on disk for the agent to invoke).

Other sibling files (e.g. `skills/evidence-check/examples/evidence.jsonl.snippet`, `skills/venue-formatting/venues/*.yaml`) propagate too — the bundle copier walks every non-`SKILL.md` file under the bundle and preserves the relative path on render.

The skill's frontmatter declares `triggers` (when the orchestrator should pull it in) and `provides` (what it produces). Files inside `references/` etc. are **not** treated as separate skills — only `<skill-id>/SKILL.md` is the discovery anchor (see `packages/adapters/_shared/loader.py:_load_skill_dir`).

## Per-hook file

A hook spec declares `triggers` (array), `phase`, `behaviour`, and the failure mode (`block` / `warn` / `audit`). Adapters that support hook scripts emit shell or python; adapters that only support prompt-level hints render them as system instructions.

### Trigger selectors

Each entry in `triggers:` is a string selector. Adapters dispatch on these prefixes. New selector classes require an entry here before they can be used in a hook file.

| Prefix | Form | Example | Fires on |
|---|---|---|---|
| `tool:` | `tool:<ToolName>[<glob>]` | `tool:Bash:codex*` | A specific host tool invocation; supports glob suffix on the argument |
| `write:` | `write:<glob>` | `write:manuscript/**/*.tex` | A write that targets the matched path glob |
| `read:` | `read:<glob>` | `read:.env` | A read that targets the matched path glob |
| `command:` | `command:/<slash>` | `command:/scholar:polish` | The named slash-command runs (any phase of its execution) |
| `subagent:` | `subagent:<id>` | `subagent:prose-polisher` | The named subagent is dispatched |
| `phase:` | `phase:<paper\|patent\|shared>` | `phase:paper` | Any command of that phase runs (coarse-grained) |

Prose entries (e.g. `"any external-agent invocation"`) are NOT valid selectors — adapters cannot dispatch on them. Put English prose in the `## When it fires` body section, not in `triggers:`.

## Adapter contract

For each adapter under `packages/adapters/<host>/`:

```text
generate.py
├── load_plugin(path) -> Plugin   # parses plugin.yaml + all md frontmatter
├── validate(plugin)              # against packages/core/schemas/command.schema.json
├── render(plugin, out_dir)       # emits host-specific files
└── main()                        # CLI: --plugin ... --out ...
```

The Claude Code adapter emits the `.claude/` layout (commands, agents, skill bundles, executable hook scripts via `plugin.json`). The Codex CLI adapter emits flat prompt files under `.codex/prompts/scholar-ip/`, inlines any subagent it cannot represent, and syncs each skill bundle to `.agents/skills/scholar-skill-<id>/` (Codex's actual skill-discovery root); cross-skill markdown links into `references/` are rewritten by `_command_skill_body` so the flattened layout still resolves (conformance invariant K). The OpenCode adapter emits commands, agents, and full skill bundles under `.opencode/{commands,agents,skills}/`; hooks are intentionally not rendered (they would need to be JS modules under `.opencode/plugins/`, which is on the roadmap).

Conformance invariants A–L (see `tests/README.md`) gate every render: I asserts bundle propagation, J asserts source-tree relative-link integrity, K asserts rendered-output relative-link integrity (the regression catcher for adapter path-flattening), L asserts YAML `references[].doc:` resolution.

See `packages/adapters/<host>/README.md` for the exact mapping.
