# Plugin Format

`scholar-ip-copilot` authors **once** and **renders many**. This doc specifies the platform-neutral format under `plugins/scholar-ip/` and how each adapter consumes it.

## Top-level manifest: `plugin.yaml`

```yaml
id: scholar-ip
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
    out:    .codex/prompts/scholar-ip/
  - id: opencode
    status: planned
    out:    .opencode/plugins/scholar-ip/

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

## Per-skill folder

`SKILL.md` plus optional `reference.md` and `examples/`. The skill's frontmatter declares `triggers` (when the orchestrator should pull it in) and `provides` (what it produces).

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

The Claude Code adapter emits the `.claude/` layout. The Codex CLI adapter emits flat prompt files (and inlines any subagent it cannot represent). The OpenCode adapter is documented but stubbed.

See `packages/adapters/<host>/README.md` for the exact mapping.
