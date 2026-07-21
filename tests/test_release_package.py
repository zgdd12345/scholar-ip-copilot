from __future__ import annotations

import json
import os
import shutil
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
from evidraft.render import RENDERER_VERSION, Host


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "scholar-ip"


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


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
