"""Plugin + frontmatter loader shared by every adapter.

The platform-neutral source under ``plugins/scholar-ip/`` is parsed once into a
``Plugin`` dict-like structure that adapters then translate to their host
format. Keeps every adapter ~100 lines of pure rendering logic.

Retention enforcement
---------------------
v0.2 emits the ``retention:`` block declared on a command as a POSIX bash
snippet that adapters splice into the rendered command body as a
``## Pre-run cleanup`` section. The snippet is run by the LLM at command start
(host-agnostic, no special API needed). v0.3 will promote this to a first-class
adapter hook (PreToolUse on Claude Code; equivalent on Codex CLI / OpenCode)
once those host APIs converge on a uniform pre-command callback contract. The
body-level snippet path stays as a safety net for hosts without hooks.
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


# ---------------------------------------------------------------------------
# Retention enforcement
# ---------------------------------------------------------------------------


def render_retention_prune_snippet(
    command_id: str,
    output_dir: str,
    keep_last: int | None,
    max_age_days: int | None,
    file_glob: str = "*",
) -> str | None:
    """Generate a bash one-liner that prunes ``<output_dir>/<file_glob>``
    to the retention budget. Returns ``None`` if no retention is declared.

    Returns shell-safe POSIX (used by Claude Code and Codex CLI adapters).
    Operates on regular files only; never traverses into subdirs unless
    ``file_glob`` explicitly says so. Skips hidden files (``.last.yaml`` etc.)
    because ``find -name '*'`` and shell globs do not match leading-dot files
    by default — that is precisely the behaviour we want for the index file
    ``.evidraft/reviews/.last.yaml`` and any other dotfile under
    ``<output_dir>``.

    Properties:
        * Idempotent — running the snippet twice in a row is a no-op the
          second time.
        * Guarded — when ``<output_dir>`` does not exist the snippet is a
          no-op, so the very first invocation of a command never errors out.
        * Order — age-based pruning runs first, then keep-last takes the
          remaining file count down to the cap.
    """
    if keep_last is None and max_age_days is None:
        return None

    parts: list[str] = []
    parts.append(f"# evidraft retention prune for /{command_id} ({output_dir})")
    parts.append(f'DIR="{output_dir}"')
    parts.append(f'GLOB="{file_glob}"')
    if max_age_days is not None:
        parts.append(f"MAX_AGE_DAYS={int(max_age_days)}")
    if keep_last is not None:
        parts.append(f"KEEP_LAST={int(keep_last)}")
    parts.append('if [ -d "$DIR" ]; then')
    if max_age_days is not None:
        # -maxdepth 1: never descend into subdirs.
        # -type f: regular files only.
        # -name "$GLOB": leading-dot files are not matched by '*' globs,
        #   which is intentional — preserves .last.yaml and any dotfiles.
        # -mtime +N: strictly older than N*24h.
        parts.append(
            '  find "$DIR" -maxdepth 1 -type f -name "$GLOB" '
            '-mtime +$MAX_AGE_DAYS -delete 2>/dev/null || true'
        )
    if keep_last is not None:
        # `ls -1t` lists newest first; `tail -n +K` skips the first K-1 lines
        # so we delete everything from line K onward (i.e. everything past
        # the keep-last cap). Quote the path to survive spaces; xargs -I{}
        # handles per-file rm with no shell expansion.
        parts.append(
            '  ls -1t "$DIR"/$GLOB 2>/dev/null | tail -n +$((KEEP_LAST + 1)) '
            "| xargs -I{} rm -f -- {} 2>/dev/null || true"
        )
    parts.append("fi")
    return "\n".join(parts)
