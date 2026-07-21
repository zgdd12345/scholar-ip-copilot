---
name: scholar-polish
description: Polish manuscript prose while preserving evidence and citations.
---

# Polish workflow router

Read `workflow.yaml`, resolve the selected action, and validate its declared inputs.
Load only the selected action's procedure; never preload another stage.
Apply the declared policies and role assignments before executing the procedure.
Run deterministic workflow preflight before writes and finalize after the stage completes.
Delegate adaptively when independent review improves fidelity: use no fixed cardinality, waves, or retry count. Scale review to the number and risk of the proposed hunks, and stop when every hunk has a fidelity verdict.

- `run`: load `stages/run.md`.

If no action is supplied and this workflow has multiple actions, show the valid action
names and stop. For a single-action workflow, default to `run`.
