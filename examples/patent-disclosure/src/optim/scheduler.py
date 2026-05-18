# =====================================================================
# ILLUSTRATIVE EXAMPLE -- NOT A WORKING SCHEDULER
# This file is part of an EviDraft example project (patent-disclosure).
# The "Adaptive Cosine Warmup with Momentum Scaling" scheduler below is
# a FICTIONAL invention used purely to demonstrate the /patent-* flow.
# Do not rely on it for real training.
# =====================================================================
"""Synthetic ``AdaptiveCosineWarmupMomentumScaler`` scheduler.

The fictional invention couples a cosine warmup on the learning rate
with a complementary scaling of the optimiser's momentum coefficient.
The intuition (also fictional) is that small steps during warmup
benefit from a temporarily lowered momentum, after which both signals
ride the same cosine envelope back to their target values.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class AdaptiveCosineWarmupConfig:
    """Fictional config object for the scheduler."""

    base_lr: float = 0.1
    base_momentum: float = 0.9
    warmup_iters: int = 1000
    total_iters: int = 90000
    min_lr_ratio: float = 0.01
    momentum_floor: float = 0.5
    coupling_alpha: float = 0.75


class AdaptiveCosineWarmupMomentumScaler:
    """Couples a cosine LR warmup with a paired momentum schedule.

    The alleged contribution is the *coupling* between the cosine
    envelope and the momentum coefficient, governed by
    ``coupling_alpha``. When ``coupling_alpha == 0`` the scheduler
    degenerates to a vanilla cosine LR with constant momentum.
    """

    def __init__(self, cfg: AdaptiveCosineWarmupConfig):
        self.cfg = cfg

    def lr(self, step: int) -> float:
        c = self.cfg
        if step < c.warmup_iters:
            # Cosine *warmup* (rising half of a cosine).
            t = step / max(1, c.warmup_iters)
            return c.base_lr * 0.5 * (1.0 - math.cos(math.pi * t))
        t = (step - c.warmup_iters) / max(1, c.total_iters - c.warmup_iters)
        cosine = 0.5 * (1.0 + math.cos(math.pi * t))
        floor = c.base_lr * c.min_lr_ratio
        return floor + (c.base_lr - floor) * cosine

    def momentum(self, step: int) -> float:
        """Momentum coefficient, coupled to the LR envelope.

        During warmup the momentum starts at ``momentum_floor`` and
        rises linearly. After warmup it tracks the cosine envelope of
        ``lr`` scaled by ``coupling_alpha``.
        """
        c = self.cfg
        if step < c.warmup_iters:
            t = step / max(1, c.warmup_iters)
            return c.momentum_floor + (c.base_momentum - c.momentum_floor) * t
        ratio = self.lr(step) / c.base_lr  # in [min_lr_ratio, 1.0]
        # Linear blend between floor and base, weighted by coupling_alpha.
        blend = c.coupling_alpha * ratio + (1.0 - c.coupling_alpha)
        return c.momentum_floor + (c.base_momentum - c.momentum_floor) * blend
