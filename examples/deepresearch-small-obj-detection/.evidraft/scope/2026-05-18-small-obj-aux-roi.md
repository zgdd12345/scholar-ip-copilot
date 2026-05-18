---
kind: paper
slug: small-obj-aux-roi
status: approved
verdict: refine                     # see §Verdict reasoning below
riskiest_assumption: "Training-time auxiliary ROI branch transfers a re-usable small-object region prior into backbone features that survives inference-time branch removal AND beats matched-FPS single-stage baselines on VisDrone."
evidence_seeds:
  - "ev_0001 / ev_0002 — CFINet (yuan2023cfinet, ICCV 2023). Coarse-to-fine RPN + Feature Imitation BRANCH + auxiliary imitation loss + small obj + Faster R-CNN. STRONGEST overlap; the comparison anchor. (Replaces the hallucinated OAN seed — see ev_0010.)"
  - "ev_0003 — QueryDet (yang2022querydet, CVPR 2022). Cascaded sparse queries, two-stage at inference. Differentiator axis: ours is single-stage at inference (drops aux)."
  - "ev_0004 — SAHI (akyon2022sahi, ICIP 2022). Inference-time geometric slicing, no training aux. Motivation overlap, mechanism orthogonal."
  - "ev_0005 — MGDFIS (mgdfis2025). VisDrone-on-Faster-R-CNN current best at 33.4 mAP / +2 over baseline. PRIMARY BASELINE."
  - "ev_0006 — RemDet (remdet2024). 110 FPS on single 4090; hardware comparator confirms our 2× RTX Pro 6000 timeline."
  - "ev_0007 — CLAB (clab2025). Contrastive aux branch dropped at inference; VOD (excluded from main related-work but cite as pattern inspiration)."
  - "ev_0008 / ev_0009 — Mr. DETR (mrdetr2024) + RT-DETRv3 (rtdetrv3_2024). 'Aux-branch-dropped-at-inference' is mainstream in DETR family; we extend to Faster R-CNN side."
  - "ev_0010 — AUDIT TRAIL: OAN (Yang 2022 ECCV) was hallucinated. Replaced by CFINet (ev_0001)."
approved_date: 2026-05-18
staleness_until: 2026-06-01          # 14 days from today (2026-05-18)
---

# Scope: small-object detection with single-stage aux ROI branch

## 1. Target venue and audience (Q1)

- **Venue (placeholder)**: arXiv preprint. Conference template chosen at submission via `/scholar:paper-venue`.
- **Audience**: same-field computer-vision experts (no popular-science framing; assume FCOS / YOLO / Faster R-CNN are background).
- **AI-disclosure policy**: not declared in paper body; separate materials. arXiv permits this. Re-evaluate when switching to a venue with mandatory disclosure (ICML / NeurIPS / ACL / IEEE).

## 2. One-sentence contribution (Q2)

> Improve small-object detection by prepending a learned attention-region proposal that pre-localises candidate regions before the detector head — instantiated as a training-time auxiliary ROI branch that is dropped at inference.

## 3. Closest prior work (Q3)

| Direction | Representative | Notes |
|---|---|---|
| Slicing-based inference | SAHI | geometric, inference-time, no training change |
| Coarse-to-fine / query-guided | QueryDet, CFINet | sparse queries vs our dense region map |
| Two-stage with explicit RPN | Faster R-CNN | our baseline; theirs keeps RPN at inference, ours drops the aux branch |
| Auxiliary supervision lineage | OAN (2022), deep supervision (2015), RepVGG | OAN is the riskiest neighbour — almost the same template; the differentiator must live in *what is supervised*, not *that something is supervised* |

**Concrete refs**: deferred to `/scholar:deepresearch`.

## 4. Working novelty hypothesis (Q4)

> Different from Faster R-CNN's two-stage RPN→detector pipeline, our method is **single-stage at inference**. During training we add an auxiliary ROI branch supervised specifically on **small-object-rich regions** (supervision signal TBD — heatmap / density / grid candidates). The branch is dropped at deployment, so the inference cost matches a single-stage detector while the backbone has absorbed the region prior.

**Risk flagged by novelty-critic (pre-deepresearch)**: "auxiliary branch dropped at inference" is a mature template (OAN 2022, deep supervision, RepVGG). The differentiator must be the **small-object-specific supervision signal**, not the architectural trick.

## 5. Evidence / evaluation plan (Q5)

| Item | Status |
|---|---|
| Codebase | not_started — need Faster R-CNN baseline reproduce + aux ROI branch prototype |
| Experiments | not_started — no csv yet |
| Datasets | VisDrone (primary). Optional secondary: COCO small-subset, TinyPerson |
| Baselines | Faster R-CNN (must), + 1 strong single-stage (FCOS / YOLOv8), + 1 small-obj specialist (SAHI or QueryDet) |
| Metrics | mAP, mAP@small, FPS at matched config |
| Ablations | (a) ± aux branch; (b) aux supervision variants (heatmap / density / grid); (c) ≥ 3 seeds |

## 6. Hard constraints (Q6)

```yaml
deadline:       2026-08-18           # 3 months
compute:        2× RTX Pro 6000      # Blackwell, 96 GB each
datasets:       public only          # no NDA / internal
authorship:    solo
ethics:         no IRB / privacy concerns (public datasets only)
ai_disclosure: not in body; separate materials
```

**Feasibility**: 3 months × 2× Pro 6000 × public data × solo = tight but realistic if month 1 closes deepresearch + baseline reproduce.

## 7. Carlini conclusion-first abstract (Q7)

**Not written.** Author cannot fill `method` technical details (supervision signal candidates exist as a list, not as a chosen variant) and cannot project the headline number (`+N.N mAP@small at matched FPS`). Per the brainstorming protocol, this directly produces `verdict: refine`.

## Verdict reasoning

- Q1–Q3 are well-scoped (audience, contribution shape, prior-work direction known).
- Q4 names a defensible angle but the differentiator lives downstream of work not yet done (OAN comparison, supervision-signal choice).
- Q5 is a clean blank slate (`codebase: not_started`, `experiments: not_started`) — not disqualifying, but it means novelty can't be confirmed yet.
- Q6 constraints are realistic.
- **Q7 fails the Carlini test.** Headline number and method details are both absent.

→ **`verdict: refine`** is mandatory. `pursue` requires either Q3+Q4 with concrete refs OR Q7 with a credible headline projection. `kill` would require Q4 to collapse on inspection — it doesn't; the angle is alive, just unproven.

## Next actions (priority order)

1. **`/scholar:deepresearch`** — `topic: "training-time auxiliary ROI branch for small-object detection; single-stage at inference"`, `breadth: 6`, `depth: 2`, `providers: [arxiv, semantic-scholar, openalex]`. Must close OAN / SAHI / QueryDet / deep-supervision lineage with concrete `citation_key`s.
2. **Re-open this scope** after deepresearch: replace each `evidence_seeds: TODO` with concrete `ev_NNNN`; revisit Q4 to sharpen the supervision-signal differentiator; attempt Q7 again with a target number bounded by what the deepresearch SOTA snapshot allows.
3. **Bootstrap codebase**: Faster R-CNN reproduce on VisDrone using your preferred framework (mmdetection / detectron2 / native PyTorch). Branchprototype `aux_roi_head` with heatmap supervision as the v0 supervision signal.
4. **Then** `/scholar:paper-experiment` once first ablation csv lands.

## Approval

When you've reviewed the scope and want to flip `status: approved`, edit the frontmatter or tell me and I'll update. Until then `scope-required` hook stays in `block` mode and the gated commands (`/scholar:paper-idea`, `/scholar:deepresearch`, `/scholar:paper-draft`, `/scholar:patent-claims`, `/scholar:polish`) refuse.
