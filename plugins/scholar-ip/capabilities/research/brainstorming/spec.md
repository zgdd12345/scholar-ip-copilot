---
id: brainstorming
title: "Scope-clarification discipline: question schema, verdict matrix, scope file template, staleness rule"
kind: skill
phase: shared
description: >
  Load when workflow:scope.run runs, or when a downstream creative command
  (paper-idea, patent-scout, paper-draft, patent-claims, deepresearch, polish)
  finds the scope file missing or stale. Provides the per-branch question
  schema, the Pursue/Refine/Kill verdict matrix, the canonical scope-file
  template (paper and patent variants, bilingual section labels), and the
  14-day staleness rule.
triggers:
  - "workflow:scope.run"
  - "downstream command finds .evidraft/scope/ missing"
  - "downstream command finds scope file stale"
  - "policy:scope preflight blocks"
provides:
  - question-schema-paper
  - question-schema-patent
  - verdict-matrix
  - scope-file-template
  - staleness-rule
allowed_tools: [Read, Glob, Grep, Write, Edit]
policies: []
references:
  - doc: policy:scope
  - doc: workflow:scope.run
  - doc: capability:using-scholar-ip-copilot
  - doc: references/question-schemas.md
  - doc: references/carlini-and-approaches.md
  - doc: references/verdict-matrix.md
  - doc: references/scope-file-template.md
  - doc: references/staleness-rule.md
  - doc: references/anti-patterns.md
  - url: "https://github.com/obra/superpowers (superpowers brainstorming method) — interview-style clarification"
  - url: "https://github.com/andrehuang/research-companion — idea-level intake patterns"
---

# brainstorming

## When to use

Pull this skill the moment `workflow:scope.run` starts, or whenever a downstream command fails the `policy:scope` gate (missing or stale scope file) and the user has to redo this stage. It owns the question schema, the verdict matrix, the scope file template, and the staleness rule. Every other artefact about scope defers to this one for shape.

This skill never drafts method, experiments, related-work prose, or claim text. It only clarifies *what the project is for*.

## Inputs

- `.evidraft/project.yaml` (project type, status, and optional `scope.staleness_days`; legacy v1 scope overrides remain migration-only).
- existing `.evidraft/scope/*.md` (prior iterations — read for context, never overwrite).
- existing `.evidraft/ideas/*.md` (prior ideation, optional).
- user statements during the interview.

## Outputs

- exactly one new file at `.evidraft/scope/YYYY-MM-DD-<slug>.md`.

## Procedure

Run these phases in order. Load only the reference you need for the phase you are in.

| # | Phase | Reference | Owns |
|---|---|---|---|
| 1 | Branch-specific question schema | [question-schemas.md](references/question-schemas.md) | paper (6 axes) + patent (7 axes) tables, fast-mode subsets, bilingual axis labels |
| 2 | Gap-surfacing + path selection (full mode) | [carlini-and-approaches.md](references/carlini-and-approaches.md) | Carlini conclusion-first test recipe, 2–3-approaches-with-tradeoffs technique |
| 3 | Verdict decision | [verdict-matrix.md](references/verdict-matrix.md) | Pursue / Refine / Kill matrix, conditions, fast-mode caveat |
| 4 | Write the scope file | [scope-file-template.md](references/scope-file-template.md) | path / slug rules, canonical frontmatter, paper body, patent body |
| 5 | Lifecycle | [staleness-rule.md](references/staleness-rule.md) | 14-day default, project.yaml override, policy:scope preflight interaction |
| — | Always avoid | [anti-patterns.md](references/anti-patterns.md) | what NOT to do |

Fast mode skips phase 2; otherwise the order is fixed.

## Quality checklist

- [ ] Exactly one scope file written per `workflow:scope.run` invocation.
- [ ] Frontmatter has all six required keys: `kind`, `status`, `verdict`, `riskiest_assumption`, `evidence_seeds`, `staleness_until` (plus `approved_date` if approved).
- [ ] `kind` is `paper` or `patent`; `status` is `draft` or `approved`; `verdict` is `pursue`, `refine`, or `kill`.
- [ ] Every novelty claim has at least one contrasted prior reference.
- [ ] Carlini draft is present (full mode) and gaps are explicit.
- [ ] 2–3 approaches are recorded with tradeoffs (full mode); the chosen one is named.
- [ ] No invented citations, numbers, or jurisdictions.
- [ ] Body sections match the canonical paper or patent list in [scope-file-template.md](references/scope-file-template.md).
