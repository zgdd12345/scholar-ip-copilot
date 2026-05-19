"""Plugin manifest migration framework.

Reads plugin.yaml's manifest_version, walks the change log from there
to the target version, and produces either:
- a dry-run plan (list of changes), or
- an in-place rewrite.

v1.0.0 is the first versioned format; earlier (unversioned) plugins
are detected via the *absence* of manifest_version and treated as
manifest_version "0.0.0" for migration purposes.

Migrations are registered as `(from_version, to_version, fn)` triples.
The migrator builds the path between source and target via topological
sort over the registered triples; refuses if no path exists.
"""

from __future__ import annotations

import argparse
import copy
import datetime as _dt
import sys
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import yaml

# ---------------------------------------------------------------------------
# Types & registry
# ---------------------------------------------------------------------------

#: A migration function maps a plugin dict at `from_version` to a plugin dict
#: at `to_version`. It MUST be pure: no file I/O, no global state mutation.
MigrationFn = Callable[[dict], dict]


@dataclass(frozen=True)
class MigrationStep:
    """One edge in the migration graph."""

    from_version: str
    to_version: str
    fn: MigrationFn
    description: str = ""

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"MigrationStep({self.from_version} -> {self.to_version})"


@dataclass
class MigrationPlan:
    """The ordered sequence of steps that gets the plugin to the target."""

    source_version: str
    target_version: str
    steps: list[MigrationStep] = field(default_factory=list)

    @property
    def is_noop(self) -> bool:
        return not self.steps

    def describe(self) -> list[str]:
        if self.is_noop:
            return [f"no migrations needed (already at {self.target_version})"]
        out = []
        for step in self.steps:
            label = step.description or f"{step.from_version} -> {step.to_version}"
            out.append(f"{step.from_version} -> {step.to_version}: {label}")
        return out


# Registry keyed by (from_version, to_version). Multiple edges out of the same
# node are allowed (e.g., 1.0.0 -> 1.1.0 and 1.0.0 -> 2.0.0 could both exist).
_REGISTRY: dict[tuple[str, str], MigrationStep] = {}


def register(
    from_v: str, to_v: str, *, description: str = ""
) -> Callable[[MigrationFn], MigrationFn]:
    """Decorator: register a pure migration `from_v -> to_v`.

    Usage:

        @register("0.0.0", "1.0.0", description="add manifest_version")
        def _v0_to_v1(plugin: dict) -> dict:
            plugin.setdefault("manifest_version", "1.0.0")
            return plugin
    """

    def _decorate(fn: MigrationFn) -> MigrationFn:
        key = (from_v, to_v)
        if key in _REGISTRY:
            raise ValueError(f"duplicate migration registered for {from_v} -> {to_v}")
        _REGISTRY[key] = MigrationStep(
            from_version=from_v, to_version=to_v, fn=fn, description=description
        )
        return fn

    return _decorate


# ---------------------------------------------------------------------------
# Built-in migrations
# ---------------------------------------------------------------------------


@register(
    "0.0.0",
    "1.0.0",
    description="introduce manifest_version field (set to '1.0.0' if absent)",
)
def _v0_0_0_to_v1_0_0(plugin: dict) -> dict:
    """v0 -> v1: add `manifest_version: "1.0.0"`.

    Pure: receives a (deep-copied) dict, returns a new dict with the field set.
    No I/O, no logging — the framework handles both.
    """
    out = dict(plugin)
    out.setdefault("manifest_version", "1.0.0")
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_manifest(path: Path) -> dict:
    """Load a plugin.yaml from disk. Returns the parsed dict."""
    text = Path(path).read_text(encoding="utf-8")
    doc = yaml.safe_load(text)
    if not isinstance(doc, dict):
        raise ValueError(f"{path}: expected a YAML mapping at top level, got {type(doc).__name__}")
    return doc


def detect_version(plugin: dict) -> str:
    """Return the manifest_version of a parsed plugin dict.

    A plugin without `manifest_version` is treated as `"0.0.0"` — the
    sentinel for pre-v1 (unversioned) manifests.
    """
    v = plugin.get("manifest_version")
    if v is None:
        return "0.0.0"
    if not isinstance(v, str):
        raise ValueError(
            f"manifest_version must be a string, got {type(v).__name__}: {v!r}"
        )
    return v


def plan(plugin: dict, target_version: str) -> MigrationPlan:
    """Compute the ordered list of MigrationSteps from `plugin`'s version to target.

    Raises ValueError if no path exists in the registered graph.
    """
    source = detect_version(plugin)
    if source == target_version:
        return MigrationPlan(source_version=source, target_version=target_version, steps=[])

    steps = _shortest_path(source, target_version)
    if steps is None:
        raise ValueError(
            f"no migration path from {source} to {target_version}"
        )
    return MigrationPlan(source_version=source, target_version=target_version, steps=steps)


def apply(
    plugin: dict, target_version: str, *, dry_run: bool = False
) -> tuple[dict, list[str]]:
    """Apply the planned migrations to `plugin`.

    Returns (resulting_dict, log_lines). When `dry_run=True`, the input is not
    modified — the function still computes the would-be result so callers can
    diff. When `dry_run=False`, the same value is returned but the plan is
    fully executed and the log records every step.

    Raises ValueError if no migration path exists (see `plan`).
    """
    p = plan(plugin, target_version)
    log: list[str] = []
    log.append(
        f"source manifest_version={p.source_version}, target={p.target_version}"
    )

    if p.is_noop:
        log.append(f"no migrations needed (already at {target_version})")
        return copy.deepcopy(plugin), log

    current = copy.deepcopy(plugin)
    for step in p.steps:
        label = step.description or f"{step.from_version} -> {step.to_version}"
        log.append(f"applying {step.from_version} -> {step.to_version}: {label}")
        current = step.fn(copy.deepcopy(current))
        # Guarantee the new manifest_version is set after the step, even if the
        # migration fn forgot to do so.
        current.setdefault("manifest_version", step.to_version)
        if current.get("manifest_version") != step.to_version:
            # The migration may have intentionally bumped beyond the edge; if
            # not, normalise.
            current["manifest_version"] = step.to_version

    if dry_run:
        log.append("dry-run: no files written")
    return current, log


# ---------------------------------------------------------------------------
# Internal: path finding
# ---------------------------------------------------------------------------


def _shortest_path(source: str, target: str) -> list[MigrationStep] | None:
    """BFS over the registered graph from `source` to `target`.

    Returns the ordered list of MigrationSteps, or None if unreachable. BFS
    over the edge set is a topological sort for our acyclic version graph,
    and yields a deterministic shortest path.
    """
    if source == target:
        return []
    # Adjacency: from_version -> [MigrationStep, ...]
    adj: dict[str, list[MigrationStep]] = {}
    for step in _REGISTRY.values():
        adj.setdefault(step.from_version, []).append(step)

    if source not in adj:
        return None

    # BFS
    queue: deque[tuple[str, list[MigrationStep]]] = deque([(source, [])])
    visited: set[str] = {source}
    while queue:
        node, path_so_far = queue.popleft()
        for step in adj.get(node, []):
            if step.to_version == target:
                return path_so_far + [step]
            if step.to_version not in visited:
                visited.add(step.to_version)
                queue.append((step.to_version, path_so_far + [step]))
    return None


# ---------------------------------------------------------------------------
# File I/O wrapper (the only impure part of the module)
# ---------------------------------------------------------------------------


def _write_log(plugin_path: Path, log: list[str]) -> Path:
    """Write a migrate-<ts>.log next to plugin.yaml. Returns the log path."""
    ts = _dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    log_path = plugin_path.parent / f"migrate-{ts}.log"
    log_path.write_text("\n".join(log) + "\n", encoding="utf-8")
    return log_path


def _dump_yaml(doc: dict) -> str:
    """Serialise a plugin dict back to YAML.

    `sort_keys=False` so existing field order is preserved best-effort, and
    `default_flow_style=False` keeps block style. Note pyyaml does not
    perfectly preserve comments / quoting — for v1.0.0 we accept that
    migrations may rewrite the file in canonical form.
    """
    return yaml.safe_dump(doc, sort_keys=False, default_flow_style=False, allow_unicode=True)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m packages.core.src.migrate",
        description="Migrate a scholar-ip-copilot plugin.yaml between manifest_version values.",
    )
    parser.add_argument(
        "--plugin",
        required=True,
        type=Path,
        help="Path to plugin.yaml (e.g. plugins/scholar-ip/plugin.yaml).",
    )
    parser.add_argument(
        "--to",
        required=True,
        dest="target",
        help="Target manifest_version (semver). Example: 1.0.0",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the migration plan; do not rewrite the file.",
    )
    args = parser.parse_args(argv)

    plugin_path: Path = args.plugin
    if not plugin_path.exists():
        print(f"error: {plugin_path} does not exist", file=sys.stderr)
        return 2

    plugin = load_manifest(plugin_path)
    try:
        result, log = apply(plugin, args.target, dry_run=args.dry_run)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for line in log:
        print(line)

    if args.dry_run:
        return 0

    # If there were no steps to apply, leave the file untouched.
    source = detect_version(plugin)
    if source == args.target:
        return 0

    plugin_path.write_text(_dump_yaml(result), encoding="utf-8")
    log_path = _write_log(plugin_path, log)
    print(f"wrote {plugin_path}")
    print(f"log: {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ---------------------------------------------------------------------------
# Future contributors
# ---------------------------------------------------------------------------
#
# To add a migration, register a decorated pure function:
#
#     @register("1.0.0", "1.1.0", description="rename `foo` to `bar`")
#     def _v1_0_to_v1_1(plugin: dict) -> dict:
#         out = dict(plugin)
#         if "foo" in out:
#             out["bar"] = out.pop("foo")
#         return out
#
# Each registered function MUST be pure (input dict -> output dict, no I/O).
# The framework handles file I/O and the migrate-<ts>.log next to plugin.yaml.
# Multi-step migrations are composed automatically via BFS over the registered
# edges; if any intermediate edge is missing, the migrator refuses with a
# clear "no migration path from X to Y" error.
