"""code-intel-mcp — MCP server stub package.

Re-exports the code-intelligence tool functions declared in :mod:`server`.
All tools currently raise :class:`NotImplementedError`. See
``docs/roadmap.md`` and ``README.md`` for the v0.2 / v0.5 implementation
plan.
"""

from __future__ import annotations

from .server import (
    extract_config_schema,
    find_entrypoints,
    map_method_to_code,
    search_code,
    summarize_repo,
)

__all__ = [
    "summarize_repo",
    "find_entrypoints",
    "extract_config_schema",
    "map_method_to_code",
    "search_code",
]
