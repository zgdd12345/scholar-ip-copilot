"""Ownership-safe installation helpers for rendered host bundles."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from .legacy import V1_COMMANDS, V1_SKILLS
from .transaction import replace_owned_tree


PUBLIC_CODEX_SKILLS = {
    "scholar-using",
    "scholar-scope",
    "scholar-research",
    "scholar-paper",
    "scholar-patent",
    "scholar-polish",
    "scholar-xreview",
}

V1_CODEX_ENTRIES = {f"scholar-{value}" for value in V1_COMMANDS} | {
    f"scholar-skill-{value}" for value in V1_SKILLS
}


def _owned_names(destination: Path) -> set[str]:
    manifest = destination / ".evidraft-ownership.json"
    if not manifest.is_file():
        return set()
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    names: set[str] = set()
    for value in raw.get("owned_paths", []):
        relative = Path(str(value))
        if relative.is_absolute() or len(relative.parts) != 1 or relative.name in {".", ".."}:
            raise ValueError(f"unsafe owned skill path: {value}")
        names.add(relative.name)
    private_path = raw.get("private_path")
    if private_path is not None:
        relative = Path(str(private_path))
        if relative.is_absolute() or len(relative.parts) != 1:
            raise ValueError(f"unsafe private skill path: {private_path}")
        names.add(relative.name)
    return names


def _validate_source(rendered_root: Path) -> tuple[dict[str, Path], Path]:
    skills_root = rendered_root.resolve() / "skills"
    bundles = {
        path.name: path
        for path in skills_root.iterdir()
        if path.is_dir() and not path.is_symlink() and (path / "SKILL.md").is_file()
    }
    if set(bundles) != PUBLIC_CODEX_SKILLS:
        raise ValueError("rendered Codex source must contain exactly seven v2 public skills")
    private = skills_root / ".evidraft-private"
    required = (
        private / "capabilities" / "index.yaml",
        private / "roles" / "roles.yaml",
        private / "policies" / "policy.yaml",
        private / "templates" / "paper-project" / "manuscript" / "main.tex",
        private / "schemas" / "project.schema.json",
    )
    if private.is_symlink() or not all(path.is_file() for path in required):
        raise ValueError("rendered Codex source is missing private workflow resources")
    return bundles, private


def sync_codex_skills(rendered_root: Path, destination: Path) -> list[Path]:
    """Install exactly seven rendered skills and remove only known owned v1/v2 paths."""
    bundles, private = _validate_source(rendered_root)
    destination = destination.absolute()
    if destination.is_symlink():
        raise ValueError(f"skill destination must not be a symlink: {destination}")
    old_owned = _owned_names(destination)
    private_name = ".evidraft-private"
    new_owned = set(bundles) | {private_name}
    old_owned |= V1_CODEX_ENTRIES | new_owned

    with tempfile.TemporaryDirectory(prefix="evidraft-sync-") as raw:
        staged = Path(raw) / "new"
        staged.mkdir()
        for name, source in bundles.items():
            shutil.copytree(source, staged / name, symlinks=True)
        shutil.copytree(private, staged / private_name, symlinks=True)

        manifest = destination / ".evidraft-ownership.json"
        replace_owned_tree(
            root=destination,
            staged_root=staged,
            new_owned={Path(name) for name in new_owned},
            old_owned={Path(name) for name in old_owned},
            manifest=manifest,
            manifest_data={
                "version": 2,
                "owned_paths": sorted(bundles),
                "private_path": private_name,
            },
        )

    return [destination / name for name in sorted(bundles)]
