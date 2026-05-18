<!-- ILLUSTRATIVE EXAMPLE -- /scholar:paper-experiment output for cv-detection-paper. -->

# Result analysis (cv-detection-paper, illustrative)

Means are computed over three seeds (0, 1, 2) for each (dataset, split) cell.

| Metric        | Setting                        | Number | Source (file:row/col)                                   | Evidence id | Notes                                                      |
|---------------|--------------------------------|--------|---------------------------------------------------------|-------------|------------------------------------------------------------|
| mAP@0.5       | Method X, COCO val2017         | 0.612  | experiments/runs/exp_2026_03_01.csv:2-4 / map_50        | ev_0017     | Mean of three seeds.                                       |
| mAP@0.5:0.95  | Method X, COCO val2017         | 0.418  | experiments/runs/exp_2026_03_01.csv:2-4 / map_5095      | ev_0017     | Headline number cited in the abstract.                     |
| mAP@0.5       | Method X, VOC test2007         | 0.823  | experiments/runs/exp_2026_03_01.csv:5-7 / map_50        | ev_0017     | Cross-dataset transfer reading.                            |
| mAP@0.5:0.95  | Method X, VOC test2007         | 0.564  | experiments/runs/exp_2026_03_01.csv:5-7 / map_5095      | ev_0017     |                                                            |
| mAP@0.5:0.95  | Ablation: IoU-aware off, COCO  | 0.402  | experiments/runs/exp_2026_03_02.csv:2-4 / map_5095      | ev_0018     | -1.6 pts vs main; supports the IoU-aware design choice.    |
| mAP@0.5:0.95  | Ablation: IoU-aware off, VOC   | 0.547  | experiments/runs/exp_2026_03_02.csv:5-7 / map_5095      | ev_0018     | Same ablation, VOC side.                                   |

The LaTeX table generated from this analysis lives at
`.evidraft/experiments/tables/main_results.tex` and is `\input`ed from
`manuscript/sections/experiments.tex`.
