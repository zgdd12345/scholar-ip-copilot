# workflow:using.run

Use this read-only router when the user asks what EviDraft can do, where a project
currently stands, or which workflow should handle a request.

## Route by intent

1. Read the user's request before presenting a workflow map. Route unambiguous intent
   directly to the matching public workflow and do not ask for confirmation:
   - one identifiable paper to explain, close-read, critique, or inspect equations ->
     `workflow:research.explain`;
   - a personal topic reading list -> `workflow:research.reading-list`;
   - a broad, comparative, or systematic literature review ->
     `workflow:research.deep`;
   - project goals, contribution boundaries, or invention scope ->
     `workflow:scope.run`;
   - paper, patent, polish, or external-review work -> the public action whose
     description directly matches that request.
2. Ask one clarifying question only when the intent is ambiguous between two or more
   materially different workflows. After the answer, route directly without another
   confirmation round.
3. Routing is a handoff, not execution inside this read-only workflow. Name the exact
   `workflow:<id>.<action>` and pass through the user's supplied arguments unchanged.

## Orientation and project state

When the user asks for a tour rather than a concrete task:

1. Read the current workflow YAML files for the authoritative public action list.
2. Inspect `.evidraft/project.yaml` and existing artefacts when present.
3. Report completed work only when it is visible in current project state.
4. Summarise the relevant paper, patent, research, scope, polish, and external-review
   paths. Prefer the shortest path that matches the stated goal.
5. End with the current stage, the directly recommended next action, and any missing
   prerequisite visible in project state.

## Constraints

- Remain read-only and do not create project files.
- Do not route a topic-level request to single-paper explanation.
- Do not invent workflow or action names; use current workflow sources.
- Do not turn a clear request into a general onboarding interview.

## Done criteria

- A clear intent is handed directly to one public workflow.
- An ambiguous intent receives at most one clarifying question.
- A tour accurately reflects current workflow sources and project state.
