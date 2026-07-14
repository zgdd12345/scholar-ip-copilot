# Multi-Subagent Paper Explanation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the two-stream `research.explain` implementation with the approved adaptive, wave-scheduled multi-subagent workflow while preserving its public command and twelve-section note contract.

**Architecture:** A validated capability bundle declares one closed task graph plus PaperMap and AnalysisPacket schemas. The parent workflow coordinates identity, collision handling, bounded parallel dispatch, one fresh retry, deterministic status, and final synthesis; four read-only native worker modes return structured values, while the narrowed `paper-explainer` is the only mode that receives the output path or writes the note.

**Tech Stack:** Python 3.10+, YAML, JSON Schema Draft 2020-12, Markdown role/workflow specifications, PyYAML, jsonschema, pytest, Ruff, the shared EviDraft renderer and installer.

## Global Constraints

- Work only in `/Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.worktrees/paper-explanation` on branch `codex/paper-explanation`.
- Run Python commands with `PYTHONPATH=src:. /Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.venv/bin/python`; do not create or select another environment.
- Apply strict Red -> Green -> Refactor for every production, configuration, and behavior change; record the expected missing-behavior failure before implementation.
- Keep `workflow:research.explain <source> [--mode beginner|graduate|reviewer] [--out PATH]` and `.evidraft/notes/paper-explanations/<paper-slug>.md` unchanged.
- Keep mandatory external related-work research, all twelve note headings, evidence labels, collision behavior, projectless preflight, and routing through `$scholar-using` unchanged.
- Keep exactly 6 semantic roles and 26 capabilities; expand native role modes from 16 to 20.
- Preserve all 15 frozen v1 mode hashes, the 22-command migration fixture and digest, and legacy adapter-count fixtures byte-for-byte.
- Use `max_parallel: 4`, `max_attempts: 2`, `nested_delegation: forbidden`, lexical `task_id` dispatch order, and a fresh subagent for attempt two.
- A retry receives the same immutable input, scope, and budget as attempt one except for the incremented `attempt`.
- Worker modes never receive `out`, a resolved output path, collision state, or Write/Edit permission; only `paper-explainer` receives the collision-safe output path and writes the final note.
- Hosts without independent delegation report `incomplete: delegation unavailable`; they never execute a monolithic fallback.
- `complete` requires every enabled task complete and a non-blocking reviewer audit; `partial` requires all mandatory work complete with optional gaps; `incomplete` covers delegation absence, any non-complete mandatory task, required audit failure, or synthesis contract failure.
- `I0` failure writes no note. A mandatory external-research failure may write only a prominently marked incomplete source-analysis draft with failed IDs, both attempt reasons, missing sections, and recovery actions.
- Do not hand-edit ignored host outputs, marketplace metadata, or Codex configuration. Refresh them only through the existing renderer, installer, and plugin-creator scripts after tracked work is integrated.

---

### Task 1: Add the validated paper-explanation runtime bundle

**Files:**
- Create: `plugins/scholar-ip/capabilities/research/paper-explanation/task-graph.yaml`
- Create: `plugins/scholar-ip/capabilities/research/paper-explanation/paper-map.schema.json`
- Create: `plugins/scholar-ip/capabilities/research/paper-explanation/analysis-packet.schema.json`
- Create: `src/evidraft/paper_explanation.py`
- Create: `tests/test_paper_explanation_task_graph.py`
- Modify: `src/evidraft/install.py`
- Modify: `plugins/scholar-ip/capabilities/index.yaml`
- Modify: `tests/test_v2_capabilities.py`
- Modify: `tests/test_v2_renderer.py`
- Modify: `tests/test_v2_install.py`

**Interfaces:**
- Consumes: `plugin_root: pathlib.Path` and the declared role-mode set loaded by `evidraft.render`.
- Produces: `validate_paper_explanation_bundle(plugin_root: Path, declared_modes: set[str]) -> dict[str, object]`, which returns the validated graph or raises `FileNotFoundError`, `jsonschema.SchemaError`, `jsonschema.ValidationError`, or `ValueError` before renderer output is touched.
- Produces: one authoritative graph with task definitions and per-profile dependencies; one `PaperMap` schema for `I0`; one `AnalysisPacket` schema for all post-index workers and `A1`.

- [ ] **Step 1: Write the failing task-graph and schema tests**

Create `tests/test_paper_explanation_task_graph.py` with helpers that load the three bundle resources and these exact behavioral checks:

```python
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
        "E1", "L1", "M1", "R1", "R2", "X1"
    ]
    assert graph["profiles"]["reviewer"]["dependencies"]["A1"] == [
        "C1", "E1", "L1", "M1", "R1", "R2", "X1"
    ]
    assert graph["profiles"]["reviewer"]["dependencies"]["S0"] == ["A1"]


def test_graph_assigns_exact_modes_mandatory_work_and_one_writer() -> None:
    tasks = _graph()["tasks"]
    assert set(tasks) == {
        "I0", "B1", "B2", "B3", "M1", "E1", "X1", "L1", "R1", "R2", "C1", "A1", "S0"
    }
    assert tasks["I0"]["mode"] == "paper-indexer"
    assert tasks["E1"]["mode"] == tasks["C1"]["mode"] == "paper-reasoning-worker"
    assert tasks["A1"]["mode"] == "explanation-evidence-auditor"
    assert tasks["S0"]["mode"] == "paper-explainer"
    assert {task_id for task_id, task in tasks.items() if task["mandatory"]} == {
        "I0", "B3", "R1", "R2", "A1", "S0"
    }
    assert [task_id for task_id, task in tasks.items() if task["writes_final_note"]] == ["S0"]
    for task_id, task in tasks.items():
        assert set(task) == {
            "role", "mode", "tier", "scope", "mandatory", "output", "writes_final_note", "budget"
        }
        if task_id != "S0":
            assert task["writes_final_note"] is False


@pytest.mark.parametrize("mutation", ["cycle", "unknown-dependency", "unknown-mode", "second-writer"])
def test_graph_validation_rejects_unsafe_mutations(mutation: str) -> None:
    graph = copy.deepcopy(_graph())
    modes = _declared_modes() | {
        "paper-indexer", "paper-analysis-worker", "paper-reasoning-worker",
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
        "task_id": "I0", "attempt": 1,
        "source_identity": {"title": "Attention Is All You Need", "authors": ["A. Author"], "year": 2017, "venue": "NeurIPS", "canonical_url": "https://arxiv.org/abs/1706.03762"},
        "full_text_ref": "papers/attention.pdf",
        "sections": [{"id": "3", "title": "Model Architecture", "locator": "Paper section 3"}],
        "equations": [{"id": "1", "locator": "Equation 1", "symbols": [{"symbol": "Q", "definition": "queries"}]}],
        "figures": [], "tables": [],
        "experiments": {"datasets": [], "baselines": [], "metrics": [], "ablations": [], "result_locators": []},
        "claims": [{"text": "The model uses self-attention.", "locator": "Paper section 3"}],
        "assumptions": [], "limitations": [], "implementation_refs": [],
    }
    jsonschema.validate(valid, schema)
    invalid = valid | {"output_path": ".evidraft/notes/forbidden.md"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(invalid, schema)


@pytest.mark.parametrize(
    ("status", "retry_reason"),
    [("complete", None), ("partial", None), ("failed", "canonical source timed out")],
)
def test_analysis_packet_schema_validates_all_terminal_statuses(status: str, retry_reason: str | None) -> None:
    schema = _schema("analysis-packet.schema.json")
    jsonschema.Draft202012Validator.check_schema(schema)
    packet = {
        "task_id": "M1", "attempt": 1, "status": status,
        "findings": [{"claim": "The method uses self-attention.", "evidence_refs": ["Paper section 3.2"], "confidence": "high", "label": "paper"}],
        "uncertainties": [], "rejections": [], "retry_reason": retry_reason,
        "search_metadata": None, "external_works": [],
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
        "task_id": "R1", "attempt": 1, "status": "complete", "findings": [],
        "uncertainties": [], "rejections": [], "retry_reason": None,
        "search_metadata": {"queries": ["self-attention similar methods"], "providers": ["arxiv"], "cutoff": "2026-07-13"},
        "external_works": [{"title": "A Verified Work", "authors": ["A. Author"], "year": 2025, "canonical_url": "https://arxiv.org/abs/2501.00001", "relationship": "similar method", "methodological_difference": "uses sparse attention", "evidence_scope": "abstract-only", "label": "external-citation"}],
    }
    jsonschema.validate(packet, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({key: value for key, value in packet.items() if key != "search_metadata"}, schema)
```

- [ ] **Step 2: Run the focused test and verify Red**

Run:

```bash
PYTHONPATH=src:. /Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.venv/bin/python \
  -m pytest tests/test_paper_explanation_task_graph.py -q
```

Expected: collection fails because `evidraft.paper_explanation` and the three runtime resources do not exist. This is the missing contract, not an environment or fixture failure.

- [ ] **Step 3: Add the exact task graph**

Create `task-graph.yaml` with the scheduler above and these task records. All records use exactly the eight keys asserted by Step 1:

```yaml
format_version: 1
scheduler: {max_parallel: 4, max_attempts: 2, nested_delegation: forbidden, result_order: task_id}
tasks:
  I0: {role: researcher, mode: paper-indexer, tier: standard, scope: [paper-index], mandatory: true, output: paper-map, writes_final_note: false, budget: {max_sources: 0, max_findings: 100}}
  B1: {role: researcher, mode: paper-analysis-worker, tier: standard, scope: [method, intuitive-equations], mandatory: false, output: analysis-packet, writes_final_note: false, budget: {max_sources: 0, max_findings: 20}}
  B2: {role: researcher, mode: paper-analysis-worker, tier: standard, scope: [experiments, limitations], mandatory: false, output: analysis-packet, writes_final_note: false, budget: {max_sources: 0, max_findings: 20}}
  B3: {role: researcher, mode: paper-analysis-worker, tier: standard, scope: [similar-methods, frontier-methods], mandatory: true, output: analysis-packet, writes_final_note: false, budget: {max_sources: 10, max_findings: 20}}
  M1: {role: researcher, mode: paper-analysis-worker, tier: standard, scope: [method], mandatory: false, output: analysis-packet, writes_final_note: false, budget: {max_sources: 0, max_findings: 12}}
  E1: {role: researcher, mode: paper-reasoning-worker, tier: deep, scope: [equations], mandatory: false, output: analysis-packet, writes_final_note: false, budget: {max_sources: 0, max_findings: 12}}
  X1: {role: researcher, mode: paper-analysis-worker, tier: standard, scope: [experiments], mandatory: false, output: analysis-packet, writes_final_note: false, budget: {max_sources: 0, max_findings: 12}}
  L1: {role: researcher, mode: paper-analysis-worker, tier: standard, scope: [limitations], mandatory: false, output: analysis-packet, writes_final_note: false, budget: {max_sources: 0, max_findings: 12}}
  R1: {role: researcher, mode: paper-analysis-worker, tier: standard, scope: [similar-methods], mandatory: true, output: analysis-packet, writes_final_note: false, budget: {max_sources: 5, max_findings: 12}}
  R2: {role: researcher, mode: paper-analysis-worker, tier: standard, scope: [frontier-methods], mandatory: true, output: analysis-packet, writes_final_note: false, budget: {max_sources: 5, max_findings: 12}}
  C1: {role: researcher, mode: paper-reasoning-worker, tier: deep, scope: [claim-boundaries], mandatory: false, output: analysis-packet, writes_final_note: false, budget: {max_sources: 0, max_findings: 12}}
  A1: {role: evidence-reviewer, mode: explanation-evidence-auditor, tier: standard, scope: [cross-packet-audit], mandatory: true, output: analysis-packet, writes_final_note: false, budget: {max_sources: 0, max_findings: 20}}
  S0: {role: researcher, mode: paper-explainer, tier: deep, scope: [synthesis], mandatory: true, output: reading-note, writes_final_note: true, budget: {max_sources: 0, max_findings: 100}}
profiles:
  beginner:
    tasks: [I0, B1, B2, B3, S0]
    dependencies: {I0: [], B1: [I0], B2: [I0], B3: [I0], S0: [B1, B2, B3]}
  graduate:
    tasks: [I0, E1, L1, M1, R1, R2, S0, X1]
    dependencies: {I0: [], E1: [I0], L1: [I0], M1: [I0], R1: [I0], R2: [I0], X1: [I0], S0: [E1, L1, M1, R1, R2, X1]}
  reviewer:
    tasks: [I0, A1, C1, E1, L1, M1, R1, R2, S0, X1]
    dependencies: {I0: [], C1: [I0], E1: [I0], L1: [I0], M1: [I0], R1: [I0], R2: [I0], X1: [I0], A1: [C1, E1, L1, M1, R1, R2, X1], S0: [A1]}
```

- [ ] **Step 4: Add the two closed JSON Schemas**

Create both schemas as Draft 2020-12 documents with `additionalProperties: false` at every object boundary. `paper-map.schema.json` requires exactly the top-level fields used by the valid fixture. Use these closed definitions:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://scholar-ip-copilot/schemas/paper-map.schema.json",
  "type": "object",
  "additionalProperties": false,
  "required": ["task_id", "attempt", "source_identity", "full_text_ref", "sections", "equations", "figures", "tables", "experiments", "claims", "assumptions", "limitations", "implementation_refs"],
  "properties": {
    "task_id": {"const": "I0"},
    "attempt": {"type": "integer", "minimum": 1, "maximum": 2},
    "source_identity": {"$ref": "#/$defs/sourceIdentity"},
    "full_text_ref": {"type": "string", "minLength": 1},
    "sections": {"type": "array", "minItems": 1, "items": {"$ref": "#/$defs/locatedSection"}},
    "equations": {"type": "array", "items": {"$ref": "#/$defs/equation"}},
    "figures": {"type": "array", "items": {"$ref": "#/$defs/locatedItem"}},
    "tables": {"type": "array", "items": {"$ref": "#/$defs/locatedItem"}},
    "experiments": {"$ref": "#/$defs/experiments"},
    "claims": {"type": "array", "items": {"$ref": "#/$defs/statement"}},
    "assumptions": {"type": "array", "items": {"$ref": "#/$defs/statement"}},
    "limitations": {"type": "array", "items": {"$ref": "#/$defs/statement"}},
    "implementation_refs": {"type": "array", "items": {"$ref": "#/$defs/locatedItem"}}
  },
  "$defs": {
    "sourceIdentity": {"type": "object", "additionalProperties": false, "required": ["title", "authors", "year", "venue", "canonical_url"], "properties": {"title": {"type": "string", "minLength": 1}, "authors": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}}, "year": {"type": "integer", "minimum": 1000, "maximum": 3000}, "venue": {"type": "string", "minLength": 1}, "canonical_url": {"type": "string", "format": "uri"}}},
    "locatedSection": {"type": "object", "additionalProperties": false, "required": ["id", "title", "locator"], "properties": {"id": {"type": "string", "minLength": 1}, "title": {"type": "string", "minLength": 1}, "locator": {"type": "string", "minLength": 1}}},
    "locatedItem": {"type": "object", "additionalProperties": false, "required": ["id", "locator"], "properties": {"id": {"type": "string", "minLength": 1}, "locator": {"type": "string", "minLength": 1}}},
    "statement": {"type": "object", "additionalProperties": false, "required": ["text", "locator"], "properties": {"text": {"type": "string", "minLength": 1}, "locator": {"type": "string", "minLength": 1}}},
    "symbol": {"type": "object", "additionalProperties": false, "required": ["symbol", "definition"], "properties": {"symbol": {"type": "string", "minLength": 1}, "definition": {"type": "string", "minLength": 1}}},
    "equation": {"type": "object", "additionalProperties": false, "required": ["id", "locator", "symbols"], "properties": {"id": {"type": "string", "minLength": 1}, "locator": {"type": "string", "minLength": 1}, "symbols": {"type": "array", "items": {"$ref": "#/$defs/symbol"}}}},
    "stringList": {"type": "array", "items": {"type": "string", "minLength": 1}},
    "experiments": {"type": "object", "additionalProperties": false, "required": ["datasets", "baselines", "metrics", "ablations", "result_locators"], "properties": {"datasets": {"$ref": "#/$defs/stringList"}, "baselines": {"$ref": "#/$defs/stringList"}, "metrics": {"$ref": "#/$defs/stringList"}, "ablations": {"$ref": "#/$defs/stringList"}, "result_locators": {"$ref": "#/$defs/stringList"}}}
  }
}
```

`analysis-packet.schema.json` keeps the approved seven required top-level fields: `task_id`, `attempt`, `status`, `findings`, `uncertainties`, `rejections`, and `retry_reason`. A failed packet requires a non-empty retry reason; complete and partial packets require `null`. The schema permits closed `search_metadata` and `external_works` fields and conditionally requires them for B3/R1/R2; non-external tasks may return `search_metadata: null` and an empty `external_works`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://scholar-ip-copilot/schemas/analysis-packet.schema.json",
  "type": "object",
  "additionalProperties": false,
  "required": ["task_id", "attempt", "status", "findings", "uncertainties", "rejections", "retry_reason"],
  "properties": {
    "task_id": {"type": "string", "pattern": "^[A-Z][0-9]$"},
    "attempt": {"type": "integer", "minimum": 1, "maximum": 2},
    "status": {"enum": ["complete", "partial", "failed"]},
    "findings": {"type": "array", "items": {"$ref": "#/$defs/finding"}},
    "uncertainties": {"type": "array", "items": {"type": "string", "minLength": 1}},
    "rejections": {"type": "array", "items": {"$ref": "#/$defs/rejection"}},
    "retry_reason": {"type": ["string", "null"]},
    "search_metadata": {"oneOf": [{"type": "null"}, {"$ref": "#/$defs/searchMetadata"}]},
    "external_works": {"type": "array", "items": {"$ref": "#/$defs/externalWork"}}
  },
  "allOf": [
    {"if": {"properties": {"status": {"const": "failed"}}, "required": ["status"]}, "then": {"properties": {"retry_reason": {"type": "string", "minLength": 1}}}, "else": {"properties": {"retry_reason": {"type": "null"}}}},
    {"if": {"properties": {"task_id": {"enum": ["B3", "R1", "R2"]}}, "required": ["task_id"]}, "then": {"required": ["search_metadata", "external_works"], "properties": {"search_metadata": {"$ref": "#/$defs/searchMetadata"}}}}
  ],
  "$defs": {
    "finding": {"type": "object", "additionalProperties": false, "required": ["claim", "evidence_refs", "confidence", "label"], "properties": {"claim": {"type": "string", "minLength": 1}, "evidence_refs": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}}, "confidence": {"enum": ["high", "medium", "low"]}, "label": {"enum": ["paper", "external-citation", "external-official-code", "interpretation", "audit"]}}},
    "rejection": {"type": "object", "additionalProperties": false, "required": ["candidate", "reason"], "properties": {"candidate": {"type": "string", "minLength": 1}, "reason": {"type": "string", "minLength": 1}}},
    "searchMetadata": {"type": "object", "additionalProperties": false, "required": ["queries", "providers", "cutoff"], "properties": {"queries": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}}, "providers": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}}, "cutoff": {"type": "string", "format": "date"}}},
    "externalWork": {"type": "object", "additionalProperties": false, "required": ["title", "authors", "year", "canonical_url", "relationship", "methodological_difference", "evidence_scope", "label"], "properties": {"title": {"type": "string", "minLength": 1}, "authors": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}}, "year": {"type": "integer", "minimum": 1000, "maximum": 3000}, "canonical_url": {"type": "string", "format": "uri"}, "relationship": {"type": "string", "minLength": 1}, "methodological_difference": {"type": "string", "minLength": 1}, "evidence_scope": {"enum": ["full-text", "abstract-only", "official-project"]}, "label": {"enum": ["external-citation", "external-official-code"]}}}
  }
}
```

- [ ] **Step 5: Implement the closed graph and bundle validators**

In `src/evidraft/paper_explanation.py`, implement these public functions and constants:

```python
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import yaml


PAPER_EXPLANATION_RESOURCES = (
    "task-graph.yaml", "paper-map.schema.json", "analysis-packet.schema.json"
)
EXPECTED_SCHEDULER = {
    "max_parallel": 4, "max_attempts": 2,
    "nested_delegation": "forbidden", "result_order": "task_id",
}
EXPECTED_TASKS = {
    "I0": {"role": "researcher", "mode": "paper-indexer", "tier": "standard", "scope": ["paper-index"], "mandatory": True, "output": "paper-map", "writes_final_note": False, "budget": {"max_sources": 0, "max_findings": 100}},
    "B1": {"role": "researcher", "mode": "paper-analysis-worker", "tier": "standard", "scope": ["method", "intuitive-equations"], "mandatory": False, "output": "analysis-packet", "writes_final_note": False, "budget": {"max_sources": 0, "max_findings": 20}},
    "B2": {"role": "researcher", "mode": "paper-analysis-worker", "tier": "standard", "scope": ["experiments", "limitations"], "mandatory": False, "output": "analysis-packet", "writes_final_note": False, "budget": {"max_sources": 0, "max_findings": 20}},
    "B3": {"role": "researcher", "mode": "paper-analysis-worker", "tier": "standard", "scope": ["similar-methods", "frontier-methods"], "mandatory": True, "output": "analysis-packet", "writes_final_note": False, "budget": {"max_sources": 10, "max_findings": 20}},
    "M1": {"role": "researcher", "mode": "paper-analysis-worker", "tier": "standard", "scope": ["method"], "mandatory": False, "output": "analysis-packet", "writes_final_note": False, "budget": {"max_sources": 0, "max_findings": 12}},
    "E1": {"role": "researcher", "mode": "paper-reasoning-worker", "tier": "deep", "scope": ["equations"], "mandatory": False, "output": "analysis-packet", "writes_final_note": False, "budget": {"max_sources": 0, "max_findings": 12}},
    "X1": {"role": "researcher", "mode": "paper-analysis-worker", "tier": "standard", "scope": ["experiments"], "mandatory": False, "output": "analysis-packet", "writes_final_note": False, "budget": {"max_sources": 0, "max_findings": 12}},
    "L1": {"role": "researcher", "mode": "paper-analysis-worker", "tier": "standard", "scope": ["limitations"], "mandatory": False, "output": "analysis-packet", "writes_final_note": False, "budget": {"max_sources": 0, "max_findings": 12}},
    "R1": {"role": "researcher", "mode": "paper-analysis-worker", "tier": "standard", "scope": ["similar-methods"], "mandatory": True, "output": "analysis-packet", "writes_final_note": False, "budget": {"max_sources": 5, "max_findings": 12}},
    "R2": {"role": "researcher", "mode": "paper-analysis-worker", "tier": "standard", "scope": ["frontier-methods"], "mandatory": True, "output": "analysis-packet", "writes_final_note": False, "budget": {"max_sources": 5, "max_findings": 12}},
    "C1": {"role": "researcher", "mode": "paper-reasoning-worker", "tier": "deep", "scope": ["claim-boundaries"], "mandatory": False, "output": "analysis-packet", "writes_final_note": False, "budget": {"max_sources": 0, "max_findings": 12}},
    "A1": {"role": "evidence-reviewer", "mode": "explanation-evidence-auditor", "tier": "standard", "scope": ["cross-packet-audit"], "mandatory": True, "output": "analysis-packet", "writes_final_note": False, "budget": {"max_sources": 0, "max_findings": 20}},
    "S0": {"role": "researcher", "mode": "paper-explainer", "tier": "deep", "scope": ["synthesis"], "mandatory": True, "output": "reading-note", "writes_final_note": True, "budget": {"max_sources": 0, "max_findings": 100}},
}
EXPECTED_PROFILES = {
    "beginner": {"tasks": ["I0", "B1", "B2", "B3", "S0"], "dependencies": {"I0": [], "B1": ["I0"], "B2": ["I0"], "B3": ["I0"], "S0": ["B1", "B2", "B3"]}},
    "graduate": {"tasks": ["I0", "E1", "L1", "M1", "R1", "R2", "S0", "X1"], "dependencies": {"I0": [], "E1": ["I0"], "L1": ["I0"], "M1": ["I0"], "R1": ["I0"], "R2": ["I0"], "X1": ["I0"], "S0": ["E1", "L1", "M1", "R1", "R2", "X1"]}},
    "reviewer": {"tasks": ["I0", "A1", "C1", "E1", "L1", "M1", "R1", "R2", "S0", "X1"], "dependencies": {"I0": [], "C1": ["I0"], "E1": ["I0"], "L1": ["I0"], "M1": ["I0"], "R1": ["I0"], "R2": ["I0"], "X1": ["I0"], "A1": ["C1", "E1", "L1", "M1", "R1", "R2", "X1"], "S0": ["A1"]}},
}


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

def validate_paper_explanation_graph(
    graph: object, declared_modes: set[str]
) -> dict[str, object]:
    """Validate the closed scheduler, task records, profiles, dependencies and writer."""
    if not isinstance(graph, dict) or set(graph) != {
        "format_version", "scheduler", "tasks", "profiles"
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
```

`validate_paper_explanation_graph` must enforce the exact top-level and nested keys asserted in Step 1; exact scheduler values; exact three profiles and task sets; every task's exact role, mode, tier, scope, mandatory flag, output type, writer flag, and budget from Step 3; known role modes; one writer `S0`; dependency membership; no self-dependency; and acyclicity by visiting each enabled profile graph. `validate_paper_explanation_bundle` must require all three files, call `Draft202012Validator.check_schema` for both schemas, and return the validated graph. Do not add a fourth task-graph schema file. Task 2 connects this validator to renderer preflight after the four referenced role modes exist, so Task 1 remains independently Green.

- [ ] **Step 6: Add renderer and installer regression tests, verify their Red, then implement**

Extend `tests/test_v2_renderer.py` so `test_render_copies_native_paper_explanation_resources` checks byte equality for `spec.md`, the graph, and both schemas on every host. The five native mode copy assertions and fail-closed graph mutation test belong to Task 2, when those modes are registered.

Extend `tests/test_v2_install.py::test_sync_upgrades_exact_v1_entries_and_preserves_user_skills` to assert the installed private bundle contains the graph and both schemas. Add each file to `src/evidraft/install.py::_validate_source.required` so an incomplete rendered source is rejected before the destination changes.

Run before the installer change:

```bash
PYTHONPATH=src:. /Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.venv/bin/python \
  -m pytest tests/test_v2_renderer.py -k 'paper_explanation or task_graph' \
  tests/test_v2_install.py::test_sync_upgrades_exact_v1_entries_and_preserves_user_skills -q
```

Expected: renderer copy and installed-resource checks fail because the bundle resources are absent.

- [ ] **Step 7: Refresh the capability digest, verify Green, and commit**

Compute the digest only after all four files in the capability bundle are final:

```bash
PYTHONPATH=src:. /Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.venv/bin/python -c \
  'from pathlib import Path; import hashlib; root=Path("plugins/scholar-ip/capabilities/research/paper-explanation"); d=hashlib.sha256(); [(d.update(p.relative_to(root).as_posix().encode()), d.update(b"\0"), d.update(p.read_bytes()), d.update(b"\0")) for p in sorted(x for x in root.rglob("*") if x.is_file())]; print(d.hexdigest())'
```

Replace only `paper-explanation.bundle_sha256` in `plugins/scholar-ip/capabilities/index.yaml`. Then run:

```bash
PYTHONPATH=src:. /Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.venv/bin/python \
  -m pytest tests/test_paper_explanation_task_graph.py tests/test_v2_capabilities.py \
  tests/test_v2_renderer.py tests/test_v2_install.py -q
```

Expected: zero failures.

```bash
git add src/evidraft/paper_explanation.py src/evidraft/install.py \
  plugins/scholar-ip/capabilities/research/paper-explanation \
  plugins/scholar-ip/capabilities/index.yaml tests/test_paper_explanation_task_graph.py \
  tests/test_v2_capabilities.py tests/test_v2_renderer.py tests/test_v2_install.py
git commit -m "feat(research): add validated explanation task graph"
```

---

### Task 2: Add read-only worker modes and narrow the synthesizer

**Files:**
- Create: `plugins/scholar-ip/roles/modes/paper-indexer.md`
- Create: `plugins/scholar-ip/roles/modes/paper-analysis-worker.md`
- Create: `plugins/scholar-ip/roles/modes/paper-reasoning-worker.md`
- Create: `plugins/scholar-ip/roles/modes/explanation-evidence-auditor.md`
- Modify: `plugins/scholar-ip/roles/modes/paper-explainer.md`
- Modify: `plugins/scholar-ip/roles/roles.yaml`
- Modify: `src/evidraft/render.py`
- Modify: `tests/test_v2_role_modes.py`
- Modify: `tests/test_v2_workflow_source.py`
- Modify: `tests/test_v2_renderer.py`

**Interfaces:**
- Consumes: validated `IndexerInput` or `WorkerInput` selected from `task-graph.yaml`.
- Produces: `PaperMap` from `paper-indexer`; `AnalysisPacket` from analysis, reasoning, and audit modes; exactly one twelve-section Markdown note from `paper-explainer`.
- Preserves: the frozen `EXPECTED` and `MODE_SPEC_SHA256` dictionaries in `tests/test_v2_role_modes.py`.

- [ ] **Step 1: Write failing role registration and permission tests**

Extend `NATIVE_EXPECTED` in `tests/test_v2_role_modes.py` with the five native modes and their exact role/tier/tool contracts:

```python
NATIVE_EXPECTED = {
    "paper-indexer": ("researcher", "standard", 5, 7, 6, 3),
    "paper-analysis-worker": ("researcher", "standard", 6, 8, 7, 5),
    "paper-reasoning-worker": ("researcher", "deep", 5, 8, 7, 3),
    "explanation-evidence-auditor": ("evidence-reviewer", "standard", 6, 8, 7, 4),
    "paper-explainer": ("researcher", "deep", 6, 8, 7, 5),
}
```

Rename `test_roles_map_exactly_sixteen_unique_modes_to_private_specs` to `test_roles_map_exactly_twenty_unique_modes_to_private_specs`. Add:

```python
def test_paper_explanation_workers_are_read_only_and_synthesizer_is_sole_writer() -> None:
    worker_modes = {
        "paper-indexer", "paper-analysis-worker", "paper-reasoning-worker",
        "explanation-evidence-auditor",
    }
    for mode in worker_modes:
        metadata, body = _frontmatter(ROLES_ROOT / "modes" / f"{mode}.md")
        assert "Write" not in metadata["allowed_tools"]
        assert "Edit" not in metadata["allowed_tools"]
        assert "never accept or infer an output path or collision state" in body.lower()
        assert "nested subagent" in body.lower()
        assert "return" in body.lower()
    metadata, body = _frontmatter(ROLES_ROOT / "modes/paper-explainer.md")
    assert metadata["allowed_tools"] == ["Read", "Glob", "Grep", "Write", "Edit"]
    assert "sole" in body.lower()
    assert "canonical task order" in body.lower()
```

Add the four modes to `MODE_ASSIGNMENTS` in `tests/test_v2_workflow_source.py`, and change its exact declared-mode count from 16 to 20.

- [ ] **Step 2: Run focused tests and verify Red**

```bash
PYTHONPATH=src:. /Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.venv/bin/python \
  -m pytest tests/test_v2_role_modes.py \
  tests/test_v2_workflow_source.py::test_actions_reference_only_declared_roles_policies_and_tiers -q
```

Expected: missing mode specs/registrations, 16-versus-20 count mismatch, and the broad `paper-explainer` permission/ownership assertions fail.

- [ ] **Step 3: Register the four worker modes**

In `roles.yaml`, add standard mode specs for `paper-indexer`, `paper-analysis-worker`, and `explanation-evidence-auditor`; add deep mode spec for `paper-reasoning-worker`. Add the first three researcher modes except `explanation-evidence-auditor`, which belongs to `evidence-reviewer`. Keep six semantic roles.

Each new mode file must use YAML frontmatter with the exact `id`, allowed tools, responsibilities/constraints/checklist counts from Step 1, references to `paper-explanation/spec.md`, `task-graph.yaml`, and its output schema, plus policies `[workspace-safety, evidence-integrity]`. Use these tool lists:

```yaml
paper-indexer: [Read, Glob, Grep]
paper-analysis-worker: [Read, Glob, Grep, WebSearch, WebFetch]
paper-reasoning-worker: [Read, Glob, Grep]
explanation-evidence-auditor: [Read, Glob, Grep, WebFetch]
```

Every mode body must contain `## Inputs you read`, `## Outputs you return`, `## Execution protocol`, and `## Failure modes you avoid`. `paper-indexer` must explicitly accept only `task_id`, `attempt`, `explanation_mode`, `source_identity`, `full_text_ref`, and `budget`; it must not accept `PaperMap`, `dependency_packets`, `task_scope`, output path, or collision state. Every post-index worker must explicitly state all of the following:

```text
- Accept exactly one task_id, attempt, closed task_scope, explanation_mode, immutable PaperMap, full_text_ref, dependency_packets, and budget.
- Never accept or infer an output path or collision state.
- Never create or modify a file.
- Never dispatch a nested subagent.
- Return exactly one schema-valid packet and preserve uncertainty instead of inventing evidence.
```

Add mode-specific behavior: indexer returns the source map; analysis handles only its declared method/experiment/limitation/external scope; reasoning separates paper statements from interpretation; auditor resolves locators, conflicts, abstract-only scope, canonical links, and required coverage.

- [ ] **Step 4: Narrow `paper-explainer` to synthesis only**

Set `allowed_tools` to `[Read, Glob, Grep, Write, Edit]`. Its inputs are only selected mode, final collision-safe path, validated PaperMap, validated packets in canonical task order, retry history, failed IDs, optional audit packet, and calculated final status. It must not perform source mapping, specialist analysis, web retrieval, packet repair, retry, or nested delegation.

Its synthesis protocol must enforce all twelve existing headings and evidence labels, the spec's conflict rules, explicit complete/partial/incomplete banners and recovery metadata, no note after `I0` failure, and one final write. Use exactly six responsibilities, eight constraints, and seven checklist items so the native contract remains testable without freezing its hash.

- [ ] **Step 5: Expand renderer validation to 20 modes and stabilize tool tests**

Change the renderer's closed mode count and error message from 16 to 20. Import and call `validate_paper_explanation_bundle(plugin_root, declared_modes)` immediately after the renderer constructs `declared_modes` and before any output is touched.

Extend `tests/test_v2_renderer.py` so the native-resource test also checks all five native mode files. Add a parameterized fail-closed test that copies the plugin, mutates the graph to create a cycle, unknown dependency, unknown mode, or second writer, calls `render_plugin`, and asserts `ValueError` plus `not out.exists()`.

Mutate `paper-explainer` frontmatter structurally through `yaml.safe_load` rather than relying on the old seven-tool string, then assert forbidden globs are filtered and a scalar `allowed_tools` is rejected. Preserve the assertion that Claude's rendered researcher agent tool union contains WebSearch/WebFetch, while worker mode specs themselves remain read-only.

- [ ] **Step 6: Verify Green and commit**

```bash
PYTHONPATH=src:. /Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.venv/bin/python \
  -m pytest tests/test_v2_role_modes.py tests/test_v2_workflow_source.py \
  tests/test_v2_renderer.py tests/test_paper_explanation_task_graph.py -q
```

Expected: zero failures and all 15 frozen role hashes unchanged.

```bash
git add plugins/scholar-ip/roles src/evidraft/render.py \
  tests/test_v2_role_modes.py tests/test_v2_workflow_source.py tests/test_v2_renderer.py
git commit -m "feat(research): add explanation worker modes"
```

---

### Task 3: Replace the two-stream stage with adaptive wave scheduling

**Files:**
- Modify: `plugins/scholar-ip/workflows/research/workflow.yaml`
- Modify: `plugins/scholar-ip/workflows/research/stages/explain.md`
- Modify: `plugins/scholar-ip/capabilities/research/paper-explanation/spec.md`
- Modify: `plugins/scholar-ip/capabilities/index.yaml`
- Modify: `tests/test_v2_workflow_source.py`
- Modify: `tests/test_v2_capabilities.py`
- Test: `tests/test_paper_explanation_routing.py`
- Test: `tests/test_v2_contract_mapping.py`

**Interfaces:**
- Consumes: the validated bundle and five native role modes from Tasks 1-2.
- Produces: one parent-coordinated, adaptive invocation plan for beginner, graduate, or reviewer mode, including retry history and deterministic status.
- Preserves: source identity, output collision, preflight, twelve headings, routing, public action inputs/output, and external verification targets.

- [ ] **Step 1: Write failing workflow projection and scheduler tests**

Change the exact action assertion to:

```python
assert action["roles"] == [
    {"id": "researcher", "mode": "paper-indexer", "tier": "standard"},
    {"id": "researcher", "mode": "paper-analysis-worker", "tier": "standard"},
    {"id": "researcher", "mode": "paper-reasoning-worker", "tier": "deep"},
    {"id": "evidence-reviewer", "mode": "explanation-evidence-auditor", "tier": "standard"},
    {"id": "researcher", "mode": "paper-explainer", "tier": "deep"},
]
```

Replace the obsolete two-stream/literature-reviewer contract test with three tests:

```python
def test_research_explain_stage_declares_adaptive_graph_scheduler() -> None:
    stage = (WORKFLOW_ROOT / "research/stages/explain.md").read_text(encoding="utf-8")
    normalized = " ".join(stage.split())
    for token in (
        "task-graph.yaml", "paper-map.schema.json", "analysis-packet.schema.json",
        "max_parallel: 4", "max_attempts: 2", "lexical `task_id` order",
        "beginner", "B1", "B2", "B3", "graduate", "M1", "E1", "X1", "L1", "R1", "R2",
        "reviewer", "C1", "A1", "S0",
    ):
        assert token in stage
    assert "two bounded work streams" not in normalized
    assert "literature-reviewer" not in stage


def test_research_explain_retry_and_status_contract_is_deterministic() -> None:
    normalized = " ".join((WORKFLOW_ROOT / "research/stages/explain.md").read_text().split())
    for token in (
        "fresh subagent", "except `attempt`", "complete", "partial", "incomplete",
        "mandatory task", "both attempt reasons", "missing sections", "recovery actions",
        "I0", "writes no note",
    ):
        assert token in normalized


def test_research_explain_refuses_monolithic_fallback_and_keeps_one_writer() -> None:
    normalized = " ".join((WORKFLOW_ROOT / "research/stages/explain.md").read_text().split())
    assert "incomplete: delegation unavailable" in normalized
    assert "must not run a monolithic fallback" in normalized
    assert "Only `paper-explainer` receives the resolved output path" in normalized
    assert "workers never receive `out`" in normalized
    assert "workers never receive" in normalized and "collision state" in normalized
```

Keep the existing heading, evidence-label, collision, preflight-order, target-count, and incomplete-output assertions.

- [ ] **Step 2: Run focused tests and verify Red**

```bash
PYTHONPATH=src:. /Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.venv/bin/python \
  -m pytest tests/test_v2_workflow_source.py -k 'research_explain' -q
```

Expected: the role list still has two entries and the stage lacks task graph loading, adaptive task IDs, fresh retry, partial status, and delegation-unavailable refusal.

- [ ] **Step 3: Project all five modes from the action**

Keep the existing `source`, `mode`, `out`, defaults, output, policies, and retention fields byte-equivalent in meaning. Replace only `explain.roles` with the five ordered assignments asserted in Step 1. Do not remove `literature-reviewer` from the role registry or any other action.

- [ ] **Step 4: Rewrite Phase 2-5 as the executable scheduler contract**

Keep Phase 1 collision/preflight behavior and the twelve-heading synthesis contract. Replace source mapping and two-stream dispatch with these exact ordered coordinator phases:

```markdown
## Phase 2: Load and validate the task graph
## Phase 3: Dispatch adaptive dependency waves
### IndexerInput contract
### WorkerInput contract
### Retry contract
## Phase 4: Calculate terminal status and synthesize
## Phase 5: Validate and report
```

Phase 2 loads the graph and both schemas from the capability bundle, checks host delegation before dispatch, and reports `incomplete: delegation unavailable` without a monolithic fallback. Phase 3 dispatches `I0`, then the selected profile's ready tasks in lexical ID order with effective concurrency `min(host capacity, 4)`, then `A1` for reviewer, then `S0`. Workers receive no output or collision fields and cannot delegate.

For every timeout, execution failure, or schema-invalid packet, record the reason and dispatch attempt two to a fresh subagent with the identical input except `attempt: 2`; after a second failure, record a terminal failed packet. Calculate the three statuses exactly as stated in Global Constraints. Pass only validated packets, failure history, audit, status, and output ownership to `S0`.

Partial/incomplete notes must include a banner, failed task IDs, both attempt reasons, missing sections, and recovery actions. `I0` failure produces no note; mandatory external failure may produce the marked source-analysis draft. Preserve canonical packet order by task ID, numeric-conflict handling, external-versus-author distinction, unsupported-claim exclusion, abstract-only scope, 3-5 similar plus 3-5 frontier targets, and search metadata.

- [ ] **Step 5: Update the human-readable capability spec and digest**

Revise `paper-explanation/spec.md` so it names all runtime resources and role modes, reproduces the approved profile allocations, input/return contracts, retry rules, status table, sole-writer rule, and no-delegation outcome. Remove statements that assign mapping or external retrieval directly to `paper-explainer` or `literature-reviewer`.

Add a capability test asserting the normalized spec contains `task-graph.yaml`, all five modes, `max_parallel: 4`, `max_attempts: 2`, `complete`, `partial`, `incomplete`, and `delegation unavailable`. Refresh only the paper-explanation bundle digest using the Task 1 command.

- [ ] **Step 6: Verify Green, run frozen routing regressions, and commit**

```bash
PYTHONPATH=src:. /Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.venv/bin/python \
  -m pytest tests/test_v2_workflow_source.py tests/test_v2_capabilities.py \
  tests/test_paper_explanation_task_graph.py tests/test_v2_role_modes.py \
  tests/test_paper_explanation_routing.py tests/test_v2_contract_mapping.py -q
```

Expected: zero failures; public routing/output remains unchanged; frozen v1 fixture and hashes remain unchanged.

```bash
git add plugins/scholar-ip/workflows/research/workflow.yaml \
  plugins/scholar-ip/workflows/research/stages/explain.md \
  plugins/scholar-ip/capabilities/research/paper-explanation/spec.md \
  plugins/scholar-ip/capabilities/index.yaml tests/test_v2_workflow_source.py \
  tests/test_v2_capabilities.py
git commit -m "feat(research): schedule explanation subagents adaptively"
```

---

### Task 4: Verify, review, integrate, and refresh the installed plugin

**Files:**
- Verify tracked source and tests from Tasks 1-3.
- Regenerate ignored host outputs only through existing commands after branch integration.
- Do not modify `.env`, credentials, `~/.codex/config.toml`, or marketplace JSON by hand.

**Interfaces:**
- Consumes: three reviewed implementation commits.
- Produces: a merge-ready branch, verified three-host render, validated Codex/Claude packages where tools exist, and a refreshed local Scholar installation sourced from the integrated main checkout.

- [ ] **Step 1: Run focused and full Python verification**

```bash
PYTHONPATH=src:. /Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.venv/bin/python \
  -m pytest tests/test_paper_explanation_task_graph.py tests/test_paper_explanation_routing.py \
  tests/test_v2_capabilities.py tests/test_v2_role_modes.py tests/test_v2_workflow_source.py \
  tests/test_v2_contract_mapping.py tests/test_v2_release_surface.py \
  tests/test_v2_renderer.py tests/test_v2_install.py -q
PYTHONPATH=src:. /Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.venv/bin/python \
  -m pytest tests/ -q
```

Expected: both commands exit zero with no warnings or failures.

- [ ] **Step 2: Run lint, render, package, and plugin validators**

```bash
PYTHONPATH=src:. /Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.venv/bin/python \
  -m ruff check src packages tests
make PYTHON=/Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.venv/bin/python render
make PYTHON=/Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.venv/bin/python wheel-smoke
/Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.venv/bin/python \
  /Users/fsm/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .codex/plugins/scholar
```

Expected: Ruff reports `All checks passed!`; all renderers and wheel smoke exit zero; Codex validation exits zero. If `claude` is present, also run:

```bash
make PYTHON=/Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.venv/bin/python plugin-validate
```

If `claude` is absent, record that one limitation explicitly; do not weaken the other gates.

- [ ] **Step 3: Inspect rendered parity, final diff, and sensitive values**

```bash
rg -n "task-graph.yaml|paper-indexer|paper-analysis-worker|paper-reasoning-worker|explanation-evidence-auditor|incomplete: delegation unavailable" \
  .claude/plugins/scholar-ip .codex/plugins/scholar .opencode
git diff --check
git status --short --branch
git diff "$(git merge-base master HEAD)"...HEAD --stat
git diff "$(git merge-base master HEAD)"...HEAD -- \
  ':!docs/superpowers/specs/*.md' ':!docs/superpowers/plans/*.md'
rg -n --hidden -g '!*.lock' -g '!.git/**' \
  '(BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|api[_-]?key\s*[:=]|secret\s*[:=]|token\s*[:=])' \
  src plugins tests docs
```

Expected: all three host outputs contain the same graph, schemas, modes, and delegation refusal; no whitespace errors, unintended files, frozen-fixture changes, or secret values.

- [ ] **Step 4: Request the broad whole-branch review and resolve findings**

Generate a review package from `git merge-base master HEAD` through `HEAD`. The reviewer must inspect spec compliance, graph/schema correctness, retry/status semantics, sole-writer isolation, frozen-contract preservation, tests, and host parity. Resolve every Critical or Important finding with a focused failing regression test, fresh Green verification, and re-review; record Minor findings for final triage.

- [ ] **Step 5: Integrate only after all gates are green**

Use the `superpowers:finishing-a-development-branch` workflow. Confirm the target is the main checkout's `master`, the main checkout has no overlapping user changes, and the reviewed branch head is unchanged. Fast-forward or merge without rewriting history, then rerun the focused suite in the main checkout using its designated `.venv`.

- [ ] **Step 6: Refresh the installed plugin through supported tooling**

From the integrated main checkout, run the existing render/install flow and plugin-creator cachebuster. Read the marketplace name with the provided script; do not edit marketplace/config files:

```bash
make PYTHON=.venv/bin/python install-codex
.venv/bin/python /Users/fsm/.codex/skills/.system/plugin-creator/scripts/update_plugin_cachebuster.py \
  .codex/plugins/scholar
.venv/bin/python /Users/fsm/.codex/skills/.system/plugin-creator/scripts/read_marketplace_name.py \
  --marketplace-path .agents/plugins/marketplace.json
codex plugin list
codex plugin add scholar@scholar-ip-copilot
codex plugin list
```

Expected: marketplace name `scholar-ip-copilot`; `scholar@scholar-ip-copilot` points to this repository's integrated `.codex/plugins/scholar`; install/update succeeds and remains enabled. If discovery points elsewhere, stop before mutation and report the mismatch.

- [ ] **Step 7: Final handoff**

Report the commits, focused/full/lint/render/wheel/plugin validation outcomes, final review verdict, integration status, installed plugin source, and any unavailable validator. Advise opening a new Codex task before testing `$scholar-using` or `$scholar-research explain`, because the current task keeps its already-loaded skill snapshot.
