"""The key results view: the important pictures of each image in one folder
per group, and one summary workbook.

PRE-VALIDATION. Nothing is measured or drawn here; every file is a copy or a
table of what the pipeline already saved, and the originals are not changed.

Per group, results/<group>/0_key_results/ holds, for every image, copies of
    <image>_1_lacunae_outlines.png         1_lacunae/<image>_lacunae_outlines.png
    <image>_2_canaliculi_verification.png  2_canaliculi/<image>_canaliculi_verification.png
    <image>_3_pols_outlines.png            3_pols/<image>_pols_outlines.png
named so they sort by image, and a README.md.
results/SUMMARY.xlsx: sheets Read me, Per group, Per animal, Per image and
Statistics, from src/animal_stats.py, and Judge on vs off, from
results/archive/judge/judge_on_vs_off.csv (python src/diagnostics.py
judge-compare).

In DEV mode the held-out images are left out (docs/HOLDOUT.md).

Usage (from the repo root):
    python src/key_results.py all        # every group's folder and results/SUMMARY.xlsx
    python src/key_results.py check      # every copy equal to its original
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

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
group, copied from the sections beside this folder (the originals are not
changed), named so they sort by image:

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


def main() -> None:
    parser = argparse.ArgumentParser(description="The key results view and results/SUMMARY.xlsx.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("all", help="Every group's 0_key_results/ and results/SUMMARY.xlsx.")
    sub.add_parser("check", help="Every key picture equal to its original.")
    args = parser.parse_args()
    if args.command == "check":
        sys.exit(check())
    missing = sum(copy_group(g) for g in config.GROUPS)
    write_summary_xlsx()
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
