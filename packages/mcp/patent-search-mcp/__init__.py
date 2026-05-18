"""patent-search-mcp — MCP server stub package.

Re-exports the patent retrieval and analysis tool functions declared in
:mod:`server`. All tools currently raise :class:`NotImplementedError`. See
``docs/roadmap.md`` and ``README.md`` for the v0.2 implementation plan.

All outputs from this server are advisory only. See
``docs/legal-and-ethics.md``.
"""

from __future__ import annotations

from .server import (
    build_prior_art_chart,
    compare_claim_elements,
    extract_claims,
    search_patents,
)

__all__ = [
    "search_patents",
    "extract_claims",
    "build_prior_art_chart",
    "compare_claim_elements",
]
