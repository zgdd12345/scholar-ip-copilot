# Test suite

Run the complete suite from the project virtual environment:

```bash
source .venv/bin/activate
python -m pytest tests/
python -m ruff check .
```

The suite is organized by v2 contract rather than generated-file counts:

| Module | Coverage |
|---|---|
| `test_v2_contract_mapping.py` | Frozen 22-to-7 migration matrix and legacy behavior contract |
| `test_v2_workflow_source.py` | Seven workflow schemas, actions, roles, policies, and operation IDs |
| `test_v2_capabilities.py` | Private capability index, source links, and rendered links |
| `test_v2_core.py` | Migration transactions, locking, evidence, snapshots, policies, and retention |
| `test_v2_renderer.py` | Shared IR and three-host golden rendering |
| `test_v2_adapter_cli.py` | Thin adapter CLI equivalence and dry-run behavior |
| `test_v2_install.py` | Ownership-safe cleanup and exact seven-entry installation |
| `test_v2_release_surface.py` | Version, manifest, console scripts, and removed v1 source surface |
| `test_v2_e2e.py` | Reading-list, full paper, and full patent fixtures across all hosts |
| `test_schema_fixtures.py` | Positive and negative project/legacy migration fixtures |

Tests derive public entry names from workflow contracts and require exactly seven on
Claude Code, Codex, and OpenCode. Private stages, six roles, three policies, and
capabilities must render without becoming discoverable entries.

The v1 contract JSON under `fixtures/v2/` is immutable migration input. It preserves old
parameters, defaults, outputs, policies, role behavior, and retention without retaining
the old authoring tree as a runtime surface.

Schema fixtures under `fixtures/schemas/` include v1 compatibility cases intentionally;
their old terminology is test data, not current user-facing configuration guidance.

The three contracts under `fixtures/e2e/` execute through `integration/v2_flow.py`.
They verify declared output contracts, evidence allocation, project format migration,
and the seven-entry surface on every host.
