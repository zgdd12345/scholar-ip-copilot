# Related Work (draft)

> Produced by `/scholar:deepresearch` run dr-2026-05-18-002.
> Every paragraph cites only `citation_key`s present in
> `.evidraft/literature/references.bib` and every numeric / strong claim
> resolves to an `evidence_id` in `.evidraft/evidence/evidence.jsonl`.
> Citation audit: `citation_audit.json` in this directory.

Small-object detection has converged on four mechanistic families. We position our work explicitly against each.

## Training-time auxiliary supervision, dropped at inference

A recent body of work supervises an auxiliary branch only at training, deletes it at inference, and keeps deployment cost identical to a vanilla detector. CFINet (`yuan2023cfinet`) attaches a **Feature Imitation** branch with a supervised-contrastive auxiliary loss to a Faster R-CNN small-object detector and reports state-of-the-art results on SODA-D and SODA-A (`ev_0001`, `ev_0002`). On the DETR side, Mr. DETR (`mrdetr2024`) trains one-to-many prediction routes that are explicitly discarded at inference (`ev_0008`), and RT-DETRv3 (`rtdetrv3_2024`) trains multiple auxiliary branches under hierarchical dense positive supervision without adding inference latency (`ev_0009`). The video-detection analogue CLAB (`clab2025`) confirms the train-vs-inference asymmetry works at the backbone level via contrastive supervision (`ev_0007`). Our work sits in this family but differs along two axes: (i) we keep the *detector* single-stage at inference — CFINet, our nearest neighbour, retains the two-stage Faster R-CNN pipeline; and (ii) our auxiliary signal is a small-object-region map (heatmap / density / grid variants under ablation) applied at the ROI head, rather than a feature-level contrastive imitation. Both axes are explicit in our method section and in the ablation design.

## Coarse-to-fine refinement for small objects

A second family compresses high-resolution computation by predicting candidate locations first and refining only on those regions. QueryDet (`yang2022querydet`) issues cascaded sparse queries: coarse predictions on low-resolution features guide sparse computation on high-resolution features, improving COCO mAP_small by 2.0 and creating a new VisDrone state-of-the-art with 2.3× high-resolution acceleration (`ev_0003`). QueryDet keeps both stages active at inference; the speedup is via sparsity, not via dropping a stage. We share the "spend compute where small objects are" motivation but invert the cost: our auxiliary branch pays at training, not at inference. A combination (sparse-query inference + our training-time aux) is a natural v2.

## Inference-time scale handling

A third family makes no training-time change at all. SAHI (`akyon2022sahi`) slices the input image into overlapping patches, runs the base detector per patch, and merges detections — delivering +6.8 / +5.1 / +5.3 AP on FCOS / VFNet / TOOD with inference-time slicing alone, and +12.7 / +13.4 / +14.5 AP with the slicing-aided fine-tuning variant (`ev_0004`). The mechanism is detector-agnostic and widely adopted but multiplies inference cost by the number of slices. Our approach treats inference cost as a hard constraint and shifts the work to training.

## Faster R-CNN baselines for small-object detection on VisDrone

The two-stage Faster R-CNN baseline on VisDrone has been improved by multi-scale feature integration: MGDFIS (`mgdfis2025`) reports 33.4% mAP, +2 over the Faster R-CNN baseline and +12.5% AP50 (`ev_0005`). UAV-targeted efficient detectors such as RemDet (`remdet2024`) reach 110 FPS on a single RTX 4090 with a +3.4% VisDrone mAP gain over their baseline (`ev_0006`); they are not directly comparable on framework family but bound the inference-cost expectations. We adopt Faster R-CNN + MGDFIS as our primary numerical baseline; our auxiliary ROI branch is orthogonal to MGDFIS's feature fusion and the two should compose.

## Audit trail

A pre-WebSearch LLM-seed retrieval initially flagged an "Object-Aware Aggregation Network (OAN), Yang et al. 2022, ECCV" as our nearest neighbour. Two domain-restricted WebSearch passes (arxiv.org + openaccess.thecvf.com) returned zero matches; the recall was hallucinated (`ev_0010`). The mechanism we attributed to OAN actually lives in CFINet (`yuan2023cfinet`, `ev_0001`), which has now taken its place as the primary comparison anchor. This audit trail is preserved per the EviDraft `superseded`-row convention.
