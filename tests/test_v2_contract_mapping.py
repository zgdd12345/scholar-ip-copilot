"""Frozen behavioral contracts for the EviDraft v1-to-v2 workflow collapse."""

from __future__ import annotations

import json
import hashlib
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "v2" / "legacy_to_v2_contract.json"
)
WORKFLOW_ROOT = REPO_ROOT / "plugins" / "scholar-ip" / "workflows"
FIXTURE_SHA256 = "ad51d5fbc621d411fdb6f5ca2cc873725e71bb6060e8efa9e6c22ca8160ddb4d"

EXPECTED_OPERATIONS = (
    ("using", "using", "run"),
    ("brainstorming", "scope", "run"),
    ("using-deep-research", "research", "guide"),
    ("reading-list", "research", "reading-list"),
    ("deepresearch", "research", "deep"),
    ("paper-init", "paper", "init"),
    ("paper-lit", "paper", "lit"),
    ("paper-idea", "paper", "idea"),
    ("paper-code-audit", "paper", "code-audit"),
    ("paper-experiment", "paper", "experiment"),
    ("paper-review", "paper", "review"),
    ("paper-draft", "paper", "draft"),
    ("paper-check", "paper", "check"),
    ("paper-venue", "paper", "venue"),
    ("patent-init", "patent", "init"),
    ("patent-scout", "patent", "scout"),
    ("patent-prior-art", "patent", "prior-art"),
    ("patent-disclosure", "patent", "disclosure"),
    ("patent-claims", "patent", "claims"),
    ("patent-review", "patent", "review"),
    ("polish", "polish", "run"),
    ("xreview", "xreview", "run"),
)
PUBLIC_WORKFLOWS = frozenset(
    {"using", "scope", "research", "paper", "patent", "polish", "xreview"}
)
CONTRACT_FIELDS = (
    "legacy_id",
    "inputs",
    "outputs",
    "policies",
    "roles",
    "retention",
)
ACTION_FIELDS = frozenset((*CONTRACT_FIELDS, "procedure", "defaults"))
ROLE_IDS = frozenset(
    {
        "researcher",
        "evidence-reviewer",
        "code-reviewer",
        "experiment-reviewer",
        "writing-reviewer",
        "patent-reviewer",
    }
)
ROLE_TIERS = frozenset({"fast", "standard", "deep"})
POLICY_FOR_HOOK = {
    "citation-guard": "evidence-integrity",
    "evidence-consistency": "evidence-integrity",
    "humanize-evidence-preserve": "evidence-integrity",
    "sensitive-file-guard": "workspace-safety",
    "external-write-zone": "workspace-safety",
    "scope-required": "scope",
}
NON_POLICY_HOOKS = {"latex-compile"}
ROLE_FOR_SUBAGENT = {
    "brainstormer": ("researcher", "standard"),
    "literature-reviewer": ("researcher", "standard"),
    "screener": ("researcher", "fast"),
    "paper-critic": ("researcher", "standard"),
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


def _load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


CONTRACT = _load_fixture()
MAPPINGS = CONTRACT["mappings"]


def _workflow_path(workflow: str) -> Path:
    return WORKFLOW_ROOT / workflow / "workflow.yaml"


def _load_workflow(workflow: str) -> dict[str, Any]:
    path = _workflow_path(workflow)
    assert path.is_file(), (
        f"missing EviDraft v2 workflow source: {path.relative_to(REPO_ROOT)}"
    )
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict), f"{path} must contain a YAML mapping"
    return document


def _policies_for_hooks(hooks: list[str]) -> list[str]:
    assert set(POLICY_FOR_HOOK).isdisjoint(NON_POLICY_HOOKS), (
        "policy and non-policy hook vocabularies must be disjoint"
    )
    policies: list[str] = []
    for hook in hooks:
        is_policy = hook in POLICY_FOR_HOOK
        is_non_policy = hook in NON_POLICY_HOOKS
        assert is_policy or is_non_policy, f"unknown legacy hook {hook!r}"
        assert is_policy != is_non_policy, (
            f"legacy hook {hook!r} must belong to exactly one hook vocabulary"
        )
        policy = POLICY_FOR_HOOK.get(hook)
        if is_policy and policy not in policies:
            policies.append(policy)
    return policies


def _roles_for_subagents(subagents: list[str]) -> list[dict[str, str]]:
    roles: list[dict[str, str]] = []
    for subagent in subagents:
        assert subagent in ROLE_FOR_SUBAGENT, (
            f"legacy subagent {subagent!r} has no v2 semantic-role projection"
        )
        role_id, tier = ROLE_FOR_SUBAGENT[subagent]
        roles.append({"id": role_id, "mode": subagent, "tier": tier})
    return roles


def _expected_actions_by_workflow() -> dict[str, set[str]]:
    expected: dict[str, set[str]] = defaultdict(set)
    for item in MAPPINGS:
        expected[item["workflow"]].add(item["action"])
    return dict(expected)


def _case_id(item: dict[str, Any]) -> str:
    return f"{item['legacy_id']}->{item['workflow']}.{item['action']}"


def _assert_action_matches_contract(
    mapping: dict[str, Any], actual: dict[str, Any]
) -> None:
    assert set(actual) == ACTION_FIELDS
    assert actual["legacy_id"] == mapping["legacy_id"]
    assert actual["defaults"] == {
        item["name"]: item["default"] for item in actual["inputs"] if "default" in item
    }
    for field in ("inputs", "outputs", "policies", "roles", "retention"):
        actual_value = actual[field]
        if field == "retention":
            assert set(mapping[field]).issubset(actual_value), (
                f"{mapping['workflow']}.{mapping['action']} changed frozen {field}"
            )
            actual_value = {key: actual_value[key] for key in mapping[field]}
        assert _normalize_v2_references(actual_value) == _normalize_v2_references(mapping[field]), (
            f"{mapping['workflow']}.{mapping['action']} changed frozen {field}"
        )


def _normalize_v2_references(value: Any) -> Any:
    """Ignore identifier relocation while preserving every behavioral field."""
    if isinstance(value, str):
        replacements = {
            "skills/scholar-search/SKILL.md": "capability:scholar-search",
            "/scholar:deepresearch": "workflow:research.deep",
            "citation-guard + evidence-consistency apply": "policy:evidence-integrity applies",
            "EviDraft agent id whose body is rendered as the prompt": (
                "EviDraft role mode whose full private spec is rendered as the prompt"
            ),
        }
        for old, new in replacements.items():
            value = value.replace(old, new)
        return value
    if isinstance(value, list):
        return [_normalize_v2_references(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_v2_references(item) for key, item in value.items()}
    return value


def test_fixture_freezes_all_22_legacy_commands() -> None:
    assert hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest() == FIXTURE_SHA256
    assert CONTRACT["contract_version"] == 2
    assert len(MAPPINGS) == 22
    actual = tuple(
        (item["legacy_id"], item["workflow"], item["action"])
        for item in MAPPINGS
    )
    assert actual == EXPECTED_OPERATIONS
    assert {item["workflow"] for item in MAPPINGS} == PUBLIC_WORKFLOWS
    assert len({item["legacy_id"] for item in MAPPINGS}) == len(MAPPINGS)
    assert len(
        {(item["workflow"], item["action"]) for item in MAPPINGS}
    ) == len(MAPPINGS)


def test_fixture_records_complete_frontmatter_contracts() -> None:
    required = {
        "legacy_id",
        "workflow",
        "action",
        "inputs",
        "outputs",
        "legacy_hooks",
        "policies",
        "roles",
        "retention",
    }
    for item in MAPPINGS:
        assert set(item) == required, item["legacy_id"]
        assert isinstance(item["inputs"], list), item["legacy_id"]
        assert isinstance(item["outputs"], list), item["legacy_id"]
        assert isinstance(item["legacy_hooks"], list), item["legacy_id"]
        assert isinstance(item["policies"], list), item["legacy_id"]
        assert isinstance(item["roles"], list), item["legacy_id"]
        assert isinstance(item["retention"], dict), item["legacy_id"]
        for role in item["roles"]:
            assert set(role) == {"id", "mode", "tier"}, item["legacy_id"]
            assert role["id"] in ROLE_IDS, item["legacy_id"]
            assert isinstance(role["mode"], str) and role["mode"], item["legacy_id"]
            assert role["tier"] in ROLE_TIERS, item["legacy_id"]
        assert item["policies"] == _policies_for_hooks(item["legacy_hooks"])
        assert item["roles"] == _roles_for_subagents(
            [role["mode"] for role in item["roles"]]
        )


@pytest.mark.parametrize("workflow", sorted(PUBLIC_WORKFLOWS))
def test_all_seven_v2_workflow_documents_exist(workflow: str) -> None:
    path = _workflow_path(workflow)
    assert path.is_file(), (
        f"missing EviDraft v2 workflow source: {path.relative_to(REPO_ROOT)}"
    )


@pytest.mark.parametrize("workflow", sorted(PUBLIC_WORKFLOWS))
def test_v2_workflow_exposes_exact_action_set(workflow: str) -> None:
    document = _load_workflow(workflow)
    assert document.get("id") == workflow
    actions = document.get("actions")
    assert isinstance(actions, dict), f"{workflow}.actions must be a mapping"
    assert set(actions) == _expected_actions_by_workflow()[workflow]


@pytest.mark.parametrize("expected", MAPPINGS, ids=_case_id)
def test_v2_action_preserves_legacy_behavior(expected: dict[str, Any]) -> None:
    document = _load_workflow(expected["workflow"])
    actions = document.get("actions")
    assert isinstance(actions, dict), f"{expected['workflow']}.actions must be a mapping"
    assert expected["action"] in actions, (
        f"missing action {expected['workflow']}.{expected['action']}"
    )

    actual = actions[expected["action"]]
    assert isinstance(actual, dict)
    _assert_action_matches_contract(expected, actual)

    procedure = actual["procedure"]
    assert isinstance(procedure, str) and procedure.strip()
    procedure_path = _workflow_path(expected["workflow"]).parent / procedure
    assert procedure_path.is_file(), (
        f"missing procedure for {expected['workflow']}.{expected['action']}: "
        f"{procedure_path.relative_to(REPO_ROOT)}"
    )


@pytest.mark.parametrize(
    ("legacy_id", "field", "replacement"),
    (
        pytest.param("paper-draft", "policies", [], id="hook-derived-policies"),
        pytest.param("paper-draft", "roles", [], id="semantic-roles"),
        pytest.param("polish", "retention", {}, id="retention"),
    ),
)
def test_frozen_contract_rejects_deleted_workflow_behavior(
    legacy_id: str,
    field: str,
    replacement: list[Any] | dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    mapping = next(item for item in MAPPINGS if item["legacy_id"] == legacy_id)
    mutated_root = tmp_path / "workflows"
    shutil.copytree(WORKFLOW_ROOT, mutated_root)

    path = mutated_root / mapping["workflow"] / "workflow.yaml"
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    original = document["actions"][mapping["action"]][field]
    assert original, f"mutation case requires non-empty {legacy_id}.{field}"
    document["actions"][mapping["action"]][field] = replacement
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    monkeypatch.setitem(globals(), "WORKFLOW_ROOT", mutated_root)

    mutated_action = _load_workflow(mapping["workflow"])["actions"][mapping["action"]]
    with pytest.raises(AssertionError, match=rf"changed frozen {field}"):
        _assert_action_matches_contract(mapping, mutated_action)


def test_frozen_contract_rejects_unknown_hook() -> None:
    hooks = list(next(item for item in MAPPINGS if item["legacy_id"] == "paper-draft")["legacy_hooks"])
    hooks[hooks.index("citation-guard")] = "citation-gurad"
    with pytest.raises(AssertionError, match="unknown legacy hook 'citation-gurad'"):
        _policies_for_hooks(hooks)
