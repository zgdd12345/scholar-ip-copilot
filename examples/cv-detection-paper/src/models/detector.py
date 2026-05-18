# =====================================================================
# ILLUSTRATIVE EXAMPLE -- NOT A WORKING DETECTOR
# This file is part of an EviDraft example project (cv-detection-paper).
# All class names, hyper-parameters, and "results" referenced from it are
# fictional and exist only so the /paper-* commands can be demonstrated
# end-to-end. Do not import from this in real research.
# =====================================================================
"""Synthetic anchor-free detection head used by the example paper.

The example pretends a method called ``Method X'' has been published. The
head below is the alleged main contribution; the rest of the imaginary
codebase (backbone, neck, training loop) is stubbed for brevity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class AnchorFreeHeadConfig:
    """Fictional config object for the head."""

    in_channels: int = 256
    num_classes: int = 80
    feat_strides: Tuple[int, ...] = (8, 16, 32, 64, 128)
    centerness_on_reg: bool = True
    use_iou_aware: bool = True
    reg_max: int = 16  # discrete bins for the distribution-focal regression


class AnchorFreeHead:
    """Placeholder anchor-free detection head ("Method X" main contribution).

    The real method (in this fictional paper) decodes box distances from a
    per-location distribution rather than from anchors. We pretend the
    forward pass produces three tensors per FPN level: classification
    logits, regression distribution logits, and centerness logits. The
    /scholar:paper-code-audit command cites this docstring as evidence ev_0042.

    Args:
        cfg: an :class:`AnchorFreeHeadConfig` instance.
    """

    def __init__(self, cfg: AnchorFreeHeadConfig):
        self.cfg = cfg
        # In the real codebase these would be Conv2d / Linear modules.
        self._cls_tower = ["conv"] * 4
        self._reg_tower = ["conv"] * 4
        self._cls_head = "conv"
        self._reg_head = "conv"
        self._ctr_head = "conv"

    def forward(self, feats: List[object]) -> List[Tuple[object, object, object]]:
        """Run the head on the FPN feature pyramid.

        Each entry of ``feats`` is one FPN level. The head shares towers
        across levels; this is the design choice cited as a "shared
        per-level tower" in the paper.
        """
        outputs: List[Tuple[object, object, object]] = []
        for level_feat in feats:
            cls_feat = self._apply_tower(self._cls_tower, level_feat)
            reg_feat = self._apply_tower(self._reg_tower, level_feat)
            cls_logits = self._cls_head  # placeholder
            reg_dist = self._reg_head    # placeholder
            ctr_logits = self._ctr_head if self.cfg.centerness_on_reg else None
            outputs.append((cls_logits, reg_dist, ctr_logits))
        return outputs

    @staticmethod
    def _apply_tower(tower: List[str], feat: object) -> object:
        # Placeholder for stacked convs.
        for _ in tower:
            feat = feat  # no-op
        return feat

    def decode_box(self, dist_logits: object, stride: int) -> object:
        """Decode the per-location distance distribution into (l, t, r, b).

        This is the "distribution-focal decoding" step the paper claims
        is novel. In this synthetic stub we simply return the input.
        """
        return dist_logits
