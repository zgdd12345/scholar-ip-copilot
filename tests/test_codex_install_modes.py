from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from evidraft.codex_install import codex_project_mode_preflight
from evidraft.cli import main
from evidraft.install import remove_codex_project_skills


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_REF = "scholar@scholar-ip-copilot"


def _recipe(makefile: str, target: str) -> str:
    lines = makefile.splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith(f"{target}:"))
    recipe: list[str] = []
    for line in lines[start + 1 :]:
        if line and not line.startswith(("\t", " ")):
            break
        recipe.append(line)
    return "\n".join(recipe)


def test_default_and_compatibility_modes_never_install_both_surfaces() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "install-codex: install-codex-plugin" in makefile
    assert "install-codex-plugin:" in makefile
    assert "install-codex-project:" in makefile
    assert "sync-codex-skills" not in _recipe(makefile, "install-codex-plugin")
    assert "plugin add" not in _recipe(makefile, "install-codex-project")
    assert "--out plugins/scholar --check" in _recipe(makefile, "package-check")
    assert "install-codex-project" not in _recipe(makefile, "_install-all")
    assert "install-codex-project" not in _recipe(makefile, "verify")


def test_remove_project_skills_deletes_only_manifest_owned_paths(tmp_path: Path) -> None:
    destination = tmp_path / ".agents" / "skills"
    owned = destination / "scholar-paper"
    legacy_but_unowned = destination / "scholar-paper-draft"
    user = destination / "scholar-custom"
    for path in (owned, legacy_but_unowned, user):
        path.mkdir(parents=True)
        (path / "SKILL.md").write_text(path.name, encoding="utf-8")
    (destination / ".evidraft-ownership.json").write_text(
        '{"version": 2, "owned_paths": ["scholar-paper"]}\n',
        encoding="utf-8",
    )

    removed = remove_codex_project_skills(destination)

    assert removed == [owned]
    assert not owned.exists()
    assert legacy_but_unowned.is_dir()
    assert user.is_dir()
    assert not (destination / ".evidraft-ownership.json").exists()


@pytest.mark.parametrize(
    "manifest_document",
    [
        '{"version": 2, "owned_paths": ["../keep"]}',
        '{"version": 2, "owned_paths": [], "private_path": ".."}',
    ],
)
def test_remove_project_skills_rejects_unsafe_manifest_without_mutation(
    tmp_path: Path, manifest_document: str
) -> None:
    destination = tmp_path / "skills"
    sentinel = destination / "keep"
    sentinel.mkdir(parents=True)
    manifest = destination / ".evidraft-ownership.json"
    manifest.write_text(manifest_document, encoding="utf-8")

    with pytest.raises(ValueError, match=r"unsafe (owned|private) skill path"):
        remove_codex_project_skills(destination)

    assert sentinel.is_dir()
    assert manifest.is_file()


def test_project_mode_refuses_active_plugin_without_removing_it(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, f"{PLUGIN_REF} installed, enabled\n", "")

    with pytest.raises(RuntimeError, match=r"codex plugin remove scholar@scholar-ip-copilot"):
        codex_project_mode_preflight(tmp_path, runner=runner)

    assert len(calls) == 1
    assert calls[0][-2:] == ["plugin", "list"]
    assert all("remove" not in command for command in calls)


def test_project_mode_allows_inactive_plugin(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, f"{PLUGIN_REF} available, disabled\n", "")

    codex_project_mode_preflight(tmp_path, runner=runner)

    assert len(calls) == 1


def test_install_plugin_cli_accepts_explicit_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: list[tuple[Path, Path, Path, Path]] = []

    @dataclass(frozen=True)
    class Result:
        plugin_ref: str = PLUGIN_REF
        installed_version: str = "3.0.0+codex.test"

    def reinstall(repo: Path, marketplace: Path, plugin: Path, creator: Path) -> Result:
        captured.append((repo, marketplace, plugin, creator))
        return Result()

    monkeypatch.setattr("evidraft.cli.reinstall_codex_plugin", reinstall)
    repo = tmp_path / "repo"
    marketplace = repo / ".agents" / "plugins" / "marketplace.json"
    plugin = repo / "plugins" / "scholar"
    creator = tmp_path / "creator"

    assert main(
        [
            "install-codex-plugin",
            "--repo-root",
            str(repo),
            "--marketplace",
            str(marketplace),
            "--plugin",
            str(plugin),
            "--plugin-creator",
            str(creator),
        ]
    ) == 0
    assert captured == [(repo, marketplace, plugin, creator)]


def test_remove_and_preflight_cli_commands_delegate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, Path]] = []
    monkeypatch.setattr(
        "evidraft.cli.remove_codex_project_skills",
        lambda destination: calls.append(("remove", destination)) or [],
    )
    monkeypatch.setattr(
        "evidraft.cli.codex_project_mode_preflight",
        lambda repo: calls.append(("preflight", repo)),
    )

    destination = tmp_path / "skills"
    assert main(["remove-codex-project-skills", "--dest", str(destination)]) == 0
    assert main(["codex-project-mode-preflight", "--repo-root", str(tmp_path)]) == 0
    assert calls == [("remove", destination), ("preflight", tmp_path)]
