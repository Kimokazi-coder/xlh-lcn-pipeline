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

# Outputs: one folder per image, plus the summary table.
RESULTS_DIR = PROJECT_ROOT / "results"

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
