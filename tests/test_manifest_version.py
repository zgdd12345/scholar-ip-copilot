"""Tests for the versioned plugin manifest + migration tool framework (Module J).

Covers:
- plugin.yaml carries the new `manifest_version: "1.0.0"` field and validates
  against `packages/core/schemas/plugin.schema.json`.
- The migration framework adds `manifest_version` on the v0 -> v1 step.
- The migrator refuses targets it has no path to.
- The migrator is a no-op when source == target.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

from packages.core.src import migrate

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_YAML = REPO_ROOT / "plugins" / "scholar-ip" / "plugin.yaml"
PLUGIN_SCHEMA = REPO_ROOT / "packages" / "core" / "schemas" / "plugin.schema.json"


def _load_plugin() -> dict:
    return yaml.safe_load(PLUGIN_YAML.read_text(encoding="utf-8"))


def test_current_plugin_yaml_has_manifest_version() -> None:
    doc = _load_plugin()
    assert "manifest_version" in doc, (
        "plugin.yaml is missing the `manifest_version` field introduced in Module J"
    )
    assert isinstance(doc["manifest_version"], str), (
        "manifest_version must be a quoted string in YAML, not a float; got "
        f"{type(doc['manifest_version']).__name__}"
    )
    assert doc["manifest_version"] == "1.0.0"


def test_current_plugin_yaml_validates_against_plugin_schema() -> None:
    doc = _load_plugin()
    schema = json.loads(PLUGIN_SCHEMA.read_text(encoding="utf-8"))
    # Must not raise.
    jsonschema.validate(doc, schema)


def test_migrate_0_0_0_to_1_0_0_adds_manifest_version() -> None:
    # Synthesise an in-memory pre-v1 plugin (no manifest_version).
    pre_v1: dict = {
        "id": "scholar",
        "name": "EviDraft",
        "version": "0.0.1",
        "description": "test fixture",
    }
    assert "manifest_version" not in pre_v1
    assert migrate.detect_version(pre_v1) == "0.0.0"

    plan = migrate.plan(pre_v1, "1.0.0")
    assert len(plan.steps) == 1, (
        f"expected single-step v0->v1 migration, got {len(plan.steps)}: {plan.steps}"
    )
    step = plan.steps[0]
    assert step.from_version == "0.0.0"
    assert step.to_version == "1.0.0"

    result, log = migrate.apply(pre_v1, "1.0.0", dry_run=True)
    assert result["manifest_version"] == "1.0.0"
    # Input must not be mutated under dry-run.
    assert "manifest_version" not in pre_v1
    # Log should mention the step and the dry-run sentinel.
    joined = "\n".join(log)
    assert "0.0.0 -> 1.0.0" in joined
    assert "dry-run" in joined


def test_migrate_refuses_unknown_target() -> None:
    plugin: dict = {
        "id": "scholar",
        "manifest_version": "1.0.0",
        "name": "EviDraft",
        "version": "0.0.1",
        "description": "test fixture",
    }
    with pytest.raises(ValueError) as exc:
        migrate.apply(plugin, "2.0.0")
    assert "no migration path from 1.0.0 to 2.0.0" in str(exc.value)


def test_migrate_noop_when_already_at_target() -> None:
    plugin: dict = {
        "id": "scholar",
        "manifest_version": "1.0.0",
        "name": "EviDraft",
        "version": "0.0.1",
        "description": "test fixture",
    }
    result, log = migrate.apply(plugin, "1.0.0")
    assert result == plugin
    # Plan itself must be empty.
    plan = migrate.plan(plugin, "1.0.0")
    assert plan.is_noop
    assert plan.steps == []
    # Log should be informational only, no "applying ..." lines.
    assert not any(line.startswith("applying ") for line in log)
