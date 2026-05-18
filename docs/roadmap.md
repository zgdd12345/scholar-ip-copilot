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

## v0.3 — Patent retrieval depth + optional MCP backends

`later`

- [ ] Claim parser (independent / dependent, element extraction)
- [ ] Automated claim-chart construction
- [ ] Novelty heuristics against prior art (must remain advisory, no legal conclusion)
- [ ] (optional) MCP backends for offline / deterministic use — concrete candidates:
  - `scholar-search` → MCP for air-gapped CI runs, deterministic snapshots, or rate-limit-isolated arXiv / Semantic Scholar / OpenAlex querying
  - `patent-search` → MCP for jurisdiction-pinned USPTO / EPO / Google Patents fetch with reproducible result sets
  - `latex-build` → MCP that wraps `latexmk` with a structured error parser so hooks can react on typed failures rather than shell exit codes
  - `code-intel` → MCP fronted by tree-sitter / language servers / semantic index for repos too large to scan with `Glob` / `Grep`
  - Rationale: a user might want MCP backends when they need offline operation, deterministic CI fixtures, or a process boundary around heavy parsers — the skill contract is unchanged

## v0.4 — Authoring quality

`done`

- [x] `latex-style-audit` skill — 28 rules covering captions, cross-refs, math, tables/figures, microtypography, common misuses
- [x] `bib-audit` skill — 20 rules covering required fields per entry type, year/venue/DOI/URL hygiene, cross-entry author drift, coverage against evidence.jsonl + manuscript
- [x] `xref-audit` skill — 14 rules covering label hygiene, broken refs, macro consistency, float order
- [x] `consistency-checker` agent — 9 rules covering term drift, number drift (`fail`), abbreviation order, symbol drift, voice/tense, claim-vs-result mismatch (`fail`), section-order, dataset-name normalisation
- [x] `/scholar:paper-check` upgraded from 5 audit blocks to 9 (Citation / LaTeX / Style / Bib quality / Cross-references / Figures & tables / Claim-evidence / Numbers / Consistency)
- [x] `consistency-checker` wired into `/scholar:paper-review` and `/scholar:patent-review` subagents

## v0.5 — Code understanding

`later`

- [ ] Semantic code index (vector + symbol)
- [ ] Repo-wiki generator
- [ ] Architecture-summary subagent integrated with the `code-intel` skill (and its optional v0.3+ MCP backend)
- [ ] `method_to_code.md` auto-bootstrap from method description

## v1.0 — Hardening and packaging

`later`

- [ ] Versioned plugin manifest with migration tool
- [ ] Adapter conformance test suite (Claude Code, Codex, OpenCode)
- [ ] End-to-end fixtures: synthetic repo → manuscript pdf → disclosure md
- [ ] Web UI (read-only) for inspecting `.evidraft/`

---

## Non-goals (explicitly)

- We **do not** auto-publish, auto-submit to venues, or auto-file patents.
- We **do not** generate legal opinions. Patent review reports are **attorney-reviewable** drafts.
- We **do not** fabricate citations, experiment numbers, or code references. If a hook is bypassed, the plugin is misconfigured.
- We **do not** try to replicate every host's plugin format inside the plugin source — adapters do that.
