---
name: scholar-research
description: Route reading lists, single-paper explanation, and deep literature research.
---

# Research workflow router

Read `workflow.yaml`, resolve the selected action, and validate its declared inputs.
Load only the selected action's procedure; never preload another stage.
Apply the declared policies and role assignments before executing the procedure.
Run deterministic workflow preflight before writes and finalize after the stage completes.

- `reading-list`: load `stages/reading-list.md`.
- `explain`: load `stages/explain.md`.
- `deep`: load `stages/deep.md`.

If no action is supplied and this workflow has multiple actions, show the valid action
names and stop. For a single-action workflow, default to `run`.
