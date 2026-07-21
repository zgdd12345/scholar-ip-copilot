from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from evidraft.core import (
    append_evidence,
    audit_evidence,
    migrate_project,
    resolve_evidence,
    workflow_finalize,
    workflow_preflight,
)
from evidraft.render import Host, load_workflows, render_plugin


PUBLIC_WORKFLOW_IDS = {
    "using",
    "scope",
    "research",
    "paper",
    "patent",
    "polish",
    "xreview",
}


@dataclass(frozen=True)
class FlowResult:
    workflow_id: str
    actions: tuple[str, ...]
    declared_outputs: tuple[tuple[str, ...], ...]
    evidence_ids: tuple[str, ...]
    format_version: int
    public_entry_counts: dict[Host, int]


def execute_flow(
    *,
    plugin_root: Path,
    project_root: Path,
    render_root: Path,
    workflow_id: str,
    actions: tuple[str, ...],
) -> FlowResult:
    workflows = load_workflows(plugin_root)
    workflow = workflows[workflow_id]
    if not actions or any(action not in workflow.actions for action in actions):
        raise AssertionError(f"invalid {workflow_id} action sequence: {actions}")

    public_entry_counts: dict[Host, int] = {}
    for host in Host:
        host_root = render_root / host.value
        render_plugin(plugin_root, host_root, host)
        public_entry_counts[host] = _assert_rendered_flow(
            host_root=host_root,
            host=host,
            workflow_id=workflow_id,
            actions=actions,
        )

    _write_v1_project(project_root, workflow_id)
    migration = migrate_project(project_root)
    assert migration.changed
    evidence_ids: list[str] = []
    declared_outputs: list[tuple[str, ...]] = []
    for action_id in actions:
        action = workflow.actions[action_id]
        outputs = tuple(str(output["path"]) for output in action["outputs"])
        declared_outputs.append(outputs)
        workflow_preflight(
            project_root,
            f"{workflow_id}.{action_id}",
            target_paths=outputs,
        )
        created = _evidence_for_action(project_root, workflow_id, action_id)
        if created is not None:
            evidence_ids.append(created["id"])
        assert workflow_finalize(project_root, retention=action["retention"]).removed == ()

    for identifier in evidence_ids:
        assert resolve_evidence(project_root, identifier)["id"] == identifier
    audit = audit_evidence(project_root)
    assert audit.valid is True
    assert set(audit.checked_ids) == set(evidence_ids)
    project = yaml.safe_load(
        (project_root / ".evidraft" / "project.yaml").read_text(encoding="utf-8")
    )
    return FlowResult(
        workflow_id=workflow_id,
        actions=actions,
        declared_outputs=tuple(declared_outputs),
        evidence_ids=tuple(evidence_ids),
        format_version=project["format_version"],
        public_entry_counts=public_entry_counts,
    )


def _assert_rendered_flow(
    *, host_root: Path, host: Host, workflow_id: str, actions: tuple[str, ...]
) -> int:
    if host is Host.CLAUDE:
        public_entries = list((host_root / "commands").glob("*.md"))
        public_ids = {entry.stem for entry in public_entries}
        bundle = host_root / "private" / "workflows" / workflow_id
        private = host_root / "private"
    elif host is Host.CODEX:
        public_entries = list((host_root / "skills").glob("scholar-*/SKILL.md"))
        public_ids = {entry.parent.name.removeprefix("scholar-") for entry in public_entries}
        bundle = host_root / "skills" / f"scholar-{workflow_id}"
        private = host_root / "skills" / ".evidraft-private"
    else:
        public_entries = list((host_root / "commands").glob("scholar-*.md"))
        public_ids = {entry.stem.removeprefix("scholar-") for entry in public_entries}
        bundle = host_root / "private" / "workflows" / workflow_id
        private = host_root / "private"

    assert public_ids == PUBLIC_WORKFLOW_IDS
    installed = yaml.safe_load((bundle / "workflow.yaml").read_text(encoding="utf-8"))
    assert installed["id"] == workflow_id
    for action_id in actions:
        action = installed["actions"][action_id]
        assert (bundle / action["procedure"]).is_file()
    assert (private / "capabilities" / "index.yaml").is_file()
    assert (private / "roles" / "roles.yaml").is_file()
    assert (private / "policies" / "policy.yaml").is_file()
    assert (private / "schemas" / "project.schema.json").is_file()
    assert (private / "templates" / "paper-project" / "manuscript" / "main.tex").is_file()
    return len(public_entries)


def _write_v1_project(project_root: Path, workflow_id: str) -> None:
    project_type = "patent" if workflow_id == "patent" else "paper"
    evidraft = project_root / ".evidraft"
    (evidraft / "evidence").mkdir(parents=True)
    project = {
        "project_type": project_type,
        "title": f"E2E {workflow_id}",
        "status": {},
        "artifacts": {"evidence": ".evidraft/evidence/evidence.jsonl"},
        "rules": {
            "require_citation_for_claims": True,
            "require_experiment_source_for_numbers": True,
            "require_code_trace_for_code_claims": True,
            "allow_unverified_claims": False,
        },
    }
    (evidraft / "project.yaml").write_text(
        yaml.safe_dump(project, sort_keys=False), encoding="utf-8"
    )
    (evidraft / "evidence" / "evidence.jsonl").write_text("", encoding="utf-8")


def _evidence_for_action(
    project_root: Path, workflow_id: str, action_id: str
) -> dict | None:
    common = {
        "claim": f"Verified E2E claim from {workflow_id}.{action_id}.",
        "support": "Deterministic fixture record",
        "confidence": "high",
        "verified": True,
        "added_by": f"{workflow_id}.{action_id}",
    }
    if (workflow_id, action_id) == ("paper", "lit"):
        return append_evidence(
            project_root,
            {
                **common,
                "type": "paper",
                "source": "doi:10.0000/evidraft-e2e",
                "citation_key": "alba2026evidraft",
            },
        )
    if (workflow_id, action_id) == ("paper", "experiment"):
        result_file = project_root / "experiments" / "result.json"
        result_file.parent.mkdir(parents=True, exist_ok=True)
        result_file.write_text('{"score": 1.0}\n', encoding="utf-8")
        return append_evidence(
            project_root,
            {
                **common,
                "type": "experiment",
                "source": "experiments/result.json",
                "file_path": "experiments/result.json",
                "line_range": "1:1",
            },
        )
    if (workflow_id, action_id) == ("patent", "scout"):
        source_file = project_root / "src" / "invention.py"
        source_file.parent.mkdir(parents=True, exist_ok=True)
        source_file.write_text("INVENTION = True\n", encoding="utf-8")
        return append_evidence(
            project_root,
            {
                **common,
                "type": "code",
                "source": "src/invention.py",
                "file_path": "src/invention.py",
                "line_range": "1:1",
            },
        )
    if (workflow_id, action_id) == ("patent", "prior-art"):
        return append_evidence(
            project_root,
            {
                **common,
                "type": "patent",
                "source": "patent:US0000000A1",
            },
        )
    return None
