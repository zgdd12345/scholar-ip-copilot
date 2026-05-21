---
id: patent-disclosure
title: "Technical Invention Disclosure (TID / 技术交底书) drafting discipline"
kind: skill
phase: patent
description: >
  Load when /scholar:patent-init, /scholar:patent-scout, or /scholar:patent-disclosure run. Provides
  the full TID section specification in EN + ZH, the inventor-question
  prompts (earliest public disclosure, joint inventors, funding, third-party
  dependencies), what counts as enabling disclosure, how to write Alternatives
  that actually broaden scope, and the anti-patterns (marketing prose, vague
  functional language) that block a draft.
triggers:
  - "/scholar:patent-init"
  - "/scholar:patent-scout"
  - "/scholar:patent-disclosure"
  - "writing invention_disclosure.md"
  - "drafting TID section"
provides:
  - tid-section-spec
  - inventor-question-prompts
  - enabling-disclosure-rules
  - alternatives-broadening-recipe
  - tid-anti-patterns
allowed_tools: [Read, Glob, Grep, Write, Edit]
hooks: [citation-guard, evidence-consistency, sensitive-file-guard]
references:
  - doc: ../../../../docs/legal-and-ethics.md
  - doc: ../evidence-check/SKILL.md
  - doc: ../codebase-audit/SKILL.md
  - doc: ../patent-claims/SKILL.md
---

# patent-disclosure

## When to use

Load whenever you are drafting, extending, or auditing `.evidraft/patent/invention_disclosure.md`. The TID (技术交底书 / Technical Invention Disclosure) is the **primary** patent deliverable: it is the hand-off document for a registered patent agent / attorney. Draft claims and the claim chart are secondary artefacts; the attorney can rewrite them, but the TID is what the attorney needs from the inventor.

The TID is jurisdiction-agnostic. The same structure works for US (USPTO), EP (EPO), CN (CNIPA 技术交底书), JP (JPO), and PCT.

## Inputs

- existing `.evidraft/patent/invention_disclosure.md` template (from `/scholar:patent-init`)
- `.evidraft/patent/invention_candidates.md` (from `/scholar:patent-scout`)
- `.evidraft/code/method_to_code.md` + `.evidraft/code/repo_summary.md`
- `.evidraft/evidence/evidence.jsonl` (filter `type=code`, `type=experiment`)
- `.evidraft/project.yaml` (jurisdiction, inventors)
- user-supplied `inventors.yaml`, internal design docs

## Outputs

- `.evidraft/patent/invention_disclosure.md` — one H2 per candidate, plus the mandatory "Needs attorney review" footer

## Procedure

### 1. Full TID section spec (EN + ZH)

For each invention candidate, write one H2 block with these sub-sections, in order. Both languages are listed so a bilingual attorney intake form maps cleanly; in a given document use whichever language the project's `language` field declares, but keep the headers parallel.

| # | EN heading | ZH heading | What to write |
|---|---|---|---|
| 1 | Title | 技术名称 | A specific technical title. Not a marketing name. Include the **type of system** ("method for", "system for", "apparatus for") so claim drafting downstream has a stable preamble seed. |
| 2 | Field of the invention | 技术领域 | One paragraph naming the technical field (e.g. "object detection in computer vision systems") at the level a `G06` / `G06V` IPC class would. |
| 3 | Background | 背景技术 | What existed before. Cite prior internal work, related products, key prior-art references (use evidence ids of `type=paper` or `type=patent`). Do **not** trash competitors. State the technical limitations factually. |
| 4 | Problem solved | 要解决的技术问题 | One paragraph: the concrete technical problem. Examples: "real-time inference under 30 ms on edge devices with batch=1"; "training divergence under label noise > 20%". Avoid abstract problems like "improving user experience". |
| 5 | Summary | 发明概述 | 3-5 sentences: the inventive concept in plain technical English. A skilled reader should grasp the gist without diagrams. End with one sentence of the technical effect (without numbers — numbers go in §9). |
| 6 | Technical solution | 技术方案 | The **core** section. Step-by-step description of the mechanism, sufficient for a skilled person to reproduce it. Use numbered steps. Reference equations if they are essential. This is where "enabling disclosure" is decided. |
| 7 | Implementation details | 具体实施方式 | Concrete embodiment: data structures, function signatures, configs, hyperparameters. Every paragraph references `file_path` + line range from `method_to_code.md` / `evidence.jsonl`. |
| 8 | Alternatives / variants | 可替代方案 / 变体实施例 | ≥ 2 alternative embodiments. See §3 below for the recipe. |
| 9 | Advantages / technical effects | 技术效果 / 有益效果 | Each bullet pairs a technical effect with an evidence id. Quantitative effects ("X reduces inference time from 80 ms to 23 ms on Y") preferred over qualitative. Advantages without evidence are dropped. |
| 10 | Examples | 实施例 / 实验数据 | ≥ 1 worked example. Where possible, tie to a row in `.evidraft/experiments/result_analysis.md`. Show inputs, the steps, outputs. |
| 11 | Diagrams suggestions | 附图建议 | List the figures the attorney should request: block diagram (system architecture), flowchart (method steps), state diagram (lifecycle), data structure diagram, timing diagram. Do not draw them — name them and describe what they show. |
| 12 | Code traceability | 代码追踪 | Table mapping every key technical feature -> `file_path:lines` + `ev_NNNN`. Mirror the structure of `method_to_code.md`. |
| 13 | Inventor questions | 待发明人确认事项 | Checklist of items only the inventor can confirm. See §2 below. |

Style rules across all sections:

- Specific and testable. No marketing.
- One technical idea per paragraph.
- Use "the method" / "the system" / "the apparatus" — these are the claim-preamble seeds.
- Quote configs and code by exact name; do not paraphrase variable names.

### 2. Inventor-question prompts

Section 13 of every TID candidate ends with this checklist. Treat each item as a question the inventor must answer before the TID is handed off:

```
## 13. Inventor questions (待发明人确认事项)

- [ ] Earliest public disclosure date (talk, blog post, demo, GitHub release, paper preprint, customer-facing deployment). Provide the exact date and the venue. If none yet, write "none to date".
- [ ] Prior internal disclosure inside the organisation (internal review, design doc, code review, sales pitch). Provide dates and audience.
- [ ] Named inventors with substantive contribution to the inventive concept (not just implementation labour). For each: name, affiliation, email, the part(s) of §6 / §7 they contributed.
- [ ] Funding source / contract obligations. Was the work funded by a government grant (e.g. SBIR/STTR, NIH, EU H2020, 国家自然科学基金), under a CRADA, or under a customer contract with assignment / march-in clauses?
- [ ] Third-party code or model dependencies used in the embodiment. For each: project, license, version, whether it appears in the inventive part (vs. plumbing).
- [ ] Pre-existing IP from the same inventors or organisation that this builds on (patent numbers, applications).
- [ ] Trade-secret considerations: any portion the inventor prefers not to disclose in a published patent (would prefer trade-secret protection).
- [ ] Jurisdiction priority (US / EP / CN / JP / PCT). If unsure, default to PCT and let the attorney advise.
- [ ] Co-assignee / joint-owner relationships (co-inventor at different affiliation, joint-development agreement).
- [ ] Known prior art the inventor is aware of, even if not yet in `prior_art_map.md`.
```

Rules:

- Never fill these in for the inventor. They appear as unchecked checkboxes until a human inventor confirms.
- "Earliest public disclosure date" matters legally — flag missing as the highest-priority gap.
- Joint-inventor disputes are common: ask for each named inventor's contribution by TID section.

### 3. Enabling disclosure: what counts

A TID section §6 + §7 is "enabling" when a skilled person in the field can build the embodiment from the document plus general knowledge in the field. Concretely:

- Every non-obvious step is named explicitly. Avoid "the model is trained" — say which loss, which optimiser family, which initialisation strategy, on what data.
- Hyperparameters that materially affect behaviour are listed with values (or ranges) and a rationale. "Learning rate 3e-4 with cosine decay over 200 epochs" beats "trained with standard hyperparameters".
- Where the invention uses a known building block (e.g., "a transformer encoder"), cite the prior art (`type=paper` evidence) instead of re-deriving it. The block can be enabling by reference.
- Where the invention is the building block (a new layer, new operator, new data structure), pseudocode or equations are mandatory. Function signatures from §12 Code traceability count as enabling evidence, not as substitutes for explanation.
- Failure modes and operating ranges are stated (e.g., "the method assumes input resolution ≥ 224×224; below this, accuracy degrades").

A non-enabling section is rejected by the attorney; better to catch it in TID review.

### 4. Alternatives that actually broaden scope

Section 8 (Alternatives / variants) is what gives a future patent claim scope beyond the single embodiment. Bad alternatives are restatements; good alternatives are **technically different mechanisms that achieve the same effect**.

Recipe — for each axis below where applicable to the invention, list one alternative:

| Axis | Example "narrow" embodiment | Example alternative |
|---|---|---|
| Substitutable component | "uses a transformer encoder" | "uses a CNN backbone with comparable receptive field" |
| Substitutable algorithm | "uses gradient descent" | "uses any iterative first-order optimiser including Adam, RMSProp, SGD with momentum" |
| Substitutable hardware | "executes on GPU" | "executes on any SIMD-capable accelerator including TPU, NPU, or DSP" |
| Substitutable data type | "32-bit floats" | "any numerical representation including bfloat16, int8 quantised, or block floating point" |
| Substitutable I/O | "image input" | "any 2D sampled signal including LiDAR depth maps, ultrasound" |
| Order / pipelining | "step A then step B" | "step A and step B in either order, including in parallel" |
| Equivalent objective | "loss is cross-entropy" | "loss is any classification-suitable objective including hinge, focal, or label-smoothed cross-entropy" |

Rules:

- Each alternative must remain technically plausible. Listing impossible alternatives ("could be done by hand") harms the disclosure.
- Two alternatives minimum. More is better up to ~5; beyond that, you are likely listing trivial variations.
- Every alternative should be evaluable for prior-art coverage in `claim_chart.md` later. If you cannot conceive of how to evaluate it, it is too vague.

### 5. Mandatory footer

Every TID ends with (and the plugin must never remove):

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

See `docs/legal-and-ethics.md` for the policy that requires this footer.

## Quality checklist

- [ ] One H2 per candidate.
- [ ] All 13 sub-sections present per candidate (or marked `n/a` with one-line reason).
- [ ] Every advantage in §9 has an evidence id.
- [ ] §8 lists ≥ 2 alternatives that vary along distinct axes.
- [ ] §7 and §12 reference real `file_path:lines` from `evidence.jsonl`.
- [ ] §13 inventor checklist is present and unchecked.
- [ ] Mandatory footer present and unmodified.
- [ ] No marketing verbs (`revolutionary`, `groundbreaking`, `world-leading`, `best-in-class`).
- [ ] No vague functional language ("means for processing X" without describing the means).

## Anti-patterns

- Marketing prose. "Our revolutionary approach achieves unprecedented results." -> rewrite as "The method achieves X on benchmark Y (ev_NNNN)."
- Functional-only descriptions. "A component that performs detection" tells the attorney nothing — describe the mechanism.
- Re-using the abstract of a paper as §5 Summary. The TID summary is for the engineer / attorney, not the reviewer.
- Filling §13 inventor questions on the inventor's behalf.
- Listing trivial "alternatives" ("could also be coded in C++"). Alternatives must be mechanistic substitutes.
- Including advantages without evidence ids.
- Dropping the "Needs attorney review" footer.
- Disclosing third-party trade secrets or confidential data the inventor does not have a right to disclose.
