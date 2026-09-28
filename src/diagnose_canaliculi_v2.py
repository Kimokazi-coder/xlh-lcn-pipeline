"""PHASE 0 READ-ONLY DIAGNOSTICS for the canaliculi side. Changes nothing.

STATUS: v1-raw / pre-validation. This module measures the CURRENT default
canaliculi pipeline (canaliculi_v1 with ASSIGNMENT_METHOD="graph",
PREPROCESS_MODE="tophat", COUNT_MODE="edge") and reports evidence. It
imports canaliculi_v1 and segment_lacunae_v2 and calls their functions
unmodified; it writes only into results/diagnostics/phase0/.
Everything is in PIXEL units (config.PIXEL_SIZE_UM is None).

What it answers, section by section:

(a) Crops. Full-resolution, unscaled 256x256 crops of the SAME region from
    the raw red channel, the canaliculi mask, the skeleton and the
    verification overlay, written side by side as one PNG. One crop from
    the densest region (most skeleton pixels in a sliding window), one from
    the sparsest region that still contains a lacuna, plus any --crop the
    caller asks for.

(b) Fragmentation metrics. How broken up the skeleton is, and how much of
    it the per-lacuna assignment can actually reach.

(c) Gap evidence -- THE decisive section for whether Phase 2 is worth
    doing. For every degree-1 skeleton endpoint it finds the nearest
    skeleton pixel within GAP_SEARCH_RADIUS_PX that belongs to a DIFFERENT
    connected component, then measures the gap length, the angle between
    the thread's local direction and the gap vector, and how much signal
    lies in the gap. The signal is expressed as a "signal fraction": 0.0 =
    the gap is at the image's background level, 1.0 = the gap is right at
    the threshold that would have included it in the mask. If most gaps
    sit near 1.0 the fragmentation is a threshold problem and is fixable in
    2D; if most sit near 0.0 there is genuinely no signal there, the
    canaliculus has left the focal plane, and no amount of thresholding or
    bridging will recover it.

    Mapping the threshold back to raw intensity. canaliculi_v1 thresholds
    a PREPROCESSED image, so a single scalar cut does not correspond to a
    single raw intensity. It does correspond to a per-pixel raw SURFACE,
    and that surface can be written down exactly. preprocess_channel does
        smoothed = gaussian(raw, SMOOTH_SIGMA_PX)
        tophat   = smoothed - opening(smoothed, disk(TOPHAT_RADIUS_PX))
        th       = (tophat - background_mode) / peak
    and total_signal_mask keeps th > t_lo. Substituting and rearranging,
        th(p) > t_lo  <=>  smoothed(p) > opening(smoothed)(p) + bg + t_lo*peak
    so the equivalent threshold at pixel p is
        t_lo_raw(p) = opening(smoothed)(p) + bg + t_lo*peak
    which this module computes and self-checks against canaliculi_v1's own
    mask (the agreement is printed; it should be ~100%).

(d) Large linear structures. Per skeleton connected component: length,
    end-to-end straightness and mean mask width, with components flagged
    that are simultaneously much longer, much straighter and much wider
    than the pooled canaliculus population -- candidate vascular canals,
    canal edges or section artifacts rather than canaliculi. Phase 1 is
    meant to be built on this table, so the thresholds here are reported,
    not applied to anything.

(e) Lacuna detection gaps. For every object in segment_lacunae_v2's
    pre-filter label image: area, mean intensity, solidity, aspect ratio,
    whether v2 kept it, and if not, WHICH of v2's filters rejected it
    first. Separately, broad bright objects found by a large morphological
    opening of the raw channel, which can surface lacunae that never
    reached v2's top-class cut t_hi at all and so never appear in v2's
    label image.

Relation to OCY (Kollmannsberger et al., New J. Phys. 2017,
github.com/phi-max/OCY_connectomics): the metrics in (b) and (d) are the
2D analogues of what OCY reports in OCY_get_network_params.m -- component
count (its bwconncomp on the skeleton), edge-length and node-degree
distributions. Section (c) has no OCY counterpart and cannot have one:
OCY works on 3D stacks where a canaliculus leaving one plane simply
continues in the next, so out-of-plane truncation does not exist for them.
It is the dominant failure mode for single 2D optical sections, which is
why it gets its own section here.

Tuning / held-out split (ground rule 9): TUNING_IMAGE_STEMS below names 3
WT images used for choosing parameters in later phases; every other image
is held out. Every pooled table in this module is printed for the two sets
separately so a parameter cannot be silently tuned on all of them.

Usage:
    python src/diagnose_canaliculi_v2.py --dir data/WT
    python src/diagnose_canaliculi_v2.py --dir data/WT --crop 555,400
    python src/diagnose_canaliculi_v2.py --image "data/WT/543-2.tif"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from skimage import measure, morphology, segmentation
from skimage.io import imsave

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from count_lacunae import load_channel  # noqa: E402
import canaliculi_v1 as can  # noqa: E402
import segment_lacunae_v2 as seg2  # noqa: E402


# --- Parameters -----------------------------------------------------------
# Every constant below is a DIAGNOSTIC setting. None of them feed the
# pipeline; they only decide what gets measured and printed here.

# Tuning set for later phases (ground rule 9: not 542_z06 alone, and at
# least one sparse field). Chosen from the pooled skeleton lengths measured
# in the previous session: 543-2 is one of the densest WT fields (~44k
# skeleton px), 542_z06 and 682_z29 are among the sparsest (~35k and ~37k),
# so the set spans the density range rather than sampling one end of it.
# Everything not named here is held out. Stems match Path.stem exactly.
TUNING_IMAGE_STEMS = (
    "542 WT  2_z06c1-2",
    "543-2",
    "682_z29c1-3",
)

# Side length of the inspection crops, in px. Fixed by the brief. Crops are
# written at full resolution with no rescaling, so 1 crop px = 1 image px.
CROP_SIZE_PX = 256

# How far from a skeleton endpoint to look for a different component, in px.
# Fixed by the brief. Also the largest gap any Phase 2 bridging step could
# ever consider, so the measured distribution below is the evidence for
# choosing MAX_BRIDGE_GAP_PX later.
GAP_SEARCH_RADIUS_PX = 15

# How many skeleton pixels to walk back from an endpoint to estimate the
# thread's local direction, in px. Fixed by the brief ("last ~5 skeleton
# px"). Long enough to average out the 1px staircase of a rasterized
# diagonal, short enough not to average over a real bend in a wavy
# canaliculus.
LOCAL_DIRECTION_WALK_PX = 5

# Radius (px) of the disk used for the "broad bright objects" opening in
# (e). A morphological opening with this disk deletes anything narrower
# than 2R+1 px across. Measured canalicular widths (previous session,
# post-top-hat, pooled over all 8 WT images) are p50 ~6.0 and p99 ~8.5 px
# full width, so R=8 (diameter 17) erases every canaliculus while a lacuna
# (minor axis ~20-30 px) survives. The brief suggests "~2x the widest
# canaliculus"; that reading gives R~17, which is reported alongside as
# BROAD_OPENING_RADIUS_ALT_PX so the choice can be made on evidence in
# Phase 3 rather than now.
BROAD_OPENING_RADIUS_PX = 8
BROAD_OPENING_RADIUS_ALT_PX = 17

# Flagging rule for (d). A component is flagged only if it clears ALL
# three. The length and width cutoffs are percentiles of the POOLED
# distribution measured in this run (printed with the table), so they adapt
# to the data instead of being fixed numbers. The straightness cutoff is
# the one hand-set value: a canaliculus is visibly wavy, so end-to-end
# distance over path length stays well below 1, while a vascular canal edge
# runs nearly straight. 0.6 is an INITIAL GUESS, NOT YET TUNED -- the
# printed straightness distribution is the evidence for revising it.
LENGTH_FLAG_PERCENTILE = 99.0
WIDTH_FLAG_PERCENTILE = 99.0
STRAIGHTNESS_FLAG_MIN = 0.6

# Objects the user asked about by name in 542_z06, as (x=col, y=row) in the
# 1024x1024 image with the origin at top-left, i.e. Fiji's convention.
# Reported individually in (e) whichever way the general tables come out.
KNOWN_POINTS_542_Z06 = {
    "missed lacuna?": (230, 300),
    "kept, real?": (630, 140),
    "kept, real? (2)": (105, 60),
    "kept, real? (3)": (555, 140),
}

# The long vertical bright structure in 542_z06 the user flagged, as a
# column band. Used only to check whether (d)'s flagging catches it.
KNOWN_LINEAR_STRUCTURE_542_Z06 = {"col_min": 530, "col_max": 580}

DIAG_DIR = config.DIAGNOSTICS_DIR / "phase0"

NEIGHBOUR_OFFSETS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


# --- Pipeline reconstruction ---------------------------------------------

def threshold_surface(channel: np.ndarray) -> dict:
    """Invert canaliculi_v1's preprocessing to a per-pixel raw threshold.

    Returns the smoothed image the pipeline actually thresholds, the
    equivalent threshold SURFACE in those same units, and the scalars used.
    The arithmetic deliberately re-derives what can.preprocess_channel does
    rather than calling it, because the point is to invert it; the caller
    self-checks the result against can's own mask."""
    smoothed = ndi.gaussian_filter(channel, can.SMOOTH_SIGMA_PX) if can.SMOOTH_SIGMA_PX > 0 else channel
    opened = morphology.opening(smoothed, morphology.disk(can.TOPHAT_RADIUS_PX))
    tophat = smoothed - opened

    background = 0.0
    if can.BACKGROUND_MODE_SUBTRACT:
        peak_th = float(tophat.max())
        if peak_th > 0:
            counts, edges = np.histogram(tophat / peak_th, bins=256, range=(0.0, 1.0))
            counts[0] = 0
            counts[199:] = 0
            if counts.max() > 0:
                background = float(edges[int(np.argmax(counts))]) * peak_th

    shifted = np.clip(tophat - background, 0.0, None)
    peak = float(shifted.max())
    normalized = shifted / peak if peak > 0 else shifted
    _mask, t_lo = can.total_signal_mask(normalized)

    return {
        "smoothed": smoothed,
        "t_lo_raw": opened + background + t_lo * peak,
        "t_lo": t_lo,
        "background": background,
        "peak": peak,
    }


def raw_background_mode(channel: np.ndarray) -> float:
    """Modal intensity of the raw channel -- the level a pixel sits at when
    it carries no signal at all. The floor that gap intensities in (c) are
    measured up from."""
    counts, edges = np.histogram(channel, bins=256, range=(0.0, 1.0))
    return float(edges[int(np.argmax(counts))])


def pipeline_state(image_path: Path) -> dict:
    """Run the CURRENT default pipeline on one image and keep every
    intermediate the diagnostics need. Calls canaliculi_v1 and
    segment_lacunae_v2 functions unmodified."""
    display, channel = load_channel(image_path)
    _display2, labels, kept, t_hi = seg2.segment_image(image_path)

    lacuna_mask, lacuna_id_map = can.build_lacuna_maps(labels, kept)
    candidate, t_lo = can.canaliculi_candidate_mask(channel, lacuna_mask, "tophat")
    # The lacuna bodies plus canaliculi_v1's buffer are cut out of the
    # candidate mask AFTER thresholding, so pixels in here can be above the
    # threshold and still absent from the mask. (c) has to know about them
    # or it will read a lacuna body as "dim signal in a gap".
    buffered_lacunae = morphology.dilation(lacuna_mask, morphology.disk(can.LACUNA_DILATION_PX))
    skeleton = morphology.skeletonize(candidate)
    dist_to_lacuna, nearest_id = can.nearest_lacuna_map(lacuna_id_map)

    cell_ids = list(range(1, len(kept) + 1))
    G, skel_obj = can.build_network_graph(skeleton)
    can.clean_network_graph(G, dist_to_lacuna)
    can.attach_lacunae(G, dist_to_lacuna, nearest_id, cell_ids)
    owner, node_dist = can.assign_by_connectivity(G, cell_ids)
    edge_owner = can.assign_edges(G, owner, node_dist)
    owner_map = can.build_owner_pixel_map(skeleton.shape, skel_obj, G, edge_owner, owner)

    surface = threshold_surface(channel)
    # Self-check: does the inverted surface reproduce the pipeline's own
    # threshold decision? Compared before the lacuna buffer and the small-
    # object despeckle, which are separate steps applied after the cut.
    pipeline_cut = can.total_signal_mask(can.preprocess_channel(channel, "tophat"))[0]
    surface_cut = surface["smoothed"] > surface["t_lo_raw"]
    surface_agreement = float((pipeline_cut == surface_cut).mean())

    return {
        "path": image_path,
        "stem": image_path.stem,
        "display": display,
        "channel": channel,
        "labels": labels,
        "kept": kept,
        "t_hi": t_hi,
        "t_lo": t_lo,
        "lacuna_mask": lacuna_mask,
        "buffered_lacunae": buffered_lacunae,
        "lacuna_id_map": lacuna_id_map,
        "candidate": candidate,
        "skeleton": skeleton,
        "dist_to_lacuna": dist_to_lacuna,
        "graph": G,
        "skel_obj": skel_obj,
        "owner": owner,
        "edge_owner": edge_owner,
        "owner_map": owner_map,
        "surface": surface,
        "surface_agreement": surface_agreement,
        "raw_background": raw_background_mode(channel),
    }


def render_verification(state: dict) -> np.ndarray:
    """In-memory copy of canaliculi_v1.save_verification's drawing, so the
    overlay panel can be cropped without writing a file or importing a
    private helper. Mirrors that function step for step; duplicated here
    only because Phase 0 must not modify the pipeline module."""
    vis = (state["display"].astype(np.float32) * can.VIS_DIM_FACTOR).astype(np.uint8)
    colors = can.lacuna_colors(len(state["kept"]))
    for lacuna_id in range(1, len(state["kept"]) + 1):
        color = colors[lacuna_id]
        boundary = segmentation.find_boundaries(state["lacuna_id_map"] == lacuna_id, mode="outer")
        vis[boundary] = color
        owned = state["skeleton"] & (state["owner_map"] == lacuna_id)
        if owned.any():
            owned = morphology.dilation(owned, morphology.disk(can.VIS_SKELETON_DILATION_PX))
        vis[owned] = color
    return vis


# --- (a) Crops ------------------------------------------------------------

def _window_sums(binary: np.ndarray, win: int) -> tuple[np.ndarray, np.ndarray]:
    """Per-centre sum of `binary` over a win x win window, plus a mask of
    the centres whose window lies wholly inside the image."""
    sums = ndi.uniform_filter(binary.astype(np.float32), size=win, mode="constant") * (win * win)
    valid = np.zeros(binary.shape, dtype=bool)
    half = win // 2
    valid[half:binary.shape[0] - win + half, half:binary.shape[1] - win + half] = True
    return sums, valid


def pick_crop_origins(state: dict, win: int) -> dict[str, tuple[int, int]]:
    """Top-left corners of the densest crop and of the sparsest crop that
    still contains a lacuna, as (row, col)."""
    skel_sums, valid = _window_sums(state["skeleton"], win)
    lac_sums, _ = _window_sums(state["lacuna_mask"], win)
    half = win // 2

    dense_scores = np.where(valid, skel_sums, -np.inf)
    dr, dc = np.unravel_index(int(np.argmax(dense_scores)), dense_scores.shape)

    has_lacuna = valid & (lac_sums > 0)
    if has_lacuna.any():
        sparse_scores = np.where(has_lacuna, skel_sums, np.inf)
        sr, sc = np.unravel_index(int(np.argmin(sparse_scores)), sparse_scores.shape)
    else:
        sr, sc = dr, dc  # no window contains a lacuna; fall back

    return {
        "dense": (int(dr) - half, int(dc) - half),
        "sparse": (int(sr) - half, int(sc) - half),
    }


def _to_rgb(arr: np.ndarray) -> np.ndarray:
    if arr.ndim == 3:
        return arr.astype(np.uint8)
    if arr.dtype == bool:
        arr = arr.astype(np.uint8) * 255
    elif arr.dtype != np.uint8:
        arr = (np.clip(arr, 0.0, 1.0) * 255).astype(np.uint8)
    return np.stack([arr] * 3, axis=-1)


def save_crop_panel(state: dict, origin: tuple[int, int], win: int, out_path: Path) -> tuple[int, int, int, int]:
    """raw | mask | skeleton | overlay, side by side at full resolution.
    Returns the crop box actually used, as (row0, col0, row1, col1)."""
    rows, cols = state["skeleton"].shape
    r0 = int(np.clip(origin[0], 0, max(0, rows - win)))
    c0 = int(np.clip(origin[1], 0, max(0, cols - win)))
    r1, c1 = r0 + win, c0 + win

    panels = [
        _to_rgb(state["channel"][r0:r1, c0:c1]),
        _to_rgb(state["candidate"][r0:r1, c0:c1]),
        _to_rgb(state["skeleton"][r0:r1, c0:c1]),
        _to_rgb(render_verification(state)[r0:r1, c0:c1]),
    ]
    separator = np.full((win, 4, 3), 128, dtype=np.uint8)
    strip = panels[0]
    for panel in panels[1:]:
        strip = np.hstack([strip, separator, panel])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    imsave(out_path, strip, check_contrast=False)
    return r0, c0, r1, c1


# --- (b) Fragmentation metrics -------------------------------------------

def fragmentation_metrics(state: dict) -> dict:
    """How broken up the skeleton is, and how much of it the per-lacuna
    assignment reaches. Lengths come from the cleaned graph's edge weights,
    so numerator and denominator of the owned fraction are measured the
    same way; the raw skeleton pixel count is reported alongside because it
    is the one unambiguous size of the skeleton."""
    skeleton = state["skeleton"]
    comp_labels = measure.label(skeleton, connectivity=2)
    n_components = int(comp_labels.max())
    skel_px = int(skeleton.sum())
    comp_sizes = np.bincount(comp_labels.ravel())[1:].astype(float) if n_components else np.array([])

    G = state["graph"]
    real = can._real_subgraph(G)
    total_graph_len = float(sum(w for _u, _v, w in real.edges(data="weight")))
    owned_graph_len = 0.0
    for edge in state["edge_owner"]:
        u, v = tuple(edge)
        if real.has_edge(u, v):
            owned_graph_len += float(real[u][v]["weight"])

    degrees = np.array([real.degree(n) for n in real.nodes()], dtype=int)

    return {
        "stem": state["stem"],
        "skel_px": skel_px,
        "n_components": n_components,
        "components_per_10k_skel_px": (10000.0 * n_components / skel_px) if skel_px else 0.0,
        "total_graph_len": total_graph_len,
        "owned_graph_len": owned_graph_len,
        "owned_len_fraction": (owned_graph_len / total_graph_len) if total_graph_len else 0.0,
        "n_nodes": int(degrees.size),
        "deg1_fraction": float((degrees == 1).mean()) if degrees.size else 0.0,
        "comp_len_percentiles": (
            {q: float(np.percentile(comp_sizes, q)) for q in (10, 25, 50, 75, 90)}
            if comp_sizes.size
            else {q: 0.0 for q in (10, 25, 50, 75, 90)}
        ),
        "comp_sizes": comp_sizes,
        "surface_agreement": state["surface_agreement"],
    }


# --- (c) Gap evidence ----------------------------------------------------

def skeleton_endpoints(skeleton: np.ndarray) -> np.ndarray:
    """Pixel-level degree-1 skeleton pixels, i.e. thread ends. Measured on
    the skeleton IMAGE rather than on the cleaned graph, because these are
    the objects a Phase 2 bridging step would operate on -- graph cleanup
    has already pruned some of them away."""
    neighbours = ndi.convolve(skeleton.astype(np.uint8), np.ones((3, 3), np.uint8), mode="constant")
    return np.argwhere(skeleton & (neighbours - skeleton.astype(np.uint8) == 1))


def _walk_back(skeleton: np.ndarray, start: tuple[int, int], max_steps: int) -> tuple[int, int]:
    """Walk inward from an endpoint along the thread and return the pixel
    reached, up to max_steps away. Stops early at a junction, where 'the
    thread's direction' stops being defined."""
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


def gap_evidence(state: dict) -> list[dict]:
    """One record per skeleton endpoint that has a different component
    within GAP_SEARCH_RADIUS_PX. See the module docstring for what
    signal_fraction means and how t_lo_raw is derived."""
    skeleton = state["skeleton"]
    comp_labels = measure.label(skeleton, connectivity=2)
    smoothed = state["surface"]["smoothed"]
    t_lo_raw = state["surface"]["t_lo_raw"]
    channel = state["channel"]
    floor = state["raw_background"]
    buffered = state["buffered_lacunae"]

    radius = GAP_SEARCH_RADIUS_PX
    offsets_r, offsets_c = np.mgrid[-radius:radius + 1, -radius:radius + 1]
    offset_dist = np.hypot(offsets_r, offsets_c)
    in_range = offset_dist <= radius

    rows, cols = skeleton.shape
    records = []
    for r, c in skeleton_endpoints(skeleton):
        r, c = int(r), int(c)
        r0, r1 = max(0, r - radius), min(rows, r + radius + 1)
        c0, c1 = max(0, c - radius), min(cols, c + radius + 1)
        window = comp_labels[r0:r1, c0:c1]
        wr0, wc0 = r0 - (r - radius), c0 - (c - radius)
        dist_window = offset_dist[wr0:wr0 + window.shape[0], wc0:wc0 + window.shape[1]]
        ok_window = in_range[wr0:wr0 + window.shape[0], wc0:wc0 + window.shape[1]]

        other = (window > 0) & (window != comp_labels[r, c]) & ok_window
        if not other.any():
            continue
        masked = np.where(other, dist_window, np.inf)
        idx = np.unravel_index(int(np.argmin(masked)), masked.shape)
        gap_len = float(masked[idx])
        tr, tc = r0 + idx[0], c0 + idx[1]

        back = _walk_back(skeleton, (r, c), LOCAL_DIRECTION_WALK_PX)
        direction = np.array([r - back[0], c - back[1]], dtype=float)
        gap_vector = np.array([tr - r, tc - c], dtype=float)
        norm = np.linalg.norm(direction) * np.linalg.norm(gap_vector)
        if norm > 0:
            cosine = float(np.dot(direction, gap_vector) / norm)
            angle = float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))
        else:
            angle = float("nan")

        # Sample strictly between the two thread pixels, so the measurement
        # is of the gap and not of the threads on either side.
        n_samples = max(1, int(round(gap_len)) - 1)
        ts = np.linspace(0.0, 1.0, n_samples + 2)[1:-1]
        sr = np.clip(np.round(r + ts * (tr - r)).astype(int), 0, rows - 1)
        sc = np.clip(np.round(c + ts * (tc - c)).astype(int), 0, cols - 1)

        headroom = t_lo_raw[sr, sc] - floor
        fraction = np.clip(np.where(headroom > 0, (smoothed[sr, sc] - floor) / headroom, 0.0), 0.0, None)
        records.append(
            {
                "gap_len": gap_len,
                "angle_deg": angle,
                # Mean over the gap answers "is there signal here on
                # average"; the MINIMUM answers the question that actually
                # matters, "is the thread continuous", because one
                # background-level pixel in the middle breaks it however
                # bright the two ends are.
                "signal_fraction": float(fraction.mean()),
                "signal_fraction_min": float(fraction.min()),
                # A gap line crossing the buffered lacuna region samples the
                # lacuna body, not a canaliculus, and will read as bright
                # signal for a reason that has nothing to do with
                # thresholding. Tracked so these can be reported apart.
                "in_lacuna_buffer": float(buffered[sr, sc].mean()),
                "raw_over_background": float(channel[sr, sc].mean() / floor) if floor > 0 else float("nan"),
            }
        )
    return records


# --- (d) Large linear structures -----------------------------------------

def skeleton_path_lengths(skeleton: np.ndarray, comp_labels: np.ndarray, n_components: int) -> np.ndarray:
    """True geodesic length of each skeleton component, in px.

    Counting pixels is wrong here: a diagonal step covers sqrt(2) px, not
    1, so a pixel count makes a diagonal run ~41% shorter than it is and
    lets Feret/length exceed 1. Instead every adjacent pixel PAIR
    contributes its own step length, orthogonal 1 and diagonal sqrt(2),
    halved because the convolution counts each pair from both ends. (A
    staircase pixel with both an orthogonal and a diagonal neighbour on the
    same side is counted slightly generously; that is a sub-pixel effect
    and is not corrected.)"""
    ortho_kernel = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], dtype=np.float32)
    diag_kernel = np.array([[1, 0, 1], [0, 0, 0], [1, 0, 1]], dtype=np.float32)
    skel = skeleton.astype(np.float32)
    ortho = ndi.convolve(skel, ortho_kernel, mode="constant") * skel
    diag = ndi.convolve(skel, diag_kernel, mode="constant") * skel
    per_pixel = 0.5 * (ortho + np.sqrt(2.0) * diag)
    totals = np.bincount(
        comp_labels.ravel(), weights=per_pixel.ravel(), minlength=n_components + 1
    )
    return totals


def _max_centre_distance(coords: np.ndarray) -> float:
    """Largest distance between any two pixel centres of a component. Taken
    over the convex hull for anything big enough that all-pairs would be
    slow; the extreme pair is always on the hull."""
    if coords.shape[0] < 2:
        return 0.0
    points = coords.astype(float)
    if points.shape[0] > 64:
        try:
            from scipy.spatial import ConvexHull

            points = points[ConvexHull(points).vertices]
        except Exception:
            # Collinear components have no 2D hull; the extremes of the
            # dominant axis bound the answer well enough for this table.
            order = np.argsort(points[:, 0] + points[:, 1])
            points = points[[order[0], order[-1]]]
    diff = points[:, None, :] - points[None, :, :]
    return float(np.sqrt((diff ** 2).sum(axis=-1)).max())


def raw_band_profile(state: dict, col_min: int, col_max: int, pad: int = 60) -> str:
    """Column profile of the RAW channel and of the broad-opening mask
    across a named column band. This is the check that matters for whether
    Phase 1's "auto" rule can work: a vascular canal is broad in the RAW
    channel, but canaliculi_v1's top-hat (disk radius TOPHAT_RADIUS_PX)
    deletes anything broader than 2R+1 px, so by the time the canaliculi
    mask exists only the structure's EDGES survive -- and edges are thin,
    which is exactly what a width-based rule cannot catch."""
    channel = state["channel"]
    broad = morphology.opening(channel, morphology.disk(BROAD_OPENING_RADIUS_PX))
    broad_mask, _t = can.total_signal_mask(broad)

    lo, hi = max(0, col_min - pad), min(channel.shape[1], col_max + pad + 1)
    lines = [
        f"    {'col':>5s} {'raw mean':>9s} {'in broad mask':>14s} {'in canal. mask':>15s}",
    ]
    for col in range(lo, hi, 5):
        lines.append(
            f"    {col:5d} {channel[:, col].mean():9.4f} "
            f"{100 * broad_mask[:, col].mean():13.1f}% {100 * state['candidate'][:, col].mean():14.1f}%"
        )
    return "\n".join(lines)


def component_shape_table(state: dict) -> list[dict]:
    """Per skeleton connected component: length (px), end-to-end
    straightness and mean mask width. Straightness is the maximum caliper
    (Feret) diameter over the true geodesic path length: ~1 for a straight
    run, well below 1 for anything wavy or branched. Width is 2x the mean
    distance transform of the MASK sampled on the component's skeleton
    pixels, i.e. how thick the structure that skeleton came from is."""
    comp_labels = measure.label(state["skeleton"], connectivity=2)
    n_components = int(comp_labels.max())
    mask_distance = ndi.distance_transform_edt(state["candidate"])
    path_lengths = skeleton_path_lengths(state["skeleton"], comp_labels, n_components)

    table = []
    for region in measure.regionprops(comp_labels):
        coords = region.coords
        length = float(path_lengths[region.label])
        # End-to-end distance between pixel CENTRES, not regionprops'
        # feret_diameter_max: Feret measures the convex hull of the pixel
        # SQUARES, so it adds up to a pixel diagonal of padding at each
        # end. On a 2px component that padding is the whole measurement and
        # drives straightness to 2.0. Centre-to-centre has no such offset.
        end_to_end = _max_centre_distance(coords)
        widths = 2.0 * mask_distance[coords[:, 0], coords[:, 1]]
        table.append(
            {
                "stem": state["stem"],
                "label": int(region.label),
                "length": length,
                "n_pixels": int(region.area),
                "straightness": (end_to_end / length) if length > 0 else 0.0,
                "max_width": float(widths.max()),
                "mean_width": float(widths.mean()),
                "row_min": int(region.bbox[0]),
                "col_min": int(region.bbox[1]),
                "row_max": int(region.bbox[2]),
                "col_max": int(region.bbox[3]),
                "coords": coords,
            }
        )
    return table


def flag_components(table: list[dict], length_cut: float, width_cut: float) -> list[dict]:
    """Components clearing ALL THREE of the length, straightness and width
    cutoffs. Requiring all three is deliberate: plenty of ordinary
    canaliculi are long, and plenty of short fragments are straight, but a
    structure that is long AND straight AND wide is not a canaliculus."""
    return [
        entry
        for entry in table
        if entry["length"] >= length_cut
        and entry["straightness"] >= STRAIGHTNESS_FLAG_MIN
        and entry["mean_width"] >= width_cut
    ]


def known_structure_scores(entry: dict, rows: int) -> tuple[float, float]:
    """(fraction of this component's pixels inside the 542_z06 column band,
    fraction of image height it spans). Returned as scores rather than a
    yes/no so the candidates can be RANKED: the skeleton is fragmented, so
    a structure spanning the field may well be broken into several
    components, none of which passes a "spans >=50% of the height" gate on
    its own."""
    band = KNOWN_LINEAR_STRUCTURE_542_Z06
    coords = entry["coords"]
    in_band = float(((coords[:, 1] >= band["col_min"]) & (coords[:, 1] <= band["col_max"])).mean())
    height_span = float((entry["row_max"] - entry["row_min"]) / rows)
    return in_band, height_span


# --- (e) Lacuna detection gaps -------------------------------------------

def v2_reject_reason(region, rows: int, cols: int) -> str:
    """Which of segment_lacunae_v2.filter_regions' tests rejects this
    object first, or "kept". Mirrors that function's order exactly; it is
    re-implemented rather than called because filter_regions returns only
    the survivors and the question here is why the others went."""
    if region.area < seg2.TEST_MIN_AREA_PX2:
        return f"area<{seg2.TEST_MIN_AREA_PX2}"
    if region.area > seg2.TEST_MAX_AREA_FRACTION_OF_IMAGE * rows * cols:
        return "area>max_fraction"
    if region.solidity < seg2.TEST_MIN_SOLIDITY:
        return f"solidity<{seg2.TEST_MIN_SOLIDITY}"
    minor, major = region.axis_minor_length, region.axis_major_length
    aspect = (major / minor) if minor > 0 else float("inf")
    if aspect > seg2.TEST_ASPECT_RATIO_MAX:
        return f"aspect>{seg2.TEST_ASPECT_RATIO_MAX}"
    if seg2.EXCLUDE_BORDER_OBJECTS:
        min_row, min_col, max_row, max_col = region.bbox
        if min_row == 0 or min_col == 0 or max_row == rows or max_col == cols:
            return "on_border"
    return "kept"


def v2_object_table(state: dict) -> list[dict]:
    """Every object in v2's PRE-FILTER label image, with the stats v2's
    filters look at and the verdict those filters reach."""
    labels = state["labels"]
    channel = state["channel"]
    rows, cols = labels.shape
    table = []
    for region in measure.regionprops(labels, intensity_image=channel):
        minor, major = region.axis_minor_length, region.axis_major_length
        table.append(
            {
                "label": int(region.label),
                "area": float(region.area),
                "mean_intensity": float(region.intensity_mean),
                "solidity": float(region.solidity),
                "aspect": (major / minor) if minor > 0 else float("inf"),
                "centroid_col": float(region.centroid[1]),
                "centroid_row": float(region.centroid[0]),
                "verdict": v2_reject_reason(region, rows, cols),
            }
        )
    return table


def broad_object_table(state: dict, radius: int) -> list[dict]:
    """Broad bright objects: open the raw channel with a disk large enough
    to delete every canaliculus, then threshold the opened image on its own
    histogram. Objects here that v2's label image does not contain never
    reached v2's top-class cut t_hi at all, which is the case v2's filter
    table cannot show."""
    channel = state["channel"]
    opened = morphology.opening(channel, morphology.disk(radius))
    mask, _t = can.total_signal_mask(opened)
    labels = measure.label(mask, connectivity=2)

    v2_mask = state["labels"] > 0
    table = []
    for region in measure.regionprops(labels, intensity_image=channel):
        coords = region.coords
        minor, major = region.axis_minor_length, region.axis_major_length
        overlap = float(v2_mask[coords[:, 0], coords[:, 1]].mean())
        table.append(
            {
                "label": int(region.label),
                "area": float(region.area),
                "mean_intensity": float(region.intensity_mean),
                "solidity": float(region.solidity),
                "aspect": (major / minor) if minor > 0 else float("inf"),
                "centroid_col": float(region.centroid[1]),
                "centroid_row": float(region.centroid[0]),
                "in_v2_mask_fraction": overlap,
                "kept_by_v2": bool(
                    state["lacuna_id_map"][coords[:, 0], coords[:, 1]].max() > 0
                ),
            }
        )
    return table


def nearest_object(table: list[dict], x: int, y: int) -> dict | None:
    """The table entry whose centroid is closest to a point the user named,
    as (x=col, y=row)."""
    if not table:
        return None
    return min(
        table,
        key=lambda e: (e["centroid_col"] - x) ** 2 + (e["centroid_row"] - y) ** 2,
    )


# --- Reporting helpers ---------------------------------------------------

def ascii_hist(values: np.ndarray, edges: np.ndarray, label: str, width: int = 44) -> None:
    if values.size == 0:
        print(f"  {label}: (no data)")
        return
    counts, _ = np.histogram(values, bins=edges)
    peak = max(1, counts.max())
    print(f"  {label} (n={values.size})")
    for i, count in enumerate(counts):
        bar = "#" * int(round(width * count / peak))
        share = 100.0 * count / values.size
        print(f"    [{edges[i]:6.2f}, {edges[i+1]:6.2f}) {count:7d} {share:5.1f}%  {bar}")


def split_sets(states: list[dict]) -> tuple[list[dict], list[dict]]:
    tuning = [s for s in states if s["stem"] in TUNING_IMAGE_STEMS]
    held_out = [s for s in states if s["stem"] not in TUNING_IMAGE_STEMS]
    return tuning, held_out


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 0 read-only diagnostics for the canaliculi pipeline. Writes nothing outside "
        "results/diagnostics/phase0/ and changes no pipeline behaviour."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--image", type=Path, help="Path to a single .tif image.")
    group.add_argument("--dir", type=Path, help="Directory of .tif images to process.")
    parser.add_argument(
        "--crop",
        type=str,
        default=None,
        help="Extra crop at 'x,y' (x=col, y=row, Fiji convention), taken as the crop CENTRE.",
    )
    args = parser.parse_args()

    if args.image:
        if not args.image.is_file():
            raise FileNotFoundError(f"No such file: {args.image}")
        paths = [args.image]
    else:
        if not args.dir.is_dir():
            raise NotADirectoryError(f"No such directory: {args.dir}")
        paths = sorted(args.dir.glob("*.tif"))

    extra_crop = None
    if args.crop:
        x_str, y_str = args.crop.split(",")
        extra_crop = (int(x_str), int(y_str))

    states, frag_rows, comp_table, gap_records = [], [], [], {}

    print("=" * 100)
    print("PHASE 0 DIAGNOSTICS -- v1-raw / pre-validation, PIXEL units. Read-only: no pipeline behaviour changed.")
    print(f"Tuning set: {', '.join(TUNING_IMAGE_STEMS)}")
    print("=" * 100)

    for path in paths:
        print(f"\nprocessing {path.name} ...")
        state = pipeline_state(path)
        states.append(state)

        out_dir = DIAG_DIR / path.stem.replace(" ", "_")
        origins = pick_crop_origins(state, CROP_SIZE_PX)
        for name, origin in origins.items():
            box = save_crop_panel(state, origin, CROP_SIZE_PX, out_dir / f"crop_{name}.png")
            print(f"  (a) crop_{name}.png  rows {box[0]}-{box[2]}  cols {box[1]}-{box[3]}")
        if extra_crop is not None:
            half = CROP_SIZE_PX // 2
            origin = (extra_crop[1] - half, extra_crop[0] - half)
            box = save_crop_panel(
                state, origin, CROP_SIZE_PX, out_dir / f"crop_x{extra_crop[0]}_y{extra_crop[1]}.png"
            )
            print(f"  (a) crop_x{extra_crop[0]}_y{extra_crop[1]}.png  rows {box[0]}-{box[2]}  cols {box[1]}-{box[3]}")

        frag_rows.append(fragmentation_metrics(state))
        comp_table.extend(component_shape_table(state))
        gap_records[state["stem"]] = gap_evidence(state)
        print(f"  (c) {len(gap_records[state['stem']])} endpoint-gap pairs found")

    tuning, held_out = split_sets(states)

    # --- (b) ---
    print("\n" + "=" * 100)
    print("(b) FRAGMENTATION METRICS, per image")
    print("=" * 100)
    header = (
        f'{"image":24s} {"set":9s} {"skel_px":>8s} {"comps":>6s} {"comp/10k":>9s} '
        f'{"graph_len":>10s} {"owned_len":>10s} {"owned_f":>8s} {"deg1_f":>7s} {"surf_chk":>9s}'
    )
    print(header)
    for row in frag_rows:
        tag = "tuning" if row["stem"] in TUNING_IMAGE_STEMS else "held-out"
        print(
            f'{row["stem"][:24]:24s} {tag:9s} {row["skel_px"]:8d} {row["n_components"]:6d} '
            f'{row["components_per_10k_skel_px"]:9.1f} {row["total_graph_len"]:10.0f} '
            f'{row["owned_graph_len"]:10.0f} {row["owned_len_fraction"]:8.3f} '
            f'{row["deg1_fraction"]:7.3f} {row["surface_agreement"]:9.4f}'
        )

    print(f'\n{"":24s} {"component skeleton length (px)":s}')
    print(f'{"image":24s} {"set":9s} {"p10":>8s} {"p25":>8s} {"p50":>8s} {"p75":>8s} {"p90":>8s}')
    for row in frag_rows:
        tag = "tuning" if row["stem"] in TUNING_IMAGE_STEMS else "held-out"
        p = row["comp_len_percentiles"]
        print(
            f'{row["stem"][:24]:24s} {tag:9s} {p[10]:8.1f} {p[25]:8.1f} {p[50]:8.1f} {p[75]:8.1f} {p[90]:8.1f}'
        )

    for label, subset in (("TUNING", TUNING_IMAGE_STEMS), ("HELD-OUT", None)):
        rows = [
            r for r in frag_rows
            if (r["stem"] in TUNING_IMAGE_STEMS) == (subset is not None)
        ]
        if not rows:
            continue
        sizes = np.concatenate([r["comp_sizes"] for r in rows]) if rows else np.array([])
        print(
            f"\n  POOLED {label} (n={len(rows)} images): "
            f'comp/10k={np.mean([r["components_per_10k_skel_px"] for r in rows]):.1f}  '
            f'owned_len_fraction={np.mean([r["owned_len_fraction"] for r in rows]):.3f}  '
            f'deg1_fraction={np.mean([r["deg1_fraction"] for r in rows]):.3f}  '
            f'median component length={np.median(sizes):.1f}px'
        )

    # --- (c) ---
    print("\n" + "=" * 100)
    print("(c) GAP EVIDENCE -- is the fragmentation a threshold problem or out-of-plane truncation?")
    print("=" * 100)
    print(
        "signal_fraction: 0.0 = the gap sits at the image background level (no signal, canaliculus has\n"
        "left the focal plane, NOT recoverable in 2D); 1.0 = the gap sits right at the threshold that\n"
        "would have admitted it (dim-but-present signal, recoverable by thresholding or bridging)."
    )
    for label, is_tuning in (("TUNING", True), ("HELD-OUT", False)):
        pooled = [
            rec
            for stem, recs in gap_records.items()
            if (stem in TUNING_IMAGE_STEMS) == is_tuning
            for rec in recs
        ]
        if not pooled:
            continue
        # Gap lines that run through the buffered lacuna region are
        # sampling a lacuna body, not a canaliculus. They would read as
        # bright signal for a reason that has nothing to do with the
        # threshold, so they are reported separately rather than pooled in.
        clean = [r for r in pooled if r["in_lacuna_buffer"] == 0.0]
        via_lacuna = len(pooled) - len(clean)
        gaps = np.array([r["gap_len"] for r in clean])
        angles = np.array([r["angle_deg"] for r in clean])
        angles = angles[np.isfinite(angles)]
        means = np.array([r["signal_fraction"] for r in clean])
        mins = np.array([r["signal_fraction_min"] for r in clean])
        print(
            f"\n-- {label} set, {len(pooled)} endpoint-gap pairs "
            f"({via_lacuna} crossed the lacuna buffer and are excluded below, {len(clean)} remain)"
        )
        ascii_hist(gaps, np.arange(0, GAP_SEARCH_RADIUS_PX + 1.5, 1.5), "gap length (px)")
        ascii_hist(angles, np.arange(0, 181, 20.0), "angle: thread direction vs gap vector (deg)")
        ascii_hist(means, np.arange(0, 1.3, 0.1), "MEAN signal fraction along the gap")
        ascii_hist(mins, np.arange(0, 1.3, 0.1), "MINIMUM signal fraction along the gap (the dimmest point)")
        print(
            f"    mean-based:    median={np.median(means):.3f}  >=0.7: {100 * (means >= 0.7).mean():.1f}%  "
            f"<=0.3: {100 * (means <= 0.3).mean():.1f}%"
        )
        print(
            f"    minimum-based: median={np.median(mins):.3f}  >=0.7: {100 * (mins >= 0.7).mean():.1f}%  "
            f"<=0.3: {100 * (mins <= 0.3).mean():.1f}%"
        )
        # A short gap is sampled only a pixel or two from bright thread on
        # both sides, where the Gaussian and the top-hat leave signal
        # regardless. Only the longer gaps probe genuinely empty ground, so
        # the trend across this breakdown is the real evidence.
        print(f'\n    {"gap length":>12s} {"n":>7s} {"median mean":>12s} {"median min":>11s} {"min>=0.7":>9s}')
        for lo, hi in ((2, 5), (5, 8), (8, 11), (11, 15.1)):
            sel = (gaps >= lo) & (gaps < hi)
            if not sel.any():
                continue
            print(
                f'    {f"{lo}-{hi:.0f}px":>12s} {int(sel.sum()):7d} {np.median(means[sel]):12.3f} '
                f'{np.median(mins[sel]):11.3f} {100 * (mins[sel] >= 0.7).mean():8.1f}%'
            )

    # --- (d) ---
    print("\n" + "=" * 100)
    print("(d) LARGE LINEAR STRUCTURES")
    print("=" * 100)
    lengths = np.array([e["length"] for e in comp_table])
    widths = np.array([e["mean_width"] for e in comp_table])
    # Straightness of a 2-pixel fragment is noise, so the distribution is
    # reported over components long enough for a direction to mean
    # anything. The flag rule needs a length far above this anyway.
    long_enough = lengths >= 20.0
    straightnesses = np.array([e["straightness"] for e in comp_table])[long_enough]
    length_cut = float(np.percentile(lengths, LENGTH_FLAG_PERCENTILE))
    width_cut = float(np.percentile(widths, WIDTH_FLAG_PERCENTILE))
    print(f"pooled over {len(comp_table)} components from {len(states)} images")
    for name, arr in (
        ("length (px)", lengths),
        ("mean width (px)", widths),
        (f"straightness (len>=20px, n={int(long_enough.sum())})", straightnesses),
    ):
        print(
            f'  {name:38s} p50={np.percentile(arr, 50):8.2f}  p90={np.percentile(arr, 90):8.2f}  '
            f'p99={np.percentile(arr, 99):8.2f}  max={arr.max():8.2f}'
        )
    print(f'\n  longest 10 components overall (the population the flag rule is aimed at):')
    print(f'    {"image":24s} {"length":>9s} {"straight":>9s} {"mean_w":>7s} {"max_w":>7s} {"rows":>13s} {"cols":>13s}')
    for entry in sorted(comp_table, key=lambda e: -e["length"])[:10]:
        print(
            f'    {entry["stem"][:24]:24s} {entry["length"]:9.1f} {entry["straightness"]:9.3f} '
            f'{entry["mean_width"]:7.2f} {entry["max_width"]:7.2f} '
            f'{entry["row_min"]:5d}-{entry["row_max"]:<7d} {entry["col_min"]:5d}-{entry["col_max"]:<7d}'
        )
    print(
        f"\nflag rule: length >= p{LENGTH_FLAG_PERCENTILE:.0f} ({length_cut:.1f}px) AND "
        f"straightness >= {STRAIGHTNESS_FLAG_MIN} AND mean width >= p{WIDTH_FLAG_PERCENTILE:.0f} ({width_cut:.2f}px)"
    )
    flagged = flag_components(comp_table, length_cut, width_cut)
    print(f"flagged: {len(flagged)} component(s)")
    flagged_ids = {(e["stem"], e["label"]) for e in flagged}
    print(f'\n{"image":24s} {"length":>9s} {"straight":>9s} {"width":>7s} {"rows":>13s} {"cols":>13s}')
    for entry in sorted(flagged, key=lambda e: -e["length"])[:20]:
        print(
            f'{entry["stem"][:24]:24s} {entry["length"]:9.1f} {entry["straightness"]:9.3f} '
            f'{entry["mean_width"]:7.2f} {entry["row_min"]:5d}-{entry["row_max"]:<7d} '
            f'{entry["col_min"]:5d}-{entry["col_max"]:<7d}'
        )

    # Does any of this catch the structure the user pointed out? Ranked,
    # not gated -- see known_structure_scores.
    candidates = []
    for entry in comp_table:
        if entry["stem"] != "542 WT  2_z06c1-2":
            continue
        in_band, height_span = known_structure_scores(entry, 1024)
        if in_band >= 0.5 and entry["length"] >= 50:
            candidates.append((in_band, height_span, entry))
    candidates.sort(key=lambda t: -t[2]["length"])
    print(
        f"\n542_z06 components with >=50% of their pixels in cols "
        f'{KNOWN_LINEAR_STRUCTURE_542_Z06["col_min"]}-{KNOWN_LINEAR_STRUCTURE_542_Z06["col_max"]} '
        f"and length >=50px: {len(candidates)}"
    )
    print(
        f'  {"length":>8s} {"straight":>9s} {"width":>7s} {"in_band":>8s} {"height_f":>9s} '
        f'{"rows":>13s}  flagged?'
    )
    for in_band, height_span, entry in candidates[:10]:
        is_flagged = (entry["stem"], entry["label"]) in flagged_ids
        print(
            f'  {entry["length"]:8.1f} {entry["straightness"]:9.3f} {entry["mean_width"]:7.2f} '
            f'{in_band:8.2f} {height_span:9.2f} {entry["row_min"]:5d}-{entry["row_max"]:<7d}  {is_flagged}'
        )

    z06 = next((s for s in states if s["stem"] == "542 WT  2_z06c1-2"), None)
    if z06 is not None:
        print(
            "\nRAW-channel profile across the 542_z06 band (is the structure broad BEFORE the top-hat?):"
        )
        print(
            raw_band_profile(
                z06,
                KNOWN_LINEAR_STRUCTURE_542_Z06["col_min"],
                KNOWN_LINEAR_STRUCTURE_542_Z06["col_max"],
            )
        )

    # --- (e) ---
    print("\n" + "=" * 100)
    print("(e) LACUNA DETECTION GAPS")
    print("=" * 100)
    for state in states:
        table = v2_object_table(state)
        verdicts: dict[str, int] = {}
        for entry in table:
            verdicts[entry["verdict"]] = verdicts.get(entry["verdict"], 0) + 1
        tag = "tuning" if state["stem"] in TUNING_IMAGE_STEMS else "held-out"
        summary = "  ".join(f"{k}={v}" for k, v in sorted(verdicts.items(), key=lambda kv: -kv[1]))
        print(f'\n{state["stem"][:40]:40s} [{tag}] {len(table)} pre-filter objects -> {summary}')

        broad = broad_object_table(state, BROAD_OPENING_RADIUS_PX)
        broad_alt = broad_object_table(state, BROAD_OPENING_RADIUS_ALT_PX)
        missed = [e for e in broad if not e["kept_by_v2"] and e["area"] >= seg2.TEST_MIN_AREA_PX2]
        print(
            f'  broad-opening objects: r={BROAD_OPENING_RADIUS_PX}: {len(broad)} '
            f'({len(missed)} of area>={seg2.TEST_MIN_AREA_PX2} not kept by v2)   '
            f'r={BROAD_OPENING_RADIUS_ALT_PX}: {len(broad_alt)}'
        )

        if state["stem"] == "542 WT  2_z06c1-2":
            print("  named points (x=col, y=row):")
            for name, (x, y) in KNOWN_POINTS_542_Z06.items():
                v2_entry = nearest_object(table, x, y)
                broad_entry = nearest_object(broad, x, y)
                if v2_entry:
                    distance = np.hypot(v2_entry["centroid_col"] - x, v2_entry["centroid_row"] - y)
                    print(
                        f'    {name:18s} ({x},{y})  v2 object at '
                        f'({v2_entry["centroid_col"]:.0f},{v2_entry["centroid_row"]:.0f}) d={distance:.0f}px  '
                        f'area={v2_entry["area"]:.0f} mean_I={v2_entry["mean_intensity"]:.3f} '
                        f'solidity={v2_entry["solidity"]:.2f} aspect={v2_entry["aspect"]:.2f} '
                        f'-> {v2_entry["verdict"]}'
                    )
                if broad_entry:
                    distance = np.hypot(broad_entry["centroid_col"] - x, broad_entry["centroid_row"] - y)
                    print(
                        f'    {"":18s}          broad object at '
                        f'({broad_entry["centroid_col"]:.0f},{broad_entry["centroid_row"]:.0f}) d={distance:.0f}px  '
                        f'area={broad_entry["area"]:.0f} mean_I={broad_entry["mean_intensity"]:.3f} '
                        f'in_v2_mask={broad_entry["in_v2_mask_fraction"]:.2f} '
                        f'kept_by_v2={broad_entry["kept_by_v2"]}'
                    )

    print("\n" + "=" * 100)
    print(f"crops written under {DIAG_DIR}")
    print("=" * 100)


if __name__ == "__main__":
    main()
