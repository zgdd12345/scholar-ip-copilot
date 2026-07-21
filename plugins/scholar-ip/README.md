# `scholar-ip` source plugin (EviDraft)

This directory is the host-neutral EviDraft 3.0 source. One renderer projects it to
Claude Code, Codex, and OpenCode without changing workflow behavior or project outputs.

## Public workflows

Exactly seven workflows are public:

| Workflow | Actions |
|---|---|
| `using` | direct entry |
| `scope` | direct entry |
| `research` | `reading-list`, `explain`, `deep` |
| `paper` | `init`, `lit`, `idea`, `code-audit`, `experiment`, `review`, `draft`, `check`, `venue` |
| `patent` | `init`, `scout`, `prior-art`, `disclosure`, `claims`, `review` |
| `polish` | direct entry |
| `xreview` | direct entry |

Invocation syntax is host-specific:

```text
Claude Code  /scholar:paper draft
Codex        $scholar-paper draft
Codex        $scholar-research explain papers/attention-is-all-you-need.pdf --mode graduate
OpenCode     /scholar-paper draft
```

The `research explain` action writes its academic note to
`.evidraft/notes/paper-explanations/<paper-slug>.md`.

The removed v1 command names are not compatibility aliases. Use the workflow/action
form above.

`research.guide` was removed and guidance routes through `using`.
`research.explain` always attempts similar and current methods, schedules up to 15 ready
tasks, and degrades to a `partial` note with named gaps when external work fails or is
unavailable. Audit findings are advisory and do not by themselves stop synthesis.

## Source layout

| Path | Contract |
|---|---|
| `workflows/<id>/workflow.yaml` | Action inputs, defaults, outputs, policies, roles, retention, and procedures |
| `workflows/<id>/SKILL.md` | Thin public router; one per workflow |
| `workflows/<id>/stages/` | Private, on-demand action procedures |
| `roles/roles.yaml` | Six semantic roles and their modes |
| `policies/policy.yaml` | `workspace-safety`, `scope`, and `evidence-integrity` |
| `capabilities/` | Private domain references indexed by `capabilities/index.yaml` |
| `templates/` | Stable paper and patent project scaffolds |
| `plugin.yaml` | Versioned product manifest and seven-workflow surface |

Capabilities are not host skills and role modes are not additional agents. Public
discovery remains bounded to seven entries on every host.

This directory is the authored source. `plugins/scholar` is the deterministic, tracked
Codex and Claude release package. Codex marketplace mode is the default, while
project-local `.agents/skills` is a mutually exclusive compatibility mode. The Python
wheel contains renderer and CLI code only and requires an external `--plugin` path.
After reinstall, users must restart their host session; Codex users must open a new
task.

See [plugin-format.md](../../docs/plugin-format.md) for the authoring contract,
[architecture.md](../../docs/architecture.md) for component boundaries, and
[migration-v2.md](../../docs/migration-v2.md) for project-data migration, and
[migration-v3.md](../../docs/migration-v3.md) for the lighter workflow contract.
