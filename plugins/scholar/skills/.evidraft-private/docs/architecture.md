# Architecture

EviDraft 3.0 has one source model, one deterministic Python core, and one renderer.
Claude Code, Codex, and OpenCode are host profiles rather than separate implementations.

## Source model

```text
plugins/scholar-ip/
├── plugin.yaml
├── workflows/                 seven public routers
│   └── <workflow>/
│       ├── workflow.yaml      action contract
│       └── stages/*.md        on-demand LLM procedure
├── roles/roles.yaml           six semantic roles and modes
├── policies/policy.yaml       safety, advisory scope, and evidence audit
├── capabilities/              private reference material
└── templates/                 project artefact templates
```

The public routers are `using`, `scope`, `research`, `paper`, `patent`, `polish`,
and `xreview`. The workflow YAML is the contract. Every action declares its inputs,
defaults, outputs, policies, roles, retention, and procedure. Routers perform action
selection and project-state checks; they load a stage body only after selecting it.

Capabilities are private. They provide reference material to stages but are not
registered as host skills, so their trigger language cannot compete with public routers.

## Roles and tiers

The six roles are:

- `researcher`
- `evidence-reviewer`
- `code-reviewer`
- `experiment-reviewer`
- `writing-reviewer`
- `patent-reviewer`

A workflow role assignment includes a mode and a semantic tier. Modes preserve the
specialised behavior of the v1 agents without creating another public entity. Tiers are
`fast`, `standard`, and `deep`; Claude maps them to Haiku, Sonnet, and Opus. Other hosts
use their nearest supported capability.

Roles return findings to the workflow aggregator. They do not write shared output files
concurrently.

## Policies

Three policy IDs describe the shared behavior:

| Policy | Responsibility |
|---|---|
| `workspace-safety` | Project-root confinement, sensitive paths, and operation write zones |
| `scope` | Advisory project intent, constraints, and success criteria |
| `evidence-integrity` | Final evidence audit with `PASS`, `WARN`, or `FAIL` findings |

Scope and evidence checks report warnings without preventing draft generation, and
audit findings are advisory; `paper.check` and `patent.review` own the strict final
verdict. Path confinement, sensitive-file protection, overwrite approval, and
publication boundaries remain hard.

## Deterministic core

`src/evidraft/` owns the operations that must not depend on model judgment:

- v1-to-v2 project migration;
- safety-only workflow preflight and retention finalization;
- evidence append, resolve, and full audit;
- content-addressed web snapshots;
- deterministic workspace and evidence validation;
- atomic writes and ownership-aware rendering.

Retrieval, critique, experiment interpretation, patent reasoning, and prose generation
remain LLM responsibilities. The core validates their structured inputs and outputs.

## Migration and concurrency

Project data uses `format_version: 2`; a missing value means v1. Before the first write,
the core acquires an owner-aware migration lock, checks capacity, records a journal,
backs up every modified file, validates a complete temporary result, and atomically
replaces the originals. A failed transaction restores its backup. A completed migration
is idempotent.

Evidence append uses an exclusive cross-process lock and a single writer. IDs are stable
and monotonic; `supersedes` must refer to a valid acyclic history. Invalid legacy rows
are preserved in quarantine and produce a failing final evidence audit until resolved.

Snapshot identity is `sha256(raw_body)`. Migration retains URL-hash files and adds the
content-addressed copy before updating evidence paths.

## Rendering

`src/evidraft/render.py` loads the seven workflow contracts into a shared IR and applies
one of three host profiles:

| Host | Public form | Role projection |
|---|---|---|
| Claude Code | `/scholar:<workflow> [action]` | native agent files and model tiers |
| Codex | `$scholar-<workflow> [action]` | private role data loaded by router |
| OpenCode | `/scholar-<workflow> [action]` | native subagent files where supported |

Render output is assembled through atomic file replacement. The renderer records every
owned path in `.evidraft-render-manifest.json`; later runs remove only prior owned paths.
User-created files with similar names are not selected by a wildcard.

## Stable project outputs

The refactor changes invocation and authoring structure, not project artefact locations.
Evidence and audits remain under `.evidraft/`, manuscripts under `manuscript/`, and
venue packages under `submissions/`. See [data-model.md](data-model.md).

## Package boundary

`plugins/scholar-ip` is the authored source. `plugins/scholar` is the deterministic,
tracked Codex and Claude release package. Codex marketplace mode is the default;
project-local `.agents/skills` is a mutually exclusive compatibility mode.

The wheel contains renderer and CLI code only, publishes `evidraft`,
`evidraft-claude-code`, `evidraft-codex-cli`, and `evidraft-opencode`, and requires an
external `--plugin` path. Release verification uses the tracked package and temporary
host fixtures without installing any host.
