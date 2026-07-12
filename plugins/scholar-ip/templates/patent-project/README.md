# patent-project template

This directory is a **template**, not a working project. The `patent init` action
materialises this tree (without overwriting existing files) into the user's
project root.

## What lands on disk

```
<project>/
  .evidraft/
    project.yaml                          patent-typed project descriptor
    evidence/evidence.jsonl               append-only evidence store
    patent/
      invention_disclosure.md             primary deliverable: 技术交底书 / TID
      invention_candidates.md             candidates from patent.scout
      prior_art_map.md                    prior art from patent.prior-art
      claim_chart.md                      element-by-element traceability
      claims.md                           draft claims (advisory, not filed text)
      patent_review_report.md             multi-role review output
```

## Primary deliverable: 技术交底书 / Technical Invention Disclosure (TID)

The TID at `.evidraft/patent/invention_disclosure.md` is the **primary**
patent artefact. It is a structured technical write-up handed to a registered
patent agent / attorney as the input for drafting a real patent application.

Each candidate in the TID uses the 13 bilingual (English + 中文) subsections
required by the `patent disclosure` action:

1. Title (技术名称)
2. Field of the invention (技术领域)
3. Background (背景技术)
4. Problem solved (要解决的技术问题)
5. Summary (发明概述)
6. Technical solution (技术方案)
7. Implementation details (具体实施方式)
8. Alternatives / variants (可替代方案 / 变体实施例)
9. Advantages / technical effects (技术效果 / 有益效果)
10. Examples (实施例 / 实验数据)
11. Diagrams suggestions (附图建议)
12. Code traceability (代码追踪)
13. Inventor questions (待发明人确认事项)

## Advisory artefacts

`claims.md` and `claim_chart.md` are **advisory** outputs. They help reviewers
and the attorney understand scope and traceability. They are **not** filing
text and must be rewritten by a registered patent agent / attorney before any
filing decision.

## Attorney review is mandatory

Every TID ends with a "Needs attorney review" checklist and disclaimer. The
plugin refuses to remove it. EviDraft does not produce patentability opinions
or freedom-to-operate analyses; consult counsel.
