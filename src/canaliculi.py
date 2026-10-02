"""Feature 2: canalicular network, skeleton, cell ownership and measurements.

PRE-VALIDATION. Nothing here has been checked against manual (ImageJ)
counts yet. PIXEL units throughout (config.PIXEL_SIZE_UM is None), so
lengths are px and densities are per px or per px^2.

Lacunae come from src/lacunae.py (imported, not copied).

Method, per image. Adapted from the OCY pipeline (Kollmannsberger et al.,
New J. Phys. 2017) where noted. OCY works on 3D confocal stacks; these are
single 2D optical sections, which is behind every departure from it.
    1. Flatten the background: a light Gaussian, a white top-hat and a
       histogram-mode offset subtraction (OCY_main.m, OCY_thr_stack.m).
    2. Threshold with hysteresis: dim pixels are kept only where they
       connect to confidently bright ones. Both cuts come from the image's
       own histogram. Inside vascular-canal structures ("flagged", found on
       the raw channel) only already-bright pixels are kept.
    3. Remove the lacuna bodies (plus a 2 px buffer) and small specks, then
       skeletonize to one-pixel centre lines.
    4. Bridge short gaps where a thread was interrupted: only gaps that are
       short, in line with the thread, and hold real signal all along. No
       bridge may touch a lacuna or a flagged structure. OCY has no such step:
       in 3D a thread leaving one plane continues in the next.
    5. Turn the skeleton into a graph and clean it to a fixed point: prune
       short spurs, collapse crossing artefacts, merge degree-2 chains
       (OCY's Skel2Graph3D with THR_BRANCH).
    6. Ownership: each lacuna is a virtual source attached to skeleton nodes
       near its body; one multi-source shortest-path run gives every
       reachable node to the cell it connects to through the network, and
       every edge to the owner of its nearer end (OCY_assign_dist.m). There
       is no limit on distance.
    7. Measure, per lacuna and per field (below).

Measures:
    HEADLINE (they do not depend on which cell owns which thread)
        roots_count          threads leaving each lacuna's surface
        ring_length_r30_px   skeleton px within 30 px of each lacuna body,
                             each pixel counted for its nearest lacuna
        canalicular_length_density_per_px   per field: all skeleton px
                             divided by the analysed field area
    ALSO REPORTED
        ring_length_r60_px   the same ring measure at 60 px
    OWNERSHIP-DEPENDENT (network descriptors, not headline measures)
        owned_length_px      total length of the edges a cell owns
        edge_count           number of graph edges a cell owns
        mean_edge_length_px  owned_length_px / edge_count
    edge_count is an OCY-style NETWORK parameter, not "canaliculi per cell":
    a branching tree with T tips has about 2T - 1 edges. Only about a third
    of the skeleton is graph-connected to any lacuna in these 2D sections,
    and owned threads can lie hundreds of px from their cell.

Outputs, per image, in results/<image>/:
    canaliculi_verification.png   each lacuna and the threads it owns in one
                                  colour, over the original image
    canaliculi_skeleton.png       the skeleton, unannotated
    canaliculi_mask.png           the network mask, unannotated
    canaliculi_measurements.xlsx  "summary", "field", "per_lacuna", "notes"
    canaliculi_measurements.json  the same numbers plus the parameters
After a --dir run, also results/summary_table.xlsx and .csv (one row per
image; see write_summary_table).

Regression check: 543-2 must give 62.33 edges per interior cell, 27.41 px
mean edge length and 21 bridges (python src/diagnostics.py reference-check).

Usage (from the repo root):
    python src/canaliculi.py --dir data/WT
    python src/canaliculi.py --image "data/WT/543-2.tif"
    python src/canaliculi.py --dir data/WT -o OTHER_FOLDER    (default output: results/)
"""

from __future__ import annotations

import argparse
import colorsys
import csv
import json
import random
import sys
from pathlib import Path

import networkx as nx
import numpy as np
from scipy import ndimage as ndi
from skimage import filters, measure, morphology, segmentation
from skimage.io import imsave
from skan import Skeleton, summarize

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lacunae  # noqa: E402

# Parameters: network mask
# None of these has been validated against manual counts. Values derived from
# data were derived on a fixed tuning set (542_z06, 543-2, 682_z29) with the
# other five WT images held out, and say so.

# Sigma (px) of the Gaussian applied before the top-hat, to suppress shot
# noise without erasing threads. OCY_main.m does the same with
# smooth3(img,'gaussian',5). Must stay below the canaliculus width (about
# 5 px here).
SMOOTH_SIGMA_PX = 0.8

# Radius (px) of the disk for the white top-hat. Adapted from OCY_thr_stack.m,
# which uses strel('disk',25) at 0.2 um/voxel. A white top-hat keeps what is
# narrower than its disk and flattens what is broader, so the radius has to
# sit just above the widest real canaliculus and well below the diffuse halo
# around each lacuna. Measured after top-hatting: canalicular half-widths are
# p50 about 3.0 and p99 about 4.2 px, so real threads are at most about 8 px
# across and a disk of radius 5 (diameter 11) cannot fit inside one. Checked
# by eye at r=4, 5 and 6 on 542_z06 and 543-2: r=4 starts breaking threads
# into fragments, r=6 starts fusing neighbouring threads into ribbons, r=5
# does neither. After the top-hat, the image's histogram mode is subtracted
# as a residual background offset, as OCY_thr_stack.m does.
TOPHAT_RADIUS_PX = 5

# Hysteresis threshold. The high cut is the lower of the image's two
# three-class multi-Otsu cuts (its own histogram), and the low cut is this
# fraction of it. Adopted as the default on 2026-09-28 from the Phase 2
# comparison of eight settings: with gap bridging, it was the one setting
# inside both guards fixed in advance (total skeleton length at most 1.20x
# and loops at most max(1.5x, +50) of the old default) on the tuning and the
# held-out images, while cutting skeleton components per 10,000 px from 225
# to 169. 0.5 was tried first and failed both guards by growing dim regions
# into sheets. One value tried after one failure, not a sweep: the weakest
# provenance of any default here.
HYSTERESIS_LOW_FRACTION = 0.75

# Buffer (px) removed from the network mask around each lacuna body, so the
# lacuna's own bright rim is not read as a stub of canaliculus.
LACUNA_DILATION_PX = 2

# Mask fragments smaller than this (px^2) are dropped as thresholding noise
# before skeletonizing. Deliberately small so a real, thin, short thread
# survives; despeckling is by pixel count, never by erosion, which would
# delete one-pixel-wide threads.
MIN_THREAD_OBJECT_PX2 = 8

# Parameters: vascular-canal structures ("flagged")
# Broad bright structures (vascular canals, canal edges) are found on the RAW
# channel, where they are one large object; after the top-hat they survive
# only as fragments indistinguishable from canaliculi. They are used for one
# thing only: hysteresis and gap bridging may not ADD connections inside
# them. Nothing that the plain threshold keeps is ever removed. Without this,
# hysteresis and bridging grew a vertical segment along the vascular band of
# 542_z06 (near (555,500)) that ownership then handed to a cell.

# Radius (px) of the opening that finds broad objects in the raw channel: it
# erases anything narrower than 2R+1 px. Measured canalicular widths are p50
# about 6.0 and p99 about 8.5 px, so R=8 (diameter 17) erases every
# canaliculus while leaving lacunae and larger structures. At this radius the
# 542_z06 structure is a single 27,496 px^2 object.
BROAD_OPENING_RADIUS_PX = 8

# Shape gate: a broad object is flagged only if it clears both limits. From
# all 98 kept v2 lacunae and all 103 lacuna-scale objects over the 8 WT
# images: the largest lacuna-scale object spans 0.23 of an image dimension
# with a 210.6 px major axis. Flagged structures span 0.58 to 0.80 with major
# axes of 646 to 920 px; sorted spans run 0.80, 0.73, 0.63, 0.62, 0.58, then
# 0.37, 0.35, 0.34, a clean gap that 0.45 sits in. The major-axis cut is 2x
# the largest lacuna major axis. Both select the same 5 objects on the WT
# images. Derived from WT only.
FLAGGED_MIN_SPAN_FRACTION = 0.45
FLAGGED_MIN_MAJOR_AXIS_PX = 420.0

# Dilation (px) of the flagged region, to cover the structure's own boundary.
# Network-mask density in rings outward from the 542_z06 structure, against
# the far field: 0.70x at 0 to 4 px, then 0.96x, 1.09x, 1.01x, 1.01x. It is at
# baseline from about 4 px out, so 4 px, not more.
FLAGGED_DILATION_PX = 4

# Parameters: gap bridging
# A 2D section cuts a 3D network, so a canaliculus leaving the focal plane
# ends mid-field. Phase 0(c) sampled the signal in the gap between each
# skeleton endpoint and its nearest different component (pooled over the 8 WT
# images; median of the MINIMUM signal fraction along the gap, where 1.0 is
# the threshold): 2 to 5 px 0.964, 5 to 8 px 0.886, 8 to 11 px 0.734, 11 to
# 15 px 0.568. A blind morphological closing is not used: only 21% of
# endpoint-to-neighbour angles are under 20 degrees, so most nearest
# neighbours are parallel threads, and closing would fuse them.

# Longest gap bridged (px). At 8 to 11 px the dimmest point in a gap still
# sits at 0.73 of the threshold (median); by 11 to 15 px it is 0.57 and only
# about 29% of gaps keep a minimum above 0.7.
MAX_BRIDGE_GAP_PX = 10.0

# Largest angle (degrees) between the thread's own direction at the endpoint
# and the vector to the partner. Pooled angles run 21.0% under 20 degrees,
# 17.8% at 20 to 40, 17.7% at 40 to 60, then a long tail to 180; 40 keeps the
# two leading bins, the pairs that point at each other.
MAX_BRIDGE_ANGLE_DEG = 40.0

# The MINIMUM signal fraction along the gap must reach this: one
# background-level pixel breaks a thread however bright its ends. 93.5% of
# 5 to 8 px gaps qualify but only 29.9% of 11 to 15 px gaps, so this limit
# and MAX_BRIDGE_GAP_PX reinforce each other.
MIN_BRIDGE_SIGNAL_FRACTION = 0.7

# How far (px) to walk back along the thread to estimate its direction: long
# enough to average out the staircase of a rasterized diagonal, short enough
# not to average across a real bend.
DIRECTION_WALK_PX = 5

# Parameters: graph and ownership

# Terminal branches shorter than this (px) are thresholding spurs and are
# pruned, repeatedly, since pruning one can expose another.
PRUNE_SPUR_LEN_PX = 4

# Internal edges (both ends real junctions) shorter than this (px) are
# crossing artefacts and are collapsed by merging their ends. OCY's
# Skel2Graph3D THR_BRANCH does the same with 5 voxels, about 2.5x their
# canaliculus diameter; scaled to our threads that would be about 15 px and
# would remove half of all internal edges, so the value is anchored on our
# own geometry instead: a false junction where two threads cross spans at
# most one thread width, about 6 px here. The pooled internal-edge length
# distribution is smooth (p10 3.4, p25 7.8, p50 16.7 px); this removes 18% of
# internal edges.
MIN_INTERNAL_EDGE_LEN_PX = 6

# Safety stop for the prune, collapse and merge loop; it normally converges
# in a few passes.
GRAPH_CLEANUP_MAX_ITER = 20

# A skeleton node within this distance (px) of a lacuna body is attached to
# that lacuna. The first guess of 5 left 28 of 98 lacunae with no attachment
# at all. With the current mask the smallest node-to-body gap per lacuna runs
# p50 2.24, p95 5.00, max 7.00 px, so 10 attaches every lacuna with room to
# spare.
LACUNA_ATTACH_GAP_PX = 10

# Parameters: per-cell measures

# Attachment points closer than this (px) count as one root, so one thick
# thread meeting the boundary over several skeleton nodes is counted once.
# Canalicular full width is p50 about 6.0 and p99 about 8.5 px, so two
# points 8 px apart or less cannot be separate threads.
ROOT_MERGE_DIST_PX = 8.0

# Radii (px) for the ring skeleton length: skeleton pixels within this
# Euclidean distance of the lacuna body, each counted for its nearest lacuna
# only. Uses neither the graph nor ownership. 30 px is the ring used in the
# round 2 local-density measurement; 60 px is twice that, about two thirds
# of the median lacuna major axis (89 px). Pixel counts, the same unit as
# the per-field skeleton length, so a diagonal step counts 1 px.
RING_RADII_PX = (30, 60)

# Parameters: drawing (cosmetic, no effect on any number)

# Owned skeleton is dilated by this (px) in the verification image so thin
# threads are visible.
VIS_SKELETON_DILATION_PX = 2

# One colour per lacuna: hues evenly spaced for contrast, then shuffled with
# config.RANDOM_SEED so neighbours rarely get similar hues and a rerun gives
# the same colours.
COLOR_SATURATION = 0.9
COLOR_VALUE = 1.0

NEIGHBOUR_OFFSETS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

# Per-lacuna measures, in output order, with units and kind.
CELL_METRICS = [
    ("roots_count", "count", "headline"),
    ("ring_length_r30_px", "px", "headline"),
    ("ring_length_r60_px", "px", "reported"),
    ("owned_length_px", "px", "ownership-dependent"),
    ("edge_count", "count", "ownership-dependent"),
    ("mean_edge_length_px", "px", "ownership-dependent"),
]

# Size-normalised per-cell measures, appended after every existing column so
# no existing column changes name, order or value. From the overnight report
# (docs/OVERNIGHT_REPORT.md, task 4.1): roots and ring lengths rise with
# lacuna size (Spearman 0.84 and 0.88 across images, positive within every
# image), and these forms remove that dependence. Definitions as in
# experiments/task4_size.py:
#   perimeter_px                skimage regionprops perimeter of the lacuna
#   ring_area_rR_px2            pixels of the nearest-lacuna partition within R
#                               px of the body, other lacunae excluded (A_R)
#   in_frame_fraction_rR        in-frame share of the full annulus of radius R
#                               around this lacuna alone, in an unbounded plane
#   ring_density_rR             ring_length_rR_px / ring_area_rR_px2 (L_R / A_R)
#   roots_per_100px_perimeter   100 x roots_count / perimeter_px
# (name, unit, extra decimals beyond config.CSV_FLOAT_PRECISION)
NORMALISED_METRICS = [
    ("perimeter_px", "px", 0),
    ("ring_area_r30_px2", "px^2", 0),
    ("ring_area_r60_px2", "px^2", 0),
    ("in_frame_fraction_r30", "unitless", 0),
    ("in_frame_fraction_r60", "unitless", 0),
    ("ring_density_r30", "px^-1", 4),
    ("ring_density_r60", "px^-1", 4),
    ("roots_per_100px_perimeter", "per 100 px", 0),
]


# Network mask

def _subtract_background_mode(img: np.ndarray) -> np.ndarray:
    """Residual-background offset removal after the top-hat, adapted from
    OCY_thr_stack.m: a 256-bin histogram of img/max(img) with bin 1 and bins
    200 and up zeroed; the modal bin is the background level, which is
    subtracted, clipping at 0."""
    peak = float(img.max())
    if peak <= 0:
        return img
    counts, edges = np.histogram(img / peak, bins=256, range=(0.0, 1.0))
    counts[0] = 0
    counts[199:] = 0
    if counts.max() == 0:
        return img
    background = float(edges[int(np.argmax(counts))]) * peak
    return np.clip(img - background, 0.0, None)


def preprocess_channel(channel: np.ndarray) -> np.ndarray:
    """Gaussian, white top-hat and mode subtraction, renormalized to
    [0, 1], so thin threads threshold as thin threads instead of fusing into
    ribbons."""
    img = channel
    if SMOOTH_SIGMA_PX > 0:
        img = ndi.gaussian_filter(img, SMOOTH_SIGMA_PX)
    img = morphology.white_tophat(img, morphology.disk(TOPHAT_RADIUS_PX))
    img = _subtract_background_mode(img)
    peak = float(img.max())
    return img / peak if peak > 0 else img


def total_signal_mask(img: np.ndarray) -> tuple[np.ndarray, float]:
    """The lower of the two three-class multi-Otsu cuts on this image's own
    histogram (background against everything else). Strict ">", so a pixel
    exactly at the cut is never included."""
    try:
        thresholds = filters.threshold_multiotsu(img, classes=3)
        t_lo = float(thresholds[0])
    except ValueError:
        t_lo = float(filters.threshold_otsu(img))
    return img > t_lo, t_lo


def flagged_structures(channel: np.ndarray) -> np.ndarray:
    """Broad bright raw-channel structures far larger and more elongated
    than any lacuna (vascular canals, canal edges), dilated by
    FLAGGED_DILATION_PX. Nothing is removed from anything here; see the
    flagged parameters above for what it is used for."""
    rows, cols = channel.shape
    opened = morphology.opening(channel, morphology.disk(BROAD_OPENING_RADIUS_PX))
    mask, _threshold = total_signal_mask(opened)
    labels = measure.label(mask, connectivity=2)

    flagged = np.zeros(channel.shape, dtype=bool)
    for region in measure.regionprops(labels):
        min_row, min_col, max_row, max_col = region.bbox
        span = max((max_row - min_row) / rows, (max_col - min_col) / cols)
        major = float(region.axis_major_length)
        if span < FLAGGED_MIN_SPAN_FRACTION or major < FLAGGED_MIN_MAJOR_AXIS_PX:
            continue
        flagged |= labels == region.label

    if flagged.any() and FLAGGED_DILATION_PX > 0:
        flagged = morphology.dilation(flagged, morphology.disk(FLAGGED_DILATION_PX))
    return flagged


def hysteresis_mask(img: np.ndarray, no_growth: np.ndarray) -> tuple[np.ndarray, float]:
    """Hysteresis threshold of the preprocessed image. Returns (mask, the
    strict cut). Inside `no_growth` only pixels already above the strict cut
    survive, so there hysteresis can add nothing."""
    strict_mask, t_lo = total_signal_mask(img)
    low = t_lo * HYSTERESIS_LOW_FRACTION
    mask = filters.apply_hysteresis_threshold(img, low, t_lo)
    if no_growth.any():
        mask = mask & ~(no_growth & ~strict_mask)
    return mask, t_lo


def network_candidate_mask(
    preprocessed: np.ndarray, lacuna_mask: np.ndarray, flagged: np.ndarray
) -> tuple[np.ndarray, float]:
    """Threshold, remove the buffered lacuna bodies, despeckle by size."""
    signal, t_lo = hysteresis_mask(preprocessed, flagged)
    buffered_lacunae = morphology.dilation(lacuna_mask, morphology.disk(LACUNA_DILATION_PX))
    candidate = signal & ~buffered_lacunae
    candidate = morphology.remove_small_objects(candidate, min_size=MIN_THREAD_OBJECT_PX2)
    return candidate, t_lo


# Gap bridging

def skeleton_endpoints(skeleton: np.ndarray) -> np.ndarray:
    """Pixel-level degree-1 skeleton pixels, i.e. thread ends."""
    neighbours = ndi.convolve(skeleton.astype(np.uint8), np.ones((3, 3), np.uint8), mode="constant")
    return np.argwhere(skeleton & (neighbours - skeleton.astype(np.uint8) == 1))


def walk_back(skeleton: np.ndarray, start: tuple[int, int], max_steps: int) -> tuple[int, int]:
    """Walk inward from an endpoint along the thread, up to max_steps. Stops
    at a junction, where the thread's direction stops being defined."""
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
    """Every endpoint-to-component pair passing all three tests: gap length,
    angle, and minimum signal along the gap.

    The signal fraction is preprocessed / t_lo, so 1.0 means "this pixel
    would have been in the mask". `forbidden` is the lacuna bodies plus the
    flagged structures: a bridge may not start in, end in or cross either."""
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

        # One bridge per endpoint pair, so two endpoints facing each other
        # do not both draw the same line.
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
    """Draw each accepted bridge into the mask, which is then
    re-skeletonized, so a bridge becomes part of the network."""
    out = mask.copy()
    for bridge in bridges:
        sr, sc = bridge["pixels"]
        out[sr, sc] = True
    return out


# Lacuna maps

def build_lacuna_maps(labels: np.ndarray, kept: list[tuple]) -> tuple[np.ndarray, np.ndarray]:
    """(lacuna_mask, lacuna_id_map). lacuna_id_map is 0 outside any kept
    lacuna, else its 1..N id, the numbering src/lacunae.py uses."""
    lacuna_id_map = np.zeros(labels.shape, dtype=np.int32)
    for lacuna_id, (region, _on_border) in enumerate(kept, start=1):
        lacuna_id_map[labels == region.label] = lacuna_id
    return lacuna_id_map > 0, lacuna_id_map


def nearest_lacuna_map(lacuna_id_map: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """For every pixel, (distance to the nearest lacuna pixel, that lacuna's
    id): a Euclidean partition seeded from the lacunae."""
    dist, indices = ndi.distance_transform_edt(lacuna_id_map == 0, return_indices=True)
    nearest_id = lacuna_id_map[indices[0], indices[1]]
    return dist, nearest_id


# Graph

def _node_key(row: float, col: float) -> tuple[int, int]:
    return (int(round(row)), int(round(col)))


def _is_cell_node(node) -> bool:
    """True for the virtual ("cell", id) source nodes."""
    return isinstance(node, tuple) and len(node) == 2 and node[0] == "cell"


def real_subgraph(G: nx.Graph) -> nx.Graph:
    """The skeleton graph without the virtual cell nodes."""
    return G.subgraph([n for n in G.nodes() if not _is_cell_node(n)])


def build_network_graph(skeleton: np.ndarray):
    """One weighted graph of the whole skeleton: nodes are junction and
    endpoint pixels, edges are branches weighted by length (px). Each edge
    keeps `branches`, the skan branch indices whose pixels it covers, so
    simplification never loses the pixel paths.

    nx.Graph holds no parallel edges: where two branches join the same pair
    of nodes (a small loop) the shorter weight is kept, though both
    branches' pixels are recorded. This affects 1.3% of branches over the 8
    WT images."""
    G = nx.Graph()
    if not skeleton.any():
        return G, None

    skel_obj = Skeleton(skeleton)
    branches = summarize(skel_obj, separator="-")

    for idx, b in branches.iterrows():
        if b["branch-type"] == 3:  # isolated loop, no tip
            continue
        src = _node_key(b["image-coord-src-0"], b["image-coord-src-1"])
        dst = _node_key(b["image-coord-dst-0"], b["image-coord-dst-1"])
        w = float(b["branch-distance"])
        if src == dst:
            continue
        if G.has_edge(src, dst):
            G[src][dst]["branches"].append(idx)
            G[src][dst]["weight"] = min(w, G[src][dst]["weight"])
        else:
            G.add_edge(src, dst, weight=w, branches=[idx])

    return G, skel_obj


def _node_absorbed(G: nx.Graph, node) -> list:
    """Branch indices folded into `node` by a collapse or a chain merge, kept
    so the verification image still paints every pixel a cell owns."""
    return G.nodes[node].setdefault("absorbed", [])


def prune_spurs(G: nx.Graph) -> bool:
    """Remove terminal branches shorter than PRUNE_SPUR_LEN_PX, repeating
    until nothing more qualifies. True if anything changed."""
    any_change = False
    changed = True
    while changed:
        changed = False
        for node in list(G.nodes()):
            if G.degree(node) == 1:
                neighbor = next(iter(G.neighbors(node)))
                if G[node][neighbor]["weight"] < PRUNE_SPUR_LEN_PX:
                    G.remove_node(node)
                    changed = any_change = True
    G.remove_nodes_from([n for n in list(G.nodes()) if G.degree(n) == 0])
    return any_change


def _merge_nodes(G: nx.Graph, keep, drop) -> None:
    """Fold `drop` into `keep`: their edge disappears (its pixels are
    absorbed by `keep`) and every other edge of `drop` is re-pointed at
    `keep`, merging with an existing edge by the shorter weight."""
    absorbed = _node_absorbed(G, keep)
    absorbed.extend(G[keep][drop]["branches"])
    absorbed.extend(_node_absorbed(G, drop))

    for neighbor in list(G.neighbors(drop)):
        if neighbor == keep:
            continue
        data = G[drop][neighbor]
        if G.has_edge(keep, neighbor):
            existing = G[keep][neighbor]
            existing["branches"].extend(data["branches"])
            existing["weight"] = min(existing["weight"], data["weight"])
        else:
            G.add_edge(keep, neighbor, weight=data["weight"], branches=list(data["branches"]))
    G.remove_node(drop)


def collapse_short_internal_edges(G: nx.Graph, dist_to_lacuna: np.ndarray) -> bool:
    """Merge the two ends of every internal edge (both ends real junctions)
    shorter than MIN_INTERNAL_EDGE_LEN_PX: in a 2D projection two threads
    that merely cross produce two junctions a thread width apart, and the
    stub between them is the crossing, not a canaliculus. The end nearer a
    lacuna survives, so a merge cannot cost a cell its attachment. True if
    anything changed."""
    changed = False
    for u, v in list(G.edges()):
        if not G.has_edge(u, v):
            continue  # already consumed by an earlier merge in this pass
        if G.degree(u) < 3 or G.degree(v) < 3:
            continue  # terminal edge, handled by prune_spurs
        if G[u][v]["weight"] >= MIN_INTERNAL_EDGE_LEN_PX:
            continue
        keep, drop = (u, v) if dist_to_lacuna[u] <= dist_to_lacuna[v] else (v, u)
        _merge_nodes(G, keep, drop)
        changed = True
    return changed


def simplify_degree2_chains(G: nx.Graph) -> bool:
    """Dissolve every degree-2 node into its neighbours, summing weights, so
    one uninterrupted thread is ONE edge of its true length. Pruning and
    collapsing leave such nodes behind; OCY never sees them because it
    rebuilds its graph from the voxel skeleton each round. A degree-2 node
    whose neighbours coincide or already share an edge is left alone, since
    nx.Graph cannot hold the parallel edge. True if anything changed."""
    changed = False
    for node in list(G.nodes()):
        if not G.has_node(node) or G.degree(node) != 2:
            continue
        a, b = list(G.neighbors(node))
        if a == b or G.has_edge(a, b):
            continue
        weight = G[node][a]["weight"] + G[node][b]["weight"]
        branches = list(G[node][a]["branches"]) + list(G[node][b]["branches"]) + _node_absorbed(G, node)
        G.remove_node(node)
        G.add_edge(a, b, weight=weight, branches=branches)
        changed = True
    return changed


def clean_network_graph(G: nx.Graph, dist_to_lacuna: np.ndarray) -> nx.Graph:
    """Prune, collapse and merge, repeated until nothing changes, because
    each step creates work for the others (OCY repeats its condense and
    re-graph cycle until network length stops changing)."""
    for _ in range(GRAPH_CLEANUP_MAX_ITER):
        changed = prune_spurs(G)
        changed |= collapse_short_internal_edges(G, dist_to_lacuna)
        changed |= simplify_degree2_chains(G)
        if not changed:
            break
    G.remove_nodes_from([n for n in list(G.nodes()) if G.degree(n) == 0])
    return G


def attach_lacunae(G: nx.Graph, dist_to_lacuna: np.ndarray, nearest_id: np.ndarray, cell_ids: list[int]) -> nx.Graph:
    """Add a virtual ("cell", id) node per lacuna, linked to every skeleton
    node within LACUNA_ATTACH_GAP_PX of its body. The link weight is the gap
    distance, so paths start at the cell boundary."""
    for node in list(G.nodes()):
        r, c = node
        gap = float(dist_to_lacuna[r, c])
        if gap <= LACUNA_ATTACH_GAP_PX:
            lacuna_id = int(nearest_id[r, c])
            if lacuna_id in cell_ids:
                G.add_edge(("cell", lacuna_id), node, weight=gap)
    return G


def assign_by_connectivity(G: nx.Graph, cell_ids: list[int]) -> tuple[dict, dict]:
    """Multi-source Dijkstra from all cell nodes at once. Every reachable
    skeleton node is owned by the cell whose shortest graph path reaches it.
    Returns (owner {node: cell_id}, node_dist {node: graph distance to that
    cell, px})."""
    sources = [("cell", i) for i in cell_ids if G.has_node(("cell", i))]
    if not sources:
        return {}, {}

    dist, paths = nx.multi_source_dijkstra(G, sources, weight="weight")
    owner: dict = {}
    node_dist: dict = {}
    for target, path in paths.items():
        if _is_cell_node(target):
            continue
        source = path[0]
        if not _is_cell_node(source):
            continue
        owner[target] = source[1]
        node_dist[target] = dist[target]
    return owner, node_dist


def assign_edges(G: nx.Graph, owner: dict, node_dist: dict) -> dict:
    """Give every real edge an owning cell: the owner of whichever end is
    nearer a cell through the network (OCY_assign_dist.m). Ties go to the
    lower cell id so a rerun is reproducible. Edges with no owned end (a
    fragment not connected to any lacuna) are left out. Returns
    {frozenset({u, v}): cell_id}."""
    edge_owner: dict = {}
    for u, v in G.edges():
        if _is_cell_node(u) or _is_cell_node(v):
            continue  # virtual attachment edge, not a canaliculus
        cu, cv = owner.get(u), owner.get(v)
        if cu is None and cv is None:
            continue
        if cu is None:
            winner = cv
        elif cv is None:
            winner = cu
        else:
            du, dv = node_dist.get(u, np.inf), node_dist.get(v, np.inf)
            if du < dv:
                winner = cu
            elif dv < du:
                winner = cv
            else:
                winner = min(cu, cv)
        edge_owner[frozenset((u, v))] = winner
    return edge_owner


def cell_edge_lengths(G: nx.Graph, edge_owner: dict, cell_id: int) -> list[float]:
    """Length (px) of each edge this cell owns: len() is edge_count, sum()
    is owned_length_px."""
    lengths = []
    for edge, owner_id in edge_owner.items():
        if owner_id != cell_id:
            continue
        u, v = tuple(edge)
        lengths.append(float(G[u][v]["weight"]))
    return lengths


def cell_root_count(G: nx.Graph, cell_id: int) -> int:
    """Distinct threads leaving this lacuna's surface: the skeleton nodes
    attached to its virtual node, clustered by single linkage at
    ROOT_MERGE_DIST_PX so one thick thread counts once."""
    src = ("cell", cell_id)
    if not G.has_node(src):
        return 0
    points = [n for n in G.neighbors(src) if not _is_cell_node(n)]
    if not points:
        return 0

    unmerged = list(points)
    clusters: list[list] = []
    while unmerged:
        seed = unmerged.pop()
        cluster = [seed]
        changed = True
        while changed:
            changed = False
            for other in list(unmerged):
                if any(np.hypot(other[0] - m[0], other[1] - m[1]) <= ROOT_MERGE_DIST_PX for m in cluster):
                    cluster.append(other)
                    unmerged.remove(other)
                    changed = True
        clusters.append(cluster)
    return len(clusters)


def ring_lengths(skeleton: np.ndarray, dist_to_lacuna: np.ndarray, nearest_id: np.ndarray, n_lacunae: int) -> dict:
    """{radius: array indexed by lacuna id} of skeleton pixel counts within
    that radius of each lacuna, each pixel counted for its nearest lacuna."""
    out = {}
    for radius in RING_RADII_PX:
        pixels = skeleton & (dist_to_lacuna <= radius) & (nearest_id > 0)
        out[radius] = np.bincount(nearest_id[pixels], minlength=n_lacunae + 1)
    return out


def build_owner_pixel_map(shape: tuple[int, int], skel_obj, G: nx.Graph, edge_owner: dict, owner: dict) -> np.ndarray:
    """Paint every owned branch's pixel path with its cell id, including the
    branches absorbed into nodes during cleanup, for the verification image."""
    owner_map = np.zeros(shape, dtype=np.int32)
    if skel_obj is None:
        return owner_map

    def paint(branch_indices, cell_id):
        for branch_index in branch_indices:
            coords = skel_obj.path_coordinates(branch_index)
            rows = np.clip(coords[:, 0].astype(int), 0, shape[0] - 1)
            cols = np.clip(coords[:, 1].astype(int), 0, shape[1] - 1)
            owner_map[rows, cols] = cell_id

    for edge, cell_id in edge_owner.items():
        u, v = tuple(edge)
        if not G.has_edge(u, v):
            continue
        paint(G[u][v]["branches"], cell_id)
    for node, cell_id in owner.items():
        if G.has_node(node):
            paint(G.nodes[node].get("absorbed", ()), cell_id)
    return owner_map


# Measurements

def measure_cells(kept: list[tuple], skeleton: np.ndarray, dist_to_lacuna: np.ndarray,
                  nearest_id: np.ndarray, precision: int) -> dict:
    """Graph, ownership and every per-lacuna measure."""
    cell_ids = list(range(1, len(kept) + 1))

    G, skel_obj = build_network_graph(skeleton)
    clean_network_graph(G, dist_to_lacuna)
    attach_lacunae(G, dist_to_lacuna, nearest_id, cell_ids)
    owner, node_dist = assign_by_connectivity(G, cell_ids)
    edge_owner = assign_edges(G, owner, node_dist)
    rings = ring_lengths(skeleton, dist_to_lacuna, nearest_id, len(kept))

    rows = []
    for lacuna_id, (_region, on_border) in enumerate(kept, start=1):
        lengths = cell_edge_lengths(G, edge_owner, lacuna_id)
        count = len(lengths)
        total = float(sum(lengths))
        row = {
            "lacuna_id": lacuna_id,
            "on_border": bool(on_border),
            "roots_count": cell_root_count(G, lacuna_id),
        }
        for radius in RING_RADII_PX:
            row[f"ring_length_r{radius}_px"] = int(rings[radius][lacuna_id])
        row["owned_length_px"] = round(total, precision)
        row["edge_count"] = count
        row["mean_edge_length_px"] = round(total / count if count else 0.0, precision)
        rows.append(row)

    return {
        "rows": rows,
        "graph": G,
        "edge_owner": edge_owner,
        "owner": owner,
        "node_dist": node_dist,
        "owner_map": build_owner_pixel_map(skeleton.shape, skel_obj, G, edge_owner, owner),
    }


def add_normalised_measures(rows: list[dict], lacuna_id_map: np.ndarray, dist_to_lacuna: np.ndarray,
                            nearest_id: np.ndarray, precision: int) -> None:
    """Append the NORMALISED_METRICS to each per-lacuna row, in place."""
    regions = {r.label: r for r in measure.regionprops(lacuna_id_map)}
    n_rows, n_cols = lacuna_id_map.shape
    areas = {}
    for radius in RING_RADII_PX:
        ring = (dist_to_lacuna > 0) & (dist_to_lacuna <= radius)
        areas[radius] = np.bincount(nearest_id[ring], minlength=lacuna_id_map.max() + 1)
    for row in rows:
        region = regions[row["lacuna_id"]]
        perimeter = float(region.perimeter)
        row["perimeter_px"] = round(perimeter, precision)
        fractions, densities = {}, {}
        for radius in RING_RADII_PX:
            area = int(areas[radius][row["lacuna_id"]])
            row[f"ring_area_r{radius}_px2"] = area
            # Full annulus around this lacuna alone: its mask in a box padded
            # beyond the radius, so the frame cannot cut it.
            pad = radius + 2
            r0, c0, r1, c1 = region.bbox
            box = np.zeros((r1 - r0 + 2 * pad, c1 - c0 + 2 * pad), dtype=bool)
            box[pad:pad + r1 - r0, pad:pad + c1 - c0] = region.image
            dist = ndi.distance_transform_edt(~box)
            ann_r, ann_c = np.nonzero((dist > 0) & (dist <= radius))
            ann_r = ann_r + r0 - pad
            ann_c = ann_c + c0 - pad
            inside = (ann_r >= 0) & (ann_r < n_rows) & (ann_c >= 0) & (ann_c < n_cols)
            fractions[radius] = round(float(inside.mean()), precision)
            length = row[f"ring_length_r{radius}_px"]
            densities[radius] = round(length / area, precision + 4) if area else None
        for radius in RING_RADII_PX:
            row[f"in_frame_fraction_r{radius}"] = fractions[radius]
        for radius in RING_RADII_PX:
            row[f"ring_density_r{radius}"] = densities[radius]
        row["roots_per_100px_perimeter"] = (
            round(100.0 * row["roots_count"] / perimeter, precision) if perimeter > 0 else None)


def summarize_interior(rows: list[dict], precision: int) -> dict:
    """Mean, median and sample SD over interior lacunae for every per-cell
    measure. SD is None below 2 values."""
    interior = [m for m in rows if not m["on_border"]]
    stats = {"interior_lacuna_count": len(interior), "units": "px"}
    for field, _unit, _kind in CELL_METRICS:
        values = np.array([m[field] for m in interior if m.get(field) is not None], dtype=float)
        if values.size == 0:
            mean = median = sd = None
        else:
            mean = round(float(values.mean()), precision)
            median = round(float(np.median(values)), precision)
            sd = round(float(values.std(ddof=1)), precision) if values.size >= 2 else None
        stats[field] = {"mean": mean, "median": median, "sd": sd}
    for field, _unit, extra in NORMALISED_METRICS:
        if not interior or field not in interior[0]:
            continue
        values = np.array([m[field] for m in interior if m.get(field) is not None], dtype=float)
        digits = precision + extra
        if values.size == 0:
            mean = median = sd = None
        else:
            mean = round(float(values.mean()), digits)
            median = round(float(np.median(values)), digits)
            sd = round(float(values.std(ddof=1)), digits) if values.size >= 2 else None
        stats[field] = {"mean": mean, "median": median, "sd": sd}
    return stats


def field_metrics(skeleton: np.ndarray, G: nx.Graph, lacuna_mask: np.ndarray, n_lacunae: int, precision: int) -> dict:
    """Per-field measures. They use the whole skeleton and no ownership, so
    fragmentation affects them far less than any per-cell measure."""
    rows, cols = skeleton.shape
    analysed_area = float(rows * cols - lacuna_mask.sum())
    skel_px = float(skeleton.sum())

    comp_labels = measure.label(skeleton, connectivity=2)
    sizes = np.bincount(comp_labels.ravel())[1:].astype(float)

    real = real_subgraph(G)
    junctions = sum(1 for n in real.nodes() if real.degree(n) >= 3)

    def per_area(value: float) -> float | None:
        return round(value / analysed_area, precision + 4) if analysed_area > 0 else None

    return {
        "analysed_area_px2": round(analysed_area, precision),
        "total_skeleton_length_px": round(skel_px, precision),
        "canalicular_length_density_per_px": per_area(skel_px),
        "junction_count": int(junctions),
        "junction_density_per_px2": per_area(float(junctions)),
        "lacuna_count": int(n_lacunae),
        "lacunae_per_px2": per_area(float(n_lacunae)),
        "skeleton_component_count": int(sizes.size),
        "mean_component_length_px": round(float(sizes.mean()), precision) if sizes.size else 0.0,
        "median_component_length_px": round(float(np.median(sizes)), precision) if sizes.size else 0.0,
    }


FIELD_UNITS = {
    "analysed_area_px2": "px^2",
    "total_skeleton_length_px": "px",
    "canalicular_length_density_per_px": "px^-1",
    "junction_count": "count",
    "junction_density_per_px2": "px^-2",
    "lacuna_count": "count",
    "lacunae_per_px2": "px^-2",
    "skeleton_component_count": "count",
    "mean_component_length_px": "px",
    "median_component_length_px": "px",
}


def analyse_image(image_path: Path) -> dict:
    """Everything feature 2 computes for one image, without writing."""
    precision = config.CSV_FLOAT_PRECISION
    lac = lacunae.analyse_image(image_path)
    _display, channel = lacunae.load_channel(image_path)
    kept = lac["kept"]

    lacuna_mask, lacuna_id_map = build_lacuna_maps(lac["labels"], kept)
    flagged = flagged_structures(channel)
    preprocessed = preprocess_channel(channel)
    candidate, t_lo = network_candidate_mask(preprocessed, lacuna_mask, flagged)
    skeleton = morphology.skeletonize(candidate)

    bridges = find_bridges(skeleton, preprocessed, t_lo, lacuna_mask | flagged)
    if bridges:
        candidate = apply_bridges(candidate, bridges)
        skeleton = morphology.skeletonize(candidate)

    dist_to_lacuna, nearest_id = nearest_lacuna_map(lacuna_id_map)
    cells = measure_cells(kept, skeleton, dist_to_lacuna, nearest_id, precision)
    add_normalised_measures(cells["rows"], lacuna_id_map, dist_to_lacuna, nearest_id, precision)
    return {
        "image_path": image_path,
        "lacunae": lac,
        "display": lac["display"],
        "lacuna_id_map": lacuna_id_map,
        "candidate": candidate,
        "skeleton": skeleton,
        "flagged": flagged,
        "bridges": bridges,
        "t_lo": t_lo,
        "rows": cells["rows"],
        "summary": summarize_interior(cells["rows"], precision),
        "field": field_metrics(skeleton, cells["graph"], lacuna_mask, len(kept), precision),
        "graph": cells["graph"],
        "edge_owner": cells["edge_owner"],
        "node_dist": cells["node_dist"],
        "owner_map": cells["owner_map"],
    }


# Output

def lacuna_colors(n_lacunae: int) -> dict[int, tuple[int, int, int]]:
    hues = [i / n_lacunae for i in range(n_lacunae)]
    random.Random(config.RANDOM_SEED).shuffle(hues)
    colors = {}
    for lacuna_id, hue in enumerate(hues, start=1):
        r, g, b = colorsys.hsv_to_rgb(hue, COLOR_SATURATION, COLOR_VALUE)
        colors[lacuna_id] = (int(r * 255), int(g * 255), int(b * 255))
    return colors


def save_verification(result: dict, out_path: Path) -> None:
    """Each lacuna outlined, and the skeleton it owns drawn, in its colour
    over the full-brightness original, so the tracing can be checked against
    the real threads underneath. Unowned skeleton is not drawn."""
    n = len(result["lacunae"]["kept"])
    colors = lacuna_colors(n)
    vis = result["display"].copy()
    for lacuna_id in range(1, n + 1):
        color = colors[lacuna_id]
        boundary = segmentation.find_boundaries(result["lacuna_id_map"] == lacuna_id, mode="outer")
        vis[boundary] = color
        owned_skeleton = result["skeleton"] & (result["owner_map"] == lacuna_id)
        if owned_skeleton.any():
            owned_skeleton = morphology.dilation(owned_skeleton, morphology.disk(VIS_SKELETON_DILATION_PX))
        vis[owned_skeleton] = color
    out_path.parent.mkdir(parents=True, exist_ok=True)
    imsave(out_path, vis, check_contrast=False)


def parameters(result: dict) -> dict:
    return {
        "pixel_size_um": config.PIXEL_SIZE_UM,
        "smooth_sigma_px": SMOOTH_SIGMA_PX,
        "tophat_radius_px": TOPHAT_RADIUS_PX,
        "background_mode_subtract": True,
        "threshold": "hysteresis, high cut = lower 3-class multi-Otsu cut",
        "hysteresis_low_fraction": HYSTERESIS_LOW_FRACTION,
        "network_threshold_t_lo": result["t_lo"],
        "lacuna_threshold_t_hi": result["lacunae"]["t_hi"],
        "lacuna_dilation_px": LACUNA_DILATION_PX,
        "min_thread_object_px2": MIN_THREAD_OBJECT_PX2,
        "block_growth_in_flagged": True,
        "broad_opening_radius_px": BROAD_OPENING_RADIUS_PX,
        "flagged_min_span_fraction": FLAGGED_MIN_SPAN_FRACTION,
        "flagged_min_major_axis_px": FLAGGED_MIN_MAJOR_AXIS_PX,
        "flagged_dilation_px": FLAGGED_DILATION_PX,
        "flagged_area_px2": float(result["flagged"].sum()),
        "gap_bridging": True,
        "max_bridge_gap_px": MAX_BRIDGE_GAP_PX,
        "max_bridge_angle_deg": MAX_BRIDGE_ANGLE_DEG,
        "min_bridge_signal_fraction": MIN_BRIDGE_SIGNAL_FRACTION,
        "direction_walk_px": DIRECTION_WALK_PX,
        "prune_spur_len_px": PRUNE_SPUR_LEN_PX,
        "min_internal_edge_len_px": MIN_INTERNAL_EDGE_LEN_PX,
        "graph_cleanup_max_iter": GRAPH_CLEANUP_MAX_ITER,
        "lacuna_attach_gap_px": LACUNA_ATTACH_GAP_PX,
        "ownership": "graph connectivity, no distance cap",
        "root_merge_dist_px": ROOT_MERGE_DIST_PX,
        "ring_radii_px": list(RING_RADII_PX),
    }


NOTE = (
    "Pre-validation: not checked against manual counts. Pixel units. Headline "
    "measures: roots_count, ring_length_r30_px, and the per-field "
    "canalicular_length_density_per_px. owned_length_px, edge_count and "
    "mean_edge_length_px depend on which cell owns which thread, which is "
    "unbounded in distance; they are network descriptors, and edge_count is "
    "not canaliculi per cell. Summary statistics cover interior lacunae only."
)


def save_json(result: dict, out_path: Path) -> None:
    payload = {
        "status": "pre-validation",
        "units": "px",
        "image": result["image_path"].name,
        "note": NOTE,
        "lacuna_count": result["lacunae"]["lacuna_count"],
        "interior_lacuna_count": result["summary"]["interior_lacuna_count"],
        "n_bridges": len(result["bridges"]),
        "headline_measures": ["roots_count", "ring_length_r30_px", "field.canalicular_length_density_per_px"],
        "ownership_dependent_measures": ["owned_length_px", "edge_count", "mean_edge_length_px"],
        "normalised_measures": [f for f, _u, _x in NORMALISED_METRICS],
        "summary": result["summary"],
        "field": result["field"],
        "bridges": [
            {
                "from_row_col": list(b["from"]),
                "to_row_col": list(b["to"]),
                "gap_len_px": round(b["gap_len"], 4),
                "angle_deg": round(b["angle_deg"], 4),
                "min_signal_fraction": round(b["min_signal_fraction"], 4),
            }
            for b in result["bridges"]
        ],
        "parameters": parameters(result),
        "lacunae": result["rows"],
        "provenance": lacunae.provenance(),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)


def save_xlsx(result: dict, out_path: Path) -> None:
    from openpyxl import Workbook

    wb = Workbook()
    summary = wb.active
    summary.title = "summary"
    summary.append(["image", "status", "lacuna_count", "interior_lacuna_count", "n_bridges"])
    summary.append([
        result["image_path"].name, "pre-validation", result["lacunae"]["lacuna_count"],
        result["summary"]["interior_lacuna_count"], len(result["bridges"]),
    ])
    summary.append([])
    summary.append(["Pre-validation, pixel units. Statistics below are over interior (on_border False) lacunae only."])
    summary.append(["metric", "kind", "mean", "median", "sd", "units", "n"])
    stats = result["summary"]
    for field, unit, kind in CELL_METRICS:
        s = stats[field]
        summary.append([field, kind, s["mean"], s["median"], s["sd"], unit, stats["interior_lacuna_count"]])
    for field, unit, _extra in NORMALISED_METRICS:
        if field in stats:
            s = stats[field]
            summary.append([field, "normalised", s["mean"], s["median"], s["sd"], unit, stats["interior_lacuna_count"]])

    field_sheet = wb.create_sheet("field")
    field_sheet.append(["metric", "kind", "value", "units"])
    for key, value in result["field"].items():
        kind = "headline" if key == "canalicular_length_density_per_px" else "reported"
        field_sheet.append([key, kind, value, FIELD_UNITS[key]])

    per_lacuna = wb.create_sheet("per_lacuna")
    columns = ["lacuna_id", "on_border"] + [f for f, _u, _k in CELL_METRICS]
    columns += [f for f, _u, _x in NORMALISED_METRICS if result["rows"] and f in result["rows"][0]]
    per_lacuna.append(columns)
    for m in result["rows"]:
        per_lacuna.append([m[c] for c in columns])

    notes = wb.create_sheet("notes")
    notes.append([NOTE])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)


def write_outputs(result: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    imsave(out_dir / "canaliculi_mask.png", (result["candidate"] * 255).astype(np.uint8), check_contrast=False)
    imsave(out_dir / "canaliculi_skeleton.png", (result["skeleton"] * 255).astype(np.uint8), check_contrast=False)
    save_verification(result, out_dir / "canaliculi_verification.png")
    save_xlsx(result, out_dir / "canaliculi_measurements.xlsx")
    save_json(result, out_dir / "canaliculi_measurements.json")


SUMMARY_COLUMNS = [
    "image",
    "file",
    "status",
    "lacuna count",
    "interior lacuna count",
    "median lacuna area (px^2)",
    "roots per cell",
    "ring length 30 px per cell (px)",
    "ring length 60 px per cell (px)",
    "field length density (px^-1)",
    # Appended (normalised measures, means over interior cells).
    "perimeter per cell (px)",
    "ring area 30 px per cell (px^2)",
    "ring area 60 px per cell (px^2)",
    "in-frame fraction 30 px per cell",
    "in-frame fraction 60 px per cell",
    "ring density 30 px per cell (px^-1)",
    "ring density 60 px per cell (px^-1)",
    "roots per 100 px perimeter per cell",
]

SUMMARY_NOTES = [
    "PRE-VALIDATION. Not yet checked against manual (ImageJ) counts.",
    "PIXEL units. The images carry no micron calibration.",
    "Median lacuna area and every per-cell value are over interior lacunae (not touching the frame edge).",
    "roots per cell: distinct canalicular threads leaving each lacuna surface (mean over interior cells).",
    "ring length 30 / 60 px per cell: skeleton px within 30 / 60 px of each lacuna body, each pixel counted",
    "for its nearest lacuna only (mean over interior cells). Neither depends on network ownership.",
    "field length density: all skeleton px divided by the analysed field area (field minus lacunae).",
    "Headline measures: roots per cell, ring length 30 px, field length density.",
    "Appended columns (normalised measures, means over interior cells): perimeter; ring area A_r, the pixels",
    "of the nearest-lacuna partition within r px of the body; in-frame fraction of the full r px annulus;",
    "ring density L_r / A_r; roots per 100 px of perimeter. They remove the dependence of roots and ring",
    "length on lacuna size (docs/OVERNIGHT_REPORT.md, task 4.1).",
]


def write_summary_table(results: list[dict], out_root: Path) -> None:
    """results/summary_table.csv and .xlsx: one row per image."""
    rows = []
    for r in results:
        rows.append([
            lacunae.clean_name(r["image_path"]),
            r["image_path"].name,
            "pre-validation",
            r["lacunae"]["lacuna_count"],
            r["lacunae"]["interior_lacuna_count"],
            r["lacunae"]["summary"]["area_px2"]["median"],
            r["summary"]["roots_count"]["mean"],
            r["summary"]["ring_length_r30_px"]["mean"],
            r["summary"]["ring_length_r60_px"]["mean"],
            r["field"]["canalicular_length_density_per_px"],
        ] + [r["summary"].get(f, {}).get("mean") for f, _u, _x in NORMALISED_METRICS])

    out_root.mkdir(parents=True, exist_ok=True)
    with open(out_root / "summary_table.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(SUMMARY_COLUMNS)
        writer.writerows(rows)

    from openpyxl import Workbook

    wb = Workbook()
    sheet = wb.active
    sheet.title = "summary"
    sheet.append(SUMMARY_COLUMNS)
    for row in rows:
        sheet.append(row)
    notes = wb.create_sheet("notes")
    for line in SUMMARY_NOTES:
        notes.append([line])
    wb.save(out_root / "summary_table.xlsx")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Canalicular network and per-lacuna measurements (pre-validation, px)."
    )
    lacunae.add_input_arguments(parser)
    args = parser.parse_args()

    results = []
    for image_path in lacunae.image_paths(args):
        result = analyse_image(image_path)
        out_dir = args.out / lacunae.clean_name(image_path)
        write_outputs(result, out_dir)
        s = result["summary"]
        print(
            f"{image_path.name}: lacunae={result['lacunae']['lacuna_count']}  "
            f"roots/cell={s['roots_count']['mean']}  ring30/cell={s['ring_length_r30_px']['mean']} px  "
            f"field density={result['field']['canalicular_length_density_per_px']}  "
            f"edges/cell={s['edge_count']['mean']}  mean edge={s['mean_edge_length_px']['mean']} px  "
            f"bridges={len(result['bridges'])}  -> {out_dir}"
        )
        results.append({k: result[k] for k in ("image_path", "lacunae", "summary", "field")})

    if args.dir:
        write_summary_table(results, args.out)
        print(f"summary table -> {args.out / 'summary_table.xlsx'} and .csv")


if __name__ == "__main__":
    main()
