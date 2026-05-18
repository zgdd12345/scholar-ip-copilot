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
- [x] MCP stubs with documented interfaces for 6 servers
- [x] Examples: `cv-detection-paper/`, `generic-paper/`, `patent-disclosure/`
- [x] Reference analysis of 10 upstream projects

## v0.2 — Real retrieval and parsing

`next`

- [ ] `scholar-search-mcp`: arXiv + Semantic Scholar minimal client
- [ ] `bib-manager-mcp`: real BibTeX dedupe / normalize using `bibtexparser`
- [ ] `latex-build-mcp`: `latexmk` wrapper + structured error parser
- [ ] `code-intel-mcp`: `summarize_repo` via tree-sitter / language servers; entrypoint detection
- [ ] `experiment-mcp`: csv/jsonl loader + numeric-claim source check
- [ ] PDF text extraction (`pypdfium2` or `pymupdf`) behind the scholar-search MCP

## v0.3 — Patent retrieval and prior-art automation

`later`

- [ ] `patent-search-mcp`: USPTO / Google Patents / EPO connectors
- [ ] Claim parser (independent / dependent, element extraction)
- [ ] Automated claim-chart construction
- [ ] Novelty heuristics against prior art (must remain advisory, no legal conclusion)

## v0.4 — Authoring quality

`later`

- [ ] LaTeX style auditor (figure captions, table notation, math consistency)
- [ ] Bibliography auditor (uncited entries, missing entries, malformed keys)
- [ ] Cross-reference auditor (`\ref`, `\eqref`, `\cite` round-trip)
- [ ] `prose-polisher` and `consistency-checker` reviewers (multi-pass)

## v0.5 — Code understanding

`later`

- [ ] Semantic code index (vector + symbol)
- [ ] Repo-wiki generator
- [ ] Architecture-summary subagent integrated with `code-intel-mcp`
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
