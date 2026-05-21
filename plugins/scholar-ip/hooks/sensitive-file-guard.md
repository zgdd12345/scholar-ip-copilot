---
id: sensitive-file-guard
title: "Sensitive file guard"
kind: hook
phase: shared
triggers:
  - "read:.env"
  - "read:**/.env"
  - "read:**/.env.*"
  - "read:secrets/**"
  - "read:credentials.json"
  - "read:**/*.pem"
  - "read:**/*.key"
  - "read:**/id_rsa*"
  - "read:<safety.forbidden_paths>"
behaviour: "Deny reads of secrets, credentials, and key material by default; require an explicit, single-shot user confirmation to override."
failure_mode: block
references:
  - doc: ../../../docs/legal-and-ethics.md
  - doc: ../plugin.yaml
---

# sensitive-file-guard

## When it fires

Any `Read`, `Glob`, `Grep`, or `Bash:cat*` / `Bash:ls*` invocation whose target path matches any pattern in:

- the built-in list (above): `.env`, `**/.env*`, `secrets/`, `credentials.json`, `**/*.pem`, `**/*.key`, `**/id_rsa*`,
- the project-defined extension list under `.evidraft/project.yaml` → `safety.forbidden_paths` (which inherits from `plugin.yaml` → `safety.forbidden_paths`).

Matching is glob-style and case-sensitive on POSIX, case-insensitive on Windows-style FS reports.

## Rules

1. **Default behaviour is deny.** The tool call is intercepted before the file system is touched; no bytes from the target ever enter the agent context.
2. **Override is single-shot.** The user can grant a one-time override per session with an explicit message of the form:

   ```
   /override sensitive-file-guard --path <exact-path> --reason "<one-line reason>"
   ```

   The override applies to **exactly that path** for the next read attempt only. It does not whitelist the path for the rest of the session.
3. **No silent escalation.** An agent may *propose* an override and ask the user — it may not auto-issue one, even if the user previously approved a similar path.
4. **Read of an overridden file is logged.** The override and the resulting read are appended to `.evidraft/audit/sensitive_reads.log` with timestamp, requesting agent id, and reason.
5. **Writes** to forbidden paths are always blocked, with no override.

## Failure mode

`block` — the tool call returns an error to the calling agent:

```
sensitive-file-guard: BLOCKED
  path: <path>
  matched: <pattern>
  reason: forbidden by safety.forbidden_paths
  override: send `/override sensitive-file-guard --path <path> --reason "<reason>"`
```

`failure_mode` is not downgradable in `.evidraft/project.yaml`; the only way to read is the explicit per-call override above. Removing the rule from `plugin.yaml` is treated as a security-significant change and requires manual edit by the user.

## Adapter notes

- **Claude Code** — register as a `PreToolUse` hook on `Read`, `Glob`, `Grep`, and the Bash command patterns. The hook resolves the target path, matches against the union of `plugin.yaml`'s and the project's `safety.forbidden_paths`, and returns `deny` with the message above. Override is implemented as a session-scoped one-shot token.
- **Codex CLI** — Codex commands inline the rule into every `allowed_tools`-bearing prompt and refuse to issue a Read against matching paths. The override command is documented in the user's project README on `/scholar:paper-init` / `/scholar:patent-init`.
- **OpenCode** — planned; will register on the host's pre-read event.
