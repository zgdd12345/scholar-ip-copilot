# workflow:paper.init

Perform lightweight, lazy initialization in the current working directory. Create
only these four required core files, plus their parent directories:

- `.evidraft/project.yaml`
- `.evidraft/evidence/evidence.jsonl`
- `.evidraft/literature/references.bib`
- `manuscript/main.tex`

Later actions materialize matrices, analyses, section files, and other stage-owned
artifacts when first needed. Initialization is best effort: unknown optional
metadata is recorded as a gap.

## Steps

1. Inspect the project without reading sensitive paths. Note existing code,
   experiments, manuscripts, and any of the four core files.
2. When `.evidraft/project.yaml` is missing, infer or ask only for values needed
   now: `project_type`, `title`, `field`, and `target_venue`. Leave unknown optional
   values unset rather than inventing them.
3. Create each missing core file and its parent directory. Use the smallest
   schema-valid record for `.evidraft/project.yaml`, an empty append-only JSONL
   store for `.evidraft/evidence/evidence.jsonl`, an empty canonical bibliography
   for `.evidraft/literature/references.bib`, and the neutral manuscript skeleton
   for `manuscript/main.tex`.
4. Leave every existing core file unchanged. Report any difference between supplied
   metadata and the existing project record for a later explicit edit; init never
   rewrites the record.
5. Validate the project record against `../../../schemas/project.schema.json`.
6. Report existing later-stage artifacts, but do not create them. In particular,
   init does not create `manuscript/sections/`.

## Constraints

- Respect `policy:workspace-safety`; it is the only condition that can block init.
- Do not invent author names, affiliations, venues, commands, or project metadata.
- Never overwrite any existing file, including an existing manuscript,
  bibliography, or evidence store.

## Done criteria

- All four required core files exist; `.evidraft/project.yaml` validates.
- Status is `complete` when the requested metadata was recorded,
  `complete_with_gaps` when optional metadata remains unknown, or `blocked` only
  when workspace safety prevents writing the core files.
- Chat output recommends the next action that matches the material already present.
