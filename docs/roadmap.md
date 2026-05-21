# Roadmap

> Status legend: `done` `mvp` `next` `later`

## v0.1 — MVP skeleton (this milestone)

`mvp`

- [x] Monorepo layout: `docs/`, `plugins/scholar-ip/`, `packages/core/`, `packages/adapters/`, `packages/mcp/`, `examples/`, `tests/`
- [x] Core JSON schemas: `project`, `evidence`, `paper`, `patent`, `command`
- [x] `plugins/scholar-ip/plugin.yaml` — single authoring manifest
- [x] 14 commands (`paper-*` × 8, `patent-*` × 6) as platform-neutral markdown prompts
- [x] 9 specialist agents
- [x] 7 skills (literature-review, evidence-check, codebase-audit, experiment-analysis, latex-writing, patent-disclosure, patent-claims)
- [x] 4 hook specs (citation-guard, evidence-consistency, latex-compile, sensitive-file-guard)
- [x] 2 templates (`paper-project/`, `patent-project/`)
- [x] Claude Code adapter (markdown generator + plugin.json emitter)
- [x] Codex CLI adapter (prompt/workflow emitter)
- [x] OpenCode adapter (docs + stubbed generator)
- [x] MCP stubs with documented interfaces for 6 servers (deleted in v0.2 — see below)
- [x] Examples: `cv-detection-paper/`, `generic-paper/`, `patent-disclosure/`
- [x] Reference analysis of 10 upstream projects

## v0.2 — Host-native skills + hardening

`next`

- [x] 5 new skills (`scholar-search`, `bib-manager`, `latex-build`, `code-intel`, `patent-search`) using host-native `WebSearch` / `WebFetch` / `Bash`
- [x] Delete 7 MCP stub packages — replaced by skills
- [x] `retention:` adapter enforcement wired
- [x] schema fixture pytest gate + minimal CI

## v0.3 — Patent depth (skill-only)

`done`

- [x] `claim-parser` skill — parses `claims.md` into `claims_parsed.json` (preamble + transition + bracketed elements + antecedent chain + dependency graph); 9 structural warnings (4 `fail`, 4 `warn`, 1 `info`)
- [x] `claim-chart-builder` skill — emits `claim_chart.md` + `claim_chart-<ts>.json` with `overlap_score ∈ {none, low, medium, high, identical}` (`identical` requires verbatim quote), risk roll-up rule, suggested-revision recipe (never widens scope)
- [x] `novelty-heuristics` skill — per-element overlap analysis + `verdict_hint ∈ {novel, narrow, redraft, withdraw}` **advisory only**; 7 rule_ids; ethics framing shipped verbatim in description AND body
- [x] `/scholar:patent-claims` upgraded to drive parser + chart-builder after writing `claims.md` (structured form is canonical, prose is for humans)
- [x] `/scholar:patent-review` upgraded with structured-audit pre-pass (parser + chart + heuristics); panel roles now consume structured findings instead of working from prose; novelty-critic must explicitly override heuristic verdicts when they disagree

**No MCP shipped.** All three skills use host-native `Read` / `Glob` / `Grep` / `Write` / `Bash:grep*` only. Optional MCP backends remain a future possibility (see v0.3 → v0.x deferred list) but are not on the v1.0 critical path.

## v0.3.deferred — optional MCP backends

`later (optional)`

- [ ] `scholar-search` → MCP for air-gapped CI runs, deterministic snapshots, or rate-limit-isolated arXiv / Semantic Scholar / OpenAlex querying
- [ ] `patent-search` → MCP for jurisdiction-pinned USPTO / EPO / Google Patents fetch with reproducible result sets
- [ ] `latex-build` → MCP that wraps `latexmk` with a structured error parser so hooks can react on typed failures rather than shell exit codes
- [ ] `code-intel` → MCP fronted by tree-sitter / language servers / **vector semantic index** (e.g. backed by zilliztech/claude-context) for repos too large to scan with `Glob` / `Grep`. This subsumes the dropped v0.5 "semantic code index" item.
- Rationale: users may want MCP backends for offline operation, deterministic CI fixtures, or a process boundary around heavy parsers — the skill contract is unchanged; MCP is one possible backend.

## v0.4 — Authoring quality

`done`

- [x] `latex-style-audit` skill — 28 rules covering captions, cross-refs, math, tables/figures, microtypography, common misuses
- [x] `bib-audit` skill — 20 rules covering required fields per entry type, year/venue/DOI/URL hygiene, cross-entry author drift, coverage against evidence.jsonl + manuscript
- [x] `xref-audit` skill — 14 rules covering label hygiene, broken refs, macro consistency, float order
- [x] `consistency-checker` agent — 9 rules covering term drift, number drift (`fail`), abbreviation order, symbol drift, voice/tense, claim-vs-result mismatch (`fail`), section-order, dataset-name normalisation
- [x] `/scholar:paper-check` upgraded from 5 audit blocks to 9 (Citation / LaTeX / Style / Bib quality / Cross-references / Figures & tables / Claim-evidence / Numbers / Consistency)
- [x] `consistency-checker` wired into `/scholar:paper-review` and `/scholar:patent-review` subagents

## v0.5 — Code understanding

`dropped`

The four items originally planned here turned out to be redundant after v0.2's skill migration:

- ~~Semantic code index (vector + symbol)~~ — moved to `v0.x.deferred` as an optional MCP backend for very large repos (e.g. backed by zilliztech/claude-context). Small-to-medium repos are served by `Glob` / `Grep` / `Read` driven through `skills/code-intel/SKILL.md`.
- ~~Repo-wiki generator~~ — `.evidraft/code/repo_summary.md` produced by `agents/codebase-analyst.md` already plays this role; there is no separate "wiki" deliverable.
- ~~Architecture-summary subagent~~ — `codebase-analyst` is already that subagent (since v0.1).
- ~~`method_to_code.md` auto-bootstrap~~ — `/scholar:paper-code-audit` already prompts the LLM to bootstrap this artefact end-to-end via the `code-intel` skill; no separate command needed.

Rationale: Claude Code, Codex CLI, and OpenCode all do general-purpose code understanding natively. The plugin's job is to *channel* that capability into evidence-grounded artefacts (`repo_summary.md`, `method_to_code.md`, `paper_code_audit.md`), which v0.1–v0.4 already cover. Anything left over is large-repo-specific and belongs under the optional MCP-backend track.

## v1.0 — Hardening and packaging

`later`

- [x] Versioned plugin manifest with migration tool — `manifest_version: "1.0.0"` added to `plugin.yaml`; `packages/core/schemas/plugin.schema.json` defines the top-level schema; `packages/core/src/migrate.py` ships the migration framework + `0.0.0 → 1.0.0` step + CLI; 5 pytest tests pass.
- [x] Adapter conformance test suite — `tests/test_adapter_conformance.py` (21 parametrised tests across 11 invariants: A file-count, B frontmatter-survival, C retention preamble, D MCP-reference ratchet, E required-skill (existence + rendering), F subagent-dispatch, G executable hooks, H per-agent model + effort, I skill-bundle propagation, J relative-link integrity (source), K relative-link integrity (rendered output, catches adapter path-flattening bugs); across claude-code / codex-cli / opencode). Full `pytest tests/` reports 52 passing.
- [x] Skill bundle pattern + propagation (Path A) — `packages/adapters/_shared/bundle.py` provides `copy_skill_bundle` + `bundle_dest_paths`; every adapter now treats each `skills/<id>/` as a directory bundle; conformance invariant I asserts every reference ships to every host. `_shared/loader.py` `_load_skill_dir` enforces one-skill-per-directory discovery so `references/*.md` are never misclassified as skills.
- [x] Progressive-disclosure refactor (Path B) — 12 skills + 1 command split into thin entries plus on-demand `references/*.md`: persistent context drops from 3245 → 1323 lines (**-59%**); 57 references propagated by Path A. Per-split metrics, the C-list rule-of-thumb, and the architectural decision log live in [`docs/optimization-status.md`](optimization-status.md).
- [x] Link-check CI invariant — conformance invariant J asserts every relative markdown link under `plugins/scholar-ip/` resolves to a real file; replaces the shell one-liner used during split review (flagged as environment-fragile). Strips fenced code blocks + inline code spans before parsing so backticked regex examples do not false-positive.
- [x] Codex Option A — cross-skill link rewriting. Codex flattens commands + skills under a single `skills/` dir with `scholar-` and `scholar-skill-` prefixes; the adapter now rewrites `[text](../skills/<X>/...)` to `[text](../scholar-skill-<X>/...)` in command bodies before writing. Rendered-output invariant K (counterpart to source-level J) gates regression by scanning the rendered tree directly. Caught 11 broken links in `scholar-deepresearch/SKILL.md` that source-level J could not see.
- [x] End-to-end fixtures — three examples now ship full audit / review fixtures:
  - `examples/deepresearch-small-obj-detection/` — `/scholar:brainstorming` + `/scholar:deepresearch` Stages 1–6 via real WebSearch / WebFetch (incl. OAN-hallucination audit trail).
  - `examples/cv-detection-paper/` — populated `/scholar:paper-check` 9-block audit: compile errors, style audit (28-rule), bib audit (20-rule), xref audit (14-rule), consistency audit (9-rule, incl. one `NUMBER_DRIFT (fail)` demonstrating the most important rule), final `paper_check_report.md` with documented hook-downgrade.
  - `examples/patent-disclosure/` — populated v0.3 structured-audit pre-pass: `claims_parsed.json` + `claim_chart-<ts>.json` (with no-support-override demonstration) + `novelty_audit-<ts>.findings.json` (per-claim `verdict_hint` advisory) + v0.3 6-role `patent_review_report.md`.
- ~~Web UI (read-only) for inspecting `.evidraft/`~~ **DROPPED.** `.evidraft/` is already renderable: GitHub renders the markdown + JSON natively; Obsidian / VSCode / any markdown previewer covers local inspection; PDF handoff to advisors / attorneys is one `pandoc` invocation. Building a Web UI introduces a frontend stack (framework / build pipeline / JS deps / hosting / cross-browser testing) with a cost-to-value ratio that does not pay off for a research-workflow plugin. The plugin's job is to *generate* evidence-grounded artefacts; *consuming* them is the host's job (Claude Code) or the user's IDE / GitHub / email-friendly PDF export.

---

## Non-goals (explicitly)

- We **do not** auto-publish, auto-submit to venues, or auto-file patents.
- We **do not** generate legal opinions. Patent review reports are **attorney-reviewable** drafts.
- We **do not** fabricate citations, experiment numbers, or code references. If a hook is bypassed, the plugin is misconfigured.
- We **do not** try to replicate every host's plugin format inside the plugin source — adapters do that.
