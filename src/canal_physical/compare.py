"""Side by side: the raw image, the current method and the new one.

Same crop and same display window as the existing verification images, so the
only difference a reader sees is the skeleton. A scale bar in micrometres is on
every panel. The zoom crops are chosen by a rule, not by eye: see
`zoom_boxes`.

**Pixel size 0.13 um/px, rounded, unconfirmed per image.** Pre-validation.
"""
from __future__ import annotations

import numpy as np

import canaliculi
import lacunae

# The scale bar: a round number of micrometres that is a sensible share of the
# frame. 10 um is 77 px at 0.13 um/px, about 7.5% of a 1024 px frame.
SCALE_BAR_UM = 10.0

# Zoom crops. Side in micrometres, and how many to save per image.
ZOOM_SIDE_UM = 13.0  # 100 px at 0.13 um/px
ZOOM_COUNT = 3
# The rule: the image is divided into tiles of the zoom side, the skeleton length
# of each method is counted in every tile, and the tiles with the largest
# absolute difference are taken, in order, without overlap. This is deterministic
# and does not look at how good either skeleton is, so it cannot be cherry-picked.
ZOOM_RULE = ("tiles of the zoom side, ranked by the absolute difference in skeleton pixel count between "
             "the two methods, taken in order with no overlap")


def display_window(channel: np.ndarray) -> tuple:
    """The fixed window of the existing verification images: the current method
    draws its verification picture over the full-brightness original, which is
    lacunae.load_channel's display. Here the raw panel uses the same percentile
    window the figures use for the dataset, so all three panels match."""
    low, high = np.percentile(channel, (1.0, 99.8))
    return float(low), float(high)


def windowed(channel: np.ndarray, window: tuple) -> np.ndarray:
    low, high = window
    out = np.clip((channel - low) / (high - low), 0.0, 1.0) if high > low else np.zeros_like(channel)
    return (out * 255).astype(np.uint8)


def overlay(display_uint8: np.ndarray, skeleton: np.ndarray, lacuna_id_map: np.ndarray,
            colors: dict, owner_map: np.ndarray | None = None) -> np.ndarray:
    """One method drawn in the style of the existing verification image: each
    lacuna outlined in its colour, and the skeleton it owns painted in that
    colour. Unowned skeleton is drawn in white, so a reader can see what the
    ownership did not reach."""
    from skimage import segmentation

    rgb = np.stack([display_uint8] * 3, axis=-1) if display_uint8.ndim == 2 else display_uint8.copy()
    unowned = skeleton.copy()
    if owner_map is not None:
        for lacuna_id, color in colors.items():
            painted = skeleton & (owner_map == lacuna_id)
            rgb[painted] = color
            unowned &= ~painted
    rgb[unowned] = (255, 255, 255)
    for lacuna_id, color in colors.items():
        body = lacuna_id_map == lacuna_id
        if body.any():
            rgb[segmentation.find_boundaries(body, mode="outer")] = color
    return rgb


def tile_difference(skeleton_a: np.ndarray, skeleton_b: np.ndarray, side_px: int) -> np.ndarray:
    """Per tile, the absolute difference in skeleton pixel count. Deterministic."""
    rows, cols = skeleton_a.shape
    n_r, n_c = rows // side_px, cols // side_px
    diff = np.zeros((n_r, n_c), dtype=np.int64)
    for i in range(n_r):
        for j in range(n_c):
            sl = (slice(i * side_px, (i + 1) * side_px), slice(j * side_px, (j + 1) * side_px))
            diff[i, j] = abs(int(skeleton_a[sl].sum()) - int(skeleton_b[sl].sum()))
    return diff


def zoom_boxes(skeleton_current: np.ndarray, skeleton_new: np.ndarray, params,
               count: int = ZOOM_COUNT) -> list:
    """The crops where the two skeletons differ most, by ZOOM_RULE.

    Returns [(row0, col0, side_px, difference)], highest difference first. Ties
    break by position, so the result does not depend on anything but the two
    skeletons."""
    side_px = params.px_int(ZOOM_SIDE_UM)
    diff = tile_difference(skeleton_current, skeleton_new, side_px)
    order = sorted(((int(diff[i, j]), i, j) for i in range(diff.shape[0]) for j in range(diff.shape[1])),
                   key=lambda t: (-t[0], t[1], t[2]))
    boxes = []
    for value, i, j in order:
        if len(boxes) >= count:
            break
        boxes.append((i * side_px, j * side_px, side_px, value))
    return boxes
