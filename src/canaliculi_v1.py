"""EXPERIMENTAL per-lacuna canaliculi feature extraction.

STATUS: v1-RAW, pre-validation. Builds on segment_lacunae_v2's lacuna
segmentation (imported, not modified) to additionally trace the canalicular
network and attribute it to individual lacunae. Nothing here has been
checked against ground truth. Parameters below are candidates only and are
kept out of config.py until validated. Everything stays in PIXEL units --
PIXEL_SIZE_UM is None, so nothing is converted to microns.

Method:
    1. Segment lacunae with segment_lacunae_v2's multi-Otsu + watershed
       approach (imported as-is).
    2. Segment the canalicular network: red signal above background (the
       LOWER of the two multi-Otsu cuts -- background vs. everything else,
       computed per-image, same idea as v2's threshold but one level down),
       minus a small buffer around the lacuna bodies, despeckled by size
       (not by erosion, which would erase 1px-wide threads), then
       skeletonized to 1px centerlines.
    3. Every skeleton pixel is assigned to its NEAREST lacuna via a single
       Euclidean distance transform seeded from the lacuna mask (a
       Voronoi-by-distance partition of the field between lacunae). This is
       an approximation in dense fields where two lacunae's true territory
       doesn't follow a clean Euclidean split -- accepted, per spec.
    4. Per lacuna, using skan on that lacuna's own skeleton subset:
       - build the pixel/branch graph with skan and drop cycle branches
         (branch-type 3 -- no defined tip, not a canaliculus);
       - within each connected piece of that subset, the node closest to
         the lacuna body (by the same distance transform) is the "root"
         (where the canaliculus meets the cell body); every other degree-1
         node is a "tip";
       - each root-to-tip path (summing skan's branch-distance along the
         unique tree path, so branch points partway along a canaliculus
         are handled correctly) is counted as one canaliculus, and its
         length is that path's total distance, traced only as far as the
         thread actually continues (no fixed search radius);
       - a piece of the subset that never gets within MAX_ROOT_GAP_PX of
         the lacuna is treated as unreachable (not a canaliculus of this
         lacuna) rather than fabricating a long "gap-jump" canaliculus.

Border lacunae (on_border=True, from v2) are kept in the per-lacuna table
and drawn in the verification image, but excluded from the per-image
summary stats -- their canaliculi are truncated by the field of view.

Outputs, per image, under results/canaliculi/<image_stem_with_underscores>/:
    verification.png   original image at near-full brightness; every lacuna
                        and its owned canaliculi drawn in one unique,
                        randomly (but reproducibly) assigned color, so the
                        colored tracing can be checked directly against the
                        real red canaliculi underneath
    measurements.xlsx   "summary" sheet (interior-only mean/median/SD of
                         canaliculi_count and mean_canaliculus_length_px)
                         + "per_lacuna" sheet (one row per lacuna, incl.
                         border ones, flagged on_border)
    measurements.json   same data + the parameters used for this run

Usage:
    python src/canaliculi_v1.py --dir data/WT
    python src/canaliculi_v1.py --image data/WT/example.tif
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import deque
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from skimage import filters, morphology, segmentation
from skimage.io import imsave
from skan import Skeleton, summarize

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from count_lacunae import load_channel  # noqa: E402
import segment_lacunae_v2 as seg2  # noqa: E402

# --- Candidate parameters (NOT in config.py yet -- see module docstring) ---
# Buffer (px) eroded away from the canaliculi candidate mask around each
# lacuna body, so the lacuna's own bright rim isn't mistaken for a stub of
# canaliculus right at the boundary.
LACUNA_DILATION_PX = 2

# Candidate canaliculus fragments smaller than this (px^2) are dropped as
# thresholding noise before skeletonizing. Kept deliberately small so a
# real, thin, short thread survives -- despeckling here is by pixel COUNT,
# never by erosion/opening (which would delete 1px-wide real threads).
MIN_THREAD_OBJECT_PX2 = 8

# A connected skeleton fragment whose closest point to a lacuna is farther
# than this (px) is treated as not actually attached to that lacuna (an
# orphan fragment from a gap in thresholding), not as one long canaliculus.
MAX_ROOT_GAP_PX = 15

# Cosmetic only: how much the owned-skeleton pixels are dilated for
# visibility in the verification PNG. Does not affect any measurement.
# Raised from 1 -> 2 so canaliculi read as brighter/thicker against the
# dimmed background.
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

CANALICULI_DIR = config.RESULTS_DIR / "canaliculi"


# --- Canalicular network segmentation -----------------------------------

def total_signal_mask(channel: np.ndarray) -> tuple[np.ndarray, float]:
    """Lower of the two multi-Otsu (3-class) cuts on this image's own
    histogram: background vs. everything else (mesh + lacunae). Same
    per-image-adaptive idea as v2's threshold, one level down."""
    try:
        thresholds = filters.threshold_multiotsu(channel, classes=3)
        t_lo = float(thresholds[0])
    except ValueError:
        t_lo = float(filters.threshold_otsu(channel))
    return channel >= t_lo, t_lo


def build_lacuna_maps(labels: np.ndarray, kept: list[tuple]) -> tuple[np.ndarray, np.ndarray]:
    """Return (lacuna_mask, lacuna_id_map). lacuna_id_map is 0 outside any
    kept lacuna, else the lacuna's 1..N id (same numbering as v2's
    per-lacuna measurements)."""
    lacuna_id_map = np.zeros(labels.shape, dtype=np.int32)
    for lacuna_id, (region, _on_border) in enumerate(kept, start=1):
        lacuna_id_map[labels == region.label] = lacuna_id
    return lacuna_id_map > 0, lacuna_id_map


def canaliculi_candidate_mask(channel: np.ndarray, lacuna_mask: np.ndarray) -> tuple[np.ndarray, float]:
    signal, t_lo = total_signal_mask(channel)
    buffered_lacunae = morphology.dilation(lacuna_mask, morphology.disk(LACUNA_DILATION_PX))
    candidate = signal & ~buffered_lacunae
    candidate = morphology.remove_small_objects(candidate, min_size=MIN_THREAD_OBJECT_PX2)
    return candidate, t_lo


def nearest_lacuna_map(lacuna_id_map: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """For every pixel, (distance to the nearest lacuna pixel, that
    lacuna's id) -- a Euclidean Voronoi partition seeded from the lacunae."""
    dist, indices = ndi.distance_transform_edt(lacuna_id_map == 0, return_indices=True)
    nearest_id = lacuna_id_map[indices[0], indices[1]]
    return dist, nearest_id


# --- Per-lacuna canaliculi tracing (skan) -------------------------------

def _node_key(row: float, col: float) -> tuple[int, int]:
    return (int(round(row)), int(round(col)))


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


# --- Per-lacuna measurements ---------------------------------------------

def canaliculi_measurements(
    kept: list[tuple],
    skeleton: np.ndarray,
    nearest_id: np.ndarray,
    dist_to_lacuna: np.ndarray,
    precision: int,
) -> tuple[list[dict], dict[int, list[float]]]:
    measurements = []
    lengths_by_lacuna: dict[int, list[float]] = {}
    for lacuna_id, (_region, on_border) in enumerate(kept, start=1):
        owned_skeleton = skeleton & (nearest_id == lacuna_id)
        lengths = trace_lacuna_canaliculi(owned_skeleton, dist_to_lacuna)
        lengths_by_lacuna[lacuna_id] = lengths

        count = len(lengths)
        total_length = float(sum(lengths))
        mean_length = total_length / count if count else 0.0
        measurements.append(
            {
                "lacuna_id": lacuna_id,
                "canaliculi_count": count,
                "total_length_px": round(total_length, precision),
                "mean_canaliculus_length_px": round(mean_length, precision),
                "on_border": bool(on_border),
                "units": "px",
            }
        )
    return measurements, lengths_by_lacuna


SUMMARY_METRICS = [
    ("canaliculi_count", "unitless"),
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

def image_output_dir(image_path: Path) -> Path:
    safe_stem = image_path.stem.replace(" ", "_")
    return CANALICULI_DIR / safe_stem


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
    nearest_id: np.ndarray,
    lacuna_ids: list[int],
    colors: dict[int, tuple[int, int, int]],
    out_path: Path,
) -> None:
    vis = (display_uint8.astype(np.float32) * VIS_DIM_FACTOR).astype(np.uint8)
    for lacuna_id in lacuna_ids:
        color = colors[lacuna_id]
        boundary = segmentation.find_boundaries(lacuna_id_map == lacuna_id, mode="outer")
        vis[boundary] = color

        owned_skeleton = skeleton & (nearest_id == lacuna_id)
        if owned_skeleton.any():
            owned_skeleton = morphology.dilation(owned_skeleton, morphology.disk(VIS_SKELETON_DILATION_PX))
        vis[owned_skeleton] = color

    out_path.parent.mkdir(parents=True, exist_ok=True)
    imsave(out_path, vis, check_contrast=False)


def save_xlsx(image_name: str, measurements: list[dict], stats: dict, out_path: Path) -> None:
    from openpyxl import Workbook

    wb = Workbook()

    summary = wb.active
    summary.title = "summary"
    summary.append(["image", "lacuna_count", "interior_lacuna_count"])
    summary.append([image_name, len(measurements), stats["interior_lacuna_count"]])
    summary.append([])
    summary.append(["v1-raw / pre-validation -- stats below over interior (on_border=False) lacunae only"])
    summary.append(["metric", "mean", "median", "sd", "units", "n"])
    for field, unit in SUMMARY_METRICS:
        s = stats[field]
        summary.append([field, s["mean"], s["median"], s["sd"], unit, stats["interior_lacuna_count"]])

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
    out_path: Path,
) -> None:
    payload = {
        "status": "v1-raw",
        "note": (
            "Not yet validated against ground truth. Canaliculus count/length "
            "come from a per-lacuna Euclidean-nearest skeleton assignment, an "
            "approximation in dense fields. Border lacunae are kept "
            "(on_border=true) but excluded from summary stats."
        ),
        "image": str(image_path),
        "units": "px",
        "lacuna_count": len(measurements),
        "summary": stats,
        "parameters": {
            "pixel_size_um": config.PIXEL_SIZE_UM,
            "lacuna_segmentation": "segment_lacunae_v2 (multi-Otsu 3-class + watershed; see that module)",
            "total_signal_threshold_t_lo": t_lo,
            "lacuna_top_class_threshold_t_hi": t_hi,
            "lacuna_dilation_px": LACUNA_DILATION_PX,
            "min_thread_object_px2": MIN_THREAD_OBJECT_PX2,
            "max_root_gap_px": MAX_ROOT_GAP_PX,
        },
        "lacunae": measurements,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)


def print_summary(stats: dict) -> None:
    for field, unit in SUMMARY_METRICS:
        s = stats[field]
        mean = "n/a" if s["mean"] is None else f"{s['mean']:.2f}"
        median = "n/a" if s["median"] is None else f"{s['median']:.2f}"
        sd = "n/a" if s["sd"] is None else f"{s['sd']:.2f}"
        print(f"    {field:28s} mean={mean:>10s}  median={median:>10s}  sd={sd:>10s}  ({unit})")


def process(image_path: Path) -> dict:
    display, channel = load_channel(image_path)
    _display2, labels, kept, t_hi = seg2.segment_image(image_path)

    lacuna_mask, lacuna_id_map = build_lacuna_maps(labels, kept)
    candidate, t_lo = canaliculi_candidate_mask(channel, lacuna_mask)
    skeleton = morphology.skeletonize(candidate)
    dist_to_lacuna, nearest_id = nearest_lacuna_map(lacuna_id_map)

    measurements, _lengths_by_lacuna = canaliculi_measurements(
        kept, skeleton, nearest_id, dist_to_lacuna, precision=config.CSV_FLOAT_PRECISION
    )
    stats = summarize_interior(measurements, precision=config.CSV_FLOAT_PRECISION)

    out_dir = image_output_dir(image_path)
    colors = lacuna_colors(len(kept))
    all_ids = list(range(1, len(kept) + 1))
    save_verification(display, lacuna_id_map, skeleton, nearest_id, all_ids, colors, out_dir / "verification.png")
    save_xlsx(image_path.name, measurements, stats, out_dir / "measurements.xlsx")
    save_json(image_path, measurements, stats, t_lo, t_hi, out_dir / "measurements.json")

    mean_count = stats["canaliculi_count"]["mean"]
    mean_length = stats["mean_canaliculus_length_px"]["mean"]
    mean_count_s = "n/a" if mean_count is None else f"{mean_count:.2f}"
    mean_length_s = "n/a" if mean_length is None else f"{mean_length:.2f}"
    print(
        f"{image_path.name}: lacunae={len(kept)}  mean_canaliculi_per_cell={mean_count_s}  "
        f"mean_canaliculus_length_px={mean_length_s}  -> {out_dir}"
    )
    print_summary(stats)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="v1-RAW experimental per-lacuna canaliculi extraction (pre-validation)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--image", type=Path, help="Path to a single .tif image.")
    group.add_argument("--dir", type=Path, help="Directory of .tif images to process.")
    args = parser.parse_args()

    if args.image:
        if not args.image.is_file():
            raise FileNotFoundError(f"No such file: {args.image}")
        process(args.image)
    else:
        if not args.dir.is_dir():
            raise NotADirectoryError(f"No such directory: {args.dir}")
        for image_path in sorted(args.dir.glob("*.tif")):
            process(image_path)


if __name__ == "__main__":
    main()
