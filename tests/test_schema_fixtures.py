"""Pytest gate for schema regression fixtures.

Each yaml under ``tests/fixtures/schemas/`` has a verdict encoded in its
filename suffix: ``__valid.yaml`` or ``__invalid.yaml``. This test loads
each fixture, validates it against the right schema, and asserts the
verdict matches the suffix.

Schema target resolution:
    * ``command-*.yaml`` (or any fixture whose top-level YAML keys include
      ``id`` and ``kind``) -> ``command.schema.json``
    * everything else (presence of ``project_type`` is the canonical signal)
      -> ``project.schema.json``
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "schemas"
SCHEMA_DIR = REPO_ROOT / "packages" / "core" / "schemas"

FIXTURES = sorted(FIXTURE_DIR.glob("*.yaml"))


def _verdict_from_name(name: str) -> str:
    """Return ``"valid"`` or ``"invalid"`` based on the filename suffix."""
    stem = Path(name).stem
    if stem.endswith("__valid"):
        return "valid"
    if stem.endswith("__invalid"):
        return "invalid"
    raise ValueError(
        f"fixture {name!r} must end with __valid.yaml or __invalid.yaml"
    )


def _schema_for(doc: dict, fixture_path: Path) -> Path:
    """Pick the right schema for a fixture.

    A fixture targets ``command.schema.json`` if its filename starts with
    ``command-`` OR if the top-level YAML carries both ``id`` and ``kind`` keys
    (the canonical command/agent/skill/hook frontmatter shape).

    Otherwise it targets ``project.schema.json``.
    """
    if fixture_path.name.startswith("command-"):
        return SCHEMA_DIR / "command.schema.json"
    if isinstance(doc, dict) and "id" in doc and "kind" in doc:
        return SCHEMA_DIR / "command.schema.json"
    return SCHEMA_DIR / "project.schema.json"


@pytest.mark.parametrize(
    "fixture", FIXTURES, ids=[f.name for f in FIXTURES]
)
def test_schema_fixture(fixture: Path) -> None:
    expected = _verdict_from_name(fixture.name)
    doc = yaml.safe_load(fixture.read_text(encoding="utf-8"))
    assert doc is not None, f"fixture {fixture} parsed to None"

    schema_path = _schema_for(doc, fixture)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    if expected == "valid":
        # Must not raise.
        jsonschema.validate(doc, schema)
    else:
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(doc, schema)


def test_at_least_six_fixtures_present() -> None:
    """Guards against accidental deletion of the regression set."""
    assert len(FIXTURES) >= 6, (
        f"expected >=6 schema fixtures, found {len(FIXTURES)}: "
        f"{[f.name for f in FIXTURES]}"
    )
