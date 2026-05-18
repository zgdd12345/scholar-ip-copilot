"""MCP server stub: external-agent.

This module declares the tool interface for the ``external-agent-mcp``
MCP server. All tools are stubs in v0.1 and raise
:class:`NotImplementedError`. Real implementations are scheduled — see
``docs/roadmap.md``.

The server wraps the EviDraft external-agent bridge as MCP tools so any
MCP-aware host (Claude Code, Codex CLI, OpenCode, generic IDEs) can
delegate a single review pass to another coding agent (Codex CLI,
Claude bare, OpenCode) without re-implementing the CLI plumbing.

Security posture (enforced by the real implementation, declared here for
the contract):
    - prompts are delivered to subprocesses via stdin only,
    - the write zone is ``.evidraft/reviews/``,
    - Codex runs with ``--sandbox read-only``; Claude bare with
      ``--permission-mode dontAsk --allowedTools "Read"``; OpenCode
      runs against a worktree / copy of the project.
"""

from __future__ import annotations

from typing import Any


_ROADMAP_HINT = "scheduled for v0.2 — see roadmap.md"


def review_with(
    agent: str,
    prompt: str,
    workdir: str,
    persona: str,
    schema_path: str | None = None,
    timeout_seconds: int = 600,
) -> dict[str, Any]:
    """Delegate a single review pass to an external coding agent.

    Purpose:
        Spawn the chosen external agent (Codex CLI, Claude bare, or
        OpenCode), feed it ``prompt`` via stdin, and capture its
        structured output to a file under ``.evidraft/reviews/``. This
        is the MCP-tool form of ``/scholar:xreview``.

    Args:
        agent: One of ``"codex"``, ``"claude-bare"``, ``"opencode"``.
            Picks the CLI binary and sandboxing strategy.
        prompt: The fully rendered prompt (persona body + target file
            contents + optional schema). The implementation passes this
            to the agent via stdin or ``"$(cat …)"``; it never appears
            in argv.
        workdir: Project root (or a throwaway worktree, for OpenCode)
            to pin the agent's working directory to.
        persona: EviDraft agent id whose body was rendered into
            ``prompt`` (e.g. ``"novelty-critic"``). Used for output
            filename and telemetry.
        schema_path: Optional path to a JSON schema the external agent
            should conform its output to. If ``None``, the default
            ``{findings, top3, verdict, tokens, cost_usd}`` shape is
            assumed.
        timeout_seconds: Hard wall-clock timeout. Default 600 s.

    Returns:
        A dict shaped like
        ``{"output_path": str, "exit_code": int,
        "tokens": int | None, "cost_usd": float | None}``.
        ``output_path`` is always under ``.evidraft/reviews/``.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


def list_supported_agents() -> list[dict[str, Any]]:
    """List the external coding agents this bridge can delegate to.

    Purpose:
        Let a host discover which agents are wired up, which env var
        holds their auth, whether the agent supports a native
        read-only sandbox, and the verbatim CLI pattern the bridge
        uses. Useful for UI population and for capability checks
        before calling :func:`review_with`.

    Args:
        (none)

    Returns:
        A list of agent descriptor dicts, shaped like
        ``[{"id": str, "read_only": bool, "auth_env": str,
        "cli": str}]``. For v0.1 the contract values are:

        - ``{"id": "codex", "read_only": True,
          "auth_env": "CODEX_API_KEY",
          "cli": "codex exec --sandbox read-only --json -C $WORKDIR
          --output-last-message $OUT_FILE - < $PROMPT_FILE"}``
        - ``{"id": "claude-bare", "read_only": True,
          "auth_env": "ANTHROPIC_API_KEY",
          "cli": "claude --bare -p \\"$(cat $PROMPT_FILE)\\"
          --permission-mode dontAsk --allowedTools \\"Read\\"
          --output-format json > $OUT_FILE"}``
        - ``{"id": "opencode", "read_only": False,
          "auth_env": "OPENAI_API_KEY|ANTHROPIC_API_KEY|...",
          "cli": "opencode run --format json --dir $WORKDIR
          -f $TARGET_FILE \\"$(cat $PROMPT_FILE)\\" > $OUT_FILE"}``

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


def parse_review_output(path: str) -> dict[str, Any]:
    """Parse a captured external-agent review output file.

    Purpose:
        Normalise the structured output written by :func:`review_with`
        into a uniform shape regardless of which agent produced it.
        Used by ``/scholar:xreview`` to render the chat summary and to
        populate ``.evidraft/reviews/.last.yaml``.

    Args:
        path: Path to the captured output file under
            ``.evidraft/reviews/``.

    Returns:
        A dict shaped like
        ``{"findings": list[str], "top3": list[str],
        "cost_usd": float | None}``. ``findings`` is the full list of
        review findings; ``top3`` is the highest-priority subset (at
        most 3 entries) the agent picked; ``cost_usd`` is the reported
        invocation cost in USD or ``None`` if the agent did not
        report it.

    Raises:
        NotImplementedError: Always, in v0.1.
        FileNotFoundError: (v0.2+) If ``path`` does not exist.
        ValueError: (v0.2+) If the file content cannot be parsed as
            either the EviDraft review JSON envelope or a recognised
            agent-native envelope.
    """
    raise NotImplementedError(_ROADMAP_HINT)


if __name__ == "__main__":
    # Minimal hint for running this module as an MCP server entrypoint.
    # In v0.2+ this will wire the tool functions above into an MCP
    # transport (stdio or websocket) using the official MCP Python SDK,
    # and the subprocess-orchestration code described in
    # plugins/scholar-ip/skills/external-agent-bridge/SKILL.md.
    raise SystemExit(
        "external-agent-mcp is a stub in v0.1 — see "
        "packages/mcp/external-agent-mcp/README.md and docs/roadmap.md"
    )
