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
    F. subagent dispatch     — every command whose source frontmatter declares
       a non-empty ``subagents:`` list renders with a ``## Dispatch plan``
       section AND mentions each declared subagent's id at least once in the
       rendered body

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
        # Plugin manifest must exist at .claude-plugin/plugin.json (the path
        # Claude Code's plugin loader expects).
        assert (root / ".claude-plugin" / "plugin.json").is_file(), (
            "claude_code: .claude-plugin/plugin.json missing from rendered output"
        )

    elif adapter == "codex_cli":
        # Codex has no slash commands or workflow files; every source command
        # and source skill is flattened into a single skills/ directory, each
        # as its own ``skills/<prefixed-name>/SKILL.md`` bundle. Commands use
        # the ``scholar-`` prefix; source skills use ``scholar-skill-`` so
        # ids that exist in both (e.g. ``brainstorming``) don't collide.
        all_skill_files = _files_under(files, "skills")
        n_cmd_skill = sum(
            1 for p in all_skill_files
            if p.parent.name.startswith("scholar-") and not p.parent.name.startswith("scholar-skill-")
        )
        n_src_skill = sum(
            1 for p in all_skill_files if p.parent.name.startswith("scholar-skill-")
        )
        assert n_cmd_skill == n_src_commands, (
            f"codex_cli: command-as-skill rendered={n_cmd_skill} != source "
            f"commands={n_src_commands}"
        )
        assert n_src_skill == n_src_skills, (
            f"codex_cli: source-skill-as-skill rendered={n_src_skill} != "
            f"source skills={n_src_skills}"
        )
        # No separate agent files — they are inlined.
        assert not _files_under(files, "agents"), (
            "codex_cli: did not expect a separate agents/ dir; subagents "
            "should be inlined into the command bodies"
        )
        # Codex plugin manifest must be at .codex-plugin/plugin.json.
        assert (root / ".codex-plugin" / "plugin.json").is_file(), (
            "codex_cli: .codex-plugin/plugin.json missing from rendered output"
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
        # Commands are rendered as skills at skills/scholar-<id>/SKILL.md.
        # The frontmatter carries ``name`` (=== "scholar-<id>"); the body's
        # first heading is "# <source slash>" so users see e.g. "/scholar:foo"
        # at the top of the SKILL.
        for cmd in plugin.commands:
            target = root / "skills" / f"scholar-{cmd.id}" / "SKILL.md"
            assert target.is_file(), f"codex_cli missing {target}"
            meta, body = split_frontmatter(target.read_text(encoding="utf-8"))
            assert meta.get("name") == f"scholar-{cmd.id}", (
                f"codex_cli skills/scholar-{cmd.id}/SKILL.md: frontmatter "
                f"name {meta.get('name')!r} != expected scholar-{cmd.id!r}"
            )
            src_meta = src_cmd_by_id[cmd.id]
            src_slash = src_meta.get("slash") or f"/{cmd.id}"
            first = body.lstrip("\n").splitlines()[0]
            assert first == f"# {src_slash}", (
                f"codex_cli skills/scholar-{cmd.id}/SKILL.md: body first "
                f"line {first!r} != `# {src_slash}` (slash header drifted)"
            )

        # Source skills are rendered as skills/scholar-skill-<id>/SKILL.md.
        for sk in plugin.skills:
            target = root / "skills" / f"scholar-skill-{sk.id}" / "SKILL.md"
            assert target.is_file(), (
                f"codex_cli missing skills/scholar-skill-{sk.id}/SKILL.md "
                "(skill id drifted or rename did not propagate)"
            )
            meta, _ = split_frontmatter(target.read_text(encoding="utf-8"))
            assert meta.get("name") == f"scholar-skill-{sk.id}", (
                f"codex_cli skills/scholar-skill-{sk.id}/SKILL.md: "
                f"frontmatter name {meta.get('name')!r} != expected "
                f"scholar-skill-{sk.id!r}"
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
            target = root / "skills" / f"scholar-{cmd.id}" / "SKILL.md"
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
            target = root / "skills" / f"scholar-skill-{sid}" / "SKILL.md"
        if not target.is_file():
            missing.append(str(target.relative_to(root)))

    assert not missing, (
        f"{adapter}: command references skill(s) that were not rendered: "
        f"{missing}"
    )


# ---------------------------------------------------------------------------
# F. subagent-dispatch invariant (claude_code only)
# ---------------------------------------------------------------------------


def test_invariant_f_subagent_dispatch_present(
    plugin: Plugin,
    rendered: dict[str, dict[str, Any]],
) -> None:
    """For every command whose source frontmatter declares a non-empty
    ``subagents:`` list, the rendered ``commands/<id>.md`` body MUST contain
    a ``## Dispatch plan`` section AND mention each declared subagent id at
    least once in the body.

    This closes the "declare-but-never-dispatch" anti-pattern: source YAML
    can claim a command uses subagent X, but unless the rendered body tells
    the model to dispatch X the host never actually invokes it. We check
    only the ``claude_code`` adapter because the codex_cli adapter inlines
    subagent prose differently (no separate agents/ tree, agents are folded
    into per-command SKILL bodies); the codex inlining is covered by
    invariant A's file-count assertions.
    """
    adapter = "claude_code"
    root = Path(rendered[adapter]["root"])

    offenders: list[str] = []
    declared_total = 0
    for cmd in plugin.commands:
        subs = (cmd.meta or {}).get("subagents") or []
        if not isinstance(subs, list) or not subs:
            continue
        target = root / "commands" / cmd.path.name
        assert target.is_file(), f"claude_code: missing rendered file {target}"
        text = target.read_text(encoding="utf-8")
        if "## Dispatch plan" not in text:
            offenders.append(
                f"{cmd.path.name}: declares subagents={subs} but rendered "
                "body has no `## Dispatch plan` section"
            )
            continue
        for sub_id in subs:
            sid = str(sub_id)
            declared_total += 1
            if sid not in text:
                offenders.append(
                    f"{cmd.path.name}: declares subagent {sid!r} but the "
                    "rendered body never mentions it"
                )

    assert not offenders, (
        "subagent-dispatch invariant violated; "
        f"{len(offenders)} issue(s):\n  - " + "\n  - ".join(offenders)
    )
    assert declared_total > 0, (
        "no commands declare subagents — the fixture must be wrong or every "
        "command silently lost its `subagents:` block"
    )


# ---------------------------------------------------------------------------
# G. executable hooks invariant (Track C2: real hooks via hooks.json)
# ---------------------------------------------------------------------------


def test_invariant_g_executable_hooks_present(
    rendered: dict[str, dict[str, Any]],
) -> None:
    """The claude_code adapter must emit a real Claude Code hooks manifest:

    1. ``<root>/hooks/hooks.json`` exists and parses as JSON.
    2. The manifest covers at least the three wired events
       (``SessionStart``, ``PostToolUse``, ``UserPromptSubmit``).
    3. The three companion bash scripts
       (``citation-guard.sh``, ``scope-required.sh``, ``session-start.sh``)
       are present in ``<root>/hooks/`` and are executable (mode bits include
       ``0o111``).

    Prior to this invariant the adapter only listed hooks in ``plugin.json``
    as advisory text; nothing actually fired.
    """
    import os
    import stat

    root = Path(rendered["claude_code"]["root"])
    hooks_dir = root / "hooks"
    manifest_path = hooks_dir / "hooks.json"

    assert manifest_path.is_file(), (
        f"claude_code: expected hooks manifest at {manifest_path} but it is "
        "missing — adapter did not emit hooks/hooks.json"
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert isinstance(manifest, dict), (
        f"claude_code: hooks.json must be a JSON object keyed by event name, "
        f"got {type(manifest).__name__}"
    )

    required_events = {"SessionStart", "PostToolUse", "UserPromptSubmit"}
    missing_events = required_events - set(manifest.keys())
    assert not missing_events, (
        f"claude_code: hooks.json missing required event entries: "
        f"{sorted(missing_events)}; got keys={sorted(manifest.keys())}"
    )

    for event, entries in manifest.items():
        assert isinstance(entries, list) and entries, (
            f"claude_code: hooks.json[{event!r}] must be a non-empty list"
        )
        for entry in entries:
            inner = entry.get("hooks") if isinstance(entry, dict) else None
            assert isinstance(inner, list) and inner, (
                f"claude_code: hooks.json[{event!r}] entry missing `hooks` "
                f"list: {entry!r}"
            )
            for h in inner:
                assert h.get("type") == "command" and h.get("command"), (
                    f"claude_code: hooks.json[{event!r}] entry has malformed "
                    f"hook object: {h!r}"
                )

    expected_scripts = (
        "citation-guard.sh",
        "scope-required.sh",
        "session-start.sh",
    )
    for name in expected_scripts:
        script_path = hooks_dir / name
        assert script_path.is_file(), (
            f"claude_code: expected executable hook script {script_path} but "
            "it is missing"
        )
        mode = os.stat(script_path).st_mode
        executable_bits = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        assert (mode & executable_bits) == executable_bits, (
            f"claude_code: hook script {name} mode is {oct(mode)} but must "
            f"include the executable bits {oct(executable_bits)}"
        )


# ---------------------------------------------------------------------------
# H. agent dispatch-hint completeness (model / effort)
# ---------------------------------------------------------------------------


_VALID_MODELS = {"haiku", "sonnet", "opus", "inherit"}
_VALID_EFFORTS = {"low", "medium", "high"}


def test_invariant_h_every_agent_declares_model(plugin: Plugin) -> None:
    """Every source agent must declare a `model:` (one of haiku / sonnet /
    opus / inherit). The field maps directly to Claude Code's per-subagent
    model pin and to the equivalent dispatch hint on other hosts; leaving it
    unset means every agent inherits the session model and the per-tier cost
    savings vanish.
    """
    missing: list[str] = []
    bad: list[tuple[str, str]] = []
    for ag in plugin.agents:
        model = (ag.meta or {}).get("model")
        if not model:
            missing.append(ag.id)
            continue
        if str(model) not in _VALID_MODELS:
            bad.append((ag.id, str(model)))
    assert not missing, (
        f"agent(s) missing required `model:` field: {sorted(missing)}"
    )
    assert not bad, (
        f"agent(s) with invalid `model:` value (must be one of "
        f"{sorted(_VALID_MODELS)}): {bad}"
    )


def test_invariant_h_effort_set_when_model_pinned(plugin: Plugin) -> None:
    """If an agent pins a concrete model (haiku/sonnet/opus, i.e. not
    `inherit`), it must also declare an `effort:` hint. `inherit` agents are
    allowed to omit `effort:` because the session-level effort applies.
    """
    missing: list[str] = []
    bad: list[tuple[str, str]] = []
    for ag in plugin.agents:
        meta = ag.meta or {}
        model = meta.get("model")
        effort = meta.get("effort")
        if model and model != "inherit" and not effort:
            missing.append(ag.id)
        if effort and str(effort) not in _VALID_EFFORTS:
            bad.append((ag.id, str(effort)))
    assert not missing, (
        f"agent(s) pinned to a concrete model but missing `effort:`: "
        f"{sorted(missing)}"
    )
    assert not bad, (
        f"agent(s) with invalid `effort:` value (must be one of "
        f"{sorted(_VALID_EFFORTS)}): {bad}"
    )
