"""Render the seven EviDraft workflows for each supported host."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from .legacy import V1_AGENTS, V1_COMMANDS, V1_HOOK_FILES, V1_SKILLS
from .transaction import replace_owned_tree


_WORKFLOW_SCHEMA = Path(__file__).resolve().parent / "schemas" / "workflow.schema.json"
EXPECTED_ACTIONS = {
    "using": {"run"},
    "scope": {"run"},
    "research": {"guide", "reading-list", "deep"},
    "paper": {"init", "lit", "idea", "code-audit", "experiment", "review", "draft", "check", "venue"},
    "patent": {"init", "scout", "prior-art", "disclosure", "claims", "review"},
    "polish": {"run"},
    "xreview": {"run"},
}


class Host(str, Enum):
    CLAUDE = "claude"
    CODEX = "codex"
    OPENCODE = "opencode"


@dataclass(frozen=True)
class HostProfile:
    host: Host
    invocation: str
    private_root: Path
    spec_home: str
    role_spec: str
    role_dispatch: str
    model_tiers: tuple[tuple[str, str], ...]
    emits_agents: bool
    hook_projection: tuple[str, ...] = ()


HOST_PROFILES = {
    Host.CLAUDE: HostProfile(
        host=Host.CLAUDE,
        invocation="/scholar:<workflow> [action]",
        private_root=Path("private"),
        spec_home="`${{CLAUDE_PLUGIN_ROOT}}/private/workflows/{workflow}/workflow.yaml`",
        role_spec="${CLAUDE_PLUGIN_ROOT}/private/roles/modes/<mode>.md",
        role_dispatch=(
            "For every selected action's role assignment, dispatch the declared role and mode "
            "with this model mapping: fast -> haiku, standard -> sonnet, deep -> opus. "
            "The role file uses `inherit`; the action assignment is authoritative.\n"
        ),
        model_tiers=(("fast", "haiku"), ("standard", "sonnet"), ("deep", "opus")),
        emits_agents=True,
    ),
    Host.CODEX: HostProfile(
        host=Host.CODEX,
        invocation="$scholar-<workflow> [action]",
        private_root=Path("skills/.evidraft-private"),
        spec_home="`workflow.yaml`",
        role_spec="../.evidraft-private/roles/modes/<mode>.md",
        role_dispatch=(
            "For every selected action's role assignment, resolve the declared mode in "
            "`../.evidraft-private/roles/roles.yaml` and load exactly one private mode spec at "
            "`../.evidraft-private/roles/modes/<mode>.md`. The mode spec is authoritative for "
            "tools, responsibilities, constraints, and output contracts. Map fast, standard, "
            "and deep to the closest available host effort levels.\n"
        ),
        model_tiers=(("fast", "low"), ("standard", "medium"), ("deep", "high")),
        emits_agents=False,
    ),
    Host.OPENCODE: HostProfile(
        host=Host.OPENCODE,
        invocation="/scholar-<workflow> [action]",
        private_root=Path("private"),
        spec_home="`.opencode/private/workflows/{workflow}/workflow.yaml`",
        role_spec=".opencode/private/roles/modes/<mode>.md",
        role_dispatch=(
            "For every selected action's role assignment, dispatch the declared role and mode. "
            "Map fast, standard, and deep to the closest available host effort levels.\n"
        ),
        model_tiers=(("fast", "low"), ("standard", "medium"), ("deep", "high")),
        emits_agents=True,
    ),
}


@dataclass(frozen=True)
class Workflow:
    id: str
    description: str
    actions: dict[str, dict[str, Any]]
    root: Path


def load_workflows(plugin_root: Path) -> dict[str, Workflow]:
    plugin_root = plugin_root.resolve()
    schema = json.loads(_WORKFLOW_SCHEMA.read_text(encoding="utf-8"))
    workflows: dict[str, Workflow] = {}
    for workflow_path in sorted((plugin_root / "workflows").glob("*/workflow.yaml")):
        raw = yaml.safe_load(workflow_path.read_text(encoding="utf-8")) or {}
        jsonschema.validate(raw, schema)
        workflow_id = str(raw["id"])
        if workflow_id in workflows:
            raise ValueError(f"duplicate workflow id: {workflow_id}")
        workflows[workflow_id] = Workflow(
            id=workflow_id,
            description=str(raw["description"]),
            actions=dict(raw["actions"]),
            root=workflow_path.parent,
        )
    return workflows


def _validate_plugin_source(plugin_root: Path) -> dict[str, Workflow]:
    """Validate every source dependency before the output tree is touched."""
    workflows = load_workflows(plugin_root)
    if set(workflows) != set(EXPECTED_ACTIONS):
        raise ValueError("v2 source must define exactly seven canonical workflows")
    for workflow_id, expected in EXPECTED_ACTIONS.items():
        if set(workflows[workflow_id].actions) != expected:
            raise ValueError(f"unexpected action set for workflow {workflow_id}")
    roles = _load_roles(plugin_root)
    if len(roles) != 6:
        raise ValueError("v2 source must define exactly six semantic roles")
    mode_specs = _load_mode_specs(plugin_root)
    declared_modes = {
        str(mode)
        for role in roles.values()
        for mode in role.get("modes", [])
    }
    if set(mode_specs) != declared_modes or len(declared_modes) != 16:
        raise ValueError("v2 source must map exactly 16 role modes to private specs")
    for mode, spec in mode_specs.items():
        metadata, _body = _split_frontmatter(spec.read_text(encoding="utf-8"))
        if metadata.get("id") != mode:
            raise ValueError(f"role mode spec id mismatch: {spec}")
    policy_path = plugin_root / "policies" / "policy.yaml"
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    if not isinstance(policy, dict) or not isinstance(policy.get("policies"), dict):
        raise ValueError(f"invalid policy source: {policy_path}")
    if set(policy["policies"]) != {"workspace-safety", "scope", "evidence-integrity"}:
        raise ValueError("v2 source must define exactly three public policies")
    capability_root = plugin_root / "capabilities"
    capability_index = yaml.safe_load(
        (capability_root / "index.yaml").read_text(encoding="utf-8")
    )
    capabilities = capability_index.get("capabilities", {})
    if capability_index.get("format_version") != 2 or len(capabilities) != 26:
        raise ValueError("v2 source must map exactly 26 private capabilities")
    for entry in capabilities.values():
        spec = capability_root / str(entry["spec"])
        if not spec.is_file():
            raise FileNotFoundError(spec)
    required_resources = (
        plugin_root / "plugin.yaml",
        plugin_root / "templates" / "paper-project" / "manuscript" / "main.tex",
        plugin_root / "templates" / "patent-project" / ".evidraft" / "project.yaml",
        plugin_root / "schemas" / "project.schema.json",
        plugin_root / "schemas" / "evidence.schema.json",
        plugin_root / "docs" / "architecture.md",
        plugin_root / "README.md",
    )
    for resource in required_resources:
        if not resource.is_file():
            raise FileNotFoundError(resource)
    for workflow in workflows.values():
        router = workflow.root / "SKILL.md"
        if not router.is_file():
            raise FileNotFoundError(router)
        for action in workflow.actions.values():
            procedure = workflow.root / str(action["procedure"])
            if not procedure.is_file():
                raise FileNotFoundError(procedure)
    return workflows


def _load_roles(plugin_root: Path) -> dict[str, dict[str, Any]]:
    raw = yaml.safe_load((plugin_root / "roles" / "roles.yaml").read_text(encoding="utf-8"))
    return dict(raw["roles"])


def _load_policies(plugin_root: Path) -> dict[str, dict[str, Any]]:
    raw = yaml.safe_load((plugin_root / "policies" / "policy.yaml").read_text(encoding="utf-8"))
    return dict(raw["policies"])


def _load_mode_specs(plugin_root: Path) -> dict[str, Path]:
    raw = yaml.safe_load((plugin_root / "roles" / "roles.yaml").read_text(encoding="utf-8"))
    specs: dict[str, Path] = {}
    for tier in raw["tiers"].values():
        for mode, relative in tier["mode_specs"].items():
            if mode in specs:
                raise ValueError(f"duplicate role mode spec: {mode}")
            spec = plugin_root / "roles" / str(relative)
            if not spec.is_file():
                raise FileNotFoundError(spec)
            specs[str(mode)] = spec
    return specs


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        raise ValueError("role mode spec must start with YAML frontmatter")
    _start, header, body = text.split("---", 2)
    metadata = yaml.safe_load(header)
    if not isinstance(metadata, dict):
        raise ValueError("role mode spec frontmatter must be a mapping")
    return metadata, body


def _frontmatter(description: str, body: str, **extra: Any) -> str:
    metadata = {"description": description, **extra}
    return "---\n" + yaml.safe_dump(metadata, sort_keys=False).strip() + "\n---\n\n" + body


def _router_body(
    workflow: Workflow, profile: HostProfile, workspace_safety: dict[str, Any]
) -> str:
    source = (workflow.root / "SKILL.md").read_text(encoding="utf-8")
    if source.startswith("---\n"):
        _, _, remainder = source.partition("\n---\n")
        source = remainder.lstrip("\n")
    spec_home = profile.spec_home.format(workflow=workflow.id)
    preamble = (
        f"Spec home: {spec_home}. Resolve the action there before loading a stage.\n"
        "Resolve every output placeholder from the action inputs. Before any write, run "
        "`evidraft workflow preflight <workflow>.<action> --target <each concrete write path> "
        "--evidence-id <each current evidence id>`; repeat each flag as needed and omit it "
        "when the action has none. For `xreview.run`, additionally pass the reviewed input as "
        "`--read-target <target>` and its concrete `.evidraft/reviews/...` output as `--target`. "
        "Never pass unresolved `<...>` placeholders. Then "
        "after completion inspect the selected action's `retention`. If it is non-empty, "
        "run `evidraft workflow finalize --directory <directory> --pattern <pattern> "
        "--keep-last <keep_last> --max-age-days <max_age_days>` using its declared values; "
        "if retention is empty, skip finalize.\n"
        "Apply `policy:workspace-safety`: use only its default allowed tools and never invoke "
        f"{', '.join(workspace_safety['tool_access']['forbidden_tool_patterns'])}.\n"
        f"{profile.role_dispatch}\n"
    )
    return preamble + source


def _role_body(
    role_id: str,
    role: dict[str, Any],
    profile: HostProfile,
    workspace_safety: dict[str, Any],
) -> str:
    modes = ", ".join(f"`{mode}`" for mode in role.get("modes", []))
    body = (
        f"# {role_id}\n\n{role['description']}\n\n"
        f"Supported modes: {modes}.\n"
        "Resolve the assigned mode in `roles.yaml`, then load exactly one private mode spec at "
        f"`{profile.role_spec}` before acting. The mode spec is authoritative for tools, "
        "responsibilities, constraints, and output contracts. "
        "Use only the mode and inputs assigned by the selected workflow action. "
        "Never invoke tools forbidden by policy:workspace-safety: "
        f"{', '.join(workspace_safety['tool_access']['forbidden_tool_patterns'])}. "
        "Return findings to the workflow aggregator; do not write shared outputs concurrently.\n"
    )
    extra: dict[str, Any] = {}
    if profile.host is Host.CLAUDE:
        extra["name"] = role_id
        extra["model"] = "inherit"
        extra["tools"] = list(workspace_safety["tool_access"]["default_allowed_tools"])
    elif profile.host is Host.OPENCODE:
        extra["mode"] = "subagent"
        extra["permission"] = {"bash": {"rm -rf*": "deny", "sudo*": "deny"}}
    return _frontmatter(str(role["description"]), body, **extra)


def _write_text(root: Path, relative: Path, text: str) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _copy_capabilities(plugin_root: Path, stage_root: Path, profile: HostProfile) -> None:
    source_root = plugin_root / "capabilities"
    relative_root = profile.private_root / "capabilities"
    for source in sorted(path for path in source_root.rglob("*") if path.is_file()):
        relative = relative_root / source.relative_to(source_root)
        target = stage_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())


def _copy_private_resources(
    plugin_root: Path, stage_root: Path, profile: HostProfile
) -> None:
    private_root = profile.private_root
    _write_text(
        stage_root,
        private_root / "plugin.yaml",
        (plugin_root / "plugin.yaml").read_text(encoding="utf-8"),
    )
    _write_text(
        stage_root,
        private_root / "README.md",
        (plugin_root / "README.md").read_text(encoding="utf-8"),
    )
    for resource_name in ("templates", "schemas", "docs"):
        source_root = plugin_root / resource_name
        for source in sorted(path for path in source_root.rglob("*") if path.is_file()):
            relative = private_root / resource_name / source.relative_to(source_root)
            target = stage_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())


def _copy_workflow_bundle(
    stage_root: Path, workflow: Workflow, relative_root: Path, profile: HostProfile
) -> None:
    _write_text(
        stage_root,
        relative_root / "workflow.yaml",
        (workflow.root / "workflow.yaml").read_text(encoding="utf-8"),
    )
    for procedure in sorted((workflow.root / "stages").glob("*.md")):
        text = procedure.read_text()
        if profile.host is Host.CODEX:
            for resource in ("capabilities", "roles", "policies", "templates", "schemas"):
                text = text.replace(
                    f"../../../{resource}/", f"../../.evidraft-private/{resource}/"
                )
        _write_text(stage_root, relative_root / "stages" / procedure.name, text)


def _codex_manifest() -> dict[str, Any]:
    return {
        "name": "scholar",
        "version": "2.0.0",
        "description": "Evidence-grounded academic and patent workflows.",
        "skills": "./skills/",
        "license": "MIT",
        "author": {"name": "scholar-ip-copilot contributors"},
        "interface": {
            "displayName": "EviDraft",
            "shortDescription": "Evidence-grounded research and patent workflows",
            "longDescription": (
                "Seven compact workflows for literature, papers, patents, evidence, and review."
            ),
            "developerName": "scholar-ip-copilot contributors",
            "category": "Productivity",
            "defaultPrompt": [
                "Orient me in this EviDraft project.",
                "Continue the evidence-backed paper workflow.",
                "Review the current patent disclosure and claims.",
            ],
            "capabilities": ["Read", "Write", "Research"],
        },
    }


def _stage_render(plugin_root: Path, stage_root: Path, host: Host) -> list[Path]:
    profile = HOST_PROFILES[host]
    workflows = load_workflows(plugin_root)
    roles = _load_roles(plugin_root)
    workspace_safety = _load_policies(plugin_root)["workspace-safety"]
    for workflow in workflows.values():
        body = _router_body(workflow, profile, workspace_safety)
        if host is Host.CLAUDE:
            text = _frontmatter(workflow.description, body, **{"argument-hint": "<action> [args]"})
            _write_text(stage_root, Path("commands") / f"{workflow.id}.md", text)
            bundle_root = Path("private") / "workflows" / workflow.id
        elif host is Host.CODEX:
            text = _frontmatter(workflow.description, body, name=f"scholar-{workflow.id}")
            bundle_root = Path("skills") / f"scholar-{workflow.id}"
            _write_text(stage_root, bundle_root / "SKILL.md", text)
        else:
            text = _frontmatter(workflow.description, body)
            _write_text(stage_root, Path("commands") / f"scholar-{workflow.id}.md", text)
            bundle_root = Path("private") / "workflows" / workflow.id
        _copy_workflow_bundle(stage_root, workflow, bundle_root, profile)

    policies_text = (plugin_root / "policies" / "policy.yaml").read_text(encoding="utf-8")
    private_root = profile.private_root
    _copy_capabilities(plugin_root, stage_root, profile)
    _copy_private_resources(plugin_root, stage_root, profile)
    source_roles = plugin_root / "roles"
    for source in sorted(path for path in source_roles.rglob("*") if path.is_file()):
        _write_text(
            stage_root,
            private_root / "roles" / source.relative_to(source_roles),
            source.read_text(encoding="utf-8"),
        )
    _write_text(stage_root, private_root / "policies" / "policy.yaml", policies_text)
    if profile.emits_agents:
        for role_id, role in sorted(roles.items()):
            _write_text(
                stage_root,
                Path("agents") / f"{role_id}.md",
                _role_body(role_id, role, profile, workspace_safety),
            )

    if host is Host.CLAUDE:
        plugin_json = {
            "name": "scholar",
            "version": "2.0.0",
            "description": "Evidence-grounded academic and patent workflows.",
            "author": {"name": "scholar-ip-copilot contributors"},
            "license": "MIT",
            "homepage": "https://github.com/scholar-ip-copilot/scholar-ip-copilot",
        }
        _write_text(
            stage_root,
            Path(".claude-plugin") / "plugin.json",
            json.dumps(plugin_json, indent=2) + "\n",
        )
    elif host is Host.CODEX:
        _write_text(
            stage_root,
            Path(".codex-plugin") / "plugin.json",
            json.dumps(_codex_manifest(), indent=2) + "\n",
        )
    return sorted(path for path in stage_root.rglob("*") if path.is_file())


def _safe_relative(path_value: str) -> Path:
    relative = Path(path_value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"unsafe owned path: {path_value}")
    return relative


def _read_owned_paths(out_dir: Path) -> set[Path]:
    manifest = out_dir / ".evidraft-render-manifest.json"
    if not manifest.is_file():
        return set()
    if manifest.is_symlink():
        raise ValueError(f"render manifest must not be a symlink: {manifest}")
    raw = json.loads(manifest.read_text(encoding="utf-8"))
    return {_safe_relative(str(value)) for value in raw.get("owned_paths", [])}


def _v1_owned_paths(host: Host) -> set[Path]:
    if host is Host.CLAUDE:
        return (
            {Path("commands") / f"{value}.md" for value in V1_COMMANDS}
            | {Path("agents") / f"{value}.md" for value in V1_AGENTS}
            | {Path("skills") / value for value in V1_SKILLS}
            | {Path("hooks") / value for value in V1_HOOK_FILES}
        )
    if host is Host.CODEX:
        return (
            {Path("skills") / f"scholar-{value}" for value in V1_COMMANDS}
            | {Path("skills") / f"scholar-skill-{value}" for value in V1_SKILLS}
            | {Path("README.md")}
        )
    return (
        {Path("commands") / f"scholar-{value}.md" for value in V1_COMMANDS}
        | {Path("agents") / f"{value}.md" for value in V1_AGENTS}
        | {Path("skills") / value for value in V1_SKILLS}
        | {Path("README.md"), Path("plugin.toml")}
    )


def _atomic_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(f".{target.name}.evidraft-{os.getpid()}")
    try:
        shutil.copyfile(source, temp)
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)


def _output_target(root: Path, relative: Path) -> Path:
    target = root / relative
    resolved_root = root.resolve()
    resolved_parent = target.parent.resolve(strict=False)
    if not resolved_parent.is_relative_to(resolved_root):
        raise ValueError(f"owned path escapes render root: {relative.as_posix()}")
    return target


def _prune_empty_parents(path: Path, stop: Path) -> None:
    parent = path.parent
    while parent != stop and parent.is_dir():
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


def _remove_output_file(out_dir: Path, relative: Path) -> None:
    target = _output_target(out_dir, relative)
    if target.is_file() or target.is_symlink():
        target.unlink()
        _prune_empty_parents(target, out_dir)


def clean_rendered(out_dir: Path) -> list[Path]:
    """Remove only paths claimed by a renderer ownership manifest."""
    out_dir = out_dir.resolve()
    if not out_dir.is_dir():
        return []
    owned = _read_owned_paths(out_dir)
    removed: list[Path] = []
    for relative in sorted(owned, reverse=True):
        target = _output_target(out_dir, relative)
        if target.is_file() or target.is_symlink():
            target.unlink()
            removed.append(target)
            _prune_empty_parents(target, out_dir)
    (out_dir / ".evidraft-render-manifest.json").unlink(missing_ok=True)
    return removed


def render_plugin(plugin_root: Path, out_dir: Path, host: Host | str) -> list[Path]:
    host = Host(host)
    plugin_root = plugin_root.resolve()
    _validate_plugin_source(plugin_root)
    out_dir = out_dir.absolute()
    has_manifest = (out_dir / ".evidraft-render-manifest.json").is_file()
    old_owned = _read_owned_paths(out_dir)
    if not has_manifest:
        old_owned = _v1_owned_paths(host)

    with tempfile.TemporaryDirectory(prefix="evidraft-render-") as temp_dir:
        stage_root = Path(temp_dir) / "new"
        stage_root.mkdir()
        staged = _stage_render(plugin_root, stage_root, host)
        new_owned = {path.relative_to(stage_root) for path in staged}
        for relative in old_owned | new_owned:
            _output_target(out_dir, relative)
        manifest = out_dir / ".evidraft-render-manifest.json"
        manifest_data = {
            "version": 2,
            "host": host.value,
            "owned_paths": sorted(path.as_posix() for path in new_owned),
        }
        replace_owned_tree(
            root=out_dir,
            staged_root=stage_root,
            new_owned=new_owned,
            old_owned=old_owned,
            manifest=manifest,
            manifest_data=manifest_data,
        )
    return sorted([out_dir / path for path in new_owned] + [manifest])
