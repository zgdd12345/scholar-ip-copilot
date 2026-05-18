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

## Install / use (MVP draft)

> Retrieval and tooling use the host's built-in `WebSearch`, `WebFetch`, and `Bash` via skills under `plugins/scholar-ip/skills/`. No external MCP is required for v0.2. MCP backends are reserved for v0.3+ as an optional offline / deterministic alternative — see [`packages/mcp/README.md`](packages/mcp/README.md).

### Claude Code

```bash
# clone
git clone https://github.com/<you>/scholar-ip-copilot.git
cd scholar-ip-copilot

# generate Claude-Code-flavored plugin into your project
python -m packages.adapters.claude_code.generate \
    --plugin plugins/scholar-ip \
    --out ~/your-project/.claude/plugins/scholar-ip
```

Then from inside `~/your-project`:

```
/scholar:paper-init
/scholar:paper-code-audit
/scholar:paper-experiment
/scholar:paper-draft
/scholar:paper-check
```

### Codex CLI

```bash
python -m packages.adapters.codex_cli.generate \
    --plugin plugins/scholar-ip \
    --out ~/your-project/.codex/prompts/scholar-ip
```

See [`packages/adapters/claude-code/README.md`](packages/adapters/claude-code/README.md) and [`packages/adapters/codex-cli/README.md`](packages/adapters/codex-cli/README.md) for full instructions and the platform-neutral schema in [`docs/plugin-format.md`](docs/plugin-format.md).

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
