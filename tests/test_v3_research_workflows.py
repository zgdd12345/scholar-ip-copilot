from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "scholar-ip"
WORKFLOWS = PLUGIN / "workflows"
CAPABILITY = PLUGIN / "capabilities" / "research" / "paper-explanation"
RESEARCH_CAPABILITIES = PLUGIN / "capabilities" / "research"
ROLES = PLUGIN / "roles"


def _yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").lower().split())


def test_research_surface_removes_guide_and_defaults_deep_to_fast() -> None:
    workflow = _yaml(WORKFLOWS / "research" / "workflow.yaml")

    assert list(workflow["actions"]) == ["reading-list", "explain", "deep"]
    assert "guidance" not in workflow["description"].lower()
    assert workflow["actions"]["deep"]["defaults"]["mode"] == "fast"
    mode = next(item for item in workflow["actions"]["deep"]["inputs"] if item["name"] == "mode")
    assert mode["default"] == "fast"
    assert not (WORKFLOWS / "research" / "stages" / "guide.md").exists()
    skill = (WORKFLOWS / "research" / "SKILL.md").read_text()
    assert "`guide`" not in skill
    assert "guidance" not in skill.lower()


def test_scope_defaults_to_one_follow_up_then_one_approval() -> None:
    workflow = _yaml(WORKFLOWS / "scope" / "workflow.yaml")
    action = workflow["actions"]["run"]
    mode = next(item for item in action["inputs"] if item["name"] == "mode")
    stage = _normalized(WORKFLOWS / "scope" / "stages" / "run.md")

    assert action["defaults"]["mode"] == mode["default"] == "fast"
    assert "ask exactly one follow-up question" in stage
    assert "ask exactly once for approval" in stage
    assert "one question per message" not in stage
    assert "3 questions per branch" not in stage


def test_using_routes_clear_intent_directly_and_only_clarifies_ambiguity() -> None:
    stage = _normalized(WORKFLOWS / "using" / "stages" / "run.md")

    assert "route unambiguous intent directly" in stage
    assert "do not ask for confirmation" in stage
    assert "ask one clarifying question" in stage
    assert "only when the intent is ambiguous" in stage
    assert "offer to invoke" not in stage


def test_reading_list_collision_policy_is_automatic_only_for_default_path() -> None:
    stage = _normalized(WORKFLOWS / "research" / "stages" / "reading-list.md")

    assert "automatic unique sibling" in stage
    assert "append a numeric suffix" in stage
    assert "if explicit `out` is non-empty" in stage
    assert "ask for confirmation before replacing it" in stage
    assert "do not proceed" not in stage


def test_conditional_outputs_are_declared_optional() -> None:
    research = _yaml(WORKFLOWS / "research" / "workflow.yaml")["actions"]
    scope = _yaml(WORKFLOWS / "scope" / "workflow.yaml")["actions"]["run"]

    assert research["explain"]["outputs"][0]["required"] is False
    critique = next(
        output
        for output in research["deep"]["outputs"]
        if output["path"] == ".evidraft/literature/critique/"
    )
    citation_audit = next(
        output
        for output in research["deep"]["outputs"]
        if output["path"] == ".evidraft/literature/citation_audit.json"
    )
    assert critique["required"] is False
    assert citation_audit["required"] is False
    assert scope["outputs"][0]["required"] is False


def test_deep_done_criteria_require_critique_only_in_full_mode() -> None:
    stage = _normalized(WORKFLOWS / "research" / "stages" / "deep.md")

    assert "all 6 artefacts" not in stage
    assert "fast mode does not require `critique/`" in stage
    assert "only `mode=full` requires `critique/`" in stage


def test_explain_requires_graph_external_attempts_and_partial_degradation() -> None:
    workflow = _yaml(WORKFLOWS / "research" / "workflow.yaml")
    explain = workflow["actions"]["explain"]
    stage = _normalized(WORKFLOWS / "research" / "stages" / "explain.md")
    spec = _normalized(CAPABILITY / "spec.md")
    combined = f"{stage} {spec}"

    assert explain["roles"] == [
        {"id": "researcher", "mode": "paper-indexer", "tier": "standard"},
        {"id": "researcher", "mode": "paper-analysis-worker", "tier": "standard"},
        {"id": "researcher", "mode": "paper-reasoning-worker", "tier": "deep"},
        {
            "id": "evidence-reviewer",
            "mode": "explanation-evidence-auditor",
            "tier": "standard",
        },
        {"id": "researcher", "mode": "paper-explainer", "tier": "deep"},
    ]
    for token in (
        "task-graph.yaml",
        "min(host_capacity, 15, ready_task_count)",
        "similar-methods",
        "current-methods",
        "fresh worker",
        "attempt: 2",
        "status: partial",
        "both attempt reasons",
    ):
        assert token in combined
    assert "ordinary beginner and graduate explanations do not require external research" not in combined
    assert "no fixed cardinality, dependency waves, or retry count" not in combined


def test_explanation_resources_and_modes_are_restored() -> None:
    for name in (
        "task-graph.yaml",
        "paper-map.schema.json",
        "analysis-packet.schema.json",
    ):
        assert (CAPABILITY / name).is_file()

    worker_modes = {
        "paper-indexer",
        "paper-analysis-worker",
        "paper-reasoning-worker",
        "explanation-evidence-auditor",
    }
    for mode in worker_modes:
        assert (ROLES / "modes" / f"{mode}.md").is_file()

    roles = _yaml(ROLES / "roles.yaml")["roles"]
    assigned_modes = {mode for role in roles.values() for mode in role.get("modes", [])}
    assert worker_modes <= assigned_modes
    for retained in ("paper-explainer", *worker_modes):
        assert (ROLES / "modes" / f"{retained}.md").is_file()
        assert retained in assigned_modes


def test_explain_missing_full_text_writes_a_boundary_note() -> None:
    stage = _normalized(WORKFLOWS / "research" / "stages" / "explain.md")
    spec = _normalized(CAPABILITY / "spec.md")
    combined = f"{stage} {spec}"

    assert "full text is unavailable, write a limited evidence-boundary note" in combined
    assert "do not infer unseen methods, equations, figures, tables, or results" in combined
    assert "status: partial" in combined
    assert "identity/evidence-boundary note" in combined
    assert "do not invent analysis" in combined


def test_explain_auditor_is_advisory_and_workspace_safety_remains_hard() -> None:
    combined = f"{_normalized(WORKFLOWS / 'research/stages/explain.md')} {_normalized(CAPABILITY / 'spec.md')}"

    assert "auditor findings cannot suppress synthesis" in combined
    assert "scope and evidence-integrity are advisory" in combined
    for token in ("workspace confinement", "sensitive paths", "overwrite", "external publication"):
        assert token in combined


def test_reading_list_network_failure_still_writes_a_boundary_note() -> None:
    stage = _normalized(WORKFLOWS / "research" / "stages" / "reading-list.md")
    reviewer = _normalized(ROLES / "modes" / "literature-reviewer.md")
    combined = f"{stage} {reviewer}"

    assert "when network access or webfetch is unavailable" in combined
    assert "write the one output note" in combined
    assert "evidence boundary" in combined
    assert "complete_with_gaps" in combined
    assert "do not invent metadata" in combined
    assert "must stop" not in combined


def test_using_contract_only_questions_for_ambiguity_or_explicit_overwrite() -> None:
    stage = _normalized(WORKFLOWS / "using" / "stages" / "run.md")
    spec = _normalized(RESEARCH_CAPABILITIES / "using-scholar-ip-copilot" / "spec.md")
    combined = f"{stage} {spec}"

    assert "route unambiguous intent directly" in combined
    assert "do not ask for confirmation" in combined
    assert "ask one clarifying question only when" in combined
    assert "explicit output replacement" in combined
    assert "always confirm" not in combined
    assert "required by policy:scope" not in combined


def test_scope_is_advisory_across_research_runtime_resources() -> None:
    paths = [
        RESEARCH_CAPABILITIES / "using-scholar-ip-copilot" / "spec.md",
        RESEARCH_CAPABILITIES / "using-deep-research" / "spec.md",
        RESEARCH_CAPABILITIES / "brainstorming" / "spec.md",
        RESEARCH_CAPABILITIES / "brainstorming" / "references" / "staleness-rule.md",
        RESEARCH_CAPABILITIES / "deep-literature-review" / "references" / "stage-1-frame.md",
        RESEARCH_CAPABILITIES / "deep-literature-review" / "references" / "failure-modes.md",
        ROLES / "modes" / "deep-research-orchestrator.md",
    ]
    combined = " ".join(_normalized(path) for path in paths)

    assert "scope is advisory" in combined
    for hard_gate in (
        "policy:scope preflight blocks",
        "scope gate",
        "gated action",
        "required by policy:scope",
        "blocks when required scaffolding",
    ):
        assert hard_gate not in combined


def test_deep_fast_skips_critique_and_audit_gaps_do_not_block() -> None:
    stage = _normalized(WORKFLOWS / "research" / "stages" / "deep.md")
    capability = _normalized(RESEARCH_CAPABILITIES / "deep-literature-review" / "spec.md")
    references = " ".join(
        _normalized(RESEARCH_CAPABILITIES / "deep-literature-review" / "references" / name)
        for name in (
            "breadth-depth-budget.md",
            "stage-5-critique.md",
            "stage-6-synthesise.md",
            "failure-modes.md",
            "prisma-recipe.md",
        )
    )
    orchestrator = _normalized(ROLES / "modes" / "deep-research-orchestrator.md")
    combined = f"{stage} {capability} {references} {orchestrator}"

    assert "mode=fast skips stage 5 critique" in combined
    assert "do not dispatch `paper-critic`" in combined
    assert "mode=full requires critique" in combined
    assert "missing or failed citation audit" in combined
    assert "complete_with_gaps" in combined
    for refusal in (
        "run does not complete",
        "refuse to mark the run done",
        "never proceed past stage 6",
        "citation_audit.json` reports `failed=0`",
    ):
        assert refusal not in combined


def test_research_explain_has_fixed_bounded_graph_while_deep_remains_adaptive() -> None:
    paths = [
        WORKFLOWS / "research" / "stages" / "explain.md",
        WORKFLOWS / "research" / "stages" / "deep.md",
        RESEARCH_CAPABILITIES / "paper-explanation" / "spec.md",
        RESEARCH_CAPABILITIES / "deep-literature-review" / "references" / "stage-5-critique.md",
        ROLES / "modes" / "deep-research-orchestrator.md",
    ]
    combined = " ".join(_normalized(path) for path in paths)

    assert "min(host_capacity, 15, ready_task_count)" in combined
    assert "max_attempts: 2" in combined
    assert "dispatch according to task independence" in combined
    assert "one pass per included paper" not in combined
    assert "dispatch sub-agents one stage at a time" not in combined
