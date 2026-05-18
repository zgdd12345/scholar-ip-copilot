<!-- ILLUSTRATIVE EXAMPLE -- /scholar:paper-code-audit output for cv-detection-paper. -->

# Paper-code audit (cv-detection-paper, illustrative)

| Paper claim                                                                  | Where in paper          | Code evidence (file:lines)            | Verdict        | Notes                                                                 |
|------------------------------------------------------------------------------|-------------------------|---------------------------------------|----------------|-----------------------------------------------------------------------|
| "We propose an anchor-free head with shared per-level towers."               | Method, Sec. 3.1        | src/models/detector.py:33-77          | CONFIRMED      | Class definition and tower wiring present.                            |
| "The regression branch uses a 16-bin distribution-focal decoding."           | Method, Sec. 3.2        | src/models/detector.py:79-85; configs/base.yaml:12 | PARTIAL  | Switch (`reg_max=16`) exists; decoder body is a stub in this example. |
| "IoU-aware classification improves mAP@0.5:0.95 by 1.6 points."              | Experiments, Sec. 4.2   | configs/base.yaml:12; experiments/runs/exp_2026_03_02.csv | CONFIRMED | Ablation row matches ev_0018 (0.418 -> 0.402).                       |
| "Centerness is attached to the regression branch."                           | Method, Sec. 3.1        | configs/base.yaml:10; src/models/detector.py:68 | CONFIRMED | Default `centerness_on_reg: true` matches `forward` branching.        |
| "Method X is the first anchor-free head with distribution-focal decoding."   | Introduction            | n/a                                   | NOT_AUDITABLE  | Novelty claim; defer to literature matrix and `/scholar:paper-check`.         |

Summary: 3 CONFIRMED, 1 PARTIAL, 0 MISSING, 0 MISMATCH, 1 NOT_AUDITABLE.
