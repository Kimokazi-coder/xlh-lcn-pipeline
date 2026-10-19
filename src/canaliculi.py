"""Feature 2: canalicular network, skeleton, cell ownership and measurements.

PRE-VALIDATION. Nothing here has been checked against manual (ImageJ)
counts yet. PIXEL units throughout (config.PIXEL_SIZE_UM is None), so
lengths are px and densities are per px or per px^2.

Lacunae come from src/lacunae.py (imported, not copied).

There is ONE method: the ridge method with gap bridging off, which was
variant D of the ablation (tag archive-2026-10-13). Nothing about it is
validated and it has not been compared with a manual count.

Method, per image. Adapted from the OCY pipeline (Kollmannsberger et al.,
New J. Phys. 2017) where noted. OCY works on 3D confocal stacks; these are
single 2D optical sections, which is behind every departure from it.
    1. Flatten the background: a light Gaussian, a white top-hat and a
       histogram-mode offset subtraction (OCY_main.m, OCY_thr_stack.m).
    2. Take the Sato ridge response of that flattened image over the scales
       RIDGE_SIGMAS_PX, as the maximum across them. A canaliculus is found
       because it is a thin bright ridge, not because it is bright.
    3. Threshold the RESPONSE with hysteresis: dim pixels are kept only where
       they connect to confidently bright ones. Both cuts come from the
       response's own histogram. Inside vascular-canal structures ("flagged",
       found on the raw channel) only already-bright pixels are kept.
    4. Remove the lacuna bodies (plus a 2 px buffer) and small specks. Then,
       inside each lacuna's own GLOW ZONE and nowhere else, accept the response
       down to config.GLOW_ZONE_CUT_FRACTION of the low cut where it continues
       mask the global cut already produced: one global cut empties a ring
       around every body, where a thread's contrast runs at a third to two
       thirds of normal (section 18 of docs/METHODS.md). The zone is the
       lacuna's own glow extent, measured on the raw channel, never a fixed
       width. Then skeletonize to one-pixel centre lines. There is no gap
       bridging: a gap is left as a gap.
    5. Turn the skeleton into a graph and clean it to a fixed point: prune
       short spurs, collapse crossing artefacts, merge degree-2 chains
       (OCY's Skel2Graph3D with THR_BRANCH).
    6. Ownership: each lacuna is a virtual source attached to skeleton nodes
       near its body, by CONTACT within config.CONTACT_REACH_PX (no test, at
       weight 0, so a touched lacuna owns what touches it) and by SIGNAL beyond
       it; one multi-source shortest-path run gives every reachable node to the
       cell it connects to through the network, and every edge to the owner of
       its nearer end (OCY_assign_dist.m).
    7. Apply the biological length limit: every skeleton pixel further than
       config.MAX_CANALICULUS_LENGTH_UM from the surface of its owning lacuna,
       measured ALONG THE NETWORK, is pruned, and ownership is rebuilt on what
       is left, to a fixed point. A pixel that no lacuna reaches within the
       limit is not pruned; it simply stays unowned.
    8. Measure, per lacuna and per field (below).

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

Outputs, per image, in results/<label>/2_canaliculi/ (the label is the short
image name of config.IMAGE_LABELS; see lacunae.image_label and result_path):
    <label>_canaliculi_skeleton.png       the skeleton, unannotated
    <label>_canaliculi_mask.png           the network mask, unannotated
    <label>_canaliculi_results.xlsx       "summary", "field", "per_lacuna", "notes"
    <label>_canaliculi_results.json       the same numbers plus the parameters
    <label>_canaliculi_verification.png   each lacuna and the threads it owns in
                                  one colour, over the original image, to check
                                  the tracing against the real threads
After a --dir run, also results/all_images/summary_all_images.xlsx and .csv
(one row per image; see write_summary_table).

Regression check: 543-2 must give 161.00 edges per interior cell, 21.63 px
mean edge length and 8.50 roots per interior cell
(python src/diagnostics.py reference-check).

Usage (from the repo root):
    python src/canaliculi.py --dir data/WT
    python src/canaliculi.py --image "data/WT/543-2.tif"
    python src/canaliculi.py --dir data/WT -o OTHER_FOLDER    (default output: results/)
"""

from __future__ import annotations

import argparse
import colorsys
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

# Parameters: the ridge filter

# The scales of the Sato tubeness filter, in pixels. These are variant D of the
# ablation (tag archive-2026-10-13, src/canal_physical/ablation.py): the scales
# that bracket the canalicular half width measured on this data, with one step
# between them. A Sato filter responds to a tube whose radius is near sigma.
# Confocal blur widens a thread beyond its true size, so these describe the
# image and not the canaliculus, and none of them came from a published value.
RIDGE_SIGMAS_PX = (3.0, 3.6, 4.2)

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

# Parameters: the glow zone

# How the radial glow profile of a lacuna is sampled, on the RAW channel.
# 180 rays is one every 2 degrees, which is finer than the body outline's own
# steps; the step along a ray is half a pixel; the profile is smoothed over 3
# samples so one dark pixel cannot end it; and the local background is the
# median of the raw channel in this ring around the body, every lacuna body
# excluded. The ring starts beyond the widest glow the cap allows and is 20 px
# deep, which is enough pixels for a stable median.
GLOW_PROFILE_ANGLES = 180
GLOW_PROFILE_STEP_PX = 0.5
GLOW_PROFILE_SMOOTH = 3
GLOW_BACKGROUND_BAND_PX = (70.0, 90.0)

# The widest a glow zone may be. Set in micrometres in config.py; see the
# comment there.
GLOW_ZONE_MAX_PX = config.px_int(config.GLOW_ZONE_MAX_UM)

# Parameters: the biological length limit
# The longest a canaliculus may be, along the network from the surface of the
# lacuna that owns it. Set in micrometres in config.py and converted here, so the
# micrometre value is the parameter and this follows from it. Nothing about it is
# validated; see config.MAX_CANALICULUS_LENGTH_UM for where the value comes from.
MAX_CANALICULUS_LENGTH_PX = config.px_int(config.MAX_CANALICULUS_LENGTH_UM)

# The prune can cut a path and leave what was behind it unreachable, which can
# push another pixel past the limit, so it repeats. This bounds the repetition;
# it is never reached in practice and exists so a pathological image cannot loop.
PRUNE_LENGTH_MAX_ITER = 10


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

# How far a lacuna reaches to attach a thread. Set in micrometres in config.py;
# see the comment there. Attachment is by SIGNAL, not by distance alone: a node
# within reach attaches only if the straight path from the lacuna surface to it
# carries ridge response all the way, so a path across empty space is refused.
LACUNA_ATTACH_REACH_PX = config.px_int(config.LACUNA_ATTACH_REACH_UM)

# How close a skeleton node must be to a lacuna body to attach to it by CONTACT:
# no signal test, and at weight 0, so the touched lacuna reaches it before any
# neighbour can. Already in pixels in config.py; see the comment there. Setting
# it to 0 turns the rule off, which is how the before and after runs of the
# contact diagnostic are made.
CONTACT_REACH_PX = config.CONTACT_REACH_PX

# How close a thread must come to a lacuna to count as ATTACHED for the ring
# attached length measure. This was the ownership reach while ownership went by
# distance alone, and it stays at that value as a constant of its own: a measure
# must not change meaning because an ownership rule changed, or a before and
# after comparison would be reading two different measures.
RING_ATTACHED_GAP_PX = 10

# How far a dim thread may continue past the skeleton a lacuna already owns, in
# pixels. Set in micrometres in config.py; see the comment there.
DIM_THREAD_REACH_PX = config.px_int(config.DIM_THREAD_REACH_UM)

# The shortest an unattached dim component may be, in pixels, once skeletonized.
# Set in micrometres in config.py; see the comment there.
UNATTACHED_MIN_LENGTH_PX = config.px_int(config.UNATTACHED_MIN_LENGTH_UM)

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


def preprocess_unnormalised(channel: np.ndarray) -> np.ndarray:
    """Gaussian, white top-hat and mode subtraction, in the channel's own
    units (before preprocess_channel divides by the maximum)."""
    img = channel
    if SMOOTH_SIGMA_PX > 0:
        img = ndi.gaussian_filter(img, SMOOTH_SIGMA_PX)
    img = morphology.white_tophat(img, morphology.disk(TOPHAT_RADIUS_PX))
    return _subtract_background_mode(img)


def preprocess_channel(channel: np.ndarray) -> np.ndarray:
    """Gaussian, white top-hat and mode subtraction, renormalized to
    [0, 1], so thin threads threshold as thin threads instead of fusing into
    ribbons."""
    img = preprocess_unnormalised(channel)
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


def ridge_response(preprocessed: np.ndarray) -> np.ndarray:
    """Sato tubeness of the flattened channel over RIDGE_SIGMAS_PX, as the
    maximum across the scales.

    A canaliculus is found because it is a ridge, a thin bright line, and not
    because it is bright: that is the one idea separating this method from a
    plain threshold of the intensity. black_ridges is False because the
    canaliculi are bright on a dark background. The response has no physical
    unit, and only its own histogram is ever used to threshold it.

    Sato rather than Frangi: both are Hessian based, and Sato's tubeness keeps a
    single response per scale without Frangi's second shape term, which is tuned
    for blob rejection and would need two more constants with no evidence here."""
    response = filters.sato(preprocessed.astype(np.float64), sigmas=list(RIDGE_SIGMAS_PX),
                            black_ridges=False, mode="reflect")
    return np.nan_to_num(response, nan=0.0, posinf=0.0, neginf=0.0)


def hysteresis_mask(img: np.ndarray, no_growth: np.ndarray, t_lo: float | None = None) -> tuple[np.ndarray, float]:
    """Hysteresis threshold of `img`. Returns (mask, the strict cut). Inside
    `no_growth` only pixels already above the strict cut survive, so there
    hysteresis can add nothing. A given t_lo replaces the computed strict cut
    (sensitivity diagnostics only).

    The strict cut is the lower of the image's own three-class multi-Otsu cuts,
    so it comes from this image and nothing else."""
    if t_lo is None:
        strict_mask, t_lo = total_signal_mask(img)
    else:
        strict_mask = img > t_lo
    low = t_lo * HYSTERESIS_LOW_FRACTION
    mask = filters.apply_hysteresis_threshold(img, low, t_lo)
    if no_growth.any():
        mask = mask & ~(no_growth & ~strict_mask)
    return mask, t_lo


def network_candidate_mask(
    preprocessed: np.ndarray, lacuna_mask: np.ndarray, flagged: np.ndarray, t_lo: float | None = None
) -> tuple[np.ndarray, float, np.ndarray]:
    """(mask, the strict cut, the ridge response). Hysteresis on the RIDGE
    RESPONSE of the flattened channel, then the buffered lacuna bodies removed
    and the small fragments despeckled.

    The cut is the response's own, and a given t_lo replaces it (sensitivity
    diagnostics only). Despeckling is by pixel count, never by erosion, which
    would delete one-pixel-wide threads."""
    response = ridge_response(preprocessed)
    signal, t_lo = hysteresis_mask(response, flagged, t_lo)
    buffered_lacunae = morphology.dilation(lacuna_mask, morphology.disk(LACUNA_DILATION_PX))
    candidate = signal & ~buffered_lacunae
    candidate = morphology.remove_small_objects(candidate, min_size=MIN_THREAD_OBJECT_PX2)
    return candidate, t_lo, response


# The glow a lacuna casts, and the zone that follows it

def _moving_average(values: np.ndarray, window: int) -> np.ndarray:
    """A centred moving average along the last axis, edges repeated. One dark
    pixel on a ray must not end a profile by itself."""
    if window <= 1:
        return values
    pad = window // 2
    padded = np.pad(values, ((0, 0), (pad, pad)), mode="edge")
    kernel = np.ones(window, dtype=np.float64) / window
    return np.apply_along_axis(lambda row: np.convolve(row, kernel, mode="valid"), 1, padded)


def glow_extent_px(channel: np.ndarray, lacuna_id_map: np.ndarray, n_lacunae: int) -> np.ndarray:
    """How far each lacuna's glow reaches beyond its body, in px, indexed by
    lacuna id (index 0 unused). Measured on the RAW channel, never on the
    flattened one, because the flattening is what removes the glow.

    A bright osteocyte is surrounded by out-of-plane glow, and a thread that
    leaves it is traced only where that glow ends: METHODS section 18 measured
    the ridge response at 31 to 71% of its value 40 px further out, which is why
    one global cut empties a ring around every body. The width of that ring is a
    property of each lacuna and not a constant, and it is what widens in Hyp
    bone with a periosteocytic lesion, so every rule built on it has to be built
    on the lacuna's own measurement.

    Per lacuna:
      - the LOCAL BACKGROUND is the median of the raw channel in the ring
        GLOW_BACKGROUND_BAND_PX around the body, every lacuna body left out, so
        it is this lacuna's own surroundings and not the image's;
      - GLOW_PROFILE_ANGLES rays leave the centroid, and along each one the
        distance is the true distance to the body, so a concave body is measured
        from its real edge;
      - the profile is the raw channel along the ray, smoothed over
        GLOW_PROFILE_SMOOTH samples, and the surface value is its mean within
        1.5 px of the body edge;
      - the ray's extent is the first distance at which the profile falls to
        config.GLOW_PROFILE_FRACTION of the surface value's excess above the
        background, that is to background + fraction x (surface - background);
      - a ray that leaves the frame or enters another lacuna before it answers
        is censored; a ray whose surface is already at or below the background
        has no glow and answers 0;
      - the lacuna's extent is the MEDIAN over the rays that answered, capped at
        GLOW_ZONE_MAX_PX.
    """
    height, width = channel.shape
    all_bodies = lacuna_id_map > 0
    extents = np.zeros(n_lacunae + 1, dtype=np.float64)
    if GLOW_ZONE_MAX_PX <= 0:
        return extents  # the rule turned off, which is how a before run is made
    angles = np.linspace(0.0, 2.0 * np.pi, GLOW_PROFILE_ANGLES, endpoint=False)
    sin_a, cos_a = np.sin(angles), np.cos(angles)
    cap = float(GLOW_ZONE_MAX_PX)

    for lacuna_id in range(1, n_lacunae + 1):
        body = lacuna_id_map == lacuna_id
        if not body.any():
            continue
        rows, cols = np.nonzero(body)
        r0, c0 = float(rows.mean()), float(cols.mean())
        gap = ndi.distance_transform_edt(~body)

        ring = ((gap >= GLOW_BACKGROUND_BAND_PX[0]) & (gap <= GLOW_BACKGROUND_BAND_PX[1])
                & ~all_bodies)
        background = float(np.median(channel[ring])) if ring.any() else float(
            np.median(channel[~all_bodies]))

        radius = float(np.hypot(rows - r0, cols - c0).max())
        steps = np.arange(0.0, radius + cap + 2.0, GLOW_PROFILE_STEP_PX)
        rr = r0 + steps[None, :] * sin_a[:, None]
        cc = c0 + steps[None, :] * cos_a[:, None]
        in_frame = (rr >= 0) & (rr <= height - 1) & (cc >= 0) & (cc <= width - 1)
        d = ndi.map_coordinates(gap, [rr, cc], order=1, mode="nearest")
        v = ndi.map_coordinates(channel, [rr, cc], order=1, mode="nearest")
        other = ndi.map_coordinates((all_bodies & ~body).astype(np.uint8), [rr, cc],
                                    order=0, mode="nearest") > 0

        n_ang, n_s = rr.shape
        index = np.arange(n_s)[None, :]
        in_body = d < 0.5
        crossed = in_body.any(axis=1)
        last_in = np.where(crossed, n_s - 1 - np.argmax(in_body[:, ::-1], axis=1), n_s)
        after = index > last_in[:, None]
        blocked = after & (~in_frame | other)
        first_block = np.where(blocked.any(axis=1), np.argmax(blocked, axis=1), n_s)
        usable = after & (index < first_block[:, None]) & (d <= cap)

        at_edge = usable & (d <= 1.5)
        have_edge = at_edge.any(axis=1)
        surface = np.where(have_edge,
                           (v * at_edge).sum(axis=1) / np.maximum(at_edge.sum(axis=1), 1),
                           np.nan)
        excess = surface - background
        threshold = background + config.GLOW_PROFILE_FRACTION * excess

        smooth = _moving_average(v, GLOW_PROFILE_SMOOTH)
        below = usable & (smooth <= threshold[:, None])
        answered = below.any(axis=1)
        first_below = np.argmax(below, axis=1)
        extent_ray = np.where(answered, d[np.arange(n_ang), first_below], np.nan)
        reached = usable.any(axis=1) & ((d * usable).max(axis=1) >= cap - GLOW_PROFILE_STEP_PX)
        extent_ray = np.where(np.isnan(extent_ray) & reached, cap, extent_ray)
        extent_ray = np.where(have_edge & (excess <= 0.0), 0.0, extent_ray)

        good = crossed & have_edge & ~np.isnan(extent_ray)
        extent = float(np.median(extent_ray[good])) if good.any() else 0.0
        extents[lacuna_id] = min(extent, cap)
    return extents


def glow_zone_mask(lacuna_id_map: np.ndarray, extents: np.ndarray) -> np.ndarray:
    """The union of every lacuna's own glow zone: pixels within that lacuna's
    glow extent of its body. Where two zones overlap the pixel is in both, which
    is what a union means; nothing here decides ownership."""
    zone = np.zeros(lacuna_id_map.shape, dtype=bool)
    for lacuna_id in range(1, extents.size):
        if extents[lacuna_id] <= 0:
            continue
        body = lacuna_id_map == lacuna_id
        if not body.any():
            continue
        zone |= ndi.distance_transform_edt(~body) <= extents[lacuna_id]
    return zone

def grow_in_glow_zone(candidate: np.ndarray, response: np.ndarray, t_hi: float,
                      zone: np.ndarray, lacuna_mask: np.ndarray,
                      flagged: np.ndarray) -> np.ndarray:
    """The pixels a lower cut adds INSIDE the glow zones, and nowhere else.

    One global cut empties a ring around every lacuna: METHODS section 18
    measured the ridge response there at 31 to 71% of what the same tissue shows
    40 px further out, and found the hysteresis low cut dropping 59.9% of
    everything visible in those rings, 27 times every other stage together.

    So inside each lacuna's own glow zone the response is accepted down to
    config.GLOW_ZONE_CUT_FRACTION of the low cut, under the two limits that make
    it a continuation and not a flood:
      - it must CONNECT to mask the global cut already produced, which is the
        only seed, so nothing is created in open field, and
      - it may only lie inside a zone, which is each lacuna's own glow extent
        and never a fixed width.
    Outside the zones the mask is exactly what the global cut gave. The lacuna
    bodies and their buffer stay cut out, and inside a flagged vascular
    structure only already-bright pixels survive, both as in hysteresis_mask."""
    if not zone.any():
        return candidate
    low = t_hi * HYSTERESIS_LOW_FRACTION
    floor = low * config.GLOW_ZONE_CUT_FRACTION
    buffered = morphology.dilation(lacuna_mask, morphology.disk(LACUNA_DILATION_PX))
    extra = zone & (response >= floor) & ~buffered
    if flagged.any():
        extra &= ~(flagged & (response < t_hi))
    return ndi.binary_propagation(candidate, mask=candidate | extra)



# The hole around a lacuna, the zone that follows it, and the gain inside it
# METHODS section 19. The glow zone of section 18 left the holes in place
# because its zone (the glow extent, 3.9 to 33.2 px) is often narrower than the
# hole (9.0 to 59.2 px) and because it could only extend mask that the global
# cut had already made. The zone is therefore measured on the hole itself, and
# the cut inside it is the SAME global cut applied to a response put back on the
# footing of the tissue just beyond the hole.

# The frame around a body is cut into this many angular sectors, 2 degrees each,
# and a sector's empty width is the smallest distance to the body over the
# skeleton pixels in it. The measurement of METHODS section 18, unchanged: a ray
# marched outward instead runs along the corridor between two threads and
# reports a hole where a thread sits 3 px to the side.
HOLE_SECTORS = 180
# How far out a sector looks for skeleton before it is censored.
HOLE_MAX_SEARCH_PX = 150
HOLE_ZONE_MARGIN_PX = config.px(config.HOLE_ZONE_MARGIN_UM)
HOLE_GAIN_BAND_PX = config.px(config.HOLE_GAIN_BAND_UM)
HOLE_GAIN_STEP_PX = max(1.0, config.px(config.HOLE_GAIN_STEP_UM))
# The gain profile is not measured inside this ring around a body, and the first
# gain measured outside it is carried inward instead. Two reasons, both already
# in the pipeline, so this is not a new number: no mask can exist within
# LACUNA_DILATION_PX of a body, because the buffer is cut out of it; and the
# top-hat leaves the body's own edge as a ridge, which the Sato filter answers
# at its own scale, out to about the largest of RIDGE_SIGMAS_PX. That answer is
# the body, not a thread, and measured on 542_z06 it runs at 0.0445 against
# 0.0077 in the band beyond, which pins the gain at 1 exactly where the hole is
# deepest. Skipping the ring is what makes the profile a thread measurement.
HOLE_GAIN_SKIP_PX = LACUNA_DILATION_PX + max(RIDGE_SIGMAS_PX)
HOLE_NEW_MIN_LENGTH_PX = config.px_int(config.HOLE_NEW_MIN_LENGTH_UM)


def _body_window(body: np.ndarray, shape: tuple, reach: float) -> tuple:
    """The bounding box of one body grown by `reach`, so the work around a
    lacuna is done on its own neighbourhood and not on the whole frame."""
    rows, cols = np.nonzero(body)
    reach = int(np.ceil(reach)) + 1
    return (max(0, int(rows.min()) - reach), min(shape[0], int(rows.max()) + reach + 1),
            max(0, int(cols.min()) - reach), min(shape[1], int(cols.max()) + reach + 1))


def empty_width_px(lacuna_id_map: np.ndarray, skeleton: np.ndarray, n_lacunae: int) -> np.ndarray:
    """How wide the hole in the skeleton is around each lacuna, in px, indexed
    by lacuna id (index 0 unused), nan where no sector answered.

    The measurement of METHODS section 18, in the pipeline because the zone is
    now built on it. The frame around a body is cut into HOLE_SECTORS angular
    sectors, and a sector's empty width is the smallest distance from the body
    to a SKELETON PIXEL lying in it; the lacuna's empty width is the median over
    the sectors that answered. A sector with no skeleton within
    HOLE_MAX_SEARCH_PX, or with another lacuna body nearer than its skeleton, is
    censored.

    It is measured on the skeleton's own pixels, never by marching a ray: a ray
    runs along the corridor between two threads and reports a hole where a
    thread sits 3 px to the side, which overstated the width by up to a third
    when it was tried.

    The caller passes the skeleton of the GLOBAL CUT, before any zone pass, so
    that the zone is never defined by its own output."""
    widths = np.full(n_lacunae + 1, np.nan, dtype=np.float64)
    shape = lacuna_id_map.shape
    all_bodies = lacuna_id_map > 0
    for lacuna_id in range(1, n_lacunae + 1):
        body = lacuna_id_map == lacuna_id
        if not body.any():
            continue
        rows, cols = np.nonzero(body)
        r0, c0 = float(rows.mean()), float(cols.mean())
        r_lo, r_hi, c_lo, c_hi = _body_window(body, shape, HOLE_MAX_SEARCH_PX)
        sub_body = body[r_lo:r_hi, c_lo:c_hi]
        sub_gap = ndi.distance_transform_edt(~sub_body)
        sub_skel = skeleton[r_lo:r_hi, c_lo:c_hi]
        sub_other = (all_bodies & ~body)[r_lo:r_hi, c_lo:c_hi]
        rr, cc = np.indices(sub_gap.shape)
        ang = np.arctan2(rr + r_lo - r0, cc + c_lo - c0) % (2.0 * np.pi)
        sector = (np.round(ang / (2.0 * np.pi) * HOLE_SECTORS).astype(np.int64)) % HOLE_SECTORS
        near = (sub_gap > 0) & (sub_gap <= HOLE_MAX_SEARCH_PX)

        blocked = np.full(HOLE_SECTORS, np.inf)
        sel = near & sub_other
        np.minimum.at(blocked, sector[sel], sub_gap[sel])
        found = np.full(HOLE_SECTORS, np.inf)
        sel = near & sub_skel
        np.minimum.at(found, sector[sel], sub_gap[sel])
        answered = np.isfinite(found) & (blocked > found)
        if answered.any():
            widths[lacuna_id] = float(np.median(found[answered]))
    return widths


def hole_zone_extents_px(widths: np.ndarray) -> np.ndarray:
    """How far each lacuna's zone reaches beyond its body: its own empty width
    plus one thread half width, capped at config.GLOW_ZONE_MAX_UM.

    The margin is what makes the zone reach the first thread that bounds the
    hole instead of stopping just short of it. The cap is the one of section 18,
    so a lacuna whose hole fills the frame cannot claim the image. A lacuna
    whose sectors all went unanswered has no skeleton anywhere within
    HOLE_MAX_SEARCH_PX, so its hole is at least that wide and the cap is the
    only bound there is: it takes the cap. That does not happen on the 8 WT
    images, where every lacuna answers."""
    extents = np.where(np.isnan(widths), float(GLOW_ZONE_MAX_PX),
                       np.nan_to_num(widths) + HOLE_ZONE_MARGIN_PX)
    extents = np.minimum(extents, float(GLOW_ZONE_MAX_PX))
    extents[0] = 0.0
    return extents


def hole_zone_owner(lacuna_id_map: np.ndarray, extents: np.ndarray) -> np.ndarray:
    """0 outside every zone, else the id of the lacuna whose zone it is.

    Zones overlap where two bodies are close. A pixel claimed by several goes to
    the NEAREST of the bodies that claim it, which is the partition ownership
    already uses, so every pixel has exactly one gain and no pixel is boosted
    twice. A pixel inside any body, or in no zone, is 0."""
    shape = lacuna_id_map.shape
    owner = np.zeros(shape, dtype=np.int32)
    best = np.full(shape, np.inf, dtype=np.float64)
    for lacuna_id in range(1, extents.size):
        extent = float(extents[lacuna_id])
        if extent <= 0:
            continue
        body = lacuna_id_map == lacuna_id
        if not body.any():
            continue
        r_lo, r_hi, c_lo, c_hi = _body_window(body, shape, extent)
        sub_gap = ndi.distance_transform_edt(~body[r_lo:r_hi, c_lo:c_hi])
        sub_best = best[r_lo:r_hi, c_lo:c_hi]
        sel = (sub_gap > 0) & (sub_gap <= extent) & (sub_gap < sub_best)
        sub_best[sel] = sub_gap[sel]
        owner[r_lo:r_hi, c_lo:c_hi][sel] = lacuna_id
    owner[lacuna_id_map > 0] = 0
    return owner


def hole_zone_gains(response: np.ndarray, lacuna_id_map: np.ndarray, zone_owner: np.ndarray,
                    extents: np.ndarray) -> dict:
    """Each lacuna's own contrast gain, as a RADIAL PROFILE: by distance from
    its body edge, the config.HOLE_GAIN_PERCENTILE of the ridge response in the
    band just beyond its zone over the same percentile at that distance inside
    it, clipped to config.HOLE_GAIN_MIN and config.HOLE_GAIN_MAX.

    Returns {lacuna id: gains by annulus}, each annulus HOLE_GAIN_STEP_PX wide
    from the body edge outward, smoothed over config.HOLE_GAIN_SMOOTH annuli.

    This is METHODS section 18's measurement per lacuna and per distance. The
    loss in a hole is not flat: measured on 543-2 the response p90 runs at 0.87
    of the low cut at the body edge, 2.07 ten px out and 3.7 from 40 px out,
    because the top-hat digs a trough around a bright body. A single gain for
    the whole zone therefore over-corrects where the skeleton already is and
    under-corrects where the empty width is decided, which is what the first
    version did and why it moved no hole.

    The same percentile is taken on both sides so the ratio compares like with
    like, and the band is the same control band section 18 reads the hole
    against. Lacuna bodies are left out of both. An annulus whose response is 0
    at that percentile takes the cap, which changes nothing: a gain times zero
    is still zero and the global cut still has to be passed.

    The innermost HOLE_GAIN_SKIP_PX are not measured at all: there is no mask
    there to lift, and what the response holds there is the body's own edge seen
    by the ridge filter. The first gain measured outside that ring is carried
    inward, so the deepest part of the hole is corrected by the nearest
    measurement of a thread and never by a measurement of the body."""
    profiles = {}
    shape = lacuna_id_map.shape
    all_bodies = lacuna_id_map > 0
    percentile = float(config.HOLE_GAIN_PERCENTILE)
    smooth = max(1, int(config.HOLE_GAIN_SMOOTH))
    for lacuna_id in range(1, extents.size):
        extent = float(extents[lacuna_id])
        if extent <= 0 or not (zone_owner == lacuna_id).any():
            continue
        body = lacuna_id_map == lacuna_id
        r_lo, r_hi, c_lo, c_hi = _body_window(body, shape, extent + HOLE_GAIN_BAND_PX)
        sub_gap = ndi.distance_transform_edt(~body[r_lo:r_hi, c_lo:c_hi])
        sub_resp = response[r_lo:r_hi, c_lo:c_hi]
        outside = ~all_bodies[r_lo:r_hi, c_lo:c_hi]
        band = (sub_gap > extent) & (sub_gap <= extent + HOLE_GAIN_BAND_PX) & outside
        beyond = float(np.percentile(sub_resp[band], percentile)) if band.any() else 0.0
        n_bins = max(1, int(np.ceil(extent / HOLE_GAIN_STEP_PX)))
        levels = np.full(n_bins, np.nan)
        for b in range(n_bins):
            lo, hi = b * HOLE_GAIN_STEP_PX, (b + 1) * HOLE_GAIN_STEP_PX
            if hi <= HOLE_GAIN_SKIP_PX:
                continue  # the body's own edge, not a thread: left unmeasured
            ring = (sub_gap > lo) & (sub_gap <= hi) & outside
            if ring.any():
                levels[b] = float(np.percentile(sub_resp[ring], percentile))
        levels = _fill_and_smooth(levels, smooth)
        with np.errstate(divide="ignore", invalid="ignore"):
            gains = np.where(levels > 0, beyond / levels, float(config.HOLE_GAIN_MAX))
        gains = np.clip(np.nan_to_num(gains, nan=float(config.HOLE_GAIN_MIN)),
                        float(config.HOLE_GAIN_MIN), float(config.HOLE_GAIN_MAX))
        profiles[lacuna_id] = gains
    return profiles


def _fill_and_smooth(values: np.ndarray, window: int) -> np.ndarray:
    """An annulus with no pixel of its own takes its neighbours' level, and the
    profile is then averaged over `window` annuli, so one noisy ring cannot set
    a gain by itself."""
    out = np.array(values, dtype=np.float64)
    if np.isnan(out).all():
        return out
    index = np.arange(out.size)
    good = ~np.isnan(out)
    out = np.interp(index, index[good], out[good])
    if window > 1 and out.size > 1:
        kernel = np.ones(window) / window
        out = np.convolve(np.pad(out, window // 2, mode="edge"), kernel, mode="valid")[:out.size]
    return out


def boost_in_zones(response: np.ndarray, lacuna_id_map: np.ndarray, zone_owner: np.ndarray,
                   extents: np.ndarray, profiles: dict) -> np.ndarray:
    """The ridge response with each zone pixel multiplied by the gain of the
    annulus it lies in. Outside the zones the response is untouched."""
    boosted = response.copy()
    shape = lacuna_id_map.shape
    for lacuna_id, gains in profiles.items():
        body = lacuna_id_map == lacuna_id
        extent = float(extents[lacuna_id])
        r_lo, r_hi, c_lo, c_hi = _body_window(body, shape, extent)
        sub_gap = ndi.distance_transform_edt(~body[r_lo:r_hi, c_lo:c_hi])
        sel = zone_owner[r_lo:r_hi, c_lo:c_hi] == lacuna_id
        if not sel.any():
            continue
        bins = np.clip((sub_gap[sel] / HOLE_GAIN_STEP_PX).astype(np.int64), 0, gains.size - 1)
        window = boosted[r_lo:r_hi, c_lo:c_hi]
        window[sel] = response[r_lo:r_hi, c_lo:c_hi][sel] * gains[bins]
    return boosted


def gain_summary(profiles: dict, extents: np.ndarray) -> dict:
    """What the profiles did, small enough for the detection record: the gain at
    the body edge and at the outer end of the zone, per lacuna."""
    at_body, at_edge, highest = [], [], []
    for lacuna_id in sorted(profiles):
        gains = profiles[lacuna_id]
        at_body.append(round(float(gains[0]), 4))
        at_edge.append(round(float(gains[-1]), 4))
        highest.append(round(float(gains.max()), 4))
    if not at_body:
        return {"lacunae": 0}
    return {
        "lacunae": len(at_body),
        "at_the_body_edge": {"min": min(at_body), "median": round(float(np.median(at_body)), 4),
                             "max": max(at_body)},
        "at_the_outer_end": {"min": min(at_edge), "median": round(float(np.median(at_edge)), 4),
                             "max": max(at_edge)},
        "at_the_cap": int(sum(1 for g in highest if g >= config.HOLE_GAIN_MAX)),
    }


def guard_new_components(merged: np.ndarray, before: np.ndarray) -> tuple:
    """(mask, what the guard removed). A component of `merged` that holds no
    pixel of `before` is mask that did not exist at all, which inside a zone is
    what the glow's own grain looks like once the gain lifts it over the cut. It
    is kept only if it looks like a thread: at least HOLE_NEW_MIN_LENGTH_PX long
    once skeletonized and at least config.HOLE_NEW_MIN_ASPECT times longer than
    it is wide.

    The two tests the unattached dim tier already applies (section 8), for the
    same reason: nothing vouches for this mask, so it is accepted on its own
    shape alone. A component that continues mask that was already there is not
    new and is not tested."""
    labels = morphology.label(merged, connectivity=2)
    if labels.max() == 0:
        return merged, {"new_components": 0, "kept": 0, "dropped_short": 0,
                        "dropped_round": 0, "dropped_px": 0, "kept_px": 0}
    old = set(np.unique(labels[before & (labels > 0)]))
    dropped = np.zeros_like(merged)
    report = {"new_components": 0, "kept": 0, "dropped_short": 0, "dropped_round": 0,
              "dropped_px": 0, "kept_px": 0}
    for region in measure.regionprops(labels):
        if region.label in old:
            continue
        report["new_components"] += 1
        piece = labels[region.slice] == region.label
        minor, major = region.axis_minor_length, region.axis_major_length
        aspect = (major / minor) if minor > 0 else float("inf")
        length = int(morphology.skeletonize(piece).sum())
        if length < HOLE_NEW_MIN_LENGTH_PX:
            report["dropped_short"] += 1
        elif aspect < config.HOLE_NEW_MIN_ASPECT:
            report["dropped_round"] += 1
        else:
            report["kept"] += 1
            report["kept_px"] += int(region.area)
            continue
        dropped[region.slice] |= piece
        report["dropped_px"] += int(region.area)
    return merged & ~dropped, report


def grow_in_hole_zone(candidate: np.ndarray, boosted: np.ndarray, t_hi: float,
                      zone_owner: np.ndarray, lacuna_mask: np.ndarray,
                      flagged: np.ndarray) -> tuple:
    """(mask, what it did). Inside each lacuna's own zone, and nowhere else, the
    ridge response is multiplied by that lacuna's contrast gain and the SAME
    global cuts are applied to it.

    The cut is not lowered: the response is put back on the footing of the
    tissue just beyond the hole, and then the pipeline's own hysteresis, its own
    body buffer, its own vascular rule and its own despeckle step decide, as
    everywhere else. There is NO requirement to connect to mask the global cut
    already made, which is what separates this from the glow zone rule of
    section 18: a thread whose whole run inside the hole is under the cut has no
    seed to grow from, and that is the thread the holes are made of. The noise
    guard is what stands in the place of that requirement.

    Outside the zones the mask is the one that came in, pixel for pixel."""
    report = {"zone_px": int((zone_owner > 0).sum()), "added_px": 0, "guard": None}
    inside = zone_owner > 0
    if not inside.any():
        return candidate, report
    signal, _cut = hysteresis_mask(boosted, flagged, t_hi)
    buffered = morphology.dilation(lacuna_mask, morphology.disk(LACUNA_DILATION_PX))
    grown = morphology.remove_small_objects(signal & ~buffered, min_size=MIN_THREAD_OBJECT_PX2)
    merged = (candidate & ~inside) | (grown & inside)
    report["added_before_the_guard_px"] = int((merged & ~candidate).sum())
    merged, guard = guard_new_components(merged, candidate)
    report["guard"] = guard
    report["added_px"] = int((merged & ~candidate).sum())
    return merged, report


def build_lacuna_maps(labels: np.ndarray, kept: list[tuple]) -> tuple[np.ndarray, np.ndarray]:
    """(lacuna_mask, lacuna_id_map). lacuna_id_map is 0 outside any kept
    lacuna, else its 1..N id, the numbering src/lacunae.py uses."""
    lacuna_id_map = np.zeros(labels.shape, dtype=np.int32)
    for lacuna_id, (region, _on_border) in enumerate(kept, start=1):
        lacuna_id_map[labels == region.label] = lacuna_id
    return lacuna_id_map > 0, lacuna_id_map


def nearest_lacuna_map(lacuna_id_map: np.ndarray) -> tuple:
    """For every pixel, (distance to the nearest lacuna pixel, that lacuna's id,
    the row and column of that pixel): a Euclidean partition seeded from the
    lacunae. The third value is the point on a lacuna surface that an attachment
    path starts from."""
    dist, indices = ndi.distance_transform_edt(lacuna_id_map == 0, return_indices=True)
    nearest_id = lacuna_id_map[indices[0], indices[1]]
    return dist, nearest_id, indices


def path_min_signal(signal: np.ndarray, r0: float, c0: float, r1: float, c1: float) -> float:
    """The dimmest value of `signal` along the straight line from (r0, c0) to
    (r1, c1), sampled about once per pixel with bilinear interpolation.

    The minimum, not the mean: one background-level pixel breaks a thread
    however bright its two ends are."""
    steps = max(2, int(round(float(np.hypot(r1 - r0, c1 - c0)))) + 1)
    rows = np.linspace(r0, r1, steps)
    cols = np.linspace(c0, c1, steps)
    return float(ndi.map_coordinates(signal, [rows, cols], order=1, mode="nearest").min())


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
    """Remove terminal branches shorter than PRUNE_SPUR_LEN_PX from the GRAPH,
    repeating until nothing more qualifies. True if anything changed.

    The spur's pixels are NOT removed from the skeleton: only the graph drops
    them. They are therefore folded into the node they hang off, exactly as a
    collapse or a chain merge folds what it absorbs, so that the cell owning
    that node owns them too. Without this they stayed in the skeleton with no
    owner at all, and a short stub beside a body, which is the commonest thing
    a new thread in a hole leaves behind, read as skeleton that no lacuna owns.
    It changes no graph measure: the spur is still out of the graph, so no edge
    length, degree or root count moves. What it changes is the owner map, and
    only from nobody to the cell the stub hangs off."""
    any_change = False
    changed = True
    while changed:
        changed = False
        for node in list(G.nodes()):
            if G.degree(node) == 1:
                neighbor = next(iter(G.neighbors(node)))
                if G[node][neighbor]["weight"] < PRUNE_SPUR_LEN_PX:
                    absorbed = _node_absorbed(G, neighbor)
                    absorbed.extend(G[node][neighbor].get("branches", ()))
                    absorbed.extend(_node_absorbed(G, node))
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


def touching_bodies(G: nx.Graph, lacuna_id_map: np.ndarray, cell_ids: list[int]) -> dict:
    """{node: [every lacuna whose body it lies within CONTACT_REACH_PX of]}.

    The contact rule of METHODS section 8 offers each node to its NEAREST lacuna
    only. A thread that touches two bodies, or that touches one body while
    another body's surface is a pixel nearer, was therefore handed to the
    neighbour, which is the ownership failure the census found beside the holes.
    This asks the question the rule is named for: which bodies does this node
    touch."""
    nodes = [n for n in G.nodes() if not _is_cell_node(n)]
    touching: dict = {}
    if not nodes:
        return touching
    rows = np.array([n[0] for n in nodes])
    cols = np.array([n[1] for n in nodes])
    shape = lacuna_id_map.shape
    for lacuna_id in cell_ids:
        body = lacuna_id_map == lacuna_id
        if not body.any():
            continue
        r_lo, r_hi, c_lo, c_hi = _body_window(body, shape, CONTACT_REACH_PX)
        inside = ((rows >= r_lo) & (rows < r_hi) & (cols >= c_lo) & (cols < c_hi))
        if not inside.any():
            continue
        gap = ndi.distance_transform_edt(~body[r_lo:r_hi, c_lo:c_hi])
        gaps = gap[rows[inside] - r_lo, cols[inside] - c_lo]
        near = gaps <= CONTACT_REACH_PX
        for node_index, node_gap in zip(np.flatnonzero(inside)[near], gaps[near]):
            touching.setdefault(nodes[node_index], []).append((float(node_gap), lacuna_id))
    # A node that touches two bodies goes to the NEARER surface. The first
    # version gave it to both at weight 0 and let the tie fall to the lower cell
    # id, which is arbitrary where a thread runs between two cells; the distance
    # to the surface is not.
    return {node: [lacuna_id for _gap, lacuna_id in sorted(found)[:1]]
            for node, found in touching.items()}


def attach_lacunae(G: nx.Graph, dist_to_lacuna: np.ndarray, nearest_id: np.ndarray,
                   nearest_index: np.ndarray, cell_ids: list[int], response: np.ndarray,
                   min_signal: float, lacuna_id_map: np.ndarray | None = None) -> nx.Graph:
    """Add a virtual ("cell", id) node per lacuna, linked to the skeleton nodes
    near its body. Every node is offered to its NEAREST lacuna only, and that
    lacuna takes it under one of two rules:

    CONTACT, within CONTACT_REACH_PX of the body: no test, at weight 0. Inside
    that reach there is no empty space between body and node to cross, so there
    is nothing for a signal test to decide, and the weight is 0 because the
    thread starts at the surface. The zero weight is the whole point: it makes
    contact happen before the shortest path assignment that follows, so a lacuna
    that is touched owns what touches it and no neighbour can reach that node
    first and swallow the thread. Without it the flattening decides: the top-hat
    digs a trough around every body, and a path leaving a surface crosses that
    trough at its dimmest point, so the signal test below refused threads that
    visibly touch the cell (92 of 108 lacunae had skeleton within 8 px of the
    body that they did not own: python src/diagnostics.py contact).

    With config.CONTACT_EVERY_TOUCHING_BODY, contact is decided by which bodies
    the node TOUCHES and not by which body is nearest overall (touching_bodies
    above), which is what the rule has always said in words: a lacuna owns the
    thread that touches it. A node 5 px from one body and 7 px from another used
    to be offered only to the second, because it was nearest, and then refused
    by the signal test; it now attaches to the body it touches. A node that
    touches two bodies goes to the nearer surface. Beyond the contact reach
    nothing changes.

    SIGNAL, from there out to LACUNA_ATTACH_REACH_PX, at weight = the gap, so
    the path starts at the cell boundary. Distance alone would hand a lacuna any
    network that happened to pass nearby, across empty space; the survey found
    about half of all attachments doing exactly that. So the straight path from
    the nearest point of the lacuna surface to the node is sampled on the ridge
    response, and its dimmest point must reach `min_signal`, or the node does not
    attach to that lacuna."""
    touching = (touching_bodies(G, lacuna_id_map, cell_ids)
                if (config.CONTACT_EVERY_TOUCHING_BODY and lacuna_id_map is not None) else {})
    for node in list(G.nodes()):
        if _is_cell_node(node):
            continue
        contacts = touching.get(node)
        if contacts:
            for lacuna_id in contacts:
                G.add_edge(("cell", lacuna_id), node, weight=0.0)
            continue
        r, c = node
        gap = float(dist_to_lacuna[r, c])
        if gap > LACUNA_ATTACH_REACH_PX:
            continue
        lacuna_id = int(nearest_id[r, c])
        if lacuna_id not in cell_ids:
            continue
        if not touching and gap <= CONTACT_REACH_PX:
            G.add_edge(("cell", lacuna_id), node, weight=0.0)
            continue
        sr, sc = int(nearest_index[0, r, c]), int(nearest_index[1, r, c])
        if path_min_signal(response, sr, sc, r, c) < min_signal:
            continue
        G.add_edge(("cell", lacuna_id), node, weight=gap)
    return G


def attach_judged_segments(G: nx.Graph, extra_attach: dict | None) -> nx.Graph:
    """The ownership the AI judge named, expressed the way the pipeline already
    expresses ownership (the experiment of branch exp-ai-layer, off by default;
    docs/EXPERIMENT_AI.md).

    For each segment the judge called real and gave an owner, one edge of weight
    0 from that cell to the graph node nearest the point the caller gives, which
    is the END of that segment nearest that cell (ai_judge.nearest_end): the
    same zero weight the contact rule uses, for the same reason. The path then
    enters the thread where the thread starts, and the multi source shortest
    path below splits the network where the two cells' paths meet.

    Nothing else is written. The ownership below decides everything, so the
    judge grants ownership and never vetoes it, the old owner keeps whatever the
    shortest path still gives it, and no ownership rule moves into the model.

    A node both the judge and the contact rule reach at weight 0 goes to the
    lower cell id, which is how every other tie in this file is broken."""
    if not extra_attach:
        return G
    nodes = [n for n in G.nodes() if not _is_cell_node(n)]
    if not nodes:
        return G
    coords = np.array(nodes, dtype=np.float64)
    for lacuna_id, segments in sorted(extra_attach.items()):
        for pixels in segments:
            pixels = np.asarray(pixels, dtype=np.float64)
            gaps = ((coords[:, None, :] - pixels[None, :, :]) ** 2).sum(axis=2).min(axis=1)
            G.add_edge(("cell", int(lacuna_id)), nodes[int(np.argmin(gaps))], weight=0.0)
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


def grow_dim_threads(candidate: np.ndarray, response: np.ndarray, t_hi: float,
                     owned_skeleton: np.ndarray, lacuna_mask: np.ndarray,
                     flagged: np.ndarray) -> np.ndarray:
    """The pixels a second, dimmer pass adds to the network mask.

    A canaliculus often fades before it ends, and hysteresis can only grow into
    what already reaches the low cut somewhere, so a thread that fades below it
    stops dead. This pass accepts response down to
    config.DIM_THREAD_CUT_FRACTION of the low cut, but only where it CONTINUES
    skeleton a lacuna already owns, and only config.DIM_THREAD_REACH_UM further
    along the dim structure than that skeleton reaches.

    The reach is what keeps it a continuation rather than a flood. At half the
    low cut the faint band is a connected mesh covering much of the frame, so
    connectivity alone would swallow it whole.

    The two exclusions of the first pass still apply: nothing grows into a
    vascular structure unless it was already above the high cut, and nothing
    grows into the lacuna buffer."""
    from skimage.graph import MCP_Geometric

    if not owned_skeleton.any():
        return np.zeros_like(candidate)
    low = t_hi * HYSTERESIS_LOW_FRACTION
    permissive = response >= low * config.DIM_THREAD_CUT_FRACTION
    if flagged.any():
        permissive = permissive & ~(flagged & ~(response >= t_hi))
    permissive = permissive & ~morphology.dilation(lacuna_mask, morphology.disk(LACUNA_DILATION_PX))
    permissive = permissive | owned_skeleton
    costs = np.where(permissive, 1.0, np.inf)
    reached, _traceback = MCP_Geometric(costs, fully_connected=True).find_costs(
        np.argwhere(owned_skeleton))
    grown = permissive & np.isfinite(reached) & (reached <= DIM_THREAD_REACH_PX)
    grown = morphology.remove_small_objects(grown | candidate, min_size=MIN_THREAD_OBJECT_PX2)
    return grown & ~candidate


def find_unattached_threads(response: np.ndarray, t_hi: float, owned_skeleton: np.ndarray,
                            skeleton: np.ndarray, lacuna_mask: np.ndarray,
                            flagged: np.ndarray) -> np.ndarray:
    """Dim thread-shaped structure that touches no lacuna, as a skeleton of its
    own.

    The second pass only continues threads a lacuna already owns, so a
    canaliculus whose whole run is dim, or whose lacuna lies outside the section,
    is still missed. This finds those, from the same dim tier, and keeps a
    component only if it looks like a thread and not like a patch of background:
    at least UNATTACHED_MIN_LENGTH_PX long once skeletonized and at least
    config.UNATTACHED_MIN_ASPECT times longer than wide.

    The test is strict because nothing vouches for this tier: there is no lacuna
    at the end of it, so it is accepted on its own shape alone. What comes back
    is NEVER owned and never enters a per-lacuna measure."""
    low = t_hi * HYSTERESIS_LOW_FRACTION
    permissive = response >= low * config.DIM_THREAD_CUT_FRACTION
    if flagged.any():
        permissive = permissive & ~(flagged & ~(response >= t_hi))
    permissive = permissive & ~morphology.dilation(lacuna_mask, morphology.disk(LACUNA_DILATION_PX))
    # Anything the main skeleton or its ownership already covers is not this.
    seeded = morphology.dilation(skeleton | owned_skeleton, morphology.disk(1))
    labels = morphology.label(permissive, connectivity=2)
    touching = set(np.unique(labels[seeded & (labels > 0)]))
    touching.discard(0)

    out = np.zeros_like(permissive)
    for region in measure.regionprops(labels):
        if region.label in touching:
            continue
        minor, major = region.axis_minor_length, region.axis_major_length
        aspect = (major / minor) if minor > 0 else float("inf")
        if aspect < config.UNATTACHED_MIN_ASPECT:
            continue
        piece = labels[region.slice] == region.label
        thin = morphology.skeletonize(piece)
        if int(thin.sum()) < UNATTACHED_MIN_LENGTH_PX:
            continue
        out[region.slice] |= thin
    return out


def network_distance_map(skeleton: np.ndarray, lacuna_mask: np.ndarray) -> np.ndarray:
    """For every skeleton pixel, its distance in px from the nearest lacuna
    SURFACE measured ALONG THE NETWORK. inf where no lacuna reaches it.

    This is a geodesic distance on the skeleton itself: a path may travel only
    along skeleton pixels and across the lacuna buffer that separates a thread
    from the body it belongs to, and a diagonal step costs sqrt(2)
    (skimage.graph.MCP_Geometric). Every lacuna body is a source at distance 0,
    so the distance is measured from the surface outward and the shortest path
    decides which lacuna a thread is measured from, which is the rule ownership
    already uses.

    It is deliberately independent of the network graph and its cleanup, so the
    length limit is enforced on the same quantity the report measures."""
    from skimage.graph import MCP_Geometric

    if not skeleton.any() or not lacuna_mask.any():
        return np.full(skeleton.shape, np.inf, dtype=np.float64)
    buffered = morphology.dilation(lacuna_mask, morphology.disk(LACUNA_DILATION_PX))
    costs = np.where(skeleton | buffered, 1.0, np.inf)
    mcp = MCP_Geometric(costs, fully_connected=True)
    dist, _traceback = mcp.find_costs(np.argwhere(lacuna_mask))
    return np.where(skeleton, dist, np.inf)


def thread_end_mask(skeleton: np.ndarray) -> np.ndarray:
    """Skeleton pixels with exactly one skeleton neighbour: the tip of a thread."""
    neighbours = ndi.convolve(skeleton.astype(np.uint8), np.ones((3, 3), dtype=np.uint8),
                                  mode="constant", cval=0) - skeleton
    return skeleton & (neighbours == 1)


def prune_beyond_length_limit(kept: list[tuple], skeleton: np.ndarray, lacuna_mask: np.ndarray,
                              dist_to_lacuna: np.ndarray, nearest_id: np.ndarray,
                              nearest_index: np.ndarray, response: np.ndarray, min_signal: float,
                              limit_px: float, lacuna_id_map: np.ndarray | None = None,
                              extra_attach: dict | None = None) -> tuple:
    """(skeleton, ownership, how it went). Every skeleton pixel further than
    `limit_px` along the network from a lacuna surface is removed, and ownership
    is built on what is left.

    Removing a pixel can cut a path and leave what lay behind it reachable only
    by a longer way round, which can push another pixel past the limit, so this
    repeats to a fixed point.

    A pixel that no lacuna reaches at all is NOT pruned: there is no lacuna to
    measure a length from, so the limit says nothing about it and it stays in the
    skeleton, unowned."""
    removed_total = 0
    rounds = 0
    for _ in range(PRUNE_LENGTH_MAX_ITER):
        dist_map = network_distance_map(skeleton, lacuna_mask)
        beyond = skeleton & np.isfinite(dist_map) & (dist_map > limit_px)
        n = int(beyond.sum())
        if n == 0:
            break
        skeleton = skeleton & ~beyond
        removed_total += n
        rounds += 1
    else:
        raise AssertionError(f"the length prune did not settle in {PRUNE_LENGTH_MAX_ITER} rounds")
    own = build_ownership(kept, skeleton, dist_to_lacuna, nearest_id, nearest_index, response,
                          min_signal, lacuna_id_map, extra_attach)
    return skeleton, own, {"removed_px": removed_total, "rounds": rounds,
                           "limit_px": float(limit_px),
                           "limit_um": config.MAX_CANALICULUS_LENGTH_UM}


# Measurements

def build_ownership(kept: list[tuple], skeleton: np.ndarray, dist_to_lacuna: np.ndarray,
                    nearest_id: np.ndarray, nearest_index: np.ndarray, response: np.ndarray,
                    min_signal: float, lacuna_id_map: np.ndarray | None = None,
                    extra_attach: dict | None = None) -> dict:
    """The graph, its cleanup, the lacuna attachment and the ownership, with the
    pixel map the verification picture draws. Detection: no measure is taken
    here. src/quantification.py measures from what this returns."""
    cell_ids = list(range(1, len(kept) + 1))
    G, skel_obj = build_network_graph(skeleton)
    clean_network_graph(G, dist_to_lacuna)
    attach_lacunae(G, dist_to_lacuna, nearest_id, nearest_index, cell_ids, response, min_signal,
                   lacuna_id_map)
    # Nothing unless the AI judge experiment is switched on, and then only the
    # owner it named, at weight 0 (attach_judged_segments).
    attach_judged_segments(G, extra_attach)
    owner, node_dist = assign_by_connectivity(G, cell_ids)
    edge_owner = assign_edges(G, owner, node_dist)
    return {
        "graph": G,
        "owner": owner,
        "node_dist": node_dist,
        "edge_owner": edge_owner,
        "owner_map": build_owner_pixel_map(skeleton.shape, skel_obj, G, edge_owner, owner),
    }


def analyse_image(image_path: Path, t_hi: float | None = None, t_lo: float | None = None) -> dict:
    """Detection of feature 2 for one image, without writing. t_hi and t_lo
    replace the two computed cuts; only the sensitivity diagnostics pass them,
    the pipeline never does. Measures: src/quantification.py."""
    lac = lacunae.analyse_image(image_path, t_hi)
    _display, channel = lacunae.load_channel(image_path)
    return analyse_network(image_path, lac, channel, t_lo)


def analyse_network(image_path: Path, lac: dict, channel: np.ndarray, t_lo: float | None = None) -> dict:
    """Feature 2 detection from a finished lacuna result onward (the part of
    analyse_image after the lacuna stage), so a diagnostic can rerun the
    network stage without the lacuna stage (network-sweep)."""
    kept = lac["kept"]
    # The AI judge experiment (branch exp-ai-layer, docs/EXPERIMENT_AI.md), off
    # by default. The judge is shown the FINISHED tracing and its ownership, so
    # that run has to exist before the verdicts can be placed on it: with the
    # switch on, the whole network stage runs once with it off, which is what
    # main produces and what the judge was shown, and the verdicts are then
    # applied to the mask and everything after it is redone. With the switch
    # off this costs nothing at all, not even an import.
    base = None
    if config.AI_JUDGE_ENABLED:
        saved = config.AI_JUDGE_ENABLED
        config.AI_JUDGE_ENABLED = False
        try:
            base = analyse_network(image_path, lac, channel, t_lo)
        finally:
            config.AI_JUDGE_ENABLED = saved

    lacuna_mask, lacuna_id_map = build_lacuna_maps(lac["labels"], kept)
    flagged = flagged_structures(channel)
    preprocessed = preprocess_channel(channel)
    candidate, t_lo, response = network_candidate_mask(preprocessed, lacuna_mask, flagged, t_lo)
    # The glow zone: inside each lacuna's own glow, and only there, a lower cut,
    # seeded from the mask the global cut already produced (section 18). The
    # extent is measured on the RAW channel, never on the flattened one, which
    # is what removes the glow.
    glow_extents = glow_extent_px(channel, lacuna_id_map, len(kept))
    candidate_before_glow_zone = candidate
    if config.HOLE_ZONE_RULE:
        # METHODS section 19. The zone is the HOLE itself, measured on the
        # skeleton the global cut produced, before any zone pass, so it is never
        # defined by its own output; and inside it the response is put back on
        # the footing of the tissue just beyond the hole and the SAME global
        # cuts are applied. The glow extent above is still measured, because it
        # is what section 18 documents and what the checks read the zone
        # against, but it no longer decides where the cut applies.
        skeleton_global_cut = morphology.skeletonize(candidate)
        hole_widths = empty_width_px(lacuna_id_map, skeleton_global_cut, len(kept))
        zone_extents = hole_zone_extents_px(hole_widths)
        zone_owner = hole_zone_owner(lacuna_id_map, zone_extents)
        gains = hole_zone_gains(response, lacuna_id_map, zone_owner, zone_extents)
        boosted = boost_in_zones(response, lacuna_id_map, zone_owner, zone_extents, gains)
        glow_zone = zone_owner > 0
        candidate, hole_report = grow_in_hole_zone(candidate, boosted, t_lo, zone_owner,
                                                   lacuna_mask, flagged)
        hole_report["gains"] = gain_summary(gains, zone_extents)
    else:
        # The glow zone version of section 18, kept so that a before run can be
        # made with it (python src/diagnostics.py hole-check).
        skeleton_global_cut = morphology.skeletonize(candidate)
        hole_widths = np.full(len(kept) + 1, np.nan)
        zone_extents = glow_extents
        zone_owner = np.zeros(lacuna_id_map.shape, dtype=np.int32)
        gains = {}
        glow_zone = glow_zone_mask(lacuna_id_map, glow_extents)
        candidate = grow_in_glow_zone(candidate, response, t_lo, glow_zone, lacuna_mask, flagged)
        hole_report = None
    skeleton = morphology.skeletonize(candidate)
    # What the ridge threshold alone traced. Nothing about ownership enters it,
    # so it is the skeleton an ownership rule must leave pixel for pixel alone;
    # the dim pass below is seeded from OWNED skeleton and so does follow
    # ownership, by design (section 8 of docs/METHODS.md).
    skeleton_first_pass = skeleton
    candidate_first_pass = candidate

    # The judge's verdicts for THIS image, read from its decision file and
    # placed on the mask: a segment judged real that the pipeline does not have
    # adds the mask its centre line is the centre line of, a segment judged
    # artifact takes that mask away whether the pipeline traced it or not, and
    # anything unjudged is left exactly as it is. Everything after this point,
    # the dim pass, the 50 um cap, the ownership and the quantification, runs
    # unchanged on the edited mask, and the owner the judge named enters it as
    # a zero weight attachment and in no other way.
    ai = None
    if base is not None:
        import ai_judge  # noqa: PLC0415 (deliberate: see above)
        ai = ai_judge.apply_to_base(image_path, candidate, base, lac, channel)
        candidate = ai["candidate"]
        skeleton = morphology.skeletonize(candidate)

    dist_to_lacuna, nearest_id, nearest_index = nearest_lacuna_map(lacuna_id_map)
    # Attachment is by signal: the dimmest point of the straight path from a
    # lacuna surface to a skeleton node must reach this on the ridge response, or
    # the node does not attach. The cut is the response's own, so it comes from
    # this image and nothing else.
    attach_min_signal = (t_lo * HYSTERESIS_LOW_FRACTION
                         * config.LACUNA_ATTACH_MIN_SIGNAL_FRACTION)
    # The biological length limit: no canaliculus runs further than
    # config.MAX_CANALICULUS_LENGTH_UM from the lacuna that owns it, measured
    # along the network. What lies beyond is pruned and ownership is rebuilt.
    skeleton_before = skeleton
    skeleton, own, prune = prune_beyond_length_limit(
        kept, skeleton, lacuna_mask, dist_to_lacuna, nearest_id, nearest_index, response,
        attach_min_signal, MAX_CANALICULUS_LENGTH_PX, lacuna_id_map,
        ai["attach"] if ai else None)

    # The second, dimmer pass: continue the threads a lacuna already owns into
    # signal the first cut could not reach. Everything after it is redone on the
    # grown mask, so the graph, the ownership and the 50 um limit all see one
    # skeleton and not two.
    dim = grow_dim_threads(candidate, response, t_lo, skeleton & (own["owner_map"] > 0),
                           lacuna_mask, flagged)
    if ai is not None:
        # A territory the judge called an artifact stays out: the dim pass is
        # seeded from owned skeleton and would otherwise put part of it back.
        dim = dim & ~ai["remove"]
    if dim.any():
        candidate = candidate | dim
        skeleton = morphology.skeletonize(candidate)
        skeleton_before = skeleton
        skeleton, own, prune = prune_beyond_length_limit(
            kept, skeleton, lacuna_mask, dist_to_lacuna, nearest_id, nearest_index, response,
            attach_min_signal, MAX_CANALICULUS_LENGTH_PX, lacuna_id_map,
            ai["attach"] if ai else None)
    # Dim thread-shaped structure that touches no lacuna: a class of its own,
    # never owned, counted only in the field measures.
    unattached = find_unattached_threads(response, t_lo, skeleton & (own["owner_map"] > 0),
                                         skeleton, lacuna_mask, flagged)
    if ai is not None:
        # What the verdicts actually moved: the pixels of tracing that both runs
        # own and that changed hands, measured against the run with the switch
        # off that the judge was shown. It is the one number that says whether a
        # verdict split a network, and it is NOT the judge writing anywhere: it
        # is what the shortest path did once the attachment was there.
        before, after = base["owner_map"], own["owner_map"]
        both = (before > 0) & (after > 0)
        ai["counts"]["ownership_moved_px"] = int((both & (before != after)).sum())
        ai["counts"]["newly_owned_px"] = int(((before == 0) & (after > 0)).sum())
        ai["counts"]["no_longer_owned_px"] = int(((before > 0) & (after == 0)).sum())
    return {
        "image_path": image_path,
        "lacunae": lac,
        "display": lac["display"],
        "lacuna_id_map": lacuna_id_map,
        "lacuna_mask": lacuna_mask,
        "candidate": candidate,
        "dim_pass_px": int(dim.sum()),
        "unattached": unattached,
        "unattached_px": int(unattached.sum()),
        "skeleton": skeleton,
        "skeleton_first_pass": skeleton_first_pass,
        "candidate_first_pass": candidate_first_pass,
        "candidate_before_glow_zone": candidate_before_glow_zone,
        "glow_zone": glow_zone,
        "glow_extents_px": glow_extents,
        "skeleton_global_cut": skeleton_global_cut,
        "hole_width_px": hole_widths,
        "zone_extents_px": zone_extents,
        "zone_owner": zone_owner,
        "zone_gains": gains,
        "hole_zone": hole_report,
        "glow_zone_added_px": int((candidate_before_glow_zone ^ candidate_first_pass).sum()),
        "ai_judge": None if ai is None else {
            k: ai[k] for k in ("counts", "geometry_sha256", "decisions_written_at",
                               "model", "zone_px")},
        # 0 outside every empty zone, else the lacuna whose zone it is. None
        # with the switch off, so nothing is computed and nothing is stored.
        "ai_zone_owner": None if ai is None else ai["zone_owner"],
        "skeleton_before_length_prune": skeleton_before,
        "length_prune": prune,
        "flagged": flagged,
        "ridge_response": response,
        "t_lo": t_lo,
        "graph": own["graph"],
        "edge_owner": own["edge_owner"],
        "owner": own["owner"],
        "node_dist": own["node_dist"],
        "owner_map": own["owner_map"],
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


# Unattached dim threads are drawn in this grey: present, visibly not owned by
# any cell, and never mistaken for a lacuna colour.
UNATTACHED_COLOUR = (150, 150, 150)


def save_verification(result: dict, out_path: Path) -> None:
    """Each lacuna outlined, and the skeleton it owns drawn, in its colour over
    the full-brightness original, so the tracing can be checked against the real
    threads underneath. Unowned skeleton is not drawn.

    Unattached dim threads (canaliculi.find_unattached_threads) are drawn in
    grey, under the owned skeleton, so what the field density counts but no cell
    owns can be seen and told apart at a glance."""
    n = len(result["lacunae"]["kept"])
    colors = lacuna_colors(n)
    vis = result["display"].copy()
    unattached = result.get("unattached")
    if unattached is not None and unattached.any():
        vis[morphology.dilation(unattached, morphology.disk(VIS_SKELETON_DILATION_PX))] =             UNATTACHED_COLOUR
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
    extra = {}
    if result.get("ai_judge") is not None:
        # The AI judge experiment is switched on. Recorded here so that no
        # result file can be mistaken for one the pipeline made alone.
        extra = {"ai_judge": dict(result["ai_judge"],
                                  experiment="branch exp-ai-layer, docs/EXPERIMENT_AI.md")}
    return {
        "pixel_size_um": config.PIXEL_SIZE_UM,
        "smooth_sigma_px": SMOOTH_SIGMA_PX,
        "tophat_radius_px": TOPHAT_RADIUS_PX,
        "background_mode_subtract": True,
        "thresholded_quantity": "multiscale ridge response (skimage.filters.sato, bright ridges)",
        "ridge_sigmas_px": list(RIDGE_SIGMAS_PX),
        "threshold": "hysteresis on the ridge response, high cut = its lower 3-class multi-Otsu cut",
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
        "gap_bridging": False,
        "unattached_min_length_um": config.UNATTACHED_MIN_LENGTH_UM,
        "unattached_min_aspect": config.UNATTACHED_MIN_ASPECT,
        "unattached_px": result["unattached_px"],
        "dim_thread_cut_fraction": config.DIM_THREAD_CUT_FRACTION,
        "dim_thread_reach_um": config.DIM_THREAD_REACH_UM,
        "dim_thread_reach_px": DIM_THREAD_REACH_PX,
        "dim_pass_added_px": result["dim_pass_px"],
        "lacuna_attach_reach_um": config.LACUNA_ATTACH_REACH_UM,
        "lacuna_attach_reach_px": LACUNA_ATTACH_REACH_PX,
        "lacuna_attach_min_signal_fraction": config.LACUNA_ATTACH_MIN_SIGNAL_FRACTION,
        "contact_reach_px": CONTACT_REACH_PX,
        "glow_profile_fraction": config.GLOW_PROFILE_FRACTION,
        "glow_zone_cut_fraction": config.GLOW_ZONE_CUT_FRACTION,
        "glow_zone_max_um": config.GLOW_ZONE_MAX_UM,
        "glow_zone_max_px": GLOW_ZONE_MAX_PX,
        # The zone from the hole (METHODS section 19), which is the rule that
        # decides where the gain applies; the glow extent above is measurement.
        "hole_zone_rule": config.HOLE_ZONE_RULE,
        "hole_zone_margin_um": config.HOLE_ZONE_MARGIN_UM,
        "hole_zone_margin_px": HOLE_ZONE_MARGIN_PX,
        "hole_zone_sectors": HOLE_SECTORS,
        "hole_gain_band_um": config.HOLE_GAIN_BAND_UM,
        "hole_gain_percentile": config.HOLE_GAIN_PERCENTILE,
        "hole_gain_clip": [config.HOLE_GAIN_MIN, config.HOLE_GAIN_MAX],
        "hole_new_min_length_um": config.HOLE_NEW_MIN_LENGTH_UM,
        "hole_new_min_length_px": HOLE_NEW_MIN_LENGTH_PX,
        "hole_new_min_aspect": config.HOLE_NEW_MIN_ASPECT,
        "hole_zone_px": int(result["glow_zone"].sum()),
        "hole_zone_added_px": (result["hole_zone"]["added_px"]
                               if result["hole_zone"] else 0),
        "hole_gain_step_um": config.HOLE_GAIN_STEP_UM,
        "hole_gain_smooth_annuli": config.HOLE_GAIN_SMOOTH,
        "hole_zone_gains": (result["hole_zone"]["gains"] if result["hole_zone"] else None),
        "hole_zone_guard_dropped_px": (result["hole_zone"]["guard"]["dropped_px"]
                                       if result["hole_zone"] else 0),
        "contact_every_touching_body": config.CONTACT_EVERY_TOUCHING_BODY,
        "lacuna_attach_rule": ("a node attaches only if the dimmest ridge response on the straight "
                               "path from the lacuna surface to it reaches that fraction of the "
                               "response's own low cut"),
        "prune_spur_len_px": PRUNE_SPUR_LEN_PX,
        "min_internal_edge_len_px": MIN_INTERNAL_EDGE_LEN_PX,
        "graph_cleanup_max_iter": GRAPH_CLEANUP_MAX_ITER,
        "ownership": "graph connectivity, no distance cap",
        "root_merge_dist_px": ROOT_MERGE_DIST_PX,
        "ring_radii_px": list(RING_RADII_PX),
        # The biological length limit, in micrometres and in the pixels it became.
        "max_canaliculus_length_um": config.MAX_CANALICULUS_LENGTH_UM,
        "max_canaliculus_length_px": MAX_CANALICULUS_LENGTH_PX,
        "length_prune_removed_px": result["length_prune"]["removed_px"],
        "length_prune_rounds": result["length_prune"]["rounds"],
        "canaliculus_length_range_um": list(config.CANALICULUS_LENGTH_RANGE_UM),
        **extra,
    }


DETECTION_NOTE = (
    "Detection record: what feature 2 did, with no measured value in it. The "
    "mask, the skeleton, the vascular mask and the graph file beside it are what "
    "it produced; every number measured from them is in "
    "results/<label>/5_quantification/ (src/quantification.py). The method is "
    "the ridge method with gap bridging off, so no gap was joined."
)


def save_detection_json(result: dict, out_path: Path) -> None:
    """The record of one network detection run: parameters, the computed cuts,
    and provenance."""
    label = lacunae.image_label(result["image_path"])
    payload = {
        "status": "pre-validation",
        "units": "px",
        "stage": "canalicular network detection",
        "image": result["image_path"].name,
        "image_label": label,
        "note": DETECTION_NOTE,
        "outputs": {
            "mask": f"{label}_{config.SUFFIX_CANALICULI_MASK}",
            "skeleton": f"{label}_{config.SUFFIX_CANALICULI_SKELETON}",
            "vascular_mask": f"{label}_{config.SUFFIX_CANALICULI_VASCULAR}",
            "unattached": f"{label}_{config.SUFFIX_CANALICULI_UNATTACHED}",
            "graph": f"{label}_{config.SUFFIX_CANALICULI_GRAPH}",
            "verification": f"{label}_{config.SUFFIX_CANALICULI_VERIFICATION}",
        },
        "parameters": parameters(result),
        "provenance": lacunae.provenance(),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)


def save_graph(result: dict, out_path: Path) -> None:
    """The cleaned graph and its ownership, for src/quantification.py: node
    keys (row, col) and ("cell", id), edge weight (length px) and branches,
    the node owner, its distance through the network and the edge owner. The
    skan object is not in it; only the drawing needs that."""
    import pickle

    payload = {
        "format": 1,
        "image_label": lacunae.image_label(result["image_path"]),
        "graph": result["graph"],
        "owner": result["owner"],
        "node_dist": result["node_dist"],
        "edge_owner": result["edge_owner"],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        pickle.dump(payload, f, protocol=4)


def write_outputs(result: dict, out_root: Path) -> None:
    """The canaliculi files of one image under out_root (the results layout)."""
    label = lacunae.image_label(result["image_path"])

    def path(section, suffix):
        return lacunae.result_path(out_root, label, section, suffix)

    def save_mask(mask, suffix):
        imsave(path(config.SECTION_CANALICULI, suffix), (mask * 255).astype(np.uint8), check_contrast=False)

    mask_path = path(config.SECTION_CANALICULI, config.SUFFIX_CANALICULI_MASK)
    mask_path.parent.mkdir(parents=True, exist_ok=True)
    imsave(mask_path, (result["candidate"] * 255).astype(np.uint8), check_contrast=False)
    save_mask(result["skeleton"], config.SUFFIX_CANALICULI_SKELETON)
    save_mask(result["flagged"], config.SUFFIX_CANALICULI_VASCULAR)
    save_mask(result["unattached"], config.SUFFIX_CANALICULI_UNATTACHED)
    save_graph(result, path(config.SECTION_CANALICULI, config.SUFFIX_CANALICULI_GRAPH))
    save_detection_json(result, path(config.SECTION_CANALICULI, config.SUFFIX_CANALICULI_DETECTION))
    save_verification(result, path(config.SECTION_CANALICULI, config.SUFFIX_CANALICULI_VERIFICATION))


# Bone ROI masks (option -m). One PNG per image, white = bone, the size of the
# image, named by the image's clean name or by its short name, the label used
# in results/ (config.IMAGE_LABELS, the one naming table). No ROI is applied
# without -m.
ROI_SHORT_NAMES = config.IMAGE_LABELS


def load_roi_mask(roi_dir: Path, image_path: Path, shape: tuple) -> tuple[np.ndarray | None, str | None]:
    """(mask, file name) of the ROI for one image, or (None, None) if the
    folder holds none. A mask of another size is refused."""
    from skimage.io import imread

    clean = lacunae.clean_name(image_path)
    for name in (clean, ROI_SHORT_NAMES.get(clean, clean)):
        path = roi_dir / f"{name}.png"
        if path.is_file():
            data = imread(path)
            if data.ndim == 3:
                data = data[..., :3].max(axis=-1)
            if data.shape != shape:
                raise ValueError(f"ROI {path.name} is {data.shape}, the image is {shape}")
            return data > 127, path.name
    return None, None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Canalicular network detection (pre-validation, px). Measures: src/quantification.py."
    )
    lacunae.add_input_arguments(parser)
    args = parser.parse_args()

    for image_path in lacunae.image_paths(args):
        result = analyse_image(image_path)
        out_dir = args.out / lacunae.image_label(image_path)
        write_outputs(result, args.out)
        print(
            f"{image_path.name}: lacunae={result['lacunae']['lacuna_count']}  "
            f"skeleton px={int(result['skeleton'].sum())}  "
            f"t_lo={result['t_lo']:.6f}  -> {out_dir}"
        )

    print("Measure these with: python src/quantification.py "
          + (f"--dir {args.dir}" if args.dir else f'--image "{args.image}"')
          + (f" -o {args.out}" if args.out != config.RESULTS_DIR else ""))


if __name__ == "__main__":
    main()
