# Example: end-to-end `/scholar:deepresearch` on a small-object-detection topic

End-to-end fixture for the EviDraft v0.3 patent-depth + v0.2 host-native skills migration. This example was produced by a real dogfood run (May 2026) of `/scholar:brainstorming` followed by `/scholar:deepresearch` Stages 1–6 against a synthetic but representative research topic.

This is a historical fixture. Its scope gate and six-stage full-run behavior describe
the captured 2026 run, not the EviDraft 3.0 default workflow.

> **Topic.** "Training-time auxiliary ROI branch for small-object detection; single-stage at inference."
>
> **Frame the project gives.** A researcher starting from a one-sentence contribution but with no codebase, no experiments, and a working hypothesis that "auxiliary branch dropped at inference" is novel for small-object detection on a Faster R-CNN baseline.
>
> **Frame the dogfood gives.** That hypothesis is **not novel as originally stated**: CFINet (ICCV 2023) already does aux + small-object + Faster R-CNN. The real defensible novelty axes — single-stage at inference + ROI-region-map supervision — are surfaced by the run, and the scope is updated accordingly.

## What this fixture exercises

| EviDraft component | Demonstrated by |
|---|---|
| `/scholar:brainstorming` | `.evidraft/scope/2026-05-18-small-obj-aux-roi.md` — 7-question paper-branch flow, Carlini conclusion-first test, `verdict: refine`, approval cycle |
| `scope-required` hook | scope `status: approved` + `approved_date` + `staleness_until` — the gate that lets `/scholar:deepresearch` proceed |
| `/scholar:deepresearch` Stage 1 (Frame) | `.evidraft/literature/plan.yaml` — 6 sub-queries, year window, inclusion/exclusion keywords, breadth/depth |
| `/scholar:deepresearch` Stage 2 (Retrieve) | `.evidraft/literature/candidates.jsonl` — 10 verified rows + 1 audit-trail `superseded` row (see below) |
| `/scholar:deepresearch` Stage 3 (Screen) | `.evidraft/literature/screening_log.csv` — PRISMA-style decisions including a real `include_with_caveat` case (CLAB, video-modality) |
| `/scholar:deepresearch` Stage 4 (Cluster) | `.evidraft/literature/clusters.yaml` + `evidence_map.json` — 5 method-family clusters, canonical contrast paper per cluster |
| `/scholar:deepresearch` Stage 5 (Critique) | `.evidraft/literature/critique/cl_{01,02,03,04}.md` — per-paper SWOT + "Delta vs our angle" |
| `/scholar:deepresearch` Stage 6 (Synthesise) | `.evidraft/literature/related_work.draft.md` (5 paragraphs, every claim cites both `citation_key` + `evidence_id`) + `citation_audit.json` (5/5 PASS) |
| `scholar-search` skill (Path A + Path B) | Demonstrated end-to-end: WebSearch with `allowed_domains: [arxiv.org, openaccess.thecvf.com]` for discovery, then WebFetch on the abs URLs for metadata (see scope's `evidence_seeds` for the citation_keys this produced) |
| `verified: false` / `superseded` audit trail | `cand_0001` and `ev_0010` — preserved record of an LLM-seed hallucination (`OAN, Yang 2022 ECCV`) that was falsified by two domain-restricted WebSearch passes. The mechanism we attributed to OAN actually lives in CFINet. |
| Evidence discipline | `references.bib` has the 8 `citation_key`s used in the draft; every paragraph in `related_work.draft.md` resolves through `citation_audit.json` |

## What this fixture does NOT cover

- `/scholar:paper-init` — the project.yaml here is hand-tuned for the deepresearch focus; for a complete scaffold-from-scratch see `examples/cv-detection-paper/`.
- `/scholar:paper-code-audit`, `/scholar:paper-experiment` — no code or experiment data in this fixture (the dogfood ran on the *idea* stage, before code or experiments exist).
- `/scholar:paper-draft`, `/scholar:paper-check`, `/scholar:paper-venue` — manuscript assembly. `related_work.draft.md` is the deepresearch output; turning it into `manuscript/sections/related_work.tex` is the next user action.
- Patent flow — see `examples/patent-disclosure/`.

## Stage-by-stage PRISMA snapshot

```
candidates_retrieved:        10 (via WebSearch on 6 sub-queries; allowed_domains = arxiv + cvf)
after_dedup:                 10 (no exact dups; 1 superseded LLM-seed row archived as audit trail)
screened_in:                  9
screened_in_with_caveat:      1 (CLAB; video modality, mechanism-cite only)
screened_out:                 0
clustered:                   10 → 5 clusters (cl_01..cl_05)
critiqued (per-paper SWOT):   7 papers across 4 active clusters (cl_05 is survey-only)
cited_in_draft:               8 unique citation_keys in 5 paragraphs
citation_audit:               5/5 paragraphs PASS
```

## Key research takeaway from the run

The cluster-01 summary table (in `critique/cl_01.md`) compares CFINet, CLAB, Mr. DETR, RT-DETRv3, and the planned work along four axes (aux branch / dropped at inference / small-object specific / Faster R-CNN baseline) plus supervision signal. **No existing row simultaneously ticks all four**; the gap is precisely where the project's novelty must live, plus an explicit choice of supervision signal (heatmap / density / grid — to be ablated). This is the kind of structural finding that justifies upgrading the scope verdict from `refine` toward `pursue` on a re-open.

## Reproducing this fixture

```bash
# In a fresh project directory:
/scholar:using                                  # orientation
/scholar:paper-init                             # scaffold .evidraft/ + manuscript/
/scholar:brainstorming                          # 7-question paper flow; produces .evidraft/scope/
# (approve the scope manually: status: draft -> approved)
/scholar:deepresearch                           # 6 stages; produces everything under .evidraft/literature/
```

The numbers above (10 candidates, 5 clusters, 8 citations) are illustrative; a real run with different breadth/depth or sub-queries will produce a different cardinality. The *structure* — plan → candidates → screening → clusters → critique → draft + citation audit — is the invariant.

## Audit trail (what this fixture preserves about its own limits)

- The dogfood ran in May 2026 with `WebSearch` + `WebFetch` only. No external API key was used.
- 4 BibTeX entries (mgdfis2025, remdet2024, clab2025, mrdetr2024, rtdetrv3_2024) carry a `TODO: authors` placeholder — full author lists need a follow-up WebFetch on each arXiv abs page. The `citation_audit.json` is structurally PASS; populating these authors is the next minor task before the draft can be compiled.
- The OAN audit-trail (`cand_0001` superseded; `ev_0010` note) is preserved deliberately. A future maintainer or reviewer can see *how* the run caught its own hallucination; that's part of the fixture's value, not a bug.
- All `critique/cl_*.md` SWOT bullets are tagged `[TODO: PDF]` where they would require reading the full paper PDF to verify beyond the abstract. The skill's anti-pattern guidance ("SWOT bullets must trace to a section / figure / table, not abstract paraphrase") is honored by leaving these flags in place rather than hiding them.
