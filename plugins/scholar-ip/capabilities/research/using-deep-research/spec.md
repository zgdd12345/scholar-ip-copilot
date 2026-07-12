---
id: using-deep-research
title: "Entrypoint for workflow:research.deep — what it does, what it needs, how to start"
kind: skill
phase: shared
description: >
  Load this skill when the user wants to run a deep / PRISMA-style literature
  review and may not have an EviDraft project set up yet. Walks through the
  minimum scaffolding (`workflow:paper.init` + `workflow:scope.run`) that
  unblocks `workflow:research.deep`, surfaces the `breadth` / `depth` budget
  knobs, lists the 6-stage output artefact map, offers a scope-stub fast-path
  for ad-hoc use, and explains the four failure modes (no scope, retrieval
  denied, budget exceeded, failed citation audit). Use when the user says
  "deep lit review", "PRISMA review", "comprehensive review on X", or invokes
  `workflow:research.deep` directly without context.
triggers:
  - "workflow:research.deep"
  - "workflow:research.guide"
  - "deep literature review"
  - "PRISMA-style review"
  - "comprehensive literature review on <topic>"
  - "I want to research papers on <topic>"
  - "do a full lit review for me"
provides:
  - deep-research-prereqs
  - scope-stub-fast-path
  - budget-knob-defaults
  - resume-protocol
  - output-artefact-map
allowed_tools: [Read, Glob, Grep, Write, Edit, "Bash:mkdir*", "Bash:date*"]
references:
  - doc: capability:deep-literature-review
  - doc: capability:scholar-search
  - doc: capability:brainstorming
  - doc: workflow:research.deep
  - doc: workflow:scope.run
  - doc: workflow:paper.init
---

# Using deep-research

See [references/example.md](references/example.md) for the bundle-resource demonstration pattern (propagated to every host's rendered output by the loader's skill-bundle support).

You are about to drive a PRISMA-style 6-stage deep literature review for the user. Read this once, then run the right action sequence. Invoking `workflow:research.deep` directly is also fine, but `policy:scope` preflight blocks when required scaffolding is missing.

## What `workflow:research.deep` produces

A 6-stage pipeline (Frame → Retrieve → Screen → Cluster → Critique → Synthesise) writing into `.evidraft/literature/`:

| Stage | Artefact | Owner |
|---|---|---|
| 1 Frame | `plan.yaml` (research question, providers, budget, PRISMA block) | orchestrator |
| 2 Retrieve | `candidates.jsonl` (dedup'd across arXiv / Semantic Scholar / OpenAlex) | `scholar-search` skill via `WebSearch` + `WebFetch` |
| 3 Screen | `screening_log.csv` + PRISMA counts | `screener` subagent |
| 4 Cluster | `clusters.yaml`, `evidence_map.json` (method families) | orchestrator |
| 5 Critique | `critique/<cluster-id>.md` (SWOT + Delta-vs-our-angle per paper) | `paper-critic` subagent |
| 6 Synthesise | `related_work.draft.md` + `citation_audit.json` | `literature-reviewer` + `evidence-auditor` subagents |

Plus appended `type=paper` evidence rows in `.evidraft/evidence/evidence.jsonl` and verified entries in `.evidraft/literature/references.bib`.

## Required scaffolding (two cheap one-off steps)

You do **not** need a paper project to use deepresearch. The two prereq commands just create the on-disk skeleton the pipeline writes to:

```text
workflow:paper.init                       # 30s — builds .evidraft/ + minimal manuscript/ skeleton
workflow:scope.run "<your topic>"     # 5min interactive — writes .evidraft/scope/<date>-<slug>.md
workflow:research.deep "<topic>" --breadth 30 --depth 2
```

`paper-init` builds `.evidraft/project.yaml`, empty `references.bib`, empty `evidence.jsonl`. You can ignore the `manuscript/` directory if you are only doing a lit review.

`workflow:scope.run` writes a single scope file. `policy:scope` preflight enforces three rules on the latest `.md` under `.evidraft/scope/`:

1. **Existence** — at least one file matches.
2. **Approval** — frontmatter has `status: approved`.
3. **Freshness** — `today - approved_date <= staleness_days` (default 14).

The fast-path stub below satisfies all three.

## Fast-path: scope-stub for ad-hoc use

When the user explicitly pushes back on the 5-minute brainstorming step ("just run it"), you may stub the scope file. **Confirm with the user first** ("running brainstorming gives sharper recall — want to skip it?") and then:

```bash
TODAY="$(date +%Y-%m-%d)"
STALE="$(date -v+14d +%Y-%m-%d 2>/dev/null || date -d '+14 days' +%Y-%m-%d)"
mkdir -p .evidraft/scope
cat > ".evidraft/scope/${TODAY}-fast.md" <<EOF
---
kind: paper
status: approved
verdict: pursue
riskiest_assumption: "Ad-hoc scope; needs later refinement."
evidence_seeds: []
approved_date: ${TODAY}
staleness_until: ${STALE}
---
# Scope: <topic>

> Created via scope-stub fast path; not a substitute for brainstorming.
> policy:scope checks: status=approved + 14-day freshness.

## Research question
<one sentence — extract from the user's request>

## Inclusion
- year_range: 2021-2026
- venues: any
- languages: en

## Exclusion
- (none specified)
EOF
```

The frontmatter (`status: approved`, `approved_date`) is what makes preflight pass; without it the stub is treated as a draft and the gated action is refused. The orchestrator's stage-1 frame reads this file when building `plan.yaml`.

## Budget knobs

| Knob | Default | Meaning |
|---|---|---|
| `breadth` | 20 | sub-queries × providers in stage 2; total candidates capped at `breadth × 50` |
| `depth` | 2 | reference / citation hops in stage 2 and lineage hops in stage 4 |
| `mode` | `default` | `fast` halves both; useful for scoping before committing to a real run |
| `resume_from` | (none) | skip earlier stages when their artefacts already exist on disk |

Recommended presets:

- **Real lit review**: `--breadth 30 --depth 2` (~150-300 candidates, ~10-25 included)
- **Scoping pass**: `--breadth 10 --mode fast`
- **One-shot survey paper**: `--breadth 50 --depth 3` (expensive; do this once)

## Resume on crash

Every stage's artefact is written to disk before the next stage begins. If the run crashes mid-pipeline:

```text
workflow:research.deep --resume_from screen      # skip Frame + Retrieve
workflow:research.deep --resume_from cluster
workflow:research.deep --resume_from synthesise
```

The orchestrator validates that all earlier stages' artefacts exist + parse cleanly; otherwise it refuses and tells you which stage to re-run.

## Failure modes you must handle gracefully

1. **No scope file** → `policy:scope` preflight blocks. Offer `workflow:scope.run` or the scope-stub fast path above. Never bypass silently.
2. **Network / WebSearch denied** → fall back to user's local PDFs + `references.bib`. Each fallback row uses `source: "local-bib"` or `source: "local-pdf"`. Log the degradation in `plan.yaml.notes`.
3. **Budget exceeded** → orchestrator refuses fan-out and surfaces the refusal to the user, logged in `plan.yaml.budget_log[]`. Suggest the user increase `--breadth` or accept truncation.
4. **Stage-6 `citation_audit.json` has `failed > 0`** → run does not complete. Surface the failing claims and tell the user which stage to re-run. The orchestrator will refuse to declare the run done.

## When NOT to use deepresearch

- For a **one-pass quick refresh**: use `workflow:paper.lit` instead (cheaper, single stage).
- For **"write me a quick survey"** without PRISMA discipline: use `workflow:paper.lit "<topic>" --draft-outline` — same single-pass matrix plus a method-family outline written to `.evidraft/literature/related_work_outline.md`. Cheaper than deepresearch, less rigorous; not a substitute when claims need PRISMA backing.
- For **1-3 specific paper lookups**: just call the `scholar-search` skill directly via `@agent-scholar:scholar-search "<query>"`.
- For **BibTeX cleanup only**: use the `bib-manager` skill.

## Decision tree

```text
User wants lit review:
  ├─ "comprehensive" / "PRISMA" / "for a paper" / >5 papers expected
  │     → recommend full path: paper-init + brainstorming + deepresearch
  │
  ├─ "write me a quick survey / outline" / "I want a draft to skim"
  │     → workflow:paper.lit "<topic>" --draft-outline
  │       (single-pass matrix + outline; NOT PRISMA, NOT deepresearch Stage 6)
  │
  ├─ "quick" / "ad-hoc" / <10 papers expected
  │     → either workflow:paper.lit, or offer the scope-stub fast-path
  │       + workflow:research.deep --breadth 10 --mode fast
  │
  └─ "just one paper" / "what's the SOTA for X"
        → @agent-scholar:scholar-search directly, no scaffolding needed
```

## Recommendation when invoked

If the user just typed `workflow:research.guide` with no topic, ask them for the topic, then propose the right path based on their answer. If they typed `workflow:research.guide "<topic>"`, default to the **full** path (paper-init + brainstorming + deepresearch) and offer the fast-path only if they push back on brainstorming.
