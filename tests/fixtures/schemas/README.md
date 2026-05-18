# Schema regression fixtures

Tiny YAML files that exercise specific schema rules. Each file is named
`<concern>__<expected-result>.yaml`. v0.2 will pick these up with
`pytest` and pass them through `jsonschema.validate(...)` against
`packages/core/schemas/project.schema.json` (or `command.schema.json`).

For v0.1 they are useful as documentation of the boundary cases.

| Fixture | Schema target | Expected verdict | Why it exists |
|---|---|---|---|
| `hook_mode-block-alias__valid.yaml` | `project.schema.json` | VALID | `hook_mode` accepts `block` as an alias of `enabled`. |
| `hook_mode-enabled-legacy__valid.yaml` | `project.schema.json` | VALID | The legacy `enabled` value still validates. |
| `hook_mode-unknown__invalid.yaml` | `project.schema.json` | INVALID | Typos like `blocking` are rejected. |
| `lit_deep-breadth-too-large__invalid.yaml` | `project.schema.json` | INVALID | `breadth > 12` is out of range. |
| `lit_deep-provider-local-bib__invalid.yaml` | `project.schema.json` | INVALID | `local-bib` is a `candidates.jsonl` fallback, NOT a config-side provider. |
| `lit_deep-providers-all-valid__valid.yaml` | `project.schema.json` | VALID | All three MCP providers accepted. |

Add new fixtures whenever a schema rule has a boundary worth pinning down.
