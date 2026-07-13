# Paper Explanation Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `research.explain`, an evidence-grounded single-paper workflow that writes an academic Markdown reading note with mandatory verified similar and recent methods.

**Architecture:** Keep the seven-workflow public surface and add `explain` beneath the existing `research` router. A private `paper-explanation` capability defines the note contract, a deep-tier `paper-explainer` mode owns full-text analysis and synthesis, and the existing `literature-reviewer` plus `scholar-search` own mandatory external research. The frozen 22-command migration fixture remains unchanged; tests explicitly register the new native v2 action and resources.

**Tech Stack:** YAML workflow IR, Markdown specifications, Python 3.10+, PyYAML, jsonschema, pytest, Ruff, shared EviDraft renderer, Codex plugin CLI.

## Global Constraints

- Run Python, tests, renderers, and linters through `.venv`.
- Follow strict Red-Green-Refactor and observe each expected failure before production edits.
- Keep exactly seven public workflows; add only `research.explain`.
- Accept local PDF, arXiv ID/URL, DOI, or paper URL as `source`.
- Support `beginner`, `graduate`, and `reviewer`; default to `graduate`.
- Default output: `.evidraft/notes/paper-explanations/<paper-slug>.md`.
- Do not require project initialisation or scope approval.
- Do not write BibTeX, evidence records, manuscript files, or project status.
- External research is mandatory: target 3-5 verified similar methods and 3-5 verified subsequent or newest-found methods.
- A completed note requires readable source full text and successful external retrieval.
- Preserve non-empty notes unless `overwrite` is explicitly confirmed; recommend `augment` for freshness updates.
- Distinguish source-paper evidence, external evidence, abstract-only evidence, and interpretation.
- Add no dependencies.

---

### Task 1: Add private explanation primitives

**Files:**
- Create: `plugins/scholar-ip/capabilities/research/paper-explanation/spec.md`
- Create: `plugins/scholar-ip/roles/modes/paper-explainer.md`
- Modify: `plugins/scholar-ip/capabilities/index.yaml`
- Modify: `plugins/scholar-ip/roles/roles.yaml`
- Modify: `src/evidraft/render.py`
- Test: `tests/test_v2_capabilities.py`
- Test: `tests/test_v2_role_modes.py`
- Test: `tests/test_v2_renderer.py`

**Interfaces:**
- Consumes: `capability:scholar-search`, the researcher registry, and renderer validation.
- Produces: `capability:paper-explanation` and researcher mode `paper-explainer` at tier `deep`.

- [ ] **Step 1: Write failing resource tests**

In `tests/test_v2_capabilities.py`, add `paper-explanation` to the research group, rename the legacy-only test to `test_capability_index_maps_all_private_capabilities_into_seven_groups`, and change `assert len(entries) == 25` to `assert len(entries) == 26`.

In `tests/test_v2_role_modes.py`, keep `EXPECTED` and `MODE_SPEC_SHA256` as frozen v1-derived maps, then add:

```python
NATIVE_EXPECTED = {
    "paper-explainer": ("researcher", "deep", 7, 7, 7, 7),
}
ALL_EXPECTED = EXPECTED | NATIVE_EXPECTED
```

Use `ALL_EXPECTED` in the registry and semantic-section tests. Keep the frozen SHA test iterating over `MODE_SPEC_SHA256` only.

In `tests/test_v2_renderer.py`, add:

```python
@pytest.mark.parametrize("host", list(Host))
def test_render_copies_native_paper_explanation_resources(tmp_path: Path, host: Host) -> None:
    out = tmp_path / host.value
    render_plugin(PLUGIN_ROOT, out, host)
    private = out / (
        "skills/.evidraft-private" if host is Host.CODEX else "private"
    )
    assert (private / "capabilities/research/paper-explanation/spec.md").is_file()
    assert (private / "roles/modes/paper-explainer.md").is_file()
```

- [ ] **Step 2: Verify Red**

Run:

```bash
.venv/bin/python -m pytest \
  tests/test_v2_capabilities.py \
  tests/test_v2_role_modes.py \
  tests/test_v2_renderer.py::test_render_copies_native_paper_explanation_resources -q
```

Expected: failures for missing `paper-explanation`, missing `paper-explainer`, and the renderer's 25-capability/15-mode constraints.

- [ ] **Step 3: Create the capability spec**

Create `plugins/scholar-ip/capabilities/research/paper-explanation/spec.md` with:

```yaml
---
id: paper-explanation
title: Evidence-grounded single-paper explanation
kind: skill
phase: shared
description: >
  Read one paper at full-text level, explain it at beginner, graduate, or
  reviewer depth, and produce a durable academic note with mandatory verified
  similar, subsequent, and newest-found related methods.
triggers:
  - "workflow:research.explain"
  - "explain this paper"
  - "close-read this paper"
  - "explain the equations in this paper"
provides:
  - paper-source-resolution
  - three-mode-explanation
  - evidence-labelled-note-schema
  - mandatory-related-method-landscape
allowed_tools: [Read, Glob, Grep, Write, Edit, WebSearch, WebFetch]
policies: [workspace-safety]
references:
  - doc: capability:scholar-search
---
```

Its body must contain executable instructions under these headings:

```markdown
# paper-explanation
## Source resolution
## Mode contract
## Required note schema
## Evidence labels
## Mandatory external research
## Collision protocol
## Failure contract
## Completion checklist
```

Copy the twelve note headings, evidence-label semantics, 3-5 plus 3-5 targets, dated search-scope rules, collision behaviour, and incomplete outcomes exactly from the approved design. Do not use placeholder prose.

- [ ] **Step 4: Create and register the role mode**

Create `plugins/scholar-ip/roles/modes/paper-explainer.md` with exactly seven entries in each counted list:

```yaml
---
id: paper-explainer
title: Full-text paper explainer and synthesis owner
allowed_tools: [Read, Glob, Grep, Write, Edit, WebSearch, WebFetch]
role: >
  Own the full-text analysis and final synthesis for research.explain while
  preserving the boundary between paper evidence, external evidence, and
  interpretation.
description: >
  Use for one identifiable paper when the deliverable is a durable academic
  reading note rather than a literature matrix or manuscript section.
responsibilities:
  - Resolve and verify the source paper identity.
  - Read full text and map sections, equations, figures, and tables.
  - Apply the selected mode without dropping required sections.
  - Explain key equations symbol by symbol and label derivations.
  - Integrate the verified related-method landscape.
  - Write exactly one collision-safe Markdown reading note.
  - Report source status, mode, cutoff, counts, and output path.
constraints:
  - Never complete from a source-paper abstract alone.
  - Never invent metadata, section labels, equations, results, or URLs.
  - Never present interpretation as an author claim.
  - Never omit mandatory external research or its cutoff.
  - Never call newest-found work an absolute state of the art.
  - Never modify BibTeX, evidence, manuscript, or project status.
  - Never overwrite a non-empty note without explicit approval.
review_checklist:
  - Source identity and readable full text are verified.
  - All twelve required note headings are present.
  - Every technical claim carries the correct evidence label.
  - Key equations define every explained symbol.
  - Related-method targets are met or the shortfall is evidenced.
  - Queries, providers, cutoff, and rejections are recorded.
  - The report states path and completion status accurately.
references:
  - doc: ../../capabilities/research/paper-explanation/spec.md
  - doc: ../../capabilities/research/scholar-search/spec.md
policies:
  - workspace-safety
---
```

The body must include `## Inputs you read`, `## Outputs you write`, `## Synthesis protocol`, and `## Failure modes you avoid`. State that only `paper-explainer` writes the final note.

Register `paper-explainer: modes/paper-explainer.md` under the deep tier and add `paper-explainer` to the researcher modes in `plugins/scholar-ip/roles/roles.yaml`.

- [ ] **Step 5: Index and validate native resource counts**

Compute the capability digest with:

```bash
.venv/bin/python -c 'from pathlib import Path; import hashlib; root=Path("plugins/scholar-ip/capabilities/research/paper-explanation"); d=hashlib.sha256(); [(d.update(p.relative_to(root).as_posix().encode()), d.update(b"\0"), d.update(p.read_bytes()), d.update(b"\0")) for p in sorted(x for x in root.rglob("*") if x.is_file())]; print(d.hexdigest())'
```

Use `apply_patch` to add `paper-explanation` to
`plugins/scholar-ip/capabilities/index.yaml` with `group: research`,
`spec: research/paper-explanation/spec.md`, and `bundle_sha256` set to the exact
64-character digest printed by that command. Do not copy a digest from another
capability.

In `src/evidraft/render.py`, change the closed counts to 16 role modes and 26 capabilities, including the same values in their error messages.

- [ ] **Step 6: Verify Green and commit**

Run the Step 2 command. Expected: zero failures.

```bash
git add plugins/scholar-ip/capabilities plugins/scholar-ip/roles \
  src/evidraft/render.py tests/test_v2_capabilities.py \
  tests/test_v2_role_modes.py tests/test_v2_renderer.py
git commit -m "feat(research): add paper explanation primitives"
```

---

### Task 2: Expose `research.explain`

**Files:**
- Modify: `plugins/scholar-ip/plugin.yaml`
- Modify: `plugins/scholar-ip/workflows/research/workflow.yaml`
- Modify: `plugins/scholar-ip/workflows/research/SKILL.md`
- Create: `plugins/scholar-ip/workflows/research/stages/explain.md`
- Modify: `src/evidraft/render.py`
- Test: `tests/test_v2_release_surface.py`
- Test: `tests/test_v2_workflow_source.py`
- Test: `tests/test_v2_contract_mapping.py`
- Test: `tests/test_v2_renderer.py`

**Interfaces:**
- Consumes: `paper-explanation`, `paper-explainer`, `literature-reviewer`, and `scholar-search`.
- Produces: `workflow:research.explain` with `source`, `mode`, `out`, and one Markdown output.

- [ ] **Step 1: Write failing action tests**

Update release and renderer expectations:

```python
# tests/test_v2_release_surface.py
"research": ["guide", "reading-list", "explain", "deep"],

# tests/test_v2_renderer.py
def test_load_workflows_exposes_seven_entries_and_twenty_three_actions() -> None:
    workflows = load_workflows(PLUGIN_ROOT)
    assert set(workflows) == PUBLIC_IDS
    assert sum(len(workflow.actions) for workflow in workflows.values()) == 23
```

In `tests/test_v2_workflow_source.py`, retain `ROUTES` as the frozen legacy map and add:

```python
NATIVE_ACTIONS = {"research": {"explain": "paper-explain"}}

def _all_actions(workflow_id: str) -> dict[str, str]:
    return ROUTES[workflow_id] | NATIVE_ACTIONS.get(workflow_id, {})
```

Use `_all_actions` for current action-set, router, role/policy, and procedure checks. Keep `STAGE_BODY_SHA256` and the exact 22-command assertions iterating only over `ROUTES`.

In `tests/test_v2_contract_mapping.py`, add `NATIVE_ACTIONS_BY_WORKFLOW = {"research": {"explain"}}` and make the exact-action test expect the frozen action set union the native set. Do not modify the frozen JSON fixture or digest.

Add this contract assertion in `tests/test_v2_workflow_source.py`:

```python
def test_research_explain_declares_the_native_paper_note_contract() -> None:
    action = _load_yaml(WORKFLOW_ROOT / "research" / "workflow.yaml")["actions"]["explain"]
    assert action["legacy_id"] == "paper-explain"
    assert action["defaults"] == {"mode": "graduate"}
    assert [item["name"] for item in action["inputs"]] == ["source", "mode", "out"]
    assert action["inputs"][1]["values"] == ["beginner", "graduate", "reviewer"]
    assert action["outputs"] == [
        {"path": ".evidraft/notes/paper-explanations/<paper-slug>.md"}
    ]
    assert action["policies"] == []
    assert action["roles"] == [
        {"id": "researcher", "mode": "paper-explainer", "tier": "deep"},
        {"id": "researcher", "mode": "literature-reviewer", "tier": "standard"},
    ]
    assert action["retention"] == {}
```

`paper-explain` occupies the schema-required `legacy_id` field as a stable operation key but is not added to the v1 migration fixture.

- [ ] **Step 2: Verify Red**

```bash
.venv/bin/python -m pytest \
  tests/test_v2_release_surface.py::test_manifest_declares_only_the_v2_authoring_surface \
  tests/test_v2_workflow_source.py::test_research_explain_declares_the_native_paper_note_contract \
  tests/test_v2_contract_mapping.py::test_v2_workflow_exposes_exact_action_set \
  tests/test_v2_renderer.py::test_load_workflows_exposes_seven_entries_and_twenty_three_actions -q
```

Expected: missing `research.explain` and 22-action validation failures.

- [ ] **Step 3: Add the public action contract**

Set research actions in `plugins/scholar-ip/plugin.yaml` to `[guide, reading-list, explain, deep]`.

Add to `plugins/scholar-ip/workflows/research/workflow.yaml`:

```yaml
  explain:
    legacy_id: paper-explain
    procedure: stages/explain.md
    defaults: {mode: graduate}
    inputs:
    - name: source
      type: string
      optional: false
      description: Local PDF path, arXiv identifier or URL, DOI, or paper URL.
    - name: mode
      type: enum
      values: [beginner, graduate, reviewer]
      optional: true
      default: graduate
      description: Explanation emphasis; every mode retains the complete note schema.
    - name: out
      type: path
      optional: true
      description: Override .evidraft/notes/paper-explanations/<paper-slug>.md.
    outputs:
    - path: .evidraft/notes/paper-explanations/<paper-slug>.md
    policies: []
    roles:
    - id: researcher
      mode: paper-explainer
      tier: deep
    - id: researcher
      mode: literature-reviewer
      tier: standard
    retention: {}
```

Add ``- `explain`: load `stages/explain.md`.`` to the research router. Add `explain` to the research set in `src/evidraft/render.py`.

- [ ] **Step 4: Create the executable stage**

Create `plugins/scholar-ip/workflows/research/stages/explain.md` with links to the private paper-explanation and scholar-search specs and these exact sections:

```markdown
# workflow:research.explain
## Phase 1: Resolve source and output
## Phase 2: Map the source paper
## Phase 3: Run bounded analysis work streams
## Phase 4: Synthesize the academic note
## Phase 5: Validate and report
## Constraints
## Done criteria
```

Phase 1 must classify and verify source identity, require readable full text, derive an ASCII slug, run preflight for the concrete output, and resolve `reuse/augment/overwrite`. Phase 3 must assign source analysis to `paper-explainer` and mandatory related-work retrieval to `literature-reviewer`; after shared metadata is resolved, parallel dispatch is allowed, but neither worker may race on the final file. Phase 4 must include the full twelve-heading note skeleton, all evidence labels, 3-5 plus 3-5 verified targets, query/provider/cutoff/rejection metadata, and the selected-mode emphasis. Phase 5 must report path, mode, full-text status, cutoff, included counts, and rejected count, and must report incomplete when source full text or external retrieval failed.

- [ ] **Step 5: Verify Green and commit**

Run the Step 2 command, then:

```bash
.venv/bin/python -m pytest tests/test_v2_workflow_source.py \
  tests/test_v2_contract_mapping.py tests/test_v2_release_surface.py \
  tests/test_v2_renderer.py -q
```

Expected: zero failures and an unchanged frozen fixture.

```bash
git add plugins/scholar-ip/plugin.yaml plugins/scholar-ip/workflows/research \
  src/evidraft/render.py tests/test_v2_release_surface.py \
  tests/test_v2_workflow_source.py tests/test_v2_contract_mapping.py \
  tests/test_v2_renderer.py
git commit -m "feat(research): expose paper explanation workflow"
```

---

### Task 3: Route single-paper requests through `using`

**Files:**
- Modify: `plugins/scholar-ip/capabilities/research/using-scholar-ip-copilot/spec.md`
- Modify: `plugins/scholar-ip/capabilities/index.yaml`
- Modify: `README.md`
- Modify: `plugins/scholar-ip/README.md`
- Create: `tests/test_paper_explanation_routing.py`

**Interfaces:**
- Consumes: `workflow:research.explain`.
- Produces: English and Chinese single-paper routing plus public usage/output documentation.

- [ ] **Step 1: Write failing routing tests**

Create `tests/test_paper_explanation_routing.py`:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "scholar-ip"


def test_using_routes_unambiguous_single_paper_requests_to_explain() -> None:
    spec = (PLUGIN / "capabilities/research/using-scholar-ip-copilot/spec.md").read_text()
    for token in (
        "workflow:research.explain",
        "single identifiable paper",
        "local PDF",
        "arXiv",
        "DOI",
        "paper URL",
        "confirm",
        "ambiguous",
        "workflow:research.deep",
    ):
        assert token in spec


def test_public_docs_list_explain_and_its_note_output() -> None:
    root = (ROOT / "README.md").read_text()
    plugin = (PLUGIN / "README.md").read_text()
    for text in (root, plugin):
        assert "`guide`, `reading-list`, `explain`, `deep`" in text
    assert "`research explain`" in root
    assert ".evidraft/notes/paper-explanations/<paper-slug>.md" in root
```

- [ ] **Step 2: Verify Red**

```bash
.venv/bin/python -m pytest tests/test_paper_explanation_routing.py -q
```

Expected: two failures because routing and docs do not mention `explain`.

- [ ] **Step 3: Add the routing branch**

Add to the intent section of `using-scholar-ip-copilot/spec.md`:

```markdown
### Single-paper explanation routing

- If the user supplies a local PDF, arXiv identifier/URL, DOI, or paper URL and
  asks to explain, analyse, close-read, interpret equations, critique, or
  produce an academic reading note, recommend `workflow:research.explain`.
- If the user names one uniquely identifiable paper with the same intent,
  recommend `workflow:research.explain`.
- Recognise equivalent Chinese intent for paper explanation, close reading,
  formula analysis, and academic reading notes.
- `workflow:using.run` remains read-only: recommend and confirm before invoking.
- If the name is ambiguous between papers, methods, projects, or research
  directions, resolve or ask for the specific paper first.
- Route an entire research direction to `workflow:research.deep`, not explain.
```

Add `workflow:research.explain` to the command map as a full-text explanation with mandatory verified related methods and one academic Markdown note.

- [ ] **Step 4: Refresh the modified capability digest**

```bash
.venv/bin/python -c 'from pathlib import Path; import hashlib; root=Path("plugins/scholar-ip/capabilities/research/using-scholar-ip-copilot"); d=hashlib.sha256(); [(d.update(p.relative_to(root).as_posix().encode()), d.update(b"\0"), d.update(p.read_bytes()), d.update(b"\0")) for p in sorted(x for x in root.rglob("*") if x.is_file())]; print(d.hexdigest())'
```

Replace only `using-scholar-ip-copilot.bundle_sha256` in the capability index with the printed digest.

- [ ] **Step 5: Update public docs**

List research actions as `guide`, `reading-list`, `explain`, `deep` in both READMEs. Add this example:

```text
$scholar-research explain papers/attention-is-all-you-need.pdf --mode graduate
```

Add this output row:

```markdown
| `research explain` | `.evidraft/notes/paper-explanations/<paper-slug>.md` |
```

Keep the seven-workflow claim and preserve references to 22 frozen legacy commands; current native action totals may say 23.

- [ ] **Step 6: Verify Green and commit**

```bash
.venv/bin/python -m pytest tests/test_paper_explanation_routing.py \
  tests/test_v2_capabilities.py tests/test_v2_release_surface.py -q
```

Expected: zero failures.

```bash
git add plugins/scholar-ip/capabilities/research/using-scholar-ip-copilot/spec.md \
  plugins/scholar-ip/capabilities/index.yaml README.md \
  plugins/scholar-ip/README.md tests/test_paper_explanation_routing.py
git commit -m "docs(using): route single-paper explanation requests"
```

---

### Task 4: Verify, render, validate, and reinstall

**Files:**
- Regenerate ignored outputs: `.claude/`, `.codex/`, `.opencode/`, `.agents/skills/`
- Update ignored generated manifest: `.codex/plugins/scholar/.codex-plugin/plugin.json`
- No tracked source files change in this task.

**Interfaces:**
- Consumes: Tasks 1-3.
- Produces: verified three-host output and a refreshed locally installed Codex plugin.

- [ ] **Step 1: Run feature and full suites**

```bash
.venv/bin/python -m pytest tests/test_paper_explanation_routing.py \
  tests/test_v2_capabilities.py tests/test_v2_role_modes.py \
  tests/test_v2_workflow_source.py tests/test_v2_contract_mapping.py \
  tests/test_v2_release_surface.py tests/test_v2_renderer.py -q
.venv/bin/python -m pytest tests/ -q
```

Expected: both commands exit zero with no failures.

- [ ] **Step 2: Run lint and render all hosts**

```bash
.venv/bin/python -m ruff check src packages tests
make PYTHON=.venv/bin/python render
```

Expected: Ruff reports `All checks passed!`; all three render commands exit zero.

- [ ] **Step 3: Inspect rendered resources**

```bash
rg -n "^  explain:|paper-explanation|paper-explainer" \
  .claude/plugins/scholar-ip .codex/plugins/scholar .opencode
```

Expected: each host contains the action, private capability, and private role mode.

- [ ] **Step 4: Validate plugin packages**

```bash
.venv/bin/python /Users/fsm/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py \
  .codex/plugins/scholar
```

Expected: zero exit and no Codex manifest errors.

If `claude` is available, also run `make PYTHON=.venv/bin/python plugin-validate`. If unavailable, report that limitation without weakening the Python, renderer, or Codex results.

- [ ] **Step 5: Inspect tracked state**

```bash
git status --short
git diff --check
git log -4 --oneline
```

Expected: no unstaged tracked changes, no whitespace errors, and the design plus three implementation commits. Inspect changed files for unintended edits and secret-like values.

- [ ] **Step 6: Cachebust and reinstall from the existing local marketplace**

```bash
.venv/bin/python /Users/fsm/.codex/skills/.system/plugin-creator/scripts/update_plugin_cachebuster.py \
  .codex/plugins/scholar
.venv/bin/python /Users/fsm/.codex/skills/.system/plugin-creator/scripts/read_marketplace_name.py \
  --marketplace-path .agents/plugins/marketplace.json
```

Expected marketplace name: `scholar-ip-copilot`.

Run `codex plugin list` and confirm `scholar@scholar-ip-copilot` points to this repository's local `.codex/plugins/scholar`. If confirmed:

```bash
codex plugin add scholar@scholar-ip-copilot
codex plugin list
```

Expected: install/update succeeds and the plugin is installed and enabled. If the marketplace is absent or points elsewhere, stop before marketplace mutation and report the mismatch; never hand-edit `marketplace.json` or `config.toml`.

- [ ] **Step 7: Handoff**

Advise testing `$scholar-using` and `$scholar-research explain` in a new Codex task so the refreshed skills are loaded.
