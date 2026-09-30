"""Evidence-based gap bridging for the canalicular skeleton (Phase 2c).
v1-raw, pre-validation. NON-DEFAULT: canaliculi_v1.GAP_BRIDGING is False.

A single 2D optical section cuts a 3D network, so a canaliculus that dives
out of the focal plane ends mid-field. Phase 0(c) measured how much signal
actually lies in those gaps, by algebraically inverting canaliculi_v1's
preprocessing to a per-pixel raw threshold surface and sampling along the
straight line between a skeleton endpoint and its nearest different
component. The result, pooled over all 8 WT images, as a function of gap
length (median of the MINIMUM signal fraction along the gap, where 0.0 is
image background and 1.0 is the threshold that would have admitted it):

    2-5 px   0.964    5-8 px   0.886    8-11 px  0.734    11-15 px  0.568

So most gaps hold dim-but-present signal rather than nothing, and how much
falls off with distance. That is the evidence this module's three limits
come from; see each constant.

WHY NOT MORPHOLOGICAL CLOSING. A blind closing joins whatever is near,
including two neighbouring canaliculi running side by side, which fuses
them into one thread and creates a false loop. Phase 0(c) showed this is
the common case, not a corner case: only 21% of endpoint-to-neighbour
angles are under 20 degrees, so most nearest neighbours are parallel
threads rather than continuations. Every bridge here must pass all three
tests -- short enough, aligned with the thread's own direction, and with
real signal along its whole length.

DEPARTURE FROM OCY (Kollmannsberger et al., New J. Phys. 2017): OCY has no
gap-bridging step and needs none. Their input is a 3D stack, where a
canaliculus leaving one plane simply continues in the next, so
out-of-plane truncation does not exist for them. This step exists only
because our fields are single 2D sections.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from skimage import measure

# Longest gap that may be bridged, in px. From the table above: at 8-11 px
# the median dimmest point in the gap still sits at 0.73 of the way to the
# threshold, but by 11-15 px it has fallen to 0.57 and only ~29% of gaps
# keep a minimum above 0.7. 10 px is where the evidence for "this is one
# interrupted thread" is still strong for most pairs.
MAX_BRIDGE_GAP_PX = 10.0

# Largest angle, in degrees, between the thread's own local direction at
# the endpoint and the vector to the candidate partner. A continuation runs
# on in roughly the same direction; a neighbouring parallel thread sits off
# to the side. Phase 0(c)'s pooled angle histogram runs 21.0% under 20 deg,
# 17.8% in 20-40, 17.7% in 40-60, then a long tail out to 180. 40 deg keeps
# the two leading bins, i.e. the pairs that actually point at each other,
# and drops everything from side-on to backwards.
MAX_BRIDGE_ANGLE_DEG = 40.0

# The MINIMUM signal fraction along the gap must reach this. Using the
# minimum, not the mean, is the point: one background-level pixel in the
# middle breaks the thread however bright its two ends are, and the mean is
# dominated by the bright ends. 0.7 is where Phase 0(c) split its summary
# ("share >= 0.7"), and on that measure 93.5% of 5-8 px gaps qualify but
# only 29.9% of 11-15 px gaps do, so this limit and MAX_BRIDGE_GAP_PX
# reinforce each other rather than duplicating.
MIN_BRIDGE_SIGNAL_FRACTION = 0.7

# How far to walk back along the thread to estimate its local direction, in
# px. Same value and reasoning as the Phase 0(c) diagnostic: long enough to
# average out the 1px staircase of a rasterized diagonal, short enough not
# to average across a real bend in a wavy canaliculus.
DIRECTION_WALK_PX = 5

NEIGHBOUR_OFFSETS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def skeleton_endpoints(skeleton: np.ndarray) -> np.ndarray:
    """Pixel-level degree-1 skeleton pixels, i.e. thread ends."""
    neighbours = ndi.convolve(skeleton.astype(np.uint8), np.ones((3, 3), np.uint8), mode="constant")
    return np.argwhere(skeleton & (neighbours - skeleton.astype(np.uint8) == 1))


def walk_back(skeleton: np.ndarray, start: tuple[int, int], max_steps: int) -> tuple[int, int]:
    """Walk inward from an endpoint along the thread, up to max_steps.
    Stops at a junction, where the thread's direction stops being defined."""
    rows, cols = skeleton.shape
    visited = {start}
    current = start
    for _ in range(max_steps):
        candidates = []
        for dr, dc in NEIGHBOUR_OFFSETS:
            r, c = current[0] + dr, current[1] + dc
            if 0 <= r < rows and 0 <= c < cols and skeleton[r, c] and (r, c) not in visited:
                candidates.append((r, c))
        if len(candidates) != 1:
            break
        current = candidates[0]
        visited.add(current)
    return current


def find_bridges(
    skeleton: np.ndarray,
    preprocessed: np.ndarray,
    t_lo: float,
    forbidden: np.ndarray,
) -> list[dict]:
    """Every endpoint-to-component pair passing all three tests.

    The signal test is done in PRE-PROCESSED units: `preprocessed` is the
    image the pipeline actually thresholds and `t_lo` the cut it applies,
    so the signal fraction is simply preprocessed/t_lo, and a value of 1.0
    means "this pixel would have been in the mask". Phase 0(c) measured
    the same quantity by inverting the top-hat chain to a per-pixel RAW
    threshold surface instead. The two agree exactly at the threshold, by
    construction, and differ somewhat below it; the ratio here is used
    because it is defined for every PREPROCESS_MODE, including the ridge
    modes, whose response has no raw-intensity inverse. See
    report_phase2.py, which prints both measures side by side for the
    top-hat mode so the difference is on the record.

    `forbidden` is the union of the lacuna bodies and any excluded region:
    a bridge may not pass through either. Bridging through a lacuna would
    invent a canaliculus crossing a cell body; bridging through an excluded
    region would reintroduce exactly what the exclusion removed."""
    comp_labels = measure.label(skeleton, connectivity=2)
    radius = int(np.ceil(MAX_BRIDGE_GAP_PX))
    offsets_r, offsets_c = np.mgrid[-radius:radius + 1, -radius:radius + 1]
    offset_dist = np.hypot(offsets_r, offsets_c)
    in_range = offset_dist <= MAX_BRIDGE_GAP_PX

    rows, cols = skeleton.shape
    bridges = []
    claimed: set = set()
    for r, c in skeleton_endpoints(skeleton):
        r, c = int(r), int(c)
        if forbidden[r, c]:
            continue
        r0, r1 = max(0, r - radius), min(rows, r + radius + 1)
        c0, c1 = max(0, c - radius), min(cols, c + radius + 1)
        window = comp_labels[r0:r1, c0:c1]
        wr0, wc0 = r0 - (r - radius), c0 - (c - radius)
        dist_window = offset_dist[wr0:wr0 + window.shape[0], wc0:wc0 + window.shape[1]]
        ok_window = in_range[wr0:wr0 + window.shape[0], wc0:wc0 + window.shape[1]]

        own = comp_labels[r, c]
        other = (window > 0) & (window != own) & ok_window
        if not other.any():
            continue
        masked = np.where(other, dist_window, np.inf)
        idx = np.unravel_index(int(np.argmin(masked)), masked.shape)
        gap_len = float(masked[idx])
        tr, tc = int(r0 + idx[0]), int(c0 + idx[1])

        # One bridge per unordered component pair per endpoint pair, so two
        # endpoints facing each other do not both draw the same line.
        key = (min((r, c), (tr, tc)), max((r, c), (tr, tc)))
        if key in claimed:
            continue

        back = walk_back(skeleton, (r, c), DIRECTION_WALK_PX)
        direction = np.array([r - back[0], c - back[1]], dtype=float)
        gap_vector = np.array([tr - r, tc - c], dtype=float)
        norm = np.linalg.norm(direction) * np.linalg.norm(gap_vector)
        if norm <= 0:
            continue
        cosine = float(np.dot(direction, gap_vector) / norm)
        angle = float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))
        if angle > MAX_BRIDGE_ANGLE_DEG:
            continue

        n_samples = max(1, int(round(gap_len)) - 1)
        ts = np.linspace(0.0, 1.0, n_samples + 2)[1:-1]
        sr = np.clip(np.round(r + ts * (tr - r)).astype(int), 0, rows - 1)
        sc = np.clip(np.round(c + ts * (tc - c)).astype(int), 0, cols - 1)
        if forbidden[sr, sc].any():
            continue

        fraction = np.clip(preprocessed[sr, sc] / t_lo, 0.0, None) if t_lo > 0 else np.zeros(sr.shape)
        if float(fraction.min()) < MIN_BRIDGE_SIGNAL_FRACTION:
            continue

        claimed.add(key)
        bridges.append(
            {
                "from": (r, c),
                "to": (tr, tc),
                "gap_len": gap_len,
                "angle_deg": angle,
                "min_signal_fraction": float(fraction.min()),
                "pixels": (sr, sc),
            }
        )
    return bridges


def apply_bridges(mask: np.ndarray, bridges: list[dict]) -> np.ndarray:
    """Draw each accepted bridge into the candidate mask. The mask is
    re-skeletonized afterwards by the caller, so a bridge becomes part of
    the network rather than a separate overlay."""
    out = mask.copy()
    for bridge in bridges:
        sr, sc = bridge["pixels"]
        out[sr, sc] = True
    return out


def bridge_overlay(display_uint8: np.ndarray, skeleton: np.ndarray, bridges: list[dict]) -> np.ndarray:
    """Every bridge drawn in a distinct colour over the image, so each one
    can be checked by eye against the signal it claims to follow."""
    from skimage import morphology as morph

    vis = display_uint8.copy()
    thin = morph.dilation(skeleton, morph.disk(1))
    vis[thin] = (0.5 * vis[thin] + 0.5 * np.array([255, 255, 255])).astype(np.uint8)
    for bridge in bridges:
        sr, sc = bridge["pixels"]
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                rr = np.clip(sr + dr, 0, vis.shape[0] - 1)
                cc = np.clip(sc + dc, 0, vis.shape[1] - 1)
                vis[rr, cc] = [0, 255, 0]
    return vis
