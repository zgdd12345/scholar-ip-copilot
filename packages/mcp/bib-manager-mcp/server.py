"""MCP server stub: bib-manager.

This module declares the tool interface for the ``bib-manager-mcp`` MCP
server. All tools are stubs in v0.1 and raise :class:`NotImplementedError`.
Real implementations are scheduled — see ``docs/roadmap.md``.

v0.2 implementation plan: wrap `bibtexparser` for parsing, dedup, and
citation-key normalisation, and use a `\\cite{}` regex pass for the
missing / unused checks.
"""

from __future__ import annotations


_ROADMAP_HINT = "scheduled for v0.2 — see roadmap.md"


def dedupe_bib(path: str) -> dict[str, int]:
    """Remove duplicate entries from a BibTeX file in place.

    Purpose:
        Detect duplicates by DOI when available, falling back to a
        title+first-author hash. Used by ``/scholar:paper-lit`` and
        ``/scholar:paper-check``.

    Args:
        path: Local path to a ``.bib`` file. The file is rewritten in place
            after deduplication.

    Returns:
        A dict shaped ``{"removed": int, "kept": int}``.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


def normalize_citation_keys(
    path: str,
    pattern: str = "firstauthorYEARkeyword",
) -> dict[str, str]:
    """Rewrite citation keys in a BibTeX file to a uniform pattern.

    Purpose:
        Produce stable, human-readable citation keys so that draft text and
        bibliography stay in sync across renames.

    Args:
        path: Local path to a ``.bib`` file.
        pattern: Naming pattern. Default ``"firstauthorYEARkeyword"`` yields
            keys such as ``"smith2024diffusion"``.

    Returns:
        A mapping ``{old_key: new_key}`` describing every rename that was
        applied. Empty dict if no renames were necessary.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


def check_missing_entries(tex_path: str, bib_path: str) -> list[str]:
    """Find ``\\cite{}`` keys used in a LaTeX file but absent from BibTeX.

    Purpose:
        Used by ``/scholar:paper-check`` to catch dangling citations before
        compilation.

    Args:
        tex_path: Local path to a ``.tex`` file (or a directory; see v0.2
            spec).
        bib_path: Local path to a ``.bib`` file.

    Returns:
        A sorted list of citation keys referenced in ``tex_path`` that have
        no matching entry in ``bib_path``.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


def check_unused_references(tex_path: str, bib_path: str) -> list[str]:
    """Find BibTeX entries that are never cited from a LaTeX file.

    Purpose:
        Used by ``/scholar:paper-check`` to keep the bibliography tight and to flag
        entries that may have been pulled in by accident.

    Args:
        tex_path: Local path to a ``.tex`` file (or a directory).
        bib_path: Local path to a ``.bib`` file.

    Returns:
        A sorted list of citation keys present in ``bib_path`` that are not
        cited anywhere in ``tex_path``.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


if __name__ == "__main__":
    raise SystemExit(
        "bib-manager-mcp is a stub in v0.1 — see "
        "packages/mcp/bib-manager-mcp/README.md and docs/roadmap.md"
    )
