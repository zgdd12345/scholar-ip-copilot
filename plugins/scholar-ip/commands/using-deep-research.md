---
id: using-deep-research
title: "Entrypoint command for the /scholar:deepresearch workflow"
description: >
  Load the `using-deep-research` skill: explains what `/scholar:deepresearch`
  produces, the two prereqs (`/scholar:paper-init` + `/scholar:brainstorming`)
  that unblock the `scope-required` hook, the scope-stub fast-path for ad-hoc
  use, the `breadth` / `depth` budget knobs, the resume-on-crash protocol,
  and the four failure modes. Use when the user wants to start a deep
  literature review and may not have an EviDraft project scaffolded yet.
kind: command
slash: /scholar:using-deep-research
phase: shared
inputs:
  - name: topic
    type: string
    optional: true
    description: "Optional research topic; the skill will propose the right command sequence based on it."
allowed_tools: [Read, Glob, Grep]
hooks: []
references:
  - doc: ../skills/using-deep-research/SKILL.md
  - doc: ../skills/deep-literature-review/SKILL.md
  - doc: ../commands/deepresearch.md
  - doc: ../commands/brainstorming.md
  - doc: ../commands/paper-init.md
---

# /scholar:using-deep-research

Load `skills/using-deep-research/SKILL.md` and follow it. This is the **single entry point** for the deep / PRISMA-style literature review workflow.

The skill walks through:

1. What the 6-stage pipeline produces (`plan.yaml`, `candidates.jsonl`, `screening_log.csv`, `clusters.yaml`, `critique/<id>.md`, `related_work.draft.md`, `citation_audit.json`).
2. The two-step scaffolding (`/scholar:paper-init` + `/scholar:brainstorming`) that unblocks the `scope-required` hook.
3. The scope-stub fast-path for ad-hoc use (when the user explicitly pushes back on the 5-minute brainstorming step).
4. The `breadth` / `depth` / `mode` / `resume_from` budget knobs and three recommended presets.
5. The four failure modes (no scope, network denied, budget exceeded, failed citation audit).
6. When NOT to use deepresearch (use `/scholar:paper-lit` or `scholar-search` skill instead for lighter tasks).

## Behaviour when invoked

- **No topic argument** → ask the user for the topic, then propose the right command sequence based on whether they want a real review, a scoping pass, or a one-shot survey.
- **With a topic argument** → default to the **full path**:
  ```text
  /scholar:paper-init
  /scholar:brainstorming "<topic>"
  /scholar:deepresearch "<topic>" --breadth 30 --depth 2
  ```
  Offer the scope-stub fast-path only if the user explicitly says they want to skip brainstorming.

## Done criteria

- The skill has been loaded and the user knows the prereq sequence.
- The user has decided on full path vs fast-path vs lighter alternative.
- The next command has been proposed verbatim (no ambiguity, copy-paste ready).
