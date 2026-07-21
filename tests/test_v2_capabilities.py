from __future__ import annotations

import hashlib
import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

from evidraft.render import Host, render_plugin


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "scholar-ip"
CAPABILITIES = PLUGIN_ROOT / "capabilities"

EXPECTED_GROUPS = {
    "research": {
        "brainstorming",
        "deep-literature-review",
        "literature-review",
        "paper-explanation",
        "patent-search",
        "scholar-search",
        "using-deep-research",
        "using-scholar-ip-copilot",
    },
    "evidence": {"bib-audit", "bib-manager", "evidence-check"},
    "code": {"code-intel", "codebase-audit", "external-agent-bridge"},
    "experiments": {"experiment-analysis"},
    "latex": {
        "latex-build",
        "latex-style-audit",
        "latex-writing",
        "venue-formatting",
        "xref-audit",
    },
    "patent": {
        "claim-chart-builder",
        "claim-parser",
        "novelty-heuristics",
        "patent-claims",
        "patent-disclosure",
    },
    "editing": {"humanize"},
}

CAPABILITY_PATH = re.compile(
    r"(?:\.\./\.\./\.\./capabilities|\.\./\.\./\.evidraft-private/capabilities)"
    r"/[A-Za-z0-9_./<>-]+"
)
ROLE_PATH = re.compile(
    r"(?:\.\./\.\./\.\./roles|\.\./\.\./\.evidraft-private/roles)/roles\.yaml"
)
DELETED_AUTHORING_PATH = re.compile(
    r"(?:^|[`'\"(\s])(?:(?:\.\./)+|plugins/scholar-ip/)?"
    r"(?:skills|agents|commands|hooks)/",
    re.MULTILINE,
)


def _capability_index() -> dict[str, dict[str, str]]:
    raw = yaml.safe_load((CAPABILITIES / "index.yaml").read_text(encoding="utf-8"))
    assert raw["format_version"] == 2
    return raw["capabilities"]


def _local_capability_paths(document: Path) -> set[Path]:
    paths: set[Path] = set()
    for match in CAPABILITY_PATH.findall(document.read_text(encoding="utf-8")):
        clean = match.rstrip(".,;:)").replace("<venue>", "arxiv")
        paths.add((document.parent / clean).resolve())
    return paths


def _bundle_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def test_capability_index_maps_all_private_capabilities_into_seven_groups() -> None:
    entries = _capability_index()
    actual: dict[str, set[str]] = {group: set() for group in EXPECTED_GROUPS}

    assert set(entries) == set().union(*EXPECTED_GROUPS.values())
    for capability_id, entry in entries.items():
        assert set(entry) == {"group", "spec", "bundle_sha256"}
        assert entry["group"] in actual
        actual[entry["group"]].add(capability_id)
        assert entry["spec"] == f"{entry['group']}/{capability_id}/spec.md"

    assert actual == EXPECTED_GROUPS
    assert len(entries) == 26


def test_private_capability_bundles_match_the_normalized_v2_content_hashes() -> None:
    entries = _capability_index()

    for capability_id, entry in entries.items():
        private_root = CAPABILITIES / entry["group"] / capability_id
        assert (private_root / "spec.md").is_file()
        assert _bundle_sha256(private_root) == entry["bundle_sha256"]


def test_paper_explanation_preserves_the_approved_research_and_collision_contract() -> None:
    spec = CAPABILITIES / "research" / "paper-explanation" / "spec.md"
    normalized = " ".join(spec.read_text(encoding="utf-8").split())

    assert (
        "For external work, verify a canonical page before inclusion and record title, year, "
        "link, relationship, concrete methodological difference, search date, and search scope."
    ) in normalized
    assert (
        "Never overwrite a non-empty note silently. Offer reuse, a unique dated sibling, or "
        "explicitly confirmed replacement."
    ) in normalized


def test_paper_explanation_spec_declares_the_bounded_runtime_contract() -> None:
    spec = CAPABILITIES / "research" / "paper-explanation" / "spec.md"
    normalized = " ".join(spec.read_text(encoding="utf-8").split())

    for token in (
        "paper-explainer",
        "paper-indexer",
        "paper-analysis-worker",
        "paper-reasoning-worker",
        "explanation-evidence-auditor",
        "task-graph.yaml",
        "min(host_capacity, 15, ready_task_count)",
        "max_attempts: 2",
        "similar-methods",
        "current-methods",
        "fresh worker",
        "attempt: 2",
        "complete",
        "partial",
        "both attempt reasons",
        "auditor findings cannot suppress synthesis",
    ):
        assert token in normalized

    assert "Ordinary beginner and graduate explanations do not require external research." not in normalized


def test_capability_tree_exposes_no_host_discoverable_skill_files() -> None:
    assert not list(CAPABILITIES.rglob("SKILL.md"))
    assert {path.name for path in CAPABILITIES.iterdir() if path.is_dir()} == set(EXPECTED_GROUPS)


def test_source_stage_capability_references_are_private_and_resolve() -> None:
    stages = list((PLUGIN_ROOT / "workflows").glob("*/stages/*.md"))
    combined = "\n".join(path.read_text(encoding="utf-8") for path in stages)

    assert "skills/" not in combined
    referenced = set().union(*(_local_capability_paths(stage) for stage in stages))
    assert referenced
    assert all(path.exists() for path in referenced)


def test_xreview_uses_v2_role_modes_without_deleted_authoring_paths() -> None:
    stage = PLUGIN_ROOT / "workflows" / "xreview" / "stages" / "run.md"
    bridge = CAPABILITIES / "code" / "external-agent-bridge" / "spec.md"
    combined = stage.read_text(encoding="utf-8") + bridge.read_text(encoding="utf-8")

    assert ROLE_PATH.search(stage.read_text(encoding="utf-8"))
    assert (stage.parent / ROLE_PATH.search(stage.read_text()).group()).resolve().is_file()
    for deleted_root in ("agents/", "commands/", "hooks/", "plugins/scholar-ip/agents"):
        assert deleted_root not in combined


def test_claude_bridge_passes_prompt_through_stdin_not_argv(tmp_path: Path) -> None:
    bridge = (
        CAPABILITIES / "code" / "external-agent-bridge" / "spec.md"
    ).read_text(encoding="utf-8")
    claude_section = bridge.split("### Claude bare", 1)[1].split("### OpenCode", 1)[0]
    command = next(
        line for line in claude_section.splitlines() if line.startswith("claude ")
    )
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_claude = fake_bin / "claude"
    fake_claude.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' \"$@\" > \"$ARGV_CAPTURE\"\n"
        "cat > \"$STDIN_CAPTURE\"\n"
        "printf '{}\\n'\n",
        encoding="utf-8",
    )
    fake_claude.chmod(0o755)
    prompt = tmp_path / "review.prompt"
    sentinel = "PROMPT-SENTINEL-6f859743"
    prompt.write_text(sentinel, encoding="utf-8")
    argv_capture = tmp_path / "argv.txt"
    stdin_capture = tmp_path / "stdin.txt"
    output = tmp_path / "out.json"
    env = {
        **os.environ,
        "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        "PROMPT_FILE": str(prompt),
        "OUT_FILE": str(output),
        "ARGV_CAPTURE": str(argv_capture),
        "STDIN_CAPTURE": str(stdin_capture),
    }

    result = subprocess.run(
        ["/bin/sh", "-c", command],
        check=False,
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert stdin_capture.read_text(encoding="utf-8") == sentinel
    assert sentinel not in argv_capture.read_text(encoding="utf-8")
    assert output.read_text(encoding="utf-8") == "{}\n"


def test_external_bridge_sources_have_no_prompt_substitution_or_opencode_launch() -> None:
    forbidden = ("$(cat $PROMPT_FILE)", "opencode run", "Bash:opencode*")
    violations: list[str] = []
    for root in (PLUGIN_ROOT, REPO_ROOT / "plugins" / "scholar"):
        for document in root.rglob("*"):
            if not document.is_file() or document.suffix not in {".md", ".yaml"}:
                continue
            text = document.read_text(encoding="utf-8")
            for token in forbidden:
                if token in text:
                    violations.append(
                        f"{document.relative_to(REPO_ROOT).as_posix()}: {token}"
                    )

    assert violations == []


def test_private_prose_has_no_references_to_deleted_authoring_roots() -> None:
    documents = [
        path
        for root in (CAPABILITIES, PLUGIN_ROOT / "workflows")
        for path in root.rglob("*")
        if path.is_file() and path.suffix in {".md", ".yaml"}
    ]
    violations: list[str] = []
    for document in documents:
        text = document.read_text(encoding="utf-8")
        if (
            DELETED_AUTHORING_PATH.search(text)
            or "SKILL.md" in text
            or "/scholar:" in text
        ):
            violations.append(document.relative_to(PLUGIN_ROOT).as_posix())

    assert violations == []


@pytest.mark.parametrize("host", list(Host))
def test_rendered_stage_capability_references_resolve(
    tmp_path: Path, host: Host
) -> None:
    out = tmp_path / host.value
    render_plugin(PLUGIN_ROOT, out, host)
    if host is Host.CODEX:
        stages = list((out / "skills").glob("scholar-*/stages/*.md"))
    else:
        stages = list((out / "private" / "workflows").glob("*/stages/*.md"))

    referenced = set().union(*(_local_capability_paths(stage) for stage in stages))
    assert referenced
    assert all(path.exists() for path in referenced)
    capability_root = out / (
        "skills/.evidraft-private/capabilities"
        if host is Host.CODEX
        else "private/capabilities"
    )
    assert not list(capability_root.rglob("SKILL.md"))
    rendered_xreview = next(stage for stage in stages if "xreview" in stage.as_posix())
    role_path = ROLE_PATH.search(rendered_xreview.read_text(encoding="utf-8"))
    assert role_path
    assert (rendered_xreview.parent / role_path.group()).resolve().is_file()
