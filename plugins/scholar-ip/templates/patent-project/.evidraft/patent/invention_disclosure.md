# Technical Invention Disclosure (TID) / 技术交底书

> Primary patent deliverable. This is a structured technical write-up handed
> off to a registered patent agent / attorney as the input for drafting a real
> patent application. It is **not** a filed application, **not** legal advice,
> and **not** itself a patent.
>
> Populate via `workflow:patent.disclosure`. One H2 section per invention candidate
> from `invention_candidates.md`. The 13 required subsections below are the
> per-candidate TID structure (jurisdiction-agnostic; works for US / EP /
> CN-CNIPA / JP / PCT).

---

## C-XXX: TODO Candidate title

### 1. Title (技术名称)

<!-- Concise technical title. No marketing language. -->
TODO

### 2. Field of the invention (技术领域)

<!-- One paragraph: technical field the invention belongs to. -->
TODO

### 3. Background (背景技术)

<!-- What existed before; what the prior approaches are; what problems they
     have. Cite via evidence ids from ../evidence/evidence.jsonl and entries
     in prior_art_map.md. -->
TODO

### 4. Problem solved (要解决的技术问题)

<!-- The specific technical problem this invention solves. One paragraph. -->
TODO

### 5. Summary (发明概述)

<!-- One short paragraph summarising the invention so a domain engineer can
     grasp it in 60 seconds. -->
TODO

### 6. Technical solution (技术方案)

<!-- The core. Enough detail that a person skilled in the art could reproduce
     the invention. Describe inputs, outputs, key steps, key data structures,
     and the relationship between components. -->
TODO

### 7. Implementation details (具体实施方式)

<!-- Concrete embodiment, with file_path and line range references from
     ../code/method_to_code.md and ../evidence/evidence.jsonl. -->

| Step / component | Description | file_path | line_range | Evidence id |
|------------------|-------------|-----------|------------|-------------|

### 8. Alternatives / variants (可替代方案 / 变体实施例)

<!-- At least two alternative embodiments. Each should be a real variant, not
     a re-statement of the main solution. -->

- Variant A: TODO
- Variant B: TODO

### 9. Advantages / technical effects (技术效果 / 有益效果)

<!-- Specific, testable, technical statements. Every advantage MUST cite an
     evidence id. Advantages without evidence are dropped by
     workflow:patent.disclosure. -->

| Advantage | Evidence id | Notes |
|-----------|-------------|-------|

### 10. Examples (实施例 / 实验数据)

<!-- At least one worked example. Ideally tied to an experiment in
     ../experiments/ with concrete numbers and their sources. -->
TODO

### 11. Diagrams suggestions (附图建议)

<!-- What figures the attorney should request from the inventor. -->

- [ ] Block diagram of the overall system
- [ ] Flowchart of the core procedure
- [ ] State / sequence diagram (if applicable)
- [ ] Data-structure or schema figure (if applicable)
- [ ] Other: TODO

### 12. Code traceability (代码追踪)

<!-- Map every key technical feature to a file_path and line range. -->

| Feature | file_path | line_range | Evidence id | Notes |
|---------|-----------|------------|-------------|-------|

### 13. Inventor questions (待发明人确认事项)

<!-- Only the inventor can answer these. -->

- [ ] Earliest public disclosure / use / sale date?
- [ ] Any prior internal disclosure (talks, demos, papers, blog posts)?
- [ ] All named inventors and their contributions confirmed?
- [ ] Joint inventors from other organisations?
- [ ] Third-party dependencies and their licenses confirmed?
- [ ] Funding source or contractual obligations affecting IP ownership?
- [ ] Any related provisional or non-provisional filings already in flight?

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
