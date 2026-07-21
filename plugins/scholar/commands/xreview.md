---
description: Delegate a bounded review pass to an external coding agent.
argument-hint: <action> [args]
---

Spec home: `${CLAUDE_PLUGIN_ROOT}/private/workflows/xreview/workflow.yaml`. Resolve the action there before loading a stage.
Resolve every output placeholder from the action inputs. Before any write, run `evidraft workflow preflight <workflow>.<action> --target <each concrete write path>`; repeat `--target` as needed. This preflight is safety-only and never reads the evidence store. For `xreview.run`, additionally pass the reviewed input as `--read-target <target>` and its concrete `.evidraft/reviews/...` output as `--target`. Never pass unresolved `<...>` placeholders. When the selected procedure requests an evidence check, run it separately after useful output exists with `evidraft evidence audit --id <each current evidence id>`; repeat `--id` as needed, and report audit findings as gaps rather than folding them into preflight. Then after completion inspect the selected action's `retention`. If it is non-empty, run `evidraft workflow finalize --directory <directory> --pattern <pattern> --keep-last <keep_last> --max-age-days <max_age_days>` using its declared values; if retention is empty, skip finalize.
Apply `policy:workspace-safety`: use only its default allowed tools and never invoke Bash:rm -rf*, Bash:sudo*.
Each selected action's role assignment declares availability only. Never dispatch merely because an assignment exists. The selected procedure controls dispatch timing and cardinality for every other action; research.explain is controlled by its validated task graph and bounded at 15. When the procedure dispatches a role, use its declared mode with this model mapping: fast -> haiku, standard -> sonnet, deep -> opus. The role file uses `inherit`; the action assignment is authoritative.

# Xreview workflow router

Read `workflow.yaml`, resolve the selected action, and validate its declared inputs.
Load only the selected action's procedure; never preload another stage.
Apply the declared policies and role assignments before executing the procedure.
Run deterministic workflow preflight before writes and finalize after the stage completes.
Delegate adaptively: use no fixed cardinality, waves, or retry count. Let target complexity and recoverable failures determine whether another bounded invocation is useful, while preserving timeout, cost, read-only, and write-zone limits.

- `run`: load `stages/run.md`.

If no action is supplied and this workflow has multiple actions, show the valid action
names and stop. For a single-action workflow, default to `run`.
