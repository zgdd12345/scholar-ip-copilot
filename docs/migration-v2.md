# Migrating projects to format version 2

EviDraft 2.0 keeps existing `.evidraft/`, `manuscript/`, and `submissions/` paths. It
changes the project data schema and the host-facing command surface.

## When migration runs

A project with no `format_version` is v1. The deterministic core migrates it before the
first write, or explicitly with:

```bash
.venv/bin/evidraft --root <project> migrate
```

A project already at `format_version: 2` is a no-op.

## Transaction guarantees

Migration acquires a project lock, verifies available capacity, journals the operation,
backs up every file it may replace, validates the complete v2 temporary state, and uses
atomic replacement. Failure restores the original files. Concurrent hosts cannot both
perform the migration, and stale locks are recovered only when their recorded owner is
dead.

## Evidence and snapshots

Valid evidence keeps its stable ID. Records that cannot satisfy the v2 schema are copied
verbatim to quarantine and reported; publish-class actions remain blocked until those
rows are resolved. The original evidence text is never discarded.

Legacy URL-hash snapshots remain on disk. Migration computes `sha256(raw_body)`, stores
the content-addressed copy, and updates evidence paths only after that copy validates.
Two responses from the same URL therefore remain distinct when their raw bodies differ.

## Public workflows

The renderer installs only `using`, `scope`, `research`, `paper`, `patent`, `polish`, and
`xreview`. Former phase-specific entry files are not generated. Their behavior is
available as actions, for example `paper draft`, `patent claims`, or `research deep`.

Re-rendering uses `.evidraft-render-manifest.json` to remove paths owned by the previous
installation. It does not remove arbitrary user directories whose names begin with
`scholar-`.
