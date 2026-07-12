# Resume protocol

`resume_from=<stage>` skips every earlier stage. The orchestrator must:

1. Locate the latest `run_id` in `plan.yaml`.
2. Verify the artefacts of every stage strictly before `<stage>` exist and parse. If any is missing or malformed, refuse and name the missing artefact.
3. Restore `breadth` / `depth` from `plan.yaml`, not from user input. See [breadth-depth-budget.md](breadth-depth-budget.md) for the knob semantics.
4. Append, never overwrite — every artefact carries the same `run_id` so multiple runs in the same project can be diffed.
