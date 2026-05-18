---
id: deep-literature-review
title: "Deep literature review: 6-stage pipeline, PRISMA flow, SWOT, citation audit"
kind: skill
phase: paper
description: >
  Load whenever /scholar:deepresearch runs. Provides the full 6-stage
  Frame → Retrieve → Screen → Cluster → Critique → Synthesise spec, the
  breadth/depth semantics, the PRISMA screening-log recipe, the citation
  audit rules, the per-paper SWOT template, and the clusters.yaml schema.
  Complements (does not replace) the lighter literature-review skill used
  by /scholar:paper-lit.
triggers:
  - "/scholar:deepresearch"
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
hooks: [citation-guard, evidence-consistency]
references:
  - doc: ../literature-review/SKILL.md
  - doc: ../evidence-check/SKILL.md
  - doc: ../../../../packages/mcp/scholar-search-mcp/README.md
---

# deep-literature-review

## When to use

Pull this skill whenever `/scholar:deepresearch` runs (or when resuming one of its stages). The light single-pass `/scholar:paper-lit` keeps its own skill (`literature-review`); this one is the heavyweight cousin. The two are not interchangeable: `literature-review` defines the citation-key convention, BibTeX hygiene, and method-family clustering that *both* commands share; `deep-literature-review` adds the 6-stage pipeline, the PRISMA screening log, the per-paper SWOT, and the citation audit.

If `scholar-search-mcp` is unavailable, every stage degrades to local PDFs + BibTeX (see *Failure modes*).

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

## Procedure

### Stage 1 — Frame

1. Read `project.yaml` + the latest `scope/*.md`.
2. Decompose the topic into ≤ `breadth` sub-queries, each tagged by perspective (method, dataset, theory, application, evaluation, critique). One perspective per query. Modelled on **STORM**'s perspective-guided retrieval.
3. Derive inclusion / exclusion keywords, year window, venue allow-list, language allow-list.
4. Write `plan.yaml` (schema in `commands/deepresearch.md`).

### Stage 2 — Retrieve

1. For each sub-query × each provider in `plan.yaml.providers`, call `search_papers(query, year_range=..., venue=..., top_k=breadth*5, provider=p)`. Record `source` (`arxiv | semantic-scholar | openalex`).
2. For `depth > 1`, fan out one hop of `get_paper_references` and `get_paper_citations` per retained paper, capped by the remaining budget. Total candidates ≤ `breadth * 50`.
3. Deduplicate by DOI, then by (normalised title, first author, year). Keep one canonical row per dedup cluster; stash variants under `aliases`. Never silently blend two providers into one row.
4. Write `candidates.jsonl` (one JSON object per line).

### Stage 3 — Screen

1. Build the rubric from `plan.yaml.inclusion_keywords`, `exclusion_keywords`, `filters`.
2. Score 0–5; decide `include / maybe / exclude`; one-sentence `reason` per row.
3. For borderline rows with missing abstracts, call `get_paper_metadata` once before deciding.
4. Aggregate PRISMA counts; write them to `plan.yaml.prisma` and the per-row decisions to `screening_log.csv`.

This stage is owned by the `screener` sub-agent. The discipline is borrowed from PRISMA-flow tooling (ASReview, Rayyan, open-paper-machine): every drop has a reason; no silent rejects.

### Stage 4 — Cluster

1. Group `include` rows into 3–6 clusters by **technical mechanism**, not by application (use the family rules from `../literature-review/SKILL.md`).
2. For each cluster, walk one hop each of `get_paper_references` (ancestors) and `get_paper_citations` (follow-on), capped by `depth`. Fill `method_lineage`, `dataset_lineage`, `theory_lineage`.
3. Mint provisional `citation_key`s using the `firstauthorYEARkeyword` rule.
4. Write `clusters.yaml` and `evidence_map.json`.

### Stage 5 — Critique

Per paper, per cluster, write a SWOT plus `Delta vs our angle`. Owned by `paper-critic`. Every bullet cites a section / figure / table / equation. Modelled on the per-section sub-agent pattern used by **GPT-Researcher** and the structured research-brief style of **Open Deep Research**.

### Stage 6 — Synthesise + audit

1. `literature-reviewer` drafts `related_work.draft.md`: one paragraph per cluster (or per tight pair); ≥ 2 `citation_key`s per paragraph; ends with a contrast sentence backed by an `evidence_id`.
2. `evidence-auditor` runs the **citation audit** on every claim in the draft. Each claim resolves to a `citation_key` (must exist in `references.bib`; use `resolve_citation` when matching free-text) and ≥ 1 `evidence_id`. Resolutions land in `citation_audit.json`.
3. If `citation_audit.failed > 0`, refuse to mark the run done.

## Breadth / depth semantics

| Knob | Default | Meaning | Hard ceiling |
|---|---|---|---|
| `breadth` | 6 | max sub-queries at Stage 1; multiplies into per-query `top_k = breadth * 5` at Stage 2; max clusters at Stage 4 capped at `min(6, breadth)`. | total candidates ≤ `breadth * 50`. |
| `depth` | 2 | recursion depth for `get_paper_references` / `get_paper_citations`; `depth=1` skips the lineage hop entirely. | `depth ≤ 3` in `full` mode; `depth ≤ 2` in `fast` mode. |

`mode=fast` halves both, rounded up, and skips Stage 5 SWOT bullets that require the full PDF. The budget is tracked in `plan.yaml.budget_log[]`; over-budget fan-outs are refused and logged.

This is the same control surface used by **dzhng/deep-research**: two knobs, both user-facing, both visible in the artefact.

## PRISMA flow recipe

Compute and persist:

```
retrieved        = len(candidates.jsonl, before dedup)
after_dedup      = len(candidates.jsonl, canonical rows only)
screened_in      = count(decision=include)
screened_out     = count(decision=exclude)
maybe            = count(decision=maybe)
clustered        = sum(len(cluster.members) for cluster in clusters.yaml)
cited_in_draft   = count(distinct citation_key referenced in related_work.draft.md)
```

`excluded_by_reason` is a histogram of the `reason` column. Print the full flow to chat at the end of every run.

## Citation audit rules

For every claim in `related_work.draft.md`:

1. Resolve to one or more `citation_key`s — each must already exist in `.evidraft/literature/references.bib`. Use `scholar-search-mcp.resolve_citation(claim, candidates)` for free-text matches; otherwise look up by hand.
2. Resolve to one or more `evidence_id`s — each must already exist in `.evidraft/evidence/evidence.jsonl`.
3. Append a row to `citation_audit.json.claims[]` with `paragraph, claim, citation_keys, evidence_ids, status, resolver, confidence`.
4. If `status=failed` for any claim, the run does not complete. Surface the failing claims and tell the user which stage to re-run.

Strong-claim verbs in the draft (SOTA, novel, first, outperform, significant, superior, …) still require a `\cite{}` or `ev_NNNN` within 30 chars — the `citation-guard` hook will block the write otherwise.

## Per-paper SWOT template

```markdown
## <citation_key> — <paper title>

- **Strengths.**     - <bullet> (Section X.Y / Fig N / Tbl M / Eq K)
- **Weaknesses.**    - <bullet> (Section X.Y / ...)
- **Opportunities.** - <bullet> (what gap this opens for us)
- **Threats.**       - <bullet> (what blocks our angle if this paper is right)
- **Delta vs our angle.** <one paragraph; ends with the appended evidence id>
```

Rules:

- Strengths / Weaknesses describe the paper itself; Opportunities / Threats describe the paper *as it bears on our project*.
- Every bullet cites a section, figure, table, or equation. Abstract paraphrase is not a citation.
- `Delta vs our angle` is mandatory. If you cannot write it, the paper does not belong in related work.
- `mode=fast` drops bullets that require the full PDF; mark them `[skipped — fast mode]`. Abstract-only bullets are tagged `[abstract-only]`.

## `clusters.yaml` schema

```yaml
run_id: <utc-timestamp>
clusters:
  - id: c1
    name: <short technical-mechanism phrase>
    members: [cand_0001, cand_0007, ...]
    method_lineage: [<citation_key>, ...]      # ancestors via get_paper_references
    dataset_lineage: [<dataset name>, ...]
    theory_lineage: [<concept>, ...]
    why_one_cluster: <one sentence>
```

Rules:

- 3–6 clusters per run; a 7th cluster is a signal to collapse two existing ones (same rule as the light `literature-review` skill).
- Every paper belongs to at most one cluster (borderline cases get a secondary cluster note inside the cluster file).
- Cluster names describe **technical mechanism**, not application ("DETR-style set prediction" not "object detection").

## Failure modes

- `scholar-search-mcp` raises `NotImplementedError` (v0.1 stubs) → fall back to local BibTeX + PDFs. Each fallback row uses `source: "local-bib"` or `source: "local-pdf"`. Log the fallback in `plan.yaml.notes`.
- `get_paper_metadata` cannot fetch a missing abstract → screener decides on title + venue alone and notes `reason="abstract unavailable; decided on title+venue"`. No invented abstracts.
- `get_paper_references` / `get_paper_citations` unavailable → Stage 4 skips lineage fields (leaves `[]`) and logs `"lineage: degraded (mcp stub)"`. Cluster membership still produced.
- PDF unavailable at Stage 5 → SWOT bullets tagged `[abstract-only]` with reduced confidence; never invent section numbers.
- `resolve_citation` unavailable at Stage 6 → fall back to manual lookup against `references.bib` + `evidence.jsonl`; unresolved claims are `status: failed` and the run does not complete.
- Budget exceeded → fan-out refused, logged in `plan.yaml.budget_log[]`, surfaced to the user.

## Resume protocol

`resume_from=<stage>` skips every earlier stage. To resume:

1. Locate the latest `run_id` in `plan.yaml`.
2. Verify the artefacts of every stage strictly before `<stage>` exist and parse. If any is missing or malformed, refuse and name the missing artefact.
3. Restore `breadth` / `depth` from `plan.yaml`, not from user input.
4. Append, never overwrite — every artefact carries the same `run_id`.

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

## Idea-level references

- **STORM** — perspective-guided retrieval; we borrow the per-perspective sub-query split at Stage 1.
- **GPT-Researcher** — per-section sub-agent dispatch; we borrow the one-sub-agent-per-stage pattern.
- **dzhng/deep-research** — breadth/depth knobs; we expose the same two user-facing controls.
- **Open Deep Research** — structured research brief; we adopt the explicit `plan.yaml` artefact instead of an implicit prompt.
- **open-paper-machine** — PRISMA-style screening log shape; we adopt `id, score, decision, reason` as the canonical CSV.

These are idea-level borrowings only; no upstream code is imported.

## Anti-patterns

- Running `/scholar:deepresearch` when `/scholar:paper-lit` would suffice. The deep command is for survey-grade reviews; light projects pay a real cost in time and tokens.
- Blending metadata from two providers into one `candidates.jsonl` row.
- Re-scoring screened candidates after seeing later ones.
- Writing a SWOT bullet that paraphrases the abstract.
- Skipping `Delta vs our angle` for "obviously different" papers.
- Marking a run done while `citation_audit.failed > 0`.
- Editing `manuscript/sections/related_work.tex` directly — that file is owned by `/scholar:paper-review`, which consumes `related_work.draft.md` as its outline.
