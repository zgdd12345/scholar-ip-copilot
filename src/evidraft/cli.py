"""Command-line interface for the deterministic EviDraft core."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .claude_install import install_claude_plugin
from .codex_install import codex_project_mode_preflight, reinstall_codex_plugin
from .core import (
    append_evidence,
    audit_evidence,
    migrate_project,
    resolve_evidence,
    store_snapshot,
    workflow_finalize,
    workflow_prepare_output,
    workflow_preflight,
    workflow_validate_paper_explanation_return,
)
from .install import remove_codex_project_skills, sync_codex_skills
from .release import release_package_drift, render_plugin_package
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
    prepare_output = workflow_commands.add_parser("prepare-output")
    prepare_output.add_argument("operation")
    prepare_output.add_argument("--target", required=True)
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
    audit = evidence_commands.add_parser("audit")
    audit.add_argument("--id", action="append", default=[])

    snapshot = commands.add_parser("snapshot")
    snapshot_commands = snapshot.add_subparsers(dest="snapshot_command", required=True)
    store = snapshot_commands.add_parser("store")
    store.add_argument("url")
    store.add_argument("input", type=Path)
    render = commands.add_parser("render")
    render.add_argument("--host", required=True, choices=[host.value for host in Host])
    render.add_argument("--plugin", required=True, type=Path)
    render.add_argument("--out", required=True, type=Path)
    package = commands.add_parser("package")
    package.add_argument("--plugin", required=True, type=Path)
    package.add_argument("--out", required=True, type=Path)
    package.add_argument("--check", action="store_true")
    sync = commands.add_parser("sync-codex-skills")
    sync.add_argument("--source", required=True, type=Path)
    sync.add_argument("--dest", required=True, type=Path)
    install_codex_plugin = commands.add_parser("install-codex-plugin")
    install_codex_plugin.add_argument("--repo-root", required=True, type=Path)
    install_codex_plugin.add_argument("--marketplace", required=True, type=Path)
    install_codex_plugin.add_argument("--plugin", required=True, type=Path)
    install_codex_plugin.add_argument("--plugin-creator", type=Path)
    install_claude_plugin_parser = commands.add_parser("install-claude-plugin")
    install_claude_plugin_parser.add_argument("--repo-root", required=True, type=Path)
    remove_project_skills = commands.add_parser("remove-codex-project-skills")
    remove_project_skills.add_argument("--dest", required=True, type=Path)
    project_mode_preflight = commands.add_parser("codex-project-mode-preflight")
    project_mode_preflight.add_argument("--repo-root", required=True, type=Path)
    clean = commands.add_parser("clean-rendered")
    clean.add_argument("--out", required=True, type=Path)
    paper_explanation = commands.add_parser("paper-explanation")
    paper_explanation_commands = paper_explanation.add_subparsers(
        dest="paper_explanation_command", required=True
    )
    validate_return = paper_explanation_commands.add_parser("validate-return")
    validate_return.add_argument("--bundle", required=True, type=Path)
    validate_return.add_argument("--task-id", required=True)
    validate_return.add_argument("--attempt", required=True, type=int)
    validate_return.add_argument(
        "--packet-json",
        help="JSON object; omit or pass '-' to read the exact return from stdin.",
    )
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
        )
        print(
            json.dumps(
                {"operation": result.operation, "warnings": result.warnings}
            )
        )
    elif args.command == "workflow" and args.workflow_command == "prepare-output":
        result = workflow_prepare_output(args.root, args.operation, args.target)
        print(
            json.dumps(
                {"operation": result.operation, "warnings": result.warnings}
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
    elif args.command == "evidence" and args.evidence_command == "audit":
        result = audit_evidence(args.root, identifiers=args.id)
        print(
            json.dumps(
                {
                    "valid": result.valid,
                    "findings": result.findings,
                    "checked_ids": result.checked_ids,
                },
                sort_keys=True,
            )
        )
    elif args.command == "snapshot" and args.snapshot_command == "store":
        print(store_snapshot(args.root, args.url, args.input.read_bytes()))
    elif args.command == "render":
        written = render_plugin(args.plugin, args.out, Host(args.host))
        print(json.dumps({"host": args.host, "written": len(written)}))
    elif args.command == "package":
        if args.check:
            findings = release_package_drift(args.plugin, args.out)
            for finding in findings:
                print(finding)
            return 1 if findings else 0
        written = render_plugin_package(args.plugin, args.out)
        print(json.dumps({"written": len(written), "output": str(args.out.resolve())}))
    elif args.command == "sync-codex-skills":
        installed = sync_codex_skills(args.source, args.dest)
        print(json.dumps({"installed": len(installed), "destination": str(args.dest.resolve())}))
    elif args.command == "install-codex-plugin":
        result = reinstall_codex_plugin(
            args.repo_root,
            args.marketplace,
            args.plugin,
            args.plugin_creator,
        )
        print(
            json.dumps(
                {
                    "plugin_ref": result.plugin_ref,
                    "installed_version": result.installed_version,
                }
            )
        )
    elif args.command == "install-claude-plugin":
        result = install_claude_plugin(args.repo_root)
        print(
            json.dumps(
                {
                    "marketplace_added": result.marketplace_added,
                    "plugin_ref": result.plugin_ref,
                }
            )
        )
    elif args.command == "remove-codex-project-skills":
        removed = remove_codex_project_skills(args.dest)
        print(
            json.dumps(
                {
                    "removed": [str(path) for path in removed],
                    "destination": str(args.dest.resolve()),
                }
            )
        )
    elif args.command == "codex-project-mode-preflight":
        codex_project_mode_preflight(args.repo_root)
        print(json.dumps({"ready": True, "mode": "project-skills"}))
    elif args.command == "clean-rendered":
        removed = clean_rendered(args.out)
        print(json.dumps({"removed": len(removed), "output": str(args.out.resolve())}))
    elif (
        args.command == "paper-explanation"
        and args.paper_explanation_command == "validate-return"
    ):
        raw = sys.stdin.read() if args.packet_json in (None, "-") else args.packet_json
        result = workflow_validate_paper_explanation_return(
            args.bundle,
            json.loads(raw),
            expected_task_id=args.task_id,
            expected_attempt=args.attempt,
        )
        print(
            json.dumps(
                {
                    "valid": True,
                    "task_id": result["task_id"],
                    "attempt": result["attempt"],
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
