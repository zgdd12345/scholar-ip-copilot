"""Tests for skill-bundle support in the shared loader.

Each <skills>/<id>/ directory is one skill; SKILL.md is the entry, and the
parent directory (the bundle) carries arbitrary sibling files like
references/, assets/, or scripts/. The loader must (a) discover one skill per
bundle, (b) NOT treat references/*.md as additional skills, and (c) record
the bundle directory on the loaded FrontmatterDoc so adapters can propagate
the bundle into rendered output.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.adapters._shared.loader import (
    FrontmatterDoc,
    load_plugin,
)


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


@pytest.fixture
def bundle_plugin(tmp_path: Path) -> Path:
    """A minimal plugin tree with one skill carrying a references/ bundle."""
    root = tmp_path / "plugin"
    _write(
        root / "plugin.yaml",
        "id: testplugin\nname: Testplugin\nversion: 0.0.1\n",
    )
    _write(
        root / "skills" / "alpha" / "SKILL.md",
        "---\nid: alpha\nkind: skill\ntitle: Alpha\ndescription: alpha skill\n---\n\nAlpha body.\n",
    )
    _write(
        root / "skills" / "alpha" / "references" / "stage-1.md",
        "# Stage 1\n\nReference content for stage 1.\n",
    )
    _write(
        root / "skills" / "alpha" / "references" / "schemas" / "plan.yaml",
        "version: 1\n",
    )
    _write(
        root / "skills" / "beta" / "SKILL.md",
        "---\nid: beta\nkind: skill\ntitle: Beta\ndescription: beta skill\n---\n\nBeta body.\n",
    )
    return root


def test_bundle_dir_recorded_on_frontmatterdoc(bundle_plugin: Path) -> None:
    """Each loaded skill carries its bundle_dir (parent of SKILL.md)."""
    plugin = load_plugin(bundle_plugin)
    by_id = {d.id: d for d in plugin.skills}
    assert by_id["alpha"].bundle_dir == bundle_plugin / "skills" / "alpha"
    assert by_id["beta"].bundle_dir == bundle_plugin / "skills" / "beta"


def test_references_not_loaded_as_separate_skills(bundle_plugin: Path) -> None:
    """skills/alpha/references/stage-1.md must NOT show up as its own skill."""
    plugin = load_plugin(bundle_plugin)
    skill_ids = {d.id for d in plugin.skills}
    assert skill_ids == {"alpha", "beta"}, (
        f"expected exactly {{alpha, beta}}, got {skill_ids} — "
        f"references/ files are being misclassified as skills"
    )


def test_validate_skips_bundle_resources(bundle_plugin: Path, tmp_path: Path) -> None:
    """validate() must not error on files inside references/ subdirs.

    The schema is loaded from packages/core/schemas/command.schema.json by
    callers; we synthesize a minimal compatible schema for unit-test isolation.
    """
    from packages.adapters._shared.loader import validate

    schema = tmp_path / "command.schema.json"
    schema.write_text(
        '{"type":"object","required":["id","title","kind"],'
        '"properties":{"kind":{"enum":["command","agent","skill","hook"]}}}',
        encoding="utf-8",
    )
    plugin = load_plugin(bundle_plugin)
    errors = validate(plugin, schema)
    refs_errors = [e for e in errors if "references" in e]
    assert refs_errors == [], (
        f"validate() raised errors on references/ files: {refs_errors}"
    )


def test_opencode_propagates_bundle_files(bundle_plugin: Path, tmp_path: Path) -> None:
    """OpenCode renders skills/<id>/SKILL.md AND every bundle sibling, with
    sub-directory structure preserved."""
    from packages.adapters.opencode.generate import render as render_opencode

    out_dir = tmp_path / "opencode-out"
    written = render_opencode(load_plugin(bundle_plugin), out_dir)

    # Bundle files MUST appear in the written-paths list, not only on disk
    # (regression guard: a future bug that copies files but forgets to extend
    # `written` would otherwise slip past the filesystem assertions below).
    assert (out_dir / "skills" / "alpha" / "references" / "stage-1.md") in written
    assert (out_dir / "skills" / "alpha" / "references" / "schemas" / "plan.yaml") in written

    # SKILL.md still rendered
    assert (out_dir / "skills" / "alpha" / "SKILL.md").is_file()

    # references/ subdir copied verbatim
    assert (out_dir / "skills" / "alpha" / "references" / "stage-1.md").is_file()
    content = (out_dir / "skills" / "alpha" / "references" / "stage-1.md").read_text()
    assert "Stage 1" in content

    # Nested subdir preserved
    assert (out_dir / "skills" / "alpha" / "references" / "schemas" / "plan.yaml").is_file()

    # Skill without a bundle (just SKILL.md) renders cleanly — no spurious extras
    beta_dir = out_dir / "skills" / "beta"
    beta_files = {p.name for p in beta_dir.iterdir() if p.is_file()}
    assert beta_files == {"SKILL.md"}, f"beta should have only SKILL.md, got {beta_files}"


def test_claude_code_propagates_bundle_files(bundle_plugin: Path, tmp_path: Path) -> None:
    """Claude Code renders skills/<id>/SKILL.md AND every bundle sibling."""
    from packages.adapters.claude_code.generate import render as render_claude_code

    out_dir = tmp_path / "claude-out"
    written = render_claude_code(load_plugin(bundle_plugin), out_dir)

    # Bundle files must appear in the written-paths list, not only on disk
    # (regression guard against future bug where copy happens but
    # written.extend(...) is forgotten).
    assert (out_dir / "skills" / "alpha" / "references" / "stage-1.md") in written
    assert (out_dir / "skills" / "alpha" / "references" / "schemas" / "plan.yaml") in written

    assert (out_dir / "skills" / "alpha" / "SKILL.md").is_file()
    assert (out_dir / "skills" / "alpha" / "references" / "stage-1.md").is_file()
    assert (out_dir / "skills" / "alpha" / "references" / "schemas" / "plan.yaml").is_file()

    beta_dir = out_dir / "skills" / "beta"
    beta_files = {p.name for p in beta_dir.iterdir() if p.is_file()}
    assert beta_files == {"SKILL.md"}


def test_codex_cli_propagates_bundle_files(bundle_plugin: Path, tmp_path: Path) -> None:
    """Codex CLI renders skills/scholar-skill-<id>/SKILL.md AND every bundle sibling."""
    from packages.adapters.codex_cli.generate import render as render_codex_cli

    out_dir = tmp_path / "codex-out"
    written = render_codex_cli(load_plugin(bundle_plugin), out_dir)

    # Bundle files must appear in the written-paths list, not only on disk
    # (regression guard against future bug where copy happens but
    # written.extend(...) is forgotten).
    assert (out_dir / "skills" / "scholar-skill-alpha" / "references" / "stage-1.md") in written
    assert (out_dir / "skills" / "scholar-skill-alpha" / "references" / "schemas" / "plan.yaml") in written

    # Source skills land under scholar-skill-<id>/ in Codex's flattened layout
    assert (out_dir / "skills" / "scholar-skill-alpha" / "SKILL.md").is_file()
    assert (out_dir / "skills" / "scholar-skill-alpha" / "references" / "stage-1.md").is_file()
    assert (out_dir / "skills" / "scholar-skill-alpha" / "references" / "schemas" / "plan.yaml").is_file()

    beta_dir = out_dir / "skills" / "scholar-skill-beta"
    beta_files = {p.name for p in beta_dir.iterdir() if p.is_file()}
    assert beta_files == {"SKILL.md"}


# ---------------------------------------------------------------------------
# Dry-run vs render symmetry: --dry-run must enumerate the same paths render()
# actually writes (otherwise users running `make render DRY=1` would get a
# misleading preview that omits bundle resources).
# ---------------------------------------------------------------------------


def _assert_dry_run_matches_render(
    adapter_module, plugin_dir: Path, tmp_path: Path, label: str
) -> None:
    plugin = adapter_module.load_plugin(plugin_dir)
    out_dry = tmp_path / f"{label}-dry"
    out_render = tmp_path / f"{label}-render"
    out_dry.mkdir()  # render mkdirs but dry-run doesn't; equalise for relative_to

    dry = {p.relative_to(out_dry) for p in adapter_module._dry_run_paths(plugin, out_dry)}
    rendered = {p.relative_to(out_render) for p in adapter_module.render(plugin, out_render)}

    assert dry == rendered, (
        f"{label} dry-run != render\n"
        f"  dry-only:    {sorted(dry - rendered)}\n"
        f"  render-only: {sorted(rendered - dry)}"
    )


def test_opencode_dry_run_matches_render(bundle_plugin: Path, tmp_path: Path) -> None:
    from packages.adapters.opencode import generate as oc

    _assert_dry_run_matches_render(oc, bundle_plugin, tmp_path, "opencode")


def test_claude_code_dry_run_matches_render(bundle_plugin: Path, tmp_path: Path) -> None:
    from packages.adapters.claude_code import generate as cc

    _assert_dry_run_matches_render(cc, bundle_plugin, tmp_path, "claude_code")


def test_codex_cli_dry_run_matches_render(bundle_plugin: Path, tmp_path: Path) -> None:
    from packages.adapters.codex_cli import generate as cx

    _assert_dry_run_matches_render(cx, bundle_plugin, tmp_path, "codex_cli")
