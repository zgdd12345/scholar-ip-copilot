"""Skill-bundle file copy helper, shared by every adapter that renders skills.

A "skill bundle" is the source skill directory (parent of SKILL.md) plus any
sibling files / subdirectories like ``references/``, ``assets/``, ``scripts/``.
Adapters that propagate these to rendered output use ``copy_skill_bundle`` to
do it consistently; their ``--dry-run`` mode uses ``bundle_dest_paths`` to
enumerate the same set of destinations without touching the filesystem.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

from .loader import FrontmatterDoc


def _bundle_files(doc: FrontmatterDoc) -> Iterator[tuple[Path, Path]]:
    """Yield ``(src, rel)`` for every file under ``doc.bundle_dir`` except
    the top-level ``SKILL.md`` itself.

    ``rel`` is the path relative to ``bundle_dir``. Yields nothing when ``doc``
    has no ``bundle_dir`` (commands / agents / hooks) or when the directory
    contains only ``SKILL.md``.

    Sorting is lexicographic on the full source path — deterministic across
    runs, identical for ``copy_skill_bundle`` and ``bundle_dest_paths``.
    """
    if doc.bundle_dir is None or not doc.bundle_dir.is_dir():
        return
    for src in sorted(doc.bundle_dir.rglob("*")):
        if not src.is_file():
            continue
        if src.name == "SKILL.md" and src.parent == doc.bundle_dir:
            continue
        yield src, src.relative_to(doc.bundle_dir)


def copy_skill_bundle(doc: FrontmatterDoc, dest_skill_dir: Path) -> list[Path]:
    """Copy every file under ``doc.bundle_dir`` (except top-level ``SKILL.md``)
    into ``dest_skill_dir``, preserving sub-directory structure.

    Returns the list of destination paths written. Returns ``[]`` when ``doc``
    has no ``bundle_dir`` or when the bundle contains only ``SKILL.md``.

    Trusts callers (the source tree under ``plugins/scholar-ip/skills/``) for
    bundle hygiene: symlinks are followed and their targets copied (not the
    links themselves); circular symlinks within a bundle would loop. This is
    acceptable because bundles are author-controlled, in-tree content.
    """
    written: list[Path] = []
    for src, rel in _bundle_files(doc):
        dest = dest_skill_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        written.append(dest)
    return written


def bundle_dest_paths(doc: FrontmatterDoc, dest_skill_dir: Path) -> list[Path]:
    """Return the destination paths ``copy_skill_bundle`` would write.

    Pure enumeration — no ``mkdir``, no ``copyfile``, no filesystem mutation.
    Each adapter's ``--dry-run`` mode uses this to mirror ``render()``'s actual
    output without producing files; the equivalence is asserted by
    ``test_*_dry_run_matches_render`` in ``tests/test_loader_skill_bundles.py``.
    """
    return [dest_skill_dir / rel for _, rel in _bundle_files(doc)]
