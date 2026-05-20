"""Skill-bundle file copy helper, shared by every adapter that renders skills.

A "skill bundle" is the source skill directory (parent of SKILL.md) plus any
sibling files / subdirectories like ``references/``, ``assets/``, ``scripts/``.
Adapters that propagate these to rendered output use ``copy_skill_bundle`` to
do it consistently.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .loader import FrontmatterDoc


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
    if doc.bundle_dir is None or not doc.bundle_dir.is_dir():
        return []
    written: list[Path] = []
    for src in sorted(doc.bundle_dir.rglob("*")):
        if not src.is_file():
            continue
        if src.name == "SKILL.md" and src.parent == doc.bundle_dir:
            continue
        rel = src.relative_to(doc.bundle_dir)
        dest = dest_skill_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        written.append(dest)
    return written
