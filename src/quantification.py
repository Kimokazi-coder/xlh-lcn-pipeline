"""Quantification of the lacunae and the canalicular network (pre-validation, px).

Every measured number of this project is computed here. Detection draws and
saves; this script measures. Nothing here changes a threshold, a parameter or
an algorithm: each measure is the one the detection modules used to compute,
moved over unchanged.

What it reads, per image, from a results folder that src/lacunae.py and
src/canaliculi.py have already written:
    1_lacunae/<label>_lacuna_labels.png          0 outside a kept lacuna, else
                                                 its 1..N id (the numbering of
                                                 every output)
    1_lacunae/<label>_lacunae_detection.json     parameters and the lacuna cut
    2_canaliculi/<label>_canaliculi_mask.png     the network mask, after bridging
    2_canaliculi/<label>_canaliculi_skeleton.png the one-pixel skeleton
    2_canaliculi/<label>_canaliculi_vascular_mask.png   broad bright structures,
                                                 already dilated by
                                                 canaliculi.FLAGGED_DILATION_PX
    2_canaliculi/<label>_canaliculi_bridged_pixels.png  the pixels gap bridging
                                                 added, which have no signal
                                                 under them
    2_canaliculi/<label>_canaliculi_graph.pickle the cleaned graph and ownership
    2_canaliculi/<label>_canaliculi_detection.json      parameters, the network
                                                 cut and the bridges

What it writes:
    5_quantification/<label>_quantification.json   every number, the parameters
                                                   of both stages and provenance
    5_quantification/<label>_quantification.xlsx   the same as sheets
    5_quantification/<label>_quantification.pdf    the same to read
    all_images/quantification/quantification_all_images.csv, .xlsx and .pdf
                                                   one row per image

Usage, from the repository root:
    python src/quantification.py --dir data/WT
    python src/quantification.py --image "data/WT/543-2.tif"
    python src/quantification.py --dir data/WT -o OTHER_FOLDER
    python src/quantification.py --dir data/WT -m ROI_MASK_FOLDER

Pre-validation: no number here has been checked against manual (ImageJ) counts.
Pixel units: the images carry no micron calibration, so lengths are px, areas
px^2 and densities px^-1. Statistics are over interior lacunae only (those not
touching the frame edge), as in every earlier output.
"""
from __future__ import annotations

import argparse
import csv
import json
import pickle
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from skimage import measure, morphology
from skimage.io import imread

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canaliculi  # noqa: E402
import lacunae  # noqa: E402


# The measure lists. They live here because this is where the measures are.
# While the split is in progress they still name the lists of the detection
# modules, which the next step moves over unchanged.
LACUNA_MEASUREMENT_FIELDS = lacunae.LACUNA_MEASUREMENT_FIELDS
LACUNA_SUMMARY_METRICS = lacunae.LACUNA_SUMMARY_METRICS
CELL_METRICS = canaliculi.CELL_METRICS
NORMALISED_METRICS = canaliculi.NORMALISED_METRICS
NETWORK_V2_METRICS = canaliculi.NETWORK_V2_METRICS
FIELD_V2 = canaliculi.FIELD_V2
FIELD_V2_KEYS = canaliculi.FIELD_V2_KEYS
FIELD_UNITS = canaliculi.FIELD_UNITS
RING_RADII_PX = canaliculi.RING_RADII_PX


# Canalicular width
# The local full width (px) of a thread at a skeleton pixel: twice the
# Euclidean distance from that pixel to the nearest pixel outside the
# canalicular mask. On a one-pixel centre line this is the standard
# distance-transform width. It is a new measure, added with this script.
#
# Which mask: the mask with real signal under it, that is the saved network mask
# minus the pixels gap bridging added. A bridge is drawn, not measured, so its
# pixels would report the width of a drawn line.
#
# Which pixels: skeleton pixels that lie on that mask, outside the lacuna buffer
# (canaliculi.LACUNA_DILATION_PX around every lacuna body, which the mask
# already excludes) and outside the vascular mask, which is already dilated by
# canaliculi.FLAGGED_DILATION_PX. Inside a vascular canal the bright structure
# is not a canaliculus, so its width is not a thread width.
#
# Limits, to keep in mind for every number below: the threads are only about 2
# to 6 px wide, so the width is close to the pixel grid and is quantised in
# steps of about 1 px; it moves with the threshold, because a lower cut makes
# every thread wider; and it is not validated against any manual measurement.
WIDTH_PERCENTILES = (10, 90)

# (name, unit, extra decimals beyond config.CSV_FLOAT_PRECISION, summary column)
WIDTH_IMAGE_METRICS = [
    ("width_mean_px", "px", 0, "canalicular width mean (px)"),
    ("width_median_px", "px", 0, "canalicular width median (px)"),
    ("width_p10_px", "px", 0, "canalicular width p10 (px)"),
    ("width_p90_px", "px", 0, "canalicular width p90 (px)"),
    ("width_pixels_used", "count", 0, "canalicular width pixels used"),
]

# Per lacuna, the mean width over the pixels of its own 30 px ring.
WIDTH_CELL_METRICS = [
    ("ring_width_mean_r30_px", "px", 0, "canalicular width in ring 30 px per cell (px)"),
]

HEADLINE_MEASURES = [
    "roots_count",
    "ring_length_r30_px",
    "field.canalicular_length_density_per_px",
    "width.width_median_px",
    "ring_width_mean_r30_px",
]

NOTE = (
    "Pre-validation: not checked against manual counts. Pixel units. Headline "
    "measures: roots_count, ring_length_r30_px, the per-field "
    "canalicular_length_density_per_px, and the canalicular width "
    "(width_median_px per image, ring_width_mean_r30_px per lacuna). "
    "owned_length_px, edge_count and mean_edge_length_px depend on which cell "
    "owns which thread, which is unbounded in distance; they are network "
    "descriptors, and edge_count is not canaliculi per cell. The width is "
    "quantised by the pixel grid (threads are about 2 to 6 px wide) and moves "
    "with the threshold. Summary statistics cover interior lacunae only."
)


# Reading what detection saved

def quant_path(out_root: Path, label: str, extension: str) -> Path:
    """results/<label>/5_quantification/<label>_quantification.<extension>."""
    return lacunae.result_path(out_root, label, config.SECTION_QUANTIFICATION,
                               config.SUFFIX_QUANTIFICATION + extension)


def summary_path(out_root: Path, extension: str) -> Path:
    """results/all_images/quantification/quantification_all_images.<extension>."""
    return lacunae.all_images_path(out_root, config.QUANT_SUMMARY_NAME + extension,
                                   config.ALL_IMAGES_QUANT_DIR)


def _read_mask(path: Path) -> np.ndarray:
    """A saved 0 or 255 mask as bool."""
    return np.asarray(imread(path)) > 0


def load_detection(out_root: Path, label: str) -> dict:
    """Everything detection saved for one image. Raises FileNotFoundError with
    the command to run when a file is missing."""
    def lac(suffix):
        return lacunae.result_path(out_root, label, config.SECTION_LACUNAE, suffix)

    def can(suffix):
        return lacunae.result_path(out_root, label, config.SECTION_CANALICULI, suffix)

    needed = {
        "labels": lac(config.SUFFIX_LACUNA_LABELS),
        "lacunae_detection": lac(config.SUFFIX_LACUNAE_DETECTION),
        "mask": can(config.SUFFIX_CANALICULI_MASK),
        "skeleton": can(config.SUFFIX_CANALICULI_SKELETON),
        "vascular": can(config.SUFFIX_CANALICULI_VASCULAR),
        "bridged": can(config.SUFFIX_CANALICULI_BRIDGED),
        "graph": can(config.SUFFIX_CANALICULI_GRAPH),
        "canaliculi_detection": can(config.SUFFIX_CANALICULI_DETECTION),
    }
    missing = [str(p) for p in needed.values() if not p.is_file()]
    if missing:
        raise FileNotFoundError(
            f"{label}: detection output is missing:\n  " + "\n  ".join(missing)
            + "\nRun src/lacunae.py and then src/canaliculi.py on the image first."
        )

    with open(needed["graph"], "rb") as f:
        graph_data = pickle.load(f)
    labels = np.asarray(imread(needed["labels"])).astype(np.int32)
    mask = _read_mask(needed["mask"])
    bridged = _read_mask(needed["bridged"])
    return {
        "label": label,
        "lacuna_id_map": labels,
        "lacuna_mask": labels > 0,
        "mask": mask,
        "thresholded": mask & ~bridged,
        "bridged": bridged,
        "skeleton": _read_mask(needed["skeleton"]),
        "vascular": _read_mask(needed["vascular"]),
        "graph": graph_data["graph"],
        "owner": graph_data["owner"],
        "node_dist": graph_data["node_dist"],
        "edge_owner": graph_data["edge_owner"],
        "lacunae_detection": json.loads(needed["lacunae_detection"].read_text(encoding="utf-8")),
        "canaliculi_detection": json.loads(needed["canaliculi_detection"].read_text(encoding="utf-8")),
    }


def kept_from_labels(lacuna_id_map: np.ndarray) -> list[tuple]:
    """[(region, on_border), ...] in lacuna_id order, the list the measures
    expect. regionprops returns the regions in label order, and the labels are
    the 1..N ids, so region i is lacuna i. on_border is the frame-edge test of
    lacunae.filter_regions, recomputed from the same bounding box."""
    rows, cols = lacuna_id_map.shape
    kept = []
    for region in measure.regionprops(lacuna_id_map):
        min_row, min_col, max_row, max_col = region.bbox
        on_border = min_row == 0 or min_col == 0 or max_row == rows or max_col == cols
        kept.append((region, bool(on_border)))
    return kept


# Measures: the canalicular width

def width_map(thresholded: np.ndarray) -> np.ndarray:
    """Local full width (px) at every pixel of the canalicular mask: twice the
    Euclidean distance transform of that mask."""
    return 2.0 * ndi.distance_transform_edt(thresholded)


def width_sample_mask(detection: dict) -> np.ndarray:
    """The skeleton pixels whose width is measured: on the canalicular mask with
    real signal under it, not a bridged pixel, not in the lacuna buffer and not
    in the vascular mask (which is already dilated)."""
    buffered_lacunae = morphology.dilation(detection["lacuna_mask"],
                                           morphology.disk(canaliculi.LACUNA_DILATION_PX))
    return (detection["skeleton"] & detection["thresholded"] & ~detection["bridged"]
            & ~buffered_lacunae & ~detection["vascular"])


def width_image_measures(width: np.ndarray, sample: np.ndarray, precision: int) -> dict:
    """Mean, median, p10, p90 of the width over the sampled skeleton pixels, and
    how many pixels that is. All None with no usable pixel."""
    values = width[sample]
    if values.size == 0:
        out = {name: None for name, _u, _x, _c in WIDTH_IMAGE_METRICS}
        out["width_pixels_used"] = 0
        return out
    p10, p90 = np.percentile(values, WIDTH_PERCENTILES)
    return {
        "width_mean_px": round(float(values.mean()), precision),
        "width_median_px": round(float(np.median(values)), precision),
        "width_p10_px": round(float(p10), precision),
        "width_p90_px": round(float(p90), precision),
        "width_pixels_used": int(values.size),
    }


def add_width_measures(rows: list[dict], width: np.ndarray, sample: np.ndarray,
                       dist_to_lacuna: np.ndarray, nearest_id: np.ndarray, precision: int) -> None:
    """Append ring_width_mean_r30_px to each per-lacuna row, in place: the mean
    width over the sampled skeleton pixels of that lacuna's 30 px ring, the same
    ownership rule as ring_length_r30_px (within 30 px of a lacuna body, counted
    for the nearest lacuna). None when the ring holds no usable pixel."""
    radius = canaliculi.RING_RADII_PX[0]
    in_ring = sample & (dist_to_lacuna <= radius)
    for row in rows:
        selected = in_ring & (nearest_id == row["lacuna_id"])
        values = width[selected]
        row["ring_width_mean_r30_px"] = round(float(values.mean()), precision) if values.size else None


# Measures: everything that existed before, per lacuna and per field

def network_rows(kept: list[tuple], detection: dict, dist_to_lacuna: np.ndarray,
                 nearest_id: np.ndarray, precision: int) -> list[dict]:
    """Roots, ring lengths and the ownership-dependent measures per lacuna, from
    the graph and the ownership that detection saved. The loop of the former
    canaliculi.measure_cells, unchanged."""
    graph = detection["graph"]
    edge_owner = detection["edge_owner"]
    rings = canaliculi.ring_lengths(detection["skeleton"], dist_to_lacuna, nearest_id, len(kept))

    rows = []
    for lacuna_id, (_region, on_border) in enumerate(kept, start=1):
        lengths = canaliculi.cell_edge_lengths(graph, edge_owner, lacuna_id)
        count = len(lengths)
        total = float(sum(lengths))
        row = {
            "lacuna_id": lacuna_id,
            "on_border": bool(on_border),
            "roots_count": canaliculi.cell_root_count(graph, lacuna_id),
        }
        for radius in canaliculi.RING_RADII_PX:
            row[f"ring_length_r{radius}_px"] = int(rings[radius][lacuna_id])
        row["owned_length_px"] = round(total, precision)
        row["edge_count"] = count
        row["mean_edge_length_px"] = round(total / count if count else 0.0, precision)
        rows.append(row)
    return rows


def measure_cells(kept: list, skeleton: np.ndarray, dist_to_lacuna: np.ndarray,
                  nearest_id: np.ndarray, precision: int) -> dict:
    """Ownership and the per-lacuna network measures from arrays in memory, for a
    caller that has a skeleton but no results folder (the experiment scripts)."""
    own = canaliculi.build_ownership(kept, skeleton, dist_to_lacuna, nearest_id)
    rows = network_rows(kept, {"graph": own["graph"], "edge_owner": own["edge_owner"], "skeleton": skeleton},
                        dist_to_lacuna, nearest_id, precision)
    return {"rows": rows, **own}


def quantify(detection: dict, image_path: Path, roi_mask: np.ndarray | None = None) -> dict:
    """Every measure of one image, from what detection saved."""
    precision = config.CSV_FLOAT_PRECISION
    lacuna_id_map = detection["lacuna_id_map"]
    skeleton = detection["skeleton"]
    kept = kept_from_labels(lacuna_id_map)
    dist_to_lacuna, nearest_id = canaliculi.nearest_lacuna_map(lacuna_id_map)

    # Lacuna shape, the former lacunae.measurements_for.
    shape_rows = [
        lacunae.region_to_measurement(lacuna_id, region, on_border, precision)
        for lacuna_id, (region, on_border) in enumerate(kept, start=1)
    ]
    border = sum(1 for _region, on_border in kept if on_border)

    # Network measures per lacuna, then the appended families.
    net_rows = network_rows(kept, detection, dist_to_lacuna, nearest_id, precision)
    canaliculi.add_normalised_measures(net_rows, lacuna_id_map, dist_to_lacuna, nearest_id, precision)
    canaliculi.add_network_v2_measures(net_rows, skeleton, dist_to_lacuna, nearest_id, precision)

    # The canalicular width, the new measure.
    sample = width_sample_mask(detection)
    width = width_map(detection["thresholded"])
    add_width_measures(net_rows, width, sample, dist_to_lacuna, nearest_id, precision)

    # One row per lacuna: shape first, then the network measures.
    rows = []
    for shape_row, net_row in zip(shape_rows, net_rows):
        assert shape_row["lacuna_id"] == net_row["lacuna_id"]
        assert shape_row["on_border"] == net_row["on_border"]
        merged = dict(shape_row)
        merged.update({k: v for k, v in net_row.items() if k not in merged})
        rows.append(merged)

    field = canaliculi.field_metrics(skeleton, detection["graph"], detection["lacuna_mask"],
                                     len(kept), precision, detection["vascular"], roi_mask)
    return {
        "image_path": image_path,
        "label": detection["label"],
        "lacuna_count": len(kept),
        "border_lacuna_count": border,
        "interior_lacuna_count": len(kept) - border,
        "n_bridges": detection["canaliculi_detection"]["n_bridges"],
        "rows": rows,
        "areas": [row["area_px2"] for row in rows],
        "lacuna_summary": lacunae.summarize_interior(shape_rows, precision),
        "summary": summarize_interior(net_rows, precision),
        "field": field,
        "width": width_image_measures(width, sample, precision),
        "width_values": width[sample],
        "parameters": {
            "lacunae": detection["lacunae_detection"]["parameters"],
            "canaliculi": detection["canaliculi_detection"]["parameters"],
            "quantification": {
                "width_definition": "2 x Euclidean distance transform of the canalicular mask at each skeleton pixel",
                "width_mask": "the saved network mask minus the bridged pixels",
                "width_excluded": ["bridged pixels", "the lacuna buffer", "the dilated vascular mask"],
                "width_percentiles": list(WIDTH_PERCENTILES),
                "ring_radii_px": list(canaliculi.RING_RADII_PX),
                "statistics_over": "interior lacunae only",
            },
        },
    }


def summarize_interior(rows: list[dict], precision: int) -> dict:
    """Interior mean, median and sample SD of every per-lacuna network measure,
    the former canaliculi.summarize_interior with the width added."""
    stats = canaliculi.summarize_interior(rows, precision)
    interior = [r for r in rows if not r["on_border"]]
    for field, _unit, extra, _col in WIDTH_CELL_METRICS:
        values = np.array([r[field] for r in interior if r.get(field) is not None], dtype=float)
        digits = precision + extra
        if values.size == 0:
            mean = median = sd = None
        else:
            mean = round(float(values.mean()), digits)
            median = round(float(np.median(values)), digits)
            sd = round(float(values.std(ddof=1)), digits) if values.size >= 2 else None
        stats[field] = {"mean": mean, "median": median, "sd": sd}
    return stats


# Column order of the per-lacuna table, in four blocks.

def shape_columns() -> list[str]:
    return list(lacunae.LACUNA_MEASUREMENT_FIELDS)


def network_columns() -> list[str]:
    return [f for f, _u, _k in canaliculi.CELL_METRICS]


def normalised_columns() -> list[str]:
    return [f for f, _u, _x in canaliculi.NORMALISED_METRICS]


def v2_columns() -> list[str]:
    return [m[0] for m in canaliculi.NETWORK_V2_METRICS]


def width_columns() -> list[str]:
    return [f for f, _u, _x, _c in WIDTH_CELL_METRICS]


def lacuna_columns(rows: list[dict]) -> list[str]:
    """Every per-lacuna column, in output order, that the rows actually hold."""
    order = shape_columns() + network_columns() + normalised_columns() + v2_columns() + width_columns()
    seen, out = set(), []
    for name in order:
        if name not in seen and (not rows or name in rows[0]):
            seen.add(name)
            out.append(name)
    return out


# Measuring without writing
# A diagnostic or a figure needs the numbers of a run it has just made in
# memory, with a switch on or a threshold scaled, which never reaches a results
# folder. These two run detection and then measure the same arrays, so the file
# route and the memory route cannot drift apart.

def detection_in_memory(result: dict) -> dict:
    """What load_detection returns, taken from an in-memory detection result
    (canaliculi.analyse_network) instead of from the saved files."""
    lac = result["lacunae"]
    return {
        "label": lacunae.image_label(result["image_path"]),
        "lacuna_id_map": result["lacuna_id_map"],
        "lacuna_mask": result["lacuna_id_map"] > 0,
        "mask": result["candidate"],
        "thresholded": result["candidate"] & ~result["bridged_pixels"],
        "bridged": result["bridged_pixels"],
        "skeleton": result["skeleton"],
        "vascular": result["flagged"],
        "graph": result["graph"],
        "owner": result["owner"],
        "node_dist": result["node_dist"],
        "edge_owner": result["edge_owner"],
        "lacunae_detection": {
            "parameters": {**lacunae.parameters(), "computed_threshold_t_hi": lac["t_hi"]},
        },
        "canaliculi_detection": {
            "parameters": canaliculi.parameters(result),
            "n_bridges": len(result["bridges"]),
        },
    }


def analyse_network(image_path: Path, lac: dict, channel: np.ndarray, t_lo: float | None = None,
                    roi_mask: np.ndarray | None = None) -> dict:
    """Network detection from a finished lacuna result onward, then every
    measure. The detection keys and the measured keys in one dict, so it can
    replace the former canaliculi.analyse_network for any caller."""
    detected = canaliculi.analyse_network(image_path, lac, channel, t_lo, roi_mask)
    measured = quantify(detection_in_memory(detected), image_path, roi_mask)
    return {**detected, **measured}


def analyse_image(image_path: Path, t_hi: float | None = None, t_lo: float | None = None,
                  roi_mask: np.ndarray | None = None) -> dict:
    """Both detection stages and every measure for one image, without writing.
    t_hi and t_lo replace the two computed cuts; only the sensitivity
    diagnostics pass them, the pipeline never does."""
    lac = lacunae.analyse_image(image_path, t_hi)
    _display, channel = lacunae.load_channel(image_path)
    return analyse_network(image_path, lac, channel, t_lo, roi_mask)


# Output: json

def save_json(result: dict, out_path: Path) -> None:
    payload = {
        "status": "pre-validation",
        "units": "px",
        "image": result["image_path"].name,
        "image_label": result["label"],
        "note": NOTE,
        "lacuna_count": result["lacuna_count"],
        "border_lacuna_count": result["border_lacuna_count"],
        "interior_lacuna_count": result["interior_lacuna_count"],
        "n_bridges": result["n_bridges"],
        "headline_measures": HEADLINE_MEASURES,
        "ownership_dependent_measures": ["owned_length_px", "edge_count", "mean_edge_length_px"],
        "normalised_measures": normalised_columns(),
        "network_v2_measures": v2_columns() + canaliculi.FIELD_V2_KEYS,
        "width_measures": [f for f, _u, _x, _c in WIDTH_IMAGE_METRICS] + width_columns(),
        "lacuna_shape_summary": result["lacuna_summary"],
        "summary": result["summary"],
        "field": result["field"],
        "width": result["width"],
        "lacunae": result["rows"],
        "parameters": result["parameters"],
        "provenance": lacunae.provenance(),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)


WIDTH_NOTES = [
    "Canalicular width: 2 x the Euclidean distance transform of the canalicular mask at each skeleton pixel.",
    "Measured only on skeleton pixels with real signal under them: bridged pixels, the lacuna buffer and the",
    "dilated vascular mask are excluded. The threads are about 2 to 6 px wide, so the width is close to the",
    "pixel grid and quantised in steps of about 1 px, it moves with the threshold (a lower cut widens every",
    "thread), and it has not been validated against any manual measurement.",
]


# Output: xlsx

def save_xlsx(result: dict, out_path: Path) -> None:
    from openpyxl import Workbook

    wb = Workbook()
    sheet = wb.active
    sheet.title = "per_image"
    sheet.append(["image", "status", "lacuna_count", "border_lacuna_count", "interior_lacuna_count", "n_bridges"])
    sheet.append([result["image_path"].name, "pre-validation", result["lacuna_count"],
                  result["border_lacuna_count"], result["interior_lacuna_count"], result["n_bridges"]])
    sheet.append([])
    sheet.append(["Pre-validation, pixel units. Statistics below are over interior (on_border False) lacunae only."])
    sheet.append(["metric", "kind", "mean", "median", "sd", "units", "n"])
    n_interior = result["interior_lacuna_count"]
    for field, unit in lacunae.LACUNA_SUMMARY_METRICS:
        s = result["lacuna_summary"][field]
        sheet.append([field, "lacuna shape", s["mean"], s["median"], s["sd"], unit, n_interior])
    for field, unit, kind in canaliculi.CELL_METRICS:
        s = result["summary"][field]
        sheet.append([field, kind, s["mean"], s["median"], s["sd"], unit, n_interior])
    for field, unit, _extra in canaliculi.NORMALISED_METRICS:
        if field in result["summary"]:
            s = result["summary"][field]
            sheet.append([field, "normalised", s["mean"], s["median"], s["sd"], unit, n_interior])
    for field, unit, _extra, _col in canaliculi.NETWORK_V2_METRICS:
        if field in result["summary"]:
            s = result["summary"][field]
            sheet.append([field, "network v2", s["mean"], s["median"], s["sd"], unit, n_interior])
    for field, unit, _extra, _col in WIDTH_CELL_METRICS:
        s = result["summary"][field]
        sheet.append([field, "width", s["mean"], s["median"], s["sd"], unit, n_interior])

    field_sheet = wb.create_sheet("field")
    field_sheet.append(["metric", "kind", "value", "units"])
    for key, value in result["field"].items():
        kind = "headline" if key == "canalicular_length_density_per_px" else "reported"
        field_sheet.append([key, kind, value, canaliculi.FIELD_UNITS[key]])

    width_sheet = wb.create_sheet("width")
    width_sheet.append(["metric", "kind", "value", "units"])
    for key, unit, _extra, _col in WIDTH_IMAGE_METRICS:
        kind = "headline" if key == "width_median_px" else "reported"
        width_sheet.append([key, kind, result["width"][key], unit])

    per_lacuna = wb.create_sheet("per_lacuna")
    columns = lacuna_columns(result["rows"])
    per_lacuna.append(columns)
    for row in result["rows"]:
        per_lacuna.append([row.get(c) for c in columns])

    notes = wb.create_sheet("notes")
    notes.append([NOTE])
    for line in WIDTH_NOTES:
        notes.append([line])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)


# Output: pdf
# Plain text pages in a monospace font, then the histograms. matplotlib is
# already a dependency of this project (figures/make_figures.py uses it).

PDF_PAGE_INCHES = (11.69, 8.27)  # A4 landscape, so a wide table fits across it
PDF_FONT_SIZE = 7.0  # the largest used; a wide table gets a smaller one
PDF_MIN_FONT_SIZE = 4.0
PDF_MARGIN_INCHES = 0.4
MONOSPACE_WIDTH_RATIO = 0.6  # advance width of DejaVu Sans Mono, in font sizes
LINE_SPACING = 1.3


def _cell(value) -> str:
    """One table cell as plain text. None prints empty, so a missing value can
    never look like a zero."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def text_table(headers: list, rows: list, gap: int = 2) -> list:
    """A fixed-width text table: the header, a rule, then one line per row."""
    body = [[_cell(v) for v in row] for row in rows]
    widths = [len(h) for h in headers]
    for row in body:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    sep = " " * gap
    lines = [sep.join(h.ljust(w) for h, w in zip(headers, widths)).rstrip(),
             sep.join("-" * w for w in widths)]
    for row in body:
        lines.append(sep.join(c.ljust(w) for c, w in zip(row, widths)).rstrip())
    return lines


def _fit(lines: list) -> tuple:
    """(font size, lines per page) so the widest line fits across the page."""
    widest = max((len(line) for line in lines), default=1)
    usable_width = PDF_PAGE_INCHES[0] - 2 * PDF_MARGIN_INCHES
    size = min(PDF_FONT_SIZE, usable_width * 72.0 / (widest * MONOSPACE_WIDTH_RATIO))
    size = max(size, PDF_MIN_FONT_SIZE)
    usable_height = PDF_PAGE_INCHES[1] - 2 * PDF_MARGIN_INCHES
    per_page = max(10, int(usable_height * 72.0 / (size * LINE_SPACING)))
    return size, per_page


def _text_pages(pdf, lines: list, first_page_header: list | None = None) -> None:
    """Write the lines as monospace pages. The font is the largest that keeps
    the widest line inside the page, so no column is ever cut off."""
    import matplotlib.pyplot as plt

    header = first_page_header or []
    font_size, lines_per_page = _fit(header + lines)
    pages, page = [], []
    room = lines_per_page - len(header)
    for line in lines:
        page.append(line)
        if len(page) >= room:
            pages.append(page)
            page, room = [], lines_per_page
    if page:
        pages.append(page)
    x = PDF_MARGIN_INCHES / PDF_PAGE_INCHES[0]
    y = 1.0 - PDF_MARGIN_INCHES / PDF_PAGE_INCHES[1]
    for i, body in enumerate(pages):
        fig = plt.figure(figsize=PDF_PAGE_INCHES)
        fig.text(x, y, "\n".join((header if i == 0 else []) + body),
                 family="monospace", fontsize=font_size, va="top", ha="left",
                 linespacing=LINE_SPACING)
        pdf.savefig(fig)
        plt.close(fig)


def _histogram_page(pdf, panels: list, title: str) -> None:
    """One page of histograms: [(values, title, x label), ...]."""
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(len(panels), 1, figsize=PDF_PAGE_INCHES)
    axes = np.atleast_1d(axes)
    fig.suptitle(title, fontsize=9)
    for ax, (values, panel_title, xlabel) in zip(axes, panels):
        values = np.asarray(values, dtype=float)
        if values.size:
            ax.hist(values, bins=int(min(40, max(5, np.sqrt(values.size)))), color="0.4")
        ax.set_title(f"{panel_title} (n = {values.size})", fontsize=8)
        ax.set_xlabel(xlabel, fontsize=8)
        ax.set_ylabel("count", fontsize=8)
        ax.tick_params(labelsize=7)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    pdf.savefig(fig)
    plt.close(fig)


def header_lines(title: str) -> list:
    return [
        title,
        "=" * len(title),
        "PRE-VALIDATION: no number here has been checked against manual (ImageJ) counts.",
        "PIXEL UNITS: lengths px, areas px^2, densities px^-1. The images carry no micron calibration.",
        "Statistics are over interior lacunae only (those not touching the frame edge).",
        "",
    ]


def per_image_lines(result: dict) -> list:
    """The per-image measures as text: the counts, the interior statistics, the
    field block and the width block."""
    n = result["interior_lacuna_count"]
    lines = ["Per image", "---------"]
    lines += text_table(["measure", "value"],
                        [["lacuna count", result["lacuna_count"]],
                         ["interior lacuna count", result["interior_lacuna_count"]],
                         ["frame-edge lacuna count", result["border_lacuna_count"]],
                         ["gap bridges added (detection)", result["n_bridges"]]])
    title = f"Interior lacunae only: mean, median and sample SD (n = {n})"
    lines += ["", title, "-" * len(title)]
    stats_rows = []
    for field, unit in lacunae.LACUNA_SUMMARY_METRICS:
        s = result["lacuna_summary"][field]
        stats_rows.append([field, "lacuna shape", s["mean"], s["median"], s["sd"], unit])
    for field, unit, kind in canaliculi.CELL_METRICS:
        s = result["summary"][field]
        stats_rows.append([field, kind, s["mean"], s["median"], s["sd"], unit])
    for field, unit, _extra in canaliculi.NORMALISED_METRICS:
        if field in result["summary"]:
            s = result["summary"][field]
            stats_rows.append([field, "normalised", s["mean"], s["median"], s["sd"], unit])
    for field, unit, _extra, _col in canaliculi.NETWORK_V2_METRICS:
        if field in result["summary"]:
            s = result["summary"][field]
            stats_rows.append([field, "network v2", s["mean"], s["median"], s["sd"], unit])
    for field, unit, _extra, _col in WIDTH_CELL_METRICS:
        s = result["summary"][field]
        stats_rows.append([field, "width", s["mean"], s["median"], s["sd"], unit])
    lines += text_table(["measure", "kind", "mean", "median", "sd", "units"], stats_rows)

    lines += ["", "Per field", "---------"]
    lines += text_table(["measure", "value", "units"],
                        [[k, v, canaliculi.FIELD_UNITS[k]] for k, v in result["field"].items()])
    title = "Canalicular width, the new measure"
    lines += ["", title, "-" * len(title)]
    lines += text_table(["measure", "value", "units"],
                        [[k, result["width"][k], u] for k, u, _x, _c in WIDTH_IMAGE_METRICS])
    lines += [""] + WIDTH_NOTES
    return lines


LACUNA_PDF_BLOCKS = [
    ("Lacuna shape", shape_columns),
    ("Network per lacuna", lambda: ["lacuna_id"] + network_columns() + width_columns()),
    ("Normalised per lacuna", lambda: ["lacuna_id"] + normalised_columns()),
    ("Network v2 per lacuna", lambda: ["lacuna_id"] + v2_columns()),
]


def per_lacuna_lines(rows: list) -> list:
    """The per-lacuna table in blocks of columns, so nothing is cut off, with
    every lacuna in every block."""
    lines = []
    for title, columns in LACUNA_PDF_BLOCKS:
        names = [c for c in columns() if not rows or c in rows[0]]
        if not names:
            continue
        lines += ["", title, "-" * len(title)]
        lines += text_table(names, [[row.get(c) for c in names] for row in rows])
    return lines


def save_pdf(result: dict, out_path: Path) -> None:
    from matplotlib.backends.backend_pdf import PdfPages

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(out_path) as pdf:
        _text_pages(pdf, per_image_lines(result) + per_lacuna_lines(result["rows"]),
                    header_lines(f"Quantification: {result['label']}"))
        _histogram_page(pdf, [(result["areas"], "Lacuna area", "area (px^2)"),
                              (result["width_values"], "Canalicular width at the measured skeleton pixels",
                               "width (px)")],
                        f"{result['label']}: distributions, pre-validation, px")


def write_outputs(result: dict, out_root: Path) -> None:
    """The three quantification files of one image."""
    label = result["label"]
    save_json(result, quant_path(out_root, label, ".json"))
    save_xlsx(result, quant_path(out_root, label, ".xlsx"))
    save_pdf(result, quant_path(out_root, label, ".pdf"))


# The cross-image table: one row per image. The columns are those of the former
# summary_all_images, in the same order and with the same values, and the width
# columns are appended after them.

SUMMARY_COLUMNS = (list(canaliculi.SUMMARY_COLUMNS)
                   + [c for _f, _u, _x, c in WIDTH_IMAGE_METRICS]
                   + [c for _f, _u, _x, c in WIDTH_CELL_METRICS])

SUMMARY_NOTES = list(canaliculi.SUMMARY_NOTES) + [
    "Appended with the detection and quantification split: the canalicular width.",
] + WIDTH_NOTES


def summary_row(result: dict) -> list:
    """One row of the cross-image table, in SUMMARY_COLUMNS order."""
    summary, field = result["summary"], result["field"]
    return ([
        lacunae.clean_name(result["image_path"]),
        result["image_path"].name,
        "pre-validation",
        result["lacuna_count"],
        result["interior_lacuna_count"],
        result["lacuna_summary"]["area_px2"]["median"],
        summary["roots_count"]["mean"],
        summary["ring_length_r30_px"]["mean"],
        summary["ring_length_r60_px"]["mean"],
        field["canalicular_length_density_per_px"],
    ]
        + [summary.get(f, {}).get("mean") for f, _u, _x in canaliculi.NORMALISED_METRICS]
        + [summary.get(m[0], {}).get("mean") for m in canaliculi.NETWORK_V2_METRICS]
        + [field.get(k) for k in canaliculi.FIELD_V2_KEYS]
        + [result["label"]]
        + [result["width"][f] for f, _u, _x, _c in WIDTH_IMAGE_METRICS]
        + [summary.get(f, {}).get("mean") for f, _u, _x, _c in WIDTH_CELL_METRICS])


def write_summary_table(results: list, out_root: Path) -> None:
    """quantification_all_images.csv, .xlsx and .pdf: one row per image."""
    write_summary_rows([summary_row(r) for r in results], out_root, results)


def write_summary_rows(rows: list, out_root: Path, results: list | None = None) -> None:
    """The cross-image table from finished rows, so a caller that measured in
    worker processes can write it without carrying the arrays back. The pdf
    needs the distributions, so it is written only when `results` is given."""
    csv_path = summary_path(out_root, ".csv")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(SUMMARY_COLUMNS)
        writer.writerows(rows)

    from openpyxl import Workbook

    wb = Workbook()
    sheet = wb.active
    sheet.title = "summary"
    sheet.append(SUMMARY_COLUMNS)
    for row in rows:
        sheet.append(row)
    notes = wb.create_sheet("notes")
    for line in SUMMARY_NOTES:
        notes.append([line])
    wb.save(summary_path(out_root, ".xlsx"))

    if results is not None:
        save_summary_pdf(results, rows, summary_path(out_root, ".pdf"))


SUMMARY_PDF_COLUMNS_PER_BLOCK = 6


def save_summary_pdf(results: list, rows: list, out_path: Path) -> None:
    """One row per image, the columns in blocks so none is cut off, then the
    pooled histograms."""
    from matplotlib.backends.backend_pdf import PdfPages

    lines = []
    labels = [row[SUMMARY_COLUMNS.index("image_label")] for row in rows]
    rest = [c for c in SUMMARY_COLUMNS if c not in ("image", "file", "status", "image_label")]
    for start in range(0, len(rest), SUMMARY_PDF_COLUMNS_PER_BLOCK):
        block = rest[start:start + SUMMARY_PDF_COLUMNS_PER_BLOCK]
        table = []
        for label, row in zip(labels, rows):
            values = [row[SUMMARY_COLUMNS.index(c)] for c in block]
            table.append([label] + values)
        lines += ["", f"Columns {start + 1} to {start + len(block)} of {len(rest)}"]
        lines += text_table(["image_label"] + block, table)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(out_path) as pdf:
        _text_pages(pdf, lines, header_lines(f"Quantification: all {len(results)} images"))
        areas = [a for r in results for a in r["areas"]]
        widths = np.concatenate([r["width_values"] for r in results]) if results else np.array([])
        _histogram_page(pdf, [(areas, "Lacuna area, every image pooled", "area (px^2)"),
                              (widths, "Canalicular width, every image pooled", "width (px)")],
                        "All images: pooled distributions, pre-validation, px")


# Command line

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Quantification of the lacunae and the canalicular network (pre-validation, px). "
                    "Reads what src/lacunae.py and src/canaliculi.py saved.")
    lacunae.add_input_arguments(parser)
    parser.add_argument("-m", "--roi-dir", type=Path, default=None,
                        help="Folder of bone ROI masks (white = bone), for field_density_in_roi_per_px.")
    args = parser.parse_args()

    image_paths = lacunae.image_paths(args)
    results = []
    for image_path in image_paths:
        label = lacunae.image_label(image_path)
        detection = load_detection(args.out, label)
        roi_mask = None
        if args.roi_dir is not None:
            roi_mask, _name = canaliculi.load_roi_mask(args.roi_dir, image_path,
                                                       detection["lacuna_id_map"].shape)
        result = quantify(detection, image_path, roi_mask)
        write_outputs(result, args.out)
        results.append(result)
        print(f"{image_path.name}: lacunae={result['lacuna_count']} "
              f"(interior {result['interior_lacuna_count']})  "
              f"roots per cell={result['summary']['roots_count']['mean']}  "
              f"ring 30 px={result['summary']['ring_length_r30_px']['mean']} px  "
              f"width median={result['width']['width_median_px']} px  "
              f"-> {quant_path(args.out, label, '.json').parent}")

    if len(results) > 1 or args.dir:
        write_summary_table(results, args.out)
        print(f"cross-image table -> {summary_path(args.out, '.xlsx')}, .csv and .pdf")


if __name__ == "__main__":
    main()
