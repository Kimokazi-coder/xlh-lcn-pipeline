"""Task 4.1: size confound in the per-cell measures.

    python -u experiments/task4_size.py 4.1

From the cached default results only (no pipeline rerun). Per lacuna:
perimeter; ring area at 30 and 60 px (in-frame pixels of the
nearest-lacuna partition within r of the body, other lacunae excluded);
the in-frame fraction of the full annulus (the annulus of radius r around
this lacuna alone, in an unbounded plane); ring density L_r / A_r; roots
per 100 px of perimeter. Spearman correlations against lacuna area:
pooled, within each image, and between images (image means against median
area, n = 8).

Outputs in results_experiments/task4/. PRE-VALIDATION, PIXEL units,
(x, y) = (column, row).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import ndimage as ndi
from scipy.stats import spearmanr
from skimage import measure

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
import canaliculi  # noqa: E402

OUT = C.OUT_ROOT / "task4"
RADII = (30, 60)
IN_FRAME_MIN = 0.9  # from the task text


def per_lacuna_table() -> pd.DataFrame:
    path = OUT / "4.1_per_lacuna.csv"
    if path.is_file():
        return pd.read_csv(path)
    rows = []
    for p in C.IMAGE_PATHS:
        d = C.load(p)
        idm = d["lacuna_id_map"]
        dist, nearest = canaliculi.nearest_lacuna_map(idm)
        regs = {r.label: r for r in measure.regionprops(idm)}
        H, W = idm.shape
        for lrow, crow in zip(d["lacuna_rows"], d["cell_rows"]):
            lid = lrow["lacuna_id"]
            r = regs[lid]
            row = {"image": d["short"], "lacuna_id": lid, "x": lrow["centroid_col_px"], "y": lrow["centroid_row_px"],
                   "on_border": lrow["on_border"], "area_px2": lrow["area_px2"], "perimeter_px": float(r.perimeter),
                   "roots": crow["roots_count"], "ring30_px": crow["ring_length_r30_px"],
                   "ring60_px": crow["ring_length_r60_px"], "owned_length_px": crow["owned_length_px"],
                   "edge_count": crow["edge_count"]}
            for rad in RADII:
                ring = (dist > 0) & (dist <= rad) & (nearest == lid)
                row[f"ring_area{rad}_px2"] = int(ring.sum())
                # Full annulus around this lacuna alone, unbounded plane.
                pad = rad + 2
                r0, c0, r1, c1 = r.bbox
                sub = np.zeros((r1 - r0 + 2 * pad, c1 - c0 + 2 * pad), dtype=bool)
                sub[pad:pad + r1 - r0, pad:pad + c1 - c0] = r.image
                e = ndi.distance_transform_edt(~sub)
                ann = (e > 0) & (e <= rad)
                rr, cc = np.nonzero(ann)
                rr = rr + r0 - pad
                cc = cc + c0 - pad
                inside = (rr >= 0) & (rr < H) & (cc >= 0) & (cc < W)
                row[f"full_annulus{rad}_px2"] = int(ann.sum())
                row[f"in_frame_fraction{rad}"] = float(inside.mean())
                row[f"ring_density{rad}"] = row[f"ring{rad}_px"] / row[f"ring_area{rad}_px2"] if row[f"ring_area{rad}_px2"] else float("nan")
            row["roots_per_100px_perimeter"] = 100.0 * row["roots"] / row["perimeter_px"]
            rows.append(row)
        print(d["short"], "done")
    df = pd.DataFrame(rows)
    C.write_csv(path, df)
    return df


MEASURES = [
    ("roots", 30), ("roots_per_100px_perimeter", 30),
    ("ring30_px", 30), ("ring_density30", 30), ("ring_area30_px2", 30),
    ("ring60_px", 60), ("ring_density60", 60), ("ring_area60_px2", 60),
    ("perimeter_px", 30),
]


def rho(x, y) -> tuple[float, float, int]:
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 4:
        return float("nan"), float("nan"), int(ok.sum())
    r, p = spearmanr(x[ok], y[ok])
    return float(r), float(p), int(ok.sum())


def item_4_1() -> None:
    df = per_lacuna_table()
    interior = df[~df.on_border.astype(bool)]
    rows = []
    for subset_name, frame_ok in (("interior", None), ("interior, in-frame >= 0.9", IN_FRAME_MIN)):
        for m, rad in MEASURES:
            sub = interior if frame_ok is None else interior[interior[f"in_frame_fraction{rad}"] >= frame_ok]
            r, p, n = rho(sub["area_px2"].to_numpy(float), sub[m].to_numpy(float))
            within = []
            for img, g in sub.groupby("image"):
                rr, _pp, nn = rho(g["area_px2"].to_numpy(float), g[m].to_numpy(float))
                within.append((img, rr, nn))
            wr = np.array([w[1] for w in within], dtype=float)
            # Between images: image mean of the measure against median area.
            agg = sub.groupby("image").agg(med_area=("area_px2", "median"), mean_m=(m, "mean"))
            br, bp, bn = rho(agg["med_area"].to_numpy(float), agg["mean_m"].to_numpy(float))
            row = {"subset": subset_name, "measure": m, "pooled_rho": r, "pooled_p": p, "pooled_n": n,
                   "within_median_rho": float(np.nanmedian(wr)) if wr.size else float("nan"),
                   "within_min_rho": float(np.nanmin(wr)) if wr.size else float("nan"),
                   "within_max_rho": float(np.nanmax(wr)) if wr.size else float("nan"),
                   "within_positive": int((wr > 0).sum()), "within_images": int(np.isfinite(wr).sum()),
                   "between_images_rho": br, "between_images_p": bp, "between_images_n": bn}
            for img, rr, nn in within:
                row[f"rho_{img}"] = rr
            rows.append(row)
    cdf = pd.DataFrame(rows)
    C.write_csv(OUT / "4.1_correlations.csv", cdf)

    # The claim as stated: image-level roots per cell and ring 30 against
    # median lacuna area, from the pipeline's own summary numbers.
    claim = []
    for p in C.IMAGE_PATHS:
        d = C.load(p)
        claim.append({"image": d["short"], "median_area_px2": d["lacuna_summary"]["area_px2"]["median"],
                      "roots_per_cell": d["cell_summary"]["roots_count"]["mean"],
                      "ring30_per_cell": d["cell_summary"]["ring_length_r30_px"]["mean"],
                      "field_density": d["field"]["canalicular_length_density_per_px"]})
    claim = pd.DataFrame(claim)
    cr = {k: spearmanr(claim.median_area_px2, claim[k]) for k in ("roots_per_cell", "ring30_per_cell", "field_density")}
    # Image-level means of the normalised measures.
    norm = interior.groupby("image").agg(median_area=("area_px2", "median"),
                                         roots_per_100px=("roots_per_100px_perimeter", "mean"),
                                         ring_density30=("ring_density30", "mean"),
                                         ring_density60=("ring_density60", "mean")).reset_index()
    nr = {k: spearmanr(norm.median_area, norm[k]) for k in ("roots_per_100px", "ring_density30", "ring_density60")}

    frame = interior[["in_frame_fraction30", "in_frame_fraction60"]].describe().T
    lines = ["# 4.1 Size confound", "",
             "Pre-validation, px. Per-cell measures against lacuna area. Interior lacunae only (n = "
             f"{len(interior)} over 8 images), as every pipeline mean. The 8 images are probably sections of",
             "3 fields (task 6.1), so the same cell can appear in several images: the pooled n overstates the",
             "number of independent cells, and the between-image n = 8 is closer to 3 independent fields.", "",
             "## The claim: image-level roots and ring 30 rise with median lacuna area", "",
             C.md_table(claim, floatfmt="{:.4g}"), "",
             f"Spearman, n = 8: roots per cell rho = {cr['roots_per_cell'][0]:.3f} (p = {cr['roots_per_cell'][1]:.3f}); "
             f"ring 30 per cell rho = {cr['ring30_per_cell'][0]:.3f} (p = {cr['ring30_per_cell'][1]:.3f}); "
             f"field density rho = {cr['field_density'][0]:.3f} (p = {cr['field_density'][1]:.3f}).", "",
             "Image-level means of the normalised measures against median area, n = 8: "
             + "; ".join(f"{k} rho = {v[0]:.3f} (p = {v[1]:.3f})" for k, v in nr.items()) + ".", "",
             "## Per-lacuna Spearman correlations against area", "",
             "pooled: all interior lacunae together. within: one rho per image (median, min, max, and how",
             "many of the images are positive). between: image mean of the measure against the image's",
             "median area.", "",
             C.md_table(cdf[["subset", "measure", "pooled_rho", "pooled_p", "pooled_n", "within_median_rho",
                             "within_min_rho", "within_max_rho", "within_positive", "within_images",
                             "between_images_rho", "between_images_p"]], floatfmt="{:.3f}"), "",
             "Within-image rho per image:", "",
             C.md_table(cdf[["subset", "measure"] + [c for c in cdf.columns if c.startswith("rho_")]], floatfmt="{:.2f}"),
             "", "In-frame fraction of the full annulus over interior lacunae:", "",
             C.md_table(frame.reset_index().rename(columns={"index": "radius"}), floatfmt="{:.3f}"), ""]
    C.write_text(OUT / "4.1_size_confound.md", "\n".join(lines))
    print("\n".join(lines))


ITEMS = {"4.1": item_4_1}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    item = sys.argv[1]
    ok = C.run_item(item, ITEMS[item])
    sys.exit(0 if ok else 1)
