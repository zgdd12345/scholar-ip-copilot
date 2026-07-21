# Selective EviDraft 3.0 Plugin Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Commit a selective EviDraft 3.0 that restores the structured `research.explain` graph, packages one reproducible Codex/Claude plugin, and installs Codex through exactly one discovery mode.

**Architecture:** Keep `plugins/scholar-ip/` as the only authored workflow source. Restore the paper-explanation validator and private worker bundle, project Codex and Claude into a deterministic tracked `plugins/scholar/` package, and keep OpenCode as a runtime projection. Put host installation orchestration behind tested Python functions so cachebuster restoration and discovery-mode checks do not depend on fragile shell cleanup.

**Tech Stack:** Python 3.10+, pytest, PyYAML, jsonschema, Ruff, GNU Make, Codex plugin-creator helpers, Claude Code plugin validator.

## Global Constraints

- Work only in `/Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.worktrees/evidraft3-lightweight` on `codex/evidraft3-lightweight` until final integration.
- Activate `/Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.venv` and set `PYTHONPATH=src:.` for every Python, test, lint, build, or Make command.
- Do not reset, stash, rewrite history, edit locked Claude worktrees, or discard any pre-existing v3 change.
- Follow Red -> Green -> Refactor for every production change and retain fresh Red and Green output in the task record.
- Keep `format_version: 2`, seven public workflows, 22 actions, and no `research.guide` alias.
- Keep `research.explain` graph scheduling at `max_parallel: 15`, `max_attempts: 2`, nested delegation forbidden, and task-ID result order.
- Always attempt similar-method and current-method research; exhausted or unavailable tasks produce a `partial` note with gaps and attempt reasons.
- Keep the dedicated indexer, analysis worker, reasoning worker, evidence auditor, and synthesizer; auditor findings are advisory and never suppress synthesis.
- Keep scope and evidence-integrity advisory. Workspace confinement, sensitive paths, unsafe symlinks, overwrite approval, and external-publication authority remain hard boundaries.
- Derive release metadata from `plugins/scholar-ip/plugin.yaml`; the tracked base version is exactly `3.0.0`.
- Treat cachebusters as transient installation state and restore the tracked base manifest on success and failure.
- Keep the wheel renderer/CLI-only; do not bundle `plugins/scholar-ip`, `plugins/scholar`, or host plugin payloads.
- Never edit `.env`, credentials, `~/.codex/config.toml`, or marketplace JSON outside this repository.

---

### Task 1: Preserve and verify the pre-existing lightweight v3 baseline

**Files:**
- Commit existing modifications: the 103 tracked changes already present in the worktree
- Commit existing additions: `docs/migration-v3.md`, `tests/test_v3_content_workflows.py`, `tests/test_v3_core.py`, `tests/test_v3_research_workflows.py`, `tests/test_v3_shared_contracts.py`
- Exclude: ignored `.claude/`, `.codex/`, `.opencode/`, `.agents/skills/`, build output, and test caches

**Interfaces:**
- Consumes: commit `caa3dc4` plus the dirty v3 worktree state
- Produces: an immutable checkpoint commit from which every selective-v3 Red test starts

- [ ] **Step 1: Record the exact baseline state**

Run:

```bash
cd /Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.worktrees/evidraft3-lightweight
git status --short
git diff --stat
git diff --check
```

Expected: 93 modified, 10 deleted, and 5 untracked paths; `git diff --check` exits 0.

- [ ] **Step 2: Verify the pre-existing v3 baseline in the designated environment**

Run:

```bash
cd /Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.worktrees/evidraft3-lightweight
source /Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.venv/bin/activate
export PYTHONPATH=src:.
python -m pytest tests/ -q
python -m ruff check src packages tests
```

Expected: 308 tests pass and Ruff exits 0. If the count differs because the test tree changed after plan creation, record the collected count and require zero failures.

- [ ] **Step 3: Stage only the preserved v3 state**

Run:

```bash
git add -u
git add docs/migration-v3.md tests/test_v3_content_workflows.py tests/test_v3_core.py tests/test_v3_research_workflows.py tests/test_v3_shared_contracts.py
git diff --cached --check
git status --short
```

Expected: every pre-existing non-ignored v3 path is staged and no generated host tree is staged.

- [ ] **Step 4: Commit the checkpoint**

Run:

```bash
git commit -m "chore: preserve lightweight EviDraft 3 baseline"
```

Expected: one checkpoint commit containing only the pre-existing v3 implementation.

---

### Task 2: Restore the paper-explanation graph and runtime validator

**Files:**
- Create: `src/evidraft/paper_explanation.py`
- Restore and modify: `plugins/scholar-ip/capabilities/research/paper-explanation/task-graph.yaml`
- Restore and modify: `plugins/scholar-ip/capabilities/research/paper-explanation/paper-map.schema.json`
- Restore and modify: `plugins/scholar-ip/capabilities/research/paper-explanation/analysis-packet.schema.json`
- Modify: `src/evidraft/core.py`
- Modify: `src/evidraft/cli.py`
- Modify: `src/evidraft/__init__.py`
- Create: `tests/test_paper_explanation_task_graph.py`
- Modify: `tests/test_v3_core.py`

**Interfaces:**
- Consumes: `roles.yaml` mode identifiers and the three resource files under the capability bundle
- Produces: `validate_paper_explanation_bundle(plugin_root, declared_modes)`, `validate_paper_explanation_instance(bundle, instance, *, expected_task_id, expected_attempt)`, and `workflow_validate_paper_explanation_return(bundle, instance, *, expected_task_id, expected_attempt)`

- [ ] **Step 1: Write the failing graph and API tests**

Restore the schema, identity, attempt, URL, budget, and stdin CLI cases from commit `f1d60df`, then replace the scheduler and audit expectations with these exact assertions:

```python
def test_task_graph_caps_parallelism_at_fifteen_and_uses_two_attempts() -> None:
    assert _graph()["scheduler"] == {
        "max_parallel": 15,
        "max_attempts": 2,
        "nested_delegation": "forbidden",
        "result_order": "task_id",
    }


def test_graph_requires_similar_and_current_attempts_in_every_profile() -> None:
    graph = _graph()
    assert graph["tasks"]["B3"]["mandatory"] is True
    assert graph["tasks"]["B3"]["scope"] == ["similar-methods", "current-methods"]
    assert graph["tasks"]["R1"]["mandatory"] is True
    assert graph["tasks"]["R1"]["scope"] == ["similar-methods"]
    assert graph["tasks"]["R2"]["mandatory"] is True
    assert graph["tasks"]["R2"]["scope"] == ["current-methods"]
    assert "B3" in graph["profiles"]["beginner"]["tasks"]
    for profile in ("graduate", "reviewer"):
        assert {"R1", "R2"} <= set(graph["profiles"][profile]["tasks"])


def test_auditor_packet_has_no_blocking_control_surface() -> None:
    schema = _schema("analysis-packet.schema.json")
    assert "blocking" not in schema["properties"]
    severities = schema["$defs"]["finding"]["properties"]["severity"]["enum"]
    assert severities == ["info", "warning", "error"]


def test_external_failure_still_records_search_attempt() -> None:
    packet = _analysis_packet(task_id="R2", attempt=2, status="failed")
    packet["retry_reason"] = "provider timeout"
    packet["search_metadata"] = {
        "queries": ["source paper current methods"],
        "providers": ["OpenAlex"],
        "cutoff": "2026-07-21",
        "opened_sources": [],
    }
    packet["external_works"] = []
    _instance_validator()(BUNDLE, packet, expected_task_id="R2", expected_attempt=2)
```

In `tests/test_v3_core.py`, replace the obsolete-runtime assertion with:

```python
def test_v3_keeps_safety_only_preflight_and_restores_explanation_validation() -> None:
    assert not hasattr(core_module, "scope_policy")
    assert hasattr(core_module, "audit_evidence")
    assert callable(core_module.workflow_validate_paper_explanation_return)
```

- [ ] **Step 2: Run the focused tests and verify Red**

Run:

```bash
source /Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.venv/bin/activate
export PYTHONPATH=src:.
python -m pytest tests/test_paper_explanation_task_graph.py tests/test_v3_core.py -q
```

Expected: collection fails because `evidraft.paper_explanation` and the three graph resources are absent. This is the required missing-behavior failure.

- [ ] **Step 3: Restore the validator with the selective-v3 scheduler**

Use the complete `f1d60df:src/evidraft/paper_explanation.py` implementation as the read-only source and restore it with `apply_patch`. Its scheduler constant must be:

```python
EXPECTED_SCHEDULER = {
    "max_parallel": 15,
    "max_attempts": 2,
    "nested_delegation": "forbidden",
    "result_order": "task_id",
}
```

Keep the closed task/profile validation, acyclic dependency check, Draft 2020-12 schema checks, strict URI checker, task/attempt binding, and source/finding budget enforcement. Rename the R2 and B3 graph scope token from `frontier-methods` to `current-methods` in both `EXPECTED_TASKS` and `task-graph.yaml`.

- [ ] **Step 4: Restore schemas and make audit/external attempts advisory but explicit**

Restore `paper-map.schema.json` unchanged from `f1d60df`. Restore `analysis-packet.schema.json`, then make these exact contract changes:

```json
"severity": {"enum": ["info", "warning", "error"]}
```

Remove the top-level `blocking` property and the A1 conditional that requires it. Require `search_metadata` and `external_works` for B3, R1, and R2 for every status, including `failed`. Define search metadata as:

```json
"searchMetadata": {
  "type": "object",
  "additionalProperties": false,
  "required": ["queries", "providers", "cutoff", "opened_sources"],
  "properties": {
    "queries": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}},
    "providers": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}},
    "cutoff": {"type": "string", "format": "date"},
    "opened_sources": {"type": "array", "items": {"type": "string", "format": "uri"}}
  }
}
```

- [ ] **Step 5: Restore the core wrapper and CLI without restoring policy gates**

Add only this wrapper to `src/evidraft/core.py`:

```python
def workflow_validate_paper_explanation_return(
    bundle: Path | str,
    instance: object,
    *,
    expected_task_id: str,
    expected_attempt: int,
) -> dict[str, object]:
    return validate_paper_explanation_instance(
        Path(bundle),
        instance,
        expected_task_id=expected_task_id,
        expected_attempt=expected_attempt,
    )
```

Restore `paper-explanation validate-return` and stdin JSON handling in `src/evidraft/cli.py`. Re-export the wrapper from `src/evidraft/__init__.py`. Preserve the v3 `evidence audit` command and do not restore `scope_policy`, `PUBLISH_OPERATIONS`, `PreflightResult.scope`, or `--evidence-id` preflight behavior.

- [ ] **Step 6: Run Green and the adjacent core suite**

Run:

```bash
python -m pytest tests/test_paper_explanation_task_graph.py tests/test_v3_core.py -q
python -m pytest tests/test_v2_core.py tests/test_v2_release_surface.py -q
python -m ruff check src/evidraft tests/test_paper_explanation_task_graph.py tests/test_v3_core.py
```

Expected: all selected tests and Ruff pass.

- [ ] **Step 7: Commit**

Run:

```bash
git add src/evidraft plugins/scholar-ip/capabilities/research/paper-explanation tests/test_paper_explanation_task_graph.py tests/test_v3_core.py
git commit -m "feat(research): restore selective explanation graph runtime"
```

---

### Task 3: Restore dedicated workers and partial synthesis semantics

**Files:**
- Restore and modify: `plugins/scholar-ip/roles/modes/paper-indexer.md`
- Restore and modify: `plugins/scholar-ip/roles/modes/paper-analysis-worker.md`
- Restore and modify: `plugins/scholar-ip/roles/modes/paper-reasoning-worker.md`
- Restore and modify: `plugins/scholar-ip/roles/modes/explanation-evidence-auditor.md`
- Modify: `plugins/scholar-ip/roles/modes/paper-explainer.md`
- Modify: `plugins/scholar-ip/roles/roles.yaml`
- Modify: `plugins/scholar-ip/workflows/research/workflow.yaml`
- Modify: `plugins/scholar-ip/workflows/research/stages/explain.md`
- Modify: `plugins/scholar-ip/capabilities/research/paper-explanation/spec.md`
- Modify: `plugins/scholar-ip/policies/policy.yaml`
- Modify: `plugins/scholar-ip/capabilities/index.yaml`
- Modify: `src/evidraft/render.py`
- Modify: `src/evidraft/install.py`
- Modify: `tests/test_v2_capabilities.py`
- Modify: `tests/test_v2_install.py`
- Modify: `tests/test_v2_renderer.py`
- Modify: `tests/test_v2_role_modes.py`
- Modify: `tests/test_v2_workflow_source.py`
- Modify: `tests/test_v3_research_workflows.py`
- Modify: `tests/test_v3_shared_contracts.py`

**Interfaces:**
- Consumes: the validated task graph and packet schemas from Task 2
- Produces: five graph roles, four read-only host worker agents, one sole writer, and an instruction-level retry/degradation contract rendered identically across hosts

- [ ] **Step 0: Capture the skill-behavior baseline before editing guidance**

Run five fresh-context read-only evaluator samples against the current `research` router, `stages/explain.md`, and paper-explanation spec. Use this exact prompt and do not expose the approved design or new tests:

```text
You are evaluating the currently supplied EviDraft research skill only. A user asks for a graduate explanation of one identified paper. The host can create independent workers, but the external provider times out twice. State: whether similar and current methods are attempted, the worker/dependency schedule, retry count, whether an auditor runs, whether a note is written, and the final status. Quote the supplied skill contract for each decision. Do not edit files.
```

Record every response in the task log. The baseline is Red when it treats external research as conditional, omits the fixed graph or auditor, or uses `complete_with_gaps` instead of `partial`. If all five unexpectedly satisfy the approved contract, stop because the guidance change has no demonstrated behavior gap.

- [ ] **Step 1: Replace obsolete negative tests with the approved behavior**

Add assertions equivalent to:

```python
def test_explain_requires_graph_external_attempts_and_partial_degradation() -> None:
    combined = f"{_normalized(WORKFLOWS / 'research/stages/explain.md')} {_normalized(CAPABILITY / 'spec.md')}"
    for token in (
        "task-graph.yaml",
        "min(host_capacity, 15, ready_task_count)",
        "similar-methods",
        "current-methods",
        "fresh worker",
        "attempt: 2",
        "status: partial",
        "both attempt reasons",
    ):
        assert token in combined
    assert "ordinary beginner and graduate explanations do not require external research" not in combined
    assert "no fixed cardinality, dependency waves, or retry count" not in combined


def test_explain_auditor_is_advisory_and_workspace_safety_remains_hard() -> None:
    combined = f"{_normalized(WORKFLOWS / 'research/stages/explain.md')} {_normalized(CAPABILITY / 'spec.md')}"
    assert "auditor findings cannot suppress synthesis" in combined
    assert "scope and evidence-integrity are advisory" in combined
    for token in ("workspace confinement", "sensitive paths", "overwrite", "external publication"):
        assert token in combined
```

Update renderer and role tests to require 20 private modes, 10 Claude/OpenCode agents, the four read-only worker agents, and all three graph/schema resources on every host. Update install tests so deleting any restored resource rejects the source before touching the destination.

- [ ] **Step 2: Run Red**

Run:

```bash
python -m pytest tests/test_v3_research_workflows.py tests/test_v3_shared_contracts.py tests/test_v2_workflow_source.py tests/test_v2_capabilities.py tests/test_v2_role_modes.py tests/test_v2_renderer.py tests/test_v2_install.py -q
```

Expected: failures show the current conditional external branch, missing worker modes/resources, 16-mode renderer, and installer that accepts an incomplete explanation bundle.

- [ ] **Step 3: Restore the four bounded read-only modes**

Use the full mode documents from `f1d60df` as the source. Preserve their exact input ownership and tool restrictions. Apply these selective-v3 changes:

```yaml
# paper-analysis-worker external scopes
- Always execute assigned similar-methods or current-methods retrieval.
- Record queries, providers, cutoff, every canonical source opened, rejected candidates, and failure reason.
- Return a failed packet after an exhausted attempt; never invent fallback prose.

# explanation-evidence-auditor
- Return findings with severity info, warning, or error.
- Never return a blocking control flag.
- Findings are correction guidance for the synthesizer and cannot suppress synthesis.
```

Add all four modes back to `roles.yaml` under their original tiers and roles, producing exactly 20 unique modes.

- [ ] **Step 4: Replace the explanation stage and capability status contract**

Start from the structured `f1d60df` stage/spec and retain the v3 safe-boundary-note behavior. Replace the old blocking rules with this exact decision table:

```markdown
| Condition | Final behavior |
|---|---|
| Every selected task returns a valid complete packet | Write one note with `status: complete`. |
| Any selected task fails, is unavailable, or has incomplete external coverage | Write one note with `status: partial`, named gaps, failed task IDs, and both attempt reasons. |
| I0 cannot map readable full text | Write a limited `status: partial` identity/evidence-boundary note locally; do not invent analysis. |
| Auditor reports any finding or fails | Preserve warnings/recovery guidance and continue synthesis; audit alone does not change complete to partial when all analysis packets are valid. |
| Workspace, sensitive-path, unsafe-symlink, overwrite, or output-write safety fails | Return `status: error` and do not write. |
```

State effective concurrency exactly as `min(host_capacity, 15, ready_task_count)`. State that every profile schedules similar/current external research, a failed first attempt dispatches a fresh worker with identical immutable input and `attempt: 2`, and S0 still runs after terminal failures. Keep `paper-explainer` as the only role receiving the output path.

- [ ] **Step 5: Restore renderer and installer completeness checks**

In `src/evidraft/render.py`, restore `PAPER_EXPLANATION_WORKER_MODES`, call `validate_paper_explanation_bundle()` during source validation, require exactly 20 modes, restore `_mode_agent_body()`, and emit the four worker agents only for Claude and OpenCode. Update each host router to say that `research.explain` is controlled by its validated graph and bounded at 15.

In `src/evidraft/install.py`, require the three graph/schema resources and four worker mode specs in `_validate_source()`. Add `Bash:evidraft paper-explanation validate-return*` to the workspace-safety allowed tools while leaving `scope.enforcement: advisory` and `evidence-integrity.enforcement: audit` unchanged.

- [ ] **Step 6: Update capability hashes and run Green**

Recalculate only the normalized hash entries whose source documents changed. Run:

```bash
python -m pytest tests/test_paper_explanation_task_graph.py tests/test_v3_research_workflows.py tests/test_v3_shared_contracts.py tests/test_v2_workflow_source.py tests/test_v2_capabilities.py tests/test_v2_role_modes.py tests/test_v2_renderer.py tests/test_v2_install.py -q
python -m pytest tests/test_v2_contract_mapping.py tests/test_paper_explanation_routing.py -q
python -m ruff check src packages tests
```

Expected: all selected tests pass and the public action surface remains 22.

- [ ] **Step 6a: Re-run the five skill-behavior samples with the changed guidance**

Use the identical prompt and five fresh contexts. Every sample must attempt both external scopes, use the validated dependency graph with a two-attempt limit, run the dedicated auditor in reviewer mode only, continue to synthesis after external failure, and return a written `partial` note with both reasons. Treat any divergent response as a wording defect: tighten the smallest contract sentence, rerun focused tests, and repeat the five samples.

- [ ] **Step 7: Commit**

Run:

```bash
git add plugins/scholar-ip src/evidraft/render.py src/evidraft/install.py tests
git commit -m "feat(research): restore bounded explanation workers"
```

---

### Task 4: Derive host metadata and build the deterministic combined release package

**Files:**
- Modify: `plugins/scholar-ip/plugin.yaml`
- Modify: `packages/core/schemas/plugin.schema.json`
- Modify: `src/evidraft/render.py`
- Create: `src/evidraft/release.py`
- Modify: `src/evidraft/cli.py`
- Create: `tests/test_release_package.py`
- Modify: `tests/test_v2_renderer.py`
- Modify: `tests/test_v2_release_surface.py`

**Interfaces:**
- Consumes: `render_plugin(plugin_root, out_dir, host)` and the keyword-only `replace_owned_tree` transaction API
- Produces: `PluginMetadata`, `load_plugin_metadata()`, `render_plugin_package()`, and `release_package_drift()`

- [ ] **Step 1: Write failing metadata and release tests**

Use these public expectations:

```python
def test_host_manifests_derive_metadata_from_plugin_yaml(tmp_path: Path) -> None:
    plugin = tmp_path / "plugin"
    shutil.copytree(PLUGIN, plugin)
    source = yaml.safe_load((plugin / "plugin.yaml").read_text())
    source["version"] = source["manifest_version"] = "3.0.1"
    source["description"] = "Metadata sentinel"
    (plugin / "plugin.yaml").write_text(yaml.safe_dump(source, sort_keys=False))
    for host in (Host.CLAUDE, Host.CODEX):
        out = tmp_path / host.value
        render_plugin(plugin, out, host)
        manifest_path = out / (".codex-plugin/plugin.json" if host is Host.CODEX else ".claude-plugin/plugin.json")
        manifest = json.loads(manifest_path.read_text())
        assert manifest["version"] == "3.0.1"
        assert manifest["description"] == "Metadata sentinel"


def test_release_package_contains_both_host_surfaces(tmp_path: Path) -> None:
    out = tmp_path / "scholar"
    render_plugin_package(PLUGIN, out)
    assert (out / ".codex-plugin/plugin.json").is_file()
    assert (out / ".claude-plugin/plugin.json").is_file()
    assert len(list((out / "skills").glob("scholar-*/SKILL.md"))) == 7
    assert len(list((out / "commands").glob("*.md"))) == 7
    assert len(list((out / "agents").glob("*.md"))) == 10


def test_release_package_is_path_independent(tmp_path: Path) -> None:
    first_plugin = tmp_path / "a" / "plugin"
    second_plugin = tmp_path / "b" / "plugin"
    shutil.copytree(PLUGIN, first_plugin)
    shutil.copytree(PLUGIN, second_plugin)
    first = tmp_path / "first"
    second = tmp_path / "second"
    render_plugin_package(first_plugin, first)
    render_plugin_package(second_plugin, second)
    assert _tree_bytes(first) == _tree_bytes(second)
```

Add collision, rollback, unknown-file, and drift tests. A same-path/same-bytes collision is coalesced; a same-path/different-bytes collision raises before output changes.

- [ ] **Step 2: Run Red**

Run:

```bash
python -m pytest tests/test_release_package.py tests/test_v2_renderer.py tests/test_v2_release_surface.py -q
```

Expected: import fails because `evidraft.release` is absent; the metadata sentinel test also exposes hard-coded `3.0.0`.

- [ ] **Step 3: Add canonical metadata and derive both manifests**

Add these source fields and validate them in `plugin.schema.json`:

```yaml
homepage: https://github.com/zgdd12345/scholar-ip-copilot
repository: https://github.com/zgdd12345/scholar-ip-copilot
keywords: [research, literature-review, academic-writing, patents, evidence]
```

Implement:

```python
@dataclass(frozen=True)
class PluginMetadata:
    id: str
    display_name: str
    version: str
    description: str
    license: str
    homepage: str
    repository: str
    keywords: tuple[str, ...]
    author_name: str


def load_plugin_metadata(plugin_root: Path) -> PluginMetadata:
    raw = yaml.safe_load((Path(plugin_root) / "plugin.yaml").read_text(encoding="utf-8"))
    return PluginMetadata(
        id=str(raw["id"]),
        display_name=str(raw["name"]),
        version=str(raw["version"]),
        description=str(raw["description"]).strip(),
        license=str(raw["license"]),
        homepage=str(raw["homepage"]),
        repository=str(raw["repository"]),
        keywords=tuple(str(value) for value in raw["keywords"]),
        author_name=str(raw["authors"][0]["name"]),
    )
```

Pass this value into `_codex_manifest(metadata)` and `_claude_manifest(metadata)`. Codex interface metadata uses `display_name` and `homepage` as `websiteURL`; omit assets, privacy, and terms fields.

- [ ] **Step 4: Implement deterministic release packaging**

Create `src/evidraft/release.py` with:

```python
RELEASE_MANIFEST = ".evidraft-release-manifest.json"
RELEASE_FORMAT_VERSION = 1


def _safe_relative(value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError(f"unsafe release path: {value}")
    return relative


def _file_bytes(root: Path) -> dict[str, bytes]:
    root = Path(root)
    if not root.is_dir():
        return {}
    files: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"release tree contains symlink: {path}")
        if path.is_file():
            files[path.relative_to(root).as_posix()] = path.read_bytes()
    return files


def _read_release_owned_paths(root: Path) -> set[Path]:
    manifest = Path(root) / RELEASE_MANIFEST
    if not manifest.is_file():
        return set()
    document = json.loads(manifest.read_text(encoding="utf-8"))
    if document.get("format_version") != RELEASE_FORMAT_VERSION:
        raise ValueError("unsupported release manifest format")
    return {
        _safe_relative(value)
        for values in document.get("hosts", {}).values()
        for value in values
    }


def _existing_release_files(root: Path) -> set[Path]:
    root = Path(root)
    if not root.is_dir():
        return set()
    return {
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() or path.is_symlink()
    }


def source_sha256(plugin_root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in Path(plugin_root).rglob("*") if item.is_file()):
        relative = path.relative_to(plugin_root).as_posix().encode("utf-8")
        body = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(body).to_bytes(8, "big"))
        digest.update(body)
    return digest.hexdigest()


def render_plugin_package(plugin_root: Path, out_dir: Path) -> list[Path]:
    plugin_root = Path(plugin_root).resolve()
    out_dir = Path(out_dir).absolute()
    metadata = load_plugin_metadata(plugin_root)
    with tempfile.TemporaryDirectory(prefix="evidraft-package-") as raw:
        temporary = Path(raw)
        staged = temporary / "staged"
        staged.mkdir()
        by_host: dict[str, list[str]] = {}
        owners: dict[Path, str] = {}
        for host in (Host.CLAUDE, Host.CODEX):
            rendered_root = temporary / host.value
            rendered = render_plugin(plugin_root, rendered_root, host)
            relative_files = sorted(
                path.relative_to(rendered_root)
                for path in rendered
                if path.name != ".evidraft-render-manifest.json"
            )
            by_host[host.value] = [path.as_posix() for path in relative_files]
            for relative in relative_files:
                source = rendered_root / relative
                target = staged / relative
                if relative in owners:
                    if target.read_bytes() != source.read_bytes():
                        raise ValueError(
                            f"release path collision: {relative} from "
                            f"{owners[relative]} and {host.value}"
                        )
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                owners[relative] = host.value

        old_owned = _read_release_owned_paths(out_dir)
        unknown = _existing_release_files(out_dir) - old_owned - {Path(RELEASE_MANIFEST)}
        if unknown:
            names = ", ".join(path.as_posix() for path in sorted(unknown))
            raise ValueError(f"unknown files in release root: {names}")
        manifest_data = {
            "format_version": RELEASE_FORMAT_VERSION,
            "plugin": {"id": metadata.id, "version": metadata.version},
            "renderer_version": RENDERER_VERSION,
            "source_sha256": source_sha256(plugin_root),
            "hosts": by_host,
        }
        new_owned = set(owners)
        replace_owned_tree(
            root=out_dir,
            staged_root=staged,
            new_owned=new_owned,
            old_owned=old_owned,
            manifest=out_dir / RELEASE_MANIFEST,
            manifest_data=manifest_data,
        )
    return sorted([out_dir / path for path in new_owned] + [out_dir / RELEASE_MANIFEST])


def release_package_drift(plugin_root: Path, package_root: Path) -> list[str]:
    package_root = Path(package_root)
    with tempfile.TemporaryDirectory(prefix="evidraft-drift-") as raw:
        expected_root = Path(raw) / "scholar"
        render_plugin_package(plugin_root, expected_root)
        expected = _file_bytes(expected_root)
    actual = _file_bytes(package_root)
    findings = [f"missing: {path}" for path in sorted(expected.keys() - actual.keys())]
    findings.extend(
        f"changed: {path}"
        for path in sorted(expected.keys() & actual.keys())
        if expected[path] != actual[path]
    )
    findings.extend(f"unexpected: {path}" for path in sorted(actual.keys() - expected.keys()))
    return findings
```

The release manifest must contain `format_version`, plugin ID/version, renderer version, source SHA-256, and sorted owned paths per host. It must contain no absolute path, timestamp, or mtime.

- [ ] **Step 5: Add the package CLI and run Green**

Add `evidraft package --plugin plugins/scholar-ip --out plugins/scholar` and `--check`. `--check` returns nonzero with one line per drift finding and never writes the target.

Run:

```bash
python -m pytest tests/test_release_package.py tests/test_v2_renderer.py tests/test_v2_release_surface.py -q
python -m ruff check src/evidraft tests/test_release_package.py tests/test_v2_renderer.py tests/test_v2_release_surface.py
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

Run:

```bash
git add plugins/scholar-ip/plugin.yaml packages/core/schemas/plugin.schema.json src/evidraft tests/test_release_package.py tests/test_v2_renderer.py tests/test_v2_release_surface.py
git commit -m "feat(release): add reproducible combined plugin package"
```

---

### Task 5: Track the release package and point both marketplaces at it

**Files:**
- Create: `plugins/scholar/**`
- Modify: `.agents/plugins/marketplace.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `.gitignore`
- Modify: `tests/test_release_package.py`
- Modify: `tests/test_v3_shared_contracts.py`

**Interfaces:**
- Consumes: `evidraft package` and `release_package_drift()` from Task 4
- Produces: one clean-checkout install target shared by Codex and Claude

- [ ] **Step 1: Write failing tracked-package and marketplace tests**

```python
def test_repo_marketplaces_point_to_tracked_scholar_package() -> None:
    codex = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
    claude = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
    assert codex["plugins"][0]["source"] == {"source": "local", "path": "./plugins/scholar"}
    assert codex["plugins"][0]["policy"] == {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL",
    }
    assert codex["plugins"][0]["category"] == "Productivity"
    assert claude["plugins"][0]["source"] == "./plugins/scholar"


def test_tracked_release_package_has_no_drift() -> None:
    assert release_package_drift(PLUGIN, ROOT / "plugins/scholar") == []
```

- [ ] **Step 2: Run Red**

Run:

```bash
python -m pytest tests/test_release_package.py tests/test_v3_shared_contracts.py -q
```

Expected: `plugins/scholar` is missing and both marketplace source paths still point at ignored outputs.

- [ ] **Step 3: Generate and validate the tracked base package**

Run:

```bash
python -m evidraft.cli package --plugin plugins/scholar-ip --out plugins/scholar
python -m evidraft.cli package --plugin plugins/scholar-ip --out plugins/scholar --check
python /Users/fsm/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py plugins/scholar
claude plugin validate plugins/scholar
```

Expected: drift check, Codex plugin-creator validation, and Claude validation all pass. The base Codex manifest version remains exactly `3.0.0`.

- [ ] **Step 4: Update both marketplace descriptors**

Set Codex source to:

```json
{"source": "local", "path": "./plugins/scholar"}
```

Preserve `AVAILABLE`, `ON_INSTALL`, `Productivity`, marketplace name `scholar-ip-copilot`, and render order. Set the Claude source to `./plugins/scholar`. Remove only the obsolete `.claude-plugin/` ignore rule so a clean checkout visibly contains its tracked descriptor.

- [ ] **Step 5: Run Green and commit**

Run:

```bash
python -m pytest tests/test_release_package.py tests/test_v3_shared_contracts.py -q
git diff --check
git add plugins/scholar .agents/plugins/marketplace.json .claude-plugin/marketplace.json .gitignore tests/test_release_package.py tests/test_v3_shared_contracts.py
git commit -m "feat(release): track installable Scholar package"
```

---

### Task 6: Make Codex marketplace installation transactional and mutually exclusive

**Files:**
- Create: `src/evidraft/codex_install.py`
- Modify: `src/evidraft/install.py`
- Modify: `src/evidraft/cli.py`
- Modify: `Makefile`
- Create: `tests/test_codex_plugin_install.py`
- Create: `tests/test_codex_install_modes.py`
- Modify: `tests/test_v2_install.py`

**Interfaces:**
- Consumes: repo marketplace JSON, tracked `plugins/scholar`, plugin-creator helper scripts, and Codex CLI
- Produces: `validate_marketplace_plugin()`, `reinstall_codex_plugin()`, `remove_codex_project_skills()`, and mutually exclusive Make targets

- [ ] **Step 1: Write failing cachebuster and discovery-mode tests**

Use a fake command runner that records arguments and invokes a callback for the cachebuster step. Cover:

```python
def test_reinstall_restores_base_manifest_after_success(tmp_path: Path) -> None:
    original = (release / ".codex-plugin/plugin.json").read_bytes()
    result = reinstall_codex_plugin(repo, marketplace, release, creator, runner=fake_runner)
    assert result.plugin_ref == "scholar@scholar-ip-copilot"
    assert (release / ".codex-plugin/plugin.json").read_bytes() == original
    assert any(command[-3:] == ["plugin", "add", result.plugin_ref] for command in calls)


@pytest.mark.parametrize("failing_step", ["cachebuster", "plugin-add", "post-validate"])
def test_reinstall_restores_base_manifest_after_failure(tmp_path: Path, failing_step: str) -> None:
    original = (release / ".codex-plugin/plugin.json").read_bytes()
    with pytest.raises(RuntimeError, match=failing_step):
        reinstall_codex_plugin(repo, marketplace, release, creator, runner=failing_runner)
    assert (release / ".codex-plugin/plugin.json").read_bytes() == original


def test_default_and_compatibility_modes_never_install_both_surfaces() -> None:
    makefile = (ROOT / "Makefile").read_text()
    assert "install-codex: install-codex-plugin" in makefile
    assert "install-codex-plugin:" in makefile
    assert "install-codex-project:" in makefile
    assert "sync-codex-skills" not in _recipe(makefile, "install-codex-plugin")
    assert "plugin add" not in _recipe(makefile, "install-codex-project")
```

Also test that a wrong marketplace name, non-local source, wrong path, missing package, or active marketplace plugin in project mode fails before any mutation.

- [ ] **Step 2: Run Red**

Run:

```bash
python -m pytest tests/test_codex_plugin_install.py tests/test_codex_install_modes.py tests/test_v2_install.py -q
```

Expected: the new modules/functions/targets do not exist.

- [ ] **Step 3: Implement validated, transient cachebusting**

Define:

```python
@dataclass(frozen=True)
class MarketplacePlugin:
    marketplace_name: str
    plugin_name: str
    plugin_root: Path


@dataclass(frozen=True)
class ReinstallResult:
    plugin_ref: str
    installed_version: str


def validate_marketplace_plugin(
    repo_root: Path,
    marketplace_path: Path,
    plugin_name: str = "scholar",
) -> MarketplacePlugin:
    repo_root = Path(repo_root).resolve()
    marketplace_path = Path(marketplace_path).resolve()
    document = json.loads(marketplace_path.read_text(encoding="utf-8"))
    if document.get("name") != "scholar-ip-copilot":
        raise ValueError("unexpected marketplace name")
    matches = [entry for entry in document.get("plugins", []) if entry.get("name") == plugin_name]
    if len(matches) != 1:
        raise ValueError(f"marketplace must contain exactly one {plugin_name} entry")
    source = matches[0].get("source")
    if source != {"source": "local", "path": "./plugins/scholar"}:
        raise ValueError("marketplace plugin source must be local ./plugins/scholar")
    plugin_root = (repo_root / "plugins" / "scholar").resolve()
    if not (plugin_root / ".codex-plugin" / "plugin.json").is_file():
        raise FileNotFoundError(plugin_root)
    public_skills = list((plugin_root / "skills").glob("scholar-*/SKILL.md"))
    if len(public_skills) != 7:
        raise ValueError("tracked plugin must expose exactly seven public skills")
    return MarketplacePlugin(document["name"], plugin_name, plugin_root)
```

Implement installation with this control flow:

```python
def _restore_bytes(path: Path, content: bytes) -> None:
    temporary = path.with_name(f".{path.name}.restore-{os.getpid()}")
    try:
        temporary.write_bytes(content)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def reinstall_codex_plugin(
    repo_root: Path,
    marketplace_path: Path,
    plugin_root: Path,
    plugin_creator_root: Path,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    codex_command: tuple[str, ...] = (
        "codex",
        "-c",
        'model_reasoning_effort="xhigh"',
    ),
) -> ReinstallResult:
    selected = validate_marketplace_plugin(repo_root, marketplace_path)
    if selected.plugin_root != Path(plugin_root).resolve():
        raise ValueError("marketplace and requested plugin roots differ")
    creator = Path(plugin_creator_root).resolve()
    manifest = selected.plugin_root / ".codex-plugin" / "plugin.json"
    base_bytes = manifest.read_bytes()
    python = sys.executable
    runner(
        [python, str(creator / "scripts/validate_plugin.py"), str(selected.plugin_root)],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    marketplace_name = runner(
        [
            python,
            str(creator / "scripts/read_marketplace_name.py"),
            "--marketplace-path",
            str(marketplace_path),
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if marketplace_name != selected.marketplace_name:
        raise ValueError("plugin-creator marketplace name mismatch")
    listed = runner(
        [*codex_command, "plugin", "marketplace", "list"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if selected.marketplace_name not in listed:
        runner(
            [*codex_command, "plugin", "marketplace", "add", str(Path(repo_root).resolve())],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    plugin_ref = f"{selected.plugin_name}@{selected.marketplace_name}"
    try:
        runner(
            [python, str(creator / "scripts/update_plugin_cachebuster.py"), str(selected.plugin_root)],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        installed_version = json.loads(manifest.read_text(encoding="utf-8"))["version"]
        runner(
            [*codex_command, "plugin", "add", plugin_ref],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        post = runner(
            [*codex_command, "plugin", "list"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        if plugin_ref not in post or "enabled" not in post:
            raise RuntimeError("post-validate: installed plugin is not enabled")
        return ReinstallResult(plugin_ref, installed_version)
    finally:
        _restore_bytes(manifest, base_bytes)
```

The exact marketplace list parsing may be isolated in a tested helper if the local CLI emits JSON. Preserve this order: validate marketplace/package, run plugin-creator validation and name reader, ensure the non-default repo marketplace is configured, save original manifest bytes, run the plugin-creator cachebuster helper once, run `codex plugin add scholar@scholar-ip-copilot`, perform post-install list validation, and restore the exact original bytes in `finally`.

Accept the plugin-creator root as an argument and default it from `CODEX_HOME` or `~/.codex`; do not hard-code Alba's home path in production code. Accept a runner dependency for tests. Codex invocations from Make use `-c 'model_reasoning_effort="xhigh"'` and never edit global config.

- [ ] **Step 4: Implement ownership-only project-skill removal and mode preflight**

Add:

```python
def remove_codex_project_skills(destination: Path) -> list[Path]:
    """Remove only entries declared by .evidraft-ownership.json."""
    destination = Path(destination).absolute()
    owned = _owned_names(destination)
    removed = [destination / name for name in sorted(owned) if (destination / name).exists()]
    if not owned:
        return []
    with tempfile.TemporaryDirectory(prefix="evidraft-remove-skills-") as raw:
        staged = Path(raw) / "empty"
        staged.mkdir()
        manifest = destination / ".evidraft-ownership.json"
        replace_owned_tree(
            root=destination,
            staged_root=staged,
            new_owned=set(),
            old_owned={Path(name) for name in owned},
            manifest=manifest,
            manifest_data={"version": 2, "owned_paths": []},
        )
        manifest.unlink()
    return removed
```

Replace the ellipsis with path validation plus the existing recoverable transaction mechanism. Do not add `V1_CODEX_ENTRIES` unless they are explicitly named in the ownership manifest. Add a project-mode preflight that refuses when `scholar@scholar-ip-copilot` is active and reports the exact Codex remove/disable command; it must not remove the plugin automatically.

- [ ] **Step 5: Define mutually exclusive Make targets**

The target graph must be:

```make
install-codex: install-codex-plugin

install-codex-plugin: package-check remove-codex-project-skills
	$(PYTHON) -m evidraft.cli install-codex-plugin \
		--repo-root . \
		--marketplace .agents/plugins/marketplace.json \
		--plugin plugins/scholar

install-codex-project: package-check codex-project-mode-preflight
	$(PYTHON) -m evidraft.cli sync-codex-skills \
		--source plugins/scholar --dest .agents/skills
```

Add explicit `remove-codex-project-skills` and `codex-project-mode-preflight` CLI/Make targets. Do not include compatibility mode in aggregate `install` or `verify`.

- [ ] **Step 6: Run Green and commit**

Run:

```bash
python -m pytest tests/test_codex_plugin_install.py tests/test_codex_install_modes.py tests/test_v2_install.py -q
python -m ruff check src/evidraft tests/test_codex_plugin_install.py tests/test_codex_install_modes.py tests/test_v2_install.py
git add src/evidraft Makefile tests/test_codex_plugin_install.py tests/test_codex_install_modes.py tests/test_v2_install.py
git commit -m "feat(install): enforce one Codex discovery mode"
```

---

### Task 7: Make release verification non-mutating and enforce the wheel boundary

**Files:**
- Modify: `Makefile`
- Modify: `.github/workflows/ci.yml`
- Modify: `pyproject.toml` only if a packaging test exposes plugin payload leakage
- Modify: `tests/test_v2_release_surface.py`
- Modify: `tests/test_release_package.py`
- Modify: `tests/test_v2_e2e.py`
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/plugin-format.md`
- Modify: `docs/migration-v3.md`
- Modify: `plugins/scholar-ip/README.md`
- Modify: `plugins/scholar-ip/docs/architecture.md`

**Interfaces:**
- Consumes: package drift, Codex validator, Claude validator, three host renderers, and wheel build
- Produces: a read-only `verify`/`release-check`, portable CI gates, and accurate installation documentation

- [ ] **Step 1: Write failing release-gate and wheel tests**

```python
def test_release_gates_check_drift_and_both_plugin_formats() -> None:
    makefile = (ROOT / "Makefile").read_text()
    assert "package-check:" in makefile
    assert "plugin-validate-codex:" in makefile
    assert "plugin-validate-claude:" in makefile
    assert "verify: package-check test lint plugin-validate wheel-smoke" in makefile
    assert "verify: install" not in makefile


def test_wheel_gate_forbids_plugin_payload() -> None:
    makefile = (ROOT / "Makefile").read_text()
    for prefix in ("plugins/", ".codex-plugin/", ".claude-plugin/", "skills/"):
        assert prefix in makefile
```

Add CI assertions for package drift, marketplace resolution, tracked package presence, Claude validation, portable Codex manifest tests, OpenCode inventory, `git diff --exit-code`, and absence of `.agents/skills/.evidraft-ownership.json` in checkout.

- [ ] **Step 2: Run Red**

Run:

```bash
python -m pytest tests/test_v2_release_surface.py tests/test_release_package.py tests/test_v2_e2e.py -q
```

Expected: Make/CI still couple `verify` to installation and do not gate the tracked package or wheel payload boundary.

- [ ] **Step 3: Replace Make release and validation targets**

Add `package`, `package-check`, `plugin-validate-codex`, and `plugin-validate-claude`. The Codex target runs:

```bash
$(PYTHON) $(PLUGIN_CREATOR_ROOT)/scripts/validate_plugin.py plugins/scholar
```

The Claude target runs `claude plugin validate plugins/scholar`. `verify` must render OpenCode to its normal ignored tree only when explicitly requested; the release gate renders OpenCode to a temporary directory or uses pytest fixtures. `verify` and `release-check` must never call `install`.

Make host installation targets consume the verified topology:

```make
install-claude: package-check plugin-validate-claude
	claude plugin marketplace add ./ --scope project
	claude plugin update scholar@scholar-ip-copilot --scope project
	claude plugin enable scholar@scholar-ip-copilot --scope project

install-opencode: package-check
	$(PYTHON) -m packages.adapters.opencode.generate \
		--plugin $(PLUGIN_SRC) --out $(OPENCODE_OUT)
```

If `claude plugin marketplace add` reports an already configured identical root, treat that specific state as success; a different root for the same marketplace name is an error. Do not point Claude back to `.claude/plugins/scholar-ip`.

Extend the wheel ZIP assertion to reject every member whose path starts with `plugins/`, `.codex-plugin/`, `.claude-plugin/`, or `skills/`. Retain the smoke calls from `/tmp` and require an explicit external `--plugin` source for each renderer.

- [ ] **Step 4: Extend CI without relying on Alba's home directory**

CI runs pytest/Ruff first, `python -m evidraft.cli package --plugin plugins/scholar-ip --out plugins/scholar --check`, marketplace/package contract tests, Claude validation, OpenCode temporary inventory, wheel smoke, and `git diff --exit-code`. The local `plugin-validate-codex` target remains the required plugin-creator gate; CI uses the committed portable manifest-contract tests because the personal system skill path is not available on clean runners.

- [ ] **Step 5: Update documentation to the actual release topology**

Document these exact facts:

- `plugins/scholar-ip` is authored source; `plugins/scholar` is deterministic tracked Codex/Claude release output.
- Codex defaults to marketplace mode; `.agents/skills` is explicit mutually exclusive compatibility mode.
- `research.guide` is removed and guidance routes through `using`.
- `research.explain` always attempts similar/current methods with up to 15 ready tasks, degrades to a `partial` note, and treats audit findings as advisory.
- Scope/evidence checks report warnings; path, sensitive-file, overwrite, and publication boundaries remain hard.
- The wheel contains renderer/CLI code and requires an external `--plugin` path.
- Host sessions must restart, and Codex must open a new task, after reinstall.

- [ ] **Step 6: Run Green, the full local release gate, and commit**

Run:

```bash
python -m pytest tests/test_v2_release_surface.py tests/test_release_package.py tests/test_v2_e2e.py -q
python -m pytest tests/ -q
python -m ruff check src packages tests
make PYTHON=python package-check
make PYTHON=python plugin-validate-codex
make PYTHON=python plugin-validate-claude
make PYTHON=python wheel-smoke
git diff --check
```

Expected: all tests, Ruff, both validators, drift, and wheel smoke pass without installing a host.

Run:

```bash
git add Makefile .github/workflows/ci.yml pyproject.toml tests README.md docs plugins/scholar-ip/README.md plugins/scholar-ip/docs/architecture.md
git commit -m "ci: enforce reproducible multi-host release gates"
```

---

### Task 8: Review, integrate, reinstall, and verify real hosts

**Files:**
- No planned source edits; any defect found here starts a new Red test in the owning task before a fix
- Update generated runtime outputs only through their renderer/installer commands

**Interfaces:**
- Consumes: all committed selective-v3 tasks and the integrated `master`
- Produces: verified source, integrated branch, installed Codex/Claude/OpenCode state, and a new-task handoff

- [ ] **Step 1: Run the complete non-mutating release gate**

Run:

```bash
cd /Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.worktrees/evidraft3-lightweight
source /Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.venv/bin/activate
export PYTHONPATH=src:.
make PYTHON=python release-check
git diff --check
git status --short
```

Expected: all gates pass and tracked source remains clean.

- [ ] **Step 2: Verify a clean archive**

Run:

```bash
archive_root=$(mktemp -d /tmp/evidraft-clean-checkout.XXXXXX)
git archive HEAD | tar -x -C "$archive_root"
cd "$archive_root"
source /Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot/.venv/bin/activate
export PYTHONPATH=src:.
python -m evidraft.cli package --plugin plugins/scholar-ip --out plugins/scholar --check
python -m pytest tests/test_release_package.py tests/test_v2_release_surface.py -q
test ! -e .agents/skills/.evidraft-ownership.json
```

Expected: drift and clean-checkout tests pass without ignored host state.

- [ ] **Step 3: Perform spec and code-quality review**

Use `superpowers:requesting-code-review`. Reject integration for any unresolved critical or important finding. For each accepted defect, add a failing regression test, observe Red, implement the minimum fix, rerun focused and full gates, and commit separately.

- [ ] **Step 4: Fast-forward master only after all gates are green**

From the primary checkout, verify `master` has not diverged, then fast-forward it to `codex/evidraft3-lightweight`. Do not merge, reset, or overwrite unrelated user changes if the primary checkout is no longer clean; stop and report the exact divergence instead.

- [ ] **Step 5: Reinstall from integrated master**

From `/Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot`:

```bash
source .venv/bin/activate
export PYTHONPATH=src:.
make PYTHON=python install-codex
make PYTHON=python install-claude
make PYTHON=python install-opencode
```

Expected: Codex uses marketplace mode only; Claude updates the project-scoped plugin from `plugins/scholar`; OpenCode receives the verified `.opencode` projection. The Codex base manifest returns byte-for-byte to version `3.0.0` after its cachebusted install.

- [ ] **Step 6: Verify installed host state**

Run host list/version probes with Codex's local config override:

```bash
codex -c 'model_reasoning_effort="xhigh"' plugin list
claude plugin list --json
```

Verify `scholar@scholar-ip-copilot` is installed and enabled, the installed Codex version has exactly one cachebuster suffix, exactly seven public Scholar skills/commands are visible on each host, `.agents/skills/.evidraft-ownership.json` is absent in marketplace mode, OpenCode has seven commands and required private resources, no `*.evidraft.lock` remains, and `plugins/scholar/.codex-plugin/plugin.json` still reports base `3.0.0`.

- [ ] **Step 7: Final handoff**

Report commit IDs, exact verification commands and outcomes, any unavailable external host probe, and the installed versions. Instruct Alba to start a new Codex task and restart Claude/OpenCode sessions so caches reload the integrated plugin.
