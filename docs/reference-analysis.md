# Reference Analysis

> The projects below shaped EviDraft's command set, agent roster, and data model. We borrow architecture and command design. We do **not** copy code unless the license permits and provenance is preserved. Every recommendation here is an *idea-level* reference, not a code import.

Format: each entry has **What stands out**, **What EviDraft adopts**, **What we skip (for now)**, **Risks**.

---

## 1. `trilogy-group/cc-skill-patent-disclosure`

Codebase-to-patent skill for Claude Code.

- **What stands out**
  - End-to-end flow: `/scholar:patent-disclosure` discovers possible inventions in the repo, drafts attorney-reviewable material, and ties claims back to code lines.
  - Multi-role QC: novelty / prior-art / claim-drafting reviewers.
  - Claim-to-code mapping is explicit, not implicit.
- **What EviDraft adopts**
  - `/scholar:patent-scout` and `/scholar:patent-disclosure` command structure.
  - `claim_chart.md` with `code support` column.
  - Multi-role review (`patent-engineer`, `claim-drafter`, `novelty-critic`).
- **What we skip**
  - Live USPTO calls — deferred to `patent-search-mcp`.
- **Risks**
  - License unknown at time of writing; verify before code reuse. Ideas only.

---

## 2. `RobThePCGuy/Claude-Patent-Creator`

Patent-focused MCP backend.

- **What stands out**
  - MCP-mediated retrieval of MPEP / 35 USC / 37 CFR.
  - Distinct review pipelines (claim review, specification review, formalities check).
  - Diagram-support hooks.
- **What EviDraft adopts**
  - Architectural split: retrieval as MCP, drafting as command.
  - Explicit `patent-claims` review and `patent-review` formalities pass.
- **What we skip**
  - MPEP / regulation retrieval — listed as future work.
- **Risks**
  - Jurisdiction-specific retrieval needs careful licensing of the source data.

---

## 3. `LigphiDonk/Oh-my--paper`

Cross-host research pipeline (Claude Code + Codex).

- **What stands out**
  - Stage commands `/omp:setup`, `/omp:survey`, `/omp:ideate`, `/omp:experiment`, `/omp:write`, `/omp:review`.
  - Designed from day one to run on more than one coding agent.
- **What EviDraft adopts**
  - The whole stage decomposition (renamed to `/scholar:paper-init`, `/scholar:paper-lit`, `/scholar:paper-idea`, `/scholar:paper-experiment`, `/scholar:paper-draft`, `/scholar:paper-check`).
  - Adapter mindset: same workflow lives across Claude Code, Codex CLI, OpenCode.
- **What we skip**
  - n/a; this is the closest spiritual ancestor.

---

## 4. `TobiasBlask/open-paper-machine`

Literature → LaTeX/PDF pipeline.

- **What stands out**
  - `search-papers` / `screen-papers` / `draft-section` / `export-latex` / `verify-citations` / `audit-paper`.
  - The paper-vs-code audit concept and claim/code/experiment consistency check.
- **What EviDraft adopts**
  - `/scholar:paper-code-audit` directly inspired by audit-paper.
  - Citation verification folded into `/scholar:paper-check`.
  - Stage of `draft-section` retained inside `/scholar:paper-draft` (outline → plan → section LaTeX).
- **What we skip**
  - Full PDF export pipeline — depends on `latex-build-mcp`.

---

## 5. `JeanDiable/academic-research-plugin`

Survey-focused academic plugin.

- **What stands out**
  - Survey writing as a first-class skill.
  - `paper_search.py` and `bibtex_utils.py` as concrete helpers.
- **What EviDraft adopts**
  - Survey writing folded into `/scholar:paper-review`.
  - Citation-assistant role → `evidence-auditor` agent.
- **What we skip**
  - We do not import its python helpers; `bib-manager-mcp` will reimplement only the interfaces we need.

---

## 6. `andrehuang/academic-writing-agents`

Multi-agent academic writing review.

- **What stands out**
  - A clean roster: consistency-checker, logic-reviewer, technical-reviewer, writing-reviewer, latex-layout-auditor, bibliography-auditor, research-analyst, brainstormer, paper-crawler, prose-polisher, section-drafter, latex-figure-specialist.
- **What EviDraft adopts**
  - Agent roster is the basis for our 9 agents: `literature-reviewer`, `codebase-analyst`, `experiment-analyst`, `novelty-critic`, `methodology-reviewer`, `latex-editor`, `patent-engineer`, `claim-drafter`, `evidence-auditor`.
  - "Multiple specialised reviewers > one generalist" pattern.
- **What we skip**
  - We collapse `prose-polisher` and `writing-reviewer` into `latex-editor` for MVP; they can split out later.

---

## 7. `xinyuliu-jeffrey/simple-auto-research-skill`

Disciplined research skill emphasising evidence.

- **What stands out**
  - Hard rule: claims must be supported by data in `experiments/`.
  - Claim-evidence matrix.
- **What EviDraft adopts**
  - `hooks/evidence-consistency.md` enforces this rule globally.
  - `evidence-auditor` agent + claim-evidence matrix output.
- **What we skip**
  - Nothing — this is one of the most directly applicable inspirations.

---

## 8. `PHY041/claude-skill-write-academic-report`

Research repo in → compiled report out.

- **What stands out**
  - Chapter-level subagents.
  - Cross-reference audit.
  - LaTeX compilation pass.
- **What EviDraft adopts**
  - Outline → section-plan → section-LaTeX pipeline.
  - Cross-reference audit folded into `/scholar:paper-check`.
- **What we skip**
  - Long-thesis style not in MVP scope; main target is conference / arXiv length.

---

## 9. `alirezarezvani/claude-skills`

Large skill library spanning many hosts.

- **What stands out**
  - Skill packaging and the platform-portability mindset.
  - Research / litreview / patent skills are already separated.
- **What EviDraft adopts**
  - The adapter pattern (Claude Code / Codex / Cursor / OpenCode rendered from a shared source).
  - Skill folder layout.
- **What we skip**
  - We do not yet generate Cursor or Aider variants — listed in roadmap.

---

## 10. `reporecall`, `zilliztech/claude-context`, "Understand Anything"

Codebase indexing and semantic search.

- **What stands out**
  - Semantic code search.
  - Repo wiki + architecture summary.
  - Method-to-code mapping.
- **What EviDraft adopts**
  - `code-intel` skill (formerly planned as `code-intel-mcp`; v0.2 lives as a skill that uses Glob/Grep/Read + optional `Bash:tree-sitter*`).
  - `codebase-analyst` agent and the `code/method_to_code.md` artefact.
- **What we skip**
  - Real vector index — stubbed in MVP, listed under v0.5.
- **Risks**
  - Vendor SDK licenses vary; we keep the MCP interface independent of any single implementation.

---

## Summary: what makes EviDraft different

| Capability | Best upstream | EviDraft's twist |
|---|---|---|
| Cross-agent workflow | Oh-my-paper | Adapter layer + single `plugin.yaml` source of truth |
| Patent disclosure from code | cc-skill-patent-disclosure | Bound to evidence store + multi-role review out of the box |
| Paper vs code audit | open-paper-machine | First-class command + 5-state verdict (CONFIRMED / PARTIAL / MISSING / MISMATCH / NOT_AUDITABLE) |
| Evidence discipline | simple-auto-research-skill | Promoted to a global hook, not an optional check |
| Multi-agent review | academic-writing-agents | Consolidated 9 agents covering both paper and patent |
| Code understanding | reporecall / claude-context | MCP interface decoupled from any one indexing impl |

---

## License posture

- All upstream references are *idea-level*. Re-implement, do not copy.
- If we ever vendor code, the file gets a `THIRD_PARTY/` provenance note and we preserve the upstream license. None vendored at v0.1.
