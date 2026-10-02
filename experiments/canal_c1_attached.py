"""C1: attached ring length, per image and per lacuna, with crops.

    python -u experiments/canal_c1_attached.py

Reads the new pipeline columns ring_attached_length_r30_px and _r60_px (src/
canaliculi.py, appended on branch canaliculi-v2) from a run of the default
pipeline, and reports per image the share of ring length that is attached
(threads reaching within LACUNA_ATTACH_GAP_PX of the lacuna) and its range.
Crops of the 3 interior lacunae with the most passing length show attached
ring pixels in vermillion and passing ring pixels in sky blue.

Outputs in results_experiments/canal_v2/: C1_attached_ring.csv, .md,
C1_crops.png. PRE-VALIDATION, PIXEL units, (x, y) = (column, row).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from skimage import measure, segmentation

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canal_common as K  # noqa: E402
import common as C  # noqa: E402
import canaliculi  # noqa: E402

VERMILLION = (213, 94, 0)
SKY_BLUE = (86, 180, 233)
CYAN = (0, 255, 255)
CROP_HALF = 90


def ring_parts(d: dict, lacuna_id: int, radius: int = 30) -> tuple[np.ndarray, np.ndarray]:
    """(attached, passing) ring pixels of one lacuna, by the pipeline's rule."""
    dist, nearest = canaliculi.nearest_lacuna_map(d["lacuna_id_map"])
    ring = d["skeleton"] & (dist <= radius) & (nearest == lacuna_id)
    labels = measure.label(ring, connectivity=2)
    near = ring & (dist <= canaliculi.LACUNA_ATTACH_GAP_PX)
    ids = np.unique(labels[near])
    attached = np.isin(labels, ids[ids > 0])
    return attached, ring & ~attached


def crop_panel(d: dict, row: dict) -> np.ndarray:
    lid = row["lacuna_id"]
    attached, passing = ring_parts(d, lid)
    if int(attached.sum()) != row["ring_attached_length_r30_px"]:
        raise AssertionError(f"{d['short']} L{lid}: crop attached px differ from the pipeline column")
    x, y = int(round(row["x"])), int(round(row["y"]))
    raw, (x0, y0) = C.crop(C.to_rgb(d["channel"]), x, y, CROP_HALF)
    sl = (slice(y0, y0 + raw.shape[0]), slice(x0, x0 + raw.shape[1]))
    over = C.paint(raw // 2, d["skeleton"][sl], (150, 150, 150))
    over = C.paint(over, passing[sl], SKY_BLUE)
    over = C.paint(over, attached[sl], VERMILLION)
    over = C.outline(over, d["lacuna_id_map"][sl] == lid, CYAN)
    dist, nearest = canaliculi.nearest_lacuna_map(d["lacuna_id_map"])
    region = (dist <= 30) & (nearest == lid)
    edge = segmentation.find_boundaries(region[sl], mode="inner") & ~(d["lacuna_id_map"][sl] > 0)
    over[edge & (np.indices(edge.shape).sum(axis=0) % 4 < 2)] = (255, 255, 255)
    title = (f"{d['short']} L{lid} ({x},{y}): ring30 {row['ring30']} px, attached {row['ring_attached_length_r30_px']}, "
             f"passing {row['ring30'] - row['ring_attached_length_r30_px']}")
    return C.panel_row([raw, over], [title, "vermillion attached, blue passing, grey other"], scale=3)


def item_c1() -> None:
    out_csv = K.OUT / "C1_attached_ring.csv"
    rows, data = [], {}
    for name in K.names():
        d = K.pipeline(name)
        data[name] = d
        for lr, cr in zip(d["lacuna_rows"], d["cell_rows"]):
            for r in (30, 60):
                assert cr[f"ring_attached_length_r{r}_px"] <= cr[f"ring_length_r{r}_px"]
            rows.append({"image": name, "lacuna_id": cr["lacuna_id"], "x": round(lr["centroid_col_px"]),
                         "y": round(lr["centroid_row_px"]), "on_border": cr["on_border"],
                         "roots": cr["roots_count"], "ring30": cr["ring_length_r30_px"],
                         "ring_attached_length_r30_px": cr["ring_attached_length_r30_px"],
                         "ring60": cr["ring_length_r60_px"],
                         "ring_attached_length_r60_px": cr["ring_attached_length_r60_px"]})
    df = pd.DataFrame(rows)
    df["share30"] = df.ring_attached_length_r30_px / df.ring30.replace(0, np.nan)
    df["share60"] = df.ring_attached_length_r60_px / df.ring60.replace(0, np.nan)
    C.write_csv(out_csv, df)
    it = df[~df.on_border.astype(bool)]
    summ = []
    for name, g in it.groupby("image", sort=False):
        summ.append({"image": name, "interior lacunae": len(g),
                     "attached / ring 30 (sum)": g.ring_attached_length_r30_px.sum() / g.ring30.sum(),
                     "per cell min": g.share30.min(), "per cell median": g.share30.median(),
                     "per cell max": g.share30.max(),
                     "attached / ring 60 (sum)": g.ring_attached_length_r60_px.sum() / g.ring60.sum(),
                     "ring30 mean": g.ring30.mean(), "attached30 mean": g.ring_attached_length_r30_px.mean()})
    sdf = pd.DataFrame(summ)
    pooled30 = it.ring_attached_length_r30_px.sum() / it.ring30.sum()
    pooled60 = it.ring_attached_length_r60_px.sum() / it.ring60.sum()
    rho = it[["roots", "ring30", "ring_attached_length_r30_px"]].corr(method="spearman")

    # Crops: the 3 interior lacunae with the most passing length, one per image if possible.
    it2 = it.assign(passing=it.ring30 - it.ring_attached_length_r30_px).sort_values("passing", ascending=False)
    picks, seen = [], set()
    for r in it2.itertuples():
        if r.image not in seen:
            picks.append(r)
            seen.add(r.image)
        if len(picks) == 3:
            break
    panels = [crop_panel(data[p.image], p._asdict()) for p in picks]
    C.write_png(K.OUT / "C1_crops.png", C.panel_grid(panels))

    md = ["# C1 Attached ring length", "",
          "Pre-validation, px. New per-lacuna columns `ring_attached_length_r30_px` and `ring_attached_length_r60_px`",
          "(src/canaliculi.py, appended after every existing column). The ring of a lacuna is exactly the pixel set of",
          "`ring_length_rR_px` (skeleton px within R px of the lacuna masks whose nearest lacuna is this one). Its",
          "8-connected components are taken within that ring only. A component is attached if one of its pixels lies",
          f"within {canaliculi.LACUNA_ATTACH_GAP_PX} px (`LACUNA_ATTACH_GAP_PX`, the constant the roots use) of the",
          "lacuna masks. The attached length is the pixel count of attached components; the rest is passing length.",
          "Attached is at most ring length for every lacuna (asserted in the pipeline and here).", "",
          "## Share of ring length that is attached, interior lacunae", "",
          C.md_table(sdf, floatfmt="{:.3f}"), "",
          f"Pooled over all {len(it)} interior lacunae: attached / ring 30 = {pooled30:.3f}, attached / ring 60 = "
          f"{pooled60:.3f}. Per-cell share at 30 px ranges from {it.share30.min():.3f} to {it.share30.max():.3f}.", "",
          "Spearman correlations over interior lacunae (roots, ring 30, attached ring 30):", "",
          C.md_table(rho.reset_index().rename(columns={"index": "measure"}), floatfmt="{:.3f}"), "",
          "## Crops", "",
          "`C1_crops.png`: the 3 interior lacunae with the most passing length (one per image), raw and overlay at 3x.",
          "Vermillion: attached ring pixels. Sky blue: passing ring pixels. Grey: other skeleton. Cyan: lacuna outline.",
          "White dashes: edge of the 30 px ring region. Per-lacuna values: `C1_attached_ring.csv`.", "",
          "Shown: " + "; ".join(f"{p.image} L{p.lacuna_id} ({p.x},{p.y}), passing {p.passing} of {p.ring30} px"
                                for p in picks) + ".", ""]
    C.write_text(K.OUT / "C1_attached_ring.md", "\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    K.OUT.mkdir(parents=True, exist_ok=True)
    ok = C.run_item("C1", item_c1)
    sys.exit(0 if ok else 1)
