"""MCP server stub: latex-build.

This module declares the tool interface for the ``latex-build-mcp`` MCP
server. All tools are stubs in v0.1 and raise :class:`NotImplementedError`.
Real implementations are scheduled — see ``docs/roadmap.md``.

v0.2 implementation plan: wrap `latexmk` via :mod:`subprocess`, parse the
resulting ``.log`` file for errors, and render previews with `pdftoppm`
(or `pdf2image`) on demand.
"""

from __future__ import annotations

from typing import Any


_ROADMAP_HINT = "scheduled for v0.2 — see roadmap.md"


def compile_latex(project_path: str, main_tex: str = "main.tex") -> dict[str, Any]:
    """Compile a LaTeX project rooted at ``project_path``.

    Purpose:
        Drive `latexmk` (in v0.2) on the manuscript and return a structured
        result that ``/scholar:paper-check`` and the ``latex-compile`` hook can act
        on. Pure local subprocess; never network.

    Args:
        project_path: Local directory containing the LaTeX sources.
        main_tex: Filename of the root ``.tex`` file relative to
            ``project_path``. Defaults to ``"main.tex"``.

    Returns:
        A dict shaped ``{"success": bool, "pdf_path": str | None,
        "log_path": str}``. On failure ``pdf_path`` is ``None`` and the
        caller is expected to feed ``log_path`` into
        :func:`parse_latex_errors`.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


def parse_latex_errors(log_path: str) -> list[dict[str, Any]]:
    """Parse a LaTeX ``.log`` file into structured error / warning records.

    Purpose:
        Convert noisy `latexmk` output into a list of actionable issues that
        ``/scholar:paper-check`` can present to the user.

    Args:
        log_path: Local path to a LaTeX ``.log`` file.

    Returns:
        A list of issue dicts, each shaped
        ``{"file": str, "line": int | None, "kind": str, "message": str}``.
        ``kind`` is one of ``"error" | "warning" | "badbox" | "info"``.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


def render_pdf_preview(pdf_path: str, page: int = 1) -> str:
    """Render a single page of a PDF to an image for preview.

    Purpose:
        Give the user a fast visual check after a compile, without
        requiring a full PDF viewer.

    Args:
        pdf_path: Local path to a PDF file.
        page: 1-indexed page number to render. Defaults to ``1``.

    Returns:
        Local filesystem path of the rendered preview image (PNG in v0.2).

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


if __name__ == "__main__":
    raise SystemExit(
        "latex-build-mcp is a stub in v0.1 — see "
        "packages/mcp/latex-build-mcp/README.md and docs/roadmap.md"
    )
