# Scope file template

Path: `.evidraft/scope/YYYY-MM-DD-<slug>.md`.

`<slug>` rules: lowercase, hyphen-separated, ASCII, ≤ 6 words, summarises the contribution (not the field). On collision append `-v2`, `-v3`, etc.

## Frontmatter (canonical — both paper and patent)

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

## Body — paper branch (canonical section list, bilingual labels where helpful)

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

## Body — patent branch (canonical section list, bilingual labels where helpful)

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
