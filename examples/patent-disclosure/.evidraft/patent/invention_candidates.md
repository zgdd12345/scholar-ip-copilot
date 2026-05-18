<!-- ILLUSTRATIVE EXAMPLE -- /scholar:patent-scout output for the patent-disclosure
     example. Candidate content is fictional. -->

# Invention candidates (illustrative)

## C-001 Adaptive Cosine Warmup

- **Source signals**:
  - `src/optim/scheduler.py` -- `AdaptiveCosineWarmupMomentumScaler`
    (lines 36-73), `AdaptiveCosineWarmupConfig` (lines 21-33).
  - `configs/scheduler.yaml` -- default `coupling_alpha: 0.75`.
  - Inventor engineering log 2026-02-14 (ev_0104) -- ~0.4 pt top-1
    error reduction over two seeds on the internal benchmark.
- **Plain-language summary**: A learning-rate / momentum scheduler in
  which momentum is derived from the cosine learning-rate envelope
  through a single scalar coupling weight.
- **Apparent novelty**: Coupling weight $\alpha$ that smoothly
  interpolates between "cosine LR + constant momentum" (the standard
  baseline, ev_0103) and "momentum fully tracks the cosine ratio".
- **Patent potential (engineering view, not legal)**: medium.
- **Next actions**:
  1. `/scholar:patent-prior-art` -- search for prior coupled LR/momentum
     schedules, especially anything that reuses the cosine ratio.
  2. `/scholar:patent-disclosure` -- draft the TID (already populated for this
     example).
  3. `/scholar:patent-claims` -- advisory claims.
