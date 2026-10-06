"""Run the current method and the experimental one on the same images, compare.

    python src/canal_physical/run.py --dir data/WT
    python src/canal_physical/run.py --dir data/WT --tune
    python -m canal_physical.run --dir data/WT          (with src/ on PYTHONPATH)

Nothing outside results_experiments/canal_physical/ is written. The current method
is the pipeline of this branch, untouched. The experimental method differs from it
in one place only: the quantity that is thresholded. Both are measured by
src/quantification.py, the same function with the same code, so a difference in a
number is a difference in the skeleton and never in the measuring.

**Pixel size 0.13 um/px, rounded, unconfirmed per image.** Pre-validation: no
number here has been checked against a manual count. This branch does not claim
the new method is better; it reports what changed and leaves the judgement to the
reader.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for _extra in (str(ROOT), str(ROOT / "src")):
    if _extra not in sys.path:
        sys.path.insert(0, _extra)

import numpy as np  # noqa: E402

import canaliculi  # noqa: E402
import config  # noqa: E402
import lacunae  # noqa: E402
import quantification  # noqa: E402
from canal_physical import (compare, metrics, params as params_mod,  # noqa: E402
                            plausibility, preprocess, ridge, skeleton)

OUT_DIR = ROOT / "results_experiments" / "canal_physical"
CURRENT = "current"
NEW = "ridge"
METHOD_NAMES = {
    CURRENT: "current method: hysteresis on the flattened intensity",
    NEW: "experimental method: hysteresis on a multiscale ridge response",
}

# Candidate ridge scales, in px, tried on the tuning set only. The chosen set is
# the one that spans the measured canalicular half widths, p50 3.0 px to p99
# 4.2 px (docs/METHODS.md section 2), because that is what the measurement says;
# the others are recorded so the choice can be seen in context. No candidate was
# chosen by comparing it with a literature value.
SIGMA_CANDIDATES_PX = [
    (3.0,),
    (3.0, 3.6, 4.2),
    (1.5, 3.0, 4.5),
    (2.0, 3.0, 4.0, 5.0),
    (4.2,),
]
CHOSEN_SIGMAS_PX = (3.0, 3.6, 4.2)
TUNING_RULE = ("the set spanning the measured half widths p50 3.0 px to p99 4.2 px, "
               "with one step between them; not chosen by any literature value")


# Reporting before anything else

def field_report(params) -> list:
    """The field width in micrometres and every parameter in px and um."""
    lines = [f"Pixel size {params.pixel_size_um} um/px. {params_mod.PIXEL_LABEL}.",
             f"Field 1024 x 1024 px = {1024 * params.pixel_size_um:g} x {1024 * params.pixel_size_um:g} um "
             f"= {(1024 * params.pixel_size_um) ** 2:g} um^2.",
             "",
             "Every parameter of the method, in micrometres and in pixels:",
             f"  {'parameter':30s} {'um':>22s} {'px':>24s}  what",
             "  " + "-" * 82]
    for name, um, px, what in params.table():
        lines.append(f"  {name:30s} {str(um):>22s} {str(px):>24s}  {what}")
    lines += ["", "The pixel values are the ones src/canaliculi.py uses. Asserted equal:"]
    for name, um, px, current in skeleton.check_parameters_match_current(params):
        shown = px if px is not None else um
        lines.append(f"  {name:30s} this branch {str(shown):>10s}   src/canaliculi.py {str(current):>10s}")
    return lines


def tiff_resolution_report(params) -> list:
    """Every TIFF resolution tag, and whether it disagrees with the pixel size."""
    import tifffile

    lines = ["TIFF resolution tags of the input images:"]
    disagree = []
    for path in sorted((ROOT / "data" / "WT").glob("*.tif")):
        with tifffile.TiffFile(path) as tf:
            tags = {t.name: t.value for t in tf.pages[0].tags if "Resolution" in t.name}
        if not tags:
            lines.append(f"  {path.name:26s} no resolution tag")
            continue
        x = tags.get("XResolution")
        per_inch = x[0] / x[1] if isinstance(x, tuple) and x[1] else None
        um_per_px = 25400.0 / per_inch if per_inch else None
        lines.append(f"  {path.name:26s} {tags} -> {um_per_px:g} um/px"
                     if um_per_px else f"  {path.name:26s} {tags}")
        if um_per_px and abs(um_per_px - params.pixel_size_um) > 1e-6:
            disagree.append((path.name, um_per_px))
    if disagree:
        lines += ["",
                  "DISAGREEMENT: the tag below does not match the pixel size in use. It is the generic",
                  "300 DPI placeholder that docs/METHODS.md already records (7 of 8 images carry no tag,",
                  "one reports a generic 300 DPI), not a microscope calibration: it would make the frame",
                  f"{1024 * disagree[0][1] / 1000:.1f} mm wide. It is treated as absent. See DECISIONS.md."]
        for name, value in disagree:
            lines.append(f"  {name}: {value:g} um/px against {params.pixel_size_um} um/px in use")
    return lines


# Detection

def detect_current(image_path: Path, lac: dict, channel: np.ndarray) -> tuple:
    """The current method, unchanged."""
    detected = canaliculi.analyse_network(image_path, lac, channel)
    return quantification.detection_in_memory(detected), detected


def detect_ridge(image_path: Path, lac: dict, channel: np.ndarray, params,
                 sigmas_px: tuple | None = None) -> tuple:
    """The experimental method. Only the thresholded quantity differs from the
    current one; every other step is the current method's own code."""
    lacuna_mask, lacuna_id_map = canaliculi.build_lacuna_maps(lac["labels"], lac["kept"])
    flagged = preprocess.vascular_mask(channel)
    flattened = preprocess.flatten(channel)
    response = ridge.ridge_response(flattened, params, sigmas_px)
    mask, t_hi = skeleton.ridge_network_mask(response, lacuna_mask, flagged, params)
    built = skeleton.skeletonize_and_bridge(mask, response, t_hi, lacuna_mask, flagged)
    dist_to_lacuna, nearest_id = canaliculi.nearest_lacuna_map(lacuna_id_map)
    own = skeleton.ownership(lac["kept"], built["skeleton"], dist_to_lacuna, nearest_id)
    network_parameters = {
        "method": METHOD_NAMES[NEW],
        "thresholded_quantity": "multiscale ridge response (skimage.filters.sato, bright ridges)",
        "ridge_response_high_cut": t_hi,
        "ridge_response_low_cut": t_hi * params.hysteresis_low_fraction,
        "ridge": ridge.response_summary(response, params, sigmas_px),
        **{name: (px if px is not None else um) for name, um, px, _what in params.table()},
    }
    detection = metrics.detection_dict(
        lacunae.image_label(image_path), lacuna_id_map, built["mask"], built["bridged_pixels"],
        built["skeleton"], flagged, own, len(built["bridges"]),
        {**lacunae.parameters(), "computed_threshold_t_hi": lac["t_hi"]}, network_parameters)
    extra = {"response": response, "response_cut": t_hi, "own": own, "lacuna_id_map": lacuna_id_map,
             "dist_to_lacuna": dist_to_lacuna, "nearest_id": nearest_id, **built}
    return detection, extra


# Check: the current method against the committed results

def compare_with_results(label: str, result: dict) -> list:
    """Every measured value of results/<label>/5_quantification/ against this
    recomputation, at tolerance 0. Empty when they agree."""
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
        "lacuna_count": result["lacuna_count"],
        "border_lacuna_count": result["border_lacuna_count"],
        "interior_lacuna_count": result["interior_lacuna_count"],
        "n_bridges": result["n_bridges"],
        "lacuna_shape_summary": result["lacuna_summary"],
        "summary": result["summary"],
        "field": result["field"],
        "width": result["width"],
        "lacunae": result["rows"],
    }
    for key, value in fresh.items():
        walk(committed.get(key), value, key)
    return diffs


# Output

def write_image_json(label: str, params, results: dict, extra: dict, boxes: list, out_dir: Path) -> None:
    """One json per image: the parameters of both methods, every measure of both,
    the zoom rule and a provenance block."""
    payload = {
        "status": "pre-validation",
        "pixel_size_label": params_mod.PIXEL_LABEL,
        "pixel_size_um": params.pixel_size_um,
        "image_label": label,
        "methods": METHOD_NAMES,
        "note": ("An experiment. The current method is the pipeline of this branch, untouched. The "
                 "experimental method differs in one place only, the quantity that is thresholded. Both "
                 "are measured by src/quantification.py, the same code. No claim is made that either is "
                 "better."),
        "parameters": {
            "experimental": results[NEW]["parameters"]["canaliculi"],
            "current": results[CURRENT]["parameters"]["canaliculi"],
            "lacunae": results[CURRENT]["parameters"]["lacunae"],
            "in_micrometres": [{"parameter": n, "um": um, "px": px, "what": w}
                               for n, um, px, w in params.table()],
        },
        "measures": {method: results[method]["comparison"] for method in (CURRENT, NEW)},
        "per_lacuna": {method: results[method]["rows"] for method in (CURRENT, NEW)},
        "plausibility": {method: [
            {"measure": what, "measured": value, "range_low": low, "range_high": high, "unit": unit,
             "verdict": verdict, "note": note}
            for what, value, low, high, unit, verdict, note in
            plausibility.table(results[method]["comparison"], params)] for method in (CURRENT, NEW)},
        "plausibility_caveats": plausibility.CAVEATS,
        "zoom_rule": compare.ZOOM_RULE,
        "zoom_boxes": [{"index": i, "row": r, "col": c, "side_px": s, "side_um": params.um(s),
                        "skeleton_px_difference": v}
                       for i, (r, c, s, v) in enumerate(boxes, start=1)],
        "ridge_response": extra["ridge_summary"],
        "provenance": {**lacunae.provenance(), "pixel_size_um": params.pixel_size_um,
                       "pixel_size_label": params_mod.PIXEL_LABEL},
    }
    path = out_dir / label / f"{label}_canal_physical.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, default=float)


def write_comparison_tables(rows: list, plaus_rows: list, out_dir: Path, params) -> None:
    """comparison_all_images.csv, .xlsx and .pdf: one row per image and method,
    with the plausibility table beside them."""
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "comparison_all_images.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(metrics.COMPARISON_COLUMNS)
        writer.writerows(rows)

    from openpyxl import Workbook

    wb = Workbook()
    sheet = wb.active
    sheet.title = "comparison"
    sheet.append(metrics.COMPARISON_COLUMNS)
    for row in rows:
        sheet.append(row)
    p_sheet = wb.create_sheet("plausibility")
    p_sheet.append(["image_label", "method", "measure", "measured", "range_low", "range_high", "unit",
                    "verdict", "note"])
    for row in plaus_rows:
        p_sheet.append(row)
    notes = wb.create_sheet("notes")
    notes.append([params_mod.PIXEL_LABEL])
    for line in plausibility.CAVEATS:
        notes.append([line])
    xlsx_path = out_dir / "comparison_all_images.xlsx"
    fixed_workbook_dates(wb)
    wb.save(xlsx_path)
    fixed_zip_dates(xlsx_path)

    write_comparison_pdf(rows, plaus_rows, out_dir / "comparison_all_images.pdf", params)


# openpyxl stamps the document properties and every zip entry with the time of
# writing, so two identical runs would produce different bytes. Both are fixed
# here, which makes the workbook reproducible: the brief asks for two runs to give
# identical outputs. Nothing about the content changes.
FIXED_DATE = (1980, 1, 1, 0, 0, 0)


def fixed_workbook_dates(wb) -> None:
    import datetime

    stamp = datetime.datetime(*FIXED_DATE)
    wb.properties.created = stamp
    wb.properties.modified = stamp
    wb.properties.creator = ""
    wb.properties.lastModifiedBy = ""


def fixed_zip_dates(path: Path) -> None:
    """Rewrite the workbook with fixed entry dates and a fixed modified stamp.

    openpyxl writes the time of saving into docProps/core.xml whatever the
    properties say, and gives every zip entry the current time, so this is done
    after the save. The cell values are copied untouched."""
    import re
    import shutil
    import zipfile

    stamp = f"{FIXED_DATE[0]:04d}-{FIXED_DATE[1]:02d}-{FIXED_DATE[2]:02d}T00:00:00Z".encode()
    tmp = path.with_name(path.name + ".tmp")
    with zipfile.ZipFile(path) as src, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in sorted(src.infolist(), key=lambda i: i.filename):
            data = src.read(info.filename)
            if info.filename == "docProps/core.xml":
                data = re.sub(rb"(<dcterms:(?:created|modified)[^>]*>)[^<]*", rb"" + stamp, data)
            entry = zipfile.ZipInfo(info.filename, date_time=FIXED_DATE)
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = info.external_attr
            dst.writestr(entry, data)
    shutil.move(str(tmp), str(path))


def write_comparison_pdf(rows: list, plaus_rows: list, path: Path, params) -> None:
    """Plain text pages, readable in a PDF preview."""
    from matplotlib.backends.backend_pdf import PdfPages

    header = [
        "Canalicular method comparison: current against experimental",
        "=" * 58,
        f"PIXEL SIZE {params.pixel_size_um} um/px. {params_mod.PIXEL_LABEL.upper()}.",
        "PRE-VALIDATION: no number here has been checked against a manual count.",
        "Both methods are measured by src/quantification.py, the same code.",
        "No claim is made that either method is better.",
        "",
    ]
    lines = []
    per_block = 6
    keep = [c for c in metrics.COMPARISON_COLUMNS if c not in ("pixel_size_label",)]
    rest = [c for c in keep if c not in ("image_label", "method")]
    for start in range(0, len(rest), per_block):
        block = rest[start:start + per_block]
        table = []
        for row in rows:
            values = [row[metrics.COMPARISON_COLUMNS.index(c)] for c in block]
            table.append([row[metrics.COMPARISON_COLUMNS.index("image_label")],
                          row[metrics.COMPARISON_COLUMNS.index("method")]] + values)
        lines += ["", f"Measures {start + 1} to {start + len(block)} of {len(rest)}"]
        lines += quantification.text_table(["image", "method"] + block, table)
    lines += ["", "Plausibility, reporting only", "-" * 28]
    lines += quantification.text_table(
        ["image", "method", "measure", "measured", "low", "high", "unit", "verdict"],
        [r[:8] for r in plaus_rows])
    lines += [""] + plausibility.CAVEATS
    with PdfPages(path, metadata=compare.PDF_METADATA) as pdf:
        quantification._text_pages(pdf, lines, header)


def write_readme(out_dir: Path, params, images: list, chosen: tuple) -> None:
    """What was run, with the commands, the versions and the commit."""
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
        "# Experimental canalicular method, current against new",
        "",
        f"**{params_mod.PIXEL_LABEL}.** Pre-validation: no number here has been checked against a manual",
        "count. This is an experiment on branch `canal-physical`; it is not the pipeline and nothing in",
        "`src/lacunae.py`, `src/canaliculi.py`, `src/quantification.py` or `src/diagnostics.py` was changed.",
        "No claim is made that the new method is better: the comparison table and the zoom crops are there",
        "to be judged.",
        "",
        "## What was run",
        "",
        "Two methods on the same 8 WT sections, with the same lacunae, the same vascular handling, the same",
        "bridging rule, the same graph cleanup, the same ownership and the same ring radii. They differ in",
        "one place: the current method thresholds the flattened intensity, the experimental one thresholds a",
        "multiscale ridge response of the same flattened image. Both are measured by",
        "`src/quantification.py`, the same function with the same code.",
        "",
        "```",
        "python src/canal_physical/run.py --dir data/WT --tune    # the tuning set only, writes tuning_log.csv",
        "python src/canal_physical/run.py --dir data/WT           # all 8 images, every output below",
        "```",
        "",
        "`python -m canal_physical.run --dir data/WT` works too when `src/` is on PYTHONPATH.",
        "",
        f"Commit: `{prov['git_commit']}`, tracked files clean: {not prov['git_dirty']}.",
        f"Config hash: `{prov['config_hash']}`.",
        f"Ridge scales chosen: {list(chosen)} px = {[params.um(s) for s in chosen]} um.",
        "",
        "## Versions",
        "",
        "```",
    ]
    lines += [f"{name}: {value}" for name, value in versions.items()]
    lines += [
        "```",
        "",
        "## Parameters",
        "",
        "Every parameter in micrometres and in pixels. The pixel values are the ones `src/canaliculi.py`",
        "uses, asserted equal at this pixel size.",
        "",
        "| parameter | um | px | what |",
        "|---|---|---|---|",
    ]
    for name, um, px, what in params.table():
        lines.append(f"| `{name}` | {um} | {px if px is not None else ''} | {what} |")
    lines += [
        "",
        "## Output",
        "",
        "| file | what |",
        "|---|---|",
        "| `<label>/<label>_triptych.png` and `.pdf` | raw, current, experimental, same crop and window, zoom boxes marked |",
        "| `<label>/<label>_zoom_1` to `_zoom_3.png` | the three crops where the two skeletons differ most |",
        "| `<label>/<label>_canal_physical.json` | parameters of both methods, every measure, the zoom rule, provenance |",
        "| `comparison_all_images.csv`, `.xlsx`, `.pdf` | one row per image and method, plus the plausibility table |",
        "| `tuning_log.csv` | every ridge scale set tried on the tuning set, and what it gave |",
        "| `DECISIONS.md` | every assumption and every open question |",
        "",
        "## Zoom crops",
        "",
        f"Chosen by rule, not by eye: {compare.ZOOM_RULE}. The boxes are drawn on the full image.",
        "",
        "## Images",
        "",
    ]
    lines += [f"- {lacunae.image_label(p)} (`{p.name}`)" for p in images]
    path = out_dir / "README.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


# Tuning, on the tuning set only

def run_tuning(images: list, params, out_dir: Path) -> None:
    """Every candidate scale set on the tuning images, recorded. The held-out
    images are not touched here."""
    tuning = [p for p in images if lacunae.image_label(p) in params_mod.TUNING_IMAGES]
    rows = []
    print(f"Tuning on {len(tuning)} of {len(images)} images: "
          f"{', '.join(lacunae.image_label(p) for p in tuning)}")
    print(f"Held out, not used here: {', '.join(params_mod.HELD_OUT_IMAGES)}")
    for path in tuning:
        label = lacunae.image_label(path)
        lac = lacunae.analyse_image(path)
        _display, channel = lacunae.load_channel(path)
        cur_detection, _cur = detect_current(path, lac, channel)
        current_skeleton = cur_detection["skeleton"]
        for sigmas in SIGMA_CANDIDATES_PX:
            detection, extra = detect_ridge(path, lac, channel, params, sigmas)
            skel = detection["skeleton"]
            overlap = int((skel & current_skeleton).sum())
            dice = 2.0 * overlap / (int(skel.sum()) + int(current_skeleton.sum()))
            row = [label, str(list(sigmas)), str([params.um(s) for s in sigmas]),
                   int(detection["mask"].sum()), int(skel.sum()), int(current_skeleton.sum()),
                   len(extra["bridges"]), round(dice, 6),
                   "chosen" if tuple(sigmas) == CHOSEN_SIGMAS_PX else ""]
            rows.append(row)
            print(f"  {label:9s} sigmas {str(list(sigmas)):22s} mask {row[3]:7d} skeleton {row[4]:6d} "
                  f"bridges {row[6]:3d} dice {dice:.4f}{'  <- chosen' if row[8] else ''}")
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "tuning_log.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["image_label", "sigmas_px", "sigmas_um", "mask_px", "skeleton_px",
                         "current_skeleton_px", "n_bridges", "dice_with_current_skeleton", "chosen"])
        writer.writerow([f"# {params_mod.PIXEL_LABEL}. Tuning set only: "
                         f"{', '.join(params_mod.TUNING_IMAGES)}. Rule: {TUNING_RULE}."])
        writer.writerows(rows)
    print(f"tuning log -> {out_dir / 'tuning_log.csv'}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Experimental canalicular method against the current one (pre-validation, "
                    "pixel size 0.13 um/px rounded and unconfirmed).")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--image", type=Path, help="One .tif image.")
    group.add_argument("--dir", type=Path, help="A folder of .tif images.")
    parser.add_argument("-o", "--out", type=Path, default=OUT_DIR,
                        help="Output folder (default results_experiments/canal_physical/).")
    parser.add_argument("--tune", action="store_true",
                        help="Try every candidate ridge scale set on the tuning images only.")
    args = parser.parse_args()

    params = params_mod.DEFAULT
    for line in field_report(params) + [""] + tiff_resolution_report(params) + [""]:
        print(line)

    images = [args.image] if args.image else sorted(args.dir.glob("*.tif"))
    if not images:
        raise SystemExit("no .tif images found")

    if args.tune:
        run_tuning(images, params, args.out)
        return

    rows, plaus_rows, all_diffs = [], [], []
    for path in images:
        label = lacunae.image_label(path)
        lac = lacunae.analyse_image(path)
        display, channel = lacunae.load_channel(path)

        cur_detection, cur_detected = detect_current(path, lac, channel)
        new_detection, new_extra = detect_ridge(path, lac, channel, params, CHOSEN_SIGMAS_PX)
        results = {
            CURRENT: metrics.measure(cur_detection, path, params),
            NEW: metrics.measure(new_detection, path, params),
        }

        diffs = compare_with_results(label, results[CURRENT])
        all_diffs += [(label, *d) for d in diffs]
        print(f"{label}: current method against results/ at tolerance 0: "
              f"{'PASS' if not diffs else f'FAIL, {len(diffs)} differ'}")

        boxes = compare.zoom_boxes(cur_detection["skeleton"], new_detection["skeleton"], params)
        colors = canaliculi.lacuna_colors(len(lac["kept"]))
        new_owner_map = canaliculi.build_owner_pixel_map(
            new_detection["skeleton"].shape, new_extra["own"]["skel_obj"], new_extra["own"]["graph"],
            new_extra["own"]["edge_owner"], new_extra["own"]["owner"])
        current_rgb = compare.overlay(display, cur_detection["skeleton"], cur_detection["lacuna_id_map"],
                                      colors, cur_detected["owner_map"])
        new_rgb = compare.overlay(display, new_detection["skeleton"], new_detection["lacuna_id_map"],
                                  colors, new_owner_map)
        image_dir = args.out / label
        caption = f"{params_mod.PIXEL_LABEL}, pre-validation"
        compare.triptych(display, current_rgb, new_rgb, label, params, boxes,
                         image_dir / f"{label}_triptych.png", image_dir / f"{label}_triptych.pdf", caption)
        for i, box in enumerate(boxes, start=1):
            compare.zoom(display, current_rgb, new_rgb, label, params, box, i,
                         image_dir / f"{label}_zoom_{i}.png", caption)

        new_extra["ridge_summary"] = ridge.response_summary(new_extra["response"], params, CHOSEN_SIGMAS_PX)
        write_image_json(label, params, results, new_extra, boxes, args.out)

        for method in (CURRENT, NEW):
            rows.append(metrics.comparison_row(label, method, results[method], params_mod.PIXEL_LABEL))
            for what, value, low, high, unit, verdict, note in plausibility.table(
                    results[method]["comparison"], params):
                plaus_rows.append([label, method, what, value, low, high, unit, verdict, note])
        print(f"  current  skeleton {int(cur_detection['skeleton'].sum()):6d} px   "
              f"experimental skeleton {int(new_detection['skeleton'].sum()):6d} px   "
              f"zoom boxes {[b[3] for b in boxes]}")

    write_comparison_tables(rows, plaus_rows, args.out, params)
    write_readme(args.out, params, images, CHOSEN_SIGMAS_PX)
    print(f"\ncomparison -> {args.out / 'comparison_all_images.xlsx'}, .csv and .pdf")
    if all_diffs:
        print(f"FAIL: the current method differs from results/ in {len(all_diffs)} values")
        for d in all_diffs[:10]:
            print("  DIFF", *d)
        raise SystemExit(1)
    print("PASS: the current method equals results/ at tolerance 0 on every image")


if __name__ == "__main__":
    main()
