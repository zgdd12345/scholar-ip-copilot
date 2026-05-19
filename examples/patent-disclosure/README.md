# Example: patent-disclosure (illustrative)

> **All content in this directory is illustrative and fictional.**
> Inventor names, prior-art references (PA-01, PA-02), the
> ``Adaptive Cosine Warmup with Momentum Scaling'' invention itself,
> and every claim element are synthetic. The directory exists only to
> show what an EviDraft patent project looks like after running the
> full `/patent-*` workflow on a small synthetic codebase. Nothing in
> this directory is legal advice, a patentability opinion, or filed
> text.

## What this example shows

A complete EviDraft patent project after the user has run:

```
/scholar:patent-init
/scholar:patent-scout
/scholar:patent-prior-art
/scholar:patent-disclosure       # 技术交底书 (TID) -- primary deliverable
/scholar:patent-claims           # advisory
/scholar:patent-review
```

The primary deliverable is the bilingual TID at
`.evidraft/patent/invention_disclosure.md`. The claims, the claim
chart, and the multi-role review report are advisory artefacts to help
an attorney.

## Layout

```
patent-disclosure/
├── src/optim/scheduler.py             AdaptiveCosineWarmupMomentumScaler (fictional)
├── configs/scheduler.yaml             scheduler hyper-params
└── .evidraft/
    ├── project.yaml                   project_type: patent, jurisdiction: US
    ├── evidence/evidence.jsonl        4 records (code, paper, note)
    └── patent/
        ├── invention_disclosure.md    populated 13-section bilingual TID
        ├── invention_candidates.md    C-001
        ├── prior_art_map.md           PA-01, PA-02 (fictional)
        ├── claim_chart.md             5 rows mapped to spec + code
        ├── claims.md                  1 independent + 3 dependent claims
        └── patent_review_report.md    5 reviewer roles + Verdict: NEEDS_WORK
```

## Walk-through (what each command produces in this example)

### 1. `/scholar:patent-init`

Scaffolds `.evidraft/patent/` and writes
`invention_disclosure.md` with all 13 section headers empty, plus the
"Needs attorney review" checklist at the bottom. Sets
`project_type: patent` in `.evidraft/project.yaml`. Chat output ends
with:

```
Next:
  /scholar:patent-scout       enumerate invention candidates from code + docs
```

### 2. `/scholar:patent-scout`

Reads the source tree and produces `invention_candidates.md`. In this
example it surfaces a single candidate `C-001 Adaptive Cosine Warmup`.

### 3. `/scholar:patent-prior-art`

Writes `prior_art_map.md`. For this example it surfaces two fictional
references (PA-01, PA-02) and identifies the closest overlap (linear
momentum warmup in PA-01; independent momentum decay in PA-02).

### 4. `/scholar:patent-disclosure` (primary deliverable)

Produces the **TID (技术交底书)** in
`.evidraft/patent/invention_disclosure.md`. Each of the 13 sections is
**bilingual**: an `EN` block and a `ZH (中文)` block. The "Needs
attorney review" footer is always present at the bottom and the
plugin refuses to remove it.

The 13 sections in this example:

1. Title (技术名称)
2. Field of the invention (技术领域)
3. Background (背景技术)
4. Problem solved (要解决的技术问题)
5. Summary (发明概述)
6. Technical solution (技术方案)
7. Implementation details (具体实施方式) -- cites
   `src/optim/scheduler.py:36-73` and `:59-73`
8. Alternatives / variants (可替代方案 / 变体实施例) -- two variants
9. Advantages / technical effects (技术效果 / 有益效果) -- every
   bullet is tagged with an evidence id
10. Examples (实施例 / 实验数据) -- references ev_0104
11. Diagrams suggestions (附图建议)
12. Code traceability (代码追踪) -- table mapping every feature to a
    file and line range
13. Inventor questions (待发明人确认事项)

### 5. `/scholar:patent-claims` (advisory)

Writes `claims.md` (1 independent + 3 dependent claims) and updates
`claim_chart.md` with one row per claim element. The footer

```
> Draft claims. Not filed text. Must be reviewed and adapted by a registered
> patent agent / attorney before any filing decision.
```

is always present.

### 6. `/scholar:patent-review`

Runs 5 reviewer roles (patent engineer, claim drafter, novelty critic,
methodology reviewer, skeptical examiner) and writes
`patent_review_report.md`. In this example the report opens with the v0.3 **Structured audits (pre-pass)** block and ends with `Verdict: NEEDS_WORK` + top-3 next actions.

This example now ships the full v0.3 structured-audit fixture:

- `.evidraft/patent/claims_parsed.json` — `claim-parser` output: 4 claims (c1 independent + c2/c3/c4 dependent), 7 total elements, antecedent_chain, 1 info-severity TERMINOLOGY_DRIFT warning. Plus paired `claim_parse-20260518T140100Z.log`.
- `.evidraft/patent/claim_chart-20260518T140105Z.json` — `claim-chart-builder` output: 7 rows. 1 high-risk row triggered by the **no-support override** on c2[a] (no spec or code support), demonstrating the documented rule. 2 medium-risk rows with `suggested_revision` populated; 4 low-risk rows with `suggested_revision: null`.
- `.evidraft/patent/novelty_audit-20260518T140110Z.{findings.json,log}` — `novelty-heuristics` output: 6 findings (4 warn, 2 info), per-claim `verdict_hint` ∈ {narrow, redraft, narrow, novel} — **advisory only**, never a legal conclusion. The `advisory_only` framing ships verbatim in both files; the log carries the `# novelty_audit log — advisory only; not legal advice; attorney review required.` header.
- `.evidraft/patent/patent_review_report.md` — v0.3 6-role panel (engineer / drafter / novelty critic / methodology / examiner / **consistency-checker** new at v0.4). Opens with a `## Structured audits (pre-pass)` block summarising the three structured outputs, then runs the panel. `Verdict: NEEDS_WORK` forced by (a) c2 `verdict_hint: redraft` and (b) c2[a] high-risk row.

The findings are illustrative — no real attorney review was performed and no claim has been filed. The format is what a real `/scholar:patent-claims` + `/scholar:patent-review` would produce.

## Consistency notes

- All `file_path` + line-range cites in `evidence.jsonl`, the TID's
  Section 12, and the claim chart point to real lines in
  `src/optim/scheduler.py`.
- BibTeX-style cite `loshchilov2022cosineexample` (ev_0103) and the
  prior-art ids `PA-01`, `PA-02` are fictional.
- The TID retains its mandatory bilingual section headers and the
  "Needs attorney review" footer.
