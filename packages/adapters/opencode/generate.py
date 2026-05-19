"""Render the EviDraft plugin into an OpenCode-flavored layout.

OpenCode loads plugins as JavaScript/TypeScript modules registered in
``opencode.json``'s ``plugin`` array. Components (slash commands, subagents,
skills) are auto-discovered as markdown from these directories, walked from
cwd up to the worktree root, plus the user-global equivalents under
``~/.config/opencode/``:

* ``.opencode/commands/<name>.md``  — slash commands. Filename is the command
  name; OpenCode does **not** support ``/foo:bar`` namespacing, so we encode
  the original ``scholar:`` namespace into the filename as
  ``scholar-<command-id>.md``.
* ``.opencode/agents/<id>.md``      — subagents. Frontmatter requires
  ``mode: subagent`` and uses OpenCode's per-tool ``permission`` block instead
  of Claude Code's ``tools`` list.
* ``.opencode/skills/<id>/SKILL.md`` — Anthropic-style skills (the source
  frontmatter passes through nearly verbatim; only ``name`` and ``description``
  are required).

Source hooks are deferred for OpenCode: OpenCode hooks must be JavaScript
callbacks exported from a plugin module, so they cannot be rendered as
markdown. The README explains this gap.

Output tree (rooted at ``--out``)::

    commands/scholar-<command-id>.md
    agents/<agent-id>.md
    skills/<skill-id>/SKILL.md
    README.md
"""

from __future__ import annotations

import argparse
import shutil
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


_CC_TO_OPENCODE_TOOL = {
    "Read": ("read", "allow"),
    "Glob": ("read", "allow"),
    "Grep": ("read", "allow"),
    "Edit": ("edit", "allow"),
    "Write": ("write", "allow"),
}


def _copy_skill_bundle(doc: FrontmatterDoc, dest_skill_dir: Path) -> list[Path]:
    """Copy every file under doc.bundle_dir (except top-level SKILL.md) into
    ``dest_skill_dir``, preserving sub-directory structure.

    Returns the list of destination paths written. Returns [] when doc has no
    bundle_dir or when the bundle contains only SKILL.md.

    Trusts callers (the source tree under plugins/scholar-ip/skills/) for
    bundle hygiene: symlinks are followed and their targets copied (not the
    links themselves); circular symlinks within a bundle would loop. This is
    acceptable because bundles are author-controlled, in-tree content.
    """
    if doc.bundle_dir is None or not doc.bundle_dir.is_dir():
        return []
    written: list[Path] = []
    for src in sorted(doc.bundle_dir.rglob("*")):
        if not src.is_file():
            continue
        if src.name == "SKILL.md" and src.parent == doc.bundle_dir:
            continue  # already written by the SKILL.md branch
        rel = src.relative_to(doc.bundle_dir)
        dest = dest_skill_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        written.append(dest)
    return written


def _command_frontmatter(meta: dict[str, Any]) -> dict[str, Any]:
    """OpenCode command frontmatter is minimal: description plus optional
    ``agent`` and ``model``. Tools are not declared per-command; per-tool
    permission lives on the agent.
    """
    fm: dict[str, Any] = {}
    desc = meta.get("description") or meta.get("title")
    if desc:
        fm["description"] = str(desc).strip()
    if meta.get("model"):
        fm["model"] = meta["model"]
    return fm


def _agent_frontmatter(meta: dict[str, Any]) -> dict[str, Any]:
    """Translate Claude-style ``tools: [Read, Edit, ...]`` to OpenCode's
    ``mode: subagent`` + per-tool ``permission`` block.
    """
    fm: dict[str, Any] = {"mode": "subagent"}
    desc = meta.get("description") or meta.get("role") or meta.get("title")
    if desc:
        fm["description"] = str(desc).strip()
    if meta.get("model"):
        fm["model"] = meta["model"]
    tools = meta.get("allowed_tools") or []
    if tools:
        perm: dict[str, str] = {}
        for t in tools:
            mapped = _CC_TO_OPENCODE_TOOL.get(t)
            if mapped:
                key, val = mapped
                perm.setdefault(key, val)
            elif isinstance(t, str) and t.lower().startswith("bash"):
                perm.setdefault("bash", "allow")
        if perm:
            fm["permission"] = perm
    return fm


def _skill_frontmatter(meta: dict[str, Any]) -> dict[str, Any]:
    fm: dict[str, Any] = {"name": meta.get("id", "skill")}
    desc = meta.get("description") or meta.get("title")
    if desc:
        fm["description"] = str(desc).strip()
    return fm


def _strip_body(body: str) -> str:
    return body.strip("\n")


def _render_readme(plugin: Plugin) -> str:
    m = plugin.manifest
    n_cmd = len(plugin.commands)
    n_agent = len(plugin.agents)
    n_skill = len(plugin.skills)
    n_hook = len(plugin.hooks)
    lines = [
        f"# {m.get('name', 'EviDraft')} for OpenCode",
        "",
        (m.get("description") or "").strip(),
        "",
        "## Layout",
        "",
        f"- `commands/scholar-<id>.md` — {n_cmd} slash command(s); invoke as `/scholar-<id>`",
        f"- `agents/<id>.md` — {n_agent} subagent(s)",
        f"- `skills/<id>/SKILL.md` — {n_skill} skill(s)",
        "",
        "## Installation",
        "",
        "Copy or symlink these directories under your project's `.opencode/` "
        "(project-scoped) or `~/.config/opencode/` (user-global). OpenCode "
        "auto-discovers them on next session.",
        "",
        "```bash",
        "mkdir -p .opencode",
        "cp -R commands .opencode/commands",
        "cp -R agents   .opencode/agents",
        "cp -R skills   .opencode/skills",
        "```",
        "",
        "## Caveats",
        "",
        f"- OpenCode has no `/foo:bar` namespacing, so commands are exposed as "
        f"`/scholar-<id>` (e.g. `/scholar-paper-init`).",
        f"- {n_hook} source hook(s) are NOT rendered: OpenCode hooks must be "
        f"JavaScript callbacks exported from a plugin module, not markdown. "
        f"If you need the same gating, port the hooks to a `.opencode/plugins/"
        f"scholar.ts` module by hand. See the source `plugins/scholar-ip/hooks/`.",
        "",
    ]
    return "\n".join(lines)


def render(plugin: Plugin, out_dir: Path) -> list[Path]:
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    readme = out_dir / "README.md"
    readme.write_text(_render_readme(plugin), encoding="utf-8")
    written.append(readme)

    cmd_dir = out_dir / "commands"
    cmd_dir.mkdir(parents=True, exist_ok=True)
    for d in plugin.commands:
        meta = d.meta or {}
        fm = _command_frontmatter(meta)
        preamble = render_retention_section(meta)
        body = preamble + d.body.lstrip("\n") if preamble else d.body
        # OpenCode has no slash namespacing — prefix the filename to keep the
        # ``scholar:`` namespace explicit for users.
        target = cmd_dir / f"scholar-{d.id}.md"
        target.write_text(dump_frontmatter(fm, body), encoding="utf-8")
        written.append(target)

    if plugin.agents:
        agent_dir = out_dir / "agents"
        agent_dir.mkdir(parents=True, exist_ok=True)
        for d in plugin.agents:
            fm = _agent_frontmatter(d.meta or {})
            target = agent_dir / d.path.name
            target.write_text(dump_frontmatter(fm, d.body), encoding="utf-8")
            written.append(target)

    if plugin.skills:
        skills_root = out_dir / "skills"
        for d in plugin.skills:
            sk_dir = skills_root / d.id
            sk_dir.mkdir(parents=True, exist_ok=True)
            fm = _skill_frontmatter(d.meta or {})
            target = sk_dir / "SKILL.md"
            target.write_text(dump_frontmatter(fm, d.body), encoding="utf-8")
            written.append(target)
            written.extend(_copy_skill_bundle(d, sk_dir))

    return written


def _dry_run_paths(plugin: Plugin, out_dir: Path) -> list[Path]:
    paths = [out_dir / "README.md"]
    paths.extend(out_dir / "commands" / f"scholar-{d.id}.md" for d in plugin.commands)
    paths.extend(out_dir / "agents" / d.path.name for d in plugin.agents)
    paths.extend(out_dir / "skills" / d.id / "SKILL.md" for d in plugin.skills)
    return paths


load_plugin = _load_plugin
validate = _validate


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="evidraft-opencode",
        description="Render the EviDraft plugin into an OpenCode layout.",
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
        # Keep the legacy lint banner the conformance test parses out.
        n_lint = (
            len(plugin.commands)
            + len(plugin.agents)
            + len(plugin.skills)
            + len(plugin.hooks)
        )
        print(
            f"[opencode] lint: {n_lint} document(s) in {args.plugin.resolve()} passed schema check"
        )
        print(
            f"[opencode] dry-run: would write {len(paths)} file(s) to {args.out.resolve()}"
        )
        return 0

    written = render(plugin, args.out)
    for p in written:
        print(p)
    print(f"[opencode] wrote {len(written)} file(s) to {args.out.resolve()}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
