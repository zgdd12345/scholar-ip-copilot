"""Crash-recoverable owned-tree replacement shared by render and install."""

from __future__ import annotations

import fcntl
import json
import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def _relative(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"unsafe transaction path: {value}")
    return path


def _remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


def _copy_node(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(f".{target.name}.evidraft-{os.getpid()}")
    _remove(temp)
    try:
        if source.is_symlink():
            temp.symlink_to(os.readlink(source), target_is_directory=source.is_dir())
        elif source.is_dir():
            shutil.copytree(source, temp, symlinks=True)
        else:
            shutil.copy2(source, temp)
        os.replace(temp, target)
    finally:
        _remove(temp)


def _atomic_json(path: Path, document: dict) -> None:
    temp = path.with_name(f".{path.name}.{os.getpid()}")
    try:
        temp.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


@contextmanager
def _locked(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_RDWR
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "a+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _existing_roots(root: Path, candidates: set[Path]) -> list[Path]:
    selected: list[Path] = []
    for relative in sorted(candidates, key=lambda item: (len(item.parts), item.as_posix())):
        if any(parent == relative or parent in relative.parents for parent in selected):
            continue
        target = root / relative
        if target.exists() or target.is_symlink():
            selected.append(relative)
    return selected


def _recover(root: Path, transaction: Path, manifest: Path) -> None:
    journal_path = transaction / "journal.json"
    if not journal_path.is_file():
        _remove(transaction)
        return
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    if journal.get("phase") == "committed":
        _remove(transaction)
        return
    new_owned = [_relative(value) for value in journal["new_owned"]]
    backup_roots = [_relative(value) for value in journal["backup_roots"]]
    for relative in sorted(new_owned, key=lambda item: len(item.parts), reverse=True):
        _remove(root / relative)
    backup = transaction / "backup"
    for relative in backup_roots:
        target = root / relative
        _remove(target)
        _copy_node(backup / relative, target)
    if manifest.exists() and not manifest.is_file():
        raise ValueError(f"deployment manifest must be a regular file: {manifest}")
    manifest.unlink(missing_ok=True)
    manifest_backup = transaction / "manifest.backup"
    if journal.get("manifest_existed"):
        _copy_node(manifest_backup, manifest)
    _remove(transaction)


def _reject_symlink_components(path: Path) -> None:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for index, component in enumerate(absolute.parts[1:]):
        current /= component
        if current.is_symlink():
            # macOS exposes /tmp and /var as root-level aliases. Resolve only that
            # operating-system boundary; symlinks deeper in the user path are rejected.
            if index == 0:
                current = current.resolve()
                continue
            raise ValueError(f"deployment path contains symlink component: {current}")


def replace_owned_tree(
    *,
    root: Path,
    staged_root: Path,
    new_owned: set[Path],
    old_owned: set[Path],
    manifest: Path,
    manifest_data: dict | None,
) -> None:
    """Replace owned paths as one recoverable transaction under a persistent lock."""
    root = root.absolute()
    _reject_symlink_components(root)
    if root.exists() and not root.is_dir():
        raise ValueError(f"deployment root must be a directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    staged_root = staged_root.resolve(strict=True)
    if not staged_root.is_dir():
        raise ValueError(f"staged deployment root must be a directory: {staged_root}")
    manifest = manifest.absolute()
    if manifest.parent != root:
        raise ValueError(f"deployment manifest must be directly under root: {manifest}")
    if manifest.is_symlink() or (manifest.exists() and not manifest.is_file()):
        raise ValueError(f"deployment manifest must be a regular file: {manifest}")
    new_owned = {_relative(path) for path in new_owned}
    old_owned = {_relative(path) for path in old_owned}
    lock = root.parent / f".{root.name}.evidraft.lock"
    transaction = root.parent / f".{root.name}.evidraft-transaction"
    if lock.is_symlink():
        raise ValueError(f"deployment lock must not be a symlink: {lock}")
    if transaction.is_symlink():
        raise ValueError(f"deployment transaction must not be a symlink: {transaction}")
    with _locked(lock):
        if transaction.exists():
            _recover(root, transaction, manifest)
        transaction.mkdir()
        backup = transaction / "backup"
        backup.mkdir()
        candidates = new_owned | old_owned
        backup_roots = _existing_roots(root, candidates)
        for relative in backup_roots:
            _copy_node(root / relative, backup / relative)
        manifest_existed = manifest.is_file() and not manifest.is_symlink()
        if manifest_existed:
            shutil.copy2(manifest, transaction / "manifest.backup")
        journal = {
            "version": 1,
            "phase": "prepared",
            "new_owned": sorted(path.as_posix() for path in new_owned),
            "backup_roots": [path.as_posix() for path in backup_roots],
            "manifest_existed": manifest_existed,
            "manifest_after_commit": "absent" if manifest_data is None else "present",
        }
        _atomic_json(transaction / "journal.json", journal)
        try:
            for relative in sorted(backup_roots, key=lambda item: len(item.parts), reverse=True):
                _remove(root / relative)
            for relative in sorted(new_owned):
                _copy_node(staged_root / relative, root / relative)
            if manifest_data is None:
                manifest.unlink(missing_ok=True)
            else:
                _atomic_json(manifest, manifest_data)
            journal["phase"] = "committed"
            _atomic_json(transaction / "journal.json", journal)
        except BaseException:
            _recover(root, transaction, manifest)
            raise
        _remove(transaction)
