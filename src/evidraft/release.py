"""Build a deterministic combined Claude and Codex plugin package."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from .render import RENDERER_VERSION, Host, load_plugin_metadata, render_plugin
from .transaction import replace_owned_tree


RELEASE_MANIFEST = ".evidraft-release-manifest.json"
RELEASE_FORMAT_VERSION = 1


def _safe_relative(value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError(f"unsafe release path: {value}")
    return relative


def _file_bytes(root: Path) -> dict[str, bytes]:
    root = Path(root)
    if not root.is_dir():
        return {}
    files: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"release tree contains symlink: {path}")
        if path.is_file():
            files[path.relative_to(root).as_posix()] = path.read_bytes()
    return files


def _normalize_markdown_eof(root: Path) -> None:
    for path in root.rglob("*.md"):
        body = path.read_bytes()
        if body:
            path.write_bytes(body.rstrip(b"\n") + b"\n")


def _read_release_owned_paths(root: Path) -> set[Path]:
    manifest = Path(root) / RELEASE_MANIFEST
    if not manifest.is_file():
        return set()
    document = json.loads(manifest.read_text(encoding="utf-8"))
    if document.get("format_version") != RELEASE_FORMAT_VERSION:
        raise ValueError("unsupported release manifest format")
    return {
        _safe_relative(value)
        for values in document.get("hosts", {}).values()
        for value in values
    }


def _existing_release_files(root: Path) -> set[Path]:
    root = Path(root)
    if not root.is_dir():
        return set()
    return {
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() or path.is_symlink()
    }


def source_sha256(plugin_root: Path) -> str:
    digest = hashlib.sha256()
    plugin_root = Path(plugin_root)
    for path in sorted(item for item in plugin_root.rglob("*") if item.is_file()):
        relative = path.relative_to(plugin_root).as_posix().encode("utf-8")
        body = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(body).to_bytes(8, "big"))
        digest.update(body)
    return digest.hexdigest()


def render_plugin_package(plugin_root: Path, out_dir: Path) -> list[Path]:
    plugin_root = Path(plugin_root).resolve()
    out_dir = Path(out_dir).absolute()
    metadata = load_plugin_metadata(plugin_root)
    with tempfile.TemporaryDirectory(prefix="evidraft-package-") as raw:
        temporary = Path(raw)
        staged = temporary / "staged"
        staged.mkdir()
        by_host: dict[str, list[str]] = {}
        owners: dict[Path, str] = {}
        for host in (Host.CLAUDE, Host.CODEX):
            rendered_root = temporary / host.value
            rendered = render_plugin(plugin_root, rendered_root, host)
            _normalize_markdown_eof(rendered_root)
            relative_files = sorted(
                path.relative_to(rendered_root)
                for path in rendered
                if path.name != ".evidraft-render-manifest.json"
            )
            by_host[host.value] = [path.as_posix() for path in relative_files]
            for relative in relative_files:
                source = rendered_root / relative
                target = staged / relative
                if relative in owners:
                    if target.read_bytes() != source.read_bytes():
                        raise ValueError(
                            f"release path collision: {relative} from "
                            f"{owners[relative]} and {host.value}"
                        )
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                owners[relative] = host.value

        old_owned = _read_release_owned_paths(out_dir)
        unknown = _existing_release_files(out_dir) - old_owned - {Path(RELEASE_MANIFEST)}
        if unknown:
            names = ", ".join(path.as_posix() for path in sorted(unknown))
            raise ValueError(f"unknown files in release root: {names}")
        manifest_data = {
            "format_version": RELEASE_FORMAT_VERSION,
            "plugin": {"id": metadata.id, "version": metadata.version},
            "renderer_version": RENDERER_VERSION,
            "source_sha256": source_sha256(plugin_root),
            "hosts": by_host,
        }
        new_owned = set(owners)
        replace_owned_tree(
            root=out_dir,
            staged_root=staged,
            new_owned=new_owned,
            old_owned=old_owned,
            manifest=out_dir / RELEASE_MANIFEST,
            manifest_data=manifest_data,
        )
    return sorted([out_dir / path for path in new_owned] + [out_dir / RELEASE_MANIFEST])


def release_package_drift(plugin_root: Path, package_root: Path) -> list[str]:
    package_root = Path(package_root)
    with tempfile.TemporaryDirectory(prefix="evidraft-drift-") as raw:
        expected_root = Path(raw) / "scholar"
        render_plugin_package(plugin_root, expected_root)
        expected = _file_bytes(expected_root)
    actual = _file_bytes(package_root)
    findings = [f"missing: {path}" for path in sorted(expected.keys() - actual.keys())]
    findings.extend(
        f"changed: {path}"
        for path in sorted(expected.keys() & actual.keys())
        if expected[path] != actual[path]
    )
    findings.extend(f"unexpected: {path}" for path in sorted(actual.keys() - expected.keys()))
    return findings
