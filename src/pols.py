"""POL proxy: each lacuna's bright body and the surround that stays above the
bone background (results/pols/DEFINITION.md).

PRE-VALIDATION. This is NOT a measurement of periosteocytic lesions (POLs). The
phase 0 look (results/pols/FINDINGS.md) found no separate lesion zone in these
images: no dark ring, no distinct halo and no step inside the body, only a smooth
fall from the body to the bone background, about 2.3 um wide in WT, which has no
lesions. What is measured here is that surround, a proxy, and every output says
so. Nothing has been checked against a manual measure.

Units: micrometres, at config.PIXEL_SIZE_UM_ACQUIRED (0.13 um/px). The rest of
the pipeline reports pixels so that a fresh run equals results/WT/; this module
has no earlier output to match, so it reports physical units.

Nothing is detected again and no existing stage is changed or run. Per image it
reads what the lacuna and network stages saved in results/<group>/<label>/
(quantification.load_detection): the lacuna label image, the classes with no
shape measure and the vascular mask; and, from 5_quantification, each lacuna's
area (checked against the label image) and roots_count (copied, for reference).
It never writes into those folders.

Per lacuna (DEFINITION.md has the reasons):
    1. territory: the pixels whose nearest body is this lacuna's;
    2. profile: in SECTORS sectors about the body centroid, the median raw red of
       each 1 px band of distance from the body edge, over a slab of SLAB_BANDS
       bands, usable pixels only (frame, territory, no body, no vascular mask);
    3. background: the median raw red BACKGROUND_BAND_PX from the body edge,
       bodies and vascular mask left out; surface: within SURFACE_BAND_PX of it;
    4. in each sector the surround ends where the profile first falls to
       background + LEVEL_FRACTION x (surface - background), at most MAX_HALO_UM
       from the body edge;
    5. outer region = body plus each sector's surround; POL area = outer - body,
       POL ratio = outer / body.
Flags, any of which makes a lacuna unreliable: edge, vessel, neighbour,
incomplete, no_contrast. Lacunae of the classes dim and out_of_focus carry no
area measure anywhere in the pipeline and get no POL measure; they are counted.

Outputs, in results/<group>/pols/ (config.RESULTS_ROOT/<group>/POL_DIR):
    overlays/<label>_pols_overlay.png  body outlined green, outer boundary
                                       magenta, ids cyan (measured), yellow
                                       (flagged) or grey (no shape measure)
    <group>_pols_run.json              parameters, counts, provenance
    with the switch --csv (off by default):
    <group>_pols_per_lacuna.csv        one row per lacuna
    <group>_pols_per_image.csv         one row per image
and with the command summary, from the per-image files of every group:
    results/pols/summary_by_group.csv and results/pols/SUMMARY.md

Usage (from the repo root):
    python src/pols.py measure --dir data/WT --csv
    python src/pols.py summary
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from skimage import segmentation

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canaliculi  # noqa: E402
import lacunae  # noqa: E402
import quantification  # noqa: E402

# Parameters
# None is fitted to any image and none is validated. Each comment says where the
# value comes from; DEFINITION.md lists them together.

# The surround is looked for in this many sectors of equal angle about the body
# centroid, and each sector is one radial profile. Chosen, not measured. A sector
# must be wide enough that one canaliculus (about 6 px wide, METHODS section 18)
# is a minority of a band where the profile ends, 1.5 to 3 um out: 20 px from a
# body of the smallest kept size (400 px2, radius about 11 px) a 45 degree arc is
# 24 px. And there must be enough sectors for the two ends, the two sides and the
# four diagonals of an elongated lacuna.
SECTORS = 8

# Radial bands are 1 px (0.13 um) deep, and the profile at a band is the median of
# that band and the band on each side: the 3-sample smoothing of the glow profile
# (canaliculi.GLOW_PROFILE_SMOOTH), so one dark or bright band cannot end a
# profile by itself.
SLAB_BANDS = canaliculi.GLOW_PROFILE_SMOOTH

# Where the surround ends, as a fraction of its height above the background, and
# the farthest it may reach from the body edge. Both are the glow zone's own
# values (config.GLOW_PROFILE_FRACTION, config.GLOW_ZONE_MAX_UM), so the pipeline
# keeps one definition of where a glow ends and one cap. 8 um is a plausibility
# bound and not a measured lesion size.
LEVEL_FRACTION = config.GLOW_PROFILE_FRACTION
MAX_HALO_UM = config.GLOW_ZONE_MAX_UM
MAX_HALO_PX = config.px_int(MAX_HALO_UM)

# The bone background is the ring 70 to 90 px from the body edge, beyond the
# widest surround the cap allows (canaliculi.GLOW_BACKGROUND_BAND_PX); the
# surface is within 1.5 px of the body edge (the rule of canaliculi.glow_extent_px).
BACKGROUND_BAND_PX = canaliculi.GLOW_BACKGROUND_BAND_PX
SURFACE_BAND_PX = 1.5

# The fewest usable pixels a median is taken over. Guessed.
MIN_SLAB_PIXELS = 5

# A lacuna is measured only if at least this share of its sectors answered,
# because its median width needs half of them.
MIN_ANSWERED_SHARE = 0.5

# Layout and names.
POL_DIR = "pols"
OVERLAY_DIR = "overlays"
SUFFIX_OVERLAY = "pols_overlay.png"
SUMMARY_DIR = config.RESULTS_ROOT / "pols"
STATUS = "pre-validation"
NOTE = ("PRE-VALIDATION. POL proxy, not a measurement of periosteocytic lesions: the "
        "bright lacuna body plus the surround that stays above the bone background. In WT, "
        "which has no lesions, the surround is optical glow (results/pols/FINDINGS.md). "
        "Units um, 0.13 um/px. Definition: results/pols/DEFINITION.md.")

# The window around a body: far enough for the background ring.
PAD = int(np.ceil(BACKGROUND_BAND_PX[1])) + 2
UM2_PER_PX = config.PIXEL_SIZE_UM_ACQUIRED ** 2

STOP_REASONS = ("frame", "neighbour", "vessel")
FLAGS = ("edge", "vessel", "neighbour", "incomplete", "no_contrast")
FLAG_LETTERS = {"edge": "E", "vessel": "V", "neighbour": "N", "incomplete": "I", "no_contrast": "C"}
MEASURES = ("body_area_um2", "outer_area_um2", "pol_area_um2", "pol_ratio",
            "halo_width_median_um", "halo_width_mean_um", "halo_width_max_um")


# Measuring one lacuna

def sector_profiles(d: np.ndarray, sector: np.ndarray, channel: np.ndarray, usable: np.ndarray,
                    blocked: dict, level: float) -> list[tuple]:
    """[(state, width_px or None)] per sector. state is "answered", a stop
    reason of STOP_REASONS, or "cap" (still above the level at MAX_HALO_PX);
    measure_lacuna adds "no_level" when there is no level to compare with.
    The width is the distance of the last band above the level."""
    n_bands = MAX_HALO_PX + 1
    band = np.ceil(d).astype(np.int64)
    near = (band >= 1) & (band <= n_bands)
    key = sector * (n_bands + 1) + band
    size = SECTORS * (n_bands + 1)
    counts = {name: np.bincount(key[near & mask], minlength=size) for name, mask in blocked.items()}
    take = near & usable
    order = np.argsort(key[take], kind="stable")
    keys = key[take][order]
    values = channel[take][order]
    half = SLAB_BANDS // 2
    out = []
    for s in range(SECTORS):
        state, width = "cap", None
        for k in range(1, MAX_HALO_PX + 1):
            lo = s * (n_bands + 1) + max(1, k - half)
            hi = s * (n_bands + 1) + k + half
            slab = values[np.searchsorted(keys, lo, "left"):np.searchsorted(keys, hi, "right")]
            if slab.size < MIN_SLAB_PIXELS:
                stop = {name: int(c[lo:hi + 1].sum()) for name, c in counts.items()}
                if max(stop.values()) > 0:
                    state = max(STOP_REASONS, key=lambda name: stop[name])
                    break
                continue  # too few pixels by geometry alone, nothing blocks
            if np.median(slab) <= level:
                state, width = "answered", k - 1
                break
        out.append((state, width))
    return out


def measure_lacuna(i: int, box: tuple, channel_p: np.ndarray, labels_p: np.ndarray, out_p: np.ndarray,
                   vascular_p: np.ndarray, nearest_p: np.ndarray) -> dict:
    """The POL proxy of lacuna i. box: its bounding box in the padded image.
    Returns the row values and its outer region in the padded frame."""
    window = (slice(box[0].start - PAD, box[0].stop + PAD), slice(box[1].start - PAD, box[1].stop + PAD))
    ch, lab, out, vas, near = (a[window] for a in (channel_p, labels_p, out_p, vascular_p, nearest_p))
    body = lab == i
    d = ndi.distance_transform_edt(~body)
    rows, cols = np.nonzero(body)
    r0, c0 = rows.mean(), cols.mean()
    rr, cc = np.indices(body.shape)
    theta = np.arctan2(rr - r0, cc - c0)
    sector = np.floor((theta + np.pi) / (2.0 * np.pi / SECTORS)).astype(np.int64) % SECTORS
    any_body = lab > 0
    territory = near == i
    usable = territory & ~out & ~vas & ~any_body

    surface_px = usable & (d > 0) & (d <= SURFACE_BAND_PX)
    ring = (d >= BACKGROUND_BAND_PX[0]) & (d <= BACKGROUND_BAND_PX[1]) & ~out & ~vas & ~any_body
    surface = float(np.median(ch[surface_px])) if surface_px.sum() >= MIN_SLAB_PIXELS else float("nan")
    background = float(np.median(ch[ring])) if ring.sum() >= MIN_SLAB_PIXELS else float("nan")
    level = background + LEVEL_FRACTION * (surface - background)

    if np.isfinite(level):
        blocked = {"frame": out, "neighbour": ~out & ~territory, "vessel": ~out & territory & vas & ~any_body}
        sectors = sector_profiles(d, sector, ch, usable, blocked, level)
    else:
        # Too few usable pixels at the body edge or in the background ring (the
        # body is walled in by the vascular mask, the frame or its neighbours):
        # there is no level, so no sector can answer.
        sectors = [("no_level", None)] * SECTORS
    answered = [w for state, w in sectors if state == "answered"]
    reach = np.array([MAX_HALO_PX if w is None else w for _state, w in sectors])
    outer = body | (usable & (d > 0) & (d <= reach[sector]))

    body_px, outer_px = int(body.sum()), int(outer.sum())
    widths_um = [config.um(w) for w in answered]
    # Edge: the outer region (which holds the body) touches the frame, or a
    # sector stopped at it.
    flags = {
        "edge": bool((ndi.binary_dilation(outer, structure=np.ones((3, 3), bool)) & out).any()
                     or any(state == "frame" for state, _w in sectors)),
        "vessel": bool((vas & (d <= MAX_HALO_PX)).any()),
        "neighbour": False,  # set once every outer region is known (measure_image)
        "incomplete": len(answered) < MIN_ANSWERED_SHARE * SECTORS,
        "no_contrast": bool(np.isfinite(level) and surface <= background),
    }
    return {
        "window": window,
        "outer": outer,
        "centroid": (r0 + window[0].start - PAD, c0 + window[1].start - PAD),
        "body_px": body_px,
        "outer_px": outer_px,
        "sectors": sectors,
        "widths_um": widths_um,
        "surface": surface,
        "background": background,
        "level": level,
        "flags": flags,
    }


# Measuring one image

def measure_image(channel: np.ndarray, labels: np.ndarray, vascular: np.ndarray, no_shape_ids) -> tuple:
    """(per-lacuna results in id order, outer label image). A lacuna with no
    shape measure gets None and keeps its body in the outer label image."""
    h, w = channel.shape
    n = int(labels.max())
    labels_p = np.pad(labels.astype(np.int32), PAD)
    channel_p = np.pad(channel, PAD)
    out_p = np.pad(np.zeros((h, w), dtype=bool), PAD, constant_values=True)
    vascular_p = np.pad(vascular.astype(bool), PAD)
    _dist, (ir, ic) = ndi.distance_transform_edt(labels_p == 0, return_indices=True)
    nearest_p = labels_p[ir, ic]
    outer_p = labels_p.copy()
    boxes = ndi.find_objects(labels_p)
    no_shape = set(int(x) for x in no_shape_ids)
    results = []
    for i in range(1, n + 1):
        if boxes[i - 1] is None:
            raise ValueError(f"lacuna {i} has no pixel in the label image")
        if i in no_shape:
            results.append(None)
            continue
        res = measure_lacuna(i, boxes[i - 1], channel_p, labels_p, out_p, vascular_p, nearest_p)
        outer_p[res["window"]][res["outer"]] = i
        results.append(res)
    # The neighbour flag: an outer region that touches another lacuna's outer
    # region or body. Territories are disjoint, so touching is what an overlap
    # becomes.
    ring = np.ones((3, 3), bool)
    for i, res in enumerate(results, start=1):
        if res is None:
            continue
        win = res["window"]
        mine = outer_p[win] == i
        around = ndi.binary_dilation(mine, structure=ring) & ~mine
        others = outer_p[win][around]
        res["flags"]["neighbour"] = bool(((others > 0) & (others != i)).any())
    return results, outer_p[PAD:-PAD, PAD:-PAD]


def _round(value, digits: int = config.CSV_FLOAT_PRECISION):
    if value is None:
        return ""
    if isinstance(value, float) and not np.isfinite(value):
        return ""
    return round(float(value), digits)


def lacuna_rows(group: str, label: str, results: list, quant_rows: list, glow_px: np.ndarray,
                labels: np.ndarray) -> list[dict]:
    """One csv row per lacuna. quant_rows: the lacunae of the image's
    quantification json, whose area must equal the label image's."""
    h, w = labels.shape
    boxes = ndi.find_objects(labels.astype(np.int32))
    rows = []
    for i, res in enumerate(results, start=1):
        q = quant_rows[i - 1]
        if q["lacuna_id"] != i:
            raise ValueError(f"{label}: quantification json out of order at lacuna {i}")
        box = boxes[i - 1]
        on_border = box[0].start == 0 or box[1].start == 0 or box[0].stop == h or box[1].stop == w
        row = {"status": STATUS, "group": group, "image": label, "lacuna_id": i,
               "lacuna_class": q.get("lacuna_class", ""), "on_border": bool(on_border)}
        if res is None:
            rr, cc = np.nonzero(labels == i)
            row.update({"centroid_row_px": _round(rr.mean(), 2), "centroid_col_px": _round(cc.mean(), 2),
                        "measured": False})
            rows.append(row)
            continue
        if q.get("area_px2") is not None and int(q["area_px2"]) != res["body_px"]:
            raise ValueError(f"{label}: lacuna {i} has {res['body_px']} px in the label image and "
                             f"{q['area_px2']} px in 5_quantification; the outputs are out of step")
        states = [state for state, _w in res["sectors"]]
        widths = res["widths_um"]
        body_um2 = res["body_px"] * UM2_PER_PX
        outer_um2 = res["outer_px"] * UM2_PER_PX
        flagged = any(res["flags"].values())
        row.update({
            "centroid_row_px": _round(res["centroid"][0], 2),
            "centroid_col_px": _round(res["centroid"][1], 2),
            "body_area_um2": _round(body_um2),
            "outer_area_um2": _round(outer_um2),
            "pol_area_um2": _round(outer_um2 - body_um2),
            "pol_ratio": _round(outer_um2 / body_um2),
            "halo_width_median_um": _round(float(np.median(widths)) if widths else None),
            "halo_width_mean_um": _round(float(np.mean(widths)) if widths else None),
            "halo_width_max_um": _round(float(np.max(widths)) if widths else None),
            "sectors_answered": states.count("answered"),
            "sectors_stopped_frame": states.count("frame"),
            "sectors_stopped_neighbour": states.count("neighbour"),
            "sectors_stopped_vessel": states.count("vessel"),
            "sectors_above_level_at_cap": states.count("cap"),
            "sectors_without_level": states.count("no_level"),
            "sector_widths_um": ";".join("" if wpx is None else f"{config.um(wpx):.2f}"
                                         for _state, wpx in res["sectors"]),
            "surface": _round(res["surface"]),
            "background": _round(res["background"]),
            "level": _round(res["level"]),
            "glow_extent_um": _round(config.um(float(glow_px[i]))),
            "roots_count": q.get("roots_count", ""),
        })
        for name in FLAGS:
            row[f"flag_{name}"] = bool(res["flags"][name])
        row["flagged"] = bool(flagged)
        row["measured"] = not flagged
        rows.append(row)
    return rows


LACUNA_COLUMNS = (["status", "group", "image", "lacuna_id", "lacuna_class", "on_border", "centroid_row_px",
                   "centroid_col_px"] + list(MEASURES)
                  + ["sectors_answered", "sectors_stopped_frame", "sectors_stopped_neighbour",
                     "sectors_stopped_vessel", "sectors_above_level_at_cap", "sectors_without_level",
                     "sector_widths_um", "surface",
                     "background", "level", "glow_extent_um", "roots_count"]
                  + [f"flag_{name}" for name in FLAGS] + ["flagged", "measured"])


def image_row(group: str, label: str, rows: list[dict]) -> dict:
    """Counts and the mean and median of each measure over the measured
    lacunae (shape measure and no flag) of one image."""
    shape = [r for r in rows if "flagged" in r]
    measured = [r for r in shape if r["measured"]]
    out = {"status": STATUS, "group": group, "image": label, "n_lacunae": len(rows),
           "n_no_shape": len(rows) - len(shape), "n_shape": len(shape),
           "n_flagged": sum(1 for r in shape if r["flagged"]),
           "fraction_flagged": _round(sum(1 for r in shape if r["flagged"]) / len(shape)) if shape else "",
           "n_measured": len(measured)}
    for name in FLAGS:
        out[f"n_flag_{name}"] = sum(1 for r in shape if r[f"flag_{name}"])
    for m in MEASURES:
        values = [r[m] for r in measured if r[m] != ""]
        out[f"{m}_mean"] = _round(float(np.mean(values)) if values else None)
        out[f"{m}_median"] = _round(float(np.median(values)) if values else None)
    return out


IMAGE_COLUMNS = (["status", "group", "image", "n_lacunae", "n_no_shape", "n_shape", "n_flagged",
                  "fraction_flagged", "n_measured"] + [f"n_flag_{name}" for name in FLAGS]
                 + [f"{m}_{stat}" for m in MEASURES for stat in ("mean", "median")])


# Overlay

def save_overlay(channel: np.ndarray, labels: np.ndarray, outer: np.ndarray, rows: list[dict],
                 path: Path, title: str) -> None:
    """The field in grey, the body outlined green on its own edge pixels, the
    outer boundary of each lacuna with a POL measure magenta just outside its
    outer region, and each lacuna's id: cyan measured, yellow flagged with the
    flag letters, grey for a lacuna with no shape measure."""
    import matplotlib  # noqa: PLC0415
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # noqa: PLC0415

    grey = (np.clip(channel, 0.0, 1.0) * 255).astype(np.uint8)
    rgb = np.stack([grey] * 3, axis=-1)
    shape_ids = [r["lacuna_id"] for r in rows if "flagged" in r]
    outer_shape = np.where(np.isin(outer, shape_ids), outer, 0)
    rgb[segmentation.find_boundaries(outer_shape, mode="outer")] = (255, 0, 255)
    rgb[segmentation.find_boundaries(labels, mode="inner")] = (0, 255, 0)
    h, w = grey.shape
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(rgb, interpolation="nearest")
    ax.set_axis_off()
    for r in rows:
        if "flagged" not in r:
            text, colour = f"{r['lacuna_id']} {r['lacuna_class']}", "0.7"
        elif r["flagged"]:
            letters = "".join(FLAG_LETTERS[name] for name in FLAGS if r[f"flag_{name}"])
            text, colour = f"{r['lacuna_id']} {letters}", "yellow"
        else:
            text, colour = str(r["lacuna_id"]), "cyan"
        ax.text(float(r["centroid_col_px"]), float(r["centroid_row_px"]), text, color=colour, fontsize=7,
                ha="center", va="center")
    ax.text(4, 4, title, color="white", fontsize=7, va="top", ha="left",
            bbox={"facecolor": "black", "alpha": 0.6, "pad": 2, "edgecolor": "none"})
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=100)
    plt.close(fig)


OVERLAY_TITLE = ("PRE-VALIDATION. POL proxy (not a lesion measure): body green, outer boundary magenta.\n"
                 "Ids: cyan measured, yellow flagged (E edge, V vessel, N neighbour, I incomplete, "
                 "C no contrast), grey no shape measure.")


# Files

def write_csv(path: Path, columns: list, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, restval="", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parameters() -> dict:
    return {
        "pixel_size_um": config.PIXEL_SIZE_UM_ACQUIRED,
        "sectors": SECTORS,
        "slab_bands": SLAB_BANDS,
        "band_depth_um": config.PIXEL_SIZE_UM_ACQUIRED,
        "level_fraction": LEVEL_FRACTION,
        "max_halo_um": MAX_HALO_UM,
        "max_halo_px": MAX_HALO_PX,
        "background_band_px": list(BACKGROUND_BAND_PX),
        "surface_band_px": SURFACE_BAND_PX,
        "min_slab_pixels": MIN_SLAB_PIXELS,
        "min_answered_share": MIN_ANSWERED_SHARE,
    }


def measure_group(data_dir: Path, results_root: Path, export_csv: bool) -> int:
    """Measure every image of one group folder. An image that fails is listed
    and skipped; the others carry on. Returns the number of failures."""
    group = Path(data_dir).resolve().name
    paths = sorted(Path(data_dir).glob("*.tif"))
    if not paths:
        print(f"No .tif image in {data_dir}: nothing to do, nothing written.")
        return 0
    out_dir = Path(results_root) / POL_DIR
    lacuna_table, image_table, failures = [], [], []
    for path in paths:
        label = lacunae.image_label(path)
        try:
            detection = quantification.load_detection(results_root, label)
            quant = json.loads(quantification.quant_path(results_root, label, ".json").read_text(encoding="utf-8"))
            _display, channel = lacunae.load_channel(path)
            labels = detection["lacuna_id_map"]
            if labels.shape != channel.shape:
                raise ValueError(f"label image {labels.shape} and image {channel.shape} differ in size")
            if len(quant["lacunae"]) != int(labels.max()):
                raise ValueError("5_quantification and the label image hold different lacuna counts")
            results, outer = measure_image(channel, labels, detection["vascular"], detection["no_shape_ids"])
            glow = canaliculi.glow_extent_px(channel, labels, int(labels.max()))
            rows = lacuna_rows(group, label, results, quant["lacunae"], glow, labels)
        except Exception as exc:  # an image that fails is listed and the others carry on
            failures.append({"image": label, "error": f"{type(exc).__name__}: {exc}"})
            print(f"{label}: FAILED, skipped ({type(exc).__name__}: {exc})")
            continue
        save_overlay(channel, labels, outer, rows, out_dir / OVERLAY_DIR / f"{label}_{SUFFIX_OVERLAY}",
                     f"{group} / {label}. {OVERLAY_TITLE}")
        img = image_row(group, label, rows)
        lacuna_table += rows
        image_table.append(img)
        print(f"{label}: {img['n_lacunae']} lacunae, {img['n_shape']} with a shape measure, "
              f"{img['n_flagged']} flagged, {img['n_measured']} measured; "
              f"outer area mean {img['outer_area_um2_mean']} um2, POL ratio mean {img['pol_ratio_mean']}")
    if export_csv:
        write_csv(out_dir / f"{group}_pols_per_lacuna.csv", LACUNA_COLUMNS, lacuna_table)
        write_csv(out_dir / f"{group}_pols_per_image.csv", IMAGE_COLUMNS, image_table)
    record = {
        "status": STATUS,
        "units": "um",
        "stage": "POL proxy",
        "group": group,
        "note": NOTE,
        "csv_exported": bool(export_csv),
        "images": [r["image"] for r in image_table],
        "failed_images": failures,
        "counts": {"lacunae": len(lacuna_table),
                   "with_shape_measure": sum(1 for r in lacuna_table if "flagged" in r),
                   "flagged": sum(1 for r in lacuna_table if r.get("flagged") is True),
                   "measured": sum(1 for r in lacuna_table if r.get("measured") is True)},
        "parameters": parameters(),
        "provenance": lacunae.provenance(),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / f"{group}_pols_run.json", "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    print(f"-> {out_dir}" + ("" if export_csv else "  (no csv: run with --csv to export the tables)"))
    return len(failures)


# Group summary

SUMMARY_COLUMNS = (["status", "group", "n_images", "n_images_measured", "n_lacunae", "n_shape", "n_flagged",
                    "n_measured", "fraction_flagged_mean"]
                   + [f"{m}_{stat}" for m in MEASURES for stat in ("mean_of_image_means", "sd_of_image_means")])


def summarize_groups(groups, out_dir: Path) -> list[dict]:
    """results/pols/summary_by_group.csv and SUMMARY.md: per group, the mean
    and SD over images of each per-image mean, with the counts."""
    rows = []
    for group in groups:
        path = config.RESULTS_ROOT / group / POL_DIR / f"{group}_pols_per_image.csv"
        if not path.is_file():
            raise FileNotFoundError(f"{path} is missing: run python src/pols.py measure --dir data/{group} --csv")
        with open(path, newline="", encoding="utf-8") as f:
            images = list(csv.DictReader(f))

        def numbers(col):
            return [float(r[col]) for r in images if r[col] != ""]

        row = {"status": STATUS, "group": group, "n_images": len(images),
               "n_images_measured": sum(1 for r in images if int(r["n_measured"]) > 0),
               "n_lacunae": sum(int(r["n_lacunae"]) for r in images),
               "n_shape": sum(int(r["n_shape"]) for r in images),
               "n_flagged": sum(int(r["n_flagged"]) for r in images),
               "n_measured": sum(int(r["n_measured"]) for r in images),
               "fraction_flagged_mean": _round(np.mean(numbers("fraction_flagged")))}
        for m in MEASURES:
            values = numbers(f"{m}_mean")
            row[f"{m}_mean_of_image_means"] = _round(float(np.mean(values)) if values else None)
            row[f"{m}_sd_of_image_means"] = _round(float(np.std(values, ddof=1)) if len(values) > 1 else None)
        rows.append(row)
    write_csv(out_dir / "summary_by_group.csv", SUMMARY_COLUMNS, rows)
    write_summary_md(rows, neighbour_sensitivity(groups), out_dir / "SUMMARY.md")
    return rows


SENSITIVITY_MEASURES = ("outer_area_um2", "pol_area_um2", "pol_ratio", "halo_width_median_um")


def neighbour_sensitivity(groups) -> list[dict]:
    """The group values again with the neighbour flag not applied, every other
    flag still applied: how much the dense packing of the Hyp fields decides
    which lacunae are measured. A sensitivity line, not the result."""
    out = []
    for group in groups:
        path = config.RESULTS_ROOT / group / POL_DIR / f"{group}_pols_per_lacuna.csv"
        with open(path, newline="", encoding="utf-8") as f:
            lacunae_rows = [r for r in csv.DictReader(f) if r["flagged"] != ""]
        kept = [r for r in lacunae_rows
                if not any(r[f"flag_{name}"] == "True" for name in FLAGS if name != "neighbour")]
        by_image = {}
        for r in kept:
            by_image.setdefault(r["image"], []).append(r)
        row = {"group": group, "n_measured": len(kept), "n_images_measured": len(by_image)}
        for m in SENSITIVITY_MEASURES:
            means = [float(np.mean([float(r[m]) for r in rows if r[m] != ""])) for rows in by_image.values()
                     if any(r[m] != "" for r in rows)]
            row[m] = float(np.mean(means)) if means else None
        out.append(row)
    return out


def write_summary_md(rows: list[dict], sensitivity: list[dict], path: Path) -> None:
    def cell(row, m, digits=2):
        mean, sd = row[f"{m}_mean_of_image_means"], row[f"{m}_sd_of_image_means"]
        if mean == "":
            return "n/a"
        return f"{mean:.{digits}f}" + ("" if sd == "" else f" ({sd:.{digits}f})")

    lines = [
        "# POL proxy: summary by group",
        "",
        "**Pre-validation.** POL proxy, not a measurement of periosteocytic lesions: the bright lacuna body",
        "plus the surround that stays above the bone background ([DEFINITION.md](DEFINITION.md)). In WT, which",
        "has no lesions, the surround is optical glow ([FINDINGS.md](FINDINGS.md)). Descriptive only: no test",
        "was run and no difference is claimed. Units um and um2 (0.13 um/px).",
        "",
        "Each value is the mean over the group's images of the per-image mean over its measured lacunae",
        "(shape measure and no flag), with the SD between images in brackets. Made by",
        "`python src/pols.py summary` from `results/<group>/pols/<group>_pols_per_image.csv`.",
        "",
        "| group | images | lacunae | with shape measure | flagged | measured | body area | outer area | POL area | POL ratio | halo width, median of sectors |",
        "| - | - | - | - | - | - | - | - | - | - | - |",
    ]
    for r in rows:
        share = "" if r["fraction_flagged_mean"] == "" else f" ({100 * r['fraction_flagged_mean']:.0f}% per image)"
        lines.append(
            f"| {r['group']} | {r['n_images']} ({r['n_images_measured']} with a measured lacuna) "
            f"| {r['n_lacunae']} | {r['n_shape']} | {r['n_flagged']}"
            f"{share} | {r['n_measured']} | {cell(r, 'body_area_um2', 1)} "
            f"| {cell(r, 'outer_area_um2', 1)} | {cell(r, 'pol_area_um2', 1)} | {cell(r, 'pol_ratio')} "
            f"| {cell(r, 'halo_width_median_um')} |")
    lines += ["", "Flagged lacunae are listed in the per-lacuna tables but are in no mean. Images with no",
              "measured lacuna count in the images column and add nothing to the means.", ""]
    lines += ["## Sensitivity: the neighbour flag not applied", "",
              "Not the result. The same group means (mean over images of the per-image mean) with the",
              "neighbour flag left out and every other flag kept, because the Hyp fields are packed so densely",
              "that this one flag decides which of their lacunae are measured.", "",
              "| group | images with a measured lacuna | measured lacunae | outer area | POL area | POL ratio "
              "| halo width, median of sectors |",
              "| - | - | - | - | - | - | - |"]
    for r in sensitivity:
        vals = ["n/a" if r[m] is None else f"{r[m]:.{1 if 'area' in m else 2}f}" for m in SENSITIVITY_MEASURES]
        lines.append(f"| {r['group']} | {r['n_images_measured']} | {r['n_measured']} | " + " | ".join(vals) + " |")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


# Self-test

def _synthetic(shape: tuple, centres: list, radius: float, ramp_px: float, bg: float = 0.2,
               height: float = 0.4) -> tuple:
    """A label image of round bodies and a channel: 1.0 inside a body, and
    outside it a linear fall from bg + height at the edge to bg at ramp_px."""
    rr, cc = np.indices(shape)
    labels = np.zeros(shape, dtype=np.int32)
    for i, (r0, c0) in enumerate(centres, start=1):
        labels[np.hypot(rr - r0, cc - c0) <= radius] = i
    d = ndi.distance_transform_edt(labels == 0)
    channel = bg + height * np.clip(1.0 - d / ramp_px, 0.0, 1.0)
    channel[labels > 0] = 1.0
    return channel, labels


def selftest() -> int:
    """Checks of the geometry and the flags on synthetic images whose answer
    is known. They test the code, not the biology."""
    checks = []

    def check(name, ok, detail=""):
        checks.append(ok)
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))

    no_vessel = np.zeros((400, 400), bool)
    # One round body with a linear surround 20 px wide. The level, a tenth of the
    # height above the background, is crossed 18 px out, so every sector should
    # answer 18 px (2.34 um), give or take the slab.
    channel, labels = _synthetic((400, 400), [(200, 200)], 20, 20)
    res, _outer = measure_image(channel, labels, no_vessel, [])
    widths = [w for state, w in res[0]["sectors"]]
    check("ramp of 20 px: all 8 sectors answer", all(s == "answered" for s, _w in res[0]["sectors"]),
          f"{[s for s, _w in res[0]['sectors']]}")
    check("ramp of 20 px: width 17 to 19 px in every sector", all(w is not None and 17 <= w <= 19 for w in widths),
          f"{widths}")
    check("ramp of 20 px: no flag", not any(res[0]["flags"].values()), f"{res[0]['flags']}")
    expected = np.pi * (20 + 18) ** 2
    check("ramp of 20 px: outer area within 10% of a disk of radius 38 px",
          abs(res[0]["outer_px"] - expected) < 0.1 * expected, f"{res[0]['outer_px']} px against {expected:.0f}")

    # A short ramp, and a bright thread 6 px wide running from the body to the
    # frame: the median must ignore the thread, so its sector stays short too.
    channel, labels = _synthetic((400, 400), [(200, 200)], 20, 3)
    channel[197:203, 200:400][labels[197:203, 200:400] == 0] = 0.9
    res, _outer = measure_image(channel, labels, no_vessel, [])
    widths = [w for _state, w in res[0]["sectors"]]
    check("short ramp with a thread: width at most 3 px in every sector",
          all(w is not None and w <= 3 for w in widths), f"{widths}")

    # Two bodies whose surrounds meet: both flagged neighbour.
    channel, labels = _synthetic((400, 400), [(200, 175), (200, 225)], 20, 20)
    res, _outer = measure_image(channel, labels, no_vessel, [])
    check("two bodies 10 px apart: both flagged neighbour", res[0]["flags"]["neighbour"] and res[1]["flags"]["neighbour"])
    # The same two bodies far apart: neither flagged.
    channel, labels = _synthetic((400, 600), [(200, 150), (200, 450)], 20, 20)
    res, _outer = measure_image(channel, labels, np.zeros((400, 600), bool), [])
    check("two bodies 260 px apart: no flag on either", not any(res[0]["flags"].values())
          and not any(res[1]["flags"].values()))

    # A body 5 px from the frame: flagged edge.
    channel, labels = _synthetic((400, 400), [(200, 25)], 20, 20)
    res, _outer = measure_image(channel, labels, no_vessel, [])
    check("body 5 px from the frame: flagged edge", res[0]["flags"]["edge"])

    # A vessel 40 px from the body edge: flagged vessel, nothing else.
    channel, labels = _synthetic((400, 400), [(200, 200)], 20, 20)
    vessel = no_vessel.copy()
    vessel[:, 260:270] = True
    res, _outer = measure_image(channel, labels, vessel, [])
    others = {k: v for k, v in res[0]["flags"].items() if k != "vessel"}
    check("vessel 40 px from the body: flagged vessel only", res[0]["flags"]["vessel"] and not any(others.values()),
          f"{res[0]['flags']}")

    # A body with no shape measure is not measured and keeps its body only.
    res, outer = measure_image(channel, labels, no_vessel, [1])
    check("no shape measure: not measured, outer region is the body", res[0] is None
          and np.array_equal(outer > 0, labels > 0))

    ok = all(checks)
    print(f"\n{'PASS' if ok else 'FAIL'}: {sum(checks)} of {len(checks)} checks.")
    return 0 if ok else 1


# Command line

def main() -> None:
    parser = argparse.ArgumentParser(description="POL proxy (pre-validation, um): body and the surround above "
                                                 "the bone background. results/pols/DEFINITION.md.")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("measure", help="Measure every image of one group folder.")
    p.add_argument("--dir", type=Path, required=True, help="A group folder of .tif images, e.g. data/Hyp_RD.")
    p.add_argument("-r", "--results", type=Path, default=None,
                   help="The group's results folder, read for the detection output and written under "
                        "pols/ (default: results/<name of the input folder>).")
    p.add_argument("--csv", action="store_true",
                   help="Switch, off by default: also export the per-lacuna and per-image csv tables.")
    p = sub.add_parser("summary", help="Summarise the per-image tables of every group.")
    p.add_argument("--groups", nargs="+", default=list(config.GROUPS), help="Groups (default: config.GROUPS).")
    p.add_argument("-o", "--out", type=Path, default=SUMMARY_DIR, help="Output folder (default: results/pols).")
    sub.add_parser("selftest", help="Checks of the geometry and the flags on synthetic images.")
    args = parser.parse_args()

    if args.command == "selftest":
        sys.exit(selftest())
    if args.command == "measure":
        results_root = args.results or config.RESULTS_ROOT / Path(args.dir).resolve().name
        failed = measure_group(args.dir, results_root, args.csv)
        if failed:
            sys.exit(1)
    else:
        for row in summarize_groups(args.groups, args.out):
            print(f"{row['group']}: {row['n_images']} images, {row['n_measured']} measured lacunae, "
                  f"outer area {row['outer_area_um2_mean_of_image_means']} um2, "
                  f"POL ratio {row['pol_ratio_mean_of_image_means']}")
        print(f"-> {args.out}")


if __name__ == "__main__":
    main()
