---
id: deepresearch
title: "Deep literature research (6-stage pipeline)"
kind: command
slash: /scholar:deepresearch
phase: paper
description: >
  Heavyweight 6-stage literature workflow (Frame → Retrieve → Screen →
  Cluster → Critique → Synthesise) with PRISMA-style screening log and a
  mandatory final citation-audit pass. Multi-provider retrieval (arxiv /
  semantic-scholar / openalex). breadth/depth knobs bound the budget;
  resume_from skips earlier stages. Procedure detail in
  skills/deep-literature-review/SKILL.md.
inputs:
  - name: topic
    type: string
    optional: true
    description: "Free-text research focus. Falls back to project.yaml.topic when omitted."
  - name: breadth
    type: integer
    optional: true
    default: 6
    description: "Maximum sub-queries per fan-out at every stage."
  - name: depth
    type: integer
    optional: true
    default: 2
    description: "Recursion depth for follow-up queries (citations / references)."
  - name: providers
    type: list
    optional: true
    default: [arxiv, semantic-scholar, openalex]
    description: "Ordered retrieval backends consumed by skills/scholar-search/SKILL.md. Records `source` per row; never blends silently."
  - name: mode
    type: enum
    values: [fast, full]
    optional: true
    default: full
    description: "`fast` halves breadth+depth and skips per-paper SWOT; `full` runs all 6 stages."
  - name: resume_from
    type: enum
    values: [frame, retrieve, screen, cluster, critique, synthesise]
    optional: true
    description: "Skip all earlier stages and resume at the named stage."
outputs:
  - path: .evidraft/literature/plan.yaml
  - path: .evidraft/literature/candidates.jsonl
  - path: .evidraft/literature/screening_log.csv
  - path: .evidraft/literature/clusters.yaml
  - path: .evidraft/literature/evidence_map.json
  - path: .evidraft/literature/critique/
  - path: .evidraft/literature/related_work.draft.md
  - path: .evidraft/literature/citation_audit.json
allowed_tools: [Read, Glob, Grep, Write, Edit, WebSearch, WebFetch, "Bash:cat*", "Bash:ls*"]
hooks: [scope-required, citation-guard, evidence-consistency]
subagents: [deep-research-orchestrator, screener, paper-critic, literature-reviewer, evidence-auditor]
references:
  - doc: ../skills/deep-literature-review/SKILL.md
  - doc: ../skills/literature-review/SKILL.md
  - doc: ../skills/scholar-search/SKILL.md
  - doc: ../skills/bib-manager/SKILL.md
  - doc: ../skills/evidence-check/SKILL.md
---

# /scholar:deepresearch

Heavyweight 6-stage literature workflow: **Frame → Retrieve → Screen → Cluster → Critique → Synthesise**. Complements `/scholar:paper-lit` (which stays the light single-pass command); does **not** replace it. Every stage emits a durable artefact under `.evidraft/literature/` so partial runs are resumable via `resume_from`.

All retrieval flows through the `scholar-search` skill (`skills/scholar-search/SKILL.md`), which drives host-native `WebSearch` + `WebFetch` against arXiv / Semantic Scholar / OpenAlex (URL templates + rate-limit policy + cache convention live in the skill). When the host has no network, every stage degrades to local PDFs + BibTeX and records that fallback in the stage artefact.

The orchestration is owned by `deep-research-orchestrator`; this command is the executable contract.

## Resume protocol

If `resume_from=<stage>` is passed, skip every earlier stage. The orchestrator must:

1. Verify the prior stage's artefact exists and is well-formed; if not, refuse and tell the user which stage to re-run.
2. Restore the `breadth` / `depth` budget that was logged in `plan.yaml` rather than re-deriving from inputs.
3. Append, never overwrite — every artefact carries a `run_id` so multiple runs in the same project can be diffed.

## Stage 1 — Frame

**Preconditions.** `.evidraft/scope/*.md` exists (the `scope-required` hook enforces this). `topic` is set by user input or by `project.yaml`.

**Procedure.**

1. Read `.evidraft/project.yaml` (`field`, `target_venue`, `topic`) and the most recent `.evidraft/scope/*.md`.
2. Derive a research brief: research question, sub-questions, inclusion keywords, exclusion keywords, year window, venue allow-list, language allow-list.
3. Expand sub-queries up to `breadth` (default 6). One sub-query per perspective (method, dataset, theory, application, evaluation, critique).
4. Write `plan.yaml`.

**Artefact schema — `plan.yaml`.**

```yaml
run_id: <utc-timestamp>
topic: <string>
research_question: <string>
sub_queries:
  - id: q1
    text: <string>
    perspective: method | dataset | theory | application | evaluation | critique
filters:
  year_range: [<int>, <int>]
  venues: [<string>, ...]   # allow-list; empty = any
  languages: [en]
inclusion_keywords: [<string>, ...]
exclusion_keywords: [<string>, ...]
breadth: <int>
depth: <int>
providers: [arxiv, semantic-scholar, openalex]
mode: fast | full
```

**Failure mode.** No MCP needed at this stage. If `scope-required` blocks, stop and ask the user to run `/scholar:brainstorming`.

**Handoff.** Stage 2 reads `plan.yaml` only.

## Stage 2 — Retrieve

**Preconditions.** `plan.yaml` exists and validates.

**Procedure.**

1. For every sub-query, invoke `skills/scholar-search/SKILL.md` with `query`, `year_range`, `venue`, `top_k=breadth*5`, once per provider in `plan.yaml.providers`. The skill issues the appropriate `WebFetch` against arXiv / S2 / OpenAlex (URL templates verbatim in the skill), parses the response, dedups, and emits rows conforming to the `candidates.jsonl` schema below. Record `provider` as the `source` field of each row.
2. For `depth > 1`: for each retained paper, fan out via the skill's per-paper detail URLs to enumerate references (S2 `/paper/<id>?fields=references`) and citations (S2 `/paper/<id>?fields=citations` or OpenAlex `/works?filter=cites:<id>`) — one hop per depth level beyond 1. Cap total candidates at `breadth * 50` to prevent runaway expansion.
3. Deduplicate by DOI, then by (normalised title, first author, year). Keep the most authoritative `source` per dedup cluster, but preserve all variants under `aliases`.
4. Append rows to `candidates.jsonl`. Never blend metadata from two providers into one row without explicit reconciliation (see orchestrator constraints).

**Concurrency.** The `sub_query × provider` matrix in step 1 is fully independent — fan out concurrently with `min(breadth, lit_deep.max_concurrency)` in flight (default `lit_deep.max_concurrency: 8`, configurable in `.evidraft/project.yaml`). The `depth > 1` hops in step 2 are serial (they depend on step 1's retained set), but each hop's per-paper fan-out is again independent. Dedup (step 3) is single-threaded.

**Artefact schema — `candidates.jsonl`** (one JSON object per line):

```json
{"id":"cand_NNNN","title":"...","abstract":"...","venue":"...","year":2023,
 "authors":["..."],"doi":"...","source":"arxiv|semantic-scholar|openalex",
 "provider_id":"arxiv:2401.01234","sub_query_ids":["q1","q3"],
 "depth":0,"aliases":[{"source":"openalex","provider_id":"W..."}],
 "run_id":"..."}
```

**Failure mode.** If `WebFetch` is unavailable, every provider returns a hard rate-limit after retries, or the host has no network, fall back to: (a) BibTeX entries already in `.evidraft/literature/references.bib`, (b) PDFs under `references/` or `papers/`. Each fallback row uses `source: "local-bib"` or `source: "local-pdf"` and `provider_id: null`. Log the fallback in `plan.yaml.notes`. **Note:** `local-bib` / `local-pdf` only ever appear as `source:` on `candidates.jsonl` rows; they are **not** legal values for `project.yaml.lit_deep.providers` (the config enum is web-retrieval providers only).

**Handoff.** Stage 3 reads `candidates.jsonl` and `plan.yaml.inclusion_keywords` / `exclusion_keywords`.

## Stage 3 — Screen

**Preconditions.** `candidates.jsonl` exists with ≥1 row.

**Procedure.** Dispatch `screener` (one pass per candidate).

1. Score each candidate against the inclusion / exclusion rubric derived from `plan.yaml`. Use a 0–5 integer score; `decision in {include, exclude, maybe}`.
2. Every drop carries a single-sentence `reason`. No silent rejects.
3. When the abstract is missing and the candidate's score is borderline (`maybe`), invoke `skills/scholar-search/SKILL.md` with the candidate's `provider_id` to fetch the per-paper detail (S2 `/paper/<id>?fields=abstract` is the cheapest retry); if that still fails, set `decision=exclude` with `reason="abstract unavailable"`.
4. Emit PRISMA counts: `retrieved`, `after_dedup`, `screened_in`, `screened_out`, plus `excluded_by_reason` histogram.

**Artefact schema — `screening_log.csv`.**

```
id,score,decision,reason,run_id
cand_0001,5,include,"matches q1 method perspective, dataset overlap","..."
cand_0002,1,exclude,"out of year range (1998 < 2018)","..."
```

PRISMA counts append to `plan.yaml.prisma:`.

**Failure mode.** If the abstract fetch fails for every borderline row, surface that explicitly in the chat summary; do not invent abstracts.

**Handoff.** Stage 4 reads only rows with `decision=include`.

## Stage 4 — Cluster

**Preconditions.** `screening_log.csv` exists with ≥1 `include` row.

**Procedure.**

1. Group included candidates into 3–6 clusters by **technical mechanism**, not by application (see `skills/literature-review/SKILL.md` — same family rules as the light command).
2. For each cluster, surface the method lineage, dataset lineage, theory lineage by walking one hop of references (parent works) and one hop of citations (follow-on works) via `skills/scholar-search/SKILL.md`, capped by `depth`.
3. Write `clusters.yaml` and `evidence_map.json`. Every member paper gets a provisional `citation_key` following the `firstauthorYEARkeyword` convention from `skills/literature-review/SKILL.md`.

**Artefact schema — `clusters.yaml`.**

```yaml
run_id: <...>
clusters:
  - id: c1
    name: <short technical-mechanism phrase>
    members: [cand_0001, cand_0007, ...]
    method_lineage: [<citation_key>, ...]      # ancestors via get_paper_references
    dataset_lineage: [<dataset name>, ...]
    theory_lineage: [<concept>, ...]
    why_one_cluster: <one sentence>
```

**Artefact schema — `evidence_map.json`.**

```json
{"cand_0001":{"citation_key":"smith2023foo","cluster":"c1",
              "evidence_ids":["ev_0123"],"source":"arxiv"}}
```

**Failure mode.** If the reference / citation hops return no data (network down, provider 429 after retries, paper id unresolvable), skip the lineage fields (leave `[]`) and note `"lineage: degraded (retrieval unavailable)"` per cluster.

**Handoff.** Stage 5 reads `clusters.yaml` and (for the SWOT inputs) the candidate abstracts from `candidates.jsonl`.

## Stage 5 — Critique

**Preconditions.** `clusters.yaml` exists.

**Procedure.** Dispatch `paper-critic` (one pass per included paper).

1. For each `cluster c`, write `critique/<cluster-id>.md` containing one section per member paper.
2. Each section is a SWOT — **Strengths, Weaknesses, Opportunities, Threats** — plus a mandatory `Delta vs our angle` paragraph that names how *this* project differs.
3. Every SWOT bullet must trace to a section / figure / table / equation of the actual paper (not an abstract paraphrase).
4. In `mode=fast`, skip SWOT bullets that require opening the full PDF; keep only `Delta vs our angle`.

**Concurrency.** Per-paper SWOT writes within a single cluster are independent — dispatch in parallel. Across clusters, serialise (one `critique/<id>.md` write at a time per cluster file to keep the append atomic). Net speedup at typical breadth=6 / 5 papers per cluster: ~5×.

**Artefact schema — `critique/<cluster-id>.md`.**

```markdown
# Cluster <id>: <name>

## <citation_key> — <paper title>

- **Strengths.** … (cite §x / Fig y / Tbl z / Eq w)
- **Weaknesses.** …
- **Opportunities.** …
- **Threats.** …
- **Delta vs our angle.** …

(repeat per member paper)
```

**Failure mode.** If the PDF is unavailable and only the abstract is in hand, mark each bullet `[abstract-only]` and reduce confidence; never invent a section number.

**Handoff.** Stage 6 reads `clusters.yaml`, `critique/*.md`, and `evidence_map.json`.

## Stage 6 — Synthesise

**Preconditions.** `critique/<cluster-id>.md` exists for every cluster.

**Procedure.** Dispatch `literature-reviewer` for drafting, then `evidence-auditor` for the citation audit.

1. Draft `related_work.draft.md` — one paragraph per cluster (or per tight pair of clusters when a single family would otherwise become a wall of citations).
2. Every paragraph must cite ≥ 2 `citation_key`s and end with a contrast sentence that names our angle, backed by at least one `evidence_id`. `citation-guard` and `evidence-consistency` block silently otherwise.
3. Append every synthesised position to `.evidraft/evidence/evidence.jsonl` as `type=note` records with `verified=false` (the auditor flips them later).
4. **Citation-audit pass (mandatory).** Walk every claim in `related_work.draft.md`. For each:
   - Resolve to a `citation_key` (must exist in `references.bib`; when the draft only has a free-text claim, invoke `skills/scholar-search/SKILL.md` with the free-text title to discover the canonical paper and then `skills/bib-manager/SKILL.md` to land the entry under the right key).
   - Resolve to ≥ 1 `evidence_id` (must exist in `evidence.jsonl`).
   - Record the resolution in `citation_audit.json`. If any claim fails to resolve, the audit fails — do **not** proceed; the orchestrator must surface the failing claims and stop.

**Artefact schema — `citation_audit.json`.**

```json
{
  "run_id": "...",
  "total_claims": <int>,
  "resolved": <int>,
  "failed": <int>,
  "claims": [
    {"paragraph": 1, "claim": "...", "citation_keys": ["smith2023foo"],
     "evidence_ids": ["ev_0123"], "status": "resolved",
     "resolver": "resolve_citation | manual", "confidence": 0.91}
  ]
}
```

**Failure mode.** If `skills/scholar-search/SKILL.md` cannot resolve a free-text claim (network down, all providers 429), fall back to manual lookup against `references.bib` + `evidence.jsonl`. If a claim still cannot be resolved, leave the claim in the draft but flag `status: failed` and refuse to mark the run complete.

**Handoff.** The draft is **not** copied into `manuscript/sections/related_work.tex` by this command — that remains the job of `/scholar:paper-review`, which will consume `related_work.draft.md` as its outline.

## PRISMA flow summary (mandatory chat output)

At the end of every run, print to chat:

```
PRISMA flow (run <run_id>)
  candidates_retrieved : <int>
  after_dedup          : <int>
  screened_in          : <int>
  screened_out         : <int>   (top-3 reasons: ...)
  clustered            : <int>   (<N> clusters)
  cited_in_draft       : <int>
  citation_audit       : resolved=<int> failed=<int>
```

If `citation_audit.failed > 0`, refuse to mark the run done and tell the user which claims failed and which stage to re-run.

## Constraints

- Never invent a paper, author, year, venue, DOI, or section number.
- Never blend two providers' metadata into one `candidates.jsonl` row; record one `source` and stash variants under `aliases`.
- `breadth` / `depth` are the only fan-out knobs the user controls. Do not silently exceed them.
- Strong-claim verbs in `related_work.draft.md` need a `\cite{}` or `ev_NNNN` within 30 chars (`citation-guard`).
- The synthesis stage never proceeds past a failed citation audit.

## Done criteria

- All 6 artefacts under `.evidraft/literature/` exist for the current `run_id`.
- `citation_audit.json` reports `failed=0`.
- PRISMA summary printed to chat.
- Chat output recommends `/scholar:paper-review` next (to render the draft into LaTeX) or `/scholar:paper-idea` (to feed the novelty matrix).
