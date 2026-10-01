"""Task 2: lacuna and network thresholds.

    python -u experiments/task2_thresholds.py 2.1   # which stage rejects the visibly missed bodies
    python -u experiments/task2_thresholds.py 2.2   # t_hi, t_lo against brightness statistics
    python -u experiments/task2_thresholds.py 2.3   # both cuts x0.9 and x1.1 on 3 images
    python -u experiments/task2_thresholds.py 2.4   # full grid, all 8 images (pass 2)

Outputs in results_experiments/task2/. PRE-VALIDATION, PIXEL units,
(x, y) = (column, row).

The two cuts: t_hi is the lacuna cut (upper 3-class multi-Otsu cut of the
raw red channel, src/lacunae.py). t_lo is the network strict cut (lower
3-class multi-Otsu cut of the preprocessed channel, src/canaliculi.py); the
hysteresis low cut is 0.75 t_lo and the bridging signal test is relative to
t_lo, so both follow it. The canal detector's own cut (flagged structures)
is left at its default in every run here.
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import ndimage as ndi
from scipy.stats import spearmanr
from skimage import filters, measure, morphology

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402

OUT = C.OUT_ROOT / "task2"
GRID = OUT / "grid"


# 2.1 missed bodies -----------------------------------------------------------------

CASES_2_1 = [("543_3", 40, 310), ("542_z06", 230, 300), ("542_z06", 5, 930)]
SEARCH_RADIUS_PX = 30  # pieces within this distance of the named point are examined


def piece_props(mask: np.ndarray) -> dict:
    lab = measure.label(mask, connectivity=2)
    if lab.max() == 0:
        return {"area": 0}
    r = max(measure.regionprops(lab), key=lambda q: q.area)
    minor, major = r.axis_minor_length, r.axis_major_length
    return {"area": int(r.area), "solidity": round(float(r.solidity), 3),
            "aspect": round(float(major / minor), 2) if minor > 0 else float("inf"),
            "bbox": r.bbox}


def verdict(region, shape) -> str:
    import lacunae
    rows, cols = shape
    if region.area < lacunae.MIN_AREA_PX2:
        return f"area {region.area} < {lacunae.MIN_AREA_PX2}"
    if region.area > lacunae.MAX_AREA_FRACTION_OF_IMAGE * rows * cols:
        return "area above the 5% cap"
    if region.solidity < lacunae.MIN_SOLIDITY:
        return f"solidity {region.solidity:.3f} < {lacunae.MIN_SOLIDITY}"
    minor, major = region.axis_minor_length, region.axis_major_length
    aspect = major / minor if minor > 0 else float("inf")
    if aspect > lacunae.MAX_ASPECT_RATIO:
        return f"aspect {aspect:.2f} > {lacunae.MAX_ASPECT_RATIO}"
    return "kept"


def item_2_1() -> None:
    import lacunae
    out_md = OUT / "2.1_missed_bodies.md"
    if out_md.is_file():
        print("2.1 done already")
        return
    lines = ["# 2.1 Which stage rejects the visibly missed bodies", "",
             "Pre-validation, px, (x, y) = (column, row). Each stage of src/lacunae.py is replayed with the",
             "pipeline's own functions. Pieces within 30 px of the named point are listed.", ""]
    rows_all = []
    for name, x, y in CASES_2_1:
        d = C.load(name)
        ch = d["channel"]
        t_hi = d["t_hi"]
        yy, xx = np.mgrid[0:ch.shape[0], 0:ch.shape[1]]
        near = np.hypot(xx - x, yy - y) <= SEARCH_RADIUS_PX
        cut = ch >= t_hi
        filled = morphology.remove_small_holes(cut, area_threshold=lacunae.FILL_HOLES_PX2)
        opened = morphology.opening(filled, morphology.disk(lacunae.DESPECKLE_OPENING_RADIUS_PX))
        assert np.array_equal(opened, d["topmask"])
        win = ch[max(0, y - 15):y + 16, max(0, x - 15):x + 16]
        lines.append(f"## {name} near ({x},{y})")
        lines.append("")
        lines.append(f"t_hi = {t_hi:.4f}. Raw red in a 31 px square around the point: max {win.max():.3f}, "
                     f"p90 {np.percentile(win, 90):.3f}, mean {win.mean():.3f}. Pixels above t_hi within "
                     f"{SEARCH_RADIUS_PX} px: {int((cut & near).sum())}.")
        lines.append("")
        # Follow the component(s) of the final mask that touch the neighbourhood.
        comp = measure.label(d["topmask"], connectivity=2)
        comp_ids = [c for c in np.unique(comp[near]) if c]
        cut_comp = measure.label(cut, connectivity=2)
        tbl = ["| stage | what is there |", "|---|---|"]
        cut_ids = [c for c in np.unique(cut_comp[near]) if c]
        for cid in cut_ids:
            pr = piece_props(cut_comp == cid)
            tbl.append(f"| at the cut | component of {pr['area']} px^2, solidity {pr.get('solidity')}, aspect {pr.get('aspect')} |")
        fill_comp = measure.label(filled, connectivity=2)
        for cid in [c for c in np.unique(fill_comp[near]) if c]:
            pr = piece_props(fill_comp == cid)
            tbl.append(f"| after hole fill (<= {lacunae.FILL_HOLES_PX2} px^2) | {pr['area']} px^2, solidity {pr.get('solidity')} |")
        for cid in comp_ids:
            pr = piece_props(comp == cid)
            tbl.append(f"| after r=1 opening | {pr['area']} px^2, solidity {pr.get('solidity')}, aspect {pr.get('aspect')} |")
            ws_ids = [w for w in np.unique(d["ws_labels"][comp == cid]) if w]
            ws_areas = sorted([int((d["ws_labels"] == w).sum()) for w in ws_ids], reverse=True)
            tbl.append(f"| watershed | {len(ws_ids)} piece(s) in that component: {ws_areas} px^2 |")
            m_ids = [m for m in np.unique(d["labels"][comp == cid]) if m]
            regs = {r.label: r for r in measure.regionprops(d["labels"])}
            for m in m_ids:
                r = regs[m]
                v = verdict(r, ch.shape)
                cy, cx = r.centroid
                tbl.append(f"| after re-merge, filter | piece at ({cx:.0f},{cy:.0f}): {r.area} px^2, solidity "
                           f"{r.solidity:.3f}, aspect {r.axis_major_length / max(r.axis_minor_length, 1e-9):.2f}: **{v}** |")
                rows_all.append({"case": f"{name} ({x},{y})", "piece_x": round(cx), "piece_y": round(cy),
                                 "area_px2": int(r.area), "solidity": round(float(r.solidity), 3),
                                 "aspect": round(float(r.axis_major_length / max(r.axis_minor_length, 1e-9)), 2),
                                 "verdict": v})
        lines += tbl + [""]
        # crop: raw | cut | final (kept green, rejected pieces red)
        half = 70
        raw_c, (x0, y0) = C.crop(C.to_rgb(ch), x, y, half)
        cut_c, _ = C.crop(C.to_rgb(cut), x, y, half)
        kept_ids = set(int(v) for v in d["kept_labels"])
        lab_c, _ = C.crop(d["labels"], x, y, half)
        fin = raw_c.copy()
        rej = np.isin(lab_c, [m for m in np.unique(lab_c) if m and m not in kept_ids])
        kep = np.isin(lab_c, [m for m in np.unique(lab_c) if m in kept_ids])
        fin = C.outline(fin, rej, (255, 60, 60))
        fin = C.outline(fin, kep, (0, 255, 0))
        fin = C.mark(fin, x - x0, y - y0, color=(255, 255, 0), r=3)
        C.write_png(OUT / "2.1_crops" / f"{name}_x{x}_y{y}.png",
                    C.panel_row([raw_c, cut_c, fin], [f"{name} ({x},{y}) raw", f"red >= t_hi {t_hi:.3f}",
                                                       "kept green, rejected red"], scale=2))
    C.write_csv(OUT / "2.1_missed_bodies.csv", pd.DataFrame(rows_all))
    C.write_text(out_md, "\n".join(lines) + "\n")
    print("\n".join(lines))


# 2.2 cuts against brightness ----------------------------------------------------

def item_2_2() -> None:
    import canaliculi
    path = OUT / "2.2_cuts_vs_brightness.csv"
    if path.is_file():
        print(pd.read_csv(path).to_string(index=False))
        return
    rows = []
    for p in C.IMAGE_PATHS:
        d = C.load(p)
        ch = d["channel"]
        # Preprocessed before the final division by its own maximum, so t_lo
        # can be expressed in raw units.
        img = ndi.gaussian_filter(ch, canaliculi.SMOOTH_SIGMA_PX)
        img = morphology.white_tophat(img, morphology.disk(canaliculi.TOPHAT_RADIUS_PX))
        img = canaliculi._subtract_background_mode(img)
        peak = float(img.max())
        prep = d["preprocessed"]
        rows.append({
            "image": d["short"],
            "t_hi": d["t_hi"], "t_lo": d["t_lo"],
            "red_mean": float(ch.mean()), "red_median": float(np.median(ch)),
            "red_p99": float(np.percentile(ch, 99)), "red_p999": float(np.percentile(ch, 99.9)),
            "red_saturated_fraction": float((ch >= 1.0).mean()),
            "t_hi_over_p99": d["t_hi"] / float(np.percentile(ch, 99)),
            "fraction_above_t_hi": float((ch >= d["t_hi"]).mean()),
            "prep_peak_raw_units": peak,
            "t_lo_raw_units": d["t_lo"] * peak,
            "prep_mean": float(prep.mean()), "prep_p99": float(np.percentile(prep, 99)),
            "t_lo_over_prep_p99": d["t_lo"] / float(np.percentile(prep, 99)),
            "fraction_above_t_lo": float((prep > d["t_lo"]).mean()),
            "lacuna_count": d["lacuna_count"],
            "median_area_px2": d["lacuna_summary"]["area_px2"]["median"],
        })
    df = pd.DataFrame(rows)
    C.write_csv(path, df)
    corr = []
    for cut, stats in (("t_hi", ["red_mean", "red_median", "red_p99", "red_p999", "red_saturated_fraction"]),
                       ("t_lo", ["prep_mean", "prep_p99", "prep_peak_raw_units"]),
                       ("t_lo_raw_units", ["red_mean", "red_p99", "prep_peak_raw_units"])):
        for s in stats:
            rho, pv = spearmanr(df[cut], df[s])
            r = np.corrcoef(df[cut], df[s])[0, 1]
            corr.append({"cut": cut, "statistic": s, "spearman_rho": rho, "spearman_p": pv, "pearson_r": r, "n": len(df)})
    cdf = pd.DataFrame(corr)
    C.write_csv(OUT / "2.2_correlations.csv", cdf)
    print(df.to_string(index=False))
    print(cdf.to_string(index=False))


# Grid runner (2.3, 2.4) ------------------------------------------------------------

def setting_name(hi_scale, lo_scale, hi_value=None, lo_value=None) -> str:
    a = f"hi{hi_scale:g}" if hi_value is None else f"hiV{hi_value:.4f}"
    b = f"lo{lo_scale:g}" if lo_value is None else f"loV{lo_value:.4f}"
    return f"{a}_{b}"


def run_setting(args) -> str:
    """One image at one setting. Writes grid/<image>__<setting>.json and
    returns its path. Skips if it exists."""
    name, hi_scale, lo_scale, hi_value, lo_value = args
    sname = setting_name(hi_scale, lo_scale, hi_value, lo_value)
    out = GRID / f"{name}__{sname}.json"
    if out.is_file():
        return str(out)
    d = C.load(name)
    t_hi = hi_value if hi_value is not None else d["t_hi"] * hi_scale
    t_lo = lo_value if lo_value is not None else d["t_lo"] * lo_scale
    if hi_value is None and hi_scale == 1.0:
        labels, kept, lac_rows = d["labels"], d["kept"], d["lacuna_rows"]
    else:
        lac = C.lacuna_stage(d["channel"], t_hi=t_hi)
        labels, kept, lac_rows = lac["labels"], lac["kept"], lac["rows"]
    if lo_value is None and lo_scale == 1.0 and hi_value is None and hi_scale == 1.0:
        cell_rows, dens, nb = d["cell_rows"], d["field"]["canalicular_length_density_per_px"], d["n_bridges"]
        skel_px = int(d["skeleton"].sum())
    else:
        signal = d["signal"] if (lo_value is None and lo_scale == 1.0) else None
        net = C.network_stage(d["channel"], labels, kept, preprocessed=d["preprocessed"], flagged=d["flagged"],
                              t_lo=t_lo, signal=signal)
        cell_rows, dens, nb = net["cell_rows"], net["density"], len(net["bridges"])
        skel_px = int(net["skeleton"].sum())
    h = C.headline(lac_rows, cell_rows, dens, nb)
    C.write_json(out, {"image": name, "setting": sname, "t_hi": t_hi, "t_lo": t_lo,
                       "hi_scale": hi_scale, "lo_scale": lo_scale, "skeleton_px": skel_px,
                       "headline": h, "lacuna_rows": lac_rows, "cell_rows": cell_rows})
    return str(out)


def collect(jobs) -> pd.DataFrame:
    rows = []
    for name, hs, ls, hv, lv in jobs:
        f = GRID / f"{name}__{setting_name(hs, ls, hv, lv)}.json"
        j = json.loads(f.read_text())
        rows.append({"image": name, "setting": j["setting"], "t_hi": j["t_hi"], "t_lo": j["t_lo"],
                     "skeleton_px": j["skeleton_px"], **j["headline"]})
    return pd.DataFrame(rows)


def relative_to_default(df: pd.DataFrame, default_setting: str) -> pd.DataFrame:
    meas = ["lacuna_count", "interior_count", "median_area_px2", "roots_per_cell", "ring30_per_cell_px",
            "ring60_per_cell_px", "field_density_per_px", "bridges", "skeleton_px"]
    base = df[df.setting == default_setting].set_index("image")
    rows = []
    for _, r in df.iterrows():
        b = base.loc[r["image"]]
        row = {"image": r["image"], "setting": r["setting"]}
        for m in meas:
            row[m] = r[m]
            row[f"{m}_pct"] = 100.0 * (r[m] - b[m]) / b[m] if b[m] else float("nan")
        rows.append(row)
    return pd.DataFrame(rows)


def run_jobs(jobs, workers: int = 8) -> None:
    todo = [j for j in jobs if not (GRID / f"{j[0]}__{setting_name(*j[1:])}.json").is_file()]
    print(f"{len(jobs)} runs, {len(todo)} to compute")
    if todo:
        with ProcessPoolExecutor(max_workers=min(workers, len(todo))) as ex:
            for path in ex.map(run_setting, todo):
                print("done", Path(path).name, flush=True)


def item_2_3() -> None:
    images = ["542_z06", "543-2", "682_z29"]
    jobs = [(n, s, s, None, None) for n in images for s in (1.0, 0.9, 1.1)]
    run_jobs(jobs)
    df = collect(jobs)
    rel = relative_to_default(df, setting_name(1.0, 1.0))
    C.write_csv(OUT / "2.3_quick_sensitivity.csv", rel)
    cols = ["image", "setting", "lacuna_count", "interior_count", "median_area_px2", "roots_per_cell",
            "ring30_per_cell_px", "field_density_per_px", "bridges"]
    md = ["# 2.3 Quick sensitivity: both cuts scaled together", "",
          "Pre-validation, px. hi = t_hi scale, lo = t_lo scale. Per-cell values are means over interior lacunae.", "",
          C.md_table(rel[cols]), "",
          "Change against the default (percent):", "",
          C.md_table(rel[["image", "setting"] + [c + "_pct" for c in cols[2:]]], floatfmt="{:+.1f}")]
    C.write_text(OUT / "2.3_quick_sensitivity.md", "\n".join(md) + "\n")
    print(rel[cols].to_string(index=False))
    print(rel[["image", "setting"] + [c + "_pct" for c in cols[2:]]].to_string(index=False))


ITEMS = {"2.1": item_2_1, "2.2": item_2_2, "2.3": item_2_3}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    GRID.mkdir(parents=True, exist_ok=True)
    item = sys.argv[1]
    ok = C.run_item(item, ITEMS[item])
    sys.exit(0 if ok else 1)
