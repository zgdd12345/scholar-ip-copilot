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
