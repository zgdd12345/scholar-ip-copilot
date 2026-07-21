---
id: paper-explanation
title: Evidence-grounded single-paper explanation
kind: skill
phase: shared
description: >
  Read one paper at full-text level, explain it at beginner, graduate, or
  reviewer depth, and optionally compare it with verified related work.
triggers:
  - "workflow:research.explain"
  - "explain this paper"
  - "close-read this paper"
  - "explain the equations in this paper"
provides:
  - paper-source-resolution
  - three-mode-explanation
  - evidence-labelled-reading-note
  - conditional-related-work-comparison
allowed_tools: [Read, Glob, Grep, Write, Edit, WebSearch, WebFetch]
policies: [workspace-safety]
references:
  - doc: capability:scholar-search
---

# paper-explanation

## Source contract

Accept a local PDF, arXiv identifier or URL, DOI, or paper URL. Preflight a local path
before reading it. Resolve one unique paper and verify title, authors, year, venue,
canonical URL, and research problem. Readable full text supports a complete explanation.
When full text is unavailable, write a limited evidence-boundary note from verified
identity and any canonical abstract; do not infer unseen methods, equations, figures,
tables, or results.

Preserve extraction defects and absent material as explicit gaps. The limited note names
the readable material, unsupported requested coverage, and recovery action and returns
status `complete_with_gaps`. Request a better source without withholding this useful
boundary record.

## Explanation modes

Use `graduate` by default:

- `beginner` prioritises terminology, prerequisites, intuition, and careful analogies;
- `graduate` balances method mechanics, equations, experiments, limitations, and
  reproduction guidance;
- `reviewer` prioritises assumptions, novelty boundaries, missing controls, validity,
  statistical support, and overclaiming risk.

Ordinary beginner and graduate explanations do not require external research. Expand
related research only in reviewer mode or the user explicitly requests comparison,
similar methods, subsequent work, improvements, or current alternatives.

## Best-effort execution

The coordinator may perform the explanation directly or delegate bounded independent
checks when useful. Delegation is adaptive: it has no required worker count, fixed
dependency waves, or prescribed retry count. Lack of delegation capacity is not a
reason to refuse an explanation that can be completed in the current session. A failed
optional check becomes a named gap, while readable source-paper analysis continues.

`paper-explainer` owns synthesis and the final destination. When the conditional
external branch runs, reuse `literature-reviewer` for bounded discovery and comparison.
No intermediate private runtime resource is required. Only the final owner receives the
resolved destination, and at most one note is written.

## Note contract

Cover the requested portions of:

1. paper identity and one-sentence takeaway;
2. research problem, background, and prerequisites;
3. core contributions and claim boundaries;
4. method walkthrough;
5. key equations with symbol definitions;
6. experimental setup and results;
7. limitations, failure modes, and reproduction notes;
8. learning-check questions when useful; and
9. sources and verification record.

When the external branch runs, add similar or contemporary methods and subsequent,
improved, or current alternatives. These sections are conditional, not filler required
for an ordinary explanation.

Use explicit evidence labels: `[Paper section ...]`, `[Equation ...]`,
`[Figure ...]`, and `[Table ...]` for source-paper evidence; `[External: citation]`
and `[External: official-code]` for verified external evidence; `[Interpretation]` for
derivation, analogy, or assessment; and `[abstract-only]` for claims supported only by
a verified external abstract. Never present interpretation as an author statement.

For external work, verify a canonical page before inclusion and record title, year,
link, relationship, concrete methodological difference, search date, and search scope.
Discovery snippets are not evidence. Do not make unbounded latest or state-of-the-art
claims.

## Collision contract

Never overwrite a non-empty note silently. Offer reuse, a unique dated sibling, or
explicitly confirmed replacement. Re-check the target immediately before writing and
perform at most one final write after workspace preparation.

## Status contract

Return exactly one status:

- `complete` when the requested explanation was written from readable source evidence
  without a material requested omission;
- `complete_with_gaps` when a useful note was written but named source, optional-check,
  or requested-comparison gaps remain;
- `blocked` when source identity or a safe output destination cannot be established and
  no note is written. Blocked is limited to unresolved paper identity or an unsafe output
  destination.

An external-search shortfall requested by the user normally yields
`complete_with_gaps`, not refusal, when the source-paper explanation remains useful.

## Quality checklist

- Source identity and readable full text were checked.
- Claims are separated into paper, interpretation, and external evidence.
- Every explained equation defines symbols or names the extraction gap.
- Conditional external work is verified and bounded when requested.
- Existing non-empty output is preserved without explicit replacement approval.
- The final status and recovery action match the artefact actually produced.
