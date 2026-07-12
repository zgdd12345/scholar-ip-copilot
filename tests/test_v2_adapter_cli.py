from __future__ import annotations

from pathlib import Path
import shutil

import jsonschema
import pytest

from evidraft.cli import main as evidraft_main
from evidraft.render import Host
from packages.adapters.claude_code.generate import main as claude_main
from packages.adapters.codex_cli.generate import main as codex_main
from packages.adapters.opencode.generate import main as opencode_main


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "scholar-ip"


@pytest.mark.parametrize(
    ("host", "adapter_main"),
    [
        (Host.CLAUDE, claude_main),
        (Host.CODEX, codex_main),
        (Host.OPENCODE, opencode_main),
    ],
)
def test_legacy_adapter_cli_delegates_to_v2_renderer(
    tmp_path: Path, host: Host, adapter_main
) -> None:
    out = tmp_path / host.value

    assert adapter_main(["--plugin", str(PLUGIN_ROOT), "--out", str(out)]) == 0

    if host is Host.CLAUDE:
        entries = list((out / "commands").glob("*.md"))
    elif host is Host.CODEX:
        entries = list((out / "skills").glob("scholar-*/SKILL.md"))
    else:
        entries = list((out / "commands").glob("scholar-*.md"))
    assert len(entries) == 7
    assert (out / ".evidraft-render-manifest.json").is_file()


@pytest.mark.parametrize(
    "adapter_main", [claude_main, codex_main, opencode_main]
)
def test_adapter_dry_run_is_read_only(tmp_path: Path, adapter_main) -> None:
    out = tmp_path / "out"

    assert adapter_main(
        ["--plugin", str(PLUGIN_ROOT), "--out", str(out), "--dry-run"]
    ) == 0

    assert not out.exists()


@pytest.mark.parametrize("host", list(Host))
def test_unified_cli_renders_each_host(tmp_path: Path, host: Host) -> None:
    out = tmp_path / host.value

    assert evidraft_main(
        [
            "--root",
            str(REPO_ROOT),
            "render",
            "--host",
            host.value,
            "--plugin",
            str(PLUGIN_ROOT),
            "--out",
            str(out),
        ]
    ) == 0

    assert (out / ".evidraft-render-manifest.json").is_file()


def test_adapter_fails_closed_for_invalid_workflow(tmp_path: Path) -> None:
    plugin = tmp_path / "plugin"
    workflow = plugin / "workflows" / "bad"
    workflow.mkdir(parents=True)
    (plugin / "roles").mkdir()
    (plugin / "policies").mkdir()
    (workflow / "workflow.yaml").write_text("id: bad\nactions: {}\n")

    with pytest.raises(jsonschema.ValidationError):
        codex_main(["--plugin", str(plugin), "--out", str(tmp_path / "out")])

    assert not (tmp_path / "out").exists()


def test_renderer_accepts_plugin_copied_outside_repository(tmp_path: Path) -> None:
    plugin = tmp_path / "standalone-plugin"
    shutil.copytree(PLUGIN_ROOT, plugin)
    out = tmp_path / "out"

    assert codex_main(["--plugin", str(plugin), "--out", str(out)]) == 0

    assert len(list((out / "skills").glob("scholar-*/SKILL.md"))) == 7


@pytest.mark.parametrize("missing", ["roles", "policies"])
def test_renderer_validates_complete_source_before_creating_output(
    tmp_path: Path, missing: str
) -> None:
    plugin = tmp_path / "standalone-plugin"
    shutil.copytree(PLUGIN_ROOT, plugin)
    shutil.rmtree(plugin / missing)
    out = tmp_path / "out"

    with pytest.raises(FileNotFoundError):
        codex_main(["--plugin", str(plugin), "--out", str(out)])

    assert not out.exists()
