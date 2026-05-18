---
id: using
title: "Orient yourself in the scholar plugin — the using-scholar-ip-copilot entrypoint"
kind: command
slash: /scholar:using
phase: shared
description: >
  Loads the `using-scholar-ip-copilot` skill and walks the user through the
  full EviDraft workflow (paper + patent), gating rules, and where each
  command's output lands on disk. Equivalent to `superpowers:using-superpowers`.
allowed_tools: [Read, Glob, Grep]
hooks: []
references:
  - doc: ../skills/using-scholar-ip-copilot/SKILL.md
  - doc: ../../../README.md
  - doc: ../../../docs/architecture.md
---

# /scholar:using

**Meta entrypoint.** Type `/scholar:using` whenever you want a fresh tour of the EviDraft plugin — what each command does, in what order, what gets persisted, and what hooks gate downstream work.

## What this command does

1. Load `skills/using-scholar-ip-copilot/SKILL.md` and follow it exactly.
2. Detect the current project state (`.evidraft/project.yaml` present? which `status:` rows are `done`?).
3. Print a personalised "where you are" map: completed stages, the next recommended command, and any gating hooks that are currently blocking progress.
4. List every `/scholar:<cmd>`, grouped by phase (shared / paper / patent / submission-time / external-bridge / polish), with a one-line description each.
5. Offer to invoke the next recommended command on confirmation.

## When to use it

- First conversation in a project — orient before touching anything.
- Returning to a project after time away — confirm where you left off.
- Onboarding a teammate — share a single command they can run.
- Before answering "how do I do X?" — read the orientation first.

## Constraints

- Read-only. This command never writes to `.evidraft/`, `manuscript/`, or source.
- Never invents progress: if `.evidraft/project.yaml` is missing, says so and recommends `/scholar:paper-init` or `/scholar:patent-init`.
- Never claims a stage is `done` without checking the `status:` block.

## Done criteria

- Chat output ends with: current stage, next recommended command, and any gating hook that needs to clear.
