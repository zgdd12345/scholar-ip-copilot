# EviDraft 3.0 workflow migration

EviDraft 3.0 lightens workflow execution without changing project data. Existing
projects keep `format_version: 2`; there is no project-data rewrite for this release.

## Public interface

The seven workflow names remain stable. The redundant `research guide` action was
removed without an alias. Use `workflow:using.run` (or the host-specific `using`
entrypoint) for orientation and direct routing.

Primary output paths under `.evidraft/`, `manuscript/`, and `submissions/` remain
valid. An output may now declare `required: false` when it is conditional on inputs or
on a successful validation step.

## Existing projects

The new workflow does not delete existing intermediate artefacts. Old task-graph
packets, section plans, audit logs, and other generated files remain ordinary project
files; they can be retained or removed by the project owner. New runs simply stop
requiring redundant intermediates.

Scope is advisory, generation is best-effort, and final paper/patent checks report
`PASS`, `WARN`, or `FAIL`. Workspace confinement, sensitive-path protection, explicit
overwrite approval, and external-review write zones remain enforced.
