"""Task 3: lacuna audits and their network-level effect.

    python -u experiments/task3_lacunae.py 3.0   # check that the copied merge reproduces the pipeline
    python -u experiments/task3_lacunae.py 3.1   # crumb loss audit
    python -u experiments/task3_lacunae.py 3.2   # saddle audit, straight line against widest path
    python -u experiments/task3_lacunae.py 3.3   # band objects
    python -u experiments/task3_lacunae.py 3.4   # opening r 2, 3, 4, lacuna level
    python -u experiments/task3_lacunae.py 3.5   # enclosed holes up to 200 px^2, lacuna level
    python -u experiments/task3_lacunae.py 3.6   # network-level effect of each variant (pass 2)
    python -u experiments/task3_lacunae.py 3.7   # before and after crops (pass 2)

Outputs in results_experiments/task3/. PRE-VALIDATION, PIXEL units,
(x, y) = (column, row). Every variant is built here; src/ is not changed.
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import ndimage as ndi
from skimage import measure, morphology

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
import lacunae  # noqa: E402

OUT = C.OUT_ROOT / "task3"


# Re-merge variants ---------------------------------------------------------------
# The re-merge itself is common.merge_fast, a bounding-box copy of
# lacunae.merge_shallow_splits with hooks for min_area and the ratio
# function, checked to reproduce the pipeline's labels on all 8 images
# (item 3.0 here and results_experiments/task0/fast_copies_check.csv).

merge_copy = C.merge_fast
straight_ratio = C.straight_ratio


def widest_saddle(dist_crop: np.ndarray, comp_crop: np.ndarray, a: tuple, b: tuple) -> float:
    """Largest h such that the two points are connected (8-connectivity)
    inside the component through pixels with distance >= h: the bottleneck
    of the widest path between them. Binary search over the component's
    distance values."""
    vals = np.unique(dist_crop[comp_crop])
    lo, hi = 0, len(vals) - 1
    limit = min(dist_crop[a], dist_crop[b])
    hi = int(np.searchsorted(vals, limit, side="right")) - 1
    best = 0.0
    while lo <= hi:
        mid = (lo + hi) // 2
        h = vals[mid]
        lab = measure.label(comp_crop & (dist_crop >= h), connectivity=2)
        if lab[a] and lab[a] == lab[b]:
            best = float(h)
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def widest_ratio(distance, comp_mask_crop, offset, pa, pb, peak_a, peak_b) -> float:
    r0, c0 = offset
    dc = distance[r0:r0 + comp_mask_crop.shape[0], c0:c0 + comp_mask_crop.shape[1]]
    a = (pa[0] - r0, pa[1] - c0)
    b = (pb[0] - r0, pb[1] - c0)
    return widest_saddle(dc, comp_mask_crop, a, b) / min(peak_a, peak_b)


def item_3_0() -> None:
    path = OUT / "3.0_merge_copy_check.csv"
    if path.is_file():
        print(path.read_text())
        return
    rows = []
    for p in C.IMAGE_PATHS:
        d = C.load(p)
        dist = ndi.distance_transform_edt(d["topmask"])
        m = merge_copy(d["ws_labels"], d["topmask"], dist)
        rows.append({"image": d["short"], "labels_identical": bool(np.array_equal(m, d["labels"]))})
        print(rows[-1])
    C.write_csv(path, pd.DataFrame(rows))


# helpers ------------------------------------------------------------------------

def kept_map(d) -> dict:
    """{label: (lacuna_id, on_border)} for kept lacunae."""
    return {int(lbl): (i, bool(b)) for i, (lbl, b) in enumerate(zip(d["kept_labels"], d["on_border"]), start=1)}


def xy(row) -> str:
    return f"({row['centroid_col_px']:.0f},{row['centroid_row_px']:.0f})"


def gap_md(values: pd.Series, ids: list, name: str) -> str:
    return ""


# 3.1 crumb loss -------------------------------------------------------------------

def item_3_1() -> None:
    path = OUT / "3.1_crumb_loss.csv"
    if path.is_file():
        print(pd.read_csv(path).to_string(index=False))
        return
    rows = []
    for p in C.IMAGE_PATHS:
        d = C.load(p)
        km = kept_map(d)
        comps = measure.label(d["topmask"], connectivity=2)
        labels = d["labels"]
        regs = {r.label: r for r in measure.regionprops(labels)}
        for lbl, (lid, border) in km.items():
            lrow = d["lacuna_rows"][lid - 1]
            region = regs[lbl]
            rr, cc = region.coords[0]
            cid = comps[rr, cc]
            sl = ndi.find_objects((comps == cid).astype(np.int32))[0]
            comp_mask = comps[sl] == cid
            comp_area = int(comp_mask.sum())
            pieces = [q for q in np.unique(labels[sl][comp_mask]) if q]
            kept_in_comp = [q for q in pieces if q in km]
            dropped = [q for q in pieces if q not in km]
            # Each dropped piece goes to the kept lacuna it shares the most
            # boundary with (8-neighbourhood).
            lost_here, lost_list = 0, []
            for q in dropped:
                qm = labels == q
                ring = morphology.binary_dilation(qm, np.ones((3, 3), bool)) & ~qm
                touch = {k: int((labels[ring] == k).sum()) for k in kept_in_comp}
                touch = {k: v for k, v in touch.items() if v > 0}
                if not touch:
                    continue
                best = max(touch, key=lambda k: (touch[k], -k))
                if best == lbl:
                    a = int(qm.sum())
                    lost_here += a
                    why = lacunae_reason(regs[q], labels.shape)
                    lost_list.append(f"{a} ({why})")
            kept_sum = int(sum(regs[k].area for k in kept_in_comp))
            unlabelled = int((comp_mask & (labels[sl] == 0)).sum())
            dropped_total = int(sum(regs[q].area for q in dropped))
            rows.append({
                "image": d["short"], "lacuna_id": lid, "at_xy": xy(lrow), "on_border": border,
                "area_px2": int(region.area), "component_area_px2": comp_area,
                "kept_lacunae_in_component": len(kept_in_comp),
                "component_minus_kept_px2": comp_area - kept_sum,
                "missing_pct_of_component": 100.0 * (comp_area - kept_sum) / comp_area,
                "dropped_pieces_in_component": len(dropped),
                "dropped_px2": dropped_total,
                "unlabelled_by_watershed_px2": unlabelled,
                "adjacent_dropped_px2": lost_here,
                "adjacent_pct_of_area": 100.0 * lost_here / region.area,
                "adjacent_pieces": "; ".join(lost_list),
            })
        print(d["short"], "done")
    df = pd.DataFrame(rows)
    C.write_csv(path, df)
    big = df[df.missing_pct_of_component > 3].sort_values("missing_pct_of_component", ascending=False)
    md = ["# 3.1 Crumb loss audit", "",
          "Pre-validation, px. For every kept lacuna: its pre-watershed component (the lacuna mask after",
          "the cut, hole fill and r=1 opening) against what the pipeline keeps of it. missing % is the",
          "share of the component in no kept lacuna. It splits into dropped pieces (watershed pieces",
          "removed by a filter, almost always area < 400 px^2) and pixels the watershed never labels (it",
          "floods with 4-connectivity, while components are 8-connected, so pixels joined only",
          "diagonally stay 0). adjacent is the part of the dropped pieces that shares its longest boundary",
          "with this lacuna, as a share of the lacuna's own area. When a component holds more than one",
          "kept lacuna, its missing % is shared by all of them.", "",
          f"Kept lacunae: {len(df)}. Whose component misses more than 3%: {len(big)}. With any adjacent",
          f"dropped piece: {(df.adjacent_dropped_px2 > 0).sum()}. With unlabelled pixels: "
          f"{(df.unlabelled_by_watershed_px2 > 0).sum()}.", "",
          C.md_table(big[["image", "lacuna_id", "at_xy", "on_border", "area_px2", "component_area_px2",
                          "kept_lacunae_in_component", "missing_pct_of_component", "dropped_px2",
                          "unlabelled_by_watershed_px2", "adjacent_dropped_px2", "adjacent_pct_of_area",
                          "adjacent_pieces"]], floatfmt="{:.1f}"),
          "",
          "Distribution of missing % of the component over all kept lacunae (count per bin):", "",
          bins_md(df.missing_pct_of_component, [0, 0.0001, 1, 3, 5, 10, 20, 50, 1000]), ""]
    C.write_text_once(OUT / "3.1_crumb_loss.md", "\n".join(md))
    print("\n".join(md))


def lacunae_reason(region, shape) -> str:
    rows, cols = shape
    if region.area < lacunae.MIN_AREA_PX2:
        return "area"
    if region.area > lacunae.MAX_AREA_FRACTION_OF_IMAGE * rows * cols:
        return "max area"
    if region.solidity < lacunae.MIN_SOLIDITY:
        return "solidity"
    mi, ma = region.axis_minor_length, region.axis_major_length
    if (ma / mi if mi > 0 else np.inf) > lacunae.MAX_ASPECT_RATIO:
        return "aspect"
    return "kept?"


def bins_md(values: pd.Series, edges: list) -> str:
    lines = ["| bin | count |", "|---|---|"]
    v = np.asarray(values, dtype=float)
    for a, b in zip(edges[:-1], edges[1:]):
        n = int(((v >= a) & (v < b)).sum())
        lines.append(f"| [{a:g}, {b:g}) | {n} |")
    return "\n".join(lines) + "\n"


# 3.2 saddle audit -----------------------------------------------------------------

POINTS_3_2 = [("543_3", 875, 545), ("682_z08", 435, 545), ("682_z08", 555, 520), ("682_z29", 100, 835)]


def item_3_2() -> None:
    path = OUT / "3.2_saddle_pairs.csv"
    if not path.is_file():
        rows = []
        for p in C.IMAGE_PATHS:
            d = C.load(p)
            dist = ndi.distance_transform_edt(d["topmask"])
            rec_s, rec_w = [], []
            m_s = merge_copy(d["ws_labels"], d["topmask"], dist, record=rec_s)
            m_w = merge_copy(d["ws_labels"], d["topmask"], dist, ratio_fn=widest_ratio, record=rec_w)
            assert np.array_equal(m_s, d["labels"])
            ws = d["ws_labels"]
            km = kept_map(d)
            for s, w in zip(rec_s, rec_w):
                assert (s["a"], s["b"]) == (w["a"], w["b"])
                am, bm = ws == s["a"], ws == s["b"]
                adj = bool((morphology.binary_dilation(am, np.ones((3, 3), bool)) & bm).any())
                ca = np.argwhere(am).mean(axis=0)
                cb = np.argwhere(bm).mean(axis=0)
                final_a, final_b = int(m_s[am][0]), int(m_s[bm][0])
                rows.append({
                    "image": d["short"], "component": s["component"],
                    "piece_a_xy": f"({ca[1]:.0f},{ca[0]:.0f})", "piece_b_xy": f"({cb[1]:.0f},{cb[0]:.0f})",
                    "area_a": int(am.sum()), "area_b": int(bm.sum()), "adjacent": adj,
                    "peak_a": round(s["peak_a"], 2), "peak_b": round(s["peak_b"], 2),
                    "ratio_straight": round(s["ratio"], 4), "ratio_widest": round(w["ratio"], 4),
                    "merged_default": final_a == final_b,
                    "merged_widest": int(m_w[am][0]) == int(m_w[bm][0]),
                    "a_kept_default": final_a in km, "b_kept_default": final_b in km,
                    "mid_x": (ca[1] + cb[1]) / 2, "mid_y": (ca[0] + cb[0]) / 2,
                })
            kept_w = lacunae.filter_regions(m_w)
            C.write_json(OUT / "3.2_widest" / f"{d['short']}.json",
                         {"default_count": d["lacuna_count"], "widest_count": len(kept_w),
                          "widest_rows": lacunae.measurements_for(kept_w, C.PRECISION)})
            print(d["short"], len(rec_s), "pairs")
        C.write_csv(path, pd.DataFrame(rows))
    df = pd.read_csv(path)
    df["flip_pair"] = (df.ratio_straight >= 0.35) != (df.ratio_widest >= 0.35)
    df["flip_final"] = df.merged_default != df.merged_widest
    lines = ["# 3.2 Saddle audit", "",
             "Pre-validation, px. Every pair of watershed pieces of at least 400 px^2 inside one pre-watershed",
             "component, which is the set of pairs the pipeline's re-merge tests. ratio_straight is the",
             "pipeline's measure: the lowest distance-transform value on the straight line between the two",
             "peaks, over the smaller peak. ratio_widest uses the widest path inside the mask instead: the",
             "largest h such that the two peaks stay 8-connected through pixels with distance >= h, over the",
             "smaller peak. The cut 0.35 is not retuned.", "",
             f"Pairs tested: {len(df)} in {df.groupby(['image', 'component']).ngroups} components. "
             f"Pairs whose own test flips at 0.35: {int(df.flip_pair.sum())}. Pairs whose final merged or split "
             f"state differs (after the union-find): {int(df.flip_final.sum())}.", "",
             C.md_table(df[["image", "piece_a_xy", "piece_b_xy", "area_a", "area_b", "adjacent", "ratio_straight",
                            "ratio_widest", "merged_default", "merged_widest", "flip_pair"]], floatfmt="{:.3f}"),
             "", "Distribution of the ratios (count per bin):", "",
             "| bin | straight | widest |", "|---|---|---|"]
    edges = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.6, 0.7, 0.8, 0.9, 1.01]
    for a, b in zip(edges[:-1], edges[1:]):
        ns = int(((df.ratio_straight >= a) & (df.ratio_straight < b)).sum())
        nw = int(((df.ratio_widest >= a) & (df.ratio_widest < b)).sum())
        lines.append(f"| [{a:.2f}, {b:.2f}) | {ns} | {nw} |")
    lines += ["", "## Named points", ""]
    for name, x, y in POINTS_3_2:
        sub = df[(df.image == name) & (np.hypot(df.mid_x - x, df.mid_y - y) <= 60)]
        lines.append(f"**{name} near ({x},{y})**: {len(sub)} tested pair(s) with midpoint within 60 px.")
        if len(sub):
            lines.append("")
            lines.append(C.md_table(sub[["piece_a_xy", "piece_b_xy", "area_a", "area_b", "ratio_straight",
                                         "ratio_widest", "merged_default", "merged_widest"]], floatfmt="{:.3f}"))
        lines.append("")
    lines.append("**542_z06, all tested pairs:**")
    lines.append("")
    lines.append(C.md_table(df[df.image == "542_z06"][["piece_a_xy", "piece_b_xy", "area_a", "area_b",
                                                        "ratio_straight", "ratio_widest", "merged_default",
                                                        "merged_widest"]], floatfmt="{:.3f}"))
    counts = []
    for p in C.IMAGE_PATHS:
        j = json.loads((OUT / "3.2_widest" / f"{C.short(p)}.json").read_text())
        counts.append(f"{C.short(p)} {j['default_count']} to {j['widest_count']}")
    lines += ["", "Kept lacuna count, default to widest-path merge: " + ", ".join(counts) + ".", ""]
    C.write_text(OUT / "3.2_saddle_audit.md", "\n".join(lines))
    print("\n".join(lines))


# 3.3 band objects -----------------------------------------------------------------

BAND_OBJECTS = [("542_z06", 555, 149), ("682_z23", 363, 7)]


def all_kept_table() -> pd.DataFrame:
    """One row per kept lacuna over the 8 images with the shape measures
    used in 3.3 (and reused in 3.6)."""
    path = OUT / "kept_lacunae_measures.csv"
    if path.is_file():
        return pd.read_csv(path)
    rows = []
    for p in C.IMAGE_PATHS:
        d = C.load(p)
        regs = {r.label: r for r in measure.regionprops(d["labels"])}
        flagged = d["flagged"]
        for (lbl, b), lrow in zip(zip(d["kept_labels"], d["on_border"]), d["lacuna_rows"]):
            r = regs[int(lbl)]
            sl = r.slice
            m = np.pad(r.image, 6)
            edt = ndi.distance_transform_edt(m)
            opened = morphology.binary_opening(m, morphology.disk(5))
            rr, cc = r.coords[:, 0], r.coords[:, 1]
            rows.append({
                "image": d["short"], "lacuna_id": lrow["lacuna_id"], "x": lrow["centroid_col_px"],
                "y": lrow["centroid_row_px"], "on_border": bool(b), "area_px2": int(r.area),
                "minor_axis_px": float(r.axis_minor_length), "major_axis_px": float(r.axis_major_length),
                "solidity": float(r.solidity), "aspect": float(r.axis_major_length / r.axis_minor_length),
                "flagged_overlap_fraction": float(flagged[rr, cc].mean()),
                "thickness_px": float(2 * edt.max()),
                "kept_after_r5_opening": float(opened.sum() / m.sum()),
                "mean_red": float(d["channel"][rr, cc].mean()),
            })
    df = pd.DataFrame(rows)
    C.write_csv(path, df)
    return df


def separation(df: pd.DataFrame, col: str, is_band: pd.Series) -> dict:
    """Do the band objects sit apart from all others on this measure? Checks
    both ends. Returns the side, the band values, the nearest other value
    and the gap."""
    band = df.loc[is_band, col].to_numpy()
    other = df.loc[~is_band, col].to_numpy()
    out = {"measure": col, "band_values": ", ".join(f"{v:.3f}" for v in band)}
    if band.max() < other.min():
        out.update(side="low", nearest_other=other.min(), gap=other.min() - band.max(),
                   gap_rel=(other.min() - band.max()) / other.min(), separates=True)
    elif band.min() > other.max():
        out.update(side="high", nearest_other=other.max(), gap=band.min() - other.max(),
                   gap_rel=(band.min() - other.max()) / band.min(), separates=True)
    else:
        lo_rank = int((other < band.max()).sum())
        hi_rank = int((other > band.min()).sum())
        out.update(side="none", nearest_other=float("nan"), gap=float("nan"), gap_rel=float("nan"),
                   separates=False, others_inside_low_side=lo_rank, others_inside_high_side=hi_rank)
    return out


def is_band_row(df: pd.DataFrame) -> pd.Series:
    mask = pd.Series(False, index=df.index)
    for name, x, y in BAND_OBJECTS:
        mask |= (df.image == name) & (np.hypot(df.x - x, df.y - y) < 15)
    return mask


def item_3_3() -> None:
    df = all_kept_table()
    band = is_band_row(df)
    assert band.sum() == 2, band.sum()
    measures = ["minor_axis_px", "flagged_overlap_fraction", "solidity", "thickness_px", "kept_after_r5_opening",
                "area_px2", "aspect"]
    sep = pd.DataFrame([separation(df, m, band) for m in measures])
    C.write_csv(OUT / "3.3_separation.csv", sep)
    lines = ["# 3.3 Band objects", "",
             "Pre-validation, px. All 98 kept lacunae over the 8 images. The two band objects are 542_z06 at",
             "(555,149) and 682_z23 at (363,7). minor_axis_px is the pipeline's ellipse minor axis.",
             "flagged_overlap_fraction is the share of the lacuna's pixels inside the flagged (canal) mask,",
             "which the pipeline dilates by 4 px. thickness_px is twice the largest distance-transform value",
             "inside the lacuna, and kept_after_r5_opening the share left by an opening with the top-hat",
             "disk (r = 5); both are given for comparison with the round 3 report.", "",
             C.md_table(sep, floatfmt="{:.3f}"), ""]
    for m in ["minor_axis_px", "flagged_overlap_fraction", "solidity"]:
        s = df.assign(band=band).sort_values(m)
        lines.append(f"**{m}**, the 8 lowest and 4 highest:")
        lines.append("")
        lines.append(C.md_table(pd.concat([s.head(8), s.tail(4)])[["image", "lacuna_id", "x", "y", "on_border", m, "band"]],
                                floatfmt="{:.3f}"))
        lines.append("")
    nz = df[df.flagged_overlap_fraction > 0]
    lines.append(f"Kept lacunae with any flagged overlap: {len(nz)}.")
    lines.append("")
    lines.append(C.md_table(nz[["image", "lacuna_id", "x", "y", "on_border", "area_px2", "minor_axis_px",
                                "flagged_overlap_fraction", "solidity"]], floatfmt="{:.3f}"))
    C.write_text(OUT / "3.3_band_objects.md", "\n".join(lines) + "\n")
    print("\n".join(lines))


# 3.4 opening ----------------------------------------------------------------------

OPEN_RADII = (2, 3, 4)


def opened_largest(labels: np.ndarray, lbl: int, r: int) -> np.ndarray:
    """Binary opening of one lacuna with disk(r), largest 8-connected piece
    kept, as a full-frame mask. The opening runs in the bounding box plus a
    margin, clipped to the frame; skimage's erosion treats the frame edge as
    foreground, so an object touching the frame is not eaten from that
    side."""
    m = labels == lbl
    sl = ndi.find_objects(m.astype(np.int32))[0]
    pad = r + 3
    r0, r1 = max(0, sl[0].start - pad), min(m.shape[0], sl[0].stop + pad)
    c0, c1 = max(0, sl[1].start - pad), min(m.shape[1], sl[1].stop + pad)
    sub = m[r0:r1, c0:c1]
    o = morphology.binary_opening(sub, morphology.disk(r))
    lab = measure.label(o, connectivity=2)
    out = np.zeros_like(m)
    if lab.max() == 0:
        return out
    sizes = np.bincount(lab.ravel())
    sizes[0] = 0
    out[r0:r1, c0:c1] = lab == int(np.argmax(sizes))
    return out


def shape_of(mask: np.ndarray) -> dict:
    if not mask.any():
        return {"area": 0, "aspect": float("nan"), "perimeter": 0.0, "solidity": float("nan")}
    r = measure.regionprops(mask.astype(np.uint8))[0]
    return {"area": int(r.area), "aspect": float(r.axis_major_length / max(r.axis_minor_length, 1e-9)),
            "perimeter": float(r.perimeter), "solidity": float(r.solidity)}


def item_3_4() -> None:
    path = OUT / "3.4_opening.csv"
    if not path.is_file():
        rows = []
        for p in C.IMAGE_PATHS:
            d = C.load(p)
            for (lbl, b), lrow in zip(zip(d["kept_labels"], d["on_border"]), d["lacuna_rows"]):
                base = shape_of(d["labels"] == lbl)
                row = {"image": d["short"], "lacuna_id": lrow["lacuna_id"], "at_xy": xy(lrow), "on_border": bool(b),
                       "area": base["area"], "aspect": base["aspect"], "perimeter": base["perimeter"],
                       "solidity": base["solidity"]}
                for r in OPEN_RADII:
                    s = shape_of(opened_largest(d["labels"], int(lbl), r))
                    row[f"r{r}_area_lost_pct"] = 100 * (base["area"] - s["area"]) / base["area"]
                    row[f"r{r}_aspect"] = s["aspect"]
                    row[f"r{r}_perimeter_change_pct"] = 100 * (s["perimeter"] - base["perimeter"]) / base["perimeter"]
                    row[f"r{r}_solidity"] = s["solidity"]
                    row[f"r{r}_lost"] = s["area"] == 0
                    row[f"r{r}_below_400"] = 0 < s["area"] < lacunae.MIN_AREA_PX2
                rows.append(row)
            print(d["short"], "done")
        C.write_csv(path, pd.DataFrame(rows))
    df = pd.read_csv(path)
    lines = ["# 3.4 Tails and serrated edges: opening of each lacuna (lacuna level only)", "",
             "Pre-validation, px. Each kept lacuna's own mask is opened with disk(r) and its largest piece kept.",
             "Perimeter is skimage's regionprops perimeter. Nothing in the network stage is run here.", "",
             "| r | median area lost % | p90 | max | lacunae losing > 10% | > 20% | lost entirely | left below 400 px^2 | median perimeter change % | median aspect change |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in OPEN_RADII:
        a = df[f"r{r}_area_lost_pct"]
        lines.append(f"| {r} | {a.median():.1f} | {a.quantile(0.9):.1f} | {a.max():.1f} | {(a > 10).sum()} | "
                     f"{(a > 20).sum()} | {int(df[f'r{r}_lost'].sum())} | {int(df[f'r{r}_below_400'].sum())} | "
                     f"{df[f'r{r}_perimeter_change_pct'].median():+.1f} | {(df[f'r{r}_aspect'] - df.aspect).median():+.3f} |")
    lines += ["", "The 15 lacunae losing the most area at r = 3:", ""]
    top = df.sort_values("r3_area_lost_pct", ascending=False).head(15)
    lines.append(C.md_table(top[["image", "lacuna_id", "at_xy", "on_border", "area", "solidity", "r2_area_lost_pct",
                                 "r3_area_lost_pct", "r4_area_lost_pct", "aspect", "r3_aspect",
                                 "r3_perimeter_change_pct"]], floatfmt="{:.2f}"))
    lines += ["", "Per image at r = 3:", ""]
    g = df.groupby("image").agg(n=("area", "size"), median_lost=("r3_area_lost_pct", "median"),
                                max_lost=("r3_area_lost_pct", "max"),
                                median_perim=("r3_perimeter_change_pct", "median")).reset_index()
    lines.append(C.md_table(g, floatfmt="{:.1f}"))
    C.write_text(OUT / "3.4_opening.md", "\n".join(lines) + "\n")
    print("\n".join(lines))


# 3.5 holes ------------------------------------------------------------------------

HOLE_MAX_PX2 = 200  # from the task text


def holes_of(labels: np.ndarray, lbl: int) -> list[np.ndarray]:
    """Enclosed holes of one lacuna (background components not reaching the
    frame or the outside), as full-frame masks, with label 0 inside."""
    m = labels == lbl
    filled = ndi.binary_fill_holes(m)
    holes = filled & ~m
    lab = measure.label(holes, connectivity=1)
    return [lab == k for k in range(1, lab.max() + 1)]


def item_3_5() -> None:
    path = OUT / "3.5_holes.csv"
    if not path.is_file():
        rows = []
        for p in C.IMAGE_PATHS:
            d = C.load(p)
            for (lbl, b), lrow in zip(zip(d["kept_labels"], d["on_border"]), d["lacuna_rows"]):
                hs = holes_of(d["labels"], int(lbl))
                if not hs:
                    continue
                m = d["labels"] == lbl
                base = shape_of(m)
                fill = m.copy()
                sizes = []
                for h in hs:
                    a = int(h.sum())
                    other = int((d["labels"][h] != 0).sum())
                    sizes.append(a)
                    if a <= HOLE_MAX_PX2 and other == 0:
                        fill |= h
                new = shape_of(fill)
                hm = np.zeros_like(m)
                for h in hs:
                    hm |= h
                rows.append({"image": d["short"], "lacuna_id": lrow["lacuna_id"], "at_xy": xy(lrow),
                             "on_border": bool(b), "holes_px2": ";".join(str(s) for s in sorted(sizes, reverse=True)),
                             "area": base["area"], "area_filled": new["area"],
                             "area_change_pct": 100 * (new["area"] - base["area"]) / base["area"],
                             "solidity": base["solidity"], "solidity_filled": new["solidity"],
                             "hole_mean_red": float(d["channel"][hm].mean()),
                             "skeleton_px_in_holes": int(d["skeleton"][hm].sum())})
        C.write_csv(path, pd.DataFrame(rows))
    df = pd.read_csv(path)
    lines = ["# 3.5 Enclosed holes, filled up to 200 px^2 (lacuna level only)", "",
             "Pre-validation, px. Holes are background regions fully enclosed by one kept lacuna's final mask",
             "(4-connected background, as skimage remove_small_holes counts them). The pipeline already fills",
             "holes up to 20 px^2 before the watershed, so what remains here is larger, or was created by the",
             "r=1 opening or the watershed cut.", "",
             f"Kept lacunae with at least one enclosed hole: {len(df)}.", "",
             C.md_table(df, floatfmt="{:.3f}")]
    C.write_text(OUT / "3.5_holes.md", "\n".join(lines) + "\n")
    print("\n".join(lines))


# 3.6 network-level effect of the variants (pass 2) ---------------------------------

# 3.3 variant: reject a kept object whose share of area left after an
# opening with the top-hat disk (r = 5) is below this. The middle of the gap
# between the two band objects (0.207, 0.348) and the next kept lacuna
# (0.681); see 3.3_band_objects.md. Rests on 2 objects.
BAND_OPENING_SHARE_MIN = 0.515
BAND_OPENING_RADIUS = 5

VARIANTS = ["crumbs_join_merge", "widest_path_merge", "band_filter", "open_r2", "open_r3", "open_r4", "fill_holes_200"]


def opening_share(region) -> float:
    m = np.pad(region.image, 6)
    return float(morphology.binary_opening(m, morphology.disk(BAND_OPENING_RADIUS)).sum() / m.sum())


def band_filter_regions(label_image: np.ndarray, rejected: list | None = None) -> list[tuple]:
    """lacunae.filter_regions plus one extra test (the 3.3 variant)."""
    kept = []
    for region, b in lacunae.filter_regions(label_image):
        share = opening_share(region)
        if share < BAND_OPENING_SHARE_MIN:
            if rejected is not None:
                cy, cx = region.centroid
                rejected.append({"x": round(cx), "y": round(cy), "area_px2": int(region.area),
                                 "opening_share": round(share, 3), "on_border": bool(b)})
            continue
        kept.append((region, b))
    return kept


def variant_lacunae(d: dict, variant: str, rejected: list | None = None) -> tuple[np.ndarray, list]:
    """(labels, kept) for one lacuna variant, from the cached default stages."""
    topmask, ws = d["topmask"], d["ws_labels"]
    if variant == "crumbs_join_merge":
        dist = ndi.distance_transform_edt(topmask)
        labels = C.merge_fast(ws, topmask, dist, min_area=0)
        return labels, lacunae.filter_regions(labels)
    if variant == "widest_path_merge":
        dist = ndi.distance_transform_edt(topmask)
        labels = C.merge_fast(ws, topmask, dist, ratio_fn=widest_ratio)
        return labels, lacunae.filter_regions(labels)
    if variant == "band_filter":
        return d["labels"], band_filter_regions(d["labels"], rejected)
    new = np.zeros_like(d["labels"])
    for lbl in d["kept_labels"]:
        lbl = int(lbl)
        if variant.startswith("open_r"):
            m = opened_largest(d["labels"], lbl, int(variant[-1]))
        elif variant == "fill_holes_200":
            m = d["labels"] == lbl
            for h in holes_of(d["labels"], lbl):
                if h.sum() <= HOLE_MAX_PX2 and not (d["labels"][h] != 0).any():
                    m = m | h
        else:
            raise ValueError(variant)
        new[m] = lbl
    # The changed shapes go through the pipeline's own filters again.
    return new, lacunae.filter_regions(new)


def _variant_run(args) -> str:
    name, variant = args
    path = OUT / "3.6_runs" / f"{name}__{variant}.json"
    if path.is_file():
        return str(path)
    d = C.load(name)
    rejected: list = []
    labels, kept = variant_lacunae(d, variant, rejected)
    rows = lacunae.measurements_for(kept, C.PRECISION)
    net = C.network_stage(d["channel"], labels, kept, preprocessed=d["preprocessed"], flagged=d["flagged"],
                          signal=d["signal"], t_lo=d["t_lo"])
    h = C.headline(rows, net["cell_rows"], net["density"], len(net["bridges"]))
    C.write_npz(C.OUT_ROOT / "_cache" / "variants" / f"{name}__{variant}.npz", lacuna_id_map=net["lacuna_id_map"],
                skeleton=net["skeleton"])
    C.write_json(path, {"image": name, "variant": variant, "headline": h, "skeleton_px": int(net["skeleton"].sum()),
                        "rejected_by_band_filter": rejected, "lacuna_rows": rows, "cell_rows": net["cell_rows"]})
    return str(path)


def item_3_6() -> None:
    from concurrent.futures import ProcessPoolExecutor
    names = [C.short(p) for p in C.IMAGE_PATHS]
    jobs = [(n, v) for v in VARIANTS for n in names]
    with ProcessPoolExecutor(max_workers=8) as ex:
        for pth in ex.map(_variant_run, jobs):
            print("done", Path(pth).name, flush=True)
    meas = ["lacuna_count", "interior_count", "median_area_px2", "roots_per_cell", "ring30_per_cell_px",
            "ring60_per_cell_px", "field_density_per_px", "bridges"]
    rows, rejected = [], []
    for n in names:
        d = C.load(n)
        base = C.headline(d["lacuna_rows"], d["cell_rows"], d["field"]["canalicular_length_density_per_px"], d["n_bridges"])
        rows.append({"image": n, "variant": "default", **base, **{f"{m}_pct": 0.0 for m in meas}})
        for v in VARIANTS:
            j = json.loads((OUT / "3.6_runs" / f"{n}__{v}.json").read_text())
            r = {"image": n, "variant": v, **j["headline"]}
            for m in meas:
                r[f"{m}_pct"] = 100 * (r[m] - base[m]) / base[m] if base[m] else float("nan")
            # Cells whose own roots or ring 30 changed: match by centroid within 10 px.
            changed = []
            for lr, cr in zip(j["lacuna_rows"], j["cell_rows"]):
                best = None
                for dl, dc in zip(d["lacuna_rows"], d["cell_rows"]):
                    dd = np.hypot(lr["centroid_col_px"] - dl["centroid_col_px"], lr["centroid_row_px"] - dl["centroid_row_px"])
                    if dd <= 10 and (best is None or dd < best[0]):
                        best = (dd, dl, dc)
                if best is None:
                    changed.append(f"new ({lr['centroid_col_px']:.0f},{lr['centroid_row_px']:.0f})")
                elif (best[2]["roots_count"] != cr["roots_count"] or best[2]["ring_length_r30_px"] != cr["ring_length_r30_px"]
                      or best[1]["area_px2"] != lr["area_px2"]):
                    changed.append(f"({lr['centroid_col_px']:.0f},{lr['centroid_row_px']:.0f})")
            r["cells_changed"] = len(changed)
            r["cells_changed_at"] = " ".join(changed)
            rows.append(r)
            for rej in j["rejected_by_band_filter"]:
                rejected.append({"image": n, **rej})
    df = pd.DataFrame(rows)
    C.write_csv(OUT / "3.6_variants.csv", df)
    rej = pd.DataFrame(rejected)
    C.write_csv(OUT / "3.6_band_filter_rejected.csv", rej)
    summ = []
    for v in VARIANTS:
        g = df[df.variant == v]
        row = {"variant": v, "images_with_any_change": int((g.cells_changed > 0).sum()),
               "cells_changed": int(g.cells_changed.sum()),
               "lacuna_count_change": int((g.lacuna_count - df[df.variant == "default"].set_index("image").loc[g.image, "lacuna_count"].values).sum())}
        for m in ("roots_per_cell", "ring30_per_cell_px", "field_density_per_px", "bridges", "median_area_px2"):
            row[f"{m}_pct_min"] = g[f"{m}_pct"].min()
            row[f"{m}_pct_max"] = g[f"{m}_pct"].max()
        summ.append(row)
    summ = pd.DataFrame(summ)
    C.write_csv(OUT / "3.6_summary.csv", summ)
    cols = ["image", "variant", "lacuna_count", "interior_count", "roots_per_cell", "roots_per_cell_pct",
            "ring30_per_cell_px", "ring30_per_cell_px_pct", "field_density_per_px", "field_density_per_px_pct",
            "bridges", "cells_changed", "cells_changed_at"]
    md = ["# 3.6 Network-level effect of the lacuna variants", "",
          "Pre-validation, px. Each variant changes the lacunae only; the network stage then runs as in the",
          "pipeline (canal mask, preprocessed channel and hysteresis mask from the default run, which do not",
          "depend on the lacunae; lacuna removal, skeleton, bridging, graph, roots and rings recomputed).",
          "Changed shapes (opening, hole fill) go through the pipeline's own filters again.", "",
          "- crumbs_join_merge (3.1): watershed pieces under 400 px^2 may join the re-merge test.",
          "- widest_path_merge (3.2): the re-merge uses the widest-path saddle instead of the straight line.",
          f"- band_filter (3.3): also reject objects keeping less than {BAND_OPENING_SHARE_MIN} of their area after an",
          "  r = 5 opening.",
          "- open_r2, open_r3, open_r4 (3.4): each kept lacuna replaced by the largest piece of its opening.",
          "- fill_holes_200 (3.5): enclosed holes up to 200 px^2 filled.", "",
          "## Range over the 8 images (percent change against the default)", "",
          C.md_table(summ, floatfmt="{:+.2f}"), "",
          "## Objects the band filter rejects (all 8 images)", "",
          C.md_table(rej) if len(rej) else "None.", "",
          "## Every image and variant", "",
          "cells_changed counts lacunae whose area, roots or ring 30 differ from the default (matched by",
          "centroid within 10 px), or that are new.", "",
          C.md_table(df[df.variant != "default"][cols], floatfmt="{:.4g}")]
    C.write_text_once(OUT / "3.6_variants.md", "\n".join(md) + "\n")
    print("\n".join(md))


# 3.7 before and after crops (pass 2) ------------------------------------------------

OPENS = ["open_r2", "open_r3", "open_r4"]
CASES_3_7 = [
    # (image, x, y, half size, variants, why)
    ("543-2", 40, 300, 70, OPENS, "named worst case: outline runs down a thread root"),
    ("543-2", 265, 95, 70, OPENS, "named worst case: pointed tail at the lower tip"),
    ("543_3", 920, 200, 80, OPENS + ["crumbs_join_merge"], "named worst case: irregular outline, left lobe and spur"),
    ("542_z06", 105, 65, 60, ["open_r3", "crumbs_join_merge"], "named: leaked outline into a canalicular loop"),
    ("542_z06", 783, 581, 60, ["fill_holes_200"], "named: unfilled 146 px^2 hole"),
    ("682_z08", 210, 434, 70, OPENS, "serrated: perimeter -21% for area -6% at r = 3"),
    ("682_z23", 472, 61, 60, OPENS, "serrated: perimeter -13% at r = 3"),
    ("682_z29", 182, 716, 60, OPENS, "serrated: perimeter -12% at r = 3"),
    ("542_z06", 570, 100, 80, ["widest_path_merge", "band_filter"], "split that flips: band pair (584,53) and (555,149)"),
    ("682_z29", 100, 835, 70, ["widest_path_merge"], "split that flips: the calibration's two-lobe case"),
    ("543_3", 877, 545, 50, ["crumbs_join_merge", "open_r2"], "crumb gap through the cell"),
    ("542_z18", 937, 993, 50, ["crumbs_join_merge"], "crumb of 235 px^2 joins"),
    ("682_z29", 862, 728, 50, ["crumbs_join_merge"], "new object from two crumbs (archived D8 object)"),
    ("682_z23", 74, 8, 50, ["crumbs_join_merge"], "new object at the top edge"),
]


def _panel(raw_rgb, idmap, skel, base_skel, sl, color, show_diff: bool):
    from skimage import segmentation
    p = raw_rgb[sl].copy()
    p = C.paint(p, skel[sl], (0, 200, 255), alpha=0.8)
    if show_diff:
        p = C.paint(p, (skel & ~base_skel)[sl], (255, 255, 0))
        p = C.paint(p, (base_skel & ~skel)[sl], (255, 40, 40))
    b = segmentation.find_boundaries(idmap[sl], mode="inner")
    p[b] = color
    return p


def item_3_7() -> None:
    out = OUT / "3.7_crops"
    lines = ["# 3.7 Before and after crops", "",
             "Pre-validation, px. Each crop: raw red | default (outline green, skeleton blue) | each variant",
             "(outline magenta, skeleton blue, skeleton added by the variant yellow, removed red). 2x zoom.", "",
             "| file | image | at (x,y) | variants | why |", "|---|---|---|---|---|"]
    for name, x, y, half, variants, why in CASES_3_7:
        fname = f"{name}_x{x}_y{y}.png"
        lines.append(f"| `3.7_crops/{fname}` | {name} | ({x},{y}) | {', '.join(variants)} | {why} |")
        if (out / fname).is_file():
            continue
        d = C.load(name)
        raw = (C.to_rgb(d["channel"]) * 0.85).astype(np.uint8)
        r0, r1 = max(0, y - half), min(1024, y + half)
        c0, c1 = max(0, x - half), min(1024, x + half)
        sl = (slice(r0, r1), slice(c0, c1))
        panels = [raw[sl], _panel(raw, d["lacuna_id_map"], d["skeleton"], d["skeleton"], sl, (0, 255, 0), False)]
        titles = [f"{name} ({x},{y}) raw", "default"]
        for v in variants:
            with np.load(C.OUT_ROOT / "_cache" / "variants" / f"{name}__{v}.npz") as z:
                idm, sk = z["lacuna_id_map"], z["skeleton"]
            panels.append(_panel(raw, idm, sk, d["skeleton"], sl, (255, 0, 255), True))
            titles.append(v)
        C.write_png(out / fname, C.panel_row(panels, titles, scale=2))
        print(fname, "done")
    C.write_text_once(OUT / "3.7_crops.md", "\n".join(lines) + "\n")
    print("\n".join(lines))


ITEMS = {"3.0": item_3_0, "3.1": item_3_1, "3.2": item_3_2, "3.3": item_3_3, "3.4": item_3_4, "3.5": item_3_5,
         "3.6": item_3_6, "3.7": item_3_7}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    item = sys.argv[1]
    ok = C.run_item(item, ITEMS[item])
    sys.exit(0 if ok else 1)
