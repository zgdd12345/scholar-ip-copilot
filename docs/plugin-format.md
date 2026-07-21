# Plugin format 3.0

`plugins/scholar-ip/plugin.yaml` identifies the product and points to the shared workflow
IR. Both `manifest_version` and product `version` are `3.0.0`; project data versioning is
separate and lives in `.evidraft/project.yaml` as `format_version: 2`.

## Manifest

```yaml
id: scholar
manifest_version: "3.0.0"
name: EviDraft
version: "3.0.0"
entrypoints:
  workflows: workflows/
  roles: roles/roles.yaml
  policies: policies/policy.yaml
  capabilities: capabilities/
  templates: templates/
```

The manifest lists exactly seven workflows and their public actions. It contains no
host-specific prompt bodies. `packages/core/schemas/plugin.schema.json` validates this
layout.

## Workflow contract

Each `workflows/<id>/workflow.yaml` has this shape:

```yaml
id: paper
description: Route the evidence-backed paper lifecycle.
actions:
  draft:
    procedure: stages/draft.md
    inputs:
      - name: style
        type: enum
        values: [arxiv, cvpr, neurips, generic]
        optional: true
        default: arxiv
    outputs:
      - path: manuscript/main.tex
        required: true
      - path: manuscript/sections/
        required: true
    policies: [evidence-integrity]
    roles:
      - id: writing-reviewer
        mode: latex-editor
        tier: fast
    retention: {}
```

Allowed action keys are `inputs`, `outputs`, `policies`, `roles`, `retention`, and
`procedure`, plus migration metadata used by contract tests. Procedure paths are
relative to their workflow directory and must resolve. A stage is private prompt text,
not a host-discoverable entry. Output `required` defaults to `true`; conditional or
best-effort artefacts declare `required: false` explicitly.

## Roles

`roles/roles.yaml` defines the six semantic IDs and their modes. A role reference in a
workflow must name one of those IDs, an allowed mode for that role, and one of
`fast|standard|deep`. Host profiles translate tiers without changing workflow behavior.

## Policies

`policies/policy.yaml` defines exactly `workspace-safety`, `scope`, and
`evidence-integrity`. Workflow actions reference these IDs. Operation-aware rules use
the canonical `<workflow>.<action>` identifier, including `run` for direct workflows.

## Private capabilities

Capabilities are normal markdown/reference assets grouped by domain. They do not use a
host discovery filename and do not add public skills. A stage may link to a capability;
source and rendered link resolution are release invariants.

## Rendering contract

The shared renderer:

1. validates and loads every workflow into a common IR;
2. selects a host profile;
3. writes seven public routers and required private stages, roles, policies, and
   capabilities;
4. writes the host manifest;
5. records owned paths and removes only stale previously owned output.

Host adapters may change path syntax, role dispatch, model names, and hook projection.
They may not change action inputs, defaults, outputs, policy results, or retention.

`plugins/scholar-ip` is the authored source. Packaging combines its Claude and Codex
projections into `plugins/scholar`, the deterministic, tracked Codex and Claude release
package. The Python wheel deliberately excludes both trees and all host manifests and
skills; its renderers require an external `--plugin` path.

## Validation

```bash
.venv/bin/python -m pytest tests/
.venv/bin/python -m ruff check .
.venv/bin/evidraft package --plugin plugins/scholar-ip --out plugins/scholar --check
python "$PLUGIN_CREATOR_ROOT/scripts/validate_plugin.py" plugins/scholar
claude plugin validate plugins/scholar
```

These validation commands are read-only and do not install a host plugin.
