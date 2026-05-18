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
  policy: "At command start, prune review files older than max_age_days OR beyond keep_last entries (whichever cuts more). .last.yaml always retained."
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

## Auth (env vars only — never on the command line)

| Agent | Required env vars |
|---|---|
| `codex` | `CODEX_API_KEY` (or `OPENAI_API_KEY`, depending on the Codex CLI build the user has installed). |
| `claude-bare` | `ANTHROPIC_API_KEY`. |
| `opencode` | One of the OpenCode-supported provider keys (e.g. `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`); see OpenCode docs. |

The plugin **reads no key** and **echoes no key**. If the required env var
is unset, abort with a one-line message and instruct the user to set it
in their shell.

## Steps

1. **Resolve identifiers.**
   - `TS="$(date -u +%Y%m%dT%H%M%SZ)"`.
   - `WORKDIR="$(pwd)"` (project root).
   - `OUT_FILE=".evidraft/reviews/${agent}-${persona}-${TS}.md"`.
   - `PROMPT_FILE=".evidraft/reviews/.tmp/${agent}-${persona}-${TS}.prompt"`.
   - Create `.evidraft/reviews/` and `.evidraft/reviews/.tmp/` if missing.

2. **Render the prompt.** Write `PROMPT_FILE` as the concatenation of:
   - a fixed header:
     ```
     You are reviewing the file: <target>
     Persona: <persona>
     Output: respond ONLY with a JSON object matching the schema below
     (or, if no schema is attached, a JSON object with keys
     {"findings": string[], "top3": string[], "verdict": string,
      "tokens": int|null, "cost_usd": number|null}).
     Do not write to the filesystem. Do not run shell commands.
     ```
   - the body of `plugins/scholar-ip/agents/<persona>.md` **after** its
     YAML frontmatter (strip the frontmatter; keep the markdown body),
   - if `schema` is provided: a fenced ```json block containing its
     contents,
   - if `extra_context` is provided: a `## Extra context` section with
     that string verbatim,
   - a `## Target file` section containing the full UTF-8 contents of
     `target` inside a fenced code block whose language matches the
     file extension (default `text`).

   Never interpolate `target` contents into a shell command. The prompt
   is always passed to the external agent via stdin or
   `"$(cat $PROMPT_FILE)"`.

3. **Invoke the external agent.** Use **exactly one** of the three
   invocations below. Each is parameterised on `$WORKDIR`, `$OUT_FILE`,
   `$PROMPT_FILE`, and `$TARGET_FILE=target`.

   - **Codex (safest — hard-locked read-only):**
     ```
     codex exec --sandbox read-only --json -C $WORKDIR --output-last-message $OUT_FILE - < $PROMPT_FILE
     ```
   - **Claude bare:**
     ```
     claude --bare -p "$(cat $PROMPT_FILE)" --permission-mode dontAsk --allowedTools "Read" --output-format json > $OUT_FILE
     ```
   - **OpenCode (no native read-only — run against a copy / worktree):**
     ```
     opencode run --format json --dir $WORKDIR -f $TARGET_FILE "$(cat $PROMPT_FILE)" > $OUT_FILE
     ```

   For `opencode`, before invocation copy the project to a throwaway
   worktree (`git worktree add` or `cp -R` to a tmp dir) and set
   `$WORKDIR` to that worktree path; treat the original tree as
   read-only. See `external-agent-bridge/SKILL.md` for the recipe.

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

Source of truth: `skills/external-agent-bridge/SKILL.md` §Security checklist. The invocation MUST satisfy every item there (no key in argv; stdin-only prompts; sensitive-file-guard on target; write zone locked to `.evidraft/reviews/`; per-agent read-only flags; 600 s hard timeout with SIGTERM→SIGKILL escalation; no nested invocation).

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
- External agent non-zero exit → keep `$OUT_FILE` (it may contain a
  partial response), set `tokens`/`cost_usd` to `null` in `.last.yaml`,
  and surface the exit code in the chat output.
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
