"""Exclusion masks for non-LCN structures (Phase 1). v1-raw, pre-validation.

Vascular canals, canal edges and section boundaries are bright, broad
structures that are not canalicular network. This module builds a boolean
mask of pixels to drop from the canaliculi candidate mask before
skeletonization. canaliculi_v1 calls it behind EXCLUSION_MODE, which
defaults to "none" -- nothing here changes the pipeline's current output
unless a run explicitly asks for it.

Modes:
    "none"   current behaviour, no exclusion (default)
    "auto"   automatic candidate exclusion, see auto_exclusion()
    "manual" a per-image mask drawn by hand, see manual_exclusion()
    "both"   union of auto and manual

WHY "auto" WORKS ON THE RAW CHANNEL, NOT ON SKELETON GEOMETRY
The obvious rule -- flag skeleton components that are long, straight and
wide -- was tested in Phase 0(d) and does not work on this data. Pooled
over 6471 components from all 8 WT images it flagged nothing, because
canaliculi_v1's top-hat (disk radius TOPHAT_RADIUS_PX) deletes anything
broader than 2R+1 px, so a broad structure never reaches the canaliculi
mask as a broad object in the first place. The long skeleton components
that do exist (1179-2476 px) are branched mesh, straightness 0.13-0.30,
not lines. The structure the user pointed out in 542_z06 survives into the
mask only as ~9 fragments, the largest 189 px spanning 14% of the image
height -- indistinguishable from canaliculi by length, straightness or
width. In the RAW channel, before the top-hat, the same structure is one
object of 27496 px^2 spanning 63% of the image height. That is where it is
detectable, so that is where this module looks.

Relation to OCY (Kollmannsberger et al., New J. Phys. 2017): OCY has no
equivalent step. OCY_thr_stack.m top-hats and thresholds, and
OCY_get_cells.m separates cells from network by distance transform, but
nothing in that pipeline removes a vascular canal -- their 3D stacks are
taken within a chosen volume of bone and the question does not arise the
same way. This is a departure, made because our fields are single 2D
sections chosen by the microscopist and routinely contain canal edges.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from skimage import measure, morphology, segmentation
from skimage.io import imread, imsave

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import segment_lacunae_v2 as seg2  # noqa: E402


# --- Parameters -----------------------------------------------------------

# Radius (px) of the disk that opens the RAW channel to find broad objects.
# An opening with this disk deletes anything narrower than 2R+1 px across.
# Measured canalicular widths (Phase 0, post-top-hat, pooled over all 8 WT
# images) are p50 ~6.0 and p99 ~8.5 px, so R=8 (diameter 17) erases every
# canaliculus while leaving lacunae and larger structures intact. Confirmed
# in Phase 0(e): at this radius the 542_z06 structure appears as a single
# 27496 px^2 object.
BROAD_OPENING_RADIUS_PX = 8

# Shape gate. A broad object is a candidate for exclusion only if it clears
# BOTH of these. Requiring both is deliberate redundancy: they are derived
# from different properties and, on the 8 WT images, they select exactly
# the same 5 objects.
#
# Provenance (pooled over all 98 v2-kept lacunae AND all 103 pre-filter
# objects of lacuna scale, i.e. kept OR rejected, across the 8 WT images):
#     largest lacuna-scale object: major axis 210.6 px
#     largest lacuna-scale object: spans 0.23 of an image dimension
# The broad objects that clear the gate span 0.58-0.80 of a dimension with
# major axes of 646-920 px. Sorted by span, the observed values run
# 0.80, 0.73, 0.63, 0.62, 0.58, then 0.37, 0.35, 0.34, ... -- a clean gap
# between 0.58 and 0.37, with every lacuna at or below 0.23. 0.45 sits in
# that gap at roughly twice the largest span any lacuna has ever reached
# here. The major-axis cutoff is 2x the largest lacuna major axis; the
# next-largest broad objects are 311-349 px, well clear of it.
#
# This is the criterion the brief requires lacunae and lacuna halos never
# to meet. It is derived from WT images only; the gap is wide, but it has
# not been checked against Hyp or Hyp;Enpp1 fields and must be re-checked
# before those are processed.
EXCLUSION_MIN_SPAN_FRACTION = 0.45
EXCLUSION_MIN_MAJOR_AXIS_PX = 420.0

# --- Lacuna safety margin -------------------------------------------------
# No pixel within this distance of a lacuna-scale v2 object is ever
# excluded, whether v2 kept that object or rejected it.
#
# WHY THIS EXISTS. In Hyp mice, periosteocytic lesions are broad bright
# regions surrounding lacunae, and they are precisely what this thesis
# measures. A rule that removes "broad bright regions" would preferentially
# delete them, would do so only in the mutant genotypes, and would
# therefore bias the genotype comparison in the direction of the
# hypothesis. That failure mode is worse than leaving a vascular canal in,
# so the margin is absolute: it wins over the exclusion rule everywhere,
# even where that leaves an obvious canal untouched. Rejected v2 objects
# are protected too, because rejection is a shape judgement (the 542_z06
# object at (230,300) was dropped on solidity 0.45) and says nothing about
# whether a lesion surrounds it.
#
# VALUE PROVENANCE: 50 px is an INITIAL VALUE, NOT YET TUNED. It cannot be
# derived from the WT images, which by definition have no periosteocytic
# lesions to measure; the honest derivation needs Hyp fields. What is
# measured is its cost, on 542_z06, protecting lacuna-scale objects:
#     margin   0 px -> 4.0% of image protected, 82.1% of structure excludable
#     margin  25 px -> 18.7% protected, 30.8% excludable
#     margin  50 px -> 37.6% protected, 14.1% excludable
#     margin  75 px -> 57.2% protected,  5.0% excludable
#     margin 100 px -> 74.6% protected,  0.2% excludable
# 50 px keeps roughly a sixth of the flagged structure excludable while
# protecting a band about half a median lacuna length (median lacuna major
# axis 89 px) around every lacuna. Raising it makes "auto" nearly a no-op;
# that is the correct direction to err, and the per-image report prints the
# protected fraction so the cost stays visible.
LACUNA_SAFETY_MARGIN_PX = 50

# Only lacuna-SCALE v2 objects get the safety margin. v2's pre-filter label
# image also contains hundreds of sub-lacuna specks (341 of 361 objects in
# 542_z06 are below TEST_MIN_AREA_PX2), which are canalicular mesh caught
# by the top-class cut, not lacunae or lesions. Protecting a 50 px margin
# around those as well protects 89.4% of the image and makes any exclusion
# impossible. The cutoff is v2's own lacuna-scale threshold, so this module
# introduces no new size judgement of its own.
PROTECT_MIN_AREA_PX2 = seg2.TEST_MIN_AREA_PX2

# Margin (px) the final exclusion region is dilated by, to catch the
# structure's own boundary.
#
# PROVENANCE, AND A CORRECTION. Phase 0(d) reported that the structure's
# "thin edges survive the top-hat and reach the canaliculi mask", and the
# brief asked for a dilation large enough to cover them. Measured directly,
# that inference does not hold. Canaliculi-mask density in rings outward
# from the 542_z06 structure, against the density far (>120 px) from it:
#     0-4 px 0.70x   4-8 px 0.96x   8-12 px 1.09x   12-16 px 1.01x
#     16-20 px 1.01x  20-24 px 0.92x  24-28 px 1.02x
# i.e. at baseline from about 4 px outward, with no elevated edge response
# to cover. Only the immediate boundary ring differs, and it is BELOW
# baseline. So the evidence supports 4 px, not the larger margin the brief
# anticipated, and a larger value would delete ordinary canaliculi.
EXCLUSION_DILATION_PX = 4

# Where manual masks are read from: data/exclusion_masks/<image_stem>.png,
# white (non-zero) = exclude. See the README for how to draw one in Fiji.
MANUAL_MASK_DIR = config.DATA_DIR / "exclusion_masks"

VALID_MODES = ("none", "auto", "manual", "both")


# --- Automatic exclusion --------------------------------------------------

def broad_objects(channel: np.ndarray) -> tuple[np.ndarray, list]:
    """Label broad bright objects in the RAW channel: open with a disk that
    no canaliculus can contain, then threshold the opened image on its own
    histogram (per-image, no global constant -- the same adaptive idea the
    rest of the pipeline uses). Returns (labels, regionprops)."""
    from canaliculi_v1 import total_signal_mask

    opened = morphology.opening(channel, morphology.disk(BROAD_OPENING_RADIUS_PX))
    mask, _threshold = total_signal_mask(opened)
    labels = measure.label(mask, connectivity=2)
    return labels, measure.regionprops(labels)


def protected_region(v2_labels: np.ndarray) -> np.ndarray:
    """Pixels the exclusion rule may never touch: every lacuna-scale object
    in v2's PRE-FILTER label image, kept or rejected, dilated by
    LACUNA_SAFETY_MARGIN_PX. See that constant for why."""
    keep_ids = [r.label for r in measure.regionprops(v2_labels) if r.area >= PROTECT_MIN_AREA_PX2]
    lacuna_scale = np.isin(v2_labels, keep_ids) if keep_ids else np.zeros(v2_labels.shape, dtype=bool)
    if LACUNA_SAFETY_MARGIN_PX > 0 and lacuna_scale.any():
        return morphology.dilation(lacuna_scale, morphology.disk(LACUNA_SAFETY_MARGIN_PX))
    return lacuna_scale


def auto_exclusion(channel: np.ndarray, v2_labels: np.ndarray) -> tuple[np.ndarray, dict]:
    """Broad bright structures in the raw channel that are far larger and
    more elongated than any lacuna, minus the lacuna safety margin."""
    rows, cols = channel.shape
    labels, regions = broad_objects(channel)

    flagged = np.zeros(channel.shape, dtype=bool)
    objects = []
    for region in regions:
        min_row, min_col, max_row, max_col = region.bbox
        span = max((max_row - min_row) / rows, (max_col - min_col) / cols)
        major = float(region.axis_major_length)
        if span < EXCLUSION_MIN_SPAN_FRACTION or major < EXCLUSION_MIN_MAJOR_AXIS_PX:
            continue
        flagged |= labels == region.label
        minor = float(region.axis_minor_length)
        objects.append(
            {
                "area_px2": float(region.area),
                "major_axis_px": major,
                "aspect": (major / minor) if minor > 0 else float("inf"),
                "span_fraction": float(span),
                "centroid_col": float(region.centroid[1]),
                "centroid_row": float(region.centroid[0]),
                "bbox": [int(min_row), int(min_col), int(max_row), int(max_col)],
            }
        )

    if flagged.any() and EXCLUSION_DILATION_PX > 0:
        flagged = morphology.dilation(flagged, morphology.disk(EXCLUSION_DILATION_PX))

    protected = protected_region(v2_labels)
    exclusion = flagged & ~protected
    return exclusion, {
        "objects": objects,
        "flagged_area_px2": float(flagged.sum()),
        "protected_fraction": float(protected.mean()),
        "suppressed_by_margin_px2": float((flagged & protected).sum()),
    }


# --- Manual exclusion -----------------------------------------------------

def manual_mask_path(image_path: Path) -> Path | None:
    """data/exclusion_masks/<stem>.png, trying the image's own stem first
    and then the underscore-safe form used for output folder names."""
    for stem in (image_path.stem, image_path.stem.replace(" ", "_")):
        candidate = MANUAL_MASK_DIR / f"{stem}.png"
        if candidate.is_file():
            return candidate
    return None


def manual_exclusion(image_path: Path, shape: tuple[int, int]) -> tuple[np.ndarray, dict]:
    """Read a hand-drawn mask, white = exclude. Missing file is not an
    error -- it means nothing was drawn for this image -- but a mask whose
    size does not match the image is, because silently resampling someone's
    hand-drawn ROI would move the boundary they chose."""
    path = manual_mask_path(image_path)
    if path is None:
        return np.zeros(shape, dtype=bool), {"manual_mask": None}

    raw = imread(path)
    if raw.ndim == 3:
        raw = raw[..., :3].max(axis=-1)
    if raw.shape != shape:
        raise ValueError(
            f"Manual exclusion mask {path} is {raw.shape}, but {image_path.name} is {shape}. "
            "Masks must be drawn at the image's own pixel size; resampling would move the boundary."
        )
    return raw > 0, {"manual_mask": str(path)}


# --- Entry point ----------------------------------------------------------

def build_exclusion(
    image_path: Path,
    channel: np.ndarray,
    v2_labels: np.ndarray,
    mode: str,
) -> tuple[np.ndarray, dict]:
    """Boolean exclusion mask plus an audit record of how it was built."""
    if mode not in VALID_MODES:
        raise ValueError(f"Unknown exclusion mode: {mode!r} (expected one of {VALID_MODES})")

    shape = channel.shape
    exclusion = np.zeros(shape, dtype=bool)
    info: dict = {"mode": mode, "objects": [], "manual_mask": None}

    if mode in ("auto", "both"):
        auto, auto_info = auto_exclusion(channel, v2_labels)
        exclusion |= auto
        info.update(auto_info)

    if mode in ("manual", "both"):
        manual, manual_info = manual_exclusion(image_path, shape)
        # The safety margin governs hand-drawn masks too. A manual mask is
        # drawn blind to genotype (see README) but is still a human
        # decision about which bright regions are not network, which is
        # exactly the judgement that could bias the lesion measurement.
        manual = manual & ~protected_region(v2_labels)
        exclusion |= manual
        info.update(manual_info)

    protected = protected_region(v2_labels)
    info["excluded_area_px2"] = float(exclusion.sum())
    info["excluded_fraction"] = float(exclusion.mean())
    # Must be 0. Reported rather than asserted so a violation shows up in
    # the audit trail instead of only crashing the run.
    info["excluded_inside_safety_margin_px2"] = float((exclusion & protected).sum())
    info["lacuna_safety_margin_px"] = LACUNA_SAFETY_MARGIN_PX
    return exclusion, info


def save_exclusion_overlay(
    display_uint8: np.ndarray,
    exclusion: np.ndarray,
    protected: np.ndarray,
    out_path: Path,
) -> None:
    """Every exclusion drawn so it can be audited by eye: excluded pixels
    tinted, the protected region outlined, over the original image."""
    vis = display_uint8.copy()
    if exclusion.any():
        vis[exclusion] = (0.4 * vis[exclusion] + 0.6 * np.array([0, 255, 255])).astype(np.uint8)
    boundary = segmentation.find_boundaries(protected, mode="outer")
    vis[boundary] = [255, 255, 0]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    imsave(out_path, vis, check_contrast=False)
