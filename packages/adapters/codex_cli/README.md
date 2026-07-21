# Codex host profile

The Codex adapter is a thin wrapper over the shared v3 renderer:

```bash
.venv/bin/evidraft-codex-cli \
  --plugin plugins/scholar-ip \
  --out .codex/plugins/scholar
```

Use `--dry-run` to validate and list output without changing the destination.

## Public interface

Codex discovers exactly seven workflow skills:

```text
$scholar-using
$scholar-scope
$scholar-research
$scholar-paper
$scholar-patent
$scholar-polish
$scholar-xreview
```

Actions follow the workflow name, for example `$scholar-paper draft`. Stage procedures,
role modes, policies, and capabilities remain private files inside the rendered plugin;
they do not create additional discoverable skills. This keeps the public prompt budget
bounded and avoids trigger overlap.

The project installer copies only the seven owned workflow directories into
`.agents/skills/`. Cleanup is driven by an ownership manifest and exact v1-owned names,
never a `scholar-*` wildcard, so user skills are preserved.

Codex host support may use its nearest available models for `fast`, `standard`, and
`deep`; policy results and output paths remain equivalent to the other hosts.
