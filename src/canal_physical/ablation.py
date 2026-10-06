"""Ablation of the canalicular comparison: where do the straight segments come from?

The experimental ridge method draws straight, right-angled runs through dark
regions where the raw image shows no thread (see the zoom crops of 542_z18 and
682_z08). This module takes the comparison apart to find out which step puts them
there, and whether the extra connectivity survives without that step. It is a
diagnosis. Nothing here is tuned to make any result look better, and no variant
is called better than another.

    python src/canal_physical/ablation.py --dir data/WT

Seven variants, fixed before the first run and all reported. The lacunae, the
vascular handling, the graph cleanup, the ownership and the ring radii are the
same in every one, so only the named difference can move a number. The variant
list is the whole search, so there is no tuning set and no held-out set.

    A  current method, as is (the reference)
    B  current method, gap bridging off
    C  ridge method, as is (sigmas 3.0, 3.6, 4.2 px)
    D  ridge method, gap bridging off
    E  ridge method, bridging on, hysteresis low cut 0.9 of the high cut
    F  ridge method, bridging off, single scale 3.0 px
    G  ridge method, bridging off, finer scales 1.5, 2.0, 2.5 px

Everything src/quantification.py already measures is measured by it, for every
variant, so the variants cannot differ through the measuring. Three artifact
measures are added here; each is derived from the image itself and none from any
published value.

**Pixel size 0.13 um/px, rounded, unconfirmed per image.** Pre-validation: no
number here has been checked against a manual count.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _extra in (str(ROOT), str(ROOT / "src")):
    if _extra not in sys.path:
        sys.path.insert(0, _extra)

import networkx as nx  # noqa: E402
import numpy as np  # noqa: E402
from skimage import morphology  # noqa: E402

import canaliculi  # noqa: E402
import config  # noqa: E402
import lacunae  # noqa: E402
import quantification  # noqa: E402
from canal_physical import compare, metrics, params as params_mod, preprocess, ridge, skeleton  # noqa: E402

OUT_DIR = ROOT / "results_experiments" / "canal_physical_ablation"
CANAL_PHYSICAL_DIR = ROOT / "results_experiments" / "canal_physical"

# (key, what it is, family, bridging, sigmas in px, low cut as a share of the high cut)
VARIANTS = [
    ("A", "current method, as is", "current", True, None, None),
    ("B", "current method, gap bridging off", "current", False, None, None),
    ("C", "ridge method, as is", "ridge", True, (3.0, 3.6, 4.2), 0.75),
    ("D", "ridge method, gap bridging off", "ridge", False, (3.0, 3.6, 4.2), 0.75),
    ("E", "ridge method, low cut 0.9 of the high cut", "ridge", True, (3.0, 3.6, 4.2), 0.90),
    ("F", "ridge method, bridging off, single scale 3.0 px", "ridge", False, (3.0,), 0.75),
    ("G", "ridge method, bridging off, finer scales", "ridge", False, (1.5, 2.0, 2.5), 0.75),
]
VARIANT_KEYS = [v[0] for v in VARIANTS]
VARIANT_LABELS = {v[0]: v[1] for v in VARIANTS}


# Artifact measures
# Each one is read off the image, never from a published value. They say how much
# of a skeleton is drawn where the image holds no signal, and how much of it runs
# along the pixel grid, which a real canaliculus has no reason to do.

# A run this long or longer, perfectly horizontal or vertical, is counted. 8 px is
# about 1 um at 0.13 um/px: over that distance a real thread curves, and the
# images are known to carry faint axis-aligned banding
# (experiments/task1_artefact.py, "axis-aligned skeleton runs").
STRAIGHT_RUN_MIN_PX = 8

# Two nodes count as lying on one axis-aligned side if their rows or their columns
# differ by at most this, which allows the one pixel of slack a cleaned graph node
# can carry.
RECTANGLE_TOLERANCE_PX = 1


def unsupported_mask(skeleton: np.ndarray, flattened: np.ndarray, cut: float) -> np.ndarray:
    """Skeleton pixels the flattened image does not support: those not above the
    image's own lower multi-Otsu cut, which is the exact complement of the rule
    the current method uses to call a pixel signal (`img > t_lo`)."""
    return skeleton & ~(flattened > cut)


def straight_run_mask(skeleton: np.ndarray, min_length: int = STRAIGHT_RUN_MIN_PX) -> np.ndarray:
    """Skeleton pixels inside a perfectly horizontal or vertical run of at least
    `min_length` pixels.

    A run is a maximal set of consecutive skeleton pixels along one image row or
    one image column. A pixel that belongs to a long run in either direction is
    marked. Diagonal and curved stretches are never marked, however long, so this
    counts only structure that follows the pixel grid."""
    marked = np.zeros_like(skeleton, dtype=bool)
    for axis in (0, 1):
        work = skeleton if axis == 1 else skeleton.T
        out = np.zeros_like(work, dtype=bool)
        for i in range(work.shape[0]):
            line = work[i]
            if not line.any():
                continue
            # Run boundaries along this line.
            padded = np.concatenate(([False], line, [False]))
            edges = np.flatnonzero(padded[1:] != padded[:-1])
            for start, stop in zip(edges[0::2], edges[1::2]):
                if stop - start >= min_length:
                    out[i, start:stop] = True
        marked |= out if axis == 1 else out.T
    return marked


def rectangle_count(graph) -> int:
    """Closed loops of four nodes in the cleaned skeleton graph whose four sides
    are all axis-aligned.

    The loops come from networkx.cycle_basis, which gives one independent cycle
    per loop in the graph, so this counts independent four-node loops and not
    every way of walking one. A side counts as axis-aligned when its two nodes
    share a row or a column to within RECTANGLE_TOLERANCE_PX. A real network has
    no reason to close a rectangle on the pixel grid."""
    real = canaliculi.real_subgraph(graph)
    count = 0
    for cycle in nx.cycle_basis(real):
        if len(cycle) != 4:
            continue
        sides = list(zip(cycle, cycle[1:] + cycle[:1]))
        if all(abs(u[0] - v[0]) <= RECTANGLE_TOLERANCE_PX or abs(u[1] - v[1]) <= RECTANGLE_TOLERANCE_PX
               for u, v in sides):
            count += 1
    return count


def artifact_measures(detection: dict, flattened: np.ndarray, cut: float) -> dict:
    """The three artifact measures, over the whole skeleton, with the share of it
    that gap bridging drew."""
    skel = detection["skeleton"]
    total = int(skel.sum())
    if total == 0:
        return {"skeleton_px": 0, "unsupported_fraction": None, "bridged_fraction": None,
                "straight_run_fraction": None, "rectangle_count": 0,
                "unsupported_px": 0, "bridged_px": 0, "straight_run_px": 0}
    unsupported = unsupported_mask(skel, flattened, cut)
    straight = straight_run_mask(skel)
    bridged = skel & detection["bridged"]
    return {
        "skeleton_px": total,
        "unsupported_px": int(unsupported.sum()),
        "unsupported_fraction": round(float(unsupported.sum()) / total, 6),
        "bridged_px": int(bridged.sum()),
        "bridged_fraction": round(float(bridged.sum()) / total, 6),
        "straight_run_px": int(straight.sum()),
        "straight_run_fraction": round(float(straight.sum()) / total, 6),
        "rectangle_count": rectangle_count(detection["graph"]),
    }


# Building each variant
# Bridging is turned off by assembling the stage from the pipeline's own lower
# level pieces rather than by changing any pipeline function.

def _finish(kept: list, lacuna_id_map: np.ndarray, mask: np.ndarray, thresholded: np.ndarray,
            skel: np.ndarray, flagged: np.ndarray, bridges: list, label: str,
            lacuna_parameters: dict, network_parameters: dict) -> tuple:
    """Ownership and the detection dict, the same for every variant."""
    dist_to_lacuna, nearest_id = canaliculi.nearest_lacuna_map(lacuna_id_map)
    own = canaliculi.build_ownership(kept, skel, dist_to_lacuna, nearest_id)
    detection = metrics.detection_dict(label, lacuna_id_map, mask, mask & ~thresholded, skel, flagged,
                                       own, len(bridges), lacuna_parameters, network_parameters)
    detection["owner_map"] = own["owner_map"]
    detection["bridges"] = bridges
    return detection, own


def build_variant(key: str, lac: dict, channel: np.ndarray, label: str, params) -> dict:
    """One variant's detection, from the pipeline's own pieces."""
    _k, what, family, bridging, sigmas, low_fraction = next(v for v in VARIANTS if v[0] == key)
    lacuna_mask, lacuna_id_map = canaliculi.build_lacuna_maps(lac["labels"], lac["kept"])
    flagged = preprocess.vascular_mask(channel)
    flattened = preprocess.flatten(channel)
    lacuna_parameters = {**lacunae.parameters(), "computed_threshold_t_hi": lac["t_hi"]}

    if family == "current":
        candidate, t_lo = canaliculi.network_candidate_mask(flattened, lacuna_mask, flagged)
        thresholded = candidate
        skel = morphology.skeletonize(candidate)
        bridges = []
        if bridging:
            bridges = canaliculi.find_bridges(skel, flattened, t_lo, lacuna_mask | flagged)
            if bridges:
                candidate = canaliculi.apply_bridges(candidate, bridges)
                skel = morphology.skeletonize(candidate)
        network = {"variant": key, "what": what, "thresholded_quantity": "flattened intensity",
                   "gap_bridging": bridging, "high_cut": float(t_lo),
                   "low_cut": float(t_lo) * canaliculi.HYSTERESIS_LOW_FRACTION}
    else:
        variant_params = replace(params, hysteresis_low_fraction=low_fraction)
        response = ridge.ridge_response(flattened, variant_params, sigmas)
        candidate, t_hi = skeleton.ridge_network_mask(response, lacuna_mask, flagged, variant_params)
        thresholded = candidate
        skel = morphology.skeletonize(candidate)
        bridges = []
        if bridging:
            bridges = canaliculi.find_bridges(skel, response, t_hi, lacuna_mask | flagged)
            if bridges:
                candidate = canaliculi.apply_bridges(candidate, bridges)
                skel = morphology.skeletonize(candidate)
        network = {"variant": key, "what": what,
                   "thresholded_quantity": "multiscale ridge response (skimage.filters.sato)",
                   "gap_bridging": bridging, "sigmas_px": list(sigmas),
                   "sigmas_um": [params.um(s) for s in sigmas],
                   "hysteresis_low_fraction": low_fraction, "high_cut": float(t_hi),
                   "low_cut": float(t_hi) * low_fraction}

    detection, _own = _finish(lac["kept"], lacuna_id_map, candidate, thresholded, skel, flagged,
                              bridges, label, lacuna_parameters, network)
    detection["flattened"] = flattened
    return detection


def current_reference(image_path: Path, lac: dict, channel: np.ndarray) -> dict:
    """Variant A straight from the pipeline, so it is the pipeline exactly."""
    detected = canaliculi.analyse_network(image_path, lac, channel)
    detection = quantification.detection_in_memory(detected)
    detection["owner_map"] = detected["owner_map"]
    detection["bridges"] = detected["bridges"]
    detection["flattened"] = canaliculi.preprocess_channel(channel)
    return detection


# Verification images, drawn by the pipeline's own code
# canaliculi.save_verification and canaliculi.lacuna_colors are imported and
# called, never reimplemented, so the style is the pipeline's: the
# full-brightness original, each lacuna outlined in its colour, and only the
# OWNED skeleton drawn, thickened by the pipeline's own dilation. Unowned
# skeleton is not drawn at all, which hides a large part of every skeleton.

def verification_payload(lac: dict, display: np.ndarray, detection: dict) -> dict:
    """The dict canaliculi.save_verification reads, built from a variant's own
    arrays. The lacunae are the same in every variant, so a cell keeps its colour
    across all of them."""
    return {
        "lacunae": lac,
        "display": display,
        "lacuna_id_map": detection["lacuna_id_map"],
        "skeleton": detection["skeleton"],
        "owner_map": detection["owner_map"],
    }


def save_verification_images(lac: dict, display: np.ndarray, detections: dict, label: str,
                             out_dir: Path) -> dict:
    """One full-size verification image per variant. Returns {variant: path}."""
    paths = {}
    folder = out_dir / label / "verification"
    folder.mkdir(parents=True, exist_ok=True)
    for key in VARIANT_KEYS:
        path = folder / f"{label}_verification_{key}.png"
        canaliculi.save_verification(verification_payload(lac, display, detections[key]), path)
        paths[key] = path
    return paths


def check_variant_a_matches_pipeline(label: str, path: Path) -> tuple:
    """Variant A's verification image against the committed one, pixel for pixel."""
    from skimage.io import imread

    committed = lacunae.result_path(config.RESULTS_DIR, label, config.SECTION_CANALICULI,
                                    config.SUFFIX_CANALICULI_VERIFICATION)
    if not committed.is_file():
        return False, f"{committed} is missing"
    a, b = np.asarray(imread(path)), np.asarray(imread(committed))
    if a.shape != b.shape:
        return False, f"shape {a.shape} against {b.shape}"
    if not np.array_equal(a, b):
        return False, f"{int((a != b).any(axis=-1).sum())} pixels differ"
    return True, "pixel identical"


# Figures
# Every panel uses the same crop and the same display window as the verification
# images, which is the full-brightness original the pipeline draws on.

ARTIFACT_COLOURS = {"unsupported": (255, 0, 0), "straight": (0, 80, 255), "rest": (255, 255, 255)}


def panels_figure(panels: list, title: str, out_path: Path, params, extent_px: int,
                  boxes=None, out_pdf: Path | None = None) -> None:
    """A row of labelled panels at one crop, with a scale bar on each."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    import textwrap

    fig, axes = plt.subplots(1, len(panels), figsize=(3.5 * len(panels), 4.0))
    axes = np.atleast_1d(axes)
    for ax, (image, name) in zip(axes, panels):
        compare._panel(ax, image, name, params, extent_px, boxes)
    # Wrap to the figure width, so a long caption is never cut off at the edge.
    wrapped = textwrap.wrap(title, width=max(60, 46 * len(panels)))
    fig.suptitle(chr(10).join(wrapped), fontsize=8)
    fig.tight_layout(rect=(0, 0.02, 1, 0.92))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=compare.DPI, metadata=compare.PNG_METADATA)
    if out_pdf is not None:
        fig.savefig(out_pdf, metadata=compare.PDF_METADATA)
    plt.close(fig)


def skeleton_over_raw(display: np.ndarray, skel: np.ndarray, colour=(255, 255, 255)) -> np.ndarray:
    """The whole skeleton over the original, owned or not, so a variant can be
    seen in full. This is not the verification style."""
    rgb = display.copy()
    rgb[skel] = colour
    return rgb


def artifact_overlay(display: np.ndarray, detection: dict, flattened: np.ndarray,
                     cut: float) -> np.ndarray:
    """Variant C's skeleton over the original: red where the image does not
    support it, blue where it runs along the pixel grid, white elsewhere. A pixel
    that is both is drawn red."""
    skel = detection["skeleton"]
    straight = straight_run_mask(skel)
    unsupported = unsupported_mask(skel, flattened, cut)
    rgb = display.copy()
    rgb[skel & ~straight & ~unsupported] = ARTIFACT_COLOURS["rest"]
    rgb[skel & straight & ~unsupported] = ARTIFACT_COLOURS["straight"]
    rgb[unsupported] = ARTIFACT_COLOURS["unsupported"]
    return rgb


def read_zoom_boxes(label: str) -> list:
    """The three tiles the canal_physical run chose, read from its json. They are
    not chosen again here, so the two runs show the same places."""
    path = CANAL_PHYSICAL_DIR / label / f"{label}_canal_physical.json"
    boxes = json.loads(path.read_text(encoding="utf-8"))["zoom_boxes"]
    return [(b["row"], b["col"], b["side_px"], b["skeleton_px_difference"]) for b in boxes]


def crop(image: np.ndarray, box: tuple) -> np.ndarray:
    row0, col0, side, _value = box
    return image[row0:row0 + side, col0:col0 + side]


# Tables

MEASURE_COLUMNS = [
    "image_label", "variant", "what", "pixel_size_label",
    "skeleton_px", "unsupported_fraction", "unsupported_px", "bridged_fraction", "bridged_px",
    "straight_run_fraction", "straight_run_px", "rectangle_count",
    "field_length_density_per_px", "field_length_density_um_per_um2",
    "roots_per_cell",
    "ring_length_r30_px_per_cell", "ring_length_r30_um_per_cell",
    "ring_length_r60_px_per_cell", "ring_length_r60_um_per_cell",
    "width_median_px", "width_median_um", "width_p10_px", "width_p90_px",
    "junction_count", "junction_density_per_um2",
    "thread_end_fraction", "connected_to_lacuna_fraction",
    "median_edge_length_px", "mean_edge_length_px", "n_bridges",
    "lacuna_count", "interior_lacuna_count",
]

# The columns the summary reports as a mean over the images, with the change from
# variant A.
SUMMARY_MEASURES = [
    "unsupported_fraction", "bridged_fraction", "straight_run_fraction", "rectangle_count",
    "connected_to_lacuna_fraction", "junction_count", "thread_end_fraction",
    "width_median_px", "field_length_density_per_px", "roots_per_cell",
    "ring_length_r30_px_per_cell", "skeleton_px", "n_bridges",
]


def measure_row(label: str, key: str, measured: dict, artifacts: dict) -> list:
    row = {"image_label": label, "variant": key, "what": VARIANT_LABELS[key],
           "pixel_size_label": params_mod.PIXEL_LABEL, **artifacts, **measured["comparison"]}
    return [row.get(c) for c in MEASURE_COLUMNS]


def fixed_workbook(wb, path: Path) -> None:
    """Save a workbook whose bytes depend only on its contents."""
    import datetime
    import re
    import shutil
    import zipfile

    stamp = datetime.datetime(1980, 1, 1)
    wb.properties.created = stamp
    wb.properties.modified = stamp
    wb.properties.creator = ""
    wb.properties.lastModifiedBy = ""
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    fixed = b"1980-01-01T00:00:00Z"
    tmp = path.with_name(path.name + ".tmp")
    with zipfile.ZipFile(path) as src, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in sorted(src.infolist(), key=lambda i: i.filename):
            data = src.read(info.filename)
            if info.filename == "docProps/core.xml":
                data = re.sub(rb"(<dcterms:(?:created|modified)[^>]*>)[^<]*", rb"\g<1>" + fixed, data)
            entry = zipfile.ZipInfo(info.filename, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = info.external_attr
            dst.writestr(entry, data)
    shutil.move(str(tmp), str(path))


def write_tables(rows: list, out_dir: Path, params) -> list:
    """ablation_all_images.csv, .xlsx and .pdf, and the summary. Returns the
    summary rows so the report can use them."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "ablation_all_images.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(MEASURE_COLUMNS)
        writer.writerows(rows)

    index = {c: i for i, c in enumerate(MEASURE_COLUMNS)}
    means = {}
    for key in VARIANT_KEYS:
        taken = [r for r in rows if r[index["variant"]] == key]
        means[key] = {}
        for name in SUMMARY_MEASURES:
            values = [r[index[name]] for r in taken if r[index[name]] is not None]
            means[key][name] = float(np.mean(values)) if values else None

    summary_rows = []
    for key in VARIANT_KEYS:
        for name in SUMMARY_MEASURES:
            value, base = means[key][name], means["A"][name]
            change = None
            if value is not None and base not in (None, 0):
                change = round(100.0 * (value - base) / base, 2)
            summary_rows.append([key, VARIANT_LABELS[key], name,
                                 None if value is None else round(value, 6),
                                 None if base is None else round(base, 6), change])
    with open(out_dir / "ablation_summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["variant", "what", "measure", "mean_over_8_images", "variant_A_mean",
                         "percent_change_from_A"])
        writer.writerows(summary_rows)

    from openpyxl import Workbook

    wb = Workbook()
    sheet = wb.active
    sheet.title = "per_image"
    sheet.append(MEASURE_COLUMNS)
    for row in rows:
        sheet.append(row)
    s = wb.create_sheet("summary")
    s.append(["variant", "what", "measure", "mean_over_8_images", "variant_A_mean", "percent_change_from_A"])
    for row in summary_rows:
        s.append(row)
    notes = wb.create_sheet("notes")
    for line in README_NOTES(params):
        notes.append([line])
    fixed_workbook(wb, out_dir / "ablation_all_images.xlsx")

    write_tables_pdf(rows, summary_rows, means, out_dir, params)
    return summary_rows, means


def README_NOTES(params) -> list:
    return [
        params_mod.PIXEL_LABEL + ".",
        "Pre-validation: no number here has been checked against a manual count.",
        "A diagnosis, not a new method. No variant is better than another; this says what changed.",
        "unsupported_fraction: share of skeleton pixels NOT above the image's own lower multi-Otsu cut",
        "  of the flattened intensity, the same cut the current method uses as its high threshold.",
        f"straight_run_fraction: share of skeleton pixels inside a perfectly horizontal or vertical run",
        f"  of at least {STRAIGHT_RUN_MIN_PX} px (about {params.um(STRAIGHT_RUN_MIN_PX):g} um).",
        "rectangle_count: independent four-node loops of the cleaned graph whose four sides are all",
        f"  axis-aligned to within {RECTANGLE_TOLERANCE_PX} px (networkx.cycle_basis).",
        "The verification images draw OWNED skeleton only, so threads no lacuna owns are not shown.",
    ]


def write_tables_pdf(rows: list, summary_rows: list, means: dict, out_dir: Path, params) -> None:
    from matplotlib.backends.backend_pdf import PdfPages

    header = [
        "Canalicular ablation: where do the straight segments come from?",
        "=" * 62,
        f"PIXEL SIZE {params.pixel_size_um} um/px. {params_mod.PIXEL_LABEL.upper()}.",
        "PRE-VALIDATION. A diagnosis, not a new method. No variant is called better.",
        "",
        "Variants:",
    ]
    header += [f"  {k}  {VARIANT_LABELS[k]}" for k in VARIANT_KEYS] + [""]

    lines = ["Mean over the 8 images, and the change from variant A", "-" * 52]
    table = []
    for name in SUMMARY_MEASURES:
        row = [name]
        for key in VARIANT_KEYS:
            value = means[key][name]
            row.append("" if value is None else f"{value:.4g}")
        table.append(row)
    lines += quantification.text_table(["measure"] + VARIANT_KEYS, table)
    lines += ["", "Change from A, per cent", "-" * 23]
    table = []
    for name in SUMMARY_MEASURES:
        row = [name]
        for key in VARIANT_KEYS:
            value, base = means[key][name], means["A"][name]
            row.append("" if value is None or base in (None, 0) else f"{100.0 * (value - base) / base:+.1f}")
        table.append(row)
    lines += quantification.text_table(["measure"] + VARIANT_KEYS, table)

    index = {c: i for i, c in enumerate(MEASURE_COLUMNS)}
    show = ["skeleton_px", "unsupported_fraction", "bridged_fraction", "straight_run_fraction",
            "rectangle_count", "connected_to_lacuna_fraction", "junction_count", "width_median_px",
            "field_length_density_per_px", "roots_per_cell", "n_bridges"]
    lines += ["", "Every image and variant", "-" * 23]
    table = [[r[index["image_label"]], r[index["variant"]]]
             + [("" if r[index[c]] is None else f"{r[index[c]]:.4g}") for c in show] for r in rows]
    lines += quantification.text_table(["image", "v"] + show, table)
    lines += [""] + README_NOTES(params)

    with PdfPages(out_dir / "ablation_all_images.pdf", metadata=compare.PDF_METADATA) as pdf:
        quantification._text_pages(pdf, lines, header)
    with PdfPages(out_dir / "ablation_summary.pdf", metadata=compare.PDF_METADATA) as pdf:
        quantification._text_pages(pdf, lines[:len(lines) - len(rows) - 3], header)


# Check: variant A must reproduce the committed numbers exactly

def compare_with_results(label: str, measured: dict) -> list:
    """Variant A's measures against results/<label>/5_quantification/, at
    tolerance 0."""
    path = quantification.quant_path(config.RESULTS_DIR, label, ".json")
    committed = json.loads(path.read_text(encoding="utf-8"))
    diffs = []

    def walk(a, b, where):
        if isinstance(a, dict):
            for key, value in a.items():
                walk(value, (b or {}).get(key), f"{where}.{key}" if where else key)
        elif isinstance(a, list):
            for i, value in enumerate(a):
                other = b[i] if isinstance(b, list) and i < len(b) else None
                walk(value, other, f"{where}[{i}]")
        else:
            if isinstance(a, bool) or isinstance(b, bool):
                same = a == b
            elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
                same = a == b or (a != a and b != b)
            else:
                same = a == b
            if not same:
                diffs.append((where, a, b))

    fresh = {
        "lacuna_count": measured["lacuna_count"],
        "interior_lacuna_count": measured["interior_lacuna_count"],
        "n_bridges": measured["n_bridges"],
        "summary": measured["summary"],
        "field": measured["field"],
        "width": measured["width"],
        "lacunae": measured["rows"],
    }
    for key, value in fresh.items():
        walk(committed.get(key), value, key)
    return diffs


# Output per image

def write_image_json(label: str, params, measured: dict, artifacts: dict, boxes: list,
                     verification_ok: tuple, out_dir: Path) -> None:
    payload = {
        "status": "pre-validation",
        "pixel_size_label": params_mod.PIXEL_LABEL,
        "pixel_size_um": params.pixel_size_um,
        "image_label": label,
        "note": ("An ablation, not a new method. Every variant keeps the same lacunae, vascular "
                 "handling, graph cleanup, ownership and ring radii, and every measure the pipeline "
                 "already makes is made by src/quantification.py, so only the named difference can "
                 "move a number. No variant is called better than another."),
        "variants": {k: VARIANT_LABELS[k] for k in VARIANT_KEYS},
        "artifact_measure_definitions": {
            "unsupported_fraction": ("share of skeleton pixels not above the image's own lower "
                                     "multi-Otsu cut of the flattened intensity, the complement of "
                                     "the rule the current method uses to call a pixel signal"),
            "bridged_fraction": "share of skeleton pixels that gap bridging drew",
            "straight_run_fraction": (f"share of skeleton pixels inside a perfectly horizontal or "
                                      f"vertical run of at least {STRAIGHT_RUN_MIN_PX} px"),
            "rectangle_count": (f"independent four-node loops of the cleaned graph whose four sides "
                                f"are axis-aligned to within {RECTANGLE_TOLERANCE_PX} px"),
        },
        "measures": {k: measured[k]["comparison"] for k in VARIANT_KEYS},
        "artifacts": {k: artifacts[k] for k in VARIANT_KEYS},
        "zoom_boxes": [{"index": i, "row": r, "col": c, "side_px": s, "side_um": params.um(s),
                        "skeleton_px_difference": v} for i, (r, c, s, v) in enumerate(boxes, start=1)],
        "zoom_boxes_source": ("results_experiments/canal_physical/<label>/<label>_canal_physical.json, "
                              "the same tiles, not chosen again"),
        "variant_A_verification_matches_pipeline": {"ok": verification_ok[0], "detail": verification_ok[1]},
        "provenance": {**lacunae.provenance(), "pixel_size_um": params.pixel_size_um,
                       "pixel_size_label": params_mod.PIXEL_LABEL},
    }
    path = out_dir / label / f"{label}_ablation.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, default=float)


def write_figures(label: str, params, display: np.ndarray, detections: dict, boxes: list,
                  verification_paths: dict, out_dir: Path) -> None:
    """Every figure of one image."""
    from skimage.io import imread

    folder = out_dir / label
    caption = f"{params_mod.PIXEL_LABEL}, pre-validation"
    extent = display.shape[0]

    # The whole skeleton over the original, per variant, for the zoom panels.
    whole = {k: skeleton_over_raw(display, detections[k]["skeleton"]) for k in VARIANT_KEYS}
    verification = {k: np.asarray(imread(verification_paths[k])) for k in VARIANT_KEYS}

    # Overview with the tiles marked.
    panels_figure([(display, "raw image")], f"{label}: the three zoom tiles. {caption}",
                  folder / f"{label}_overview_tiles.png", params, extent, boxes)

    # Full size verification comparisons, nothing drawn on top.
    panels_figure([(display, "raw image"), (verification["A"], "A, current method"),
                   (verification["C"], "C, ridge method")],
                  f"{label}: verification style, owned skeleton only. {caption}",
                  folder / f"{label}_verification_compare.png", params, extent,
                  out_pdf=folder / f"{label}_verification_compare.pdf")
    panels_figure([(verification["A"], "A, current, bridging on"),
                   (verification["B"], "B, current, bridging off"),
                   (verification["D"], "D, ridge, bridging off")],
                  f"{label}: what gap bridging adds, verification style. {caption}",
                  folder / f"{label}_verification_compare_bridging.png", params, extent)

    for i, box in enumerate(boxes, start=1):
        side = box[2]
        title = (f"{label} zoom {i} at row {box[0]}, column {box[1]}, {params.um(side):g} um square. "
                 f"{caption}")
        panels_figure([(crop(display, box), "raw image")]
                      + [(crop(whole[k], box), f"{k}, {VARIANT_LABELS[k]}") for k in ("A", "B", "C", "D", "E")],
                      title + "  (whole skeleton drawn)",
                      folder / f"{label}_zoom{i}_variants_ABCDE.png", params, side)
        panels_figure([(crop(display, box), "raw image")]
                      + [(crop(whole[k], box), f"{k}, {VARIANT_LABELS[k]}") for k in ("F", "G")],
                      title + "  (whole skeleton drawn)",
                      folder / f"{label}_zoom{i}_variants_FG.png", params, side)
        panels_figure([(crop(display, box), "raw image"),
                       (crop(verification["A"], box), "A, current method"),
                       (crop(verification["C"], box), "C, ridge method")],
                      title + "  (verification style, owned skeleton only)",
                      folder / f"{label}_zoom{i}_verification_raw_A_C.png", params, side)
        artifact = artifact_overlay(display, detections["C"], detections["C"]["flattened"],
                                    detections["C"]["high_cut_for_artifacts"])
        panels_figure([(crop(display, box), "raw image"),
                       (crop(artifact, box), "C: red not above the cut, blue axis-aligned run")],
                      title + "  (variant C, artifact pixels marked)",
                      folder / f"{label}_artifacts_zoom{i}.png", params, side)


def write_readme(out_dir: Path, params, images: list, means: dict) -> None:
    import platform
    from importlib import metadata

    versions = {"python": platform.python_version()}
    for package in ("numpy", "scipy", "scikit-image", "networkx", "skan", "matplotlib", "openpyxl"):
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = None
    prov = lacunae.provenance()
    lines = [
        "# Canalicular ablation: where do the straight segments come from?",
        "",
        f"**{params_mod.PIXEL_LABEL}.** Pre-validation: no number here has been checked against a",
        "manual count. This is a diagnosis on branch `canal-physical-ablation`, not a new method, and",
        "**no variant is called better than another**. Nothing was tuned to improve any result.",
        "",
        "## The question",
        "",
        "The ridge method of `results_experiments/canal_physical/` draws straight, right-angled runs",
        "through dark regions where the raw image shows no thread (its zoom crops of 542_z18 and",
        "682_z08 show it). These seven variants take the comparison apart to find which step puts them",
        "there, and whether the extra connectivity survives without that step.",
        "",
        "## Variants",
        "",
        "The lacunae, the vascular handling, the graph cleanup, the ownership and the ring radii are the",
        "same in every one, so only the named difference can move a number. The list was fixed before",
        "the first run and every variant is reported.",
        "",
        "| variant | what |",
        "|---|---|",
    ]
    lines += [f"| {k} | {VARIANT_LABELS[k]} |" for k in VARIANT_KEYS]
    lines += [
        "",
        "## Artifact measures",
        "",
        "Each is read off the image itself. No published value is used anywhere in this folder, for any",
        "purpose.",
        "",
        "- **`unsupported_fraction`**: share of skeleton pixels that are **not above** the image's own",
        "  lower multi-Otsu cut of the flattened intensity. That cut is the one the current method uses",
        "  as its high threshold, so this is the exact complement of the pipeline's own rule for calling",
        "  a pixel signal. A high value means the skeleton runs where the image holds no signal.",
        f"- **`straight_run_fraction`**: share of skeleton pixels inside a perfectly horizontal or",
        f"  vertical run of at least {STRAIGHT_RUN_MIN_PX} px, about {params.um(STRAIGHT_RUN_MIN_PX):g} um. A run is a maximal set of",
        "  consecutive skeleton pixels along one image row or one image column; a pixel in a long run in",
        "  either direction is counted. Diagonal and curved stretches are never counted, however long.",
        "  A real canaliculus has no reason to follow the pixel grid over a micrometre.",
        f"- **`rectangle_count`**: independent four-node loops of the cleaned graph whose four sides are",
        f"  all axis-aligned to within {RECTANGLE_TOLERANCE_PX} px. The loops come from `networkx.cycle_basis`, which gives",
        "  one independent cycle per loop, so this counts independent loops and not every way of walking",
        "  one.",
        "- Everything else is measured by `src/quantification.py`, the same code for every variant.",
        "",
        "All of them are computed on the **whole** skeleton, not only the part a verification image draws.",
        "",
        "## Reading the verification images",
        "",
        "The verification images are drawn by the pipeline's own `canaliculi.save_verification`, imported",
        "and called, not reimplemented. That style draws the **owned skeleton only**: a thread that no",
        "lacuna owns is not drawn at all, and the owned part is thickened by the pipeline's own dilation.",
        "",
        "**This hides a large part of every skeleton, and it hides more of the current method's than of",
        "the ridge method's.** Only about a third of the current method's skeleton length is connected to",
        "a lacuna, against about seven tenths of the ridge method's, so the ridge picture looks busier",
        "partly for that reason alone and not only because its skeleton is different. The zoom panels",
        "named `_variants_` draw the whole skeleton instead, which is the fair view of what each variant",
        "traced.",
        "",
        "## Files",
        "",
        "| file | what |",
        "|---|---|",
        "| `ablation_all_images.csv`, `.xlsx`, `.pdf` | one row per image and variant, every measure |",
        "| `ablation_summary.csv`, `.pdf` | mean over the 8 images per variant, and the change from A |",
        "| `<label>/verification/<label>_verification_<variant>.png` | full size 1024 x 1024, pipeline style, one per variant |",
        "| `<label>/<label>_verification_compare.png` and `.pdf` | raw, A, C at full size, nothing drawn on top |",
        "| `<label>/<label>_verification_compare_bridging.png` | A, B, D at full size: what bridging adds |",
        "| `<label>/<label>_zoom<i>_variants_ABCDE.png` | the tile with the whole skeleton of A to E |",
        "| `<label>/<label>_zoom<i>_variants_FG.png` | the same tile for F and G |",
        "| `<label>/<label>_zoom<i>_verification_raw_A_C.png` | the same tile in verification style |",
        "| `<label>/<label>_artifacts_zoom<i>.png` | variant C's skeleton: red not above the cut, blue axis-aligned run |",
        "| `<label>/<label>_overview_tiles.png` | the whole image with the three tiles marked |",
        "| `<label>/<label>_ablation.json` | every measure, the definitions, the tiles, provenance |",
        "",
        "The three zoom tiles are the ones the `canal_physical` run chose, read from its json and not",
        "chosen again, so the two folders show the same places.",
        "",
        "## Mean over the 8 images",
        "",
        "| measure | " + " | ".join(VARIANT_KEYS) + " |",
        "|---" * (len(VARIANT_KEYS) + 1) + "|",
    ]
    for name in SUMMARY_MEASURES:
        cells = []
        for key in VARIANT_KEYS:
            value = means[key][name]
            cells.append("" if value is None else f"{value:.4g}")
        lines.append(f"| `{name}` | " + " | ".join(cells) + " |")
    lines += [
        "",
        "## How it was run",
        "",
        "```",
        "python src/canal_physical/ablation.py --dir data/WT",
        "```",
        "",
        f"Commit `{prov['git_commit']}`, tracked files clean: {not prov['git_dirty']}. Config hash",
        f"`{prov['config_hash']}`.",
        "",
        "## Versions",
        "",
        "```",
    ]
    lines += [f"{name}: {value}" for name, value in versions.items()]
    lines += ["```", "", "## Images", ""]
    lines += [f"- {lacunae.image_label(p)} (`{p.name}`)" for p in images]
    path = out_dir / "README.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ablation of the canalicular comparison (pre-validation, pixel size 0.13 um/px "
                    "rounded and unconfirmed). A diagnosis, not a new method.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--image", type=Path, help="One .tif image.")
    group.add_argument("--dir", type=Path, help="A folder of .tif images.")
    parser.add_argument("-o", "--out", type=Path, default=OUT_DIR, help="Output folder.")
    args = parser.parse_args()

    params = params_mod.DEFAULT
    print(f"Pixel size {params.pixel_size_um} um/px. {params_mod.PIXEL_LABEL}.")
    print(f"Variants: " + "; ".join(f"{k} {VARIANT_LABELS[k]}" for k in VARIANT_KEYS))
    print(f"straight run >= {STRAIGHT_RUN_MIN_PX} px = {params.um(STRAIGHT_RUN_MIN_PX):g} um; "
          f"rectangle tolerance {RECTANGLE_TOLERANCE_PX} px\n")

    images = [args.image] if args.image else sorted(args.dir.glob("*.tif"))
    rows, failures = [], []
    for path in images:
        label = lacunae.image_label(path)
        lac = lacunae.analyse_image(path)
        display, channel = lacunae.load_channel(path)

        detections, measured, artifacts = {}, {}, {}
        for key in VARIANT_KEYS:
            detections[key] = (current_reference(path, lac, channel) if key == "A"
                               else build_variant(key, lac, channel, label, params))
        # The cut every artifact measure is read against is the image's own, taken
        # once from the flattened intensity, so every variant is judged by the
        # same cut on the same image.
        flattened = detections["A"]["flattened"]
        _mask, cut = canaliculi.total_signal_mask(flattened)
        for key in VARIANT_KEYS:
            detections[key]["high_cut_for_artifacts"] = cut
            measured[key] = metrics.measure(detections[key], path, params)
            artifacts[key] = artifact_measures(detections[key], flattened, cut)
            rows.append(measure_row(label, key, measured[key], artifacts[key]))

        diffs = compare_with_results(label, measured["A"])
        boxes = read_zoom_boxes(label)
        verification_paths = save_verification_images(lac, display, detections, label, args.out)
        ok, detail = check_variant_a_matches_pipeline(label, verification_paths["A"])
        if diffs:
            failures.append((label, "variant A differs from results/", len(diffs)))
        if not ok:
            failures.append((label, "variant A verification image differs", detail))
        write_figures(label, params, display, detections, boxes, verification_paths, args.out)
        write_image_json(label, params, measured, artifacts, boxes, (ok, detail), args.out)

        print(f"{label}: A against results/ {'PASS' if not diffs else f'FAIL {len(diffs)}'}; "
              f"A verification {detail}")
        print("   " + "  ".join(
            f"{k} skel {artifacts[k]['skeleton_px']:6d} unsup {artifacts[k]['unsupported_fraction']:.3f} "
            f"straight {artifacts[k]['straight_run_fraction']:.3f} rect {artifacts[k]['rectangle_count']:3d}"
            for k in ("A", "C", "D")))

    summary_rows, means = write_tables(rows, args.out, params)
    write_readme(args.out, params, images, means)
    print(f"\ntables -> {args.out / 'ablation_all_images.xlsx'}, .csv, .pdf and the summary")
    if failures:
        print("FAIL:")
        for f in failures:
            print("  ", *f)
        raise SystemExit(1)
    print("PASS: variant A equals results/ at tolerance 0 and its verification image is pixel identical")


if __name__ == "__main__":
    main()
