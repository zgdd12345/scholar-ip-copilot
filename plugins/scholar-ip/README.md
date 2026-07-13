# `scholar-ip` source plugin (EviDraft)

This directory is the host-neutral EviDraft 2.0 source. One renderer projects it to
Claude Code, Codex, and OpenCode without changing workflow behavior or project outputs.

## Public workflows

Exactly seven workflows are public:

| Workflow | Actions |
|---|---|
| `using` | direct entry |
| `scope` | direct entry |
| `research` | `guide`, `reading-list`, `explain`, `deep` |
| `paper` | `init`, `lit`, `idea`, `code-audit`, `experiment`, `review`, `draft`, `check`, `venue` |
| `patent` | `init`, `scout`, `prior-art`, `disclosure`, `claims`, `review` |
| `polish` | direct entry |
| `xreview` | direct entry |

Invocation syntax is host-specific:

```text
Claude Code  /scholar:paper draft
Codex        $scholar-paper draft
OpenCode     /scholar-paper draft
```

The removed v1 command names are not compatibility aliases. Use the workflow/action
form above.

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

See [plugin-format.md](../../docs/plugin-format.md) for the authoring contract,
[architecture.md](../../docs/architecture.md) for component boundaries, and
[migration-v2.md](../../docs/migration-v2.md) for project-data migration.
