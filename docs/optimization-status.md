# Development & Optimization Status

Living record of the progressive-disclosure refactor work stream and the infrastructure that made it possible. Each item is marked **✅ DONE**, **🚧 IN FLIGHT**, **⏳ PLANNED**, or **❄️ DEFERRED / OUT OF SCOPE**. Pointers to the actual commits / files are inline so future maintainers can trace why each piece exists.

## Overview

The work organised under "progressive disclosure" has four threads:

1. **Spike** — empirically rule out runtime path-registration as an alternative to render-time content propagation (RED, archived).
2. **Path A** — extend the render pipeline so each skill is treated as a directory bundle and sibling files (`references/`, `assets/`, `scripts/`) propagate to every host output.
3. **Path B** — use Path A to split monolithic SKILL.md / command files into thin entries plus on-demand `references/`. Repeated across 7 files.
4. **Documentation** — keep `docs/` and adapter READMEs in sync with the new pattern.

Outcome metric (persistent context drop across the twelve splits):

| Source files refactored | Before | After | Reduction |
|---|---:|---:|---:|
| `commands/deepresearch.md` + 11 SKILL.md files | 3245 | 1323 | **-59%** |

Plus 57+ on-demand `references/*.md` files that ship to every host via bundle propagation.

---

## ✅ DONE — Path A (bundle-propagation infrastructure)

| Piece | Commits | Notes |
|---|---|---|
| `bundle_dir: Path \| None` field on `FrontmatterDoc` | `3e4bb4e` | Skills only — `None` for commands / agents / hooks. |
| `_load_skill_dir(skills_dir)` in `_shared/loader.py` | `3e4bb4e` | One-skill-per-`<id>/SKILL.md` discovery; refuses to treat `references/*.md` as additional skills. |
| `_shared/bundle.py` — `copy_skill_bundle()` | `6d5f7ca` (extracted) | Was duplicated byte-identical in three adapters; AST-confirmed identity before extraction. |
| `_shared/bundle.py` — `bundle_dest_paths()` | `5305875` | Pure enumeration for `--dry-run`; shares `_bundle_files()` iterator with the copier. |
| Adapter wiring (claude_code, codex_cli, opencode) | `eb8b4d0` (opencode) → `d401617` (claude_code) → `181cc3f` (codex_cli) → `6d5f7ca` (extraction) → `5305875` (dry-run symmetry) | Each adapter calls `copy_skill_bundle` after writing `SKILL.md`; `_dry_run_paths` calls `bundle_dest_paths` so `--dry-run` mirrors `render()` exactly. |
| Conformance invariant I — `test_invariant_i_bundle_resources_propagated` | `2009c04`, `38f5a5f` (F→I rename) | Asserts every source skill with a non-`SKILL.md` sibling propagates to claude_code + codex_cli rendered output. |
| Conformance dry-run symmetry tests | `5305875` | Three tests, one per adapter: `set(dry_run_paths) == set(render(...))`. |
| `_shared/README.md` documenting loader + bundle contracts | `b40572f` | New file; covers symlink trust model and `shutil.copyfile` permission caveat. |

**Test totals after Path A**: 49 passing across 5 test files; conformance suite = 18 parametrised tests across 9 invariants (A through I). After B2 below: 19 tests across 10 invariants (A through J). After B3 below: 21 tests across 11 invariants (A through K); 52 passing. After the 2026-05-21 audit pass (invariant L + 5 YAML doc-ref fixes + README/tests-README drift cleanup): **22 tests across 12 invariants (A through L); full `pytest tests/` reports 53 passing**.

---

## ✅ DONE — Path B (content splits)

8 source files refactored to thin entry + `references/` bundle:

| # | File | Before | After | Δ | Commit | References created |
|---|---|---:|---:|---:|---|---:|
| 1 | `commands/deepresearch.md` | 313 | **102** | -67% | `c306592` | (12 in skill, below) |
| 2 | `skills/deep-literature-review/SKILL.md` | 233 | **98** | -58% | `50152f7` | 12 (6 stage + 6 aux) — `9f968a4`, `e29c267` |
| 3 | `commands/xreview.md` | 241 | **210** | -13%* | `760edea` | 0 (dedup vs. external-agent-bridge spec home) |
| 4 | `skills/claim-chart-builder/SKILL.md` | 377 | **115** | -70% | `0abc9ca` | 7 (5 procedure + schemas + anti-patterns) |
| 5 | `skills/novelty-heuristics/SKILL.md` | 290 | **110** | -62% | `f487f98` | 4 (analysis-procedure + rule-taxonomy + output-schema + anti-patterns) |
| 6 | `skills/claim-parser/SKILL.md` | 278 | **87** | -69% | `3e3229f` | 4 (procedure + warning-taxonomy + schema + anti-patterns) |
| 7 | `skills/scholar-search/SKILL.md` | 271 | **127** | -53%† | `4f14079` | 3 (provider-matrix + procedure + anti-patterns) |
| 8 | `skills/brainstorming/SKILL.md` | 267 | **83** | -69% | `7bc2929` | 6 (question-schemas + carlini-and-approaches + verdict-matrix + scope-file-template + staleness-rule + anti-patterns) |
| 9 | `skills/latex-style-audit/SKILL.md` | 263 | **93** | -65% | `a8837b8` | 4 (rule-taxonomy + output-schemas + procedure + anti-patterns) |
| 10 | `skills/patent-search/SKILL.md` | 248 | **115** | -54% | `dcc85a6` | 3 (provider-matrix + procedure + anti-patterns) — matches scholar-search shape |
| 11 | `skills/xref-audit/SKILL.md` | 232 | **88** | -62% | `0447eb6` | 4 (rule-taxonomy + output-schemas + procedure + anti-patterns) — matches latex-style-audit shape |
| 12 | `skills/humanize/SKILL.md` | 232 | **95** | -59% | _this commit_ | 6 (rewriting-rules + banned-phrases + ethics-and-refusal + model-routing + diff-log-spec + anti-patterns) — `commands/polish.md` "§3" anchors re-pointed to `references/ethics-and-refusal.md` |
| | **TOTAL** | **3245** | **1323** | **-59%** | | **57** new references files (plus 6 for `using-deep-research` — `eefef20`) |

\* xreview is a **dedup** against `skills/external-agent-bridge/SKILL.md` (the spec home it already had), not a true split — three byte-identical CLI invocations and ~30 lines of duplicate spec collapsed to pointers. Smaller % win but eliminates drift risk between command and skill.

† scholar-search keeps cache convention / field-completeness / shortcut resolution at SKILL.md level because they are "load before every call" rules, not on-demand details — that legitimately bounds how thin the entry can get.

---

## ✅ DONE — Spike archive

| Piece | Branch | Notes |
|---|---|---|
| `spike/opencode-js-plugin` | `origin/spike/opencode-js-plugin` (8 commits, RED) | OpenCode 1.3.0 runtime `config.skills.paths` is type-existent-but-unused; source SKILL.md frontmatter is incompatible. Both findings preserved in `docs/spike-results/2026-05-19-opencode-js-plugin.md` on master. Local branch deleted; remote retained as audit archive. |

This is **why** Path A exists — the cheaper alternative was empirically falsified before any pipeline code was written.

---

## ✅ DONE — Documentation alignment

| File | Change | Commit |
|---|---|---|
| `docs/plugin-format.md` | Per-skill folder section now describes bundle pattern (`references/`, `assets/`, `scripts/`); points at `_shared/bundle.py` + `_load_skill_dir`. | `b40572f` |
| `docs/architecture.md` | Added authoring rule #4 covering bundle pattern with deep-literature-review's 12-file references/ as canonical example. | `b40572f` |
| `docs/roadmap.md` | Conformance suite metric updated: 13 → 18 tests across 9 invariants. | `b40572f` |
| `packages/adapters/README.md` | Codex + OpenCode statuses from "planned / lint-only" → first-class; output paths corrected; `_shared/bundle.py` documented; `make render` added to quick-start. | `b40572f` |
| `packages/adapters/_shared/README.md` | **NEW**. Documents loader.py + bundle.py contracts, trust / permission model, where conformance tests live. | `b40572f` |
| `docs/superpowers/plans/2026-05-19-*.md` (3 files) | Plans for spike + Path A + Path B preserved as institutional record. | `65446d1`, `27f14ab`, `fe87cba` |
| `docs/spike-results/2026-05-19-*.md` | Spike findings + RED verdict on master. | `65446d1` |

---

## ✅ DONE — B2 (link-check CI invariant)

Hardened the Path-B-split shell one-liner (flagged in review as
environment-fragile) into a stable pytest invariant.

| Piece | Notes |
|---|---|
| Conformance invariant J — `test_invariant_j_relative_links_resolve` | Walks every `*.md` under `plugins/scholar-ip/` and asserts every relative `[text](path)` resolves to a file on disk. Strips fenced code blocks + inline code spans first so backticked regex examples (e.g. the `]([^`']+\.sty)` snippet in `latex-build/SKILL.md`) do not false-positive. Out of scope: `http(s)://`, `mailto:`, `ftp://`, `data:`, and anchor-only `#section` links. |
| Verification | Injected `[missing.md](references/this-file-does-not-exist.md)` into `scholar-search/SKILL.md`, confirmed test failed with file + target + resolved-path message, reverted. Suite green on master. |

---

## ✅ DONE — D3 ("Authoring a new skill" how-to)

New file [`docs/authoring-a-skill.md`](authoring-a-skill.md) (129 lines). Hands-on walkthrough for contributors adding a skill: directory layout, SKILL.md body conventions, the references/ split decision (with the rule-of-thumb codified from twelve splits), conformance-suite registration, verification commands, and a "common pitfalls" section listing every real-world authoring bug we hit during the Path B refactor + the two audit rounds (slash-command syntax in paths, off-by-one `..` chains, code-span false positives, stale anchor refs, YAML doc: ref drift). Walked example points at `deep-literature-review`'s 12-file bundle as the canonical heavy case.

Cross-references the existing reference docs (`plugin-format.md`, `architecture.md`, `optimization-status.md`, `tests/README.md`) rather than duplicating their material.

---

## ✅ DONE — D2 (README "Progressive disclosure" section)

Added a top-level section between "What you get" and "Repository layout" that explains the pattern to GitHub visitors: thin SKILL.md + on-demand `references/`, the current metric table (12 splits → -59%, 57 references), the per-session loading semantics, and pointers to the authoring rule (`docs/architecture.md` rule 4) and the living tracker (this file). Conformance invariants I + J are cited as the CI gates that keep the propagation honest.

---

## ✅ DONE — Second-round audit (2026-05-21)

A second-round audit pass found four classes of issue that the existing invariants A-K did not gate:

| Issue | Severity | Resolution |
|---|---|---|
| 5 broken YAML `references[].doc:` paths in source | minor — doc only, never rendered as runtime link, but stale pointers mislead the model | Fixed in source (2× `../../plugin.yaml` → `../plugin.yaml`; 1× `../../../docs/...` → `../../../../docs/...`; 2× `../scholar:X/SKILL.md` → `../X/SKILL.md`) |
| README skill/command counts off (24 vs 25 / 20 vs 21 / 44 vs 46) — drift accumulated since 2026-05 when `using-deep-research` + `xref-audit` landed without README updates | minor | Fixed 4 lines in `README.md` plus a stale test count claim ("17 conformance invariants + 39 unit tests" → "21 conformance tests + 31 unit tests = 52 total") |
| `tests/README.md` claimed pytest harness "planned for v0.2"; actual: full pytest suite + 12 conformance invariants exist | wrong reader-facing claim | Rewrote `tests/README.md` to document the current 5-file / 53-test layout with the per-invariant A-L table |
| New invariant L (`test_invariant_l_frontmatter_doc_refs_resolve`) gates the YAML-doc-ref class | structural — same shape as J but for YAML frontmatter pointers | Implemented; accepts files OR directories (templates/ refs are intentional dir pointers); failed against the broken state, passed after the 5 fixes |

The audit dispatched 4 parallel Explore subagents covering: `examples/` fixtures, YAML refs, docs-vs-reality drift, and hooks/agent cross-refs. The fourth subagent's "5 broken hooks" claim turned out to be a misread (the hooks are advisory-only spec files inlined into command bodies, not executable scripts) — disregarded.

---

## ✅ DONE — A1 + A2 + A3 smoke tests (3-host runtime bundle probes)

Three rounds of bounded automated runtime tests against the host CLIs, in non-interactive mode (`claude -p`, `codex exec`, `opencode run`). Each round picks a refactored skill (or set of skills), asks the agent to (a) enumerate the `references/` directory and (b) read one specific reference and report its first heading. Verifies the bundle pattern functions at the **runtime-agent level**, not just at the file-propagation level that invariant I already asserts.

**Coverage: all 11 refactored skills with their own `references/` bundles** tested across all 3 hosts (33 distinct runtime bundle-load operations, all passing). The 2 refactored commands (`commands/deepresearch.md`, `commands/xreview.md`) have no own bundle; their cross-skill links into other skills' references are verified by invariant K (static) and Codex's A1 traversal of `.agents/skills/scholar-skill-deep-literature-review/references/` (runtime).

### A1 — `deep-literature-review` (12 references)

| Host | Invocation | Result | Cost |
|---|---|---|---|
| Claude Code | `claude -p --max-budget-usd 1.00 --model claude-haiku-4-5-20251001 -p "<prompt>"` | ✅ 12 files listed alphabetically; `stage-1-frame.md` first heading `# Stage 1 — Frame` exact match | ~$0.05 |
| Codex CLI | `codex exec "<prompt>"` — agent traversed `.agents/skills/scholar-skill-deep-literature-review/references/` (the Codex flattened path) | ✅ same answer; 7,979 tokens | ~$0.02 |
| OpenCode | `opencode run "<prompt>"` — agent used Glob to find the bundle in the source tree; GLM-5.1 model | ✅ same answer | ~$0.01 |

### A2 — `claim-chart-builder` + `claim-parser` + `novelty-heuristics` + `scholar-search` (18 references combined)

| Host | claim-chart-builder | claim-parser | novelty-heuristics | scholar-search | Cost |
|---|:---:|:---:|:---:|:---:|---:|
| Claude Code | ✅ 7 files + `# Output schemas` | ✅ 4 files + `# Warning taxonomy` | ✅ 4 files + `# Rule taxonomy` | ✅ 3 files + `# Provider matrix — ...` | ~$0.05 |
| Codex CLI | ✅ same | ✅ same | ✅ same | ✅ same (26,811 tok) | ~$0.05 |
| OpenCode | ✅ same | ✅ same | ✅ same | ✅ same | ~$0.05 |

Notable: OpenCode used the **rendered** `.opencode/skills/<id>/references/` path for A2 (a different mechanism than A1, where it used source-tree Glob). This confirms `.opencode/skills/` discovery works when the skill is rendered there.

### A3 — `brainstorming` + `latex-style-audit` + `patent-search` + `xref-audit` + `humanize` + `using-deep-research` (24 references combined)

| Host | brainstorming (6) | latex-style-audit (4) | patent-search (3) | xref-audit (4) | humanize (6) | using-deep-research (1) | Cost |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---:|
| Claude Code | ✅ + `# Scope file template` | ✅ + `# Rule taxonomy — 28 LaTeX style rules` | ✅ + `# Provider matrix — URLs, routing, rate limits` | ✅ + `# Rule taxonomy — 14 cross-reference rules` | ✅ + `# Ethics block and refusal triggers` | ✅ + `# Example bundle reference` | ~$0.05 |
| Codex CLI | ✅ same | ✅ same | ✅ same | ✅ same | ✅ same | ✅ same (36,117 tok) | ~$0.05 |
| OpenCode | ✅ same | ✅ same | ✅ same | ✅ same | ✅ same | ✅ same | ~$0.05 |

24 files × 3 hosts = 72 distinct filename assertions, plus 18 heading reads — all pass.

### What the smoke tests prove

The bundle propagation that invariant I asserts at file-level also functions at the **runtime-agent level** on all three hosts. Cross-host parity isn't just structural; agents actually navigate to the references when prompted. 11 skills × 3 hosts = **33 distinct bundle-load operations**, all returning verifiable ground-truth, covering **all refactored skills with their own `references/` bundles**.

### What the smoke tests do NOT prove

- Full multi-stage workflow runs (`/scholar:deepresearch` 6-stage, `/scholar:patent-prior-art` 5-stage, etc.) — stage-by-stage reference loading, subagent dispatch correctness, the agent picking the *right* reference for each phase.
- Hooks firing correctly during a real session.

Those need real interactive sessions with target projects and cost $5-20+ per host per workflow. The smoke tests are the responsible automated version; full E2E remains user-driven if stronger evidence is needed.

### Combined cost + pollution

Three rounds × 3 hosts = 9 invocations. Total spend ~$0.35. **Zero `.evidraft/` writes** produced by any test (prompts were explicit "do not start any workflow, do not write any files"). Working tree clean after each round.

Test prompts and per-host transcripts archived in `/tmp/a1-dogfood/` for the current session; not checked into the repo.

---

## ✅ DONE — B3 (Codex Option A — cross-skill link rewriting)

Originally deferred under the assumption that cross-skill links only happen at SKILL.md ↔ SKILL.md level (where the consistent `scholar-skill-` prefix is enough). A post-Path-B audit of `make install` output found **11 broken links** in the rendered `.codex/plugins/scholar/skills/scholar-deepresearch/SKILL.md` — the deepresearch command body links into another skill's *references*, deeper than SKILL.md, which Option B doesn't cover.

| Piece | Notes |
|---|---|
| `packages/adapters/codex_cli/generate.py` rewrite | `_CROSS_SKILL_LINK_RE` matches `](../skills/<X>/` and rewrites to `](../scholar-skill-<X>/` as the last step of `_command_skill_body`. Covers the command body AND the inlined-subagent prose. ~10 LOC. |
| Conformance invariant K — `test_invariant_k_rendered_links_resolve` | Parametrised over `(claude_code, codex_cli)`; renders each adapter into a temp dir then runs the same link-resolution scan as J against the rendered tree. **Catches the regression class source-level J cannot see** — adapter path-flattening that breaks links in the rendered output even when they're sound at source level. Two test cases; CC passes naturally (its layout preserves source paths). |
| Verification | Re-rendered all three host trees via `make install`; broken-link count across `.codex/`, `.agents/skills/`, `.claude/`, `.opencode/skills/`, `.opencode/commands/` is now **0**. Spot-checked rendered `scholar-deepresearch/SKILL.md`: 12 links now read `../scholar-skill-deep-literature-review/references/...` (correctly resolving) instead of `../skills/deep-literature-review/references/...` (broken). |

The decision-log entry "Codex link policy: Option B (no rewriting)" is **superseded** — see the updated entry at the bottom of this document.

---

## 🚧 IN FLIGHT

(nothing currently in flight)

---

## ⏳ PLANNED — by priority

### High priority

| Item | Effort | Notes |
|---|---|---|
| **A1.full / A2.full. Full multi-stage E2E runs** | User-driven, ~30 min, $5-20 per host per workflow | *A1.smoke + A2.smoke are DONE — see "DONE — A1 + A2 smoke tests" section above.* This row tracks the stronger evidence: actually running `/scholar:deepresearch` (6-stage), `/scholar:patent-prior-art` (5-stage), and `/scholar:paper-lit` end-to-end against target projects to verify per-stage reference loading, subagent dispatch, stage progression, and hook firing. Each workflow is interactive (Stage 1 Frame asks for the user's scope before Stage 2 retrieves) and needs a real target project (manuscript/, candidates, etc.). |

### Medium priority

| Item | Effort | Notes |
|---|---|---|
_Medium-priority items are exhausted._ C-list ⏳ candidates are all split (rows 8-12 in the Path B table); D2 is the README section above.

### Low priority / speculative

| Item | Effort | Notes |
|---|---|---|
| **D1. OpenCode 1.3.0 → 1.15.5 upgrade** | User-driven | The spike found 1.3.0 ignored `config.skills.paths` and our source frontmatter shape. A newer OpenCode *might* fix one or both. Until verified empirically on the newer release, do not rely on it. |
| **D4. Codex rsync-only mode re-evaluation** | Larger; ~100 lines bash | superpowers ships to Codex via `rsync` to an external marketplace fork. Could simplify our codex_cli adapter if the gain outweighs the new bash-script complexity. Defer to when Codex output diverges meaningfully from claude_code / opencode in ways the current Python adapter handles poorly. |

### C-list inventory (large SKILL.md candidates, sorted by size as of master HEAD)

```
230 external-agent-bridge/SKILL.md   ❄️  KEEP — this is xreview's spec home; splitting it dilutes the dedup target
219 patent-claims/SKILL.md           ❄️  below threshold (≤ 220) — split if it grows
219 latex-writing/SKILL.md           ❄️
210 codebase-audit/SKILL.md          ❄️
210 bib-audit/SKILL.md               ❄️
```

Rule of thumb after twelve splits: **≥ 232 lines is split-worth (both 232L candidates — `xref-audit` and `humanize` — landed clean -59% / -62% reductions); 220-231 is judgement call (depends on whether the file has clean group structure to extract); ≤ 220 is fine as a single file** under Anthropic's recommended 300-line bound. The C-list ⏳-marked candidates are now exhausted; remaining ❄️ entries are deliberately preserved.

---

## ❄️ OUT OF SCOPE / explicit YAGNI

Decisions deliberately deferred or rejected, with the reasoning so they don't need to be re-litigated:

| Decision | Why deferred |
|---|---|
| Bundle support for commands / agents / hooks | The pattern is an Anthropic *skills* convention. Commands and agents don't have multi-step structured detail in practice — when they grow (`xreview`), the answer is to point at the relevant skill's bundle, not introduce a new bundle type. |
| Performance hardening of `copy_skill_bundle` | `shutil.copyfile` per file is O(file-count). No source skill has > 13 bundle siblings (venue-formatting/venues/); render time is dominated by other passes. Re-visit if bundles grow large enough to dominate. |
| `shutil.copy2` (preserve mtime + mode bits) | No source bundle currently ships executable scripts. When the first `+x` `scripts/*.sh` lands, switch to `copy2` then. One-line change. |
| Schemas as separate `.yaml` / `.json` files instead of MD-fenced blocks | Tools today don't consume schemas directly; LLM reads them from the markdown. Switch when a real `jsonschema validate` step appears. |
| Render output goes to an external marketplace repo (superpowers Codex pattern) | We render in-tree to `.codex/plugins/scholar/`; sufficient until a third-party marketplace requirement appears. |
| `_dry_run_paths` includes only Path A bundle siblings, not future runtime artefacts | Bundle propagation is the only render-time side effect today. Add to `_dry_run_paths` if/when a new side effect appears. |

---

## Decision log (architectural)

Important choices made along the way, with one-line "why":

- **Path D RED ⇒ Path A.** Source frontmatter incompatibility AND `config.skills.paths` being unused on 1.3.0 each independently kill the alternative; pipeline change is the surviving option.
- **Skills are bundles, commands are not.** Skills are reusable units with multi-faceted content; commands are thin executable contracts that should point at skills. Asymmetry is deliberate.
- **One-skill-per-directory discovery (not `rglob`).** Eliminates the misclassification class where `references/foo.md` got loaded as a separate skill.
- **`_shared/bundle.py` extracted at 3 byte-identical copies.** YAGNI at 1-2; do it the moment the third copy lands. Extraction confirmed via AST diff before the refactor commit.
- **Codex link policy: Option A (rewrite at render time).** ~~Originally Option B (convention: no rewriting).~~ A post-Path-B audit of rendered `.codex/` output found 11 broken links in `scholar-deepresearch/SKILL.md` — the deepresearch command body links into another skill's `references/` (deeper than SKILL.md), which Option B does not cover. The rewrite (`](../skills/<X>/` → `](../scholar-skill-<X>/`) is now done at render time in `_command_skill_body`; rendered-output invariant K (`test_invariant_k_rendered_links_resolve`) is the regression gate.
- **Symlinks: follow, copy targets, do not handle cycles.** Author-controlled in-tree content; security model is "we trust the source tree".
- **`shutil.copyfile` not `copy2`.** Permission preservation deferred until first executable lands in a bundle.
- **Codex invariant A tightened with `p.name == "SKILL.md"` filter.** Defensively guards against top-level non-SKILL.md siblings inflating the skill count. Dead filter on commands today; symmetry insurance.
- **`xreview` deduped against `external-agent-bridge` rather than split into its own references.** Spec home already existed; splitting would have created the duplication, not removed it.

---

## How to extend this document

When a new piece of work lands:
- If it implements one of the ⏳ items, move it to ✅ with a row in the relevant table.
- If it introduces a new design constraint, add a row to the decision log.
- If it changes the metric (persistent context, test count, references count), update the overview table.

Commit doc updates with the implementation work, not in a separate PR. Keeps the status truthful.
