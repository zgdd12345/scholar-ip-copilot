<!-- ILLUSTRATIVE EXAMPLE -- /scholar:patent-claims output (claims side).
     Fictional. -->

# Draft claims (for attorney review)

## Claim 1 (independent)

1. A method for training a neural network by stochastic gradient
   descent, the method comprising:

   a. receiving, at each training step $t$ of a training procedure,
      a configuration comprising a warmup length $T_w$, a total length
      $T$, a base learning rate $\eta_0$, a base momentum coefficient
      $m_0$, a minimum momentum $m_{\min}$, a minimum learning-rate
      ratio $\rho$, and a coupling weight $\alpha \in [0, 1]$;

   b. computing a learning rate $\eta_t$ from a two-phase cosine
      envelope, the envelope rising during $t < T_w$ and decaying
      during $t \ge T_w$ towards $\rho \eta_0$;

   c. computing a momentum coefficient $m_t$ as a linear blend between
      $m_{\min}$ and $m_0$, the blend weight depending on the ratio
      $\eta_t / \eta_0$ and the coupling weight $\alpha$, such that at
      $\alpha = 0$ the momentum coefficient is constant during the
      $t \ge T_w$ phase;

   d. applying the pair $(\eta_t, m_t)$ to the stochastic gradient
      descent update at step $t$.

## Claim 2 (dependent on Claim 1)

2. The method of Claim 1, wherein the linear blend is replaced by a
   power blend $(\eta_t / \eta_0)^{\alpha}$.

## Claim 3 (dependent on Claim 1)

3. The method of Claim 1, wherein the coupling weight $\alpha$ is
   applied independently per parameter group of the neural network.

## Claim 4 (dependent on Claim 1)

4. The method of Claim 1, wherein during the warmup phase the
   momentum coefficient $m_t$ rises linearly from $m_{\min}$ to $m_0$
   over $T_w$ steps.

---

> Draft claims. Not filed text. Must be reviewed and adapted by a registered
> patent agent / attorney before any filing decision.
