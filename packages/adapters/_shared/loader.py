"""Plugin + frontmatter loader shared by every adapter.

The platform-neutral source under ``plugins/scholar-ip/`` is parsed once into a
``Plugin`` dict-like structure that adapters then translate to their host
format. Keeps every adapter ~100 lines of pure rendering logic.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# YAML frontmatter delimiter: lines that contain only "---".
_FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)


@dataclass
class FrontmatterDoc:
    """A single markdown file with YAML frontmatter and a body."""

    path: Path
    meta: dict[str, Any]
    body: str

    @property
    def id(self) -> str:
        return str(self.meta.get("id") or self.path.stem)


@dataclass
class Plugin:
    """Parsed plugin tree."""

    root: Path
    manifest: dict[str, Any]
    commands: list[FrontmatterDoc] = field(default_factory=list)
    agents: list[FrontmatterDoc] = field(default_factory=list)
    skills: list[FrontmatterDoc] = field(default_factory=list)
    hooks: list[FrontmatterDoc] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "manifest": self.manifest,
            "commands": [_doc_to_dict(d) for d in self.commands],
            "agents": [_doc_to_dict(d) for d in self.agents],
            "skills": [_doc_to_dict(d) for d in self.skills],
            "hooks": [_doc_to_dict(d) for d in self.hooks],
        }


def _doc_to_dict(d: FrontmatterDoc) -> dict[str, Any]:
    return {"path": str(d.path), "meta": d.meta, "body": d.body}


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split a markdown file's YAML frontmatter from its body."""
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    fm_raw, body = m.group(1), m.group(2)
    meta = yaml.safe_load(fm_raw) or {}
    if not isinstance(meta, dict):
        raise ValueError(f"Frontmatter must be a mapping, got {type(meta).__name__}")
    return meta, body


def _load_md_dir(dirpath: Path) -> list[FrontmatterDoc]:
    """Load every ``*.md`` (or ``SKILL.md``) file under ``dirpath`` recursively.

    Returns documents sorted by path for stable output. A file whose
    frontmatter fails to parse is kept with ``meta={"_parse_error": ...}`` so
    the renderer can still emit something useful and validators can report it.
    """
    if not dirpath.exists():
        return []
    docs: list[FrontmatterDoc] = []
    for md in sorted(dirpath.rglob("*.md")):
        text = md.read_text(encoding="utf-8")
        try:
            meta, body = split_frontmatter(text)
        except (yaml.YAMLError, ValueError) as exc:
            meta = {"_parse_error": str(exc), "id": md.stem}
            body = text
        docs.append(FrontmatterDoc(path=md, meta=meta, body=body))
    return docs


def load_plugin(plugin_dir: Path) -> Plugin:
    """Parse ``plugin.yaml`` plus all command/agent/skill/hook frontmatter."""
    plugin_dir = plugin_dir.resolve()
    manifest_path = plugin_dir / "plugin.yaml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing plugin.yaml at {manifest_path}")
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}

    entrypoints = manifest.get("entrypoints", {}) or {}

    def _sub(key: str, default: str) -> Path:
        return plugin_dir / (entrypoints.get(key) or default)

    return Plugin(
        root=plugin_dir,
        manifest=manifest,
        commands=_load_md_dir(_sub("commands", "commands/")),
        agents=_load_md_dir(_sub("agents", "agents/")),
        skills=_load_md_dir(_sub("skills", "skills/")),
        hooks=_load_md_dir(_sub("hooks", "hooks/")),
    )


def validate(plugin: Plugin, schema_path: Path) -> list[str]:
    """Validate every frontmatter doc against ``command.schema.json``.

    Uses ``jsonschema`` when installed; otherwise performs a small required-fields
    check so the adapter still works on a bare interpreter.
    """
    errors: list[str] = []
    if not schema_path.exists():
        return [f"schema not found: {schema_path}"]

    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    try:
        import jsonschema  # type: ignore
    except ImportError:  # pragma: no cover - graceful fallback
        jsonschema = None  # type: ignore[assignment]

    required = schema.get("required", []) or ["id", "title", "kind"]
    allowed_kinds = (
        schema.get("properties", {}).get("kind", {}).get("enum")
        or ["command", "agent", "skill", "hook"]
    )

    def _check(doc: FrontmatterDoc, expected_kind: str) -> None:
        meta = doc.meta or {}
        rel = doc.path
        if "_parse_error" in meta:
            errors.append(f"{rel}: frontmatter YAML parse error: {meta['_parse_error']}")
            return
        if jsonschema is not None:
            try:
                jsonschema.validate(meta, schema)
            except jsonschema.ValidationError as exc:  # type: ignore[attr-defined]
                errors.append(f"{rel}: {exc.message}")
                return
        else:
            for field_name in required:
                if field_name not in meta:
                    errors.append(f"{rel}: missing required field '{field_name}'")
            if meta.get("kind") and meta["kind"] not in allowed_kinds:
                errors.append(f"{rel}: kind '{meta['kind']}' not in {allowed_kinds}")
        if meta.get("kind") and meta["kind"] != expected_kind:
            errors.append(
                f"{rel}: kind '{meta.get('kind')}' does not match folder '{expected_kind}'"
            )

    for d in plugin.commands:
        _check(d, "command")
    for d in plugin.agents:
        _check(d, "agent")
    for d in plugin.skills:
        _check(d, "skill")
    for d in plugin.hooks:
        _check(d, "hook")
    return errors
