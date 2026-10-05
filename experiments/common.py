"""Shared helpers for the overnight experiments.

Nothing here changes the pipeline. The pipeline modules (src/lacunae.py,
src/canaliculi.py) are imported, never edited. Where an experiment needs a
changed internal function, the experiment script holds its own copy.

PRE-VALIDATION, PIXEL units. Coordinates in every table are (x, y) =
(column, row), the convention of `python src/diagnostics.py lacuna-table`.

Contents:
    paths and image names
    atomic writers (a crash never leaves a half file)
    the default-result cache (rule E): build, check, load
    lacuna_stage and network_stage: the pipeline steps in the pipeline's own
        order, with hooks for the experiment variants
    headline(): the headline measures of one run
    crop helpers for QC panels
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from skimage import filters, measure, morphology

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402
import canaliculi  # noqa: E402
import lacunae  # noqa: E402

EXP_DIR = ROOT / "experiments"
LOG_DIR = EXP_DIR / "logs"
OUT_ROOT = ROOT / "results_experiments"
CACHE_DIR = OUT_ROOT / "_cache" / "default"
DATA_DIR = config.DATA_DIR / "WT"
PRECISION = config.CSV_FLOAT_PRECISION

IMAGE_PATHS = sorted(DATA_DIR.glob("*.tif"))

# Short labels used in tables and in the task text: the image labels of
# config.IMAGE_LABELS, the one naming table.
SHORT = dict(config.IMAGE_LABELS)
LONG = {v: k for k, v in SHORT.items()}


def clean(path: Path) -> str:
    return lacunae.clean_name(path)


def short(path_or_name) -> str:
    name = clean(path_or_name) if isinstance(path_or_name, Path) else str(path_or_name)
    return SHORT.get(name, name)


def image_path(short_or_clean: str) -> Path:
    name = LONG.get(short_or_clean, short_or_clean)
    for p in IMAGE_PATHS:
        if clean(p) == name:
            return p
    raise KeyError(short_or_clean)


def out_dir(task: str) -> Path:
    d = OUT_ROOT / task
    d.mkdir(parents=True, exist_ok=True)
    return d


# Atomic writers

def _tmp(path: Path) -> Path:
    return path.with_name(path.name + ".tmp")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _tmp(path)
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)


def write_text_once(path: Path, text: str) -> None:
    """Write a report file only if it does not exist yet, so a reading
    appended by hand is never overwritten by a rerun."""
    if not path.is_file():
        write_text(path, text)


def write_json(path: Path, obj) -> None:
    write_text(path, json.dumps(obj, indent=2, default=_json_default))


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(type(o))


def write_csv(path: Path, df) -> None:
    """Write a pandas DataFrame as CSV, atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _tmp(path)
    df.to_csv(tmp, index=False, lineterminator="\n")
    os.replace(tmp, path)


def write_npz(path: Path, **arrays) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _tmp(path)
    with open(tmp, "wb") as f:
        np.savez_compressed(f, **arrays)
    os.replace(tmp, path)


def write_png(path: Path, rgb: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = _tmp(path)
    Image.fromarray(np.ascontiguousarray(rgb)).save(tmp, format="PNG", optimize=True)
    os.replace(tmp, path)


def md_table(df, floatfmt: str = "{:.4g}") -> str:
    """A pandas DataFrame as a markdown table, no extra dependency."""
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, row in df.iterrows():
        cells = []
        for v in row.tolist():
            if isinstance(v, (float, np.floating)):
                cells.append("" if np.isnan(v) else floatfmt.format(v))
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


# Error handling per sub-item (rule F)

def run_item(item_id: str, func, *args, **kwargs) -> bool:
    """Run one sub-item. On an exception, write the traceback to
    experiments/logs/<id>.txt and return False."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        func(*args, **kwargs)
        return True
    except Exception:
        tb = traceback.format_exc()
        write_text(LOG_DIR / f"{item_id}.txt", f"{time.strftime('%Y-%m-%d %H:%M:%S')}\n{tb}")
        print(tb, file=sys.stderr)
        return False


# Default-result cache (rule E)

def src_hash() -> str:
    h = hashlib.sha256()
    for name in ("lacunae.py", "canaliculi.py"):
        h.update((ROOT / "src" / name).read_bytes())
    return h.hexdigest()[:16]


def cache_paths(path: Path) -> tuple[Path, Path]:
    name = clean(path)
    return CACHE_DIR / f"{name}.npz", CACHE_DIR / f"{name}.json"


def cache_ok(path: Path) -> bool:
    npz, js = cache_paths(path)
    if not (npz.is_file() and js.is_file()):
        return False
    try:
        meta = json.loads(js.read_text(encoding="utf-8"))
    except Exception:
        return False
    return meta.get("src_hash") == src_hash() and meta.get("complete") is True


def build_cache(path: Path) -> dict:
    """Run the real pipeline (canaliculi.analyse_image) on one image and
    store everything later experiments need. Extra intermediates (the
    lacuna top-class mask, the watershed labels before the re-merge, the
    preprocessed channel, the hysteresis mask) are recomputed with the
    pipeline's own functions."""
    t0 = time.time()
    res = canaliculi.analyse_image(path)
    t_full = time.time() - t0

    _display, channel = lacunae.load_channel(path)
    lac = res["lacunae"]
    labels = lac["labels"].astype(np.int32)
    kept_labels = np.array([r.label for r, _b in lac["kept"]], dtype=np.int32)
    on_border = np.array([b for _r, b in lac["kept"]], dtype=bool)

    topmask, t_hi = lacunae.multiotsu_lacuna_mask(channel)
    ws_labels = lacunae.watershed_split(topmask).astype(np.int32)
    preprocessed = canaliculi.preprocess_channel(channel)
    signal, t_lo = canaliculi.hysteresis_mask(preprocessed, res["flagged"])
    assert abs(t_hi - lac["t_hi"]) == 0 and abs(t_lo - res["t_lo"]) == 0

    npz, js = cache_paths(path)
    write_npz(
        npz,
        labels=labels,
        kept_labels=kept_labels,
        on_border=on_border,
        lacuna_id_map=res["lacuna_id_map"].astype(np.int32),
        topmask=topmask,
        ws_labels=ws_labels,
        candidate=res["candidate"],
        skeleton=res["skeleton"],
        flagged=res["flagged"],
        preprocessed=preprocessed,
        signal=signal,
        owner_map=res["owner_map"].astype(np.int32),
    )
    meta = {
        "status": "pre-validation",
        "units": "px",
        "image": path.name,
        "clean_name": clean(path),
        "src_hash": src_hash(),
        "t_hi": lac["t_hi"],
        "t_lo": res["t_lo"],
        "n_bridges": len(res["bridges"]),
        "bridges": [
            {"from_row_col": list(b["from"]), "to_row_col": list(b["to"]),
             "gap_len_px": b["gap_len"], "angle_deg": b["angle_deg"],
             "min_signal_fraction": b["min_signal_fraction"]}
            for b in res["bridges"]
        ],
        "lacuna_rows": lac["rows"],
        "lacuna_summary": lac["summary"],
        "lacuna_count": lac["lacuna_count"],
        "interior_lacuna_count": lac["interior_lacuna_count"],
        "cell_rows": res["rows"],
        "cell_summary": res["summary"],
        "field": res["field"],
        "seconds_full_pipeline": round(t_full, 2),
        "complete": True,
    }
    write_json(js, meta)
    return meta


def load(path_or_short) -> dict:
    """The cached default result for one image, with `kept` rebuilt as the
    pipeline's [(region, on_border), ...] list in kept order."""
    path = path_or_short if isinstance(path_or_short, Path) else image_path(path_or_short)
    if not cache_ok(path):
        raise RuntimeError(f"cache missing or stale for {path.name}; run experiments/task0_cache.py")
    npz, js = cache_paths(path)
    meta = json.loads(js.read_text(encoding="utf-8"))
    with np.load(npz) as z:
        arrays = {k: z[k] for k in z.files}
    regions = {r.label: r for r in measure.regionprops(arrays["labels"])}
    kept = [(regions[int(lbl)], bool(b)) for lbl, b in zip(arrays["kept_labels"], arrays["on_border"])]
    _display, channel = lacunae.load_channel(path)
    out = dict(meta)
    out.update(arrays)
    out["kept"] = kept
    out["channel"] = channel
    out["path"] = path
    out["short"] = short(path)
    return out


# Fast copies of two lacuna functions
# lacunae.watershed_split and lacunae.merge_shallow_splits loop over every
# component with full-frame arrays, which takes 10 to 120 s per image. The
# copies below do the same work inside each component's bounding box (plus
# a 1 px margin). They are checked to give identical labels on all 8 images
# at the default cut and at scaled cuts (task 2.3 log and
# results_experiments/task0/fast_copies_check.csv).

def watershed_fast(mask: np.ndarray) -> np.ndarray:
    from skimage import segmentation
    distance = ndi.distance_transform_edt(mask)
    components = measure.label(mask, connectivity=2)
    markers = np.zeros_like(components, dtype=np.int32)
    next_id = 1
    H, W = mask.shape
    for comp_id, sl in enumerate(ndi.find_objects(components), start=1):
        if sl is None:
            continue
        r0, r1 = max(sl[0].start - 1, 0), min(sl[0].stop + 1, H)
        c0, c1 = max(sl[1].start - 1, 0), min(sl[1].stop + 1, W)
        comp_mask = components[r0:r1, c0:c1] == comp_id
        d_local = np.where(comp_mask, distance[r0:r1, c0:c1], 0.0)
        peak = d_local.max()
        if peak <= 0:
            continue
        h = max(lacunae.SEED_PROMINENCE_FRACTION * peak, 1e-6)
        seeds = morphology.h_maxima(d_local, h) & comp_mask
        seed_labels = measure.label(seeds, connectivity=2)
        n = seed_labels.max()
        if n == 0:
            continue
        sub = markers[r0:r1, c0:c1]
        sub[seed_labels > 0] = seed_labels[seed_labels > 0] + next_id - 1
        next_id += n
    return segmentation.watershed(-distance, markers=markers, mask=mask)


def straight_ratio(distance, comp_mask_crop, offset, pa, pb, peak_a, peak_b) -> float:
    """The pipeline's saddle ratio: lowest distance value on the straight
    line between the two peaks, over the smaller peak."""
    saddle = lacunae._sample_line_min(distance, pa[0], pa[1], pb[0], pb[1])
    return saddle / min(peak_a, peak_b)


def merge_fast(labels: np.ndarray, mask: np.ndarray, distance: np.ndarray, min_area: int = lacunae.MIN_AREA_PX2,
               ratio_fn=straight_ratio, ratio_min: float = lacunae.MERGE_SADDLE_RATIO_MIN,
               record: list | None = None) -> np.ndarray:
    """lacunae.merge_shallow_splits per component bounding box, with hooks:
    min_area (pipeline 400), ratio_fn (pipeline straight line), ratio_min
    (pipeline 0.35), and `record`, a list that receives every tested pair."""
    components = measure.label(mask, connectivity=2)
    merged = labels.copy()
    for comp_id, sl in enumerate(ndi.find_objects(components), start=1):
        if sl is None:
            continue
        r0, c0 = sl[0].start, sl[1].start
        comp_mask = components[sl] == comp_id
        m = merged[sl]
        piece_labels = np.unique(m[comp_mask])
        piece_labels = piece_labels[piece_labels != 0]
        substantial = [lbl for lbl in piece_labels if (m == lbl).sum() >= min_area]
        if len(substantial) < 2:
            continue
        peaks, peak_locs = {}, {}
        for lbl in substantial:
            pm = m == lbl
            peaks[lbl] = distance[sl][pm].max()
            rr, cc = np.unravel_index(np.argmax(np.where(pm, distance[sl], -1)), pm.shape)
            peak_locs[lbl] = (rr + r0, cc + c0)
        parent = {lbl: lbl for lbl in substantial}

        def find(x):
            while parent[x] != x:
                x = parent[x]
            return x

        for i in range(len(substantial)):
            for j in range(i + 1, len(substantial)):
                a, b = substantial[i], substantial[j]
                ratio = ratio_fn(distance, comp_mask, (r0, c0), peak_locs[a], peak_locs[b], peaks[a], peaks[b])
                if record is not None:
                    record.append({"component": comp_id, "a": int(a), "b": int(b), "ratio": float(ratio),
                                   "peak_a": float(peaks[a]), "peak_b": float(peaks[b]),
                                   "pa": peak_locs[a], "pb": peak_locs[b]})
                if ratio >= ratio_min:
                    ra, rb = find(a), find(b)
                    if ra != rb:
                        parent[ra] = rb
        for lbl in substantial:
            root = find(lbl)
            if root != lbl:
                m[m == lbl] = root
        merged[sl] = m
    return merged


# Pipeline stages with hooks

def lacuna_mask_at(channel: np.ndarray, t_hi: float) -> np.ndarray:
    """multiotsu_lacuna_mask with the cut given instead of computed. Same
    steps after the cut."""
    mask = channel >= t_hi
    mask = morphology.remove_small_holes(mask, area_threshold=lacunae.FILL_HOLES_PX2)
    if lacunae.DESPECKLE_OPENING_RADIUS_PX > 0:
        mask = morphology.opening(mask, morphology.disk(lacunae.DESPECKLE_OPENING_RADIUS_PX))
    return mask


def lacuna_stage(channel: np.ndarray, t_hi: float | None = None, merge_fn=None, filter_fn=None,
                 fast: bool = False) -> dict:
    """lacunae.segment() with hooks: a fixed t_hi, a replacement re-merge
    function and a replacement filter function. With no hooks it is
    lacunae.segment() step for step. fast=True uses watershed_fast and
    merge_fast (checked identical) instead of the pipeline's own loops."""
    if t_hi is None:
        mask, t_hi = lacunae.multiotsu_lacuna_mask(channel)
    else:
        mask = lacuna_mask_at(channel, t_hi)
    ws = watershed_fast(mask) if fast else lacunae.watershed_split(mask)
    distance = ndi.distance_transform_edt(mask)
    merged = (merge_fn or (merge_fast if fast else lacunae.merge_shallow_splits))(ws, mask, distance)
    kept = (filter_fn or lacunae.filter_regions)(merged)
    rows = lacunae.measurements_for(kept, PRECISION)
    return {"mask": mask, "ws_labels": ws, "labels": merged, "kept": kept, "t_hi": t_hi, "rows": rows}


def hysteresis_at(img: np.ndarray, no_growth: np.ndarray, t_lo: float) -> np.ndarray:
    """canaliculi.hysteresis_mask with the strict cut given instead of
    computed. Same rule otherwise."""
    strict_mask = img > t_lo
    low = t_lo * canaliculi.HYSTERESIS_LOW_FRACTION
    mask = filters.apply_hysteresis_threshold(img, low, t_lo)
    if no_growth.any():
        mask = mask & ~(no_growth & ~strict_mask)
    return mask


def network_stage(channel, labels, kept, preprocessed=None, flagged=None, t_lo: float | None = None,
                  signal=None, keep_graph: bool = False) -> dict:
    """canaliculi.analyse_image from the lacuna result onward, with hooks:
    a given preprocessed channel, flagged mask, strict cut t_lo, or a
    precomputed hysteresis mask `signal`. With no hooks it repeats the
    pipeline step for step (checked against the cache in task 0.2)."""
    lacuna_mask, lacuna_id_map = canaliculi.build_lacuna_maps(labels, kept)
    if flagged is None:
        flagged = canaliculi.flagged_structures(channel)
    if preprocessed is None:
        preprocessed = canaliculi.preprocess_channel(channel)
    if signal is None:
        if t_lo is None:
            signal, t_lo = canaliculi.hysteresis_mask(preprocessed, flagged)
        else:
            signal = hysteresis_at(preprocessed, flagged, t_lo)
    elif t_lo is None:
        _m, t_lo = canaliculi.total_signal_mask(preprocessed)
    buffered = morphology.dilation(lacuna_mask, morphology.disk(canaliculi.LACUNA_DILATION_PX))
    candidate = signal & ~buffered
    candidate = morphology.remove_small_objects(candidate, min_size=canaliculi.MIN_THREAD_OBJECT_PX2)
    skeleton = morphology.skeletonize(candidate)
    bridges = canaliculi.find_bridges(skeleton, preprocessed, t_lo, lacuna_mask | flagged)
    if bridges:
        candidate = canaliculi.apply_bridges(candidate, bridges)
        skeleton = morphology.skeletonize(candidate)
    dist, nearest = canaliculi.nearest_lacuna_map(lacuna_id_map)
    cells = canaliculi.measure_cells(kept, skeleton, dist, nearest, PRECISION)
    out = {
        "lacuna_mask": lacuna_mask,
        "lacuna_id_map": lacuna_id_map,
        "candidate": candidate,
        "skeleton": skeleton,
        "flagged": flagged,
        "t_lo": t_lo,
        "bridges": bridges,
        "cell_rows": cells["rows"],
        "density": density(skeleton, lacuna_mask),
        "owner_map": cells["owner_map"],
    }
    if keep_graph:
        out["graph"] = cells["graph"]
        out["edge_owner"] = cells["edge_owner"]
    return out


def density(skeleton: np.ndarray, lacuna_mask: np.ndarray, area_mask: np.ndarray | None = None) -> float:
    """Field length density: skeleton px / analysed area. With area_mask,
    both are restricted to it (the analysed area is area_mask minus
    lacunae)."""
    if area_mask is None:
        area = skeleton.size - int(lacuna_mask.sum())
        return float(skeleton.sum()) / area if area > 0 else float("nan")
    area = int((area_mask & ~lacuna_mask).sum())
    return float((skeleton & area_mask).sum()) / area if area > 0 else float("nan")


def headline(lac_rows: list[dict], cell_rows: list[dict], dens: float, n_bridges: int | None) -> dict:
    """Headline measures of one run, as the pipeline summarizes them:
    per-cell means over interior lacunae."""
    interior = [r for r in lac_rows if not r["on_border"]]
    cint = [r for r in cell_rows if not r["on_border"]]
    areas = [r["area_px2"] for r in interior]
    return {
        "lacuna_count": len(lac_rows),
        "interior_count": len(interior),
        "median_area_px2": float(np.median(areas)) if areas else float("nan"),
        "roots_per_cell": float(np.mean([r["roots_count"] for r in cint])) if cint else float("nan"),
        "ring30_per_cell_px": float(np.mean([r["ring_length_r30_px"] for r in cint])) if cint else float("nan"),
        "ring60_per_cell_px": float(np.mean([r["ring_length_r60_px"] for r in cint])) if cint else float("nan"),
        "field_density_per_px": dens,
        "bridges": n_bridges,
    }


# Crops and panels

def to_rgb(img: np.ndarray, lo: float | None = None, hi: float | None = None) -> np.ndarray:
    """Grey float or bool image to RGB uint8, stretched lo..hi (default the
    1st and 99.5th percentile)."""
    a = img.astype(float)
    if a.dtype == bool or img.dtype == bool:
        a = img.astype(float)
        lo, hi = 0.0, 1.0
    if lo is None:
        lo = float(np.percentile(a, 1))
    if hi is None:
        hi = float(np.percentile(a, 99.5))
    if hi <= lo:
        hi = lo + 1e-6
    g = np.clip((a - lo) / (hi - lo), 0, 1)
    g = (g * 255).astype(np.uint8)
    return np.stack([g, g, g], axis=-1)


def outline(rgb: np.ndarray, mask: np.ndarray, color, thick: int = 1) -> np.ndarray:
    from skimage import segmentation
    b = segmentation.find_boundaries(mask, mode="outer")
    if thick > 1:
        b = morphology.dilation(b, morphology.disk(thick - 1))
    out = rgb.copy()
    out[b] = color
    return out


def paint(rgb: np.ndarray, mask: np.ndarray, color, alpha: float = 1.0) -> np.ndarray:
    out = rgb.astype(float).copy()
    out[mask] = (1 - alpha) * out[mask] + alpha * np.array(color, dtype=float)
    return out.astype(np.uint8)


def crop(a: np.ndarray, x: int, y: int, half: int) -> tuple[np.ndarray, tuple[int, int]]:
    """Crop centred on (x, y) = (col, row), clipped to the frame. Returns
    the crop and its top-left (x0, y0)."""
    r0, r1 = max(0, y - half), min(a.shape[0], y + half)
    c0, c1 = max(0, x - half), min(a.shape[1], x + half)
    return a[r0:r1, c0:c1], (c0, r0)


def panel_row(panels: list[np.ndarray], titles: list[str] | None = None, scale: int = 1, gap: int = 6) -> np.ndarray:
    """Panels side by side on a white background with an optional title
    strip above each, nearest-neighbour upscaled by `scale`."""
    ups = [np.kron(p, np.ones((scale, scale, 1), dtype=np.uint8)) if scale > 1 else p for p in panels]
    h = max(p.shape[0] for p in ups)
    title_h = 14 if titles else 0
    w = sum(p.shape[1] for p in ups) + gap * (len(ups) - 1)
    canvas = np.full((h + title_h, w, 3), 255, dtype=np.uint8)
    x = 0
    for p in ups:
        canvas[title_h:title_h + p.shape[0], x:x + p.shape[1]] = p
        x += p.shape[1] + gap
    if titles:
        im = Image.fromarray(canvas)
        d = ImageDraw.Draw(im)
        x = 0
        for p, t in zip(ups, titles):
            d.text((x + 2, 1), t, fill=(0, 0, 0))
            x += p.shape[1] + gap
        canvas = np.asarray(im).copy()
    return canvas


def panel_grid(rows: list[np.ndarray], gap: int = 8) -> np.ndarray:
    w = max(r.shape[1] for r in rows)
    h = sum(r.shape[0] for r in rows) + gap * (len(rows) - 1)
    canvas = np.full((h, w, 3), 255, dtype=np.uint8)
    y = 0
    for r in rows:
        canvas[y:y + r.shape[0], :r.shape[1]] = r
        y += r.shape[0] + gap
    return canvas


def downscale(rgb: np.ndarray, factor: int = 2) -> np.ndarray:
    im = Image.fromarray(rgb)
    return np.asarray(im.resize((rgb.shape[1] // factor, rgb.shape[0] // factor), Image.LANCZOS))


def mark(rgb: np.ndarray, x: int, y: int, color=(255, 255, 0), r: int = 4) -> np.ndarray:
    im = Image.fromarray(rgb)
    d = ImageDraw.Draw(im)
    d.ellipse([x - r, y - r, x + r, y + r], outline=color)
    return np.asarray(im).copy()


def label_text(rgb: np.ndarray, x: int, y: int, text: str, color=(255, 255, 0)) -> np.ndarray:
    im = Image.fromarray(rgb)
    ImageDraw.Draw(im).text((x, y), text, fill=color)
    return np.asarray(im).copy()
