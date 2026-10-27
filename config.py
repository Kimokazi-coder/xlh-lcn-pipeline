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

# Groups. The images are organised by type, one folder per group under data/.
# RD is regular diet and HP high phosphorus. WT is the reference group: its 8
# sections are the ones every rule of the pipeline was chosen on, by visual
# inspection, and no parameter may be tuned on any other group.
GROUPS = ("WT", "WT_HP", "Hyp_RD", "Hyp_HP")
REFERENCE_GROUP = "WT"
GROUP_DESCRIPTIONS = {
    "WT": "Wild type: the reference group, the 8 sections every rule of the pipeline was chosen on",
    "WT_HP": "Wild type, high phosphorus diet",
    "Hyp_RD": "Hyp, regular diet",
    "Hyp_HP": "Hyp, high phosphorus diet",
}

# Image import (python src/diagnostics.py import-group). A source image is
# copied into data/<group>/, under its own name, only when the pipeline would
# read it the way it reads the reference group; every other file is skipped and
# listed, with the reason, in data/image_inventory.csv. The source is only read.
#
# Format, read from the file's CONTENT and never from its name, because a file
# named .tif can hold a JPEG. A TIFF is copied byte for byte; a .tiff is copied
# as .tif. A JPEG is accepted by LOSSLESS DECODING (IMPORT_DECODE_JPEG): it is
# decoded with Pillow to the uint8 pixels it holds and written as an
# uncompressed TIFF under its own name with .tif. It is never recompressed,
# resized or converted in colour, and the TIFF is read back the way the
# pipeline reads it and must give exactly the decoded pixels, or it is removed
# and the file is skipped. Any other format is skipped.
#
# Why JPEG is accepted (the user's decision of 2026-10-23, after the format
# test, docs/METHODS.md section 22): the WT TIFFs hold decoded JPEG pixels at
# the same quantization tables as the new groups' JPEGs (three of four WT
# fields that also exist as JPEG decode to their TIFF pixel for pixel), so
# decoding the new groups' JPEGs puts every group through the same path.
# CAUTION: the pixels of all four groups are therefore JPEG-decoded, with the
# losses of that compression (lossy, colour detail at half resolution, 4:2:0),
# and no group has an uncompressed original. Until 2026-10-23 a JPEG was
# skipped, on the mistaken reason that WT was uncompressed.
#
# Shape, channel count and sample type: each must be one the reference group
# holds, read from data/<REFERENCE_GROUP>/ when the command runs (there:
# 1024 x 1024 px; 3 channels, or 4 with alpha; uint8). The sample type is held
# to it for the same reason as the shape: the absolute cuts of the lacuna stage
# (DIM_LACUNA_MAX_PEAK) sit on the 0 to 1 scale an 8 bit image is read to.
#
# Pixel size: a size written in the metadata with a physical unit (an ImageJ
# unit, a TIFF resolution per centimetre, an LSM or OME voxel size) must round
# to PIXEL_SIZE_UM_ACQUIRED at the two decimals that value is given to, which is
# IMPORT_PIXEL_SIZE_TOLERANCE_UM, half of the last decimal. A resolution per
# INCH is the print density the export software writes (ZEN writes 300 dpi on
# every export, one image of the reference group included), not a pixel size,
# so it is recorded and not compared. An image with no pixel size in its
# metadata is accepted, as the reference group's images are.
IMPORT_TIFF_SUFFIXES = (".tif", ".tiff")
IMPORT_DECODE_JPEG = True
IMPORT_PIXEL_SIZE_TOLERANCE_UM = 0.005
# Git. A copied file over IMPORT_MAX_FILE_MB, or a group whose images total over
# IMPORT_MAX_GROUP_MB (MB = 10^6 bytes), is still copied, but the group's data
# folder is added to .gitignore so its images stay on this machine and out of
# the repository (GitHub refuses a file over 100 MiB). Both values were set by
# the user on 2026-10-20.
IMPORT_MAX_FILE_MB = 90.0
IMPORT_MAX_GROUP_MB = 100.0
# The inventory names a source folder by its last IMPORT_SOURCE_PATH_PARTS path
# parts and never by its full path, so no local user name or folder outside the
# study is written into the repository.
IMPORT_SOURCE_PATH_PARTS = 2
IMPORT_INVENTORY_NAME = "image_inventory.csv"  # in DATA_DIR

# Outputs: one folder per group, results/<group>/, each holding one folder per
# image and the cross-image files (results/README.md). RESULTS_DIR is the
# reference group's folder, results/WT/: the deterministic method on the 8 WT
# sections, and what python src/diagnostics.py regression compares a fresh run
# with. A run given no output folder writes to RESULTS_ROOT/<name of its input
# folder>, so a run on data/WT writes results/WT/ (lacunae.output_root).
RESULTS_ROOT = PROJECT_ROOT / "results"
RESULTS_DIR = RESULTS_ROOT / REFERENCE_GROUP
# The second, labelled set: the same pipeline with the AI judge switch on
# (docs/EXPERIMENT_AI.md), for the WT group only, in results_ai_judge/WT/ with
# the same per-image layout, the comparison against results/WT/, and the judge
# log with the case pictures that were sent. results/ stays the deterministic
# method and is never written by the judge.
AI_RESULTS_ROOT = PROJECT_ROOT / "results_ai_judge"
AI_RESULTS_DIR = AI_RESULTS_ROOT / REFERENCE_GROUP

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

# Folders inside results/<group>/<label>/. Detection writes 1_lacunae and
# 2_canaliculi, src/quantification.py writes 5_quantification, and every
# measured number lives in 5_quantification alone.
SECTION_LACUNAE = "1_lacunae"
SECTION_CANALICULI = "2_canaliculi"
SECTION_FIGURES = "3_publication_figures"
SECTION_ARCHIVE = "4_archive_not_used"
SECTION_QUANTIFICATION = "5_quantification"

# Cross-image folders inside results/<group>/.
ALL_IMAGES_DIR = "all_images"
ALL_IMAGES_ARCHIVE_DIR = "archive_not_used"
ALL_IMAGES_FIGURES_DIR = "figures"
ALL_IMAGES_QUANT_DIR = "quantification"

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
# Dim thread-shaped structure no lacuna owns (canaliculi.find_unattached_threads).
# Saved because quantification must give the same numbers whether it measures
# from memory or from these files.
SUFFIX_CANALICULI_UNATTACHED = "canaliculi_unattached.png"
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
# A run lists every image it could not process, one file per stage, in
# ALL_IMAGES_DIR, and the other images carry on. The file is written only when
# an image fails, and a later run in which none fails removes it.
FAILED_IMAGES_NAME = "failed_images_{stage}.csv"
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
# so a fresh run would no longer equal results/WT/ at tolerance 0. The units of the
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


def area_px2(um2: float) -> int:
    """Square micrometres to whole square pixels."""
    return int(round(um2 / PIXEL_SIZE_UM_ACQUIRED ** 2))


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

# CONTACT. A skeleton node this close to a lacuna body attaches to its nearest
# lacuna with NO signal test, and attaches at weight 0. The zero weight is what
# makes contact happen BEFORE the shortest path assignment: the touched lacuna
# starts at its own surface with nothing in between, so no neighbour can reach
# that node on a shorter path and take the thread that touches it. Beyond this
# reach nothing changes: LACUNA_ATTACH_MIN_SIGNAL_FRACTION above governs, out to
# LACUNA_ATTACH_REACH_UM.
#
# Why a band with no test at all. The top-hat flattening removes the lacuna
# body, which digs a trough around every one of them, so the straight path from
# a surface to a node 2 to 4 px out crosses that trough at its dimmest point and
# the test refuses a thread that visibly touches the cell. Measured on all 8 WT
# images before the rule (python src/diagnostics.py contact): 92 of 108 lacunae
# had skeleton within 8 px of the body that they did not own, 12.2% of all
# touching skeleton, and 7 lacunae owned nothing at all. On the four lacunae the
# rule was opened on, the test refused 8 of 17, 11 of 11, 5 of 6 and 8 of 10 of
# the graph nodes within the attach reach, the nearest of them 2.8 to 3.2 px
# from the body. Inside this reach there is no empty space for an attachment to
# cross, which is what contact means and is why the test can be dropped here and
# only here.
#
# This is the one limit written in PIXELS and not in micrometres, because it is
# pixel geometry and not a biological length: the network mask has every body
# plus canaliculi.LACUNA_DILATION_PX = 2 px cut out of it, so a thread's centre
# line can never sit nearer than about 3 px to a body, and 6 px is that buffer
# plus one thread half width (p50 3.0 px). 6 px is 0.78 um.
# NOT VALIDATED: no hand count chose this reach.
CONTACT_REACH_PX = 6

# (c) The second, dimmer pass. A canaliculus that leaves a lacuna often fades
# before it ends, and the survey found 11 to 13% of the area within 150 px of a
# lacuna carrying ridge response between half the low cut and the low cut: real
# structure the one-pass threshold can never reach, because hysteresis can only
# grow into what is already above the low cut somewhere.
#
# So a second pass accepts response down to DIM_THREAD_CUT_FRACTION of the low
# cut, but ONLY continuing from skeleton a lacuna already owns, and only
# DIM_THREAD_REACH_UM further along the dim structure than that skeleton reaches.
#
# Both limits are needed. The faint band is a connected mesh: seeded from owned
# skeleton with connectivity alone and no reach, it floods, because at half the
# low cut the whole band is two connected components and the mask grows by 35%
# (measured on 543_3). The reach is what makes it a thread continuation rather
# than a flood: a dim thread may carry on 10 px past where the confident skeleton
# stopped, and no further.
#
# 1.3 um is 10 px. 0.5 is the floor the survey measured the faint band against.
# NOT VALIDATED: no hand count chose either value.
DIM_THREAD_CUT_FRACTION = 0.5
DIM_THREAD_REACH_UM = 0.65

# (d) Dim threads that touch no lacuna. The second pass above only continues
# threads a lacuna already owns, so a canaliculus whose whole run is dim, or
# whose lacuna is out of the section, is still missed. Those threads are real
# structure and belong in a field measure even though no cell can claim them.
#
# They are accepted from the same dim tier, down to DIM_THREAD_CUT_FRACTION of
# the low cut, but only where the component looks like a thread rather than a
# patch of background: at least UNATTACHED_MIN_LENGTH_UM long once skeletonized,
# and at least UNATTACHED_MIN_ASPECT times longer than it is wide.
#
# 1.3 um is 10 px, about two thread widths, so a component must actually run
# somewhere. The length floor is the one a canaliculus has to clear to be worth
# counting at all. Both are deliberately strict, because this tier has no lacuna
# to vouch for it: it is accepted on its own shape alone.
#
# They are counted as "unattached": included in the field length density, which
# asks how much canalicular network the tissue holds, and NEVER in a per-lacuna
# measure, because no lacuna owns them. NOT VALIDATED.
UNATTACHED_MIN_LENGTH_UM = 1.3
UNATTACHED_MIN_ASPECT = 3.0

# (f) The glow zone, and the lower cut inside it. METHODS section 18 measured
# what empties the ring of skeleton around every lacuna: of the pixels there
# carrying a ridge response of at least half the low cut, the hysteresis LOW CUT
# drops 59.9%, which is 27 times every other stage of the pipeline together. The
# reason is not that the glow raises the floor, which was measured and is false
# (the top-hat leaves a median of exactly 0 in those rings, lower than the tissue
# beyond them, and nothing is saturated): it is that a thread's own contrast
# there runs at 31 to 71% of what the same tissue shows 40 px further out, so one
# global cut keeps a quarter of the mask it keeps elsewhere.
#
# So inside each lacuna's own glow zone, and only there, the response is accepted
# down to GLOW_ZONE_CUT_FRACTION of the low cut, and only where it CONTINUES mask
# that the global cut already produced. Outside the zones nothing changes.
#
# The zone is never a fixed width: it is each lacuna's own glow extent, the
# distance at which its radial profile on the RAW channel falls to
# GLOW_PROFILE_FRACTION of its surface excess above the local background, the
# median over 180 rays (canaliculi.glow_extent_px). A fixed width would bias
# against exactly the lacunae a periosteocytic lesion widens, which is the
# comparison this pipeline exists to make.
#
# GLOW_PROFILE_FRACTION = 0.10: the profile has fallen to a tenth of its height
# above the background, which is where a decaying glow stops being distinguishable
# from the tissue around it. Not validated; no hand count chose it.
# GLOW_ZONE_CUT_FRACTION = 0.5: the same floor the second dim pass already uses
# (section 8), so the pipeline has one definition of "dim" and not two.
# GLOW_ZONE_MAX_UM: a cap, so a lacuna whose profile never falls (a saturated
# field, a lesion filling the frame) cannot claim the image. 8 um is just past
# the widest empty ring measured in the set, 7.69 um.
GLOW_PROFILE_FRACTION = 0.10
GLOW_ZONE_CUT_FRACTION = 0.5
GLOW_ZONE_MAX_UM = 8.0

# (g) The zone from the HOLE, and the contrast gain inside it. This replaces
# the cut of (f) above: the glow extent is still measured, and is still what
# (f) documents, but it is no longer what decides where the lower cut applies.
#
# Why. The glow zone rule of (f) recovered 7% of the skeleton (543-2: 37,700 to
# 40,374 px) and left the holes in place: the empty width median over the 108
# lacunae fell only from 27.4 to 24.2 px. Two reasons, both measured. The glow
# extent (3.9 to 33.2 px) is often NARROWER than the hole it is meant to fill
# (9.0 to 59.2 px, median 27.4), so the zone stopped short of the thread that
# was missing; and the rule could only EXTEND mask the global cut already made,
# so a thread whose whole run inside the hole was under the cut had no seed to
# grow from and stayed invisible.
#
# So the zone is now measured on the hole itself, and the cut inside it is the
# same global cut applied to a response that has been put back on the footing
# of the tissue just beyond the hole.
#
# THE ZONE. Per lacuna: its EMPTY WIDTH, measured by the 180 sector rule of
# METHODS section 18 on the skeleton the GLOBAL CUT produced, before any zone
# pass, so the zone is never defined by its own output; plus HOLE_ZONE_MARGIN_UM,
# one thread half width, so the zone reaches the first thread that bounds the
# hole and not just up to it; capped at GLOW_ZONE_MAX_UM, the same 8 um cap as
# (f). Never a fixed width: a lacuna with a wider hole, which is what a
# periosteocytic lesion makes, gets a wider zone, and that is the comparison
# this pipeline exists to make.
#
# 0.39 um is 3 px, the measured thread half width of this data (the p50 mask
# width is 6 px, METHODS section 18 uses the same 3 px as its rim).
HOLE_ZONE_MARGIN_UM = 0.39

# THE GAIN, AND WHY IT IS RADIAL. Inside its own zone, and nowhere else, each
# lacuna's ridge response is multiplied by its own contrast gain, and then the
# SAME global cuts are applied to it. The gain is this lacuna's own measurement
# of what the hole costs a thread: the HOLE_GAIN_PERCENTILE of the ridge
# response in the band just beyond the zone over the same percentile inside it.
# METHODS section 18 measured that ratio at 31 to 71% for the set, which is a
# gain of 1.4 to 3.2.
#
# ONE gain per lacuna was tried first and does not shrink the hole. Measured on
# 543-2, the p90 of the ridge response by distance from the body edge, as a
# multiple of the low cut: 0.87 at 0 to 5 px, 1.50 at 5 to 10, 2.07 at 10 to 15,
# 2.71 at 20 to 25, 3.41 at 30 to 40, and a plateau of 3.7 from 40 px out. The
# loss is not flat across the hole: it is a TROUGH that is deepest at the body
# and recovers outward, which is the top-hat digging around a bright body
# (METHODS section 8 names the same trough in the attachment rule). A single
# gain of about 2 therefore over-corrects the outer half of the zone, where the
# skeleton already is, and under-corrects the inner half, which is where the
# empty width is decided. With one gain the mask grew by 12,000 px on 543-2 and
# the empty width did not fall at all.
#
# So the gain follows the trough: the profile is measured in annuli
# HOLE_GAIN_STEP_UM wide from the body edge outward, smoothed over
# HOLE_GAIN_SMOOTH annuli, and each pixel is multiplied by the gain of the
# annulus it lies in. Same measurement, same percentile on both sides, read at
# the distance the pixel actually sits at.
#
# The band is HOLE_GAIN_BAND_UM wide, the same 40 px control band section 18
# reads the hole against: the same tissue, the same directions, the same depth
# of field, differing only in being past the hole.
#
# Clipped to HOLE_GAIN_MIN so the cut inside a zone can never be stricter than
# the global cut, and to HOLE_GAIN_MAX so a lacuna whose hole holds nothing at
# all cannot claim an unbounded gain: past that the ratio is measuring an empty
# hole and not a thread in one.
HOLE_GAIN_BAND_UM = 5.2
HOLE_GAIN_PERCENTILE = 50
HOLE_GAIN_MIN = 1.0
HOLE_GAIN_MAX = 3.0
HOLE_GAIN_STEP_UM = 0.26
HOLE_GAIN_SMOOTH = 3

# THE NOISE GUARD. The gain is applied with no requirement to connect to mask
# the global cut already made, which is the whole point of it: a thread whose
# run inside the hole is entirely under the cut has no seed to grow from. That
# also means the glow's own grain can now cross the cut, so a piece of mask
# that did not exist at all before, inside a zone, is kept only if it looks like
# a thread: at least HOLE_NEW_MIN_LENGTH_UM long once skeletonized and at least
# HOLE_NEW_MIN_ASPECT times longer than it is wide. These are the two tests the
# unattached dim tier already applies (section 8), for the same reason: nothing
# vouches for this mask, so it is accepted on its own shape alone. A piece that
# continues mask that was already there is not new and is not tested.
HOLE_NEW_MIN_LENGTH_UM = 10.0
HOLE_NEW_MIN_ASPECT = 3.0

# OWNERSHIP. A lacuna owns the thread that TOUCHES it. The contact rule of
# METHODS section 8 offers each node to its NEAREST lacuna only, so a thread
# that touches two bodies, or that touches one body while another body's
# surface is a pixel nearer, was handed to the neighbour. With this True a node
# within CONTACT_REACH_PX of a body attaches to THAT body at weight 0, to every
# body it touches, and the shortest path assignment then decides the rest as
# before. Set False to reproduce the nearest-lacuna version.
CONTACT_EVERY_TOUCHING_BODY = True

# The method, and the one way back. True is the rule above. False reproduces
# the glow zone version of (f), which is what the before runs of
# python src/diagnostics.py hole-check are made with; it is not a setting to
# run results with.
HOLE_ZONE_RULE = True

# (e) Trimming a glow streak off a lacuna body. A bright osteocyte often carries
# a tail of out-of-plane glow, and the threshold takes body and tail as one
# object, which makes it far more elongated than the cell is. The aspect filter
# then rejects a real lacuna for the shape of its glow.
#
# So a region that fails ONLY the aspect test gets one second chance: the body is
# opened with a disk of GLOW_TRIM_WIDTH_FRACTION of its own widest inscribed
# radius, which removes anything narrower than that fraction of the body's widest
# point, the largest surviving piece is taken as the body, and every filter is
# applied again to it. A region that already passes is never touched, so this can
# only rescue and never lose: applied to every region instead, it pushes four
# otherwise good lacunae below the area floor and rescues one, a net loss of
# three (measured over all 8 images).
#
# 0.5 is the fraction. A canalicular thread is about 6 px wide and a lacuna body
# 30 to 90 px across, so half the widest inscribed radius sits far above a thread
# and far below a body: it cuts glow and tails, not cells. MAX_ASPECT_RATIO is
# NOT raised; the shape rule is unchanged and only what it is measured on
# changes. NOT VALIDATED.
GLOW_TRIM_WIDTH_FRACTION = 0.5

# (f) Out-of-focus lacunae. A lacuna lying partly outside the focal plane shows
# as a round glow whose bright core clears the intensity cut but is far smaller
# than MIN_AREA_PX2, so the area filter drops it. The survey found 1,184 such
# sub-area candidates over the 8 images, and nearly all of them are thresholding
# specks: a rule that counted them all would add hundreds of false cells.
#
# So the rule is the most selective one that can be justified, and a candidate
# must satisfy ALL of it. It must be ROUND, because a blurred body is round while
# a speck on a thread is not: aspect at most OUT_OF_FOCUS_MAX_ASPECT and solidity
# at least OUT_OF_FOCUS_MIN_SOLIDITY. It must be CLEARLY BRIGHTER THAN ITS
# SURROUNDINGS, mean intensity at least OUT_OF_FOCUS_MIN_CONTRAST times the mean
# of the ring just outside it, because a body glows above its background while a
# speck sits on a thread no dimmer than itself. And it must be LARGE ENOUGH TO BE
# A BODY, at least OUT_OF_FOCUS_MIN_AREA_UM2.
#
# 2.5 um2 is about 148 px, a round core about 14 px across: two canalicular
# widths, far above the specks that fill the sub-area population, and small
# enough that a blurred body still reaches it. Over the 8 images this accepts
# 3 candidates, at most ONE per image, which is the selectivity asked for.
#
# They are counted as the class "out_of_focus": included in the lacuna count and
# in thread ownership, because a cell is there and its canaliculi are real, and
# EXCLUDED from every area and shape measure, because the edge being measured is
# the blur and not the cell. NOT VALIDATED.
OUT_OF_FOCUS_MIN_AREA_UM2 = 2.5
OUT_OF_FOCUS_MAX_ASPECT = 1.5
OUT_OF_FOCUS_MIN_SOLIDITY = 0.90
OUT_OF_FOCUS_MIN_CONTRAST = 1.5

# (g) Lacunae the area, solidity and frame rules used to miss. Every value below
# was chosen from the feature table of all 173 candidates of 100 px2 or more over
# the 8 images (python src/diagnostics.py lacuna-candidates), not from one image.
#
# WHAT THE DATA SAID, and it was not what was expected. "Clearly brighter than
# its surroundings" does NOT find these lacunae: measured as the mean inside over
# the mean of a ring just outside, the missed lacunae score 1.17 to 1.58 while
# ordinary specks reach 4.87, so that test runs BACKWARDS. The reason is physical:
# a real lacuna is ringed by its own dense canaliculi, which lift the ring, while
# a speck sits on dark background. What does separate them is that an
# out-of-focus lacuna is DIM: its core never saturates. Over the whole pool the
# missed lacunae peak at 0.678 to 0.792 and the next object up peaks at 0.824, a
# clean gap, so the rule is an upper bound on brightness, not a lower one.
#
# (g1) A sub-area candidate is a lacuna if it is big enough, compact, and dim.
DIM_LACUNA_MIN_AREA_UM2 = 2.7       # 160 px, the smallest missed lacuna is 166
DIM_LACUNA_MIN_SOLIDITY = 0.80      # compact; the dimmest kept one is 0.824
DIM_LACUNA_MAX_PEAK = 0.82          # in the gap: targets reach 0.792, the next is 0.824
#
# (g2) An object cut by the frame is only partly in the field, so the area floor
# is scaled by this. It is held to a stricter solidity than an interior object,
# because less of it is visible and a fragment of a thread must not qualify: at
# the scaled floor alone, two objects in an image that must not change would be
# admitted, and the solidity test is what excludes them.
BORDER_AREA_FRACTION = 0.75         # 300 px of the 400 px floor
BORDER_MIN_SOLIDITY = 0.85
#
# (g3) A large, bright, ragged region is a body with a thick process, not debris,
# so the solidity floor is lowered for it alone. Only one object over the 8
# images qualifies; the next ragged object is a quarter of the area.
THICK_PROCESS_MIN_AREA_UM2 = 16.9   # 1000 px
THICK_PROCESS_MIN_CONTRAST = 2.5    # mean inside over the ring just outside
THICK_PROCESS_MIN_SOLIDITY = 0.40
#
# (g4) A thin dark band can split one osteocyte in two. Two regions merge when
# they are adjacent along a long shared border AND the dip between them is
# shallow AND they are not both already lacunae. The last condition is what keeps
# the rule from fusing two real neighbouring cells: a merge may rescue a fragment
# into a body, or join two sub-area pieces, and nothing else.
MERGE_MIN_SHARED_PX = 150           # the target pairs share 201 and 543 px
MERGE_MIN_DIP_FRACTION = 0.75       # gap mean over the dimmer body's mean; 0.757 and 0.829
#
# Lacunae accepted by (g1) to (g3) are the class "dim": counted and owning
# threads, excluded from area and shape measures, exactly like out_of_focus.
# MIN_AREA_PX2 is NOT lowered for everything. NOT VALIDATED.

# (h) Report only, no pruning. The range a canalicular length is reported
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
# outputs equal results/WT/ exactly (python src/diagnostics.py regression), and
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

# The AI judge experiment (branch exp-ai-layer only)
# An AI judge decides, for every candidate thread near an osteocyte, whether it
# is a real thread and which lacuna it belongs to. Deterministic code stays the
# only code that touches pixels: src/ai_judge.py makes the candidates, the judge
# labels them, and the pipeline assembles the result and runs the existing 50 um
# cap and quantification. The whole experiment, with every decision taken while
# building it, is written up in docs/EXPERIMENT_AI.md.
#
# Nothing below changes any pipeline number while AI_JUDGE_ENABLED is False,
# which is how it ships: with it off the outputs equal results/WT/ exactly
# (python src/diagnostics.py regression).

# The switch. When True, src/canaliculi.py reads the judge's decision file for
# the image it is analysing (results_ai_judge/WT/ai_log/<label>/<label>_ai_segments.json),
# joins the segments judged real to the skeleton, drops the segments judged
# artifact, and then runs the existing ownership, 50 um cap and quantification
# unchanged. An image with no decision file is an error and not a silent pass,
# because a summary table must never mix judged and unjudged images.
#
# NOT in diagnostics.SWITCHES_ON: switch-check regenerates all 8 images, and
# the judge has run on 543-2 only.
AI_JUDGE_ENABLED = False

# The provider. Only "anthropic" is implemented; the setting exists so that
# adding a second one is a change in one place and not a change everywhere.
AI_JUDGE_PROVIDER = "anthropic"

# The pinned model, and the two prices it is billed at, in dollars per million
# tokens (Anthropic list price for claude-sonnet-5-5 on 2026-10-15). The prices
# live here because the cost estimate is a number this repository computes and
# every number it computes has its source written down.
AI_JUDGE_MODEL = "claude-sonnet-5-5"
AI_PRICE_INPUT_USD_PER_MTOK = 2.00
AI_PRICE_OUTPUT_USD_PER_MTOK = 10.00

# Sampling. 0 is the asked-for setting and the one recorded in every log record.
# It is SENT only to a model that accepts it: the pinned model rejects any
# non-default temperature with HTTP 400, so for claude-sonnet-5-5 the request
# carries no temperature at all and the log says so. What makes a run
# reproducible is therefore not the sampling setting but the log and the replay
# mode (docs/EXPERIMENT_AI.md, "Reproducibility").
AI_JUDGE_TEMPERATURE = 0.0
AI_MODELS_ACCEPTING_TEMPERATURE = ()

# Thinking off, for the same reason: a judge that reasons at length before
# answering spends output tokens and adds a source of variation. The pinned
# model takes "off" as thinking type "between_tools"; if the API refuses that,
# the call is repeated once at the model's default and the log records which of
# the two was used, so the log never claims a setting that was not sent.
AI_JUDGE_THINKING_OFF = True

# The answer is a small json object, one line per segment. 8000 leaves room for
# the largest case (AI_MAX_SEGMENTS_PER_CASE segments) and for the model's own
# reasoning if the thinking setting above had to fall back.
AI_JUDGE_MAX_TOKENS = 8000

# The cost ceiling for one run, in dollars. Every run estimates its cost before
# the first call and refuses to start if the estimate is above this; while it
# runs it adds up what the answers actually cost and stops if the total passes
# it.
MAX_COST_USD = 5.0

# The quality gate of a run over several images. Once this many calls have been
# made over the whole run, if more than AI_MAX_UNJUDGED_SHARE of the cases are
# still without a valid answer after their one retry, the run stops where it is
# and nothing after it is attempted: a prompt the model cannot answer should
# cost twenty calls and not a hundred and forty five.
AI_MIN_CALLS_BEFORE_QUALITY_GATE = 20
AI_MAX_UNJUDGED_SHARE = 0.20

# Where the requests, the answers, the pictures that were sent and the decision
# files are written, inside AI_RESULTS_DIR. One folder per image.
AI_LOG_DIR = "ai_log"
# Where the dry run writes its report and its pictures, inside RESULTS_ROOT
# (results/ai_dry_run/, not tracked).
AI_DRY_RUN_DIR = "ai_dry_run"

# Candidates (step 1 of the experiment). Inside each lacuna's measured empty
# width, and only there, the ridge response is accepted down to
# AI_CANDIDATE_CUT_FRACTION of the low cut after being scaled by that lacuna's
# own contrast ratio, which is capped at AI_CONTRAST_RATIO_MAX.
#
# 0.5 is the floor the second dim pass and the glow zone rule already use
# (DIM_THREAD_CUT_FRACTION, GLOW_ZONE_CUT_FRACTION), so the pipeline keeps one
# definition of "dim" and not three. The contrast ratio is this lacuna's own
# measurement of what the glow costs a thread: the p90 of the ridge response in
# the band just beyond the empty zone over the p90 inside it, which is METHODS
# section 18's "31 to 71% of what the same tissue shows 40 px further out"
# measured per lacuna instead of per set. It is floored at 1, so the cut can
# never be stricter than the pipeline's own, and capped at 3 because beyond
# that the ratio is measuring an empty hole and not a thread in a hole.
AI_CANDIDATE_CUT_FRACTION = 0.5
AI_CONTRAST_RATIO_MAX = 3.0
# The band just beyond the empty zone, in px, the contrast ratio is measured
# against: the same 40 px control band the empty-zone diagnostic uses.
AI_REFERENCE_BAND_PX = 40
# Angular sectors the frame around a body is cut into for the empty width, 2
# degrees each, and how far a sector looks for skeleton before it is censored.
# Both as in the empty-zone diagnostic.
AI_SECTORS = 180
AI_MAX_SEARCH_PX = 150
# A candidate segment must run at least this far to be offered to the judge.
# UNATTACHED_MIN_LENGTH_UM (1.3 um, 10 px) is the floor the pipeline already
# applies to a thread no lacuna owns, so again one definition and not two.
AI_MIN_SEGMENT_LENGTH_UM = UNATTACHED_MIN_LENGTH_UM
# At most this many segments are offered in one case. A zone with more offers
# its longest ones and the rest keep the deterministic decision, counted and
# reported as not offered. The cap is what keeps the picture readable and the
# answer small, and it is a property of the picture and not of the biology.
AI_MAX_SEGMENTS_PER_CASE = 40

# The picture the judge sees (step 2). A crop of AI_CROP_PX of image data around
# the lacuna, drawn twice side by side, each panel enlarged by whole pixels to
# AI_CROP_RENDER_PX so that a one pixel wide thread and a two digit number are
# both legible. The enlargement repeats pixels and interpolates nothing, so the
# judge sees the pixels the pipeline measured.
AI_CROP_PX = 256
AI_CROP_RENDER_PX = 512
# The brightness window of the crop: these percentiles of the raw channel in the
# crop, over the pixels that are NOT inside a lacuna body. Taken with the bodies
# in, a bright osteocyte takes the top of the window and the faint threads the
# judge is asked about go black. A display stretch only; it changes nothing
# measured.
AI_CROP_WINDOW_PERCENTILES = (1.0, 99.0)

# Token and cost estimate for a dry run, which must work with no network. Text
# is estimated at AI_TOKENS_PER_CHAR tokens per character and an image at
# width x height / AI_IMAGE_PIXELS_PER_TOKEN tokens, which is the rule
# Anthropic documents for image input. The answer is estimated at
# AI_OUTPUT_TOKENS_PER_SEGMENT per segment plus AI_OUTPUT_TOKENS_FIXED. All four
# are estimates and are labelled as estimates wherever they are printed; a real
# run logs the token counts the API reports and the dry run can be told to
# measure the input exactly (diagnostics ai-dry-run --count-tokens).
AI_TOKENS_PER_CHAR = 0.25
AI_IMAGE_PIXELS_PER_TOKEN = 750.0
AI_OUTPUT_TOKENS_PER_SEGMENT = 35
AI_OUTPUT_TOKENS_FIXED = 20

# The AI lacuna judge (docs/EXPERIMENT_AI.md)
# A second judge, separate from the thread judge above. The lacuna stage was
# shaped on the 8 WT images, and on the other groups it outlines saturated
# bands, soft tissue patches and small fragments as lacunae and misses dim or
# out-of-focus bodies. This judge is shown every candidate region of an image,
# numbered, and says which of them are osteocyte lacunae. It never draws or
# changes a boundary: every region it can keep or drop is one the lacuna stage
# outlined. One fixed prompt, src/judge_prompt_lacunae.md, for every group, so
# the rule is the same everywhere. The model, the prices, the thinking and
# temperature settings, the answer length and the quality gate are the thread
# judge's own, above.
#
# Nothing below changes any pipeline number while AI_LACUNA_JUDGE_ENABLED is
# False, which is how it ships.

# The switch. When True, src/lacunae.py reads the judge's decision file for the
# image it is analysing (results_ai_lacunae/<group>/ai_log/<label>/
# <label>_ai_lacunae.json): a region judged yes is a lacuna even if a shape
# filter rejected it, a region judged no is not one even if the filters kept it,
# and a region judged unsure, or not judged, keeps the deterministic decision.
# A region the judge adds is the class "judged": counted and owning threads,
# with no area or shape measure, like the class "dim". Every later stage runs
# unchanged. An image with no decision file is an error and not a silent pass.
AI_LACUNA_JUDGE_ENABLED = False

# Where this judge writes: results_ai_lacunae/<group>/, with the same layout as
# results/<group>/, its log in <group>/ai_log/, the pictures a run would send
# in dry_run/ and the contact sheets in review/.
AI_LACUNA_RESULTS_ROOT = PROJECT_ROOT / "results_ai_lacunae"
AI_LACUNA_DRY_RUN_DIR = "dry_run"
AI_LACUNA_REVIEW_DIR = "review"

# The candidates (deterministic, permissive). Every region of the lacuna stage's
# label image before its filters decide, kept and rejected alike, plus the dim
# candidates: the connected regions of the same mask (hole fill and despeckle
# included) at AI_LACUNA_DIM_CUT_FRACTION of the image's own lacuna cut that
# overlap no region of the first kind. Nothing is merged or split.
# 0.8 is the user's value (brief of 2026-10-26), the low end of the 0.8 to 1.2
# cut scaling of the sensitivity diagnostics. Chosen on no image.
AI_LACUNA_DIM_CUT_FRACTION = 0.8
# 100 px2 is the user's value; it is also the floor the lacuna-candidates feature
# table and the dark band merge already call a candidate, below the smallest
# kept class (out_of_focus, 148 px2).
AI_LACUNA_MIN_CANDIDATE_AREA_PX2 = 100
# At most this many numbered regions per image; the rest keep the deterministic
# decision and are counted. The user's value, a property of the picture (sixty
# numbers stay legible) and not of the biology. Named AI_LACUNA_MAX_CANDIDATES
# until 2026-10-27, when the user's brief named it this; the value is unchanged.
AI_LACUNA_MAX_NUMBERED = 60
# With more candidates than that, which are numbered goes by an order of
# priority and the cap drops from its end (src/ai_judge.py,
# LACUNA_NUMBERING_TIERS): every region the filters kept, then every region they
# rejected of at least this area, then the dim candidates, then the rejected
# regions under it, each largest first. So a kept lacuna is left unnumbered
# only on an image with more kept lacunae than the cap, which is reported.
# 300 px2 is the user's value (brief of 2026-10-27), chosen on no image.
AI_LACUNA_PRIORITY_REJECTED_MIN_AREA_PX2 = 300

# The cost ceiling of one run of this judge over every image, in dollars (the
# user's value, 2026-10-26). A run estimates its cost before the first call and
# refuses above this, and stops if what the answers actually cost passes it.
# The thread judge keeps its own MAX_COST_USD above.
AI_LACUNA_MAX_COST_USD = 3.0
