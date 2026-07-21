"""Contract tests for the compact EviDraft 3.0 workflow source."""

from __future__ import annotations

import hashlib
import json
from fnmatch import fnmatchcase
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
    "paper.check": "46cd9773cfa83fc1f5c36b30fafa2085c06d9212298b5a523ca2f9d373cd7506",
    "paper.code-audit": "b45ea469a8fe306fd9c142caa3a000f9d65e8584148cecd6b54d62ee3621d6fa",
    "paper.draft": "cd407ee349e8b67d2a9cdf08b41a15427f7bdc369cd76b19627ab0e0763519dc",
    "paper.experiment": "a34fd89adc79d798f527cea24663905e1c38261292ae20c51478c9f41960592f",
    "paper.idea": "c5dbd7015aa4a72ed168eb456f6a6e0f10fc0f4c7b0fe00b87eddff63d42e6da",
    "paper.init": "2e25481347ebf841c77aa590910ac12f9fa11d9ae1b25bfc9a8d1e1402fd09b9",
    "paper.lit": "b6e78f94df0eb1d422f1c276d8f42b2b5c3f5121b53f47300ef5b62fe9beb5e7",
    "paper.review": "7fb50d38a38862cc1c56ab162e47d6927be0cb96e24df2c8744822af550b5254",
    "paper.venue": "67f410ade88073492b28c4e0145e5dc15978a5b0fd769cfcc88558050e6daa60",
    "patent.claims": "56311fc9c848e3fbc9f7524f059b65a8b1f28533a3989ee821694c964ce31ab6",
    "patent.disclosure": "8f13829a0e7cf45cc42c5c8934b256972a44eeb1db63d97ead7175af5e99985d",
    "patent.init": "a36f876527aeb7b7348de1e6ab2d113d133a7de2537b1a81ea6f7e96c9f2a02e",
    "patent.prior-art": "4c5def3f4ce4ed64dc67f65a91f150fa7272d828f1eb27b255965bd75f2b2e32",
    "patent.review": "86428aef4a7ad94523b42631a90e8c442f1942db24dfbaeee60c90a7c98b0232",
    "patent.scout": "385070d63aba92e3636392abd0a94f3a1b66071ac7bbc4b940a56a415172d996",
    "polish.run": "fe9e6a06391b793bde540d35510f5d75d941d9c51c2d7d409028e59391a250de",
    "research.deep": "30a3d260186be584f29b0b1bbbc3e56759d810ad353bfc7cdd7a4deea155e7f7",
    "research.reading-list": "66b96ac2d701b250d842f393a0e88e00148d3e3293c8873290a1089ca6b80ec7",
    "scope.run": "b7907f1f69956af46c23a1b6cfb3c34d2c33107cdc5768331ad32c2bf0e9eb7c",
    "using.run": "b4964c41087ab1333d79b1be774378d21f60450467369f8d55cd2471e71b0604",
    "xreview.run": "81d1bc406c556453a7b7c994cd4bab038b3302deb3436604ab30e7c2d59536e8",
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
    assert len(seen) == len(set(seen)) == 21
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
    assert len(paths) == 53


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
    assert policy_doc["policies"]["scope"] == {
        "description": "Provide optional project intent and constraints without blocking generation.",
        "enforcement": "advisory",
    }
    assert policy_doc["policies"]["evidence-integrity"]["enforcement"] == "audit"
    assert policy_doc["policies"]["evidence-integrity"]["verdicts"] == [
        "PASS",
        "WARN",
        "FAIL",
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
        {
            "path": ".evidraft/notes/paper-explanations/<paper-slug>.md",
            "required": False,
        }
    ]
    assert action["policies"] == []
    assert action["roles"] == [
        {"id": "researcher", "mode": "paper-explainer", "tier": "deep"},
        {"id": "researcher", "mode": "literature-reviewer", "tier": "standard"},
    ]
    assert action["retention"] == {}


def test_research_explain_removes_fixed_worker_packet_interfaces() -> None:
    stage = (WORKFLOW_ROOT / "research/stages/explain.md").read_text(encoding="utf-8")
    spec = (
        PLUGIN_ROOT / "capabilities/research/paper-explanation/spec.md"
    ).read_text(encoding="utf-8")
    for document in (stage, spec):
        for removed in (
            "task-graph.yaml",
            "paper-map.schema.json",
            "analysis-packet.schema.json",
            "task_id",
            "dependency_packets",
            "paper-indexer",
            "paper-analysis-worker",
            "paper-reasoning-worker",
            "explanation-evidence-auditor",
        ):
            assert removed not in document


def test_research_explain_has_no_validate_return_runtime_command() -> None:
    stage = (WORKFLOW_ROOT / "research/stages/explain.md").read_text(encoding="utf-8")
    assert "paper-explanation validate-return" not in stage
    assert "task graph" not in stage.lower()
    assert "packet" not in stage.lower()


def test_research_explain_preflights_local_pdf_before_any_read() -> None:
    stage = (WORKFLOW_ROOT / "research/stages/explain.md").read_text(encoding="utf-8")
    normalized = " ".join(stage.split())
    command = "evidraft workflow preflight research.explain --read-target <source>"

    assert command in normalized
    assert "For a local PDF" in stage
    assert "before reading" in normalized
    assert stage.index(command) < stage.index("Try to obtain readable full text")


def test_research_explain_rechecks_collision_immediately_before_final_write() -> None:
    stage = (WORKFLOW_ROOT / "research/stages/explain.md").read_text(encoding="utf-8")
    normalized = " ".join(stage.split())

    assert "Never overwrite a non-empty note silently" in normalized
    assert "collision-safe dated sibling" in normalized
    assert "Immediately before the single final write, re-check the path" in normalized
    assert "performs the single final write" in normalized


def test_research_explain_stage_enforces_the_complete_executable_contract() -> None:
    stage = (
        WORKFLOW_ROOT / "research" / "stages" / "explain.md"
    ).read_text(encoding="utf-8")
    normalized_stage = " ".join(stage.split())
    assert "# workflow:research.explain" in stage
    for heading in (
        "## 1. Resolve the source and destination",
        "## 2. Explain adaptively",
        "## 3. Expand related research conditionally",
        "## 4. Write and report status",
        "## Constraints",
        "## Done criteria",
    ):
        assert heading in stage
    for collision_choice in ("`reuse`", "collision-safe dated sibling", "replacement"):
        assert collision_choice in normalized_stage
    for label in (
        "[Paper section ...]",
        "[Equation ...]",
        "[Figure ...]",
        "[Table ...]",
        "[Interpretation]",
    ):
        assert label in normalized_stage
    prepare = (
        "evidraft workflow prepare-output research.explain "
        "--target <resolved-output>"
    )
    assert prepare in stage
    assert "mkdir -p" not in stage
    allowed_tools = _load_yaml(PLUGIN_ROOT / "policies" / "policy.yaml")["policies"][
        "workspace-safety"
    ]["tool_access"]["default_allowed_tools"]
    assert any(fnmatchcase(f"Bash:{prepare}", pattern) for pattern in allowed_tools)
    assert "paper-explanation validate-return" not in normalized_stage
    assert "complete_with_gaps" in normalized_stage
    assert "blocked" in normalized_stage


def test_research_explain_stage_declares_adaptive_delegation() -> None:
    stage = (WORKFLOW_ROOT / "research/stages/explain.md").read_text(
        encoding="utf-8"
    )
    normalized = " ".join(stage.split())
    for token in (
        "beginner",
        "graduate",
        "reviewer",
        "may explain directly or delegate bounded independent checks",
        "no fixed cardinality, dependency waves, or retry count",
        "literature-reviewer",
    ):
        assert token in normalized
    assert "task-graph.yaml" not in normalized


def test_research_explain_status_contract_is_deterministic() -> None:
    normalized = " ".join(
        (WORKFLOW_ROOT / "research/stages/explain.md").read_text().split()
    )
    for token in (
        "complete",
        "complete_with_gaps",
        "blocked",
        "concrete recovery action",
        "limited evidence-boundary note",
    ):
        assert token in normalized


def test_research_explain_external_research_is_conditional() -> None:
    documents = (
        WORKFLOW_ROOT / "research/stages/explain.md",
        PLUGIN_ROOT / "capabilities/research/paper-explanation/spec.md",
    )
    for document in documents:
        normalized = " ".join(document.read_text(encoding="utf-8").split())
        assert "reviewer mode or the user explicitly requests comparison" in normalized
        assert "Ordinary beginner and graduate explanations do not require external research" in normalized
        assert "External shortfalls" in normalized or "external-search shortfall" in normalized


def test_research_explain_allows_direct_fallback_and_keeps_one_writer() -> None:
    normalized = " ".join(
        (WORKFLOW_ROOT / "research/stages/explain.md").read_text().split()
    )
    assert "may explain directly" in normalized
    assert "failed optional check becomes a reported gap" in normalized
    assert "Only `paper-explainer` owns the resolved destination" in normalized
    assert "performs the single final write" in normalized
