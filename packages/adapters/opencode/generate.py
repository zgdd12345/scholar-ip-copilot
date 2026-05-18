"""Planned OpenCode adapter (v0.2). For now: lint-only.

Running this module today loads the plugin and validates it against
``packages/core/schemas/command.schema.json``. The renderer prints a friendly
"not yet implemented" message instead of writing files.

See ``README.md`` in this directory for the intended output layout.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .._shared.loader import (
    Plugin,
    load_plugin as _load_plugin,
    validate as _validate,
)


_NOT_IMPLEMENTED_BANNER = (
    "[opencode] OpenCode adapter is planned for v0.2 and not yet implemented.\n"
    "[opencode] This invocation only validates the plugin source.\n"
    "[opencode] See packages/adapters/opencode/README.md for the intended layout."
)


def render(plugin: Plugin, out_dir: Path) -> list[Path]:
    """Stub renderer. Does not write any files."""
    print(_NOT_IMPLEMENTED_BANNER)
    return []


load_plugin = _load_plugin
validate = _validate


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="evidraft-opencode",
        description="(Planned) Render EviDraft into OpenCode layout. v0.1: lint-only.",
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

    print(_NOT_IMPLEMENTED_BANNER)

    if errors:
        print("Validation errors:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print(
            f"[opencode] lint: {len(errors)} validation issue(s) in {args.plugin.resolve()}"
        )
        return 1

    n = (
        len(plugin.commands)
        + len(plugin.agents)
        + len(plugin.skills)
        + len(plugin.hooks)
    )
    print(
        f"[opencode] lint: {n} document(s) in {args.plugin.resolve()} passed schema check"
    )
    if args.dry_run:
        print("[opencode] dry-run: nothing to write (stub adapter).")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
