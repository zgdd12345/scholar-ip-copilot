<!-- ILLUSTRATIVE EXAMPLE -- /scholar:patent-claims output (chart side). Fictional. -->

# Claim chart (illustrative)

## C-001 Adaptive Cosine Warmup with Momentum Scaling

| Claim element                                                                                | Specification support                | Code support                          | Prior art overlap | Risk   | Suggested revision                                                |
|----------------------------------------------------------------------------------------------|--------------------------------------|---------------------------------------|-------------------|--------|-------------------------------------------------------------------|
| [1a] receiving a step index $t$ and a configuration (Tw, T, eta0, m0, mmin, rho, alpha)      | Disclosure Sec. 6, Sec. 7            | `src/optim/scheduler.py:21-33,36-46`  | none flagged      | low    | --                                                                |
| [1b] computing a learning rate $\eta_t$ from a cosine envelope                               | Disclosure Sec. 6                    | `src/optim/scheduler.py:48-57`        | PA-01 (overlap)   | medium | Narrow to the *two-phase* cosine envelope with explicit warmup.   |
| [1c] computing a momentum coefficient $m_t$ as a linear blend                                | Disclosure Sec. 6, Sec. 7            | `src/optim/scheduler.py:59-73`        | PA-02 (partial)   | medium | Recite that $m_t$ is derived from $\eta_t/\eta_0$ via $\alpha$.   |
| [1d] coupling weight $\alpha \in [0,1]$ such that $\alpha=0$ recovers a constant momentum    | Disclosure Sec. 5, Sec. 9            | `src/optim/scheduler.py:33,72`        | none flagged      | low    | Make the degenerate case explicit in the claim language.          |
| [1e] applying $(\eta_t, m_t)$ to an SGD-style optimiser update at step $t$                   | Disclosure Sec. 4, Sec. 6            | (caller code -- not in this example)  | PA-01 (overlap)   | high   | Limit to optimisers with a momentum coefficient and a fixed rule. |
