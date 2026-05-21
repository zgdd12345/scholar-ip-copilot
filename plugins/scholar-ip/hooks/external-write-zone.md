---
id: external-write-zone
title: "External-agent write zone"
kind: hook
phase: shared
triggers:
  - "tool:Bash:codex*"
  - "tool:Bash:claude*"
  - "tool:Bash:opencode*"
behaviour: "Pin every external-agent subprocess to .evidraft/reviews/ as its sole write zone. Any file appearing elsewhere after the agent exits is treated as a sandbox escape and the call is rejected."
failure_mode: block
references:
  - doc: ../skills/external-agent-bridge/SKILL.md
  - doc: ../commands/xreview.md
  - doc: ../../../docs/legal-and-ethics.md
  - doc: ../plugin.yaml
---

# external-write-zone

## When it fires

Any tool call whose binary matches `codex`, `claude`, or `opencode`
(captured via the `Bash:codex*` / `Bash:claude*` / `Bash:opencode*`
allowed-tool patterns declared by `/scholar:xreview`), and any future
subprocess that delegates work to an external coding agent.

In Claude Code this is a `PostToolUse` hook on those Bash patterns. In
Codex CLI the rule is inlined into the prompt header for any prompt
that orchestrates an external agent. In OpenCode the equivalent
adapter is planned.

## Rule

External-agent output **MUST** sit under `.evidraft/reviews/`. Nothing
else may be created, modified, or deleted by the external agent.

Concretely:

1. The plugin precomputes `OUT_FILE = .evidraft/reviews/<agent>-<persona>-<ts>.md`
   and passes it to the agent as the only writable target:
   - Codex: `--output-last-message $OUT_FILE`,
   - Claude bare: shell redirect `> $OUT_FILE`,
   - OpenCode: shell redirect `> $OUT_FILE`.
2. Before the call, the hook snapshots the set of files under the
   project root (`git ls-files --others --modified` + mtimes of
   tracked files).
3. After the call, the hook diffs the snapshot. Any new or modified
   file whose path does not start with `.evidraft/reviews/` is treated
   as a sandbox escape.

## Detection logic

**Scoped snapshot** — do not scan the entire project tree (large `data/`, `manuscript/figures/`, etc. make full-tree snapshots costly). Use `git status --porcelain --untracked-files=all` post-call to enumerate only changed paths.

```
marker  = touch(/tmp/xreview-pre-marker)         # before subprocess
run     = invoke(agent, prompt_via_stdin)        # external agent runs
status  = git_status_porcelain()                 # cheap; lists changed paths only

# git status --porcelain prefixes (XY):
#   A , M ,  M , ??   -> create / modify / untracked      (kind=add)
#   D ,  D            -> delete                            (kind=del)
#   R , C             -> rename / copy                     (kind=both: old=del, new=add)
adds = paths_with_kind(status, "add") \
       + find(. -newer marker -not -path './.evidraft/reviews/*')
dels = paths_with_kind(status, "del")

violations = (
    [p for p in adds if not p.startswith(".evidraft/reviews/")] +
    [p for p in dels if not p.startswith(".evidraft/reviews/")]    # deletes are violations too
)

if violations:
    # additions: remove the stray files; deletions: restore from HEAD
    delete([p for p in violations if p in adds])
    for p in violations:
        if p in dels:
            run("git", "checkout", "HEAD", "--", p)               # restore from index
    block(reason="external-write-zone violation", paths=violations)
```

Cost: O(changed paths) regardless of repo size.

The hook also rejects any external-agent CLI invocation that:

- omits the controlled output path (`--output-last-message` for Codex
  or `> $OUT_FILE` for the others),
- targets a write path outside `.evidraft/reviews/`,
- runs OpenCode against `--dir $(pwd)` of the live tree when the
  project is not already inside a throwaway worktree (the bridge skill
  is responsible for setting up the worktree; this hook verifies the
  resolved `--dir` is not the live tree).

## Failure mode

`block` by default. On violation the calling agent sees:

```
external-write-zone: BLOCKED
  agent: <codex|claude-bare|opencode>
  invocation: <command-line, with keys and prompt content elided>
  violation_paths:
    - <path-outside-.evidraft/reviews/>
  reason: external agent wrote outside the pinned review zone
  remediation: re-run with the controlled output path, or downgrade
               the hook in .evidraft/project.yaml (warn-only).
```

The violating files are deleted before the message is returned (the
external agent never gets to retain a write outside the zone).

## Downgrade path

The hook is downgradable per-project. In `.evidraft/project.yaml`:

```yaml
hooks:
  external_write_zone: warn   # was: enabled (== block)
```

Under `warn`, the hook records every violation in
`.evidraft/reviews/.violations.log` (timestamp, agent, invocation
fingerprint with keys elided, violation paths) and lets the workflow
continue. **A stern log entry is written** explaining that an external
agent wrote outside the review zone and that the project has opted
into reduced isolation.

`audit`-only mode is **not** offered for this hook — either the zone is
enforced (`block`) or violations are at least surfaced (`warn`).

## Adapter notes

- **Claude Code** — `PostToolUse` hook on `Bash:codex*`,
  `Bash:claude*`, `Bash:opencode*`. The hook resolves the project
  root, snapshots before and after, deletes any violation paths, and
  returns `deny` with the message above. The pre-call check on
  `--dir` / `--output-last-message` runs as a lightweight
  `PreToolUse` companion on the same patterns.
- **Codex CLI** — Codex does not expose a host-level post-call hook.
  The rule is therefore prepended into every `/scholar:xreview` prompt
  header as a Guardrails note: "You may write only to `$OUT_FILE`
  under `.evidraft/reviews/`. Any other write is a protocol violation
  and will be discarded." The post-call snapshot-and-delete step is
  done by the orchestrating shell script.
- **OpenCode** — planned. Will register on the host's
  file-modification event when the adapter ships. Until then, OpenCode
  invocations are required to run inside a throwaway worktree
  (`external-agent-bridge/SKILL.md`), so violations only ever touch
  the worktree, not the live project.

## What this hook never does

- Allow a write outside `.evidraft/reviews/` to persist.
- Trust an external agent's claim that its output landed in the right
  place — it always verifies via filesystem diff.
- Log API keys or full prompt content; only an elided invocation
  fingerprint is recorded.
