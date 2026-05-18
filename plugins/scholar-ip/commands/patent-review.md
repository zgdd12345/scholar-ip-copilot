---
id: patent-review
title: "Multi-role review of disclosure and claims"
kind: command
slash: /scholar:patent-review
phase: patent
outputs:
  - path: .evidraft/patent/patent_review_report.md
allowed_tools: [Read, Glob, Grep, Write, Edit]
hooks: [evidence-consistency]
subagents: [patent-engineer, claim-drafter, novelty-critic, methodology-reviewer, evidence-auditor]
references:
  - doc: ../skills/patent-disclosure/SKILL.md
  - doc: ../skills/patent-claims/SKILL.md
---

# /scholar:patent-review

Run a multi-role review pass over `invention_disclosure.md`, `claims.md`, and
`claim_chart.md`. Produce `.evidraft/patent/patent_review_report.md`.

## Reviewer roles

For each role, generate a section in the report.

1. **Patent engineer** — Are the technical solution, alternatives, examples, and diagrams sufficient to teach the invention to a skilled person?
2. **Claim drafter** — Are claims clear, properly antecedent, with consistent terminology? Are dependent claims actually narrower? Any 112(b)-style indefiniteness risk?
3. **Novelty critic** — For each independent claim element, what is the strongest prior art overlap? Where is the line of distinction?
4. **Methodology / technical reviewer** — Does the disclosure match the code? Any mismatches against `method_to_code.md`?
5. **Skeptical examiner** — Imagine you reject this. What is the rejection reasoning, and what amendment closes it?

## Output structure

```
# Patent review report

Generated: <iso datetime>
Targets:
- disclosure: .evidraft/patent/invention_disclosure.md
- claims:     .evidraft/patent/claims.md
- chart:      .evidraft/patent/claim_chart.md

## 1. Patent engineer
- Gaps:
- Suggestions:

## 2. Claim drafter
- Antecedent / consistency issues:
- Dependent-claim narrowness check:
- Suggestions:

## 3. Novelty critic
- Per-element prior-art overlap:
- Distinguishing language suggestions:

## 4. Methodology / technical reviewer
- Code vs disclosure mismatches:
- Recommendations:

## 5. Skeptical examiner
- Strongest rejection scenario:
- Suggested amendments:

## Overall verdict
- Verdict: READY_FOR_ATTORNEY / NEEDS_WORK
- Top-3 next actions:
```

## Constraints

- No legal opinions. "Verdict" describes maturity for attorney review, not patentability.
- Every "mismatch" / "overlap" must point to a file or evidence id.

## Done criteria

- Report exists.
- Verdict is one of the two enumerated values.
- Chat output prints the verdict and the top-3 next actions.
