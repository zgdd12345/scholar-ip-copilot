from __future__ import annotations

import json
import hashlib
import shutil
from pathlib import Path

import yaml

import evidraft
import packages.adapters
from evidraft.render import EXPECTED_ACTIONS, Host, load_workflows, render_plugin


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "scholar-ip"


def test_v3_versions_and_public_action_surface_are_consistent() -> None:
    pyproject = __import__("tomllib").loads((ROOT / "pyproject.toml").read_text())
    manifest = yaml.safe_load((PLUGIN / "plugin.yaml").read_text())

    assert pyproject["project"]["version"] == "3.0.0"
    assert evidraft.__version__ == "3.0.0"
    assert packages.adapters.__version__ == "3.0.0"
    assert manifest["manifest_version"] == manifest["version"] == "3.0.0"
    assert manifest["workflows"][2]["actions"] == ["reading-list", "explain", "deep"]
    assert EXPECTED_ACTIONS["research"] == {"reading-list", "explain", "deep"}
    assert sum(len(actions) for actions in EXPECTED_ACTIONS.values()) == 22


def test_workflow_outputs_default_required_true_and_preserve_explicit_false(
    tmp_path: Path,
) -> None:
    plugin = tmp_path / "plugin"
    shutil.copytree(PLUGIN, plugin)
    research_path = plugin / "workflows/research/workflow.yaml"
    research = yaml.safe_load(research_path.read_text())
    research["actions"]["reading-list"]["outputs"][0]["required"] = False
    research_path.write_text(yaml.safe_dump(research, sort_keys=False))

    workflows = load_workflows(plugin)
    reading_list = workflows["research"].actions["reading-list"]["outputs"]
    paper_check = workflows["paper"].actions["check"]["outputs"]

    assert reading_list[0]["required"] is False
    assert all(output["required"] is True for output in paper_check)


def test_renderer_has_no_paper_explanation_task_graph_or_worker_agents(
    tmp_path: Path,
) -> None:
    out = tmp_path / "rendered"
    render_plugin(PLUGIN, out, Host.CLAUDE)

    private = out / "private"
    capability = private / "capabilities/research/paper-explanation"
    assert (capability / "spec.md").is_file()
    for obsolete in (
        "task-graph.yaml",
        "paper-map.schema.json",
        "analysis-packet.schema.json",
    ):
        assert not (capability / obsolete).exists()
    for obsolete in (
        "paper-indexer",
        "paper-analysis-worker",
        "paper-reasoning-worker",
        "explanation-evidence-auditor",
    ):
        assert not (out / "agents" / f"{obsolete}.md").exists()


def test_v3_plugin_schema_accepts_only_v3_manifest() -> None:
    schema = json.loads((ROOT / "packages/core/schemas/plugin.schema.json").read_text())
    manifest = yaml.safe_load((PLUGIN / "plugin.yaml").read_text())

    assert schema["properties"]["manifest_version"]["const"] == "3.0.0"
    assert schema["properties"]["version"]["const"] == "3.0.0"
    assert manifest["manifest_version"] == manifest["version"] == "3.0.0"


def test_v3_policy_declares_safety_blocking_and_advisory_audit_semantics() -> None:
    policies = yaml.safe_load((PLUGIN / "policies/policy.yaml").read_text())["policies"]
    allowed_tools = policies["workspace-safety"]["tool_access"]["default_allowed_tools"]

    assert policies["scope"] == {
        "description": "Provide optional project intent and constraints without blocking generation.",
        "enforcement": "advisory",
    }
    assert policies["evidence-integrity"]["enforcement"] == "audit"
    assert policies["evidence-integrity"]["verdicts"] == ["PASS", "WARN", "FAIL"]
    assert {
        "Bash:evidraft workflow preflight*",
        "Bash:evidraft workflow prepare-output*",
        "Bash:evidraft workflow finalize*",
        "Bash:evidraft evidence audit*",
    } <= set(allowed_tools)
    assert not any(
        "paper-explanation validate-return" in tool
        for tool in allowed_tools
    )


def test_v3_docs_publish_the_breaking_action_migration_without_data_migration() -> None:
    root_readme = (ROOT / "README.md").read_text()
    plugin_readme = (PLUGIN / "README.md").read_text()
    migration = (ROOT / "docs/migration-v3.md").read_text()

    for document in (root_readme, plugin_readme):
        assert "EviDraft 3.0" in document
        assert "`reading-list`, `explain`, `deep`" in document
        assert "`guide`, `reading-list`, `explain`, `deep`" not in document
    assert "research guide" in migration
    assert "workflow:using.run" in migration
    assert "format_version: 2" in migration
    assert "does not delete" in migration.lower()


def _bundle_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def test_v3_install_and_capability_index_drop_obsolete_research_contracts() -> None:
    install_source = (ROOT / "src/evidraft/install.py").read_text()
    obsolete = {
        "task-graph.yaml",
        "paper-map.schema.json",
        "analysis-packet.schema.json",
        "paper-indexer.md",
        "paper-analysis-worker.md",
        "paper-reasoning-worker.md",
        "explanation-evidence-auditor.md",
    }
    assert not any(name in install_source for name in obsolete)

    using_specs = (
        PLUGIN / "capabilities/research/using-scholar-ip-copilot/spec.md",
        PLUGIN / "capabilities/research/using-deep-research/spec.md",
    )
    assert all("workflow:research.guide" not in path.read_text() for path in using_specs)

    index = yaml.safe_load((PLUGIN / "capabilities/index.yaml").read_text())["capabilities"]
    for capability_id in (
        "paper-explanation",
        "using-scholar-ip-copilot",
        "using-deep-research",
    ):
        entry = index[capability_id]
        bundle = PLUGIN / "capabilities" / Path(entry["spec"]).parent
        assert entry["bundle_sha256"] == _bundle_sha256(bundle)
