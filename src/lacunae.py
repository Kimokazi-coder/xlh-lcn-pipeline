"""Feature 1: osteocyte lacuna detection, counting and measurement.

PRE-VALIDATION. Nothing here has been checked against manual (ImageJ)
counts yet. PIXEL units throughout: config.PIXEL_SIZE_UM is None because
the images carry no usable spatial calibration, so areas are px^2 and
lengths are px.

Method, per image:
    1. Load the image and take the signal channel (config.CHANNEL, red).
    2. Split that channel's own histogram into three classes with
       multi-Otsu (background, canalicular network, lacunae) and keep the
       top class. Fill small holes and remove single-pixel specks.
    3. Separate touching bodies by thickness: a distance transform, one seed
       per relative distance maximum, then a marker-controlled watershed.
    4. Re-merge watershed pieces whose dividing saddle is shallow, so one
       elongated lacuna is not cut in two.
    5. Keep objects by area, solidity and aspect ratio. Objects touching the
       frame edge are kept and flagged on_border; they count toward
       lacuna_count but every summary statistic uses interior objects only,
       because their size and shape are truncated by the field of view.

Outputs, per image, in results/<label>/1_lacunae/ (the label is the short
image name of config.IMAGE_LABELS; see image_label and result_path):
    <label>_lacunae_outlines.png  the image with kept lacunae outlined in green
    <label>_lacunae_results.xlsx  "summary" (counts and interior mean, median,
                                  SD) and "per_lacuna" sheets
    <label>_lacunae_results.json  the same numbers plus the parameters used

Usage (from the repo root):
    python src/lacunae.py --dir data/WT
    python src/lacunae.py --image "data/WT/543-2.tif"
    python src/lacunae.py --dir data/WT -o OTHER_FOLDER    (default output: results/)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from skimage import filters, measure, morphology, segmentation
from skimage.io import imread, imsave
from skimage.util import img_as_float, img_as_ubyte

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

# Parameters
# None of these has been validated against manual counts. Each comment says
# what the value does and where it came from.

# Holes in the lacuna mask up to this size (px^2) are filled before
# splitting, so a dim spot inside a lacuna does not break it into a ring.
# Same value as the first lacuna counter used. Across the 98 kept WT
# lacunae the raw mask has 71 enclosed holes: 70 are at most 10 px^2 and are
# filled; one of 146 px^2 (542_z06, lacuna at (783,581)) stays open and is a
# known case.
FILL_HOLES_PX2 = 20

# Radius (px) of the opening that removes single-pixel specks after the
# hole fill. The smallest disk there is; an initial value, not tuned.
DESPECKLE_OPENING_RADIUS_PX = 1

# Watershed seeds are distance-transform maxima at least this fraction of
# their own component's peak, so seeding scales with each blob's size. An
# initial value, not tuned; the over-splits it can cause are undone by the
# shallow-split re-merge below.
SEED_PROMINENCE_FRACTION = 0.3

# A single elongated lacuna can show two comparable distance-transform peaks
# with no real constriction between them, and watershed then splits it.
# After watershed, pieces of one component are re-merged when the saddle
# between their peaks (the lowest distance value on the straight line
# joining them) is at least this fraction of the smaller peak. Calibrated on
# all 8 WT images: the 3 splits confirmed wrong by eye (542_z06) had ratio
# >= 0.364; the one split that looks like a real two-lobe separation had
# ratio 0.000. 0.35 sits between them.
MERGE_SADDLE_RATIO_MIN = 0.35

# Smallest kept object (px^2). From the pooled area distribution of interior
# objects over all 8 WT images (n=177 before this filter): 45% piled up
# against the earlier floor of 80, in [81, 373) px^2, a censored speck
# population rather than lacunae. The widest gap between consecutive sorted
# areas in that region is 346 to 429 px^2; 400 sits inside it.
MIN_AREA_PX2 = 400

# Largest kept object, as a fraction of the image area. A sanity cap against
# fused debris: 5% of a 1024 x 1024 field is 52,429 px^2, while the largest
# kept WT lacuna is 9,321 px^2.
MAX_AREA_FRACTION_OF_IMAGE = 0.05

# Sanity limits on shape. The kept population bottoms out at solidity 0.525
# and only two rejected lacuna-scale objects over the 8 images sit between
# 0.35 and 0.5, so the solidity cut sits in a real gap. The largest kept
# aspect ratio is 5.76.
MIN_SOLIDITY = 0.5
MAX_ASPECT_RATIO = 6.0

# Used only when a switch in config.py is on (all off by default).

# Narrow crumb rule (config.NARROW_CRUMB_RULE): least share of a dropped piece
# that must lie inside the kept lacuna's convex hull. Over the 8 WT images
# only 4 dropped pieces touch a kept lacuna, with shares 0.000, 0.000, 0.009
# and 1.000 (overnight report 3.6b); any value between 0.009 and 1.000 gives
# the same result, and 0.5 is the middle. Rests on 4 pieces.
CRUMB_INSIDE_HULL_MIN = 0.5

# Band filter (config.BAND_FILTER_MIN_OPENING_SHARE): radius (px) of the
# opening, the top-hat disk of src/canaliculi.py (TOPHAT_RADIUS_PX), the
# width above which a structure is broader than any canaliculus.
BAND_FILTER_OPENING_RADIUS_PX = 5

LACUNA_MEASUREMENT_FIELDS = [
    "lacuna_id",
    "area_px2",
    "major_axis_length_px",
    "minor_axis_length_px",
    "aspect_ratio",
    "eccentricity",
    "solidity",
    "orientation_rad",
    "centroid_row_px",
    "centroid_col_px",
    "on_border",
]

LACUNA_SUMMARY_METRICS = [
    ("area_px2", "px^2"),
    ("major_axis_length_px", "px"),
    ("minor_axis_length_px", "px"),
    ("aspect_ratio", "unitless"),
    ("eccentricity", "unitless"),
    ("solidity", "unitless"),
]


# Loading

def load_channel(image_path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Return (display_rgb_uint8, signal_channel_float).

    display_rgb_uint8 is the original image as RGB uint8, for overlays.
    signal_channel_float is config.CHANNEL as a 2D float array in [0, 1],
    inverted if config.INVERT_SIGNAL is set."""
    raw = imread(image_path)

    if raw.ndim == 2:
        display = np.stack([raw] * 3, axis=-1)
        channel_2d = raw
    elif raw.ndim == 3:
        if config.CHANNEL_AXIS == 0:
            raw = np.moveaxis(raw, 0, -1)
        elif config.CHANNEL_AXIS not in (-1, 2):
            raise ValueError(f"Unsupported config.CHANNEL_AXIS: {config.CHANNEL_AXIS!r}")

        n_channels = raw.shape[-1]
        if n_channels not in (3, 4):
            raise ValueError(f"Expected an RGB or RGBA image, got shape {raw.shape} for {image_path}")
        if config.CHANNEL is None or not (0 <= config.CHANNEL < n_channels):
            raise ValueError(
                f"config.CHANNEL={config.CHANNEL!r} is not a valid index into "
                f"an image with {n_channels} channels ({image_path})"
            )
        display = raw[..., :3]  # drop alpha, if present
        channel_2d = raw[..., config.CHANNEL]
    else:
        raise ValueError(f"Unsupported image ndim={raw.ndim} for {image_path}")

    display_uint8 = img_as_ubyte(display)
    channel_float = img_as_float(channel_2d)
    if config.INVERT_SIGNAL:
        channel_float = 1.0 - channel_float
    return display_uint8, channel_float


def clean_name(image_path: Path) -> str:
    """An image's stem with every run of whitespace replaced by one
    underscore ("542 WT  2_z06c1-2" becomes "542_WT_2_z06c1-2"). The key of
    config.IMAGE_LABELS."""
    return "_".join(image_path.stem.split())


def image_label(image) -> str:
    """The label of an image, used in every result folder and file name: its
    short name in config.IMAGE_LABELS, or its cleaned name when it is not
    listed. Takes an image path, a cleaned name or a label."""
    name = clean_name(image) if isinstance(image, Path) else str(image)
    return config.IMAGE_LABELS.get(name, name)


def result_path(out_root: Path, label: str, section: str, suffix: str, subfolder: str | None = None,
                prefixed: bool = True) -> Path:
    """Path of one result file: <out_root>/<label>/<section>/[<subfolder>/]
    <label>_<suffix>, or <suffix> alone when prefixed is False."""
    folder = Path(out_root) / label / section
    if subfolder:
        folder = folder / subfolder
    return folder / (f"{label}_{suffix}" if prefixed else suffix)


def all_images_path(out_root: Path, name: str, subfolder: str | None = None) -> Path:
    """Path of one cross-image file: <out_root>/all_images/[<subfolder>/]<name>."""
    folder = Path(out_root) / config.ALL_IMAGES_DIR
    return (folder / subfolder / name) if subfolder else folder / name


# Segmentation

def multiotsu_lacuna_mask(channel: np.ndarray, t_hi: float | None = None) -> tuple[np.ndarray, float]:
    """Three-class Otsu on this image's own histogram; the top class holds
    the bright lacuna population, separate from the dimmer network. A given
    t_hi replaces the computed cut (used only by the sensitivity diagnostics;
    the pipeline never passes one)."""
    if t_hi is None:
        try:
            thresholds = filters.threshold_multiotsu(channel, classes=3)
            t_hi = float(thresholds[-1])
        except ValueError:
            # Degenerate histogram (for example a near-constant field).
            t_hi = float(filters.threshold_otsu(channel))

    mask = channel >= t_hi
    mask = morphology.remove_small_holes(mask, area_threshold=FILL_HOLES_PX2)
    if DESPECKLE_OPENING_RADIUS_PX > 0:
        mask = morphology.opening(mask, morphology.disk(DESPECKLE_OPENING_RADIUS_PX))
    return mask, t_hi


def watershed_split(mask: np.ndarray) -> np.ndarray:
    """Separate fused blobs by thickness: seeds at each connected
    component's own relative distance-transform maxima, then a
    marker-controlled watershed, which cuts along thin necks."""
    distance = ndi.distance_transform_edt(mask)
    components = measure.label(mask, connectivity=2)

    markers = np.zeros_like(components, dtype=np.int32)
    next_id = 1
    for comp_id in range(1, components.max() + 1):
        comp_mask = components == comp_id
        d_local = np.where(comp_mask, distance, 0.0)
        peak = d_local.max()
        if peak <= 0:
            continue
        h = max(SEED_PROMINENCE_FRACTION * peak, 1e-6)
        seeds = morphology.h_maxima(d_local, h) & comp_mask
        seed_labels = measure.label(seeds, connectivity=2)
        n = seed_labels.max()
        if n == 0:
            continue
        remap = seed_labels.copy()
        remap[seed_labels > 0] += next_id - 1
        markers[seed_labels > 0] = remap[seed_labels > 0]
        next_id += n

    return segmentation.watershed(-distance, markers=markers, mask=mask)


def watershed_split_fast(mask: np.ndarray) -> np.ndarray:
    """watershed_split with the same steps done inside each component's
    bounding box plus a 1 px margin (config.FAST_LACUNA_STAGE). Identical
    labels (python src/diagnostics.py fast-check)."""
    distance = ndi.distance_transform_edt(mask)
    components = measure.label(mask, connectivity=2)
    markers = np.zeros_like(components, dtype=np.int32)
    next_id = 1
    rows, cols = mask.shape
    for comp_id, sl in enumerate(ndi.find_objects(components), start=1):
        if sl is None:
            continue
        r0, r1 = max(sl[0].start - 1, 0), min(sl[0].stop + 1, rows)
        c0, c1 = max(sl[1].start - 1, 0), min(sl[1].stop + 1, cols)
        comp_mask = components[r0:r1, c0:c1] == comp_id
        d_local = np.where(comp_mask, distance[r0:r1, c0:c1], 0.0)
        peak = d_local.max()
        if peak <= 0:
            continue
        h = max(SEED_PROMINENCE_FRACTION * peak, 1e-6)
        seeds = morphology.h_maxima(d_local, h) & comp_mask
        seed_labels = measure.label(seeds, connectivity=2)
        n = seed_labels.max()
        if n == 0:
            continue
        sub = markers[r0:r1, c0:c1]
        sub[seed_labels > 0] = seed_labels[seed_labels > 0] + next_id - 1
        next_id += n
    return segmentation.watershed(-distance, markers=markers, mask=mask)


def _sample_line_min(distance: np.ndarray, r0: float, c0: float, r1: float, c1: float, n: int = 50) -> float:
    """Lowest distance-transform value on the straight line between two
    points: the saddle depth between two candidate peaks."""
    rows = np.linspace(r0, r1, n)
    cols = np.linspace(c0, c1, n)
    ri = np.clip(np.round(rows).astype(int), 0, distance.shape[0] - 1)
    ci = np.clip(np.round(cols).astype(int), 0, distance.shape[1] - 1)
    return float(distance[ri, ci].min())


def merge_shallow_splits(labels: np.ndarray, mask: np.ndarray, distance: np.ndarray) -> np.ndarray:
    """Undo watershed splits that are not a real multi-lobe separation.

    Within each pre-watershed component, only pieces of at least
    MIN_AREA_PX2 are considered (smaller crumbs are dropped later by the
    area filter). There can be more than two. Any two whose saddle is
    shallow relative to both peaks (see MERGE_SADDLE_RATIO_MIN) are joined
    with union-find, so a chain of shallow links merges all of them."""
    components = measure.label(mask, connectivity=2)
    merged = labels.copy()
    for comp_id in range(1, components.max() + 1):
        comp_mask = components == comp_id
        piece_labels = np.unique(merged[comp_mask])
        piece_labels = piece_labels[piece_labels != 0]
        substantial = [lbl for lbl in piece_labels if (merged == lbl).sum() >= MIN_AREA_PX2]
        if len(substantial) < 2:
            continue

        peaks = {}
        peak_locs = {}
        for lbl in substantial:
            piece_mask = merged == lbl
            peaks[lbl] = distance[piece_mask].max()
            r, c = np.unravel_index(np.argmax(np.where(piece_mask, distance, -1)), distance.shape)
            peak_locs[lbl] = (r, c)

        parent = {lbl: lbl for lbl in substantial}

        def find(x):
            while parent[x] != x:
                x = parent[x]
            return x

        for i in range(len(substantial)):
            for j in range(i + 1, len(substantial)):
                a, b = substantial[i], substantial[j]
                ra, ca = peak_locs[a]
                rb, cb = peak_locs[b]
                saddle = _sample_line_min(distance, ra, ca, rb, cb)
                ratio = saddle / min(peaks[a], peaks[b])
                if ratio >= MERGE_SADDLE_RATIO_MIN:
                    ra_root, rb_root = find(a), find(b)
                    if ra_root != rb_root:
                        parent[ra_root] = rb_root

        for lbl in substantial:
            root = find(lbl)
            if root != lbl:
                merged[merged == lbl] = root
    return merged


def merge_shallow_splits_fast(labels: np.ndarray, mask: np.ndarray, distance: np.ndarray) -> np.ndarray:
    """merge_shallow_splits with the same steps done inside each component's
    bounding box (config.FAST_LACUNA_STAGE). Same pieces, same order, same
    saddle test; identical labels (python src/diagnostics.py fast-check)."""
    components = measure.label(mask, connectivity=2)
    merged = labels.copy()
    for comp_id, sl in enumerate(ndi.find_objects(components), start=1):
        if sl is None:
            continue
        r0, c0 = sl[0].start, sl[1].start
        comp_mask = components[sl] == comp_id
        m = merged[sl]
        piece_labels = np.unique(m[comp_mask])
        piece_labels = piece_labels[piece_labels != 0]
        substantial = [lbl for lbl in piece_labels if (m == lbl).sum() >= MIN_AREA_PX2]
        if len(substantial) < 2:
            continue
        peaks, peak_locs = {}, {}
        for lbl in substantial:
            piece = m == lbl
            peaks[lbl] = distance[sl][piece].max()
            rr, cc = np.unravel_index(np.argmax(np.where(piece, distance[sl], -1)), piece.shape)
            peak_locs[lbl] = (rr + r0, cc + c0)
        parent = {lbl: lbl for lbl in substantial}

        def find(x):
            while parent[x] != x:
                x = parent[x]
            return x

        for i in range(len(substantial)):
            for j in range(i + 1, len(substantial)):
                a, b = substantial[i], substantial[j]
                ra, ca = peak_locs[a]
                rb, cb = peak_locs[b]
                saddle = _sample_line_min(distance, ra, ca, rb, cb)
                if saddle / min(peaks[a], peaks[b]) >= MERGE_SADDLE_RATIO_MIN:
                    root_a, root_b = find(a), find(b)
                    if root_a != root_b:
                        parent[root_a] = root_b
        for lbl in substantial:
            root = find(lbl)
            if root != lbl:
                m[m == lbl] = root
        merged[sl] = m
    return merged


def filter_regions(label_image: np.ndarray) -> list[tuple]:
    """[(region, on_border), ...] for objects passing the area, solidity and
    aspect filters. Objects touching the frame edge are kept and flagged."""
    rows, cols = label_image.shape
    max_area = MAX_AREA_FRACTION_OF_IMAGE * rows * cols
    kept = []
    for region in measure.regionprops(label_image):
        if region.area < MIN_AREA_PX2:
            continue
        if region.area > max_area:
            continue
        if region.solidity < MIN_SOLIDITY:
            continue
        minor = region.axis_minor_length
        major = region.axis_major_length
        aspect = (major / minor) if minor > 0 else float("inf")
        if aspect > MAX_ASPECT_RATIO:
            continue

        min_row, min_col, max_row, max_col = region.bbox
        on_border = min_row == 0 or min_col == 0 or max_row == rows or max_col == cols
        kept.append((region, on_border))
    return kept


def join_enclosed_crumbs(labels: np.ndarray, kept: list[tuple]) -> np.ndarray:
    """Narrow crumb rule (config.NARROW_CRUMB_RULE). Every piece that the
    filters dropped joins a kept lacuna if it touches exactly that one kept
    lacuna (8-neighbourhood) and at least CRUMB_INSIDE_HULL_MIN of it lies
    inside that lacuna's convex hull. Pieces are visited in label order."""
    labels = labels.copy()
    rows, cols = labels.shape
    regions = {r.label: r for r in measure.regionprops(labels)}
    kept_labels = {region.label for region, _ in kept}
    for label, region in regions.items():
        if label in kept_labels:
            continue
        r0, c0, r1, c1 = region.bbox
        r0, c0, r1, c1 = max(r0 - 1, 0), max(c0 - 1, 0), min(r1 + 1, rows), min(c1 + 1, cols)
        sub = labels[r0:r1, c0:c1]
        piece = sub == label
        ring = morphology.binary_dilation(piece, np.ones((3, 3), bool)) & ~piece
        touched = {int(v) for v in np.unique(sub[ring])} & kept_labels
        if len(touched) != 1:
            continue
        target = regions[touched.pop()]
        k0, kc0, k1, kc1 = target.bbox
        rr, cc = region.coords[:, 0], region.coords[:, 1]
        inside = (rr >= k0) & (rr < k1) & (cc >= kc0) & (cc < kc1)
        hull = np.zeros(rr.shape, dtype=bool)
        hull[inside] = target.image_convex[rr[inside] - k0, cc[inside] - kc0]
        if hull.mean() >= CRUMB_INSIDE_HULL_MIN:
            labels[rr, cc] = target.label
    return labels


def fill_enclosed_holes(labels: np.ndarray, kept: list[tuple], max_px2: int) -> np.ndarray:
    """Hole fill (config.FILL_ENCLOSED_HOLES_MAX_PX2): fill every hole fully
    enclosed by one kept lacuna (4-connected background, as
    remove_small_holes counts holes) of at most max_px2, if no other piece
    lies in it."""
    labels = labels.copy()
    for region, _on_border in kept:
        r0, c0, _r1, _c1 = region.bbox
        holes = ndi.binary_fill_holes(region.image) & ~region.image
        hole_labels = measure.label(holes, connectivity=1)
        for hole in measure.regionprops(hole_labels):
            if hole.area > max_px2:
                continue
            rr, cc = hole.coords[:, 0] + r0, hole.coords[:, 1] + c0
            if (labels[rr, cc] != 0).any():
                continue
            labels[rr, cc] = region.label
    return labels


def opening_share(region) -> float:
    """Share of an object's area left after an opening with a disk of
    BAND_FILTER_OPENING_RADIUS_PX."""
    m = np.pad(region.image, BAND_FILTER_OPENING_RADIUS_PX + 1)
    opened = morphology.binary_opening(m, morphology.disk(BAND_FILTER_OPENING_RADIUS_PX))
    return float(opened.sum() / m.sum())


def band_filter(kept: list[tuple], min_share: float) -> list[tuple]:
    """Band filter (config.BAND_FILTER_MIN_OPENING_SHARE): drop kept objects
    that keep less than min_share of their area after the opening."""
    return [(region, b) for region, b in kept if opening_share(region) >= min_share]


def segment(channel: np.ndarray, t_hi: float | None = None) -> tuple[np.ndarray, list[tuple], float]:
    """(label_image, kept, t_hi) for one signal channel. The switch steps run
    only when their switch in config.py is on. A given t_hi replaces the
    computed cut (sensitivity diagnostics only)."""
    mask, t_hi = multiotsu_lacuna_mask(channel, t_hi)
    fast = config.FAST_LACUNA_STAGE
    labels = (watershed_split_fast if fast else watershed_split)(mask)
    distance = ndi.distance_transform_edt(mask)
    labels = (merge_shallow_splits_fast if fast else merge_shallow_splits)(labels, mask, distance)
    kept = filter_regions(labels)
    if config.NARROW_CRUMB_RULE:
        labels = join_enclosed_crumbs(labels, kept)
        kept = filter_regions(labels)
    if config.FILL_ENCLOSED_HOLES_MAX_PX2 and config.FILL_ENCLOSED_HOLES_MAX_PX2 > 0:
        labels = fill_enclosed_holes(labels, kept, config.FILL_ENCLOSED_HOLES_MAX_PX2)
        kept = filter_regions(labels)
    if config.BAND_FILTER_MIN_OPENING_SHARE is not None:
        kept = band_filter(kept, config.BAND_FILTER_MIN_OPENING_SHARE)
    return labels, kept, t_hi


def segment_image(image_path: Path, t_hi: float | None = None):
    """(display, channel, label_image, kept, t_hi) for one image file. A given
    t_hi replaces the computed cut (sensitivity diagnostics only)."""
    display, channel = load_channel(image_path)
    labels, kept, t_hi = segment(channel, t_hi)
    return display, channel, labels, kept, t_hi


# Measurements

def region_to_measurement(lacuna_id: int, region, on_border: bool, precision: int) -> dict:
    minor = region.axis_minor_length
    major = region.axis_major_length
    aspect_ratio = (major / minor) if minor > 0 else float("inf")
    row, col = region.centroid
    return {
        "lacuna_id": lacuna_id,
        "area_px2": round(float(region.area), precision),
        "major_axis_length_px": round(float(major), precision),
        "minor_axis_length_px": round(float(minor), precision),
        "aspect_ratio": round(float(aspect_ratio), precision),
        "eccentricity": round(float(region.eccentricity), precision),
        "solidity": round(float(region.solidity), precision),
        "orientation_rad": round(float(region.orientation), precision),
        "centroid_row_px": round(float(row), precision),
        "centroid_col_px": round(float(col), precision),
        "on_border": bool(on_border),
    }


def measurements_for(kept: list[tuple], precision: int) -> list[dict]:
    """One row per kept lacuna, numbered 1..N in kept order. The canaliculi
    feature uses the same numbering."""
    return [
        region_to_measurement(i, region, on_border, precision)
        for i, (region, on_border) in enumerate(kept, start=1)
    ]


def summarize_interior(measurements: list[dict], precision: int) -> dict:
    """Mean, median and sample SD (ddof=1) over interior lacunae only. SD is
    None below 2 objects, and everything is None with no interior object."""
    interior = [m for m in measurements if not m["on_border"]]
    n = len(interior)

    stats = {"interior_lacuna_count": n, "units": "px"}
    for field, _unit in LACUNA_SUMMARY_METRICS:
        values = np.array([m[field] for m in interior], dtype=float)
        if n == 0:
            mean = median = sd = None
        else:
            mean = round(float(values.mean()), precision)
            median = round(float(np.median(values)), precision)
            sd = round(float(values.std(ddof=1)), precision) if n >= 2 else None
        stats[field] = {"mean": mean, "median": median, "sd": sd}
    return stats


def analyse_image(image_path: Path, t_hi: float | None = None) -> dict:
    """Everything feature 1 computes for one image, without writing. t_hi:
    see segment_image."""
    precision = config.CSV_FLOAT_PRECISION
    display, channel, labels, kept, t_hi = segment_image(image_path, t_hi)
    rows = measurements_for(kept, precision)
    border = sum(1 for _r, on_border in kept if on_border)
    return {
        "image_path": image_path,
        "display": display,
        "labels": labels,
        "kept": kept,
        "t_hi": t_hi,
        "rows": rows,
        "lacuna_count": len(kept),
        "border_lacuna_count": border,
        "interior_lacuna_count": len(kept) - border,
        "summary": summarize_interior(rows, precision),
    }


# Provenance

# Libraries whose versions are recorded in every json output.
PROVENANCE_PACKAGES = ["numpy", "scipy", "scikit-image", "skan", "networkx", "pandas"]


def config_values() -> dict:
    """Every upper-case setting in config.py except the paths, which differ
    between machines and do not change any number."""
    out = {}
    for name in sorted(dir(config)):
        if not name.isupper():
            continue
        value = getattr(config, name)
        if isinstance(value, Path):
            continue
        out[name] = value
    return out


def config_hash() -> str:
    """Short SHA-256 of config_values(), so two outputs made with different
    settings can be told apart."""
    import hashlib

    text = json.dumps(config_values(), sort_keys=True, default=repr)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def provenance() -> dict:
    """Which code, settings and libraries produced an output. No timestamps,
    so the same code on the same data writes the same file. git_dirty is True
    when tracked files differ from the commit (untracked files are ignored);
    both git fields are None when git is not available."""
    import platform
    import subprocess
    from importlib import metadata

    def git(*args):
        try:
            done = subprocess.run(["git", *args], cwd=config.PROJECT_ROOT, capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.SubprocessError):
            return None
        return done.stdout.strip() if done.returncode == 0 else None

    commit = git("rev-parse", "HEAD")
    status = git("status", "--porcelain", "--untracked-files=no")
    versions = {"python": platform.python_version()}
    for package in PROVENANCE_PACKAGES:
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = None
    return {
        "git_commit": commit,
        "git_dirty": None if status is None else bool(status),
        "versions": versions,
        "config_hash": config_hash(),
        "config_hash_covers": sorted(config_values()),
    }


# Output

def save_overlay(display_uint8: np.ndarray, label_image: np.ndarray, kept: list[tuple], out_path: Path) -> None:
    kept_ids = {region.label for region, _ in kept}
    kept_mask = np.isin(label_image, list(kept_ids)) if kept_ids else np.zeros_like(label_image, dtype=bool)
    boundaries = segmentation.find_boundaries(kept_mask, mode="outer")
    overlay = display_uint8.copy()
    overlay[boundaries] = [0, 255, 0]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    imsave(out_path, overlay, check_contrast=False)


def label_image_of_kept(labels: np.ndarray, kept: list[tuple]) -> np.ndarray:
    """The label image src/quantification.py reads: 0 outside a kept lacuna,
    else the lacuna's 1..N id in kept order, the numbering of every output.
    Dropped objects are not in it. uint16, so it saves as a 16-bit PNG; the
    same array as canaliculi.build_lacuna_maps builds in memory."""
    out = np.zeros(labels.shape, dtype=np.uint16)
    for lacuna_id, (region, _on_border) in enumerate(kept, start=1):
        out[labels == region.label] = lacuna_id
    return out


def save_label_image(labels: np.ndarray, kept: list[tuple], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    imsave(out_path, label_image_of_kept(labels, kept), check_contrast=False)


def parameters() -> dict:
    return {
        "channel": config.CHANNEL,
        "channel_axis": config.CHANNEL_AXIS,
        "invert_signal": config.INVERT_SIGNAL,
        "pixel_size_um": config.PIXEL_SIZE_UM,
        "threshold_method": "multiotsu_3class_top",
        "fill_holes_px2": FILL_HOLES_PX2,
        "despeckle_opening_radius_px": DESPECKLE_OPENING_RADIUS_PX,
        "seed_prominence_fraction": SEED_PROMINENCE_FRACTION,
        "merge_saddle_ratio_min": MERGE_SADDLE_RATIO_MIN,
        "min_area_px2": MIN_AREA_PX2,
        "max_area_fraction_of_image": MAX_AREA_FRACTION_OF_IMAGE,
        "min_solidity": MIN_SOLIDITY,
        "max_aspect_ratio": MAX_ASPECT_RATIO,
        "narrow_crumb_rule": config.NARROW_CRUMB_RULE,
        "fill_enclosed_holes_max_px2": config.FILL_ENCLOSED_HOLES_MAX_PX2,
        "band_filter_min_opening_share": config.BAND_FILTER_MIN_OPENING_SHARE,
        "fast_lacuna_stage": config.FAST_LACUNA_STAGE,
    }


DETECTION_NOTE = (
    "Detection record: what feature 1 did, with no measured value in it. The "
    "lacunae it found are the 1..N labels of the label image, and every number "
    "measured from them is in results/<label>/5_quantification/ "
    "(src/quantification.py)."
)


def save_detection_json(result: dict, out_path: Path) -> None:
    """The record of one lacuna detection run: parameters, the computed cut and
    provenance. Counts and shapes are not here; quantification measures them
    from the label image."""
    payload = {
        "status": "pre-validation",
        "units": "px",
        "stage": "lacuna detection",
        "image": result["image_path"].name,
        "image_label": image_label(result["image_path"]),
        "note": DETECTION_NOTE,
        "outputs": {
            "label_image": f"{image_label(result['image_path'])}_{config.SUFFIX_LACUNA_LABELS}",
            "outlines": f"{image_label(result['image_path'])}_{config.SUFFIX_LACUNAE_OUTLINES}",
        },
        "parameters": {**parameters(), "computed_threshold_t_hi": result["t_hi"]},
        "provenance": provenance(),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)


def save_json(result: dict, out_path: Path) -> None:
    payload = {
        "status": "pre-validation",
        "units": "px",
        "image": result["image_path"].name,
        "image_label": image_label(result["image_path"]),
        "note": (
            "Pre-validation: not checked against manual counts. Pixel units. "
            "Border lacunae count toward lacuna_count but the summary covers "
            "interior lacunae only."
        ),
        "lacuna_count": result["lacuna_count"],
        "border_lacuna_count": result["border_lacuna_count"],
        "interior_lacuna_count": result["interior_lacuna_count"],
        "summary": result["summary"],
        "parameters": {**parameters(), "computed_threshold_t_hi": result["t_hi"]},
        "lacunae": result["rows"],
        "provenance": provenance(),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)


def save_xlsx(result: dict, out_path: Path) -> None:
    from openpyxl import Workbook

    wb = Workbook()
    summary = wb.active
    summary.title = "summary"
    summary.append(["image", "status", "lacuna_count", "border_lacuna_count", "interior_lacuna_count"])
    summary.append([
        result["image_path"].name, "pre-validation", result["lacuna_count"],
        result["border_lacuna_count"], result["interior_lacuna_count"],
    ])
    summary.append([])
    summary.append(["Pre-validation, pixel units. Statistics below are over interior (on_border False) lacunae only."])
    summary.append(["metric", "mean", "median", "sd", "units", "n"])
    stats = result["summary"]
    for field, unit in LACUNA_SUMMARY_METRICS:
        s = stats[field]
        summary.append([field, s["mean"], s["median"], s["sd"], unit, stats["interior_lacuna_count"]])

    per_lacuna = wb.create_sheet("per_lacuna")
    per_lacuna.append(LACUNA_MEASUREMENT_FIELDS)
    for m in result["rows"]:
        per_lacuna.append([m[f] for f in LACUNA_MEASUREMENT_FIELDS])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)


def write_outputs(result: dict, out_root: Path) -> None:
    """The lacuna files of one image under out_root (the results layout)."""
    label = image_label(result["image_path"])
    save_overlay(result["display"], result["labels"], result["kept"],
                 result_path(out_root, label, config.SECTION_LACUNAE, config.SUFFIX_LACUNAE_OUTLINES))
    save_label_image(result["labels"], result["kept"],
                     result_path(out_root, label, config.SECTION_LACUNAE, config.SUFFIX_LACUNA_LABELS))
    save_detection_json(result, result_path(out_root, label, config.SECTION_LACUNAE,
                                            config.SUFFIX_LACUNAE_DETECTION))
    save_xlsx(result, result_path(out_root, label, config.SECTION_LACUNAE, config.SUFFIX_LACUNAE_RESULTS + ".xlsx"))
    save_json(result, result_path(out_root, label, config.SECTION_LACUNAE, config.SUFFIX_LACUNAE_RESULTS + ".json"))


def image_paths(args) -> list[Path]:
    """The images named by --image or --dir (sorted *.tif)."""
    if args.image:
        if not args.image.is_file():
            raise FileNotFoundError(f"No such file: {args.image}")
        return [args.image]
    if not args.dir.is_dir():
        raise NotADirectoryError(f"No such directory: {args.dir}")
    return sorted(args.dir.glob("*.tif"))


def add_input_arguments(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--image", type=Path, help="One .tif image.")
    group.add_argument("--dir", type=Path, help="A folder of .tif images.")
    parser.add_argument(
        "-o", "--out", type=Path, default=config.RESULTS_DIR,
        help="Results folder (default: results/). Each image gets its own subfolder, named by its label; "
             "a folder run of src/canaliculi.py also writes all_images/summary_all_images.xlsx and .csv there.",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Lacuna detection and measurement (pre-validation, px).")
    add_input_arguments(parser)
    args = parser.parse_args()

    for image_path in image_paths(args):
        result = analyse_image(image_path)
        out_dir = args.out / image_label(image_path) / config.SECTION_LACUNAE
        write_outputs(result, args.out)
        s = result["summary"]["area_px2"]
        print(
            f"{image_path.name}: lacunae={result['lacuna_count']} "
            f"(interior {result['interior_lacuna_count']}, border {result['border_lacuna_count']})  "
            f"median interior area={s['median']} px^2  -> {out_dir}"
        )


if __name__ == "__main__":
    main()
