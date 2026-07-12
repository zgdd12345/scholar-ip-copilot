# workflow:patent.init

Scaffold the patent side of an EviDraft project. Reuse `.evidraft/project.yaml` if it exists (set `project_type=mixed` when both paper and patent are wanted).

## Steps

1. **Inspect.** Probe the cwd: existing `.evidraft/`, existing code, docs, `inventors.yaml`, `disclosure.md`. Do not overwrite.
2. **Infer or ask** for `title`, `field`, `jurisdiction`, inventor list. Do **not** invent inventor names.
3. **Materialise template.** Copy `../../../templates/patent-project/.evidraft/patent/` skeletons without overwriting.
4. **Write `invention_disclosure.md`** with the section headers prefilled (Background, Problem, Summary, Technical Solution, Implementation Details, Alternatives, Advantages, Examples, Diagrams, Code Traceability, Inventor Questions). Sections are empty placeholders ready for `workflow:patent.scout` and `workflow:patent.disclosure`.
5. **Append a "Needs attorney review" checklist** to the bottom of `invention_disclosure.md`. The plugin must never remove this checklist.

## Constraints

- This command does no novelty analysis. It only sets up scaffolding.
- Respect `policy:workspace-safety`.
- If `.evidraft/patent/` exists, summarise contents and ask before any write.

## Done criteria

- `.evidraft/project.yaml` reflects `project_type=patent` or `mixed`.
- All template files materialised.
- Chat output recommends `workflow:patent.scout` next.
