"""S2: bridging audit.

    python -u experiments/canal_s2_bridges.py

Every bridge the default pipeline adds (image, the two endpoints, gap length,
angle, minimum and mean signal along the gap as a fraction of t_lo), one crop
sheet per image with the bridges in sky blue on the skeleton, and the
no-bridging run of the network sweep (S1, MAX_BRIDGE_GAP_PX = 0) on every
headline measure. Bridging parameters are not changed.

Outputs in results_experiments/canal_v2/: S2_bridges.csv, S2_bridging.md,
S2_bridges_<image>.png. PRE-VALIDATION, PIXEL units, (x, y) = (column, row).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canal_common as K  # noqa: E402
import common as C  # noqa: E402
import canaliculi  # noqa: E402

SKY_BLUE = (86, 180, 233)
HALF = 24
SCALE = 4
COLS = 6


def centred(a: np.ndarray, x0: int, y0: int) -> np.ndarray:
    """The 2 HALF square with top left (x0, y0), zero padded outside the frame."""
    out = np.zeros((2 * HALF, 2 * HALF) + a.shape[2:], dtype=a.dtype)
    H, W = a.shape[:2]
    sx0, sy0, sx1, sy1 = max(x0, 0), max(y0, 0), min(x0 + 2 * HALF, W), min(y0 + 2 * HALF, H)
    out[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = a[sy0:sy1, sx0:sx1]
    return out


def tile(d: dict, b: dict, k: int) -> np.ndarray:
    r0, c0 = b["from_row_col"]
    r1, c1 = b["to_row_col"]
    x, y = int(round((c0 + c1) / 2)), int(round((r0 + r1) / 2))
    x0, y0 = x - HALF, y - HALF
    pad = centred(C.to_rgb(d["channel"]), x0, y0)
    sk = centred(d["skeleton"], x0, y0)
    bridge = np.zeros_like(sk)
    rr, cc = np.array(b["pixels_row"]) - y0, np.array(b["pixels_col"]) - x0
    ok = (rr >= 0) & (rr < 2 * HALF) & (cc >= 0) & (cc < 2 * HALF)
    bridge[rr[ok], cc[ok]] = True
    over = C.paint(pad // 2, sk, (230, 230, 230))
    over = C.paint(over, bridge, SKY_BLUE)
    up = np.kron(over, np.ones((SCALE, SCALE, 1), np.uint8))
    im = Image.fromarray(np.vstack([np.full((14, up.shape[1], 3), 255, np.uint8), up]))
    ImageDraw.Draw(im).text((2, 1), f"B{k} ({x},{y}) gap {b['gap_len_px']:.1f} px", fill=(0, 0, 0))
    return np.asarray(im)


def item_s2() -> None:
    rows = []
    for name in K.names():
        d = K.pipeline(name)
        prep = canaliculi.preprocess_channel(d["channel"])
        t_lo = d["t_lo"]
        tiles = []
        for k, b in enumerate(d["bridges"], start=1):
            frac = prep[np.array(b["pixels_row"]), np.array(b["pixels_col"])] / t_lo
            assert abs(float(frac.min()) - b["min_signal_fraction"]) < 1e-9, (name, k)
            on_skel = int(d["skeleton"][np.array(b["pixels_row"]), np.array(b["pixels_col"])].sum())
            rows.append({"image": name, "bridge": k,
                         "from_x": b["from_row_col"][1], "from_y": b["from_row_col"][0],
                         "to_x": b["to_row_col"][1], "to_y": b["to_row_col"][0],
                         "gap_len_px": round(b["gap_len_px"], 3), "angle_deg": round(b["angle_deg"], 2),
                         "min_signal_fraction": round(b["min_signal_fraction"], 4),
                         "mean_signal_fraction": round(float(frac.mean()), 4),
                         "gap_pixels": len(b["pixels_row"]), "gap_pixels_on_final_skeleton": on_skel})
            tiles.append(tile(d, b, k))
        if tiles:
            grid = []
            for i in range(0, len(tiles), COLS):
                row = tiles[i:i + COLS]
                width = sum(t.shape[1] for t in row) + 8 * (len(row) - 1)
                canvas = np.full((max(t.shape[0] for t in row), width, 3), 255, np.uint8)
                xo = 0
                for t in row:
                    canvas[:t.shape[0], xo:xo + t.shape[1]] = t
                    xo += t.shape[1] + 8
                grid.append(canvas)
            C.write_png(K.OUT / f"S2_bridges_{name}.png", C.panel_grid(grid))
    df = pd.DataFrame(rows)
    C.write_csv(K.OUT / "S2_bridges.csv", df)

    sweep = pd.read_csv(K.OUT / "S1_network_sweep.csv")
    base = sweep[sweep.parameter == "default"].set_index("image")
    nob = sweep[(sweep.parameter == "MAX_BRIDGE_GAP_PX") & (sweep.value == 0)].set_index("image")
    measures = [("roots_per_cell", "roots per cell"), ("ring30", "ring 30 px"), ("field_density", "field density"),
                ("ring30_attached", "ring attached 30 px"), ("sholl10", "Sholl 10 px"), ("sholl30", "Sholl 30 px")]
    dep = []
    for img in base.index:
        row = {"image": img, "bridges": int(base.loc[img, "bridges"])}
        for key, label in measures:
            row[f"{label}: share from bridging %"] = 100.0 * (base.loc[img, key] - nob.loc[img, key]) / base.loc[img, key]
        dep.append(row)
    dep = pd.DataFrame(dep)
    per_image = df.groupby("image", sort=False).agg(bridges=("bridge", "size"), gap_median=("gap_len_px", "median"),
                                                    gap_max=("gap_len_px", "max"),
                                                    angle_median=("angle_deg", "median"),
                                                    min_signal_median=("min_signal_fraction", "median"),
                                                    mean_signal_median=("mean_signal_fraction", "median"),
                                                    gap_px=("gap_pixels", "sum")).reset_index()
    skel = {n: int(K.pipeline(n)["skeleton"].sum()) for n in K.names()}
    per_image["gap px share of skeleton %"] = [100.0 * r.gap_px / skel[r.image] for r in per_image.itertuples()]
    cols = [c for c in dep.columns if c.endswith("%")]
    md = ["# S2 Bridging audit", "",
          "Pre-validation, px, (x, y) = (column, row). Every bridge of the default run: the two endpoints, the gap",
          "length, the angle between the thread and the gap, and the signal along the gap as a fraction of t_lo",
          "(the minimum is the pipeline's test, at least 0.7; the mean is computed here). The bridging parameters",
          f"are not changed. {len(df)} bridges over {df.image.nunique()} images; all bridges: `S2_bridges.csv`.", "",
          "## Bridges per image", "",
          C.md_table(per_image, floatfmt="{:.3f}"), "",
          "## What depends on bridging", "",
          "The share of each measure that bridging adds: (default minus the run with no bridging, from the network",
          "sweep S1, MAX_BRIDGE_GAP_PX = 0) over the default, per image. Negative means the measure is larger",
          "without bridges.", "",
          C.md_table(dep, floatfmt="{:+.2f}"), "",
          "Over the 8 images: " + "; ".join(
              f"{c.split(':')[0]} {dep[c].min():+.2f} to {dep[c].max():+.2f}% (median {dep[c].median():+.2f}%)"
              for c in cols) + ".", "",
          "Bridging adds a few px per gap: the gap pixels are "
          f"{per_image['gap px share of skeleton %'].min():.2f} to {per_image['gap px share of skeleton %'].max():.2f}% "
          "of the skeleton. Its effect on roots comes through connectivity: a bridged thread can reach a lacuna",
          "node, or two attachment points can merge. Ring 30 px and field density follow the added pixels.", "",
          "## Crops", "",
          "`S2_bridges_<image>.png`: one tile per bridge, a 48 px square at 4x centred on the gap; skeleton white,",
          "the bridge pixels sky blue (the gap as drawn into the mask before re-skeletonization).", ""]
    C.write_text(K.OUT / "S2_bridging.md", "\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    K.OUT.mkdir(parents=True, exist_ok=True)
    ok = C.run_item("S2", item_s2)
    sys.exit(0 if ok else 1)
