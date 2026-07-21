"""Transactional orchestration for Codex marketplace plugin installation."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .install import PUBLIC_CODEX_SKILLS


Runner = Callable[..., subprocess.CompletedProcess[str]]
DEFAULT_CODEX_COMMAND = (
    "codex",
    "-c",
    'model_reasoning_effort="xhigh"',
)
PLUGIN_REF = "scholar@scholar-ip-copilot"


@dataclass(frozen=True)
class MarketplacePlugin:
    marketplace_name: str
    plugin_name: str
    plugin_root: Path


@dataclass(frozen=True)
class ReinstallResult:
    plugin_ref: str
    installed_version: str


def validate_marketplace_plugin(
    repo_root: Path,
    marketplace_path: Path,
    plugin_name: str = "scholar",
) -> MarketplacePlugin:
    """Validate the tracked repo marketplace and its installable plugin package."""
    repo_root = Path(repo_root).resolve()
    marketplace_path = Path(marketplace_path).resolve()
    document = json.loads(marketplace_path.read_text(encoding="utf-8"))
    if document.get("name") != "scholar-ip-copilot":
        raise ValueError("unexpected marketplace name")
    matches = [
        entry
        for entry in document.get("plugins", [])
        if isinstance(entry, dict) and entry.get("name") == plugin_name
    ]
    if len(matches) != 1:
        raise ValueError(f"marketplace must contain exactly one {plugin_name} entry")
    source = matches[0].get("source")
    if source != {"source": "local", "path": "./plugins/scholar"}:
        raise ValueError("marketplace plugin source must be local ./plugins/scholar")

    plugin_root = (repo_root / "plugins" / "scholar").resolve()
    manifest = plugin_root / ".codex-plugin" / "plugin.json"
    if not manifest.is_file():
        raise FileNotFoundError(plugin_root)
    manifest_document = json.loads(manifest.read_text(encoding="utf-8"))
    if manifest_document.get("name") != plugin_name:
        raise ValueError(f"tracked package name must be {plugin_name}")
    public_skills = {
        path.parent.name
        for path in (plugin_root / "skills").glob("scholar-*/SKILL.md")
        if path.is_file()
    }
    if public_skills != PUBLIC_CODEX_SKILLS:
        raise ValueError("tracked plugin must expose exactly seven public skills")
    return MarketplacePlugin(document["name"], plugin_name, plugin_root)


def _restore_bytes(path: Path, content: bytes) -> None:
    temporary = path.with_name(f".{path.name}.restore-{os.getpid()}")
    try:
        temporary.write_bytes(content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _contains_exact_identifier(output: str, identifier: str) -> bool:
    boundary = re.compile(rf"(?<![A-Za-z0-9_-]){re.escape(identifier)}(?![A-Za-z0-9_-])")
    return any(boundary.search(line) for line in output.splitlines())


def _plugin_is_enabled(output: str, plugin_ref: str) -> bool:
    for line in output.splitlines():
        if _contains_exact_identifier(line, plugin_ref) and re.search(
            r"(?<![A-Za-z0-9_-])enabled(?![A-Za-z0-9_-])", line, re.IGNORECASE
        ):
            return True
    return False


def _plugin_creator_root() -> Path:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    return (codex_home / "skills" / ".system" / "plugin-creator").resolve()


def reinstall_codex_plugin(
    repo_root: Path,
    marketplace_path: Path,
    plugin_root: Path,
    plugin_creator_root: Path | None = None,
    *,
    runner: Runner = subprocess.run,
    codex_command: tuple[str, ...] = DEFAULT_CODEX_COMMAND,
) -> ReinstallResult:
    """Install the tracked Codex plugin with one transient cachebuster."""
    repo_root = Path(repo_root).resolve()
    marketplace_path = Path(marketplace_path).resolve()
    selected = validate_marketplace_plugin(repo_root, marketplace_path)
    if selected.plugin_root != Path(plugin_root).resolve():
        raise ValueError("marketplace and requested plugin roots differ")
    creator = (
        _plugin_creator_root()
        if plugin_creator_root is None
        else Path(plugin_creator_root).resolve()
    )
    python = sys.executable
    runner(
        [python, str(creator / "scripts/validate_plugin.py"), str(selected.plugin_root)],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    marketplace_name = runner(
        [
            python,
            str(creator / "scripts/read_marketplace_name.py"),
            "--marketplace-path",
            str(marketplace_path),
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if marketplace_name != selected.marketplace_name:
        raise ValueError("plugin-creator marketplace name mismatch")
    listed = runner(
        [*codex_command, "plugin", "marketplace", "list"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if not _contains_exact_identifier(listed, selected.marketplace_name):
        runner(
            [*codex_command, "plugin", "marketplace", "add", str(repo_root)],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )

    manifest = selected.plugin_root / ".codex-plugin" / "plugin.json"
    base_bytes = manifest.read_bytes()
    plugin_ref = f"{selected.plugin_name}@{selected.marketplace_name}"
    try:
        runner(
            [
                python,
                str(creator / "scripts/update_plugin_cachebuster.py"),
                str(selected.plugin_root),
            ],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        installed_version = json.loads(manifest.read_text(encoding="utf-8"))["version"]
        runner(
            [*codex_command, "plugin", "add", plugin_ref],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        post = runner(
            [*codex_command, "plugin", "list"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        if not _plugin_is_enabled(post, plugin_ref):
            raise RuntimeError("post-validate: installed plugin is not enabled")
        return ReinstallResult(plugin_ref, installed_version)
    finally:
        _restore_bytes(manifest, base_bytes)


def codex_project_mode_preflight(
    repo_root: Path,
    *,
    runner: Runner = subprocess.run,
    codex_command: tuple[str, ...] = DEFAULT_CODEX_COMMAND,
) -> None:
    """Refuse project-skill mode while the marketplace plugin remains active."""
    repo_root = Path(repo_root).resolve()
    listed = runner(
        [*codex_command, "plugin", "list"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if _plugin_is_enabled(listed, PLUGIN_REF):
        raise RuntimeError(
            f"marketplace plugin {PLUGIN_REF} is active; run: codex plugin remove {PLUGIN_REF}"
        )
