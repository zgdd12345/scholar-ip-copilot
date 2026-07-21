# Question schemas — paper and patent branches

Ask in order, **one question per message**. Wait for the user to answer before moving on. Two branches; the calling project (`.evidraft/project.yaml -> kind`) determines which.

## Paper branch (范围澄清 — Paper)

| # | Axis | Question (short form) |
|---|---|---|
| 1 | Venue / audience | Target venue and reader background? |
| 2 | One-sentence contribution | If a reviewer asked in one sentence, what is the contribution? |
| 3 | Closest 3 prior works | Name three closest works (`citation_key` if known, else author+year). |
| 4 | Claim of novelty | What is the contrast with each of those three? |
| 5 | Evidence / evaluation | Datasets, metrics, baselines, ablations — what will be shown? |
| 6 | Hard constraints | Deadline, page limit, ethics / IRB / dataset-licence issues? |

**Fast-mode subset**: rows 2, 5, 6 (the contribution; one concrete success criterion; one hard constraint).

## Patent branch (范围澄清 — Patent / 技术交底)

| # | Axis | Question (short form) |
|---|---|---|
| 1 | Field (技术领域) | What technical field and product context? |
| 2 | Problem (所要解决的技术问题) | What problem does the invention solve? |
| 3 | Inventive step (发明点) | What is the inventive step vs. the closest prior art? |
| 4 | Claim type | Apparatus / method / computer-readable medium (CRM) / system? |
| 5 | Jurisdictions | Target jurisdictions (CN / US / EP / WO / …) and filing horizon? |
| 6 | FTO | Known competitor patents or products that might block freedom-to-operate? |
| 7 | Disclosure status | Already public? Confidential? Employer or funder agreement? |

**Fast-mode subset**: rows 3, 4, 7 (inventive step; claim type; disclosure status).
