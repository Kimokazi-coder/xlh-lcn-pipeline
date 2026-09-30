"""Build the presentation outputs. Pre-validation, PIXEL units.

Runs canaliculi_v1.process on every image with the module defaults EXCEPT
two settings, set for this run only and never written back:
    reach cap ON at canaliculi_v1.REACH_CAP_PRIMARY_PX (275 px)
    SHOW_UNOWNED_GREY ON, so the overlay shows in grey what no cell owns
and writes everything under results/presentation/, never into
results/canaliculi/, whose default outputs stay as they are.

Per image, in results/presentation/<image>/: the five default-style files
(verification.png with unowned threads grey, canaliculi_mask.png,
skeleton.png, measurements.xlsx, measurements.json) plus bridges.png.

One table, results/presentation/summary_table.xlsx and .csv, one row per
image:
    lacuna_count                  all kept v2 lacunae
    interior_lacuna_count         those not touching the frame edge; the n
                                  behind every per-cell mean below
    median_lacuna_area_px2        interior lacunae, from results/lacunae/
    roots_per_cell                mean over interior cells
    ring_length_r30_px_per_cell   mean over interior cells
    ring_length_r60_px_per_cell   mean over interior cells
    field_length_density_per_px   skeleton px per analysed px of field

Usage (from the repo root):
    python src/make_presentation.py --dir data/WT
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canaliculi_v1 as can  # noqa: E402

PRESENTATION_DIR = config.RESULTS_DIR / "presentation"

COLUMNS = [
    ("image", ""),
    ("status", ""),
    ("lacuna_count", "count"),
    ("interior_lacuna_count", "count"),
    ("median_lacuna_area_px2", "px^2"),
    ("roots_per_cell", "count"),
    ("ring_length_r30_px_per_cell", "px"),
    ("ring_length_r60_px_per_cell", "px"),
    ("field_length_density_per_px", "px^-1"),
    ("reach_cap_px", "px"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dir", type=Path, required=True)
    args = parser.parse_args()

    # Presentation-only settings, applied to the imported module for this
    # process only. Nothing on disk changes.
    can.CANALICULI_DIR = PRESENTATION_DIR
    can.SHOW_UNOWNED_GREY = True
    cap = can.REACH_CAP_PRIMARY_PX

    rows = []
    for path in sorted(args.dir.glob("*.tif")):
        run = can.process(path, reach_cap=cap)
        stem = path.stem.replace(" ", "_")
        written = json.load(open(PRESENTATION_DIR / stem / "measurements.json"))
        lacunae = json.load(open(config.LACUNAE_DIR / stem / "measurements.json"))
        if lacunae["lacuna_count"] != written["lacuna_count"]:
            raise SystemExit(f"{stem}: lacuna count {written['lacuna_count']} here vs "
                             f"{lacunae['lacuna_count']} in results/lacunae")
        s = run["stats"]
        rows.append({
            "image": path.stem,
            "status": "pre-validation",
            "lacuna_count": written["lacuna_count"],
            "interior_lacuna_count": s["interior_lacuna_count"],
            "median_lacuna_area_px2": lacunae["summary"]["area"]["median"],
            "roots_per_cell": s["roots_count"]["mean"],
            "ring_length_r30_px_per_cell": s["ring_length_r30_px"]["mean"],
            "ring_length_r60_px_per_cell": s["ring_length_r60_px"]["mean"],
            "field_length_density_per_px": run["field"]["canalicular_length_density_per_px"],
            "reach_cap_px": cap,
        })

    header = [f"{name} ({unit})" if unit else name for name, unit in COLUMNS]
    with open(PRESENTATION_DIR / "summary_table.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow([r[name] for name, _ in COLUMNS])

    from openpyxl import Workbook

    wb = Workbook()
    sheet = wb.active
    sheet.title = "summary"
    sheet.append(header)
    for r in rows:
        sheet.append([r[name] for name, _ in COLUMNS])
    notes = wb.create_sheet("notes")
    for line in [
        "PRE-VALIDATION. Not yet checked against manual (ImageJ) counts.",
        "PIXEL units throughout. No micron calibration exists for these images.",
        "8 WT images only. No Hyp or Hyp;Enpp1 images have been processed.",
        "Per-cell values are means over interior lacunae (not touching the frame edge).",
        "roots_per_cell: distinct canalicular threads leaving each lacuna surface.",
        "ring_length_r30 / r60: skeleton px within 30 / 60 px of each lacuna, each pixel",
        "  counted for its nearest lacuna only. Neither depends on network ownership.",
        "field_length_density: total skeleton px divided by the analysed field area in px.",
        f"reach cap {cap:g} px was on for the overlays; it does not change any column here.",
        "See PIPELINE_NOTE.md in this folder for the method and known limitations.",
    ]:
        notes.append([line])
    wb.save(PRESENTATION_DIR / "summary_table.xlsx")

    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
