"""The key results view: the important pictures of each image in one folder
per group, a summary of each run and a comparison per image, and one summary
workbook.

PRE-VALIDATION. Nothing is measured here; every file is a copy, a table or a
picture of what the pipeline already saved, and the originals are not changed.

Per group, results/<group>/0_key_results/ holds, for every image, copies of
    <image>_1_lacunae_outlines.png         <image>/non_ai_run/1_lacunae/<image>_lacunae_outlines.png
    <image>_2_canaliculi_verification.png  <image>/non_ai_run/2_canaliculi/<image>_canaliculi_verification.png
    <image>_3_pols_outlines.png            <image>/non_ai_run/3_pols/<image>_pols_outlines.png
named so they sort by image, and a README.md.
Per image (samples), in each run's summary/: the lacunae outlines and the
canaliculi verification picture (copies), <image>_key_numbers.png and .csv,
and <image>_pols_explained.png (the POL outlines with a panel of plain text);
in <image>/comparison/: the lacunae, canaliculi and POL pictures of both runs
beside a picture of what the AI changed, and <image>_compare_numbers.png and
.csv.
results/SUMMARY.xlsx: sheets Read me, Per group, Per animal, Per image and
Statistics, from src/animal_stats.py, and Judge on vs off, from
results/archive/judge/judge_on_vs_off.csv (python src/diagnostics.py
judge-compare).

In DEV mode the held-out images are left out (docs/HOLDOUT.md).

Usage (from the repo root):
    python src/key_results.py all        # every group's folder and results/SUMMARY.xlsx
    python src/key_results.py samples    # every image's summary/ and comparison/ (FINAL mode for all)
    python src/key_results.py check      # every copy equal to its original
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import animal_stats  # noqa: E402
import lacunae  # noqa: E402
import pols  # noqa: E402

SUMMARY_XLSX = config.RESULTS_ROOT / "SUMMARY.xlsx"
# (number in the copy's name, section, suffix of the original, suffix of the copy)
KEY_PICTURES = [
    (1, config.SECTION_LACUNAE, config.SUFFIX_LACUNAE_OUTLINES, "1_lacunae_outlines.png"),
    (2, config.SECTION_CANALICULI, config.SUFFIX_CANALICULI_VERIFICATION, "2_canaliculi_verification.png"),
    (3, config.SECTION_POLS, pols.SUFFIX_OUTLINES, "3_pols_outlines.png"),
]

README = """# 0_key_results: {group}

Pre-validation. The three most important pictures of every image of this
group in the non-AI run, copied from each image's folder (the originals, in
`<image>/non_ai_run/`, are not changed), named so they sort by image. Each
image's folder also holds the same pictures with the AI judges on
(`<image>/ai_judges/`), a summary of each run (`summary/`) and the two runs
side by side (`<image>/comparison/`).

- `<image>_1_lacunae_outlines.png`: the lacunae the pipeline found, each
  outlined in green on the original image (from `1_lacunae/`).
- `<image>_2_canaliculi_verification.png`: the traced canalicular network on
  the original image, each lacuna's threads in its own colour (from
  `2_canaliculi/`).
- `<image>_3_pols_outlines.png`: the POL footprints (the working POL
  definition, to be confirmed by Dr. Murshed): green normal size, yellow above
  2 x the WT median lacunar area, cyan a cluster of merged lacunae, grey
  touching the frame (not measured); excluded regions shaded grey; id and
  area in um2 beside each; a 10 um scale bar (from `3_pols/`).

The numbers are in `results/SUMMARY.xlsx`; how to read it all is in
`results/HOW_TO_READ.md`. Made by `python src/key_results.py all`.
"""


def key_pairs(group: str) -> list[tuple[Path, Path]]:
    """(original, copy) for every key picture of every image of one group
    that the mode lets through."""
    root = config.RESULTS_ROOT / group
    out = []
    for path in pols.image_files(group):
        label = lacunae.image_label(path)
        for _n, section, suffix, key_suffix in KEY_PICTURES:
            out.append((lacunae.result_path(root, label, section, suffix),
                        root / config.SECTION_KEY_RESULTS / f"{label}_{key_suffix}"))
    return out


def copy_group(group: str) -> int:
    folder = config.RESULTS_ROOT / group / config.SECTION_KEY_RESULTS
    folder.mkdir(parents=True, exist_ok=True)
    missing = 0
    for original, copy in key_pairs(group):
        if not original.is_file():
            print(f"{group}: missing {original.relative_to(config.PROJECT_ROOT)}")
            missing += 1
            continue
        shutil.copy2(original, copy)
    (folder / "README.md").write_text(README.format(group=group), encoding="utf-8")
    print(f"{group}: {len(key_pairs(group)) - missing} pictures -> {folder.relative_to(config.PROJECT_ROOT)}")
    return missing


# The workbook

READ_ME = [
    ("status", "PRE-VALIDATION. Every number comes from the pipeline's own detection, checked by an AI "
               "reviewer on the development images, not yet against manual counts. The animal mapping "
               "(data/animals.csv) is from the file names and is not confirmed; animal 701 carries no diet "
               "label in its file names. The POL definition is a working definition, to be confirmed by "
               "Dr. Murshed."),
    ("mode", None),
    ("sheets", "Per group, Per animal, Per image: one row each; Statistics: the genotype by diet models; "
               "Judge on vs off: the AI judge layer against the method, development images only."),
    ("", ""),
    ("COLUMN", "WHAT IT MEANS"),
    ("group", "WT (wild type, regular diet), WT_HP (wild type, high phosphate diet), Hyp_RD (Hyp, regular "
              "diet), Hyp_HP (Hyp, high phosphate diet)."),
    ("animal", "The animal, from the start of the image file name (for example 548, I534)."),
    ("genotype", "WT or Hyp."),
    ("diet", "RD (regular) or HP (high phosphate)."),
    ("confirmed", "Whether the animal, genotype and diet of this row are confirmed (no: not yet)."),
    ("image", "The image's short name, as in every results file name."),
    ("images", "The images pooled in this row."),
    ("n_images", "How many images are pooled in this row."),
    ("n_lacunae", "Every lacuna the pipeline found, those touching the frame included."),
    ("n", "Measured lacunae: inside the frame and with an area. Every size number below is over these."),
    ("n_flagged", "Lacunae not measured: they touch the frame (area cut) or have no area."),
    ("area_um2_mean", "Mean lacunar area, um2 (0.13 um per pixel)."),
    ("area_um2_median", "Median lacunar area, um2."),
    ("area_um2_p90", "90th percentile of lacunar area, um2: 1 lacuna in 10 is larger."),
    ("ratio_mean, ratio_median, ratio_p90", "The same three of the area divided by the WT median lacunar area."),
    ("WT_median_area_um2", "The WT median lacunar area every ratio is against: every measured WT lacuna pooled."),
    ("share_above_2x_WT_median", "Share of the measured lacunae larger than 2 times the WT median: enlarged "
                                 "lacunae, the candidate POLs."),
    ("share_above_100_um2", "Share of the measured lacunae larger than 100 um2."),
    ("n_clusters", "Measured lacunae flagged as a cluster: two or more lacunae merged into one space."),
    ("lacunar_area_um2", "The summed area of every lacuna with an area, frame ones included, um2."),
    ("analysed_area_um2", "The field analysed: the image minus its excluded region, um2."),
    ("excluded_area_um2", "The excluded region: saturated bands at a tissue border and very large bright "
                          "structures (vascular canals, resorption features, tissue), with a 3 um margin, um2."),
    ("pol_area_per_analysed_area", "POL area per analysed area: lacunar_area_um2 divided by analysed_area_um2, "
                                   "the share of the field taken by lacunar space."),
    ("roots_per_lacuna", "Canaliculi leaving each lacuna, mean over the measured lacunae."),
    ("ring_length_30_um", "Canalicular length within 30 px (3.9 um) of each lacuna, mean, um."),
    ("field_length_density_um_per_um2", "Canalicular length per analysed area (lacunae left out), um per um2."),
    ("width_median_um", "Median apparent canalicular width, um (an upper bound: it includes optical blur)."),
    ("skeleton_length_um, network_area_um2", "Per image: the canalicular length and the area its density is over."),
    ("", ""),
    ("STATISTICS SHEET", ""),
    ("measure", "What is compared."),
    ("model", "animal level, least squares: one value per animal, the primary analysis; mixed: every lacuna or "
              "image, the animal as a random effect (intervals too narrow with so few animals)."),
    ("estimate", "The interaction: (Hyp HP minus Hyp RD) minus (WT HP minus WT RD), in the measure's unit."),
    ("ci_low, ci_high", "Its 95% interval."),
    ("p", "The p value of the interaction (no test is meaningful with 3 animals per group; read the interval)."),
    ("detectable_80", "Animal level: the smallest interaction this design would find 4 times in 5."),
    ("hyp_on_RD, hp_in_WT, wt_rd_mean", "The Hyp effect on the regular diet, the diet effect in WT, the WT RD mean."),
    ("what_it_says", "The result in plain words."),
]


# The judge comparison (2026-11-09): judge off against judge on, development
# images only, written by python src/diagnostics.py judge-compare. Its table
# is kept beside the judge's report and copied into SUMMARY.xlsx as one sheet,
# so a later write_summary_xlsx keeps it.
JUDGE_SHEET = "Judge on vs off"
JUDGE_TABLE = config.ARCHIVE_ROOT / "judge" / "judge_on_vs_off.csv"


def write_judge_sheet(xw, table: Path = JUDGE_TABLE) -> bool:
    """The sheet "Judge on vs off" from its table, into an open ExcelWriter;
    False when the table does not exist yet."""
    import pandas as pd  # noqa: PLC0415

    if not Path(table).is_file():
        return False
    pd.read_csv(table, keep_default_na=False).to_excel(xw, sheet_name=JUDGE_SHEET, index=False)
    return True


def add_judge_sheet(path: Path = SUMMARY_XLSX, table: Path = JUDGE_TABLE) -> Path:
    """Replace only the sheet "Judge on vs off" of an existing SUMMARY.xlsx,
    leaving every other sheet as it is (so a DEV mode comparison never
    rewrites the FINAL mode sheets)."""
    import pandas as pd  # noqa: PLC0415
    from openpyxl.utils import get_column_letter  # noqa: PLC0415

    with pd.ExcelWriter(path, engine="openpyxl", mode="a", if_sheet_exists="replace") as xw:
        if not write_judge_sheet(xw, table):
            raise FileNotFoundError(f"{table} is missing: run python src/diagnostics.py judge-compare first")
        sheet = xw.sheets[JUDGE_SHEET]
        for i, _col in enumerate(sheet.iter_cols(min_row=1, max_row=1), start=1):
            sheet.column_dimensions[get_column_letter(i)].width = 34 if i <= 2 else 18
        sheet.freeze_panes = "C2"
        # The Read me sheet's line that names the sheets, so it names this one too.
        read_me = xw.book["Read me"] if "Read me" in xw.book.sheetnames else None
        if read_me is not None:
            for row in read_me.iter_rows(min_row=2):
                if row[0].value == "sheets":
                    row[1].value = dict(READ_ME)["sheets"]
    print(f"-> {path.relative_to(config.PROJECT_ROOT)}, sheet {JUDGE_SHEET!r}")
    return path


def write_summary_xlsx(path: Path = SUMMARY_XLSX) -> Path:
    import pandas as pd  # noqa: PLC0415
    from openpyxl.utils import get_column_letter  # noqa: PLC0415

    t = animal_stats.tables()
    fits = animal_stats.models(t)
    read_me = [(k, v if k != "mode" else
                f"{config.HOLDOUT_MODE}: " + ("the held-out images are left out." if config.HOLDOUT_MODE == "DEV"
                                              else "every image, the held-out ones included."))
               for k, v in READ_ME]
    models = animal_stats.models_frame(fits)
    keep = ["measure", "unit", "model", "n_units", "estimate", "ci_low", "ci_high", "p", "detectable_80",
            "hyp_on_RD", "hp_in_WT", "wt_rd_mean", "n_per_cell", "n_animals", "converged", "what_it_says"]
    models = models[[c for c in keep if c in models.columns]]
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        pd.DataFrame(read_me, columns=["item", "plain words"]).to_excel(xw, sheet_name="Read me", index=False)
        t["groups"].to_excel(xw, sheet_name="Per group", index=False)
        t["animals"].to_excel(xw, sheet_name="Per animal", index=False)
        t["images"].to_excel(xw, sheet_name="Per image", index=False)
        models.to_excel(xw, sheet_name="Statistics", index=False)
        write_judge_sheet(xw)
        for name, sheet in xw.sheets.items():
            for i, col in enumerate(sheet.iter_cols(min_row=1, max_row=1), start=1):
                width = 90 if (name == "Read me" and i == 2) else 34 if i == 1 and name == "Read me" else 18
                if name == JUDGE_SHEET:
                    width = 34 if i <= 2 else 18
                sheet.column_dimensions[get_column_letter(i)].width = width
            sheet.freeze_panes = "C2" if name == JUDGE_SHEET else "A2"
    print(f"-> {path.relative_to(config.PROJECT_ROOT)}")
    return path


def check() -> int:
    """Every key picture present and byte equal to its original."""
    failed = 0
    for group in config.GROUPS:
        for original, copy in key_pairs(group):
            ok = copy.is_file() and original.is_file() and filecmp.cmp(original, copy, shallow=False)
            failed += not ok
            if not ok:
                print(f"FAIL {copy.relative_to(config.PROJECT_ROOT)}")
    if not SUMMARY_XLSX.is_file():
        print(f"FAIL {SUMMARY_XLSX} missing")
        failed += 1
    total = sum(len(key_pairs(g)) for g in config.GROUPS)
    print(f"{'PASS' if not failed else 'FAIL'}: {total - failed} of {total} key pictures equal to their originals"
          + ("" if SUMMARY_XLSX.is_file() else "; SUMMARY.xlsx missing") + ".")
    return 1 if failed else 0


# The sample folders (the user's layout of 2026-11-10). In each image's two
# runs, summary/ holds the key pictures and numbers of that run; beside the
# runs, comparison/ sets them side by side with what the AI changed. Drawn from
# the saved results only: nothing is measured again, and the numbers are those
# of the Per image sheet (animal_stats.collect, each run against the WT median
# of its own run). A held-out image is drawn like any other in FINAL mode and
# nothing about it is printed (docs/HOLDOUT.md). Display only.

# (set name, run folder, plain name)
RUNS = ((None, config.NON_AI_RUN, "non-AI run"),
        (pols.JUDGE_SET, config.AI_LACUNA_SUBFOLDER, "AI judges run (AI lacuna and POL judges on)"))
# (column of the Per image sheet, plain name, kind): the key numbers card and
# the comparison table.
KEY_NUMBERS = [
    ("n_lacunae", "lacunae found", "count"),
    ("n", "lacunae measured (area known, not cut by the frame)", "count"),
    ("area_um2_median", "median lacunar area", "um2"),
    ("area_um2_p90", "90th percentile of lacunar area (the large end)", "um2"),
    ("share_above_2x_WT_median", "share of lacunae enlarged (above 2 x the WT median)", "share"),
    ("pol_area_per_analysed_area", "POL area per analysed area", "share"),
    ("n_clusters", "clusters of merged lacunae", "count"),
    ("roots_per_lacuna", "canalicular roots per lacuna", "number"),
    ("ring_length_30_um", "canalicular length within 3.9 um of a lacuna", "um"),
    ("field_length_density_um_per_um2", "canalicular length per analysed area", "um per um2"),
]
SUFFIX_KEY_NUMBERS = "key_numbers"  # .png and .csv
SUFFIX_POLS_EXPLAINED = "pols_explained.png"
# (feature, suffix of the picture each run is shown by, suffix of the comparison)
COMPARISONS = [
    ("lacunae", config.SECTION_LACUNAE, config.SUFFIX_LACUNAE_OUTLINES, "compare_lacunae.png"),
    ("canaliculi", config.SECTION_CANALICULI, config.SUFFIX_CANALICULI_VERIFICATION, "compare_canaliculi.png"),
    ("POLs", config.SECTION_POLS, pols.SUFFIX_OUTLINES, "compare_pols.png"),
]
SUFFIX_COMPARE_NUMBERS = "compare_numbers"  # .png and .csv
# Display choices, not biology: each panel of a comparison is shown this wide;
# a pair of outlines counts as the same lacuna when it shares at least this
# share of either one's pixels.
PANEL_PX = 768
MATCH_SHARE = 0.1
RED, BLUE, YELLOW, PLAIN = (235, 40, 40), (40, 130, 255), (255, 205, 0), (225, 225, 225)
INK, PAPER = (20, 20, 20), (255, 255, 255)
PRE_VALIDATION = "Pre-validation: not checked against manual counts, not a lesion call."
POL_TEXT = [
    ("What we are looking for", True),
    ("A periosteocytic lesion (POL) is unmineralized matrix around an osteocyte, a space where bone "
     "should be. In these images the red dye fills the lacuna and that unmineralized space together, so a "
     "POL shows as a lacuna that is much larger and more irregular than normal. Its "
     "footprint is the lacuna as the pipeline outlined it. This is the working definition, to be confirmed "
     "by Dr. Murshed.", False),
    ("How to read the picture", True),
    ("Every lacuna is outlined, with its number and its area in um2. Green is a lacuna of normal size. "
     "Yellow is an enlarged lacuna, larger than 2 times the median WT lacuna: a candidate POL. Cyan is a "
     "cluster, two or more lacunae merged into one outline. Grey outlines touch the frame, so their area is "
     "cut and not measured. Grey shading is an excluded region (a saturated band at a tissue border or a "
     "very large bright structure), not analysed.", False),
    ("What the numbers mean", True),
    ("Enlarged share: how many of the measured lacunae are yellow. POL area per analysed area: how much of "
     "the analysed field the lacunar space covers. Where there are POLs, both are higher than in WT.", False),
]


def _missing(value) -> bool:
    return value is None or (isinstance(value, (float, np.floating)) and not np.isfinite(value))


def _value(value, kind: str) -> str:
    if _missing(value):
        return "none"
    if kind == "count":
        return f"{int(round(value))}"
    if kind == "share":
        return f"{100 * value:.1f}%"
    if kind == "number":
        return f"{value:.1f}"
    return f"{value:.3f} {kind}" if kind == "um per um2" else f"{value:.1f} {kind}"


def _difference(a, b, kind: str) -> str:
    if _missing(a) or _missing(b):
        return "none"
    d = b - a
    if kind == "count":
        return f"{int(round(d)):+d}"
    if kind == "share":
        return f"{100 * d:+.1f} points"
    if kind == "number":
        return f"{d:+.1f}"
    return f"{d:+.3f} {kind}" if kind == "um per um2" else f"{d:+.1f} {kind}"


def _font(size: int):
    from PIL import ImageFont  # noqa: PLC0415

    return ImageFont.load_default(size=size)


def _wrap(draw, text: str, font, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + ([line] if line else [])


def _table_picture(title: list[str], header: list[str], rows: list[list[str]], note: list[str], path: Path) -> None:
    """A table drawn as a picture, black on white: title lines, a header, the
    rows, and a note under them."""
    from PIL import Image, ImageDraw  # noqa: PLC0415

    big, small = _font(22), _font(18)
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    widths = [max(probe.textlength(str(r[i]), font=small) for r in [header] + rows) + 40 for i in range(len(header))]
    width = max(int(sum(widths)) + 40, 900)
    note_lines = [line for n in note for line in _wrap(probe, n, small, width - 40)]
    height = 30 + 34 * len(title) + 20 + 32 * (len(rows) + 1) + 20 + 26 * len(note_lines) + 20
    image = Image.new("RGB", (width, height), PAPER)
    draw = ImageDraw.Draw(image)
    y = 20
    for k, line in enumerate(title):
        draw.text((20, y), line, font=big if k == 0 else small, fill=INK)
        y += 34
    y += 10
    for r, row in enumerate([header] + rows):
        x = 20
        if r == 0:
            draw.rectangle([10, y - 4, width - 10, y + 26], fill=(230, 230, 230))
        for i, cell in enumerate(row):
            draw.text((x, y), str(cell), font=small, fill=INK)
            x += widths[i]
        y += 32
    y += 10
    for line in note_lines:
        draw.text((20, y), line, font=small, fill=(90, 90, 90))
        y += 26
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, optimize=True)


def write_key_numbers(group: str, label: str, row: dict, run_name: str, wt_median: float, folder: Path) -> None:
    """<label>_key_numbers.csv and .png: the main numbers of one image in one run."""
    import csv  # noqa: PLC0415

    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / f"{label}_{SUFFIX_KEY_NUMBERS}.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["measure", "column", "value", "unit"])
        for column, name, kind in KEY_NUMBERS:
            value = row.get(column)
            writer.writerow([name, column, "" if _missing(value) else round(float(value), 6),
                             {"count": "count", "number": "count", "share": "share"}.get(kind, kind)])
    rows = [[name, _value(row.get(column), kind)] for column, name, kind in KEY_NUMBERS]
    _table_picture([f"{group} {label}: key numbers, {run_name}", PRE_VALIDATION], ["measure", "value"], rows,
                   [f"Enlarged means above 2 x the median WT lacuna of this run ({2 * wt_median:.1f} um2). "
                    "Roots and length within 3.9 um: lacunae not cut by the frame. Every number is in "
                    "4_quantification/ and in results/SUMMARY.xlsx, sheet Per image."],
                   folder / f"{label}_{SUFFIX_KEY_NUMBERS}.png")


def write_pols_explained(group: str, label: str, run_name: str, outlines: Path, path: Path) -> None:
    """The POL outline picture with a panel of plain text beside it."""
    from PIL import Image, ImageDraw  # noqa: PLC0415

    with Image.open(outlines) as im:
        picture = im.convert("RGB")
    panel_w = 600
    image = Image.new("RGB", (picture.width + panel_w, picture.height), PAPER)
    image.paste(picture, (0, 0))
    draw = ImageDraw.Draw(image)
    head, body = _font(22), _font(17)
    x, y = picture.width + 20, 20
    for text, is_head in [(f"{group} {label}, {run_name}", True)] + POL_TEXT + [(PRE_VALIDATION, False)]:
        font = head if is_head else body
        for line in _wrap(draw, text, font, panel_w - 40):
            draw.text((x, y), line, font=font, fill=INK)
            y += 28 if is_head else 23
        y += 12
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, optimize=True)


def _background(image_path: Path) -> np.ndarray:
    """The original image, dimmed to grey, for a picture of changes."""
    display, _channel = lacunae.load_channel(image_path)
    grey = (0.45 * display.astype(np.float32).mean(axis=-1)).astype(np.uint8)
    return np.stack([grey] * 3, axis=-1)


def _draw_outlines(rgb: np.ndarray, labels: np.ndarray, ids, colour, thick: int = 2) -> None:
    from scipy import ndimage  # noqa: PLC0415
    from skimage.segmentation import find_boundaries  # noqa: PLC0415

    ids = [int(i) for i in ids]
    if not ids:
        return
    edge = find_boundaries(np.where(np.isin(labels, ids), labels, 0), mode="inner")
    if thick > 1:
        edge = ndimage.binary_dilation(edge, iterations=thick - 1)
    rgb[edge] = colour


def _overlaps(non: np.ndarray, ai: np.ndarray) -> tuple[dict, dict]:
    """({non-AI id: AI ids}, {AI id: non-AI ids}): the outlines of the two runs
    that are the same lacuna (sharing MATCH_SHARE of either one's pixels)."""
    both = (non > 0) & (ai > 0)
    pairs, counts = np.unique(np.stack([non[both], ai[both]], axis=1), axis=0, return_counts=True) \
        if both.any() else (np.zeros((0, 2), dtype=int), np.zeros(0, dtype=int))
    size_non = np.bincount(non.ravel())
    size_ai = np.bincount(ai.ravel())
    to_ai, to_non = {}, {}
    for (a, b), c in zip(pairs, counts):
        if c >= MATCH_SHARE * min(size_non[a], size_ai[b]) or c >= MATCH_SHARE * max(size_non[a], size_ai[b]):
            to_ai.setdefault(int(a), set()).add(int(b))
            to_non.setdefault(int(b), set()).add(int(a))
    return to_ai, to_non


def _pol_table(path: Path) -> dict:
    """{id: (ratio to the WT median or None, flag, cluster)} from a 3_pols table."""
    import csv  # noqa: PLC0415

    with open(path, newline="", encoding="utf-8") as f:
        return {int(r["id"]): (float(r["ratio_to_WT_median"]) if r["ratio_to_WT_median"] else None, r["flag"],
                               r["cluster"] == "yes") for r in csv.DictReader(f)}


def change_panels(image_path: Path, group: str, label: str) -> dict:
    """{feature: (rgb picture of what the AI changed, legend lines)}."""
    from skimage.io import imread  # noqa: PLC0415

    roots = [pols.set_root(group, set_name) for set_name, _folder, _name in RUNS]
    non, ai = (imread(lacunae.result_path(r, label, config.SECTION_LACUNAE, config.SUFFIX_LACUNA_LABELS))
               .astype(np.int64) for r in roots)
    t_non, t_ai = (_pol_table(lacunae.result_path(r, label, config.SECTION_POLS, pols.SUFFIX_TABLE)) for r in roots)
    to_ai, to_non = _overlaps(non, ai)
    ids_non = [int(i) for i in np.unique(non) if i]
    ids_ai = [int(i) for i in np.unique(ai) if i]
    removed = [i for i in ids_non if i not in to_ai]
    added = [i for i in ids_ai if i not in to_non]
    merged = [i for i in ids_ai if len(to_non.get(i, ())) >= 2]
    cluster_changed = [i for i in ids_ai if i in to_non and i not in merged and i in t_ai
                       and t_ai[i][2] != any(t_non.get(j, (None, "", False))[2] for j in to_non[i])]
    out = {}

    rgb = _background(image_path)
    _draw_outlines(rgb, ai, [i for i in ids_ai if i not in added + merged + cluster_changed], PLAIN)
    _draw_outlines(rgb, non, removed, RED)
    _draw_outlines(rgb, ai, added, BLUE)
    _draw_outlines(rgb, ai, merged + cluster_changed, YELLOW)
    out["lacunae"] = (rgb, [f"red: outlined without the AI, removed by it ({len(removed)})",
                            f"blue: added by the AI ({len(added)})",
                            f"yellow: pieces merged into one ({len(merged)}) or cluster flag changed "
                            f"({len(cluster_changed)}) by the AI",
                            f"white: the same in both ({len(ids_ai) - len(added) - len(merged) - len(cluster_changed)})"])

    s_non, s_ai = (imread(lacunae.result_path(r, label, config.SECTION_CANALICULI,
                                              config.SUFFIX_CANALICULI_SKELETON)) > 0 for r in roots)
    from scipy import ndimage  # noqa: PLC0415

    rgb = _background(image_path)
    rgb[s_non & s_ai] = (150, 150, 150)
    rgb[ndimage.binary_dilation(s_non & ~s_ai)] = RED
    rgb[ndimage.binary_dilation(s_ai & ~s_non)] = BLUE
    out["canaliculi"] = (rgb, [f"red: traced only without the AI ({int((s_non & ~s_ai).sum())} px)",
                               f"blue: traced only with the AI ({int((s_ai & ~s_non).sum())} px)",
                               f"grey: traced in both ({int((s_non & s_ai).sum())} px)",
                               "the AI judges trace no thread: the tracing moves only where the lacunae changed",
                               "the thread colours of the first two panels are per lacuna, not comparable between them"])

    def enlarged(table, i):
        ratio, flag, _cluster = table.get(i, (None, "x", False))
        return not flag and ratio is not None and ratio > 2.0

    big_non = [i for i in ids_non if enlarged(t_non, i)]
    big_ai = [i for i in ids_ai if enlarged(t_ai, i)]
    lost = [i for i in big_non if not any(enlarged(t_ai, j) for j in to_ai.get(i, ()))]
    new = [i for i in big_ai if not any(enlarged(t_non, j) for j in to_non.get(i, ())) and i not in merged]
    changed = [i for i in big_ai if i in merged or i in cluster_changed]
    kept = [i for i in big_ai if i not in new and i not in changed]
    rgb = _background(image_path)
    _draw_outlines(rgb, ai, kept, PLAIN)
    _draw_outlines(rgb, non, lost, RED)
    _draw_outlines(rgb, ai, new, BLUE)
    _draw_outlines(rgb, ai, changed, YELLOW)
    out["POLs"] = (rgb, [f"red: enlarged without the AI, not with it ({len(lost)})",
                         f"blue: enlarged only with the AI ({len(new)})",
                         f"yellow: enlarged, and merged or its cluster flag changed by the AI ({len(changed)})",
                         f"white: enlarged in both ({len(kept)}); enlarged = above 2 x the WT median of its run"])
    return out


def save_comparison(title: str, panels: list, legend: list[str], path: Path) -> None:
    """Panels [(caption, PIL image)] side by side, each PANEL_PX wide, under
    one title, with the legend under them."""
    from PIL import Image, ImageDraw  # noqa: PLC0415

    gap, head = 16, 70
    scaled = []
    for caption, im in panels:
        scale = PANEL_PX / im.width
        scaled.append((caption, im.convert("RGB").resize((PANEL_PX, round(im.height * scale)), Image.LANCZOS)))
    tall = max(im.height for _c, im in scaled)
    width = len(scaled) * PANEL_PX + (len(scaled) + 1) * gap
    image = Image.new("RGB", (width, head + 34 + tall + 24 + 28 * len(legend) + 20), PAPER)
    draw = ImageDraw.Draw(image)
    draw.text((gap, 14), title, font=_font(22), fill=INK)
    draw.text((gap, 42), PRE_VALIDATION, font=_font(16), fill=(90, 90, 90))
    for k, (caption, im) in enumerate(scaled):
        x = gap + k * (PANEL_PX + gap)
        draw.text((x, head + 4), caption, font=_font(18), fill=INK)
        image.paste(im, (x, head + 34))
    y = head + 34 + tall + 16
    for line in legend:
        draw.text((gap, y), line, font=_font(18), fill=INK)
        y += 28
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, optimize=True)


def build_samples(groups=None) -> int:
    """Every image's summary/ in both runs and its comparison/. Returns the
    number of pictures it could not make."""
    from PIL import Image  # noqa: PLC0415

    held_out = lacunae.held_out_labels()
    medians = {set_name: pols.wt_median_um2(set_name) for set_name, _f, _n in RUNS}
    missing = 0
    for group in groups or config.GROUPS:
        rows = {set_name: {r["image"]: r for r in animal_stats.collect(set_name, [group])[1]}
                for set_name, _f, _n in RUNS}
        done = 0
        for image_path in pols.image_files(group):
            label = lacunae.image_label(image_path)
            pictures = {}
            for set_name, _folder, run_name in RUNS:
                root = pols.set_root(group, set_name)
                summary = lacunae.sample_folder(root, label) / config.SECTION_SUMMARY
                summary.mkdir(parents=True, exist_ok=True)
                for section, suffix in ((config.SECTION_LACUNAE, config.SUFFIX_LACUNAE_OUTLINES),
                                        (config.SECTION_CANALICULI, config.SUFFIX_CANALICULI_VERIFICATION)):
                    original = lacunae.result_path(root, label, section, suffix)
                    if not original.is_file():
                        missing += 1
                        continue
                    shutil.copy2(original, summary / original.name)
                write_key_numbers(group, label, rows[set_name][label], run_name, medians[set_name], summary)
                outlines = lacunae.result_path(root, label, config.SECTION_POLS, pols.SUFFIX_OUTLINES)
                write_pols_explained(group, label, run_name, outlines, summary / f"{label}_{SUFFIX_POLS_EXPLAINED}")
                pictures[set_name] = root
            folder = config.RESULTS_ROOT / group / label / config.SAMPLE_COMPARISON
            changes = change_panels(image_path, group, label)
            for feature, section, suffix, out_suffix in COMPARISONS:
                rgb, legend = changes[feature]
                panels = []
                for set_name, _folder, run_name in RUNS:
                    with Image.open(lacunae.result_path(pictures[set_name], label, section, suffix)) as im:
                        panels.append((run_name.split(" (")[0], im.copy()))
                panels.append(("what the AI changed", Image.fromarray(rgb)))
                save_comparison(f"{group} {label}: {feature}, without and with the AI judges", panels, legend,
                                folder / f"{label}_{out_suffix}")
            write_compare_numbers(group, label, rows, folder)
            done += 1
        print(f"{group}: {done} images, summary/ in both runs and comparison/"
              + (f" ({sum(1 for p in pols.image_files(group) if lacunae.image_label(p) in held_out)} held out, "
                 "not shown)" if held_out & {lacunae.image_label(p) for p in pols.image_files(group)} else ""))
    return missing


def write_compare_numbers(group: str, label: str, rows: dict, folder: Path) -> None:
    """<label>_compare_numbers.csv and .png: each key number in both runs and the difference."""
    import csv  # noqa: PLC0415

    non, ai = (rows[set_name][label] for set_name, _f, _n in RUNS)
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / f"{label}_{SUFFIX_COMPARE_NUMBERS}.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["measure", "column", "non_ai_run", "ai_judges", "ai_minus_non_ai"])
        for column, name, _kind in KEY_NUMBERS:
            a, b = non.get(column), ai.get(column)
            writer.writerow([name, column] + ["" if _missing(v) else round(float(v), 6) for v in (a, b)]
                            + ["" if _missing(a) or _missing(b) else round(float(b) - float(a), 6)])
    table = [[name, _value(non.get(c), kind), _value(ai.get(c), kind), _difference(non.get(c), ai.get(c), kind)]
             for c, name, kind in KEY_NUMBERS]
    _table_picture([f"{group} {label}: key numbers without and with the AI judges", PRE_VALIDATION],
                   ["measure", "non-AI run", "AI judges run", "AI minus non-AI"], table,
                   ["Each run is measured against the median WT lacuna of its own run. The AI judges run has the "
                    "AI lacuna judge (which outlines are lacunae) and the AI POL judge (merges split pieces, "
                    "flags clusters, removes what is no lacuna) on; nothing is redrawn by them."],
                   folder / f"{label}_{SUFFIX_COMPARE_NUMBERS}.png")


def main() -> None:
    parser = argparse.ArgumentParser(description="The key results view and results/SUMMARY.xlsx.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("all", help="Every group's 0_key_results/ and results/SUMMARY.xlsx.")
    sub.add_parser("check", help="Every key picture equal to its original.")
    p = sub.add_parser("samples", help="Every image's summary/ in both runs and its comparison/ (no table rebuilt).")
    p.add_argument("-g", "--group", choices=config.GROUPS, default=None, help="One group only.")
    args = parser.parse_args()
    if args.command == "check":
        sys.exit(check())
    if args.command == "samples":
        sys.exit(1 if build_samples([args.group] if args.group else None) else 0)
    missing = sum(copy_group(g) for g in config.GROUPS)
    write_summary_xlsx()
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
