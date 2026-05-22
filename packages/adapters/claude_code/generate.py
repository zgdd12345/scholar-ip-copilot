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
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Any

from .._shared.bundle import bundle_dest_paths, copy_skill_bundle
from .._shared.loader import (
    Plugin,
    dump_frontmatter,
    load_plugin as _load_plugin,
    render_retention_section,
    validate as _validate,
)


# ---------------------------------------------------------------------------
# Subagent dispatch plan
# ---------------------------------------------------------------------------


def _short_role(agent_meta: dict[str, Any], agent_id: str) -> str:
    """Return a one-line "when to dispatch" hint for ``agent_id``.

    Preference order: source ``role`` first sentence -> ``title`` -> ``description``
    first sentence -> a generic fallback derived from the agent id. The hint is
    collapsed onto a single line and trimmed so the rendered Dispatch plan
    stays scannable.
    """
    role = agent_meta.get("role") or ""
    if isinstance(role, str) and role.strip():
        text = " ".join(role.split())
        first = text.split(". ", 1)[0]
        return first.rstrip(".") + "."
    title = agent_meta.get("title") or ""
    if isinstance(title, str) and title.strip():
        return str(title).strip().strip('"').rstrip(".") + "."
    desc = agent_meta.get("description") or ""
    if isinstance(desc, str) and desc.strip():
        text = " ".join(desc.split())
        first = text.split(". ", 1)[0]
        return first.rstrip(".") + "."
    # Last-resort generic from the agent id.
    verb = "review"
    if "draft" in agent_id:
        verb = "draft"
    elif "analyst" in agent_id or "analyse" in agent_id or "analyze" in agent_id:
        verb = "analyse"
    elif "audit" in agent_id:
        verb = "audit"
    elif "verify" in agent_id or "check" in agent_id:
        verb = "verify"
    topic = agent_id.replace("-", " ")
    return f"to {verb} {topic}."


def _dispatch_plan_section(
    meta: dict[str, Any],
    agents_by_id: dict[str, dict[str, Any]],
) -> str:
    """If ``meta`` declares a non-empty ``subagents:`` list, return a
    ``## Dispatch plan`` markdown section. Otherwise return ``""``.

    The section uses Anthropic's canonical plain-English dispatch prose
    (`Use the <agent-id> subagent to ...`). When 4+ subagents are declared we
    additionally surface the superpowers parallel-agents pattern as a fenced
    pseudo-code block — the model picks sequential or parallel based on the
    work's actual dependency graph.
    """
    subs = meta.get("subagents") or []
    if not isinstance(subs, list) or not subs:
        return ""

    lines: list[str] = []
    lines.append("<!-- evidraft: dispatch-plan -->")
    lines.append("## Dispatch plan")
    lines.append("")
    lines.append(
        "This command is wired to dispatch one or more Claude Code subagents "
        "via the Task tool. The frontmatter `subagents:` field declares which "
        "agents are in scope; the steps below tell you when each one fires."
    )
    lines.append("")
    for sub_id in subs:
        sid = str(sub_id)
        ameta = agents_by_id.get(sid, {})
        hint = _short_role(ameta, sid)
        lines.append(f"- **`{sid}`** — {hint}")
        lines.append(
            f"  Dispatch instruction: **Use the `{sid}` subagent** to handle the "
            "responsibility above when its step fires below."
        )
    lines.append("")
    if len(subs) >= 4:
        lines.append(
            "When the steps above mark a block of agents as independent, "
            "dispatch them concurrently using the superpowers parallel-agents "
            "pattern:"
        )
        lines.append("")
        lines.append("```text")
        for sid in subs:
            lines.append(f'Task(subagent_type="{sid}", prompt="<fill from the matching step>")')
        lines.append(f"// All {len(subs)} run concurrently")
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Frontmatter translators
# ---------------------------------------------------------------------------


def _command_frontmatter(meta: dict[str, Any]) -> dict[str, Any]:
    """Map platform-neutral command meta -> Claude Code command frontmatter.

    Claude Code derives the slash name from the filename and namespaces it
    with the plugin's ``name`` field, so we do not emit a ``slash`` key.
    """
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
    return fm


def _agent_frontmatter(meta: dict[str, Any]) -> dict[str, Any]:
    fm: dict[str, Any] = {"name": meta.get("id", "agent")}
    desc = meta.get("description") or meta.get("role") or meta.get("title")
    if desc:
        fm["description"] = str(desc).strip()
    tools = meta.get("allowed_tools") or []
    if tools:
        fm["tools"] = list(tools)
    # Forward Claude-Code-recognised dispatch hints when the source frontmatter
    # declares them (per https://code.claude.com/docs/en/plugins-reference).
    # `model: inherit` is the implicit default and intentionally not emitted.
    model = meta.get("model")
    if model and model != "inherit":
        fm["model"] = str(model)
    effort = meta.get("effort")
    if effort:
        fm["effort"] = str(effort)
    return fm


def _skill_frontmatter(meta: dict[str, Any]) -> dict[str, Any]:
    fm: dict[str, Any] = {"name": meta.get("id", "skill")}
    desc = meta.get("description") or meta.get("title")
    if desc:
        fm["description"] = str(desc).strip()
    if meta.get("triggers"):
        fm["triggers"] = list(meta["triggers"])
    return fm


# ---------------------------------------------------------------------------
# Top-level manifest
# ---------------------------------------------------------------------------


def _build_plugin_json(plugin: Plugin) -> dict[str, Any]:
    """Emit the Claude Code plugin manifest.

    Per https://code.claude.com/docs/en/plugins-reference, ``name`` is the only
    required field and is used to namespace components (e.g. /scholar:foo).
    Components in ``commands/``, ``agents/``, ``skills/``, ``hooks/`` are
    auto-discovered at the plugin root — we deliberately do not list them.
    """
    m = plugin.manifest
    # ``displayName`` is intentionally omitted — it requires Claude Code
    # v2.1.143+ and is rejected by older CLIs at validate-time. The
    # platform-neutral manifest's ``name`` ("EviDraft") is human-facing;
    # CC's ``name`` field doubles as the slash namespace and must be
    # kebab-case, so we map from the platform-neutral ``id`` ("scholar").
    out: dict[str, Any] = {
        "name": m.get("id", "scholar"),
        "version": m.get("version", "0.0.1"),
        "description": (m.get("description") or "").strip(),
        "homepage": m.get("homepage"),
    }
    if m.get("license"):
        out["license"] = m["license"]
    authors = m.get("authors") or []
    if authors:
        first = authors[0] if isinstance(authors[0], dict) else {"name": authors[0]}
        out["author"] = first
    return {k: v for k, v in out.items() if v is not None and v != ""}


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Executable hook rendering
# ---------------------------------------------------------------------------


def _derive_event_and_matcher(meta: dict[str, Any]) -> tuple[str, str | None]:
    """Infer (event, matcher) for a hook's hooks.json entry.

    Priority:
      1. Explicit ``cc_event`` / ``cc_matcher`` fields in the source frontmatter.
      2. A ``triggers:`` entry shaped like ``<Event>:<matcher>:<path-glob>``
         (e.g. ``PostToolUse:Write|Edit:manuscript/**``).
      3. Fallback: event ``PostToolUse`` with no matcher.

    Path globs in (2) are discarded — the script's own check is responsible for
    path-level scoping, since Claude Code matchers do not reliably support
    arbitrary path patterns.
    """
    event = meta.get("cc_event")
    matcher = meta.get("cc_matcher")
    if event:
        return str(event), (str(matcher) if matcher else None)

    triggers = meta.get("triggers") or []
    if isinstance(triggers, list):
        for t in triggers:
            if not isinstance(t, str):
                continue
            parts = t.split(":", 2)
            if parts and parts[0] in {
                "SessionStart",
                "PostToolUse",
                "PreToolUse",
                "UserPromptSubmit",
                "Stop",
                "SubagentStop",
                "Notification",
                "PreCompact",
            }:
                return parts[0], (parts[1] if len(parts) > 1 and parts[1] else None)

    return "PostToolUse", None


def _render_executable_hooks(plugin: Plugin, out_dir: Path) -> list[Path]:
    """Emit ``<out_dir>/hooks/hooks.json`` and copy each executable script.

    Only hooks whose frontmatter declares ``executable_script:`` are wired.
    Additionally, if a standalone ``session-start.sh`` exists at the source
    ``hooks/`` directory (no companion .md), a ``SessionStart`` entry is
    synthesised so the session-start hook works without bumping the hook
    .md count.

    The function is idempotent: ``hooks.json`` is overwritten each render
    and stale executables are not removed (CC only consults files that
    hooks.json references).
    """
    src_hooks_dir = plugin.root / "hooks"
    written: list[Path] = []

    # event -> list of CC matcher entries
    entries: dict[str, list[dict[str, Any]]] = {}
    seen_scripts: set[str] = set()

    def _add(event: str, matcher: str | None, basename: str) -> None:
        cmd = '"${CLAUDE_PLUGIN_ROOT}"/hooks/' + basename
        entry: dict[str, Any] = {"hooks": [{"type": "command", "command": cmd}]}
        if matcher:
            entry["matcher"] = matcher
        entries.setdefault(event, []).append(entry)

    out_hooks_dir = out_dir / "hooks"

    for hook in plugin.hooks:
        script_field = (hook.meta or {}).get("executable_script")
        if not script_field:
            continue
        script_name = Path(str(script_field)).name
        src_script = src_hooks_dir / script_name
        if not src_script.is_file():
            # Skip silently; not all dev checkouts will have the script yet.
            continue
        out_hooks_dir.mkdir(parents=True, exist_ok=True)
        dest = out_hooks_dir / script_name
        shutil.copyfile(src_script, dest)
        mode = os.stat(src_script).st_mode
        os.chmod(dest, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        written.append(dest)
        seen_scripts.add(script_name)

        event, matcher = _derive_event_and_matcher(hook.meta or {})
        _add(event, matcher, script_name)

    # Synthesise the session-start hook (no companion .md) if its script is
    # present and was not already wired above.
    ss_src = src_hooks_dir / "session-start.sh"
    if ss_src.is_file() and "session-start.sh" not in seen_scripts:
        out_hooks_dir.mkdir(parents=True, exist_ok=True)
        dest = out_hooks_dir / "session-start.sh"
        shutil.copyfile(ss_src, dest)
        mode = os.stat(ss_src).st_mode
        os.chmod(dest, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        written.append(dest)
        _add("SessionStart", None, "session-start.sh")

    if entries:
        manifest_path = out_hooks_dir / "hooks.json"
        # CC schema requires the events nested under a top-level ``hooks`` key.
        sorted_entries = {k: entries[k] for k in sorted(entries)}
        manifest_path.write_text(
            json.dumps({"hooks": sorted_entries}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written.append(manifest_path)

        # Copy any sourced helper files alongside the executables (e.g.
        # ``_lib.sh`` — non-executable, sourced via `. "$(dirname $0)/_lib.sh"`).
        for helper in sorted(src_hooks_dir.glob("_*.sh")):
            dest = out_hooks_dir / helper.name
            shutil.copyfile(helper, dest)
            written.append(dest)

        # Sidecar lookup consumed by _lib.sh::hook_disabled_by_command. The
        # rendered command frontmatter no longer carries the source `hooks:`
        # field (CC only recognises description/argument-hint/allowed-tools),
        # so we project the per-command allowlist into a separate JSON the
        # PostToolUse hooks read at runtime. Format is intentionally minimal:
        #   - command name present, value = [] → all hooks disabled for that cmd
        #   - command name present, value = [a, b] → only a,b fire; others skip
        #   - command name absent → no opt-out declared → all hooks fire (legacy)
        cmd_hook_map: dict[str, list[str]] = {}
        for cmd in plugin.commands:
            meta = cmd.meta or {}
            if "hooks" not in meta:
                continue
            value = meta.get("hooks")
            if not isinstance(value, list):
                continue
            cmd_name = str(meta.get("id") or cmd.path.stem)
            cmd_hook_map[cmd_name] = [str(h) for h in value]
        if cmd_hook_map:
            ch_path = out_hooks_dir / "command-hooks.json"
            ch_path.write_text(
                json.dumps(
                    {"version": 1, "commands": dict(sorted(cmd_hook_map.items()))},
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            written.append(ch_path)

    return written


def render(plugin: Plugin, out_dir: Path) -> list[Path]:
    """Render ``plugin`` into ``out_dir``. Returns the list of written paths."""
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    manifest_dir = out_dir / ".claude-plugin"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / "plugin.json"
    manifest_path.write_text(
        json.dumps(_build_plugin_json(plugin), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    written.append(manifest_path)

    # Build an id -> agent-meta map so the command renderer can derive a
    # "when to dispatch" hint for each subagent declared on a command.
    agents_by_id: dict[str, dict[str, Any]] = {
        (d.meta or {}).get("id") or d.path.stem: (d.meta or {})
        for d in plugin.agents
    }

    cmd_dir = out_dir / "commands"
    cmd_dir.mkdir(parents=True, exist_ok=True)
    for d in plugin.commands:
        meta = d.meta or {}
        fm = _command_frontmatter(meta)
        preamble = render_retention_section(meta)
        body = preamble + d.body.lstrip("\n") if preamble else d.body
        dispatch = _dispatch_plan_section(meta, agents_by_id)
        if dispatch:
            # Idempotent append: only add a trailing dispatch plan if the
            # body does not already carry one (re-renders are no-ops).
            if "## Dispatch plan" not in body:
                if not body.endswith("\n"):
                    body = body + "\n"
                body = body + "\n" + dispatch + "\n"
        target = cmd_dir / d.path.name
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
            written.extend(copy_skill_bundle(d, sk_dir))

    written.extend(_render_executable_hooks(plugin, out_dir))

    return written


def _dry_run_paths(plugin: Plugin, out_dir: Path) -> list[Path]:
    paths = [out_dir / ".claude-plugin" / "plugin.json"]
    paths.extend(out_dir / "commands" / d.path.name for d in plugin.commands)
    paths.extend(out_dir / "agents" / d.path.name for d in plugin.agents)
    for d in plugin.skills:
        sk_dir = out_dir / "skills" / d.id
        paths.append(sk_dir / "SKILL.md")
        paths.extend(bundle_dest_paths(d, sk_dir))
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
