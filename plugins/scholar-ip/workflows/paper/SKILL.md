---
name: scholar-paper
description: Route the complete evidence-backed paper lifecycle.
---

# Paper workflow router

Read `workflow.yaml`, resolve the selected action, and validate its declared inputs.
Load only the selected action's procedure; never preload another stage.
Apply the declared policies and role assignments before executing the procedure.
Run deterministic workflow preflight before writes and finalize after the stage completes.
Delegate adaptively when a stage benefits from independent review: use no fixed cardinality, waves, or retry count. Choose the smallest useful set from the available roles based on current gaps, and stop when additional delegation would not materially improve the result.

- `init`: load `stages/init.md`.
- `lit`: load `stages/lit.md`.
- `idea`: load `stages/idea.md`.
- `code-audit`: load `stages/code-audit.md`.
- `experiment`: load `stages/experiment.md`.
- `review`: load `stages/review.md`.
- `draft`: load `stages/draft.md`.
- `check`: load `stages/check.md`.
- `venue`: load `stages/venue.md`.

If no action is supplied and this workflow has multiple actions, show the valid action
names and stop. For a single-action workflow, default to `run`.
