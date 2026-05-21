# scholar-ip-copilot · EviDraft

**Evidence-grounded academic and patent copilot for codebases, experiments, literature, LaTeX papers, and invention disclosures.**

`scholar-ip-copilot` (product name: **EviDraft**, plugin id: `scholar-ip`) is a cross-agent plugin library that turns an existing **code repository + experiment data + literature** into:

- a method-to-code map and a repo summary,
- a literature matrix, an evidence store, and a related-work draft,
- a LaTeX paper draft with claim-evidence traceability,
- an attorney-reviewable invention disclosure and a first set of draft claims,
- multi-role review reports for both paper and patent.

EviDraft is **not** "write me a paper" — it is a disciplined workflow that refuses to make strong claims without citable evidence and refuses to make code claims without file/line traceability.

---

## Why scholar-ip-copilot

Most existing research / writing agents start from a topic or a prompt. EviDraft starts from **what you have already built**:

```
codebase + experiments + literature + your invention notes
        │
        ▼   /scholar:paper-* and /scholar:patent-* commands
        │
        ▼
LaTeX paper draft   +   attorney-reviewable disclosure   +   review reports
```

Core design principles:

| Principle | What it means |
|---|---|
| **Evidence-grounded** | No literature claim without a `citation_key`; no number without a row in `experiments/`; no code claim without `file_path` + line range. |
| **Codebase-grounded** | Method, ablations, and claims are mapped back to source files, entry points, configs, and key functions. |
| **Human-in-the-loop** | Patent outputs are *attorney-reviewable*, not legal advice. Paper drafts are *human-reviewable*, not guaranteed publishable. |
| **Cross-agent compatible** | Core workflows live in a platform-neutral manifest. Claude Code / Codex CLI / OpenCode are *adapters*. |

---

## Supported agents

The plugin is authored once as a platform-neutral manifest (`plugin.yaml` + `commands/`, `agents/`, `skills/`, `hooks/`). Adapters then emit the format each host expects:

| Host | Status | Adapter path |
|---|---|---|
| Claude Code | MVP (first-class) | `packages/adapters/claude-code/` |
| Codex CLI | MVP (prompt/workflow files) | `packages/adapters/codex-cli/` |
| OpenCode | Planned (docs only) | `packages/adapters/opencode/` |
| Other coding agents | Future | follow `packages/core/schemas/command.schema.json` |

---

## What you get

### Meta entrypoint

`/scholar:using` — load the `using-scholar-ip-copilot` orientation skill. Type this any time to see the full command map, your current project stage, and what to run next. Mirrors `superpowers:using-superpowers`.

### Paper workflow — arXiv-first, venue template at submission time

EviDraft drafts manuscripts in a **neutral arXiv-style** template. The conversion to a specific venue (CVPR / NeurIPS / ICCV / ECCV / ICML / ICLR / EMNLP / ACL / AAAI / IEEE / ACM …) is a separate, late step driven by the `venue-formatting` skill and the `/scholar:paper-venue` command. This keeps the draft stable while you decide where to submit.

```
/scholar:paper-init          → scaffold .evidraft/ + manuscript/ (arXiv style) + project.yaml
/scholar:paper-lit           → literature matrix + references.bib + evidence.jsonl
/scholar:paper-review        → related-work / survey draft, every claim tied to evidence
/scholar:paper-idea          → novelty matrix, risk matrix, experiments-to-run
/scholar:paper-code-audit    → method_to_code.md + paper_code_audit.md (CONFIRMED / PARTIAL / MISSING / MISMATCH / NOT_AUDITABLE)
/scholar:paper-experiment    → result_analysis.md + LaTeX tables + figure suggestions
/scholar:paper-draft         → outline → section plan → manuscript/main.tex (arXiv style)
/scholar:paper-check         → citation, LaTeX, figure/table refs, claim-evidence, number-source audit
/scholar:paper-venue         → convert arXiv-style manuscript into a target venue's template
```

### Patent workflow — 技术交底书 (Technical Invention Disclosure) first

The **primary** patent deliverable is a **技术交底书** (Technical Invention Disclosure, TID) ready to hand off to a registered patent agent / attorney. Draft claims and the claim chart are **secondary** artefacts produced from the TID to help reviewers, **not** filing text.

```
/scholar:patent-init         → scaffold .evidraft/patent/ + invention_disclosure.md (TID) template
/scholar:patent-scout        → invention_candidates.md from code + docs
/scholar:patent-prior-art    → prior_art_map.md + claim_chart.md (skeleton)
/scholar:patent-disclosure   → 技术交底书 / Technical Invention Disclosure  ◀ primary deliverable
/scholar:patent-claims       → draft independent + dependent claims, with claim-chart traceability (advisory)
/scholar:patent-review       → multi-role review (engineer, drafter, novelty critic, technical reviewer, examiner)
```

### Shared / Phase 2 — clarify, deep-search, delegate, polish

```
/scholar:brainstorming       → requirement clarification (superpowers-style); writes .evidraft/scope/<date>-<slug>.md;
                                hard precondition (scope-required hook, block→warn|disabled in project.yaml) for
                                /scholar:paper-idea, /scholar:patent-scout, /scholar:paper-draft,
                                /scholar:patent-claims, /scholar:deepresearch, /scholar:polish
/scholar:deepresearch        → 6-stage heavyweight literature workflow (Frame → Retrieve → Screen → Cluster →
                                Critique → Synthesise); PRISMA-style screening log; multi-provider
                                (arxiv | semantic-scholar | openalex); breadth/depth knobs
/scholar:xreview             → delegate to another coding agent (Codex / Claude bare / OpenCode) for a second
                                opinion; output zone locked to .evidraft/reviews/; user-supplied API keys via env
/scholar:polish              → Williams-style humanize: cut AI-flavour, preserve numbers/citations/entities/hedges;
                                mandatory diff log under .evidraft/style/; NOT a detector-evasion tool
```

All outputs land in `.evidraft/` so the workspace stays inspectable and diffable.

---

## Progressive disclosure

Each `skills/<id>/SKILL.md` is a **thin entry**: load-before-every-call rules + a navigation map. On-demand details (rule taxonomies, output schemas, multi-step procedures, anti-patterns) live as siblings under `skills/<id>/references/*.md` and are only loaded when the agent actually needs them. Every reference file ships to every host through the adapter pipeline — the propagation is asserted by conformance invariant **I**, and every relative link is asserted by invariant **J**.

Current state, master branch:

| Splits | Source lines before | After (entries only) | Reduction | On-demand references shipped |
|---:|---:|---:|---:|---:|
| **12** | 3245 | **1323** | **-59%** | **57** |

What this means for a session:

- A typical `/scholar:*` invocation loads the **entry** SKILL.md (~80–130 lines) instead of the historical 230–377-line monolith.
- The on-demand reference is fetched only for the phase the agent is in — e.g. `deep-literature-review` runs six stage references but each stage agent only loads its own.
- Cross-host parity is enforced by the same render pipeline; if a reference ships under Claude Code's `skills/<id>/references/<f>.md`, it ships under Codex's `skills/scholar-skill-<id>/references/<f>.md` too.

Authoring details: [`docs/architecture.md`](docs/architecture.md) (authoring rule 4) and the living tracker [`docs/optimization-status.md`](docs/optimization-status.md) (per-split metrics + the C-list rule-of-thumb refined across 12 data points).

---

## Repository layout

```
scholar-ip-copilot/
├── docs/                         architecture, roadmap, reference analysis, data model, plugin format, legal & ethics
├── plugins/
│   └── scholar-ip/               platform-neutral plugin (commands, agents, skills, hooks, templates)
├── packages/
│   ├── core/                     JSON schemas + (future) python helpers
│   ├── adapters/                 claude-code / codex-cli / opencode adapters
│   └── mcp/                      (reserved, v0.3+) MCP backends — host-native skills cover v0.2
├── examples/                     cv-detection-paper, generic-paper, patent-disclosure
└── tests/                        fixtures + integration scaffolding
```

See [`docs/architecture.md`](docs/architecture.md) for the layered architecture and [`docs/data-model.md`](docs/data-model.md) for the on-disk format.

---

## Install

`scholar-ip-copilot` is a platform-neutral plugin source. Three host adapters render
it into the shape Claude Code, Codex CLI, and OpenCode each load. Everything is
local — no GitHub publishing or marketplace upload required.

> Retrieval and tooling use the host's built-in `WebSearch`, `WebFetch`, and
> `Bash` via skills under `plugins/scholar-ip/skills/`. No external MCP is
> required for v0.2. MCP backends are reserved for v0.3+ — see
> [`packages/mcp/README.md`](packages/mcp/README.md).

### Prerequisites

- Python 3.10+
- `make`, `bash`, `jq` (jq is required by `citation-guard.sh` and
  `scope-required.sh`; available on every standard dev box)
- One or more of: `claude` CLI · `codex` CLI · `opencode` CLI

### Quick install (works on all three hosts)

```bash
# 1. Clone and set up the venv
git clone https://github.com/zgdd12345/scholar-ip-copilot
cd scholar-ip-copilot
python -m venv .venv && source .venv/bin/activate
pip install -e .

# 2. Render every host adapter (parallel, ~0.5s)
make install
```

`make install` produces:

| Path | Purpose |
|---|---|
| `.claude/plugins/scholar-ip/` | Claude Code plugin (with `.claude-plugin/plugin.json` + `hooks/hooks.json` + 3 executable hooks) |
| `.codex/plugins/scholar/` | Codex plugin (with `.codex-plugin/plugin.json` + 46 skills) |
| `.opencode/{commands,agents,skills}/` | OpenCode auto-discovery layout |
| `.agents/skills/scholar-*` | Codex's actual skill-discovery directory (synced from `.codex/plugins/scholar/skills/`) |

The render outputs are `.gitignore`'d — re-run `make install` after pulling.

### Per-host registration

#### Claude Code

```bash
claude plugin marketplace add ./ --scope project
claude plugin install scholar@scholar-ip-copilot --scope project
```

Verify, then **restart any active Claude Code session**:

```bash
claude plugin list | grep scholar      # → ✔ enabled
claude plugin validate .claude/plugins/scholar-ip
```

In the new session you get:
- 21 `/scholar:*` slash commands (each with a `## Dispatch plan` if it declares subagents)
- 15 subagents listed in `/agents` (per-agent `model:` + `effort:` hints)
- 25 skills (`/skills` lists them and the model implicit-matches against the rich descriptions)
- 3 real hooks firing on session start / `Write|Edit` / gated `/scholar:*` prompts

#### Codex CLI

```bash
codex plugin marketplace add ./
```

Then add this once to `~/.codex/config.toml` (alongside any other `[plugins."..."]` blocks):

```toml
[plugins."scholar@scholar-ip-copilot"]
enabled = true
```

Restart Codex. `/skills` now lists **46** entries — 21 commands rendered as
`scholar-<id>` plus 25 source skills as `scholar-skill-<id>`. Skills are
auto-discovered from `<repo>/.agents/skills/` (walked from cwd up to the
worktree root). The marketplace + config block are forward-looking; until
Codex 0.131+ syncs local marketplaces the `.agents/skills/` path is what
actually loads.

#### OpenCode

Just stay inside the repo — OpenCode walks `cwd` for
`.opencode/{commands,agents,skills}/`. No registration needed:

```bash
opencode    # in the repo root → 21 commands + 15 agents + 25 skills
```

For **global** access (anywhere on the machine), copy or symlink:

```bash
mkdir -p ~/.config/opencode
cp -R .opencode/commands ~/.config/opencode/commands
cp -R .opencode/agents   ~/.config/opencode/agents
cp -R .opencode/skills   ~/.config/opencode/skills
```

Note: 7 source hooks are **not** rendered for OpenCode (hooks must be JS
modules under `.opencode/plugins/`). See
[`packages/adapters/opencode/README.md`](packages/adapters/opencode/README.md)
for the gap.

### Verify all hosts

```bash
make verify
```

This re-renders, runs the 21 conformance tests (across 12 invariants A–L) + 31 unit tests (52 total), and
prints which CLIs are detected. Use it as a smoke test after `git pull`
or before reporting a host-specific issue.

### Updating

```bash
git pull
make install   # re-renders + re-syncs codex skills
# Claude Code: restart to pick up the new marketplace cache
# Codex:        restart — new skills appear in /skills
# OpenCode:    next session auto-discovers
```

### Agentic install (CC / Codex reading this README)

If you ask a host's coding agent to "install this plugin" while pointing it
at this repo, the agent can follow this section verbatim. The exact command
order is: `make install` → host-specific registration → restart session.

See [`packages/adapters/claude_code/README.md`](packages/adapters/claude_code/README.md),
[`packages/adapters/codex_cli/README.md`](packages/adapters/codex_cli/README.md),
and [`packages/adapters/opencode/README.md`](packages/adapters/opencode/README.md)
for adapter internals + the platform-neutral schema in
[`docs/plugin-format.md`](docs/plugin-format.md).

---

## Legal & ethics

- Patent outputs are **attorney-reviewable disclosures**, never final legal opinions. See [`docs/legal-and-ethics.md`](docs/legal-and-ethics.md).
- Citation guard and evidence consistency hooks refuse to write strong claims without backing references.
- Sensitive files (`.env`, `secrets/`, `credentials.json`, …) are denied by default; user confirmation required.
- Any reuse of third-party project ideas is documented under [`docs/reference-analysis.md`](docs/reference-analysis.md) — we borrow architecture and command design, not code, unless license permits.

---

## Status

This is an **MVP skeleton** focused on workflow correctness over breadth. See [`docs/roadmap.md`](docs/roadmap.md) for the staged plan.

## License

MIT — see [`LICENSE`](LICENSE).
