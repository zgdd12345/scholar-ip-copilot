<!-- ILLUSTRATIVE EXAMPLE -- repo summary for the synthetic cv-detection-paper. -->

# Repo summary (cv-detection-paper, illustrative)

- **Language**: Python (stdlib only; no torch / numpy import in the example)
- **Top-level layout**:
  - `src/models/detector.py` -- `AnchorFreeHead`, `AnchorFreeHeadConfig`
  - `configs/base.yaml` -- model + train + data hyper-parameters
  - `experiments/runs/exp_2026_03_01.csv` -- main run, 3 seeds x 2 datasets
  - `experiments/runs/exp_2026_03_02.csv` -- ablation run (IoU-aware off)
- **Entry points**: none in this synthetic example. In a real project this row
  would point at `tools/train.py` or `tools/eval.py`.
- **Configs**: `configs/base.yaml`
- **Tests / CI**: none in this synthetic example.
- **Build / run commands**: n/a -- everything is a stub.
- **README / DATASHEET / MODEL_CARD**: only `README.md` (this example).
