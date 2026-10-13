"""From a ridge response to a cleaned, owned skeleton.

Every step here except the thresholding is the current method's own code,
imported from src/canaliculi.py and called unchanged, so the two methods differ
in one place only: what is thresholded. The lengths come from params in
micrometres, and `check_parameters_match_current` asserts that at 0.13 um/px they
are the pixel values the imported code already uses, so there is one source of
truth and no value can drift quietly.

**Pixel size 0.13 um/px, rounded, unconfirmed per image.** Pre-validation.
"""
from __future__ import annotations

import numpy as np
from skimage import filters, morphology

import canaliculi


def check_parameters_match_current(params) -> list:
    """[(name, um, px, the pixel value the imported code uses)] and an assertion
    that they agree. A tuned value that no longer matches must be given its own
    code path rather than silently disagreeing with the imported functions."""
    rows = [
        ("lacuna_buffer", params.lacuna_buffer_um, params.px_int(params.lacuna_buffer_um),
         canaliculi.LACUNA_DILATION_PX),
        ("min_object_area", params.min_object_area_um2, params.area_px2(params.min_object_area_um2),
         canaliculi.MIN_THREAD_OBJECT_PX2),
        ("max_bridge_gap", params.max_bridge_gap_um, params.px(params.max_bridge_gap_um),
         canaliculi.MAX_BRIDGE_GAP_PX),
        ("direction_walk", params.direction_walk_um, params.px_int(params.direction_walk_um),
         canaliculi.DIRECTION_WALK_PX),
        ("max_bridge_angle_deg", params.max_bridge_angle_deg, None, canaliculi.MAX_BRIDGE_ANGLE_DEG),
        ("min_bridge_signal_fraction", params.min_bridge_signal_fraction, None,
         canaliculi.MIN_BRIDGE_SIGNAL_FRACTION),
        ("prune_spur", params.prune_spur_um, params.px(params.prune_spur_um), canaliculi.PRUNE_SPUR_LEN_PX),
        ("min_internal_edge", params.min_internal_edge_um, params.px(params.min_internal_edge_um),
         canaliculi.MIN_INTERNAL_EDGE_LEN_PX),
        ("lacuna_attach_gap", params.lacuna_attach_gap_um, params.px(params.lacuna_attach_gap_um),
         canaliculi.LACUNA_ATTACH_GAP_PX),
        ("root_merge", params.root_merge_um, params.px(params.root_merge_um), canaliculi.ROOT_MERGE_DIST_PX),
        ("hysteresis_low_fraction", params.hysteresis_low_fraction, None, canaliculi.HYSTERESIS_LOW_FRACTION),
        ("ring_radii", list(params.ring_radii_um), params.ring_radii_px(), list(canaliculi.RING_RADII_PX)),
    ]
    disagree = [r for r in rows if (r[2] if r[2] is not None else r[1]) != r[3]]
    assert not disagree, f"parameters differ from the imported code: {disagree}"
    return rows


def ridge_network_mask(response: np.ndarray, lacuna_mask: np.ndarray, flagged: np.ndarray,
                       params) -> tuple:
    """(mask, high cut). Hysteresis on the ridge response, with the lacuna buffer
    and the small fragments removed, in the shape of
    canaliculi.network_candidate_mask but reading the response.

    The high cut is the lower of the response's own three-class multi-Otsu cuts,
    the rule the current method applies to the flattened intensity, so the cut
    comes from this image and nothing else. The low cut is that times the
    carried-over fraction. Inside a flagged vascular structure only pixels
    already above the high cut survive, so hysteresis cannot grow into a canal,
    which is what the current method does."""
    strict, t_hi = canaliculi.total_signal_mask(response)
    low = t_hi * params.hysteresis_low_fraction
    mask = filters.apply_hysteresis_threshold(response, low, t_hi)
    if flagged.any():
        mask = mask & ~(flagged & ~strict)
    buffer_px = params.px_int(params.lacuna_buffer_um)
    buffered_lacunae = morphology.dilation(lacuna_mask, morphology.disk(buffer_px))
    mask = mask & ~buffered_lacunae
    mask = morphology.remove_small_objects(mask, min_size=params.area_px2(params.min_object_area_um2))
    return mask, float(t_hi)
