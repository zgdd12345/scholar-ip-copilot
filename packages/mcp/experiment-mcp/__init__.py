"""experiment-mcp — MCP server stub package.

Re-exports the experiment-results tool functions declared in :mod:`server`.
All tools currently raise :class:`NotImplementedError`. See
``docs/roadmap.md`` and ``README.md`` for the v0.2 implementation plan.
"""

from __future__ import annotations

from .server import (
    check_number_sources,
    generate_latex_table,
    load_results,
    suggest_figures,
    summarize_metrics,
)

__all__ = [
    "load_results",
    "summarize_metrics",
    "generate_latex_table",
    "suggest_figures",
    "check_number_sources",
]
