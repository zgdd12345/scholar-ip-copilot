---
id: external-agent-bridge
title: "External-agent bridge — CLI invocation matrix and security recipe"
kind: skill
phase: shared
description: >
  Single source of truth for delegating an EviDraft review task to another
  coding agent (Codex CLI or Claude bare) and refusing OpenCode until it has
  a verified read-only sandbox. Defines the runnable CLI signatures, the sandboxing posture, the prompt-rendering recipe,
  the security checklist, the adaptive follow-up/timeout protocol, and the cost
  telemetry capture.
triggers:
  - "when workflow:xreview.run runs"
  - "when an existing review command receives --fanout <agent>"
  - "when the user asks 'how do I get a second opinion from <other agent>?'"
provides:
  - "CLI invocation matrix for codex / claude-bare and fail-closed status for opencode"
  - "prompt-rendering recipe (semantic role + mode + target file + optional schema)"
  - "security checklist (stdin-only prompts, env-var auth, write-zone pin)"
  - "adaptive follow-up / timeout protocol"
  - "cost telemetry capture (tokens, cost_usd)"
allowed_tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - "Bash:codex*"
  - "Bash:claude*"
policies: [workspace-safety]
references:
  - doc: ../../../roles/roles.yaml
  - doc: ../../../policies/policy.yaml
  - url: "https://github.com/openai/codex"
  - url: "https://github.com/hamelsmu/claude-review-loop"
  - url: "https://github.com/lastmile-ai/mcp-agent"
---

# external-agent-bridge

<EXTREMELY-IMPORTANT>
When `workflow:xreview.run` runs, follow this skill exactly. Never invent
CLI flags. Never put a key or user content in argv. Never let the
external agent write outside `.evidraft/reviews/`.
</EXTREMELY-IMPORTANT>

This skill is the implementation contract for `workflow:xreview.run` and for
any future `--fanout <agent>` mode on `workflow:paper.review` and
`workflow:patent.review`.

## CLI invocation matrix

The two runnable invocations below are **verbatim** — the `xreview.run`
workflow stage and any adapter MUST use them exactly. OpenCode has no runnable
invocation until a verified OS-enforced read-only contract is available.

### Codex (safest — hard-locked read-only)

```
codex exec --sandbox read-only --json -C $WORKDIR --output-last-message $OUT_FILE - < $PROMPT_FILE
```

- `--sandbox read-only` — Codex's hardest sandbox; the agent cannot
  modify the filesystem.
- `--json` — structured event stream on stdout.
- `-C $WORKDIR` — pin the working directory.
- `--output-last-message $OUT_FILE` — write the final assistant
  message to a path we control.
- `-` — read the prompt from stdin.
- `< $PROMPT_FILE` — feed the rendered prompt via stdin (never via
  argv).
- Env: `CODEX_API_KEY` (or `OPENAI_API_KEY`, depending on the Codex CLI
  build the user has installed).
- Read-only is enforced by Codex itself, not by us — this is the
  preferred agent when available.

### Claude bare

```
claude --bare --permission-mode dontAsk --allowedTools "Read" --output-format json -p < "$PROMPT_FILE" > "$OUT_FILE"
```

- `--bare` — strip the interactive UI; run a single non-interactive
  turn.
- `-p < "$PROMPT_FILE"` — print mode reads the rendered prompt from
  stdin; prompt bytes never become a process argument.
- `--permission-mode dontAsk` paired with `--allowedTools "Read"` —
  Claude bare's read-only posture. The agent may read but not write,
  edit, or execute shell.
- `--output-format json` — structured envelope on stdout, captured to
  `$OUT_FILE`.
- Env: `ANTHROPIC_API_KEY`.

### OpenCode (unavailable — fail closed)

OpenCode has no verified stdin plus OS-enforced read-only sandbox contract in
the supported CLI. `xreview.run` therefore returns `status: blocked` before
checking provider auth, creating review paths, rendering or copying prompt or
project data, or launching a process. A directory flag, disposable project
copy, or post-run file-manifest comparison is not an isolation boundary.

## Prompt-rendering recipe

The prompt fed to every agent is a single UTF-8 markdown file written
to `.evidraft/reviews/.tmp/<agent>-<persona>-<ts>.prompt`. It is built
deterministically:

1. **Header** (fixed):
   ```
   You are reviewing the file: <target>
   Persona: <persona>
   Output: respond ONLY with a JSON object matching the schema below
   (or, if no schema is attached, a JSON object with keys
   {"findings": string[], "top3": string[], "verdict": string,
    "tokens": int|null, "cost_usd": number|null}).
   Do not write to the filesystem. Do not run shell commands.
   ```
2. **Semantic role and mode** — resolve `<persona>` as a mode that occurs
   exactly once in `../../../roles/roles.yaml`, follow its `mode_specs` entry,
   and attach the **entire** `../../../roles/modes/<persona>.md` frontmatter and
   body after the matching role description, role id, mode, and requested tier.
   Abort if the mapping or file is missing. This capability never invents
   reviewer voices or accepts undeclared modes.
3. **Optional schema** — if `schema` is provided, attach its contents
   inside a fenced ```json block under a `## Output schema` heading.
4. **Optional extra context** — if `extra_context` is provided, attach
   it verbatim under a `## Extra context` heading.
5. **Target file** — under a `## Target file` heading, attach the full
   UTF-8 contents of `target` inside a fenced code block whose language
   tag matches the file extension (default `text`).

Never interpolate user content into a shell command. The prompt is delivered
via stdin for both runnable agents. OpenCode is refused before prompt rendering.

## Security checklist

- [ ] **No key in argv.** All auth comes from env vars
      (`CODEX_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, etc.).
      The plugin never reads, logs, or echoes a key.
- [ ] **No user content in argv.** Codex and Claude bare use stdin. The
      prompt file is mode 0600. OpenCode is never launched.
- [ ] **Read-only flags applied where supported.** Codex →
      `--sandbox read-only`; Claude bare →
      `--permission-mode dontAsk --allowedTools "Read"`.
- [ ] **Write zone pinned.** `policy:workspace-safety` preflight with
      `failure_mode: block` rejects any file appearing outside
      `.evidraft/reviews/` after the invocation. This post-check is defense in
      depth for already sandboxed agents, not a substitute for process isolation.
- [ ] **`policy:workspace-safety` pre-check.** Reject if `target` matches
      `.env*`, `secrets/`, `**/*.pem`, `**/*.key`,
      `credentials.json`, or any project-defined forbidden path.
- [ ] **Hard timeout.** 600 seconds per invocation. On timeout, kill
      the subprocess (`SIGTERM`, then `SIGKILL` after 5 s), keep
      whatever was written to `$OUT_FILE`, and surface a timeout
      message.
- [ ] **No nested invocation.** `workflow:xreview.run` may not call
      `workflow:xreview.run` again from inside the external agent's
      response.

## Adaptive follow-up / timeout protocol

Choose follow-up invocations from the task complexity and the returned
quality/error signal. There is no fixed retry count: stop after a useful review or
after a terminal auth, safety, timeout, or cost-limit result.

| Condition | Action |
|---|---|
| Exit code 0, valid JSON output | Parse and continue. |
| Exit code 0, parse fails | Preserve raw output, prepend a parse-failure note, continue. |
| Exit code != 0 within timeout | Preserve the stderr tail and classify whether the error is recoverable. Invoke again only when another attempt is justified by the task and error signal; otherwise report the exit code. |
| Timeout (600 s) | Kill subprocess; do not retry; surface "timed out after 600s". |
| `policy:workspace-safety` violation | Block; delete any file the external agent wrote outside `.evidraft/reviews/`; do not retry. |

Follow-up invocations do not reuse cost: every attempt's `tokens` / `cost_usd`
is added to the telemetry record.

## Cost telemetry capture

Each agent reports cost differently. Capture what is available; record
`null` otherwise.

| Agent | How to extract |
|---|---|
| `codex` | `--json` stream emits a `session.summary` event at the end with `input_tokens`, `output_tokens`, and `usd_cost`. Sum into the telemetry record. |
| `claude-bare` | `--output-format json` envelope includes a `usage` block (`input_tokens`, `output_tokens`). Record tokens; leave `cost_usd: null` until a pricing table lands in `packages/mcp/README.md` (v0.3+). |
| `opencode` | Not invoked. Return `status: blocked` with `tokens: null` and `cost_usd: null`. |

Telemetry is appended to `.evidraft/reviews/.last.yaml` and (in v0.2)
to a rolling `.evidraft/reviews/.cost.jsonl` ledger.

## Future MCP-bridge pattern (v0.2 direction)

The same matrix can be exposed as MCP tools, so any MCP-aware host
(Claude Code, Codex CLI, OpenCode, generic IDEs) can call `review_with`
without re-implementing the CLI plumbing. Two patterns are in scope:

- **`mcp-agent`** ([lastmile-ai/mcp-agent](https://github.com/lastmile-ai/mcp-agent))
  — wrap each external agent as an MCP "agent server" so the bridge
  composes them as ordinary MCP tools.
- **Microsoft Agent Framework `.as_mcp_server()`** — a comparable
  wrap-an-agent-as-MCP path; useful when the external agent already
  ships as a framework component.

When MCP wiring lands (v0.3+, tracked in `packages/mcp/README.md`),
three tool functions are anticipated — `review_with`,
`list_supported_agents`, `parse_review_output` — so the host integration
can be reviewed before any network or subprocess code is committed.

Inspiration / prior art (idea-level only, not vendored):

- `openai/codex-plugin-cc` — Codex-as-a-Claude-Code-plugin pattern.
- `hamelsmu/claude-review-loop` — Claude-on-Claude review loop.
- `lastmile-ai/mcp-agent` — multi-agent MCP composition.

## What this skill never does

- Invent a new persona. Always resolve a declared mode from the shared role table.
- Allow the external agent to write outside `.evidraft/reviews/`.
- Pass API keys, prompts, or target content through `argv` in a way
  that could leak to `ps`, shell history, or process listing.
- Skip the `policy:workspace-safety` pre-check on `target`.
- Run OpenCode against the live project tree.
