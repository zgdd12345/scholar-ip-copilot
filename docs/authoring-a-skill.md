# Authoring workflows and private capabilities

EviDraft 2.0 does not register internal capabilities as public host skills. Extend an
existing workflow action unless the product genuinely needs a new top-level user intent.

## Add an action

1. Select one of `research`, `paper`, or `patent`.
2. Add the action contract to `plugins/scholar-ip/workflows/<id>/workflow.yaml`.
3. Create its private procedure at `workflows/<id>/stages/<action>.md`.
4. Declare every input, default, output, policy, role, tier, and retention rule.
5. Add the action to the manifest and contract mapping tests.
6. Render all three hosts and verify that no new public entry appears.

Use canonical operation IDs such as `paper.draft` in policy configuration. Procedure
paths are relative to the workflow directory and must resolve in both source and rendered
trees.

## Add private reference material

Put reusable domain material under `plugins/scholar-ip/capabilities/` and register it in
the private capability index. Capability files must not be named `SKILL.md`; that would
make them host-discoverable. Link them from the stage that needs them and keep paths
relative and portable.

## Add a role mode

Prefer a mode on one of the six semantic roles over a seventh role. A mode must define a
bounded responsibility and return findings to the workflow aggregator. Select
`fast`, `standard`, or `deep` based on reasoning requirements, not host model names.

## Verification

```bash
.venv/bin/python -m pytest tests/
.venv/bin/python -m ruff check .
.venv/bin/evidraft render --host claude --plugin plugins/scholar-ip --out /tmp/evidraft-claude
.venv/bin/evidraft render --host codex --plugin plugins/scholar-ip --out /tmp/evidraft-codex
.venv/bin/evidraft render --host opencode --plugin plugins/scholar-ip --out /tmp/evidraft-opencode
```

Each render must expose exactly the same seven workflows, preserve action contracts, and
resolve every private link.
