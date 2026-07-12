---
id: deep-literature-review
title: "Deep literature review: 6-stage pipeline, PRISMA flow, SWOT, citation audit"
kind: skill
phase: paper
description: >
  Load whenever workflow:research.deep runs. Provides the full 6-stage
  Frame → Retrieve → Screen → Cluster → Critique → Synthesise spec, the
  breadth/depth semantics, the PRISMA screening-log recipe, the citation
  audit rules, the per-paper SWOT template, and the clusters.yaml schema.
  Complements (does not replace) the lighter literature-review skill used
  by workflow:paper.lit.
triggers:
  - "workflow:research.deep"
  - "running 6-stage literature workflow"
  - "writing PRISMA screening log"
  - "writing per-paper SWOT"
  - "running citation audit on related_work.draft.md"
  - "resuming a deepresearch run"
provides:
  - six-stage-spec
  - breadth-depth-semantics
  - prisma-flow-recipe
  - citation-audit-rules
  - per-paper-swot-template
  - clusters-yaml-schema
  - resume-protocol
allowed_tools: [Read, Glob, Grep, Write, Edit]
policies: [evidence-integrity]
references:
  - doc: capability:literature-review
  - doc: capability:scholar-search
  - doc: capability:evidence-check
---

# deep-literature-review

## When to use

Pull this skill whenever `workflow:research.deep` runs (or when resuming one of its stages). The light single-pass `workflow:paper.lit` keeps its own skill (`capability:literature-review`); this one is the heavyweight cousin. The two are not interchangeable: `literature-review` defines the citation-key convention, BibTeX hygiene, and method-family clustering that *both* commands share; `deep-literature-review` adds the 6-stage pipeline, the PRISMA screening log, the per-paper SWOT, and the citation audit.

Retrieval is delegated to the `scholar-search` skill (`capability:scholar-search`), which calls the built-in `WebSearch` / `WebFetch`. When network access is unavailable or the session is offline, every stage degrades to local PDFs + BibTeX — see [references/failure-modes.md](references/failure-modes.md).

## How to navigate this skill

This capability specification is the entry; the **detail for each stage** lives in `references/`. Load only the stage you are running:

| Stage | Reference | Owns |
|---|---|---|
| 1 — Frame | [references/stage-1-frame.md](references/stage-1-frame.md) | procedure, `plan.yaml` schema |
| 2 — Retrieve | [references/stage-2-retrieve.md](references/stage-2-retrieve.md) | procedure, `candidates.jsonl` schema, dedup rules, concurrency |
| 3 — Screen | [references/stage-3-screen.md](references/stage-3-screen.md) | procedure, `screening_log.csv` schema, PRISMA counts |
| 4 — Cluster | [references/stage-4-cluster.md](references/stage-4-cluster.md) | procedure, `clusters.yaml` + `evidence_map.json` schemas |
| 5 — Critique | [references/stage-5-critique.md](references/stage-5-critique.md) | procedure, SWOT template, concurrency |
| 6 — Synthesise | [references/stage-6-synthesise.md](references/stage-6-synthesise.md) | procedure, `citation_audit.json` schema, audit rules |

**Cross-cutting concerns** (load when needed, not by default):

- Budget knobs `breadth` / `depth` / `mode`: [references/breadth-depth-budget.md](references/breadth-depth-budget.md)
- PRISMA counts formula + final chat output: [references/prisma-recipe.md](references/prisma-recipe.md)
- Resume from a specific stage: [references/resume-protocol.md](references/resume-protocol.md)
- Failure / degradation catalog (every stage): [references/failure-modes.md](references/failure-modes.md)
- Upstream idea credits: [references/upstream-credits.md](references/upstream-credits.md)
- Anti-patterns: [references/anti-patterns.md](references/anti-patterns.md)

## Inputs

- `.evidraft/project.yaml` (`field`, `target_venue`, `topic`)
- the latest `.evidraft/scope/*.md`
- `.evidraft/literature/plan.yaml`, `candidates.jsonl`, `screening_log.csv`, `clusters.yaml`, `evidence_map.json`, `critique/*.md`, `related_work.draft.md`, `citation_audit.json` (whichever already exist for the current `run_id`)
- `.evidraft/literature/references.bib`
- `.evidraft/evidence/evidence.jsonl`
- optional MCP tools: `search_papers(provider=...)`, `get_paper_metadata`, `get_paper_references`, `get_paper_citations`, `download_pdf`, `resolve_citation`

## Outputs

All under `.evidraft/literature/`:

- `plan.yaml` (Stage 1)
- `candidates.jsonl` (Stage 2)
- `screening_log.csv` (Stage 3)
- `clusters.yaml`, `evidence_map.json` (Stage 4)
- `critique/<cluster-id>.md` (Stage 5)
- `related_work.draft.md`, `citation_audit.json` (Stage 6)

Plus new `type=note` rows appended to `.evidraft/evidence/evidence.jsonl` per `Delta vs our angle` paragraph.

## Quality checklist

- [ ] `plan.yaml` exists, declares `run_id`, `breadth`, `depth`, `providers`, `mode`.
- [ ] `candidates.jsonl` has one canonical row per dedup cluster; `source` is one of `arxiv | semantic-scholar | openalex | local-bib | local-pdf`.
- [ ] `screening_log.csv` covers 100% of `candidates.jsonl`; every exclude has a one-sentence reason.
- [ ] `plan.yaml.prisma` populated; counts match `screening_log.csv`.
- [ ] `clusters.yaml` has 3–6 clusters; every cluster has 1+ members and a `why_one_cluster` sentence.
- [ ] Every cluster has a `critique/<cluster-id>.md`; every member paper has a SWOT + `Delta vs our angle`.
- [ ] `related_work.draft.md` has one paragraph per cluster (or per tight pair); every paragraph cites ≥ 2 `citation_key`s and ends with a contrast sentence.
- [ ] `citation_audit.json` reports `failed = 0`.
- [ ] PRISMA flow printed to chat at the end.
