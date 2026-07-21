"""Behavior-preservation tests for private role-mode specifications."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml

from evidraft.render import Host, render_plugin


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "scholar-ip"
ROLES_ROOT = PLUGIN_ROOT / "roles"

EXPECTED = {
    "brainstormer": ("researcher", "standard", 7, 7, 5, 5),
    "deep-research-orchestrator": ("researcher", "deep", 6, 5, 5, 7),
    "literature-reviewer": ("researcher", "standard", 4, 4, 4, 7),
    "paper-critic": ("researcher", "standard", 6, 6, 5, 5),
    "screener": ("researcher", "fast", 5, 6, 5, 5),
    "consistency-checker": ("evidence-reviewer", "fast", 6, 6, 6, 5),
    "evidence-auditor": ("evidence-reviewer", "standard", 6, 5, 5, 7),
    "codebase-analyst": ("code-reviewer", "standard", 4, 4, 4, 6),
    "methodology-reviewer": ("code-reviewer", "standard", 5, 5, 5, 3),
    "experiment-analyst": ("experiment-reviewer", "standard", 5, 4, 3, 6),
    "latex-editor": ("writing-reviewer", "fast", 5, 5, 5, 8),
    "prose-polisher": ("writing-reviewer", "standard", 6, 8, 5, 5),
    "claim-drafter": ("patent-reviewer", "deep", 6, 6, 6, 5),
    "novelty-critic": ("patent-reviewer", "deep", 4, 4, 3, 5),
    "patent-engineer": ("patent-reviewer", "deep", 5, 5, 6, 5),
}
NATIVE_EXPECTED = {
    "paper-explainer": ("researcher", "deep", 6, 5, 7, 5),
}
ALL_EXPECTED = EXPECTED | NATIVE_EXPECTED
REMOVED_EXPLANATION_MODES = {
    "paper-indexer",
    "paper-analysis-worker",
    "paper-reasoning-worker",
    "explanation-evidence-auditor",
}
MODE_SPEC_SHA256 = {
    "brainstormer": "b2f65c91e2b869fcd76514233f8cece9aa6207c1a1f52fe9ac448e796cc4e161",
    "claim-drafter": "0c60990664279d2b0d37d4bbb8a5ef6c84bbc32fec7fc745a05a321a7f62e5e9",
    "codebase-analyst": "a29bc87a1625eb25e8cf58f4fd9166e201e7ebce9ec64a60cb546cee0d5caf39",
    "consistency-checker": "a47e6fa0a53873b22caec6e83d3efa3cb94bba263bb3a5d6f782d0d73f2e5c40",
    "deep-research-orchestrator": "7b073dd82ba85c6f81b4df005db6fc5b8399e26aaae6bdfa766a9b0ab32d4edd",
    "evidence-auditor": "77292727255e1790ffb8358d5373d17c1bee80435586717e539f22f951d72984",
    "experiment-analyst": "0ebbe79da02bc74da5e33bb7e2c975a93a33d2d7ed82a8011ed103784e38d2e9",
    "latex-editor": "18d06d47c5840afbf89e641a917506f6e2b418835418776f43022c8b9c76fb18",
    "literature-reviewer": "b76c215a1a1daf77eb88b4df4a526247c6a7a1e0e24ab06db5b5d591cf661193",
    "methodology-reviewer": "51dca210335c2096a90462f9bc2ef44c626a91e190f0d6a0f27f18454e3cfcf3",
    "novelty-critic": "03266071d7d7312a00078c9f2009821e390406fa3146125c595e933a0294ec21",
    "paper-critic": "65d888fa7c2a9c286889d0b15d46638320dd0612ccbdf9c3b832791bb75e1150",
    "patent-engineer": "dc5c978297ef440f17df5729bf068bb497f0e9e94561ecb70e8dcee8324db23c",
    "prose-polisher": "0f6d38bbdfc8b6dbc4462d7bc71bd94d37020d281204b47bd493a74a7295acd7",
    "screener": "ed3bbc07b48d2d85e14572c4839e4f12d86ffa747b78833ba2e4259fc3790bea",
}


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    _, header, body = text.split("---", 2)
    return yaml.safe_load(header), body


def _mode_index() -> dict[str, tuple[str, str, str]]:
    roles = _load(ROLES_ROOT / "roles.yaml")
    indexed: dict[str, tuple[str, str, str]] = {}
    tier_specs: dict[str, tuple[str, str]] = {}
    for tier, tier_doc in roles["tiers"].items():
        for mode, spec in tier_doc["mode_specs"].items():
            assert mode not in tier_specs
            tier_specs[mode] = (tier, spec)
    for role_id, role in roles["roles"].items():
        for mode in role["modes"]:
            assert mode not in indexed
            tier, spec = tier_specs[mode]
            indexed[mode] = (role_id, tier, spec)
    assert set(tier_specs) == set(indexed)
    return indexed


def test_roles_map_exactly_sixteen_unique_modes_to_private_specs() -> None:
    index = _mode_index()

    assert set(index) == set(ALL_EXPECTED)
    assert {role for role, _, _ in index.values()} == {
        "researcher",
        "evidence-reviewer",
        "code-reviewer",
        "experiment-reviewer",
        "writing-reviewer",
        "patent-reviewer",
    }
    for mode, (expected_role, expected_tier, *_counts) in ALL_EXPECTED.items():
        role, tier, spec = index[mode]
        assert (role, tier) == (expected_role, expected_tier)
        assert spec == f"modes/{mode}.md"
        assert (ROLES_ROOT / spec).is_file()


def test_mode_specs_preserve_v1_tools_and_semantic_sections() -> None:
    for mode, (*_mapping, responsibilities, constraints, checklist, tools) in ALL_EXPECTED.items():
        metadata, body = _frontmatter(ROLES_ROOT / "modes" / f"{mode}.md")
        assert metadata["id"] == mode
        assert metadata["allowed_tools"]
        assert len(metadata["allowed_tools"]) == tools
        assert len(metadata["responsibilities"]) == responsibilities
        assert len(metadata["constraints"]) == constraints
        assert len(metadata["review_checklist"]) == checklist
        assert metadata["policies"]
        assert set(metadata["policies"]) <= {
            "workspace-safety",
            "scope",
            "evidence-integrity",
        }
        assert body.strip()
        if mode == "deep-research-orchestrator":
            assert "Run only the stages enabled by the selected mode" in body
            assert "earliest safe recovery stage" in body
        else:
            assert "Inputs you read" in body
            assert "Outputs you " in body
            assert "Failure modes you avoid" in body


def test_removed_explanation_workers_are_absent_and_explainer_is_sole_writer() -> None:
    for mode in REMOVED_EXPLANATION_MODES:
        assert not (ROLES_ROOT / "modes" / f"{mode}.md").exists()
    metadata, body = _frontmatter(ROLES_ROOT / "modes/paper-explainer.md")
    assert metadata["allowed_tools"] == ["Read", "Glob", "Grep", "Write", "Edit"]
    assert "perform one final write" in body.lower()
    assert "complete_with_gaps" in body
    assert "conditional comparison branch" in body.lower()


def test_paper_explainer_has_resolvable_capability_reference_and_sections() -> None:
    headings = {
        "## Inputs you read",
        "## Outputs you return",
        "## Execution protocol",
        "## Failure modes you avoid",
    }
    metadata, body = _frontmatter(ROLES_ROOT / "modes/paper-explainer.md")
    assert headings <= set(body.splitlines())
    assert [reference["doc"] for reference in metadata["references"]] == [
        "../../capabilities/research/paper-explanation/spec.md"
    ]
    assert (ROLES_ROOT / "modes" / metadata["references"][0]["doc"]).resolve().is_file()


def test_normalized_mode_specs_match_the_frozen_behavior_snapshot() -> None:
    assert set(MODE_SPEC_SHA256) == set(EXPECTED)
    for mode, expected in MODE_SPEC_SHA256.items():
        content = (ROLES_ROOT / "modes" / f"{mode}.md").read_bytes()
        assert hashlib.sha256(content).hexdigest() == expected


def test_mode_specs_have_only_resolvable_v2_resource_references() -> None:
    for spec in sorted((ROLES_ROOT / "modes").glob("*.md")):
        metadata, body = _frontmatter(spec)
        text = spec.read_text(encoding="utf-8")
        assert "skills/" not in text
        assert "hooks/" not in text
        assert "agents/" not in text
        assert "/scholar:" not in text
        for reference in metadata.get("references", []):
            target = (spec.parent / reference["doc"]).resolve()
            assert target.is_file(), f"unresolved reference in {spec.name}: {reference}"
        assert body.strip()


def test_every_workflow_role_assignment_resolves_to_its_role_mode_spec() -> None:
    index = _mode_index()
    assignments = 0
    for workflow_path in (PLUGIN_ROOT / "workflows").glob("*/workflow.yaml"):
        workflow = _load(workflow_path)
        for action in workflow["actions"].values():
            for assignment in action["roles"]:
                assignments += 1
                role, _tier, spec = index[assignment["mode"]]
                assert assignment["id"] == role
                assert (ROLES_ROOT / spec).is_file()
    assert assignments > 0


def test_xreview_prompt_attaches_the_complete_selected_mode_spec() -> None:
    bridge = (
        PLUGIN_ROOT / "capabilities" / "code" / "external-agent-bridge" / "spec.md"
    ).read_text()
    stage = (PLUGIN_ROOT / "workflows" / "xreview" / "stages" / "run.md").read_text()
    assert "entire" in bridge
    assert "roles/modes/<persona>.md" in bridge
    assert "frontmatter and" in bridge
    assert "full private mode spec" in stage


@pytest.mark.parametrize("host", list(Host))
def test_renderer_copies_all_mode_specs_privately(tmp_path: Path, host: Host) -> None:
    out = tmp_path / host.value
    render_plugin(PLUGIN_ROOT, out, host)
    private = (
        out / "skills" / ".evidraft-private"
        if host is Host.CODEX
        else out / "private"
    )

    modes = sorted((private / "roles" / "modes").glob("*.md"))
    assert {path.stem for path in modes} == set(ALL_EXPECTED)
    assert not list((private / "roles").rglob("SKILL.md"))

    agents = sorted((out / "agents").glob("*.md")) if (out / "agents").exists() else []
    if host is Host.CODEX:
        assert agents == []
        routers = sorted((out / "skills").glob("scholar-*/SKILL.md"))
        assert len(routers) == 7
        assert all(
            "../.evidraft-private/roles/modes/<mode>.md" in path.read_text()
            for path in routers
        )
    else:
        assert len(agents) == 6
        semantic_agents = {
            "code-reviewer",
            "evidence-reviewer",
            "experiment-reviewer",
            "patent-reviewer",
            "researcher",
            "writing-reviewer",
        }
        assert all(
            "roles/modes/<mode>.md" in (out / "agents" / f"{role}.md").read_text()
            for role in semantic_agents
        )
        assert all(not (out / "agents" / f"{mode}.md").exists() for mode in REMOVED_EXPLANATION_MODES)
