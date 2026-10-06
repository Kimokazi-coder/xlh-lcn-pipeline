"""Background flattening: the current method's own, by import.

The experimental method changes one idea, the quantity that is thresholded, so it
starts from exactly the image the current method starts from. Flattening is a
light Gaussian, a white top-hat and subtraction of the histogram mode
(docs/METHODS.md section 1, feature 2, step 1), and
canaliculi.preprocess_channel is called unchanged rather than copied, so the two
methods cannot drift apart here.

**Pixel size 0.13 um/px, rounded, unconfirmed per image.** Pre-validation.
"""
from __future__ import annotations

import numpy as np

import canaliculi


def flatten(channel: np.ndarray) -> np.ndarray:
    """The flattened channel both methods threshold, from the current method."""
    return canaliculi.preprocess_channel(channel)


def vascular_mask(channel: np.ndarray) -> np.ndarray:
    """Broad bright structures (vascular canals and their edges), already dilated
    by canaliculi.FLAGGED_DILATION_PX. The current method's own function: nothing
    is removed from the image, growth into these regions is blocked, and the width
    measure leaves them out."""
    return canaliculi.flagged_structures(channel)


def tophat_radius_px() -> int:
    """The radius the flattening uses, for the parameter report."""
    return canaliculi.TOPHAT_RADIUS_PX
