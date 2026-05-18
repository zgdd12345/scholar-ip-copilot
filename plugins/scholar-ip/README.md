# `scholar-ip` plugin (EviDraft)

Platform-neutral source for the EviDraft plugin (id: `scholar`). Adapters under
`packages/adapters/*` render this tree into Claude Code / Codex CLI / OpenCode
formats. Hosts invoke commands as `/scholar:<cmd>`.

| Folder       | What lives here |
|--------------|-----------------|
| `commands/`  | 16 slash commands: `/scholar:using`, `/scholar:paper-*` (×9), `/scholar:patent-*` (×6) |
| `agents/`    | 9 specialist subagents |
| `skills/`    | 8 reusable skills (literature-review, evidence-check, codebase-audit, experiment-analysis, latex-writing, patent-disclosure, patent-claims, venue-formatting) + `using-scholar-ip-copilot` orientation |
| `hooks/`     | 4 guardrail specs (citation-guard, evidence-consistency, latex-compile, sensitive-file-guard) |
| `templates/` | `paper-project/` and `patent-project/` scaffolds materialised by `/scholar:paper-init` and `/scholar:patent-init` |
| `plugin.yaml`| Top-level manifest |

See [`../../docs/plugin-format.md`](../../docs/plugin-format.md) for the file
contract and [`../../docs/architecture.md`](../../docs/architecture.md) for how
the layers fit together.

## Naming convention

- **Plugin id**: `scholar` (set in `plugin.yaml`).
- **Plugin folder**: `plugins/scholar-ip/` (ties to repo name `scholar-ip-copilot`).
- **Slash invocation**: `/scholar:<cmd>` — colon-namespaced, idiomatic for Claude Code (mirrors `superpowers:<skill>`).
- **Filenames**: bare `<cmd>.md` (no prefix) — namespace is implicit from plugin id; keeps filenames Windows-safe.
- **Meta entry**: `/scholar:using` loads the `using-scholar-ip-copilot` orientation skill.
