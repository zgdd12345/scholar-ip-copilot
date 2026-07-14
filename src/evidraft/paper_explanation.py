"""Validate the closed paper-explanation runtime bundle."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

import jsonschema
import yaml


PAPER_EXPLANATION_RESOURCES = (
    "task-graph.yaml",
    "paper-map.schema.json",
    "analysis-packet.schema.json",
)
EXPECTED_SCHEDULER = {
    "max_parallel": 4,
    "max_attempts": 2,
    "nested_delegation": "forbidden",
    "result_order": "task_id",
}
EXPECTED_TASKS = {
    "I0": {
        "role": "researcher",
        "mode": "paper-indexer",
        "tier": "standard",
        "scope": ["paper-index"],
        "mandatory": True,
        "output": "paper-map",
        "writes_final_note": False,
        "budget": {"max_sections": 100},
    },
    "B1": {
        "role": "researcher",
        "mode": "paper-analysis-worker",
        "tier": "standard",
        "scope": ["method", "intuitive-equations"],
        "mandatory": False,
        "output": "analysis-packet",
        "writes_final_note": False,
        "budget": {"max_sources": 0, "max_findings": 20},
    },
    "B2": {
        "role": "researcher",
        "mode": "paper-analysis-worker",
        "tier": "standard",
        "scope": ["experiments", "limitations"],
        "mandatory": False,
        "output": "analysis-packet",
        "writes_final_note": False,
        "budget": {"max_sources": 0, "max_findings": 20},
    },
    "B3": {
        "role": "researcher",
        "mode": "paper-analysis-worker",
        "tier": "standard",
        "scope": ["similar-methods", "frontier-methods"],
        "mandatory": True,
        "output": "analysis-packet",
        "writes_final_note": False,
        "budget": {"max_sources": 10, "max_findings": 20},
    },
    "M1": {
        "role": "researcher",
        "mode": "paper-analysis-worker",
        "tier": "standard",
        "scope": ["method"],
        "mandatory": False,
        "output": "analysis-packet",
        "writes_final_note": False,
        "budget": {"max_sources": 0, "max_findings": 12},
    },
    "E1": {
        "role": "researcher",
        "mode": "paper-reasoning-worker",
        "tier": "deep",
        "scope": ["equations"],
        "mandatory": False,
        "output": "analysis-packet",
        "writes_final_note": False,
        "budget": {"max_sources": 0, "max_findings": 12},
    },
    "X1": {
        "role": "researcher",
        "mode": "paper-analysis-worker",
        "tier": "standard",
        "scope": ["experiments"],
        "mandatory": False,
        "output": "analysis-packet",
        "writes_final_note": False,
        "budget": {"max_sources": 0, "max_findings": 12},
    },
    "L1": {
        "role": "researcher",
        "mode": "paper-analysis-worker",
        "tier": "standard",
        "scope": ["limitations"],
        "mandatory": False,
        "output": "analysis-packet",
        "writes_final_note": False,
        "budget": {"max_sources": 0, "max_findings": 12},
    },
    "R1": {
        "role": "researcher",
        "mode": "paper-analysis-worker",
        "tier": "standard",
        "scope": ["similar-methods"],
        "mandatory": True,
        "output": "analysis-packet",
        "writes_final_note": False,
        "budget": {"max_sources": 5, "max_findings": 12},
    },
    "R2": {
        "role": "researcher",
        "mode": "paper-analysis-worker",
        "tier": "standard",
        "scope": ["frontier-methods"],
        "mandatory": True,
        "output": "analysis-packet",
        "writes_final_note": False,
        "budget": {"max_sources": 5, "max_findings": 12},
    },
    "C1": {
        "role": "researcher",
        "mode": "paper-reasoning-worker",
        "tier": "deep",
        "scope": ["claim-boundaries"],
        "mandatory": False,
        "output": "analysis-packet",
        "writes_final_note": False,
        "budget": {"max_sources": 0, "max_findings": 12},
    },
    "A1": {
        "role": "evidence-reviewer",
        "mode": "explanation-evidence-auditor",
        "tier": "standard",
        "scope": ["cross-packet-audit"],
        "mandatory": True,
        "output": "analysis-packet",
        "writes_final_note": False,
        "budget": {"max_sources": 0, "max_findings": 20},
    },
    "S0": {
        "role": "researcher",
        "mode": "paper-explainer",
        "tier": "deep",
        "scope": ["synthesis"],
        "mandatory": True,
        "output": "reading-note",
        "writes_final_note": True,
        "budget": {"max_sources": 0, "max_findings": 100},
    },
}
EXPECTED_PROFILES = {
    "beginner": {
        "tasks": ["I0", "B1", "B2", "B3", "S0"],
        "dependencies": {
            "I0": [],
            "B1": ["I0"],
            "B2": ["I0"],
            "B3": ["I0"],
            "S0": ["B1", "B2", "B3"],
        },
    },
    "graduate": {
        "tasks": ["I0", "E1", "L1", "M1", "R1", "R2", "S0", "X1"],
        "dependencies": {
            "I0": [],
            "E1": ["I0"],
            "L1": ["I0"],
            "M1": ["I0"],
            "R1": ["I0"],
            "R2": ["I0"],
            "X1": ["I0"],
            "S0": ["E1", "L1", "M1", "R1", "R2", "X1"],
        },
    },
    "reviewer": {
        "tasks": ["I0", "A1", "C1", "E1", "L1", "M1", "R1", "R2", "S0", "X1"],
        "dependencies": {
            "I0": [],
            "C1": ["I0"],
            "E1": ["I0"],
            "L1": ["I0"],
            "M1": ["I0"],
            "R1": ["I0"],
            "R2": ["I0"],
            "X1": ["I0"],
            "A1": ["C1", "E1", "L1", "M1", "R1", "R2", "X1"],
            "S0": ["A1"],
        },
    },
}


def _runtime_format_checker() -> jsonschema.FormatChecker:
    checker = jsonschema.FormatChecker()

    def is_absolute_uri(value: object) -> bool:
        if not isinstance(value, str) or any(character.isspace() for character in value):
            return False
        parsed = urlsplit(value)
        return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)

    checker.checks("uri")(is_absolute_uri)
    return checker


def _assert_acyclic(profile_id: str, profile: dict[str, object]) -> None:
    dependencies = profile["dependencies"]
    if not isinstance(dependencies, dict):
        raise ValueError(f"invalid dependencies for profile {profile_id}")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise ValueError(f"dependency cycle in profile {profile_id}")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in dependencies.get(task_id, []):
            if dependency not in dependencies:
                raise ValueError(f"unknown dependency {dependency} in profile {profile_id}")
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in dependencies:
        visit(task_id)


def validate_paper_explanation_graph(graph: object, declared_modes: set[str]) -> dict[str, object]:
    """Validate the closed scheduler, task records, profiles, dependencies and writer."""
    if not isinstance(graph, dict) or set(graph) != {
        "format_version",
        "scheduler",
        "tasks",
        "profiles",
    }:
        raise ValueError("invalid paper-explanation graph keys")
    if graph["format_version"] != 1 or graph["scheduler"] != EXPECTED_SCHEDULER:
        raise ValueError("invalid paper-explanation scheduler")
    tasks = graph["tasks"]
    profiles = graph["profiles"]
    if tasks != EXPECTED_TASKS:
        raise ValueError("paper-explanation tasks do not match the approved contract")
    if profiles != EXPECTED_PROFILES:
        raise ValueError("paper-explanation profiles do not match the approved contract")
    if {task["mode"] for task in tasks.values()} - declared_modes:
        raise ValueError("paper-explanation graph references an undeclared role mode")
    writers = [task_id for task_id, task in tasks.items() if task["writes_final_note"]]
    if writers != ["S0"]:
        raise ValueError("paper-explanation graph must define S0 as its sole writer")
    for profile_id, profile in profiles.items():
        _assert_acyclic(profile_id, profile)
    return graph


def validate_paper_explanation_bundle(
    plugin_root: Path, declared_modes: set[str]
) -> dict[str, object]:
    """Load and validate the paper-explanation graph and both Draft 2020-12 schemas."""
    bundle = plugin_root / "capabilities/research/paper-explanation"
    paths = {name: bundle / name for name in PAPER_EXPLANATION_RESOURCES}
    for path in paths.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    for name in ("paper-map.schema.json", "analysis-packet.schema.json"):
        schema = json.loads(paths[name].read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
    graph = yaml.safe_load(paths["task-graph.yaml"].read_text(encoding="utf-8"))
    return validate_paper_explanation_graph(graph, declared_modes)


def validate_paper_explanation_instance(
    bundle: Path,
    instance: object,
    *,
    expected_task_id: str,
    expected_attempt: int,
) -> dict[str, object]:
    """Validate one worker return against its schema, identity, attempt, and graph budget."""
    bundle = Path(bundle)
    paths = {name: bundle / name for name in PAPER_EXPLANATION_RESOURCES}
    for path in paths.values():
        if not path.is_file():
            raise FileNotFoundError(path)

    graph = yaml.safe_load(paths["task-graph.yaml"].read_text(encoding="utf-8"))
    declared_modes = {str(task["mode"]) for task in EXPECTED_TASKS.values()}
    validate_paper_explanation_graph(graph, declared_modes)
    tasks = graph["tasks"]
    if expected_task_id not in tasks or expected_task_id == "S0":
        raise ValueError(f"task_id has no structured worker return: {expected_task_id}")
    if (
        isinstance(expected_attempt, bool)
        or not isinstance(expected_attempt, int)
        or not 1 <= expected_attempt <= EXPECTED_SCHEDULER["max_attempts"]
    ):
        raise ValueError(f"attempt is outside the graph contract: {expected_attempt}")

    schema_name = (
        "paper-map.schema.json"
        if tasks[expected_task_id]["output"] == "paper-map"
        else "analysis-packet.schema.json"
    )
    schema = json.loads(paths[schema_name].read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(
        schema, format_checker=_runtime_format_checker()
    ).validate(instance)
    if not isinstance(instance, dict):
        raise ValueError("worker return must be a JSON object")
    if instance.get("task_id") != expected_task_id:
        raise ValueError(
            f"task_id mismatch: expected {expected_task_id}, got {instance.get('task_id')}"
        )
    if instance.get("attempt") != expected_attempt:
        raise ValueError(
            f"attempt mismatch: expected {expected_attempt}, got {instance.get('attempt')}"
        )

    budget = tasks[expected_task_id]["budget"]
    if schema_name == "paper-map.schema.json":
        sections = instance.get("sections", [])
        if len(sections) > budget["max_sections"]:
            raise ValueError(
                f"max_sections exceeded for {expected_task_id}: "
                f"{len(sections)} > {budget['max_sections']}"
            )
    else:
        findings = instance.get("findings", [])
        external_works = instance.get("external_works", [])
        if len(findings) > budget["max_findings"]:
            raise ValueError(
                f"max_findings exceeded for {expected_task_id}: "
                f"{len(findings)} > {budget['max_findings']}"
            )
        if len(external_works) > budget["max_sources"]:
            raise ValueError(
                f"max_sources exceeded for {expected_task_id}: "
                f"{len(external_works)} > {budget['max_sources']}"
            )
    return instance
