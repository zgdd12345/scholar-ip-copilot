from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest
import yaml

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


def test_task_graph_declares_closed_scheduler_and_adaptive_profiles() -> None:
    graph = _graph()
    assert set(graph) == {"format_version", "scheduler", "tasks", "profiles"}
    assert graph["format_version"] == 1
    assert graph["scheduler"] == {
        "max_parallel": 4,
        "max_attempts": 2,
        "nested_delegation": "forbidden",
        "result_order": "task_id",
    }
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
    valid = {
        "task_id": "I0",
        "attempt": 1,
        "source_identity": {
            "title": "Attention Is All You Need",
            "authors": ["A. Author"],
            "year": 2017,
            "venue": "NeurIPS",
            "canonical_url": "https://arxiv.org/abs/1706.03762",
        },
        "full_text_ref": "papers/attention.pdf",
        "sections": [{"id": "3", "title": "Model Architecture", "locator": "Paper section 3"}],
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
        "claims": [{"text": "The model uses self-attention.", "locator": "Paper section 3"}],
        "assumptions": [],
        "limitations": [],
        "implementation_refs": [],
    }
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
