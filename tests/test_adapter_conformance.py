"""Adapter conformance test suite (Module K).

Runs each adapter against ``plugins/scholar-ip/`` into a temp dir and asserts
*structural* invariants — not byte-for-byte snapshots. The invariants survive
ordinary content edits (a wording tweak in a skill body must not break CI) but
catch the regressions Module K is meant to gate:

    A. file-count invariants — every source artefact maps to the expected
       rendered file(s) per adapter
    B. frontmatter survival  — emitted frontmatter fields equal source values
    C. retention preamble    — ``## Pre-run cleanup`` appears IFF source
       declares ``retention:`` (symmetric)
    D. no MCP references     — rendered output does not REGRESS by adding new
       files that mention the deprecated ``*-mcp`` server names. Implemented
       as a ratchet against ``expected_counts.json`` so existing legacy
       mentions in source bodies do not break CI, but any *new* file gaining
       an MCP reference does
    E. required skills       — every ``../skills/<X>/SKILL.md`` referenced by
       a command exists in source AND is rendered by claude-code / codex-cli

Style and parametrisation mirror ``tests/test_schema_fixtures.py``.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from packages.adapters._shared.loader import (
    Plugin,
    load_plugin,
    split_frontmatter,
)
from packages.adapters.claude_code.generate import render as render_claude_code
from packages.adapters.codex_cli.generate import render as render_codex_cli

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = REPO_ROOT / "plugins" / "scholar-ip"
FIXTURE = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "adapter_invariants"
    / "expected_counts.json"
)

# Adapter ids exposed to pytest.mark.parametrize. ``opencode`` is lint-only.
ADAPTERS = ("claude_code", "codex_cli", "opencode")
WRITING_ADAPTERS = ("claude_code", "codex_cli")

MCP_TERMS = (
    "scholar-search-mcp",
    "bib-manager-mcp",
    "latex-build-mcp",
    "code-intel-mcp",
    "experiment-mcp",
    "patent-search-mcp",
    "external-agent-mcp",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def plugin() -> Plugin:
    return load_plugin(PLUGIN_DIR)


@pytest.fixture(scope="module")
def expected() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rendered(plugin: Plugin, tmp_path_factory: pytest.TempPathFactory) -> dict[
    str, dict[str, Any]
]:
    """Render each writing adapter once and cache the result.

    Returns a dict keyed by adapter id with ``{"root": Path, "files":
    list[Path]}``. ``opencode`` is intentionally absent — it is exercised via
    its CLI dry-run in ``test_opencode_lint_dry_run``.
    """
    out: dict[str, dict[str, Any]] = {}

    cc_root = tmp_path_factory.mktemp("claude_code")
    out["claude_code"] = {
        "root": cc_root.resolve(),
        "files": render_claude_code(plugin, cc_root),
    }

    cx_root = tmp_path_factory.mktemp("codex_cli")
    out["codex_cli"] = {
        "root": cx_root.resolve(),
        "files": render_codex_cli(plugin, cx_root),
    }
    return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _files_under(files: list[Path], subdir: str) -> list[Path]:
    """Return rendered files whose path contains ``/<subdir>/``."""
    needle = f"/{subdir}/"
    return [p for p in files if needle in str(p)]


def _rel_paths(files: list[Path], root: Path) -> set[str]:
    return {str(p.relative_to(root)) for p in files}


def _source_skill_ids_referenced_by_commands(plugin: Plugin) -> set[str]:
    """Walk every command's ``references:`` block for ``../skills/<X>/SKILL.md``
    and return the set of referenced skill ids.
    """
    pattern = re.compile(r"\.\./skills/([^/]+)/SKILL\.md")
    found: set[str] = set()
    for cmd in plugin.commands:
        refs = (cmd.meta or {}).get("references") or []
        for r in refs:
            doc = r.get("doc") if isinstance(r, dict) else None
            if not doc:
                continue
            m = pattern.match(str(doc))
            if m:
                found.add(m.group(1))
    return found


# ---------------------------------------------------------------------------
# Source-count fixture (drift catcher)
# ---------------------------------------------------------------------------


def test_expected_counts_match_source_tree(
    plugin: Plugin, expected: dict[str, Any]
) -> None:
    """Re-count source artefacts and assert they match the JSON fixture.

    A contributor adding/removing a command/agent/skill/hook MUST bump the
    fixture, which surfaces in CI as a clear, intentional change.
    """
    assert len(plugin.commands) == expected["commands"], (
        f"source commands={len(plugin.commands)} but fixture says "
        f"{expected['commands']}; update expected_counts.json"
    )
    assert len(plugin.agents) == expected["agents"], (
        f"source agents={len(plugin.agents)} but fixture says "
        f"{expected['agents']}; update expected_counts.json"
    )
    assert len(plugin.skills) == expected["skills"], (
        f"source skills={len(plugin.skills)} but fixture says "
        f"{expected['skills']}; update expected_counts.json"
    )
    assert len(plugin.hooks) == expected["hooks"], (
        f"source hooks={len(plugin.hooks)} but fixture says "
        f"{expected['hooks']}; update expected_counts.json"
    )

    templates_dir = PLUGIN_DIR / "templates"
    template_subdirs = sorted(
        p.name for p in templates_dir.iterdir() if p.is_dir()
    )
    assert len(template_subdirs) == expected["templates_root_dirs"], (
        f"templates root dirs={template_subdirs} but fixture expects "
        f"{expected['templates_root_dirs']}"
    )

    retention_ids = sorted(
        d.id for d in plugin.commands if (d.meta or {}).get("retention")
    )
    assert retention_ids == sorted(expected["retention_commands"]), (
        f"commands with retention={retention_ids} but fixture says "
        f"{expected['retention_commands']}"
    )


# ---------------------------------------------------------------------------
# A. file-count invariants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("adapter", WRITING_ADAPTERS)
def test_invariant_a_file_counts(
    adapter: str,
    plugin: Plugin,
    rendered: dict[str, dict[str, Any]],
) -> None:
    """Every source command/agent/skill maps to the right number of rendered
    files for ``adapter``. Hooks intentionally have no per-file output in
    either adapter (claude_code surfaces them in ``plugin.json``; codex_cli
    inlines them into per-command ``## Guardrails`` blocks).
    """
    files = rendered[adapter]["files"]
    root = rendered[adapter]["root"]

    n_src_commands = len(plugin.commands)
    n_src_agents = len(plugin.agents)
    n_src_skills = len(plugin.skills)

    if adapter == "claude_code":
        n_cmd = len(_files_under(files, "commands"))
        n_agent = len(_files_under(files, "agents"))
        n_skill = len(_files_under(files, "skills"))
        assert n_cmd == n_src_commands, (
            f"claude_code: commands rendered={n_cmd} != source={n_src_commands}"
        )
        assert n_agent == n_src_agents, (
            f"claude_code: agents rendered={n_agent} != source={n_src_agents}"
        )
        assert n_skill == n_src_skills, (
            f"claude_code: skills rendered={n_skill} != source={n_src_skills}"
        )
        # plugin.json must exist at the root.
        assert (root / "plugin.json").is_file(), (
            "claude_code: plugin.json missing from rendered output"
        )

    elif adapter == "codex_cli":
        n_prompt = len(_files_under(files, "prompts"))
        n_skill = len(_files_under(files, "skills"))
        assert n_prompt == n_src_commands, (
            f"codex_cli: prompts rendered={n_prompt} != source commands="
            f"{n_src_commands}"
        )
        assert n_skill == n_src_skills, (
            f"codex_cli: skills rendered={n_skill} != source={n_src_skills}"
        )
        # No separate agent files — they are inlined.
        assert not _files_under(files, "agents"), (
            "codex_cli: did not expect a separate agents/ dir; subagents "
            "should be inlined into the prompts"
        )


def test_invariant_a_opencode_lint_dry_run(
    plugin: Plugin,
    expected: dict[str, Any],
) -> None:
    """opencode is lint-only: assert dry-run exits 0 and the document count in
    its output matches the source artefact total (commands + agents + skills +
    hooks).
    """
    expected_total = (
        expected["commands"]
        + expected["agents"]
        + expected["skills"]
        + expected["hooks"]
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "packages.adapters.opencode.generate",
            "--plugin",
            str(PLUGIN_DIR),
            "--out",
            "/tmp/scholar-ip-opencode-conformance",
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"opencode dry-run exit={result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    m = re.search(r"\[opencode\] lint: (\d+) document\(s\)", result.stdout)
    assert m is not None, (
        f"opencode lint banner not found in stdout:\n{result.stdout}"
    )
    actual = int(m.group(1))
    assert actual == expected_total, (
        f"opencode lint document count={actual} != expected total="
        f"{expected_total} (commands+agents+skills+hooks)"
    )


# ---------------------------------------------------------------------------
# B. frontmatter survival
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("adapter", WRITING_ADAPTERS)
def test_invariant_b_frontmatter_survival(
    adapter: str,
    plugin: Plugin,
    rendered: dict[str, dict[str, Any]],
) -> None:
    """For every rendered command/skill file, where the adapter emits a given
    frontmatter field (``id``/``kind``/``slash``/``phase``), that field's value
    must equal the source.

    Adapters that do not emit a particular field are not faulted for it — both
    adapters intentionally rewrite frontmatter to a host-specific minimal
    shape. This invariant catches the regression case where an emitted field's
    *value* drifts from source, e.g. a renamed skill id silently mis-aliased.

    For codex_cli (no YAML frontmatter at all on commands) we instead assert
    the ``# {slash}`` heading in the body equals the source ``slash``.
    """
    root = Path(rendered[adapter]["root"])

    # By-id maps from the source for fast lookup.
    src_cmd_by_id = {d.id: d.meta or {} for d in plugin.commands}
    src_skill_by_id = {d.id: d.meta or {} for d in plugin.skills}

    if adapter == "claude_code":
        # Commands: emitted frontmatter only carries `description`,
        # `argument-hint`, `allowed-tools`, `slash`. We assert the `slash`
        # field equals source; the body's first heading also reflects slash.
        for cmd in plugin.commands:
            target = root / "commands" / cmd.path.name
            assert target.is_file(), f"claude_code missing {target}"
            meta, _body = split_frontmatter(target.read_text(encoding="utf-8"))
            src_meta = src_cmd_by_id[cmd.id]
            if src_meta.get("slash") is not None and "slash" in meta:
                assert meta["slash"] == src_meta["slash"], (
                    f"claude_code commands/{cmd.path.name}: rendered slash "
                    f"{meta['slash']!r} != source {src_meta['slash']!r}"
                )

        # Skills: emitted frontmatter carries `name` (=== source id). Assert.
        for sk in plugin.skills:
            target = root / "skills" / sk.id / "SKILL.md"
            assert target.is_file(), f"claude_code missing {target}"
            meta, _body = split_frontmatter(target.read_text(encoding="utf-8"))
            src_meta = src_skill_by_id[sk.id]
            assert meta.get("name") == src_meta.get("id", sk.id), (
                f"claude_code skills/{sk.id}/SKILL.md: rendered name "
                f"{meta.get('name')!r} != source id {src_meta.get('id')!r}"
            )

    elif adapter == "codex_cli":
        # Commands have no YAML frontmatter; the slash header is the first
        # body line ("# /scholar:foo"). Verify it matches source slash.
        for cmd in plugin.commands:
            target = root / "prompts" / f"{cmd.id}.md"
            assert target.is_file(), f"codex_cli missing {target}"
            first = target.read_text(encoding="utf-8").splitlines()[0]
            src_meta = src_cmd_by_id[cmd.id]
            src_slash = src_meta.get("slash") or f"/{cmd.id}"
            assert first == f"# {src_slash}", (
                f"codex_cli prompts/{cmd.id}.md: first line {first!r} != "
                f"`# {src_slash}` (slash header drifted from source)"
            )

        # Skills have no YAML frontmatter; the file name itself is the id.
        for sk in plugin.skills:
            target = root / "skills" / f"{sk.id}.md"
            assert target.is_file(), (
                f"codex_cli missing skills/{sk.id}.md (skill id drifted "
                "or rename did not propagate)"
            )


# ---------------------------------------------------------------------------
# C. retention preamble invariant (symmetric)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("adapter", WRITING_ADAPTERS)
def test_invariant_c_retention_preamble_symmetric(
    adapter: str,
    plugin: Plugin,
    rendered: dict[str, dict[str, Any]],
    expected: dict[str, Any],
) -> None:
    """A rendered command contains the ``## Pre-run cleanup`` header IFF the
    source declares ``retention:``. Symmetric — neither false positives nor
    false negatives.
    """
    root = Path(rendered[adapter]["root"])
    expected_retention = set(expected["retention_commands"])

    for cmd in plugin.commands:
        if adapter == "claude_code":
            target = root / "commands" / cmd.path.name
        else:  # codex_cli
            target = root / "prompts" / f"{cmd.id}.md"
        assert target.is_file(), f"{adapter}: missing rendered file {target}"
        text = target.read_text(encoding="utf-8")
        has_preamble = "## Pre-run cleanup" in text
        declares_retention = bool((cmd.meta or {}).get("retention"))

        assert declares_retention == has_preamble, (
            f"{adapter} {target.name}: declares_retention="
            f"{declares_retention} but has_preamble={has_preamble} — "
            f"retention preamble invariant violated"
        )
        if declares_retention:
            assert cmd.id in expected_retention, (
                f"{cmd.id} declares retention but is not in fixture "
                f"retention_commands; update expected_counts.json"
            )


# ---------------------------------------------------------------------------
# D. no MCP references invariant (ratchet)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("adapter", WRITING_ADAPTERS)
def test_invariant_d_no_new_mcp_references(
    adapter: str,
    rendered: dict[str, dict[str, Any]],
    expected: dict[str, Any],
) -> None:
    """No rendered command/agent/skill file may mention the deprecated
    ``*-mcp`` server names UNLESS it is on the ``_mcp_legacy_baseline`` list
    in ``expected_counts.json``.

    This is a *ratchet*: the set of legacy files is allowed to shrink (and
    when it does, the test will fail and force the contributor to tighten
    the baseline) but must never grow.
    """
    root = Path(rendered[adapter]["root"])
    files = rendered[adapter]["files"]
    allowed = set(expected["_mcp_legacy_baseline"][adapter])

    offenders: set[str] = set()
    for p in files:
        if p.suffix != ".md":
            continue
        rel = str(p.relative_to(root))
        text = p.read_text(encoding="utf-8")
        if any(term in text for term in MCP_TERMS):
            offenders.add(rel)

    new = offenders - allowed
    stale = allowed - offenders
    assert not new, (
        f"{adapter}: new file(s) mention deprecated *-mcp server names — "
        f"please remove the MCP references or, if intentional, bump "
        f"_mcp_legacy_baseline.{adapter} in expected_counts.json: {sorted(new)}"
    )
    assert not stale, (
        f"{adapter}: file(s) in _mcp_legacy_baseline.{adapter} no longer "
        f"contain *-mcp references — please tighten the baseline (remove "
        f"these entries from expected_counts.json): {sorted(stale)}"
    )


# ---------------------------------------------------------------------------
# E. required-skill invariant
# ---------------------------------------------------------------------------


def test_invariant_e_referenced_skills_exist_in_source(
    plugin: Plugin,
) -> None:
    """Every ``../skills/<X>/SKILL.md`` referenced by a command must resolve
    to an existing source skill.
    """
    referenced = _source_skill_ids_referenced_by_commands(plugin)
    source_ids = {d.id for d in plugin.skills}
    missing = referenced - source_ids
    assert not missing, (
        f"command references missing source skill(s): {sorted(missing)}"
    )


@pytest.mark.parametrize("adapter", WRITING_ADAPTERS)
def test_invariant_e_referenced_skills_rendered(
    adapter: str,
    plugin: Plugin,
    rendered: dict[str, dict[str, Any]],
) -> None:
    """Every referenced skill must also be rendered into the adapter's tree
    (claude_code: ``skills/<id>/SKILL.md``; codex_cli: ``skills/<id>.md``).
    """
    referenced = _source_skill_ids_referenced_by_commands(plugin)
    root = Path(rendered[adapter]["root"])

    missing: list[str] = []
    for sid in sorted(referenced):
        if adapter == "claude_code":
            target = root / "skills" / sid / "SKILL.md"
        else:  # codex_cli
            target = root / "skills" / f"{sid}.md"
        if not target.is_file():
            missing.append(str(target.relative_to(root)))

    assert not missing, (
        f"{adapter}: command references skill(s) that were not rendered: "
        f"{missing}"
    )
