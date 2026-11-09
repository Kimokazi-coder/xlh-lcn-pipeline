"""The POL section: candidate POL measure, lacunar size, pending definition.

PRE-VALIDATION. Periosteocytic lesions (POLs) are enlarged lacunae. There is
no agreed definition of a POL in these images yet, so this section shows the
one candidate that needs no new detection: the size of each lacuna, set against
the WT median. It is not a lesion call, and every output says
"candidate POL measure: lacunar size, pending definition".

The ring proxy that this section showed before is retired: it measured the dye
glow around every lacuna, the same width in WT, and not lesions. Its code
(src/pol_ring_proxy.py) and outputs were deleted on 2026-11-09; they are in
git history (tag method-freeze-v2).

Nothing is detected again. Per image it reads what the pipeline saved in
results/<group>/: each lacuna's area, frame flag and class from
4_quantification/<label>_quantification.json, and the label image from
1_lacunae/<label>_lacuna_labels.png (ids 1..N, the same numbering).

Units: um2, at config.PIXEL_SIZE_UM_ACQUIRED (0.13 um/px, so 0.0169 um2 per
px2). The rest of the pipeline reports pixels; areas here are the same
numbers times that factor.

Per lacuna:
    area_um2             area_px2 x 0.0169, empty when the lacuna has no area
    ratio_to_WT_median   area_um2 / the WT median, empty when flagged
    flag                 edge     the lacuna touches the frame, so its area is cut
                         no_area  its class (dim, out_of_focus) has no area measure
                         empty    measured
The WT median is the median area of every measured (unflagged) lacuna of the 8
WT images, pooled, recomputed from results/WT/ on every run.

Outputs, per group, in results/<group>/3_pols/:
    <label>_pols_lacunar_size.png   the original image, each measured lacuna
                                    filled with the colour of its ratio to the
                                    WT median (one scale for every group, the
                                    colour bar in um2), id and area beside it;
                                    flagged lacunae outlined grey, not filled;
                                    10 um scale bar
    <label>_pols_lacunar_size.csv   id, area_um2, ratio_to_WT_median, flag
    pols_all_images.csv and .xlsx   per image: n measured, mean, median and
                                    90th percentile of area and of ratio
    contact_sheet.png               every lacunar size picture, small
    README.md                       what the section holds
Across groups: results/summary/pols_lacunar_size_by_group.csv, the same
statistics per group, every measured lacuna of the group pooled.

Usage (from the repo root):
    python src/pols.py measure -d data/WT_HP     # one group
    python src/pols.py all                       # every group, then the summary
    python src/pols.py check                     # every file against the jsons
    python src/pols.py selftest
"""

from __future__ import annotations

import argparse
import csv
import gc
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lacunae  # noqa: E402
import quantification  # noqa: E402

LABEL = "candidate POL measure: lacunar size, pending definition"
UM_PER_PX = config.PIXEL_SIZE_UM_ACQUIRED
UM2_PER_PX2 = UM_PER_PX ** 2

SUFFIX_PICTURE = "pols_lacunar_size.png"
SUFFIX_TABLE = "pols_lacunar_size.csv"
GROUP_TABLE = "pols_all_images"  # .csv and .xlsx
CONTACT_SHEET = "contact_sheet.png"
SUMMARY_TABLE = config.SUMMARY_ROOT / "pols_lacunar_size_by_group.csv"

LACUNA_COLUMNS = ["id", "area_um2", "ratio_to_WT_median", "flag", "cluster"]
STAT_COLUMNS = ["n", "n_flagged", "area_um2_mean", "area_um2_median", "area_um2_p90",
                "ratio_mean", "ratio_median", "ratio_p90"]
# The POL metrics (finishing brief of 2026-11-06, phase 4), appended so no
# earlier column moves. Over the measured lacunae: the share above 2 times the
# WT median and above POL_LARGE_AREA_UM2, and the clusters (config section
# g9). Over every lacuna with an area, edge ones included (their part inside
# the frame lies in the field): the summed area over the analysed area, the
# image minus the excluded region (config section g9).
POL_COLUMNS = ["n_lacunae", "share_above_2x_WT_median", "share_above_100_um2", "n_clusters",
               "lacunar_area_um2", "analysed_area_um2", "excluded_area_um2", "pol_area_per_analysed_area"]
IMAGE_COLUMNS = ["status", "group", "image"] + STAT_COLUMNS + ["WT_median_area_um2"] + POL_COLUMNS
GROUP_COLUMNS = ["status", "group", "n_images"] + STAT_COLUMNS + ["WT_median_area_um2"] + POL_COLUMNS
ANIMAL_COLUMNS = (["status", "animal", "genotype", "diet", "group", "confirmed", "n_images"] + STAT_COLUMNS
                  + ["WT_median_area_um2"] + POL_COLUMNS)
ANIMAL_TABLE = config.SUMMARY_ROOT / "pols_by_animal.csv"
ANIMALS_FILE = config.DATA_DIR / "animals.csv"
# The brief's fixed size line, beside the 2 x WT median one.
POL_LARGE_AREA_UM2 = 100.0
POL_RATIO_LINE = 2.0
DIGITS = 4

# Picture. One colour scale for every group: the ratio to the WT median on a
# log2 axis from 1/4 to 4 times, clipped at both ends, so a lacuna of the WT
# median size is the middle colour everywhere. viridis is colour-blind safe and
# has no white that could vanish on a bright lacuna. Display only.
RATIO_LIMITS = (0.25, 4.0)
RATIO_TICKS = (0.25, 0.5, 1.0, 2.0, 4.0)
COLOUR_MAP = "viridis"
FILL_ALPHA = 0.7
SCALE_BAR_UM = 10.0


# The judge-on set (2026-11-09): the same section, made the same way from the
# lacunae the AI lacuna judge accepted, in results/<group>/3_pols/ai_judge/. It
# reads that set's quantification and label image (results/<group>/<section>/
# ai_judge/), and its ratios are against the WT median of the same set, so
# each method is measured against its own reference group.
JUDGE_SET = config.AI_LACUNA_SUBFOLDER
SETS = (JUDGE_SET,)
JUDGE_PICTURE_CHECK_TABLE = config.ARCHIVE_ROOT / "judge" / "POL_PICTURE_CHECK_ai_judge.csv"


def set_root(group: str, set_name: str | None = None) -> Path:
    """The results root of a group, or of one of its result sets."""
    group_root = config.RESULTS_ROOT / group
    return config.result_set_root(group_root, set_name) if set_name else group_root


def set_note(set_name: str | None) -> str:
    """What a picture title adds for a result set; nothing for the method itself."""
    return " AI lacuna judge on." if set_name == JUDGE_SET else ""


# Numbers

def _round(value):
    return None if value is None else round(float(value), DIGITS)


def image_files(group: str) -> list[Path]:
    """The group's images, without the held-out ones in DEV mode (docs/HOLDOUT.md)."""
    return lacunae.without_held_out(sorted((config.DATA_DIR / group).glob("*.tif")))


def quant_json(results_root: Path, label: str) -> dict:
    return json.loads(quantification.quant_path(results_root, label, ".json").read_text(encoding="utf-8"))


def lacuna_records(results_root: Path, label: str) -> list[dict]:
    """The quantification json's lacunae of one image, as {id, area_px2, flag,
    cluster}. cluster is None in a json made before the flag existed."""
    out = []
    for r in quant_json(results_root, label)["lacunae"]:
        if r["area_px2"] is None:
            flag = "no_area"
        elif r["on_border"]:
            flag = "edge"
        else:
            flag = ""
        out.append({"id": int(r["lacuna_id"]), "area_px2": r["area_px2"], "flag": flag,
                    "cluster": r.get("cluster")})
    return out


def field_areas_um2(results_root: Path, label: str) -> tuple[float, float]:
    """(analysed area, excluded area) of one image in um2, from its
    quantification json. A json made before the excluded region existed has
    nothing excluded, so the analysed area is the whole image."""
    q = quant_json(results_root, label)
    field = q["field"]
    if "analysed_field_area_px2" in field:
        return field["analysed_field_area_px2"] * UM2_PER_PX2, field["excluded_area_px2"] * UM2_PER_PX2
    labels = lacunae.result_path(results_root, label, config.SECTION_LACUNAE, config.SUFFIX_LACUNA_LABELS)
    from PIL import Image  # noqa: PLC0415

    with Image.open(labels) as im:
        w, h = im.size
    return w * h * UM2_PER_PX2, 0.0


def wt_median_um2(set_name: str | None = None) -> float:
    """Median area of every measured WT lacuna, pooled over the WT images, of
    the method itself or of one of its result sets."""
    root = set_root(config.REFERENCE_GROUP, set_name)
    areas = [r["area_px2"] * UM2_PER_PX2
             for p in image_files(config.REFERENCE_GROUP)
             for r in lacuna_records(root, lacunae.image_label(p)) if not r["flag"]]
    if not areas:
        raise FileNotFoundError(f"no measured WT lacuna in {root}")
    return float(np.median(areas))


def cluster_word(value) -> str:
    """The cluster flag as the tables write it: yes, no, or empty when unknown."""
    return "" if value is None else ("yes" if value else "no")


def lacuna_rows(records: list[dict], wt_median: float) -> list[dict]:
    rows = []
    for r in records:
        area = None if r["area_px2"] is None else r["area_px2"] * UM2_PER_PX2
        ratio = area / wt_median if (area is not None and not r["flag"]) else None
        rows.append({"id": r["id"], "area_um2": _round(area), "ratio_to_WT_median": _round(ratio),
                     "flag": r["flag"], "cluster": cluster_word(r.get("cluster"))})
    return rows


def stats(rows: list[dict]) -> dict:
    """n measured and flagged; mean, median, 90th percentile of area and ratio
    over the measured lacunae. Computed from the unrounded areas."""
    measured = [r for r in rows if not r["flag"]]
    areas = np.array([r["_area"] for r in measured], dtype=float)
    ratios = np.array([r["_ratio"] for r in measured], dtype=float)
    out = {"n": len(measured), "n_flagged": len(rows) - len(measured)}
    for name, values in (("area_um2", areas), ("ratio", ratios)):
        empty = values.size == 0
        out[f"{name}_mean"] = None if empty else _round(values.mean())
        out[f"{name}_median"] = None if empty else _round(np.median(values))
        out[f"{name}_p90"] = None if empty else _round(np.percentile(values, 90))
    return out


def with_raw(records: list[dict], wt_median: float) -> list[dict]:
    """The rows with their unrounded area and ratio, for the statistics."""
    rows = lacuna_rows(records, wt_median)
    for row, r in zip(rows, records):
        row["_area"] = None if r["area_px2"] is None else r["area_px2"] * UM2_PER_PX2
        row["_ratio"] = None if (row["_area"] is None or r["flag"]) else row["_area"] / wt_median
    return rows


def pol_metrics(rows: list[dict], analysed_um2: float, excluded_um2: float) -> dict:
    """The POL metrics (POL_COLUMNS) of a set of lacunae, rows as with_raw
    makes them, over a field of analysed_um2 (the summed analysed areas when
    the rows come from several images)."""
    measured = [r for r in rows if not r["flag"]]
    n = len(measured)
    summed = float(sum(r["_area"] for r in rows if r["_area"] is not None))
    return {
        "n_lacunae": len(rows),
        "share_above_2x_WT_median": _round(sum(r["_ratio"] > POL_RATIO_LINE for r in measured) / n) if n else None,
        "share_above_100_um2": _round(sum(r["_area"] > POL_LARGE_AREA_UM2 for r in measured) / n) if n else None,
        "n_clusters": sum(r["cluster"] == "yes" for r in measured),
        "lacunar_area_um2": _round(summed),
        "analysed_area_um2": _round(analysed_um2),
        "excluded_area_um2": _round(excluded_um2),
        "pol_area_per_analysed_area": _round(summed / analysed_um2) if analysed_um2 > 0 else None,
    }


def animal_map() -> dict:
    """{(group, image label): its row of data/animals.csv}."""
    with open(ANIMALS_FILE, newline="", encoding="utf-8") as f:
        return {(r["group"], r["image_label"]): r for r in csv.DictReader(f)}


# Files

def write_csv(path: Path, columns: list, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore", restval="", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r.get(c) is None else r.get(c)) for c in columns})


def write_xlsx(path: Path, columns: list, rows: list[dict], notes: list[str]) -> None:
    from openpyxl import Workbook  # noqa: PLC0415

    wb = Workbook()
    sheet = wb.active
    sheet.title = "per_image"
    sheet.append(list(columns))
    for r in rows:
        sheet.append([r.get(c) for c in columns])
    notes_sheet = wb.create_sheet("notes")
    for line in notes:
        notes_sheet.append([line])
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def notes(wt_median: float) -> list[str]:
    return [f"PRE-VALIDATION. {LABEL}.",
            f"Area um2 = area px2 x {UM2_PER_PX2:g} ({UM_PER_PX} um/px). Ratio = area / WT median "
            f"({wt_median:.4f} um2, every measured WT lacuna pooled).",
            "Measured: interior lacunae with an area. Flagged and left out of every statistic: edge "
            "(touches the frame, area cut) and no_area (classes dim and out_of_focus have no area).",
            "n_lacunae: every lacuna, edge ones included. share_above_2x_WT_median and share_above_100_um2: "
            "of the measured lacunae. n_clusters: measured lacunae flagged cluster (two or more lacuna "
            "bodies joined by a neck under 3 um, config section g9).",
            "pol_area_per_analysed_area: the summed area of every lacuna with an area (edge ones included) "
            "over the analysed area, the image minus the excluded region (saturated border regions and very "
            "large structures, config section g9).",
            "Working POL definition (to be confirmed by Dr. Murshed): the enlarged, irregular, dye-filled "
            "lacunar space is the POL footprint (docs/METHODS.md, 24.0).",
            "Source: 4_quantification/<image>_quantification.json. No new detection. src/pols.py."]


# Picture
# Drawn pixel for pixel with Pillow, so that what it shows can be checked:
# the image region is the original image at its own size, and only the masks
# of the lacunae change colour in it. A measured lacuna is filled inside its
# own mask and nowhere else; a flagged one gets a 1 px grey line on the inner
# edge of its mask, also inside it. No ring, band, halo or any shape outside a
# mask is drawn. The labels and the scale bar are text and a bar on the image,
# each recorded as a box; the title and the colour bar sit outside the image.

TITLE_H = 34
PANEL_W = 260
FONT_PX = 12
GREY = (166, 166, 166)
BAR_TOP, BAR_HEIGHT, BAR_X, BAR_W = 90, 560, 40, 24
SCALE_BAR_PX = int(round(SCALE_BAR_UM / UM_PER_PX))


def fill_colour(ratio: float) -> np.ndarray:
    """The colour of a ratio to the WT median on the fixed log scale, uint8."""
    from matplotlib import colormaps  # noqa: PLC0415

    lo, hi = np.log(RATIO_LIMITS[0]), np.log(RATIO_LIMITS[1])
    x = float(np.clip((np.log(ratio) - lo) / (hi - lo), 0.0, 1.0))
    return np.rint(np.asarray(colormaps[COLOUR_MAP](x)[:3]) * 255).astype(np.uint8)


def read_table(path: Path) -> list[dict]:
    """A per-image table as written: id int, area and ratio float or None."""
    with open(path, newline="", encoding="utf-8") as f:
        return [{"id": int(r["id"]), "area_um2": float(r["area_um2"]) if r["area_um2"] else None,
                 "ratio_to_WT_median": float(r["ratio_to_WT_median"]) if r["ratio_to_WT_median"] else None,
                 "flag": r["flag"], "cluster": r.get("cluster", "")} for r in csv.DictReader(f)]


def label_text(row: dict) -> str:
    if row["area_um2"] is None:
        return f"{row['id']}: no area"
    return f"{row['id']}: {row['area_um2']:.1f}" + (" (edge)" if row["flag"] == "edge" else "")


def render_picture(display: np.ndarray, labels: np.ndarray, rows: list[dict], wt_median: float,
                   title: str) -> tuple[np.ndarray, list]:
    """The picture as an array, and the boxes (x0, y0, x1, y1, in image
    coordinates) of everything drawn that is not a lacuna mask: the labels and
    the scale bar."""
    from PIL import Image, ImageDraw, ImageFont  # noqa: PLC0415
    from scipy import ndimage as ndi  # noqa: PLC0415

    h, w = labels.shape
    region = display.astype(np.float64)
    for r in rows:
        mask = labels == r["id"]
        if r["flag"]:
            edge = mask & ~ndi.binary_erosion(mask)
            region[edge] = GREY
        else:
            region[mask] = (1 - FILL_ALPHA) * region[mask] + FILL_ALPHA * fill_colour(r["ratio_to_WT_median"])
    region = np.rint(region).astype(np.uint8)

    canvas = Image.new("RGB", (w + PANEL_W, h + TITLE_H), (255, 255, 255))
    canvas.paste(Image.fromarray(region), (0, TITLE_H))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=FONT_PX)
    boxes = []

    def text_on_image(x, y, s, fill, anchor):
        box = draw.textbbox((x, y + TITLE_H), s, font=font, anchor=anchor, stroke_width=1)
        draw.text((x, y + TITLE_H), s, font=font, anchor=anchor, fill=fill, stroke_width=1, stroke_fill=(0, 0, 0))
        boxes.append((int(np.floor(box[0])), int(np.floor(box[1])) - TITLE_H,
                      int(np.ceil(box[2])), int(np.ceil(box[3])) - TITLE_H))

    for r in rows:
        ys, xs = np.nonzero(labels == r["id"])
        if xs.size == 0:
            continue
        y = float(np.clip(ys.mean(), 10, h - 10))
        if xs.max() + 70 < w:
            text_on_image(int(xs.max()) + 4, y, label_text(r), (255, 255, 255) if not r["flag"] else GREY, "lm")
        else:
            text_on_image(int(xs.min()) - 4, y, label_text(r), (255, 255, 255) if not r["flag"] else GREY, "rm")
    x1, y0 = w - 20, h - 22
    draw.rectangle([x1 - SCALE_BAR_PX, y0 + TITLE_H, x1 - 1, y0 + 3 + TITLE_H], fill=(255, 255, 255))
    boxes.append((x1 - SCALE_BAR_PX, y0, x1, y0 + 4))
    text_on_image(x1 - SCALE_BAR_PX // 2, y0 - 3, f"{SCALE_BAR_UM:g} um", (255, 255, 255), "mb")

    draw.text((8, TITLE_H // 2), title, font=ImageFont.load_default(size=15), anchor="lm", fill=(0, 0, 0))
    px, py = w + BAR_X, TITLE_H + BAR_TOP
    draw.text((w + 12, TITLE_H + 14), "lacunar area (um2)", font=font, fill=(0, 0, 0))
    draw.text((w + 12, TITLE_H + 32), "colour: area / WT median", font=font, fill=(0, 0, 0))
    draw.text((w + 12, TITLE_H + 50), "same scale, every group", font=font, fill=(0, 0, 0))
    lo, hi = np.log(RATIO_LIMITS[0]), np.log(RATIO_LIMITS[1])
    for i in range(BAR_HEIGHT):
        ratio = float(np.exp(hi - (hi - lo) * i / (BAR_HEIGHT - 1)))
        draw.line([px, py + i, px + BAR_W - 1, py + i], fill=tuple(int(v) for v in fill_colour(ratio)))
    draw.rectangle([px, py, px + BAR_W - 1, py + BAR_HEIGHT - 1], outline=(0, 0, 0))
    for ratio in RATIO_TICKS:
        yy = py + int(round((hi - np.log(ratio)) / (hi - lo) * (BAR_HEIGHT - 1)))
        is_median = ratio == 1.0
        draw.line([px + BAR_W, yy, px + BAR_W + (14 if is_median else 6), yy], fill=(0, 0, 0), width=3 if is_median else 1)
        text = f"{ratio * wt_median:.1f}" + ("  WT median" if is_median else "")
        draw.text((px + BAR_W + 18, yy), text, font=font, anchor="lm", fill=(0, 0, 0))
    gy = py + BAR_HEIGHT + 28
    draw.rectangle([px, gy, px + BAR_W - 1, gy + 14], outline=GREY, width=1)
    draw.text((px + BAR_W + 8, gy + 7), "flagged: grey outline,", font=font, anchor="lm", fill=(0, 0, 0))
    draw.text((px + BAR_W + 8, gy + 23), "not filled (edge, no area)", font=font, anchor="lm", fill=(0, 0, 0))
    draw.text((w + 12, gy + 52), "labels: id: area in um2", font=font, fill=(0, 0, 0))
    out = np.asarray(canvas).copy()
    canvas.close()
    return out, boxes


def picture_title(group: str, label: str, set_name: str | None = None) -> str:
    return f"{group} {label}: {LABEL}.{set_note(set_name)} Pre-validation, not a lesion call."


# The POL outline picture (finishing brief, phase 4): every POL footprint, the
# lacuna as the lacuna stage outlined it, outlined on the original image in
# the 2 px style of the lacuna outline picture, its colour saying which kind
# it is; excluded regions shaded grey. Display only.
SUFFIX_OUTLINES = "pols_outlines.png"
OUTLINES_CONTACT_SHEET = "contact_sheet_outlines.png"
OUTLINE_NORMAL = (0, 255, 0)      # the green of the lacuna outline picture
OUTLINE_ENLARGED = (255, 255, 0)
OUTLINE_CLUSTER = (0, 255, 255)
OUTLINE_EDGE = GREY
OUTLINES_PANEL_W = 330


def outline_kind(row: dict) -> str:
    """edge, cluster, enlarged or normal: the colour of one footprint. Edge
    and no-area lacunae are not measured, so they are neither of the others."""
    if row["flag"]:
        return "edge"
    if row["cluster"] == "yes":
        return "cluster"
    if row["ratio_to_WT_median"] is not None and row["ratio_to_WT_median"] > POL_RATIO_LINE:
        return "enlarged"
    return "normal"


OUTLINE_COLOURS = {"normal": OUTLINE_NORMAL, "enlarged": OUTLINE_ENLARGED, "cluster": OUTLINE_CLUSTER,
                   "edge": OUTLINE_EDGE}


def outline_label(row: dict) -> str:
    """id: area, with the kind in words for a reader who cannot tell the
    colours apart."""
    kind = outline_kind(row)
    if row["area_um2"] is None:
        return f"{row['id']}: no area"
    word = {"enlarged": " >2x", "cluster": " cluster", "edge": " edge"}.get(kind, "")
    return f"{row['id']}: {row['area_um2']:.0f}{word}"


def render_outlines(display: np.ndarray, labels: np.ndarray, rows: list[dict], excluded: np.ndarray,
                    wt_median: float, title: str, metrics: dict) -> np.ndarray:
    """The POL outline picture of one image as an array."""
    from PIL import Image, ImageDraw, ImageFont  # noqa: PLC0415
    from skimage import segmentation  # noqa: PLC0415

    h, w = labels.shape
    region = lacunae.shade_excluded(display, excluded)
    for r in rows:
        # 2 px: the mask's own edge pixels, and the pixels just outside it that
        # no other lacuna holds.
        mask = labels == r["id"]
        line = (segmentation.find_boundaries(mask, mode="inner")
                | (segmentation.find_boundaries(mask, mode="outer") & (labels == 0)))
        region[line] = OUTLINE_COLOURS[outline_kind(r)]
    canvas = Image.new("RGB", (w + OUTLINES_PANEL_W, h + TITLE_H), (255, 255, 255))
    canvas.paste(Image.fromarray(region), (0, TITLE_H))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=FONT_PX)
    for r in rows:
        ys, xs = np.nonzero(labels == r["id"])
        if xs.size == 0:
            continue
        y = float(np.clip(ys.mean(), 10, h - 10)) + TITLE_H
        colour = OUTLINE_COLOURS[outline_kind(r)]
        if xs.max() + 80 < w:
            x, anchor = int(xs.max()) + 4, "lm"
        else:
            x, anchor = int(xs.min()) - 4, "rm"
        draw.text((x, y), outline_label(r), font=font, anchor=anchor, fill=colour, stroke_width=1,
                  stroke_fill=(0, 0, 0))
    x1, y0 = w - 20, h - 22 + TITLE_H
    draw.rectangle([x1 - SCALE_BAR_PX, y0, x1 - 1, y0 + 3], fill=(255, 255, 255))
    draw.text((x1 - SCALE_BAR_PX // 2, y0 - 3), f"{SCALE_BAR_UM:g} um", font=font, anchor="mb",
              fill=(255, 255, 255), stroke_width=1, stroke_fill=(0, 0, 0))
    draw.text((8, TITLE_H // 2), title, font=ImageFont.load_default(size=15), anchor="lm", fill=(0, 0, 0))

    x, y = w + 12, TITLE_H + 14
    black = (0, 0, 0)
    draw.text((x, y), "POL footprints: each lacuna as outlined,", font=font, fill=black)
    draw.text((x, y + 16), "the working POL definition (to be", font=font, fill=black)
    draw.text((x, y + 32), "confirmed by Dr. Murshed). Pre-validation.", font=font, fill=black)
    y += 64
    legend = [(OUTLINE_NORMAL, "normal size: up to 2 x WT median",
               f"(up to {POL_RATIO_LINE * wt_median:.1f} um2)"),
              (OUTLINE_ENLARGED, "enlarged: above 2 x WT median", "(label says >2x)"),
              (OUTLINE_CLUSTER, "cluster: two or more lacunae merged", "(label says cluster)"),
              (OUTLINE_EDGE, "touches the frame: area cut,", "not measured (label says edge)")]
    for colour, line1, line2 in legend:
        draw.rectangle([x, y, x + 26, y + 12], fill=(40, 0, 0), outline=colour, width=3)
        draw.text((x + 34, y), line1, font=font, fill=black)
        draw.text((x + 34, y + 15), line2, font=font, fill=black)
        y += 40
    shade = tuple(int(v) for v in np.rint(0.4 * np.array([40, 0, 0]) + 0.6 * np.array(lacunae.EXCLUDED_SHADE_RGB)))
    draw.rectangle([x, y, x + 26, y + 12], fill=shade, outline=(255, 255, 255), width=1)
    draw.text((x + 34, y), "grey: excluded region, not analysed", font=font, fill=black)
    draw.text((x + 34, y + 15), "(saturated border or large structure)", font=font, fill=black)
    y += 48
    draw.text((x, y), "labels: id: area in um2", font=font, fill=black)
    y += 16
    draw.text((x, y), f"WT median lacuna: {wt_median:.1f} um2", font=font, fill=black)
    y += 32

    def fmt(value, percent=False):
        if value is None:
            return "none"
        return f"{100 * value:.1f}%" if percent else f"{value:.1f}"

    lines = [f"lacunae: {metrics['n_lacunae']} ({metrics['n']} measured)",
             f"median: {fmt(metrics['area_um2_median'])} um2",
             f"90th percentile: {fmt(metrics['area_um2_p90'])} um2",
             f"above 2 x WT median: {fmt(metrics['share_above_2x_WT_median'], True)}",
             f"above 100 um2: {fmt(metrics['share_above_100_um2'], True)}",
             f"clusters: {metrics['n_clusters']}",
             f"POL area per analysed area: {fmt(metrics['pol_area_per_analysed_area'], True)}",
             f"excluded: {fmt(metrics['excluded_area_um2'])} um2"]
    draw.text((x, y), "this image (measured lacunae):", font=font, fill=black)
    for i, line in enumerate(lines, start=1):
        draw.text((x, y + 16 * i), line, font=font, fill=black)
    out = np.asarray(canvas).copy()
    canvas.close()
    return out


def read_excluded(results_root: Path, label: str, shape: tuple) -> np.ndarray:
    """The saved excluded region of one image (config section g9); nothing
    excluded when detection saved none."""
    from skimage.io import imread  # noqa: PLC0415

    path = lacunae.result_path(results_root, label, config.SECTION_LACUNAE, config.SUFFIX_EXCLUDED_MASK)
    return np.asarray(imread(path)) > 0 if path.is_file() else np.zeros(shape, dtype=bool)


def save_outlines(image_path: Path, labels: np.ndarray, table: Path, excluded: np.ndarray, wt_median: float,
                  metrics: dict, path: Path, set_name: str | None = None) -> None:
    """Draw the POL outline picture of one image from its table as written."""
    from PIL import Image  # noqa: PLC0415

    display, _channel = lacunae.load_channel(image_path)
    label = lacunae.image_label(image_path)
    picture = render_outlines(display, labels, read_table(table), excluded, wt_median,
                              f"{image_path.parent.name} {label}: POL footprints.{set_note(set_name)} "
                              "Pre-validation, not a lesion call.", metrics)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(picture).save(path)
    del display, picture


def save_picture(image_path: Path, labels: np.ndarray, table: Path, wt_median: float, path: Path,
                 set_name: str | None = None) -> None:
    """Draw the picture of one image from its table as written to disk."""
    from PIL import Image  # noqa: PLC0415

    display, _channel = lacunae.load_channel(image_path)
    picture, _boxes = render_picture(display, labels, read_table(table), wt_median,
                                     picture_title(image_path.parent.name, lacunae.image_label(image_path),
                                                   set_name))
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(picture).save(path)
    del display, picture


def check_picture(image_path: Path, results_root: Path, wt_median: float, set_name: str | None = None) -> dict:
    """The automatic check of one picture: it equals the picture drawn again
    from its table; outside the label and scale bar boxes, every changed pixel
    lies inside a lacuna mask; every measured lacuna is filled with its own
    colour on its whole mask, so the filled count equals the measured rows; a
    flagged lacuna is not filled; every printed area is its table value; each
    mask's area is its table area; the image is unchanged elsewhere."""
    from PIL import Image  # noqa: PLC0415
    from skimage.io import imread  # noqa: PLC0415

    label = lacunae.image_label(image_path)
    table = lacunae.result_path(results_root, label, config.SECTION_POLS, SUFFIX_TABLE)
    picture_path = lacunae.result_path(results_root, label, config.SECTION_POLS, SUFFIX_PICTURE)
    rows = read_table(table)
    labels = np.asarray(imread(lacunae.result_path(results_root, label, config.SECTION_LACUNAE,
                                                   config.SUFFIX_LACUNA_LABELS)))
    display, _channel = lacunae.load_channel(image_path)
    with Image.open(picture_path) as im:
        saved = np.asarray(im.convert("RGB")).copy()
    again, boxes = render_picture(display, labels, rows, wt_median,
                                  picture_title(image_path.parent.name, label, set_name))
    h, w = labels.shape
    region = saved[TITLE_H:TITLE_H + h, :w]
    in_box = np.zeros((h, w), dtype=bool)
    for x0, y0, x1, y1 in boxes:
        in_box[max(0, y0):max(0, y1) + 1, max(0, x0):max(0, x1) + 1] = True
    changed = np.any(region != display, axis=2)
    out = {"image": label, "rows": len(rows), "measured_rows": sum(1 for r in rows if not r["flag"]),
           "redrawn_from_table_equal": bool(np.array_equal(saved, again)),
           "changed_outside_masks_px": int((changed & ~in_box & (labels == 0)).sum()),
           "unchanged_outside_drawing": bool(not (changed & ~in_box & (labels == 0)).any())}
    filled, wrong_fill, flagged_filled, area_mismatch = 0, [], [], []
    for r in rows:
        mask = labels == r["id"]
        if r["area_um2"] is not None and abs(mask.sum() * UM2_PER_PX2 - r["area_um2"]) > 0.051:
            area_mismatch.append(r["id"])
        free = mask & ~in_box
        if r["flag"]:
            from scipy import ndimage as ndi  # noqa: PLC0415

            inner = free & ndi.binary_erosion(mask)
            if np.any(region[inner] != display[inner]):
                flagged_filled.append(r["id"])
            continue
        want = np.rint((1 - FILL_ALPHA) * display[free].astype(np.float64)
                       + FILL_ALPHA * fill_colour(r["ratio_to_WT_median"])).astype(np.uint8)
        if free.any() and np.array_equal(region[free], want):
            filled += 1
        else:
            wrong_fill.append(r["id"])
    out.update({"filled": filled, "filled_equals_measured_rows": filled == out["measured_rows"],
                "wrong_fill_ids": wrong_fill, "flagged_filled_ids": flagged_filled,
                "mask_area_differs_ids": area_mismatch})
    out["pass"] = bool(out["redrawn_from_table_equal"] and out["unchanged_outside_drawing"]
                       and out["filled_equals_measured_rows"] and not wrong_fill and not flagged_filled
                       and not area_mismatch)
    del saved, again, display, labels, region
    return out


# Group and summary

README = """# 3_pols: {group}

{label_cap}. Pre-validation: no lesion is called here.

POLs (periosteocytic lesions) are enlarged lacunae, and there is no agreed
definition of one in these images yet. This section shows the one candidate
that needs no new detection: the area of each lacuna the pipeline measured, in
um2 at 0.13 um/px, and its ratio to the WT median lacunar area (every measured
WT lacuna pooled).

- `<image>_pols_lacunar_size.png`: the original image, each measured lacuna
  filled with the colour of its ratio to the WT median (one scale for every
  group, the colour bar in um2), its id and area beside it; flagged lacunae
  (touching the frame, or of a class with no area) outlined grey, not filled;
  10 um scale bar.
- `<image>_pols_lacunar_size.csv`: id, area_um2, ratio_to_WT_median, flag.
- `pols_all_images.csv` and `.xlsx`: per image, n measured, and the mean,
  median and 90th percentile of area and of ratio.
- `contact_sheet.png`: every picture of the group, small.

Across groups: `results/summary/pols_lacunar_size_by_group.csv`.
Made by `python src/pols.py all` (every group) or
`python src/pols.py measure -d data/{group}` (this group only).

The ring proxy this folder held before is retired, because it measured the dye
glow around every lacuna, the same width in WT, and not lesions. Its files were
in `../5_archive/pol_ring_proxy/`, deleted on 2026-11-09; they are in git
history (tag `method-freeze-v2`).
"""


JUDGE_README = """# 3_pols/ai_judge: {group}

{label_cap}, **with the AI lacuna judge on**. Pre-validation: no lesion is
called here, and no verdict of the judge is validated.

The same section as `3_pols/` beside this folder, made by the same code from
the lacunae the AI lacuna judge accepted (`1_lacunae/ai_judge/`,
`4_quantification/ai_judge/`): the judge was shown every candidate region of
the lacuna stage and said which are lacunae, keeping enlarged lacunae and
clusters under the working POL definition (docs/METHODS.md 24.0 and 29). It
never draws a boundary, so every footprint is the lacuna stage's own outline.
A region the judge added that the filters had rejected is the class `judged`
and has no area (flag `no_area`), like the `dim` class.

- `<image>_pols_outlines.png`: the POL footprints, as in `3_pols/`.
- `<image>_pols_lacunar_size.png` and `.csv`: lacunar size per lacuna.
- `pols_all_images.csv` and `.xlsx`: per image, the size statistics and the
  POL metrics.
- `contact_sheet.png`, `contact_sheet_outlines.png`: every picture, small.

The ratios here are against the WT median of the judge-on set
({wt_median:.2f} um2), so each method is measured against its own reference
group. Made with the method at tag `method-freeze-v2` and the judge rerun of
2026-11-09 by `python src/pols.py all --set ai_judge`. The judge off against
judge on comparison is in `results/archive/judge/` and in the sheet "Judge on
vs off" of `results/SUMMARY.xlsx`.
"""


def write_readme(results_root: Path, group: str, set_name: str | None = None,
                 wt_median: float | None = None) -> Path:
    path = lacunae.group_path(results_root, config.SECTION_POLS, "README.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    text = README if set_name is None else JUDGE_README
    path.write_text(text.format(group=group, label_cap=LABEL[0].upper() + LABEL[1:], wt_median=wt_median or 0.0),
                    encoding="utf-8")
    return path


def measure_group(group: str, results_root: Path | None = None, wt_median: float | None = None,
                  set_name: str | None = None) -> list[dict]:
    """Every image of one group: picture and table per image, the group table
    and the contact sheet. Returns the image rows. With `set_name`, of that
    result set of the group (JUDGE_SET: the AI lacuna judge on). A held-out
    image is written in FINAL mode but its numbers are not printed."""
    from skimage.io import imread  # noqa: PLC0415

    results_root = Path(results_root or set_root(group, set_name))
    wt_median = wt_median_um2(set_name) if wt_median is None else wt_median
    held_out = lacunae.held_out_labels()
    image_rows, tiles, outline_tiles = [], [], []
    for image_path in image_files(group):
        label = lacunae.image_label(image_path)
        records = lacuna_records(results_root, label)
        rows = with_raw(records, wt_median)
        labels = np.asarray(imread(lacunae.result_path(results_root, label, config.SECTION_LACUNAE,
                                                       config.SUFFIX_LACUNA_LABELS)))
        if int(labels.max()) != len(records):
            raise ValueError(f"{group}/{label}: {int(labels.max())} labels, {len(records)} lacunae in the json")
        table = lacunae.result_path(results_root, label, config.SECTION_POLS, SUFFIX_TABLE)
        write_csv(table, LACUNA_COLUMNS, rows)
        picture = lacunae.result_path(results_root, label, config.SECTION_POLS, SUFFIX_PICTURE)
        save_picture(image_path, labels, table, wt_median, picture, set_name)
        analysed, excluded_um2 = field_areas_um2(results_root, label)
        image_rows.append({"status": LABEL, "group": group, "image": label, **stats(rows),
                           "WT_median_area_um2": _round(wt_median), **pol_metrics(rows, analysed, excluded_um2)})
        outlines = lacunae.result_path(results_root, label, config.SECTION_POLS, SUFFIX_OUTLINES)
        save_outlines(image_path, labels, table, read_excluded(results_root, label, labels.shape), wt_median,
                      image_rows[-1], outlines, set_name)
        del labels
        gc.collect()
        tiles.append((label, picture))
        outline_tiles.append((label, outlines))
        if label in held_out:
            print(f"{group}/{label}: written (held out, numbers not shown)")
        else:
            print(f"{group}/{label}: {image_rows[-1]['n']} measured, {image_rows[-1]['n_flagged']} flagged, "
                  f"median {image_rows[-1]['area_um2_median']} um2, POL area per analysed area "
                  f"{image_rows[-1]['pol_area_per_analysed_area']}")
    group_table = lacunae.group_path(results_root, config.SECTION_POLS, GROUP_TABLE)
    write_csv(group_table.with_suffix(".csv"), IMAGE_COLUMNS, image_rows)
    note = [] if set_name is None else [f"AI LACUNA JUDGE ON (result set {set_name}): the lacunae the judge "
                                        "accepted; ratios against the WT median of this set."]
    write_xlsx(group_table.with_suffix(".xlsx"), IMAGE_COLUMNS, image_rows, note + notes(wt_median))
    where = "3_pols" if set_name is None else f"3_pols/{set_name}"
    lacunae.save_contact_sheet(tiles, f"{group}: {LABEL}.{set_note(set_name)} Full size: {where}/<image>_"
                                      f"{SUFFIX_PICTURE}.",
                               lacunae.group_path(results_root, config.SECTION_POLS, CONTACT_SHEET))
    lacunae.save_contact_sheet(outline_tiles, f"{group}: POL footprints.{set_note(set_name)} Full size: "
                                              f"{where}/<image>_{SUFFIX_OUTLINES}.",
                               lacunae.group_path(results_root, config.SECTION_POLS, OUTLINES_CONTACT_SHEET))
    write_readme(results_root, group, set_name, wt_median)
    return image_rows


def group_summary(groups=config.GROUPS, wt_median: float | None = None) -> list[dict]:
    """results/summary/pols_lacunar_size_by_group.csv: per group, every
    measured lacuna pooled."""
    wt_median = wt_median_um2() if wt_median is None else wt_median
    out = []
    for group in groups:
        rows, analysed, excluded = [], 0.0, 0.0
        files = image_files(group)
        for p in files:
            label = lacunae.image_label(p)
            rows += with_raw(lacuna_records(config.RESULTS_ROOT / group, label), wt_median)
            a, e = field_areas_um2(config.RESULTS_ROOT / group, label)
            analysed, excluded = analysed + a, excluded + e
        out.append({"status": LABEL, "group": group, "n_images": len(files), **stats(rows),
                    "WT_median_area_um2": _round(wt_median), **pol_metrics(rows, analysed, excluded)})
    write_csv(SUMMARY_TABLE, GROUP_COLUMNS, out)
    return out


def animal_summary(groups=config.GROUPS, wt_median: float | None = None) -> list[dict]:
    """results/summary/pols_by_animal.csv: per animal of data/animals.csv,
    every measured lacuna of its images pooled, the analysed areas summed. In
    DEV mode the held-out images are left out, so an animal may have fewer
    images than it has."""
    wt_median = wt_median_um2() if wt_median is None else wt_median
    animals = animal_map()
    pooled = {}
    for group in groups:
        for p in image_files(group):
            label = lacunae.image_label(p)
            a = animals[(group, label)]
            entry = pooled.setdefault(a["animal"], {"meta": a, "group": group, "rows": [], "analysed": 0.0,
                                                    "excluded": 0.0, "n_images": 0})
            entry["rows"] += with_raw(lacuna_records(config.RESULTS_ROOT / group, label), wt_median)
            area, excl = field_areas_um2(config.RESULTS_ROOT / group, label)
            entry["analysed"] += area
            entry["excluded"] += excl
            entry["n_images"] += 1
    out = []
    for animal, e in pooled.items():
        out.append({"status": LABEL, "animal": animal, "genotype": e["meta"]["genotype"],
                    "diet": e["meta"]["diet"], "group": e["group"], "confirmed": e["meta"]["confirmed"],
                    "n_images": e["n_images"], **stats(e["rows"]), "WT_median_area_um2": _round(wt_median),
                    **pol_metrics(e["rows"], e["analysed"], e["excluded"])})
    write_csv(ANIMAL_TABLE, ANIMAL_COLUMNS, out)
    return out


def check(groups=config.GROUPS, set_name: str | None = None) -> int:
    """Every file of every group: present, and each per-lacuna table equal to
    the json areas times 0.0169 and to the WT median ratio. With `set_name`,
    of that result set (which has no summary tables across groups)."""
    wt_median = wt_median_um2(set_name)
    failed = 0
    for group in groups:
        root = set_root(group, set_name)
        for p in image_files(group):
            label = lacunae.image_label(p)
            want = lacuna_rows(lacuna_records(root, label), wt_median)
            pic = lacunae.result_path(root, label, config.SECTION_POLS, SUFFIX_PICTURE)
            tab = lacunae.result_path(root, label, config.SECTION_POLS, SUFFIX_TABLE)
            outl = lacunae.result_path(root, label, config.SECTION_POLS, SUFFIX_OUTLINES)
            problem = ""
            if not pic.is_file() or not tab.is_file() or not outl.is_file():
                problem = "missing file"
            else:
                with open(tab, newline="", encoding="utf-8") as f:
                    got = list(csv.DictReader(f))
                norm = [{k: ("" if r[k] is None else str(r[k])) for k in LACUNA_COLUMNS} for r in want]
                if got != norm:
                    problem = "table differs from the json"
            failed += bool(problem)
            print(f"{group:<7} {label:<26} {problem or 'PASS'}")
        for name in (f"{GROUP_TABLE}.csv", f"{GROUP_TABLE}.xlsx", CONTACT_SHEET, OUTLINES_CONTACT_SHEET):
            if not lacunae.group_path(root, config.SECTION_POLS, name).is_file():
                print(f"{group:<7} {name:<26} missing file")
                failed += 1
    for table in (SUMMARY_TABLE, ANIMAL_TABLE) if set_name is None else ():
        if not table.is_file():
            print(f"{table} missing")
            failed += 1
    print(f"\n{'FAIL' if failed else 'PASS'}: lacunar size check{f' ({set_name})' if set_name else ''}, "
          f"{failed} problem(s).")
    return 1 if failed else 0


PICTURE_CHECK_TABLE = config.ARCHIVE_ROOT / "POL_PICTURE_CHECK.csv"
PICTURE_CHECK_COLUMNS = ["group", "image", "rows", "measured_rows", "filled", "filled_equals_measured_rows",
                         "redrawn_from_table_equal", "unchanged_outside_drawing", "changed_outside_masks_px",
                         "wrong_fill_ids", "flagged_filled_ids", "mask_area_differs_ids", "pass"]


def check_pictures(groups=config.GROUPS, set_name: str | None = None) -> int:
    """check_picture on every image of every group, one image at a time; with
    `set_name`, of that result set, into JUDGE_PICTURE_CHECK_TABLE."""
    wt_median = wt_median_um2(set_name)
    rows = []
    for group in groups:
        for image_path in image_files(group):
            r = check_picture(image_path, set_root(group, set_name), wt_median, set_name)
            r["group"] = group
            for k in ("wrong_fill_ids", "flagged_filled_ids", "mask_area_differs_ids"):
                r[k] = " ".join(str(i) for i in r[k])
            rows.append(r)
            print(f"{group:<7} {r['image']:<26} filled {r['filled']:>3} of {r['measured_rows']:>3} measured  "
                  f"{'PASS' if r['pass'] else 'FAIL'}", flush=True)
            gc.collect()
    table = PICTURE_CHECK_TABLE if set_name is None else JUDGE_PICTURE_CHECK_TABLE
    write_csv(table, PICTURE_CHECK_COLUMNS, rows)
    failed = sum(not r["pass"] for r in rows)
    print(f"\n{'FAIL' if failed else 'PASS'}: {len(rows) - failed} of {len(rows)} pictures. -> {table}")
    return 1 if failed else 0


# Self-test

def selftest() -> int:
    """Synthetic records with known areas: the conversion, the flags, the
    ratio, the statistics and a picture that saves."""
    import tempfile  # noqa: PLC0415

    checks = []
    records = [{"id": 1, "area_px2": 1000.0, "flag": ""}, {"id": 2, "area_px2": 2000.0, "flag": ""},
               {"id": 3, "area_px2": 500.0, "flag": "edge"}, {"id": 4, "area_px2": None, "flag": "no_area"}]
    median = 1000.0 * UM2_PER_PX2
    rows = with_raw(records, median)
    checks.append(("area 1000 px2 is 16.9 um2", rows[0]["area_um2"] == 16.9))
    checks.append(("ratio of the WT median size is 1", rows[0]["ratio_to_WT_median"] == 1.0))
    checks.append(("ratio of twice the size is 2", rows[1]["ratio_to_WT_median"] == 2.0))
    checks.append(("an edge lacuna keeps its area and has no ratio",
                   rows[2]["area_um2"] == 8.45 and rows[2]["ratio_to_WT_median"] is None))
    checks.append(("a lacuna with no area has neither", rows[3]["area_um2"] is None))
    s = stats(rows)
    checks.append(("n counts the measured lacunae only", s["n"] == 2 and s["n_flagged"] == 2))
    checks.append(("mean and median of 16.9 and 33.8", s["area_um2_mean"] == 25.35 and s["area_um2_median"] == 25.35))
    checks.append(("90th percentile of the ratio", s["ratio_p90"] == 1.9))
    checks.append(("the method's own titles are unchanged by the result set option",
                   picture_title("WT", "x") == f"WT x: {LABEL}. Pre-validation, not a lesion call."
                   and picture_title("WT", "x", JUDGE_SET) != picture_title("WT", "x")))
    judged_path = lacunae.result_path(set_root("WT", JUDGE_SET), "x", config.SECTION_POLS, SUFFIX_TABLE)
    checks.append(("the judge-on set lives in results/<group>/3_pols/ai_judge/",
                   judged_path == config.RESULTS_ROOT / "WT" / config.SECTION_POLS / JUDGE_SET / f"x_{SUFFIX_TABLE}"
                   and set_root("WT") == config.RESULTS_ROOT / "WT"))
    image = next(iter(image_files(config.REFERENCE_GROUP)), None)
    if image is not None:
        labels = np.zeros(lacunae.load_channel(image)[1].shape, dtype=np.int32)
        labels[100:140, 100:125] = 1
        labels[200:250, 300:340] = 2
        labels[0:20, 0:25] = 3
        labels[400:410, 400:410] = 4
        with tempfile.TemporaryDirectory() as tmp:
            table = Path(tmp) / "table.csv"
            write_csv(table, LACUNA_COLUMNS, rows)
            display = lacunae.load_channel(image)[0]
            picture, boxes = render_picture(display, labels, read_table(table), median, "self-test")
            region = picture[TITLE_H:TITLE_H + labels.shape[0], :labels.shape[1]]
            in_box = np.zeros(labels.shape, dtype=bool)
            for x0, y0, x1, y1 in boxes:
                in_box[max(0, y0):max(0, y1) + 1, max(0, x0):max(0, x1) + 1] = True
            changed = np.any(region != display, axis=2)
            checks.append(("outside the masks only labels and the scale bar change",
                           not (changed & ~in_box & (labels == 0)).any()))
            want = np.rint(0.3 * display[labels == 2].astype(float) + 0.7 * fill_colour(2.0)).astype(np.uint8)
            checks.append(("a measured lacuna is filled with its colour on its whole mask",
                           np.array_equal(region[labels == 2], want)))
            checks.append(("a flagged lacuna is not filled inside its edge",
                           np.array_equal(region[401:409, 401:409], display[401:409, 401:409])))
            checks.append(("its edge is grey", bool(np.all(region[400, 400:410] == GREY))))

            # The POL metrics and the outline picture (phase 4).
            pol_records = [{"id": 1, "area_px2": 1000.0, "flag": "", "cluster": False},
                           {"id": 2, "area_px2": 3000.0, "flag": "", "cluster": False},
                           {"id": 3, "area_px2": 7000.0, "flag": "", "cluster": True},
                           {"id": 4, "area_px2": 500.0, "flag": "edge", "cluster": False}]
            pol_rows = with_raw(pol_records, median)
            m = pol_metrics(pol_rows, 1000.0, 50.0)
            checks.append(("POL metrics: n, shares above 2x and 100 um2, clusters",
                           m["n_lacunae"] == 4 and m["share_above_2x_WT_median"] == round(2 / 3, DIGITS)
                           and m["share_above_100_um2"] == round(1 / 3, DIGITS) and m["n_clusters"] == 1))
            checks.append(("POL area per analysed area sums every lacuna with an area, edge included",
                           m["lacunar_area_um2"] == round(11500 * UM2_PER_PX2, DIGITS)
                           and m["pol_area_per_analysed_area"] == round(11500 * UM2_PER_PX2 / 1000.0, DIGITS)))
            pol_labels = np.zeros(labels.shape, dtype=np.int32)
            pol_labels[100:140, 100:125] = 1
            pol_labels[200:260, 300:350] = 2
            pol_labels[500:600, 500:570] = 3
            pol_labels[0:20, 0:25] = 4
            excluded = np.zeros(labels.shape, dtype=bool)
            excluded[800:900, 800:900] = True
            pol_table = Path(tmp) / "pol_table.csv"
            write_csv(pol_table, LACUNA_COLUMNS, pol_rows)
            pic = render_outlines(display, pol_labels, read_table(pol_table), excluded, median, "self-test",
                                  {**stats(pol_rows), **m})
            reg = pic[TITLE_H:TITLE_H + labels.shape[0], :labels.shape[1]]
            checks.append(("outline colours: normal green, enlarged yellow, cluster cyan, edge grey",
                           tuple(reg[100, 110]) == OUTLINE_NORMAL and tuple(reg[200, 320]) == OUTLINE_ENLARGED
                           and tuple(reg[500, 530]) == OUTLINE_CLUSTER and tuple(reg[19, 10]) == OUTLINE_EDGE))
            checks.append(("inside a footprint the image is unchanged",
                           np.array_equal(reg[110:130, 105:120], display[110:130, 105:120])))
            checks.append(("the excluded region is shaded, the image elsewhere is not",
                           not np.array_equal(reg[850, 850], display[850, 850])
                           and np.array_equal(reg[700:790, 700:790], display[700:790, 700:790])))
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    ok = all(ok for _n, ok in checks)
    print(f"\n{'PASS' if ok else 'FAIL'}: {sum(ok for _n, ok in checks)} of {len(checks)} checks.")
    return 0 if ok else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=f"The POL section: {LABEL}.")
    sub = parser.add_subparsers(dest="command", required=True)
    set_help = (f"A result set instead of the method itself: {JUDGE_SET} is the AI lacuna judge on, "
                f"results/<group>/3_pols/{JUDGE_SET}/ (no summary tables across groups).")
    p = sub.add_parser("measure", help="One group: results/<group>/3_pols/.")
    p.add_argument("-d", "--dir", type=Path, required=True, help="A group folder of .tif images, e.g. data/WT_HP.")
    p.add_argument("-r", "--results", type=Path, default=None,
                   help="The group's results folder (default: results/<name of the input folder>).")
    p.add_argument("--set", dest="set_name", choices=SETS, default=None, help=set_help)
    p = sub.add_parser("all", help="Every group, then results/summary/pols_lacunar_size_by_group.csv and "
                                   "pols_by_animal.csv.")
    p.add_argument("--set", dest="set_name", choices=SETS, default=None, help=set_help)
    sub.add_parser("summary", help="Only results/summary/pols_lacunar_size_by_group.csv and pols_by_animal.csv.")
    p = sub.add_parser("check", help="Every 3_pols file against the quantification jsons.")
    p.add_argument("--set", dest="set_name", choices=SETS, default=None, help=set_help)
    sub.add_parser("selftest", help="Checks on synthetic records.")
    p = sub.add_parser("check-pictures", help="Every 3_pols picture, one image at a time: drawn from its table, "
                                              "colour only inside the masks (results/archive/POL_PICTURE_CHECK.csv).")
    p.add_argument("--set", dest="set_name", choices=SETS, default=None, help=set_help)
    args = parser.parse_args()
    set_name = getattr(args, "set_name", None)
    if args.command == "selftest":
        sys.exit(selftest())
    if args.command == "check-pictures":
        sys.exit(check_pictures(set_name=set_name))
    if args.command == "check":
        sys.exit(check(set_name=set_name))
    if args.command == "measure":
        group = Path(args.dir).resolve().name
        measure_group(group, args.results, set_name=set_name)
    elif args.command == "all":
        wt_median = wt_median_um2(set_name)
        for group in config.GROUPS:
            measure_group(group, wt_median=wt_median, set_name=set_name)
    if set_name is not None:
        print(f"result set {set_name}: no summary tables across groups are written.")
        return
    rows = group_summary()
    print(f"-> {SUMMARY_TABLE}")
    for r in rows:
        print(f"  {r['group']:<7} n={r['n']:<4} median {r['area_um2_median']} um2, ratio median {r['ratio_median']}")
    animal_summary()
    print(f"-> {ANIMAL_TABLE}")


if __name__ == "__main__":
    main()
