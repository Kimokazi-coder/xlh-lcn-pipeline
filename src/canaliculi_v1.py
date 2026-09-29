"""EXPERIMENTAL per-lacuna canaliculi feature extraction.

STATUS: v1-RAW, pre-validation. Builds on segment_lacunae_v2's lacuna
segmentation (imported, not modified) to additionally trace the canalicular
network and attribute it to individual lacunae. Nothing here has been
checked against ground truth. Parameters below are candidates only and are
kept out of config.py until validated. Everything stays in PIXEL units --
PIXEL_SIZE_UM is None, so nothing is converted to microns.

SWITCHES (defaults marked *). Every one keeps the previous behaviour
available so old and new can be compared on the same image; any
non-default run writes to all_method_results/ with a suffix naming the
setting, so it can never overwrite a default output.

    LACUNA_SOURCE      *"v2" | "v3_candidate" | "hybrid"
                       which lacuna detector feeds this module
    PREPROCESS_MODE    *"tophat" | "ridge" | "tophat+ridge" | "none"
                       how the channel is flattened before thresholding
    THRESHOLD_MODE     *"multiotsu_low" | "hysteresis"
                       how the pre-processed image is cut
    GAP_BRIDGING       *False | True
                       evidence-based joining of broken threads
    EXCLUSION_MODE     *"none" | "auto" | "manual" | "both"
                       removal of non-LCN structures before skeletonizing
    ASSIGNMENT_METHOD  *"graph" | "euclidean"
                       how a canaliculus is attributed to a cell
    COUNT_MODE         *"edge" | "path" | "roots"
                       what counts as one canaliculus

NONE of these defaults has been validated. They are the settings that have
been looked at most, not the settings known to be right. Every tunable
constant below carries its own provenance comment -- what it does, why
that value, and whether it came from a measured distribution, a visual
check, or is an untuned initial guess. Values derived from data were
derived on a fixed tuning set (542_z06, 543-2, 682_z29) with the other
five WT images held out.

A NOTE ON COUNT_MODE, for the write-up: "edge" counts graph edges, which
is an OCY-style NETWORK parameter and NOT "canaliculi per cell". A tree
with T tips has ~2T-1 edges, so edge counts run about double any per-cell
canaliculus count. "roots" is the per-cell quantity.

Method:
    1. Segment lacunae with segment_lacunae_v2's multi-Otsu + watershed
       approach (imported as-is).
    2. Segment the canalicular network. PREPROCESS_MODE selects how:
       - "tophat" (default, OCY-style -- see OCY_thr_stack.m and
         OCY_main.m in Kollmannsberger et al., "The small world of
         osteocytes"): light Gaussian smoothing (sigma below canaliculus
         width), then a white top-hat with a disk structuring element to
         flatten the diffuse background haze, then the histogram-mode
         offset subtraction OCY applies after its top-hat, then normalize
         and threshold. Without this, a plain global cut on the raw
         channel renders ~3-5px threads as ~6-10px fused ribbons whose
         skeletons branch everywhere -- a main reason counts ran high.
       - "none" (old behaviour, kept for comparison): threshold the raw
         channel directly.
       Either way the cut is the LOWER of the two multi-Otsu (3-class)
       cuts on the (pre-processed) image -- background vs. everything
       else, computed per-image, same idea as v2's threshold but one
       level down; strict ">" so a pixel exactly at the cut is never
       included. The lacuna bodies plus a small buffer are then
       subtracted, the result despeckled by size (not by erosion, which
       would erase 1px-wide threads), then skeletonized to 1px
       centerlines.
    3. Assign every skeleton branch to a lacuna. Two methods, chosen by
       ASSIGNMENT_METHOD:
       - "graph" (default): the whole skeleton is one weighted graph
         (nodes = junction/endpoint pixels, edges = branches weighted by
         branch length). Each lacuna is attached as a virtual source node
         linked to every skeleton node within LACUNA_ATTACH_GAP_PX of its
         body. A single multi-source shortest-path run then assigns every
         reachable skeleton node to whichever cell it is graph-connected
         to via the shortest path -- i.e. by network connectivity, the
         way OCY (Kollmannsberger et al., "The small world of osteocytes")
         assigns a canaliculus to the cell it physically connects to,
         not by which cell is spatially closest in a straight line. This
         fixes the old method's straight-edged territories in dense
         fields, which could hand half of a canaliculus to the wrong
         neighbor. The graph is cleaned up first (clean_network_graph,
         OCY's Skel2Graph3D THR_BRANCH idea): terminal spurs shorter than
         PRUNE_SPUR_LEN_PX pruned, internal edges shorter than
         MIN_INTERNAL_EDGE_LEN_PX collapsed as thread-crossing artifacts,
         degree-2 chains re-simplified into single edges so one thread is
         one edge of its true length, all iterated to a fixed point.
       - "euclidean" (old behaviour, kept for comparison): every skeleton
         pixel assigned to its nearest lacuna by a Euclidean distance
         transform (a Voronoi split), with no spur pruning.
    4. Per lacuna, count canaliculi and their lengths. For the "graph"
       method, COUNT_MODE decides what "one canaliculus" means:
       - "edge" (default, OCY-style): one canaliculus = one graph edge
         between two nodes, the way OCY counts `link` structs -- every
         per-network number in OCY_get_network_params.m is derived from
         them. Every real edge is assigned to the cell that reaches it
         first through the network (see assign_edges). Reported per cell:
         edges owned, total length, mean edge length.
       - "path" (old behaviour, kept for comparison): single-source
         Dijkstra from that lacuna's virtual node; every reachable,
         cell-owned, degree-1 real node is a tip: one canaliculus.
         Length = path distance from the tip back to the root (the first
         real node on the path), i.e. the full path minus the virtual
         attachment edge. This re-counts the shared trunk once per tip,
         inflating both count and mean length.
       The "euclidean" method is always path-based (per-component
       root-to-tip tree search within that lacuna's owned skeleton
       subset; root = point closest to the lacuna body; a fragment
       farther than MAX_ROOT_GAP_PX from the lacuna is treated as
       unreachable, not one long canaliculus) and ignores COUNT_MODE.

Border lacunae (on_border=True, from v2) are kept in the per-lacuna table
and drawn in the verification image, but excluded from the per-image
summary stats -- their canaliculi are truncated by the field of view.

Outputs, per image, under results/canaliculi/<image_stem_with_underscores>/.
A DEFAULT run (no CLI overrides) writes these five files, unsuffixed, at
the top level of that folder:
    verification.png   original image at near-full brightness; every lacuna
                        and its owned canaliculi drawn in one unique,
                        randomly (but reproducibly) assigned color, so the
                        colored tracing can be checked directly against the
                        real red canaliculi underneath. With "graph"
                        assignment, a cell's color should visibly follow
                        its connected threads and stop at network branch
                        points, not cut the field into straight-edged
                        blocks.
    canaliculi_mask.png the raw binary network mask, unannotated -- what
                         the per-cell tracing is actually built on
    skeleton.png        that mask's 1px-wide skeleton, unannotated
    measurements.xlsx   "summary" sheet (interior-only mean/median/SD of
                         canaliculi_count, total_length_px and
                         mean_canaliculus_length_px) + "per_lacuna" sheet
                         (one row per lacuna, incl. border ones, flagged
                         on_border)
    measurements.json   same data + the parameters used for this run

A COMPARISON run -- any run passing --method, --preprocess or
--count-mode to override a default for that run only -- suffixes every
filename with the overrides used ("_<method>", "_pre-<mode>",
"_count-<mode>", concatenated if several) AND writes the whole set into
the all_method_results/ subfolder of the same image folder:

    results/canaliculi/<image>/
        verification.png              <- default run
        canaliculi_mask.png
        skeleton.png
        measurements.xlsx
        measurements.json
        all_method_results/           <- every comparison run
            verification_euclidean.png
            measurements_pre-none.json
            skeleton_count-path.png
            ...

So a comparison run can never overwrite the default outputs, and the
current default result stays visible at the top of the folder instead of
being buried among a dozen variants. Existing results were moved into
this layout by src/tidy_canaliculi_results.py.

Usage:
    python src/canaliculi_v1.py --dir data/WT
    python src/canaliculi_v1.py --dir data/WT --method euclidean
    python src/canaliculi_v1.py --dir data/WT --preprocess none
    python src/canaliculi_v1.py --dir data/WT --count-mode path
    python src/canaliculi_v1.py --image data/WT/example.tif
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import deque
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
from count_lacunae import load_channel  # noqa: E402
import segment_lacunae_v2 as seg2  # noqa: E402
import exclusion_mask  # noqa: E402
import gap_bridging as gap_bridging_mod  # noqa: E402
import merge_adjacent_lacunae  # noqa: E402

# --- Candidate parameters (NOT in config.py yet -- see module docstring) ---

# Which assignment method to use. "graph" = network-connectivity (OCY-style,
# current default). "euclidean" = old nearest-distance Voronoi, kept for
# comparison -- see the module docstring and README section above.
ASSIGNMENT_METHOD = "graph"

# What counts as ONE canaliculus. Applies to the "graph" method only --
# the legacy "euclidean" method is inherently path-based and ignores this.
#   "edge" (default, OCY-style): one canaliculus = one graph edge between
#       two nodes (branch points / endpoints), which is how OCY counts --
#       its `link` structs are the canaliculi, and OCY_get_network_params.m
#       derives every per-network number from them. Reported per cell:
#       number of edges owned, total length, mean edge length.
#   "path" (old behaviour, kept for comparison): one canaliculus = one
#       cell-to-tip path. This double-counts the shared trunk of every
#       branching thread -- a stem that forks into 4 tips is reported as 4
#       canaliculi, each carrying the whole stem length again -- so it
#       inflates both count and mean length.
#   "roots" (Phase 4b, NOT default): one canaliculus = one distinct thread
#       LEAVING THE LACUNA SURFACE. Counts the skeleton branches attaching
#       within LACUNA_ATTACH_GAP_PX of the body, merging attachment points
#       closer than ROOT_MERGE_DIST_PX so one thick root is not counted
#       twice. This is closest to what a person counts by eye in ImageJ
#       ("canaliculi emanating per lacuna"), and is insensitive to how the
#       thread fragments further out -- which matters here, because 82% of
#       skeleton nodes are degree-1 thread ends (Phase 0b).
#
# IMPORTANT, for the write-up: "edge" is an OCY-style NETWORK parameter --
# the number of graph edges the cell owns. It is NOT "canaliculi per cell"
# and should not be reported under that name. A tree with T tips has ~2T-1
# edges, so edge counts run about double any per-cell canaliculus count.
# "roots" is the per-cell quantity.
COUNT_MODE = "edge"

# Two attachment points closer than this are treated as one root. A single
# thick canaliculus can meet the lacuna boundary over several skeleton
# pixels and so present more than one graph node within the attachment
# gap; merging below one thread width stops that being counted twice.
# Measured canalicular full width is p50 ~6.0 and p99 ~8.5 px (Phase 0),
# so 8 px is just under the widest real thread -- below it, two points
# cannot be separate threads.
ROOT_MERGE_DIST_PX = 8.0

# Removal of non-LCN structures (vascular canals, canal edges) from the
# canaliculi candidate mask before skeletonization. See exclusion_mask.py
# for how each mode builds its region and why "auto" works on the raw
# channel rather than on skeleton geometry.
#   "none"   (default) no exclusion -- current behaviour, unchanged
#   "auto"   broad bright raw-channel structures far larger than any lacuna
#   "manual" a hand-drawn mask from data/exclusion_masks/<stem>.png
#   "both"   union of the two
# Stays "none" until the exclusion has been reviewed: on the 8 WT images
# the flagged structures do NOT measurably inflate the canaliculi mask
# inside themselves (density ratios 0.80-1.46, two of five below 1), so
# switching this on would remove mask pixels at roughly the field's own
# density -- i.e. mostly real canaliculi. See docs/PROGRESS.md.
EXCLUSION_MODE = "none"

# Which lacuna detector feeds the canaliculi step.
#   "v2"           (default) segment_lacunae_v2: brightness, the top class
#                  of a 3-class multi-Otsu cut. Accepted and unchanged.
#   "v3_candidate" segment_lacunae_v3_candidate: breadth, a large
#                  morphological opening of the raw channel. NOT default.
#   "hybrid"       segment_lacunae_hybrid: every v2 lacuna, plus a v3-only
#                  object only if it is bright enough relative to this
#                  image's own lacunae, is not on a flagged structure, and
#                  has >= MIN_ROOTS canaliculi radiating from it. NOT
#                  default. Adds 2 objects across the 8 WT images.
# v3 finds every v2 object on 7 of 8 WT images and adds 5-29 more per
# image. Whether those extras are real lacunae -- many are partly outside
# the focal plane -- is a scientific decision, not a coding one, so they
# are listed in docs/DECISIONS_NEEDED.md for review rather than adopted.
LACUNA_SOURCE = "v2"

# --- Canalicular-mask preprocessing (OCY-style; see module docstring) ---
# "tophat" = smooth + white top-hat + histogram-mode offset subtraction
# before thresholding (default). "none" = threshold the raw channel, the
# old behaviour, kept behind this switch for before/after comparison.
# "ridge" and "tophat+ridge" are Phase 2 additions and are NOT default.
#   "tophat"       (default) smooth + white top-hat + mode subtraction
#   "ridge"        smooth + multi-scale ridge filter
#   "tophat+ridge" the top-hat chain, then the ridge filter on its output
#   "none"         raw channel
PREPROCESS_MODE = "tophat"

# Which multi-scale ridge (tubeness) filter the "ridge" modes use.
# skimage offers three and they are not interchangeable here:
#   "sato"      responds to bright tube-like structures from the Hessian
#               eigenvalues, with the scale set only by `sigmas`. Chosen as
#               the default of the two offered: one meaningful parameter,
#               and it degrades gracefully where threads cross.
#   "meijering" built for neurites, uses a modified Hessian that is more
#               sensitive to very thin lines but also noisier on texture,
#               which this densely textured matrix has a lot of.
#   frangi      NOT offered. It carries three extra parameters (alpha,
#               beta, gamma) that would each need tuning and provenance,
#               and it is known to suppress response at junctions -- which
#               is where the canalicular network's branch points are, the
#               thing we most need to keep.
RIDGE_FILTER = "sato"

# Scales (px) the ridge filter is evaluated at. A ridge filter responds
# most where sigma matches the structure's half-width, so these have to
# span the measured canalicular half-width range rather than be guessed.
# Measured post-top-hat over all 8 WT images (diagnose_canaliculi_mask.py):
# half-width p50 ~3.0, p90 ~4.2, p99 ~4.2 px, with the thinnest threads
# around 1 px. 1-4 covers that range at 1 px steps.
RIDGE_SIGMAS_PX = (1.0, 2.0, 3.0, 4.0)

# How the (pre-processed) image is cut into foreground/background.
#   "multiotsu_low" the lower of the two 3-class multi-Otsu cuts. The
#                   pre-2026-09-28 default, kept for comparison.
#   "hysteresis"    (DEFAULT) keep dim pixels only where they connect to a
#                   confidently bright one -- reconnects a dim stretch of a
#                   real thread without admitting isolated background
#                   speckle.
#
# ADOPTED AS DEFAULT 2026-09-28, on the Phase 2 comparison plus a visual
# check of the crops confirming the added connections follow real dim
# threads. Of eight settings tried, this one (with bridging, below) was
# inside BOTH pre-declared guards on the tuning AND held-out sets --
# 1.13x total skeleton length against a 1.20x limit, 2.13x loops against a
# max(1.5x, +50) limit -- while cutting components per 10,000 skeleton px
# from 225 to 169 and raising owned length fraction from 0.244 to 0.343.
# Five of the eight settings failed a guard; see docs/DECISIONS_NEEDED.md D1.
THRESHOLD_MODE = "hysteresis"

# For "hysteresis": the high cut is the image's own multi-Otsu low cut (the
# value the old default used), and the low cut is this fraction of it. Both
# are therefore derived per image from its own histogram, with no global
# intensity constant.
#
# 0.75 was SELECTED, not assumed. 0.5 was tried first and failed both
# guards (1.30x length, 6.53x loops) by growing dim regions into sheets;
# 0.75 passes on tuning and held-out alike. It remains lightly tuned --
# one value tried after one failure, not a swept parameter -- so treat it
# as the weakest-provenance number in the default set.
HYSTERESIS_LOW_FRACTION = 0.75

# Evidence-based gap bridging (Phase 2c). See gap_bridging.py for the three
# tests a bridge must pass and where each limit comes from.
#
# ADOPTED AS DEFAULT 2026-09-28. On top of hysteresis it adds only ~18
# bridges per image, against ~122 on the old default, because hysteresis
# has already closed most of the same gaps -- two independent mechanisms
# converging on the same gaps, which is the evidence those gaps are real.
GAP_BRIDGING = True

# Forbid hysteresis and gap bridging from creating NEW connections inside a
# Phase 1 flagged structure (the auto shape gate in exclusion_mask, taken
# BEFORE the lacuna safety margin).
#
# WHY. Step 1 adopted hysteresis + bridging as defaults. The x555_y500 crop
# of 542_z06 then showed both of them growing a vertical segment along the
# vascular band, which the assignment step duly handed to a cell. That is a
# vessel wall being counted as a canaliculus.
#
# WHAT IT DOES, AND DOES NOT DO. Inside a flagged structure, hysteresis may
# keep only pixels that were ALREADY above the high (strict) cut, and no
# gap bridge may start in, end in, or cross the region. Nothing is deleted:
# every pixel the old multiotsu_low default would have had is still there,
# so this can only ever remove connections the new default would have ADDED.
# Outside flagged structures nothing changes at all.
#
# This is independent of EXCLUSION_MODE, which stays "none". Exclusion
# REMOVES signal and is still unjustified (Phase 1 found flagged structures
# do not clearly inflate the mask); this only declines to ADD any, which
# needs no such justification.
BLOCK_GROWTH_IN_FLAGGED = True

# Radius (px) of the disk structuring element for the white top-hat.
# Adapted from OCY_thr_stack.m, which uses strel('disk',25) at 0.2 um/voxel.
# A white top-hat keeps what is NARROWER than its structuring element and
# flattens what is broader, so the radius has to sit just above the widest
# real canaliculus and well below the diffuse halo around each lacuna.
# Measured with diagnose_canaliculi_mask.py: after top-hatting, canalicular
# half-widths are p50~3.0 / p99~4.2 px, i.e. real threads are at most ~8px
# across, so a disk of radius 5 (diameter 11) cannot fit inside one and
# every thread survives intact. Checked visually at r=4/5/6 on 542_z06 and
# 543-2: r=4 starts breaking threads into fragments, r=6 starts fusing
# neighbouring threads back into ribbons, r=5 does neither.
TOPHAT_RADIUS_PX = 5

# Sigma (px) of the Gaussian applied before the top-hat, to suppress shot
# noise without erasing threads. OCY_main.m does the same with
# smooth3(img,'gaussian',5). Must stay BELOW the canaliculus width (~5px
# here). Set to 0 to disable.
SMOOTH_SIGMA_PX = 0.8

# OCY_thr_stack.m, after its top-hat, builds a 256-bin histogram of the
# image, zeroes the first bin and everything from bin 200 up, and subtracts
# the modal intensity, clipping at 0 -- a residual-background offset
# removal. Reproduced here. Set to False to skip it.
BACKGROUND_MODE_SUBTRACT = True

# Write the raw binary network mask and its skeleton as PNGs next to the
# verification overlay, so the segmentation itself can be inspected
# directly instead of only through the colored per-cell tracing.
SAVE_MASK_PNG = True

# A skeleton node within this many px of a lacuna body is treated as
# attached to it (a graph-method "root"). This is a gap-closing tolerance
# for the LACUNA_DILATION_PX buffer already carved out around each lacuna,
# not a search radius for real canaliculi -- but the initial guess of 5
# left 28/98 lacunae (29%) across all 8 WT images with NO attachment
# point at all (see --attach-gaps in diagnose_lacuna_splits.py), which
# silently gave them 0 canaliculi while a few well-attached neighbors
# absorbed tips that should have been unreachable/theirs instead. The
# min-gap distribution across all 98 lacunae was smooth (2.24 up to 11.18
# px, no natural break to split on), so 10 was a coverage choice, not a
# gap-based one: it left 1/98 lacunae unattached instead of 28.
# Since the top-hat preprocessing went in, thread signal survives right up
# against the lacuna boundaries and the gaps have collapsed: max min-gap is
# now 7.00 px (p50 2.24, p95 5.00) and 0/98 lacunae are unattached, so 10
# now clears the worst case with room to spare rather than sitting inside
# the distribution. Re-check with diagnose_lacuna_splits.py --attach-gaps
# if the dataset or the preprocessing changes.
LACUNA_ATTACH_GAP_PX = 10

# Terminal branches (graph method) shorter than this are treated as
# thresholding-noise spurs and pruned before counting/assignment -- this
# is what brings canaliculi_count down from the tens-to-hundreds/cell seen
# with the Euclidean method to a plausible range. Iteratively applied
# (pruning one spur can expose another).
PRUNE_SPUR_LEN_PX = 4

# Internal edges (both ends a real junction) shorter than this are treated
# as crossing artifacts and collapsed -- see collapse_short_internal_edges.
# OCY's equivalent is Skel2Graph3D's THR_BRANCH, called with 5 voxels in
# OCY_run_Skel2Graph3D.m; that is ~2.5x their canaliculus diameter, which
# scaled to our threads would be ~15px and would take out half of all
# internal edges, so the value here is anchored on our own geometry
# instead: a false junction where two threads cross spans at most one
# thread width, and the measured thread width here is ~6px (post-top-hat
# half-width p50 = 3.0px, see TOPHAT_RADIUS_PX). An edge shorter than that
# cannot be a real canalicular segment between two real branch points.
# The pooled internal-edge length distribution across all 8 WT images is
# smooth with no natural break (p10=3.4, p25=7.8, p50=16.7px), so this is
# a geometry-based cutoff, not a gap-based one; it removes 18% of internal
# edges. Set to 0 to disable.
MIN_INTERNAL_EDGE_LEN_PX = 6

# Safety stop for the prune/collapse/simplify loop in clean_network_graph.
# It normally converges in a handful of passes; this only bounds the
# pathological case.
GRAPH_CLEANUP_MAX_ITER = 20

# Buffer (px) eroded away from the canaliculi candidate mask around each
# lacuna body, so the lacuna's own bright rim isn't mistaken for a stub of
# canaliculus right at the boundary.
LACUNA_DILATION_PX = 2

# Candidate canaliculus fragments smaller than this (px^2) are dropped as
# thresholding noise before skeletonizing. Kept deliberately small so a
# real, thin, short thread survives -- despeckling here is by pixel COUNT,
# never by erosion/opening (which would delete 1px-wide real threads).
MIN_THREAD_OBJECT_PX2 = 8

# Euclidean method only: a connected skeleton fragment whose closest point
# to a lacuna is farther than this (px) is treated as not actually
# attached to that lacuna, not as one long canaliculus.
MAX_ROOT_GAP_PX = 15

# Cosmetic only: how much the owned-skeleton pixels are dilated for
# visibility in the verification PNG. Does not affect any measurement.
VIS_SKELETON_DILATION_PX = 2

# Cosmetic only: how much the background image is shown at in the
# verification PNG. 1.0 = full-brightness original, no dimming, so the
# real red canaliculi are shown exactly as acquired underneath the colored
# tracing, for a direct check that the tracing actually matches the signal.
VIS_DIM_FACTOR = 1.0

# Cosmetic only: colors are evenly spaced around the hue wheel for maximum
# contrast, then shuffled so lacuna N and N+1 (often spatial neighbors)
# don't land on adjacent, blend-prone hues. Shuffled with config.RANDOM_SEED
# so a rerun reproduces the same color assignment (comparable across runs)
# rather than changing every time.
COLOR_SATURATION = 0.9
COLOR_VALUE = 1.0

CANALICULI_DIR = config.CANALICULI_DIR

# Subfolder of an image's output folder that comparison runs (any run with
# a non-empty output suffix, i.e. one overriding a default via --method,
# --preprocess or --count-mode) write into, so the default run's outputs
# stay alone at the top level. Layout only -- affects no measurement.
# src/tidy_canaliculi_results.py uses the same name for existing results.
COMPARISON_SUBDIR = "all_method_results"


# --- Canalicular network segmentation -----------------------------------

def _subtract_background_mode(img: np.ndarray) -> np.ndarray:
    """Residual-background offset removal, adapted from OCY_thr_stack.m:
    256-bin histogram of img/max(img), zero out bin 1 and bins 200+, take
    the modal bin as the background level, subtract it and clip at 0.
    (OCY subtracts the bin INDEX from an 8-bit image, which comes to the
    same thing as subtracting the modal intensity; written out explicitly
    here because our channel is float in [0, 1].)"""
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


def preprocess_channel(channel: np.ndarray, mode: str) -> np.ndarray:
    """Flatten the background before thresholding, so thin threads
    threshold as thin threads instead of fusing into ribbons. OCY-style:
    smooth3 gaussian (OCY_main.m) then imtophat + mode subtraction
    (OCY_thr_stack.m). Returns an image renormalized to [0, 1]; "none"
    returns the channel unchanged."""
    if mode == "none":
        return channel
    if mode not in ("tophat", "ridge", "tophat+ridge"):
        raise ValueError(
            f"Unknown preprocess mode: {mode!r} "
            "(expected 'tophat', 'ridge', 'tophat+ridge' or 'none')"
        )

    img = channel
    if SMOOTH_SIGMA_PX > 0:
        img = ndi.gaussian_filter(img, SMOOTH_SIGMA_PX)
    if mode in ("tophat", "tophat+ridge"):
        img = morphology.white_tophat(img, morphology.disk(TOPHAT_RADIUS_PX))
        if BACKGROUND_MODE_SUBTRACT:
            img = _subtract_background_mode(img)
    if mode in ("ridge", "tophat+ridge"):
        img = _ridge_response(img)
    peak = float(img.max())
    return img / peak if peak > 0 else img


def _ridge_response(img: np.ndarray) -> np.ndarray:
    """Multi-scale ridge (tubeness) response for BRIGHT thin structures.
    See RIDGE_FILTER for why sato is offered and frangi is not, and
    RIDGE_SIGMAS_PX for where the scales come from.

    This is a departure from OCY, which thresholds a top-hatted image
    globally (OCY_thr_stack.m) and has no ridge step. The reason is the 2D
    setting: OCY's 3D stacks keep a canaliculus continuous across planes,
    while a single optical section leaves ~82% of skeleton nodes as
    degree-1 thread ends (Phase 0b). A ridge filter scores a pixel on
    whether it sits on a locally line-like structure rather than on its
    brightness alone, which is the property that survives a thread dimming
    as it leaves the focal plane."""
    if RIDGE_FILTER == "sato":
        return filters.sato(img, sigmas=RIDGE_SIGMAS_PX, black_ridges=False)
    if RIDGE_FILTER == "meijering":
        return filters.meijering(img, sigmas=RIDGE_SIGMAS_PX, black_ridges=False)
    raise ValueError(f"Unknown RIDGE_FILTER: {RIDGE_FILTER!r} (expected 'sato' or 'meijering')")


def total_signal_mask(channel: np.ndarray) -> tuple[np.ndarray, float]:
    """Lower of the two multi-Otsu (3-class) cuts on this image's own
    histogram: background vs. everything else (mesh + lacunae). Same
    per-image-adaptive idea as v2's threshold, one level down. Strict ">"
    so a background-valued pixel exactly at the cut is never included."""
    try:
        thresholds = filters.threshold_multiotsu(channel, classes=3)
        t_lo = float(thresholds[0])
    except ValueError:
        t_lo = float(filters.threshold_otsu(channel))
    return channel > t_lo, t_lo


def build_lacuna_maps(labels: np.ndarray, kept: list[tuple]) -> tuple[np.ndarray, np.ndarray]:
    """Return (lacuna_mask, lacuna_id_map). lacuna_id_map is 0 outside any
    kept lacuna, else the lacuna's 1..N id (same numbering as v2's
    per-lacuna measurements)."""
    lacuna_id_map = np.zeros(labels.shape, dtype=np.int32)
    for lacuna_id, (region, _on_border) in enumerate(kept, start=1):
        lacuna_id_map[labels == region.label] = lacuna_id
    return lacuna_id_map > 0, lacuna_id_map


def threshold_mask(
    img: np.ndarray, threshold_mode: str, no_growth: np.ndarray | None = None
) -> tuple[np.ndarray, float]:
    """Cut the pre-processed image into foreground/background. Returns
    (mask, the strict cut), so the reported t_lo means the same thing in
    both modes and stays comparable across settings.

    `no_growth` is a region where the permissive cut may not add anything:
    inside it only pixels already above the STRICT cut survive. See
    BLOCK_GROWTH_IN_FLAGGED."""
    strict_mask, t_lo = total_signal_mask(img)
    if threshold_mode == "multiotsu_low":
        return strict_mask, t_lo
    if threshold_mode == "hysteresis":
        # Keep a dim pixel only where it is connected to a confidently
        # bright one. Both cuts come from this image's own histogram --
        # the high cut IS the old default pipeline's cut, so hysteresis can
        # only ever ADD to that mask, never remove from it.
        low = t_lo * HYSTERESIS_LOW_FRACTION
        mask = filters.apply_hysteresis_threshold(img, low, t_lo)
        if no_growth is not None and no_growth.any():
            # Subtract only what hysteresis ADDED inside the region; the
            # strict-cut pixels there are kept, so nothing is deleted.
            mask = mask & ~(no_growth & ~strict_mask)
        return mask, t_lo
    raise ValueError(
        f"Unknown threshold mode: {threshold_mode!r} (expected 'multiotsu_low' or 'hysteresis')"
    )


def canaliculi_candidate_mask(
    channel: np.ndarray,
    lacuna_mask: np.ndarray,
    mode: str,
    threshold_mode: str = "multiotsu_low",
    no_growth: np.ndarray | None = None,
) -> tuple[np.ndarray, float]:
    signal, t_lo = threshold_mask(preprocess_channel(channel, mode), threshold_mode, no_growth)
    buffered_lacunae = morphology.dilation(lacuna_mask, morphology.disk(LACUNA_DILATION_PX))
    candidate = signal & ~buffered_lacunae
    candidate = morphology.remove_small_objects(candidate, min_size=MIN_THREAD_OBJECT_PX2)
    return candidate, t_lo


def nearest_lacuna_map(lacuna_id_map: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """For every pixel, (distance to the nearest lacuna pixel, that
    lacuna's id) -- a Euclidean Voronoi partition seeded from the lacunae.
    Used directly by the "euclidean" assignment method, and by "graph" for
    deciding which lacuna a within-gap attachment point belongs to."""
    dist, indices = ndi.distance_transform_edt(lacuna_id_map == 0, return_indices=True)
    nearest_id = lacuna_id_map[indices[0], indices[1]]
    return dist, nearest_id


def _node_key(row: float, col: float) -> tuple[int, int]:
    return (int(round(row)), int(round(col)))


def _is_cell_node(node) -> bool:
    """True for the virtual ("cell", id) source nodes, False for real
    skeleton pixel-coordinate nodes."""
    return isinstance(node, tuple) and len(node) == 2 and node[0] == "cell"


# --- "euclidean" assignment (old method, kept for comparison) -----------

def trace_lacuna_canaliculi(owned_skeleton: np.ndarray, dist_to_lacuna: np.ndarray) -> list[float]:
    """Return the list of root-to-tip canaliculus lengths (px) for one
    lacuna's owned skeleton subset. Empty list if there are none."""
    if not owned_skeleton.any():
        return []

    skel_obj = Skeleton(owned_skeleton)
    branch_data = summarize(skel_obj, separator="-")
    if len(branch_data) == 0:
        return []

    lengths: list[float] = []
    for _skeleton_id, component in branch_data.groupby("skeleton-id"):
        adjacency: dict[tuple[int, int], list[tuple[tuple[int, int], float]]] = {}
        for _idx, row in component.iterrows():
            if row["branch-type"] == 3:  # isolated cycle, no defined tip
                continue
            src = _node_key(row["image-coord-src-0"], row["image-coord-src-1"])
            dst = _node_key(row["image-coord-dst-0"], row["image-coord-dst-1"])
            weight = float(row["branch-distance"])
            adjacency.setdefault(src, []).append((dst, weight))
            adjacency.setdefault(dst, []).append((src, weight))

        if not adjacency:
            continue

        root = min(adjacency, key=lambda node: dist_to_lacuna[node[0], node[1]])
        if dist_to_lacuna[root[0], root[1]] > MAX_ROOT_GAP_PX:
            continue  # this fragment never actually reaches the lacuna

        # BFS from root, summing edge weight to every other node; degree-1
        # nodes other than the root are tips (canaliculus endpoints).
        cumulative = {root: 0.0}
        queue = deque([root])
        while queue:
            node = queue.popleft()
            for neighbor, weight in adjacency[node]:
                if neighbor not in cumulative:
                    cumulative[neighbor] = cumulative[node] + weight
                    queue.append(neighbor)

        for node, path_length in cumulative.items():
            if node == root:
                continue
            if len(adjacency[node]) == 1:  # degree-1, i.e. a tip
                lengths.append(path_length)

    return lengths


def canaliculi_measurements_euclidean(
    kept: list[tuple],
    skeleton: np.ndarray,
    nearest_id: np.ndarray,
    dist_to_lacuna: np.ndarray,
    precision: int,
) -> list[dict]:
    measurements = []
    for lacuna_id, (_region, on_border) in enumerate(kept, start=1):
        owned_skeleton = skeleton & (nearest_id == lacuna_id)
        lengths = trace_lacuna_canaliculi(owned_skeleton, dist_to_lacuna)
        measurements.append(_measurement_row(lacuna_id, lengths, on_border, precision))
    return measurements


# --- "graph" assignment (network connectivity, OCY-style) ---------------

def build_network_graph(skeleton: np.ndarray):
    """One weighted graph of the whole canalicular skeleton. Nodes are
    junction/endpoint pixel coords, edges are branches weighted by branch
    length in px. Each edge carries `branches`, the list of skan branch
    indices whose pixels it covers, so the graph can be simplified later
    (short internal edges collapsed, degree-2 chains merged) without
    losing the pixel paths the verification image is drawn from.

    nx.Graph holds no parallel edges, so where two separate branches join
    the same pair of nodes (a small loop) the weight kept is the shorter
    one, though both branches' pixels are recorded. That affects 1.3% of
    branches across the 8 WT images -- noted rather than fixed, since a
    MultiGraph would complicate every shortest-path step downstream for a
    ~1% effect."""
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
    """Branch indices whose pixels were folded into `node` when a short
    internal edge or a degree-2 chain was collapsed onto it. Kept so the
    verification image still paints every pixel the cell owns."""
    return G.nodes[node].setdefault("absorbed", [])


def prune_spurs(G: nx.Graph) -> bool:
    """Remove terminal branches shorter than PRUNE_SPUR_LEN_PX --
    thresholding-noise spurs, not real canaliculi. Removing one spur can
    expose another (its former neighbor may now be a short spur too), so
    this repeats until nothing more qualifies. Returns True if anything
    changed."""
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
    """Fold `drop` into `keep`: the edge between them disappears (its
    pixels are absorbed by `keep`), and every other edge of `drop` is
    re-pointed at `keep`. A re-pointed edge that duplicates one `keep`
    already has is merged into it, keeping the shorter weight and the
    union of the pixel paths."""
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
    """Remove INTERNAL edges (both ends a real junction) shorter than
    MIN_INTERNAL_EDGE_LEN_PX by merging their two endpoints into one node.

    This is the 2D version of what OCY handles with Skel2Graph3D's
    THR_BRANCH parameter (OCY_run_Skel2Graph3D.m calls it with THR=5):
    "all branches shorter than THR are removed", not only terminal ones.
    In a dense 2D projection, two threads that merely cross produce two
    junction nodes about one thread-width apart joined by a stub edge.
    That stub is not a canaliculus, it is the crossing itself -- left in,
    every crossing adds a spurious edge to the count and chops the two
    real threads into four fragments.

    The surviving node is whichever endpoint is closer to a lacuna body,
    so a node that was within LACUNA_ATTACH_GAP_PX of a cell cannot lose
    its attachment to the merge. Returns True if anything changed."""
    changed = False
    for u, v in list(G.edges()):
        if not G.has_edge(u, v):
            continue  # already consumed by an earlier merge in this pass
        if G.degree(u) < 3 or G.degree(v) < 3:
            continue  # terminal edge -- prune_spurs' business, not ours
        if G[u][v]["weight"] >= MIN_INTERNAL_EDGE_LEN_PX:
            continue
        keep, drop = (u, v) if dist_to_lacuna[u] <= dist_to_lacuna[v] else (v, u)
        _merge_nodes(G, keep, drop)
        changed = True
    return changed


def simplify_degree2_chains(G: nx.Graph) -> bool:
    """Dissolve every degree-2 node into its two neighbours, summing the
    weights, so one uninterrupted thread is ONE edge of its true length
    instead of several fragments.

    A degree-2 node is not a branch point and should not exist in a
    junction-to-junction graph, but pruning a spur off a degree-3 node
    leaves one behind, and so does collapsing a short internal edge. OCY
    never sees these because Skel2Graph3D rebuilds the graph from the
    voxel skeleton each round (Graph2Skel3D -> Skeleton3D -> Skel2Graph3D
    in OCY_run_Skel2Graph3D.m); simplifying in place is the cheaper 2D
    equivalent. Without it, edge counts are inflated and edge lengths are
    fragmented across several rows of the same real thread.

    A degree-2 node whose two neighbours are the same node, or already
    share an edge, is left alone: dissolving it would need a parallel edge
    that nx.Graph cannot hold, and dropping it would lose real length.
    Returns True if anything changed."""
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
    """Prune spurs, collapse short internal edges, re-simplify degree-2
    chains -- and repeat, because each step creates work for the others
    (collapsing an internal edge can leave a degree-2 node; dissolving
    that node can leave a short terminal edge). OCY does the equivalent by
    re-running its whole condense/skeletonize/re-graph cycle until the
    total network length stops changing (OCY_run_Skel2Graph3D.m);
    GRAPH_CLEANUP_MAX_ITER is a safety stop, not the intended exit."""
    for _ in range(GRAPH_CLEANUP_MAX_ITER):
        changed = prune_spurs(G)
        changed |= collapse_short_internal_edges(G, dist_to_lacuna)
        changed |= simplify_degree2_chains(G)
        if not changed:
            break
    G.remove_nodes_from([n for n in list(G.nodes()) if G.degree(n) == 0])
    return G


def attach_lacunae(
    G: nx.Graph,
    dist_to_lacuna: np.ndarray,
    nearest_id: np.ndarray,
    cell_ids: list[int],
) -> nx.Graph:
    """Add a virtual ("cell", id) node per lacuna, linked to every skeleton
    node within LACUNA_ATTACH_GAP_PX of that lacuna's body (nearest_id
    decides WHICH lacuna a given attachment point belongs to; the link
    weight is the gap distance, so paths start at the cell boundary)."""
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
    skeleton node is owned by the cell whose shortest graph path reaches
    it -- network connectivity, not straight-line distance. Returns
    (owner: {node_coord: cell_id}, node_dist: {node_coord: graph distance
    to that owning cell}); node_dist is what assign_edges uses to decide
    which end of an edge is the upstream one."""
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
    """Give EVERY real (non-virtual) edge an owning cell, not just the
    edges that happen to lie on some node's shortest path. An edge belongs
    to the cell that reaches it first, i.e. the owner of whichever endpoint
    is closer to a cell through the network -- the same rule OCY uses in
    OCY_assign_dist.m, where each link voxel takes min(node.dist + offset)
    over the link's two ends, so a link is reached through the end nearer
    a cell. Ties (equal distance, different cells) go to the lower cell id
    so a rerun is reproducible.

    Returns {frozenset({u, v}): cell_id}. Edges with no owned endpoint
    (a skeleton fragment not graph-connected to any lacuna) are left out."""
    edge_owner: dict = {}
    for u, v in G.edges():
        if _is_cell_node(u) or _is_cell_node(v):
            continue  # virtual lacuna attachment edge, not a canaliculus
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
    """Edge-based canaliculi for one cell (OCY-style): one canaliculus =
    one graph edge between two nodes/branch points, exactly as OCY counts
    `link` structs in OCY_get_network_params.m. Returns the length of each
    edge this cell owns, so len() is the count, sum() the total length and
    mean() the mean edge length."""
    lengths = []
    for edge, owner_id in edge_owner.items():
        if owner_id != cell_id:
            continue
        u, v = tuple(edge)
        lengths.append(float(G[u][v]["weight"]))
    return lengths


def trace_cell_canaliculi(G: nx.Graph, cell_id: int, owner: dict) -> list[float]:
    """Path-based canaliculi for one cell: single-source Dijkstra from its
    virtual node; every reachable, cell-owned, degree-1 real node is one
    canaliculus, with length measured from the lacuna boundary (the root
    -- the first real node on the path) outward, i.e. the full path minus
    the virtual attachment edge."""
    src = ("cell", cell_id)
    if not G.has_node(src):
        return []

    dist, paths = nx.single_source_dijkstra(G, src, weight="weight")
    lengths = []
    for node, path in paths.items():
        if _is_cell_node(node):
            continue
        if owner.get(node) != cell_id:
            continue  # reachable from this cell, but globally owned by another
        if G.degree(node) != 1:
            continue  # not a tip
        root = path[1] if len(path) > 1 else node
        attach_weight = G[src][root]["weight"] if G.has_edge(src, root) else 0.0
        lengths.append(dist[node] - attach_weight)
    return lengths


def cell_root_lengths(G: nx.Graph, cell_id: int) -> list[float]:
    """Root-based canaliculi for one cell (COUNT_MODE="roots").

    The attachment points are exactly the real nodes attach_lacunae linked
    to this cell's virtual node. They are clustered by single-linkage at
    ROOT_MERGE_DIST_PX, so one thick thread meeting the boundary over
    several nodes counts once. The "length" returned per root is the
    length of the edge leaving that attachment point, so the caller's
    existing count/total/mean reporting still means something -- but the
    COUNT is the quantity this mode exists for."""
    src = ("cell", cell_id)
    if not G.has_node(src):
        return []
    points = [n for n in G.neighbors(src) if not _is_cell_node(n)]
    if not points:
        return []

    # Single-linkage clustering by Euclidean distance between attachment
    # points. Done directly rather than via scipy so the rule stays visible.
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

    lengths = []
    for cluster in clusters:
        best = 0.0
        for node in cluster:
            for neighbour in G.neighbors(node):
                if _is_cell_node(neighbour):
                    continue
                best = max(best, float(G[node][neighbour]["weight"]))
        lengths.append(best)
    return lengths


def field_metrics(
    skeleton: np.ndarray,
    G: nx.Graph,
    lacuna_mask: np.ndarray,
    excluded: np.ndarray,
    n_lacunae: int,
    precision: int,
) -> dict:
    """Per-FIELD measurements (Phase 4a), independent of which cell owns
    which thread.

    This matters because per-lacuna attribution is the fragile part in 2D:
    only ~23% of skeleton length is graph-connected to any lacuna (Phase
    0b), so anything per-cell is computed from a quarter of the network.
    These numbers use all of it and do not depend on the assignment step at
    all, which makes them far less sensitive to fragmentation."""
    rows, cols = skeleton.shape
    analysed_area = float(rows * cols - lacuna_mask.sum() - (excluded & ~lacuna_mask).sum())
    skel_px = float(skeleton.sum())

    comp_labels = measure.label(skeleton, connectivity=2)
    sizes = np.bincount(comp_labels.ravel())[1:].astype(float)

    real = _real_subgraph(G)
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
        "units": "px",
        "note": (
            "Per-field metrics do not use the per-lacuna assignment, so "
            "fragmentation affects them far less than any per-cell number."
        ),
    }


def build_owner_pixel_map(
    shape: tuple[int, int],
    skel_obj,
    G: nx.Graph,
    edge_owner: dict,
    owner: dict,
) -> np.ndarray:
    """Paint every owned branch's real pixel path with its cell id, for
    reuse by save_verification (same drawing code as the euclidean
    method's nearest_id map). Each graph edge may cover several skan
    branches after simplification, and each node may have absorbed a few
    more when short edges were collapsed onto it -- both are painted, so
    the overlay still shows every pixel the cell owns."""
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


def canaliculi_measurements_graph(
    kept: list[tuple],
    skeleton: np.ndarray,
    dist_to_lacuna: np.ndarray,
    nearest_id: np.ndarray,
    precision: int,
    count_mode: str,
) -> tuple[list[dict], np.ndarray, nx.Graph, dict]:
    """Assignment is identical in both count modes (network connectivity,
    multi-source shortest path); only what gets COUNTED differs -- see
    COUNT_MODE. Also returns the final graph and its edge ownership, for
    the sanity report."""
    cell_ids = list(range(1, len(kept) + 1))

    G, skel_obj = build_network_graph(skeleton)
    clean_network_graph(G, dist_to_lacuna)
    attach_lacunae(G, dist_to_lacuna, nearest_id, cell_ids)
    owner, node_dist = assign_by_connectivity(G, cell_ids)
    edge_owner = assign_edges(G, owner, node_dist)

    measurements = []
    for lacuna_id, (_region, on_border) in enumerate(kept, start=1):
        if count_mode == "edge":
            lengths = cell_edge_lengths(G, edge_owner, lacuna_id)
        elif count_mode == "path":
            lengths = trace_cell_canaliculi(G, lacuna_id, owner)
        elif count_mode == "roots":
            lengths = cell_root_lengths(G, lacuna_id)
        else:
            raise ValueError(
                f"Unknown count mode: {count_mode!r} (expected 'edge', 'path' or 'roots')"
            )
        measurements.append(_measurement_row(lacuna_id, lengths, on_border, precision))

    owner_map = build_owner_pixel_map(skeleton.shape, skel_obj, G, edge_owner, owner)
    return measurements, owner_map, G, edge_owner


# --- Shared measurement row / summary ------------------------------------

def _measurement_row(lacuna_id: int, lengths: list[float], on_border: bool, precision: int) -> dict:
    """`lengths` is one length per canaliculus, whatever COUNT_MODE says a
    canaliculus is: one owned graph EDGE ("edge", default) or one
    cell-to-tip PATH ("path"). The three reported numbers are the same
    either way -- count, total length, mean length -- so "canaliculi_count"
    is the edge count and "mean_canaliculus_length_px" the mean edge length
    under "edge". The mode used is recorded in the summary sheet and JSON."""
    count = len(lengths)
    total_length = float(sum(lengths))
    mean_length = total_length / count if count else 0.0
    return {
        "lacuna_id": lacuna_id,
        "canaliculi_count": count,
        "total_length_px": round(total_length, precision),
        "mean_canaliculus_length_px": round(mean_length, precision),
        "on_border": bool(on_border),
        "units": "px",
    }


SUMMARY_METRICS = [
    ("canaliculi_count", "unitless"),
    ("total_length_px", "px"),
    ("mean_canaliculus_length_px", "px"),
]


def summarize_interior(measurements: list[dict], precision: int) -> dict:
    interior = [m for m in measurements if not m["on_border"]]
    n = len(interior)
    stats = {"interior_lacuna_count": n, "units": "px"}
    for field, _unit in SUMMARY_METRICS:
        values = np.array([m[field] for m in interior], dtype=float)
        if n == 0:
            mean = median = sd = None
        else:
            mean = round(float(values.mean()), precision)
            median = round(float(np.median(values)), precision)
            sd = round(float(values.std(ddof=1)), precision) if n >= 2 else None
        stats[field] = {"mean": mean, "median": median, "sd": sd}
    return stats


# --- Output ---------------------------------------------------------------

def image_output_dir(image_path: Path, output_suffix: str = "") -> Path:
    """Where this run's files go. A default run (empty suffix) writes to
    the image's own folder; a comparison run (any CLI override, so a
    non-empty suffix) writes one level down in COMPARISON_SUBDIR, keeping
    the default outputs alone at the top level."""
    safe_stem = image_path.stem.replace(" ", "_")
    image_dir = CANALICULI_DIR / safe_stem
    return image_dir / COMPARISON_SUBDIR if output_suffix else image_dir


def lacuna_colors(n_lacunae: int) -> dict[int, tuple[int, int, int]]:
    """One color per lacuna id (1..n_lacunae). Hues are evenly spaced for
    max contrast, then shuffled (seeded, so reruns are reproducible) so
    spatial neighbors don't get blend-prone adjacent hues."""
    import colorsys

    hues = [i / n_lacunae for i in range(n_lacunae)]
    random.Random(config.RANDOM_SEED).shuffle(hues)

    colors = {}
    for lacuna_id, hue in enumerate(hues, start=1):
        r, g, b = colorsys.hsv_to_rgb(hue, COLOR_SATURATION, COLOR_VALUE)
        colors[lacuna_id] = (int(r * 255), int(g * 255), int(b * 255))
    return colors


def save_verification(
    display_uint8: np.ndarray,
    lacuna_id_map: np.ndarray,
    skeleton: np.ndarray,
    owner_map: np.ndarray,
    lacuna_ids: list[int],
    colors: dict[int, tuple[int, int, int]],
    out_path: Path,
) -> None:
    """owner_map: int array, 0 = unowned, else the owning lacuna's id --
    either the euclidean nearest_id map or the graph method's
    build_owner_pixel_map output. Same drawing code either way."""
    vis = (display_uint8.astype(np.float32) * VIS_DIM_FACTOR).astype(np.uint8)
    for lacuna_id in lacuna_ids:
        color = colors[lacuna_id]
        boundary = segmentation.find_boundaries(lacuna_id_map == lacuna_id, mode="outer")
        vis[boundary] = color

        owned_skeleton = skeleton & (owner_map == lacuna_id)
        if owned_skeleton.any():
            owned_skeleton = morphology.dilation(owned_skeleton, morphology.disk(VIS_SKELETON_DILATION_PX))
        vis[owned_skeleton] = color

    out_path.parent.mkdir(parents=True, exist_ok=True)
    imsave(out_path, vis, check_contrast=False)


def save_xlsx(
    image_name: str,
    measurements: list[dict],
    stats: dict,
    method: str,
    count_mode: str,
    preprocess: str,
    field_stats: dict | None,
    out_path: Path,
) -> None:
    from openpyxl import Workbook

    wb = Workbook()

    summary = wb.active
    summary.title = "summary"
    summary.append(
        ["image", "lacuna_count", "interior_lacuna_count", "assignment_method", "count_mode", "preprocess_mode"]
    )
    summary.append(
        [image_name, len(measurements), stats["interior_lacuna_count"], method, count_mode, preprocess]
    )
    summary.append([])
    summary.append(
        [
            "count_mode='edge': one canaliculus = one graph edge (OCY-style); "
            "'path': one canaliculus = one cell-to-tip path (re-counts shared trunks)"
        ]
    )
    summary.append(["v1-raw / pre-validation -- stats below over interior (on_border=False) lacunae only"])
    summary.append(["metric", "mean", "median", "sd", "units", "n"])
    for field, unit in SUMMARY_METRICS:
        s = stats[field]
        summary.append([field, s["mean"], s["median"], s["sd"], unit, stats["interior_lacuna_count"]])

    # NOTE: named field_stats, not field -- the SUMMARY_METRICS loop above
    # binds a loop variable called `field`, which would shadow it.
    if field_stats:
        sheet = wb.create_sheet("field")
        sheet.append(["per-field metrics -- independent of the per-lacuna assignment"])
        sheet.append([
            "Only ~23% of skeleton length is graph-connected to any lacuna in these 2D",
            "sections, so per-cell numbers use a quarter of the network. These use all of it.",
        ])
        sheet.append([])
        sheet.append(["metric", "value", "units"])
        for key, value in field_stats.items():
            if key in ("units", "note"):
                continue
            unit = "px^-1" if key.endswith("_per_px") else ("px^-2" if key.endswith("_per_px2") else "px")
            if key.endswith("count"):
                unit = "unitless"
            sheet.append([key, value, unit])

    per_lacuna = wb.create_sheet("per_lacuna")
    fields = ["lacuna_id", "canaliculi_count", "total_length_px", "mean_canaliculus_length_px", "on_border", "units"]
    per_lacuna.append(fields)
    for m in measurements:
        per_lacuna.append([m[f] for f in fields])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)


def save_json(
    image_path: Path,
    measurements: list[dict],
    stats: dict,
    t_lo: float,
    t_hi: float,
    method: str,
    preprocess: str,
    count_mode: str,
    exclusion_info: dict,
    field: dict | None,
    threshold_mode: str,
    gap_bridging: bool,
    bridges: list,
    block_growth: bool,
    flagged: np.ndarray,
    out_path: Path,
) -> None:
    payload = {
        "status": "v1-raw",
        "note": (
            "Not yet validated against ground truth. "
            + (
                "Canaliculi are assigned by network connectivity "
                "(multi-source shortest path over the skeleton graph, "
                "OCY-style) with short noise spurs pruned first. "
                + (
                    "One canaliculus = one graph edge between two nodes "
                    "(count_mode='edge', OCY-style): canaliculi_count is "
                    "the number of edges the cell owns and "
                    "mean_canaliculus_length_px the mean edge length."
                    if count_mode == "edge"
                    else "One canaliculus = one cell-to-tip path "
                    "(count_mode='path'), which re-counts the shared trunk "
                    "of a branching thread once per tip."
                )
                if method == "graph"
                else "Canaliculus count/length come from a per-lacuna "
                "Euclidean-nearest skeleton assignment, an approximation "
                "in dense fields, with no spur pruning; always path-based, "
                "count_mode does not apply."
            )
            + " Border lacunae are kept (on_border=true) but excluded from summary stats."
        ),
        "image": str(image_path),
        "units": "px",
        "lacuna_count": len(measurements),
        "summary": stats,
        "exclusion": exclusion_info,
        "field": field,
        "parameters": {
            "assignment_method": method,
            "count_mode": count_mode if method == "graph" else "path (euclidean is always path-based)",
            "preprocess_mode": preprocess,
            "threshold_mode": threshold_mode,
            "hysteresis_low_fraction": HYSTERESIS_LOW_FRACTION if threshold_mode == "hysteresis" else None,
            "ridge_filter": RIDGE_FILTER if "ridge" in preprocess else None,
            "ridge_sigmas_px": list(RIDGE_SIGMAS_PX) if "ridge" in preprocess else None,
            "gap_bridging": gap_bridging,
            "n_bridges_added": len(bridges),
            "block_growth_in_flagged": block_growth,
            "flagged_area_px2": float(flagged.sum()),
            "tophat_radius_px": TOPHAT_RADIUS_PX if "tophat" in preprocess else None,
            "smooth_sigma_px": SMOOTH_SIGMA_PX if preprocess != "none" else None,
            "background_mode_subtract": BACKGROUND_MODE_SUBTRACT if "tophat" in preprocess else None,
            "pixel_size_um": config.PIXEL_SIZE_UM,
            "lacuna_segmentation": "segment_lacunae_v2 (multi-Otsu 3-class + watershed; see that module)",
            "total_signal_threshold_t_lo": t_lo,
            "lacuna_top_class_threshold_t_hi": t_hi,
            "lacuna_dilation_px": LACUNA_DILATION_PX,
            "min_thread_object_px2": MIN_THREAD_OBJECT_PX2,
            "lacuna_attach_gap_px": LACUNA_ATTACH_GAP_PX,
            "prune_spur_len_px": PRUNE_SPUR_LEN_PX,
            "min_internal_edge_len_px": MIN_INTERNAL_EDGE_LEN_PX,
            "graph_cleanup_max_iter": GRAPH_CLEANUP_MAX_ITER,
            "max_root_gap_px": MAX_ROOT_GAP_PX,
        },
        "lacunae": measurements,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)


# --- Sanity report (pooled across a whole run) ---------------------------

# Cumulative edge-length bins (px) for the report, the same idea as OCY's
# n.dist_edge in OCY_get_network_params.m (which uses 0.5 um bins at a
# known scale). PIXEL_SIZE_UM is None here, so these are pixel bins and
# nothing is compared to a published micron figure.
SANITY_EDGE_LEN_BINS_PX = (5, 10, 20, 40, 80, 160)

# Literature anchors. A real canalicular network is tree-like: branch
# points are overwhelmingly 3-way (one thread splitting into two), and the
# canaliculi between them are mostly short, i.e. the length distribution is
# strongly right-skewed. These are shape checks, not absolute ones -- with
# no um/px calibration an absolute length cannot be compared to anything
# published.
SANITY_MIN_DEG3_FRACTION_OF_JUNCTIONS = 0.8
SANITY_MIN_SKEW_RATIO = 1.2  # mean / median of edge length
# Fraction of real nodes that may be degree-1 (thread ends) before the
# skeleton counts as fragmented rather than connected. In a connected
# tree-like network, endpoints are a minority of nodes.
SANITY_MAX_DEG1_FRACTION = 0.5


def _percentiles(values: np.ndarray, qs=(10, 25, 50, 75, 90, 99)) -> str:
    return "  ".join(f"p{q}={np.percentile(values, q):7.2f}" for q in qs)


def _real_subgraph(G: nx.Graph) -> nx.Graph:
    """The skeleton graph without the virtual ("cell", id) nodes, so a
    node's degree counts canaliculi and not its lacuna attachment."""
    return G.subgraph([n for n in G.nodes() if not _is_cell_node(n)])


def sanity_report(runs: list[dict]) -> None:
    """Pooled edge-length and node-degree distributions across every image
    in this run, checked against the literature shape of a real LCN.

    Modelled on what OCY reports in OCY_get_network_params.m: n.dist_edge
    (cumulative edge-length distribution over the `link` structs), n.hbz
    (cumulative node degree over non-cell non-endpoint nodes) and n.t_nodes
    (tree-like nodes: degree 3 with clustering coefficient 0). Everything
    stays in pixels.

    Two populations are reported separately, because they answer different
    questions: ALL edges/nodes in the skeleton graph, and only those the
    per-cell numbers are actually computed from (edges with an owning
    cell). A skeleton fragment not graph-connected to any lacuna inflates
    the first and never touches the second."""
    runs = [r for r in runs if r.get("graph") is not None]
    if not runs:
        print("\n[sanity] no graph-method runs to report on (euclidean method has no network graph).")
        return

    all_lengths: list[float] = []
    owned_lengths: list[float] = []
    all_degrees: list[int] = []
    owned_degrees: list[int] = []
    tree_nodes = junction_nodes = 0

    print("\n" + "=" * 78)
    print("SANITY REPORT -- pooled over", len(runs), "image(s). v1-raw / pre-validation, PIXEL units.")
    print("=" * 78)
    print(f'{"image":24s} {"nodes":>7s} {"edges":>7s} {"owned_edges":>12s} {"components":>11s}')

    for run in runs:
        G = run["graph"]
        real = _real_subgraph(G)
        edge_owner = run["edge_owner"] or {}

        for u, v, w in real.edges(data="weight"):
            all_lengths.append(float(w))
            if frozenset((u, v)) in edge_owner:
                owned_lengths.append(float(w))

        owned_nodes = {n for edge in edge_owner for n in tuple(edge)}
        clustering = nx.clustering(real)
        for node in real.nodes():
            degree = real.degree(node)
            all_degrees.append(degree)
            if node in owned_nodes:
                owned_degrees.append(degree)
            if degree >= 3:
                junction_nodes += 1
                if degree == 3 and clustering[node] == 0:
                    tree_nodes += 1  # OCY's n.t_nodes criterion

        print(
            f'{run["image"][:24]:24s} {real.number_of_nodes():7d} {real.number_of_edges():7d} '
            f'{len(edge_owner):12d} {nx.number_connected_components(real):11d}'
        )

    # --- Phase 0(b) fragmentation + Phase 4a per-field metrics -----------
    fields = [r["field"] for r in runs if r.get("field")]
    if fields:
        print()
        print("-- Fragmentation and per-field metrics (per image)")
        print(
            f'{"image":24s} {"skel_px":>8s} {"comps":>6s} {"comp/10k":>9s} {"len_dens":>10s} '
            f'{"junc_dens":>10s} {"lac/area":>10s} {"med_comp":>9s}'
        )
        for run in runs:
            f = run.get("field")
            if not f:
                continue
            skel_px = f["total_skeleton_length_px"]
            comps = f["skeleton_component_count"]
            print(
                f'{run["image"][:24]:24s} {skel_px:8.0f} {comps:6d} '
                f'{(10000.0 * comps / skel_px if skel_px else 0):9.1f} '
                f'{f["canalicular_length_density_per_px"]:10.5f} '
                f'{f["junction_density_per_px2"]:10.6f} {f["lacunae_per_px2"]:10.7f} '
                f'{f["median_component_length_px"]:9.1f}'
            )
        print(
            "   Per-field metrics do not use the per-lacuna assignment. Only ~23% of skeleton "
            "length is graph-connected to a lacuna in these 2D sections, so per-cell numbers "
            "are computed from a quarter of the network and these are not."
        )

    for label, lengths in (("ALL edges", all_lengths), ("CELL-OWNED edges", owned_lengths)):
        arr = np.array(lengths, dtype=float)
        if arr.size == 0:
            print(f"\n-- Edge length ({label}): none")
            continue
        print(f"\n-- Edge length distribution, {label} (px), n={arr.size}")
        print(f"   mean={arr.mean():7.2f}  {_percentiles(arr)}  max={arr.max():7.2f}")
        print("   cumulative (OCY n.dist_edge style):", end="")
        for b in SANITY_EDGE_LEN_BINS_PX:
            print(f"  >={b}px: {100 * (arr >= b).mean():5.1f}%", end="")
        print()

    for label, degrees in (("ALL nodes", all_degrees), ("CELL-OWNED nodes", owned_degrees)):
        arr = np.array(degrees, dtype=int)
        if arr.size == 0:
            print(f"\n-- Node degree ({label}): none")
            continue
        print(f"\n-- Node degree distribution, {label}, n={arr.size}")
        for d in (1, 2, 3, 4):
            print(f"   deg {d}{'+' if d == 4 else ' '}: {int((arr >= d).sum() if d == 4 else (arr == d).sum()):7d}"
                  f"  ({100 * ((arr >= d).mean() if d == 4 else (arr == d).mean()):5.1f}%)")
        junctions = arr[arr >= 3]
        if junctions.size:
            print(f"   mean degree over junctions (deg>=3, OCY n.mean_deg): {junctions.mean():.3f}")

    # --- verdicts against the literature shape ---------------------------
    print("\n-- Anchors (literature shape of a real LCN; shape checks only, no um/px scale)")
    arr = np.array(owned_lengths or all_lengths, dtype=float)
    median, mean = float(np.median(arr)), float(arr.mean())
    skew_ratio = mean / median if median else float("inf")
    _verdict(
        skew_ratio >= SANITY_MIN_SKEW_RATIO,
        "most canaliculi short (right-skewed edge lengths)",
        f"mean/median = {mean:.1f}/{median:.1f} = {skew_ratio:.2f} "
        f"(want >= {SANITY_MIN_SKEW_RATIO})",
    )

    deg = np.array(all_degrees, dtype=int)
    junctions = deg[deg >= 3]
    deg3_fraction = float((junctions == 3).mean()) if junctions.size else 0.0
    _verdict(
        deg3_fraction >= SANITY_MIN_DEG3_FRACTION_OF_JUNCTIONS,
        "branch points are 3-way (tree-like)",
        f"{100 * deg3_fraction:.1f}% of junctions are degree-3 "
        f"(want >= {100 * SANITY_MIN_DEG3_FRACTION_OF_JUNCTIONS:.0f}%); "
        f"{tree_nodes}/{junction_nodes} also have clustering 0 (OCY n.t_nodes)",
    )

    deg1_fraction = float((deg == 1).mean()) if deg.size else 0.0
    _verdict(
        deg1_fraction <= SANITY_MAX_DEG1_FRACTION,
        "network is connected, not fragmented",
        f"{100 * deg1_fraction:.1f}% of all nodes are degree-1 thread ends "
        f"(want <= {100 * SANITY_MAX_DEG1_FRACTION:.0f}%)",
    )
    print("=" * 78)


def _verdict(ok: bool, name: str, detail: str) -> None:
    print(f"   [{'OK  ' if ok else 'FLAG'}] {name}\n          {detail}")


def print_summary(stats: dict) -> None:
    for field, unit in SUMMARY_METRICS:
        s = stats[field]
        mean = "n/a" if s["mean"] is None else f"{s['mean']:.2f}"
        median = "n/a" if s["median"] is None else f"{s['median']:.2f}"
        sd = "n/a" if s["sd"] is None else f"{s['sd']:.2f}"
        print(f"    {field:28s} mean={mean:>10s}  median={median:>10s}  sd={sd:>10s}  ({unit})")


def save_mask_pngs(candidate: np.ndarray, skeleton: np.ndarray, out_dir: Path, suffix: str) -> None:
    """The raw binary network mask and its skeleton, unannotated -- what
    the per-cell tracing is actually built on."""
    out_dir.mkdir(parents=True, exist_ok=True)
    imsave(out_dir / f"canaliculi_mask{suffix}.png", (candidate * 255).astype(np.uint8), check_contrast=False)
    imsave(out_dir / f"skeleton{suffix}.png", (skeleton * 255).astype(np.uint8), check_contrast=False)


def process(
    image_path: Path,
    method: str | None = None,
    output_suffix: str = "",
    preprocess: str | None = None,
    count_mode: str | None = None,
    exclusion: str | None = None,
    threshold_mode: str | None = None,
    gap_bridging: bool | None = None,
    lacuna_source: str | None = None,
    block_growth: bool | None = None,
) -> dict:
    method = method or ASSIGNMENT_METHOD
    preprocess = preprocess or PREPROCESS_MODE
    count_mode = count_mode or COUNT_MODE
    exclusion = exclusion or EXCLUSION_MODE
    threshold_mode = threshold_mode or THRESHOLD_MODE
    gap_bridging = GAP_BRIDGING if gap_bridging is None else gap_bridging
    lacuna_source = lacuna_source or LACUNA_SOURCE
    block_growth = BLOCK_GROWTH_IN_FLAGGED if block_growth is None else block_growth

    display, channel = load_channel(image_path)
    if lacuna_source == "v2":
        _display2, labels, kept, t_hi = seg2.segment_image(image_path)
    elif lacuna_source == "v3_candidate":
        import segment_lacunae_v3_candidate as seg3

        _display2, labels, kept, t_hi = seg3.segment_image(image_path)
    elif lacuna_source == "hybrid":
        import segment_lacunae_hybrid as seghy

        _display2, labels, kept, t_hi = seghy.segment_image(image_path)
    else:
        raise ValueError(
            f"Unknown lacuna source: {lacuna_source!r} "
            "(expected 'v2', 'v3_candidate' or 'hybrid')"
        )

    # Optional post-merge of lacuna pieces split apart by a thresholding
    # break. Off by default; applies to whatever LACUNA_SOURCE produced.
    if merge_adjacent_lacunae.MERGE_ADJACENT_PAIRS:
        labels, kept, _pairs = merge_adjacent_lacunae.apply_merges(labels, kept)

    lacuna_mask, lacuna_id_map = build_lacuna_maps(labels, kept)
    # The Phase 1 shape gate, BEFORE the safety margin. Used only to stop
    # hysteresis and bridging ADDING connections along a vascular canal;
    # nothing is removed. Independent of EXCLUSION_MODE.
    flagged = (
        exclusion_mask.flagged_structures(channel)[0]
        if block_growth
        else np.zeros(channel.shape, dtype=bool)
    )
    candidate, t_lo = canaliculi_candidate_mask(
        channel, lacuna_mask, preprocess, threshold_mode, flagged if block_growth else None
    )
    # Non-LCN structures are dropped from the candidate mask BEFORE
    # skeletonizing, so nothing downstream ever sees them as network.
    excluded, exclusion_info = exclusion_mask.build_exclusion(image_path, channel, labels, exclusion)
    if excluded.any():
        candidate = candidate & ~excluded
    skeleton = morphology.skeletonize(candidate)

    bridges: list = []
    if gap_bridging:
        preprocessed = preprocess_channel(channel, preprocess)
        # A bridge may not start in, end in, or cross a lacuna body, an
        # excluded region, or (with BLOCK_GROWTH_IN_FLAGGED) a flagged
        # non-LCN structure.
        forbidden = lacuna_mask | excluded | flagged
        bridges = gap_bridging_mod.find_bridges(skeleton, preprocessed, t_lo, forbidden)
        if bridges:
            candidate = gap_bridging_mod.apply_bridges(candidate, bridges)
            skeleton = morphology.skeletonize(candidate)
    dist_to_lacuna, nearest_id = nearest_lacuna_map(lacuna_id_map)

    graph = edge_owner = None
    if method == "graph":
        measurements, owner_map, graph, edge_owner = canaliculi_measurements_graph(
            kept, skeleton, dist_to_lacuna, nearest_id,
            precision=config.CSV_FLOAT_PRECISION, count_mode=count_mode,
        )
    elif method == "euclidean":
        measurements = canaliculi_measurements_euclidean(
            kept, skeleton, nearest_id, dist_to_lacuna, precision=config.CSV_FLOAT_PRECISION
        )
        owner_map = nearest_id
    else:
        raise ValueError(f"Unknown method: {method!r} (expected 'graph' or 'euclidean')")

    stats = summarize_interior(measurements, precision=config.CSV_FLOAT_PRECISION)
    field = (
        field_metrics(
            skeleton, graph, lacuna_mask, excluded, len(kept),
            precision=config.CSV_FLOAT_PRECISION,
        )
        if graph is not None
        else None
    )

    out_dir = image_output_dir(image_path, output_suffix)
    if SAVE_MASK_PNG:
        save_mask_pngs(candidate, skeleton, out_dir, output_suffix)
    if exclusion != "none":
        exclusion_mask.save_exclusion_overlay(
            display, excluded, exclusion_mask.protected_region(labels),
            out_dir / f"exclusion{output_suffix}.png",
        )
    if gap_bridging:
        out_dir.mkdir(parents=True, exist_ok=True)
        imsave(
            out_dir / f"bridges{output_suffix}.png",
            gap_bridging_mod.bridge_overlay(display, skeleton, bridges),
            check_contrast=False,
        )
    colors = lacuna_colors(len(kept))
    all_ids = list(range(1, len(kept) + 1))
    save_verification(
        display, lacuna_id_map, skeleton, owner_map, all_ids, colors, out_dir / f"verification{output_suffix}.png"
    )
    save_xlsx(
        image_path.name, measurements, stats, method, count_mode, preprocess, field,
        out_dir / f"measurements{output_suffix}.xlsx",
    )
    save_json(
        image_path, measurements, stats, t_lo, t_hi, method, preprocess, count_mode,
        exclusion_info, field, threshold_mode, gap_bridging, bridges, block_growth, flagged,
        out_dir / f"measurements{output_suffix}.json",
    )

    mean_count = stats["canaliculi_count"]["mean"]
    mean_length = stats["mean_canaliculus_length_px"]["mean"]
    mean_count_s = "n/a" if mean_count is None else f"{mean_count:.2f}"
    mean_length_s = "n/a" if mean_length is None else f"{mean_length:.2f}"
    mode_tag = count_mode if method == "graph" else "path"
    if exclusion != "none":
        mode_tag += f"/excl-{exclusion}"
    if threshold_mode != "multiotsu_low":
        mode_tag += f"/{threshold_mode}"
    if gap_bridging:
        mode_tag += f"/bridged({len(bridges)})"
    print(
        f"{image_path.name} [{method}/{preprocess}/{mode_tag}]: lacunae={len(kept)}  "
        f"mean_canaliculi_per_cell={mean_count_s}  mean_canaliculus_length_px={mean_length_s}  -> {out_dir}"
    )
    print_summary(stats)
    return {
        "stats": stats,
        "graph": graph,
        "edge_owner": edge_owner,
        "image": image_path.name,
        "field": field,
        "skeleton": skeleton,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="v1-RAW experimental per-lacuna canaliculi extraction (pre-validation)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--image", type=Path, help="Path to a single .tif image.")
    group.add_argument("--dir", type=Path, help="Directory of .tif images to process.")
    parser.add_argument(
        "--method",
        choices=["graph", "euclidean"],
        default=None,
        help="Override ASSIGNMENT_METHOD for this run; suffixes output filenames with _<method> "
        "so a comparison run never overwrites the default-method outputs.",
    )
    parser.add_argument(
        "--preprocess",
        choices=["tophat", "ridge", "tophat+ridge", "none"],
        default=None,
        help="Override PREPROCESS_MODE for this run; suffixes output filenames with _pre-<mode> "
        "so a comparison run never overwrites the default outputs.",
    )
    parser.add_argument(
        "--count-mode",
        choices=["edge", "path", "roots"],
        default=None,
        help="Override COUNT_MODE for this run ('edge' = one canaliculus per graph edge, OCY-style; "
        "'path' = one per cell-to-tip path). Graph method only; suffixes output filenames with "
        "_count-<mode> so a comparison run never overwrites the default outputs.",
    )
    parser.add_argument(
        "--exclusion",
        choices=list(exclusion_mask.VALID_MODES),
        default=None,
        help="Override EXCLUSION_MODE for this run; suffixes output filenames with _excl-<mode> "
        "so a comparison run never overwrites the default outputs.",
    )
    parser.add_argument(
        "--threshold-mode",
        choices=["multiotsu_low", "hysteresis"],
        default=None,
        help="Override THRESHOLD_MODE for this run; suffixes output filenames with _thr-<mode>.",
    )
    # GAP_BRIDGING defaults to True, so --gap-bridging alone could never turn
    # it off and the pre-2026-09-28 path was unreachable from the command
    # line. --no-gap-bridging is the way back to it.
    bridging = parser.add_mutually_exclusive_group()
    bridging.add_argument(
        "--gap-bridging",
        action="store_true",
        default=None,
        help="Force gap bridging on for this run (it is already the default); "
        "suffixes output filenames with _bridged.",
    )
    bridging.add_argument(
        "--no-gap-bridging",
        action="store_true",
        help="Disable gap bridging for this run (GAP_BRIDGING override); "
        "suffixes output filenames with _nobridge. With --threshold-mode multiotsu_low "
        "this reproduces the pre-2026-09-28 default.",
    )
    parser.add_argument(
        "--hysteresis-low",
        type=float,
        default=None,
        help="Override HYSTERESIS_LOW_FRACTION for this run (only meaningful with "
        "--threshold-mode hysteresis); suffixes output filenames with _hl<value>.",
    )
    parser.add_argument(
        "--lacuna-source",
        choices=["v2", "v3_candidate", "hybrid"],
        default=None,
        help="Override LACUNA_SOURCE for this run; suffixes output filenames with _lac-<source>.",
    )
    parser.add_argument(
        "--merge-adjacent",
        action="store_true",
        help="Merge kept lacuna pieces separated by a thresholding break "
        "(MERGE_ADJACENT_PAIRS override); suffixes output filenames with _merged.",
    )
    parser.add_argument(
        "--no-block-growth",
        action="store_true",
        help="Disable BLOCK_GROWTH_IN_FLAGGED for this run (lets hysteresis and bridging grow "
        "along flagged non-LCN structures); suffixes output filenames with _nogrowthblock.",
    )
    parser.add_argument(
        "--no-sanity",
        action="store_true",
        help="Skip the pooled edge-length / node-degree sanity report printed after the run.",
    )
    args = parser.parse_args()

    suffix = ""
    if args.method:
        suffix += f"_{args.method}"
    if args.preprocess:
        suffix += f"_pre-{args.preprocess}"
    if args.count_mode:
        suffix += f"_count-{args.count_mode}"
    if args.exclusion:
        suffix += f"_excl-{args.exclusion}"
    if args.threshold_mode:
        suffix += f"_thr-{args.threshold_mode}"
    if args.gap_bridging:
        suffix += "_bridged"
    if args.no_gap_bridging:
        suffix += "_nobridge"
    if args.lacuna_source:
        suffix += f"_lac-{args.lacuna_source}"
    if args.no_block_growth:
        suffix += "_nogrowthblock"
    if args.merge_adjacent:
        suffix += "_merged"
        merge_adjacent_lacunae.MERGE_ADJACENT_PAIRS = True
    if args.hysteresis_low is not None:
        suffix += f"_hl{args.hysteresis_low}"
        globals()["HYSTERESIS_LOW_FRACTION"] = args.hysteresis_low

    if args.image:
        if not args.image.is_file():
            raise FileNotFoundError(f"No such file: {args.image}")
        paths = [args.image]
    else:
        if not args.dir.is_dir():
            raise NotADirectoryError(f"No such directory: {args.dir}")
        paths = sorted(args.dir.glob("*.tif"))

    runs = [
        process(
            image_path,
            method=args.method,
            output_suffix=suffix,
            preprocess=args.preprocess,
            count_mode=args.count_mode,
            exclusion=args.exclusion,
            threshold_mode=args.threshold_mode,
            gap_bridging=False if args.no_gap_bridging else args.gap_bridging,
            lacuna_source=args.lacuna_source,
            block_growth=False if args.no_block_growth else None,
        )
        for image_path in paths
    ]
    if not args.no_sanity:
        sanity_report(runs)


if __name__ == "__main__":
    main()
