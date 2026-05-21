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

**Test totals after Path A**: 49 passing across 5 test files; conformance suite = 18 parametrised tests across 9 invariants (A through I). After B2 below: 19 tests across 10 invariants (A through J).

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

## 🚧 IN FLIGHT

(nothing currently in flight)

---

## ⏳ PLANNED — by priority

### High priority

| Item | Effort | Notes |
|---|---|---|
| **A1. Dogfood `/scholar:deepresearch`** | User-driven, ~30 min | Has not yet been run end-to-end on the refactored skill. Without this we don't have runtime evidence that 12-file `references/` actually works for the agent during a real 6-stage run. *Path B Task 5 verified file propagation; this verifies runtime behaviour.* |
| **A2. Dogfood other refactored skills** | Spot-check, ~10 min each | `/scholar:patent-prior-art` (touches claim-chart-builder + claim-parser + novelty-heuristics) and `/scholar:paper-lit` (touches scholar-search) are the highest-value targets. |

### Medium priority

| Item | Effort | Notes |
|---|---|---|
| **C. Remaining mid-size skills** | ~30-60 min each | All currently 230-267 lines — under Anthropic's recommended <300-line ceiling but still candidates if they have clear sub-section structure. ROI declining vs. the original ≥290-line splits. Listed below: see "C-list inventory". |
| **D2. Top-level README "Progressive disclosure" section** | ~15 min | Explains the pattern to GitHub visitors; currently README mentions deepresearch only by name. |

### Low priority / speculative

| Item | Effort | Notes |
|---|---|---|
| **B3. Codex Option A — intra-bundle link rewriting** | ~30 lines Python + 1 test | Defaulted to Option B (convention: no cross-skill links inside `references/*.md`). Revisit only if an author actually wants to link cross-skill from inside a reference. |
| **D1. OpenCode 1.3.0 → 1.15.5 upgrade** | User-driven | The spike found 1.3.0 ignored `config.skills.paths` and our source frontmatter shape. A newer OpenCode *might* fix one or both. Until verified empirically on the newer release, do not rely on it. |
| **D3. "Authoring a new skill" guide** | ~50 lines docs | The bundle pattern is now in place but undocumented in a user-facing how-to. Write when external contributors arrive. |
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
| Codex intra-bundle link rewriting (Option A) | Convention (Option B): no cross-skill links from inside `references/*.md`. Cross-skill linkage stays at SKILL.md level where Codex's `scholar-skill-<id>` prefix is consistent. |
| `_dry_run_paths` includes only Path A bundle siblings, not future runtime artefacts | Bundle propagation is the only render-time side effect today. Add to `_dry_run_paths` if/when a new side effect appears. |

---

## Decision log (architectural)

Important choices made along the way, with one-line "why":

- **Path D RED ⇒ Path A.** Source frontmatter incompatibility AND `config.skills.paths` being unused on 1.3.0 each independently kill the alternative; pipeline change is the surviving option.
- **Skills are bundles, commands are not.** Skills are reusable units with multi-faceted content; commands are thin executable contracts that should point at skills. Asymmetry is deliberate.
- **One-skill-per-directory discovery (not `rglob`).** Eliminates the misclassification class where `references/foo.md` got loaded as a separate skill.
- **`_shared/bundle.py` extracted at 3 byte-identical copies.** YAGNI at 1-2; do it the moment the third copy lands. Extraction confirmed via AST diff before the refactor commit.
- **Codex link policy: Option B (no rewriting).** Convention is enforceable by code review; auto-rewriting adds adapter-specific code paths we can avoid.
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
