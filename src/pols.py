"""The POL section: candidate POL measure, lacunar size, pending definition.

PRE-VALIDATION. Periosteocytic lesions (POLs) are enlarged lacunae. There is
no agreed definition of a POL in these images yet, so this section shows the
one candidate that needs no new detection: the size of each lacuna, set against
the WT median. It is not a lesion call, and every output says
"candidate POL measure: lacunar size, pending definition".

The ring proxy that this section showed before (src/pol_ring_proxy.py) is
retired: it measured the dye glow around every lacuna, the same width in WT,
and not lesions. Its outputs are in results/<group>/5_archive/pol_ring_proxy/.

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

LACUNA_COLUMNS = ["id", "area_um2", "ratio_to_WT_median", "flag"]
STAT_COLUMNS = ["n", "n_flagged", "area_um2_mean", "area_um2_median", "area_um2_p90",
                "ratio_mean", "ratio_median", "ratio_p90"]
IMAGE_COLUMNS = ["status", "group", "image"] + STAT_COLUMNS + ["WT_median_area_um2"]
GROUP_COLUMNS = ["status", "group", "n_images"] + STAT_COLUMNS + ["WT_median_area_um2"]
DIGITS = 4

# Picture. One colour scale for every group: the ratio to the WT median on a
# log2 axis from 1/4 to 4 times, clipped at both ends, so a lacuna of the WT
# median size is the middle colour everywhere. viridis is colour-blind safe and
# has no white that could vanish on a bright lacuna. Display only.
RATIO_LIMITS = (0.25, 4.0)
RATIO_TICKS = (0.25, 0.5, 1.0, 2.0, 4.0)
COLOUR_MAP = "viridis"
FILL_ALPHA = 0.7
OUTLINE_LW = 1.2  # measured lacunae are also outlined in their own colour, opaque
FLAGGED_COLOUR = "#A6A6A6"
SCALE_BAR_UM = 10.0
DPI = 100


# Numbers

def _round(value):
    return None if value is None else round(float(value), DIGITS)


def image_files(group: str) -> list[Path]:
    return sorted((config.DATA_DIR / group).glob("*.tif"))


def lacuna_records(results_root: Path, label: str) -> list[dict]:
    """The quantification json's lacunae of one image, as {id, area_px2, flag}."""
    q = json.loads(quantification.quant_path(results_root, label, ".json").read_text(encoding="utf-8"))
    out = []
    for r in q["lacunae"]:
        if r["area_px2"] is None:
            flag = "no_area"
        elif r["on_border"]:
            flag = "edge"
        else:
            flag = ""
        out.append({"id": int(r["lacuna_id"]), "area_px2": r["area_px2"], "flag": flag})
    return out


def wt_median_um2() -> float:
    """Median area of every measured WT lacuna, pooled over the WT images."""
    areas = [r["area_px2"] * UM2_PER_PX2
             for p in image_files(config.REFERENCE_GROUP)
             for r in lacuna_records(config.RESULTS_DIR, lacunae.image_label(p)) if not r["flag"]]
    if not areas:
        raise FileNotFoundError("no measured WT lacuna in results/WT/4_quantification/")
    return float(np.median(areas))


def lacuna_rows(records: list[dict], wt_median: float) -> list[dict]:
    rows = []
    for r in records:
        area = None if r["area_px2"] is None else r["area_px2"] * UM2_PER_PX2
        ratio = area / wt_median if (area is not None and not r["flag"]) else None
        rows.append({"id": r["id"], "area_um2": _round(area), "ratio_to_WT_median": _round(ratio),
                     "flag": r["flag"]})
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
            "Source: 4_quantification/<image>_quantification.json. No new detection. src/pols.py."]


# Picture

def save_picture(image_path: Path, labels: np.ndarray, rows: list[dict], wt_median: float, path: Path) -> None:
    """The lacunar size picture of one image (module docstring)."""
    import matplotlib  # noqa: PLC0415

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # noqa: PLC0415
    from matplotlib import colors, patheffects  # noqa: PLC0415
    from skimage import measure  # noqa: PLC0415

    display, _channel = lacunae.load_channel(image_path)
    h, w = labels.shape
    norm = colors.LogNorm(vmin=RATIO_LIMITS[0], vmax=RATIO_LIMITS[1], clip=True)
    cmap = plt.get_cmap(COLOUR_MAP)
    fill = np.zeros((h, w, 4), dtype=float)
    for r in rows:
        if r["flag"]:
            continue
        rgba = cmap(norm(r["_ratio"]))
        fill[labels == r["id"]] = (rgba[0], rgba[1], rgba[2], FILL_ALPHA)

    bar_w = 230
    fig = plt.figure(figsize=((w + bar_w) / DPI, (h + 40) / DPI), dpi=DPI)
    ax = fig.add_axes([0, 0, w / (w + bar_w), h / (h + 40)])
    ax.imshow(display, interpolation="nearest")
    ax.imshow(fill, interpolation="nearest")
    halo = [patheffects.withStroke(linewidth=2, foreground="black")]
    for r in rows:
        mask = labels == r["id"]
        if not mask.any():
            continue
        edge = FLAGGED_COLOUR if r["flag"] else cmap(norm(r["_ratio"]))
        for c in measure.find_contours(np.pad(mask, 1).astype(float), 0.5):
            ax.plot(c[:, 1] - 1, c[:, 0] - 1, color=edge, lw=1.0 if r["flag"] else OUTLINE_LW)
        rows_i, cols_i = np.nonzero(mask)
        x = cols_i.max() + 4
        ha = "left"
        if x > w - 60:
            x, ha = cols_i.min() - 4, "right"
        y = float(np.clip(rows_i.mean(), 8, h - 8))
        text = f"{r['id']}: {r['area_um2']:.1f}" if r["area_um2"] is not None else f"{r['id']}: {r['flag']}"
        ax.text(x, y, text, color="white" if not r["flag"] else FLAGGED_COLOUR, fontsize=7, ha=ha,
                va="center", path_effects=halo)
    bar_px = SCALE_BAR_UM / UM_PER_PX
    x0, y0 = w - 20 - bar_px, h - 20
    ax.plot([x0, x0 + bar_px], [y0, y0], color="white", lw=3, solid_capstyle="butt")
    ax.text(x0 + bar_px / 2, y0 - 6, f"{SCALE_BAR_UM:g} um", color="white", fontsize=8, ha="center",
            va="bottom", path_effects=halo)
    ax.set_xlim(-0.5, w - 0.5)
    ax.set_ylim(h - 0.5, -0.5)
    ax.axis("off")

    cax = fig.add_axes([(w + 40) / (w + bar_w), 0.12, 22 / (w + bar_w), 0.7])
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    bar = fig.colorbar(sm, cax=cax)
    bar.set_ticks(list(RATIO_TICKS))
    bar.set_ticklabels([f"{t * wt_median:.0f}" + (" (WT median)" if t == 1.0 else "") for t in RATIO_TICKS])
    bar.ax.minorticks_off()
    bar.ax.tick_params(labelsize=8)
    bar.set_label("lacunar area (um2), colour by ratio to the WT median", fontsize=8)
    fig.text(0.005, 1 - 20 / (h + 40), f"{image_path.parent.name} {lacunae.image_label(image_path)}: {LABEL}. "
             f"Grey outline: flagged (edge or no area), not filled. Pre-validation.",
             fontsize=9, ha="left", va="center")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=DPI, facecolor="white")
    plt.close(fig)


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
glow around every lacuna, the same width in WT, and not lesions. Its files are
in `../5_archive/pol_ring_proxy/`.
"""


def write_readme(results_root: Path, group: str) -> Path:
    path = lacunae.group_path(results_root, config.SECTION_POLS, "README.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(README.format(group=group, label_cap=LABEL[0].upper() + LABEL[1:]), encoding="utf-8")
    return path


def measure_group(group: str, results_root: Path | None = None, wt_median: float | None = None) -> list[dict]:
    """Every image of one group: picture and table per image, the group table
    and the contact sheet. Returns the image rows."""
    from skimage.io import imread  # noqa: PLC0415

    results_root = Path(results_root or config.RESULTS_ROOT / group)
    wt_median = wt_median_um2() if wt_median is None else wt_median
    image_rows, tiles = [], []
    for image_path in image_files(group):
        label = lacunae.image_label(image_path)
        records = lacuna_records(results_root, label)
        rows = with_raw(records, wt_median)
        labels = np.asarray(imread(lacunae.result_path(results_root, label, config.SECTION_LACUNAE,
                                                       config.SUFFIX_LACUNA_LABELS)))
        if int(labels.max()) != len(records):
            raise ValueError(f"{group}/{label}: {int(labels.max())} labels, {len(records)} lacunae in the json")
        write_csv(lacunae.result_path(results_root, label, config.SECTION_POLS, SUFFIX_TABLE), LACUNA_COLUMNS, rows)
        picture = lacunae.result_path(results_root, label, config.SECTION_POLS, SUFFIX_PICTURE)
        save_picture(image_path, labels, rows, wt_median, picture)
        tiles.append((label, picture))
        image_rows.append({"status": LABEL, "group": group, "image": label, **stats(rows),
                           "WT_median_area_um2": _round(wt_median)})
        print(f"{group}/{label}: {image_rows[-1]['n']} measured, {image_rows[-1]['n_flagged']} flagged, "
              f"median {image_rows[-1]['area_um2_median']} um2")
    table = lacunae.group_path(results_root, config.SECTION_POLS, GROUP_TABLE)
    write_csv(table.with_suffix(".csv"), IMAGE_COLUMNS, image_rows)
    write_xlsx(table.with_suffix(".xlsx"), IMAGE_COLUMNS, image_rows, notes(wt_median))
    lacunae.save_contact_sheet(tiles, f"{group}: {LABEL}. Full size: 3_pols/<image>_{SUFFIX_PICTURE}.",
                               lacunae.group_path(results_root, config.SECTION_POLS, CONTACT_SHEET))
    write_readme(results_root, group)
    return image_rows


def group_summary(groups=config.GROUPS, wt_median: float | None = None) -> list[dict]:
    """results/summary/pols_lacunar_size_by_group.csv: per group, every
    measured lacuna pooled."""
    wt_median = wt_median_um2() if wt_median is None else wt_median
    out = []
    for group in groups:
        rows = []
        files = image_files(group)
        for p in files:
            rows += with_raw(lacuna_records(config.RESULTS_ROOT / group, lacunae.image_label(p)), wt_median)
        out.append({"status": LABEL, "group": group, "n_images": len(files), **stats(rows),
                    "WT_median_area_um2": _round(wt_median)})
    write_csv(SUMMARY_TABLE, GROUP_COLUMNS, out)
    return out


def check(groups=config.GROUPS) -> int:
    """Every file of every group: present, and each per-lacuna table equal to
    the json areas times 0.0169 and to the WT median ratio."""
    wt_median = wt_median_um2()
    failed = 0
    for group in groups:
        root = config.RESULTS_ROOT / group
        for p in image_files(group):
            label = lacunae.image_label(p)
            want = lacuna_rows(lacuna_records(root, label), wt_median)
            pic = lacunae.result_path(root, label, config.SECTION_POLS, SUFFIX_PICTURE)
            tab = lacunae.result_path(root, label, config.SECTION_POLS, SUFFIX_TABLE)
            problem = ""
            if not pic.is_file() or not tab.is_file():
                problem = "missing file"
            else:
                with open(tab, newline="", encoding="utf-8") as f:
                    got = list(csv.DictReader(f))
                norm = [{k: ("" if r[k] is None else str(r[k])) for k in LACUNA_COLUMNS} for r in want]
                if got != norm:
                    problem = "table differs from the json"
            failed += bool(problem)
            print(f"{group:<7} {label:<26} {problem or 'PASS'}")
        for name in (f"{GROUP_TABLE}.csv", f"{GROUP_TABLE}.xlsx", CONTACT_SHEET):
            if not lacunae.group_path(root, config.SECTION_POLS, name).is_file():
                print(f"{group:<7} {name:<26} missing file")
                failed += 1
    if not SUMMARY_TABLE.is_file():
        print(f"{SUMMARY_TABLE} missing")
        failed += 1
    print(f"\n{'FAIL' if failed else 'PASS'}: lacunar size check, {failed} problem(s).")
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
    image = next(iter(image_files(config.REFERENCE_GROUP)), None)
    if image is not None:
        labels = np.zeros(lacunae.load_channel(image)[1].shape, dtype=np.int32)
        labels[100:140, 100:125] = 1
        labels[200:250, 300:340] = 2
        labels[0:20, 0:25] = 3
        labels[400:410, 400:410] = 4
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "picture.png"
            save_picture(image, labels, rows, median, out)
            checks.append(("the picture is written", out.is_file() and out.stat().st_size > 0))
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    ok = all(ok for _n, ok in checks)
    print(f"\n{'PASS' if ok else 'FAIL'}: {sum(ok for _n, ok in checks)} of {len(checks)} checks.")
    return 0 if ok else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=f"The POL section: {LABEL}.")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("measure", help="One group: results/<group>/3_pols/.")
    p.add_argument("-d", "--dir", type=Path, required=True, help="A group folder of .tif images, e.g. data/WT_HP.")
    p.add_argument("-r", "--results", type=Path, default=None,
                   help="The group's results folder (default: results/<name of the input folder>).")
    sub.add_parser("all", help="Every group, then results/summary/pols_lacunar_size_by_group.csv.")
    sub.add_parser("summary", help="Only results/summary/pols_lacunar_size_by_group.csv.")
    sub.add_parser("check", help="Every 3_pols file against the quantification jsons.")
    sub.add_parser("selftest", help="Checks on synthetic records.")
    args = parser.parse_args()
    if args.command == "selftest":
        sys.exit(selftest())
    if args.command == "check":
        sys.exit(check())
    if args.command == "measure":
        group = Path(args.dir).resolve().name
        measure_group(group, args.results)
    elif args.command == "all":
        wt_median = wt_median_um2()
        for group in config.GROUPS:
            measure_group(group, wt_median=wt_median)
    rows = group_summary()
    print(f"-> {SUMMARY_TABLE}")
    for r in rows:
        print(f"  {r['group']:<7} n={r['n']:<4} median {r['area_um2_median']} um2, ratio median {r['ratio_median']}")


if __name__ == "__main__":
    main()
