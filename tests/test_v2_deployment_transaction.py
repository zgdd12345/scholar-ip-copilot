from __future__ import annotations

import json
import multiprocessing
import os
from pathlib import Path

from evidraft.install import sync_codex_skills
from evidraft.render import Host, render_plugin


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "scholar-ip"
PUBLIC = {"using", "scope", "research", "paper", "patent", "polish", "xreview"}


def _crash_after_prepare(kind: str, source: str, destination: str) -> None:
    import evidraft.transaction as transaction

    target_root = Path(destination).resolve()
    real_atomic_json = transaction._atomic_json
    real_copy_node = transaction._copy_node
    prepared = False

    def track_prepare(path: Path, document: dict) -> None:
        nonlocal prepared
        real_atomic_json(path, document)
        if Path(path).name == "journal.json" and document.get("phase") == "prepared":
            prepared = True

    def terminate_on_install(source_path: Path, target_path: Path) -> None:
        if prepared and Path(target_path).is_relative_to(target_root):
            os._exit(91)
        real_copy_node(source_path, target_path)

    transaction._atomic_json = track_prepare
    transaction._copy_node = terminate_on_install
    if kind == "render":
        render_plugin(PLUGIN, target_root, Host.CLAUDE)
    else:
        sync_codex_skills(Path(source), target_root)


def _render_worker(destination: str, ready: multiprocessing.synchronize.Event) -> None:
    ready.wait()
    render_plugin(PLUGIN, Path(destination), Host.CODEX)


def _crash_during_recovery(destination: str) -> None:
    import evidraft.transaction as transaction

    target_root = Path(destination).resolve()
    backup = target_root.parent / f".{target_root.name}.evidraft-transaction" / "backup"
    real_copy_node = transaction._copy_node

    def terminate_after_one_restore(source_path: Path, target_path: Path) -> None:
        real_copy_node(source_path, target_path)
        if Path(source_path).is_relative_to(backup) and Path(target_path).is_relative_to(
            target_root
        ):
            os._exit(92)

    transaction._copy_node = terminate_after_one_restore
    render_plugin(PLUGIN, target_root, Host.CLAUDE)


def _public_codex_skills(destination: Path) -> set[str]:
    return {
        path.parent.name.removeprefix("scholar-")
        for path in destination.glob("scholar-*/SKILL.md")
    }


def test_renderer_recovers_after_process_exit_mid_commit(tmp_path: Path) -> None:
    destination = tmp_path / "claude"
    render_plugin(PLUGIN, destination, Host.CLAUDE)
    sentinel = destination / ".claude-plugin" / "plugin.json"
    sentinel.write_text("previous release", encoding="utf-8")

    context = multiprocessing.get_context("fork")
    process = context.Process(
        target=_crash_after_prepare,
        args=("render", "", str(destination)),
    )
    process.start()
    process.join(30)

    assert process.exitcode == 91
    transaction = tmp_path / ".claude.evidraft-transaction"
    assert transaction.is_dir()
    assert not sentinel.exists()

    render_plugin(PLUGIN, destination, Host.CLAUDE)

    assert not transaction.exists()
    manifest = json.loads(
        (destination / ".evidraft-render-manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["version"] == 2
    assert {path.stem for path in (destination / "commands").glob("*.md")} == PUBLIC


def test_codex_install_recovers_after_process_exit_mid_commit(tmp_path: Path) -> None:
    rendered = tmp_path / "rendered"
    render_plugin(PLUGIN, rendered, Host.CODEX)
    destination = tmp_path / "skills"
    sync_codex_skills(rendered, destination)
    sentinel = destination / "scholar-paper" / "SKILL.md"
    sentinel.write_text("previous release", encoding="utf-8")

    context = multiprocessing.get_context("fork")
    process = context.Process(
        target=_crash_after_prepare,
        args=("install", str(rendered), str(destination)),
    )
    process.start()
    process.join(30)

    assert process.exitcode == 91
    transaction = tmp_path / ".skills.evidraft-transaction"
    assert transaction.is_dir()
    assert not sentinel.exists()

    sync_codex_skills(rendered, destination)

    assert not transaction.exists()
    assert _public_codex_skills(destination) == PUBLIC
    manifest = json.loads(
        (destination / ".evidraft-ownership.json").read_text(encoding="utf-8")
    )
    assert len(manifest["owned_paths"]) == 7


def test_recovery_remains_idempotent_when_recovery_process_also_exits(tmp_path: Path) -> None:
    destination = tmp_path / "claude"
    render_plugin(PLUGIN, destination, Host.CLAUDE)
    sentinel = destination / ".claude-plugin" / "plugin.json"
    sentinel.write_text("previous release", encoding="utf-8")
    context = multiprocessing.get_context("fork")

    commit = context.Process(
        target=_crash_after_prepare,
        args=("render", "", str(destination)),
    )
    commit.start()
    commit.join(30)
    assert commit.exitcode == 91

    recovery = context.Process(target=_crash_during_recovery, args=(str(destination),))
    recovery.start()
    recovery.join(30)
    assert recovery.exitcode == 92

    render_plugin(PLUGIN, destination, Host.CLAUDE)

    assert json.loads(sentinel.read_text(encoding="utf-8"))["version"] == "3.0.0"
    assert not (tmp_path / ".claude.evidraft-transaction").exists()


def test_concurrent_renderers_serialize_to_one_complete_bundle(tmp_path: Path) -> None:
    destination = tmp_path / "codex"
    context = multiprocessing.get_context("fork")
    ready = context.Event()
    processes = [
        context.Process(target=_render_worker, args=(str(destination), ready)) for _ in range(2)
    ]
    for process in processes:
        process.start()
    ready.set()
    for process in processes:
        process.join(30)

    assert [process.exitcode for process in processes] == [0, 0]
    assert _public_codex_skills(destination / "skills") == PUBLIC
    manifest = json.loads(
        (destination / ".evidraft-render-manifest.json").read_text(encoding="utf-8")
    )
    assert len(manifest["owned_paths"]) == len(set(manifest["owned_paths"]))
    assert not (tmp_path / ".codex.evidraft-transaction").exists()
