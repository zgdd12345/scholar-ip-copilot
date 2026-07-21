---
description: Orient users in the complete EviDraft paper and patent workflow.
name: scholar-using
---

Spec home: `workflow.yaml`. Resolve the action there before loading a stage.
Resolve every output placeholder from the action inputs. Before any write, run `evidraft workflow preflight <workflow>.<action> --target <each concrete write path>`; repeat `--target` as needed. This preflight is safety-only and never reads the evidence store. For `xreview.run`, additionally pass the reviewed input as `--read-target <target>` and its concrete `.evidraft/reviews/...` output as `--target`. Never pass unresolved `<...>` placeholders. When the selected procedure requests an evidence check, run it separately after useful output exists with `evidraft evidence audit --id <each current evidence id>`; repeat `--id` as needed, and report audit findings as gaps rather than folding them into preflight. Then after completion inspect the selected action's `retention`. If it is non-empty, run `evidraft workflow finalize --directory <directory> --pattern <pattern> --keep-last <keep_last> --max-age-days <max_age_days>` using its declared values; if retention is empty, skip finalize.
Apply `policy:workspace-safety`: use only its default allowed tools and never invoke Bash:rm -rf*, Bash:sudo*.
Each selected action's role assignment declares availability only. Never dispatch merely because an assignment exists. The selected procedure controls dispatch timing and cardinality for every other action; research.explain is controlled by its validated task graph and bounded at 15. When the procedure dispatches a role, resolve its mode in `../.evidraft-private/roles/roles.yaml` and load exactly one private mode spec at `../.evidraft-private/roles/modes/<mode>.md`. The mode spec is authoritative for tools, responsibilities, constraints, and output contracts. Map fast, standard, and deep to the closest available host effort levels.

# Using workflow router

Read `workflow.yaml`, resolve the selected action, and validate its declared inputs.
Load only the selected action's procedure; never preload another stage.
Apply the declared policies and role assignments before executing the procedure.
Run deterministic workflow preflight before writes and finalize after the stage completes.

- `run`: load `stages/run.md`.

If no action is supplied and this workflow has multiple actions, show the valid action
names and stop. For a single-action workflow, default to `run`.
