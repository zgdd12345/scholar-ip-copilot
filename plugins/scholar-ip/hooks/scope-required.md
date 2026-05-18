---
id: scope-required
title: "Scope required"
kind: hook
phase: shared
triggers:
  - "command:/scholar:paper-idea"
  - "command:/scholar:patent-scout"
  - "command:/scholar:paper-draft"
  - "command:/scholar:patent-claims"
  - "command:/scholar:deepresearch"
  - "command:/scholar:polish"
behaviour: "Refuse to run downstream creative commands without an approved, non-stale scope file under .evidraft/scope/."
failure_mode: block
references:
  - doc: ../skills/brainstorming/SKILL.md
  - doc: ../commands/brainstorming.md
  - doc: ../skills/using-scholar-ip-copilot/SKILL.md
---

# scope-required

## When it fires

Before any of the following commands begin work:

- `/scholar:paper-idea`
- `/scholar:patent-scout`
- `/scholar:paper-draft`
- `/scholar:patent-claims`
- `/scholar:deepresearch` (forward-compat, Phase 2)
- `/scholar:polish` (forward-compat, Phase 2)

Other commands (`/scholar:paper-init`, `/scholar:patent-init`, `/scholar:paper-lit`, `/scholar:patent-prior-art`, `/scholar:patent-disclosure`, `/scholar:paper-review`, `/scholar:paper-code-audit`, `/scholar:paper-experiment`, `/scholar:paper-check`, `/scholar:patent-review`, `/scholar:paper-venue`, `/scholar:xreview`, `/scholar:using`) are **not** gated by this hook. `/scholar:brainstorming` itself is exempt — it creates the scope file.

## Rules

The hook passes only if **all three** conditions hold:

1. **Existence.** At least one file matches `.evidraft/scope/*.md`. If there are several, the most recently modified is used (resolved via filename `YYYY-MM-DD-<slug>.md` then mtime as tiebreaker).
2. **Approval.** The selected file's YAML frontmatter has `status: approved`. Any file at `status: draft` is treated as missing.
3. **Freshness.** `(today - approved_date) <= staleness_days`. Default `staleness_days` is `14`, overridable in `.evidraft/project.yaml`:
   ```yaml
   scope:
     staleness_days: 14
   ```
   If `approved_date` is missing on an `approved` file, the file is treated as stale.

`evidence_seeds`, `verdict`, and `riskiest_assumption` are **not** enforced by this hook — they are owned by the brainstorming skill. This hook only gates on existence, approval, and freshness.

## Failure mode

`block` by default — the downstream command is refused with:

```
scope-required: BLOCKED
  command: <slash>
  reason: <missing | draft-only | stale>
  detail:
    scope_dir: .evidraft/scope/
    latest_file: <path or "(none)">
    status: <draft | approved | (missing)>
    approved_date: <YYYY-MM-DD or "(unset)">
    staleness_until: <YYYY-MM-DD or "(unset)">
    today: <YYYY-MM-DD>
  suggestion: run /scholar:brainstorming to (re)establish scope before retrying
```

### Downgrade path

Users may downgrade this hook in `.evidraft/project.yaml`:

```yaml
# .evidraft/project.yaml
hooks:
  scope_required: warn      # one of: block (default) | warn | disabled
```

- `warn` — the downstream command proceeds, but a bypass entry is appended to the relevant check report (`paper_check_report.md` for paper-side commands, `patent_review_report.md` for patent-side commands) under "scope-required downgraded bypass", recording the command, the reason (`missing | draft-only | stale`), and the timestamp.
- `disabled` — the hook does not run; the same bypass entry is still appended to the relevant check report so the audit trail survives.

Downgrade is per-project, not per-command. There is no per-command override.

## Adapter notes

- **Claude Code** — register as a `PreToolUse` hook on the gated slash-commands. The hook reads `.evidraft/project.yaml` once (for `scope.staleness_days` and `hooks.scope_required`), globs `.evidraft/scope/*.md`, parses the frontmatter of the selected file, and either returns `block` (with the message above) or appends a bypass row to the relevant check report.
- **Codex CLI** — Codex does not expose a tool-level hook; the adapter prepends a *Guardrails* note to each gated command prompt that re-states the three rules above and instructs the model to refuse with the same `scope-required: BLOCKED` block if any rule fails. The note also points the user at `/scholar:brainstorming`.
- **OpenCode** — planned; the rule will register on the host's command-dispatch event, mirroring the Claude Code logic.

## What this hook never does

- Validate the *content* of the scope file (verdict, riskiest assumption, evidence seeds) — that is the brainstorming skill's job.
- Modify the scope file. Read-only.
- Block `/scholar:brainstorming` itself (that command creates the file).
- Block initialisation commands (`/scholar:paper-init`, `/scholar:patent-init`) — initialisation precedes scope.
