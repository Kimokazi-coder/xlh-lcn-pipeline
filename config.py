"""Central configuration for the 2D osteocyte lacuno-canalicular (LCN) pipeline.

Every tunable parameter lives here so that an analysis run is fully described
by this file plus the input images. Nothing in this module executes analysis --
it only declares values that the pipeline modules import:

    from config import CHANNEL, THRESHOLD_METHOD

Convention: all sizes and distances in this file are given in PIXELS. Results
therefore stay in pixel units (area in px^2, length in px) until PIXEL_SIZE_UM
below is set to a real value, at which point the pipeline can convert to
physical units.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Repository root, resolved relative to this file so the pipeline works no
# matter which directory it is launched from.
PROJECT_ROOT = Path(__file__).resolve().parent

# Input images. Kept out of version control (see .gitignore).
DATA_DIR = PROJECT_ROOT / "data"

# All generated output: masks, overlays, per-image tables, figures.
RESULTS_DIR = PROJECT_ROOT / "results"

# Output layout, one constant per destination so no script hard-codes a
# path. The organising principle is that what the CURRENT DEFAULT pipeline
# produces sits at the top of its folder, and everything else -- comparison
# runs, experimental detectors, diagnostics -- sits one level down, grouped
# by what it is. src/reorganize_outputs.py moved the tree into this shape
# on 2026-09-28 and is idempotent if it ever needs re-running.
#
#   canaliculi/<image>/   per-image canalicular outputs (default at top,
#                         non-default runs in all_method_results/)
#   lacunae/<image>/      per-image lacuna outputs from the current default
#                         detector (segment_lacunae_v2). Was results/count/.
#   candidates/           detectors NOT in use by default, e.g.
#                         candidates/lacunae_v3/
#   diagnostics/          read-only measurement output, grouped by the
#                         phase or round that produced it
CANALICULI_DIR = RESULTS_DIR / "canaliculi"
LACUNAE_DIR = RESULTS_DIR / "lacunae"
CANDIDATES_DIR = RESULTS_DIR / "candidates"
DIAGNOSTICS_DIR = RESULTS_DIR / "diagnostics"

# Text reports, one folder per run (reports/phase0_1/, reports/overnight/,
# reports/round2/ ...). Figures belong under RESULTS_DIR, not here.
REPORTS_DIR = PROJECT_ROOT / "reports"

# Planning notes and the running record: PROGRESS.md, DECISIONS_NEEDED.md.
# README.md stays in the repository root.
DOCS_DIR = PROJECT_ROOT / "docs"

# File extensions treated as input images. Matching is case-insensitive.
IMAGE_EXTENSIONS = (".tif", ".tiff", ".png")


# ---------------------------------------------------------------------------
# Image / channel selection
# ---------------------------------------------------------------------------

# Index of the channel carrying the LCN signal (0-based). Set to None for
# single-channel (already 2D grayscale) images.
#   0 = red channel (current setting)
CHANNEL = 0

# Axis along which channels are stored in a multi-channel array. Most TIFFs
# written by microscope software are (Y, X, C) -> -1; ImageJ hyperstacks saved
# as (C, Y, X) -> 0. Ignored when CHANNEL is None.
CHANNEL_AXIS = -1

# True if the LCN signal is DARK on a BRIGHT background (e.g. brightfield,
# basic fuchsin transmitted light). The pipeline inverts such images before
# thresholding so that "high value = signal" always holds downstream.
INVERT_SIGNAL = False


# ---------------------------------------------------------------------------
# Spatial calibration
# ---------------------------------------------------------------------------

# Physical width of one pixel, in microns per pixel. Left unset (None) --
# all sizes and outputs in this pipeline stay in PIXEL units until a real
# calibration value from the image metadata is provided here. Do not guess;
# read it off the acquisition settings before enabling physical-unit output.
PIXEL_SIZE_UM = None


# ---------------------------------------------------------------------------
# Pre-processing (applied before thresholding)
# ---------------------------------------------------------------------------

# Sigma of the Gaussian blur used to suppress shot noise, in pixels.
# Keep it well below the canalicular width or thin canaliculi will be
# smoothed away. Set to 0 to disable blurring.
GAUSSIAN_SIGMA_PX = 1.0

# Radius of the rolling-ball / white top-hat background subtraction, in
# pixels. Should be a few times larger than a lacuna so lacunae survive it.
# Set to None to skip background correction.
BACKGROUND_RADIUS_PX = 150

# ---------------------------------------------------------------------------
# Segmentation / thresholding
# ---------------------------------------------------------------------------

# How the foreground (stained LCN) is separated from background.
#   "otsu"       - global Otsu; fast, good for evenly illuminated fields
#   "percentile" - cutoff = the given PERCENTILE_THRESHOLD of pixel
#                  intensities; useful when only a small, bright fraction
#                  of the field is signal (see PERCENTILE_THRESHOLD below)
#   "li"         - global Li minimum-cross-entropy; gentler on dim canaliculi
#   "yen"        - global Yen; more conservative than Otsu, less background
#   "triangle"   - global triangle; suited to skewed histograms (sparse signal)
#   "sauvola"    - LOCAL adaptive; use when illumination varies across the field
#   "manual"     - fixed cutoff, see MANUAL_THRESHOLD below
# Only "otsu" and "percentile" are implemented so far (lacuna counter); the
# rest are reserved for later pipeline stages.
THRESHOLD_METHOD = "otsu"

# Percentile (0-100) of red-channel pixel intensities used as the cutoff
# when THRESHOLD_METHOD == "percentile". E.g. 99.0 keeps only the brightest
# 1% of pixels as foreground -- appropriate when lacunae occupy a small,
# bright fraction of the field.
PERCENTILE_THRESHOLD = 99.0

# Fixed intensity cutoff, used only when THRESHOLD_METHOD == "manual".
# Expressed on a 0-1 scale of the image's dynamic range.
MANUAL_THRESHOLD = 0.35

# Side length of the local window for the "sauvola" method, in pixels.
# Should comfortably contain a lacuna plus surrounding matrix.
LOCAL_WINDOW_PX = 96

# Multiplier applied to the automatically computed global threshold. Values
# below 1.0 are more inclusive (recover faint canaliculi at the cost of noise);
# above 1.0 are stricter. Leave at 1.0 unless a sensitivity check demands it.
THRESHOLD_SCALE = 1.0


# ---------------------------------------------------------------------------
# Object filtering
# ---------------------------------------------------------------------------

# Smallest connected component kept, in px^2. Anything below this is treated
# as noise / speckle and removed from the mask. Calibrated against data/WT
# (real lacunae there: ~1750-3900 px^2; leftover speckle after opening:
# ~150 px^2) -- re-check this if the acquisition resolution changes.
MIN_OBJECT_SIZE_PX2 = 500

# Largest connected component kept, in px^2. Guards against merged debris,
# section folds and saturated artefacts being counted as lacunae. Calibrated
# with headroom above the largest real lacuna seen in data/WT (~3900 px^2).
# Set to None to disable the upper bound.
MAX_OBJECT_SIZE_PX2 = 5000

# Holes smaller than this (in px^2) are filled before measurement, so that
# an unstained nucleus does not split one lacuna into a ring of fragments.
FILL_HOLES_BELOW_PX2 = 20

# Radius (in pixels) of the disk structuring element used for the
# morphological opening that despeckles the mask after hole-filling and
# before connected-component labeling. Needs to be large enough to erode
# away the thin canaliculi threads still attached to each lacuna at
# threshold time (radius=5 cleanly separated lacunae from the canalicular
# network in data/WT), or the lacunae get measured as one elongated,
# low-solidity blob fused with its canaliculi. Set to 0 to skip opening.
OPENING_RADIUS_PX = 5

# Objects touching the image border are partially outside the field, so their
# measured area and canalicular count are truncated. Excluded from the kept
# count and per-lacuna CSV when EXCLUDE_BORDER_OBJECTS is True.
EXCLUDE_BORDER_OBJECTS = True

# Minimum solidity (area / convex_area) for a kept lacuna. Real lacunae are
# fairly convex blobs; low solidity flags fused/irregular blobs or debris.
MIN_SOLIDITY = 0.85

# Plausible shape bound for a lacuna in cross-section. Objects above this
# aspect ratio (major_axis_length / minor_axis_length) are excluded --
# elongated canalicular fragments typically exceed it.
LACUNA_ASPECT_RATIO_MAX = 4.0


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

# Write per-image QC overlays (mask boundaries drawn on the raw channel).
# Strongly recommended: segmentation settings should always be eyeballed.
SAVE_OVERLAYS = True

# Write the binary masks themselves, so results can be re-measured without
# re-running segmentation.
SAVE_MASKS = True

# Decimal places used in the exported CSV tables.
CSV_FLOAT_PRECISION = 4

# Seed for any operation with a random component (e.g. sampled QC crops),
# so a re-run of the same inputs reproduces the same outputs.
RANDOM_SEED = 0
