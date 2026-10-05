"""C3: Sholl crossings per lacuna, their relation to roots and area, crops.

    python -u experiments/canal_c3_sholl.py

Reads the new pipeline columns sholl_crossings_r10, _r20, _r30 (src/
canaliculi.py) from a default run, asserts they are non-negative integers,
and reports Spearman correlations with roots_count and lacuna area, and how
often a cell has fewer crossings at 30 px than at 10 px. Crops of two cells
show the three bands and the skeleton components inside them.

Outputs in results_experiments/canal_v2/: C3_sholl.csv, .md, C3_crops.png.
PRE-VALIDATION, PIXEL units, (x, y) = (column, row).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from skimage import measure

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canal_common as K  # noqa: E402
import common as C  # noqa: E402
import canaliculi  # noqa: E402

BAND_COLOURS = {10: (230, 159, 0), 20: (86, 180, 233), 30: (0, 158, 115)}  # Okabe-Ito orange, sky blue, green
ROOT_MAGENTA = (255, 0, 255)
CROP_HALF = 60


def crop_panel(d: dict, row: dict) -> np.ndarray:
    lid = row["lacuna_id"]
    dist, nearest = canaliculi.nearest_lacuna_map(d["lacuna_id_map"])
    x, y = int(round(row["x"])), int(round(row["y"]))
    raw, (x0, y0) = C.crop(C.to_rgb(d["channel"]), x, y, CROP_HALF)
    sl = (slice(y0, y0 + raw.shape[0]), slice(x0, x0 + raw.shape[1]))
    over = C.paint(raw // 3, d["skeleton"][sl], (140, 140, 140))
    counts = []
    for r, colour in BAND_COLOURS.items():
        band_area = ((dist >= r - quantification.SHOLL_HALF_WIDTH_PX) & (dist < r + quantification.SHOLL_HALF_WIDTH_PX)
                     & (nearest == lid))
        over = C.paint(over, band_area[sl] & ~d["skeleton"][sl], colour, alpha=0.7)
        hits = band_area & d["skeleton"]
        n = int(measure.label(hits, connectivity=2).max())
        assert n == row[f"sholl_r{r}"], (d["short"], lid, r, n)
        over = C.paint(over, hits[sl], (255, 255, 255))
        counts.append(f"r{r} {n}")
    over = C.outline(over, d["lacuna_id_map"][sl] == lid, (0, 255, 255))
    title = f"{d['short']} L{lid} ({x},{y}): roots {row['roots']}, crossings " + ", ".join(counts)
    return C.panel_row([raw, over], [title, "bands 10/20/30 px tinted; white: skeleton in a band"], scale=4)


def item_c3() -> None:
    rows, data = [], {}
    for name in K.names():
        d = K.pipeline(name)
        data[name] = d
        for lr, cr in zip(d["lacuna_rows"], d["cell_rows"]):
            for r in quantification.SHOLL_RADII_PX:
                v = cr[f"sholl_crossings_r{r}"]
                assert isinstance(v, int) and v >= 0, (name, cr["lacuna_id"], r, v)
            rows.append({"image": name, "lacuna_id": cr["lacuna_id"], "x": round(lr["centroid_col_px"]),
                         "y": round(lr["centroid_row_px"]), "on_border": cr["on_border"], "area_px2": lr["area_px2"],
                         "roots": cr["roots_count"], **{f"sholl_r{r}": cr[f"sholl_crossings_r{r}"]
                                                        for r in quantification.SHOLL_RADII_PX}})
    df = pd.DataFrame(rows)
    C.write_csv(K.OUT / "C3_sholl.csv", df)
    it = df[~df.on_border.astype(bool)]
    corr = []
    for r in quantification.SHOLL_RADII_PX:
        a, pa = spearmanr(it[f"sholl_r{r}"], it.roots)
        b, pb = spearmanr(it[f"sholl_r{r}"], it.area_px2)
        corr.append({"crossings at": f"{r} px", "mean": it[f"sholl_r{r}"].mean(), "median": it[f"sholl_r{r}"].median(),
                     "min": it[f"sholl_r{r}"].min(), "max": it[f"sholl_r{r}"].max(),
                     "rho with roots": a, "p roots": pa, "rho with area": b, "p area": pb})
    ra, _ = spearmanr(it.roots, it.area_px2)
    corr.append({"crossings at": "roots_count", "mean": it.roots.mean(), "median": it.roots.median(),
                 "min": it.roots.min(), "max": it.roots.max(), "rho with roots": 1.0, "p roots": 0.0,
                 "rho with area": ra, "p area": spearmanr(it.roots, it.area_px2)[1]})
    cdf = pd.DataFrame(corr)
    fewer = int((it.sholl_r30 < it.sholl_r10).sum())
    equal = int((it.sholl_r30 == it.sholl_r10).sum())
    more = int((it.sholl_r30 > it.sholl_r10).sum())
    per_image = it.groupby("image", sort=False).agg(cells=("roots", "size"), roots=("roots", "mean"),
                                                    sholl_r10=("sholl_r10", "mean"), sholl_r20=("sholl_r20", "mean"),
                                                    sholl_r30=("sholl_r30", "mean")).reset_index()
    per_image["r30 below r10"] = [int((g.sholl_r30 < g.sholl_r10).sum()) for _n, g in it.groupby("image", sort=False)]

    # Crops: the interior cell closest to the median roots in 543-2, and the cell with the largest r10 to r30 drop.
    m = it[it.image == "543-2"]
    m = m[(m.x >= 100) & (m.y >= 100) & (m.x <= 923) & (m.y <= 923)]
    a = m.assign(dev=(m.roots - it[it.image == "543-2"].roots.median()).abs()).sort_values(["dev", "lacuna_id"])
    b = it.assign(drop=it.sholl_r10 - it.sholl_r30)
    b = b[~((b.image == a.iloc[0]["image"]) & (b.lacuna_id == a.iloc[0]["lacuna_id"]))]
    b = b.sort_values(["drop", "lacuna_id"], ascending=[False, True])
    picks = [a.iloc[0], b.iloc[0]]
    panels = [crop_panel(data[p["image"]], p.to_dict()) for p in picks]
    C.write_png(K.OUT / "C3_crops.png", C.panel_grid(panels))

    md = ["# C3 Sholl crossings", "",
          "Pre-validation, px. New per-lacuna columns `sholl_crossings_r10`, `_r20`, `_r30` (interior means in the summary).",
          "The band of a lacuna at radius $R$ is the part of its nearest-lacuna partition whose distance to the lacuna",
          f"masks lies in $[R - {quantification.SHOLL_HALF_WIDTH_PX}, R + {quantification.SHOLL_HALF_WIDTH_PX})$, inside the frame.",
          "The count is the number of 8-connected skeleton components inside the band. It uses no graph, no cleanup,",
          "no attach gap and no ownership; it does use the skeleton, so the cuts and the bridging still reach it.",
          "",
          "Limits: a thread running along the band counts once however long it is; a branch point inside the band",
          "joins two threads into one component; a thread that leaves the band and comes back counts twice; near",
          "another lacuna the band is cut by the partition, and near the frame by the frame. The band is 1.5 px wide,",
          r"wider than the longest step between neighbouring pixels ($\sqrt{2}$), so a thread cannot cross it",
          "unseen.", "",
          f"All counts are non-negative integers (asserted). Interior lacunae: n = {len(it)}.", "",
          "## Distribution and Spearman correlations (interior lacunae, pooled)", "",
          C.md_table(cdf, floatfmt="{:.3f}"), "",
          "## Per image (means over interior lacunae)", "",
          C.md_table(per_image, floatfmt="{:.2f}"), "",
          "## Fewer crossings further out", "",
          f"Crossings at 30 px below crossings at 10 px: {fewer} of {len(it)} cells "
          f"({100 * fewer / len(it):.0f}%); equal: {equal}; more: {more}. Fewer crossings further out mean threads",
          "that merge or end between 10 and 30 px; more mean threads that branch or enter the band from the side.", "",
          "## Crops", "",
          "`C3_crops.png` at 4x: " + "; ".join(f"{p['image']} L{p['lacuna_id']} ({p['x']},{p['y']})" for p in picks)
          + ". The first is the 543-2 cell closest to the median roots among cells at least 100 px from the frame; the second has the largest drop from 10 to",
          "30 px. Bands tinted (10 px orange, 20 px sky blue, 30 px green); white: skeleton pixels in a band; grey: other",
          "skeleton; cyan: the lacuna. The counts in the crop equal the pipeline columns (asserted).",
          "Per-lacuna values: `C3_sholl.csv`.", ""]
    C.write_text(K.OUT / "C3_sholl.md", "\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    K.OUT.mkdir(parents=True, exist_ok=True)
    ok = C.run_item("C3", item_c3)
    sys.exit(0 if ok else 1)
