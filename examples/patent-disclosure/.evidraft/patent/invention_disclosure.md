<!-- ILLUSTRATIVE EXAMPLE -- Populated Technical Invention Disclosure (TID)
     for the EviDraft patent-disclosure example. Every technical statement,
     inventor name, prior-art reference, and number below is FICTIONAL.
     Do not file or rely on this document. -->

# Technical Invention Disclosure (技术交底书 / TID)

> Candidate: C-001 Adaptive Cosine Warmup with Momentum Scaling
> Inventor of record: Example Inventor (Example Research Lab)
> Jurisdiction (proposed): US (with PCT under consideration)
> Status: draft for attorney review

---

## C-001 Adaptive Cosine Warmup with Momentum Scaling

### 1. Title (技术名称)

- **EN**: Adaptive Cosine Warmup with Momentum Scaling for Stochastic
  Gradient Optimisers.
- **ZH (中文)**: 一种用于随机梯度优化器的自适应余弦预热与动量耦合方法.

### 2. Field of the invention (技术领域)

- **EN**: Training procedures for deep neural networks; specifically,
  learning-rate and momentum scheduling for stochastic gradient
  descent-style optimisers (SGD, SGD with momentum, Nesterov SGD).
- **ZH**: 深度神经网络训练方法, 具体涉及随机梯度类优化器 (SGD / 含动量 SGD /
  Nesterov SGD) 的学习率与动量调度.

### 3. Background (背景技术)

- **EN**: Cosine learning-rate schedules with linear warmup are a widely
  used default (ev_0103). In typical deployments the momentum
  coefficient is held *constant* throughout training. Two failure modes
  are commonly observed: (a) early-warmup instability when momentum is
  high relative to the small effective step size, and (b) late-training
  oscillation when momentum remains high while the LR cosine envelope
  decays towards a small floor. Existing fixes (momentum warmup,
  momentum decay) treat momentum as an *independent* schedule.
- **ZH**: 余弦学习率调度配合线性预热已成为常见默认方案 (ev_0103). 在工程实践中,
  动量系数通常在整个训练过程保持恒定, 导致两类问题: (a) 预热初期, 动量
  相对于较小的学习率过高, 引起不稳定; (b) 训练后期, 学习率沿余弦曲线衰减
  接近下限, 但动量仍维持高位, 产生不必要的震荡. 现有方法 (动量预热,
  动量衰减) 将动量视为与学习率相互独立的调度对象.

### 4. Problem solved (要解决的技术问题)

- **EN**: How to schedule the momentum coefficient so that it stays
  *consistent* with the cosine learning-rate envelope, without
  introducing additional hyper-parameters beyond a single coupling
  weight, and without changing the optimiser update rule itself.
- **ZH**: 如何在不修改优化器更新公式, 仅引入单一耦合权重的前提下, 让动量系数
  与余弦学习率曲线保持一致变化.

### 5. Summary (发明概述)

- **EN**: The invention is a scheduler that produces both a learning
  rate and a momentum coefficient at each training step from a single
  cosine envelope. The two outputs are linked by a *coupling weight*
  $\alpha \in [0, 1]$. At $\alpha = 0$ the scheduler degenerates to a
  vanilla cosine LR with constant momentum; at $\alpha = 1$ momentum
  fully tracks the cosine ratio. The intermediate values blend the two.
- **ZH**: 本发明提出一种调度器, 通过单一耦合权重 $\alpha \in [0, 1]$ 同时
  根据同一余弦曲线生成学习率与动量系数. $\alpha = 0$ 时退化为传统余弦学习率
  与恒定动量; $\alpha = 1$ 时动量完全跟随余弦比例; 中间值进行线性混合.

### 6. Technical solution (技术方案)

- **EN**: Let $T_w$ be the warmup-iteration count, $T$ the total
  iteration count, $\eta_0$ the base LR, $m_0$ the target momentum,
  $m_{\min}$ the momentum floor, and $\rho$ the min-LR ratio. At step
  $t$:

  1. **Warmup phase ($t < T_w$)**:
     $\eta_t = \eta_0 \cdot \tfrac{1}{2}\bigl(1 - \cos(\pi \cdot t / T_w)\bigr)$.
     $m_t = m_{\min} + (m_0 - m_{\min}) \cdot t / T_w$ (linear rise).
  2. **Main phase ($t \ge T_w$)**: let
     $u = (t - T_w) / (T - T_w)$ and
     $r_t = \tfrac{1}{2}\bigl(1 + \cos(\pi u)\bigr)$.
     $\eta_t = \rho \eta_0 + (1 - \rho) \eta_0 \cdot r_t$.
     $b_t = \alpha \cdot (\eta_t / \eta_0) + (1 - \alpha)$.
     $m_t = m_{\min} + (m_0 - m_{\min}) \cdot b_t$.
- **ZH**: 设 $T_w$ 为预热迭代数, $T$ 为总迭代数, $\eta_0$ 为基础学习率,
  $m_0$ 为目标动量, $m_{\min}$ 为动量下限, $\rho$ 为最小学习率比例. 第 $t$ 步:

  1. **预热阶段 ($t < T_w$)**: 学习率
     $\eta_t = \eta_0 \cdot \tfrac{1}{2}\bigl(1 - \cos(\pi \cdot t / T_w)\bigr)$;
     动量按线性方式从 $m_{\min}$ 升至 $m_0$.
  2. **主阶段 ($t \ge T_w$)**: 取 $u = (t - T_w)/(T - T_w)$,
     $r_t = \tfrac{1}{2}(1 + \cos(\pi u))$, 学习率
     $\eta_t = \rho \eta_0 + (1 - \rho)\eta_0 \cdot r_t$;
     动量按 $m_t = m_{\min} + (m_0 - m_{\min}) \cdot
     [\alpha (\eta_t/\eta_0) + (1 - \alpha)]$ 计算.

### 7. Implementation details (具体实施方式)

- **EN**: A reference implementation lives in
  `src/optim/scheduler.py`. The `AdaptiveCosineWarmupMomentumScaler`
  class (`src/optim/scheduler.py:36-73`, evidence ev_0101) wraps the
  configuration object `AdaptiveCosineWarmupConfig`
  (`src/optim/scheduler.py:21-33`). The `lr()` method
  (`src/optim/scheduler.py:48-57`) implements the cosine envelope; the
  `momentum()` method (`src/optim/scheduler.py:59-73`, evidence
  ev_0102) implements the coupling rule. Configuration defaults are
  in `configs/scheduler.yaml`.
- **ZH**: 参考实现位于 `src/optim/scheduler.py`.
  `AdaptiveCosineWarmupMomentumScaler` (第 36-73 行, 证据 ev_0101) 封装配置
  对象 `AdaptiveCosineWarmupConfig` (第 21-33 行); `lr()` 方法 (第 48-57 行)
  实现余弦曲线, `momentum()` 方法 (第 59-73 行, 证据 ev_0102) 实现耦合规则,
  默认值见 `configs/scheduler.yaml`.

### 8. Alternatives / variants (可替代方案 / 变体实施例)

- **EN**:
  - *Variant A -- Non-linear blend.* Replace the linear blend
    $b_t = \alpha r_t + (1 - \alpha)$ with a power blend
    $b_t = r_t^{\alpha}$.
  - *Variant B -- Per-parameter coupling.* Apply a different
    $\alpha$ per parameter group (e.g., higher coupling on layers with
    larger gradient noise).
- **ZH**:
  - *变体 A -- 非线性混合.* 用幂混合 $b_t = r_t^{\alpha}$ 替换线性混合.
  - *变体 B -- 按参数分组耦合.* 对不同参数组使用不同的 $\alpha$ (例如,
    梯度噪声较大的层采用更高耦合).

### 9. Advantages / technical effects (技术效果 / 有益效果)

- **EN**:
  - Reduced training-time oscillation in the late phase (ev_0104).
  - Single additional hyper-parameter ($\alpha$); existing cosine
    schedulers are recovered as the $\alpha=0$ case (ev_0101).
  - No change to the optimiser update equation; the scheduler is
    drop-in for any SGD-style training loop.
- **ZH**:
  - 训练后期震荡减少 (ev_0104).
  - 仅新增一个超参数 $\alpha$; $\alpha=0$ 时退化为现有余弦调度 (ev_0101).
  - 不修改优化器更新公式, 可作为 SGD 类训练流程的即插即用替换.

### 10. Examples (实施例 / 实验数据)

- **EN**: On an internal image-classification benchmark with ResNet-50
  trained for 90 000 iterations at batch size 256, the inventor's log
  (ev_0104) records that switching from a vanilla cosine LR with
  constant momentum 0.9 to the coupled scheduler at $\alpha = 0.75$
  reduces top-1 error by approximately 0.4 points averaged over two
  seeds. Numbers are illustrative and require independent replication
  before any quantitative claim is filed.
- **ZH**: 在内部图像分类基准上 (ResNet-50, 90 000 步, batch 256), 发明人
  日志 (ev_0104) 记录: 由传统余弦学习率配恒定动量 0.9 切换为 $\alpha = 0.75$
  的耦合调度后, top-1 错误率在两个随机种子的均值上降低约 0.4 个百分点. 数据
  为示例性数据, 量化主张应以独立复现为准.

### 11. Diagrams suggestions (附图建议)

- **EN**:
  - Block diagram of the scheduler showing inputs ($T_w$, $T$,
    $\eta_0$, $m_0$, $m_{\min}$, $\alpha$, $\rho$) and outputs
    ($\eta_t$, $m_t$).
  - Timing diagram overlaying $\eta_t/\eta_0$ and $m_t/m_0$ vs step.
  - State / phase diagram with the warmup and main phases as states.
- **ZH**:
  - 调度器结构框图, 标注输入与输出.
  - $\eta_t/\eta_0$ 与 $m_t/m_0$ 随训练步数的曲线图.
  - 区分预热与主阶段的状态图.

### 12. Code traceability (代码追踪)

| Feature                                                  | File                          | Lines    | Evidence id |
|----------------------------------------------------------|-------------------------------|----------|-------------|
| Config object (`AdaptiveCosineWarmupConfig`)             | `src/optim/scheduler.py`      | 21--33   | ev_0101     |
| Scheduler class (`AdaptiveCosineWarmupMomentumScaler`)   | `src/optim/scheduler.py`      | 36--73   | ev_0101     |
| Cosine warmup + main-phase LR (`lr`)                     | `src/optim/scheduler.py`      | 48--57   | ev_0101     |
| Coupled momentum schedule (`momentum`)                   | `src/optim/scheduler.py`      | 59--73   | ev_0102     |
| Default coupling weight $\alpha$                         | `configs/scheduler.yaml`      |  --      | ev_0101     |

### 13. Inventor questions (待发明人确认事项)

- [ ] Earliest public disclosure / use / sale date for the coupled
  scheduler (talks, blog posts, internal demos with non-employees).
- [ ] All named inventors and their contributorship -- is the
  per-parameter-group variant attributable to the same inventor?
- [ ] Third-party code dependencies in `src/optim/scheduler.py` and
  their licences (the example uses only Python stdlib).
- [ ] Prior internal disclosure (engineering review notes, issue
  trackers, internal wikis) that may need to be enumerated.
- [ ] Funding source / contractual obligations (grant flow-through,
  joint development agreements) that may affect ownership.
- [ ] Choice of jurisdictions to pursue (US-only, PCT, CN national
  phase, EP).

---
## Needs attorney review

- [ ] Confirm jurisdiction(s).
- [ ] Confirm earliest public disclosure / use / sale date.
- [ ] Confirm all named inventors and contributorship.
- [ ] Confirm freedom-to-use of third-party code.
- [ ] Review claim scope.
- [ ] Decide on provisional vs non-provisional filing strategy.

> This disclosure is a *technical write-up* prepared by an AI assistant from the
> code and engineering notes provided. It is not a legal opinion. A registered
> patent agent / attorney must review before any filing decision.
