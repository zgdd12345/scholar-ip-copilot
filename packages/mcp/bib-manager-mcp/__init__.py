"""bib-manager-mcp — MCP server stub package.

Re-exports the BibTeX tool functions declared in :mod:`server`. All tools
currently raise :class:`NotImplementedError`. See ``docs/roadmap.md`` and
``README.md`` for the v0.2 implementation plan.
"""

from __future__ import annotations

from .server import (
    check_missing_entries,
    check_unused_references,
    dedupe_bib,
    normalize_citation_keys,
)

__all__ = [
    "dedupe_bib",
    "normalize_citation_keys",
    "check_missing_entries",
    "check_unused_references",
]
