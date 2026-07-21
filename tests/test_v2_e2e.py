from __future__ import annotations

from pathlib import Path

import yaml

from evidraft.render import Host
from tests.integration.v2_flow import execute_flow


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "scholar-ip"
FIXTURES = ROOT / "tests" / "fixtures" / "e2e"


def _assert_flow(tmp_path: Path, fixture_name: str) -> None:
    contract = yaml.safe_load((FIXTURES / fixture_name).read_text(encoding="utf-8"))
    actions = tuple(contract["actions"])

    result = execute_flow(
        plugin_root=PLUGIN_ROOT,
        project_root=tmp_path / "project",
        render_root=tmp_path / "renders",
        workflow_id=contract["workflow"],
        actions=actions,
    )

    assert result.workflow_id == contract["workflow"]
    assert result.actions == actions
    assert result.declared_outputs == tuple(
        tuple(contract["outputs"][action]) for action in actions
    )
    assert len(result.evidence_ids) == contract["evidence_count"]
    assert result.format_version == 2
    assert result.public_entry_counts == {host: 7 for host in Host}


def test_research_reading_list_flow_is_executable_across_all_hosts(tmp_path: Path) -> None:
    _assert_flow(tmp_path, "research_reading_list.yaml")


def test_full_paper_flow_is_executable_across_all_hosts(tmp_path: Path) -> None:
    _assert_flow(tmp_path, "paper_full.yaml")


def test_full_patent_flow_is_executable_across_all_hosts(tmp_path: Path) -> None:
    _assert_flow(tmp_path, "patent_full.yaml")


def test_ci_checks_temporary_opencode_inventory_without_project_skill_ownership() -> None:
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "evidraft-opencode --plugin plugins/scholar-ip" in ci
    assert 'glob("scholar-*.md")' in ci
    assert "== 7" in ci
    assert ".agents/skills/.evidraft-ownership.json" in ci
    assert "test ! -e" in ci
