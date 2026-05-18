"""MCP server stub: scholar-search.

This module declares the tool interface for the ``scholar-search-mcp`` MCP
server. All tools are stubs in v0.1 and raise :class:`NotImplementedError`.
Real implementations are scheduled — see ``docs/roadmap.md``.

Target providers (v0.2 will pick one as the primary):
    - arXiv
    - Semantic Scholar
    - OpenAlex
"""

from __future__ import annotations

from typing import Any


_ROADMAP_HINT = "scheduled for v0.2 — see roadmap.md"


def search_papers(
    query: str,
    year_range: tuple[int, int] | None = None,
    venue: str | None = None,
    top_k: int = 20,
    provider: str = "arxiv",
) -> list[dict[str, Any]]:
    """Search the scholarly literature for papers matching ``query``.

    Purpose:
        Surface a ranked list of candidate papers from one explicit provider.
        Intended to feed the literature matrix during ``/scholar:paper-lit``
        and the Retrieve stage of ``/scholar:deepresearch``.

    Args:
        query: Free-text search query.
        year_range: Inclusive ``(min_year, max_year)`` filter, or ``None`` for
            no year restriction.
        venue: Optional venue / journal filter (e.g. ``"CVPR"``).
        top_k: Maximum number of results to return.
        provider: One of ``{"arxiv", "semantic-scholar", "openalex"}``. In
            v0.2 this routes the call to the matching client. Callers must
            never blend metadata from two providers into one row silently —
            record the chosen ``provider`` as the row's ``source``.

    Returns:
        A list of result dicts, each shaped roughly like
        ``{"paper_id": str, "title": str, "authors": list[str], "year": int,
        "venue": str | None, "url": str | None, "abstract": str | None,
        "source": str}``.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


def get_paper_metadata(paper_id: str) -> dict[str, Any]:
    """Fetch the canonical metadata record for ``paper_id``.

    Purpose:
        Resolve a single paper identifier (arXiv id, DOI, S2 id, OpenAlex id)
        to a normalised metadata dict suitable for BibTeX rendering and for
        the evidence store.

    Args:
        paper_id: Provider-qualified identifier (e.g. ``"arxiv:2401.01234"``).

    Returns:
        A metadata dict, shaped roughly like
        ``{"paper_id": str, "title": str, "authors": list[str], "year": int,
        "venue": str | None, "doi": str | None, "abstract": str | None,
        "citation_key": str | None}``.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


def download_pdf(url: str, dest: str) -> str:
    """Download a PDF from ``url`` to ``dest``.

    Purpose:
        Persist a paper PDF locally for downstream reference extraction and
        human review. Real implementation must respect provider rate limits
        and licence terms.

    Args:
        url: HTTPS URL to a PDF.
        dest: Local filesystem path where the PDF should be written.

    Returns:
        The local path the PDF was written to (typically equal to ``dest``).

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


def extract_references(pdf_path: str) -> list[dict[str, Any]]:
    """Extract the reference list from a paper PDF.

    Purpose:
        Parse the bibliography section of a downloaded PDF into a list of
        structured reference records that can be looked up via
        :func:`get_paper_metadata`.

    Args:
        pdf_path: Local path to a PDF file.

    Returns:
        A list of reference dicts, each shaped roughly like
        ``{"raw": str, "title": str | None, "authors": list[str] | None,
        "year": int | None, "doi": str | None}``.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


def get_paper_references(
    paper_id: str,
    provider: str = "semantic-scholar",
) -> list[dict[str, Any]]:
    """Fetch the works that ``paper_id`` cites (its bibliography).

    Purpose:
        Walk one hop up the citation graph from ``paper_id`` to surface its
        method / dataset / theory ancestors. Used by the Cluster stage of
        ``/scholar:deepresearch`` to build ``clusters.yaml.method_lineage``.

    Args:
        paper_id: Provider-qualified identifier (e.g. ``"arxiv:2401.01234"``
            or ``"doi:10.1109/CVPR..."``).
        provider: One of ``{"arxiv", "semantic-scholar", "openalex"}``.
            ``semantic-scholar`` and ``openalex`` carry the citation graph;
            ``arxiv`` does not and must fall back to PDF reference extraction
            via :func:`extract_references`.

    Returns:
        A list of reference dicts, each shaped roughly like
        ``{"paper_id": str | None, "title": str, "authors": list[str],
        "year": int | None, "doi": str | None, "source": str}``.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


def get_paper_citations(
    paper_id: str,
    provider: str = "semantic-scholar",
) -> list[dict[str, Any]]:
    """Fetch the works that cite ``paper_id`` (its follow-on literature).

    Purpose:
        Walk one hop down the citation graph from ``paper_id`` to surface
        follow-on / contradictory / replication work. Used by the Critique
        stage of ``/scholar:deepresearch`` to sharpen SWOT bullets and by
        the Cluster stage to fill follow-on lineage.

    Args:
        paper_id: Provider-qualified identifier.
        provider: One of ``{"arxiv", "semantic-scholar", "openalex"}``.
            ``arxiv`` does not expose forward citations and must raise
            unconditionally in v0.2.

    Returns:
        A list of citing-paper dicts, each shaped roughly like
        ``{"paper_id": str, "title": str, "authors": list[str],
        "year": int, "venue": str | None, "doi": str | None,
        "source": str}``.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


def resolve_citation(
    claim: str,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Match a free-text ``claim`` to the most likely ``citation_key``.

    Purpose:
        Power the citation-audit pass of ``/scholar:deepresearch``: every
        claim in ``related_work.draft.md`` must resolve to a ``citation_key``
        present in ``references.bib`` and at least one ``evidence_id``
        present in ``evidence.jsonl``. This function returns the best match
        from a caller-supplied candidate set (typically the union of the run's
        clustered papers and any inline citation keys).

    Args:
        claim: The free-text sentence or sub-sentence to be cited.
        candidates: A list of candidate dicts, each carrying at least
            ``{"citation_key": str, "title": str, "abstract": str | None,
            "evidence_id_hint": str | None}``.

    Returns:
        A single match dict of the form
        ``{"citation_key": str, "confidence": float,
        "evidence_id_hint": str | None}``. ``confidence`` is in ``[0, 1]``;
        callers should treat ``< 0.5`` as unresolved and refuse the audit.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


if __name__ == "__main__":
    # Minimal hint for running this module as an MCP server entrypoint.
    # In v0.2+ this will wire the tool functions above into an MCP transport
    # (stdio or websocket) using the official MCP Python SDK.
    raise SystemExit(
        "scholar-search-mcp is a stub in v0.1 — see "
        "packages/mcp/scholar-search-mcp/README.md and docs/roadmap.md"
    )
