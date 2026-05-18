"""MCP server stub: patent-search.

This module declares the tool interface for the ``patent-search-mcp`` MCP
server. All tools are stubs in v0.1 and raise :class:`NotImplementedError`.
Real implementations are scheduled — see ``docs/roadmap.md``.

Important:
    All outputs of this server are **advisory only**. Nothing this server
    returns is a legal conclusion. The EviDraft patent workflow produces
    attorney-reviewable disclosures, never final legal opinions. See
    ``docs/legal-and-ethics.md``.
"""

from __future__ import annotations

from typing import Any


_ROADMAP_HINT = "scheduled for v0.2 — see roadmap.md"


def search_patents(
    query: str,
    top_k: int = 20,
    jurisdictions: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Search patent databases for documents matching ``query``.

    Purpose:
        Surface candidate prior art for ``/scholar:patent-prior-art``. Output is
        advisory; the user / attorney is responsible for legal evaluation.

    Args:
        query: Free-text search query.
        top_k: Maximum number of results to return.
        jurisdictions: Optional list of jurisdiction codes (e.g.
            ``["US", "EP", "CN"]``). ``None`` means "search all configured
            jurisdictions".

    Returns:
        A list of result dicts, each shaped roughly like
        ``{"patent_id": str, "title": str, "assignee": str | None,
        "filed": str | None, "granted": str | None,
        "jurisdiction": str, "abstract": str | None, "url": str | None}``.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


def extract_claims(patent_text: str) -> list[dict[str, Any]]:
    """Extract the claim list from a patent document.

    Purpose:
        Parse the ``CLAIMS`` section of a patent into structured claim
        records that downstream tools can compare element-by-element.

    Args:
        patent_text: Plain-text rendering of a patent document.

    Returns:
        A list of claim dicts, each shaped
        ``{"id": str, "kind": "independent" | "dependent", "text": str,
        "depends_on": str | None}``.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


def build_prior_art_chart(
    invention: dict[str, Any],
    prior_art: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a prior-art chart skeleton for the user's invention.

    Purpose:
        Lay out the user's invention features against the prior art so an
        attorney can fill in the legal analysis. Output is **advisory** —
        it is not a legal conclusion.

    Args:
        invention: Dict describing the user's invention, shaped roughly
            like ``{"title": str, "features": list[str]}``.
        prior_art: List of prior-art records, typically rows produced by
            :func:`search_patents` augmented with extracted claims.

    Returns:
        A chart dict shaped roughly like
        ``{"rows": list[dict], "columns": list[str], "advisory": True}``,
        where each row holds one invention feature aligned to its prior-art
        coverage.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


def compare_claim_elements(
    claims: list[dict[str, Any]],
    prior_art: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compare invention claim elements against prior art.

    Purpose:
        For each element of each claim, mark whether the prior art appears
        to disclose it. Output is **advisory** and intended for an attorney
        to refine; the agent must not present this as a legal opinion.

    Args:
        claims: Claim records, typically from :func:`extract_claims` on the
            user's draft claim set.
        prior_art: Prior-art records, each containing at least the fields
            produced by :func:`search_patents` plus extracted claims.

    Returns:
        A list of element comparison dicts, each shaped roughly like
        ``{"claim_id": str, "element": str,
        "matches": list[{"patent_id": str, "evidence": str,
        "confidence": "high" | "medium" | "low"}],
        "advisory": True}``.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


if __name__ == "__main__":
    raise SystemExit(
        "patent-search-mcp is a stub in v0.1 — see "
        "packages/mcp/patent-search-mcp/README.md and docs/roadmap.md"
    )
