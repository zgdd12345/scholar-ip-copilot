# workflow:research.guide

Load `../../../capabilities/research/using-deep-research/spec.md` and follow it. This is the **single entry point** for the deep / PRISMA-style literature review workflow.

The skill walks through:

1. What the 6-stage pipeline produces (`plan.yaml`, `candidates.jsonl`, `screening_log.csv`, `clusters.yaml`, `critique/<id>.md`, `related_work.draft.md`, `citation_audit.json`).
2. The two-step scaffolding (`workflow:paper.init` + `workflow:scope.run`) that satisfies `policy:scope`.
3. The scope-stub fast-path for ad-hoc use (when the user explicitly pushes back on the 5-minute brainstorming step).
4. The `breadth` / `depth` / `mode` / `resume_from` budget knobs and three recommended presets.
5. The four failure modes (no scope, network denied, budget exceeded, failed citation audit).
6. When NOT to use deepresearch (use `workflow:paper.lit` or `scholar-search` skill instead for lighter tasks).

## Behaviour when invoked

- **No topic argument** → ask the user for the topic, then propose the right command sequence based on whether they want a real review, a scoping pass, or a one-shot survey.
- **With a topic argument** → default to the **full path**:
  ```text
  workflow:paper.init
  workflow:scope.run "<topic>"
  workflow:research.deep "<topic>" --breadth 30 --depth 2
  ```
  Offer the scope-stub fast-path only if the user explicitly says they want to skip brainstorming.

## Done criteria

- The skill has been loaded and the user knows the prereq sequence.
- The user has decided on full path vs fast-path vs lighter alternative.
- The next command has been proposed verbatim (no ambiguity, copy-paste ready).
