# tests/

Executable pytest suite. **55 tests** across **5 test files**; `make verify` re-renders + runs everything in under a second.

## Run

```bash
source .venv/bin/activate
python -m pytest tests/        # 55 passed
```

## Layout

```
tests/
├── README.md                           this file
├── test_adapter_conformance.py         13 structural invariants (A-M) across claude-code / codex-cli / opencode; 23 parametrised cases
├── test_loader_skill_bundles.py        _shared/loader.py contract — one-skill-per-dir discovery, frontmatter survival
├── test_manifest_version.py            plugin.yaml manifest_version + the migrate.py 0.0.0 -> 1.0.0 framework
├── test_retention_prune.py             retention: TTL + keep_last prune semantics
├── test_schema_fixtures.py             JSON-schema validity of every YAML under tests/fixtures/schemas/
├── fixtures/
│   ├── adapter_invariants/
│   │   └── expected_counts.json        drift catcher — commands/agents/skills/hooks counts the conformance suite asserts against the source tree
│   ├── schemas/                        positive + negative schema-validation fixtures (`*__valid.yaml`, `*__invalid.yaml`)
│   ├── cv-detection-paper.md           pointer at the cv-detection-paper example dir
│   └── patent-disclosure.md            pointer at the patent-disclosure example dir
└── integration/
    └── README.md                       end-to-end fixtures live under examples/, not here
```

## Conformance invariants (A-L)

`tests/test_adapter_conformance.py` renders the plugin against each adapter into a temp dir and asserts structural invariants that survive ordinary content edits but catch regressions:

| Letter | Invariant | Scope |
|---|---|---|
| A | file-count | each source artefact maps to expected rendered file(s) per adapter |
| B | frontmatter survival | emitted frontmatter equals source values |
| C | retention preamble | `## Pre-run cleanup` appears IFF source declares `retention:` (symmetric) |
| D | no MCP references (ratchet) | no new file may mention deprecated `*-mcp` names; baseline empty after 2026-05 cleanup |
| E | required skills | every `../skills/<X>/SKILL.md` referenced by a command exists in source and renders |
| F | subagent dispatch | commands with non-empty `subagents:` render a `## Dispatch plan` + name each subagent |
| G | executable hooks | rendered `hooks/hooks.json` plus 3 executable `.sh` scripts |
| H | per-agent dispatch hints | every agent declares `model:` (one of haiku/sonnet/opus/inherit); `effort:` set when model pinned |
| I | skill-bundle propagation | every non-`SKILL.md` sibling under a source skill ships to every host |
| J | source-tree link integrity | every relative `[text](path)` link in source resolves to a file |
| K | rendered-tree link integrity | same as J but on rendered output — catches adapter path-flattening bugs J cannot see |
| L | frontmatter doc refs | every `references[].doc:` in source YAML resolves to a file or directory |
| M | command-hook opt-out sidecar | adapter projects per-command `hooks:` allowlists into `hooks/command-hooks.json`; runtime smoke verifies `_lib.sh` opt-out + concurrency + no project-tree pollution (bash + jq required) |

## How `expected_counts.json` works

Two kinds of state live in `fixtures/adapter_invariants/expected_counts.json`:

1. **Source-derivable counts** (`commands`, `agents`, `skills`, `hooks`, `templates_root_dirs`, `retention_commands`) — drift catchers. Adding or removing a source artefact requires a deliberate, PR-visible bump.
2. **Ratchet state** (`_mcp_legacy_baseline`) — not re-derivable. Tracks which rendered files still mention legacy `*-mcp` server names so invariant D can fail closed when a new file regresses, but accept the current baseline. After the 2026-05 cleanup the baseline is empty.

## End-to-end fixtures live under `examples/`

The `examples/` directory at the repo root contains worked-example projects — populated `.evidraft/` trees demonstrating the audit / review / claim-chart outputs. The conformance suite does **not** consume them directly; they are visual regression references for humans and are referenced by the schema-validation fixtures here.
