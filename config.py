"""Shared configuration for the LCN pipeline: paths, and the few settings
that both features use.

Each feature's own parameters live, with the reason for every value, at
the top of src/lacunae.py and src/canaliculi.py.

All sizes are in PIXELS: see PIXEL_SIZE_UM below.
"""

from pathlib import Path

# Paths

# Repository root, resolved from this file so the pipeline works from any
# working directory.
PROJECT_ROOT = Path(__file__).resolve().parent

# Input images.
DATA_DIR = PROJECT_ROOT / "data"

# Outputs: one folder per image, plus the cross-image files (results/README.md).
RESULTS_DIR = PROJECT_ROOT / "results"

# Result layout. Every result file is named after its image. The label of an
# image is its short name, from this table (key: the cleaned file name made by
# clean_name in src/lacunae.py). Images not listed, for example blinded codes
# such as S001, use their cleaned name as the label. Naming only; no number
# depends on it.
IMAGE_LABELS = {
    "542_WT_2_z06c1-2": "542_z06",
    "542_WT_2_z18c1-2": "542_z18",
    "543-2": "543-2",
    "543_3": "543_3",
    "543_z13c1-2": "543_z13",
    "682_z08c1-2": "682_z08",
    "682_z23c-2": "682_z23",
    "682_z29c1-3": "682_z29",
}

# Folders inside results/<label>/. Detection writes 1_lacunae and
# 2_canaliculi, src/quantification.py writes 5_quantification, and every
# measured number lives in 5_quantification alone.
SECTION_LACUNAE = "1_lacunae"
SECTION_CANALICULI = "2_canaliculi"
SECTION_FIGURES = "3_publication_figures"
SECTION_ARCHIVE = "4_archive_not_used"
SECTION_QUANTIFICATION = "5_quantification"

# Cross-image folders inside results/.
ALL_IMAGES_DIR = "all_images"
ALL_IMAGES_ARCHIVE_DIR = "archive_not_used"
ALL_IMAGES_FIGURES_DIR = "figures"
ALL_IMAGES_QUANT_DIR = "quantification"
VALIDATION_TILES_DIR = "validation_tiles"

# File names. A per-image file is <label>_<suffix>; a suffix without an
# extension is written with each extension given in its comment.
# Detection records: what each stage did, with no measured value in them.
SUFFIX_LACUNAE_DETECTION = "lacunae_detection.json"
SUFFIX_CANALICULI_DETECTION = "canaliculi_detection.json"
SUFFIX_LACUNAE_OUTLINES = "lacunae_outlines.png"
SUFFIX_CANALICULI_MASK = "canaliculi_mask.png"
SUFFIX_CANALICULI_SKELETON = "canaliculi_skeleton.png"
SUFFIX_CANALICULI_VERIFICATION = "canaliculi_verification.png"
# Detection output that src/quantification.py reads. The label image is 16-bit,
# 0 outside a kept lacuna and its 1..N lacuna_id inside; the three masks are
# 0 or 255; the graph file holds the cleaned graph with its ownership.
SUFFIX_LACUNA_LABELS = "lacuna_labels.png"
SUFFIX_CANALICULI_VASCULAR = "canaliculi_vascular_mask.png"
SUFFIX_CANALICULI_GRAPH = "canaliculi_graph.pickle"
# Quantification output: every measured number of one image.
SUFFIX_QUANTIFICATION = "quantification"  # .json, .xlsx and .pdf
SUFFIX_FIGURE_NETWORK = "figure_network"  # .png and .pdf
SUFFIX_FIGURE_GALLERY = "figure_cell_gallery"  # .png and .pdf
SUFFIX_FIGURE_OVERVIEW = "figure_overview"  # .png and .pdf
SUFFIX_FIGURE_NETWORK_CHECKS = "figure_network_checks.json"
SUFFIX_FIGURE_GALLERY_CHECKS = "figure_cell_gallery_checks.json"
SUFFIX_FIGURE_INSET = "figure_inset_choice.json"
VARIANTS_DIR = "variants_per_image_brightness"  # in SECTION_ARCHIVE
SUFFIX_VARIANT = "_per_image_brightness"  # appended to a figure suffix, .png
VARIANT_WINDOW_FILE = "display_window_this_image.json"
SUMMARY_NAME = "summary_all_images"  # .csv and .xlsx in ALL_IMAGES_DIR
# One row per image, in ALL_IMAGES_DIR/ALL_IMAGES_QUANT_DIR. This becomes the
# only cross-image table; it replaces summary_all_images with the same columns.
QUANT_SUMMARY_NAME = "quantification_all_images"  # .csv, .xlsx and .pdf
DISPLAY_WINDOW_FILE = "display_window.json"  # in ALL_IMAGES_DIR/ALL_IMAGES_FIGURES_DIR

# Image and channel selection

# Index of the channel carrying the LCN signal (0-based): 0 = red. None for
# single-channel (grayscale) images.
CHANNEL = 0

# Axis along which channels are stored in a multi-channel array: -1 for
# (Y, X, C), as these TIFFs are; 0 for (C, Y, X).
CHANNEL_AXIS = -1

# True if the signal is DARK on a BRIGHT background (for example brightfield).
# The loader then inverts the channel so that high value means signal.
INVERT_SIGNAL = False

# Spatial calibration

# Microns per pixel for the PIPELINE's own outputs. Deliberately None, so every
# pipeline number stays in pixel units. The physical scale is known: the confocal
# acquisition record gives 0.13 um/px, confirmed for all 8 images and rounded to
# two decimals, and it lives in PIXEL_SIZE_UM_ACQUIRED below. It is not set
# here because PIXEL_SIZE_UM is recorded in the parameters block of every result
# (lacunae.parameters, canaliculi.parameters) and switches every figure scale bar
# to micrometres: setting it would change those recorded values and the figures,
# so a fresh run would no longer equal results/ at tolerance 0. The units of the
# pipeline's output are a choice; the calibration is not missing.
PIXEL_SIZE_UM = None

# The physical scale. The acquisition record gives 0.13 um per pixel in x and y,
# confirmed for all 8 images and rounded to two decimals (the 0.44 um z step is
# not used: these are single 2D sections). Every length below in micrometres is
# converted to pixels with this, and it is a separate constant from
# PIXEL_SIZE_UM above for the reason given there.
PIXEL_SIZE_UM_ACQUIRED = 0.13


def px(um: float) -> float:
    """Micrometres to pixels, at the acquisition pixel size."""
    return um / PIXEL_SIZE_UM_ACQUIRED


def px_int(um: float) -> int:
    """Micrometres to a whole number of pixels."""
    return int(round(um / PIXEL_SIZE_UM_ACQUIRED))


def um(px_value: float) -> float:
    """Pixels to micrometres."""
    return px_value * PIXEL_SIZE_UM_ACQUIRED


# Biological limits
# Fixed, and identical for every image: no limit below is fitted to the data, and
# none is tuned per image. Each is written in micrometres, which is the parameter,
# and converted once with PIXEL_SIZE_UM_ACQUIRED, which gives the pixel value the
# code uses. NOTHING HERE IS VALIDATED: no limit has been checked against a
# manual count on this data, and the ranges are what the osteocyte literature
# reports for mouse cortical bone, used as a plausibility bound and never as a
# threshold that tunes a result.

# (a) The longest a canaliculus may be, measured ALONG THE NETWORK from the
# surface of the lacuna that owns it. Beyond this the skeleton is pruned.
# 50 um is the outer end of the reported lacuna-to-lacuna spacing in cortical
# bone, so a thread longer than this from one cell body is not one canaliculus:
# it is a tracing error, or it belongs to a lacuna outside the section. This is
# the one limit that CHANGES a number; everything else here is report only.
MAX_CANALICULUS_LENGTH_UM = 50.0

# (b) How far a lacuna reaches to attach a thread, and the signal that path must
# carry. A skeleton node is attached to a lacuna only if the straight path from
# the nearest point of its surface to that node carries signal all the way: the
# DIMMEST point of the RIDGE RESPONSE along the path must reach
# LACUNA_ATTACH_MIN_SIGNAL_FRACTION of the response's own low cut. A path across
# empty space fails at its dimmest point and is refused.
#
# The response, not the flattened intensity, because the top-hat flattening digs
# a trough around every lacuna body, so an intensity test cuts through the middle
# of the population and refuses real contacts along with empty space (measured:
# python src/diagnostics.py survey). The response is also what the method
# thresholds, so the attachment asks the same question the detection asked.
#
# 2.6 um is 20 px. The reach was 10 px while attachment went by distance alone,
# where a longer reach only meant handing a lacuna any network passing nearby.
# With the signal test deciding, a longer reach is safe and is needed: contact
# threads sat 10 to 20 px from a body and were left unowned.
#
# The fraction is the one the old gap bridging required of a gap before it would
# join one, measured the same way: the minimum along the path, not the mean,
# because one background-level pixel breaks a thread however bright its ends.
# NOT VALIDATED: no hand count chose either value.
LACUNA_ATTACH_REACH_UM = 2.6
LACUNA_ATTACH_MIN_SIGNAL_FRACTION = 0.7

# (c) Report only, no pruning. The range a canalicular length is reported
# against, so a reader can see what share of threads falls inside it. The
# pipeline does not act on it.
CANALICULUS_LENGTH_RANGE_UM = (25.0, 50.0)

# Output

# Decimal places for exported measurements.
CSV_FLOAT_PRECISION = 4

# Seed for anything with a random component (the per-lacuna overlay colours),
# so a rerun reproduces the same outputs.
RANDOM_SEED = 0

# Switches (all OFF by default)
# Each changes the pipeline only when turned on. With every switch off the
# outputs equal results/ exactly (python src/diagnostics.py regression), and
# python src/diagnostics.py switch-check shows what each one changes. Karim
# decides which to turn on. Evidence: the overnight report, tag archive-2026-10-13.

# Narrow crumb rule (overnight report 3.1, 3.4, 3.6b). After the re-merge and
# the filters, a dropped watershed piece joins a kept lacuna only if it
# touches that one kept lacuna and at least half of it lies inside the
# lacuna's convex hull. On the 8 WT images it changes only 543_3 (877,545),
# whose 124 px^2 middle piece was dropped and left a gap traced as a thread.
# The broad form (every crumb may join the re-merge) also admitted new
# objects and is not offered.
NARROW_CRUMB_RULE = False

# Fill holes fully enclosed by one kept lacuna, up to this size in px^2;
# 0 = off (overnight report 3.5, 3.6). The report recommends 200 if a hole rule
# is wanted: on the 8 WT images it fills one hole, 542_z06 (783,581),
# +146 px^2, with no effect on any network measure.
FILL_ENCLOSED_HOLES_MAX_PX2 = 0

# Band filter (overnight report 3.3, 3.6): reject a kept object that keeps less
# than this share of its area after an opening with a disk of radius 5 px
# (the top-hat disk). None = off. The report found that 0.515 sits in the gap
# between the two band objects (0.207 and 0.348) and every other kept lacuna
# (0.681 and up), but that gap rests on two objects only. Removing them lets
# the skeleton trace the band wall in their place.
BAND_FILTER_MIN_OPENING_SHARE = None

# Fast lacuna stage. The watershed split and the shallow-split re-merge of
# src/lacunae.py loop over every component with full-frame arrays (10 to 120 s
# per image). When True, bounding-box versions of the same two steps are used
# instead. They give identical labels on all 8 WT images at the default cut
# and at t_hi scaled 0.8 to 1.2 (python src/diagnostics.py fast-check), and
# regression passes with it on. Off by default; it changes speed, not output.
FAST_LACUNA_STAGE = False
