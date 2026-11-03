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
It never writes into those folders; it writes its own, 4_pols, beside them.

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

Outputs. Every picture is on the image at its own resolution and says "POL
proxy, pre-validation"; the yellow zone is a proxy, mostly optical glow, never a
lesion call. Per image, in results/<group>/<label>/4_pols/ (SECTION_POLS):
    <label>_pols_overlay.png      QC overlay on the original: body edge cyan,
                                  outer boundary yellow, 1 px, ids, legend,
                                  10 um scale bar
    <label>_pols_outlines.png     body edge and outer boundary only, on the
                                  original dimmed (the 1_lacunae outlines style)
    <label>_pols_measured.png     the review picture: measured lacunae with the
                                  POL band tinted yellow, flagged ones outlined
                                  orange with their flag letters, ids, legend
    <label>_pols.json             parameters, counts, flags, provenance
    with the switch --csv (off by default):
    <label>_pols_per_lacuna.csv   one row per lacuna of this image
Per group, in results/<group>/all_images/pols/:
    contact_sheet.png             every measured picture, small, by image
    with the switch --csv: pols_all_images.csv and .xlsx, one row per image
Across groups, with the command summary, from the all_images tables:
    results/pols/summary_by_group.csv and results/pols/SUMMARY.md
The command check verifies every 4_pols folder (results/pols/layout_check.csv),
and blind-review copies the measured pictures under shuffled codes into
results/blind_review/pols/, with the key outside the repository.

Usage (from the repo root):
    python src/pols.py measure --dir data/WT --csv
    python src/pols.py summary
    python src/pols.py check
    python src/pols.py blind-review -k ../lcn-quant-keys/pols_blind_review_key.csv
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

# Layout and names. The POL section of an image sits beside 1_lacunae and
# 2_canaliculi in results/<group>/<label>/, and the group's table and contact
# sheet in results/<group>/all_images/pols/. Defined here and not in config.py,
# because every upper-case setting of config.py enters the config hash that the
# detection outputs record, and this section must leave those unchanged.
SECTION_POLS = "4_pols"
SUFFIX_OVERLAY = "pols_overlay.png"
SUFFIX_OUTLINES = "pols_outlines.png"
SUFFIX_MEASURED = "pols_measured.png"
SUFFIX_PER_LACUNA = "pols_per_lacuna.csv"
SUFFIX_RECORD = "pols.json"
ALL_IMAGES_POLS_DIR = "pols"
ALL_IMAGES_TABLE = "pols_all_images"  # .csv and .xlsx
CONTACT_SHEET = "contact_sheet.png"
SUMMARY_DIR = config.RESULTS_ROOT / "pols"
BLIND_REVIEW_DIR = config.RESULTS_ROOT / "blind_review" / "pols"
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


# Pictures
# Each picture is drawn on the original image (the outlines picture on the
# original dimmed) at its own resolution, read back after saving, and must equal
# that base on every pixel nothing was drawn on. Visualization only: every line,
# band and id comes from the label image, the outer label image and the rows of
# the per-lacuna table as measured.

# Cyan and yellow stand out on the red stain and on black, and from each other,
# also to a red green colour blind reader; orange marks a flagged lacuna.
LACUNA_RGB = (0, 255, 255)
POL_RGB = (255, 255, 0)
FLAGGED_RGB = (255, 140, 0)
TEXT_RGB = (255, 255, 255)
FONT_PX = 11
SCALE_BAR_UM = 10.0
# The POL band of a measured lacuna (outer region minus body) is tinted POL_RGB
# at this opacity, so the tissue under it stays visible.
BAND_OPACITY = 0.3
# The legend box keeps this share of the image's brightness; the outlines
# picture is drawn on the original kept at this share.
LEGEND_DIM = 0.4
OUTLINES_DIM = 0.5
PICTURE_NOTE = "POL proxy, pre-validation"
LETTER_KEY = ("E edge, V vessel, N neighbour,", "I incomplete, C no contrast")
# The contact sheet: the measured pictures this many to a row, each fitted into a
# square of this many pixels.
CONTACT_COLUMNS = 3
CONTACT_TILE_PX = 340


def marks(rows: list[dict]) -> list[tuple]:
    """(lacuna_id, state, letters) per row of the per-lacuna table, from the rows
    in memory or read back from the csv: state "measured" (POL measure, no flag),
    "flagged" (POL measure and a flag; letters, the flags' letters) or "none" (no
    POL measure: dim or out of focus)."""
    out = []
    for r in rows:
        flagged = str(r.get("flagged", ""))
        if flagged == "":
            out.append((int(r["lacuna_id"]), "none", ""))
        elif flagged == "True":
            letters = "".join(FLAG_LETTERS[name] for name in FLAGS if str(r[f"flag_{name}"]) == "True")
            out.append((int(r["lacuna_id"]), "flagged", letters))
        else:
            out.append((int(r["lacuna_id"]), "measured", ""))
    return out


def id_labels(rows: list[dict]) -> list[tuple]:
    """(lacuna_id, text, colour) of each id drawn on the measured picture: the id
    of the tables, and for a flagged lacuna its flags' letters after it, in orange."""
    return [(i, f"{i} {letters}", FLAGGED_RGB) if state == "flagged" else (i, str(i), TEXT_RGB)
            for i, state, letters in marks(rows)]


def _tint(pixels: np.ndarray, colour: tuple) -> np.ndarray:
    return np.rint((1.0 - BAND_OPACITY) * pixels + BAND_OPACITY * np.array(colour, float)).astype(np.uint8)


def _boundary(outer: np.ndarray, ids) -> np.ndarray:
    """The pixels just outside the outer regions of ids (and where two of them meet)."""
    return segmentation.find_boundaries(np.where(np.isin(outer, sorted(ids)), outer, 0), mode="outer")


def _draw(rgb: np.ndarray, touched: np.ndarray, labels: np.ndarray, outer: np.ndarray, entries: list,
          ids: list) -> np.ndarray:
    """Add a legend and the ids to rgb, a picture whose lines are drawn, and mark
    what they cover in touched. entries: (kind, colour, text) per legend row, kind
    "text", "line" (2 px sample), "band" (tinted swatch) or "bar" (the scale bar);
    the legend goes in the corner holding the fewest outer region pixels. ids:
    (lacuna_id, text, colour), white or coloured with a black edge, right of the
    outer region (left of it at the right frame), level with the body centroid."""
    from PIL import Image, ImageDraw, ImageFont  # noqa: PLC0415

    font = ImageFont.load_default(size=FONT_PX)
    h, w = labels.shape
    sample = {"text": 0, "line": 18, "band": 18, "bar": config.px_int(SCALE_BAR_UM)}
    pad, row_px, margin = 4, FONT_PX + 5, 4
    box_w = 2 * pad + max(sample[k] + (4 if sample[k] else 0) + int(np.ceil(font.getlength(t))) for k, _c, t in entries)
    box_h = 2 * pad + row_px * len(entries)
    corners = [(margin, margin), (margin, w - margin - box_w), (h - margin - box_h, margin),
               (h - margin - box_h, w - margin - box_w)]
    y0, x0 = min(corners, key=lambda yx: int((outer[yx[0]:yx[0] + box_h, yx[1]:yx[1] + box_w] > 0).sum()))
    box = (slice(y0, y0 + box_h), slice(x0, x0 + box_w))
    rgb[box] = (rgb[box] * LEGEND_DIM).astype(np.uint8)
    touched[box] = True
    rows_y = [y0 + pad + k * row_px + row_px // 2 for k in range(len(entries))]
    for (kind, colour, _text), y in zip(entries, rows_y):
        x, n = x0 + pad, sample[kind]
        if kind in ("line", "bar"):
            rgb[y - 1:y + 1, x:x + n] = colour
        elif kind == "band":
            rgb[y - 5:y + 5, x:x + n] = _tint(rgb[y - 5:y + 5, x:x + n], colour)
            rgb[y - 5, x:x + n] = rgb[y + 4, x:x + n] = colour
            rgb[y - 5:y + 5, x] = rgb[y - 5:y + 5, x + n - 1] = colour

    image = Image.fromarray(rgb)
    draw = ImageDraw.Draw(image)
    for (kind, _colour, text), y in zip(entries, rows_y):
        n = sample[kind]
        draw.text((x0 + pad + n + (4 if n else 0), y), text, font=font, fill=TEXT_RGB, anchor="lm")
    n_ids = int(labels.max())
    boxes = ndi.find_objects(outer.astype(np.int32), n_ids)
    centroids = ndi.center_of_mass(labels > 0, labels, range(1, n_ids + 1)) if n_ids else []
    for i, text, colour in ids:
        obox, cy = boxes[i - 1], centroids[i - 1][0]
        if obox is None:
            continue
        x, anchor = obox[1].stop + 2, "lm"
        if x + font.getlength(text) + 2 > w:
            x, anchor = obox[1].start - 3, "rm"
        y = float(np.clip(cy, row_px / 2, h - row_px / 2))
        draw.text((x, y), text, font=font, fill=colour, anchor=anchor, stroke_width=1, stroke_fill=(0, 0, 0))
        left, top, right, bottom = draw.textbbox((x, y), text, font=font, anchor=anchor, stroke_width=1)
        touched[max(0, int(top) - 1):int(np.ceil(bottom)) + 1, max(0, int(left) - 1):int(np.ceil(right)) + 1] = True
    return np.array(image)


def overlay_picture(display: np.ndarray, labels: np.ndarray, outer: np.ndarray, rows: list[dict]) -> tuple:
    """(picture, touched, base). The QC overlay, on the original: each lacuna
    body's edge pixels cyan, each POL proxy outer boundary (every lacuna with a
    POL measure, flagged or not) yellow just outside its outer region, 1 px,
    nothing filled; the ids of the tables, a legend and a scale bar. With no POL
    measure in the image the lacunae are drawn alone. touched: every pixel that
    may differ from base."""
    base = np.array(display[..., :3], dtype=np.uint8)
    rgb = base.copy()
    pol_ids = [i for i, state, _letters in marks(rows) if state != "none"]
    pol_line, body_line = _boundary(outer, pol_ids), segmentation.find_boundaries(labels, mode="inner")
    rgb[pol_line] = POL_RGB
    rgb[body_line] = LACUNA_RGB
    touched = pol_line | body_line
    entries = [("text", None, PICTURE_NOTE), ("line", LACUNA_RGB, "lacuna body"),
               ("line", POL_RGB, "POL proxy outer boundary") if pol_ids
               else ("text", None, "no POL proxy outline in this image"),
               ("bar", TEXT_RGB, f"{SCALE_BAR_UM:g} um")]
    ids = [(i, str(i), TEXT_RGB) for i, _state, _letters in marks(rows)]
    return _draw(rgb, touched, labels, outer, entries, ids), touched, base


def outlines_picture(display: np.ndarray, labels: np.ndarray, outer: np.ndarray, rows: list[dict]) -> tuple:
    """(picture, touched, base). In the style of the 1_lacunae outlines, on the
    original dimmed to OUTLINES_DIM (base): each body's edge cyan and each POL
    proxy outer boundary yellow, 1 px; no ids, only the note POL proxy,
    pre-validation in a corner."""
    base = (np.asarray(display[..., :3], dtype=np.float64) * OUTLINES_DIM).astype(np.uint8)
    rgb = base.copy()
    pol_ids = [i for i, state, _letters in marks(rows) if state != "none"]
    pol_line, body_line = _boundary(outer, pol_ids), segmentation.find_boundaries(labels, mode="inner")
    rgb[pol_line] = POL_RGB
    rgb[body_line] = LACUNA_RGB
    touched = pol_line | body_line
    return _draw(rgb, touched, labels, outer, [("text", None, PICTURE_NOTE)], []), touched, base


def measured_picture(display: np.ndarray, labels: np.ndarray, outer: np.ndarray, rows: list[dict]) -> tuple:
    """(picture, touched, base). The review picture, on the original: every
    lacuna body's edge cyan; for a measured lacuna (POL measure, no flag) its POL
    band (outer region minus body) tinted yellow at BAND_OPACITY and its outer
    boundary yellow; for a flagged lacuna its outer boundary orange, no tint, and
    its flags' letters after its id (id_labels); 1 px lines; a legend with the
    letter key and a scale bar."""
    base = np.array(display[..., :3], dtype=np.uint8)
    rgb = base.copy()
    m = marks(rows)
    measured = [i for i, state, _letters in m if state == "measured"]
    flagged = [i for i, state, _letters in m if state == "flagged"]
    band = np.isin(outer, measured) & (labels == 0)
    rgb[band] = _tint(rgb[band], POL_RGB)
    yellow, orange = _boundary(outer, measured), _boundary(outer, flagged)
    body_line = segmentation.find_boundaries(labels, mode="inner")
    rgb[yellow] = POL_RGB
    rgb[orange] = FLAGGED_RGB
    rgb[body_line] = LACUNA_RGB
    touched = band | yellow | orange | body_line
    entries = [("text", None, PICTURE_NOTE),
               ("line", LACUNA_RGB, "lacuna body (alone: no POL measure)"),
               ("band", POL_RGB, "POL proxy band, pre-validation"),
               ("line", FLAGGED_RGB, "flagged, not in the means"),
               ("text", None, LETTER_KEY[0]), ("text", None, LETTER_KEY[1]),
               ("bar", TEXT_RGB, f"{SCALE_BAR_UM:g} um")]
    return _draw(rgb, touched, labels, outer, entries, id_labels(rows)), touched, base


PICTURES = ((SUFFIX_OVERLAY, overlay_picture), (SUFFIX_OUTLINES, outlines_picture),
            (SUFFIX_MEASURED, measured_picture))


def _read_png(path: Path) -> np.ndarray:
    from PIL import Image  # noqa: PLC0415

    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"))


def save_picture(picture: np.ndarray, touched: np.ndarray, base: np.ndarray, path: Path) -> None:
    """Save a picture as PNG, read the file back and raise unless it equals the
    picture, has the base's size and equals the base on every pixel nothing was
    drawn on: it lies on the image pixel for pixel."""
    from PIL import Image  # noqa: PLC0415

    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(picture).save(path)
    saved = _read_png(path)
    if saved.shape != base.shape or not np.array_equal(saved, picture):
        raise ValueError(f"{path.name}: the file read back is not the picture drawn")
    if not np.array_equal(saved[~touched], base[~touched]):
        raise ValueError(f"{path.name}: the picture differs from the image off its lines, band, ids and legend")


def check_against_table(table: Path, label: str, labels: np.ndarray, outer: np.ndarray, rows: list[dict]) -> int:
    """Compare the lacunae drawn with the image's rows of a per-lacuna table: the
    same ids in the same order, each row's centroid on its body's centroid, and a
    POL outline exactly where the row has an outer area, around a region of that
    area. Raises on a mismatch; returns the rows checked."""
    with open(table, newline="", encoding="utf-8") as f:
        table_rows = [r for r in csv.DictReader(f) if r["image"] == label]
    n = int(labels.max())
    if [int(r["lacuna_id"]) for r in table_rows] != list(range(1, n + 1)):
        raise ValueError(f"the table has {len(table_rows)} rows for the image and the label image ids 1 to {n}")
    pol_ids = {i for i, state, _letters in marks(rows) if state != "none"}
    centroids = ndi.center_of_mass(labels > 0, labels, range(1, n + 1))
    areas = ndi.sum(outer > 0, outer, range(1, n + 1))
    tolerance = 10.0 ** -config.CSV_FLOAT_PRECISION
    for r, (cy, cx), area in zip(table_rows, centroids, areas):
        i = int(r["lacuna_id"])
        if abs(float(r["centroid_row_px"]) - cy) > 0.006 or abs(float(r["centroid_col_px"]) - cx) > 0.006:
            raise ValueError(f"lacuna {i}: the table's centroid is not the label image's")
        has_pol = r.get("outer_area_um2", "") != ""
        if has_pol != (i in pol_ids):
            raise ValueError(f"lacuna {i}: a POL measure in {'the table only' if has_pol else 'the pictures only'}")
        if has_pol and abs(float(r["outer_area_um2"]) - area * UM2_PER_PX) > tolerance:
            raise ValueError(f"lacuna {i}: outer area {r['outer_area_um2']} um2 in the table, "
                             f"{area * UM2_PER_PX:.4f} um2 inside the drawn outline")
    return len(table_rows)


def save_contact_sheet(group: str, results_root: Path, image_labels: list, path: Path) -> None:
    """Every image's measured picture, small, CONTACT_COLUMNS to a row, each
    labelled by image, under a title that says POL proxy, pre-validation."""
    from PIL import Image, ImageDraw, ImageFont  # noqa: PLC0415

    font = ImageFont.load_default(size=FONT_PX)
    tile, gap, label_h, title_h = CONTACT_TILE_PX, 6, 18, 24
    n_rows = max(1, -(-len(image_labels) // CONTACT_COLUMNS))
    width = CONTACT_COLUMNS * tile + (CONTACT_COLUMNS + 1) * gap
    sheet = Image.new("RGB", (width, title_h + n_rows * (tile + label_h + gap) + gap), (0, 0, 0))
    draw = ImageDraw.Draw(sheet)
    draw.text((gap, title_h // 2), f"{group}: the measured pictures, {PICTURE_NOTE}. Yellow band: measured; "
                                   f"orange: flagged, not in the means. Full size: <image>/4_pols/.",
              font=font, fill=TEXT_RGB, anchor="lm")
    for k, label in enumerate(image_labels):
        with Image.open(lacunae.result_path(results_root, label, SECTION_POLS, SUFFIX_MEASURED)) as im:
            scale = tile / max(im.width, im.height)
            thumb = im.convert("RGB").resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        row, col = divmod(k, CONTACT_COLUMNS)
        x, y = gap + col * (tile + gap), title_h + row * (tile + label_h + gap)
        sheet.paste(thumb, (x, y))
        draw.text((x + tile / 2, y + tile + label_h / 2), label, font=font, fill=TEXT_RGB, anchor="mm")
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


# Files

def write_csv(path: Path, columns: list, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, restval="", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_xlsx(path: Path, columns: list, rows: list[dict]) -> None:
    """The same table as sheet per_image, and the note as sheet notes."""
    from openpyxl import Workbook  # noqa: PLC0415

    wb = Workbook()
    sheet = wb.active
    sheet.title = "per_image"
    sheet.append(list(columns))
    for r in rows:
        sheet.append([None if r.get(c, "") == "" else r[c] for c in columns])
    wb.create_sheet("notes").append([NOTE])
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


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


def pols_path(results_root: Path, label: str, suffix: str) -> Path:
    """<results_root>/<label>/4_pols/<label>_<suffix>."""
    return lacunae.result_path(results_root, label, SECTION_POLS, suffix)


def all_images_pols_path(results_root: Path, name: str) -> Path:
    """<results_root>/all_images/pols/<name>."""
    return lacunae.all_images_path(results_root, name, ALL_IMAGES_POLS_DIR)


def write_image_section(results_root: Path, group: str, label: str, display: np.ndarray, labels: np.ndarray,
                        outer: np.ndarray, rows: list[dict], img: dict, export_csv: bool) -> None:
    """The 4_pols folder of one image: the three pictures, each checked
    (save_picture), the record, and with the switch the per-lacuna csv."""
    for suffix, draw in PICTURES:
        save_picture(*draw(display, labels, outer, rows), pols_path(results_root, label, suffix))
    if export_csv:
        write_csv(pols_path(results_root, label, SUFFIX_PER_LACUNA), LACUNA_COLUMNS, rows)
    record = {
        "status": STATUS,
        "units": "um",
        "stage": "POL proxy",
        "group": group,
        "image": label,
        "note": NOTE,
        "csv_exported": bool(export_csv),
        "counts": {"lacunae": img["n_lacunae"], "with_shape_measure": img["n_shape"], "flagged": img["n_flagged"],
                   "measured": img["n_measured"], **{f"flag_{name}": img[f"n_flag_{name}"] for name in FLAGS}},
        "measured_ids": [i for i, state, _letters in marks(rows) if state == "measured"],
        "flagged_ids": [i for i, state, _letters in marks(rows) if state == "flagged"],
        "no_shape_ids": [i for i, state, _letters in marks(rows) if state == "none"],
        "flags": {name: [r["lacuna_id"] for r in rows if r.get(f"flag_{name}") is True] for name in FLAGS},
        "files": [pols_path(results_root, label, s).name
                  for s in (SUFFIX_OVERLAY, SUFFIX_OUTLINES, SUFFIX_MEASURED)
                  + ((SUFFIX_PER_LACUNA,) if export_csv else ()) + (SUFFIX_RECORD,)],
        "parameters": parameters(),
        "provenance": lacunae.provenance(),
    }
    with open(pols_path(results_root, label, SUFFIX_RECORD), "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)


def measure_group(data_dir: Path, results_root: Path, export_csv: bool) -> int:
    """Measure every image of one group folder and write its 4_pols folder, then
    the group's contact sheet and, with the switch, its table in
    all_images/pols/. An image that fails is listed and skipped; the others carry
    on. Returns the number of failures."""
    group = Path(data_dir).resolve().name
    paths = sorted(Path(data_dir).glob("*.tif"))
    if not paths:
        print(f"No .tif image in {data_dir}: nothing to do, nothing written.")
        return 0
    image_table, failures = [], []
    for path in paths:
        label = lacunae.image_label(path)
        try:
            detection = quantification.load_detection(results_root, label)
            quant = json.loads(quantification.quant_path(results_root, label, ".json").read_text(encoding="utf-8"))
            display, channel = lacunae.load_channel(path)
            labels = detection["lacuna_id_map"]
            if labels.shape != channel.shape:
                raise ValueError(f"label image {labels.shape} and image {channel.shape} differ in size")
            if len(quant["lacunae"]) != int(labels.max()):
                raise ValueError("5_quantification and the label image hold different lacuna counts")
            results, outer = measure_image(channel, labels, detection["vascular"], detection["no_shape_ids"])
            glow = canaliculi.glow_extent_px(channel, labels, int(labels.max()))
            rows = lacuna_rows(group, label, results, quant["lacunae"], glow, labels)
            img = image_row(group, label, rows)
            write_image_section(results_root, group, label, display, labels, outer, rows, img, export_csv)
        except Exception as exc:  # an image that fails is listed and the others carry on
            failures.append((label, f"{type(exc).__name__}: {exc}"))
            print(f"{label}: FAILED, skipped ({type(exc).__name__}: {exc})")
            continue
        image_table.append(img)
        print(f"{label}: {img['n_lacunae']} lacunae, {img['n_shape']} with a shape measure, "
              f"{img['n_flagged']} flagged, {img['n_measured']} measured; "
              f"outer area mean {img['outer_area_um2_mean']} um2, POL ratio mean {img['pol_ratio_mean']}")
    if export_csv:
        write_csv(all_images_pols_path(results_root, f"{ALL_IMAGES_TABLE}.csv"), IMAGE_COLUMNS, image_table)
        write_xlsx(all_images_pols_path(results_root, f"{ALL_IMAGES_TABLE}.xlsx"), IMAGE_COLUMNS, image_table)
    save_contact_sheet(group, results_root, [r["image"] for r in image_table],
                       all_images_pols_path(results_root, CONTACT_SHEET))
    lacunae.report_failures(results_root, "pols", failures)
    print(f"-> {results_root}/<image>/{SECTION_POLS}/ and {all_images_pols_path(results_root, '')}"
          + ("" if export_csv else "  (no csv: run with --csv to export the tables)"))
    return len(failures)


# Layout check

CHECK_COLUMNS = ("group", "image", "lacunae", "measured", "flagged", "files_present", "csv_equals_old_table",
                 "pictures_equal_csv")


def check_group(data_dir: Path, results_root: Path) -> list[dict]:
    """One row per image of a group folder: the five files of 4_pols exist; its
    per-lacuna csv equals, value for value, the image's rows of the old group
    table results/<group>/pols/<group>_pols_per_lacuna.csv while that exists (and
    the all_images table equals the old per-image table); and each of the three
    pictures, drawn again from the csv read back (so from its flags), equals the
    saved file pixel for pixel, with the ids, centroids and outer areas matching
    the csv (check_against_table). A failed check is a row with the error."""
    group = Path(data_dir).resolve().name
    old_dir = Path(results_root) / "pols"
    old_lacunae, old_images = old_dir / f"{group}_pols_per_lacuna.csv", old_dir / f"{group}_pols_per_image.csv"
    old_rows = {}
    if old_lacunae.is_file():
        with open(old_lacunae, newline="", encoding="utf-8") as f:
            old_header = csv.DictReader(f).fieldnames
        with open(old_lacunae, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                old_rows.setdefault(r["image"], []).append(r)
    table = all_images_pols_path(results_root, f"{ALL_IMAGES_TABLE}.csv")
    if old_images.is_file() and table.is_file() and old_images.read_bytes() != table.read_bytes():
        raise ValueError(f"{group}: {table.name} is not the old {old_images.name}")
    out = []
    for path in sorted(Path(data_dir).glob("*.tif")):
        label = lacunae.image_label(path)
        row = {"group": group, "image": label}
        try:
            files = [pols_path(results_root, label, s) for s in
                     (SUFFIX_OVERLAY, SUFFIX_OUTLINES, SUFFIX_MEASURED, SUFFIX_PER_LACUNA, SUFFIX_RECORD)]
            missing = [p.name for p in files if not p.is_file()]
            row["files_present"] = not missing
            if missing:
                raise FileNotFoundError(", ".join(missing))
            with open(files[3], newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                header, rows = reader.fieldnames, list(reader)
            if header != list(LACUNA_COLUMNS):
                raise ValueError("the per-lacuna csv does not have the columns of the old table")
            m = marks(rows)
            row.update({"lacunae": len(rows), "measured": sum(1 for _i, s, _l in m if s == "measured"),
                        "flagged": sum(1 for _i, s, _l in m if s == "flagged")})
            if old_rows:
                row["csv_equals_old_table"] = header == old_header and rows == old_rows.get(label)
                if not row["csv_equals_old_table"]:
                    raise ValueError("the per-lacuna csv differs from the old table's rows")
            detection = quantification.load_detection(results_root, label)
            display, channel = lacunae.load_channel(path)
            labels = detection["lacuna_id_map"]
            _results, outer = measure_image(channel, labels, detection["vascular"], detection["no_shape_ids"])
            check_against_table(files[3], label, labels, outer, rows)
            for (suffix, draw), file in zip(PICTURES, files[:3]):
                if not np.array_equal(_read_png(file), draw(display, labels, outer, rows)[0]):
                    raise ValueError(f"{file.name} is not the picture the csv gives")
            row["pictures_equal_csv"] = True
        except Exception as exc:  # reported per image
            row["error"] = f"{type(exc).__name__}: {exc}"
        out.append(row)
    return out


# Blinded review set

def _inside(path: Path, root: Path) -> bool:
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def blind_review(groups, key: Path, out_dir: Path) -> int:
    """Copy every image's measured picture into one flat folder under shuffled
    codes P001, P002, ... and write the key (code, group, image) to key, which
    must lie outside the repository and must not exist yet; the output folder
    must be empty. The order comes from the system's random source, so the key is
    the only way back. The pictures carry no image name, group or genotype."""
    import random  # noqa: PLC0415
    import shutil  # noqa: PLC0415

    if _inside(key, config.PROJECT_ROOT):
        print("Refused: the key path is inside the repository. Put the key outside it, so it can never be committed.")
        return 2
    if key.exists():
        print("Refused: the key file already exists. Choose a new path; an existing key is never overwritten.")
        return 2
    sources = []
    for group in groups:
        for path in sorted((config.DATA_DIR / group).glob("*.tif")):
            label = lacunae.image_label(path)
            sources.append((group, label, pols_path(config.RESULTS_ROOT / group, label, SUFFIX_MEASURED)))
    missing = [str(p) for _g, _l, p in sources if not p.is_file()]
    if missing:
        print(f"Refused: {len(missing)} measured picture(s) missing, e.g. {missing[0]}. Run measure first.")
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    if any(out_dir.iterdir()):
        print("Refused: the output folder is not empty.")
        return 2
    seed = random.SystemRandom().randrange(2 ** 32)
    order = list(range(len(sources)))
    random.Random(seed).shuffle(order)
    key_rows = []
    for k, index in enumerate(order, start=1):
        group, label, source = sources[index]
        code = f"P{k:03d}"
        shutil.copyfile(source, out_dir / f"{code}.png")
        key_rows.append([code, group, label, str(source.relative_to(config.PROJECT_ROOT)), seed])
    key.parent.mkdir(parents=True, exist_ok=True)
    with open(key, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["code", "group", "image", "source", "seed"])
        writer.writerows(key_rows)
    print(f"{len(sources)} measured pictures coded P001 to P{len(sources):03d} into {out_dir}. Key written to {key}.")
    return 0


# Group summary

SUMMARY_COLUMNS = (["status", "group", "n_images", "n_images_measured", "n_lacunae", "n_shape", "n_flagged",
                    "n_measured", "fraction_flagged_mean"]
                   + [f"{m}_{stat}" for m in MEASURES for stat in ("mean_of_image_means", "sd_of_image_means")])


def group_images(group: str) -> list[dict]:
    """The rows of a group's all_images table, in the order measure wrote them."""
    path = all_images_pols_path(config.RESULTS_ROOT / group, f"{ALL_IMAGES_TABLE}.csv")
    if not path.is_file():
        raise FileNotFoundError(f"{path} is missing: run python src/pols.py measure --dir data/{group} --csv")
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def summarize_groups(groups, out_dir: Path) -> list[dict]:
    """results/pols/summary_by_group.csv and SUMMARY.md: per group, the mean
    and SD over images of each per-image mean, with the counts."""
    rows = []
    for group in groups:
        images = group_images(group)

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
        lacunae_rows = []
        for image in group_images(group):
            with open(pols_path(config.RESULTS_ROOT / group, image["image"], SUFFIX_PER_LACUNA), newline="",
                      encoding="utf-8") as f:
                lacunae_rows += [r for r in csv.DictReader(f) if r["flagged"] != ""]
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
        "`python src/pols.py summary` from `results/<group>/all_images/pols/pols_all_images.csv`.",
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

    def rows_of(results):
        """The id and flag columns of the per-lacuna rows of synthetic results."""
        rows = []
        for i, res in enumerate(results, start=1):
            row = {"lacuna_id": i}
            if res is not None:
                row["flagged"] = any(res["flags"].values())
                row.update({f"flag_{name}": res["flags"][name] for name in FLAGS})
            rows.append(row)
        return rows

    def edge(labels):
        return segmentation.find_boundaries(labels, mode="inner")

    # The overlay picture: the image's size, unchanged off what is drawn, the body
    # edge cyan and the POL outline yellow; with no POL measure, the lacunae alone.
    channel, labels = _synthetic((400, 400), [(200, 200)], 20, 20)
    display = np.stack([(channel * 255).astype(np.uint8)] * 3, axis=-1)
    res, outer = measure_image(channel, labels, no_vessel, [])
    picture, touched, _base = overlay_picture(display, labels, outer, rows_of(res))
    check("overlay picture: the image's size, and equal to the image off the lines, ids and legend",
          picture.shape == display.shape and np.array_equal(picture[~touched], display[~touched]))
    body_share = (picture[edge(labels)] == LACUNA_RGB).all(axis=-1).mean()
    pol_share = (picture[_boundary(outer, [1])] == POL_RGB).all(axis=-1).mean()
    check("overlay picture: body edge cyan and POL outline yellow on at least 90% of their pixels",
          body_share >= 0.9 and pol_share >= 0.9, f"{body_share:.2f}, {pol_share:.2f}")
    res, outer = measure_image(channel, labels, no_vessel, [1])
    picture, _touched, _base = overlay_picture(display, labels, outer, rows_of(res))
    body_share = (picture[edge(labels)] == LACUNA_RGB).all(axis=-1).mean()
    check("overlay picture with no POL measure: lacunae only, no pixel of the POL colour",
          not (picture == POL_RGB).all(axis=-1).any() and body_share >= 0.9, f"{body_share:.2f}")

    # The measured picture: lacuna 1 measured, lacuna 2 flagged (5 px from the frame).
    channel, labels = _synthetic((400, 600), [(200, 300), (200, 25)], 20, 20)
    display = np.stack([(channel * 255).astype(np.uint8)] * 3, axis=-1)
    res, outer = measure_image(channel, labels, np.zeros((400, 600), bool), [])
    rows = rows_of(res)
    picture, touched, _base = measured_picture(display, labels, outer, rows)
    lines = edge(labels) | _boundary(outer, [1, 2])
    band1, band2 = ((outer == i) & (labels == 0) & ~lines for i in (1, 2))
    bodies = (labels > 0) & ~lines
    check("measured picture: the tint on the measured lacuna's band only, not on the flagged one's or a body",
          [state for _i, state, _letters in marks(rows)] == ["measured", "flagged"] and band1.any() and band2.any()
          and np.array_equal(picture[band1], _tint(display[band1], POL_RGB))
          and np.array_equal(picture[band2], display[band2]) and np.array_equal(picture[bodies], display[bodies])
          and np.array_equal(picture[~touched], display[~touched]))
    yellow = (picture[_boundary(outer, [1])] == POL_RGB).all(axis=-1).mean()
    orange = (picture[_boundary(outer, [2])] == FLAGGED_RGB).all(axis=-1).mean()
    check("measured picture: the measured lacuna's outline yellow, the flagged one's orange",
          yellow >= 0.9 and orange >= 0.9, f"{yellow:.2f}, {orange:.2f}")
    letters = "".join(FLAG_LETTERS[name] for name in FLAGS if res[1]["flags"][name])
    check("flag letters: the flagged id carries its flags' letters in orange, the measured id none",
          id_labels(rows) == [(1, "1", TEXT_RGB), (2, f"2 {letters}", FLAGGED_RGB)] and letters.startswith("E"),
          f"{id_labels(rows)}")
    # The same rows as the csv holds them, every value a string: the same marks,
    # so a picture drawn from the csv read back is the picture drawn from memory.
    as_csv = [{k: str(v) for k, v in r.items()} for r in rows]
    check("pictures drawn from the csv strings equal those drawn from memory",
          all(np.array_equal(draw(display, labels, outer, as_csv)[0], draw(display, labels, outer, rows)[0])
              for _suffix, draw in PICTURES))

    # The outlines picture: the image dimmed, unchanged off its lines and note, no tint.
    picture, touched, base = outlines_picture(display, labels, outer, rows)
    check("outlines picture: the dimmed image, unchanged off its lines and note, no tint",
          np.array_equal(base, (display * OUTLINES_DIM).astype(np.uint8))
          and np.array_equal(picture[~touched], base[~touched]) and np.array_equal(picture[band1], base[band1]))

    ok = all(checks)
    print(f"\n{'PASS' if ok else 'FAIL'}: {sum(checks)} of {len(checks)} checks.")
    return 0 if ok else 1


# Command line

def main() -> None:
    parser = argparse.ArgumentParser(description="POL proxy (pre-validation, um): body and the surround above "
                                                 "the bone background. results/pols/DEFINITION.md.")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("measure", help="Measure every image of one group folder: results/<group>/<image>/4_pols/ "
                                       "and results/<group>/all_images/pols/.")
    p.add_argument("--dir", type=Path, required=True, help="A group folder of .tif images, e.g. data/Hyp_RD.")
    p.add_argument("-r", "--results", type=Path, default=None,
                   help="The group's results folder, read for the detection output and written under "
                        "<image>/4_pols/ and all_images/pols/ (default: results/<name of the input folder>).")
    p.add_argument("--csv", action="store_true",
                   help="Switch, off by default: also export the tables, <image>_pols_per_lacuna.csv per image "
                        "and pols_all_images.csv and .xlsx per group.")
    p = sub.add_parser("summary", help="Summarise the all_images tables of every group: results/pols/.")
    p.add_argument("--groups", nargs="+", default=list(config.GROUPS), help="Groups (default: config.GROUPS).")
    p.add_argument("-o", "--out", type=Path, default=SUMMARY_DIR, help="Output folder (default: results/pols).")
    p = sub.add_parser("check", help="Check the 4_pols folder of every image: files, csv, pictures against the csv.")
    p.add_argument("--groups", nargs="+", default=list(config.GROUPS), help="Groups (default: config.GROUPS).")
    p.add_argument("-o", "--out", type=Path, default=SUMMARY_DIR / "layout_check.csv",
                   help="The table of the check (default: results/pols/layout_check.csv).")
    p = sub.add_parser("blind-review", help="Copy every measured picture into results/blind_review/pols/ under "
                                            "shuffled codes; the key is written outside the repository.")
    p.add_argument("-k", "--key", type=Path, required=True,
                   help="The key to write, a csv outside the repository that does not exist yet, "
                        "e.g. ../lcn-quant-keys/pols_blind_review_key.csv.")
    p.add_argument("--groups", nargs="+", default=list(config.GROUPS), help="Groups (default: config.GROUPS).")
    p.add_argument("-o", "--out", type=Path, default=BLIND_REVIEW_DIR,
                   help="The flat output folder, empty (default: results/blind_review/pols).")
    sub.add_parser("selftest", help="Checks of the geometry, the flags and the pictures on synthetic images.")
    args = parser.parse_args()

    if args.command == "selftest":
        sys.exit(selftest())
    if args.command == "blind-review":
        sys.exit(blind_review(args.groups, args.key, args.out))
    if args.command == "check":
        rows = []
        for group in args.groups:
            rows += check_group(config.DATA_DIR / group, config.RESULTS_ROOT / group)
        write_csv(args.out, list(CHECK_COLUMNS) + ["error"], rows)
        print(f"{'group':<8} {'image':<26} {'lacunae':>7} {'measured':>8} {'flagged':>7}  check")
        for r in rows:
            print(f"{r['group']:<8} {r['image']:<26} {r.get('lacunae', ''):>7} {r.get('measured', ''):>8} "
                  f"{r.get('flagged', ''):>7}  {r.get('error', 'PASS')}")
        failed = [r for r in rows if "error" in r]
        print(f"\n{'FAIL' if failed else 'PASS'}: {len(rows) - len(failed)} of {len(rows)} images; "
              f"old tables {'compared' if any(r.get('csv_equals_old_table') for r in rows) else 'not present'}. "
              f"-> {args.out}")
        sys.exit(1 if failed else 0)
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
