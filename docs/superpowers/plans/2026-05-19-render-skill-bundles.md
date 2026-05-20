# Skill-Bundle Render Support — Implementation Plan (Path A)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the three rendering adapters (claude_code, codex_cli, opencode) plus the shared loader so each skill is treated as a **directory bundle**: its `SKILL.md` is still the entry, and **all sibling files / subdirectories** (`references/`, `assets/`, `scripts/`, etc.) are propagated to each rendered output. Unlocks progressive-disclosure authoring for the deepresearch split and any future skill that needs to externalise schemas, templates, or executable resources.

**Architecture:** Two-part change. (1) Loader: stop treating `skills/<id>/references/*.md` as additional skills (current `rglob("*.md")` does this); switch skill discovery to "one skill per immediate `<skills>/<id>/` directory, anchored on `SKILL.md`", and record `bundle_dir = SKILL.md.parent` on each `FrontmatterDoc`. Commands/agents/hooks loaders unchanged. (2) Each adapter's `render()` gains a small bundle-copy step after writing `SKILL.md`: walk `bundle_dir`, copy every file that is not `SKILL.md` itself, preserving sub-directory structure under the rendered skill directory.

**Tech Stack:** Python 3.11+, pyyaml, jsonschema (optional), pytest, existing `packages/adapters/{_shared,claude_code,codex_cli,opencode}/` rendering modules. No new dependencies.

**Branch:** `feat/render-skill-bundles` (from master at `65446d1` — `docs(spike): import OpenCode JS-plugin spike plan + verdict`).

**Spike provenance:** Spike `spike/opencode-js-plugin` (RED) ruled out runtime-path-registration on OpenCode 1.3.0. Path A (this plan) is the surviving option. See `docs/spike-results/2026-05-19-opencode-js-plugin.md` for the full "why not Path D" record.

**Open design decision (defaulted, controller may override):** For Codex CLI specifically, cross-skill relative links inside a `references/*.md` would break because Codex flattens source skills to `skills/scholar-skill-<id>/SKILL.md` and source commands to `skills/scholar-<cmd>/SKILL.md`. We default to **Option B from the architecture review**: do NOT auto-rewrite links; instead enforce a convention that `references/*.md` only links to **same-skill** files (e.g., `references/stage-2.md` links to `references/stage-3.md` are fine; cross-skill links must point at `SKILL.md` of another skill via `../../<other-skill>/SKILL.md` and Codex handles those at a different layer). This keeps the codex adapter under ~15 added lines. If the controller wants Option A (auto-rewriting) it doubles codex's task and adds a Codex-specific test.

---

## File Structure

| File | Role | Change |
|---|---|---|
| `packages/adapters/_shared/loader.py` | Frontmatter + plugin tree loader | Add `bundle_dir` field to `FrontmatterDoc`; add new `_load_skill_dir()`; route `load_plugin()` to use it for skills; update `validate()` to ignore non-SKILL.md bundle resources |
| `packages/adapters/claude_code/generate.py` | Claude Code adapter | After `target.write_text(...)` for each skill, copy bundle siblings to `<out>/skills/<id>/` |
| `packages/adapters/codex_cli/generate.py` | Codex CLI adapter | After `target.write_text(...)` for each source-skill rendered as `scholar-skill-<id>`, copy bundle siblings to `<out>/skills/scholar-skill-<id>/` |
| `packages/adapters/opencode/generate.py` | OpenCode adapter | After `target.write_text(...)` for each skill, copy bundle siblings to `<out>/skills/<id>/` |
| `tests/test_adapter_conformance.py` | Conformance harness | Add `test_invariant_f_bundle_resources_propagated` — exercises a tmp-fixture skill with a `references/` subdir and asserts each of the three adapters copies it. Existing tests must continue to pass. |
| `tests/fixtures/adapter_invariants/` | Fixture metadata | No structural change. (`expected_counts.json` counts `skills` by `id`, which already excludes `references/*.md` if loader is fixed.) |

**Files explicitly NOT touched in this plan** (deliberate scope-cut):
- Source skills under `plugins/scholar-ip/skills/*/SKILL.md` — no real `references/` files are created here. The deepresearch split that uses this capability is a separate follow-up plan.
- Codex link-rewriting logic (per Option B default above).
- `.gitignore`, `Makefile`, README — pipeline behavior changes are observable via tests; docs follow once stable.

---

## Task 0: Branch + verify clean baseline

**Files:**
- None (git operations only)

- [ ] **Step 1: Confirm starting state**

```bash
cd /Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot
git branch --show-current
git --no-pager log --oneline -1
git --no-pager status --short
```

Expected output:
```
master
65446d1 docs(spike): import OpenCode JS-plugin spike plan + verdict
```
Plus an empty status (no modifications). If status is non-empty, STOP and report.

- [ ] **Step 2: Create branch**

```bash
git checkout -b feat/render-skill-bundles
```

Expected: `Switched to a new branch 'feat/render-skill-bundles'`.

- [ ] **Step 3: Verify existing tests pass before any changes**

```bash
.venv/bin/python -m pytest tests/test_adapter_conformance.py -q 2>&1 | tail -10
```

Expected: all tests pass. Record the test count (e.g. `X passed in Y.YYs`) for comparison after each task. If any test fails, STOP — the baseline is broken; do not start work on top of red.

- [ ] **Step 4: Add this plan to the branch (it lives on master already, but a branch-local pointer is convenient for execute-time `cat` references)**

No commit needed — the plan file exists from master via the branch's initial state.

---

## Task 1: Loader supports skill bundles

**Files:**
- Modify: `packages/adapters/_shared/loader.py` — add `bundle_dir` field, new `_load_skill_dir()`, route `load_plugin()` skills path through it
- Create: `tests/test_loader_skill_bundles.py` — focused unit tests

- [ ] **Step 1: Write the failing test (FrontmatterDoc.bundle_dir)**

Create `tests/test_loader_skill_bundles.py`:

```python
"""Tests for skill-bundle support in the shared loader.

Each <skills>/<id>/ directory is one skill; SKILL.md is the entry, and the
parent directory (the bundle) carries arbitrary sibling files like
references/, assets/, or scripts/. The loader must (a) discover one skill per
bundle, (b) NOT treat references/*.md as additional skills, and (c) record
the bundle directory on the loaded FrontmatterDoc so adapters can propagate
the bundle into rendered output.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from packages.adapters._shared.loader import (
    FrontmatterDoc,
    load_plugin,
)


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


@pytest.fixture
def bundle_plugin(tmp_path: Path) -> Path:
    """A minimal plugin tree with one skill carrying a references/ bundle."""
    root = tmp_path / "plugin"
    _write(
        root / "plugin.yaml",
        "id: testplugin\nname: Testplugin\nversion: 0.0.1\n",
    )
    _write(
        root / "skills" / "alpha" / "SKILL.md",
        "---\nid: alpha\nkind: skill\ntitle: Alpha\ndescription: alpha skill\n---\n\nAlpha body.\n",
    )
    _write(
        root / "skills" / "alpha" / "references" / "stage-1.md",
        "# Stage 1\n\nReference content for stage 1.\n",
    )
    _write(
        root / "skills" / "alpha" / "references" / "schemas" / "plan.yaml",
        "version: 1\n",
    )
    _write(
        root / "skills" / "beta" / "SKILL.md",
        "---\nid: beta\nkind: skill\ntitle: Beta\ndescription: beta skill\n---\n\nBeta body.\n",
    )
    return root


def test_bundle_dir_recorded_on_frontmatterdoc(bundle_plugin: Path) -> None:
    """Each loaded skill carries its bundle_dir (parent of SKILL.md)."""
    plugin = load_plugin(bundle_plugin)
    by_id = {d.id: d for d in plugin.skills}
    assert by_id["alpha"].bundle_dir == bundle_plugin / "skills" / "alpha"
    assert by_id["beta"].bundle_dir == bundle_plugin / "skills" / "beta"
```

- [ ] **Step 2: Run the test to see it fail**

```bash
.venv/bin/python -m pytest tests/test_loader_skill_bundles.py::test_bundle_dir_recorded_on_frontmatterdoc -v 2>&1 | tail -15
```

Expected: FAIL with `AttributeError: 'FrontmatterDoc' object has no attribute 'bundle_dir'` (or similar — the field doesn't exist yet).

- [ ] **Step 3: Add bundle_dir to FrontmatterDoc and write `_load_skill_dir`**

Open `packages/adapters/_shared/loader.py`. Modify the `FrontmatterDoc` dataclass (currently lines 32-43):

```python
@dataclass
class FrontmatterDoc:
    """A single markdown file with YAML frontmatter and a body."""

    path: Path
    meta: dict[str, Any]
    body: str
    bundle_dir: Path | None = None

    @property
    def id(self) -> str:
        return str(self.meta.get("id") or self.path.stem)
```

Then add a new function `_load_skill_dir` immediately AFTER `_load_md_dir` (insert at the line currently after `return docs` in `_load_md_dir`):

```python
def _load_skill_dir(skills_dir: Path) -> list[FrontmatterDoc]:
    """Load skills as directory bundles: each <skills_dir>/<id>/SKILL.md is a skill.

    Each skill's parent directory becomes the bundle_dir on the FrontmatterDoc
    so adapters can propagate sibling files (references/, assets/, scripts/)
    into rendered output. Files under references/ etc. are NEVER treated as
    additional skills, even when they happen to be markdown.
    """
    if not skills_dir.exists():
        return []
    docs: list[FrontmatterDoc] = []
    for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        text = skill_md.read_text(encoding="utf-8")
        try:
            meta, body = split_frontmatter(text)
        except (yaml.YAMLError, ValueError) as exc:
            meta = {"_parse_error": str(exc), "id": skill_md.parent.name}
            body = text
        docs.append(
            FrontmatterDoc(path=skill_md, meta=meta, body=body, bundle_dir=skill_dir)
        )
    return docs
```

Update `load_plugin()` (currently around line 117-124) to route skills through the new function:

```python
    return Plugin(
        root=plugin_dir,
        manifest=manifest,
        commands=_load_md_dir(_sub("commands", "commands/")),
        agents=_load_md_dir(_sub("agents", "agents/")),
        skills=_load_skill_dir(_sub("skills", "skills/")),
        hooks=_load_md_dir(_sub("hooks", "hooks/")),
    )
```

- [ ] **Step 4: Run the test to see it pass**

```bash
.venv/bin/python -m pytest tests/test_loader_skill_bundles.py::test_bundle_dir_recorded_on_frontmatterdoc -v 2>&1 | tail -10
```

Expected: `1 passed`.

- [ ] **Step 5: Write the second failing test (references/ not loaded as skills)**

Append to `tests/test_loader_skill_bundles.py`:

```python
def test_references_not_loaded_as_separate_skills(bundle_plugin: Path) -> None:
    """skills/alpha/references/stage-1.md must NOT show up as its own skill."""
    plugin = load_plugin(bundle_plugin)
    skill_ids = {d.id for d in plugin.skills}
    assert skill_ids == {"alpha", "beta"}, (
        f"expected exactly {{alpha, beta}}, got {skill_ids} — "
        f"references/ files are being misclassified as skills"
    )
```

- [ ] **Step 6: Run the test to confirm it passes**

```bash
.venv/bin/python -m pytest tests/test_loader_skill_bundles.py -v 2>&1 | tail -10
```

Expected: `2 passed`. (Already passes by construction since `_load_skill_dir` walks one level only.)

- [ ] **Step 7: Write the third failing test (validate skips bundle resources)**

Append to `tests/test_loader_skill_bundles.py`:

```python
def test_validate_skips_bundle_resources(bundle_plugin: Path, tmp_path: Path) -> None:
    """validate() must not error on files inside references/ subdirs.

    The schema is loaded from packages/core/schemas/command.schema.json by
    callers; we synthesize a minimal compatible schema for unit-test isolation.
    """
    from packages.adapters._shared.loader import validate

    schema = tmp_path / "command.schema.json"
    schema.write_text(
        '{"type":"object","required":["id","title","kind"],'
        '"properties":{"kind":{"enum":["command","agent","skill","hook"]}}}',
        encoding="utf-8",
    )
    plugin = load_plugin(bundle_plugin)
    errors = validate(plugin, schema)
    # alpha and beta skills both have id+title+kind=skill — should validate clean.
    # The references/stage-1.md file MUST NOT appear in errors.
    refs_errors = [e for e in errors if "references" in e]
    assert refs_errors == [], (
        f"validate() raised errors on references/ files: {refs_errors}"
    )
```

- [ ] **Step 8: Run the test**

```bash
.venv/bin/python -m pytest tests/test_loader_skill_bundles.py::test_validate_skips_bundle_resources -v 2>&1 | tail -15
```

Expected: PASS. (Already passes — `validate()` only iterates `plugin.commands/agents/skills/hooks`, and `plugin.skills` no longer contains references/ files.)

- [ ] **Step 9: Run the existing conformance suite to verify no regression**

```bash
.venv/bin/python -m pytest tests/test_adapter_conformance.py -q 2>&1 | tail -5
```

Expected: same pass count as the Task 0 Step 3 baseline. If any test now fails, the loader change has a regression on real source skills (which currently have NO references/ subdirs, so a regression here would be surprising — debug before continuing).

- [ ] **Step 10: Commit**

```bash
git add packages/adapters/_shared/loader.py tests/test_loader_skill_bundles.py
git commit -m "feat(loader): support skill bundles

Each <skills>/<id>/ directory is treated as a bundle: SKILL.md is the
entry, the parent directory is recorded as bundle_dir on the loaded
FrontmatterDoc, and references/ / assets/ / scripts/ subfiles are no
longer misclassified as additional skills.

Adapters will use bundle_dir to propagate sibling files into rendered
output in a follow-up commit. Existing source skills (no bundles) load
unchanged."
```

Expected: one commit on `feat/render-skill-bundles`, 2 files (1 source modified, 1 test added).

---

## Task 2: OpenCode adapter copies bundle siblings

**Files:**
- Modify: `packages/adapters/opencode/generate.py` — bundle-copy step inside the skills loop
- Modify: `tests/test_loader_skill_bundles.py` — add adapter-specific tests

- [ ] **Step 1: Write the failing test**

Append to `tests/test_loader_skill_bundles.py`:

```python
def test_opencode_propagates_bundle_files(bundle_plugin: Path, tmp_path: Path) -> None:
    """OpenCode renders skills/<id>/SKILL.md AND every bundle sibling, with
    sub-directory structure preserved."""
    from packages.adapters.opencode.generate import render as render_opencode

    out_dir = tmp_path / "opencode-out"
    render_opencode(load_plugin(bundle_plugin), out_dir)

    # SKILL.md still rendered
    assert (out_dir / "skills" / "alpha" / "SKILL.md").is_file()

    # references/ subdir copied verbatim
    assert (out_dir / "skills" / "alpha" / "references" / "stage-1.md").is_file()
    content = (out_dir / "skills" / "alpha" / "references" / "stage-1.md").read_text()
    assert "Stage 1" in content

    # Nested subdir preserved
    assert (out_dir / "skills" / "alpha" / "references" / "schemas" / "plan.yaml").is_file()

    # Skill without a bundle (just SKILL.md) renders cleanly — no spurious extras
    beta_dir = out_dir / "skills" / "beta"
    beta_files = {p.name for p in beta_dir.iterdir() if p.is_file()}
    assert beta_files == {"SKILL.md"}, f"beta should have only SKILL.md, got {beta_files}"
```

- [ ] **Step 2: Run the test to see it fail**

```bash
.venv/bin/python -m pytest tests/test_loader_skill_bundles.py::test_opencode_propagates_bundle_files -v 2>&1 | tail -15
```

Expected: FAIL with assertion error on `out_dir / "skills" / "alpha" / "references" / "stage-1.md"` not existing.

- [ ] **Step 3: Implement bundle copy in OpenCode adapter**

Open `packages/adapters/opencode/generate.py`. Find the skills-render block (currently around lines 183-191):

```python
    if plugin.skills:
        skills_root = out_dir / "skills"
        for d in plugin.skills:
            sk_dir = skills_root / d.id
            sk_dir.mkdir(parents=True, exist_ok=True)
            fm = _skill_frontmatter(d.meta or {})
            target = sk_dir / "SKILL.md"
            target.write_text(dump_frontmatter(fm, d.body), encoding="utf-8")
            written.append(target)
```

Replace with the same code PLUS a bundle-copy step (insert `_copy_skill_bundle(...)` between the `target.write_text` and `written.append`):

```python
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
```

Add the `_copy_skill_bundle` helper near the top of the file (after the imports and `_CC_TO_OPENCODE_TOOL`, before the frontmatter translator functions — around line 56):

```python
def _copy_skill_bundle(doc: FrontmatterDoc, dest_skill_dir: Path) -> list[Path]:
    """Copy every file under doc.bundle_dir (except SKILL.md itself) into
    ``dest_skill_dir``, preserving sub-directory structure.

    Returns the list of destination paths written. Returns [] when doc has no
    bundle_dir (commands/agents/hooks-loader docs) or when the bundle is empty.
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
```

Add `import shutil` to the imports block at the top of the file (alongside the existing imports — around line 33-37). The `FrontmatterDoc` symbol is already imported from `_shared.loader`.

- [ ] **Step 4: Run the test to see it pass**

```bash
.venv/bin/python -m pytest tests/test_loader_skill_bundles.py::test_opencode_propagates_bundle_files -v 2>&1 | tail -10
```

Expected: `1 passed`.

- [ ] **Step 5: Run the full loader-bundle test file**

```bash
.venv/bin/python -m pytest tests/test_loader_skill_bundles.py -v 2>&1 | tail -10
```

Expected: all 4 tests pass.

- [ ] **Step 6: Run the existing conformance suite to verify no regression**

```bash
.venv/bin/python -m pytest tests/test_adapter_conformance.py -q 2>&1 | tail -5
```

Expected: same pass count as Task 0 baseline.

- [ ] **Step 7: Commit**

```bash
git add packages/adapters/opencode/generate.py tests/test_loader_skill_bundles.py
git commit -m "feat(opencode): copy skill bundle siblings to rendered output

After writing skills/<id>/SKILL.md the adapter now walks the source
bundle_dir recorded on each FrontmatterDoc and copies every non-SKILL.md
file, preserving sub-directory structure. references/, assets/, scripts/
all ride along automatically.

Skills without a bundle (commands/agents/hooks legacy docs, or skills
whose bundle dir contains only SKILL.md) render unchanged."
```

Expected: one commit, 2 files modified.

---

## Task 3: Claude Code adapter copies bundle siblings

**Files:**
- Modify: `packages/adapters/claude_code/generate.py` — bundle-copy step inside the skills loop
- Modify: `tests/test_loader_skill_bundles.py` — add adapter-specific test

- [ ] **Step 1: Write the failing test**

Append to `tests/test_loader_skill_bundles.py`:

```python
def test_claude_code_propagates_bundle_files(bundle_plugin: Path, tmp_path: Path) -> None:
    """Claude Code renders skills/<id>/SKILL.md AND every bundle sibling."""
    from packages.adapters.claude_code.generate import render as render_claude_code

    out_dir = tmp_path / "claude-out"
    render_claude_code(load_plugin(bundle_plugin), out_dir)

    assert (out_dir / "skills" / "alpha" / "SKILL.md").is_file()
    assert (out_dir / "skills" / "alpha" / "references" / "stage-1.md").is_file()
    assert (out_dir / "skills" / "alpha" / "references" / "schemas" / "plan.yaml").is_file()

    beta_dir = out_dir / "skills" / "beta"
    beta_files = {p.name for p in beta_dir.iterdir() if p.is_file()}
    assert beta_files == {"SKILL.md"}
```

- [ ] **Step 2: Run the test to see it fail**

```bash
.venv/bin/python -m pytest tests/test_loader_skill_bundles.py::test_claude_code_propagates_bundle_files -v 2>&1 | tail -10
```

Expected: FAIL.

- [ ] **Step 3: Implement bundle copy in Claude Code adapter**

Open `packages/adapters/claude_code/generate.py`. Find the skills-render block (currently around lines 402-410):

```python
    if plugin.skills:
        skills_root = out_dir / "skills"
        for d in plugin.skills:
            sk_dir = skills_root / d.id
            sk_dir.mkdir(parents=True, exist_ok=True)
            fm = _skill_frontmatter(d.meta or {})
            target = sk_dir / "SKILL.md"
            target.write_text(dump_frontmatter(fm, d.body), encoding="utf-8")
            written.append(target)
```

Replace with:

```python
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
```

Add the helper near the existing module-level helpers (insert after `_skill_frontmatter` around line 186):

```python
def _copy_skill_bundle(doc: FrontmatterDoc, dest_skill_dir: Path) -> list[Path]:
    """Copy every file under doc.bundle_dir (except top-level SKILL.md) into
    ``dest_skill_dir``, preserving sub-directory structure.

    Returns the list of destination paths written. Returns [] when doc has no
    bundle_dir or when the bundle contains only SKILL.md.
    """
    if doc.bundle_dir is None or not doc.bundle_dir.is_dir():
        return []
    written: list[Path] = []
    for src in sorted(doc.bundle_dir.rglob("*")):
        if not src.is_file():
            continue
        if src.name == "SKILL.md" and src.parent == doc.bundle_dir:
            continue
        rel = src.relative_to(doc.bundle_dir)
        dest = dest_skill_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        written.append(dest)
    return written
```

Verify `shutil` is already imported at the top of the file. If it is not, add `import shutil` to the imports block. (Note: `shutil` IS already imported per claude_code/generate.py:20 in current master; just confirm.)

- [ ] **Step 4: Run the test to see it pass**

```bash
.venv/bin/python -m pytest tests/test_loader_skill_bundles.py::test_claude_code_propagates_bundle_files -v 2>&1 | tail -10
```

Expected: `1 passed`.

- [ ] **Step 5: Run the existing conformance suite**

```bash
.venv/bin/python -m pytest tests/test_adapter_conformance.py -q 2>&1 | tail -5
```

Expected: same pass count as baseline.

- [ ] **Step 6: Commit**

```bash
git add packages/adapters/claude_code/generate.py tests/test_loader_skill_bundles.py
git commit -m "feat(claude_code): copy skill bundle siblings to rendered output

Mirrors the opencode adapter's bundle-copy step: after writing
skills/<id>/SKILL.md the adapter copies every non-SKILL.md file from
the source bundle_dir, preserving sub-directory structure."
```

Expected: one commit, 2 files modified.

---

## Task 4: Codex CLI adapter copies bundle siblings (Option B — no link rewriting)

**Files:**
- Modify: `packages/adapters/codex_cli/generate.py` — bundle-copy step on the source-skill rendering branch
- Modify: `tests/test_loader_skill_bundles.py` — add Codex-specific test

**Design note:** Codex flattens source skills to `skills/scholar-skill-<id>/`. The bundle is copied to the same flattened directory. We do NOT rewrite cross-skill relative links inside `references/*.md` (Option B). If an author writes `[next stage](references/stage-2.md)` inside `references/stage-1.md`, the link still works because both files land in the same `scholar-skill-<id>/references/` directory. If an author writes `[see other skill](../scholar-skill-other/SKILL.md)` (cross-skill), they must use the codex-prefixed form — which is brittle. The convention: keep cross-skill linkage at the SKILL.md level, not inside references/.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_loader_skill_bundles.py`:

```python
def test_codex_cli_propagates_bundle_files(bundle_plugin: Path, tmp_path: Path) -> None:
    """Codex CLI renders skills/scholar-skill-<id>/SKILL.md AND every bundle sibling."""
    from packages.adapters.codex_cli.generate import render as render_codex_cli

    out_dir = tmp_path / "codex-out"
    render_codex_cli(load_plugin(bundle_plugin), out_dir)

    # Source skills land under scholar-skill-<id>/ in Codex's flattened layout
    assert (out_dir / "skills" / "scholar-skill-alpha" / "SKILL.md").is_file()
    assert (out_dir / "skills" / "scholar-skill-alpha" / "references" / "stage-1.md").is_file()
    assert (out_dir / "skills" / "scholar-skill-alpha" / "references" / "schemas" / "plan.yaml").is_file()

    beta_dir = out_dir / "skills" / "scholar-skill-beta"
    beta_files = {p.name for p in beta_dir.iterdir() if p.is_file()}
    assert beta_files == {"SKILL.md"}
```

- [ ] **Step 2: Run the test to see it fail**

```bash
.venv/bin/python -m pytest tests/test_loader_skill_bundles.py::test_codex_cli_propagates_bundle_files -v 2>&1 | tail -10
```

Expected: FAIL.

- [ ] **Step 3: Implement bundle copy in Codex CLI adapter**

Open `packages/adapters/codex_cli/generate.py`. Find the source-skill rendering branch (currently around lines 280-288):

```python
    for d in plugin.skills:
        name = f"{SKILL_PREFIX}{d.id}"
        desc = (d.meta or {}).get("description") or (d.meta or {}).get("title") or d.id
        fm = {"name": name, "description": str(desc).strip()}
        body = _skill_skill_body(d)
        target = skills_root / name / "SKILL.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(dump_frontmatter(fm, body), encoding="utf-8")
        written.append(target)
```

Replace with:

```python
    for d in plugin.skills:
        name = f"{SKILL_PREFIX}{d.id}"
        desc = (d.meta or {}).get("description") or (d.meta or {}).get("title") or d.id
        fm = {"name": name, "description": str(desc).strip()}
        body = _skill_skill_body(d)
        target = skills_root / name / "SKILL.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(dump_frontmatter(fm, body), encoding="utf-8")
        written.append(target)
        written.extend(_copy_skill_bundle(d, target.parent))
```

Add `import shutil` to the imports block (Codex generate.py does NOT currently import shutil — confirm via `grep -n '^import' packages/adapters/codex_cli/generate.py`; add it if absent).

Add the `_copy_skill_bundle` helper near `_skill_skill_body` (around line 154):

```python
def _copy_skill_bundle(doc: FrontmatterDoc, dest_skill_dir: Path) -> list[Path]:
    """Copy every file under doc.bundle_dir (except top-level SKILL.md) into
    ``dest_skill_dir``, preserving sub-directory structure.

    Codex flattens source skills to skills/scholar-skill-<id>/; the bundle is
    propagated into that same flattened directory. We do NOT rewrite intra-
    bundle links — by convention, cross-skill linkage stays at SKILL.md level
    rather than inside references/.
    """
    if doc.bundle_dir is None or not doc.bundle_dir.is_dir():
        return []
    written: list[Path] = []
    for src in sorted(doc.bundle_dir.rglob("*")):
        if not src.is_file():
            continue
        if src.name == "SKILL.md" and src.parent == doc.bundle_dir:
            continue
        rel = src.relative_to(doc.bundle_dir)
        dest = dest_skill_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
        written.append(dest)
    return written
```

- [ ] **Step 4: Run the test to see it pass**

```bash
.venv/bin/python -m pytest tests/test_loader_skill_bundles.py::test_codex_cli_propagates_bundle_files -v 2>&1 | tail -10
```

Expected: `1 passed`.

- [ ] **Step 5: Run all bundle tests + conformance suite**

```bash
.venv/bin/python -m pytest tests/test_loader_skill_bundles.py tests/test_adapter_conformance.py -q 2>&1 | tail -5
```

Expected: all green, conformance count matches baseline.

- [ ] **Step 6: Commit**

```bash
git add packages/adapters/codex_cli/generate.py tests/test_loader_skill_bundles.py
git commit -m "feat(codex_cli): copy skill bundle siblings to rendered output

Source skills land at skills/scholar-skill-<id>/SKILL.md plus the
flattened bundle copy (references/, assets/, scripts/, ...). No
intra-bundle link rewriting — by convention cross-skill linkage stays
at SKILL.md level, not inside references/."
```

Expected: one commit, 2 files modified.

---

## Task 5: Conformance smoke test on the real source tree

**Files:**
- Modify: `tests/test_adapter_conformance.py` — add `test_invariant_f_bundle_resources_propagated`

The existing conformance tests already render each adapter and assert file counts. Source skills currently have NO references/ subdirs, so bundle behavior is a no-op on the real source tree. This task adds a positive assertion: when a source skill DOES have a bundle (validated in Task 6), it propagates correctly. For now (Task 5), the test exists and confirms the no-op case is clean.

- [ ] **Step 1: Read the existing conformance fixtures**

```bash
.venv/bin/python -c "import tests.test_adapter_conformance as t; import inspect; print(inspect.getsourcelines(t.rendered)[0])" 2>&1 | head -25
```

Expected: prints the `rendered` fixture body, confirming the harness renders `claude_code` and `codex_cli` once per module and caches by adapter id.

- [ ] **Step 2: Add the invariant test**

Append to `tests/test_adapter_conformance.py` (after the last existing test function — find the last `def test_` and add below it):

```python
# ---------------------------------------------------------------------------
# F. skill bundle propagation
# ---------------------------------------------------------------------------


def test_invariant_f_bundle_resources_propagated(
    plugin: Plugin,
    rendered: dict[str, dict[str, Any]],
) -> None:
    """For every source skill that has a bundle (any non-SKILL.md file under
    its directory), each writing adapter must render those files into the
    skill's rendered directory, preserving sub-paths.

    When no source skill has a bundle (current master baseline) this test is
    vacuously true — it asserts only what is present, never that bundles must
    exist."""
    skills_with_bundle = [
        d for d in plugin.skills
        if d.bundle_dir is not None
        and any(
            p.is_file() and not (p.name == "SKILL.md" and p.parent == d.bundle_dir)
            for p in d.bundle_dir.rglob("*")
        )
    ]

    for d in skills_with_bundle:
        bundle_rel_paths = sorted(
            str(p.relative_to(d.bundle_dir))
            for p in d.bundle_dir.rglob("*")
            if p.is_file() and not (p.name == "SKILL.md" and p.parent == d.bundle_dir)
        )

        # Claude Code: skills/<id>/<rel-path>
        cc_root = rendered["claude_code"]["root"]
        for rel in bundle_rel_paths:
            target = cc_root / "skills" / d.id / rel
            assert target.is_file(), (
                f"claude_code: missing bundle file skills/{d.id}/{rel}"
            )

        # Codex CLI: skills/scholar-skill-<id>/<rel-path>
        cx_root = rendered["codex_cli"]["root"]
        for rel in bundle_rel_paths:
            target = cx_root / "skills" / f"scholar-skill-{d.id}" / rel
            assert target.is_file(), (
                f"codex_cli: missing bundle file skills/scholar-skill-{d.id}/{rel}"
            )
```

- [ ] **Step 3: Run the new test**

```bash
.venv/bin/python -m pytest tests/test_adapter_conformance.py::test_invariant_f_bundle_resources_propagated -v 2>&1 | tail -10
```

Expected: `1 passed` (vacuously, since master source has no bundles yet).

- [ ] **Step 4: Run the full conformance suite to verify no regression**

```bash
.venv/bin/python -m pytest tests/test_adapter_conformance.py -q 2>&1 | tail -5
```

Expected: same pass count as baseline + 1 (the new test).

- [ ] **Step 5: Commit**

```bash
git add tests/test_adapter_conformance.py
git commit -m "test(conformance): assert skill bundles propagate (invariant F)

Vacuously true on current master (no source skill has a bundle yet);
becomes load-bearing the moment any source skill grows a references/
or assets/ subdir."
```

Expected: one commit, 1 file modified.

---

## Task 6: End-to-end smoke test on a real source skill

**Files:**
- Create: `plugins/scholar-ip/skills/using-deep-research/references/example.md` — minimal reference file
- Modify: `plugins/scholar-ip/skills/using-deep-research/SKILL.md` — add a single line linking to the reference

This task makes invariant F (Task 5) non-vacuous by introducing a real bundle resource. The chosen skill is `using-deep-research` because the deepresearch-split follow-up plan will heavily extend its references/ — this is a one-line bootstrap of that direction.

- [ ] **Step 1: Create the reference file**

Write `plugins/scholar-ip/skills/using-deep-research/references/example.md`:

```markdown
# Example bundle reference

This file demonstrates that skills can ship companion documents under a
`references/` subdirectory. The render pipeline propagates it to every
adapter output.

Real reference content for the deepresearch workflow will land here in a
follow-up plan (`docs/superpowers/plans/<date>-deepresearch-split.md`).
```

- [ ] **Step 2: Reference it from SKILL.md**

Open `plugins/scholar-ip/skills/using-deep-research/SKILL.md`. Find the line that says "Read this once" (around line 15 per the file audit earlier in this session — confirm with `grep -n 'Read this once' plugins/scholar-ip/skills/using-deep-research/SKILL.md` first; if the line moved, search for a nearby anchor).

Add a single line ABOVE that anchor:

```markdown
See [references/example.md](references/example.md) for the bundle-resource
demonstration pattern (propagated to every host's rendered output by the
loader's skill-bundle support).
```

If the SKILL.md no longer has the exact "Read this once" anchor (due to other edits), put this line immediately after the frontmatter close (`---`) and the first heading. Exact placement is less important than the line existing.

- [ ] **Step 3: Render and verify**

```bash
make render 2>&1 | tail -5
```

Expected: all three adapters render with no errors. Verify the bundle landed in each output:

```bash
ls .claude/plugins/scholar-ip/skills/using-deep-research/references/example.md
ls .codex/plugins/scholar/skills/scholar-skill-using-deep-research/references/example.md
ls .opencode/skills/using-deep-research/references/example.md
```

Expected: all three files exist. If any is missing, the bundle-copy step in that adapter has a bug — debug before continuing.

- [ ] **Step 4: Run the full test suite to verify the now-non-vacuous invariant F passes**

```bash
.venv/bin/python -m pytest tests/ -q 2>&1 | tail -10
```

Expected: all tests pass, including `test_invariant_f_bundle_resources_propagated` (now exercises the real `using-deep-research` bundle).

- [ ] **Step 5: Commit**

```bash
git add plugins/scholar-ip/skills/using-deep-research/SKILL.md plugins/scholar-ip/skills/using-deep-research/references/example.md
git commit -m "feat(scholar): bootstrap skill-bundle pattern on using-deep-research

Adds plugins/scholar-ip/skills/using-deep-research/references/example.md
and a one-line pointer from the SKILL.md. Demonstrates the bundle
authoring pattern end-to-end and makes test_invariant_f_bundle_resources
_propagated non-vacuous.

Real deepresearch references/ content lands in a follow-up plan."
```

Expected: one commit, 2 files (1 modified, 1 new).

---

## Task 7: Final state, PR description draft

**Files:**
- None (git operations + summary)

- [ ] **Step 1: Verify the full chain on the branch**

```bash
git --no-pager log --oneline master..HEAD
```

Expected: 6 commits, one per Task 1-6 (plus this verification doesn't add anything). Read the subjects:
```
<sha> feat(scholar): bootstrap skill-bundle pattern on using-deep-research
<sha> test(conformance): assert skill bundles propagate (invariant F)
<sha> feat(codex_cli): copy skill bundle siblings to rendered output
<sha> feat(claude_code): copy skill bundle siblings to rendered output
<sha> feat(opencode): copy skill bundle siblings to rendered output
<sha> feat(loader): support skill bundles
```

- [ ] **Step 2: Run the full test suite one more time**

```bash
.venv/bin/python -m pytest tests/ -q 2>&1 | tail -10
```

Expected: all pass.

- [ ] **Step 3: Run `make render` to confirm the rendered tree is consistent**

```bash
make render 2>&1 | tail -10
```

Expected: clean render, no errors. The three rendered trees (`.claude/`, `.codex/`, `.opencode/`) now each contain `using-deep-research/references/example.md` (or the codex-flattened equivalent).

- [ ] **Step 4: Print the PR description for the human to copy/paste when ready**

The controller prints this verbatim to the user; no commit:

```markdown
## Summary
- Loader treats each `skills/<id>/` as a directory bundle: SKILL.md is the entry, the parent directory is recorded as `bundle_dir`, and any sibling files (`references/`, `assets/`, `scripts/`) ride along into every rendered host output. Unblocks progressive-disclosure authoring (e.g. the upcoming deepresearch split).
- All three adapters (claude_code, codex_cli, opencode) gain a small `_copy_skill_bundle` helper invoked after each SKILL.md write. Codex does NOT rewrite intra-bundle links (Option B from the architecture review).
- New invariant `test_invariant_f_bundle_resources_propagated` asserts the propagation. A minimal `using-deep-research/references/example.md` makes the invariant non-vacuous.

## Background
Spike `spike/opencode-js-plugin` ruled out runtime-path-registration on OpenCode 1.3.0 (RED). See `docs/spike-results/2026-05-19-opencode-js-plugin.md`. Path A (this PR) is the surviving option.

## Test plan
- [x] `pytest tests/test_loader_skill_bundles.py` — 4 unit tests for loader + each adapter
- [x] `pytest tests/test_adapter_conformance.py` — existing invariants + new invariant F
- [x] `make render` — all three host outputs include the example bundle file
```

- [ ] **Step 5: Final report to user**

The controller surfaces:
- Branch: `feat/render-skill-bundles` (local, unpushed)
- 6 commits total
- All tests green
- Render produces bundles in all three host outputs
- Ready for review or push at the user's discretion

Do NOT push without explicit user consent. Do NOT open a PR without explicit user consent.

---

## Rollback

If a downstream user reports the change broke their existing skill discovery:

```bash
git checkout master
git branch -D feat/render-skill-bundles
```

The change is purely additive (existing skills without `references/` render identically; the only behavior change is the loader no longer treats `skills/<id>/references/foo.md` as a separate skill — and no source skill has such a file today, so the change is invisible to current callers).

---

## Out of scope (explicitly excluded)

- The deepresearch split itself (separate plan). This plan only unblocks it.
- Codex intra-bundle link rewriting (Option A). Plan defaults to Option B (no rewriting); if the controller wants A it adds ~30 lines to Task 4 plus a codex-specific link-rewrite test.
- Bundle support for commands/agents/hooks. Skills only — the bundle pattern is an Anthropic skills convention, not a generic adapter-input concept. YAGNI for other resources.
- README / docs/architecture.md updates. The pipeline behavior is observable via tests; docs follow once the deepresearch split lands and the pattern is in active use.
- Performance hardening. The bundle copy uses `shutil.copyfile` per file; for very large bundles this would be a hotspot, but no source skill comes close to "large" today.
