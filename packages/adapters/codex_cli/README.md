# EviDraft -> Codex CLI adapter

Status: **MVP (prompt/workflow files).**

Codex CLI does not have first-class sub-agent dispatch and does not natively
ingest the "command + agent + skill + hook" tuple that the platform-neutral
plugin uses. So this adapter **flattens** the plugin into self-contained
prompts that a Codex session can run directly.

## Output shape

```
<out>/
├── README.md                  # how to invoke
├── prompts/<command-id>.md    # one prompt per slash command
├── workflows/<name>.md        # ordered playbooks copied from plugin.yaml.workflows
└── skills/<skill-id>.md       # flattened skill spec
```

### Per prompt

Each `prompts/<command-id>.md` is structured as:

1. `# /<slash>` title + 1-line description
2. `## Inputs` — name, type, required/optional, default, allowed values
3. `## Outputs` — paths the command is expected to write
4. `## Instructions` — the original markdown body, verbatim
5. `## Guardrails` — every hook listed in frontmatter, plus the global safety
   policy (`forbidden_paths`, `forbidden_tool_patterns`) inlined from
   `plugin.yaml`
6. `## Inline subagent roles` — for every id in `subagents:`, the matching
   `agents/<id>.md` body is appended (deduped)

This makes each prompt **self-contained**: you can pipe one file to Codex and
get the same workflow the Claude Code adapter would route across files.

### Workflows

`workflows/paper.md` and `workflows/patent.md` are short ordered playbooks
derived from the `workflows:` section of `plugin.yaml`. They are not Codex
"runnables" by themselves; they tell the human (or a loop driver) which
prompt to run next.

## Input format

Reads `plugins/scholar-ip/` (or any plugin tree following
`docs/plugin-format.md`).

## CLI

```bash
python -m packages.adapters.codex_cli.generate \
    --plugin plugins/scholar-ip \
    --out ~/your-project/.codex/prompts/scholar-ip

python -m packages.adapters.codex_cli.generate \
    --plugin plugins/scholar-ip \
    --out /tmp/scholar-ip-codex \
    --dry-run
```

Validation problems are printed to stderr; the render proceeds.

## What is intentionally missing

- No executable hook scripts — Codex has no hook system; guardrails are
  prose only.
- No agent dispatch — every subagent is inlined.
- No tool whitelist enforcement — the model must respect the prose; Codex
  doesn't (yet) honour a manifest-level allowlist.
