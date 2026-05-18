"""Render the EviDraft plugin into a Claude-Code-flavored layout.

Output tree (rooted at ``--out``)::

    plugin.json
    commands/<id>.md
    agents/<id>.md
    skills/<id>/SKILL.md

The renderer keeps the original prose verbatim and only rewrites frontmatter to
the keys Claude Code recognises. The exact Claude Code plugin schema is still
evolving — see README.md for caveats.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from .._shared.loader import FrontmatterDoc, Plugin, load_plugin as _load_plugin, validate as _validate


# ---------------------------------------------------------------------------
# Frontmatter translators
# ---------------------------------------------------------------------------


def _command_frontmatter(meta: dict[str, Any]) -> dict[str, Any]:
    """Map platform-neutral command meta -> Claude Code command frontmatter."""
    fm: dict[str, Any] = {}
    if meta.get("description"):
        fm["description"] = meta["description"]
    elif meta.get("title"):
        fm["description"] = meta["title"]
    inputs = meta.get("inputs") or []
    if inputs:
        hints = []
        for i in inputs:
            name = i.get("name", "arg")
            hints.append(f"[{name}]" if i.get("optional") else f"<{name}>")
        fm["argument-hint"] = " ".join(hints)
    allowed = meta.get("allowed_tools") or []
    if allowed:
        fm["allowed-tools"] = list(allowed)
    if meta.get("slash"):
        fm["slash"] = meta["slash"]
    return fm


def _agent_frontmatter(meta: dict[str, Any]) -> dict[str, Any]:
    fm: dict[str, Any] = {"name": meta.get("id", "agent")}
    desc = meta.get("description") or meta.get("role") or meta.get("title")
    if desc:
        fm["description"] = str(desc).strip()
    tools = meta.get("allowed_tools") or []
    if tools:
        fm["tools"] = list(tools)
    return fm


def _skill_frontmatter(meta: dict[str, Any]) -> dict[str, Any]:
    fm: dict[str, Any] = {"name": meta.get("id", "skill")}
    desc = meta.get("description") or meta.get("title")
    if desc:
        fm["description"] = str(desc).strip()
    if meta.get("triggers"):
        fm["triggers"] = list(meta["triggers"])
    return fm


def _dump_frontmatter(fm: dict[str, Any], body: str) -> str:
    yml = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
    body = body.lstrip("\n")
    return f"---\n{yml}\n---\n\n{body}"


# ---------------------------------------------------------------------------
# Top-level manifest
# ---------------------------------------------------------------------------


def _build_plugin_json(plugin: Plugin) -> dict[str, Any]:
    m = plugin.manifest
    out: dict[str, Any] = {
        "name": m.get("name", "EviDraft"),
        "id": m.get("id", "scholar-ip"),
        "version": m.get("version", "0.0.1"),
        "description": (m.get("description") or "").strip(),
        "homepage": m.get("homepage"),
        "commands": [
            {"id": d.id, "slash": d.meta.get("slash"), "file": f"commands/{d.path.name}"}
            for d in plugin.commands
        ],
        "agents": [
            {"id": d.id, "file": f"agents/{d.path.name}"}
            for d in plugin.agents
        ],
        "skills": [
            {"id": d.id, "file": f"skills/{d.id}/SKILL.md"}
            for d in plugin.skills
        ],
    }
    if plugin.hooks:
        out["hooks"] = [
            {
                "id": d.id,
                "trigger": d.meta.get("triggers") or d.meta.get("trigger"),
                "failure_mode": d.meta.get("failure_mode", "warn"),
                "file": f"hooks/{d.path.name}",
            }
            for d in plugin.hooks
        ]
    return {k: v for k, v in out.items() if v is not None}


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


def render(plugin: Plugin, out_dir: Path) -> list[Path]:
    """Render ``plugin`` into ``out_dir``. Returns the list of written paths."""
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    manifest_path = out_dir / "plugin.json"
    manifest_path.write_text(
        json.dumps(_build_plugin_json(plugin), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    written.append(manifest_path)

    cmd_dir = out_dir / "commands"
    cmd_dir.mkdir(parents=True, exist_ok=True)
    for d in plugin.commands:
        fm = _command_frontmatter(d.meta or {})
        target = cmd_dir / d.path.name
        target.write_text(_dump_frontmatter(fm, d.body), encoding="utf-8")
        written.append(target)

    if plugin.agents:
        agent_dir = out_dir / "agents"
        agent_dir.mkdir(parents=True, exist_ok=True)
        for d in plugin.agents:
            fm = _agent_frontmatter(d.meta or {})
            target = agent_dir / d.path.name
            target.write_text(_dump_frontmatter(fm, d.body), encoding="utf-8")
            written.append(target)

    if plugin.skills:
        skills_root = out_dir / "skills"
        for d in plugin.skills:
            sk_dir = skills_root / d.id
            sk_dir.mkdir(parents=True, exist_ok=True)
            fm = _skill_frontmatter(d.meta or {})
            target = sk_dir / "SKILL.md"
            target.write_text(_dump_frontmatter(fm, d.body), encoding="utf-8")
            written.append(target)

    return written


def _dry_run_paths(plugin: Plugin, out_dir: Path) -> list[Path]:
    paths = [out_dir / "plugin.json"]
    paths.extend(out_dir / "commands" / d.path.name for d in plugin.commands)
    paths.extend(out_dir / "agents" / d.path.name for d in plugin.agents)
    paths.extend(out_dir / "skills" / d.id / "SKILL.md" for d in plugin.skills)
    return paths


# Re-exported names so users can ``from packages.adapters.claude_code import generate``.
load_plugin = _load_plugin
validate = _validate


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="evidraft-claude-code",
        description="Render the EviDraft (scholar-ip) plugin into Claude Code layout.",
    )
    ap.add_argument("--plugin", required=True, type=Path, help="path to plugins/scholar-ip")
    ap.add_argument("--out", required=True, type=Path, help="destination directory")
    ap.add_argument("--dry-run", action="store_true", help="print files instead of writing")
    ap.add_argument(
        "--schema",
        type=Path,
        default=None,
        help="override path to command.schema.json (defaults to repo packages/core/schemas/)",
    )
    args = ap.parse_args(argv)

    plugin = load_plugin(args.plugin)

    schema_path = args.schema or (
        args.plugin.resolve().parents[1] / "packages" / "core" / "schemas" / "command.schema.json"
    )
    errors = validate(plugin, schema_path)
    if errors:
        print("Validation errors:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        # Validation failures are warnings, not fatal in MVP.

    if args.dry_run:
        paths = _dry_run_paths(plugin, args.out.resolve())
        for p in paths:
            print(p)
        print(
            f"[claude-code] dry-run: would write {len(paths)} file(s) to {args.out.resolve()}"
        )
        return 0

    written = render(plugin, args.out)
    for p in written:
        print(p)
    print(f"[claude-code] wrote {len(written)} file(s) to {args.out.resolve()}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
