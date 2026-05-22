# Architecture

`scholar-ip-copilot` is a layered system. The **core** is a set of platform-neutral schemas and workflow definitions. Each **adapter** translates that core into a specific coding-agent host's plugin format. Retrieval, parsing, and computation ship as **skills** that call the host's built-in `WebSearch` / `WebFetch` / `Bash`; **MCP servers** are reserved for v0.3+ as an optional offline / deterministic backend.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        User's project workspace                          │
│   codebase + experiments/ + manuscript/ + .evidraft/ (evidence store)    │
└────────────────────────────────────▲─────────────────────────────────────┘
                                     │ files / outputs
┌──────────────────────────────────────────────────────────────────────────┐
│  Plugin layer  (plugins/scholar-ip/)                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ commands │  │  agents  │  │  skills  │  │  hooks   │  │templates │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│       └──────┬──────┴─────────────┴─────────────┴─────────────┘          │
│              │  authored against core schemas                            │
└──────────────┼───────────────────────────────────────────────────────────┘
               │
┌──────────────▼───────────────────────────────────────────────────────────┐
│  Core layer  (packages/core/)                                            │
│  - JSON schemas: project / evidence / paper / patent / command           │
│  - (planned) python helpers for evidence I/O                             │
└──────────────┬───────────────────────────────────────────────────────────┘
               │
   ┌───────────┴──────────────┬────────────────────┬───────────────────┐
   ▼                          ▼                    ▼                   ▼
┌────────────────┐   ┌──────────────────┐   ┌───────────────┐   ┌───────────┐
│ Claude Code    │   │ Codex CLI        │   │ OpenCode      │   │  Future   │
│ adapter        │   │ adapter          │   │ adapter       │   │  hosts    │
│ (.claude/...)  │   │ (.codex/prompts/ │   │ (.opencode/   │   │           │
│                │   │  + .agents/      │   │  commands/    │   │           │
│                │   │  skills/)        │   │  agents/      │   │           │
│                │   │                  │   │  skills/)     │   │           │
└────────────────┘   └──────────────────┘   └───────────────┘   └───────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  (optional, v0.3+) MCP backends — alt impls of skills above              │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Core layer (`packages/core/`)

The contract of the system. Anything authored downstream must conform.

### Schemas

| Schema | Purpose |
|---|---|
| `plugin.schema.json` | top-level `plugin.yaml` — id / manifest_version / adapters / safety policy |
| `project.schema.json` | `.evidraft/project.yaml` — project type, status, artefact paths, evidence rules, scope/style/reviewers/lit_deep |
| `evidence.schema.json` | each line of `.evidraft/evidence/evidence.jsonl` |
| `paper.schema.json` | manuscript metadata (sections, target venue, authors) |
| `patent.schema.json` | invention disclosure + claim chart metadata |
| `command.schema.json` | the platform-neutral command/agent/skill/hook definition consumed by adapters |

### Why a `command.schema.json`

Every adapter (Claude Code, Codex CLI, OpenCode) wants its own file format. Instead of writing commands three times we author them **once** in a structure that the adapter renders:

```yaml
id: paper-init
title: "Initialize an EviDraft paper project"
kind: command            # command | agent | skill | hook
inputs:                  # what the user/host can pass in
  - name: project_type
    type: enum[paper, patent, mixed]
    optional: true
outputs:                  # what lands on disk
  - path: ".evidraft/project.yaml"
  - path: "manuscript/"
allowed_tools: [Read, Write, Edit, Bash:git*, Glob, Grep]
forbidden_tools: [Bash:rm -rf*]
references: [evidence-rules, sensitive-file-guard]
prompt: |
  ... agent instructions ...
```

Adapters read this and emit `.md` / `.toml` / `.json` files for their host.

---

## 2. Plugin layer (`plugins/scholar-ip/`)

The user-facing surface. Files are authored to be readable both by humans and by an adapter renderer.

| Folder | Contents |
|---|---|
| `commands/` | 21 files: `/scholar:using`, `/scholar:paper-*`, `/scholar:patent-*` — agent instructions, one per slash command |
| `agents/` | 15 specialist subagents (literature-reviewer, codebase-analyst, novelty-critic, brainstormer, consistency-checker, deep-research-orchestrator, paper-critic, prose-polisher, screener, …) |
| `skills/` | 25 reusable how-tos that any command/agent can pull in (literature-review, evidence-check, latex-writing, …) |
| `hooks/` | 7 guardrail specs (citation-guard, evidence-consistency, external-write-zone, humanize-evidence-preserve, latex-compile, scope-required, sensitive-file-guard) plus 3 executable `.sh` scripts (citation-guard, scope-required, session-start) and the `_lib.sh` helper |
| `templates/` | `paper-project/` and `patent-project/` — scaffolded on `/scholar:paper-init` and `/scholar:patent-init` |

Authoring rules:

1. Every command file is self-contained: a host (CC, Codex) can hand it to an LLM as a single prompt and the workflow runs.
2. Every command references its **inputs / outputs / allowed_tools / hooks**.
3. Strong-claim verbs (SOTA, first, significant, outperform) are forbidden unless a citation/evidence id is supplied — see `hooks/citation-guard.md`.
4. Skills follow a **bundle pattern**: each `skills/<id>/` directory is treated as a unit. `SKILL.md` is the entry; sibling files (`references/*.md`, `assets/*`, `scripts/*`) propagate to every rendered host output via `packages/adapters/_shared/bundle.py`. The heavy-weight `skills/deep-literature-review/` skill uses this to host 12 on-demand `references/` files (one per pipeline stage + 6 cross-cutting) so the agent's working context loads only the stage it is running.

---

## 3. Adapter layer (`packages/adapters/`)

Adapters are small generators. Each one:

1. reads `plugins/scholar-ip/`,
2. validates against `packages/core/schemas/command.schema.json`,
3. writes a host-specific tree.

| Adapter | Output |
|---|---|
| `claude_code/` | `<dest>/commands/*.md`, `<dest>/agents/*.md`, `<dest>/skills/*/SKILL.md`, plus Claude Code `hooks` declared in plugin.json (3 executable hooks ship: citation-guard, scope-required, session-start). |
| `codex_cli/` | Codex prompt/workflow files under `.codex/prompts/` + `.codex/plugins/`, plus a sync of skill bundles into `.agents/skills/scholar-skill-<id>/` (Codex's actual skill-discovery directory). Subagents Codex cannot represent are inlined into the parent prompt; cross-skill links into `references/` are rewritten by `_command_skill_body` (invariant K). |
| `opencode/` | `.opencode/commands/*.md`, `.opencode/agents/*.md`, `.opencode/skills/<id>/...` with bundle propagation. Hooks are **not** rendered — they would need to be JS modules under `.opencode/plugins/`. |

This keeps platform churn out of the plugin author's life.

---

## 4. MCP layer (`packages/mcp/`)

MCP servers are **reserved for v0.3+**; v0.1 / v0.2 ship retrieval and tooling as skills that use the host's built-in `WebSearch`, `WebFetch`, and `Bash`. The `packages/mcp/` directory holds only a README documenting the migration and how to opt back in to an MCP backend later.

### Skill replacement (former MCP stub → v0.2 skill)

| Former MCP stub | Replacement skill (v0.2, host-native) |
|---|---|
| `scholar-search-mcp` | `plugins/scholar-ip/skills/scholar-search/` |
| `bib-manager-mcp` | `plugins/scholar-ip/skills/bib-manager/` |
| `latex-build-mcp` | `plugins/scholar-ip/skills/latex-build/` |
| `code-intel-mcp` | `plugins/scholar-ip/skills/code-intel/` |
| `experiment-mcp` | `plugins/scholar-ip/skills/experiment-analysis/` (already existed) |
| `patent-search-mcp` | `plugins/scholar-ip/skills/patent-search/` |
| `external-agent-mcp` | `plugins/scholar-ip/skills/external-agent-bridge/` (already existed) |

Each replacement skill is the **contract**. A v0.3+ MCP server, if added, is one possible backend that satisfies that contract — used when offline operation, deterministic CI, or rate-limit isolation matters.

---

## 5. Evidence store (`.evidraft/`)

The single source of truth for downstream drafts. Layout:

```
.evidraft/
├── project.yaml                       project type, status, artefact paths, rules
├── evidence/
│   └── evidence.jsonl                 one record per literature / experiment / code / patent / note claim
├── literature/
│   ├── references.bib                 canonical BibTeX
│   └── matrix.md                      paper × method × dataset × result × gap matrix
├── ideas/
│   ├── novelty_matrix.md
│   ├── risk_matrix.md
│   └── experiment_to_validate.md
├── code/
│   ├── repo_summary.md
│   ├── method_to_code.md
│   └── paper_code_audit.md
├── experiments/
│   ├── result_analysis.md
│   └── tables/                        LaTeX tables ready to \input
└── patent/                            (only when project_type ∈ patent / mixed)
    ├── invention_disclosure.md
    ├── invention_candidates.md
    ├── prior_art_map.md
    ├── claim_chart.md
    ├── claims.md
    └── patent_review_report.md
```

Every record in `evidence/evidence.jsonl` carries:

```json
{
  "id": "ev_0001",
  "type": "paper|experiment|code|patent|note",
  "source_kind": "paper|blog|engineering_report|docs|tutorial|spec",
  "source": "...",
  "claim": "...",
  "support": "...",
  "citation_key": "...",
  "file_path": "...",
  "line_range": "...",
  "confidence": "high|medium|low",
  "verified": true
}
```

`source_kind` is optional and defaults to `paper`. Non-paper kinds within `type=paper` (blog / engineering_report / docs / tutorial / spec) MUST carry a `file_path` pointing at a local `.evidraft/literature/snapshots/<sha1>.md` snapshot — live URL line numbers are not stable. The `snapshots/` tree is durable evidence backing (no TTL, no auto-delete); see [`data-model.md`](data-model.md) for the full schema and `plugins/scholar-ip/skills/scholar-search/SKILL.md` §Tier 2 for refresh semantics.

---

## 6. Workflows

Workflows are linear sequences of commands gated by hooks.

### Paper — arXiv-first

The default manuscript style is **arXiv neutral** (single-column or two-column with a vanilla `\documentclass{article}` preamble). Venue-specific conversion (CVPR, NeurIPS, ICCV, ECCV, ICML, ICLR, EMNLP, ACL, AAAI, IEEEtran, ACM …) is a deliberate late step driven by `skills/venue-formatting/` and `/scholar:paper-venue`. This keeps the writing loop decoupled from the publication target.

```
paper-init ─► paper-lit ─► paper-idea ─┐
                                       ▼
                       paper-code-audit ┐
                                        │
                       paper-experiment ┤
                                        ▼
                              paper-draft ─► paper-check ─► paper-venue (submission-time)
                                        ▲
                              paper-review (related work, parallel)
```

### Patent — 技术交底书 first

The primary deliverable is the **技术交底书 (Technical Invention Disclosure, TID)** in `.evidraft/patent/invention_disclosure.md`. Draft claims and claim chart are advisory artefacts to help an attorney, **not** filed text.

```
patent-init ─► patent-scout ─► patent-prior-art ─► patent-disclosure (TID, primary) ─► patent-claims (advisory) ─► patent-review
```

Both workflows can run side by side on the same project (project_type: `mixed`).

---

## 7. Safety / guardrails

Hooks enforce the principles in `README.md`. They live in `plugins/scholar-ip/hooks/` as authoritative markdown specs; adapters may also emit executable hook scripts.

| Hook | Trigger | Behaviour |
|---|---|---|
| `citation-guard` | writing related_work / intro / abstract / draft | Reject strong claim verbs (SOTA, novel, first, significant, outperform, state-of-the-art) without a `citation_key` or `evidence_id`. Executable `.sh` shipped to Claude Code. |
| `evidence-consistency` | writing paper / patent draft | Every literature claim must trace to `evidence.jsonl`; every number must trace to `experiments/`; every code claim must trace to `code/method_to_code.md`. Advisory spec. |
| `external-write-zone` | `/scholar:xreview` subagent writes | Lock external-agent output to `.evidraft/reviews/`; reject writes outside the zone. Advisory spec. |
| `humanize-evidence-preserve` | `/scholar:polish` rewrites | Block any hunk that touches a numeric literal, `\cite{}` key, `ev_NNNN` marker, registered named entity, or empirical hedging adverb. Advisory spec. |
| `latex-compile` | `.tex` modified | Run `latexmk` (or stubbed interface). Parse errors, suggest fixes. Advisory spec. |
| `scope-required` | gated `/scholar:*` invocations | Refuse `/scholar:paper-idea`, `/scholar:patent-scout`, `/scholar:paper-draft`, `/scholar:patent-claims`, `/scholar:deepresearch`, `/scholar:polish` if no fresh `.evidraft/scope/<date>-<slug>.md` exists. Executable `.sh` shipped to Claude Code. |
| `sensitive-file-guard` | read of `.env`, `secrets/`, `credentials.json`, `*.pem`, `*.key` | Deny by default; require explicit user confirmation. Advisory spec. |

Hooks are advisory in MVP — they are described in the plugin and adapters wire them into host hook systems where available.

---

## 8. What MVP does and doesn't

See [`roadmap.md`](roadmap.md). Short version:

**MVP does**: workflow skeleton, prompts, schemas, adapters for Claude Code + Codex CLI + OpenCode, two templates, three examples, 12 conformance invariants (A–L) gating the renderer.

**MVP doesn't**: semantic code index, web UI, offline / deterministic backends. Online retrieval, PDF fetch, and LaTeX compilation are delivered through v0.2 host-native skills (`WebSearch` / `WebFetch` / `Bash:latexmk*`); MCP backends for those same skills are reserved for v0.3+.
