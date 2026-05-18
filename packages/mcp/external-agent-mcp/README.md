# external-agent-mcp

**Status:** `stub` — interfaces only, all tools raise `NotImplementedError`.
**Roadmap:** see [`docs/roadmap.md`](../../../docs/roadmap.md).

MCP server that wraps the EviDraft external-agent bridge as MCP tools.
The plugin's `/scholar:xreview` command is the v0.1 consumer; v0.2+ will
let any MCP-aware host (Claude Code, Codex CLI, OpenCode, generic IDEs)
delegate a single review pass to another coding agent without
re-implementing the CLI plumbing.

The plugin must remain usable with this server disabled; in that mode
`/scholar:xreview` invokes the external agent directly via the shell
(see `plugins/scholar-ip/skills/external-agent-bridge/SKILL.md`).

## Tools

| Name | Signature | Returns |
|---|---|---|
| `review_with` | `review_with(agent: str, prompt: str, workdir: str, persona: str, schema_path: str \| None = None, timeout_seconds: int = 600)` | `dict` — `{output_path: str, exit_code: int, tokens: int \| None, cost_usd: float \| None}` |
| `list_supported_agents` | `list_supported_agents()` | `list[dict]` — `[{id: str, read_only: bool, auth_env: str, cli: str}]` |
| `parse_review_output` | `parse_review_output(path: str)` | `dict` — `{findings: list[str], top3: list[str], cost_usd: float \| None}` |

### Return shapes (informal)

```text
review_with result        ::= {output_path, exit_code, tokens?, cost_usd?}
agent descriptor          ::= {id, read_only, auth_env, cli}
parse_review_output result ::= {findings, top3, cost_usd?}
```

## Supported agents

The three agents the bridge knows how to drive, with the **verbatim**
CLI pattern `review_with` will invoke in v0.2+.

### Codex (safest — hard-locked read-only)

- Auth env: `CODEX_API_KEY` (or `OPENAI_API_KEY`, depending on the
  Codex CLI build the user has installed).
- Read-only: **yes**, enforced by Codex itself.
- CLI:
  ```
  codex exec --sandbox read-only --json -C $WORKDIR --output-last-message $OUT_FILE - < $PROMPT_FILE
  ```

### Claude bare

- Auth env: `ANTHROPIC_API_KEY`.
- Read-only: **yes**, via `--permission-mode dontAsk --allowedTools "Read"`.
- CLI:
  ```
  claude --bare -p "$(cat $PROMPT_FILE)" --permission-mode dontAsk --allowedTools "Read" --output-format json > $OUT_FILE
  ```

### OpenCode

- Auth env: one of OpenCode's supported provider keys
  (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, …);
  see the OpenCode docs.
- Read-only: **no native sandbox**. The bridge mitigates this by
  running OpenCode against a throwaway worktree / copy, not the live
  project tree.
- CLI:
  ```
  opencode run --format json --dir $WORKDIR -f $TARGET_FILE "$(cat $PROMPT_FILE)" > $OUT_FILE
  ```

`$PROMPT_FILE` is always a mode-0600 file under
`.evidraft/reviews/.tmp/`. Prompts are delivered via stdin (Codex) or
`"$(cat …)"` (Claude / OpenCode) — never via `-m "<user-content>"`
flags.

## Security posture

- **Stdin-only prompts.** No user content in argv beyond
  `"$(cat $PROMPT_FILE)"`. Codex uses real stdin (`- < $PROMPT_FILE`).
  This keeps user content out of `ps`, shell history, and process
  listings.
- **Env-var auth.** No API key ever appears in argv or in the rendered
  prompt. The plugin reads no key; the user supplies their own.
- **Write zone.** `.evidraft/reviews/` is the only path any external
  agent may write to. Enforced by the
  [`external-write-zone`](../../../plugins/scholar-ip/hooks/external-write-zone.md)
  hook with `failure_mode: block`.
- **Read-only flags where the host supports them.** Codex →
  `--sandbox read-only`. Claude bare →
  `--permission-mode dontAsk --allowedTools "Read"`.
- **Worktree / copy when not.** OpenCode runs against a throwaway
  worktree so the live project tree is never exposed to a non-sandboxed
  agent. The bridge skill describes the setup recipe.
- **Hard timeout.** 600 s default; SIGTERM then SIGKILL after 5 s.
- **`sensitive-file-guard` pre-check.** `target` is rejected if it
  matches `.env*`, `secrets/`, `**/*.pem`, `**/*.key`,
  `credentials.json`, or any project-defined forbidden path.

## v0.2 implementation direction — wrap-as-MCP

Two equivalent paths to consider when the stub is implemented:

- **[`mcp-agent`](https://github.com/lastmile-ai/mcp-agent)** — wrap
  each external agent as an MCP "agent server" and compose them as
  ordinary MCP tools. The bridge becomes a thin orchestrator over
  three uniform MCP backends.
- **Microsoft Agent Framework `.as_mcp_server()`** — a comparable
  wrap-an-agent-as-MCP path; useful when the external agent already
  ships as a framework component.

Either path keeps the public tool surface (`review_with`,
`list_supported_agents`, `parse_review_output`) frozen; only the
backend swaps.

Inspiration / prior art (idea-level only, not vendored):

- [`openai/codex-plugin-cc`](https://github.com/openai/codex) — Codex-as-a-Claude-Code-plugin pattern.
- [`hamelsmu/claude-review-loop`](https://github.com/hamelsmu/claude-review-loop) — Claude-on-Claude review loop.
- [`lastmile-ai/mcp-agent`](https://github.com/lastmile-ai/mcp-agent) — multi-agent MCP composition.

## Roadmap

- **v0.1** — this stub. Interfaces frozen, every tool raises
  `NotImplementedError("scheduled for v0.2 — see roadmap.md")`. The
  `/scholar:xreview` command drives the three CLIs directly via the
  shell.
- **v0.2** — implement `list_supported_agents` (static) and
  `review_with` (subprocess-orchestrated). Add token capture for Codex
  and Claude bare.
- **v0.3** — implement `parse_review_output` against the EviDraft
  review JSON envelope plus the three agent-native envelopes. Add a
  rolling cost ledger at `.evidraft/reviews/.cost.jsonl`.
- **v0.4** — wrap-as-MCP backend (`mcp-agent` or Agent Framework),
  keeping the public tool surface frozen.

## Enable in `.evidraft/project.yaml`

Until the implementation lands the server stays disabled. When v0.2
ships, opt in with:

```yaml
mcp:
  external-agent:
    enabled: true
    default_agent: codex   # or: claude-bare | opencode
    timeout_seconds: 600
```

See also [`docs/roadmap.md`](../../../docs/roadmap.md).
