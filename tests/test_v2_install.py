from __future__ import annotations

import json
from pathlib import Path

import pytest

from evidraft.cli import main
from evidraft.install import remove_codex_project_skills, sync_codex_skills
from evidraft.render import Host, render_plugin


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "scholar-ip"
PUBLIC = {"using", "scope", "research", "paper", "patent", "polish", "xreview"}


def _render_codex(tmp_path: Path) -> Path:
    rendered = tmp_path / "rendered"
    render_plugin(PLUGIN, rendered, Host.CODEX)
    return rendered


def test_sync_upgrades_exact_v1_entries_and_preserves_user_skills(tmp_path: Path) -> None:
    source = _render_codex(tmp_path)
    destination = tmp_path / ".agents" / "skills"
    destination.mkdir(parents=True)
    (destination / "scholar-paper-draft").mkdir()
    (destination / "scholar-skill-evidence-check").mkdir()
    custom = destination / "scholar-custom"
    custom.mkdir()
    (custom / "SKILL.md").write_text("user-owned")

    installed = sync_codex_skills(source, destination)

    assert {path.name.removeprefix("scholar-") for path in installed} == PUBLIC
    assert not (destination / "scholar-paper-draft").exists()
    assert not (destination / "scholar-skill-evidence-check").exists()
    assert (custom / "SKILL.md").read_text() == "user-owned"
    visible = {
        path.name.removeprefix("scholar-")
        for path in destination.glob("scholar-*")
        if path.name != "scholar-custom"
    }
    assert visible == PUBLIC
    private = destination / ".evidraft-private"
    assert (private / "capabilities" / "index.yaml").is_file()
    explanation = private / "capabilities" / "research" / "paper-explanation"
    for name in (
        "spec.md",
        "task-graph.yaml",
        "paper-map.schema.json",
        "analysis-packet.schema.json",
    ):
        assert (explanation / name).is_file()
    assert (private / "roles" / "roles.yaml").is_file()
    assert (private / "templates" / "paper-project" / "manuscript" / "main.tex").is_file()
    stage = destination / "scholar-paper" / "stages" / "init.md"
    assert "lazy initialization" in stage.read_text().lower()
    assert "../../../templates/" not in stage.read_text()


def test_sync_removes_only_paths_from_previous_ownership_manifest(tmp_path: Path) -> None:
    source = _render_codex(tmp_path)
    destination = tmp_path / "skills"
    destination.mkdir()
    owned_stale = destination / "old-owned"
    owned_stale.mkdir()
    user = destination / "user-owned"
    user.mkdir()
    (destination / ".evidraft-ownership.json").write_text(
        json.dumps({"version": 2, "owned_paths": ["old-owned"]})
    )

    sync_codex_skills(source, destination)

    assert not owned_stale.exists()
    assert user.is_dir()


def test_sync_rejects_incomplete_render_without_touching_destination(tmp_path: Path) -> None:
    source = _render_codex(tmp_path)
    missing = source / "skills" / "scholar-paper"
    for child in sorted(missing.rglob("*"), reverse=True):
        child.unlink() if child.is_file() else child.rmdir()
    missing.rmdir()
    destination = tmp_path / "skills"
    destination.mkdir()
    sentinel = destination / "keep"
    sentinel.write_text("unchanged")

    with pytest.raises(ValueError, match="exactly seven"):
        sync_codex_skills(source, destination)

    assert sentinel.read_text() == "unchanged"
    assert not (destination / ".evidraft-ownership.json").exists()


@pytest.mark.parametrize(
    "relative",
    [
        "skills/.evidraft-private/capabilities/research/paper-explanation/spec.md",
        "skills/.evidraft-private/capabilities/research/paper-explanation/task-graph.yaml",
        "skills/.evidraft-private/capabilities/research/paper-explanation/paper-map.schema.json",
        "skills/.evidraft-private/capabilities/research/paper-explanation/analysis-packet.schema.json",
        "skills/scholar-research/stages/explain.md",
        "skills/.evidraft-private/roles/modes/paper-indexer.md",
        "skills/.evidraft-private/roles/modes/paper-analysis-worker.md",
        "skills/.evidraft-private/roles/modes/paper-reasoning-worker.md",
        "skills/.evidraft-private/roles/modes/explanation-evidence-auditor.md",
        "skills/.evidraft-private/roles/modes/paper-explainer.md",
    ],
)
def test_sync_rejects_incomplete_explanation_bundle_without_touching_destination(
    tmp_path: Path, relative: str
) -> None:
    source = _render_codex(tmp_path)
    (source / relative).unlink()
    destination = tmp_path / "skills"
    destination.mkdir()
    sentinel = destination / "keep"
    sentinel.write_text("unchanged")

    with pytest.raises(ValueError, match="missing private workflow resources"):
        sync_codex_skills(source, destination)

    assert sentinel.read_text() == "unchanged"
    assert not (destination / ".evidraft-ownership.json").exists()


def test_sync_cli_installs_rendered_codex_skills(tmp_path: Path) -> None:
    source = _render_codex(tmp_path)
    destination = tmp_path / "skills"

    assert main(
        [
            "sync-codex-skills",
            "--source",
            str(source),
            "--dest",
            str(destination),
        ]
    ) == 0

    manifest = json.loads((destination / ".evidraft-ownership.json").read_text())
    assert len(manifest["owned_paths"]) == 7


def test_sync_rolls_back_existing_install_when_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = _render_codex(tmp_path)
    destination = tmp_path / "skills"
    old = destination / "scholar-paper"
    old.mkdir(parents=True)
    (old / "SKILL.md").write_text("old version")
    manifest = destination / ".evidraft-ownership.json"
    previous_manifest = {"version": 2, "owned_paths": ["scholar-paper"]}
    manifest.write_text(json.dumps(previous_manifest))
    from evidraft.transaction import _copy_node

    real_copy = _copy_node
    failed = False

    def fail_once(source_path: Path, target_path: Path) -> None:
        nonlocal failed
        target_path = Path(target_path)
        if (
            not failed
            and target_path == destination / "scholar-paper"
        ):
            failed = True
            raise OSError("injected install failure")
        real_copy(source_path, target_path)

    monkeypatch.setattr("evidraft.transaction._copy_node", fail_once)

    with pytest.raises(OSError, match="injected install failure"):
        sync_codex_skills(source, destination)

    assert (old / "SKILL.md").read_text() == "old version"
    assert json.loads(manifest.read_text()) == previous_manifest


def test_sync_refuses_manifest_directory_without_deleting_it(tmp_path: Path) -> None:
    source = _render_codex(tmp_path)
    destination = tmp_path / "skills"
    manifest = destination / ".evidraft-ownership.json"
    manifest.mkdir(parents=True)
    marker = manifest / "user-owned.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(ValueError, match="manifest.*regular file"):
        sync_codex_skills(source, destination)

    assert marker.read_text(encoding="utf-8") == "keep"


def test_sync_rejects_symlink_ancestor_before_creating_destination(tmp_path: Path) -> None:
    source = _render_codex(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "linked-parent"
    link.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink component"):
        sync_codex_skills(source, link / "skills")

    assert not (outside / "skills").exists()


def test_remove_codex_project_skills_is_idempotent_without_manifest(tmp_path: Path) -> None:
    destination = tmp_path / "skills"
    user_skill = destination / "scholar-user"
    user_skill.mkdir(parents=True)

    assert remove_codex_project_skills(destination) == []
    assert user_skill.is_dir()
