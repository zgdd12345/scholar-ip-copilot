from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_WORKFLOWS = {
    "using": [],
    "scope": [],
    "research": ["guide", "reading-list", "explain", "deep"],
    "paper": [
        "init",
        "lit",
        "idea",
        "code-audit",
        "experiment",
        "review",
        "draft",
        "check",
        "venue",
    ],
    "patent": ["init", "scout", "prior-art", "disclosure", "claims", "review"],
    "polish": [],
    "xreview": [],
}


def test_release_versions_and_console_scripts_are_v2() -> None:
    import evidraft
    import packages.adapters

    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    manifest = yaml.safe_load(
        (ROOT / "plugins/scholar-ip/plugin.yaml").read_text(encoding="utf-8")
    )

    assert pyproject["project"]["version"] == "2.0.0"
    assert evidraft.__version__ == "2.0.0"
    assert packages.adapters.__version__ == "2.0.0"
    assert manifest["version"] == "2.0.0"
    assert manifest["manifest_version"] == "2.0.0"
    assert pyproject["project"]["scripts"] == {
        "evidraft": "evidraft.cli:main",
        "evidraft-claude-code": "packages.adapters.claude_code.generate:main",
        "evidraft-codex-cli": "packages.adapters.codex_cli.generate:main",
        "evidraft-opencode": "packages.adapters.opencode.generate:main",
    }


def test_manifest_declares_only_the_v2_authoring_surface() -> None:
    manifest = yaml.safe_load(
        (ROOT / "plugins/scholar-ip/plugin.yaml").read_text(encoding="utf-8")
    )
    schema = json.loads(
        (ROOT / "packages/core/schemas/plugin.schema.json").read_text(encoding="utf-8")
    )

    jsonschema.validate(manifest, schema)
    assert manifest["entrypoints"] == {
        "workflows": "workflows/",
        "roles": "roles/roles.yaml",
        "policies": "policies/policy.yaml",
        "capabilities": "capabilities/",
        "templates": "templates/",
    }
    assert {item["id"]: item["actions"] for item in manifest["workflows"]} == (
        PUBLIC_WORKFLOWS
    )
    assert {item["status"] for item in manifest["adapters"]} == {"stable"}


def test_runtime_and_installable_schema_copies_are_identical() -> None:
    for name in ("project.schema.json", "evidence.schema.json"):
        canonical = (ROOT / "src" / "evidraft" / "schemas" / name).read_bytes()
        assert (ROOT / "packages" / "core" / "schemas" / name).read_bytes() == canonical
        assert (ROOT / "plugins" / "scholar-ip" / "schemas" / name).read_bytes() == canonical
    assert (
        ROOT / "packages" / "core" / "schemas" / "workflow.schema.json"
    ).read_bytes() == (
        ROOT / "src" / "evidraft" / "schemas" / "workflow.schema.json"
    ).read_bytes()


def test_project_templates_are_native_v2_and_have_no_removed_invocations() -> None:
    schema = json.loads(
        (ROOT / "src" / "evidraft" / "schemas" / "project.schema.json").read_text()
    )
    templates = ROOT / "plugins" / "scholar-ip" / "templates"
    for project_type in ("paper", "patent"):
        project = yaml.safe_load(
            (templates / f"{project_type}-project" / ".evidraft" / "project.yaml").read_text()
        )
        jsonschema.validate(project, schema)
        assert project["format_version"] == 2
        assert "hooks" not in project
    text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in templates.rglob("*")
        if path.is_file()
    )
    assert "/scholar:" not in text


def test_primary_documentation_lists_exactly_seven_host_invocations() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    rows = re.findall(
        r"^\| `(?P<id>[a-z-]+)` \| `(?P<claude>[^`]+)` \| "
        r"`(?P<codex>[^`]+)` \| `(?P<opencode>[^`]+)` \|$",
        readme,
        flags=re.MULTILINE,
    )
    assert len(rows) == 7
    assert {row[0] for row in rows} == set(PUBLIC_WORKFLOWS)
    for workflow_id, claude, codex, opencode in rows:
        assert claude == f"/scholar:{workflow_id}"
        assert codex == f"$scholar-{workflow_id}"
        assert opencode == f"/scholar-{workflow_id}"

    for required in (".evidraft/", "manuscript/", "submissions/", "not legal advice"):
        assert required in readme
    assert "compatibility alias" not in readme.lower()


def test_makefile_and_ci_define_all_release_gates() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    for target in ("test:", "lint:", "plugin-validate:", "wheel:", "wheel-smoke:", "release-check:"):
        assert target in makefile
    assert "-m pytest tests/" in makefile
    assert "-m ruff check" in makefile
    assert "claude plugin validate" in makefile
    assert "evidraft/schemas/workflow.schema.json" in makefile
    assert "evidraft-opencode --plugin" in makefile

    for os_name in ("ubuntu-latest", "macos-latest"):
        assert os_name in ci
    for version in ('"3.10"', '"3.11"', '"3.12"'):
        assert version in ci
    for gate in (
        "pytest tests/",
        "ruff check",
        "claude plugin validate",
        "python -m build",
        "pip install",
        'bin/evidraft" --help',
        'bin/evidraft-claude-code" --help',
        'bin/evidraft-codex-cli" --help',
        'bin/evidraft-opencode" --help',
        'bin/evidraft-opencode" --plugin',
        "evidraft/schemas/workflow.schema.json",
    ):
        assert gate in ci
