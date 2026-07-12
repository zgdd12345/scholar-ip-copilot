# OpenCode host profile

OpenCode is a stable v2 renderer target, not a lint-only stub:

```bash
.venv/bin/evidraft-opencode \
  --plugin plugins/scholar-ip \
  --out .opencode
```

Use `--dry-run` to validate and list output without changing the destination.

## Public interface

OpenCode receives exactly seven workflow commands: `/scholar-using`, `/scholar-scope`,
`/scholar-research`, `/scholar-paper`, `/scholar-patent`, `/scholar-polish`, and
`/scholar-xreview`. Action workflows use the form `/scholar-paper draft`.

The six semantic roles render as host subagents where supported. Private stages,
policies, and capabilities are copied for on-demand router loading and do not become
public commands.

OpenCode uses its nearest available models for `fast`, `standard`, and `deep`. Workflow
inputs, defaults, outputs, policy decisions, and retention are identical to Claude Code
and Codex.
