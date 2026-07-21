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


@dataclass(frozen=True)
class InstalledPlugin:
    plugin_ref: str
    status: str
    version: str
    plugin_root: Path


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
    except BaseException as restore_error:
        try:
            temporary.unlink(missing_ok=True)
        except BaseException as cleanup_error:
            raise restore_error from cleanup_error
        raise
    else:
        temporary.unlink(missing_ok=True)


def _marketplace_root(output: str, marketplace_name: str) -> Path | None:
    lines = output.splitlines()
    try:
        header = next(
            index
            for index, line in enumerate(lines)
            if line.split() == ["MARKETPLACE", "ROOT"]
        )
    except StopIteration as exc:
        raise ValueError("could not parse Codex marketplace inventory header") from exc
    matches: list[Path] = []
    for line in lines[header + 1 :]:
        fields = line.strip().split(maxsplit=1)
        if len(fields) != 2 or fields[0] != marketplace_name:
            continue
        root = Path(fields[1]).expanduser()
        if not root.is_absolute():
            raise ValueError("configured marketplace root must be absolute")
        matches.append(root.resolve())
    if len(matches) > 1:
        raise ValueError(f"multiple configured roots found for marketplace {marketplace_name}")
    return matches[0] if matches else None


def _installed_plugin(output: str, plugin_ref: str) -> InstalledPlugin:
    lines = output.splitlines()
    in_table = False
    matches: list[InstalledPlugin] = []
    for line in lines:
        if line.split() == ["PLUGIN", "STATUS", "VERSION", "PATH"]:
            in_table = True
            continue
        if not line.strip():
            in_table = False
            continue
        if not in_table:
            continue
        fields = re.split(r"\s{2,}", line.strip(), maxsplit=3)
        if not fields or fields[0] != plugin_ref:
            continue
        if len(fields) != 4:
            raise RuntimeError(f"post-validate: malformed installed record for {plugin_ref}")
        matches.append(InstalledPlugin(fields[0], fields[1], fields[2], Path(fields[3])))
    if len(matches) != 1:
        raise RuntimeError(f"post-validate: expected one installed record for {plugin_ref}")
    return matches[0]


def _plugin_is_enabled(output: str, plugin_ref: str) -> bool:
    for line in output.splitlines():
        fields = line.strip().split(maxsplit=1)
        if fields == [plugin_ref, "installed, enabled"]:
            return True
    return False


def _validate_installed_plugin(
    output: str,
    selected: MarketplacePlugin,
    installed_version: str,
) -> None:
    plugin_ref = f"{selected.plugin_name}@{selected.marketplace_name}"
    installed = _installed_plugin(output, plugin_ref)
    if installed.status != "installed, enabled":
        raise RuntimeError("post-validate: installed plugin is not enabled")
    if installed.version != installed_version:
        raise RuntimeError(
            "post-validate: installed version does not match cachebusted version"
        )
    if installed.plugin_root.expanduser().resolve() != selected.plugin_root:
        raise RuntimeError("post-validate: installed root provenance does not match the package")

    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser().resolve()
    cache_root = (
        codex_home
        / "plugins"
        / "cache"
        / selected.marketplace_name
        / selected.plugin_name
        / installed_version
    )
    cache_manifest = cache_root / ".codex-plugin" / "plugin.json"
    if not cache_manifest.is_file():
        raise RuntimeError("post-validate: installed cache path or manifest is missing")
    try:
        cached = json.loads(cache_manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("post-validate: installed cache manifest is invalid") from exc
    if cached.get("name") != selected.plugin_name or cached.get("version") != installed_version:
        raise RuntimeError("post-validate: installed cache manifest provenance is invalid")
    public_skills = {
        path.parent.name
        for path in (cache_root / "skills").glob("scholar-*/SKILL.md")
        if path.is_file()
    }
    if public_skills != PUBLIC_CODEX_SKILLS:
        raise RuntimeError("post-validate: installed cache must expose exactly seven public skills")


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
    configured_root = _marketplace_root(listed, selected.marketplace_name)
    if configured_root is None:
        runner(
            [*codex_command, "plugin", "marketplace", "add", str(repo_root)],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        listed = runner(
            [*codex_command, "plugin", "marketplace", "list"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        configured_root = _marketplace_root(listed, selected.marketplace_name)
    if configured_root != repo_root:
        raise ValueError(
            "configured marketplace root does not match the current canonical repository root"
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
        _validate_installed_plugin(post, selected, installed_version)
        result = ReinstallResult(plugin_ref, installed_version)
    except BaseException as operation_error:
        try:
            _restore_bytes(manifest, base_bytes)
        except BaseException as restore_error:
            raise operation_error from restore_error
        raise
    else:
        _restore_bytes(manifest, base_bytes)
        return result


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
