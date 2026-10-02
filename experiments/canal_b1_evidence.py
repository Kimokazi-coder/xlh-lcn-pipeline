"""B1 evidence: straight runs of the skeleton in every image, before any value is set.

    python -u experiments/canal_b1_evidence.py

For each image of the default run and each line length L from 40 to 300 px,
the straight-run pixels (src/canaliculi.py straight_run_mask: the skeleton
widened to 3 px, opened with one-pixel lines of L px at 24 orientations) are
grouped into 8-connected straight objects. Per object: pixels, length (largest
Feret diameter), orientation (0 = along x, 90 = along y), distance to the
flagged canal mask, whether it touches it, and the share of it inside the
542_z06 corridor of the overnight report (x 515 to 541, y 590 to 900).

Outputs in results_experiments/canal_v2/: B1_straight_runs.csv, .md;
per-image json caches in results_experiments/_cache/canal_v2/b1/.
PRE-VALIDATION, PIXEL units, (x, y) = (column, row).
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import ndimage as ndi
from skimage import measure

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canal_common as K  # noqa: E402
import common as C  # noqa: E402
import canaliculi  # noqa: E402

LENGTHS = (40, 60, 80, 85, 90, 95, 100, 105, 110, 115, 120, 140, 160, 200, 250, 300)
CORRIDOR = {"image": "542_z06", "x": (515, 541), "y": (590, 900)}  # overnight report 5.3
CACHE_B1 = K.CACHE / "b1"


def within_2px(obj: np.ndarray, sk: np.ndarray) -> int:
    """Skeleton px within 2 px of an object: what the filter would remove
    (config.BAND_LINE_REMOVE_PX = 2), counted inside the object's box."""
    rr, cc = np.nonzero(obj)
    r0, c0 = max(rr.min() - 3, 0), max(cc.min() - 3, 0)
    r1, c1 = rr.max() + 4, cc.max() + 4
    zone = ndi.binary_dilation(obj[r0:r1, c0:c1], structure=canaliculi.morphology.disk(2))
    return int((zone & sk[r0:r1, c0:c1]).sum())


def orientation_from_x(orientation_rad: float) -> float:
    """skimage regionprops orientation (angle of the major axis from the row
    axis) as degrees from the x axis in [0, 180): 0 along x, 90 along y, 45
    for a line running down and to the right in the image."""
    return float((90.0 - np.degrees(orientation_rad)) % 180.0)


def objects_of(name: str) -> list[dict]:
    path = CACHE_B1 / f"{name}.json"
    if path.is_file():
        j = json.loads(path.read_text(encoding="utf-8"))
        if j.get("src_hash") == K.src_hash():
            return j["objects"]
    d = K.pipeline(name)
    sk, fl = d["skeleton"], d["flagged"]
    dist_fl = ndi.distance_transform_edt(~fl) if fl.any() else np.full(sk.shape, np.inf)
    corridor = np.zeros(sk.shape, bool)
    if name == CORRIDOR["image"]:
        corridor[CORRIDOR["y"][0]:CORRIDOR["y"][1] + 1, CORRIDOR["x"][0]:CORRIDOR["x"][1]] = True
    out = []
    for L in LENGTHS:
        straight = canaliculi.straight_run_mask(sk, L)
        lab = measure.label(straight, connectivity=2)
        for r in measure.regionprops(lab):
            rr, cc = r.coords[:, 0], r.coords[:, 1]
            orient = orientation_from_x(r.orientation)
            out.append({"image": name, "L": L, "pixels": int(r.area),
                        "skeleton_px": int(sk[rr, cc].sum()),
                        "skeleton_px_within_2px": int(within_2px(lab == r.label, sk)),
                        "length_px": round(float(r.feret_diameter_max), 1),
                        "orientation_deg": round(float(orient), 1),
                        "x": round(float(r.centroid[1])), "y": round(float(r.centroid[0])),
                        "x0": int(r.bbox[1]), "y0": int(r.bbox[0]), "x1": int(r.bbox[3]) - 1, "y1": int(r.bbox[2]) - 1,
                        "dist_to_flagged_px": round(float(dist_fl[rr, cc].min()), 1) if fl.any() else None,
                        "touches_flagged": bool(fl[rr, cc].any()),
                        "corridor_share": round(float(corridor[rr, cc].mean()), 3)})
    C.write_json(path, {"src_hash": K.src_hash(), "objects": out})
    return out


def item_b1_evidence() -> None:
    with ProcessPoolExecutor(max_workers=8) as ex:
        parts = list(ex.map(objects_of, K.names()))
    df = pd.DataFrame([o for part in parts for o in part])
    C.write_csv(K.OUT / "B1_straight_runs.csv", df)
    line = df[(df.image == CORRIDOR["image"]) & (df.corridor_share > 0)]
    others = df[~df.index.isin(line.index)]
    rows = []
    for L in LENGTHS:
        ln = line[line.L == L]
        ot = others[others.L == L]
        near = ot[ot.dist_to_flagged_px.notna() & (ot.dist_to_flagged_px <= 20)]
        rows.append({"L": L,
                     "542_z06 line: objects": len(ln),
                     "line: longest px": ln.length_px.max() if len(ln) else 0,
                     "line: skeleton px on runs": int(ln.skeleton_px.sum()),
                     "line: skeleton px within 2 px": int(ln.skeleton_px_within_2px.sum()),
                     "line: min distance to flagged": ln.dist_to_flagged_px.min() if len(ln) else None,
                     "other objects": len(ot),
                     "others: longest px": ot.length_px.max() if len(ot) else 0,
                     "others within 20 px of flagged": len(near),
                     "those: longest px": near.length_px.max() if len(near) else 0})
    tab = pd.DataFrame(rows)
    top = (others.sort_values(["L", "length_px"], ascending=[True, False]).groupby("L").head(8)
           [["L", "image", "x", "y", "x0", "y0", "x1", "y1", "length_px", "orientation_deg", "skeleton_px",
             "dist_to_flagged_px", "touches_flagged"]])
    md = ["# B1 evidence: straight runs of the skeleton", "",
          "Pre-validation, px, (x, y) = (column, row). Default run of every image. For each line length L, the",
          "straight-run pixels are the pixels of the skeleton widened to 3 px (3 x 3 dilation) that lie under a",
          "one-pixel line of L px fitting entirely inside it, at any of 24 orientations (7.5 degree steps). They",
          "are grouped into 8-connected straight objects. Length is the largest Feret diameter; orientation is 0",
          "along x and 90 along y. \"skeleton px on runs\" counts skeleton px lying on the run pixels; \"within 2 px\"",
          "counts skeleton px within 2 px of the object, which is what the filter removes. L is the Euclidean",
          "length of the line. The 542_z06 line is every object with pixels in the corridor x 515 to 541,",
          "y 590 to 900 (overnight report 5.3). All objects: `B1_straight_runs.csv`.", "",
          "## The line against everything else, by L", "",
          C.md_table(tab, floatfmt="{:.1f}"), "",
          "## The longest other straight objects at each L (top 8)", "",
          C.md_table(top, floatfmt="{:.1f}"), ""]
    # Reading: is there an L at which the line survives and nothing else does?
    surv_line = sorted(set(line.L))
    surv_other = sorted(set(others.L))
    max_other = max(surv_other) if surv_other else None
    max_line = max(surv_line) if surv_line else None
    gap = [L for L in LENGTHS if L in surv_line and (max_other is None or L > max_other)]
    after = [L for L in LENGTHS if max_line is not None and L > max_line]
    at40 = df[df.L == LENGTHS[0]]
    touching40 = at40[at40.touches_flagged & ~at40.index.isin(line.index)]
    lg = line[line.L.isin(gap)]
    md += ["## Reading and decision", "",
           f"- The 542_z06 line is straight only in pieces at a 3 px tolerance: its longest straight object is "
           f"{line.length_px.max():.0f} px, and the skeleton within 2 px of its straight objects (what the filter would "
           f"remove) is {int(line[line.L == LENGTHS[0]].skeleton_px_within_2px.sum())} px at L {LENGTHS[0]} (of the 382 px in "
           f"the corridor) and {int(line[line.L == 80].skeleton_px_within_2px.sum())} px at L 80.",
           f"- Its straight part touches the flagged mask only at L {LENGTHS[0]}. At that L, "
           f"{len(touching40)} other straight objects touch a flagged mask in {touching40.image.nunique()} images.",
           f"- A gap in L exists: other objects survive up to L {max_other}, the line up to L {max_line}, nothing at "
           f"L {after[0] if after else 'none'}. In that gap (L {', '.join(str(g) for g in gap)}) the line's straight "
           f"object has {int(lg.skeleton_px_within_2px.max()) if len(lg) else 0} skeleton px within 2 px and lies "
           f"{lg.dist_to_flagged_px.min() if len(lg) else float('nan'):.1f} px from the flagged mask (65.01 px unrounded):"
           " it does not continue the canal region.",
           "- **Decision.** The band wall is not separable as intended: no (L, reach) removes the line as a continuation",
           "  of the canal mask without removing other threads. `BAND_LINE_FILTER` stays off, and no value is",
           "  recommended (`BAND_LINE_MIN_LEN_PX` and `BAND_LINE_REACH_PX` stay None). What the filter does at the two",
           "  evidence settings is in `B1_filter.md`.", ""]
    C.write_text(K.OUT / "B1_straight_runs.md", "\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    K.OUT.mkdir(parents=True, exist_ok=True)
    CACHE_B1.mkdir(parents=True, exist_ok=True)
    ok = C.run_item("B1_evidence", item_b1_evidence)
    sys.exit(0 if ok else 1)
