# workflow:patent.init

Perform lazy initialization for patent work. The only required artifact is
`.evidraft/project.yaml`; patent deliverables are created by the action that first
needs them. Do not eagerly create disclosure, candidate, prior-art, or claim-chart
placeholders.
Initialization is best effort: unknown optional metadata is recorded as a gap.

## Steps

1. Inspect the current directory without reading sensitive paths. Note code, design
   documents, existing disclosures, and any `.evidraft/project.yaml`.
2. Infer or ask only for values needed now: `title`, `field`, `jurisdiction`, and
   project type. Never invent inventors.
3. Create the smallest schema-valid project record when none exists. Reuse an
   existing record, setting `project_type=mixed` only when the user wants both
   paper and patent work, and update only explicitly supplied values.
4. Validate against `../../../schemas/project.schema.json` and report which later
   patent action will materialize each currently missing optional artifact.

## Constraints

- Respect `policy:workspace-safety`; it is the only condition that can block init.
- This action performs no novelty or legal analysis.
- Never overwrite an existing patent artifact.

## Done criteria

- `.evidraft/project.yaml` exists and validates.
- Status is `complete`, `complete_with_gaps` for unknown optional metadata, or
  `blocked` only when workspace safety prevents the required write.
- Chat output recommends `workflow:patent.scout` or the later action matching the
  user's existing material.
