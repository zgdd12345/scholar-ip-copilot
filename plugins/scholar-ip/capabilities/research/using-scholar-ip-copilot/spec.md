---
id: using-scholar-ip-copilot
title: "Using the scholar (EviDraft) plugin — full workflow orientation"
kind: skill
phase: shared
description: >
  Establishes how the scholar (EviDraft) plugin works, what every workflow:<id>
  does, the order to invoke them in, what gets written to .evidraft/, and which
  policies gate downstream work. Modelled on superpowers:using-superpowers.
triggers:
  - "session start"
  - "first interaction in an EviDraft project"
  - "user asks 'what can this plugin do?' or 'how do I use this?'"
  - "before any workflow:<id> is invoked for the first time in a session"
provides:
  - "complete command map (22 commands across meta / lite / paper / patent / phase-2)"
  - "workflow ordering for paper and patent phases"
  - "evidence-grounded discipline overview"
  - "gating-policy reference"
allowed_tools: [Read, Glob, Grep]
policies: []
references:
  - doc: ../../../README.md
  - doc: ../../../docs/architecture.md
  - doc: ../../../docs/data-model.md
  - doc: ../../../docs/legal-and-ethics.md
  - doc: ../../../plugin.yaml
---

# Using `scholar` (EviDraft)

<EXTREMELY-IMPORTANT>
If a `workflow:<id>` is relevant to the user's request, you MUST follow this
skill's workflow ordering and gating rules. Skipping `workflow:paper.init`
before drafting, or skipping `workflow:patent.disclosure` before claims, is a
discipline violation — preflight will refuse through the relevant policy.
</EXTREMELY-IMPORTANT>

You are working inside the **scholar** plugin (product name **EviDraft**). The plugin id is `scholar`; everything is invoked as `workflow:<id>`. Private resources are rooted beside `plugin.yaml`.

## What this plugin is for

Turn an existing **codebase + experiments + literature** into:

- a method-to-code map and a repo summary,
- a literature matrix, an evidence store, and a related-work draft,
- a LaTeX paper draft (arXiv-neutral style) with claim-evidence traceability,
- an attorney-reviewable **技术交底书 (Technical Invention Disclosure, TID)** and a first set of advisory draft claims,
- multi-role review reports for both paper and patent,
- (Phase 2) brainstorming, deep research, external-agent review, and Williams-style polish.

The plugin **refuses** to make strong claims without citable evidence, and refuses to make code claims without `file_path` + line range. That discipline is non-negotiable.

## The four design rules

| Rule | What it means |
|---|---|
| **Evidence-grounded** | No literature claim without a `citation_key`; no number without a row in `experiments/`; no code claim without `file_path:line_range`. |
| **Codebase-grounded** | Method, ablations, and claims are mapped back to source files, entry points, configs, and key functions. |
| **Human-in-the-loop** | Patent outputs are *attorney-reviewable*, not legal advice. Paper drafts are *human-reviewable*, not guaranteed publishable. |
| **Cross-agent compatible** | Same plugin renders into Claude Code, Codex CLI, OpenCode via adapters. |

## Where things live

```
<your-project>/
├── .evidraft/                      EviDraft workspace (single source of truth)
│   ├── project.yaml                project type, status, rules, scope, safety
│   ├── evidence/evidence.jsonl     every claim's provenance
│   ├── literature/                 BibTeX, matrix, related_work outline
│   ├── ideas/                      novelty / risk / experiments-to-run matrices
│   ├── code/                       repo summary, method↔code map, audit
│   ├── experiments/                result analysis + LaTeX tables
│   ├── patent/                     (patent / mixed projects) TID + claims + review
│   ├── scope/                      (Phase 2) brainstorming output
│   ├── style/                      (Phase 2) humanize diffs
│   └── reviews/                    (Phase 2) external-agent review outputs
└── manuscript/                     LaTeX project (arXiv-neutral)
    ├── main.tex
    └── sections/
```

## The full command map

### Meta (2)

| Command | What it does |
|---|---|
| `workflow:using.run` | This entry — orientation. Read-only. |
| `workflow:research.guide` | Orientation for the heavy 6-stage `workflow:research.deep` workflow: the prereqs (`paper-init` + `brainstorming`) that unblock `policy:scope`, the scope-stub fast-path, the breadth / depth budget knobs, the 6-stage artefact map, and the four failure modes. Read-only. |

### Lite (2) — personal literature research, no project required

| Command | What it does |
|---|---|
| `workflow:research.reading-list` | Single markdown reading list at `.evidraft/notes/<slug>-<date>.md`. No BibTeX, no `evidence.jsonl`, no audit chain. For personal reference reading. Every entry is `WebFetch`-verified; failed verifications are rejected, not silently downgraded. |
| `workflow:research.explain` | Full-text explanation of a single paper, with mandatory verified related methods and one academic Markdown note at `.evidraft/notes/paper-explanations/<paper-slug>.md`. No project scaffold required. |

### Paper (9) — arXiv-neutral draft, venue chosen at submission time

| Command | Purpose | Key output |
|---|---|---|
| `workflow:paper.init` | Scaffold `.evidraft/` + `manuscript/` (arXiv style) | `.evidraft/project.yaml`, `manuscript/main.tex` |
| `workflow:paper.lit` | Literature matrix + BibTeX + evidence | `.evidraft/literature/matrix.md`, `references.bib` |
| `workflow:paper.review` | Related-work / survey section | `manuscript/sections/related_work.tex` |
| `workflow:paper.idea` | Novelty / risk / experiments-to-run matrices | `.evidraft/ideas/*.md` |
| `workflow:paper.code-audit` | Method ↔ code mapping + claim audit (5-state verdict) | `.evidraft/code/method_to_code.md`, `paper_code_audit.md` |
| `workflow:paper.experiment` | Experiment analysis + LaTeX tables | `.evidraft/experiments/result_analysis.md` + `tables/*.tex` |
| `workflow:paper.draft` | Outline → section plan → full LaTeX | `manuscript/sections/*.tex` |
| `workflow:paper.check` | 9-block audit: Citation / LaTeX compile / Style (28 rules) / Bib quality (20 rules) / Cross-references (14 rules) / Figures & tables / Claim-evidence / Number-source / Consistency (semantic, 9 rules) | `.evidraft/manuscript/paper_check_report.md` + per-audit `*_audit-<ts>.findings.json` |
| `workflow:paper.venue` | Convert arXiv-style → CVPR/NeurIPS/ICCV/… template at submission | `submissions/<venue>/main.tex` |

### Patent (6) — 技术交底书 / TID first

| Command | Purpose | Key output |
|---|---|---|
| `workflow:patent.init` | Scaffold `.evidraft/patent/` + TID template | `.evidraft/patent/invention_disclosure.md` |
| `workflow:patent.scout` | Discover candidate inventions from code/docs | `.evidraft/patent/invention_candidates.md` |
| `workflow:patent.prior-art` | Prior-art map + claim-chart skeleton | `.evidraft/patent/prior_art_map.md`, `claim_chart.md` |
| `workflow:patent.disclosure` | **Primary deliverable**: 技术交底书 (TID), 13 bilingual sections | `.evidraft/patent/invention_disclosure.md` |
| `workflow:patent.claims` | Advisory: draft independent + dependent claims; parses to `claims_parsed.json` (canonical); builds structured `claim_chart-<ts>.json` with overlap_score + risk roll-up | `.evidraft/patent/claims.md` + `claims_parsed.json` + `claim_chart.md` + `claim_chart-<ts>.json` |
| `workflow:patent.review` | 5-role panel (engineer / drafter / novelty critic / technical / examiner) + consistency-checker, **backed by 3 structured audits** (claim-parser, claim-chart-builder, novelty-heuristics with advisory `verdict_hint ∈ {novel, narrow, redraft, withdraw}`) | `.evidraft/patent/patent_review_report.md` + `novelty_audit-<ts>.findings.json` |

### Shared / Phase 2 (4 modules)

| Command | Purpose | Key output |
|---|---|---|
| `workflow:scope.run` | superpowers-style requirement clarification (paper or patent branch); Carlini conclusion-first test; Pursue/Refine/Kill verdict; `--fast` mode for 3 questions | `.evidraft/scope/YYYY-MM-DD-<slug>.md` |
| `workflow:research.deep` | 6-stage heavy literature workflow: Frame → Retrieve → Screen → Cluster → Critique → Synthesise; PRISMA-style log; mandatory citation audit | `.evidraft/literature/{plan.yaml, candidates.jsonl, screening_log.csv, clusters.yaml, critique/, citation_audit.json, related_work.draft.md}` |
| `workflow:xreview.run` | Delegate to an external agent (Codex / Claude bare / OpenCode) for a second-opinion review; read-only enforced; stdin-only prompts | `.evidraft/reviews/<agent>-<persona>-<ts>.md` |
| `workflow:polish.run` | Williams-style humanize: preserves numbers/citations/entities/hedges; mandatory diff log; ethics-bound (not detector-evasion) | rewritten target + `.evidraft/style/humanize-<ts>.{log,report.md}` |

`workflow:scope.run` is a precondition enforced by `policy:scope`. The policy **blocks** `workflow:paper.draft`, `workflow:patent.claims`, and `workflow:polish.run`; it **warns** for `workflow:paper.idea`, `workflow:patent.scout`, and `workflow:research.deep`; all other operation IDs pass.

## Workflow ordering

### Paper

```
workflow:paper.init
  └─► workflow:scope.run           (required by policy:scope)
        └─► workflow:paper.lit               (light, single-pass)
        OR workflow:research.deep             (heavy, 6-stage; PRISMA-style)
              └─► workflow:paper.idea
                    └─► workflow:paper.code-audit
                          └─► workflow:paper.experiment
                                └─► workflow:paper.review
                                      └─► workflow:paper.draft
                                            └─► workflow:paper.check
                                                  └─► workflow:polish.run           (optional)
                                                        └─► workflow:paper.venue (submission)
                                            └─► workflow:xreview.run                (any time, optional)
```

### Patent

```
workflow:patent.init
  └─► workflow:scope.run        (required by policy:scope)
        └─► workflow:patent.scout
              └─► workflow:patent.prior-art
                    └─► workflow:patent.disclosure   ◀ primary deliverable: 技术交底书
                          └─► workflow:patent.claims
                                └─► workflow:patent.review
                                      └─► workflow:xreview.run  (second opinion, optional)
```

## The 3 executable policies

| Policy | Trigger | Behaviour |
|---|---|---|
| `policy:workspace-safety` | every read and write; especially `workflow:xreview.run` | Constrain paths to the project root, deny sensitive paths, and keep external-review writes under `.evidraft/reviews/`. |
| `policy:scope` | high-impact creative operations | Block publish-oriented writing without current scope; warn for idea, scout, and deep-research analysis. |
| `policy:evidence-integrity` | publishable claims and rewrites | Resolve citations and evidence ids, reject invalid supersession, require verified evidence, and preserve claim-bearing tokens. |

The deterministic kernel evaluates policies in that order during preflight and finalize. `capability:latex-build` is an action procedure used by paper checks and venue conversion, not a fourth policy. Host hooks may repeat these checks as an extra defence, but the shared policy result is authoritative across hosts.

## What to do on first interaction

### Single-paper explanation routing

Apply this branch before the general literature-intent question below. These cases
identify a single identifiable paper rather than a topic or research direction.

- If the user supplies a local PDF, arXiv identifier/URL, DOI, or paper URL and
  asks to explain, analyse, close-read, interpret equations, critique, or
  produce an academic reading note, recommend `workflow:research.explain`.
- If the user names one uniquely identifiable paper with the same intent,
  recommend `workflow:research.explain`.
- Recognise equivalent Chinese intent semantically, including 解释论文, 讲解论文,
  精读, 公式分析, and 学术阅读笔记.
- `workflow:using.run` remains read-only: recommend and confirm before invoking.
- If the request is ambiguous between papers, methods, projects, or research
  directions, resolve or ask for the specific paper first.
- Route an entire research direction to `workflow:research.deep`, not explain.

1. **Read intent first.** If the user's request involves literature work (调研 / 综述 / "look up X" / "find papers on Y") **without** explicit mention of a paper section, patent, venue, or submission, ask ONE intent-clarifying question before any recommendation:

   > Is this for personal literature research (markdown notes only), or are you building toward a paper / patent? I can do either; they go through different paths.

   **Skip the question when context disambiguates** (no need to ask):
   - `.evidraft/project.yaml.status.manuscript` is `in_progress` or `done` → paper mode.
   - `.evidraft/project.yaml.project_type` is `patent` or `mixed` → patent mode.
   - The user names a venue, "投稿", "submit", "paper section", "TID", or similar → paper / patent mode.
   - The user says "just / 只是 / 自己看 / personal / notes / 笔记" → notes mode.
   - The cwd has **no `.evidraft/` directory at all** AND the topic is a short noun phrase (≤ 4 tokens) AND no paper/patent/venue/submit keywords are present → default to **notes mode**; **confirm** ("I'll do a markdown reading list — OK?") rather than ask the binary question. This is the dominant personal-reading case: a short topic in a fresh directory rarely means "build a paper from scratch", and a single confirmation costs less than a yes/no question.

2. **For notes mode** (the answer is "personal" or skip-heuristic detected it): recommend `workflow:research.reading-list <topic>` directly. **Do not** propose `workflow:paper.init`. The reading-list command needs no project scaffold, no scope file, no BibTeX. Output lands at `.evidraft/notes/<slug>-<date>.md` and is the sole artefact.

   **Topic-specificity sub-question.** If the user's topic is a bare noun phrase ≤ 2 tokens (e.g. `code agent`, `RAG`, `vision transformer`), ask one scope-tightening question BEFORE dispatching: `narrow to <subtopic-A> | <subtopic-B> | broad survey?`. The 2-token threshold is empirical — bare topics blow up the candidate pool with scaffolds and benchmarks (the dogfood1 trial had 5 of 15 included entries only tangentially related to "code agent"). For topics ≥ 3 tokens the user has usually already done the scoping; do not re-ask.

3. **For paper / patent mode**:
   1. `Read` `.evidraft/project.yaml` if it exists.
   2. If missing → recommend `workflow:paper.init` or `workflow:patent.init`.
   3. If present → walk the `status:` block, find the first non-`done` stage, recommend its command.
   4. List any blocking policy conditions (e.g., `policy:scope` if `scope/` is missing).

4. **Always** confirm with the user before invoking the recommended next command. Never replay the **intent question itself** as a 3-option matrix — it is a single binary choice (notes vs paper/patent). Orthogonal-concern triage that arises *after* the intent is settled (e.g. output-file collision, ambiguous family clustering, missing sub-argument) remains acceptable and should still be surfaced as a small choice menu to the user.

## What this skill never does

- Pretend a stage is done when it is not.
- Invent slash-command names. Only commands listed above exist; everything else does not.
- Skip `workflow:patent.disclosure` (TID) in favour of `workflow:patent.claims` first — claims are advisory and downstream.
- Strip the "Needs attorney review" footer from any patent artefact.
- Remove the `policy:evidence-integrity` or `policy:evidence-integrity` rules from `project.yaml.rules`.
