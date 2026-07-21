from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Callable

import pytest

from evidraft.codex_install import reinstall_codex_plugin, validate_marketplace_plugin


def _build_release(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    repo = tmp_path / "repo"
    release = repo / "plugins" / "scholar"
    manifest = release / ".codex-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps({"name": "scholar", "version": "3.0.0"}, indent=2) + "\n",
        encoding="utf-8",
    )
    for name in (
        "using",
        "scope",
        "research",
        "paper",
        "patent",
        "polish",
        "xreview",
    ):
        skill = release / "skills" / f"scholar-{name}" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text(f"# {name}\n", encoding="utf-8")
    marketplace = repo / ".agents" / "plugins" / "marketplace.json"
    marketplace.parent.mkdir(parents=True)
    marketplace.write_text(
        json.dumps(
            {
                "name": "scholar-ip-copilot",
                "plugins": [
                    {
                        "name": "scholar",
                        "source": {
                            "source": "local",
                            "path": "./plugins/scholar",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    creator = tmp_path / "plugin-creator"
    (creator / "scripts").mkdir(parents=True)
    for script in (
        "validate_plugin.py",
        "read_marketplace_name.py",
        "update_plugin_cachebuster.py",
    ):
        (creator / "scripts" / script).write_text("# fake helper\n", encoding="utf-8")
    return repo, marketplace, release, creator


def _runner(
    release: Path,
    calls: list[list[str]],
    *,
    failing_step: str | None = None,
    marketplace_list: str = "scholar-ip-copilot /tmp/repo\n",
) -> Callable[..., subprocess.CompletedProcess[str]]:
    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs == {
            "cwd": release.parents[1].resolve(),
            "check": True,
            "capture_output": True,
            "text": True,
        }
        calls.append(command)
        if command[1].endswith("read_marketplace_name.py"):
            return subprocess.CompletedProcess(command, 0, "scholar-ip-copilot\n", "")
        if command[1].endswith("update_plugin_cachebuster.py"):
            manifest = release / ".codex-plugin" / "plugin.json"
            document = json.loads(manifest.read_text(encoding="utf-8"))
            document["version"] = "3.0.0+codex.test"
            manifest.write_text(json.dumps(document) + "\n", encoding="utf-8")
            if failing_step == "cachebuster":
                raise RuntimeError("cachebuster")
            return subprocess.CompletedProcess(command, 0, "", "")
        if command[-3:] == ["plugin", "marketplace", "list"]:
            return subprocess.CompletedProcess(command, 0, marketplace_list, "")
        if command[-3:-1] == ["plugin", "add"]:
            if failing_step == "plugin-add":
                raise RuntimeError("plugin-add")
            return subprocess.CompletedProcess(command, 0, "", "")
        if command[-2:] == ["plugin", "list"]:
            if failing_step == "post-validate":
                return subprocess.CompletedProcess(
                    command,
                    0,
                    "scholar@scholar-ip-copilot installed, disabled\n",
                    "",
                )
            return subprocess.CompletedProcess(
                command,
                0,
                "scholar@scholar-ip-copilot installed, enabled\n",
                "",
            )
        return subprocess.CompletedProcess(command, 0, "", "")

    return run


def test_reinstall_restores_base_manifest_after_success(tmp_path: Path) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    calls: list[list[str]] = []
    original = (release / ".codex-plugin" / "plugin.json").read_bytes()

    result = reinstall_codex_plugin(
        repo,
        marketplace,
        release,
        creator,
        runner=_runner(release, calls),
    )

    assert result.plugin_ref == "scholar@scholar-ip-copilot"
    assert result.installed_version == "3.0.0+codex.test"
    assert (release / ".codex-plugin" / "plugin.json").read_bytes() == original
    assert any(command[-3:] == ["plugin", "add", result.plugin_ref] for command in calls)
    cachebusters = [command for command in calls if command[1].endswith("update_plugin_cachebuster.py")]
    assert len(cachebusters) == 1
    assert calls[0][1].endswith("validate_plugin.py")
    assert calls[1][1].endswith("read_marketplace_name.py")
    assert calls[2][-3:] == ["plugin", "marketplace", "list"]
    assert calls[3][1].endswith("update_plugin_cachebuster.py")
    assert calls[4][-3:] == ["plugin", "add", result.plugin_ref]
    assert calls[5][-2:] == ["plugin", "list"]


@pytest.mark.parametrize("failing_step", ["cachebuster", "plugin-add", "post-validate"])
def test_reinstall_restores_base_manifest_after_failure(
    tmp_path: Path, failing_step: str
) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    calls: list[list[str]] = []
    original = (release / ".codex-plugin" / "plugin.json").read_bytes()

    with pytest.raises(RuntimeError, match=failing_step):
        reinstall_codex_plugin(
            repo,
            marketplace,
            release,
            creator,
            runner=_runner(release, calls, failing_step=failing_step),
        )

    assert (release / ".codex-plugin" / "plugin.json").read_bytes() == original
    cachebusters = [command for command in calls if command[1].endswith("update_plugin_cachebuster.py")]
    assert len(cachebusters) == 1


def test_reinstall_configures_repo_marketplace_before_cachebusting(tmp_path: Path) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    calls: list[list[str]] = []

    reinstall_codex_plugin(
        repo,
        marketplace,
        release,
        creator,
        runner=_runner(release, calls, marketplace_list="other /tmp/other\n"),
    )

    add_marketplace = next(
        index
        for index, command in enumerate(calls)
        if command[-4:-1] == ["plugin", "marketplace", "add"]
    )
    cachebuster = next(
        index for index, command in enumerate(calls) if command[1].endswith("update_plugin_cachebuster.py")
    )
    assert calls[add_marketplace][-1] == str(repo.resolve())
    assert add_marketplace < cachebuster
    assert all(
        command[:3] == ["codex", "-c", 'model_reasoning_effort="xhigh"']
        for command in calls
        if command[0] == "codex"
    )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda document: document.update(name="wrong"), "unexpected marketplace name"),
        (
            lambda document: document["plugins"][0].update(
                source={"source": "github", "repo": "example/scholar"}
            ),
            "must be local",
        ),
        (
            lambda document: document["plugins"][0].update(
                source={"source": "local", "path": "./plugins/other"}
            ),
            "must be local",
        ),
        (lambda document: document.update(plugins=[]), "exactly one scholar entry"),
    ],
)
def test_invalid_marketplace_fails_before_commands(
    tmp_path: Path,
    mutation: Callable[[dict[str, object]], None],
    message: str,
) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    document = json.loads(marketplace.read_text(encoding="utf-8"))
    mutation(document)
    marketplace.write_text(json.dumps(document), encoding="utf-8")
    calls: list[list[str]] = []

    with pytest.raises(ValueError, match=message):
        reinstall_codex_plugin(
            repo,
            marketplace,
            release,
            creator,
            runner=_runner(release, calls),
        )

    assert calls == []


def test_missing_package_fails_before_commands(tmp_path: Path) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    (release / ".codex-plugin" / "plugin.json").unlink()
    calls: list[list[str]] = []

    with pytest.raises(FileNotFoundError):
        reinstall_codex_plugin(
            repo,
            marketplace,
            release,
            creator,
            runner=_runner(release, calls),
        )

    assert calls == []


def test_requested_plugin_root_mismatch_fails_before_commands(tmp_path: Path) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    calls: list[list[str]] = []

    with pytest.raises(ValueError, match="requested plugin roots differ"):
        reinstall_codex_plugin(
            repo,
            marketplace,
            repo / "plugins" / "other",
            creator,
            runner=_runner(release, calls),
        )

    assert calls == []


def test_wrong_package_name_fails_before_commands(tmp_path: Path) -> None:
    repo, marketplace, release, creator = _build_release(tmp_path)
    manifest = release / ".codex-plugin" / "plugin.json"
    document = json.loads(manifest.read_text(encoding="utf-8"))
    document["name"] = "other"
    manifest.write_text(json.dumps(document), encoding="utf-8")
    calls: list[list[str]] = []

    with pytest.raises(ValueError, match="package name"):
        reinstall_codex_plugin(
            repo,
            marketplace,
            release,
            creator,
            runner=_runner(release, calls),
        )

    assert calls == []


def test_validate_rejects_package_without_exactly_seven_public_skills(tmp_path: Path) -> None:
    repo, marketplace, release, _ = _build_release(tmp_path)
    (release / "skills" / "scholar-using" / "SKILL.md").unlink()

    with pytest.raises(ValueError, match="exactly seven public skills"):
        validate_marketplace_plugin(repo, marketplace)


def test_validate_rejects_wrong_set_of_seven_public_skills(tmp_path: Path) -> None:
    repo, marketplace, release, _ = _build_release(tmp_path)
    (release / "skills" / "scholar-using").rename(
        release / "skills" / "scholar-unexpected"
    )

    with pytest.raises(ValueError, match="exactly seven public skills"):
        validate_marketplace_plugin(repo, marketplace)
