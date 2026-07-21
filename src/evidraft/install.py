"""Ownership-safe installation helpers for rendered host bundles."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass
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


@dataclass(frozen=True)
class CodexProjectSkillsSnapshot:
    destination: Path
    staged_root: Path
    claimed_paths: frozenset[Path]
    existing_paths: frozenset[Path]
    manifest_bytes: bytes | None


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
        if relative.is_absolute() or len(relative.parts) != 1 or relative.name in {".", ".."}:
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
        raise ValueError("rendered Codex source must contain exactly seven v3 public skills")
    private = skills_root / ".evidraft-private"
    required = (
        private / "capabilities" / "index.yaml",
        private / "capabilities" / "research" / "paper-explanation" / "spec.md",
        private / "capabilities" / "research" / "paper-explanation" / "task-graph.yaml",
        private / "capabilities" / "research" / "paper-explanation" / "paper-map.schema.json",
        private / "capabilities" / "research" / "paper-explanation" / "analysis-packet.schema.json",
        skills_root / "scholar-research" / "stages" / "explain.md",
        private / "roles" / "roles.yaml",
        private / "roles" / "modes" / "paper-indexer.md",
        private / "roles" / "modes" / "paper-analysis-worker.md",
        private / "roles" / "modes" / "paper-reasoning-worker.md",
        private / "roles" / "modes" / "explanation-evidence-auditor.md",
        private / "roles" / "modes" / "paper-explainer.md",
        private / "policies" / "policy.yaml",
        private / "templates" / "paper-project" / "manuscript" / "main.tex",
        private / "schemas" / "project.schema.json",
    )
    if private.is_symlink() or not all(path.is_file() for path in required):
        raise ValueError("rendered Codex source is missing private workflow resources")
    return bundles, private


def _copy_snapshot_node(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        target.symlink_to(os.readlink(source), target_is_directory=source.is_dir())
    elif source.is_dir():
        shutil.copytree(source, target, symlinks=True)
    else:
        shutil.copy2(source, target)


def snapshot_codex_project_skills(
    destination: Path,
    staged_root: Path,
) -> CodexProjectSkillsSnapshot:
    """Copy manifest-owned compatibility state before marketplace installation."""
    destination = Path(destination).absolute()
    if destination.is_symlink():
        raise ValueError(f"skill destination must not be a symlink: {destination}")
    manifest = destination / ".evidraft-ownership.json"
    if manifest.is_symlink() or (manifest.exists() and not manifest.is_file()):
        raise ValueError(f"deployment manifest must be a regular file: {manifest}")
    claimed = frozenset(Path(name) for name in _owned_names(destination))
    staged_root = Path(staged_root)
    staged_root.mkdir(parents=True)
    existing: set[Path] = set()
    for relative in sorted(claimed):
        source = destination / relative
        if not source.exists() and not source.is_symlink():
            continue
        _copy_snapshot_node(source, staged_root / relative)
        existing.add(relative)
    return CodexProjectSkillsSnapshot(
        destination=destination,
        staged_root=staged_root,
        claimed_paths=claimed,
        existing_paths=frozenset(existing),
        manifest_bytes=manifest.read_bytes() if manifest.is_file() else None,
    )


def restore_codex_project_skills(snapshot: CodexProjectSkillsSnapshot) -> None:
    """Restore the exact compatibility state captured before removal."""
    if snapshot.manifest_bytes is None:
        return
    manifest_data = json.loads(snapshot.manifest_bytes.decode("utf-8"))
    if not isinstance(manifest_data, dict):
        raise ValueError("deployment manifest must be a JSON object")
    manifest = snapshot.destination / ".evidraft-ownership.json"
    replace_owned_tree(
        root=snapshot.destination,
        staged_root=snapshot.staged_root,
        new_owned=set(snapshot.existing_paths),
        old_owned=set(snapshot.claimed_paths),
        manifest=manifest,
        manifest_data=manifest_data,
    )
    temporary = manifest.with_name(f".{manifest.name}.restore-{os.getpid()}")
    try:
        temporary.write_bytes(snapshot.manifest_bytes)
        os.replace(temporary, manifest)
    finally:
        temporary.unlink(missing_ok=True)


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


def remove_codex_project_skills(destination: Path) -> list[Path]:
    """Remove only entries declared by the destination ownership manifest."""
    destination = Path(destination).absolute()
    if destination.is_symlink():
        raise ValueError(f"skill destination must not be a symlink: {destination}")
    manifest = destination / ".evidraft-ownership.json"
    if manifest.is_symlink() or (manifest.exists() and not manifest.is_file()):
        raise ValueError(f"deployment manifest must be a regular file: {manifest}")
    owned = _owned_names(destination)
    removed = [
        destination / name
        for name in sorted(owned)
        if (destination / name).exists() or (destination / name).is_symlink()
    ]
    if not owned:
        return []
    with tempfile.TemporaryDirectory(prefix="evidraft-remove-skills-") as raw:
        staged = Path(raw) / "empty"
        staged.mkdir()
        replace_owned_tree(
            root=destination,
            staged_root=staged,
            new_owned=set(),
            old_owned={Path(name) for name in owned},
            manifest=manifest,
            manifest_data={"version": 2, "owned_paths": []},
        )
        manifest.unlink()
    return removed
