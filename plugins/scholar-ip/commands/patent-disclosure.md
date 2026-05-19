---
id: patent-disclosure
title: "Draft the Technical Invention Disclosure (技术交底书 / TID) — primary patent deliverable"
description: >
  Draft the 技术交底书 / Technical Invention Disclosure (TID) for a single
  invention candidate — the **primary** patent deliverable handed off to
  a registered patent agent or attorney. Pulls from `invention_candidates.md`,
  `prior_art_map.md`, the code base, and experiment evidence; every claimed
  novelty is anchored to a `file:line` citation or evidence row. Use after
  `/scholar:patent-prior-art` and before `/scholar:patent-claims`.
kind: command
slash: /scholar:patent-disclosure
phase: patent
primary_deliverable: true
inputs:
  - name: candidate_id
    type: string
    optional: true
    description: "C-001 etc. If omitted, work on every candidate."
outputs:
  - path: .evidraft/patent/invention_disclosure.md
allowed_tools: [Read, Glob, Grep, Write, Edit]
hooks: [citation-guard, evidence-consistency, sensitive-file-guard]
subagents: [patent-engineer, methodology-reviewer, evidence-auditor]
references:
  - doc: ../skills/patent-disclosure/SKILL.md
  - doc: ../../../docs/legal-and-ethics.md
---

# /scholar:patent-disclosure

**Primary patent deliverable.** Produce a **技术交底书 (Technical Invention Disclosure, TID)** — a structured technical write-up that an inventor (or the EviDraft codebase-analyst on behalf of the inventor) hands off to a registered patent agent / attorney as the input for drafting a real patent application.

The TID is **not** a filed application, **not** legal advice, and **not** itself a patent. Its job is to give the attorney everything they need to draft claims, decide filing strategy, and assess scope.

The TID is written so that:
- a domain engineer can read it and understand the invention completely,
- an attorney can read it and have no follow-up questions about the technical content,
- the inventor questions section captures everything only the inventor can confirm.

## Steps

1. **Author the disclosure prose.** Use the `patent-engineer` subagent to draft each TID section in the project's `language` setting; it owns voice, structure, and the EN/ZH section headings.
2. **Methodology review.** Use the `methodology-reviewer` subagent to cross-check that the `Technical solution` and `Implementation details` sections are internally consistent with `method_to_code.md` and any equations.
3. **Evidence audit.** Use the `evidence-auditor` subagent to verify that every `Advantage` / `Technical effect` carries an `evidence_id` resolvable in `evidence.jsonl`, and that every `Code traceability` row has a `file_path:lines` that exists on disk.

## Required sections (per candidate) — TID structure

For each candidate (or just one, if `candidate_id` is given), write or update an H2 section in `invention_disclosure.md`. The TID structure below is jurisdiction-agnostic and works for US / EP / CN (CNIPA 技术交底书) / JP / PCT.

1. **Title** (技术名称)
2. **Field of the invention** (技术领域)
3. **Background** (背景技术) — what existed before, what problems it has
4. **Problem solved** (要解决的技术问题)
5. **Summary** (发明概述)
6. **Technical solution** (技术方案) — the core; needs enough detail to enable a skilled person
7. **Implementation details** (具体实施方式) — must reference `file_path` and line ranges from `method_to_code.md` / `evidence.jsonl`
8. **Alternatives / variants** (可替代方案 / 变体实施例) — at least two alternative embodiments
9. **Advantages / technical effects** (技术效果 / 有益效果) — must include evidence ids; advantages without evidence are dropped
10. **Examples** (实施例 / 实验数据) — at least one worked example, ideally tied to an experiment in `.evidraft/experiments/`
11. **Diagrams suggestions** (附图建议) — what figures the attorney should request (block diagram, flowchart, state diagram, system architecture, …)
12. **Code traceability** (代码追踪) — table mapping every key technical feature to `file_path:lines`
13. **Inventor questions** (待发明人确认事项) — checklist of things only the inventor can confirm (earliest public disclosure date, third-party dependencies, prior internal disclosure, joint inventors, funding source / contractual obligations, …)

## Required footer

Always append (and never remove):

```
---
## Needs attorney review

- [ ] Confirm jurisdiction(s).
- [ ] Confirm earliest public disclosure / use / sale date.
- [ ] Confirm all named inventors and contributorship.
- [ ] Confirm freedom-to-use of third-party code.
- [ ] Review claim scope.
- [ ] Decide on provisional vs non-provisional filing strategy.

> This disclosure is a *technical write-up* prepared by an AI assistant from the
> code and engineering notes provided. It is not a legal opinion. A registered
> patent agent / attorney must review before any filing decision.
```

## Constraints

- Every "Advantage" / "Technical effect" needs an `evidence_id`.
- No marketing language. Specific, testable, technical statements only.
- The "Needs attorney review" footer is **mandatory** and may not be removed.

## Done criteria

- One H2 section per intended candidate.
- Required footer present.
- Chat output recommends `/scholar:patent-claims` next.
