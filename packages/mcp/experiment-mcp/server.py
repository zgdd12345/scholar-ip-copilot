"""MCP server stub: experiment.

This module declares the tool interface for the ``experiment-mcp`` MCP
server. All tools are stubs in v0.1 and raise :class:`NotImplementedError`.
Real implementations are scheduled — see ``docs/roadmap.md``.

v0.2 implementation plan: use :mod:`pandas` to normalise tabular results
(CSV / JSON / Parquet), with `pyarrow` as an optional extra for Parquet
support. Booktabs LaTeX rendering and number-source auditing are then
trivial table ops.
"""

from __future__ import annotations

from typing import Any


_ROADMAP_HINT = "scheduled for v0.2 — see roadmap.md"


def load_results(path: str) -> dict[str, Any]:
    """Load experiment results into a normalised in-memory structure.

    Purpose:
        Read whatever the user happens to store under ``experiments/`` —
        CSV, JSON, JSONL, Parquet — and return one canonical structure that
        the other tools in this module consume.

    Args:
        path: Local path to a results file or directory.

    Returns:
        A normalised dict, shaped roughly like
        ``{"schema": list[str], "rows": list[dict[str, Any]],
        "source": str}``.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


def summarize_metrics(path: str) -> list[dict[str, Any]]:
    """Summarise the metrics present in a results store.

    Purpose:
        Surface a flat list of ``(metric, setting, value)`` rows that
        ``/scholar:paper-experiment`` can turn into tables, figures, and prose.

    Args:
        path: Local path to a results file or directory.

    Returns:
        A list of metric dicts, each shaped
        ``{"metric": str, "setting": dict[str, Any] | str,
        "value": float | str, "source": str}``.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


def generate_latex_table(
    results: list[dict[str, Any]],
    style: str = "booktabs",
) -> str:
    """Render a list of result rows as a LaTeX table.

    Purpose:
        Produce a ``\\input``-ready table for the manuscript. Default style
        is ``booktabs`` (``\\toprule`` / ``\\midrule`` / ``\\bottomrule``).

    Args:
        results: List of result rows, typically obtained from
            :func:`summarize_metrics`.
        style: Table style. Currently only ``"booktabs"`` is planned for
            v0.2.

    Returns:
        A string containing the LaTeX source for the table.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


def suggest_figures(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Suggest figures appropriate for a set of result rows.

    Purpose:
        Propose plot specifications (axes, source rows, seed strategy) for
        the user / agent to instantiate. Does NOT draw anything.

    Args:
        results: List of result rows, typically obtained from
            :func:`summarize_metrics`.

    Returns:
        A list of figure spec dicts, each shaped roughly like
        ``{"kind": str, "x": str, "y": str, "group_by": str | None,
        "source": list[str], "seeds": list[int] | None,
        "rationale": str}``.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


def check_number_sources(text: str, results_path: str) -> list[dict[str, Any]]:
    """Audit every number in ``text`` against the experiment results.

    Purpose:
        Enforce the "no number without a row in ``experiments/``" rule used
        by ``/scholar:paper-check`` and the ``evidence-consistency`` hook.

    Args:
        text: Draft text (typically a manuscript section or the abstract).
        results_path: Local path to a results file or directory.

    Returns:
        A list of audit records, each shaped
        ``{"number": str, "kind": "MATCH" | "MISMATCH" | "MISSING",
        "source": str | None}``. ``source`` points to the row that backs
        the number when ``kind`` is ``MATCH`` or ``MISMATCH``.

    Raises:
        NotImplementedError: Always, in v0.1.
    """
    raise NotImplementedError(_ROADMAP_HINT)


if __name__ == "__main__":
    raise SystemExit(
        "experiment-mcp is a stub in v0.1 — see "
        "packages/mcp/experiment-mcp/README.md and docs/roadmap.md"
    )
