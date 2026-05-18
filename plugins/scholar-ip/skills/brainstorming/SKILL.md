---
id: brainstorming
title: "Scope-clarification discipline: question schema, verdict matrix, scope file template, staleness rule"
kind: skill
phase: shared
description: >
  Load when /scholar:brainstorming runs, or when a downstream creative command
  (paper-idea, patent-scout, paper-draft, patent-claims, deepresearch, polish)
  finds the scope file missing or stale. Provides the per-branch question
  schema, the Pursue/Refine/Kill verdict matrix, the canonical scope-file
  template (paper and patent variants, bilingual section labels), and the
  14-day staleness rule.
triggers:
  - "/scholar:brainstorming"
  - "downstream command finds .evidraft/scope/ missing"
  - "downstream command finds scope file stale"
  - "scope-required hook fires"
provides:
  - question-schema-paper
  - question-schema-patent
  - verdict-matrix
  - scope-file-template
  - staleness-rule
allowed_tools: [Read, Glob, Grep, Write, Edit]
hooks: []
references:
  - doc: ../../hooks/scope-required.md
  - doc: ../../commands/brainstorming.md
  - doc: ../using-scholar-ip-copilot/SKILL.md
  - url: "https://github.com/obra/superpowers (skills/collaboration/brainstorming) — interview-style clarification"
  - url: "https://github.com/andrehuang/research-companion — idea-level intake patterns"
---

# brainstorming

## When to use

Pull this skill the moment `/scholar:brainstorming` starts, or whenever a downstream command fails the `scope-required` gate (missing or stale scope file) and the user has to redo this stage. It owns the question schema, the verdict matrix, the scope file template, and the staleness rule. Every other artefact about scope defers to this one for shape.

This skill never drafts method, experiments, related-work prose, or claim text. It only clarifies *what the project is for*.

## Inputs

- `.evidraft/project.yaml` (project type, status, optional `scope.staleness_days`, optional `hooks.scope_required`).
- existing `.evidraft/scope/*.md` (prior iterations — read for context, never overwrite).
- existing `.evidraft/ideas/*.md` (prior ideation, optional).
- user statements during the interview.

## Outputs

- exactly one new file at `.evidraft/scope/YYYY-MM-DD-<slug>.md`.

## Procedure

### 1. Question schema — paper branch (范围澄清 — Paper)

Ask in order, one per message:

| # | Axis | Question (short form) |
|---|---|---|
| 1 | Venue / audience | Target venue and reader background? |
| 2 | One-sentence contribution | If a reviewer asked in one sentence, what is the contribution? |
| 3 | Closest 3 prior works | Name three closest works (`citation_key` if known, else author+year). |
| 4 | Claim of novelty | What is the contrast with each of those three? |
| 5 | Evidence / evaluation | Datasets, metrics, baselines, ablations — what will be shown? |
| 6 | Hard constraints | Deadline, page limit, ethics / IRB / dataset-licence issues? |

Fast-mode subset: rows 2, 5, 6 (the contribution; one concrete success criterion; one hard constraint).

### 2. Question schema — patent branch (范围澄清 — Patent / 技术交底)

Ask in order, one per message:

| # | Axis | Question (short form) |
|---|---|---|
| 1 | Field (技术领域) | What technical field and product context? |
| 2 | Problem (所要解决的技术问题) | What problem does the invention solve? |
| 3 | Inventive step (发明点) | What is the inventive step vs. the closest prior art? |
| 4 | Claim type | Apparatus / method / computer-readable medium (CRM) / system? |
| 5 | Jurisdictions | Target jurisdictions (CN / US / EP / WO / …) and filing horizon? |
| 6 | FTO | Known competitor patents or products that might block freedom-to-operate? |
| 7 | Disclosure status | Already public? Confidential? Employer or funder agreement? |

Fast-mode subset: rows 3, 4, 7 (inventive step; claim type; disclosure status).

### 3. Carlini conclusion-first test (full mode only)

Ask the user to draft the abstract (paper) or 技术交底书 summary (patent) **as if the work were complete**. Mirror it back. Surface, line by line:

- numbers without a source,
- comparatives ("better than", "faster than") without a named baseline,
- novelty claims without a contrasted reference,
- promised artefacts (datasets, code, ablations) that have no evidence seed yet.

Each gap becomes an explicit `TODO` in the scope file or is acknowledged as accepted risk.

### 4. Approaches with tradeoffs

Offer 2–3 candidate approaches to the stated contribution. For each:

- **Scope** — what is in / out.
- **Evidence cost** — how much literature / experimentation / coding effort it implies.
- **Riskiest assumption** — one falsifiable sentence.
- **Fallback** — what to do if that assumption breaks.

Let the user pick one or request another round.

### 5. Verdict matrix (Pursue / Refine / Kill)

Apply after the interview is complete. The verdict is a function of internal consistency, not enthusiasm.

| Verdict | Condition |
|---|---|
| `pursue` | One-sentence contribution is concrete; ≥ 1 contrasted prior reference per novelty claim; an evaluation / disclosure plan exists; no unresolved hard constraint blocks the timeline; riskiest assumption is identified and the fallback is acceptable. |
| `refine` | The contribution is real but at least one of: prior-work contrast is missing, evaluation plan is hand-waved, claim type is undecided, disclosure status is unclear. Another `/scholar:brainstorming` round is needed before downstream work. |
| `kill` | The contribution collapses under the Carlini test (no concrete output, no contrast, or a hard constraint makes the project infeasible). The scope file is still written so the decision is traceable. |

A `pursue` verdict is **not** automatic in fast mode — it is the default assumption, but if the three fast-mode answers fail any condition above, the verdict flips to `refine` or `kill`.

### 6. Scope file template

Path: `.evidraft/scope/YYYY-MM-DD-<slug>.md`.

`<slug>` rules: lowercase, hyphen-separated, ASCII, ≤ 6 words, summarises the contribution (not the field). On collision append `-v2`, `-v3`, etc.

#### Frontmatter (canonical, for both paper and patent)

```yaml
---
kind: paper                # or: patent
status: draft              # promoted to: approved (on explicit user approval)
verdict: pursue            # one of: pursue | refine | kill
riskiest_assumption: "<one falsifiable sentence>"
evidence_seeds: []         # array of citation_key | ev_NNNN | file_path strings the user already trusts
approved_date: null        # ISO date (YYYY-MM-DD) when status flipped to approved
staleness_until: 2026-06-01  # approved_date + staleness_days (default 14)
---
```

Rules:

- `verdict` is set by the brainstormer based on the verdict matrix, not by the user.
- `status` flips from `draft` to `approved` only on explicit user approval; `approved_date` and `staleness_until` are filled at that moment.
- `evidence_seeds` is empty until the user names something concrete. No invention.
- Items containing colons or starting with backticks must be quoted (YAML pitfall).

#### Body — paper branch (canonical section list, bilingual labels where helpful)

```
# Scope — <one-sentence contribution>

## 1. Venue & audience (目标会议 / 期刊与读者)
- venue:
- audience:

## 2. One-sentence contribution (一句话贡献)

## 3. Closest prior work (最接近的现有工作)
- <citation_key or "author, year">: <one-line summary> — contrast: <one sentence>
- ...
- ...

## 4. Claim of novelty (新颖性主张)

## 5. Evidence & evaluation plan (证据与评估方案)
- datasets:
- metrics:
- baselines:
- ablations:

## 6. Hard constraints (硬性约束)
- deadline:
- page limit:
- ethics / IRB / licence:

## 7. Carlini conclusion-first draft (假设已完成 — 摘要草稿)
<user's draft, with gaps flagged inline>

## 8. Approaches considered (备选路径与取舍)
- Approach A — scope / evidence cost / riskiest assumption / fallback
- Approach B — ...
- Chosen: <A | B | C> — reason:

## 9. Verdict & riskiest assumption (结论与最大风险)
- verdict: <matches frontmatter>
- riskiest assumption: <matches frontmatter>
- next command: /scholar:paper-lit
```

#### Body — patent branch (canonical section list, bilingual labels where helpful)

```
# Scope — <one-sentence inventive step>

## 1. Technical field (技术领域)

## 2. Problem solved (所要解决的技术问题)

## 3. Closest prior art (最接近的现有技术)
- <reference>: <one-line summary> — contrast: <one sentence>
- ...

## 4. Inventive step (发明点 / 区别技术特征)

## 5. Claim type (权利要求类型)
- apparatus / method / CRM / system: <chosen>
- rationale:

## 6. Jurisdictions & horizon (目标司法管辖区与时间窗)
- jurisdictions:
- filing horizon:

## 7. Freedom-to-operate (自由实施 / FTO)
- known competitor IP / products:
- concerns:

## 8. Disclosure status (公开状态)
- public yet? (date / venue / form)
- confidentiality / employer / funder agreement:

## 9. Carlini conclusion-first draft (假设已完成 — 技术交底书摘要)
<user's draft, with gaps flagged inline>

## 10. Approaches considered (备选路径与取舍)
- Approach A — scope / evidence cost / riskiest assumption / fallback
- Approach B — ...
- Chosen: <A | B | C> — reason:

## 11. Verdict & riskiest assumption (结论与最大风险)
- verdict: <matches frontmatter>
- riskiest assumption: <matches frontmatter>
- next command: /scholar:patent-scout
```

### 7. Staleness rule

Default: a scope file is **fresh** if `(today - approved_date) <= 14 days`. After 14 days it is **stale** — the user must run `/scholar:brainstorming` again, or explicitly re-confirm by re-setting `approved_date: <today>` and `staleness_until: <today + 14d>`.

Configurable in `.evidraft/project.yaml`:

```yaml
scope:
  staleness_days: 14    # raise or lower as the project's pace demands
```

Downstream creative commands consume this rule via `hooks/scope-required.md`. A `draft` (never-approved) file is treated as missing, not stale.

## Quality checklist

- [ ] Exactly one scope file written per `/scholar:brainstorming` invocation.
- [ ] Frontmatter has all six required keys: `kind`, `status`, `verdict`, `riskiest_assumption`, `evidence_seeds`, `staleness_until` (plus `approved_date` if approved).
- [ ] `kind` is `paper` or `patent`; `status` is `draft` or `approved`; `verdict` is `pursue`, `refine`, or `kill`.
- [ ] Every novelty claim has at least one contrasted prior reference.
- [ ] Carlini draft is present (full mode) and gaps are explicit.
- [ ] 2–3 approaches are recorded with tradeoffs (full mode); the chosen one is named.
- [ ] No invented citations, numbers, or jurisdictions.
- [ ] Body sections match the canonical paper or patent list above.

## Anti-patterns

- Drafting method, related-work prose, claim text, or experiment plans here — that is downstream.
- Asking multiple questions in one turn.
- Issuing `pursue` because the user is enthusiastic rather than because the verdict matrix holds.
- Setting `status: approved` without the user explicitly approving.
- Inventing a `citation_key`, author, year, dataset, number, or jurisdiction to fill a gap.
- Overwriting an existing scope file instead of writing a `-v2` slug.
- Treating a stale file as fresh because the contribution has not changed.
