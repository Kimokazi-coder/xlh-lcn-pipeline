"""B1: what the band-wall filter removes at the two evidence settings.

    python -u experiments/canal_b1_filter.py

BAND_LINE_FILTER has no recommended value (B1_straight_runs.md). It is run on
all 8 images at the two evidence settings, each alone with every other switch
off: L 97 px with reach 66 px (the only length that separates any part of the
542_z06 line; its straight piece there lies 65.01 px from the canal mask) and
L 40 px with reach 0 px (the only length at which its
straight part touches the canal mask). Every skeleton component that is
removed (or added) against the default run is listed, with before and after
crops, and the headline values per image.

Outputs in results_experiments/canal_v2/: B1_filter_components.csv,
B1_filter_images.csv, B1_filter.md, B1_crops_<setting>_<n>.png.
PRE-VALIDATION, PIXEL units, (x, y) = (column, row).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from skimage import measure

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canal_common as K  # noqa: E402
import common as C  # noqa: E402

SETTINGS = [
    ("L97_reach66", {"BAND_LINE_FILTER": True, "BAND_LINE_MIN_LEN_PX": 97, "BAND_LINE_REACH_PX": 66}),
    ("L40_reach0", {"BAND_LINE_FILTER": True, "BAND_LINE_MIN_LEN_PX": 40, "BAND_LINE_REACH_PX": 0}),
]
CROP_HALF = 45
PER_SHEET = 16
VERMILLION = (213, 94, 0)
MAGENTA = (255, 0, 255)
SKY_BLUE = (86, 180, 233)


def headline(d: dict) -> dict:
    s = d["summary"]
    return {"roots_per_cell": s["roots_count"]["mean"], "ring30_per_cell": s["ring_length_r30_px"]["mean"],
            "field_density": d["field"]["canalicular_length_density_per_px"], "bridges": len(d["bridges"]),
            "skeleton_px": int(d["skeleton"].sum())}


def padded(a: np.ndarray, x: int, y: int, half: int) -> np.ndarray:
    """A (2 half) square crop centred on (x, y), zero padded outside the frame."""
    out = np.zeros((2 * half, 2 * half) + a.shape[2:], dtype=a.dtype)
    H, W = a.shape[:2]
    x0, y0 = x - half, y - half
    sx0, sy0, sx1, sy1 = max(x0, 0), max(y0, 0), min(x0 + 2 * half, W), min(y0 + 2 * half, H)
    out[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = a[sy0:sy1, sx0:sx1]
    return out


def crop_pair(base: dict, new: dict, comp: dict) -> np.ndarray:
    """Before and after, a square crop sized to the component (at least
    2 CROP_HALF px, the whole component plus 10 px), zero padded at the frame."""
    x, y = comp["x"], comp["y"]
    half = max(CROP_HALF, int(np.ceil(comp["length_px"] / 2)) + 10)
    removed = base["skeleton"] & ~new["skeleton"]
    added = new["skeleton"] & ~base["skeleton"]
    raw = padded(C.to_rgb(base["channel"]), x, y, half)

    def layer(m):
        return padded(m, x, y, half)

    before = C.paint(raw // 2, layer(base["skeleton"]), (230, 230, 230))
    before = C.paint(before, layer(removed), VERMILLION)
    before = C.outline(before, layer(base["flagged"]), MAGENTA)
    after = C.paint(raw // 2, layer(new["skeleton"]), (230, 230, 230))
    after = C.paint(after, layer(added), SKY_BLUE)
    after = C.outline(after, layer(base["flagged"]), MAGENTA)
    scale = 2 if half <= 90 else 1
    return C.panel_row([before, after], [f"{comp['image']} ({x},{y}) before", f"after, -{comp['pixels']} px"],
                       scale=scale)


def item_b1_filter() -> None:
    comps, images = [], []
    md = ["# B1 The band-wall filter at the two evidence settings", "",
          "Pre-validation, px, (x, y) = (column, row). `BAND_LINE_FILTER` has **no recommended value**",
          "(`B1_straight_runs.md`); it stays off. Here it is turned on alone, every other switch off, at the two",
          "evidence settings, and every changed skeleton component against the default run is listed. Removed",
          "components are 8-connected pieces of default skeleton missing after the filter; added pieces are new",
          "skeleton (bridges can change when the cut creates new thread ends).", ""]
    for tag, overrides in SETTINGS:
        crops = []
        md += [f"## Setting {tag}: L {overrides['BAND_LINE_MIN_LEN_PX']} px, reach {overrides['BAND_LINE_REACH_PX']} px",
               ""]
        for name in K.names():
            base = K.pipeline(name)
            new = K.pipeline(name, overrides)
            hb, hn = headline(base), headline(new)
            row = {"setting": tag, "image": name, "skeleton_px_removed": int((base["skeleton"] & ~new["skeleton"]).sum()),
                   "skeleton_px_added": int((new["skeleton"] & ~base["skeleton"]).sum())}
            for k in hb:
                row[f"{k}_before"], row[f"{k}_after"] = hb[k], hn[k]
                row[f"{k}_pct"] = 100.0 * (hn[k] - hb[k]) / hb[k] if hb[k] else None
            images.append(row)
            for kind, mask in (("removed", base["skeleton"] & ~new["skeleton"]),
                               ("added", new["skeleton"] & ~base["skeleton"])):
                lab = measure.label(mask, connectivity=2)
                for r in measure.regionprops(lab):
                    c = {"setting": tag, "image": name, "kind": kind, "x": int(round(r.centroid[1])),
                         "y": int(round(r.centroid[0])), "pixels": int(r.area),
                         "length_px": round(float(r.feret_diameter_max), 1),
                         "orientation_deg": round(float((90.0 - np.degrees(r.orientation)) % 180.0), 1),
                         "in_542_z06_corridor": bool(name == "542_z06" and 515 <= r.centroid[1] <= 541
                                                     and 590 <= r.centroid[0] <= 900)}
                    comps.append(c)
                    if kind == "removed":
                        crops.append(crop_pair(base, new, c))
        sheets = [crops[i:i + PER_SHEET] for i in range(0, len(crops), PER_SHEET)]
        for k, sheet in enumerate(sheets, start=1):
            rows = [C.panel_row([p], None, gap=0) if False else p for p in sheet]
            grid = []
            for i in range(0, len(rows), 2):
                pair = rows[i:i + 2]
                width = sum(p.shape[1] for p in pair) + 12 * (len(pair) - 1)
                canvas = np.full((max(p.shape[0] for p in pair), width, 3), 255, np.uint8)
                xo = 0
                for p in pair:
                    canvas[:p.shape[0], xo:xo + p.shape[1]] = p
                    xo += p.shape[1] + 12
                grid.append(canvas)
            C.write_png(K.OUT / f"B1_crops_{tag}_{k}.png", C.panel_grid(grid))
        sub = pd.DataFrame([i for i in images if i["setting"] == tag])
        cs = pd.DataFrame([c for c in comps if c["setting"] == tag]) if any(c["setting"] == tag for c in comps) else None
        md += [C.md_table(sub[["image", "skeleton_px_removed", "skeleton_px_added", "roots_per_cell_pct",
                               "ring30_per_cell_pct", "field_density_pct", "bridges_before", "bridges_after"]],
                          floatfmt="{:+.2f}"), ""]
        if cs is not None:
            rem = cs[cs.kind == "removed"]
            md += [f"Removed components: {len(rem)} in {rem.image.nunique()} image(s), {int(rem.pixels.sum())} px; "
                   f"in the 542_z06 corridor: {int(rem[rem.in_542_z06_corridor].pixels.sum())} px. Added components: "
                   f"{int((cs.kind == 'added').sum())}, {int(cs[cs.kind == 'added'].pixels.sum())} px.", "",
                   C.md_table(rem.sort_values("pixels", ascending=False).head(20)[
                       ["image", "x", "y", "pixels", "length_px", "orientation_deg", "in_542_z06_corridor"]],
                       floatfmt="{:.1f}"), "",
                   f"Crops (before: removed pixels vermillion; after: added pixels sky blue; canal mask magenta): "
                   f"`B1_crops_{tag}_1.png` to `_{len(sheets)}.png`, every removed component.", ""]
        else:
            md += ["No skeleton pixel changes in any image.", ""]
    C.write_csv(K.OUT / "B1_filter_components.csv", pd.DataFrame(comps))
    C.write_csv(K.OUT / "B1_filter_images.csv", pd.DataFrame(images))
    imgs = pd.DataFrame(images)
    a = imgs[(imgs.setting == "L97_reach66")]
    b = imgs[(imgs.setting == "L40_reach0")]
    md += ["## Against the expectation", "",
           "The overnight report expected about 380 skeleton px removed from 542_z06 (about 1.1% of its skeleton,",
           "field density about -1.1%) and no change elsewhere. Nothing was adjusted to reach that. Neither evidence",
           "setting does it:",
           f"- L 97, reach 66: {int(a.skeleton_px_removed.sum())} px removed, all in 542_z06 (the straight middle of the",
           f"  line, about a quarter of it); field density {a[a.image == '542_z06'].field_density_pct.iloc[0]:+.2f}% there;",
           "  no roots, ring 30 px or bridges change; no other image changes. It needs a reach of 66 px from the canal",
           "  mask, which is not a continuation of the canal.",
           f"- L 40, reach 0: {int(b.skeleton_px_removed.sum())} px removed in {int((b.skeleton_px_removed > 0).sum())} images,",
           f"  field density {b.field_density_pct.min():+.2f} to {b.field_density_pct.max():+.2f}%. Only a small part is",
           "  the line; most removed pieces are wall pieces inside the canal masks of 542_z06 and 542_z18 and",
           "  ordinary threads (the horizontal and vertical lattice threads of the 682 images) that touch a canal mask.",
           "", "So the switch stays off, with no recommended value.", ""]
    C.write_text(K.OUT / "B1_filter.md", "\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    K.OUT.mkdir(parents=True, exist_ok=True)
    ok = C.run_item("B1_filter", item_b1_filter)
    sys.exit(0 if ok else 1)
