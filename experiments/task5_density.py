"""Task 5: density denominator, the other channels, a draft bone ROI.

    python -u experiments/task5_density.py 5.2   # green and blue channels; draft bone ROI (run first)
    python -u experiments/task5_density.py 5.1   # field density three ways
    python -u experiments/task5_density.py 5.3   # the 542_z06 vertical trace
    python -u experiments/task5_density.py 5.4   # ROI overlays for all 8; hand-edited ROI masks (pass 2)

Outputs in results_experiments/task5/. PRE-VALIDATION, PIXEL units,
(x, y) = (column, row). The ROI is a DRAFT for Karim to review; nothing in
the pipeline uses it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from scipy import ndimage as ndi
from skimage import measure, morphology
from skimage.io import imread

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402

OUT = C.OUT_ROOT / "task5"
ROI_DIR = OUT / "roi_draft"
ROI_EDITED_DIR = OUT / "roi_edited"  # optional hand-edited masks, <image>.png, white = bone

# Draft ROI parameters. Both channels are smoothed with a Gaussian of this
# sigma (px) before any rule, so the rules see regions, not threads.
ROI_SIGMA_PX = 10
# No tissue: smoothed blue below this (8-bit grey levels). Pooled over the 8
# images the smoothed blue has a separate low mode at 3 to 6 in the three
# 682 images (the dark corners), a dip at 6 to 7.5 in all three, and the
# bulk from 7.5 to 12 upward; the 542 and 543 images have no value below
# 10.5. 7.5 is the upper edge of the dip (table in 5.2_roi_draft.md).
ROI_NO_TISSUE_BLUE_MAX = 7.5
# Purple: smoothed blue / (smoothed red + 1) above this. There is no gap in
# this ratio in any image. The value is an anchor, not a gap: the largest
# ratio found in the three 543 images, which show no purple region by eye
# (543-2 0.49, 543_3 0.42, 543_z13 0.72). A DRAFT choice, listed under
# Decisions needed.
ROI_PURPLE_RATIO_MIN = 0.72


def channels(path: Path):
    a = imread(path)[..., :3].astype(float)
    return a[..., 0], a[..., 1], a[..., 2]


def roi_parts(path: Path) -> dict:
    r, _g, b = channels(path)
    sr, sb = ndi.gaussian_filter(r, ROI_SIGMA_PX), ndi.gaussian_filter(b, ROI_SIGMA_PX)
    ratio = sb / (sr + 1.0)
    no_tissue = sb < ROI_NO_TISSUE_BLUE_MAX
    purple = (ratio > ROI_PURPLE_RATIO_MIN) & ~no_tissue
    return {"no_tissue": no_tissue, "purple": purple, "roi": ~(no_tissue | purple), "ratio": ratio, "sb": sb, "sr": sr}


def roi_mask(path: Path) -> tuple[np.ndarray, str]:
    """The bone ROI for one image: a hand-edited mask from roi_edited/ if one
    exists (white = bone), else the saved draft."""
    name = C.short(path)
    edited = ROI_EDITED_DIR / f"{name}.png"
    if edited.is_file():
        return np.asarray(Image.open(edited).convert("L")) > 127, "edited"
    draft = ROI_DIR / f"{name}_roi.png"
    if draft.is_file():
        return np.asarray(Image.open(draft).convert("L")) > 127, "draft"
    return roi_parts(path)["roi"], "draft (recomputed)"


def roi_overlay(path: Path, parts: dict, d: dict) -> np.ndarray:
    r, _g, b = channels(path)
    rgb = np.stack([r, np.zeros_like(r), b], axis=-1).clip(0, 255).astype(np.uint8)
    rgb = C.paint(rgb, parts["no_tissue"], (128, 128, 128), alpha=0.6)
    rgb = C.paint(rgb, parts["purple"], (0, 220, 220), alpha=0.45)
    rgb = C.paint(rgb, d["flagged"], (255, 255, 0), alpha=0.25)
    rgb = C.outline(rgb, parts["roi"], (255, 255, 255), thick=2)
    return C.downscale(rgb, 2)


# 5.2 channels and the ROI draft -----------------------------------------------------

def item_5_2() -> None:
    table = OUT / "5.2_channels.csv"
    rows = []
    for p in C.IMAGE_PATHS:
        name = C.short(p)
        d = C.load(p)
        r, g, b = channels(p)
        parts = roi_parts(p)
        lac = d["lacuna_id_map"] > 0
        flagged = d["flagged"]
        matrix = ~lac & ~flagged & ~parts["no_tissue"]
        rows.append({
            "image": name,
            "green_mean": g.mean(), "green_max": g.max(),
            "blue_mean": b.mean(), "blue_p99": np.percentile(b, 99), "blue_max": b.max(),
            "corr_red_blue": np.corrcoef(r.ravel(), b.ravel())[0, 1],
            "blue_in_lacunae": b[lac].mean(), "blue_in_matrix": b[matrix].mean(),
            "blue_in_flagged": b[flagged].mean() if flagged.any() else float("nan"),
            "blue_on_skeleton": b[d["skeleton"]].mean(),
            "blue_over_red_matrix": (b[matrix] / (r[matrix] + 1)).mean(),
            "no_tissue_fraction": parts["no_tissue"].mean(), "purple_fraction": parts["purple"].mean(),
            "roi_fraction": parts["roi"].mean(),
            "purple_overlap_with_flagged": (parts["purple"] & flagged).sum() / max(1, parts["purple"].sum()),
            "kept_lacunae_outside_roi": int(sum(1 for lid in range(1, d["lacuna_count"] + 1)
                                               if (~parts["roi"][d["lacuna_id_map"] == lid]).mean() > 0.5)),
        })
        mask_path = ROI_DIR / f"{name}_roi.png"
        if not mask_path.is_file():
            C.write_png(mask_path, np.stack([(parts["roi"] * 255).astype(np.uint8)] * 3, axis=-1))
        ov = OUT / "5.2_roi_overlays" / f"{name}_roi_overlay.png"
        if not ov.is_file() and (parts["no_tissue"].any() or parts["purple"].any()):
            C.write_png(ov, roi_overlay(p, parts, d))
        pan = OUT / "5.2_channel_panels" / f"{name}_red_blue_ratio.png"
        if not pan.is_file():
            def st(x, lo, hi):
                return (np.clip((x - lo) / (hi - lo), 0, 1) * 255).astype(np.uint8)
            panels = [np.stack([st(r, 0, 255), np.zeros_like(r, np.uint8), st(b, 0, 255)], -1),
                      np.stack([st(b, np.percentile(b, 1), np.percentile(b, 99.5))] * 3, -1),
                      np.stack([st(parts["ratio"], 0, 1.2)] * 3, -1)]
            panels = [C.downscale(x, 4) for x in panels]
            C.write_png(pan, C.panel_row(panels, [f"{name} red+blue", "blue, stretched", "smoothed blue/red, 0 to 1.2"]))
        print(name, "done")
    df = pd.DataFrame(rows)
    C.write_csv(table, df)

    # Distributions behind the two ROI thresholds.
    sb_edges = np.arange(0, 22.5, 1.5)
    ratio_edges = np.round(np.arange(0, 2.3, 0.1), 2)
    sb_rows, ratio_rows = [], []
    for p in C.IMAGE_PATHS:
        parts = roi_parts(p)
        h, _ = np.histogram(parts["sb"], bins=sb_edges)
        sb_rows.append([C.short(p)] + h.tolist())
        h, _ = np.histogram(parts["ratio"], bins=ratio_edges)
        ratio_rows.append([C.short(p)] + h.tolist())
    sb_df = pd.DataFrame(sb_rows, columns=["image"] + [f"{a:g}-{b:g}" for a, b in zip(sb_edges[:-1], sb_edges[1:])])
    ratio_df = pd.DataFrame(ratio_rows, columns=["image"] + [f"{a:.1f}-{b:.1f}" for a, b in zip(ratio_edges[:-1], ratio_edges[1:])])
    C.write_csv(OUT / "5.2_hist_smoothed_blue.csv", sb_df)
    C.write_csv(OUT / "5.2_hist_blue_red_ratio.csv", ratio_df)
    md = ["# 5.2 Green and blue channels; draft bone ROI", "",
          "Pre-validation, 8-bit grey levels. matrix = pixels outside kept lacunae, outside the flagged",
          "(canal) mask and inside tissue. Panels per image in `5.2_channel_panels/` (red and blue as",
          "magenta, blue alone, smoothed blue over red).", "",
          C.md_table(df, floatfmt="{:.3f}"), "",
          f"## The draft ROI rule (sigma {ROI_SIGMA_PX} px smoothing of both channels)", "",
          f"- no tissue: smoothed blue < {ROI_NO_TISSUE_BLUE_MAX}",
          f"- purple: smoothed blue / (smoothed red + 1) > {ROI_PURPLE_RATIO_MIN}, outside no tissue",
          "- bone ROI: everything else. Masks in `roi_draft/<image>_roi.png` (white = bone). Overlays in",
          "  `5.2_roi_overlays/`: no tissue grey, purple cyan, flagged canal mask yellow, ROI border white.", "",
          "Smoothed blue, pixel counts per bin (the no-tissue threshold sits at the top of the 6 to 7.5 dip):", "",
          C.md_table(sb_df), "",
          "Smoothed blue / red, pixel counts per bin (no gap in any image; the purple threshold is the",
          "largest value in the three 543 images, which have no purple region by eye):", "",
          C.md_table(ratio_df), ""]
    C.write_text_once(OUT / "5.2_roi_draft.md", "\n".join(md))
    print(df.to_string(index=False))


# 5.1 density three ways --------------------------------------------------------------

def item_5_1() -> None:
    rows = []
    for p in C.IMAGE_PATHS:
        d = C.load(p)
        skel, lac, flagged = d["skeleton"], d["lacuna_id_map"] > 0, d["flagged"]
        roi, source = roi_mask(p)
        n = skel.size
        current = C.density(skel, lac)
        no_flag = C.density(skel, lac, area_mask=~flagged)
        in_roi = C.density(skel, lac, area_mask=roi)
        both = C.density(skel, lac, area_mask=roi & ~flagged)
        rows.append({
            "image": d["short"],
            "density_current": current,
            "density_without_flagged": no_flag,
            "density_in_roi": in_roi,
            "density_in_roi_without_flagged": both,
            "pct_change_without_flagged": 100 * (no_flag - current) / current,
            "pct_change_in_roi": 100 * (in_roi - current) / current,
            "pct_change_roi_and_flagged": 100 * (both - current) / current,
            "area_removed_flagged_px2": int((flagged & ~lac).sum()),
            "area_removed_flagged_pct": 100 * (flagged & ~lac).sum() / (n - lac.sum()),
            "skeleton_removed_flagged_px": int((skel & flagged).sum()),
            "area_removed_roi_px2": int((~roi & ~lac).sum()),
            "area_removed_roi_pct": 100 * (~roi & ~lac).sum() / (n - lac.sum()),
            "skeleton_removed_roi_px": int((skel & ~roi).sum()),
            "density_inside_flagged": float((skel & flagged).sum() / max(1, (flagged & ~lac).sum())),
            "density_outside_roi": float((skel & ~roi).sum() / max(1, (~roi & ~lac).sum())),
            "roi_source": source,
        })
    df = pd.DataFrame(rows)
    C.write_csv(OUT / "5.1_density_three_ways.csv", df)
    cols1 = ["image", "density_current", "density_without_flagged", "density_in_roi", "density_in_roi_without_flagged",
             "pct_change_without_flagged", "pct_change_in_roi", "pct_change_roi_and_flagged"]
    cols2 = ["image", "area_removed_flagged_px2", "area_removed_flagged_pct", "skeleton_removed_flagged_px",
             "density_inside_flagged", "area_removed_roi_px2", "area_removed_roi_pct", "skeleton_removed_roi_px",
             "density_outside_roi", "roi_source"]
    md = ["# 5.1 Field density three ways", "",
          "Pre-validation, px^-1. current: all skeleton px over (field minus lacunae), as the pipeline",
          "reports. without_flagged: the flagged canal mask (already dilated 4 px by the pipeline) removed",
          "from both the skeleton and the area. in_roi: skeleton and area restricted to the draft bone ROI",
          "of 5.2. The last column does both.", "",
          C.md_table(df[cols1], floatfmt="{:.5g}"), "",
          "What is removed:", "",
          C.md_table(df[cols2], floatfmt="{:.4g}"), ""]
    C.write_text_once(OUT / "5.1_density_three_ways.md", "\n".join(md))
    print(df[cols1].to_string(index=False))
    print(df[cols2].to_string(index=False))


# 5.3 the 542_z06 vertical trace ---------------------------------------------------------

TRACE_X = (515, 541)  # corridor around the line at x about 525 to 532 (looked at in a crop first)
TRACE_Y = (590, 900)  # from the task text


def item_5_3() -> None:
    d = C.load("542_z06")
    skel, flagged = d["skeleton"], d["flagged"]
    x0, x1 = TRACE_X
    y0, y1 = TRACE_Y
    corridor = np.zeros_like(skel)
    corridor[y0:y1 + 1, x0:x1] = True
    in_corr = skel & corridor
    # The trace itself: skeleton px in the corridor that belong to a
    # vertical straight run of at least 8 px, plus the rows the line covers.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from task1_artefact import runs_mask
    vert = runs_mask(skel, "v") & corridor
    rows_with = np.unique(np.nonzero(in_corr)[0])
    comp = measure.label(skel, connectivity=2)
    ids, counts = np.unique(comp[in_corr], return_counts=True)
    main = ids[np.argmax(counts)] if ids.size else 0
    main_len_total = int((comp == main).sum()) if main else 0
    total = int(skel.sum())
    roi, source = roi_mask(C.image_path("542_z06"))
    res = {
        "corridor_x": [x0, x1], "corridor_y": [y0, y1],
        "skeleton_px_in_corridor": int(in_corr.sum()),
        "share_of_total_skeleton": in_corr.sum() / total,
        "vertical_run_px_in_corridor": int(vert.sum()),
        "share_vertical_runs_of_total": vert.sum() / total,
        "rows_of_corridor_with_skeleton": int(rows_with.size), "rows_in_corridor": y1 - y0 + 1,
        "main_component_px_total": main_len_total,
        "main_component_share_of_total": main_len_total / total,
        "corridor_px_inside_flagged": int((in_corr & flagged).sum()),
        "corridor_px_outside_roi_draft": int((in_corr & ~roi).sum()),
        "total_skeleton_px": total,
        "field_density_current": d["field"]["canalicular_length_density_per_px"],
        "field_density_without_corridor_skeleton": float((skel & ~corridor).sum() / (skel.size - (d["lacuna_id_map"] > 0).sum())),
    }
    res["density_change_pct_if_removed"] = 100 * (res["field_density_without_corridor_skeleton"] - res["field_density_current"]) / res["field_density_current"]
    C.write_json(OUT / "5.3_542_z06_trace.json", res)
    # crop
    sl = (slice(540, 950), slice(440, 640))
    raw = C.to_rgb(d["channel"])[sl]
    sk = C.paint(raw // 2, skel[sl], (0, 255, 0))
    sk = C.paint(sk, in_corr[sl], (255, 60, 60))
    sk = C.outline(sk, flagged[sl], (255, 0, 255))
    sk = C.outline(sk, corridor[sl], (255, 255, 0))
    C.write_png(OUT / "5.3_542_z06_trace.png",
                C.panel_row([raw, sk], ["542_z06 x 440-640 y 540-950 raw",
                                        "skeleton green, corridor px red, canal mask magenta"], scale=2))
    for k, v in res.items():
        print(k, v)


ITEMS = {"5.1": item_5_1, "5.2": item_5_2, "5.3": item_5_3}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    item = sys.argv[1]
    ok = C.run_item(item, ITEMS[item])
    sys.exit(0 if ok else 1)
