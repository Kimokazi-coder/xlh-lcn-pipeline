"""Task 1: acquisition artefact.

    python -u experiments/task1_artefact.py 1.1   # TIFF tags and 8-bit histogram facts
    python -u experiments/task1_artefact.py 1.2   # 2D FFT peaks; row and column banding
    python -u experiments/task1_artefact.py 1.3   # axis-aligned skeleton runs; lattice crops
    python -u experiments/task1_artefact.py 1.4   # notch filter variant (pass 2)

Outputs in results_experiments/task1/. PRE-VALIDATION, PIXEL units,
(x, y) = (column, row).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import tifffile
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402

OUT = C.OUT_ROOT / "task1"


# 1.1 TIFF tags ----------------------------------------------------------------

def item_1_1() -> None:
    csv_path = OUT / "1.1_tiff_tags.csv"
    if csv_path.is_file():
        print("1.1 done already")
        return
    rows = []
    for p in C.IMAGE_PATHS:
        with tifffile.TiffFile(p) as t:
            pg = t.pages[0]
            tags = {tag.name: tag.value for tag in pg.tags.values()}
            arr = pg.asarray()
        res_x = tags.get("XResolution")
        unit = tags.get("ResolutionUnit")
        red = arr[..., 0]
        hist = np.bincount(red.ravel(), minlength=256)
        lo, hi = int(red.min()), int(red.max())
        inner = hist[lo:hi + 1]
        row = {
            "image": C.short(p),
            "file": p.name,
            "bytes": p.stat().st_size,
            "shape": "x".join(str(s) for s in arr.shape),
            "dtype": str(arr.dtype),
            "bits_per_sample": str(tags.get("BitsPerSample")),
            "samples_per_pixel": tags.get("SamplesPerPixel"),
            "photometric": str(getattr(tags.get("PhotometricInterpretation"), "name", tags.get("PhotometricInterpretation"))),
            "compression": str(getattr(tags.get("Compression"), "name", tags.get("Compression"))),
            "software": tags.get("Software", ""),
            "image_description": str(tags.get("ImageDescription", "")).replace("\n", " ")[:80],
            "resolution_x": f"{res_x[0]}/{res_x[1]}" if res_x else "",
            "resolution_unit": str(getattr(unit, "name", unit)) if unit is not None else "",
            "extra_samples": str(tags.get("ExtraSamples", "")),
            "alpha_constant": (bool((arr[..., 3] == arr[..., 3].flat[0]).all()) if arr.shape[-1] == 4 else ""),
            "red_min": lo,
            "red_max": hi,
            "red_distinct_levels": int((hist > 0).sum()),
            "red_empty_levels_inside_range": int((inner == 0).sum()),
            "red_saturated_fraction": float((red == 255).mean()),
            "red_zero_fraction": float((red == 0).mean()),
            "green_mean": float(arr[..., 1].mean()),
            "green_max": int(arr[..., 1].max()),
            "blue_mean": float(arr[..., 2].mean()),
            "blue_max": int(arr[..., 2].max()),
        }
        rows.append(row)
    df = pd.DataFrame(rows)
    C.write_csv(csv_path, df)
    cols = ["image", "dtype", "bits_per_sample", "samples_per_pixel", "compression", "software",
            "image_description", "resolution_x", "resolution_unit", "red_distinct_levels",
            "red_empty_levels_inside_range", "red_saturated_fraction"]
    text = ["# 1.1 TIFF tags", "",
            "Pre-validation. All values read with tifffile from the first (only) page.", "",
            C.md_table(df[cols], floatfmt="{:.4f}"),
            "red_empty_levels_inside_range counts 8-bit levels between the red minimum and maximum that",
            "no pixel uses. A value above 0 means the histogram is combed, the sign of a contrast stretch",
            "applied after the data were already 8-bit.", ""]
    C.write_text(OUT / "1.1_tiff_tags.md", "\n".join(text))
    print(df[cols].to_string(index=False))


# 1.2 FFT ----------------------------------------------------------------------

# Frequencies below this radius (in FFT bins of a 1024 px axis, i.e. periods
# above 1024 / 16 = 64 px) are left out of the peak search: there the
# spectrum is dominated by the cells and canals themselves. A reporting
# choice, not a tuned value.
FFT_MIN_RADIUS_BINS = 16
# Local spectrum background: the median of log power in a square window of
# this many bins around each frequency.
FFT_BG_WINDOW = 21
# Peaks listed per image and channel (from one half plane; the spectrum of
# a real image is point symmetric).
FFT_TOP_N = 8


def power_spectrum(img: np.ndarray) -> np.ndarray:
    a = img.astype(float)
    a = a - a.mean()
    w = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    F = np.fft.fftshift(np.fft.fft2(a * w))
    return np.abs(F) ** 2


def spectrum_peaks(P: np.ndarray) -> tuple[pd.DataFrame, np.ndarray]:
    """Local maxima of the power spectrum that stand out from their local
    background. Returns the peak table and the ratio map (power / local
    median power)."""
    n0, n1 = P.shape
    logp = np.log10(P + 1e-12)
    bg = ndi.median_filter(logp, size=FFT_BG_WINDOW, mode="wrap")
    ratio_log = logp - bg
    cy, cx = n0 // 2, n1 // 2
    yy, xx = np.mgrid[0:n0, 0:n1]
    v, u = yy - cy, xx - cx
    radius = np.hypot(u, v)
    local_max = ratio_log == ndi.maximum_filter(ratio_log, size=5, mode="wrap")
    # one half plane: v > 0, or v == 0 and u > 0
    half = (v > 0) | ((v == 0) & (u > 0))
    cand = local_max & half & (radius >= FFT_MIN_RADIUS_BINS)
    idx = np.argwhere(cand)
    vals = ratio_log[cand]
    order = np.argsort(vals)[::-1][:FFT_TOP_N]
    rows = []
    for k in order:
        r, c = idx[k]
        fu, fv = (c - cx) / n1, (r - cy) / n0  # cycles per px along x and y
        f = np.hypot(fu, fv)
        angle = float(np.degrees(np.arctan2(fv, fu))) % 180.0
        rows.append({
            "u_bin": int(c - cx), "v_bin": int(r - cy),
            "period_px": round(1.0 / f, 2),
            "period_x_px": round(1.0 / abs(fu), 2) if fu != 0 else float("inf"),
            "period_y_px": round(1.0 / abs(fv), 2) if fv != 0 else float("inf"),
            "wave_angle_deg": round(angle, 1),
            "power_over_local_median": round(float(10 ** vals[k]), 1),
        })
    return pd.DataFrame(rows), ratio_log


def banding(profile: np.ndarray) -> dict:
    """Periodic banding in a row or column mean profile: detrend with a
    31 px moving mean, then the strongest 1D spectral peak with period
    2 to 64 px, its power against the median of the spectrum within 10
    bins of it (the local spectrum), and the detrended profile's standard
    deviation in 8-bit grey levels. For a profile with no periodic
    component, power over local median behaves like Exp/ln 2, so the
    largest of the ~500 bins tested is expected near log2(500), about 9."""
    p = profile.astype(float)
    trend = ndi.uniform_filter1d(p, size=31, mode="reflect")
    d = p - trend
    spec = np.abs(np.fft.rfft(d * np.hanning(d.size))) ** 2
    freqs = np.fft.rfftfreq(d.size)
    band = (freqs >= 1 / 64) & (freqs <= 0.5)
    local_med = ndi.median_filter(spec, size=21, mode="nearest")
    ratio = np.where(band, spec / np.maximum(local_med, 1e-12), -1)
    k = int(np.argmax(ratio))
    return {
        "period_px": round(1.0 / freqs[k], 2),
        "power_over_local_median": round(float(ratio[k]), 1),
        "noise_expected_max": round(float(np.log2(band.sum())), 1),
        "period4_power_over_local_median": round(float(spec[np.argmin(abs(freqs - 0.25))] /
                                                      max(local_med[np.argmin(abs(freqs - 0.25))], 1e-12)), 1),
        "detrended_sd_grey": round(float(d.std()), 3),
    }


def folded_amplitude(img: np.ndarray, period: int, axis: int) -> float:
    """Peak-to-peak of the image mean folded at `period` px along x
    (axis=1) or y (axis=0), in the image's units. A 32 px moving mean
    along that axis is removed first, so a brightness gradient across the
    field does not show up as a phase difference (a 32 px mean cancels
    periods 2 and 4 exactly, so they survive the detrending)."""
    img = img - ndi.uniform_filter1d(img, size=32, axis=axis, mode="reflect")
    means = [img[:, k::period].mean() if axis == 1 else img[k::period, :].mean() for k in range(period)]
    return float(max(means) - min(means))


def spectrum_png(ratio_log: np.ndarray, peaks: pd.DataFrame) -> np.ndarray:
    """Black map of the spectrum with only the bins that stand out: grey
    where power over local median exceeds 10, white where it exceeds the
    noise reference (18). Top peaks circled in red. 2 x 2 max-pooled to
    512 px so single bins stay visible."""
    n0, n1 = ratio_log.shape
    ratio = 10 ** ratio_log
    g = np.zeros_like(ratio, dtype=np.uint8)
    g[ratio > 10] = 110
    g[ratio > 18] = 255
    g = g.reshape(n0 // 2, 2, n1 // 2, 2).max(axis=(1, 3))
    rgb = np.stack([g, g, g], axis=-1)
    rgb[n0 // 4, :] = np.maximum(rgb[n0 // 4, :], 40)
    rgb[:, n1 // 4] = np.maximum(rgb[:, n1 // 4], 40)
    for _, pk in peaks.iterrows():
        for s in (1, -1):
            x = n1 // 4 + s * int(pk["u_bin"]) // 2
            y = n0 // 4 + s * int(pk["v_bin"]) // 2
            rgb = C.mark(rgb, x, y, color=(255, 0, 0), r=6)
    return rgb


def item_1_2() -> None:
    peaks_csv = OUT / "1.2_fft_peaks.csv"
    band_csv = OUT / "1.2_banding.csv"
    per_img_dir = OUT / "1.2_per_image"
    all_peaks, all_band = [], []
    for p in C.IMAGE_PATHS:
        name = C.short(p)
        part = per_img_dir / f"{name}_peaks.csv"
        bpart = per_img_dir / f"{name}_banding.csv"
        if part.is_file() and bpart.is_file():
            all_peaks.append(pd.read_csv(part))
            all_band.append(pd.read_csv(bpart))
            continue
        d = C.load(p)
        raw = (d["channel"] * 255.0)
        prep = d["preprocessed"]
        pk_rows, b_rows, pngs = [], [], []
        for label, img in (("raw_red", raw), ("preprocessed", prep)):
            P = power_spectrum(img)
            pk, ratio_log = spectrum_peaks(P)
            n0, n1 = P.shape
            yy, xx = np.mgrid[0:n0, 0:n1]
            vv, uu = yy - n0 // 2, xx - n1 // 2
            half_plane = (vv > 0) | ((vv == 0) & (uu > 0))
            n_tested = int((half_plane & (np.hypot(uu, vv) >= FFT_MIN_RADIUS_BINS)).sum())
            pk["noise_expected_max"] = round(float(np.log2(n_tested)), 1)
            pk.insert(0, "image", name)
            pk.insert(1, "channel", label)
            pk_rows.append(pk)
            pngs.append(spectrum_png(ratio_log, pk))
            scale = 255.0 if label == "preprocessed" else 1.0  # grey levels for both
            g = img * scale
            exact = {}
            for tag, (du, dv) in (("x4", (256, 0)), ("y4", (0, 256)), ("x2", (512, 0)), ("y2", (0, 512))):
                rr, cc = (n0 // 2 + dv) % n0, (n1 // 2 + du) % n1
                exact[f"bin_{tag}_power_over_local_median"] = round(float(10 ** ratio_log[rr, cc]), 1)
            for axis_name, prof in (("row_means", g.mean(axis=1)), ("column_means", g.mean(axis=0))):
                b = banding(prof)
                b_rows.append({"image": name, "channel": label, "profile": axis_name, **b,
                               "fold4_x_pp_grey": round(folded_amplitude(g, 4, 1), 3),
                               "fold4_y_pp_grey": round(folded_amplitude(g, 4, 0), 3),
                               "fold2_x_pp_grey": round(folded_amplitude(g, 2, 1), 3),
                               "fold2_y_pp_grey": round(folded_amplitude(g, 2, 0), 3),
                               **exact})
        pkdf = pd.concat(pk_rows, ignore_index=True)
        bdf = pd.DataFrame(b_rows)
        C.write_png(per_img_dir / f"{name}_spectra.png",
                    C.panel_row(pngs, [f"{name} raw red: grey P/med > 10, white > 18",
                                       "preprocessed: same"]))
        C.write_csv(bpart, bdf)
        C.write_csv(part, pkdf)
        all_peaks.append(pkdf)
        all_band.append(bdf)
        print(f"{name} done")
    peaks = pd.concat(all_peaks, ignore_index=True)
    band = pd.concat(all_band, ignore_index=True)
    C.write_csv(peaks_csv, peaks)
    C.write_csv(band_csv, band)
    top = peaks.sort_values("power_over_local_median", ascending=False).groupby(["image", "channel"]).head(3)
    top = top.sort_values(["channel", "image"])
    md = ["# 1.2 FFT peaks and banding", "",
          "Pre-validation, px. 2D power spectrum of the raw red channel (8-bit grey levels) and of the",
          "preprocessed channel, Hann window, mean removed. Strength is power over the median power in a",
          "21 x 21 bin window around the frequency (the local spectrum). Periods above 64 px are left out",
          "(the cells and canals themselves). wave_angle_deg is the direction the intensity varies along",
          "(0 = along x, so the stripes are vertical; 90 = along y, horizontal stripes).", "",
          "Noise reference: where there is no periodic signal the periodogram is close to exponential, so",
          "power over local median behaves like Exp/ln 2 and the largest of N tested bins is expected near",
          "log2(N). noise_expected_max gives that value (about 18 for the ~260,000 bins of one half plane).",
          "A peak near it is what noise alone produces.", "",
          "## Strongest 3 peaks per image and channel", "",
          C.md_table(top, floatfmt="{:.2f}"), "",
          "## Exact-period bins and banding", "",
          "bin_x4 is the bin of period 4.00 px along x (u = 256, v = 0), bin_y4 the same along y, bin_x2 and",
          "bin_y2 the Nyquist bins. fold4_x_pp_grey is the peak-to-peak of the image mean folded at 4 px along",
          "x, in 8-bit grey levels (the preprocessed channel is scaled by 255 for this). The banding columns",
          "come from the row and column mean profiles after removing a 31 px moving mean.", "",
          C.md_table(band, floatfmt="{:.2f}"), ""]
    C.write_text_once(OUT / "1.2_fft.md", "\n".join(md))
    print(peaks.to_string(index=False))
    print(band.to_string(index=False))


# 1.3 axis-aligned skeleton runs --------------------------------------------------

RUN_MIN_PX = 8  # from the task text
TILE_PX = 128

LATTICE_BOX = (0, 380, 0, 250)  # x0, x1, y0, y1, from the task text (682_z08)


def runs_mask(skel: np.ndarray, direction: str, min_len: int = RUN_MIN_PX) -> np.ndarray:
    """Skeleton pixels lying in a straight run of at least min_len pixels
    along one direction: 'h' (along x), 'v' (along y), 'd1' (down-right
    diagonal), 'd2' (down-left diagonal)."""
    s = skel.astype(np.uint8)
    if direction == "v":
        return runs_mask(skel.T, "h", min_len).T
    if direction == "d2":
        return runs_mask(skel[:, ::-1], "d1", min_len)[:, ::-1]
    if direction == "h":
        out = np.zeros_like(skel, dtype=bool)
        for r in range(s.shape[0]):
            row = s[r]
            if not row.any():
                continue
            padded = np.concatenate([[0], row, [0]])
            diff = np.diff(padded)
            starts = np.where(diff == 1)[0]
            ends = np.where(diff == -1)[0]
            for a, b in zip(starts, ends):
                if b - a >= min_len:
                    out[r, a:b] = True
        return out
    if direction == "d1":
        out = np.zeros_like(skel, dtype=bool)
        n0, n1 = s.shape
        for k in range(-(n0 - 1), n1):
            diag = np.diagonal(s, offset=k)
            if not diag.any():
                continue
            padded = np.concatenate([[0], diag, [0]])
            diff = np.diff(padded)
            starts = np.where(diff == 1)[0]
            ends = np.where(diff == -1)[0]
            for a, b in zip(starts, ends):
                if b - a >= min_len:
                    for t in range(a, b):
                        r = t if k >= 0 else t - k
                        c = t + k if k >= 0 else t
                        out[r, c] = True
        return out
    raise ValueError(direction)


def item_1_3() -> None:
    table_csv = OUT / "1.3_axis_runs.csv"
    tiles_csv = OUT / "1.3_axis_runs_tiles.csv"
    rows, tiles = [], []
    for p in C.IMAGE_PATHS:
        d = C.load(p)
        skel = d["skeleton"]
        n = int(skel.sum())
        m = {k: runs_mask(skel, k) for k in ("h", "v", "d1", "d2")}
        axis = m["h"] | m["v"]
        diag = m["d1"] | m["d2"]
        row = {"image": d["short"], "skeleton_px": n,
               "share_h": m["h"].sum() / n, "share_v": m["v"].sum() / n,
               "share_axis_hv": axis.sum() / n,
               "share_d1": m["d1"].sum() / n, "share_d2": m["d2"].sum() / n,
               "share_diag": diag.sum() / n}
        x0, x1, y0, y1 = LATTICE_BOX
        box = np.zeros_like(skel)
        box[y0:y1, x0:x1] = True
        row["box_share_axis_hv"] = (axis & box).sum() / max(1, (skel & box).sum())
        row["outside_box_share_axis_hv"] = (axis & ~box).sum() / max(1, (skel & ~box).sum())
        rows.append(row)
        for ty in range(0, skel.shape[0], TILE_PX):
            for tx in range(0, skel.shape[1], TILE_PX):
                sl = (slice(ty, ty + TILE_PX), slice(tx, tx + TILE_PX))
                ns = int(skel[sl].sum())
                tiles.append({"image": d["short"], "tile_x0": tx, "tile_y0": ty, "skeleton_px": ns,
                              "axis_run_px": int(axis[sl].sum()), "diag_run_px": int(diag[sl].sum()),
                              "share_axis_hv": axis[sl].sum() / ns if ns else float("nan"),
                              "share_diag": diag[sl].sum() / ns if ns else float("nan")})
        # Heat map: skeleton with axis runs red, diagonal runs blue.
        rgb = C.to_rgb(d["channel"])
        rgb = (rgb * 0.6).astype(np.uint8)
        rgb = C.paint(rgb, skel, (200, 200, 200))
        rgb = C.paint(rgb, diag, (60, 140, 255))
        rgb = C.paint(rgb, axis, (255, 40, 40))
        C.write_png(OUT / "1.3_runs_overlay" / f"{d['short']}_axis_runs.png", C.downscale(rgb, 2))
        print(f"{d['short']} done")
    df = pd.DataFrame(rows)
    tdf = pd.DataFrame(tiles)
    C.write_csv(table_csv, df)
    C.write_csv(tiles_csv, tdf)
    print(df.to_string(index=False))
    top = tdf[tdf.skeleton_px >= 200].sort_values("share_axis_hv", ascending=False).head(15)
    print(top.to_string(index=False))
    lattice_crops()


def local_peak_table(img: np.ndarray, box, label: str) -> pd.DataFrame:
    x0, x1, y0, y1 = box
    sub = img[y0:y1, x0:x1].astype(float)
    P = power_spectrum(sub)
    n0, n1 = P.shape
    logp = np.log10(P + 1e-12)
    bg = ndi.median_filter(logp, size=11, mode="wrap")
    ratio = logp - bg
    cy, cx = n0 // 2, n1 // 2
    yy, xx = np.mgrid[0:n0, 0:n1]
    u, v = (xx - cx) / n1, (yy - cy) / n0
    f = np.hypot(u, v)
    lm = ratio == ndi.maximum_filter(ratio, size=5, mode="wrap")
    half = ((yy - cy) > 0) | (((yy - cy) == 0) & ((xx - cx) > 0))
    cand = lm & half & (f >= 1 / 32)
    idx = np.argwhere(cand)
    vals = ratio[cand]
    rows = []
    for k in np.argsort(vals)[::-1][:5]:
        r, c = idx[k]
        rows.append({"region": label, "period_px": round(1 / f[r, c], 2),
                     "wave_angle_deg": round(float(np.degrees(np.arctan2(v[r, c], u[r, c]))) % 180, 1),
                     "power_over_local_median": round(float(10 ** vals[k]), 1)})
    return pd.DataFrame(rows)


def lattice_crops() -> None:
    d = C.load("682_z08")
    raw = d["channel"]
    prep = d["preprocessed"]
    skel = d["skeleton"]
    x0, x1, y0, y1 = LATTICE_BOX
    # Control: a box of the same size in the same image, away from the
    # lattice, chosen as the box of that size with the most skeleton
    # outside the lattice box and its 64 px margin.
    w, h = x1 - x0, y1 - y0
    best, best_xy = -1, None
    for cy in range(0, 1024 - h + 1, 32):
        for cx in range(0, 1024 - w + 1, 32):
            if cx < x1 + 64 and cy < y1 + 64:
                continue
            s = int(skel[cy:cy + h, cx:cx + w].sum())
            if s > best:
                best, best_xy = s, (cx, cy)
    cx0, cy0 = best_xy
    ctrl = (cx0, cx0 + w, cy0, cy0 + h)
    panels = []
    for box, name in ((LATTICE_BOX, "lattice"), (ctrl, "control")):
        bx0, bx1, by0, by1 = box
        r = C.to_rgb(raw)[by0:by1, bx0:bx1]
        pp = C.to_rgb(prep)[by0:by1, bx0:bx1]
        sk = C.to_rgb(skel)[by0:by1, bx0:bx1]
        panels.append(C.panel_row([r, pp, sk], [f"682_z08 {name} x {bx0}-{bx1} y {by0}-{by1}: raw red",
                                                 "preprocessed", "skeleton"]))
    C.write_png(OUT / "1.3_682_z08_lattice_and_control.png", C.panel_grid(panels))
    # 3x zoom on a 96 px square in each box.
    zooms = []
    for box, name in ((LATTICE_BOX, "lattice"), (ctrl, "control")):
        bx0, _bx1, by0, _by1 = box
        zx, zy = bx0 + 40, by0 + 40
        sl = (slice(zy, zy + 96), slice(zx, zx + 96))
        zooms.append(C.panel_row([C.to_rgb(raw)[sl], C.to_rgb(prep)[sl], C.to_rgb(skel)[sl]],
                                 [f"{name} x{zx} y{zy} raw x3", "preprocessed", "skeleton"], scale=3))
    C.write_png(OUT / "1.3_682_z08_zoom.png", C.panel_grid(zooms))
    loc = pd.concat([
        local_peak_table(raw * 255, LATTICE_BOX, "lattice raw"),
        local_peak_table(raw * 255, ctrl, "control raw"),
        local_peak_table(prep, LATTICE_BOX, "lattice preprocessed"),
        local_peak_table(prep, ctrl, "control preprocessed"),
    ], ignore_index=True)
    C.write_csv(OUT / "1.3_local_fft_peaks.csv", loc)
    C.write_json(OUT / "1.3_control_box.json", {"control_box_x0_x1_y0_y1": list(ctrl)})
    print(loc.to_string(index=False))
    # Orientation of the threads under the skeleton, from the structure
    # tensor of the preprocessed channel (gradient sigma 1, window sigma 3).
    # A raster artefact puts sharp spikes at exactly 0 and 90 degrees; real
    # threads give broad peaks wherever the tissue points them.
    from skimage.feature import structure_tensor
    Arr, Arc, Acc = structure_tensor(prep, sigma=3, order="rc")
    theta = 0.5 * np.degrees(np.arctan2(2 * Arc, Acc - Arr))  # dominant gradient direction
    thread = (theta + 90.0) % 180.0  # thread direction, 0 = along x, 90 = along y
    edges = np.arange(0, 181, 5)
    rows = []
    for box, name in ((LATTICE_BOX, "lattice"), (ctrl, "control"), ((0, 1024, 0, 1024), "whole image")):
        bx0, bx1, by0, by1 = box
        sk = np.zeros_like(skel)
        sk[by0:by1, bx0:bx1] = skel[by0:by1, bx0:bx1]
        ang = thread[sk]
        h, _ = np.histogram(ang, bins=edges)
        d0 = np.minimum(ang, 180 - ang)
        d90 = abs(ang - 90)
        d45 = np.minimum(abs(ang - 45), abs(ang - 135))
        rows.append({"region": name, "skeleton_px": int(sk.sum()),
                     "within_3deg_of_0": float((d0 <= 3).mean()), "within_3deg_of_90": float((d90 <= 3).mean()),
                     "within_3deg_of_45_or_135": float((d45 <= 3).mean()) / 2,
                     "within_10deg_of_0": float((d0 <= 10).mean()), "within_10deg_of_90": float((d90 <= 10).mean()),
                     **{f"bin_{a}_{a + 5}": int(c) for a, c in zip(edges[:-1], h)}})
    odf = pd.DataFrame(rows)
    C.write_csv(OUT / "1.3_orientation.csv", odf)
    print(odf.iloc[:, :8].to_string(index=False))


ITEMS = {"1.1": item_1_1, "1.2": item_1_2, "1.3": item_1_3}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    item = sys.argv[1]
    ok = C.run_item(item, ITEMS[item])
    sys.exit(0 if ok else 1)
