"""EXPERIMENTAL re-segmentation: multi-Otsu (3-class) threshold + marker-
controlled watershed, to replace the single-global-threshold approach in
count_lacunae.py, which fuses lacunae with the canalicular mesh in dense
fields (the whole blob then fails the max-area/solidity/aspect filters and
gets rejected, undercounting badly).

STATUS: v2-RAW, pre-validation. Counts and measurements here are NOT yet
size/shape-filtered or validated against ground truth (Mahmoud's ImageJ
counts). The widened "sanity check" filters deliberately let through small
mesh specks and some elongated/fused objects alongside real lacunae -- do
not treat these numbers as final. Parameters below are candidates only and
are kept out of config.py until validated.

Approach:
    1. Multi-Otsu (3-class) threshold on the red channel's own histogram
       (background / canalicular mesh / lacunae); the upper cut isolates
       the bright lacuna population per-image, no global constant.
    2. Distance transform + marker-controlled watershed, with seeds placed
       per connected component at that component's own relative
       distance-transform maxima (a fraction of ITS OWN peak, so it scales
       with each blob's size) -- this carves a lacuna away from thin
       attached mesh by thickness, instead of losing it to fusion.
    3. Widened shape/size filters as a final sanity check (not the primary
       gate), to avoid re-introducing the original rejection problem.

Border handling: objects touching the image edge are KEPT (they count
toward lacuna_count) and flagged with on_border=True per object, rather than
dropped -- an edge-touching cell is still a real lacuna, just one whose
size/shape measurements are truncated by the field of view. Downstream
stats should filter on on_border, not this script. Set EXCLUDE_BORDER_OBJECTS
below to restore the old drop-them behaviour for comparison.

Min-area filter: TEST_MIN_AREA_PX2 is still a rough guess (not yet derived
from data). Use --report-area-distribution (see main()) to print the pooled
area distribution of interior (non-border) kept objects across a directory
of images before deciding whether/how to raise it -- do not bump this
number without looking at that distribution first.

Outputs, per image, under results/count/<image_stem_with_underscores>/:
    overlay.png        original image with kept objects outlined in green
    measurements.xlsx   "summary" sheet (image, lacuna_count, border_count,
                         interior_count, then mean/median/SD over INTERIOR
                         objects only for area/axis lengths/aspect_ratio/
                         eccentricity/solidity) + "per_lacuna" sheet (one
                         row per kept object, including on_border)
    measurements.json   same per-lacuna measurements + counts + a "summary"
                         block (same interior-only stats) + the parameters
                         used for this run

Summary stats are computed over on_border=False objects only -- border
objects are truncated by the field of view, so their size/shape would bias
the stats. Still v2-RAW / pre-validation: PIXEL_SIZE_UM is None, so
everything here is in pixels, and none of this has been checked against
Mahmoud's ImageJ ground truth yet.

Usage:
    python src/segment_lacunae_v2.py --dir data/WT
    python src/segment_lacunae_v2.py --dir data/WT --report-area-distribution
    python src/segment_lacunae_v2.py --image data/WT/example.tif
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from skimage import filters, measure, morphology, segmentation
from skimage.io import imsave

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from count_lacunae import load_channel  # noqa: E402

# --- Candidate parameters (NOT in config.py yet -- see module docstring) ---
SEED_PROMINENCE_FRACTION = 0.3
DESPECKLE_OPENING_RADIUS_PX = 1
TEST_MIN_AREA_PX2 = 400
# ^ Chosen from --report-area-distribution over all 8 WT images (n=177
# interior objects): 45% of objects (79/177) piled up against the old
# floor of 80, in [81, 373) px^2 -- a censored speck population, not real
# lacunae. The sorted areas show the widest gap between consecutive values
# in that region is 346 -> 429 px^2. 400 sits inside that gap, just above
# the top of the speck pileup and below the start of the real-lacuna tail
# (which continues smoothly from there out past 5900). Not yet validated
# against Mahmoud's ImageJ ground truth -- revisit if those disagree.
TEST_MAX_AREA_FRACTION_OF_IMAGE = 0.05
TEST_MIN_SOLIDITY = 0.5
TEST_ASPECT_RATIO_MAX = 6.0
EXCLUDE_BORDER_OBJECTS = False  # False = keep + flag on_border (current default)

COUNT_DIR = config.RESULTS_DIR / "count"


def multiotsu_lacuna_mask(channel: np.ndarray) -> tuple[np.ndarray, float]:
    """3-class Otsu on this image's own histogram; top-class cut isolates
    the bright lacuna population from the dimmer canalicular mesh."""
    try:
        thresholds = filters.threshold_multiotsu(channel, classes=3)
        t_hi = float(thresholds[-1])
    except ValueError:
        # Degenerate histogram (e.g. near-constant field) -- fall back.
        t_hi = float(filters.threshold_otsu(channel))

    mask = channel >= t_hi
    mask = morphology.remove_small_holes(mask, area_threshold=20)
    if DESPECKLE_OPENING_RADIUS_PX > 0:
        mask = morphology.opening(mask, morphology.disk(DESPECKLE_OPENING_RADIUS_PX))
    return mask, t_hi


def watershed_split(mask: np.ndarray) -> np.ndarray:
    """Separate fused blobs by thickness: distance transform + seeds at
    each connected component's own relative distance-transform maxima,
    then marker-controlled watershed to carve the component along its
    thin necks rather than keeping it as one ragged merged region."""
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


def filter_regions(label_image: np.ndarray) -> list[tuple]:
    """Return [(region, on_border), ...] for objects passing the sanity-check
    filters. Border-touching objects are kept (flagged), not dropped, unless
    EXCLUDE_BORDER_OBJECTS is set True."""
    rows, cols = label_image.shape
    max_area = TEST_MAX_AREA_FRACTION_OF_IMAGE * rows * cols
    kept = []
    for region in measure.regionprops(label_image):
        if region.area < TEST_MIN_AREA_PX2:
            continue
        if region.area > max_area:
            continue
        if region.solidity < TEST_MIN_SOLIDITY:
            continue
        minor = region.axis_minor_length
        major = region.axis_major_length
        aspect = (major / minor) if minor > 0 else float("inf")
        if aspect > TEST_ASPECT_RATIO_MAX:
            continue

        min_row, min_col, max_row, max_col = region.bbox
        on_border = min_row == 0 or min_col == 0 or max_row == rows or max_col == cols
        if on_border and EXCLUDE_BORDER_OBJECTS:
            continue

        kept.append((region, on_border))
    return kept


def segment_image(image_path: Path):
    display, channel = load_channel(image_path)
    mask, t_hi = multiotsu_lacuna_mask(channel)
    labels = watershed_split(mask)
    kept = filter_regions(labels)
    return display, labels, kept, t_hi


# --- Per-lacuna measurements -------------------------------------------------

MEASUREMENT_FIELDS = [
    "lacuna_id",
    "area",
    "major_axis_length",
    "minor_axis_length",
    "aspect_ratio",
    "eccentricity",
    "solidity",
    "orientation",
    "centroid_row",
    "centroid_col",
    "on_border",
    "units",
]


def region_to_measurement(lacuna_id: int, region, on_border: bool, precision: int) -> dict:
    minor = region.axis_minor_length
    major = region.axis_major_length
    aspect_ratio = (major / minor) if minor > 0 else float("inf")
    row, col = region.centroid
    return {
        "lacuna_id": lacuna_id,
        "area": round(float(region.area), precision),
        "major_axis_length": round(float(major), precision),
        "minor_axis_length": round(float(minor), precision),
        "aspect_ratio": round(float(aspect_ratio), precision),
        "eccentricity": round(float(region.eccentricity), precision),
        "solidity": round(float(region.solidity), precision),
        "orientation": round(float(region.orientation), precision),
        "centroid_row": round(float(row), precision),
        "centroid_col": round(float(col), precision),
        "on_border": bool(on_border),
        "units": "px",
    }


def measurements_for(kept: list[tuple], precision: int = 4) -> list[dict]:
    return [
        region_to_measurement(i, region, on_border, precision)
        for i, (region, on_border) in enumerate(kept, start=1)
    ]


# --- Per-image summary (interior lacunae only) -------------------------

SUMMARY_METRICS = [
    ("area", "px"),
    ("major_axis_length", "px"),
    ("minor_axis_length", "px"),
    ("aspect_ratio", "unitless"),
    ("eccentricity", "unitless"),
    ("solidity", "unitless"),
]


def summarize_interior(measurements: list[dict], precision: int) -> dict:
    """Mean/median/SD over on_border=False measurements only, for area,
    axis lengths, aspect_ratio, eccentricity, solidity. SD is sample SD
    (ddof=1); None when fewer than 2 interior objects (undefined)."""
    interior = [m for m in measurements if not m["on_border"]]
    n = len(interior)

    stats = {"interior_lacuna_count": n, "units": "px"}
    for field, _ in SUMMARY_METRICS:
        values = np.array([m[field] for m in interior], dtype=float)
        if n == 0:
            mean = median = sd = None
        else:
            mean = round(float(values.mean()), precision)
            median = round(float(np.median(values)), precision)
            sd = round(float(values.std(ddof=1)), precision) if n >= 2 else None
        stats[field] = {"mean": mean, "median": median, "sd": sd}
    return stats


# --- Output -------------------------------------------------------------

def image_output_dir(image_path: Path) -> Path:
    """results/count/<image_stem_with_spaces_replaced_by_underscores>/"""
    safe_stem = image_path.stem.replace(" ", "_")
    return COUNT_DIR / safe_stem


def save_overlay(display_uint8: np.ndarray, label_image: np.ndarray, kept: list[tuple], out_path: Path) -> None:
    kept_ids = {region.label for region, _ in kept}
    kept_mask = np.isin(label_image, list(kept_ids)) if kept_ids else np.zeros_like(label_image, dtype=bool)
    boundaries = segmentation.find_boundaries(kept_mask, mode="outer")
    overlay = display_uint8.copy()
    overlay[boundaries] = [0, 255, 0]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    imsave(out_path, overlay, check_contrast=False)


def save_xlsx(
    image_name: str,
    measurements: list[dict],
    border_count: int,
    interior_count: int,
    stats: dict,
    out_path: Path,
) -> None:
    from openpyxl import Workbook

    wb = Workbook()

    summary = wb.active
    summary.title = "summary"
    summary.append(["image", "lacuna_count", "border_count", "interior_count"])
    summary.append([image_name, len(measurements), border_count, interior_count])
    summary.append([])
    summary.append(["v2-raw / pre-validation -- stats below over interior (on_border=False) lacunae only"])
    summary.append(["metric", "mean", "median", "sd", "units", "n"])
    for field, unit in SUMMARY_METRICS:
        s = stats[field]
        summary.append([field, s["mean"], s["median"], s["sd"], unit, stats["interior_lacuna_count"]])

    per_lacuna = wb.create_sheet("per_lacuna")
    per_lacuna.append(MEASUREMENT_FIELDS)
    for m in measurements:
        per_lacuna.append([m[field] for field in MEASUREMENT_FIELDS])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)


def save_json(
    image_path: Path,
    measurements: list[dict],
    t_hi: float,
    border_count: int,
    interior_count: int,
    stats: dict,
    out_path: Path,
) -> None:
    payload = {
        "status": "v2-raw",
        "note": (
            "Not yet size/shape-filtered or validated against ground truth. "
            "Still includes small mesh specks and some elongated/fused objects. "
            "Border objects are kept (on_border=true), not dropped. Summary "
            "stats below are over interior (on_border=false) lacunae only."
        ),
        "image": str(image_path),
        "units": "px",
        "lacuna_count": len(measurements),
        "border_count": border_count,
        "interior_count": interior_count,
        "summary": stats,
        "parameters": {
            "channel": config.CHANNEL,
            "channel_axis": config.CHANNEL_AXIS,
            "invert_signal": config.INVERT_SIGNAL,
            "pixel_size_um": config.PIXEL_SIZE_UM,
            "threshold_method": "multiotsu_3class_top",
            "computed_threshold_t_hi": t_hi,
            "seed_prominence_fraction": SEED_PROMINENCE_FRACTION,
            "despeckle_opening_radius_px": DESPECKLE_OPENING_RADIUS_PX,
            "min_area_px2": TEST_MIN_AREA_PX2,
            "max_area_fraction_of_image": TEST_MAX_AREA_FRACTION_OF_IMAGE,
            "min_solidity": TEST_MIN_SOLIDITY,
            "aspect_ratio_max": TEST_ASPECT_RATIO_MAX,
            "exclude_border_objects": EXCLUDE_BORDER_OBJECTS,
        },
        "lacunae": measurements,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)


def print_summary(stats: dict) -> None:
    print(f"  summary (interior n={stats['interior_lacuna_count']}, units=px):")
    for field, unit in SUMMARY_METRICS:
        s = stats[field]
        mean = "n/a" if s["mean"] is None else f"{s['mean']:.2f}"
        median = "n/a" if s["median"] is None else f"{s['median']:.2f}"
        sd = "n/a" if s["sd"] is None else f"{s['sd']:.2f}"
        print(f"    {field:20s} mean={mean:>10s}  median={median:>10s}  sd={sd:>10s}  ({unit})")


def process(image_path: Path) -> tuple[int, int, int, list]:
    """Segment one image, write its outputs, and return
    (total_count, border_count, interior_count, interior_areas)."""
    display, labels, kept, t_hi = segment_image(image_path)
    measurements = measurements_for(kept, precision=config.CSV_FLOAT_PRECISION)

    border_count = sum(1 for _, on_border in kept if on_border)
    interior_count = len(kept) - border_count
    interior_areas = [float(region.area) for region, on_border in kept if not on_border]
    stats = summarize_interior(measurements, precision=config.CSV_FLOAT_PRECISION)

    out_dir = image_output_dir(image_path)
    save_overlay(display, labels, kept, out_dir / "overlay.png")
    save_xlsx(image_path.name, measurements, border_count, interior_count, stats, out_dir / "measurements.xlsx")
    save_json(image_path, measurements, t_hi, border_count, interior_count, stats, out_dir / "measurements.json")

    print(
        f"{image_path.name}: total={len(kept)}  border={border_count}  "
        f"interior={interior_count}  t_hi={t_hi:.4f}  -> {out_dir}"
    )
    print_summary(stats)
    return len(kept), border_count, interior_count, interior_areas


def print_area_distribution(areas: list[float]) -> None:
    if not areas:
        print("No interior objects to report a distribution for.")
        return
    arr = np.array(areas)
    percentiles = [5, 10, 25, 50, 75, 90, 95]
    pct_values = np.percentile(arr, percentiles)

    print()
    print(f"Pooled interior-object area distribution (n={arr.size}):")
    print(f"  min={arr.min():.0f}  max={arr.max():.0f}  mean={arr.mean():.1f}  median={np.median(arr):.1f}")
    for p, v in zip(percentiles, pct_values):
        print(f"  p{p:02d} = {v:.0f} px^2")

    # Coarse histogram so gaps between "specks" and "lacunae" are visible.
    n_bins = 20
    counts, edges = np.histogram(arr, bins=n_bins)
    print("  histogram:")
    for i in range(n_bins):
        if counts[i] == 0:
            continue
        print(f"    [{edges[i]:7.0f}, {edges[i+1]:7.0f}) : {counts[i]:3d} {'#' * int(counts[i])}")

    print()
    print("  sorted areas:")
    print("   " + ", ".join(f"{a:.0f}" for a in sorted(arr.tolist())))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="v2-RAW experimental multi-Otsu + watershed lacuna segmentation (pre-validation)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--image", type=Path, help="Path to a single .tif image.")
    group.add_argument("--dir", type=Path, help="Directory of .tif images to process.")
    parser.add_argument(
        "--report-area-distribution",
        action="store_true",
        help="After processing, print the pooled area distribution of interior (non-border) kept objects.",
    )
    args = parser.parse_args()

    all_interior_areas: list[float] = []

    if args.image:
        if not args.image.is_file():
            raise FileNotFoundError(f"No such file: {args.image}")
        _, _, _, interior_areas = process(args.image)
        all_interior_areas.extend(interior_areas)
    else:
        if not args.dir.is_dir():
            raise NotADirectoryError(f"No such directory: {args.dir}")
        for image_path in sorted(args.dir.glob("*.tif")):
            _, _, _, interior_areas = process(image_path)
            all_interior_areas.extend(interior_areas)

    if args.report_area_distribution:
        print_area_distribution(all_interior_areas)


if __name__ == "__main__":
    main()
