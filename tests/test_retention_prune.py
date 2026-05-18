"""Unit tests for the retention-prune snippet renderer.

These cover the four cases:
    1. neither ``keep_last`` nor ``max_age_days`` set -> ``None``
    2. only ``max_age_days`` set -> snippet contains ``find ... -mtime +N``
    3. only ``keep_last`` set -> snippet contains ``tail -n +<KEEP+1>``
    4. both set -> snippet contains both, with age-prune before keep-last-prune

Also pins the safety properties the adapter contract relies on:
    * snippet is guarded by ``[ -d "$DIR" ]`` (no error on first run)
    * never emits ``rm -rf`` against the directory itself
"""

from __future__ import annotations

from packages.adapters._shared.loader import render_retention_prune_snippet


def test_returns_none_when_neither_set() -> None:
    snippet = render_retention_prune_snippet(
        command_id="xreview",
        output_dir=".evidraft/reviews",
        keep_last=None,
        max_age_days=None,
    )
    assert snippet is None


def test_only_max_age_days_emits_find_mtime() -> None:
    snippet = render_retention_prune_snippet(
        command_id="xreview",
        output_dir=".evidraft/reviews",
        keep_last=None,
        max_age_days=90,
    )
    assert snippet is not None
    assert "find" in snippet
    assert "-mtime +$MAX_AGE_DAYS" in snippet
    assert "MAX_AGE_DAYS=90" in snippet
    # Should not include the keep-last branch at all.
    assert "tail -n" not in snippet
    # Safety: guarded.
    assert '[ -d "$DIR" ]' in snippet


def test_only_keep_last_emits_tail_offset() -> None:
    snippet = render_retention_prune_snippet(
        command_id="polish",
        output_dir=".evidraft/style",
        keep_last=30,
        max_age_days=None,
    )
    assert snippet is not None
    assert "KEEP_LAST=30" in snippet
    assert "tail -n +$((KEEP_LAST + 1))" in snippet
    assert "ls -1t" in snippet
    # Should not include the age branch.
    assert "-mtime" not in snippet
    assert '[ -d "$DIR" ]' in snippet


def test_both_set_emits_both_branches_in_order() -> None:
    snippet = render_retention_prune_snippet(
        command_id="xreview",
        output_dir=".evidraft/reviews",
        keep_last=50,
        max_age_days=180,
        file_glob="*.md",
    )
    assert snippet is not None
    assert "MAX_AGE_DAYS=180" in snippet
    assert "KEEP_LAST=50" in snippet
    assert '"*.md"' in snippet or 'GLOB="*.md"' in snippet
    # Age prune must come before keep-last prune.
    assert snippet.index("-mtime") < snippet.index("tail -n")


def test_snippet_is_safe_never_rms_directory() -> None:
    """Regression: snippet must not contain destructive directory-level rm."""
    snippet = render_retention_prune_snippet(
        command_id="xreview",
        output_dir=".evidraft/reviews",
        keep_last=50,
        max_age_days=180,
    )
    assert snippet is not None
    assert "rm -rf" not in snippet
    assert "--no-preserve-root" not in snippet
