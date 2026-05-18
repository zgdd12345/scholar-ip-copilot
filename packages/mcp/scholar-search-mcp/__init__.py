"""scholar-search-mcp — MCP server stub package.

Re-exports the tool functions declared in :mod:`server` so callers may write
``from scholar_search_mcp import search_papers`` once the package is
installed.

All tools currently raise :class:`NotImplementedError`. See
``docs/roadmap.md`` and ``README.md`` for the v0.2 implementation plan.
"""

from __future__ import annotations

from .server import (
    download_pdf,
    extract_references,
    get_paper_citations,
    get_paper_metadata,
    get_paper_references,
    resolve_citation,
    search_papers,
)

__all__ = [
    "search_papers",
    "get_paper_metadata",
    "download_pdf",
    "extract_references",
    "get_paper_references",
    "get_paper_citations",
    "resolve_citation",
]
