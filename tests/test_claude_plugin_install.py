from __future__ import annotations

import importlib
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest


def _installer():
    try:
        module = importlib.import_module("evidraft.claude_install")
    except ModuleNotFoundError:
        pytest.fail("evidraft.claude_install is missing")
    return module.install_claude_plugin


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    descriptor = repo / ".claude-plugin/marketplace.json"
    descriptor.parent.mkdir(parents=True)
    descriptor.write_text(json.dumps({"name": "scholar-ip-copilot"}), encoding="utf-8")
    return repo


class FakeRunner:
    def __init__(self, add: subprocess.CompletedProcess[str], listing: Any = None) -> None:
        self.add = add
        self.listing = listing
        self.calls: list[tuple[list[str], Path]] = []

    def __call__(self, command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append((command, Path(kwargs["cwd"])))
        if command[-4:] == ["add", ".", "--scope", "project"]:
            return self.add
        if command[-4:] == ["plugin", "marketplace", "list", "--json"]:
            return subprocess.CompletedProcess(command, 0, json.dumps(self.listing), "")
        return subprocess.CompletedProcess(command, 0, "ok", "")


def _already_configured() -> subprocess.CompletedProcess[str]:
    command = ["claude", "plugin", "marketplace", "add", "."]
    return subprocess.CompletedProcess(command, 1, "", "marketplace already configured")


@pytest.mark.parametrize("configured", [".", "repo"])
def test_identical_or_relative_canonical_marketplace_root_is_idempotent(
    tmp_path: Path, configured: str
) -> None:
    install = _installer()
    repo = _repo(tmp_path)
    configured_path = configured if configured == "." else str(repo)
    runner = FakeRunner(
        _already_configured(),
        [{"name": "scholar-ip-copilot", "source": "directory", "path": configured_path}],
    )

    result = install(repo, runner=runner)

    assert result.marketplace_added is False
    assert [call[0] for call in runner.calls] == [
        ["claude", "plugin", "marketplace", "add", ".", "--scope", "project"],
        ["claude", "plugin", "marketplace", "list", "--json"],
        [
            "claude",
            "plugin",
            "update",
            "scholar@scholar-ip-copilot",
            "--scope",
            "project",
        ],
        [
            "claude",
            "plugin",
            "enable",
            "scholar@scholar-ip-copilot",
            "--scope",
            "project",
        ],
    ]


def test_symlink_equivalent_marketplace_root_is_idempotent(tmp_path: Path) -> None:
    install = _installer()
    repo = _repo(tmp_path)
    link = tmp_path / "repo-link"
    link.symlink_to(repo, target_is_directory=True)
    runner = FakeRunner(
        _already_configured(),
        [{"name": "scholar-ip-copilot", "source": "directory", "path": str(link)}],
    )

    result = install(repo, runner=runner)

    assert result.marketplace_added is False


@pytest.mark.parametrize("suffix", ["-old", "/nested"])
def test_conflicting_prefix_or_suffix_marketplace_root_propagates_add_failure(
    tmp_path: Path, suffix: str
) -> None:
    install = _installer()
    repo = _repo(tmp_path)
    configured = f"{repo}{suffix}"
    runner = FakeRunner(
        _already_configured(),
        [{"name": "scholar-ip-copilot", "source": "directory", "path": configured}],
    )

    with pytest.raises(subprocess.CalledProcessError) as raised:
        install(repo, runner=runner)

    assert raised.value.returncode == 1
    assert len(runner.calls) == 2


def test_non_idempotent_marketplace_add_failure_propagates_without_listing(
    tmp_path: Path,
) -> None:
    install = _installer()
    repo = _repo(tmp_path)
    failure = subprocess.CompletedProcess(
        ["claude", "plugin", "marketplace", "add", "."], 7, "", "permission denied"
    )
    runner = FakeRunner(failure)

    with pytest.raises(subprocess.CalledProcessError) as raised:
        install(repo, runner=runner)

    assert raised.value.returncode == 7
    assert len(runner.calls) == 1


def test_successful_add_updates_and_enables_project_plugin(tmp_path: Path) -> None:
    install = _installer()
    repo = _repo(tmp_path)
    runner = FakeRunner(
        subprocess.CompletedProcess(
            ["claude", "plugin", "marketplace", "add", "."], 0, "added", ""
        )
    )

    result = install(repo, runner=runner)

    assert result.marketplace_added is True
    assert [call[0] for call in runner.calls] == [
        ["claude", "plugin", "marketplace", "add", ".", "--scope", "project"],
        [
            "claude",
            "plugin",
            "update",
            "scholar@scholar-ip-copilot",
            "--scope",
            "project",
        ],
        [
            "claude",
            "plugin",
            "enable",
            "scholar@scholar-ip-copilot",
            "--scope",
            "project",
        ],
    ]
