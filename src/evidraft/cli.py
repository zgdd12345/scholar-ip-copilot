"""Command-line interface for the deterministic EviDraft core."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .core import (
    append_evidence,
    migrate_project,
    resolve_evidence,
    store_snapshot,
    workflow_finalize,
    workflow_preflight,
)
from .install import sync_codex_skills
from .render import Host, clean_rendered, render_plugin


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="evidraft")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("migrate")
    workflow = commands.add_parser("workflow")
    workflow_commands = workflow.add_subparsers(dest="workflow_command", required=True)
    preflight = workflow_commands.add_parser("preflight")
    preflight.add_argument("operation")
    preflight.add_argument("--read-target", action="append", default=[])
    preflight.add_argument("--target", action="append", default=[])
    preflight.add_argument("--evidence-id", action="append", default=[])
    finalize = workflow_commands.add_parser("finalize")
    finalize.add_argument("--directory", required=True)
    finalize.add_argument("--pattern", default="*")
    finalize.add_argument("--keep-last", type=int)
    finalize.add_argument("--max-age-days", type=int)

    evidence = commands.add_parser("evidence")
    evidence_commands = evidence.add_subparsers(dest="evidence_command", required=True)
    append = evidence_commands.add_parser("append")
    append.add_argument("record", help="JSON evidence object without id")
    resolve = evidence_commands.add_parser("resolve")
    resolve.add_argument("id")

    snapshot = commands.add_parser("snapshot")
    snapshot_commands = snapshot.add_subparsers(dest="snapshot_command", required=True)
    store = snapshot_commands.add_parser("store")
    store.add_argument("url")
    store.add_argument("input", type=Path)
    render = commands.add_parser("render")
    render.add_argument("--host", required=True, choices=[host.value for host in Host])
    render.add_argument("--plugin", required=True, type=Path)
    render.add_argument("--out", required=True, type=Path)
    sync = commands.add_parser("sync-codex-skills")
    sync.add_argument("--source", required=True, type=Path)
    sync.add_argument("--dest", required=True, type=Path)
    clean = commands.add_parser("clean-rendered")
    clean.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "migrate":
        result = migrate_project(args.root)
        print(json.dumps({"changed": result.changed, "quarantined": result.quarantined}))
    elif args.command == "workflow" and args.workflow_command == "preflight":
        result = workflow_preflight(
            args.root,
            args.operation,
            read_paths=args.read_target,
            target_paths=args.target,
            evidence_ids=args.evidence_id,
        )
        print(
            json.dumps(
                {"operation": result.operation, "scope": result.scope, "warnings": result.warnings}
            )
        )
    elif args.command == "workflow" and args.workflow_command == "finalize":
        retention = {
            "directory": args.directory,
            "pattern": args.pattern,
            "keep_last": args.keep_last,
            "max_age_days": args.max_age_days,
        }
        result = workflow_finalize(args.root, retention=retention)
        print(json.dumps({"removed": [str(path) for path in result.removed]}))
    elif args.command == "evidence" and args.evidence_command == "append":
        print(json.dumps(append_evidence(args.root, json.loads(args.record)), sort_keys=True))
    elif args.command == "evidence" and args.evidence_command == "resolve":
        print(json.dumps(resolve_evidence(args.root, args.id), sort_keys=True))
    elif args.command == "snapshot" and args.snapshot_command == "store":
        print(store_snapshot(args.root, args.url, args.input.read_bytes()))
    elif args.command == "render":
        written = render_plugin(args.plugin, args.out, Host(args.host))
        print(json.dumps({"host": args.host, "written": len(written)}))
    elif args.command == "sync-codex-skills":
        installed = sync_codex_skills(args.source, args.dest)
        print(json.dumps({"installed": len(installed), "destination": str(args.dest.resolve())}))
    elif args.command == "clean-rendered":
        removed = clean_rendered(args.out)
        print(json.dumps({"removed": len(removed), "output": str(args.out.resolve())}))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
