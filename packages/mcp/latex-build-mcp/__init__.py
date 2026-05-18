"""latex-build-mcp — MCP server stub package.

Re-exports the LaTeX build tool functions declared in :mod:`server`. All
tools currently raise :class:`NotImplementedError`. See ``docs/roadmap.md``
and ``README.md`` for the v0.2 implementation plan.
"""

from __future__ import annotations

from .server import (
    compile_latex,
    parse_latex_errors,
    render_pdf_preview,
)

__all__ = [
    "compile_latex",
    "parse_latex_errors",
    "render_pdf_preview",
]
