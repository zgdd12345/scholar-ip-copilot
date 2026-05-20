---
id: xreview
title: "Delegate a review to an external coding agent"
kind: command
slash: /scholar:xreview
phase: shared
description: >
  Delegate a single review pass on a target file to another coding agent
  (Codex, Claude bare, or OpenCode) for a second opinion. The chosen
  EviDraft persona body is rendered as the prompt. Output lands under
  .evidraft/reviews/ only.
inputs:
  - name: agent
    type: enum
    values: [codex, claude-bare, opencode]
    description: "Which external coding agent to delegate to."
  - name: target
    type: path
    description: "File the external agent should review."
  - name: persona
    type: string
    description: "EviDraft agent id whose body is rendered as the prompt (e.g. novelty-critic, methodology-reviewer)."
  - name: schema
    type: path
    optional: true
    description: "Optional JSON schema the external agent should conform its output to."
  - name: extra_context
    type: string
    optional: true
    description: "Short free-text addendum appended to the rendered persona prompt."
outputs:
  - path: .evidraft/reviews/<agent>-<persona>-<ts>.md
    description: "Markdown review file produced from the external agent's structured output."
  - path: .evidraft/reviews/.last.yaml
    description: "Index of the most recent xreview invocation (agent, persona, target, output_path, ts, tokens, cost_usd)."
retention:
  keep_last: 50
  max_age_days: 180
allowed_tools:
  - "Bash:codex*"
  - "Bash:claude*"
  - "Bash:opencode*"
  - Read
  - Glob
  - Grep
  - Write
  - Edit
forbidden_tools:
  - "Bash:rm -rf*"
  - "Bash:sudo*"
  - "Bash:curl*"
  - "Bash:wget*"
  - "Bash:scp*"
  - "Bash:ssh*"
hooks: [scope-required, sensitive-file-guard, external-write-zone]
subagents: []
references:
  - doc: ../skills/external-agent-bridge/SKILL.md
  - doc: ../hooks/external-write-zone.md
  - doc: ../hooks/sensitive-file-guard.md
  - doc: ../../../docs/roadmap.md
---

# /scholar:xreview

Delegate a *single* review pass on `target` to an external coding agent
(`codex`, `claude-bare`, or `opencode`). The plugin renders the chosen
EviDraft persona's body (e.g. `agents/novelty-critic.md`) as the prompt,
attaches the target file's contents, and writes the agent's structured
output into `.evidraft/reviews/<agent>-<persona>-<ts>.md`.

This command does **not** invent a new reviewer voice — it reuses the
persona bodies that already ship with the plugin. The external agent is
treated as a sandboxed second opinion, never as a privileged actor.

**Spec home.** `../skills/external-agent-bridge/SKILL.md` owns the CLI
invocation matrix, the prompt-rendering recipe, the security checklist,
the retry/timeout protocol, and the cost-telemetry capture. This file
is the **executable contract** — orchestration, artefact layout, chat
output — that consumes that spec.

## Inputs

| Name | Type | Required | Notes |
|---|---|---|---|
| `agent` | enum `{codex, claude-bare, opencode}` | yes | Picks the CLI binary and the sandboxing strategy. |
| `target` | path | yes | File to be reviewed. Must not match `sensitive-file-guard` patterns. |
| `persona` | string | yes | EviDraft agent id; e.g. `novelty-critic`, `methodology-reviewer`. |
| `schema` | path | no | JSON schema the external agent should conform its output to (passed inline in the prompt). |
| `extra_context` | string | no | Short addendum appended to the rendered persona prompt. |

## Preconditions

1. `.evidraft/project.yaml` exists (otherwise route the user to `/scholar:paper-init` or `/scholar:patent-init`).
2. `scope-required` hook is satisfied (Phase 2 scope file present when project requires it).
3. `target` exists, is a regular file, and is **not** under `.env*`, `secrets/`, `**/*.pem`, `**/*.key`, or any path matched by `sensitive-file-guard`.
4. `plugins/scholar-ip/agents/<persona>.md` exists.
5. The required env var for `agent` is set (see "Auth" below). The user supplies their own keys; **no key ever appears in argv**.

## Auth

Per-agent env-var requirements are documented in
`../skills/external-agent-bridge/SKILL.md` §CLI invocation matrix (one
`Env:` line per agent). The plugin **reads no key** and **echoes no
key**. If the required env var is unset, abort with a one-line message
and instruct the user to set it in their shell.

## Steps

1. **Resolve identifiers.**
   - `TS="$(date -u +%Y%m%dT%H%M%SZ)"`.
   - `WORKDIR="$(pwd)"` (project root).
   - `OUT_FILE=".evidraft/reviews/${agent}-${persona}-${TS}.md"`.
   - `PROMPT_FILE=".evidraft/reviews/.tmp/${agent}-${persona}-${TS}.prompt"`.
   - Create `.evidraft/reviews/` and `.evidraft/reviews/.tmp/` if missing.

2. **Render the prompt.** Follow `../skills/external-agent-bridge/SKILL.md`
   §Prompt-rendering recipe (header → persona body → optional schema →
   optional extra context → target file). Write the result to
   `$PROMPT_FILE`.

3. **Invoke the external agent.** Use the verbatim CLI signature for
   the chosen `agent` from `../skills/external-agent-bridge/SKILL.md`
   §CLI invocation matrix. The three signatures (Codex / Claude bare /
   OpenCode) are parameterised on `$WORKDIR`, `$OUT_FILE`,
   `$PROMPT_FILE`, and `$TARGET_FILE=target`. For `opencode`, follow
   the worktree-copy mitigation in the skill (OpenCode has no native
   read-only sandbox) before invocation.

4. **Enforce the write zone.** The `external-write-zone` hook fires on
   the `Bash:codex*` / `Bash:claude*` / `Bash:opencode*` tool call.
   - The only writable target is `$OUT_FILE` under
     `.evidraft/reviews/`.
   - Reject the call if any new file appears outside
     `.evidraft/reviews/` after the agent exits.

5. **Parse the structured output.** Read `$OUT_FILE`:
   - If it is valid JSON (per `parse_review_output` shape):
     `{findings: string[], top3: string[], verdict?: string,
       tokens?: int, cost_usd?: number}`, render a markdown file at
     the same path with sections `# Findings`, `# Top 3`, `# Verdict`,
     `# Cost`.
   - If it is the raw JSON envelope produced by `codex exec --json` or
     `claude --output-format json`, extract the assistant's final
     message and apply the same parse.
   - On parse failure: preserve the raw output verbatim in `$OUT_FILE`,
     prepend a `> NOTE: structured-output parse failed; raw output
     below.` line, and continue.

6. **Update `.evidraft/reviews/.last.yaml`.** Append (or overwrite a
   single-record file) with:
   ```yaml
   agent: <agent>
   persona: <persona>
   target: <target>
   output_path: <OUT_FILE>
   ts: <TS>
   tokens: <int|null>
   cost_usd: <number|null>
   ```

7. **Clean up.** Delete `$PROMPT_FILE` and the `.evidraft/reviews/.tmp/`
   directory if empty.

## Security checklist

Source of truth: `../skills/external-agent-bridge/SKILL.md` §Security checklist. The invocation MUST satisfy every item there (no key in argv; stdin-only prompts; sensitive-file-guard on target; write zone locked to `.evidraft/reviews/`; per-agent read-only flags; 600 s hard timeout with SIGTERM→SIGKILL escalation; no nested invocation).

## Chat output (what the user sees at the end)

Print exactly:

```
agent:    <agent>
persona:  <persona>
target:   <target>
output:   <OUT_FILE>
tokens:   <int|"n/a">
cost_usd: <number|"n/a">

Top 3 findings:
1. <finding 1>
2. <finding 2>
3. <finding 3>
```

If the parse failed, replace the "Top 3" block with:
`(structured output unavailable — see <OUT_FILE> for the raw response)`.

## Failure modes

- Missing env var → abort with a one-line message; do not invoke.
- `target` blocked by `sensitive-file-guard` → abort; surface the hook
  message.
- External agent non-zero exit, parse failure, or timeout → handle per
  `../skills/external-agent-bridge/SKILL.md` §Retry / timeout protocol.
  Record `tokens`/`cost_usd` as available; surface exit code / timeout
  reason in the chat output.
- `external-write-zone` violation → block; delete any file the external
  agent created outside `.evidraft/reviews/`; abort.

## Done criteria

- `.evidraft/reviews/<agent>-<persona>-<ts>.md` exists and is non-empty.
- `.evidraft/reviews/.last.yaml` reflects this invocation.
- No file outside `.evidraft/reviews/` was written by the external
  agent.
- Chat output prints agent, persona, output path, token cost (if
  reported), and the top-3 findings extracted from the structured
  output.
