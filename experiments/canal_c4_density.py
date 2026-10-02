"""C4: field density without the flagged canal mask; self-test of the -m ROI option.

    python -u experiments/canal_c4_density.py

Per image of the default run: field density, the new
field_density_without_flagged_per_px, the change, the share of the area and
of the skeleton inside the flagged mask, beside the overnight report 5.1
column "without canal mask". Then the -m option of src/canaliculi.py is run
from the command line on two images with synthetic masks in the git-ignored
cache (an all-white mask named by the clean name, and a left-half mask named
by the short name); the written field_density_in_roi_per_px must equal the
value computed here. No draft ROI is used.

Outputs in results_experiments/canal_v2/: C4_density.csv, .md.
PRE-VALIDATION, PIXEL units.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canal_common as K  # noqa: E402
import common as C  # noqa: E402

ROI_TEST = K.CACHE / "c4_roi_test"


def roi_selftest() -> list[str]:
    masks = ROI_TEST / "masks"
    out = ROI_TEST / "out"
    masks.mkdir(parents=True, exist_ok=True)
    cases = [("543-2", "543-2.png", "all white", lambda s: np.ones(s, bool)),
             ("682_z08", "682_z08.png", "left half white (short name)",
              lambda s: np.pad(np.ones((s[0], s[1] // 2), bool), ((0, 0), (0, s[1] - s[1] // 2))))]
    lines = []
    for name, fname, label, make in cases:
        d = K.pipeline(name)
        roi = make(d["skeleton"].shape)
        Image.fromarray((roi * 255).astype(np.uint8)).save(masks / fname)
        lac = d["lacuna_id_map"] > 0
        expected = round(float((d["skeleton"] & roi).sum()) / float((roi & ~lac).sum()), 8)
        img = C.image_path(name)
        cmd = [sys.executable, "-u", str(C.ROOT / "src" / "canaliculi.py"), "--image", str(img), "-o", str(out),
               "-m", str(masks)]
        done = subprocess.run(cmd, capture_output=True, text=True, cwd=C.ROOT)
        assert done.returncode == 0, done.stderr[-2000:]
        js = json.loads((out / C.clean(img) / "canaliculi_measurements.json").read_text())
        got = js["field"]["field_density_in_roi_per_px"]
        plain = js["field"]["canalicular_length_density_per_px"]
        assert got == expected, (name, got, expected)
        if label == "all white":
            assert got == plain, (got, plain)
        lines.append(f"| {name} | `{fname}` | {label} | {expected} | {got} | {plain} | PASS |")
    # Without -m nothing is applied.
    for name in ("543-2",):
        assert K.pipeline(name)["field"]["field_density_in_roi_per_px"] is None
    return lines


def item_c4() -> None:
    task5 = pd.read_csv(C.OUT_ROOT / "task5" / "5.1_density_three_ways.csv")
    rows = []
    for name in K.names():
        d = K.pipeline(name)
        f = d["field"]
        lac = d["lacuna_id_map"] > 0
        fl = d["flagged"]
        t = task5[task5.image == name]
        rows.append({"image": name, "field_density": f["canalicular_length_density_per_px"],
                     "without_flagged": f["field_density_without_flagged_per_px"],
                     "change_pct": 100 * (f["field_density_without_flagged_per_px"] / f["canalicular_length_density_per_px"] - 1),
                     "flagged_share_of_area": float((fl & ~lac).sum() / (~lac).sum()),
                     "flagged_share_of_skeleton": float((d["skeleton"] & fl).sum() / d["skeleton"].sum()),
                     "overnight_5_1_without_flagged_pct": float(t.iloc[0]["pct_change_without_flagged"])})
    df = pd.DataFrame(rows)
    gap = float((df.change_pct - df.overnight_5_1_without_flagged_pct).abs().max())
    C.write_csv(K.OUT / "C4_density.csv", df)
    checks = roi_selftest()
    md = ["# C4 Field density without the flagged regions, and an optional ROI", "",
          "Pre-validation, px. New field keys (and summary table columns): `field_density_without_flagged_per_px`, the",
          "skeleton px outside the flagged canal mask over the analysed area outside it (the mask as the pipeline uses",
          "it, dilated by 4 px), and `field_density_in_roi_per_px`, written only with `python src/canaliculi.py ... -m",
          "DIR` (PNG masks, white = bone, named by the clean or the short image name, as",
          "`results_experiments/task5/roi_edited`). Without `-m` it is None: no ROI is applied by default, and the",
          "draft ROI is not used.", "",
          "## Field density without the flagged regions", "",
          C.md_table(df, floatfmt="{:.5f}"), "",
          "Against the overnight report 5.1 column \"without canal mask\" (`results_experiments/task5/",
          f"5.1_density_three_ways.csv`): the largest difference over the 8 images is {gap:.1e} percentage points"
          + (", which is the 8-decimal rounding of the stored densities: the pipeline column reproduces the experiment."
             if gap < 1e-3 else "; see the table.")
          + " 543-2, 543_3 and 543_z13 have no flagged region, so nothing changes there.", "",
          "## Self-test of the -m option (asserted)", "",
          "`src/canaliculi.py` run from the command line into the git-ignored cache with synthetic masks:", "",
          "| image | mask file | mask | expected | written | plain density | result |",
          "|---|---|---|---|---|---|---|", *checks, "",
          "Without `-m` the key is None (checked on the cached default run).", ""]
    C.write_text(K.OUT / "C4_density.md", "\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    K.OUT.mkdir(parents=True, exist_ok=True)
    ok = C.run_item("C4", item_c4)
    sys.exit(0 if ok else 1)
