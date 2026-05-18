"""Render the EviDraft plugin into a Codex-CLI-flavored layout.

Codex CLI has no first-class sub-agent concept, so every command prompt is
self-contained: subagent definitions get inlined at the bottom, and hooks
become a ``## Guardrails`` block.

Output tree (rooted at ``--out``)::

    README.md
    prompts/<command-id>.md
    workflows/paper.md, patent.md, ...
    skills/<skill-id>.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Iterable

from .._shared.loader import (
    FrontmatterDoc,
    Plugin,
    load_plugin as _load_plugin,
    validate as _validate,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _agents_by_id(plugin: Plugin) -> dict[str, FrontmatterDoc]:
    return {d.id: d for d in plugin.agents}


def _hooks_by_id(plugin: Plugin) -> dict[str, FrontmatterDoc]:
    return {d.id: d for d in plugin.hooks}


def _strip_body(body: str) -> str:
    return body.strip("\n")


def _render_command(
    doc: FrontmatterDoc,
    agents: dict[str, FrontmatterDoc],
    hooks: dict[str, FrontmatterDoc],
    safety: dict[str, Any],
) -> str:
    meta = doc.meta or {}
    title = meta.get("title") or doc.id
    slash = meta.get("slash") or f"/{doc.id}"
    desc = (meta.get("description") or "").strip()

    lines: list[str] = [f"# {slash}", ""]
    lines.append(f"_{title}_")
    if desc:
        lines.append("")
        lines.append(desc)
    lines.append("")

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

    # Guardrails: from per-command hook ids + global safety policy.
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

    # Inlined subagents (since Codex has no native subagent dispatch).
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


def _render_workflow(name: str, steps: Iterable[str]) -> str:
    lines = [f"# Workflow: {name}", "", "Ordered playbook from `plugin.yaml`.", ""]
    for i, step in enumerate(steps, 1):
        lines.append(f"{i}. `{step}`")
    lines.append("")
    return "\n".join(lines)


def _render_skill(doc: FrontmatterDoc) -> str:
    meta = doc.meta or {}
    lines = [f"# Skill: {meta.get('title') or doc.id}", ""]
    if meta.get("description"):
        lines.append(meta["description"].strip())
        lines.append("")
    if meta.get("triggers"):
        lines.append("**Triggers:** " + ", ".join(meta["triggers"]))
        lines.append("")
    if meta.get("provides"):
        lines.append("**Provides:** " + ", ".join(meta["provides"]))
        lines.append("")
    lines.append(_strip_body(doc.body))
    lines.append("")
    return "\n".join(lines)


def _render_readme(plugin: Plugin) -> str:
    m = plugin.manifest
    lines = [
        f"# {m.get('name', 'EviDraft')} for Codex CLI",
        "",
        (m.get("description") or "").strip(),
        "",
        "## How to invoke",
        "",
        "Each file under `prompts/` is a self-contained prompt that you can pipe to",
        "Codex CLI (or paste into a Codex session) to run that command:",
        "",
        "```bash",
        "codex run --prompt prompts/scholar:paper-init.md",
        "```",
        "",
        "Workflows under `workflows/` are ordered playbooks; run their steps in",
        "sequence. Skills under `skills/` describe reusable how-tos that you can",
        "reference inside a prompt with `@skills/<id>.md`.",
        "",
        "## Contents",
        "",
        f"- {len(plugin.commands)} prompt(s) under `prompts/`",
        f"- {len(plugin.skills)} skill(s) under `skills/`",
        f"- {len(plugin.manifest.get('workflows') or {})} workflow playbook(s) under `workflows/`",
        "",
        "## Caveat",
        "",
        "Codex CLI has no first-class sub-agent dispatch, so any command that",
        "declares `subagents:` in the source plugin has those roles **inlined**",
        "at the bottom of the prompt instead of dispatched. Hooks are surfaced as",
        "a `## Guardrails` section the model must obey.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


def render(plugin: Plugin, out_dir: Path) -> list[Path]:
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    agents = _agents_by_id(plugin)
    hooks = _hooks_by_id(plugin)
    safety = plugin.manifest.get("safety") or {}

    readme = out_dir / "README.md"
    readme.write_text(_render_readme(plugin), encoding="utf-8")
    written.append(readme)

    prompts_dir = out_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    for d in plugin.commands:
        target = prompts_dir / f"{d.id}.md"
        target.write_text(
            _render_command(d, agents, hooks, safety), encoding="utf-8"
        )
        written.append(target)

    workflows = plugin.manifest.get("workflows") or {}
    if workflows:
        wf_dir = out_dir / "workflows"
        wf_dir.mkdir(parents=True, exist_ok=True)
        for name, steps in workflows.items():
            target = wf_dir / f"{name}.md"
            target.write_text(_render_workflow(name, steps or []), encoding="utf-8")
            written.append(target)

    if plugin.skills:
        sk_dir = out_dir / "skills"
        sk_dir.mkdir(parents=True, exist_ok=True)
        for d in plugin.skills:
            target = sk_dir / f"{d.id}.md"
            target.write_text(_render_skill(d), encoding="utf-8")
            written.append(target)

    return written


def _dry_run_paths(plugin: Plugin, out_dir: Path) -> list[Path]:
    paths = [out_dir / "README.md"]
    paths.extend(out_dir / "prompts" / f"{d.id}.md" for d in plugin.commands)
    workflows = plugin.manifest.get("workflows") or {}
    paths.extend(out_dir / "workflows" / f"{name}.md" for name in workflows)
    paths.extend(out_dir / "skills" / f"{d.id}.md" for d in plugin.skills)
    return paths


load_plugin = _load_plugin
validate = _validate


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="evidraft-codex-cli",
        description="Render the EviDraft plugin into Codex CLI prompts/workflows.",
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
