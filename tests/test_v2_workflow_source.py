"""Contract tests for the compact EviDraft v2 workflow source."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from pathlib import PurePosixPath
import re

import jsonschema
import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "scholar-ip"
WORKFLOW_ROOT = PLUGIN_ROOT / "workflows"
SCHEMA_PATH = REPO_ROOT / "packages" / "core" / "schemas" / "workflow.schema.json"

ROUTES = {
    "using": {"run": "using"},
    "scope": {"run": "brainstorming"},
    "research": {
        "guide": "using-deep-research",
        "reading-list": "reading-list",
        "deep": "deepresearch",
    },
    "paper": {
        "init": "paper-init",
        "lit": "paper-lit",
        "idea": "paper-idea",
        "code-audit": "paper-code-audit",
        "experiment": "paper-experiment",
        "review": "paper-review",
        "draft": "paper-draft",
        "check": "paper-check",
        "venue": "paper-venue",
    },
    "patent": {
        "init": "patent-init",
        "scout": "patent-scout",
        "prior-art": "patent-prior-art",
        "disclosure": "patent-disclosure",
        "claims": "patent-claims",
        "review": "patent-review",
    },
    "polish": {"run": "polish"},
    "xreview": {"run": "xreview"},
}
NATIVE_ACTIONS = {"research": {"explain": "paper-explain"}}


def _all_actions(workflow_id: str) -> dict[str, str]:
    return ROUTES[workflow_id] | NATIVE_ACTIONS.get(workflow_id, {})

ROLE_IDS = {
    "researcher",
    "evidence-reviewer",
    "code-reviewer",
    "experiment-reviewer",
    "writing-reviewer",
    "patent-reviewer",
}
POLICY_IDS = {"workspace-safety", "scope", "evidence-integrity"}
ACTION_KEYS = {
    "legacy_id",
    "procedure",
    "inputs",
    "defaults",
    "outputs",
    "policies",
    "roles",
    "retention",
}
MODE_ASSIGNMENTS = {
    "brainstormer": ("researcher", "standard"),
    "literature-reviewer": ("researcher", "standard"),
    "screener": ("researcher", "fast"),
    "paper-critic": ("researcher", "standard"),
    "paper-explainer": ("researcher", "deep"),
    "deep-research-orchestrator": ("researcher", "deep"),
    "evidence-auditor": ("evidence-reviewer", "standard"),
    "consistency-checker": ("evidence-reviewer", "fast"),
    "codebase-analyst": ("code-reviewer", "standard"),
    "methodology-reviewer": ("code-reviewer", "standard"),
    "experiment-analyst": ("experiment-reviewer", "standard"),
    "latex-editor": ("writing-reviewer", "fast"),
    "prose-polisher": ("writing-reviewer", "standard"),
    "patent-engineer": ("patent-reviewer", "deep"),
    "claim-drafter": ("patent-reviewer", "deep"),
    "novelty-critic": ("patent-reviewer", "deep"),
}
CAPABILITY_REFERENCE = re.compile(
    r"\.\./\.\./\.\./capabilities/[A-Za-z0-9_./<>-]+"
)
STAGE_BODY_SHA256 = {
    "paper.init": "2b400b9abedda208b23647e321b5136282d4433df71e4a81c4f65be8c7ab1243",
    "paper.lit": "7fef84ba2f0968d33ace6067d5f69e058e6ebe045015b192a1224d1a8c2d4fa5",
    "paper.idea": "0f608ba61cdb53233b61707705c410db1a53cf605b8d3229d0e1942c2b54a9a9",
    "paper.code-audit": "68a250e3ee504a9c4db6470606c9585a9c112468662199f04a394c993f9f25c6",
    "paper.experiment": "61885c2ada2712faf28a673875387eb11f1a03ddea04fffdf83e4e05904ee77e",
    "paper.review": "e5819c21e3041b11085644470f67f9bf3b51823c001c68d503595522b72ac39d",
    "paper.draft": "83e0880b836ddab2c60baa9d2d5f69c570b8f127a19b883c90234b11e6e7fac3",
    "paper.check": "acc77036e2bb9cef2992b49486214188df7c08e96e3c22b666c7e4bac955d26d",
    "paper.venue": "615e0ee2a577ce0deaa078bbdd5a26794270058f80e837df4c603e82b0a00ed2",
    "patent.init": "d6cb285111d0ac80fbfd9ffa236dee06464bff8352a7dc5ca918885ab78fb286",
    "patent.scout": "47be3b22325dfee1922facaf792f491efd82e408c5943138f01562ec7896f9e1",
    "patent.prior-art": "af9d70096ffb3bbfd1005a8f0745340ba8b326e28e961289eeb3a01e5fdb4364",
    "patent.disclosure": "261d5ba0207a8f2834a022b12fce352d5ef66cb515c33b46faf97acf21e4a283",
    "patent.claims": "527710bb5f0c281df1ac58e2a53cf355d0aa7d1d3bf174f1ae28dfde57aa2864",
    "patent.review": "bfcfde2c99ee8b14defe2f592ffe41fb017dc493822a5b79fc8ff08dea7d8b08",
    "polish.run": "90d1dd5d6ad05b1d06686c27e0520135125021030397aa40371f20e4e7b34d7f",
    "research.guide": "ecd534e8ba1c3c33359455c11f2e4c6e1cf1f1e0a479fb53848d2b8fdd08b3ac",
    "research.reading-list": "254d5d5b24efa5a721c186d488aeed28330c702e43e28beec63ff1a5f8399dd9",
    "research.deep": "bc8c7c9e44b763d987214cce3c7448eae05a1531f4a7437604d65567346dce94",
    "scope.run": "fe1ed4b47634223e8c9c6a34c85b7104e3c36afda6f91dfc640c81b82b0b8ced",
    "using.run": "cc703f2bfccccc315caa6ee2093711375507648493b6cb7911f65fceb255c512",
    "xreview.run": "2d95ea20c3a7d3a346aeabadd4f2b425890f4fd6c6271599b95b180c7fca144a",
}
LEGACY_SENSITIVE_PATTERNS = [
    ".env",
    "**/.env",
    "**/.env.*",
    "secrets/**",
    "credentials.json",
    "**/*.pem",
    "**/*.key",
    "**/id_rsa*",
]


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _matches_sensitive_path(path: str, patterns: list[str]) -> bool:
    """Interpret the closed legacy vocabulary without ambiguous ``**`` globs."""
    candidate = PurePosixPath(path)
    parts = candidate.parts
    name = candidate.name
    matchers = {
        ".env": lambda: path == ".env",
        "**/.env": lambda: name == ".env",
        "**/.env.*": lambda: name.startswith(".env."),
        "secrets/**": lambda: bool(parts) and parts[0] == "secrets",
        "credentials.json": lambda: path == "credentials.json",
        "**/*.pem": lambda: name.endswith(".pem"),
        "**/*.key": lambda: name.endswith(".key"),
        "**/id_rsa*": lambda: name.startswith("id_rsa"),
    }
    unknown = set(patterns) - set(matchers)
    assert not unknown, f"test matcher needs explicit semantics for {sorted(unknown)}"
    return any(matchers[pattern]() for pattern in patterns)


def _workspace_write_allowed(policy: dict, operation: str, path: str) -> bool:
    candidate = PurePosixPath(path)
    always = policy["always"]
    confinement = always["root_confinement"]
    if confinement["reject_absolute"] and candidate.is_absolute():
        return False
    if confinement["reject_parent_traversal"] and ".." in candidate.parts:
        return False
    if _matches_sensitive_path(path, always["sensitive_path_deny"]):
        return False

    zones = policy["operation_write_zones"].get(operation)
    if zones is None:
        return True
    for pattern in zones:
        if pattern.endswith("/**"):
            root = pattern.removesuffix("/**")
            if path == root or path.startswith(f"{root}/"):
                return True
        elif path == pattern:
            return True
    return False


def test_seven_workflows_validate_and_cover_each_legacy_command_once() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    actual_dirs = {path.name for path in WORKFLOW_ROOT.iterdir() if path.is_dir()}
    assert actual_dirs == set(ROUTES)

    seen: list[str] = []
    for workflow_id, expected_actions in ROUTES.items():
        workflow = _load_yaml(WORKFLOW_ROOT / workflow_id / "workflow.yaml")
        jsonschema.validate(workflow, schema)
        assert workflow["id"] == workflow_id
        assert set(workflow["actions"]) == set(_all_actions(workflow_id))

        for action_id, operation_id in _all_actions(workflow_id).items():
            action = workflow["actions"][action_id]
            assert set(action) == ACTION_KEYS
            assert action["legacy_id"] == operation_id
            assert action["procedure"] == f"stages/{action_id}.md"

        for action_id, legacy_id in expected_actions.items():
            seen.append(legacy_id)

    expected_legacy = {legacy_id for actions in ROUTES.values() for legacy_id in actions.values()}
    assert len(seen) == len(set(seen)) == 22
    assert set(seen) == expected_legacy


def test_stage_files_match_the_frozen_v1_equivalent_bodies() -> None:
    assert set(STAGE_BODY_SHA256) == {
        f"{workflow_id}.{action_id}"
        for workflow_id, actions in ROUTES.items()
        for action_id in actions
    }
    for workflow_id, actions in ROUTES.items():
        for action_id in actions:
            stage = WORKFLOW_ROOT / workflow_id / "stages" / f"{action_id}.md"
            body = stage.read_text(encoding="utf-8").strip().encode()
            assert hashlib.sha256(body).hexdigest() == STAGE_BODY_SHA256[
                f"{workflow_id}.{action_id}"
            ]


def test_inline_local_spec_paths_resolve_from_the_stage_directory() -> None:
    paths: list[tuple[Path, str]] = []
    for stage in WORKFLOW_ROOT.glob("*/stages/*.md"):
        for relative in CAPABILITY_REFERENCE.findall(stage.read_text(encoding="utf-8")):
            relative = relative.rstrip(".,;:)").replace("<venue>", "arxiv")
            paths.append((stage, relative))
            assert (stage.parent / relative).resolve().exists(), (
                f"{stage.relative_to(REPO_ROOT)} has unresolved inline spec path "
                f"{relative}"
            )
    assert len(paths) == 56


def test_router_skills_are_short_and_load_only_the_selected_stage() -> None:
    for workflow_id in ROUTES:
        skill = (WORKFLOW_ROOT / workflow_id / "SKILL.md").read_text(encoding="utf-8")
        assert len(skill.split()) <= 250
        assert "workflow.yaml" in skill
        assert "selected action" in skill.lower()
        assert "only" in skill.lower()
        for action_id in _all_actions(workflow_id):
            assert f"`{action_id}`" in skill
            assert f"stages/{action_id}.md" in skill


def test_accumulating_actions_declare_executable_retention_targets() -> None:
    polish = _load_yaml(WORKFLOW_ROOT / "polish" / "workflow.yaml")["actions"]["run"]
    xreview = _load_yaml(WORKFLOW_ROOT / "xreview" / "workflow.yaml")["actions"]["run"]
    assert polish["retention"] == {
        "directory": ".evidraft/style",
        "pattern": "humanize-*",
        "keep_last": 30,
        "max_age_days": 90,
    }
    assert xreview["retention"] == {
        "directory": ".evidraft/reviews",
        "pattern": "*.md",
        "keep_last": 50,
        "max_age_days": 180,
    }


def test_roles_and_policies_are_closed_v2_vocabularies() -> None:
    roles_doc = _load_yaml(PLUGIN_ROOT / "roles" / "roles.yaml")
    assert set(roles_doc) == {"tiers", "roles"}
    assert set(roles_doc["tiers"]) == {"fast", "standard", "deep"}
    assert set(roles_doc["roles"]) == ROLE_IDS
    for role in roles_doc["roles"].values():
        assert set(role) == {"description", "default_tier", "modes"}
        assert role["default_tier"] in {"fast", "standard", "deep"}
        assert role["modes"]

    policy_doc = _load_yaml(PLUGIN_ROOT / "policies" / "policy.yaml")
    assert set(policy_doc) == {"policies"}
    assert set(policy_doc["policies"]) == POLICY_IDS
    assert policy_doc["policies"]["scope"]["operations"]["block"] == [
        "paper.draft",
        "patent.claims",
        "polish.run",
    ]
    assert policy_doc["policies"]["scope"]["operations"]["warn"] == [
        "paper.idea",
        "patent.scout",
        "research.deep",
    ]


def test_workspace_safety_has_global_denies_and_one_bounded_write_zone() -> None:
    policy = _load_yaml(PLUGIN_ROOT / "policies" / "policy.yaml")["policies"][
        "workspace-safety"
    ]
    assert set(policy) == {
        "description",
        "always",
        "operation_write_zones",
        "project_extension",
        "tool_access",
    }
    assert set(policy["always"]) == {"root_confinement", "sensitive_path_deny"}
    assert policy["always"]["sensitive_path_deny"] == LEGACY_SENSITIVE_PATTERNS
    assert policy["project_extension"] == "safety.forbidden_paths"
    assert policy["tool_access"]["forbidden_tool_patterns"] == [
        "Bash:rm -rf*",
        "Bash:sudo*",
    ]
    assert set(policy["tool_access"]["default_allowed_tools"]) >= {
        "Read",
        "Glob",
        "Grep",
        "Edit",
        "Write",
        "Bash:git*",
    }
    assert set(policy["operation_write_zones"]) == {"xreview.run"}
    assert policy["operation_write_zones"]["xreview.run"] == [
        ".evidraft/reviews/**",
        ".evidraft/reviews/.tmp/**",
    ]

    assert _workspace_write_allowed(policy, "paper.init", "manuscript/references.bib")
    assert _workspace_write_allowed(
        policy,
        "xreview.run",
        ".evidraft/reviews/codex-review.md",
    )
    assert _workspace_write_allowed(
        policy,
        "xreview.run",
        ".evidraft/reviews/.tmp/raw-output.json",
    )
    assert not _workspace_write_allowed(policy, "xreview.run", "manuscript/main.tex")
    assert not _workspace_write_allowed(policy, "paper.init", ".env")
    assert not _workspace_write_allowed(policy, "paper.init", "../outside.txt")


@pytest.mark.parametrize(
    "path",
    [
        "nested/.env",
        ".env.local",
        "secrets/token",
        "credentials.json",
        "keys/private.pem",
        "keys/private.key",
        ".ssh/id_rsa",
    ],
)
def test_workspace_safety_denies_the_complete_legacy_sensitive_set(path: str) -> None:
    policy = _load_yaml(PLUGIN_ROOT / "policies" / "policy.yaml")["policies"][
        "workspace-safety"
    ]
    assert not _workspace_write_allowed(policy, "paper.init", path)


def test_actions_reference_only_declared_roles_policies_and_tiers() -> None:
    roles = _load_yaml(PLUGIN_ROOT / "roles" / "roles.yaml")["roles"]
    declared_modes = [mode for role in roles.values() for mode in role["modes"]]
    assert len(declared_modes) == len(set(declared_modes)) == 16
    assert set(declared_modes) == set(MODE_ASSIGNMENTS)

    for workflow_id in ROUTES:
        workflow = _load_yaml(WORKFLOW_ROOT / workflow_id / "workflow.yaml")
        for action_id in _all_actions(workflow_id):
            action = workflow["actions"][action_id]
            assert set(action["policies"]) <= POLICY_IDS
            for assignment in action["roles"]:
                role_id, tier = MODE_ASSIGNMENTS[assignment["mode"]]
                assert assignment["id"] == role_id
                assert assignment["tier"] == tier
                assert assignment["mode"] in roles[role_id]["modes"]


def test_research_explain_declares_the_native_paper_note_contract() -> None:
    action = _load_yaml(WORKFLOW_ROOT / "research" / "workflow.yaml")["actions"]["explain"]
    assert action["legacy_id"] == "paper-explain"
    assert action["defaults"] == {"mode": "graduate"}
    assert [item["name"] for item in action["inputs"]] == ["source", "mode", "out"]
    assert action["inputs"][1]["values"] == ["beginner", "graduate", "reviewer"]
    assert action["outputs"] == [
        {"path": ".evidraft/notes/paper-explanations/<paper-slug>.md"}
    ]
    assert action["policies"] == []
    assert action["roles"] == [
        {"id": "researcher", "mode": "paper-explainer", "tier": "deep"},
        {"id": "researcher", "mode": "literature-reviewer", "tier": "standard"},
    ]
    assert action["retention"] == {}


def test_research_explain_stage_enforces_the_complete_executable_contract() -> None:
    stage = (
        WORKFLOW_ROOT / "research" / "stages" / "explain.md"
    ).read_text(encoding="utf-8")
    normalized_stage = " ".join(stage.split())
    assert "# workflow:research.explain" in stage
    for heading in (
        "## Phase 1: Resolve source and output",
        "## Phase 2: Map the source paper",
        "## Phase 3: Run bounded analysis work streams",
        "## Phase 4: Synthesize the academic note",
        "## Phase 5: Validate and report",
        "## Constraints",
        "## Done criteria",
    ):
        assert heading in stage
    for heading in (
        "## 1. Paper identity and one-sentence takeaway",
        "## 2. Research problem and background",
        "## 3. Core contributions",
        "## 4. Method walkthrough",
        "## 5. Key equations and symbol-by-symbol explanations",
        "## 6. Experimental setup and results",
        "## 7. Limitations, failure modes, and conclusion boundaries",
        "## 8. Reproduction notes",
        "## 9. Similar methods",
        "## 10. Subsequent improvements and latest related methods",
        "## 11. Learning-check questions",
        "## 12. Sources and verification record",
    ):
        assert heading in stage
    for collision_choice in ("`reuse`", "`augment`", "`overwrite`"):
        assert collision_choice in stage
    assert "Only `paper-explainer` may write the final note" in normalized_stage
    assert "neither worker may race" in normalized_stage
    assert "Mandatory external research cannot be disabled" in normalized_stage
    assert "three to five verified similar" in normalized_stage
    assert "three to five verified subsequent" in normalized_stage
    for label in (
        "[Paper section 3.2]",
        "[Equation 4]",
        "[Figure 2]",
        "[Table 1]",
        "[External: citation]",
        "[External: official-code]",
        "[Interpretation]",
        "[abstract-only]",
    ):
        assert label in normalized_stage
    assert stage.index("workflow preflight research.explain") < stage.index("`mkdir -p`")
    assert stage.index("`mkdir -p`") < stage.index("writes exactly one Markdown note")
    assert "source full text or mandatory external retrieval failed" in normalized_stage
    assert "report the action as incomplete" in normalized_stage
