"""Render the EviDraft plugin into a Codex-CLI plugin layout.

Codex CLI does not have user-defined slash commands, sub-agents, or workflow
files. Everything user-visible is shipped as a **skill** (a directory with a
``SKILL.md`` whose frontmatter declares ``name`` and ``description``). The
platform-neutral plugin is therefore flattened so that:

* every source command becomes a skill named ``scholar-<command-id>``;
* every source skill becomes a skill named ``scholar-skill-<skill-id>``
  (the ``-skill-`` infix disambiguates from same-id commands such as
  ``brainstorming``, which exists as both a command and a skill in source);
* source subagents are inlined into the command body (Codex has no
  subagent dispatch);
* source hooks are inlined as a ``## Guardrails`` block;
* source workflows are inlined into a single ``Workflows`` section in the
  README (Codex has no workflow file convention).

Output tree (rooted at ``--out`` — the plugin root)::

    .codex-plugin/plugin.json
    skills/scholar-<command-id>/SKILL.md
    skills/scholar-skill-<source-skill-id>/SKILL.md
    README.md

To make this plugin loadable, the caller also needs a Codex marketplace
file at ``<repo-root>/.agents/plugins/marketplace.json`` that points at this
plugin directory and is registered via ``codex plugin marketplace add <repo>``.
This adapter only renders the plugin itself; marketplace registration is a
separate concern.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .._shared.loader import (
    FrontmatterDoc,
    Plugin,
    dump_frontmatter,
    load_plugin as _load_plugin,
    render_retention_section,
    validate as _validate,
)


CMD_PREFIX = "scholar-"
SKILL_PREFIX = "scholar-skill-"


def _agents_by_id(plugin: Plugin) -> dict[str, FrontmatterDoc]:
    return {d.id: d for d in plugin.agents}


def _hooks_by_id(plugin: Plugin) -> dict[str, FrontmatterDoc]:
    return {d.id: d for d in plugin.hooks}


def _strip_body(body: str) -> str:
    return body.strip("\n")


def _command_skill_body(
    doc: FrontmatterDoc,
    agents: dict[str, FrontmatterDoc],
    hooks: dict[str, FrontmatterDoc],
    safety: dict[str, Any],
) -> str:
    """Build the body of the SKILL.md that represents one source command."""
    meta = doc.meta or {}
    title = meta.get("title") or doc.id
    slash = meta.get("slash") or f"/{doc.id}"

    lines: list[str] = [f"# {slash}", "", f"_{title}_", ""]

    retention = render_retention_section(meta)
    if retention:
        lines.append(retention.rstrip("\n"))

    inputs = meta.get("inputs") or []
    if inputs:
        lines.append("## Inputs")
        lines.append("")
        for i in inputs:
            label = i.get("name", "?")
            t = i.get("type", "string")
            req = "optional" if i.get("optional") else "required"
            extras = []
            if "default" in i:
                extras.append(f"default `{i['default']}`")
            if i.get("values"):
                extras.append(f"values {i['values']}")
            extra = f" — {', '.join(extras)}" if extras else ""
            lines.append(f"- `{label}` ({t}, {req}){extra}")
        lines.append("")

    outputs = meta.get("outputs") or []
    if outputs:
        lines.append("## Outputs")
        lines.append("")
        for o in outputs:
            lines.append(f"- `{o.get('path')}`")
        lines.append("")

    lines.append("## Instructions")
    lines.append("")
    lines.append(_strip_body(doc.body))
    lines.append("")

    hook_ids = meta.get("hooks") or []
    if hook_ids or safety:
        lines.append("## Guardrails")
        lines.append("")
        for hid in hook_ids:
            h = hooks.get(hid)
            if h:
                fm_mode = h.meta.get("failure_mode", "warn")
                behaviour = (h.meta.get("behaviour") or h.meta.get("title") or hid).strip()
                lines.append(f"- **{hid}** ({fm_mode}): {behaviour}")
            else:
                lines.append(f"- **{hid}**: see hooks/{hid}.md")
        forb_paths = safety.get("forbidden_paths") or []
        forb_tools = safety.get("forbidden_tool_patterns") or []
        if forb_paths:
            lines.append(f"- Never read or write: {', '.join(f'`{p}`' for p in forb_paths)}.")
        if forb_tools:
            lines.append(f"- Never invoke: {', '.join(f'`{t}`' for t in forb_tools)}.")
        lines.append("")

    sub_ids = meta.get("subagents") or []
    if sub_ids:
        lines.append("## Inline subagent roles")
        lines.append("")
        seen: set[str] = set()
        for sid in sub_ids:
            if sid in seen:
                continue
            seen.add(sid)
            ag = agents.get(sid)
            if ag is None:
                lines.append(f"### {sid}\n\n_(definition missing in plugin/agents/)_\n")
                continue
            role = (ag.meta.get("role") or ag.meta.get("title") or sid).strip()
            lines.append(f"### {sid} — {role}")
            lines.append("")
            lines.append(_strip_body(ag.body))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _skill_skill_body(doc: FrontmatterDoc) -> str:
    """Build the body of the SKILL.md that represents one source skill."""
    meta = doc.meta or {}
    lines = [f"# {meta.get('title') or doc.id}", ""]
    if meta.get("triggers"):
        lines.append("**Triggers:** " + ", ".join(meta["triggers"]))
        lines.append("")
    if meta.get("provides"):
        lines.append("**Provides:** " + ", ".join(meta["provides"]))
        lines.append("")
    lines.append(_strip_body(doc.body))
    lines.append("")
    return "\n".join(lines)


def _workflows_section(plugin: Plugin) -> list[str]:
    workflows = plugin.manifest.get("workflows") or {}
    if not workflows:
        return []
    lines = ["## Workflows", ""]
    for name, steps in workflows.items():
        lines.append(f"### {name}")
        lines.append("")
        for i, step in enumerate(steps or [], 1):
            lines.append(f"{i}. `{step}`")
        lines.append("")
    return lines


def _render_readme(plugin: Plugin) -> str:
    m = plugin.manifest
    lines = [
        f"# {m.get('name', 'EviDraft')} for Codex CLI",
        "",
        (m.get("description") or "").strip(),
        "",
        "## Layout",
        "",
        "- `.codex-plugin/plugin.json` — Codex plugin manifest",
        f"- `skills/scholar-<command-id>/SKILL.md` — {len(plugin.commands)} command(s) as invokable skills",
        f"- `skills/scholar-skill-<source-skill-id>/SKILL.md` — {len(plugin.skills)} reusable how-to skill(s)",
        "",
        "## Installation",
        "",
        "From the repo root that contains `.agents/plugins/marketplace.json`:",
        "",
        "```bash",
        "codex plugin marketplace add ./",
        "```",
        "",
        "Skills then appear in Codex `/skills`. Restart Codex after install.",
        "",
        "## Caveats",
        "",
        "Codex CLI has no first-class sub-agent dispatch, so any source command",
        "that declares `subagents:` has those roles **inlined** at the bottom of",
        "the rendered SKILL body. Source hooks become a `## Guardrails` block.",
        "",
    ]
    lines.extend(_workflows_section(plugin))
    return "\n".join(lines)


def _build_plugin_manifest(plugin: Plugin) -> dict[str, Any]:
    """Emit ``.codex-plugin/plugin.json`` matching the Codex plugin spec.

    See ``~/.codex/skills/.system/plugin-creator/references/plugin-json-spec.md``.
    Only ``name`` is required; the rest is metadata. ``skills: "./skills/"``
    is the canonical path for skill discovery within the plugin.
    """
    m = plugin.manifest
    out: dict[str, Any] = {
        "name": m.get("id", "scholar"),
        "version": m.get("version", "0.0.1"),
        "description": (m.get("description") or "").strip(),
        "skills": "./skills/",
    }
    if m.get("homepage"):
        out["homepage"] = m["homepage"]
    if m.get("license"):
        out["license"] = m["license"]
    authors = m.get("authors") or []
    if authors:
        first = authors[0] if isinstance(authors[0], dict) else {"name": authors[0]}
        out["author"] = first
    display = m.get("name")
    if display:
        out["interface"] = {"displayName": display}
    return {k: v for k, v in out.items() if v is not None and v != ""}


def render(plugin: Plugin, out_dir: Path) -> list[Path]:
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    agents = _agents_by_id(plugin)
    hooks = _hooks_by_id(plugin)
    safety = plugin.manifest.get("safety") or {}

    manifest_dir = out_dir / ".codex-plugin"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / "plugin.json"
    manifest_path.write_text(
        json.dumps(_build_plugin_manifest(plugin), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    written.append(manifest_path)

    readme = out_dir / "README.md"
    readme.write_text(_render_readme(plugin), encoding="utf-8")
    written.append(readme)

    skills_root = out_dir / "skills"
    skills_root.mkdir(parents=True, exist_ok=True)

    for d in plugin.commands:
        name = f"{CMD_PREFIX}{d.id}"
        desc = (d.meta or {}).get("description") or (d.meta or {}).get("title") or d.id
        fm = {"name": name, "description": str(desc).strip()}
        body = _command_skill_body(d, agents, hooks, safety)
        target = skills_root / name / "SKILL.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(dump_frontmatter(fm, body), encoding="utf-8")
        written.append(target)

    for d in plugin.skills:
        name = f"{SKILL_PREFIX}{d.id}"
        desc = (d.meta or {}).get("description") or (d.meta or {}).get("title") or d.id
        fm = {"name": name, "description": str(desc).strip()}
        body = _skill_skill_body(d)
        target = skills_root / name / "SKILL.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(dump_frontmatter(fm, body), encoding="utf-8")
        written.append(target)

    return written


def _dry_run_paths(plugin: Plugin, out_dir: Path) -> list[Path]:
    paths = [out_dir / ".codex-plugin" / "plugin.json", out_dir / "README.md"]
    paths.extend(
        out_dir / "skills" / f"{CMD_PREFIX}{d.id}" / "SKILL.md"
        for d in plugin.commands
    )
    paths.extend(
        out_dir / "skills" / f"{SKILL_PREFIX}{d.id}" / "SKILL.md"
        for d in plugin.skills
    )
    return paths


load_plugin = _load_plugin
validate = _validate


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="evidraft-codex-cli",
        description="Render the EviDraft plugin into a Codex CLI plugin layout.",
    )
    ap.add_argument("--plugin", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--schema", type=Path, default=None)
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

    if args.dry_run:
        paths = _dry_run_paths(plugin, args.out.resolve())
        for p in paths:
            print(p)
        print(f"[codex-cli] dry-run: would write {len(paths)} file(s) to {args.out.resolve()}")
        return 0

    written = render(plugin, args.out)
    for p in written:
        print(p)
    print(f"[codex-cli] wrote {len(written)} file(s) to {args.out.resolve()}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
