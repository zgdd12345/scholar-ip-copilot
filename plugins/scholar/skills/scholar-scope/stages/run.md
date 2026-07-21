# workflow:scope.run

Create a small, approved statement of project scope before substantial paper or patent
work. The default `fast` path minimizes interaction: inspect context, ask one useful
question, show one proposed scope, and request one approval.

## Procedure

1. Read `.evidraft/project.yaml`, prior `.evidraft/scope/*.md`, prior
   `.evidraft/ideas/*.md`, and `seed_idea` when supplied. Infer `paper` or `patent` from
   `branch` and project state. If it remains unclear, make branch selection the single
   follow-up below.
2. Build a provisional scope from known facts. Ask exactly one follow-up question about
   the highest-impact unresolved point:
   - paper: the contribution and its concrete success criterion;
   - patent: the inventive step and disclosure boundary;
   - unclear branch: whether the deliverable is a paper or patent disclosure.
   Combine closely related fields in that one question; do not start a questionnaire.
3. Assemble one concise proposal with project kind, contribution or inventive step,
   success criterion or claim boundary, hard constraint, riskiest assumption, evidence
   seeds, and a `pursue`, `refine`, or `kill` verdict. Preserve unknowns explicitly.
4. Show the complete proposal and ask exactly once for approval. Do not ask section-by-
   section questions or open another approval loop.
5. On approval, write one collision-safe
   `.evidraft/scope/YYYY-MM-DD-<slug>.md` using the canonical frontmatter from
   `../../.evidraft-private/capabilities/research/brainstorming/spec.md`, with `status: approved`,
   `approved_date`, and `staleness_until`. On rejection, write nothing and return
   `blocked` with the unresolved concern so a later invocation can start fresh.
6. Report the concrete path and one next action: `workflow:paper.lit` for paper scope or
   `workflow:patent.scout` for patent scope.

## Explicit full mode

When `mode=full` is explicitly supplied, use the same single follow-up and single
approval interaction. Expand the proposal with prior-work contrast, evaluation plan,
constraints, and alternatives only from already available context; preserve missing
details as gaps instead of starting a multi-round interview.

## Constraints

- Scope only; do not draft methods, experiments, manuscript prose, or claims.
- Never invent citations, prior art, numbers, jurisdictions, or disclosure facts.
- Write no artefact outside `.evidraft/scope/`.
- Append `-v2`, `-v3`, and so on when a target slug already exists.

## Done criteria

- Approved: exactly one valid, approved scope file exists and its path is reported.
- Rejected or unsafe: no file is written and status is `blocked` with a recovery step.
- The interaction used no more than one follow-up and one approval request.
