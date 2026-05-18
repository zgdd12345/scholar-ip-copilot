"""MCP server stub: code-intel.

This module declares the tool interface for the ``code-intel-mcp`` MCP
server. All tools are stubs in v0.1 and raise :class:`NotImplementedError`.
Real implementations are scheduled — see ``docs/roadmap.md``.

Roadmap:
    - v0.2 ships symbol / grep / tree-sitter based code intelligence.
    - v0.5 introduces a semantic vector index for natural-language lookups.
"""

from __future__ import annotations

from typing import Any


_ROADMAP_HINT_BASIC = "scheduled for v0.2 — see roadmap.md"
_ROADMAP_HINT_SEMANTIC = "scheduled for v0.5 — see roadmap.md"


def summarize_repo(path: str) -> dict[str, Any]:
    """Produce a structured summary of a code repository.

    Purpose:
        Feed ``/scholar:paper-code-audit`` with a high-level map of the project:
        languages, top-level modules, entry points, configuration files,
        and test layout.

    Args:
        path: Local path to the repository root.

    Returns:
        A dict shaped roughly like
        ``{"languages": dict[str, int],  # lines or files per language
        "modules": list[str], "entrypoints": list[str],
        "configs": list[str], "tests": list[str]}``.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT_BASIC)


def find_entrypoints(path: str) -> list[str]:
    """Locate likely program entry points in a repository.

    Purpose:
        Identify files such as ``main.py``, ``train.py``, ``cli.py``,
        ``__main__.py``, ``bin/*``, ``scripts/*`` so that the method-to-code
        map can anchor on them.

    Args:
        path: Local path to the repository root.

    Returns:
        A list of repo-relative paths.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT_BASIC)


def extract_config_schema(path: str) -> dict[str, Any]:
    """Extract configuration schema from a repository.

    Purpose:
        Parse YAML / JSON / TOML / argparse / Hydra configuration files
        into a normalised key/type/default tree, used by
        ``/scholar:paper-code-audit`` and ``/scholar:paper-experiment``.

    Args:
        path: Local path to the repository root.

    Returns:
        A nested dict describing the merged configuration surface, shaped
        roughly like ``{key: {"type": str, "default": Any,
        "source": str}}``.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT_BASIC)


def map_method_to_code(method_description: str, path: str) -> list[dict[str, Any]]:
    """Map a natural-language method description to concrete code locations.

    Purpose:
        Core helper for ``/scholar:paper-code-audit``. Given a method or component
        description from the manuscript, return ranked code anchors so the
        agent can mark the claim as ``CONFIRMED`` / ``PARTIAL`` / ``MISSING``
        / ``MISMATCH`` / ``NOT_AUDITABLE``.

    Args:
        method_description: Free-text description of the method or
            component (e.g. ``"the attention re-ranking module"``).
        path: Local path to the repository root.

    Returns:
        A list of anchor dicts, each shaped
        ``{"file": str, "line_range": tuple[int, int], "symbol": str,
        "why": str}``.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT_SEMANTIC)


def search_code(query: str, path: str, top_k: int = 20) -> list[dict[str, Any]]:
    """Search a repository for code matching ``query``.

    Purpose:
        A retrieval primitive used by other tools. v0.2 ships a
        symbol + grep + tree-sitter implementation; v0.5 replaces the
        ranking with a semantic vector index.

    Args:
        query: Free-text or symbolic query.
        path: Local path to the repository root.
        top_k: Maximum number of hits to return.

    Returns:
        A list of hit dicts, each shaped roughly like
        ``{"file": str, "line": int, "snippet": str, "score": float}``.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT_BASIC)


if __name__ == "__main__":
    raise SystemExit(
        "code-intel-mcp is a stub in v0.1 — see "
        "packages/mcp/code-intel-mcp/README.md and docs/roadmap.md"
    )
