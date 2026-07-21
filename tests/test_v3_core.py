"""Focused contracts for the EviDraft v3 core and CLI."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest
import yaml

import evidraft
import evidraft.core as core_module
import evidraft.render as render_module
from evidraft.cli import build_parser, main as cli_main
from evidraft.core import EvidenceError, PreflightError, workflow_preflight


def _write_project(root: Path) -> None:
    project = root / ".evidraft/project.yaml"
    project.parent.mkdir(parents=True)
    project.write_text(
        yaml.safe_dump(
            {
                "format_version": 2,
                "project_type": "paper",
                "title": "Test project",
                "status": {},
                "artifacts": {"evidence": ".evidraft/evidence/evidence.jsonl"},
                "rules": {},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _evidence_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "id": "ev_0001",
        "type": "note",
        "source": "notes:test",
        "claim": "A supported claim.",
        "support": "paragraph 1",
        "confidence": "high",
        "verified": True,
    }
    record.update(overrides)
    return record


def _write_evidence(root: Path, *records: dict[str, object]) -> Path:
    evidence = root / ".evidraft/evidence/evidence.jsonl"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )
    return evidence


def test_preflight_is_safety_only_and_has_no_scope_result(tmp_path: Path) -> None:
    _write_project(tmp_path)
    evidence = tmp_path / ".evidraft/evidence/evidence.jsonl"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("not json\n", encoding="utf-8")
    (evidence.parent / "quarantine.jsonl").write_text("bad evidence\n", encoding="utf-8")

    result = workflow_preflight(tmp_path, "paper.draft")

    assert asdict(result) == {"operation": "paper.draft", "warnings": ()}


def test_preflight_keeps_path_sensitive_and_xreview_write_zone_safety(tmp_path: Path) -> None:
    _write_project(tmp_path)

    with pytest.raises(PreflightError, match="sensitive"):
        workflow_preflight(tmp_path, "paper.lit", target_paths=[".env.local"])
    with pytest.raises(PreflightError, match="project root"):
        workflow_preflight(tmp_path, "paper.lit", read_paths=["../outside.md"])
    with pytest.raises(PreflightError, match="write zone"):
        workflow_preflight(tmp_path, "xreview.run", target_paths=["manuscript/main.tex"])
    assert asdict(
        workflow_preflight(
            tmp_path,
            "xreview.run",
            target_paths=[".evidraft/reviews/report.md"],
        )
    ) == {"operation": "xreview.run", "warnings": ()}


@pytest.mark.parametrize(
    ("operation", "read_paths", "target_paths"),
    [
        ("paper.init", (), ()),
        ("patent.init", (), ()),
        ("polish.run", (), ()),
        ("scope.run", (), ()),
        (
            "xreview.run",
            ("draft.md",),
            (".evidraft/reviews/report.md",),
        ),
        ("research.reading-list", (), ("reading-list.md",)),
        ("research.explain", ("draft.md",), ("explanation.md",)),
    ],
)
def test_preflight_allows_declared_projectless_operations(
    tmp_path: Path,
    operation: str,
    read_paths: tuple[str, ...],
    target_paths: tuple[str, ...],
) -> None:
    (tmp_path / "draft.md").write_text("draft\n", encoding="utf-8")

    result = workflow_preflight(
        tmp_path,
        operation,
        read_paths=read_paths,
        target_paths=target_paths,
    )

    assert result.operation == operation
    assert result.warnings == ()
    assert not (tmp_path / ".evidraft/project.yaml").exists()


@pytest.mark.parametrize("kind", ["read", "target"])
def test_preflight_rejects_absolute_workspace_paths(tmp_path: Path, kind: str) -> None:
    path = tmp_path / "draft.md"
    path.write_text("draft\n", encoding="utf-8")
    kwargs = {"read_paths" if kind == "read" else "target_paths": [path]}

    with pytest.raises(PreflightError, match="relative"):
        workflow_preflight(tmp_path, "research.explain", **kwargs)


def test_preflight_rejects_symlinked_read_path(tmp_path: Path) -> None:
    _write_project(tmp_path)
    source = tmp_path / "papers/source.pdf"
    source.parent.mkdir()
    source.write_bytes(b"%PDF-1.7")
    link = source.parent / "linked.pdf"
    link.symlink_to(source)

    with pytest.raises(PreflightError, match="symlink"):
        workflow_preflight(tmp_path, "research.explain", read_paths=[link])


@pytest.mark.parametrize("kind", ["target", "parent"])
def test_preflight_rejects_symlinked_regular_write_targets(tmp_path: Path, kind: str) -> None:
    actual = tmp_path / "actual"
    actual.mkdir()
    if kind == "target":
        (actual / "report.md").write_text("old\n", encoding="utf-8")
        (tmp_path / "report.md").symlink_to(actual / "report.md")
        target = "report.md"
    else:
        (tmp_path / "reports").symlink_to(actual, target_is_directory=True)
        target = "reports/report.md"

    with pytest.raises(PreflightError, match="symlink"):
        workflow_preflight(tmp_path, "research.explain", target_paths=[target])

    with pytest.raises(PreflightError, match="symlink"):
        core_module.workflow_prepare_output(tmp_path, "research.explain", target)


def test_evidence_audit_reports_non_empty_quarantine(tmp_path: Path) -> None:
    _write_project(tmp_path)
    quarantine = tmp_path / ".evidraft/evidence/quarantine.jsonl"
    quarantine.parent.mkdir(parents=True)
    quarantine.write_text("bad evidence\n", encoding="utf-8")

    result = core_module.audit_evidence(tmp_path)

    assert result.valid is False
    assert result.findings == ("evidence quarantine is not empty",)
    assert result.checked_ids == ()


def test_evidence_audit_returns_schema_findings_through_api_and_cli(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_project(tmp_path)
    _write_evidence(tmp_path, {"id": "ev_0001"})

    result = core_module.audit_evidence(tmp_path)

    assert result.valid is False
    assert result.checked_ids == ()
    assert len(result.findings) == 1
    assert "evidence line 1" in result.findings[0]
    assert "schema validation failed" in result.findings[0]

    assert cli_main(["--root", str(tmp_path), "evidence", "audit"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert set(payload) == {"valid", "findings", "checked_ids"}
    assert payload == {
        "valid": False,
        "findings": list(result.findings),
        "checked_ids": [],
    }


def test_evidence_audit_checks_all_current_records_and_storage(tmp_path: Path) -> None:
    _write_project(tmp_path)
    source = tmp_path / "artifacts/source.txt"
    source.parent.mkdir()
    source.write_text("one\n", encoding="utf-8")
    body = b"durable source"
    digest = __import__("hashlib").sha256(body).hexdigest()
    snapshot = tmp_path / f".evidraft/literature/snapshots/{digest}.md"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_bytes(b"tampered")
    _write_evidence(
        tmp_path,
        _evidence_record(id="ev_0001"),
        _evidence_record(id="ev_0002", supersedes="ev_0001", verified=False),
        _evidence_record(
            id="ev_0003",
            type="code",
            source="artifacts/source.txt",
            file_path="artifacts/source.txt",
            line_range="1:2",
        ),
        _evidence_record(
            id="ev_0004",
            type="paper",
            source_kind="blog",
            source="https://example.test/source",
            citation_key="source2026",
            file_path=snapshot.relative_to(tmp_path).as_posix(),
            line_range="1:1",
        ),
    )

    result = core_module.audit_evidence(tmp_path)

    assert result.valid is False
    assert result.checked_ids == ("ev_0002", "ev_0003", "ev_0004")
    assert any("not verified: ev_0002" in finding for finding in result.findings)
    assert any("out of bounds" in finding and "ev_0003" in finding for finding in result.findings)
    assert any("snapshot" in finding and "hash" in finding for finding in result.findings)


def test_evidence_audit_selected_ids_validate_graph_then_only_requested_records(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path)
    _write_evidence(
        tmp_path,
        _evidence_record(id="ev_0001"),
        _evidence_record(id="ev_0002", supersedes="ev_0001"),
        _evidence_record(id="ev_0003", verified=False),
    )

    selected = core_module.audit_evidence(tmp_path, identifiers=["ev_0001"])

    assert selected.valid is False
    assert selected.checked_ids == ("ev_0001",)
    assert any("superseded" in finding for finding in selected.findings)
    assert not any("ev_0003" in finding for finding in selected.findings)

    dangling = _evidence_record(id="ev_0004", supersedes="ev_9999")
    _write_evidence(tmp_path, dangling)
    graph = core_module.audit_evidence(tmp_path, identifiers=["ev_0004"])
    assert graph.valid is False
    assert graph.checked_ids == ()
    assert any("supersedes target does not exist" in finding for finding in graph.findings)


def test_evidence_audit_valid_result_and_cli_json_contract(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_project(tmp_path)
    _write_evidence(
        tmp_path,
        _evidence_record(id="ev_0001"),
        _evidence_record(id="ev_0002", verified=False),
    )

    result = core_module.audit_evidence(tmp_path, identifiers=["ev_0001"])
    assert asdict(result) == {
        "valid": True,
        "findings": (),
        "checked_ids": ("ev_0001",),
    }
    assert (
        cli_main(
            [
                "--root",
                str(tmp_path),
                "evidence",
                "audit",
                "--id",
                "ev_0001",
                "--id",
                "ev_0002",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out) == {
        "valid": False,
        "findings": ["evidence is not verified: ev_0002"],
        "checked_ids": ["ev_0001", "ev_0002"],
    }


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("not json\n", "invalid JSON"),
        ("[]\n", "not an object"),
        ('{"id": "ev_0001"}\n', "schema validation failed"),
    ],
)
def test_evidence_audit_reports_malformed_rows_through_api_and_cli(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    content: str,
    expected: str,
) -> None:
    _write_project(tmp_path)
    evidence = tmp_path / ".evidraft/evidence/evidence.jsonl"
    evidence.parent.mkdir(parents=True)
    evidence.write_text(content, encoding="utf-8")

    result = core_module.audit_evidence(tmp_path)

    assert result.valid is False
    assert result.checked_ids == ()
    assert len(result.findings) == 1
    assert expected in result.findings[0]
    assert cli_main(["--root", str(tmp_path), "evidence", "audit"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "valid": False,
        "findings": list(result.findings),
        "checked_ids": [],
    }


def test_append_and_resolve_keep_strict_evidence_parsing(tmp_path: Path) -> None:
    _write_project(tmp_path)
    evidence = tmp_path / ".evidraft/evidence/evidence.jsonl"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("not json\n", encoding="utf-8")

    with pytest.raises(EvidenceError, match="invalid JSON"):
        core_module.append_evidence(
            tmp_path, {key: value for key, value in _evidence_record().items() if key != "id"}
        )
    with pytest.raises(EvidenceError, match="invalid JSON"):
        core_module.resolve_evidence(tmp_path, "ev_0001")


def test_v3_removes_scope_and_paper_explanation_runtime_surfaces() -> None:
    assert evidraft.__version__ == "3.0.0"
    assert evidraft.audit_evidence is core_module.audit_evidence
    assert evidraft.EvidenceAuditResult is core_module.EvidenceAuditResult
    assert not hasattr(core_module.PreflightResult("paper.lit"), "scope")
    assert not hasattr(core_module, "scope_policy")
    assert not hasattr(core_module, "PUBLISH_OPERATIONS")
    assert not hasattr(core_module, "WARN_SCOPE_OPERATIONS")
    assert not hasattr(core_module, "workflow_validate_paper_explanation_return")
    assert not hasattr(evidraft, "workflow_validate_paper_explanation_return")
    assert not hasattr(render_module, "_mode_agent_body")
    assert not (Path(core_module.__file__).parent / "paper_explanation.py").exists()

    with pytest.raises(SystemExit):
        build_parser().parse_args(["paper-explanation", "validate-return"])
