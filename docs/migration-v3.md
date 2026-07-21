# EviDraft 3.0 workflow migration

EviDraft 3.0 lightens workflow execution without changing project data. Existing
projects keep `format_version: 2`; there is no project-data rewrite for this release.

## Public interface

The seven workflow names remain stable. The redundant `research guide` action was
removed without an alias. Use `workflow:using.run` (or the host-specific `using`
entrypoint) for orientation and direct routing.

`research.guide` was removed. `research.explain` always attempts similar and current
methods, schedules up to 15 ready tasks, and writes a `partial` note with explicit gaps
when required external work is unavailable or fails. Audit findings are advisory, so
valid packets continue to synthesis.

Primary output paths under `.evidraft/`, `manuscript/`, and `submissions/` remain
valid. An output may now declare `required: false` when it is conditional on inputs or
on a successful validation step.

## Existing projects

The new workflow does not delete existing intermediate artefacts. Old task-graph
packets, section plans, audit logs, and other generated files remain ordinary project
files; they can be retained or removed by the project owner. New runs simply stop
requiring redundant intermediates.

Scope and evidence checks report warnings, generation is best-effort, and final
paper/patent checks report `PASS`, `WARN`, or `FAIL`. Path confinement, sensitive-file
protection, overwrite approval, and publication boundaries remain hard.

Codex marketplace mode is the default. `.agents/skills` remains an explicit, mutually
exclusive compatibility mode. After reinstall, restart the Claude or OpenCode host
session; Codex users must restart and open a new task.
