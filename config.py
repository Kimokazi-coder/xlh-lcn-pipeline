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

# Folders inside results/<label>/.
SECTION_LACUNAE = "1_lacunae"
SECTION_CANALICULI = "2_canaliculi"
SECTION_FIGURES = "3_publication_figures"
SECTION_ARCHIVE = "4_archive_not_used"

# Cross-image folders inside results/.
ALL_IMAGES_DIR = "all_images"
ALL_IMAGES_ARCHIVE_DIR = "archive_not_used"
ALL_IMAGES_FIGURES_DIR = "figures"
VALIDATION_TILES_DIR = "validation_tiles"

# File names. A per-image file is <label>_<suffix>; a suffix without an
# extension is written with each extension given in its comment.
SUFFIX_LACUNAE_RESULTS = "lacunae_results"  # .xlsx and .json
SUFFIX_LACUNAE_OUTLINES = "lacunae_outlines.png"
SUFFIX_CANALICULI_RESULTS = "canaliculi_results"  # .xlsx and .json
SUFFIX_CANALICULI_MASK = "canaliculi_mask.png"
SUFFIX_CANALICULI_SKELETON = "canaliculi_skeleton.png"
SUFFIX_CANALICULI_VERIFICATION = "canaliculi_verification.png"
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

# Microns per pixel. None, so every output stays in pixel units: the image
# files carry no usable calibration (7 of 8 have no resolution tags; one
# reports a generic 300 DPI). A real value has to come from the confocal
# acquisition record. Do not guess one.
PIXEL_SIZE_UM = None

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
# decides which to turn on. Evidence: docs/OVERNIGHT_REPORT.md.

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

# Straight band-wall filter (branch canaliculi-v2, docs/CANALICULI_V2_REPORT.md
# item B1; evidence results_experiments/canal_v2/B1_straight_runs.md). When on,
# the skeleton loses the zone within BAND_LINE_REMOVE_PX of every straight run
# of the skeleton (a one-pixel line of BAND_LINE_MIN_LEN_PX px fitting in the
# skeleton widened to 3 px, at one of 24 orientations) that comes within
# BAND_LINE_REACH_PX of the flagged canal mask, and no bridge may enter that
# zone. Default: off. Recommended value: none. On the 8 WT images the 542_z06
# band line (x 515 to 541, y 590 to 900) is straight only in pieces. Its
# straight part touches the canal mask only at a length of 40 px, where 66
# other straight objects touch canal masks too; the only length that separates
# any part of it (95 to 100 px, between 90 and 105) removes 103 of its about
# 380 skeleton px, 65.01 px away from the canal mask. Both values stay None,
# and the filter refuses to run until they are set.
BAND_LINE_FILTER = False
BAND_LINE_MIN_LEN_PX = None
BAND_LINE_REACH_PX = None
# Zone removed around the straight runs (px), from the task brief ("within 2 px").
BAND_LINE_REMOVE_PX = 2
