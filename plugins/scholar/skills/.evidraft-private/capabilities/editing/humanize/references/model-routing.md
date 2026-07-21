# External-model routing config

The model used for the rewrite pass is configured in `.evidraft/project.yaml` under `style.humanize.*`. **NO real keys live in the repo**; the user supplies keys via environment variables.

## YAML schema

```yaml
style:
  humanize:
    model: anthropic:claude-sonnet-4-6     # default; falls back to in-host if env var missing
    fallback_chain:
      - openai:gpt-4o-mini
      - local:ollama/qwen2.5-7b
    preserve_citations: true               # always true in this skill; included for forward compatibility
    max_delta_ratio: 0.35                   # hard ceiling on (changed tokens / total tokens) per hunk
```

## Provider env vars

| Provider prefix | Required env var | Notes |
|---|---|---|
| `anthropic:` | `ANTHROPIC_API_KEY` | If unset, fall back to the next entry in `fallback_chain`. |
| `openai:` | `OPENAI_API_KEY` | If unset, fall back. |
| `local:ollama/...` | none | Requires a running local Ollama; if the daemon is unreachable, fall back. |
| `<none configured>` | none | Use the in-host LLM (the agent's own model). |

## Resolution algorithm

1. Read `model`. If its env var is set (or it is a local model), use it.
2. Otherwise walk `fallback_chain` in order; the first entry whose env var is present (or whose local backend is reachable) wins.
3. If every entry in the chain is unavailable, **fall back silently to the in-host LLM and log a warning to chat**. The command never blocks on missing keys.
4. The resolved model id is written to the report under `# Summary` so the user can audit which backend produced the rewrite.

## Privacy / repo hygiene

No real keys, no hard-coded account URLs, no telemetry. The plugin reads the env var; it never echoes it.
