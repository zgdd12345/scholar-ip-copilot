from __future__ import annotations

import copy
import io
import json
from pathlib import Path

import jsonschema
import pytest
import yaml

import evidraft.paper_explanation as paper_explanation_module
from evidraft.cli import main as cli_main
from evidraft.paper_explanation import validate_paper_explanation_graph


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "plugins/scholar-ip/capabilities/research/paper-explanation"
ROLES = ROOT / "plugins/scholar-ip/roles/roles.yaml"

PROFILE_TASKS = {
    "beginner": ["I0", "B1", "B2", "B3", "S0"],
    "graduate": ["I0", "E1", "L1", "M1", "R1", "R2", "S0", "X1"],
    "reviewer": ["I0", "A1", "C1", "E1", "L1", "M1", "R1", "R2", "S0", "X1"],
}


def _graph() -> dict:
    return yaml.safe_load((BUNDLE / "task-graph.yaml").read_text(encoding="utf-8"))


def _schema(name: str) -> dict:
    return json.loads((BUNDLE / name).read_text(encoding="utf-8"))


def _declared_modes() -> set[str]:
    roles = yaml.safe_load(ROLES.read_text(encoding="utf-8"))["roles"]
    return {mode for role in roles.values() for mode in role["modes"]}


def _paper_map(*, attempt: int = 1) -> dict:
    return {
        "task_id": "I0",
        "attempt": attempt,
        "source_identity": {
            "title": "Attention Is All You Need",
            "authors": ["A. Author"],
            "year": 2017,
            "venue": "NeurIPS",
            "canonical_url": "https://arxiv.org/abs/1706.03762",
        },
        "full_text_ref": "papers/attention.pdf",
        "sections": [
            {"id": "3", "title": "Model Architecture", "locator": "Paper section 3"}
        ],
        "research_question": {
            "text": "Can attention replace recurrence?",
            "locator": "Paper section 1",
        },
        "prerequisites": [
            {"text": "Sequence transduction", "locator": "Paper section 1"}
        ],
        "contributions": [
            {"text": "An attention-only architecture", "locator": "Paper section 3"}
        ],
        "method_steps": [
            {"text": "Encode tokens with self-attention", "locator": "Paper section 3.1"}
        ],
        "equations": [
            {
                "id": "1",
                "locator": "Equation 1",
                "symbols": [{"symbol": "Q", "definition": "queries"}],
            }
        ],
        "figures": [],
        "tables": [],
        "experiments": {
            "datasets": [],
            "baselines": [],
            "metrics": [],
            "ablations": [],
            "result_locators": [],
        },
        "claims": [
            {"text": "The model uses self-attention.", "locator": "Paper section 3"}
        ],
        "assumptions": [],
        "limitations": [],
        "implementation_refs": [],
        "reproduction_gaps": [
            {"text": "Random seed is not specified", "locator": "Paper section 5"}
        ],
        "uncertainties": [
            {"text": "One appendix equation is unreadable", "locator": "Appendix A"}
        ],
    }


def _analysis_packet(
    *, task_id: str = "M1", attempt: int = 1, findings: int = 1, status: str = "complete"
) -> dict:
    return {
        "task_id": task_id,
        "attempt": attempt,
        "status": status,
        "findings": [
            {
                "claim": f"Grounded finding {index}",
                "evidence_refs": ["Paper section 3"],
                "confidence": "high",
                "label": "paper",
            }
            for index in range(findings)
        ],
        "uncertainties": [],
        "rejections": [],
        "retry_reason": None,
    }


def _instance_validator():
    validator = getattr(
        paper_explanation_module, "validate_paper_explanation_instance", None
    )
    assert callable(validator), "runtime instance validator is missing"
    return validator


def test_task_graph_caps_parallelism_at_fifteen_and_uses_two_attempts() -> None:
    assert _graph()["scheduler"] == {
        "max_parallel": 15,
        "max_attempts": 2,
        "nested_delegation": "forbidden",
        "result_order": "task_id",
    }


def test_graph_requires_similar_and_current_attempts_in_every_profile() -> None:
    graph = _graph()
    assert graph["tasks"]["B3"]["mandatory"] is True
    assert graph["tasks"]["B3"]["scope"] == ["similar-methods", "current-methods"]
    assert graph["tasks"]["R1"]["mandatory"] is True
    assert graph["tasks"]["R1"]["scope"] == ["similar-methods"]
    assert graph["tasks"]["R2"]["mandatory"] is True
    assert graph["tasks"]["R2"]["scope"] == ["current-methods"]
    assert "B3" in graph["profiles"]["beginner"]["tasks"]
    for profile in ("graduate", "reviewer"):
        assert {"R1", "R2"} <= set(graph["profiles"][profile]["tasks"])


def test_task_graph_declares_closed_profiles_and_dependencies() -> None:
    graph = _graph()
    assert set(graph) == {"format_version", "scheduler", "tasks", "profiles"}
    assert graph["format_version"] == 1
    assert set(graph["profiles"]) == set(PROFILE_TASKS)
    for mode, expected in PROFILE_TASKS.items():
        profile = graph["profiles"][mode]
        assert set(profile) == {"tasks", "dependencies"}
        assert set(profile["tasks"]) == set(expected)
        assert set(profile["dependencies"]) == set(profile["tasks"])
    assert graph["profiles"]["beginner"]["dependencies"]["S0"] == ["B1", "B2", "B3"]
    assert graph["profiles"]["graduate"]["dependencies"]["S0"] == [
        "E1",
        "L1",
        "M1",
        "R1",
        "R2",
        "X1",
    ]
    assert graph["profiles"]["reviewer"]["dependencies"]["A1"] == [
        "C1",
        "E1",
        "L1",
        "M1",
        "R1",
        "R2",
        "X1",
    ]
    assert graph["profiles"]["reviewer"]["dependencies"]["S0"] == ["A1"]


def test_graph_assigns_exact_modes_mandatory_work_and_one_writer() -> None:
    tasks = _graph()["tasks"]
    assert set(tasks) == {
        "I0",
        "B1",
        "B2",
        "B3",
        "M1",
        "E1",
        "X1",
        "L1",
        "R1",
        "R2",
        "C1",
        "A1",
        "S0",
    }
    assert tasks["I0"]["mode"] == "paper-indexer"
    assert tasks["E1"]["mode"] == tasks["C1"]["mode"] == "paper-reasoning-worker"
    assert tasks["A1"]["mode"] == "explanation-evidence-auditor"
    assert tasks["S0"]["mode"] == "paper-explainer"
    assert {task_id for task_id, task in tasks.items() if task["mandatory"]} == {
        "I0",
        "B3",
        "R1",
        "R2",
        "A1",
        "S0",
    }
    assert [task_id for task_id, task in tasks.items() if task["writes_final_note"]] == ["S0"]
    for task_id, task in tasks.items():
        assert set(task) == {
            "role",
            "mode",
            "tier",
            "scope",
            "mandatory",
            "output",
            "writes_final_note",
            "budget",
        }
        if task_id != "S0":
            assert task["writes_final_note"] is False


def test_i0_graph_budget_is_exactly_the_dedicated_section_limit() -> None:
    assert _graph()["tasks"]["I0"]["budget"] == {"max_sections": 100}


@pytest.mark.parametrize(
    "mutation", ["cycle", "unknown-dependency", "unknown-mode", "second-writer"]
)
def test_graph_validation_rejects_unsafe_mutations(mutation: str) -> None:
    graph = copy.deepcopy(_graph())
    modes = _declared_modes() | {
        "paper-indexer",
        "paper-analysis-worker",
        "paper-reasoning-worker",
        "explanation-evidence-auditor",
    }
    if mutation == "cycle":
        graph["profiles"]["graduate"]["dependencies"]["M1"] = ["S0"]
    elif mutation == "unknown-dependency":
        graph["profiles"]["beginner"]["dependencies"]["B1"] = ["Z9"]
    elif mutation == "unknown-mode":
        graph["tasks"]["M1"]["mode"] = "undeclared-worker"
    else:
        graph["tasks"]["M1"]["writes_final_note"] = True
    with pytest.raises(ValueError):
        validate_paper_explanation_graph(graph, modes)


def test_paper_map_schema_accepts_grounded_map_and_rejects_extra_fields() -> None:
    schema = _schema("paper-map.schema.json")
    jsonschema.Draft202012Validator.check_schema(schema)
    valid = _paper_map()
    jsonschema.validate(valid, schema)
    invalid = valid | {"output_path": ".evidraft/notes/forbidden.md"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(invalid, schema)


@pytest.mark.parametrize(
    ("status", "retry_reason"),
    [("complete", None), ("partial", None), ("failed", "canonical source timed out")],
)
def test_analysis_packet_schema_validates_all_terminal_statuses(
    status: str, retry_reason: str | None
) -> None:
    schema = _schema("analysis-packet.schema.json")
    jsonschema.Draft202012Validator.check_schema(schema)
    packet = {
        "task_id": "M1",
        "attempt": 1,
        "status": status,
        "findings": [
            {
                "claim": "The method uses self-attention.",
                "evidence_refs": ["Paper section 3.2"],
                "confidence": "high",
                "label": "paper",
            }
        ],
        "uncertainties": [],
        "rejections": [],
        "retry_reason": retry_reason,
        "search_metadata": None,
        "external_works": [],
    }
    jsonschema.validate(packet, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(packet | {"output_path": "forbidden.md"}, schema)
    if status == "failed":
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(packet | {"retry_reason": ""}, schema)


def test_auditor_packet_has_no_blocking_control_surface() -> None:
    schema = _schema("analysis-packet.schema.json")
    assert "blocking" not in schema["properties"]
    severities = schema["$defs"]["finding"]["properties"]["severity"]["enum"]
    assert severities == ["info", "warning", "error"]


def test_external_packets_require_bounded_search_metadata() -> None:
    schema = _schema("analysis-packet.schema.json")
    packet = {
        "task_id": "R1",
        "attempt": 1,
        "status": "complete",
        "findings": [],
        "uncertainties": [],
        "rejections": [],
        "retry_reason": None,
        "search_metadata": {
            "queries": ["self-attention similar methods"],
            "providers": ["arxiv"],
            "cutoff": "2026-07-13",
            "opened_sources": [],
        },
        "external_works": [
            {
                "title": "A Verified Work",
                "authors": ["A. Author"],
                "year": 2025,
                "canonical_url": "https://arxiv.org/abs/2501.00001",
                "relationship": "similar method",
                "methodological_difference": "uses sparse attention",
                "evidence_scope": "abstract-only",
                "label": "external-citation",
            }
        ],
    }
    jsonschema.validate(packet, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            {key: value for key, value in packet.items() if key != "search_metadata"}, schema
        )


def test_external_failure_still_records_search_attempt() -> None:
    packet = _analysis_packet(task_id="R2", attempt=2, status="failed")
    packet["retry_reason"] = "provider timeout"
    packet["search_metadata"] = {
        "queries": ["source paper current methods"],
        "providers": ["OpenAlex"],
        "cutoff": "2026-07-21",
        "opened_sources": [],
    }
    packet["external_works"] = []
    _instance_validator()(BUNDLE, packet, expected_task_id="R2", expected_attempt=2)


@pytest.mark.parametrize("status", ["complete", "partial"])
def test_nonfailed_external_packet_still_requires_search_results(status: str) -> None:
    schema = _schema("analysis-packet.schema.json")
    packet = {
        "task_id": "R2",
        "attempt": 1,
        "status": status,
        "findings": [],
        "uncertainties": [],
        "rejections": [],
        "retry_reason": None,
    }

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(packet, schema)


def test_paper_map_schema_requires_all_indexer_analysis_fields() -> None:
    schema = _schema("paper-map.schema.json")
    required = {
        "research_question",
        "prerequisites",
        "contributions",
        "method_steps",
        "reproduction_gaps",
        "uncertainties",
    }
    assert required <= set(schema["required"])
    for field in required:
        invalid = copy.deepcopy(_paper_map())
        invalid.pop(field)
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(invalid, schema)


def test_runtime_validator_accepts_valid_paper_map_and_analysis_packet() -> None:
    validate = _instance_validator()

    assert validate(BUNDLE, _paper_map(), expected_task_id="I0", expected_attempt=1)[
        "task_id"
    ] == "I0"
    assert validate(
        BUNDLE, _analysis_packet(), expected_task_id="M1", expected_attempt=1
    )["task_id"] == "M1"


@pytest.mark.parametrize(
    ("packet", "task_id", "attempt", "message"),
    [
        (_analysis_packet(task_id="X1"), "M1", 1, "task_id"),
        (_analysis_packet(attempt=1), "M1", 2, "attempt"),
    ],
)
def test_runtime_validator_rejects_spoofed_task_or_stale_attempt(
    packet: dict, task_id: str, attempt: int, message: str
) -> None:
    validate = _instance_validator()

    with pytest.raises(ValueError, match=message):
        validate(BUNDLE, packet, expected_task_id=task_id, expected_attempt=attempt)


def test_runtime_validator_enforces_graph_finding_and_source_budgets() -> None:
    validate = _instance_validator()
    with pytest.raises(ValueError, match="max_findings"):
        validate(
            BUNDLE,
            _analysis_packet(findings=13),
            expected_task_id="M1",
            expected_attempt=1,
        )

    external = _analysis_packet(task_id="R1", findings=0)
    external["search_metadata"] = {
        "queries": ["verified query"],
        "providers": ["arxiv"],
        "cutoff": "2026-07-14",
        "opened_sources": [],
    }
    external["external_works"] = [
        {
            "title": f"Work {index}",
            "authors": ["A. Author"],
            "year": 2026,
            "canonical_url": f"https://example.test/work/{index}",
            "relationship": "similar",
            "methodological_difference": "different operator",
            "evidence_scope": "abstract-only",
            "label": "external-citation",
        }
        for index in range(6)
    ]
    with pytest.raises(ValueError, match="max_sources"):
        validate(BUNDLE, external, expected_task_id="R1", expected_attempt=1)


def test_runtime_validator_enforces_i0_section_budget() -> None:
    validate = _instance_validator()
    paper_map = _paper_map()
    paper_map["sections"] *= 101

    with pytest.raises(ValueError, match="max_sections"):
        validate(BUNDLE, paper_map, expected_task_id="I0", expected_attempt=1)


@pytest.mark.parametrize(
    "canonical_url",
    [
        "javascript://host",
        "ftp://example.test/paper",
        "https://",
        "https://example.test/has space",
    ],
)
def test_runtime_validator_rejects_non_http_or_malformed_canonical_url(
    canonical_url: str,
) -> None:
    validate = _instance_validator()
    invalid = _paper_map()
    invalid["source_identity"]["canonical_url"] = canonical_url

    with pytest.raises(jsonschema.ValidationError, match="uri"):
        validate(BUNDLE, invalid, expected_task_id="I0", expected_attempt=1)


def test_packet_validation_cli_reads_json_from_stdin(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(_analysis_packet())))

    assert cli_main(
        [
            "paper-explanation",
            "validate-return",
            "--bundle",
            str(BUNDLE),
            "--task-id",
            "M1",
            "--attempt",
            "1",
        ]
    ) == 0
    assert json.loads(capsys.readouterr().out) == {
        "attempt": 1,
        "task_id": "M1",
        "valid": True,
    }
