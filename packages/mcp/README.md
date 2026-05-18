# MCP layer (reserved — v0.3+)

**Status.** v0.1 / v0.2 ship retrieval and tooling as **skills** under
`plugins/scholar-ip/skills/`, which use the host's built-in `WebSearch`,
`WebFetch`, and `Bash`. MCP servers are reserved for v0.3+ as an
optional offline / deterministic backend.

## Migration: former MCP stub → replacement skill

| Former MCP stub (deleted) | Replacement skill (v0.2) |
|---|---|
| `scholar-search-mcp` | [`plugins/scholar-ip/skills/scholar-search/`](../../plugins/scholar-ip/skills/scholar-search/SKILL.md) |
| `bib-manager-mcp` | [`plugins/scholar-ip/skills/bib-manager/`](../../plugins/scholar-ip/skills/bib-manager/SKILL.md) |
| `latex-build-mcp` | [`plugins/scholar-ip/skills/latex-build/`](../../plugins/scholar-ip/skills/latex-build/SKILL.md) |
| `code-intel-mcp` | [`plugins/scholar-ip/skills/code-intel/`](../../plugins/scholar-ip/skills/code-intel/SKILL.md) |
| `experiment-mcp` | [`plugins/scholar-ip/skills/experiment-analysis/`](../../plugins/scholar-ip/skills/experiment-analysis/SKILL.md) (already existed) |
| `patent-search-mcp` | [`plugins/scholar-ip/skills/patent-search/`](../../plugins/scholar-ip/skills/patent-search/SKILL.md) |
| `external-agent-mcp` | [`plugins/scholar-ip/skills/external-agent-bridge/`](../../plugins/scholar-ip/skills/external-agent-bridge/SKILL.md) (already existed) |

## Rationale

Skills are host-portable (Claude Code / Codex / OpenCode all expose
`WebSearch` / `WebFetch` / `Bash`), evolve with upstream API changes
without code churn, and avoid maintaining seven boilerplate MCP stubs
that simply re-export the same host primitives. MCP comes back in v0.3+
when there are concrete offline / CI / determinism requirements that
the host-tool skills cannot meet.

## If you want an MCP backend for skill X

Copy the relevant skill body and re-implement its `WebFetch` / `Bash`
calls as MCP tool functions. The **skill remains the contract** — the
MCP server is one of potentially many backends that satisfy it.
