<!-- ILLUSTRATIVE EXAMPLE -- fictional literature matrix. -->

# Literature matrix (cv-detection-paper, illustrative)

| Paper (citation_key)        | Year | Venue                     | Problem                                  | Method                            | Datasets       | Key Result                                   | Gap                                                              | Evidence ids |
|----------------------------|------|---------------------------|------------------------------------------|-----------------------------------|----------------|----------------------------------------------|------------------------------------------------------------------|--------------|
| smith2024examplekey        | 2024 | J. Illustrative Vision    | Anchor-free detection on COCO            | Per-location distance regression  | COCO val2017   | mAP@0.5:0.95 of 0.41 (anchor-free baseline)  | No IoU-aware classification; per-level heads independent.        | ev_0001      |
| chen2023anchorfreebaseline | 2023 | Imaginary Conf. on CV     | Lightweight anchor-free heads            | Shared per-level tower            | COCO, VOC      | ~40% head parameter reduction vs independent | Lacks distribution-focal decoding; centerness on cls branch only.| ev_0002      |
