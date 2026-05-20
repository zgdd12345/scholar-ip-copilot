# Deepresearch Progressive-Disclosure Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the monolithic `commands/deepresearch.md` (313 lines) and `skills/deep-literature-review/SKILL.md` (233 lines) into a thin entry-point + 12 `references/` files, so that the agent's working context only carries the stage's spec when it's actually running that stage. Net result: ~140 lines of persistent context (was 546) plus ~50 lines per active stage — the original motivating "progressive disclosure" win.

**Architecture:** Uses the bundle-propagation pipeline landed in `feat/render-skill-bundles` (Path A). Each `references/<topic>.md` file lives next to `SKILL.md`; the bundle copier propagates it to all three host outputs at render time. Content is consolidated (both source files describe Stage N's procedure — references/stage-N-*.md becomes the canonical home) and the source files become thin contracts with markdown links to the references.

**Tech Stack:** Plain Markdown. No new code, no new tests beyond the existing conformance suite (invariant I — bundle propagation — automatically exercises every new references/*.md file).

**Branch:** `refactor/deepresearch-progressive-disclosure` — branch from `feat/render-skill-bundles` (the bundle-propagation feature is a hard prerequisite; if `feat/render-skill-bundles` lands on master first, rebase this branch onto master before merging).

**Open design decisions (defaulted, controller may override):**

1. **Per-stage references/ file naming.** Plan uses `stage-1-frame.md` through `stage-6-synthesise.md`. Alternative would be `01-frame.md` through `06-synthesise.md`. Names with stage tokens are more search-friendly when grepping the codebase.
2. **Auxiliary files.** Plan extracts 6 auxiliary references (prisma-recipe, breadth-depth-budget, resume-protocol, failure-modes, upstream-credits, anti-patterns). One could fold some back into SKILL.md to reduce file count; we keep them separate so each is loadable on demand.
3. **Citation-audit content.** The citation audit is documented in BOTH the command's Stage 6 section AND the skill's "Citation audit rules" section. Plan consolidates it into `references/stage-6-synthesise.md` (the stage where it fires) — not its own file.

---

## File Structure

**New files (12 references):**

```
plugins/scholar-ip/skills/deep-literature-review/references/
├── stage-1-frame.md           ~45 lines   procedure + plan.yaml schema + failure mode
├── stage-2-retrieve.md        ~55 lines   procedure + candidates.jsonl schema + dedup + concurrency
├── stage-3-screen.md          ~45 lines   procedure + screening_log.csv schema + PRISMA counts
├── stage-4-cluster.md         ~45 lines   procedure + clusters.yaml + evidence_map.json schemas
├── stage-5-critique.md        ~50 lines   procedure + SWOT template + concurrency
├── stage-6-synthesise.md      ~60 lines   procedure + citation_audit.json schema + audit rules
├── breadth-depth-budget.md    ~25 lines   knob table + budget_log behaviour + mode semantics
├── prisma-recipe.md           ~30 lines   counts formula + chat-output template + citation-guard
├── resume-protocol.md         ~20 lines   resume_from rules + verification gates
├── failure-modes.md           ~35 lines   degradation catalog by stage
├── upstream-credits.md        ~15 lines   STORM / GPT-Researcher / dzhng / Open DR / open-paper-machine
└── anti-patterns.md           ~20 lines   what not to do
```

**Modified files:**

```
plugins/scholar-ip/commands/deepresearch.md         313 → ~70 lines   (frontmatter unchanged; body becomes contract + stage map + links)
plugins/scholar-ip/skills/deep-literature-review/SKILL.md   233 → ~105 lines  (frontmatter unchanged; body becomes entry + stage map + quality checklist)
```

**Files explicitly NOT touched:**

- `plugins/scholar-ip/skills/using-deep-research/SKILL.md` — the lightweight entry-point skill; its `references/example.md` from Path A Task 6 stays. The agent reads this BEFORE deciding whether to run /scholar:deepresearch.
- `plugins/scholar-ip/skills/scholar-search/SKILL.md`, `bib-manager/SKILL.md`, etc. — referenced by deepresearch but not the subject of this refactor.
- Any source code under `packages/` — pure content move, no Python changes.
- Tests under `tests/` — invariant I (bundle propagation, landed in Path A Task 5) automatically covers every new references/ file.

---

## Task 0: Branch + baseline

**Files:** none (git ops only)

- [ ] **Step 1: Confirm starting state**

```bash
cd /Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot
git branch --show-current
git --no-pager log --oneline -1
git --no-pager status --short
```

Expected: clean tree on `feat/render-skill-bundles` at `eefef20` (or later — any commit in the Path A chain is fine as long as the bundle copier is present). If on a different branch, STOP and confirm with controller.

- [ ] **Step 2: Verify Path A bundle propagation is present**

```bash
test -f packages/adapters/_shared/bundle.py && echo "OK: bundle helper exists" || echo "MISSING: branch lacks Path A prerequisite"
.venv/bin/python -m pytest tests/test_adapter_conformance.py::test_invariant_i_bundle_resources_propagated -v 2>&1 | tail -3
```

Expected: `OK: bundle helper exists` and the invariant I test passes. If either fails, this plan cannot proceed; report and stop.

- [ ] **Step 3: Create branch**

```bash
git checkout -b refactor/deepresearch-progressive-disclosure
```

Expected: `Switched to a new branch 'refactor/deepresearch-progressive-disclosure'`.

- [ ] **Step 4: Snapshot baseline line counts**

```bash
wc -l plugins/scholar-ip/commands/deepresearch.md plugins/scholar-ip/skills/deep-literature-review/SKILL.md
```

Record the output verbatim in the report. Expected baseline: `313` and `233` lines. These are the "before" numbers used to verify the refactor lands within targets (~70 and ~105 lines respectively).

- [ ] **Step 5: Run full test + render baseline**

```bash
.venv/bin/python -m pytest tests/ -q 2>&1 | tail -3
make render 2>&1 | tail -3
```

Expected: all tests pass; render emits three host outputs cleanly. Record the test count.

- [ ] **Step 6: Commit the plan onto the branch**

```bash
git add docs/superpowers/plans/2026-05-19-deepresearch-progressive-disclosure.md
git commit -m "docs(deepresearch): import progressive-disclosure refactor plan"
```

Expected: one commit, one new file.

---

## Task 1: Extract all 6 stage references

**Files:**
- Create: `plugins/scholar-ip/skills/deep-literature-review/references/stage-1-frame.md`
- Create: `plugins/scholar-ip/skills/deep-literature-review/references/stage-2-retrieve.md`
- Create: `plugins/scholar-ip/skills/deep-literature-review/references/stage-3-screen.md`
- Create: `plugins/scholar-ip/skills/deep-literature-review/references/stage-4-cluster.md`
- Create: `plugins/scholar-ip/skills/deep-literature-review/references/stage-5-critique.md`
- Create: `plugins/scholar-ip/skills/deep-literature-review/references/stage-6-synthesise.md`

This task creates ALL six stage references in a single task because (a) they share an authoring pattern and (b) source files remain valid (with duplicate content) until Tasks 3/4 thin them. After Task 1, the system renders cleanly with extra files; later tasks will collapse the redundancy.

Each new file is the **consolidated** version of that stage from BOTH source files (the command's Stage section + the skill's Procedure section). When the two sources disagree, the command's text wins (it's more detailed). The skill's terse summaries are absorbed.

- [ ] **Step 1: Create the references/ directory**

```bash
cd /Users/fsm/project/MyProject/agentplugin/scholar-ip-copilot
mkdir -p plugins/scholar-ip/skills/deep-literature-review/references
ls plugins/scholar-ip/skills/deep-literature-review/references/
```

Expected: directory exists and is empty (or contains only files we are about to write).

- [ ] **Step 2: Write `references/stage-1-frame.md`**

Path: `plugins/scholar-ip/skills/deep-literature-review/references/stage-1-frame.md`

Content (exactly):

```markdown
# Stage 1 — Frame

**Preconditions.** `.evidraft/scope/*.md` exists (the `scope-required` hook enforces this). `topic` is set by user input or by `project.yaml`.

**Procedure.**

1. Read `.evidraft/project.yaml` (`field`, `target_venue`, `topic`) and the most recent `.evidraft/scope/*.md`.
2. Derive a research brief: research question, sub-questions, inclusion keywords, exclusion keywords, year window, venue allow-list, language allow-list.
3. Expand sub-queries up to `breadth` (default 6). One sub-query per perspective (method, dataset, theory, application, evaluation, critique). Modelled on **STORM**'s perspective-guided retrieval — see [upstream-credits.md](upstream-credits.md).
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

**Failure mode.** No MCP needed at this stage. If `scope-required` blocks, stop and ask the user to run `/scholar:brainstorming`. See [failure-modes.md](failure-modes.md) for the full degradation catalog.

**Handoff.** Stage 2 reads `plan.yaml` only.
```

- [ ] **Step 3: Write `references/stage-2-retrieve.md`**

Path: `plugins/scholar-ip/skills/deep-literature-review/references/stage-2-retrieve.md`

Content (exactly):

```markdown
# Stage 2 — Retrieve

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
 "authors":["..."],"doi":"...",
 "arxiv_id":"2308.09534",                     // optional convenience field; null when not arXiv
 "source":"arxiv|semantic-scholar|openalex|local-bib|local-pdf|llm-seed-unverified|superseded",
 "provider_id":"arxiv:2401.01234","sub_query_ids":["q1","q3"],
 "depth":0,"aliases":[{"source":"openalex","provider_id":"W..."}],
 "run_id":"...","verified":true,"confidence":"high|medium|low",
 "verify_note":"how the row's metadata was verified"}
```

**Cross-sub-query dedup** is mandatory: a candidate retrieved by both `q1` and `q3` collapses to ONE row whose `sub_query_ids` is the union `["q1", "q3"]`. The dedup key is DOI first, then (normalised title, first-author surname, year). Never emit two rows that would both `cite` the same paper.

The `source` enum carries provenance, not config: in addition to the web-retrieval providers, it accepts `local-bib` / `local-pdf` (when MCP/network unavailable; see [failure-modes.md](failure-modes.md)), `llm-seed-unverified` (initial LLM seed before WebSearch verification — every such row MUST have `verified: false`), and `superseded` (audit trail for rows replaced by a later, verified row).

**Failure mode.** Network/provider degradation falls back to local `.evidraft/literature/references.bib` and `references/` / `papers/` PDFs — full rules in [failure-modes.md#stage-2-retrieve](failure-modes.md). Note: `local-bib` / `local-pdf` only ever appear as `source:` on `candidates.jsonl` rows; they are **not** legal values for `project.yaml.lit_deep.providers` (the config enum is web-retrieval providers only).

**Handoff.** Stage 3 reads `candidates.jsonl` and `plan.yaml.inclusion_keywords` / `exclusion_keywords`.
```

- [ ] **Step 4: Write `references/stage-3-screen.md`**

Path: `plugins/scholar-ip/skills/deep-literature-review/references/stage-3-screen.md`

Content (exactly):

```markdown
# Stage 3 — Screen

**Preconditions.** `candidates.jsonl` exists with ≥1 row.

**Procedure.** Dispatch `screener` (one pass per candidate). The discipline is borrowed from PRISMA-flow tooling (ASReview, Rayyan, open-paper-machine — see [upstream-credits.md](upstream-credits.md)): every drop has a reason; no silent rejects.

1. Score each candidate against the inclusion / exclusion rubric derived from `plan.yaml`. Use a 0–5 integer score; `decision in {include, include_with_caveat, exclude, maybe}`.
2. Every drop carries a single-sentence `reason`. No silent rejects.
3. `include_with_caveat` is for rows that are mechanistically relevant but match an exclusion keyword (e.g. a video-detection paper whose aux-branch trick is the relevant pattern but the modality is excluded). When used, `decision=include_with_caveat` AND the `caveat` column carries a one-sentence "cite as inspiration in Method, not as direct baseline" guidance. These rows still reach Stage 4 clustering but are tagged for non-baseline use only.
4. When the abstract is missing and the candidate's score is borderline (`maybe`), invoke `skills/scholar-search/SKILL.md` with the candidate's `provider_id` to fetch the per-paper detail (S2 `/paper/<id>?fields=abstract` is the cheapest retry); if that still fails, set `decision=exclude` with `reason="abstract unavailable"`.
5. Emit PRISMA counts: `retrieved`, `after_dedup`, `screened_in`, `screened_in_with_caveat`, `screened_out`, plus `excluded_by_reason` histogram. See [prisma-recipe.md](prisma-recipe.md) for the canonical formula.

**Artefact schema — `screening_log.csv`.**

```
id,score,decision,reason,caveat,run_id
cand_0001,5,include,"matches q1 method perspective, dataset overlap",,dr-...
cand_0002,1,exclude,"out of year range (1998 < 2018)",,dr-...
cand_0003,3,include_with_caveat,"mechanism matches q1 but modality is video","cite as inspiration in Method, not as direct baseline",dr-...
```

`caveat` is empty for `include` / `exclude` / `maybe`; non-empty only for `include_with_caveat`.

PRISMA counts append to `plan.yaml.prisma:`.

**Failure mode.** If the abstract fetch fails for every borderline row, surface that explicitly in the chat summary; do not invent abstracts. Full degradation catalog in [failure-modes.md](failure-modes.md).

**Handoff.** Stage 4 reads only rows with `decision=include` or `decision=include_with_caveat`.
```

- [ ] **Step 5: Write `references/stage-4-cluster.md`**

Path: `plugins/scholar-ip/skills/deep-literature-review/references/stage-4-cluster.md`

Content (exactly):

```markdown
# Stage 4 — Cluster

**Preconditions.** `screening_log.csv` exists with ≥1 `include` row.

**Procedure.**

1. Group included candidates into 3–6 clusters by **technical mechanism**, not by application (see `../../literature-review/SKILL.md` — same family rules as the light command).
2. For each cluster, surface the method lineage, dataset lineage, theory lineage by walking one hop of references (parent works) and one hop of citations (follow-on works) via `skills/scholar-search/SKILL.md`, capped by `depth`.
3. Write `clusters.yaml` and `evidence_map.json`. Every member paper gets a provisional `citation_key` following the `firstauthorYEARkeyword` convention from `../../literature-review/SKILL.md`.

**Artefact schema — `clusters.yaml`.**

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
- 3–6 clusters per run; a 7th cluster is a signal to collapse two existing ones.
- Every paper belongs to at most one cluster (borderline cases get a secondary cluster note inside the cluster file).
- Cluster names describe **technical mechanism**, not application ("DETR-style set prediction" not "object detection").

**Artefact schema — `evidence_map.json`.**

```json
{"cand_0001":{"citation_key":"smith2023foo","cluster":"c1",
              "evidence_ids":["ev_0123"],"source":"arxiv"}}
```

**Failure mode.** If the reference / citation hops return no data (network down, provider 429 after retries, paper id unresolvable), skip the lineage fields (leave `[]`) and note `"lineage: degraded (retrieval unavailable)"` per cluster. Full catalog in [failure-modes.md](failure-modes.md).

**Handoff.** Stage 5 reads `clusters.yaml` and (for the SWOT inputs) the candidate abstracts from `candidates.jsonl`.
```

- [ ] **Step 6: Write `references/stage-5-critique.md`**

Path: `plugins/scholar-ip/skills/deep-literature-review/references/stage-5-critique.md`

Content (exactly):

```markdown
# Stage 5 — Critique

**Preconditions.** `clusters.yaml` exists.

**Procedure.** Dispatch `paper-critic` (one pass per included paper). Modelled on the per-section sub-agent pattern used by **GPT-Researcher** and the structured research-brief style of **Open Deep Research** — see [upstream-credits.md](upstream-credits.md).

1. For each `cluster c`, write `critique/<cluster-id>.md` containing one section per member paper.
2. Each section is a SWOT — **Strengths, Weaknesses, Opportunities, Threats** — plus a mandatory `Delta vs our angle` paragraph that names how *this* project differs.
3. Every SWOT bullet must trace to a section / figure / table / equation of the actual paper (not an abstract paraphrase).
4. In `mode=fast`, skip SWOT bullets that require opening the full PDF; keep only `Delta vs our angle`. See [breadth-depth-budget.md](breadth-depth-budget.md) for the full mode semantics.

**Concurrency.** Per-paper SWOT writes within a single cluster are independent — dispatch in parallel. Across clusters, serialise (one `critique/<id>.md` write at a time per cluster file to keep the append atomic). Net speedup at typical breadth=6 / 5 papers per cluster: ~5×.

**Per-paper SWOT template — `critique/<cluster-id>.md`.**

```markdown
# Cluster <id>: <name>

## <citation_key> — <paper title>

- **Strengths.**     - <bullet> (Section X.Y / Fig N / Tbl M / Eq K)
- **Weaknesses.**    - <bullet> (Section X.Y / ...)
- **Opportunities.** - <bullet> (what gap this opens for us)
- **Threats.**       - <bullet> (what blocks our angle if this paper is right)
- **Delta vs our angle.** <one paragraph; ends with the appended evidence id>

(repeat per member paper)
```

Rules:
- Strengths / Weaknesses describe the paper itself; Opportunities / Threats describe the paper *as it bears on our project*.
- Every bullet cites a section, figure, table, or equation. Abstract paraphrase is not a citation.
- `Delta vs our angle` is mandatory. If you cannot write it, the paper does not belong in related work.
- `mode=fast` drops bullets that require the full PDF; mark them `[skipped — fast mode]`. Abstract-only bullets are tagged `[abstract-only]`.

**Failure mode.** If the PDF is unavailable and only the abstract is in hand, mark each bullet `[abstract-only]` and reduce confidence; never invent a section number. Full catalog in [failure-modes.md](failure-modes.md).

**Handoff.** Stage 6 reads `clusters.yaml`, `critique/*.md`, and `evidence_map.json`.
```

- [ ] **Step 7: Write `references/stage-6-synthesise.md`**

Path: `plugins/scholar-ip/skills/deep-literature-review/references/stage-6-synthesise.md`

Content (exactly):

```markdown
# Stage 6 — Synthesise + audit

**Preconditions.** `critique/<cluster-id>.md` exists for every cluster.

**Procedure.** Dispatch `literature-reviewer` for drafting, then `evidence-auditor` for the citation audit.

1. Draft `related_work.draft.md` — one paragraph per cluster (or per tight pair of clusters when a single family would otherwise become a wall of citations).
2. Every paragraph must cite ≥ 2 `citation_key`s and end with a contrast sentence that names our angle, backed by at least one `evidence_id`. `citation-guard` and `evidence-consistency` block silently otherwise.
3. Append every synthesised position to `.evidraft/evidence/evidence.jsonl` as `type=note` records with `verified=false` (the auditor flips them later).
4. **Citation-audit pass (mandatory).** Walk every claim in `related_work.draft.md`. For each:
   - Resolve to a `citation_key` (must exist in `references.bib`; when the draft only has a free-text claim, invoke `skills/scholar-search/SKILL.md` with the free-text title to discover the canonical paper and then `skills/bib-manager/SKILL.md` to land the entry under the right key).
   - Resolve to ≥ 1 `evidence_id` (must exist in `evidence.jsonl`).
   - Record the resolution in `citation_audit.json`. If any claim fails to resolve, the audit fails — do **not** proceed; the orchestrator must surface the failing claims and stop.

**Citation audit rules.**

For every claim in `related_work.draft.md`:

1. Resolve to one or more `citation_key`s — each must already exist in `.evidraft/literature/references.bib`. For free-text matches, use the `scholar-search` skill's resolution recipe (query a candidate title against arXiv/Semantic Scholar/OpenAlex via `WebSearch` + `WebFetch`, then map to an existing BibTeX entry); otherwise look up by hand.
2. Resolve to one or more `evidence_id`s — each must already exist in `.evidraft/evidence/evidence.jsonl`.
3. Append a row to `citation_audit.json.claims[]` with `paragraph, claim, citation_keys, evidence_ids, status, resolver, confidence`.
4. If `status=failed` for any claim, the run does not complete. Surface the failing claims and tell the user which stage to re-run.

Strong-claim verbs in the draft (SOTA, novel, first, outperform, significant, superior, …) still require a `\cite{}` or `ev_NNNN` within 30 chars — the `citation-guard` hook will block the write otherwise.

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

**Failure mode.** If `skills/scholar-search/SKILL.md` cannot resolve a free-text claim (network down, all providers 429), fall back to manual lookup against `references.bib` + `evidence.jsonl`. If a claim still cannot be resolved, leave the claim in the draft but flag `status: failed` and refuse to mark the run complete. Full catalog in [failure-modes.md](failure-modes.md).

**Handoff.** The draft is **not** copied into `manuscript/sections/related_work.tex` by this command — that remains the job of `/scholar:paper-review`, which will consume `related_work.draft.md` as its outline.
```

- [ ] **Step 8: Verify all 6 references render correctly**

```bash
ls plugins/scholar-ip/skills/deep-literature-review/references/
wc -l plugins/scholar-ip/skills/deep-literature-review/references/*.md
```

Expected: exactly 6 files (stage-1-frame.md through stage-6-synthesise.md). Line counts within +/- 10 of the per-file estimates above. If any file is dramatically off (>2x or <0.5x the estimate), the implementer over- or under-wrote — review before continuing.

- [ ] **Step 9: Render and verify bundle propagation**

```bash
make render 2>&1 | tail -5
ls .claude/plugins/scholar-ip/skills/deep-literature-review/references/
ls .codex/plugins/scholar/skills/scholar-skill-deep-literature-review/references/
ls .opencode/skills/deep-literature-review/references/
```

Expected: all three host outputs each show the same 6 stage-*.md files (plus any pre-existing references the source already had — none in deep-literature-review/ as of master).

- [ ] **Step 10: Run the test suite to confirm invariant I passes with the new files**

```bash
.venv/bin/python -m pytest tests/ -q 2>&1 | tail -3
```

Expected: all tests pass.

- [ ] **Step 11: Commit**

```bash
git add plugins/scholar-ip/skills/deep-literature-review/references/
git commit -m "refactor(deepresearch): extract 6 stage references

Each stage of the 6-stage pipeline gets its own references/*.md file
containing the procedure, schemas, concurrency notes, and failure mode.
Content is consolidated from both commands/deepresearch.md and
skills/deep-literature-review/SKILL.md (where the command had more detail,
that text wins).

Source files (command + SKILL.md) are not yet thinned — that lands in
Tasks 3/4. Until then there is intentional duplication; tests still pass
because both copies of each stage's text are valid markdown."
```

Expected: one commit, 6 new files.

---

## Task 2: Extract 6 auxiliary references

**Files:**
- Create: `plugins/scholar-ip/skills/deep-literature-review/references/breadth-depth-budget.md`
- Create: `plugins/scholar-ip/skills/deep-literature-review/references/prisma-recipe.md`
- Create: `plugins/scholar-ip/skills/deep-literature-review/references/resume-protocol.md`
- Create: `plugins/scholar-ip/skills/deep-literature-review/references/failure-modes.md`
- Create: `plugins/scholar-ip/skills/deep-literature-review/references/upstream-credits.md`
- Create: `plugins/scholar-ip/skills/deep-literature-review/references/anti-patterns.md`

- [ ] **Step 1: Write `references/breadth-depth-budget.md`**

Path: `plugins/scholar-ip/skills/deep-literature-review/references/breadth-depth-budget.md`

Content (exactly):

```markdown
# Breadth / depth budget

| Knob | Default | Meaning | Hard ceiling |
|---|---|---|---|
| `breadth` | 6 | max sub-queries at Stage 1; multiplies into per-query `top_k = breadth * 5` at Stage 2; max clusters at Stage 4 capped at `min(6, breadth)`. | total candidates ≤ `breadth * 50`. |
| `depth` | 2 | recursion depth for `get_paper_references` / `get_paper_citations`; `depth=1` skips the lineage hop entirely. | `depth ≤ 3` in `full` mode; `depth ≤ 2` in `fast` mode. |

`mode=fast` halves both, rounded up, and skips Stage 5 SWOT bullets that require the full PDF. The budget is tracked in `plan.yaml.budget_log[]`; over-budget fan-outs are refused and logged.

This is the same control surface used by **dzhng/deep-research** — two knobs, both user-facing, both visible in the artefact. See [upstream-credits.md](upstream-credits.md) for the full credit list.
```

- [ ] **Step 2: Write `references/prisma-recipe.md`**

Path: `plugins/scholar-ip/skills/deep-literature-review/references/prisma-recipe.md`

Content (exactly):

```markdown
# PRISMA recipe + chat output

## Counts formula

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

`excluded_by_reason` is a histogram of the `reason` column from `screening_log.csv`.

## Mandatory chat output

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

## Citation-guard interaction

Strong-claim verbs in `related_work.draft.md` (SOTA, novel, first, outperform, significant, superior, …) need a `\cite{}` or `ev_NNNN` within 30 chars — the `citation-guard` hook blocks the write otherwise. The hook is automatic; the PRISMA recipe does not invoke it directly but its `cited_in_draft` count will be wrong if the draft is missing citations.
```

- [ ] **Step 3: Write `references/resume-protocol.md`**

Path: `plugins/scholar-ip/skills/deep-literature-review/references/resume-protocol.md`

Content (exactly):

```markdown
# Resume protocol

`resume_from=<stage>` skips every earlier stage. The orchestrator must:

1. Locate the latest `run_id` in `plan.yaml`.
2. Verify the artefacts of every stage strictly before `<stage>` exist and parse. If any is missing or malformed, refuse and name the missing artefact.
3. Restore `breadth` / `depth` from `plan.yaml`, not from user input. See [breadth-depth-budget.md](breadth-depth-budget.md) for the knob semantics.
4. Append, never overwrite — every artefact carries the same `run_id` so multiple runs in the same project can be diffed.
```

- [ ] **Step 4: Write `references/failure-modes.md`**

Path: `plugins/scholar-ip/skills/deep-literature-review/references/failure-modes.md`

Content (exactly):

```markdown
# Failure modes (degradation catalog)

Every stage has a defined degradation mode. The pipeline NEVER silently invents data on failure — it either falls back to a documented degraded path or stops the run.

| Stage | Trigger | Degradation | Marker |
|---|---|---|---|
| Stage 1 | `scope-required` hook blocks | Stop; ask user to run `/scholar:brainstorming` | (hook log) |
| Stage 2 | `WebFetch` unavailable / all providers 429 / no network | Fall back to local `.evidraft/literature/references.bib` + PDFs under `references/` / `papers/`. Each fallback row uses `source: "local-bib"` or `source: "local-pdf"`. | `plan.yaml.notes` records the fallback |
| Stage 3 | Borderline row's abstract fetch fails | Set `decision=exclude` with `reason="abstract unavailable"`. Do NOT invent abstracts. | `screening_log.csv` reason column |
| Stage 3 | All borderline abstract fetches fail | Surface to chat summary; do not invent abstracts. | (chat output) |
| Stage 4 | References / citations hops return no data | Skip lineage fields (leave `[]`); note `"lineage: degraded (retrieval unavailable)"` per cluster. Cluster membership still produced. | `clusters.yaml` per-cluster note |
| Stage 5 | PDF unavailable, only abstract in hand | Mark each SWOT bullet `[abstract-only]`; reduce confidence; NEVER invent section numbers. | bullet tag |
| Stage 6 | Free-text citation resolution fails | Fall back to manual lookup against `references.bib` + `evidence.jsonl`. If still unresolvable, flag `status: failed` in `citation_audit.json` and refuse to mark the run complete. | `citation_audit.json.claims[].status` |
| Budget | Fan-out exceeds `breadth * 50` or other ceiling | Refuse the fan-out; log to `plan.yaml.budget_log[]`; surface to user. | `plan.yaml.budget_log` |

**Universal rules:**
- Never invent a paper, author, year, venue, DOI, or section number.
- Never blend two providers' metadata into one row.
- Every degraded artefact must carry its degradation marker so downstream stages can detect upstream weakness.
```

- [ ] **Step 5: Write `references/upstream-credits.md`**

Path: `plugins/scholar-ip/skills/deep-literature-review/references/upstream-credits.md`

Content (exactly):

```markdown
# Upstream credits

Idea-level borrowings only; no upstream code is imported.

- **STORM** — perspective-guided retrieval; we borrow the per-perspective sub-query split at Stage 1.
- **GPT-Researcher** — per-section sub-agent dispatch; we borrow the one-sub-agent-per-stage pattern.
- **dzhng/deep-research** — breadth/depth knobs; we expose the same two user-facing controls.
- **Open Deep Research** — structured research brief; we adopt the explicit `plan.yaml` artefact instead of an implicit prompt.
- **open-paper-machine** — PRISMA-style screening log shape; we adopt `id, score, decision, reason` as the canonical CSV.
- **ASReview, Rayyan, open-paper-machine** — PRISMA discipline (every drop has a reason; no silent rejects) inspires Stage 3.
```

- [ ] **Step 6: Write `references/anti-patterns.md`**

Path: `plugins/scholar-ip/skills/deep-literature-review/references/anti-patterns.md`

Content (exactly):

```markdown
# Anti-patterns

- Running `/scholar:deepresearch` when `/scholar:paper-lit` would suffice. The deep command is for survey-grade reviews; light projects pay a real cost in time and tokens.
- Blending metadata from two providers into one `candidates.jsonl` row.
- Re-scoring screened candidates after seeing later ones.
- Writing a SWOT bullet that paraphrases the abstract.
- Skipping `Delta vs our angle` for "obviously different" papers.
- Marking a run done while `citation_audit.failed > 0`.
- Editing `manuscript/sections/related_work.tex` directly — that file is owned by `/scholar:paper-review`, which consumes `related_work.draft.md` as its outline.
- Silently exceeding the `breadth * 50` candidate ceiling instead of refusing and logging — see [breadth-depth-budget.md](breadth-depth-budget.md).
- Inventing a section / figure / table / equation reference in a SWOT bullet because the PDF was unavailable — use `[abstract-only]` instead. See [failure-modes.md](failure-modes.md).
```

- [ ] **Step 7: Verify the 6 auxiliary references**

```bash
ls plugins/scholar-ip/skills/deep-literature-review/references/
wc -l plugins/scholar-ip/skills/deep-literature-review/references/*.md
```

Expected: 12 files total (6 stage-*.md from Task 1 + 6 aux files). Line counts roughly: 20, 25, 30, 20, 35, 15. Stage files unchanged from Task 1.

- [ ] **Step 8: Render and verify**

```bash
make render 2>&1 | tail -5
ls .opencode/skills/deep-literature-review/references/ | wc -l
```

Expected: render clean, the opencode references dir contains 12 files. Sanity-check the other two adapters similarly.

- [ ] **Step 9: Run tests**

```bash
.venv/bin/python -m pytest tests/ -q 2>&1 | tail -3
```

Expected: all pass.

- [ ] **Step 10: Commit**

```bash
git add plugins/scholar-ip/skills/deep-literature-review/references/
git commit -m "refactor(deepresearch): extract 6 auxiliary references

PRISMA recipe, breadth/depth budget table, resume protocol, failure
modes catalog, upstream credits, anti-patterns. Each lives in its own
references/*.md so the agent loads only what's relevant to the current
stage.

Source files (command + SKILL.md) still contain the original copies —
those are thinned in Tasks 3-4."
```

Expected: one commit, 6 new files. Combined with Task 1, the references/ directory has 12 files.

---

## Task 3: Thin `skills/deep-literature-review/SKILL.md` to ~105 lines

**Files:**
- Modify: `plugins/scholar-ip/skills/deep-literature-review/SKILL.md`

The current SKILL.md (233 lines) becomes a thin entry that maps to the references/ files. The frontmatter is preserved. The body becomes:
1. When-to-use (kept)
2. Inputs (kept)
3. Outputs (kept)
4. **Stage map** (new — links to each `references/stage-N-*.md`)
5. **Auxiliary map** (new — links to PRISMA, budget, resume, failures, credits, anti-patterns)
6. Quality checklist (kept — it's a top-level summary, useful at entry)

Everything else (procedure detail, schemas, SWOT template, failure mode catalog, anti-patterns, upstream credits) is removed because it now lives in references/.

- [ ] **Step 1: Read the current SKILL.md to confirm line numbers**

```bash
wc -l plugins/scholar-ip/skills/deep-literature-review/SKILL.md
```

Expected: `233`. If different, re-confirm with controller before proceeding.

- [ ] **Step 2: Rewrite the body**

The frontmatter (lines 1-34) stays unchanged. The body (lines 35-233) is replaced wholesale. Open `plugins/scholar-ip/skills/deep-literature-review/SKILL.md`, leave lines 1-34 alone, and replace everything from line 35 onward with this exact content:

```markdown
# deep-literature-review

## When to use

Pull this skill whenever `/scholar:deepresearch` runs (or when resuming one of its stages). The light single-pass `/scholar:paper-lit` keeps its own skill (`../literature-review/SKILL.md`); this one is the heavyweight cousin. The two are not interchangeable: `literature-review` defines the citation-key convention, BibTeX hygiene, and method-family clustering that *both* commands share; `deep-literature-review` adds the 6-stage pipeline, the PRISMA screening log, the per-paper SWOT, and the citation audit.

Retrieval is delegated to the `scholar-search` skill (`../scholar-search/SKILL.md`), which calls the built-in `WebSearch` / `WebFetch`. When network access is unavailable or the session is offline, every stage degrades to local PDFs + BibTeX — see [references/failure-modes.md](references/failure-modes.md).

## How to navigate this skill

This SKILL.md is the entry; the **detail for each stage** lives in `references/`. Load only the stage you are running:

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
```

After the edit, the file should be roughly 105 lines (34 frontmatter + ~70 body). Verify:

```bash
wc -l plugins/scholar-ip/skills/deep-literature-review/SKILL.md
```

Expected: 100-110 lines. If outside that range, the edit was wrong — read the file and check.

- [ ] **Step 3: Render and verify**

```bash
make render 2>&1 | tail -5
```

Expected: clean render. The rendered SKILL.md files in each host output should match the thinned source.

- [ ] **Step 4: Run tests**

```bash
.venv/bin/python -m pytest tests/ -q 2>&1 | tail -3
```

Expected: all pass.

- [ ] **Step 5: Smoke-check that references/ files are still propagated**

```bash
ls .claude/plugins/scholar-ip/skills/deep-literature-review/references/ | wc -l
ls .codex/plugins/scholar/skills/scholar-skill-deep-literature-review/references/ | wc -l
ls .opencode/skills/deep-literature-review/references/ | wc -l
```

Expected: all three report `12` (6 stages + 6 aux).

- [ ] **Step 6: Commit**

```bash
git add plugins/scholar-ip/skills/deep-literature-review/SKILL.md
git commit -m "refactor(deepresearch): thin deep-literature-review/SKILL.md to entry + map

233 → ~105 lines. Body now contains: when-to-use, inputs, outputs, stage
map (links to references/stage-N-*.md), auxiliary map (links to PRISMA,
budget, resume, failures, credits, anti-patterns), and the quality
checklist.

Procedure detail, schemas, SWOT template, failure catalog, upstream
credits, and anti-patterns are all in references/ now (Tasks 1-2).
This SKILL.md only loads when /scholar:deepresearch fires; references
load on demand per stage."
```

Expected: one commit, 1 file modified (~130 line reduction).

---

## Task 4: Thin `commands/deepresearch.md` to ~70 lines

**Files:**
- Modify: `plugins/scholar-ip/commands/deepresearch.md`

The command (313 lines) becomes the executable contract:
1. Frontmatter (kept; lightly trim the `description` if it duplicates the body)
2. Title + 2-paragraph intro (kept)
3. **Stage map** (new — links to the SKILL.md's reference table OR directly to references/stage-N-*.md)
4. **Resume protocol** — one-line pointer to `references/resume-protocol.md`
5. **Constraints** (kept — terse, command-level safety rules)
6. **Done criteria** (kept — terse)

Everything else (per-stage procedure + schemas, PRISMA flow output, full failure modes) is removed because it lives in references/ via the SKILL.md.

- [ ] **Step 1: Confirm baseline**

```bash
wc -l plugins/scholar-ip/commands/deepresearch.md
```

Expected: `313` (unchanged from Task 0). If different, re-confirm with controller.

- [ ] **Step 2: Rewrite the body**

The frontmatter (lines 1-63) stays unchanged. The body (lines 64-313) is replaced wholesale. Open `plugins/scholar-ip/commands/deepresearch.md`, leave lines 1-63 alone, and replace everything from line 64 onward with this exact content:

```markdown
# /scholar:deepresearch

Heavyweight 6-stage literature workflow: **Frame → Retrieve → Screen → Cluster → Critique → Synthesise**. Complements `/scholar:paper-lit` (which stays the light single-pass command); does **not** replace it. Every stage emits a durable artefact under `.evidraft/literature/` so partial runs are resumable via `resume_from`.

All retrieval flows through the `scholar-search` skill (`../skills/scholar-search/SKILL.md`), which drives host-native `WebSearch` + `WebFetch` against arXiv / Semantic Scholar / OpenAlex. When the host has no network, every stage degrades to local PDFs + BibTeX — see `../skills/deep-literature-review/references/failure-modes.md`.

The orchestration is owned by `deep-research-orchestrator`; this command is the executable contract. **Procedure detail lives in `../skills/deep-literature-review/SKILL.md`** which links out to one file per stage under `references/`.

## Stage map

| # | Stage | Artefact | Procedure |
|---|---|---|---|
| 1 | Frame | `plan.yaml` | [stage-1-frame](../skills/deep-literature-review/references/stage-1-frame.md) |
| 2 | Retrieve | `candidates.jsonl` | [stage-2-retrieve](../skills/deep-literature-review/references/stage-2-retrieve.md) |
| 3 | Screen | `screening_log.csv` | [stage-3-screen](../skills/deep-literature-review/references/stage-3-screen.md) |
| 4 | Cluster | `clusters.yaml`, `evidence_map.json` | [stage-4-cluster](../skills/deep-literature-review/references/stage-4-cluster.md) |
| 5 | Critique | `critique/<id>.md` | [stage-5-critique](../skills/deep-literature-review/references/stage-5-critique.md) |
| 6 | Synthesise | `related_work.draft.md`, `citation_audit.json` | [stage-6-synthesise](../skills/deep-literature-review/references/stage-6-synthesise.md) |

Budget knobs (`breadth`, `depth`, `mode`): see [breadth-depth-budget](../skills/deep-literature-review/references/breadth-depth-budget.md).
Resume protocol (`resume_from=<stage>`): see [resume-protocol](../skills/deep-literature-review/references/resume-protocol.md).
PRISMA flow + final chat output: see [prisma-recipe](../skills/deep-literature-review/references/prisma-recipe.md).
Failure / degradation catalog: see [failure-modes](../skills/deep-literature-review/references/failure-modes.md).

## Constraints

- Never invent a paper, author, year, venue, DOI, or section number.
- Never blend two providers' metadata into one `candidates.jsonl` row; record one `source` and stash variants under `aliases`.
- `breadth` / `depth` are the only fan-out knobs the user controls. Do not silently exceed them.
- Strong-claim verbs in `related_work.draft.md` need a `\cite{}` or `ev_NNNN` within 30 chars (`citation-guard`).
- The synthesis stage never proceeds past a failed citation audit.

## Done criteria

- All 6 artefacts under `.evidraft/literature/` exist for the current `run_id`.
- `citation_audit.json` reports `failed=0`.
- PRISMA summary printed to chat (format in [prisma-recipe](../skills/deep-literature-review/references/prisma-recipe.md)).
- Chat output recommends `/scholar:paper-review` next (to render the draft into LaTeX) or `/scholar:paper-idea` (to feed the novelty matrix).
```

After the edit, the file should be roughly 70-75 lines (63 frontmatter + ~10-15 body). Verify:

```bash
wc -l plugins/scholar-ip/commands/deepresearch.md
```

Expected: 70-80 lines. If outside that range, the edit was wrong — read the file and check.

- [ ] **Step 3: Render and verify**

```bash
make render 2>&1 | tail -5
```

Expected: clean render. The rendered command files in each host output should reflect the thinned source.

- [ ] **Step 4: Spot-check the rendered command on each host**

```bash
wc -l .claude/plugins/scholar-ip/commands/deepresearch.md
wc -l .opencode/commands/scholar-deepresearch.md
wc -l .codex/plugins/scholar/skills/scholar-deepresearch/SKILL.md
```

Expected: each should be in the 50-100 line range (some host adapters add per-host content like a dispatch plan to the bottom; that's expected; the raw source body is 70-80 but rendered output may grow slightly).

- [ ] **Step 5: Run tests**

```bash
.venv/bin/python -m pytest tests/ -q 2>&1 | tail -3
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add plugins/scholar-ip/commands/deepresearch.md
git commit -m "refactor(deepresearch): thin command body to executable contract

313 → ~70 lines. Body now contains: 2-paragraph intro, stage map
(links to skills/deep-literature-review/references/stage-N-*.md),
links to budget / resume / PRISMA / failures, constraints, done
criteria.

Per-stage procedures and schemas (previously inlined) now live in
the references/ files extracted in Tasks 1-2. The command is the
trigger; SKILL.md is the spec home; references/ are the on-demand
deep dives."
```

Expected: one commit, 1 file modified (~240 line reduction).

---

## Task 5: Final verification + summary

**Files:** none (verification only)

- [ ] **Step 1: Final line-count summary**

```bash
echo "=== sources (before/after) ==="
wc -l plugins/scholar-ip/commands/deepresearch.md plugins/scholar-ip/skills/deep-literature-review/SKILL.md
echo
echo "=== new references ==="
wc -l plugins/scholar-ip/skills/deep-literature-review/references/*.md
echo
echo "=== total references line count ==="
wc -l plugins/scholar-ip/skills/deep-literature-review/references/*.md | tail -1
```

Expected:
- `commands/deepresearch.md`: 70-80 lines (was 313)
- `skills/deep-literature-review/SKILL.md`: 100-110 lines (was 233)
- 12 references files, each within +/- 10 of plan estimates
- Total references body: ~400 lines

- [ ] **Step 2: Full render**

```bash
make render 2>&1 | tail -10
```

Expected: clean. Three host outputs each contain 12 references/*.md files for deep-literature-review.

- [ ] **Step 3: Full test suite**

```bash
.venv/bin/python -m pytest tests/ -q 2>&1 | tail -5
```

Expected: all pass.

- [ ] **Step 4: Link smoke check**

The references/*.md files cross-link to each other (e.g., stage-1-frame.md → upstream-credits.md). Confirm none of those links point at non-existent files:

```bash
cd plugins/scholar-ip/skills/deep-literature-review/references
for f in *.md; do
  grep -oE '\[[^\]]+\]\([^)]+\.md[^)]*\)' "$f" | while read link; do
    # Extract the path part (before any # anchor)
    path=$(echo "$link" | sed -E 's/.*\(([^#)]+)([#)].*)?$/\1/')
    if [[ ! -f "$path" ]] && [[ ! -f "../$path" ]]; then
      echo "BROKEN in $f: $link"
    fi
  done
done
cd - > /dev/null
echo "(if no 'BROKEN' lines printed above, all links resolve)"
```

Expected: no "BROKEN" lines. If any link resolves to a non-existent file, fix the link in the source markdown.

- [ ] **Step 5: Verify commit chain**

```bash
git --no-pager log --oneline master..HEAD
```

Expected: 6 commits with subjects roughly matching:
```
<sha> refactor(deepresearch): thin command body to executable contract
<sha> refactor(deepresearch): thin deep-literature-review/SKILL.md to entry + map
<sha> refactor(deepresearch): extract 6 auxiliary references
<sha> refactor(deepresearch): extract 6 stage references
<sha> docs(deepresearch): import progressive-disclosure refactor plan
(plus any earlier commits from Path A if not yet on master)
```

(If Path A `feat/render-skill-bundles` has not been merged to master, the chain will also include Path A's commits. That is expected — this branch is downstream of Path A.)

- [ ] **Step 6: Report context-economy win**

Print to controller:
- Before: 313 + 233 = 546 lines persistent context when `/scholar:deepresearch` triggers + SKILL.md loads.
- After: ~70 (command) + ~105 (SKILL.md) = ~175 lines persistent. Plus ~50 lines transient per active stage.
- Reduction in persistent context: ~68%.
- Reduction in effective context during any single stage: from 546 → ~225, ~59%.

- [ ] **Step 7: Surface PR description draft**

Print to controller (do NOT push, do NOT open PR — that is the user's call):

```markdown
## Summary

Splits `commands/deepresearch.md` (313 lines) and `skills/deep-literature-review/SKILL.md` (233 lines) into a thin entry + 12 `references/` files. The agent now loads only the stage's procedure when running that stage, instead of the full 6-stage spec on every turn.

## Background

This is the canonical use case the bundle-propagation pipeline (`feat/render-skill-bundles`) was built to enable. See `docs/spike-results/2026-05-19-opencode-js-plugin.md` for the spike that ruled out an alternative approach.

## What changes

- 12 new `plugins/scholar-ip/skills/deep-literature-review/references/*.md` files: one per stage (1-6) plus 6 auxiliary (PRISMA recipe, breadth-depth budget, resume protocol, failure modes, upstream credits, anti-patterns).
- `commands/deepresearch.md`: 313 → ~70 lines. Body is now a stage map + constraints + done criteria; per-stage procedures live in the references.
- `skills/deep-literature-review/SKILL.md`: 233 → ~105 lines. Body is now when-to-use + inputs + outputs + stage map + quality checklist.
- All cross-references between the new files validated by smoke check.

## Test plan

- [x] `pytest tests/` — all pass; invariant I (bundle propagation) automatically exercises every new references/*.md.
- [x] `make render` — three host outputs each contain 12 references/*.md for deep-literature-review.
- [x] Link smoke check — every markdown link in references/*.md resolves.

## Out of scope (deliberate)

- The `using-deep-research` skill (lightweight entry-point) is untouched. Its own `references/example.md` from Path A Task 6 stays.
- Other skills/commands (scholar-search, bib-manager, etc.) are not refactored. They are mentioned by deepresearch but don't follow this pattern themselves.
- Codex intra-bundle link rewriting (Option A). Plan defaults to Option B (no rewriting) per the Path A spike's architecture review.
```

- [ ] **Step 8: Final state**

```bash
git --no-pager status --short
git branch --show-current
```

Expected: clean working tree on `refactor/deepresearch-progressive-disclosure`.

---

## Rollback

The refactor is purely additive in spirit (every line in the original sources lives somewhere in references/ now). To abandon:

```bash
git checkout feat/render-skill-bundles
git branch -D refactor/deepresearch-progressive-disclosure
```

No external services touched; no installed config affected.

---

## Out of scope (explicitly excluded)

- Modifying `packages/adapters/` Python code (Path A's job, already landed).
- Adding new tests (invariant I already covers bundle propagation; no new behaviour to assert).
- Touching the `using-deep-research` skill or its bundle.
- Renaming any source skill or command id (cosmetic; if any happens it triggers conformance failures around `expected_counts.json`).
- Auto-rewriting cross-skill relative links for Codex (Option A from the spike). Plan defaults to Option B — keep linkage at SKILL.md level inside references/.
- A general "progressive disclosure" pass on other monolithic skills (`claim-chart-builder` 347 lines, `novelty-heuristics` 262 lines). Those are separate plans if the win on deepresearch is judged worthwhile.
