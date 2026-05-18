<!-- ILLUSTRATIVE EXAMPLE -- /scholar:patent-prior-art output. All prior-art
     references below are FICTIONAL placeholders for the example. -->

# Prior-art map (illustrative)

## C-001 Adaptive Cosine Warmup with Momentum Scaling

| Ref id | Reference (fictional)                                                | Family            | Closest element                                  | Distinction                                                  |
|--------|----------------------------------------------------------------------|-------------------|--------------------------------------------------|--------------------------------------------------------------|
| PA-01  | US Patent App. 2024/0XXXXXX A1 -- "Cosine schedule with momentum warmup" (fictional) | Patent (US App.)  | Cosine LR + linear momentum warmup; constant momentum after warmup | No coupling weight $\alpha$; momentum is constant in the main phase. |
| PA-02  | Park & Yamada (2023), "Independent momentum decay for SGD" (fictional, J. Illustrative ML, vol. 4) | Non-patent literature | Linear momentum decay schedule independent of LR | Treats momentum as an independent schedule, not coupled to the cosine LR ratio. |

### Notes for the attorney

- Both references are written as if they exist; in this illustrative
  example neither is a real publication.
- The closest overlap is the linear momentum warmup of PA-01; the line
  of distinction is the coupling weight $\alpha$ and the derivation of
  the main-phase momentum from $\eta_t / \eta_0$.
