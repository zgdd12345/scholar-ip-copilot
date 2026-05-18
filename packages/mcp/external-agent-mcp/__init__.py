"""external-agent-mcp — MCP server stub package.

Re-exports the tool functions declared in :mod:`server` so callers may
write ``from external_agent_mcp import review_with`` once the package
is installed.

All tools currently raise :class:`NotImplementedError`. See
``docs/roadmap.md`` and ``README.md`` for the v0.2 implementation plan.
"""

from __future__ import annotations

from .server import (
    list_supported_agents,
    parse_review_output,
    review_with,
)

__all__ = [
    "review_with",
    "list_supported_agents",
    "parse_review_output",
]
