"""Exact-root Claude marketplace installation orchestration."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence


Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class ClaudeInstallResult:
    marketplace_added: bool
    plugin_ref: str


def _default_runner(command: Sequence[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, **kwargs)


def _raise_failure(result: subprocess.CompletedProcess[str]) -> None:
    raise subprocess.CalledProcessError(
        result.returncode,
        result.args,
        output=result.stdout,
        stderr=result.stderr,
    )


def _run(runner: Runner, command: list[str], repo_root: Path) -> subprocess.CompletedProcess[str]:
    return runner(
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def _configured_root(
    entries: object,
    marketplace_name: str,
    repo_root: Path,
) -> Path | None:
    if not isinstance(entries, list):
        return None
    matches = [
        entry
        for entry in entries
        if isinstance(entry, dict) and entry.get("name") == marketplace_name
    ]
    if len(matches) != 1:
        return None
    entry = matches[0]
    if entry.get("source") != "directory" or not isinstance(entry.get("path"), str):
        return None
    configured = Path(entry["path"]).expanduser()
    if not configured.is_absolute():
        configured = repo_root / configured
    return configured.resolve(strict=False)


def install_claude_plugin(
    repo_root: Path,
    *,
    runner: Runner = _default_runner,
) -> ClaudeInstallResult:
    """Add the project marketplace idempotently, then update and enable Scholar."""
    repo_root = Path(repo_root).resolve()
    descriptor = json.loads(
        (repo_root / ".claude-plugin/marketplace.json").read_text(encoding="utf-8")
    )
    marketplace_name = descriptor.get("name")
    if not isinstance(marketplace_name, str) or not marketplace_name:
        raise ValueError("Claude marketplace descriptor must declare a name")
    plugin_ref = f"scholar@{marketplace_name}"

    add = _run(
        runner,
        ["claude", "plugin", "marketplace", "add", ".", "--scope", "project"],
        repo_root,
    )
    marketplace_added = add.returncode == 0
    if not marketplace_added:
        output = f"{add.stdout or ''}\n{add.stderr or ''}".lower()
        if "already configured" not in output:
            _raise_failure(add)
        listing = _run(
            runner,
            ["claude", "plugin", "marketplace", "list", "--json"],
            repo_root,
        )
        if listing.returncode != 0:
            _raise_failure(add)
        try:
            entries = json.loads(listing.stdout)
        except (TypeError, json.JSONDecodeError):
            _raise_failure(add)
        configured = _configured_root(entries, marketplace_name, repo_root)
        if configured != repo_root:
            _raise_failure(add)

    for action in ("update", "enable"):
        result = _run(
            runner,
            ["claude", "plugin", action, plugin_ref, "--scope", "project"],
            repo_root,
        )
        if result.returncode != 0:
            _raise_failure(result)
    return ClaudeInstallResult(
        marketplace_added=marketplace_added,
        plugin_ref=plugin_ref,
    )
