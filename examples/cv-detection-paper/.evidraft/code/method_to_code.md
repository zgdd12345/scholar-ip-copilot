<!-- ILLUSTRATIVE EXAMPLE -- method-to-code mapping for cv-detection-paper. -->

# Method-to-code mapping (cv-detection-paper, illustrative)

| Method component                       | Source files              | Entry points        | Configs             | Key functions/classes                              | Evidence | Gaps                                                |
|----------------------------------------|---------------------------|---------------------|---------------------|----------------------------------------------------|----------|-----------------------------------------------------|
| Anchor-free detection head (Method X)  | src/models/detector.py    | (none in stub)      | configs/base.yaml   | `AnchorFreeHead` (33:77), `AnchorFreeHeadConfig` (21:30) | ev_0042  | Real training loop and FPN backbone are out of scope.|
| Distribution-focal box decoding        | src/models/detector.py    | (none in stub)      | configs/base.yaml   | `AnchorFreeHead.decode_box` (79:85)                | ev_0043  | Decoding kernel is a no-op stub.                    |
| Shared per-level tower                 | src/models/detector.py    | (none in stub)      | configs/base.yaml   | `AnchorFreeHead._cls_tower`, `_reg_tower` (49:50)  | ev_0042  | No per-level normalisation switch.                  |
| IoU-aware classification               | configs/base.yaml         | (none in stub)      | configs/base.yaml   | `AnchorFreeHeadConfig.use_iou_aware` (29:29)       | ev_0018  | Logic to gate the IoU branch lives in train loop -- not in this example. |
