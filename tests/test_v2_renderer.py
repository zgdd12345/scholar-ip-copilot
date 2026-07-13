from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml

from evidraft.render import HOST_PROFILES, Host, _atomic_copy, load_workflows, render_plugin


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "scholar-ip"
PUBLIC_IDS = {"using", "scope", "research", "paper", "patent", "polish", "xreview"}


def _public_entries(root: Path, host: Host) -> set[str]:
    if host is Host.CLAUDE:
        return {path.stem for path in (root / "commands").glob("*.md")}
    if host is Host.CODEX:
        return {
            path.parent.name.removeprefix("scholar-")
            for path in (root / "skills").glob("scholar-*/SKILL.md")
        }
    return {
        path.stem.removeprefix("scholar-")
        for path in (root / "commands").glob("scholar-*.md")
    }


def test_load_workflows_exposes_seven_entries_and_twenty_three_actions() -> None:
    workflows = load_workflows(PLUGIN_ROOT)

    assert set(workflows) == PUBLIC_IDS
    assert sum(len(workflow.actions) for workflow in workflows.values()) == 23


def test_three_host_profiles_declare_only_host_specific_projection() -> None:
    assert set(HOST_PROFILES) == set(Host)
    assert {profile.invocation for profile in HOST_PROFILES.values()} == {
        "/scholar:<workflow> [action]",
        "$scholar-<workflow> [action]",
        "/scholar-<workflow> [action]",
    }
    assert dict(HOST_PROFILES[Host.CLAUDE].model_tiers) == {
        "fast": "haiku",
        "standard": "sonnet",
        "deep": "opus",
    }
    assert all(profile.hook_projection == () for profile in HOST_PROFILES.values())


@pytest.mark.parametrize("host", list(Host))
def test_render_copies_installable_templates_manifest_and_schemas(
    tmp_path: Path, host: Host
) -> None:
    out = tmp_path / host.value
    render_plugin(PLUGIN_ROOT, out, host)
    private = out / "skills" / ".evidraft-private" if host is Host.CODEX else out / "private"

    assert (private / "plugin.yaml").is_file()
    assert (private / "templates" / "paper-project" / "manuscript" / "main.tex").is_file()
    assert (private / "templates" / "patent-project" / ".evidraft" / "project.yaml").is_file()
    assert (private / "schemas" / "project.schema.json").is_file()
    assert (private / "schemas" / "evidence.schema.json").is_file()
    assert (private / "docs" / "architecture.md").is_file()
    assert (private / "README.md").is_file()


@pytest.mark.parametrize("host", list(Host))
def test_render_copies_native_paper_explanation_resources(tmp_path: Path, host: Host) -> None:
    out = tmp_path / host.value
    render_plugin(PLUGIN_ROOT, out, host)
    private = out / (
        "skills/.evidraft-private" if host is Host.CODEX else "private"
    )
    assert (private / "capabilities/research/paper-explanation/spec.md").is_file()
    assert (private / "roles/modes/paper-explainer.md").is_file()


@pytest.mark.parametrize("missing", ["workflows/patent", "capabilities", "templates"])
def test_renderer_rejects_incomplete_v2_ir_before_output(
    tmp_path: Path, missing: str
) -> None:
    plugin = tmp_path / "plugin"
    shutil.copytree(PLUGIN_ROOT, plugin)
    shutil.rmtree(plugin / missing)
    out = tmp_path / "out"

    with pytest.raises((FileNotFoundError, ValueError)):
        render_plugin(plugin, out, Host.CLAUDE)

    assert not out.exists()


@pytest.mark.parametrize("host", list(Host))
def test_render_exposes_only_seven_public_workflows(tmp_path: Path, host: Host) -> None:
    out = tmp_path / host.value

    written = render_plugin(PLUGIN_ROOT, out, host)

    assert _public_entries(out, host) == PUBLIC_IDS
    assert len([path for path in written if path.name == "workflow.yaml"]) == 7
    manifest = json.loads((out / ".evidraft-render-manifest.json").read_text())
    assert manifest["host"] == host.value
    assert manifest["version"] == 2
    assert len(manifest["owned_paths"]) == len(set(manifest["owned_paths"]))


@pytest.mark.parametrize("host", list(Host))
def test_render_copies_private_stages_and_six_roles(tmp_path: Path, host: Host) -> None:
    out = tmp_path / host.value
    render_plugin(PLUGIN_ROOT, out, host)

    if host is Host.CODEX:
        assert (out / "skills" / "scholar-paper" / "stages" / "draft.md").is_file()
        assert (out / "skills" / ".evidraft-private" / "roles" / "roles.yaml").is_file()
    else:
        assert (out / "private" / "workflows" / "paper" / "stages" / "draft.md").is_file()
        assert (out / "private" / "roles" / "roles.yaml").is_file()
        assert len(list((out / "agents").glob("*.md"))) == 6


@pytest.mark.parametrize("host", [Host.CLAUDE, Host.OPENCODE])
def test_rendered_agents_use_host_frontmatter(tmp_path: Path, host: Host) -> None:
    out = tmp_path / host.value
    render_plugin(PLUGIN_ROOT, out, host)

    agent = out / "agents" / "researcher.md"
    metadata = yaml.safe_load(agent.read_text().split("---", 2)[1])
    if host is Host.CLAUDE:
        assert metadata["name"] == "researcher"
        assert metadata["model"] == "inherit"
        assert "Read" in metadata["tools"]
        assert "Bash:git*" in metadata["tools"]
    else:
        assert metadata["mode"] == "subagent"
        assert metadata["permission"]["bash"]["sudo*"] == "deny"


def test_claude_router_projects_each_action_tier_to_dispatch_model(tmp_path: Path) -> None:
    out = tmp_path / "claude"
    render_plugin(PLUGIN_ROOT, out, Host.CLAUDE)
    router = (out / "commands" / "research.md").read_text()

    assert "fast -> haiku" in router
    assert "standard -> sonnet" in router
    assert "deep -> opus" in router
    assert "selected action's role assignment" in router
    assert "workflow finalize --directory <directory> --pattern <pattern>" in router
    assert "--read-target <target>" in router
    assert "--target <each concrete write path>" in router
    assert "--evidence-id <each current evidence id>" in router
    assert "Bash:rm -rf*" in router
    assert "Bash:sudo*" in router


@pytest.mark.parametrize("host", list(Host))
def test_render_removes_only_previously_owned_stale_files(tmp_path: Path, host: Host) -> None:
    out = tmp_path / host.value
    out.mkdir()
    stale = out / "stale-v1.md"
    unrelated = out / "user-owned.md"
    stale.write_text("old")
    unrelated.write_text("keep")
    (out / ".evidraft-render-manifest.json").write_text(
        json.dumps({"version": 1, "host": host.value, "owned_paths": ["stale-v1.md"]})
    )

    render_plugin(PLUGIN_ROOT, out, host)

    assert not stale.exists()
    assert unrelated.read_text() == "keep"


@pytest.mark.parametrize("host", list(Host))
def test_v1_tree_without_manifest_upgrades_to_exactly_seven_entries(
    tmp_path: Path, host: Host
) -> None:
    out = tmp_path / host.value
    if host is Host.CLAUDE:
        legacy = [
            out / "commands" / "paper-draft.md",
            out / "agents" / "novelty-critic.md",
            out / "skills" / "bib-manager" / "SKILL.md",
            out / "hooks" / "hooks.json",
        ]
        user = out / "commands" / "user-command.md"
    elif host is Host.CODEX:
        legacy = [
            out / "skills" / "scholar-paper-draft" / "SKILL.md",
            out / "skills" / "scholar-skill-bib-manager" / "SKILL.md",
        ]
        user = out / "skills" / "scholar-custom" / "SKILL.md"
    else:
        legacy = [
            out / "commands" / "scholar-paper-draft.md",
            out / "agents" / "novelty-critic.md",
            out / "skills" / "bib-manager" / "SKILL.md",
            out / "plugin.toml",
        ]
        user = out / "commands" / "user-command.md"
    for path in legacy:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("v1")
    user.parent.mkdir(parents=True, exist_ok=True)
    user.write_text("user-owned")

    render_plugin(PLUGIN_ROOT, out, host)

    assert PUBLIC_IDS.issubset(_public_entries(out, host))
    assert not any(path.exists() for path in legacy)
    assert user.read_text() == "user-owned"


@pytest.mark.parametrize("owned", ["../outside.md", "/tmp/outside.md"])
def test_render_rejects_unsafe_owned_paths(tmp_path: Path, owned: str) -> None:
    out = tmp_path / "codex"
    out.mkdir()
    (out / ".evidraft-render-manifest.json").write_text(
        json.dumps({"version": 1, "host": "codex", "owned_paths": [owned]})
    )

    with pytest.raises(ValueError, match="unsafe owned path"):
        render_plugin(PLUGIN_ROOT, out, Host.CODEX)


def test_render_rejects_symlink_parent_escape_during_cleanup(tmp_path: Path) -> None:
    out = tmp_path / "codex"
    outside = tmp_path / "outside"
    out.mkdir()
    outside.mkdir()
    victim = outside / "victim.md"
    victim.write_text("keep")
    (out / "link").symlink_to(outside, target_is_directory=True)
    (out / ".evidraft-render-manifest.json").write_text(
        json.dumps({"version": 1, "host": "codex", "owned_paths": ["link/victim.md"]})
    )

    with pytest.raises(ValueError, match="escapes render root"):
        render_plugin(PLUGIN_ROOT, out, Host.CODEX)

    assert victim.read_text() == "keep"


def test_render_rejects_symlink_parent_escape_during_write(tmp_path: Path) -> None:
    out = tmp_path / "claude"
    outside = tmp_path / "outside"
    out.mkdir()
    outside.mkdir()
    (out / "commands").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="escapes render root"):
        render_plugin(PLUGIN_ROOT, out, Host.CLAUDE)

    assert not (outside / "paper.md").exists()


def test_render_rejects_symlink_ancestor_before_creating_output(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "linked-parent"
    link.symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink component"):
        render_plugin(PLUGIN_ROOT, link / "bundle", Host.CODEX)

    assert not (outside / "bundle").exists()


def test_atomic_copy_removes_partial_temp_on_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.write_text("new")
    target.write_text("old")

    def fail_after_partial(_source: Path, destination: Path) -> None:
        destination.write_text("partial")
        raise OSError("copy failed")

    monkeypatch.setattr("evidraft.render.shutil.copyfile", fail_after_partial)

    with pytest.raises(OSError, match="copy failed"):
        _atomic_copy(source, target)

    assert target.read_text() == "old"
    assert not list(tmp_path.glob(".target.evidraft-*"))


def test_manifest_replace_failure_removes_temp_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "codex"
    real_replace = __import__("os").replace

    def fail_manifest(source: Path, target: Path) -> None:
        if Path(target).name == ".evidraft-render-manifest.json":
            raise OSError("manifest replace failed")
        real_replace(source, target)

    monkeypatch.setattr("evidraft.transaction.os.replace", fail_manifest)

    with pytest.raises(OSError, match="manifest replace failed"):
        render_plugin(PLUGIN_ROOT, out, Host.CODEX)

    assert not list(out.glob("..evidraft-render-manifest.json.*"))


def test_render_refuses_manifest_directory_without_deleting_it(tmp_path: Path) -> None:
    out = tmp_path / "codex"
    manifest = out / ".evidraft-render-manifest.json"
    manifest.mkdir(parents=True)
    marker = manifest / "user-owned.txt"
    marker.write_text("keep", encoding="utf-8")

    with pytest.raises(ValueError, match="manifest.*regular file"):
        render_plugin(PLUGIN_ROOT, out, Host.CODEX)

    assert marker.read_text(encoding="utf-8") == "keep"


def test_render_transaction_restores_previous_bundle_on_copy_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "claude"
    render_plugin(PLUGIN_ROOT, out, Host.CLAUDE)
    first = out / ".claude-plugin" / "plugin.json"
    first.write_text("previous release")
    previous_manifest = (out / ".evidraft-render-manifest.json").read_text()
    from evidraft.transaction import _copy_node

    real_copy = _copy_node
    calls = 0

    def fail_second(source: Path, target: Path) -> None:
        nonlocal calls
        if target.is_relative_to(out):
            calls += 1
        if calls == 2 and target.is_relative_to(out):
            raise OSError("injected render failure")
        real_copy(source, target)

    monkeypatch.setattr("evidraft.transaction._copy_node", fail_second)

    with pytest.raises(OSError, match="injected render failure"):
        render_plugin(PLUGIN_ROOT, out, Host.CLAUDE)

    assert first.read_text() == "previous release"
    assert (out / ".evidraft-render-manifest.json").read_text() == previous_manifest


def test_clean_rendered_removes_owned_files_only(tmp_path: Path) -> None:
    from evidraft.render import clean_rendered

    out = tmp_path / "codex"
    render_plugin(PLUGIN_ROOT, out, Host.CODEX)
    user_file = out / "user-owned.txt"
    user_file.write_text("keep")

    removed = clean_rendered(out)

    assert removed
    assert user_file.read_text() == "keep"
    assert not (out / ".evidraft-render-manifest.json").exists()
    assert not (out / "skills" / "scholar-paper" / "SKILL.md").exists()


def test_codex_manifest_contains_required_interface_metadata(tmp_path: Path) -> None:
    out = tmp_path / "codex"
    render_plugin(PLUGIN_ROOT, out, Host.CODEX)

    manifest = json.loads((out / ".codex-plugin" / "plugin.json").read_text())
    assert manifest["name"] == "scholar"
    assert manifest["version"] == "2.0.0"
    assert manifest["skills"] == "./skills/"
    assert set(manifest["interface"]) >= {
        "displayName",
        "shortDescription",
        "longDescription",
        "developerName",
        "category",
        "defaultPrompt",
        "capabilities",
    }


def test_rendered_routers_stay_below_context_budget(tmp_path: Path) -> None:
    out = tmp_path / "codex"
    render_plugin(PLUGIN_ROOT, out, Host.CODEX)

    routers = list((out / "skills").glob("scholar-*/SKILL.md"))
    assert len(routers) == 7
    assert sum(len(path.read_text().split()) for path in routers) < 4_000
    assert all(len(path.read_text().splitlines()) <= 150 for path in routers)
