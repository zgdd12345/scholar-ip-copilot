# workflow:using.run

**Meta entrypoint.** Type `workflow:using.run` whenever you want a fresh tour of EviDraft: what each workflow does, in what order, what persists, and which policies gate downstream work.

## What this command does

1. Load `../../../capabilities/research/using-scholar-ip-copilot/spec.md` and follow it exactly.
2. Detect the current project state (`.evidraft/project.yaml` present? which `status:` rows are `done`?).
3. Print a personalised "where you are" map: completed stages, the next recommended action, and any policy currently blocking progress.
4. List every `workflow:<id>`, grouped by phase (shared / paper / patent / submission-time / external-bridge / polish), with a one-line description each.
5. Offer to invoke the next recommended command on confirmation.

## When to use it

- First conversation in a project — orient before touching anything.
- Returning to a project after time away — confirm where you left off.
- Onboarding a teammate — share a single command they can run.
- Before answering "how do I do X?" — read the orientation first.

## Constraints

- Read-only. This command never writes to `.evidraft/`, `manuscript/`, or source.
- Never invents progress: if `.evidraft/project.yaml` is missing, says so and recommends `workflow:paper.init` or `workflow:patent.init`.
- Never claims a stage is `done` without checking the `status:` block.

## Done criteria

- Chat output ends with: current stage, next recommended action, and any policy condition that needs to clear.
