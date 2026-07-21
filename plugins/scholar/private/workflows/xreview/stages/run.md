# workflow:xreview.run

Delegate a bounded review pass on `target` to an external coding agent
(`codex`, `claude-bare`, or `opencode`). The plugin resolves the chosen
EviDraft review mode (e.g. `novelty-critic`) to one of the six semantic
roles in `../../../roles/roles.yaml` and renders that role as the prompt,
attaches the target file's contents, and writes the agent's structured
output into `.evidraft/reviews/<agent>-<persona>-<ts>.md`.

The action is projectless: it runs from any safe working directory and
`.evidraft/project.yaml` is optional. It never requires an EviDraft scope or other
project metadata. The `.evidraft/reviews/` directory is a local review-artifact
namespace, not evidence that the target is an initialized project.

This command does **not** invent a new reviewer voice — it uses only
role and mode pairs declared in the shared role table. The external agent is
treated as a sandboxed second opinion, never as a privileged actor.

**Spec home.** `../../../capabilities/code/external-agent-bridge/spec.md` owns the CLI
invocation matrix, the prompt-rendering recipe, the security checklist,
timeout handling, and the cost-telemetry capture. This file
is the **executable contract** — orchestration, artefact layout, chat
output — that consumes that spec.

## Inputs

| Name | Type | Required | Notes |
|---|---|---|---|
| `agent` | enum `{codex, claude-bare, opencode}` | yes | Picks the CLI binary and the sandboxing strategy. |
| `target` | path | yes | File to be reviewed. Must not match `policy:workspace-safety` patterns. |
| `persona` | string | yes | EviDraft role mode; e.g. `novelty-critic`, `methodology-reviewer`. |
| `schema` | path | no | JSON schema the external agent should conform its output to (passed inline in the prompt). |
| `extra_context` | string | no | Short addendum appended to the rendered persona prompt. |

## Preconditions

1. `target` exists, is a regular file, and is **not** under `.env*`, `secrets/`, `**/*.pem`, `**/*.key`, or any path matched by `policy:workspace-safety`.
2. `persona` occurs exactly once under a semantic role in `../../../roles/roles.yaml`.
3. The required env var for `agent` is set (see "Auth" below). The user supplies their own keys; **no key ever appears in argv**.

## Auth

Per-agent env-var requirements are documented in
`../../../capabilities/code/external-agent-bridge/spec.md` §CLI invocation matrix (one
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

2. **Render the prompt.** Follow `../../../capabilities/code/external-agent-bridge/spec.md`
   §Prompt-rendering recipe (header → semantic role + full private mode spec → optional schema →
   optional extra context → target file). Write the result to
   `$PROMPT_FILE`.

3. **Invoke the external agent.** Use the verbatim CLI signature for
   the chosen `agent` from `../../../capabilities/code/external-agent-bridge/spec.md`
   §CLI invocation matrix. The three signatures (Codex / Claude bare /
   OpenCode) are parameterised on `$WORKDIR`, `$OUT_FILE`,
   `$PROMPT_FILE`, and `$TARGET_FILE=target`. For `opencode`, follow
   the worktree-copy mitigation in the skill (OpenCode has no native
   read-only sandbox) before invocation.
   - Choose any follow-up invocation adaptively from target complexity and the
     returned quality/error signal. Use no fixed cardinality, waves, or retry count;
     stop after a useful review or a terminal auth, safety, timeout, or cost limit.

4. **Enforce the fixed write zone.** Run `policy:workspace-safety` preflight before
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

Source of truth: `../../../capabilities/code/external-agent-bridge/spec.md` §Security checklist. The invocation MUST satisfy every item there (no key in argv; stdin-only prompts; policy:workspace-safety on target; fixed write zone locked to `.evidraft/reviews/`; per-agent read-only flags; 600 s hard timeout with SIGTERM→SIGKILL escalation; no nested invocation).

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
- `target` blocked by `policy:workspace-safety` → abort; surface the policy
  message.
- External agent non-zero exit, parse failure, or timeout → preserve any safe raw
  response, record `tokens`/`cost_usd` as available, and surface the exit code or
  timeout reason. Retry only when the failure is recoverable and another invocation
  is justified; never use a predeclared retry count.
- `policy:workspace-safety` violation → block; delete any file the external
  agent created outside `.evidraft/reviews/`; abort.

## Done criteria

- `.evidraft/reviews/<agent>-<persona>-<ts>.md` exists and is non-empty.
- `.evidraft/reviews/.last.yaml` reflects this invocation.
- No file outside `.evidraft/reviews/` was written by the external
  agent.
- Chat output prints agent, persona, output path, token cost (if
  reported), and the top-3 findings extracted from the structured
  output.
- Status is `complete`, `complete_with_gaps` for usable raw/partial output, or
  `blocked` for auth, safety, timeout-without-output, or an unreadable target.
