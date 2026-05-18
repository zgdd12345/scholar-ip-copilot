---
id: using-scholar-ip-copilot
title: "Using the scholar (EviDraft) plugin — full workflow orientation"
kind: skill
phase: shared
description: >
  Establishes how the scholar (EviDraft) plugin works, what every /scholar:<cmd>
  does, the order to invoke them in, what gets written to .evidraft/, and which
  hooks gate downstream work. Modelled on superpowers:using-superpowers.
triggers:
  - "session start"
  - "first interaction in an EviDraft project"
  - "user asks 'what can this plugin do?' or 'how do I use this?'"
  - "before any /scholar:<cmd> is invoked for the first time in a session"
provides:
  - "complete command map (16 commands + future modules)"
  - "workflow ordering for paper and patent phases"
  - "evidence-grounded discipline overview"
  - "gating-hook reference"
allowed_tools: [Read, Glob, Grep]
hooks: []
references:
  - doc: ../../../../README.md
  - doc: ../../../../docs/architecture.md
  - doc: ../../../../docs/data-model.md
  - doc: ../../../../docs/legal-and-ethics.md
  - doc: ../../plugin.yaml
---

# Using `scholar` (EviDraft)

<EXTREMELY-IMPORTANT>
If a `/scholar:<cmd>` is relevant to the user's request, you MUST follow this
skill's workflow ordering and gating rules. Skipping `/scholar:paper-init`
before drafting, or skipping `/scholar:patent-disclosure` before claims, is a
discipline violation — the plugin will refuse via hook.
</EXTREMELY-IMPORTANT>

You are working inside the **scholar** plugin (product name **EviDraft**). The plugin id is `scholar`; everything is invoked as `/scholar:<cmd>`. The folder on disk is `plugins/scholar-ip/` (historical, tied to the repo name `scholar-ip-copilot`).

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
│   ├── project.yaml                project type, status, rules, hooks
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

### Meta (1)

| Command | What it does |
|---|---|
| `/scholar:using` | This entry — orientation. Read-only. |

### Paper (9) — arXiv-neutral draft, venue chosen at submission time

| Command | Purpose | Key output |
|---|---|---|
| `/scholar:paper-init` | Scaffold `.evidraft/` + `manuscript/` (arXiv style) | `.evidraft/project.yaml`, `manuscript/main.tex` |
| `/scholar:paper-lit` | Literature matrix + BibTeX + evidence | `.evidraft/literature/matrix.md`, `references.bib` |
| `/scholar:paper-review` | Related-work / survey section | `manuscript/sections/related_work.tex` |
| `/scholar:paper-idea` | Novelty / risk / experiments-to-run matrices | `.evidraft/ideas/*.md` |
| `/scholar:paper-code-audit` | Method ↔ code mapping + claim audit (5-state verdict) | `.evidraft/code/method_to_code.md`, `paper_code_audit.md` |
| `/scholar:paper-experiment` | Experiment analysis + LaTeX tables | `.evidraft/experiments/result_analysis.md` + `tables/*.tex` |
| `/scholar:paper-draft` | Outline → section plan → full LaTeX | `manuscript/sections/*.tex` |
| `/scholar:paper-check` | Citation / LaTeX / refs / claim-evidence / number-source audit | `.evidraft/manuscript/paper_check_report.md` |
| `/scholar:paper-venue` | Convert arXiv-style → CVPR/NeurIPS/ICCV/… template at submission | `submissions/<venue>/main.tex` |

### Patent (6) — 技术交底书 / TID first

| Command | Purpose | Key output |
|---|---|---|
| `/scholar:patent-init` | Scaffold `.evidraft/patent/` + TID template | `.evidraft/patent/invention_disclosure.md` |
| `/scholar:patent-scout` | Discover candidate inventions from code/docs | `.evidraft/patent/invention_candidates.md` |
| `/scholar:patent-prior-art` | Prior-art map + claim-chart skeleton | `.evidraft/patent/prior_art_map.md`, `claim_chart.md` |
| `/scholar:patent-disclosure` | **Primary deliverable**: 技术交底书 (TID), 13 bilingual sections | `.evidraft/patent/invention_disclosure.md` |
| `/scholar:patent-claims` | Advisory: draft independent + dependent claims | `.evidraft/patent/claims.md` |
| `/scholar:patent-review` | 5-role review (engineer / drafter / novelty critic / technical / examiner) | `.evidraft/patent/patent_review_report.md` |

### Phase 2 (planned — separate ship)

| Command | Purpose |
|---|---|
| `/scholar:brainstorming` | superpowers-style requirement clarification; writes `.evidraft/scope/YYYY-MM-DD-<slug>.md`; hard precondition for paper-idea / patent-scout / draft / claims |
| `/scholar:deepresearch` | 6-stage heavy literature workflow: Frame → Retrieve → Screen → Cluster → Critique → Synthesise; PRISMA-style screening log |
| `/scholar:xreview` | Delegate to an external agent (Codex / Claude bare / OpenCode); writes `.evidraft/reviews/<agent>-<persona>-<ts>.md`; read-only enforced |
| `/scholar:polish` | Williams-style humanize: reduce AI-flavour, preserve numbers/citations; mandatory diff log |

## Workflow ordering

### Paper

```
/scholar:paper-init
  └─► /scholar:brainstorming           (Phase 2; recommended)
        └─► /scholar:paper-lit
              └─► /scholar:paper-idea  (or /scholar:deepresearch for heavy review)
                    └─► /scholar:paper-code-audit
                          └─► /scholar:paper-experiment
                                └─► /scholar:paper-review
                                      └─► /scholar:paper-draft
                                            └─► /scholar:paper-check
                                                  └─► /scholar:paper-polish  (Phase 2)
                                                        └─► /scholar:paper-venue  (submission time)
```

### Patent

```
/scholar:patent-init
  └─► /scholar:brainstorming        (Phase 2)
        └─► /scholar:patent-scout
              └─► /scholar:patent-prior-art
                    └─► /scholar:patent-disclosure   ◀ primary deliverable: 技术交底书
                          └─► /scholar:patent-claims
                                └─► /scholar:patent-review
```

## The 4 guardrail hooks

| Hook | Trigger | Behaviour |
|---|---|---|
| `citation-guard` | writing related_work / intro / abstract / TID advantages | Block strong-claim verbs (SOTA, novel, first, outperform, significant) without a `\cite{}` or `evidence_id` within 30 chars. |
| `evidence-consistency` | writing any paper section / TID section | Block: literature claims must trace to `evidence.jsonl`; numbers must trace to `experiments/`; code claims must include `file_path` + line range. |
| `latex-compile` | `.tex` modified | Warn: run `latexmk`, parse structured errors. |
| `sensitive-file-guard` | reading `.env`, `secrets/`, `credentials.json`, `*.pem`, `*.key` | Block by default; explicit one-shot user-confirmed override required. |

Downgrade is allowed in `.evidraft/project.yaml`'s `hooks:` block — but each downgrade is logged in the relevant check report.

## What to do on first interaction

1. `Read` `.evidraft/project.yaml` if it exists.
2. If missing → recommend `/scholar:paper-init` or `/scholar:patent-init`.
3. If present → walk the `status:` block, find the first non-`done` stage, recommend its command.
4. List any gating hooks that are currently active (e.g., scope-required if Phase 2 is installed and `scope/` is missing).
5. Confirm with the user before invoking the recommended next command.

## What this skill never does

- Pretend a stage is done when it is not.
- Invent slash-command names. Only commands listed above exist; everything else does not.
- Skip `/scholar:patent-disclosure` (TID) in favour of `/scholar:patent-claims` first — claims are advisory and downstream.
- Strip the "Needs attorney review" footer from any patent artefact.
- Remove the `citation-guard` or `evidence-consistency` rules from `project.yaml.rules`.
