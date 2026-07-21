from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from evidraft.cli import main as cli_main
from evidraft.release import (
    RELEASE_MANIFEST,
    load_plugin_metadata,
    release_package_drift,
    render_plugin_package,
    source_sha256,
)
import evidraft.release as release_module
from evidraft.render import RENDERER_VERSION, Host


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "scholar-ip"


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _release_artifact_inventory() -> dict[str, tuple[str, str]]:
    roots = [ROOT / name for name in ("dist", "build", ".release-smoke-venv")]
    roots.extend(ROOT.glob("*.egg-info"))
    roots.extend((ROOT / "src").glob("*.egg-info"))
    roots.extend((ROOT / "packages").glob("*.egg-info"))
    inventory: dict[str, tuple[str, str]] = {}
    for root in sorted(set(roots)):
        if not root.exists() and not root.is_symlink():
            continue
        paths = [root, *sorted(root.rglob("*"))] if root.is_dir() else [root]
        for path in paths:
            relative = path.relative_to(ROOT).as_posix()
            if path.is_symlink():
                inventory[relative] = ("symlink", os.readlink(path))
            elif path.is_file():
                inventory[relative] = (
                    "file",
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                )
            elif path.is_dir():
                inventory[relative] = ("directory", "")
    return inventory


def _fake_renderer(shared: bytes, *, distinct_by_host: bool = False):
    def render(_plugin: Path, out: Path, host: Host) -> list[Path]:
        out.mkdir(parents=True)
        body = shared + (host.value.encode() if distinct_by_host else b"")
        common = out / "shared.txt"
        common.write_bytes(body)
        manifest = out / ".evidraft-render-manifest.json"
        manifest.write_text("{}\n", encoding="utf-8")
        return [common, manifest]

    return render


def _plugin_with_source_symlink(tmp_path: Path, kind: str) -> Path:
    plugin = tmp_path / "plugin"
    shutil.copytree(PLUGIN, plugin)
    if kind == "file":
        linked = plugin / "README.md"
        linked.unlink()
        linked.symlink_to(PLUGIN / "README.md")
    elif kind == "directory":
        linked = plugin / "templates"
        shutil.rmtree(linked)
        linked.symlink_to(PLUGIN / "templates", target_is_directory=True)
    elif kind == "root":
        linked = tmp_path / "linked-plugin"
        linked.symlink_to(plugin, target_is_directory=True)
        plugin = linked
    else:
        linked_parent = tmp_path / "linked-parent"
        linked_parent.symlink_to(tmp_path, target_is_directory=True)
        plugin = linked_parent / plugin.name
    return plugin


def _wheel_source_repo(root: Path) -> None:
    (root / "src/evidraft").mkdir(parents=True)
    (root / "packages/adapters").mkdir(parents=True)
    for name in ("pyproject.toml", "README.md", "LICENSE"):
        (root / name).write_text(f"current {name}\n", encoding="utf-8")
    (root / "src/evidraft/current.py").write_text("CURRENT = True\n", encoding="utf-8")
    (root / "packages/adapters/current.py").write_text(
        "CURRENT = True\n", encoding="utf-8"
    )


def test_load_plugin_metadata_reads_canonical_source() -> None:
    metadata = load_plugin_metadata(PLUGIN)

    assert metadata.id == "scholar"
    assert metadata.display_name == "EviDraft"
    assert metadata.version == "3.0.0"
    assert metadata.description.startswith("Evidence-grounded academic and patent copilot")
    assert metadata.license == "MIT"
    assert metadata.homepage == "https://github.com/zgdd12345/scholar-ip-copilot"
    assert metadata.repository == "https://github.com/zgdd12345/scholar-ip-copilot"
    assert metadata.keywords == (
        "research",
        "literature-review",
        "academic-writing",
        "patents",
        "evidence",
    )
    assert metadata.author_name == "scholar-ip-copilot contributors"


def test_release_package_contains_both_host_surfaces(tmp_path: Path) -> None:
    out = tmp_path / "scholar"

    render_plugin_package(PLUGIN, out)

    assert (out / ".codex-plugin/plugin.json").is_file()
    assert (out / ".claude-plugin/plugin.json").is_file()
    assert len(list((out / "skills").glob("scholar-*/SKILL.md"))) == 7
    assert len(list((out / "commands").glob("*.md"))) == 7
    assert len(list((out / "agents").glob("*.md"))) == 10


@pytest.mark.parametrize("kind", ["file", "directory", "root", "ancestor"])
def test_release_package_rejects_source_symlink_before_creating_output(
    tmp_path: Path, kind: str
) -> None:
    plugin = _plugin_with_source_symlink(tmp_path, kind)
    out = tmp_path / "out"

    with pytest.raises(ValueError, match="source.*symlink"):
        render_plugin_package(plugin, out)

    assert not out.exists()


def test_release_source_symlink_rejection_preserves_existing_output(
    tmp_path: Path,
) -> None:
    plugin = tmp_path / "plugin"
    shutil.copytree(PLUGIN, plugin)
    out = tmp_path / "out"
    render_plugin_package(plugin, out)
    before = _tree_bytes(out)
    readme = plugin / "README.md"
    readme.unlink()
    readme.symlink_to(PLUGIN / "README.md")

    with pytest.raises(ValueError, match="source.*symlink"):
        render_plugin_package(plugin, out)

    assert _tree_bytes(out) == before


def test_release_package_is_path_and_mtime_independent(tmp_path: Path) -> None:
    first_plugin = tmp_path / "a" / "plugin"
    second_plugin = tmp_path / "b" / "plugin"
    shutil.copytree(PLUGIN, first_plugin)
    shutil.copytree(PLUGIN, second_plugin)
    for path in second_plugin.rglob("*"):
        if path.is_file():
            os.utime(path, (1_000_000_000, 1_000_000_000))
    first = tmp_path / "first"
    second = tmp_path / "second"

    render_plugin_package(first_plugin, first)
    render_plugin_package(second_plugin, second)

    assert source_sha256(first_plugin) == source_sha256(second_plugin)
    assert _tree_bytes(first) == _tree_bytes(second)


def test_release_manifest_records_only_deterministic_provenance(tmp_path: Path) -> None:
    out = tmp_path / "scholar"

    render_plugin_package(PLUGIN, out)

    raw = (out / RELEASE_MANIFEST).read_text(encoding="utf-8")
    manifest = json.loads(raw)
    assert manifest["format_version"] == 1
    assert manifest["plugin"] == {"id": "scholar", "version": "3.0.0"}
    assert manifest["renderer_version"] == RENDERER_VERSION
    assert manifest["source_sha256"] == source_sha256(PLUGIN)
    assert set(manifest["hosts"]) == {"claude", "codex"}
    assert all(paths == sorted(paths) for paths in manifest["hosts"].values())
    assert str(PLUGIN.resolve()) not in raw
    assert "timestamp" not in manifest
    assert "mtime" not in manifest


def test_same_path_same_bytes_collision_is_coalesced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("evidraft.release.render_plugin", _fake_renderer(b"same"))
    out = tmp_path / "scholar"

    render_plugin_package(PLUGIN, out)

    assert (out / "shared.txt").read_bytes() == b"same"
    manifest = json.loads((out / RELEASE_MANIFEST).read_text(encoding="utf-8"))
    assert manifest["hosts"] == {"claude": ["shared.txt"], "codex": ["shared.txt"]}


def test_same_path_different_bytes_collision_precedes_output_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "scholar"
    render_plugin_package(PLUGIN, out)
    before = _tree_bytes(out)
    monkeypatch.setattr(
        "evidraft.release.render_plugin",
        _fake_renderer(b"different-", distinct_by_host=True),
    )

    with pytest.raises(ValueError, match=r"release path collision: shared.txt from claude and codex"):
        render_plugin_package(PLUGIN, out)

    assert _tree_bytes(out) == before


def test_release_transaction_restores_previous_package_on_copy_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "scholar"
    render_plugin_package(PLUGIN, out)
    before = _tree_bytes(out)
    plugin = tmp_path / "plugin"
    shutil.copytree(PLUGIN, plugin)
    plugin_yaml = plugin / "plugin.yaml"
    plugin_yaml.write_text(
        plugin_yaml.read_text(encoding="utf-8").replace(
            "Evidence-grounded academic and patent copilot",
            "Changed academic and patent copilot",
        ),
        encoding="utf-8",
    )
    from evidraft.transaction import _copy_node

    real_copy = _copy_node
    writes = 0

    def fail_second_output_copy(source: Path, target: Path) -> None:
        nonlocal writes
        if target.is_relative_to(out):
            writes += 1
            if writes == 2:
                raise OSError("injected package failure")
        real_copy(source, target)

    monkeypatch.setattr("evidraft.transaction._copy_node", fail_second_output_copy)

    with pytest.raises(OSError, match="injected package failure"):
        render_plugin_package(plugin, out)

    assert _tree_bytes(out) == before


def test_unknown_release_file_is_rejected_and_preserved(tmp_path: Path) -> None:
    out = tmp_path / "scholar"
    unknown = out / "user-notes.md"
    unknown.parent.mkdir()
    unknown.write_text("keep", encoding="utf-8")
    adjacent = tmp_path / "adjacent.txt"
    adjacent.write_text("also keep", encoding="utf-8")

    with pytest.raises(ValueError, match="unknown files in release root: user-notes.md"):
        render_plugin_package(PLUGIN, out)

    assert unknown.read_text(encoding="utf-8") == "keep"
    assert adjacent.read_text(encoding="utf-8") == "also keep"
    assert not (out / RELEASE_MANIFEST).exists()


def test_release_package_drift_is_sorted_and_read_only(tmp_path: Path) -> None:
    out = tmp_path / "scholar"
    render_plugin_package(PLUGIN, out)
    (out / ".codex-plugin/plugin.json").unlink()
    (out / "commands/using.md").write_text("changed", encoding="utf-8")
    (out / "unexpected.txt").write_text("unexpected", encoding="utf-8")
    before = _tree_bytes(out)

    findings = release_package_drift(PLUGIN, out)

    assert findings == [
        "missing: .codex-plugin/plugin.json",
        "changed: commands/using.md",
        "unexpected: unexpected.txt",
    ]
    assert _tree_bytes(out) == before


def test_package_cli_renders_and_checks_without_writing_on_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "scholar"
    assert cli_main(["package", "--plugin", str(PLUGIN), "--out", str(out)]) == 0
    assert cli_main(
        ["package", "--plugin", str(PLUGIN), "--out", str(out), "--check"]
    ) == 0
    capsys.readouterr()
    (out / "commands/using.md").write_text("changed", encoding="utf-8")
    before = _tree_bytes(out)

    assert cli_main(
        ["package", "--plugin", str(PLUGIN), "--out", str(out), "--check"]
    ) == 1

    assert capsys.readouterr().out == "changed: commands/using.md\n"
    assert _tree_bytes(out) == before


def test_package_cli_check_does_not_create_missing_target(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "missing"

    assert cli_main(
        ["package", "--plugin", str(PLUGIN), "--out", str(out), "--check"]
    ) == 1

    assert "missing: .claude-plugin/plugin.json" in capsys.readouterr().out
    assert not out.exists()


def test_tracked_release_package_has_no_drift() -> None:
    assert release_package_drift(PLUGIN, ROOT / "plugins/scholar") == []


def test_wheel_gate_forbids_plugin_payload() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    for prefix in ("plugins/", ".codex-plugin/", ".claude-plugin/", "skills/"):
        assert prefix in makefile


def test_wheel_smoke_clears_checkout_pythonpath() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "SMOKE_ENV    := env -u PYTHONPATH" in makefile
    assert '$(SMOKE_ENV) "$$root/venv/bin/python" -m pip install' in makefile
    assert 'cd "$$root"' in makefile


def test_wheel_smoke_contract_uses_one_external_temporary_root() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    header = next(line for line in makefile.splitlines() if line.startswith("wheel-smoke:"))
    match = re.search(
        r"^wheel-smoke:[^\n]*\n(?P<body>(?:\t.*\n)+)",
        makefile,
        flags=re.MULTILINE,
    )
    assert match is not None
    recipe = header + "\n" + match.group("body")

    assert header == "wheel-smoke:"
    assert "mktemp -d /tmp/evidraft-wheel-smoke" in recipe
    assert "stage_wheel_source" in recipe
    assert "trap 'rm -rf \"$$root\"' EXIT" in recipe
    for external in ("$$root/source", "$$root/dist", "$$root/venv", "$$root/plugin"):
        assert external in recipe
    assert "$(DIST_DIR)" not in recipe
    assert "$(SMOKE_VENV)" not in recipe


def test_wheel_smoke_resolves_python_before_running_entire_smoke_from_tmp() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    match = re.search(
        r"^wheel-smoke:[^\n]*\n(?P<body>(?:\t.*\n)+)",
        makefile,
        flags=re.MULTILINE,
    )
    assert match is not None
    recipe = match.group("body")

    resolve_python = "python=$$($(SMOKE_ENV) $(PYTHON) -c"
    change_directory = 'cd "$$root";'
    assert resolve_python in recipe
    assert "os.path.abspath(sys.executable)" in recipe
    assert recipe.index(resolve_python) < recipe.index(change_directory)

    external_recipe = recipe.split(change_directory, maxsplit=1)[1]
    assert "$(PYTHON)" not in external_recipe
    assert "stage_wheel_source" in external_recipe
    staging_prefix = external_recipe.split("stage_wheel_source", maxsplit=1)[0]
    assert '$(SMOKE_ENV) "$$python" -c' in staging_prefix
    assert '"$(CURDIR)/src"' in external_recipe
    assert '"$(CURDIR)" "$$root/source"' in external_recipe
    assert 'cp -R "$(CURDIR)/$(PLUGIN_SRC)" "$$root/plugin"' in external_recipe
    assert external_recipe.index("stage_wheel_source") < external_recipe.index("cp -R")
    for command in (
        '$(SMOKE_ENV) "$$python" -m build',
        '$(SMOKE_ENV) "$$python" -m venv',
        '$(SMOKE_ENV) "$$root/venv/bin/python" -m pip install',
        '$(SMOKE_ENV) "$$root/venv/bin/evidraft" --help',
        '$(SMOKE_ENV) "$$root/venv/bin/evidraft-claude-code" --plugin',
        '$(SMOKE_ENV) "$$root/venv/bin/evidraft-codex-cli" --plugin',
        '$(SMOKE_ENV) "$$root/venv/bin/evidraft-opencode" --plugin',
    ):
        assert command in external_recipe


def test_real_wheel_smoke_preserves_repo_release_artifacts() -> None:
    before = _release_artifact_inventory()
    environment = os.environ.copy()
    environment["PYTHONPATH"] = "src:."

    subprocess.run(
        ["make", f"PYTHON={sys.executable}", "wheel-smoke"],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert _release_artifact_inventory() == before


def test_wheel_source_staging_copies_current_tree_without_build_artifacts(
    tmp_path: Path,
) -> None:
    stage = getattr(release_module, "stage_wheel_source", None)
    assert stage is not None
    repo = tmp_path / "repo"
    (repo / "src/evidraft/__pycache__").mkdir(parents=True)
    (repo / "packages/adapters").mkdir(parents=True)
    for name in ("pyproject.toml", "README.md", "LICENSE"):
        (repo / name).write_text(f"current {name}\n", encoding="utf-8")
    (repo / "src/evidraft/current.py").write_text("CURRENT = True\n", encoding="utf-8")
    (repo / "src/evidraft/__pycache__/stale.pyc").write_bytes(b"stale")
    (repo / "packages/adapters/current.py").write_text("CURRENT = True\n", encoding="utf-8")
    (repo / "packages/adapters/stale.egg-info").mkdir()
    out = tmp_path / "outside" / "source"

    stage(repo, out)

    assert (out / "src/evidraft/current.py").read_text() == "CURRENT = True\n"
    assert (out / "packages/adapters/current.py").read_text() == "CURRENT = True\n"
    assert not (out / "src/evidraft/__pycache__").exists()
    assert not (out / "packages/adapters/stale.egg-info").exists()


@pytest.mark.parametrize("kind", ["file", "directory", "root", "ancestor"])
def test_wheel_source_staging_rejects_symlink_before_creating_output_parent(
    tmp_path: Path, kind: str
) -> None:
    repo = tmp_path / "repo"
    _wheel_source_repo(repo)
    if kind == "file":
        outside = tmp_path / "outside-readme.md"
        outside.write_text("outside\n", encoding="utf-8")
        (repo / "README.md").unlink()
        (repo / "README.md").symlink_to(outside)
    elif kind == "directory":
        outside = tmp_path / "outside-src"
        shutil.copytree(repo / "src", outside)
        shutil.rmtree(repo / "src")
        (repo / "src").symlink_to(outside, target_is_directory=True)
    elif kind == "root":
        linked = tmp_path / "linked-repo"
        linked.symlink_to(repo, target_is_directory=True)
        repo = linked
    else:
        linked_parent = tmp_path / "linked-parent"
        linked_parent.symlink_to(tmp_path, target_is_directory=True)
        repo = linked_parent / repo.name
    out = tmp_path / "new-parent" / "source"

    with pytest.raises(ValueError, match="source.*symlink"):
        release_module.stage_wheel_source(repo, out)

    assert not out.exists()
    assert not out.parent.exists()


def test_wheel_source_symlink_rejection_preserves_existing_output(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _wheel_source_repo(repo)
    outside = tmp_path / "outside-readme.md"
    outside.write_text("outside\n", encoding="utf-8")
    (repo / "README.md").unlink()
    (repo / "README.md").symlink_to(outside)
    out = tmp_path / "existing"
    out.mkdir()
    marker = out / "marker.txt"
    marker.write_bytes(b"keep exactly\n")
    before = _tree_bytes(out)

    with pytest.raises(ValueError, match="source.*symlink"):
        release_module.stage_wheel_source(repo, out)

    assert _tree_bytes(out) == before


def test_wheel_source_staging_refuses_repository_output(tmp_path: Path) -> None:
    stage = getattr(release_module, "stage_wheel_source", None)
    assert stage is not None
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "packages").mkdir()
    for name in ("pyproject.toml", "README.md", "LICENSE"):
        (repo / name).write_text(name, encoding="utf-8")

    with pytest.raises(ValueError, match="outside repository"):
        stage(repo, repo / "build-source")


def test_portable_codex_manifest_contract() -> None:
    manifest = json.loads(
        (ROOT / "plugins/scholar/.codex-plugin/plugin.json").read_text(encoding="utf-8")
    )

    assert manifest["name"] == "scholar"
    assert manifest["version"] == "3.0.0"
    assert manifest["skills"] == "./skills/"
    assert manifest["interface"]["displayName"] == "EviDraft"
    assert len(list((ROOT / "plugins/scholar/skills").glob("scholar-*/SKILL.md"))) == 7


def test_release_package_markdown_files_have_diff_style_eof_hygiene(
    tmp_path: Path,
) -> None:
    out = tmp_path / "scholar"

    render_plugin_package(PLUGIN, out)

    findings = [
        path.relative_to(out).as_posix()
        for path in sorted(out.rglob("*.md"))
        if not path.read_bytes().endswith(b"\n") or path.read_bytes().endswith(b"\n\n")
    ]

    assert findings == []


@pytest.mark.parametrize(
    ("markdown_body", "expected_body"),
    [
        (b"", b"\n"),
        (b"text", b"text\n"),
        (b"text\n", b"text\n"),
        (b"text\n\n", b"text\n"),
        (b"text\r\n", b"text\n"),
        (b"text\r\n\r\n", b"text\n"),
        (b"text\r\n\n\r\n", b"text\n"),
    ],
)
def test_release_package_normalizes_markdown_eof_without_changing_binary_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    markdown_body: bytes,
    expected_body: bytes,
) -> None:
    binary_body = b"\x00binary\r\n\r\n"

    def render(_plugin: Path, out: Path, _host: Host) -> list[Path]:
        out.mkdir(parents=True)
        markdown = out / "fixture.md"
        markdown.write_bytes(markdown_body)
        binary = out / "fixture.bin"
        binary.write_bytes(binary_body)
        manifest = out / ".evidraft-render-manifest.json"
        manifest.write_text("{}\n", encoding="utf-8")
        return [markdown, binary, manifest]

    monkeypatch.setattr("evidraft.release.render_plugin", render)
    out = tmp_path / "scholar"

    render_plugin_package(PLUGIN, out)

    assert (out / "fixture.md").read_bytes() == expected_body
    assert (out / "fixture.bin").read_bytes() == binary_body
