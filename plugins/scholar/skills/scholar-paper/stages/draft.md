# workflow:paper.draft

Draft first, then let `workflow:paper.check` judge readiness. Write the most useful
paper possible from the inputs on hand and consolidate every unresolved issue in
`.evidraft/manuscript/validation_gaps.md`.

## Steps

1. **Inventory without gating.** Read any available project metadata, scope,
   evidence, bibliography, literature synthesis, code map, results, and existing
   manuscript. Missing scope, evidence, `method_to_code.md`, or prior plan must not
   block drafting. Record each missing or stale input as a validation gap and use
   explicit `TODO`, cautious wording, or omitted unsupported detail in the draft.
2. **Adaptive outline.** Derive a compact outline for the selected sections. Reuse
   existing prose that still matches the current inputs. Do not require or create
   a separate plan file for each section.
3. **Draft LaTeX.** Use the available writing, evidence, and methodology roles
   adaptively according to the gaps and section risk. Write `manuscript/main.tex`
   and the selected files under `manuscript/sections/`. Preserve existing author
   content unless the requested section requires editing it.
4. **Mark support honestly.** Use only resolvable citation keys and evidence ids.
   When support is unavailable, keep useful non-claim prose, label the unsupported
   passage with a `TODO`, and add the exact file/section and needed validation to
   the unified gap file.
5. **Consolidate validation gaps.** Write one
   `.evidraft/manuscript/validation_gaps.md` with an `Input summary` and a table:
   `Location | Gap | Impact | Recommended validation | Status`. Include missing
   citations, evidence, code traces, experiment sources, references, and compile
   checks. If no gaps remain, remove a stale gap file or write `No open gaps`.
6. **Optional compile.** Use `../../.evidraft-private/capabilities/latex/latex-build/spec.md` when
   available. A missing tool or compile failure is a gap, not a drafting blocker.

## Constraints

- Never invent a citation, result, number, code trace, or completed validation.
- Strong claims without support must be softened, marked `TODO`, or omitted.
- Preserve the user's existing manuscript structure where practical.
- Workspace safety is the only hard blocker.

## Done criteria

- `main.tex` includes every selected section that could be drafted.
- All known missing support and failed checks appear in the single validation-gap
  artifact rather than scattered planning files.
- Status is `complete` when no gaps remain, `complete_with_gaps` when a useful draft
  was produced with recorded gaps, or `blocked` only when workspace safety prevents
  every manuscript write.
- Chat output reports written sections, status, gap count, and compile result.
