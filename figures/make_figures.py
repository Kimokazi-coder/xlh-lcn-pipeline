"""Publication figures for the LCN pipeline.

PRE-VALIDATION, PIXEL units. Every figure shows the default pipeline output as
it is (src/ with every switch off), unless its caption says otherwise. Nothing
here writes into results/. Outputs go to figures_out/ as PNG (300 dpi) and PDF
(fonts embedded). Coordinates are (x, y) = (column, row).

Usage (from the repo root):
    python -u figures/make_figures.py all                 # the whole figures_out/ tree, with a summary
    python -u figures/make_figures.py window              # the fixed display window
    python -u figures/make_figures.py check               # drawing data against results/, all images
    python -u figures/make_figures.py image -i 543-2      # per-image overview
    python -u figures/make_figures.py image -i 543-2 -c 6 # the same, inset on lacuna 6
    python -u figures/make_figures.py image -i 543_3 -r   # with objects kept only at 0.8 t_hi
    python -u figures/make_figures.py network -a          # network overlay per image (and Fig02)
    python -u figures/make_figures.py gallery -a          # cell gallery per image
    python -u figures/make_figures.py variants -a         # per-image display window variants
    python -u figures/make_figures.py tiles -k KEY        # hand-count tiles, KEY outside the repository
    python -u figures/make_figures.py contact             # contact sheet (Fig01)
    python -u figures/make_figures.py contact -r          # with rejected candidates (S02)
    python -u figures/make_figures.py contact -b -k KEY   # labelled with blinding codes (S03)
    python -u figures/make_figures.py thresholds          # lacuna cut sensitivity (Fig03)
    python -u figures/make_figures.py fields -f FIELD_DIR # per-field plot (Fig04; -m merged)
    python -u figures/make_figures.py switches            # crumb rule and hole fill (S01)
    python -u figures/make_figures.py thumbs              # _thumbs/, README.md and INDEX.md

Layout of figures_out/: main/ (Fig01 to Fig04), supplement/ (S01 to S03),
per_image/<image>/ (overview, network, gallery, logs, display_variants/),
validation_tiles/, _thumbs/, README.md, INDEX.md, display_window.json.
Each output is skipped if its PNG and PDF exist; delete them to redraw.

Shared style (one place, used by every figure):
    display window   fixed for the whole dataset: the 1st and 99.8th percentile
                     of the pooled red channel of all images, the same for every
                     image and panel (figures_out/display_window.json)
    fonts            Arial (Helvetica if present, else DejaVu Sans), 7 to 9 pt
                     at 180 mm figure width; PDF fonts embedded (TrueType)
    colours          one colour, one meaning (PALETTE): interior lacuna
                     outlines cyan; frame-edge lacunae yellow (left out of
                     every per-cell mean); rejected candidates grey dashed;
                     skeleton within 30 px of an interior lacuna vermillion,
                     the rest white; roots magenta dots; inset boxes white
    outlines         at least 0.6 pt wide in the exported figure
    scale bar        in pixels ("200 px"); the images are uncalibrated. In
                     micrometres only if config.PIXEL_SIZE_UM is set.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import patheffects  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402
import canaliculi  # noqa: E402
import lacunae  # noqa: E402

# The fast lacuna stage gives labels identical to the original one (python
# src/diagnostics.py fast-check, 40 of 40; regression passes with it on), so
# the figures use it for speed. Every other setting is the default.
config.FAST_LACUNA_STAGE = True

OUT = ROOT / "figures_out"
CACHE = ROOT / "results_experiments" / "_cache" / "figures"
LOG_DIR = ROOT / "experiments" / "logs"
DATA_DIR = config.DATA_DIR / "WT"

# Short image labels, as in the overnight report.
SHORT = {
    "542_WT_2_z06c1-2": "542_z06", "542_WT_2_z18c1-2": "542_z18", "543-2": "543-2", "543_3": "543_3",
    "543_z13c1-2": "543_z13", "682_z08c1-2": "682_z08", "682_z23c-2": "682_z23", "682_z29c1-3": "682_z29",
}

# Style ----------------------------------------------------------------------------

MM = 1 / 25.4  # inches per mm
FIG_WIDTH_MM = 180.0
FONT_SIZE = 7.0
LETTER_SIZE = 9.0
OUTLINE_PT = 0.7  # at least 0.6 pt
SKELETON_COLOUR = "white"
# Since figures v2 (P2) these equal PALETTE below: one colour, one meaning.
INTERIOR_COLOUR = "#00FFFF"  # cyan: interior lacuna
BORDER_COLOUR = "#F0E442"  # Okabe-Ito yellow: lacuna touching the frame
ROOT_COLOUR = "#FF00FF"  # magenta: root
DIM_FACTOR = 0.6  # raw image dimmed to 60% under the skeleton
WINDOW_PERCENTILES = (1.0, 99.8)
SCALE_BAR_PX = 200


# Palette (figures v2) -----------------------------------------------------------
# One place for every colour of the v2 figures. Each colour has one meaning.
# Hues come from the Okabe-Ito colour-blind safe set where the hue was free
# to choose; cyan, white, magenta and grey were set by the brief.
PALETTE = {
    "interior": "#00FFFF",  # cyan outline: interior lacuna, used in every per-cell mean
    "edge": "#F0E442",  # Okabe-Ito yellow outline: lacuna touching the frame, left out of per-cell means
    "ring": "#D55E00",  # Okabe-Ito vermillion: skeleton within 30 px of an interior lacuna (ring 30 px)
    "skeleton": "#FFFFFF",  # white, at SKELETON_ALPHA: the rest of the skeleton
    "root": "#FF00FF",  # magenta dot with a thin black edge: one root
    "rejected": "#A6A6A6",  # grey, dashed: lacuna-scale object rejected by a shape or area filter
    "box": "#FFFFFF",  # white rectangle: region shown in an inset
    "low_cut": "#56B4E9",  # Okabe-Ito sky blue, dotted: object kept only at 0.8 t_hi (option -r)
    "field_mean": "#0072B2",  # Okabe-Ito blue: field mean bar in the per-field plot
}
SKELETON_ALPHA = 0.7  # the white skeleton at 70% opacity
OVERLAY_BRIGHTNESS = 0.85  # raw image at 85% under the v2 overlays (not dimmed to 60%)
RING_RADIUS_PX = 30  # the ring 30 px headline measure; must be in canaliculi.RING_RADII_PX
SKELETON_LW = 0.3  # pt, vector skeleton lines; the brief allows 0.25 to 0.5, chosen by viewing
V2_OUTLINE_PT = 0.6
INSET_FRAME_MARGIN_PX = 60  # an inset lacuna's bounding box must be at least this far from the frame

# Skeleton pixel classes for the vector drawer.
CLS_NONE, CLS_REST, CLS_RING = 0, 1, 2


def set_style() -> None:
    from matplotlib import font_manager as fm

    family = []
    for name in ("Arial", "Helvetica"):
        try:
            fm.findfont(name, fallback_to_default=False)
            family.append(name)
        except ValueError:
            pass
    family.append("DejaVu Sans")
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": family,
        "font.size": FONT_SIZE,
        "axes.titlesize": FONT_SIZE,
        "axes.labelsize": FONT_SIZE,
        "xtick.labelsize": FONT_SIZE - 1,
        "ytick.labelsize": FONT_SIZE - 1,
        "legend.fontsize": FONT_SIZE - 1,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.dpi": 300,
        "figure.dpi": 100,
        "axes.linewidth": 0.6,
        "lines.linewidth": OUTLINE_PT,
        "image.interpolation": "antialiased",
    })


def mm_axes(fig, x_mm: float, y_mm: float, w_mm: float, h_mm: float, fig_w_mm: float, fig_h_mm: float):
    """Axes placed in mm from the figure's lower left corner."""
    return fig.add_axes([x_mm / fig_w_mm, y_mm / fig_h_mm, w_mm / fig_w_mm, h_mm / fig_h_mm])


def panel_letter(fig, ax, letter: str, dx: float = 0.0) -> None:
    """Bold letter above the panel's left edge, shifted by dx (figure
    fraction; negative moves it left, clear of a centred title)."""
    bb = ax.get_position()
    fig.text(bb.x0 + dx, bb.y1 + 0.01, letter, fontsize=LETTER_SIZE, fontweight="bold", va="bottom", ha="left")


def halo(width: float = 1.6):
    return [patheffects.withStroke(linewidth=width, foreground="black")]


def scale_bar(ax, image_width_px: int, length_px: int = SCALE_BAR_PX, colour: str = "white", y_frac: float = 0.05) -> None:
    """A bar of `length_px` in the lower left of an image axes. Labelled in px
    unless config.PIXEL_SIZE_UM is set."""
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()  # imshow: y0 > y1
    w = x1 - x0
    h = abs(y0 - y1)
    bx = x0 + 0.05 * w
    by = max(y0, y1) - y_frac * h
    ax.plot([bx, bx + length_px], [by, by], color=colour, lw=2.0, solid_capstyle="butt")
    if config.PIXEL_SIZE_UM:
        label = f"{length_px * config.PIXEL_SIZE_UM:g} µm"
    else:
        label = f"{length_px} px"
    ax.text(bx + length_px / 2, by - 0.02 * h, label, color=colour, ha="center", va="bottom",
            fontsize=FONT_SIZE - 1, path_effects=halo(1.2))


def fig_stem(name: str) -> Path:
    """Where a numbered figure lives: main figures (Fig01, ...) in
    figures_out/main/, supplementary figures (S01, ...) in
    figures_out/supplement/."""
    if name.startswith("Fig"):
        return OUT / "main" / name
    if name[:1] == "S" and name[1:3].isdigit():
        return OUT / "supplement" / name
    return OUT / name


def save(fig, name: str) -> None:
    stem = fig_stem(name)
    stem.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        final = stem.with_name(f"{name}.{ext}")
        tmp = stem.with_name(f"{name}.tmp.{ext}")
        fig.savefig(tmp, dpi=300)
        os.replace(tmp, final)
    plt.close(fig)


def done(name: str) -> bool:
    stem = fig_stem(name)
    return stem.with_name(f"{name}.png").is_file() and stem.with_name(f"{name}.pdf").is_file()


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    os.replace(tmp, path)


# Display window ----------------------------------------------------------------------

def image_paths() -> list[Path]:
    return sorted(DATA_DIR.glob("*.tif"))


def short(path: Path) -> str:
    return SHORT.get(lacunae.clean_name(path), lacunae.clean_name(path))


def path_of(name: str) -> Path:
    for p in image_paths():
        if short(p) == name or lacunae.clean_name(p) == name:
            return p
    raise KeyError(name)


def display_window() -> tuple[float, float]:
    """(lo, hi) on the red channel in [0, 1], fixed for the dataset."""
    path = OUT / "display_window.json"
    if path.is_file():
        w = json.loads(path.read_text(encoding="utf-8"))
        return w["lo"], w["hi"]
    pooled = np.concatenate([lacunae.load_channel(p)[1].ravel() for p in image_paths()])
    lo, hi = (float(v) for v in np.percentile(pooled, WINDOW_PERCENTILES))
    write_json(path, {"lo": lo, "hi": hi, "lo_8bit": lo * 255, "hi_8bit": hi * 255,
                      "percentiles": list(WINDOW_PERCENTILES),
                      "pooled_over": [p.name for p in image_paths()],
                      "note": "Fixed display window for every image and panel: the 1st and 99.8th percentile "
                              "of the pooled red channel of all images. Display only; no measurement uses it."})
    return lo, hi


def windowed(channel: np.ndarray, dim: float = 1.0) -> np.ndarray:
    lo, hi = display_window()
    return np.clip((channel - lo) / (hi - lo), 0, 1) * dim


# Pipeline output for one image ----------------------------------------------------------

def root_clusters(G, cell_id: int) -> list[tuple[float, float]]:
    """The roots of one lacuna as (x, y) points: a copy of
    canaliculi.cell_root_count that returns the cluster centres instead of
    their number. Checked against roots_count when the cache is built."""
    src = ("cell", cell_id)
    if not G.has_node(src):
        return []
    points = [n for n in G.neighbors(src) if not canaliculi._is_cell_node(n)]
    unmerged = list(points)
    clusters = []
    while unmerged:
        seed = unmerged.pop()
        cluster = [seed]
        changed = True
        while changed:
            changed = False
            for other in list(unmerged):
                if any(np.hypot(other[0] - m[0], other[1] - m[1]) <= canaliculi.ROOT_MERGE_DIST_PX for m in cluster):
                    cluster.append(other)
                    unmerged.remove(other)
                    changed = True
        clusters.append(cluster)
    return [(float(np.mean([c[1] for c in cl])), float(np.mean([c[0] for c in cl]))) for cl in clusters]


def pipeline_output(path: Path) -> dict:
    """Default pipeline output for one image, cached in
    results_experiments/_cache/figures/ (git-ignored)."""
    name = short(path)
    npz, js = CACHE / f"{name}.npz", CACHE / f"{name}.json"
    if npz.is_file() and js.is_file():
        meta = json.loads(js.read_text(encoding="utf-8"))
        with np.load(npz) as z:
            meta["lacuna_id_map"] = z["lacuna_id_map"]
            meta["skeleton"] = z["skeleton"]
        meta["channel"] = lacunae.load_channel(path)[1]
        return meta
    res = canaliculi.analyse_image(path)
    roots = {}
    for row in res["rows"]:
        pts = root_clusters(res["graph"], row["lacuna_id"])
        assert len(pts) == row["roots_count"], (name, row["lacuna_id"])
        roots[str(row["lacuna_id"])] = pts
    meta = {"image": path.name, "short": name, "lacuna_rows": res["lacunae"]["rows"], "cell_rows": res["rows"],
            "lacuna_count": res["lacunae"]["lacuna_count"], "interior_count": res["lacunae"]["interior_lacuna_count"],
            "roots_xy": roots, "field": res["field"], "summary": res["summary"]}
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = npz.with_name(npz.name + ".tmp")
    with open(tmp, "wb") as f:
        np.savez_compressed(f, lacuna_id_map=res["lacuna_id_map"].astype(np.int32), skeleton=res["skeleton"])
    os.replace(tmp, npz)
    write_json(js, meta)
    meta["lacuna_id_map"] = res["lacuna_id_map"]
    meta["skeleton"] = res["skeleton"]
    meta["channel"] = lacunae.load_channel(path)[1]
    return meta


# Drawing helpers -----------------------------------------------------------------------

def draw_outlines(ax, lacuna_id_map: np.ndarray, rows: list, numbers: bool = False, lw: float = OUTLINE_PT,
                  offset=(0, 0), number_size: float = FONT_SIZE - 1) -> None:
    """Outline every kept lacuna: cyan if interior, yellow if it touches the
    frame. Contours run along pixel edges. `offset` (x0, y0) shifts them
    for a cropped view."""
    from skimage import measure

    x0, y0 = offset
    for row in rows:
        lid = row["lacuna_id"]
        m = np.pad(lacuna_id_map == lid, 1)
        colour = BORDER_COLOUR if row["on_border"] else INTERIOR_COLOUR
        for c in measure.find_contours(m.astype(float), 0.5):
            ax.plot(c[:, 1] - 1 - x0, c[:, 0] - 1 - y0, color=colour, lw=lw, solid_joinstyle="round")
        if numbers:
            # Beside the lacuna, not on it: right of its bounding box, or left
            # of it when the box is close to the right frame edge.
            cols = np.nonzero((lacuna_id_map == lid).any(axis=0))[0]
            right = cols.max() + 6
            if right > lacuna_id_map.shape[1] - 40:
                tx, ha = cols.min() - 6, "right"
            else:
                tx, ha = right, "left"
            # Kept at least 14 px inside the top and bottom frame edges.
            ty = float(np.clip(row["centroid_row_px"], 14, lacuna_id_map.shape[0] - 14))
            ax.text(tx - x0, ty - y0, str(lid), color=colour, ha=ha, va="center",
                    fontsize=number_size, fontweight="bold", path_effects=halo())


def image_axes(ax, img: np.ndarray, cmap: str = "gray") -> None:
    ax.imshow(img, cmap=cmap, vmin=0, vmax=1, interpolation="antialiased")
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_linewidth(0.5)


def skeleton_rgb(channel: np.ndarray, skeleton: np.ndarray) -> np.ndarray:
    """Raw image dimmed to 60% in grey, skeleton pixels white."""
    g = windowed(channel, DIM_FACTOR)
    rgb = np.stack([g, g, g], axis=-1)
    rgb[skeleton] = 1.0
    return rgb


# Figures v2: shared data and drawing code ---------------------------------------------

CACHE2 = ROOT / "results_experiments" / "_cache" / "figures_v2"
PER_IMAGE = OUT / "per_image"
TASK2_DIR = ROOT / "experiments"

# Rejected pieces smaller than this are not drawn: they are specks of the
# lacuna mask (the area filter drops 45% of interior pieces in [81, 373)
# px², src/lacunae.py MIN_AREA_PX2), and drawing them would bury the
# lacuna-scale objects. Display only; no measurement uses it.
REJECTED_MIN_DRAW_PX2 = 150

# A kept lacuna gets "c" after its number when at least this share of its
# pixels lies in the flagged canal mask (src/canaliculi.py
# flagged_structures). Display only; the classification is unchanged.
CANAL_MARK_MIN_SHARE = 0.5

# One-letter reason for a rejected piece, from the stage replay of
# experiments/task2_thresholds.py (verdict).
REASON_LETTER = {"area": "a", "solidity": "S", "aspect": "A"}


class AssertionFailed(Exception):
    """A drawn number differs from the pipeline number (rule 11)."""


def src_hash() -> str:
    import hashlib

    h = hashlib.sha256()
    for p in (ROOT / "src" / "lacunae.py", ROOT / "src" / "canaliculi.py", ROOT / "config.py"):
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def results_numbers(path: Path) -> tuple[list, list]:
    """(lacuna rows, cell rows) of the committed default output in
    results/<image>/, the pipeline numbers every drawn number must equal."""
    folder = config.RESULTS_DIR / lacunae.clean_name(path)
    lac = json.loads((folder / "lacunae.json").read_text(encoding="utf-8"))
    can = json.loads((folder / "canaliculi_measurements.json").read_text(encoding="utf-8"))
    return lac["lacunae"], can["lacunae"]


def rejection_reason(region, shape) -> str:
    """The filter that rejects a piece, by the stage replay of
    experiments/task2_thresholds.py (its verdict function)."""
    sys.path.insert(0, str(TASK2_DIR))
    import task2_thresholds  # noqa: E402

    v = task2_thresholds.verdict(region, shape)
    for key in ("area", "solidity", "aspect"):
        if v.startswith(key):
            return key
    raise ValueError(f"unexpected verdict {v!r}")


def build_image_data(path: Path) -> None:
    """Run the default pipeline (every switch off; the fast lacuna stage,
    identical labels) on one image and cache what the v2 figures draw, in
    results_experiments/_cache/figures_v2/ (git-ignored)."""
    from skimage import measure

    name = short(path)
    res = canaliculi.analyse_image(path)
    lac = res["lacunae"]
    roots = {}
    for row in res["rows"]:
        pts = root_clusters(res["graph"], row["lacuna_id"])
        if len(pts) != row["roots_count"]:
            raise AssertionFailed(f"{name} lacuna {row['lacuna_id']}: {len(pts)} root clusters, roots_count {row['roots_count']}")
        roots[str(row["lacuna_id"])] = pts
    kept_labels = {region.label for region, _b in lac["kept"]}
    rejected = []
    for region in measure.regionprops(lac["labels"]):
        if region.label in kept_labels or region.area < REJECTED_MIN_DRAW_PX2:
            continue
        reason = rejection_reason(region, lac["labels"].shape)
        minor, major = region.axis_minor_length, region.axis_major_length
        cy, cx = region.centroid
        rejected.append({"label": int(region.label), "area_px2": int(region.area),
                         "solidity": round(float(region.solidity), 4),
                         "aspect": round(float(major / minor), 4) if minor > 0 else None,
                         "reason": reason, "letter": REASON_LETTER[reason],
                         "x": round(float(cx), 1), "y": round(float(cy), 1), "bbox": [int(v) for v in region.bbox]})
    meta = {"image": path.name, "short": name, "src_hash": src_hash(), "t_hi": lac["t_hi"], "t_lo": res["t_lo"],
            "lacuna_rows": lac["rows"], "cell_rows": res["rows"], "roots_xy": roots, "rejected": rejected,
            "field": res["field"], "complete": True}
    CACHE2.mkdir(parents=True, exist_ok=True)
    npz = CACHE2 / f"{name}.npz"
    tmp = npz.with_name(npz.name + ".tmp")
    with open(tmp, "wb") as f:
        np.savez_compressed(f, lacuna_id_map=res["lacuna_id_map"].astype(np.int32), skeleton=res["skeleton"],
                            labels=lac["labels"].astype(np.int32), flagged=res["flagged"])
    os.replace(tmp, npz)
    write_json(CACHE2 / f"{name}.json", meta)


def ring_classes(skeleton: np.ndarray, lacuna_id_map: np.ndarray, interior_ids) -> dict:
    """Classify every skeleton pixel with the pipeline's own ring rule
    (src/canaliculi.py ring_lengths): a pixel is in the 30 px ring of
    lacuna i if its distance to the lacuna masks is at most 30 px and its
    nearest lacuna (canaliculi.nearest_lacuna_map, the same distance map) is
    i. Ring pixels of an interior lacuna are CLS_RING (vermillion); every
    other skeleton pixel, including the ring of a frame-edge lacuna, is
    CLS_REST (white). Also returns the per-lacuna ring pixel counts."""
    if RING_RADIUS_PX not in canaliculi.RING_RADII_PX:
        raise AssertionFailed(f"ring radius {RING_RADIUS_PX} is not a pipeline radius {canaliculi.RING_RADII_PX}")
    dist, nearest = canaliculi.nearest_lacuna_map(lacuna_id_map)
    in_ring = skeleton & (dist <= RING_RADIUS_PX) & (nearest > 0)
    ring_interior = in_ring & np.isin(nearest, list(interior_ids))
    classes = np.zeros(skeleton.shape, dtype=np.uint8)
    classes[skeleton] = CLS_REST
    classes[ring_interior] = CLS_RING
    n = int(lacuna_id_map.max())
    return {"classes": classes, "dist": dist, "nearest": nearest,
            "ring_count": np.bincount(nearest[in_ring], minlength=n + 1),
            "ring_interior_count": np.bincount(nearest[ring_interior], minlength=n + 1)}


def image_data(name: str) -> dict:
    """Everything the v2 figures draw for one image, checked against the
    pipeline numbers in results/<image>/ (rule 11). Raises AssertionFailed on
    any difference."""
    path = path_of(name)
    name = short(path)
    npz, js = CACHE2 / f"{name}.npz", CACHE2 / f"{name}.json"
    ok = npz.is_file() and js.is_file()
    if ok:
        meta = json.loads(js.read_text(encoding="utf-8"))
        ok = meta.get("complete") is True and meta.get("src_hash") == src_hash()
    if not ok:
        build_image_data(path)
        meta = json.loads(js.read_text(encoding="utf-8"))
    with np.load(npz) as z:
        d = dict(meta)
        for k in z.files:
            d[k] = z[k]
    d["channel"] = lacunae.load_channel(path)[1]
    d["path"] = path

    # The cached run must equal results/ for every number drawn.
    lac_rows, cell_rows = results_numbers(path)
    idm = d["lacuna_id_map"]
    if len(lac_rows) != int(idm.max()) or len(cell_rows) != len(lac_rows):
        raise AssertionFailed(f"{name}: {int(idm.max())} lacunae drawn, results/ has {len(lac_rows)}")
    areas = np.bincount(idm.ravel(), minlength=len(lac_rows) + 1)
    for lr, cr, mr in zip(lac_rows, cell_rows, d["cell_rows"]):
        i = lr["lacuna_id"]
        if areas[i] != lr["area_px2"] or lr["on_border"] != cr["on_border"]:
            raise AssertionFailed(f"{name} lacuna {i}: area {areas[i]} drawn, {lr['area_px2']} in results/")
        if (mr["roots_count"], mr["ring_length_r30_px"]) != (cr["roots_count"], cr["ring_length_r30_px"]):
            raise AssertionFailed(f"{name} lacuna {i}: cache differs from results/")
    d["lacuna_rows"], d["cell_rows"] = lac_rows, cell_rows
    d["interior_ids"] = [r["lacuna_id"] for r in lac_rows if not r["on_border"]]
    d["edge_ids"] = [r["lacuna_id"] for r in lac_rows if r["on_border"]]

    rc = ring_classes(d["skeleton"], idm, d["interior_ids"])
    d.update(rc)
    for cr in cell_rows:
        i = cr["lacuna_id"]
        drawn = int(rc["ring_interior_count"][i]) if i in d["interior_ids"] else 0
        if i in d["interior_ids"] and drawn != cr["ring_length_r30_px"]:
            raise AssertionFailed(f"{name} lacuna {i}: {drawn} vermillion px, ring_length_r30_px {cr['ring_length_r30_px']}")
        if int(rc["ring_count"][i]) != cr["ring_length_r30_px"]:
            raise AssertionFailed(f"{name} lacuna {i}: ring {int(rc['ring_count'][i])} px, results/ {cr['ring_length_r30_px']}")
        if len(d["roots_xy"][str(i)]) != cr["roots_count"]:
            raise AssertionFailed(f"{name} lacuna {i}: {len(d['roots_xy'][str(i)])} root dots, roots_count {cr['roots_count']}")

    # Canal mark: share of each kept lacuna inside the flagged canal mask.
    inside = np.bincount(idm[d["flagged"]].ravel(), minlength=len(lac_rows) + 1)
    d["canal_share"] = {r["lacuna_id"]: float(inside[r["lacuna_id"]] / areas[r["lacuna_id"]]) for r in lac_rows}
    d["canal_ids"] = [i for i, s in d["canal_share"].items() if s >= CANAL_MARK_MIN_SHARE]
    d["segments"] = skeleton_segments(d["skeleton"], d["classes"])
    return d


FORWARD_NEIGHBOURS = ((0, 1), (1, -1), (1, 0), (1, 1))  # (dr, dc): each 8-neighbour pair once


def skeleton_segments(skeleton: np.ndarray, classes: np.ndarray) -> dict:
    """The skeleton as line segments between the centres of 8-connected
    neighbouring pixels, forward neighbours only (so no pair twice), in
    (x, y) image coordinates. A segment takes the class of its first pixel.
    A pixel with no neighbour becomes a 1 px horizontal dash across itself.
    The pixels the segments join are exactly the skeleton pixels (checked)."""
    H, W = skeleton.shape
    padded = np.pad(skeleton, 1)
    segs, cls = [], []
    covered = np.zeros_like(skeleton)
    for dr, dc in FORWARD_NEIGHBOURS:
        other = padded[1 + dr:1 + dr + H, 1 + dc:1 + dc + W]
        r, c = np.nonzero(skeleton & other)
        segs.append(np.stack([np.stack([c, r], axis=1), np.stack([c + dc, r + dr], axis=1)], axis=1).astype(float))
        cls.append(classes[r, c])
        covered[r, c] = True
        covered[r + dr, c + dc] = True
    lone_r, lone_c = np.nonzero(skeleton & ~covered)
    segs.append(np.stack([np.stack([lone_c - 0.5, lone_r], axis=1), np.stack([lone_c + 0.5, lone_r], axis=1)],
                         axis=1).astype(float))
    cls.append(classes[lone_r, lone_c])
    covered[lone_r, lone_c] = True
    if not np.array_equal(covered, skeleton):
        raise AssertionFailed("vector skeleton does not cover exactly the skeleton pixels")
    segs, cls = np.concatenate(segs), np.concatenate(cls)
    return {"segs": segs, "cls": cls, "lone": int(lone_r.size)}


def draw_skeleton(ax, seg: dict, window=None, lw: float = SKELETON_LW) -> None:
    """Draw the vector skeleton: the rest in white at SKELETON_ALPHA, the
    ring of interior lacunae in opaque vermillion on top. `window` (x0, x1,
    y0, y1) keeps only segments touching that box (smaller PDFs)."""
    from matplotlib.collections import LineCollection

    segs, cls = seg["segs"], seg["cls"]
    if window is not None:
        x0, x1, y0, y1 = window
        xs, ys = segs[:, :, 0], segs[:, :, 1]
        keep = ((xs >= x0 - 1) & (xs <= x1 + 1) & (ys >= y0 - 1) & (ys <= y1 + 1)).any(axis=1)
        segs, cls = segs[keep], cls[keep]
    for k, colour, alpha, z in ((CLS_REST, PALETTE["skeleton"], SKELETON_ALPHA, 2.0),
                                (CLS_RING, PALETTE["ring"], 1.0, 2.5)):
        sel = cls == k
        if sel.any():
            ax.add_collection(LineCollection(segs[sel], colors=colour, alpha=alpha, linewidths=lw,
                                             capstyle="round", joinstyle="round", zorder=z))


def region_contours(mask: np.ndarray, pad: int = 2) -> list[np.ndarray]:
    """Contours (x, y) of a binary mask along pixel edges, found inside its
    bounding box for speed."""
    from skimage import measure

    rr, cc = np.nonzero(mask)
    if rr.size == 0:
        return []
    r0, c0 = max(rr.min() - pad, 0), max(cc.min() - pad, 0)
    r1, c1 = min(rr.max() + pad + 1, mask.shape[0]), min(cc.max() + pad + 1, mask.shape[1])
    sub = np.pad(mask[r0:r1, c0:c1], 1)
    return [np.column_stack([c[:, 1] - 1 + c0, c[:, 0] - 1 + r0]) for c in measure.find_contours(sub.astype(float), 0.5)]


def lacuna_contours(d: dict) -> dict:
    if "_contours" not in d:
        idm = d["lacuna_id_map"]
        d["_contours"] = {r["lacuna_id"]: region_contours(idm == r["lacuna_id"]) for r in d["lacuna_rows"]}
    return d["_contours"]


def ring_contours(d: dict, lacuna_id: int) -> list[np.ndarray]:
    """Outer contour of the 30 px ring region of one lacuna: the pixels
    within 30 px of the lacuna masks whose nearest lacuna is this one."""
    return region_contours((d["dist"] <= RING_RADIUS_PX) & (d["nearest"] == lacuna_id))


def lacuna_label(d: dict, lacuna_id: int) -> str:
    """The number drawn beside a lacuna, with "c" when it lies in a flagged
    canal region."""
    return f"{lacuna_id}c" if lacuna_id in d["canal_ids"] else str(lacuna_id)


def count_line(d: dict) -> str:
    n_int, n_edge, n_rej = len(d["interior_ids"]), len(d["edge_ids"]), len(d["rejected"])
    return (f"{n_int} interior lacunae used in per-cell means ({n_edge} touching the frame, "
            f"{n_rej} rejected candidate{'s' if n_rej != 1 else ''})")


def draw_lacunae(ax, d: dict, lw: float = V2_OUTLINE_PT, numbers: bool = False, number_size: float = FONT_SIZE - 1.5,
                 only=None) -> None:
    """Outline each kept lacuna (cyan interior, yellow frame edge); with
    numbers, its id (and "c") beside it in the outline colour."""
    contours = lacuna_contours(d)
    idm = d["lacuna_id_map"]
    for row in d["lacuna_rows"]:
        lid = row["lacuna_id"]
        if only is not None and lid not in only:
            continue
        colour = PALETTE["edge"] if row["on_border"] else PALETTE["interior"]
        for c in contours[lid]:
            ax.plot(c[:, 0], c[:, 1], color=colour, lw=lw, solid_joinstyle="round", zorder=4)
        if numbers:
            cols = np.nonzero((idm == lid).any(axis=0))[0]
            right = cols.max() + 6
            if right > idm.shape[1] - 50:
                tx, ha = cols.min() - 6, "right"
            else:
                tx, ha = right, "left"
            ty = float(np.clip(row["centroid_row_px"], 16, idm.shape[0] - 16))
            ax.text(tx, ty, lacuna_label(d, lid), color=colour, ha=ha, va="center", fontsize=number_size,
                    fontweight="bold", path_effects=halo(1.4), zorder=6)
            d.setdefault("_label_xy", {})[lid] = (tx + (12 if ha == "left" else -12), ty)


def draw_roots(ax, d: dict, ids, size: float = 7.0, edge_lw: float = 0.3) -> int:
    """Magenta dots at the root cluster centres of the given lacunae.
    Returns the number of dots drawn."""
    pts = [p for i in ids for p in d["roots_xy"][str(i)]]
    if pts:
        a = np.array(pts)
        ax.scatter(a[:, 0], a[:, 1], s=size, c=PALETTE["root"], edgecolors="black", linewidths=edge_lw, zorder=5)
    return len(pts)


def overlay_image(d: dict, window=None) -> np.ndarray:
    """The raw red channel in the display window at 85% brightness."""
    return windowed_with(d["channel"], window) * OVERLAY_BRIGHTNESS


def windowed_with(channel: np.ndarray, window=None) -> np.ndarray:
    """The channel in the fixed dataset window, or in `window` (lo, hi)."""
    lo, hi = window if window is not None else display_window()
    return np.clip((channel - lo) / (hi - lo), 0, 1)


def show_image(ax, img: np.ndarray, x0: int = 0, y0: int = 0, interpolation: str = "antialiased") -> None:
    """imshow in global image coordinates: pixel (x, y) is centred on (x, y)."""
    h, w = img.shape[:2]
    ax.imshow(img, cmap="gray", vmin=0, vmax=1, interpolation=interpolation,
              extent=(x0 - 0.5, x0 + w - 0.5, y0 + h - 0.5, y0 - 0.5))
    ax.set_xlim(x0 - 0.5, x0 + w - 0.5)
    ax.set_ylim(y0 + h - 0.5, y0 - 0.5)
    ax.set_xticks([])
    ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_linewidth(0.5)


def padded_crop(img: np.ndarray, cx: int, cy: int, side: int) -> tuple[np.ndarray, int, int]:
    """A side x side crop centred on (cx, cy), zero padded outside the frame.
    Returns (crop, x0, y0) with (x0, y0) the global top left."""
    x0, y0 = int(cx - side // 2), int(cy - side // 2)
    out = np.zeros((side, side) + img.shape[2:], dtype=img.dtype)
    H, W = img.shape[:2]
    sx0, sy0 = max(x0, 0), max(y0, 0)
    sx1, sy1 = min(x0 + side, W), min(y0 + side, H)
    if sx1 > sx0 and sy1 > sy0:
        out[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = img[sy0:sy1, sx0:sx1]
    return out, x0, y0


def bbox_centre(d: dict, lacuna_id: int) -> tuple[int, int]:
    ys, xs = np.nonzero(d["lacuna_id_map"] == lacuna_id)
    return int(round((xs.min() + xs.max()) / 2)), int(round((ys.min() + ys.max()) / 2))


def frame_margin(d: dict, lacuna_id: int) -> int:
    """Smallest distance (px) from the lacuna's bounding box to the frame."""
    ys, xs = np.nonzero(d["lacuna_id_map"] == lacuna_id)
    H, W = d["lacuna_id_map"].shape
    return int(min(xs.min(), ys.min(), W - 1 - xs.max(), H - 1 - ys.max()))


def scale_bar_at(ax, length_px: int, colour: str = "white", fs: float = FONT_SIZE - 1, lw: float = 1.6) -> None:
    """A bar of length_px in the lower left of the current view, labelled in px
    (in micrometres only if config.PIXEL_SIZE_UM is set)."""
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    w, h = x1 - x0, abs(y0 - y1)
    bx, by = x0 + 0.05 * w, max(y0, y1) - 0.06 * h
    ax.plot([bx, bx + length_px], [by, by], color=colour, lw=lw, solid_capstyle="butt", zorder=7,
            path_effects=[patheffects.withStroke(linewidth=lw + 1.0, foreground="black")])
    label = f"{length_px * config.PIXEL_SIZE_UM:g} µm" if config.PIXEL_SIZE_UM else f"{length_px} px"
    ax.text(bx + length_px / 2, by - 0.02 * h, label, color=colour, ha="center", va="bottom", fontsize=fs,
            path_effects=halo(1.2), zorder=7)


def legend_rows(items: list, w_mm: float, fs: float = FONT_SIZE - 1) -> int:
    """How many rows legend_strip needs for these items at this width."""
    fig = plt.figure(figsize=(2, 1))
    renderer = fig.canvas.get_renderer()
    sw, pad, gap = 6.0, 1.0, 3.0
    rows, x = 1, 0.0
    for it in items:
        t = fig.text(0, 0, it["label"], fontsize=fs)
        tw = t.get_window_extent(renderer=renderer).width / fig.dpi * 25.4
        if x > 0 and x + sw + pad + tw > w_mm:
            rows, x = rows + 1, 0.0
        x += sw + pad + tw + gap
    plt.close(fig)
    return rows


def legend_height(items: list, w_mm: float) -> float:
    return 4.0 * legend_rows(items, w_mm) + 1.0


def legend_strip(fig, x_mm: float, y_mm: float, w_mm: float, h_mm: float, fig_w: float, fig_h: float,
                 items: list, fs: float = FONT_SIZE - 1, dark: bool = True) -> None:
    """A row (or rows) of colour keys with labels, drawn inside the figure.
    Each key is drawn on a small black swatch, as it looks over the image.
    items: dicts with kind in line, outline, dot, box, text and the style."""
    ax = mm_axes(fig, x_mm, y_mm, w_mm, h_mm, fig_w, fig_h)
    ax.set_xlim(0, w_mm)
    ax.set_ylim(0, h_mm)
    ax.axis("off")
    renderer = fig.canvas.get_renderer()
    sw, sh, pad, gap = 6.0, 2.8, 1.0, 3.0
    row_h = sh + 1.2
    x, y = 0.0, h_mm - row_h / 2
    for it in items:
        t = ax.text(0, 0, it["label"], fontsize=fs, va="center", ha="left")
        bb = t.get_window_extent(renderer=renderer)
        t.remove()
        tw = bb.width / fig.dpi * 25.4
        if x > 0 and x + sw + pad + tw > w_mm:
            x, y = 0.0, y - row_h
        k = it["kind"]
        if k == "frame":
            ax.add_patch(Rectangle((x + 0.4, y - sh / 2 + 0.2), sw - 0.8, sh - 0.4, facecolor="0.85", edgecolor="black",
                                   lw=1.4))
        elif dark:
            ax.add_patch(Rectangle((x, y - sh / 2), sw, sh, facecolor="black", edgecolor="none"))
        cx = x + sw / 2
        if k == "line":
            ax.plot([x + 0.8, x + sw - 0.8], [y, y], color=it["colour"], lw=it.get("lw", 1.0), ls=it.get("ls", "-"),
                    alpha=it.get("alpha", 1.0), solid_capstyle="butt")
        elif k == "outline":
            from matplotlib.patches import Ellipse

            ax.add_patch(Ellipse((cx, y), sw - 2.4, sh - 0.9, fill=False, ec=it["colour"], lw=it.get("lw", 0.6),
                                 ls=it.get("ls", "-")))
        elif k == "dot":
            ax.scatter([cx], [y], s=it.get("s", 9), c=it["colour"], edgecolors="black", linewidths=0.3, zorder=3)
        elif k == "box":
            ax.add_patch(Rectangle((x + 1.4, y - sh / 2 + 0.6), sw - 2.8, sh - 1.2, fill=False, ec=it["colour"],
                                   lw=it.get("lw", 0.6)))
        elif k == "text":
            ax.text(cx, y, it["text"], color=it["colour"], fontsize=fs, fontweight="bold", ha="center", va="center")
        elif k == "marker":
            ax.scatter([cx], [y], s=it.get("s", 9), marker=it.get("marker", "o"), facecolors=it.get("face", "black"),
                       edgecolors=it.get("edge", "black"), linewidths=0.6, zorder=3)
        elif k == "bar":
            ax.plot([x + 0.8, x + sw - 0.8], [y, y], color=it["colour"], lw=1.6, solid_capstyle="butt")
        ax.text(x + sw + pad, y, it["label"], fontsize=fs, va="center", ha="left")
        x += sw + pad + tw + gap


def save_to(fig, stem: Path, exts: tuple = ("png", "pdf")) -> None:
    """Write stem.png (300 dpi) and stem.pdf atomically (or only `exts`)."""
    stem.parent.mkdir(parents=True, exist_ok=True)
    for ext in exts:
        final = stem.with_name(f"{stem.name}.{ext}")
        tmp = stem.with_name(f"{stem.name}.tmp.{ext}")
        fig.savefig(tmp, dpi=300)
        os.replace(tmp, final)
    plt.close(fig)


def done_at(stem: Path, exts: tuple = ("png", "pdf")) -> bool:
    return all(stem.with_name(f"{stem.name}.{ext}").is_file() for ext in exts)


# Display windows (P8). The main per-image figures use the fixed dataset
# window; their variants in per_image/<image>/display_variants/ use the 1st
# and 99.8th percentile of that image's own red channel (PNG only, to keep
# the repository small). Display only; no measurement uses either window.
FIXED_WINDOW_NOTE = "Fixed display window for the dataset."
IMAGE_WINDOW_NOTE = "Display window: this image only, display only."


def image_window(d: dict) -> tuple[float, float]:
    lo, hi = (float(v) for v in np.percentile(d["channel"], WINDOW_PERCENTILES))
    return lo, hi


def exts_for(window) -> tuple:
    return ("png", "pdf") if window is None else ("png",)


def update_inset_log(name: str, key: str, entry: dict) -> None:
    """per_image/<image>/inset.json holds one entry per figure kind."""
    path = PER_IMAGE / name / "inset.json"
    log = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"image": name}
    log[key] = entry
    write_json(path, log)


def choose_network_insets(d: dict) -> tuple[list, dict]:
    """Three interior lacunae whose bounding box is at least
    INSET_FRAME_MARGIN_PX from the frame: the fewest roots, the roots
    closest to the image median (over all interior lacunae), the most roots.
    Ties go to the smallest id; a lacuna is used once."""
    roots = {c["lacuna_id"]: c["roots_count"] for c in d["cell_rows"]}
    med = float(np.median([roots[i] for i in d["interior_ids"]]))
    eligible = [i for i in d["interior_ids"] if frame_margin(d, i) >= INSET_FRAME_MARGIN_PX]
    picks, roles = [], []
    for role, key in (("fewest roots", lambda i: (roots[i], i)), ("most roots", lambda i: (-roots[i], i)),
                      ("roots closest to the median", lambda i: (abs(roots[i] - med), i))):
        left = [i for i in eligible if i not in picks]
        if left:
            picks.append(min(left, key=key))
            roles.append(role)
    order = sorted(range(len(picks)), key=lambda k: ("fewest roots", "roots closest to the median",
                                                     "most roots").index(roles[k]))
    picks, roles = [picks[k] for k in order], [roles[k] for k in order]
    log = {"rule": f"interior lacunae with the bounding box at least {INSET_FRAME_MARGIN_PX} px from the frame; "
                   "fewest roots, roots closest to the interior median, most roots; ties to the smallest id; "
                   "each lacuna once",
           "interior_median_roots": med, "eligible": eligible,
           "insets": [{"lacuna_id": i, "roots": roots[i], "role": r} for i, r in zip(picks, roles)]}
    return picks, log


def box_letter_corner(d: dict, x0: int, y0: int, side: int, used: list, others: tuple = ()) -> tuple:
    """Where to put an inset letter: the inside corner of the box (top left,
    top right, bottom left, bottom right, in that order of preference) that
    is not inside another inset box (`others`, as (x0, y0, side)) and is
    farthest from lacuna numbers, lacuna pixels and letters already placed.
    Returns (x, y, ha, va)."""
    idm = d["lacuna_id_map"]
    labels = list(d.get("_label_xy", {}).values()) + list(used)
    best = None
    for k, (cx, cy, ha, va) in enumerate(((x0 + 8, y0 + 8, "left", "top"), (x0 + side - 8, y0 + 8, "right", "top"),
                                          (x0 + 8, y0 + side - 8, "left", "bottom"),
                                          (x0 + side - 8, y0 + side - 8, "right", "bottom"))):
        mx = cx + (15 if ha == "left" else -15)
        my = cy + (15 if va == "top" else -15)
        near = min((np.hypot(mx - lx, my - ly) for lx, ly in labels), default=1e9)
        r0, r1 = int(max(my - 20, 0)), int(min(my + 20, idm.shape[0]))
        c0, c1 = int(max(mx - 20, 0)), int(min(mx + 20, idm.shape[1]))
        busy = int((idm[r0:r1, c0:c1] > 0).sum())
        inside = any(ox - 0.5 <= mx <= ox + oside - 0.5 and oy - 0.5 <= my <= oy + oside - 0.5
                     for ox, oy, oside in others)
        score = (inside, near < 45, busy, k)
        if best is None or score < best[0]:
            best = (score, (cx, cy, ha, va))
    return best[1]


NETWORK_CAPTION = ("Vermillion: skeleton within 30 px of an interior lacuna (the ring 30 px measure). "
                   "White: the rest of the skeleton. Pre-validation, pixel units.")


def network_legend_items(d: dict, inset_ring: bool = True, inset_box: bool = True) -> list:
    items = [
        {"kind": "outline", "colour": PALETTE["interior"], "label": "interior lacuna (in per-cell means)"},
        {"kind": "outline", "colour": PALETTE["edge"], "label": "lacuna touching the frame (not in per-cell means)"},
        {"kind": "line", "colour": PALETTE["ring"], "lw": 1.2, "label": "skeleton within 30 px of an interior lacuna"},
        {"kind": "line", "colour": PALETTE["skeleton"], "alpha": SKELETON_ALPHA, "lw": 1.2, "label": "rest of the skeleton"},
        {"kind": "dot", "colour": PALETTE["root"], "label": "root of an interior lacuna"},
    ]
    if inset_ring:
        items.append({"kind": "line", "colour": "white", "lw": 0.6, "ls": (0, (3, 2)), "label": "30 px ring of the inset lacuna"})
    if inset_box:
        items.append({"kind": "box", "colour": PALETTE["box"], "label": "inset region"})
    if d["canal_ids"]:
        items.append({"kind": "text", "text": "c", "colour": PALETTE["interior"],
                      "label": "inside a flagged canal region, may be vascular"})
    return items


def network_values(d: dict) -> dict:
    """Per lacuna: the pipeline numbers and what is drawn (rule 11)."""
    out = []
    for cr in d["cell_rows"]:
        i = cr["lacuna_id"]
        interior = i in d["interior_ids"]
        out.append({"lacuna_id": i, "on_border": cr["on_border"], "roots_count": cr["roots_count"],
                    "magenta_dots": len(d["roots_xy"][str(i)]) if interior else 0,
                    "ring_length_r30_px": cr["ring_length_r30_px"],
                    "vermillion_px": int(d["ring_interior_count"][i]),
                    "ring_px_drawn_white": 0 if interior else int(d["ring_count"][i])})
    return {"image": d["short"], "status": "pre-validation", "units": "px",
            "check": "per interior lacuna vermillion_px == ring_length_r30_px and magenta_dots == roots_count; "
                     "edge lacunae: their ring is drawn white and equals ring_length_r30_px",
            "lacunae": out}


def figure_network(name: str, cells: list | None = None, window=None, stem: Path | None = None,
                   window_note: str | None = None) -> None:
    """N1: (A) raw red channel; (B) the overlay: raw at 85%, interior
    lacunae cyan, frame-edge lacunae yellow, skeleton within 30 px of an
    interior lacuna vermillion, the rest white at 70%, roots magenta; (C to
    E) three lacunae at 3x with the same overlay and the dashed 30 px ring
    contour of the inset lacuna."""
    d = image_data(name)
    name = d["short"]
    stem = stem or PER_IMAGE / name / "network"
    window_note = window_note or (FIXED_WINDOW_NOTE if window is None else IMAGE_WINDOW_NOTE)
    if done_at(stem, exts_for(window)):
        print(stem.relative_to(ROOT), "exists, skipped")
        return
    if cells is None:
        cells, log = choose_network_insets(d)
    else:
        log = {"rule": "set with -c", "insets": [{"lacuna_id": i} for i in cells]}
    for i in cells:
        if i not in d["interior_ids"]:
            raise ValueError(f"{name}: lacuna {i} is not an interior lacuna")
    if window is None:
        update_inset_log(name, "network", log)
        write_json(PER_IMAGE / name / "network_check.json", network_values(d))
    H, W = d["lacuna_id_map"].shape

    margin, gap_ab, panel, gap_in = 1.0, 2.0, 88.0, 3.0
    side = int(round(((FIG_WIDTH_MM - 2 * margin - 2 * gap_in) / 3) * W / (3 * panel)))
    inset = 3 * panel * side / W
    cap_h, legend_h, title_h, count_h = 7.5, 9.0, 4.5, 5.0
    y_inset = cap_h + legend_h + 1.0
    y_panel = y_inset + inset + title_h + count_h
    fig_h = y_panel + panel + title_h
    fig = plt.figure(figsize=(FIG_WIDTH_MM * MM, fig_h * MM))
    axA = mm_axes(fig, margin, y_panel, panel, panel, FIG_WIDTH_MM, fig_h)
    axB = mm_axes(fig, margin + panel + gap_ab, y_panel, panel, panel, FIG_WIDTH_MM, fig_h)

    show_image(axA, windowed_with(d["channel"], window))
    axA.set_title(f"{name}, red channel", pad=2)
    scale_bar_at(axA, SCALE_BAR_PX)

    show_image(axB, overlay_image(d, window))
    draw_skeleton(axB, d["segments"])
    draw_lacunae(axB, d, numbers=True)
    n_dots = draw_roots(axB, d, d["interior_ids"], size=3.0, edge_lw=0.25)
    expected = sum(c["roots_count"] for c in d["cell_rows"] if c["lacuna_id"] in d["interior_ids"])
    if n_dots != expected:
        raise AssertionFailed(f"{name}: {n_dots} dots drawn, {expected} roots in results/")
    axB.set_title("lacunae, skeleton and roots over the image at 85%", pad=2)
    axB.text(1.0, -0.012, count_line(d), transform=axB.transAxes, ha="right", va="top")

    letters = "CDE"
    used = []
    roots = {c["lacuna_id"]: c for c in d["cell_rows"]}
    corners = []
    for lid in cells:
        cx, cy = bbox_centre(d, lid)
        corners.append((int(np.clip(cx - side // 2, 0, W - side)), int(np.clip(cy - side // 2, 0, H - side))))
    for k, lid in enumerate(cells):
        x0, y0 = corners[k]
        axB.add_patch(Rectangle((x0 - 0.5, y0 - 0.5), side, side, fill=False, ec=PALETTE["box"], lw=0.6, zorder=6))
        others = tuple((ox, oy, side) for j, (ox, oy) in enumerate(corners) if j != k)
        lx, ly, ha, va = box_letter_corner(d, x0, y0, side, used, others)
        used.append((lx, ly))
        axB.text(lx, ly, letters[k], color=PALETTE["box"], ha=ha, va=va,
                 fontsize=FONT_SIZE, fontweight="bold", path_effects=halo(1.6), zorder=7)
        ax = mm_axes(fig, margin + k * (inset + gap_in), y_inset, inset, inset, FIG_WIDTH_MM, fig_h)
        img = overlay_image(d, window)[y0:y0 + side, x0:x0 + side]
        show_image(ax, img, x0, y0, interpolation="nearest")
        draw_skeleton(ax, d["segments"], window=(x0, x0 + side, y0, y0 + side), lw=0.5)
        draw_lacunae(ax, d, lw=V2_OUTLINE_PT)
        for c in ring_contours(d, lid):
            ax.plot(c[:, 0], c[:, 1], color="white", lw=0.6, ls=(0, (3, 2)), zorder=4.5)
        in_view = [i for i in d["interior_ids"]
                   if any(x0 <= p[0] < x0 + side and y0 <= p[1] < y0 + side for p in d["roots_xy"][str(i)])]
        draw_roots(ax, d, in_view, size=14.0, edge_lw=0.4)
        ax.set_xlim(x0 - 0.5, x0 + side - 0.5)
        ax.set_ylim(y0 + side - 0.5, y0 - 0.5)
        c = roots[lid]
        ax.set_title(f"L{lid}: {c['roots_count']} roots, ring 30 px = {c['ring_length_r30_px']} px", pad=2)
        if k == 0:
            scale_bar_at(ax, 50)
        panel_letter(fig, ax, letters[k], dx=-0.004)
    panel_letter(fig, axA, "A", dx=-0.004)
    panel_letter(fig, axB, "B", dx=-0.004)

    legend_strip(fig, margin, cap_h, FIG_WIDTH_MM - 2 * margin, legend_h, FIG_WIDTH_MM, fig_h,
                 network_legend_items(d))
    fig.text(margin / FIG_WIDTH_MM, 1.6 / fig_h, NETWORK_CAPTION + "\n" + window_note,
             ha="left", va="bottom", fontsize=FONT_SIZE - 0.5)
    save_to(fig, stem, exts_for(window))
    print(stem.relative_to(ROOT), "written; insets", cells)


GALLERY_TILE_PX = 240  # fixed crop per lacuna, the same for every tile
GALLERY_ZOOM = 3  # 3 output pixels per image pixel at 300 dpi
GALLERY_COLS, GALLERY_PER_PAGE = 4, 16


def gallery_tiles(d: dict, ids: list, fig, x_mm: float, top_mm: float, fig_w: float, fig_h: float,
                  window=None) -> list:
    """Draw one tile per lacuna id in a 4 column grid. Returns the per-tile
    check rows."""
    tile = GALLERY_TILE_PX * GALLERY_ZOOM / 300 * 25.4
    gap, title_h = 3.0, 4.5
    img = overlay_image(d, window)
    checks = []
    cells = {c["lacuna_id"]: c for c in d["cell_rows"]}
    areas = {r["lacuna_id"]: r["area_px2"] for r in d["lacuna_rows"]}
    for k, lid in enumerate(ids):
        r, c = divmod(k, GALLERY_COLS)
        ax = mm_axes(fig, x_mm + c * (tile + gap), fig_h - top_mm - title_h - r * (tile + title_h + gap) - tile,
                     tile, tile, fig_w, fig_h)
        cx, cy = bbox_centre(d, lid)
        crop, x0, y0 = padded_crop(img, cx, cy, GALLERY_TILE_PX)
        show_image(ax, crop, x0, y0, interpolation="nearest")
        view = (x0, x0 + GALLERY_TILE_PX, y0, y0 + GALLERY_TILE_PX)
        draw_skeleton(ax, d["segments"], window=view, lw=0.5)
        draw_lacunae(ax, d)
        for cc in ring_contours(d, lid):
            ax.plot(cc[:, 0], cc[:, 1], color="white", lw=0.6, ls=(0, (3, 2)), zorder=4.5)
        n_dots = draw_roots(ax, d, [lid], size=14.0, edge_lw=0.4)
        cell = cells[lid]
        if n_dots != cell["roots_count"] or int(d["ring_interior_count"][lid]) != cell["ring_length_r30_px"]:
            raise AssertionFailed(f"{d['short']} L{lid}: drawn {n_dots} dots, {int(d['ring_interior_count'][lid])} "
                                  f"vermillion px; results/ {cell['roots_count']}, {cell['ring_length_r30_px']}")
        ax.set_xlim(x0 - 0.5, x0 + GALLERY_TILE_PX - 0.5)
        ax.set_ylim(y0 + GALLERY_TILE_PX - 0.5, y0 - 0.5)
        ax.set_title(f"L{lacuna_label(d, lid)}  {cell['roots_count']} roots  ring30 {cell['ring_length_r30_px']} px  "
                     f"{areas[lid]:.0f} px²", pad=2)
        if k == 0:
            scale_bar_at(ax, 50)
        pts = np.array(d["roots_xy"][str(lid)]).reshape(-1, 2)
        ring_pix = (d["classes"] == CLS_RING) & (d["nearest"] == lid)
        rr, cc2 = np.nonzero(ring_pix)
        checks.append({"lacuna_id": lid, "roots_count": cell["roots_count"], "magenta_dots": n_dots,
                       "dots_inside_tile": int(((pts[:, 0] >= x0) & (pts[:, 0] < x0 + GALLERY_TILE_PX) &
                                                (pts[:, 1] >= y0) & (pts[:, 1] < y0 + GALLERY_TILE_PX)).sum()),
                       "ring_length_r30_px": cell["ring_length_r30_px"], "vermillion_px": int(ring_pix.sum()),
                       "vermillion_px_inside_tile": int(((cc2 >= x0) & (cc2 < x0 + GALLERY_TILE_PX) &
                                                         (rr >= y0) & (rr < y0 + GALLERY_TILE_PX)).sum()),
                       "tile_x0": x0, "tile_y0": y0})
    return checks


def figure_gallery(name: str, window=None, stem: Path | None = None, window_note: str | None = None) -> None:
    """N2: one tile per interior lacuna, a fixed 240 px crop centred on it
    (zero padded outside the frame), all at 3x, with the N1 colours, its
    roots and the dashed contour of its 30 px ring."""
    d = image_data(name)
    name = d["short"]
    stem = stem or PER_IMAGE / name / "gallery"
    ids = list(d["interior_ids"])
    pages = [ids[i:i + GALLERY_PER_PAGE] for i in range(0, len(ids), GALLERY_PER_PAGE)]
    stems = [stem] if len(pages) == 1 else [stem.with_name(f"{stem.name}_p{k + 1}") for k in range(len(pages))]
    window_note = window_note or (FIXED_WINDOW_NOTE if window is None else IMAGE_WINDOW_NOTE)
    if all(done_at(s, exts_for(window)) for s in stems):
        print(stem.relative_to(ROOT), "exists, skipped")
        return
    tile = GALLERY_TILE_PX * GALLERY_ZOOM / 300 * 25.4
    margin, gap, title_h = 2.0, 3.0, 4.5
    fig_w = 2 * margin + GALLERY_COLS * tile + (GALLERY_COLS - 1) * gap
    all_checks = []
    for page, s in zip(pages, stems):
        rows = int(np.ceil(len(page) / GALLERY_COLS))
        items = network_legend_items(d, inset_ring=False, inset_box=False)
        items[4] = {"kind": "dot", "colour": PALETTE["root"], "label": "root of the tile lacuna"}
        items.insert(5, {"kind": "line", "colour": "white", "lw": 0.6, "ls": (0, (3, 2)),
                         "label": "30 px ring of the tile lacuna"})
        if not any(i in d["canal_ids"] for i in page):
            items = [it for it in items if it.get("text") != "c"]
        head, legend_h, foot_h = 6.0, (10.0 if len(items) > 6 else 6.0), 7.5
        fig_h = head + rows * (tile + title_h + gap) + legend_h + foot_h
        fig = plt.figure(figsize=(fig_w * MM, fig_h * MM))
        fig.text(margin / fig_w, 1 - 1.5 / fig_h, f"{name}: interior lacunae at 3x (240 px tiles)", ha="left", va="top",
                 fontsize=FONT_SIZE + 1, fontweight="bold")
        fig.text(1 - margin / fig_w, 1 - 1.5 / fig_h, count_line(d), ha="right", va="top", fontsize=FONT_SIZE)
        all_checks += gallery_tiles(d, page, fig, margin, head, fig_w, fig_h, window)
        legend_strip(fig, margin, foot_h, fig_w - 2 * margin, legend_h, fig_w, fig_h, items)
        n_edge = len(d["edge_ids"])
        note = (f"{n_edge} lacuna{'e' if n_edge != 1 else ''} touching the frame not shown (left out of per-cell means). "
                "Tiles: 240 px squares centred on each interior lacuna, zero padded outside the frame, one scale. "
                + NETWORK_CAPTION + " " + window_note)
        fig.text(margin / fig_w, 1.5 / fig_h, note, ha="left", va="bottom", fontsize=FONT_SIZE - 0.5, wrap=True)
        save_to(fig, s, exts_for(window))
        print(s.relative_to(ROOT), "written")
    if window is None:
        write_json(PER_IMAGE / name / "gallery_check.json",
                   {"image": name, "status": "pre-validation", "units": "px",
                    "check": "per tile: magenta_dots == roots_count and vermillion_px == ring_length_r30_px",
                    "tiles": all_checks})


TILES_DIR = OUT / "validation_tiles"
KEY_COLUMNS = ["code", "image", "lacuna_id", "centre_x", "centre_y"]

TILES_README = """# Hand-count tiles

Pre-validation, pixel units. One tile per interior lacuna of the 8 WT sections: a 240 x 240 px crop of
the raw red channel (8-bit, the values of the image file, no display window), centred on the centre of
the lacuna's bounding box, zero padded (black) where the crop leaves the frame. There is no outline,
skeleton, root dot or number on any tile, and the PNG files hold pixel data only (no file name or text
in any metadata).

**Purpose.** These tiles are for counting roots by hand without seeing the pipeline result. Count the
roots (distinct canalicular threads leaving the lacuna surface) of the lacuna at the centre of each tile
and enter the number in `annotation_template.csv` (columns code, hand_roots, hand_notes). Do not open
`figures_out/per_image/` or `results/` while counting.

**Codes.** The tiles are named T001, T002 and so on in a random order drawn from the operating system's
random source, so the order cannot be rebuilt from this repository. The key (code, image, lacuna id,
centre x and y) stays outside the repository, at the path given with `-k` when the tiles were made; the
command refuses a key path inside the repository. Join the key to the filled template to compare the
hand counts with `roots_count` in `results/<image>/canaliculi_measurements.json`.

**Limits.** The tiles hide the pipeline result, not the image: a tile can be matched to its section by
appearance. A neighbouring lacuna can be partly visible at a tile edge; only the centre lacuna is
counted.

Regenerate (the key path must be outside the repository):
`python -u figures/make_figures.py tiles -k PATH_OUTSIDE_REPO/validation_tiles_key.csv`
With an existing key the tiles are rebuilt from it; without one, a new random order is drawn.
"""


def inside_repo(path: Path) -> bool:
    try:
        path.resolve().relative_to(ROOT.resolve())
        return True
    except ValueError:
        return False


def tile_pixels(d: dict, lacuna_id: int) -> np.ndarray:
    """The 240 px raw red crop (uint8, the file's values) centred on the
    lacuna's bounding box centre, zero padded outside the frame."""
    raw8 = np.round(d["channel"] * 255).astype(np.uint8)
    cx, cy = bbox_centre(d, lacuna_id)
    crop, _x0, _y0 = padded_crop(raw8, cx, cy, GALLERY_TILE_PX)
    return crop


def write_tile_png(path: Path, pixels: np.ndarray) -> None:
    """8-bit greyscale PNG with pixel data only (no text, time or dpi chunk)."""
    from PIL import Image

    tmp = path.with_name(path.name + ".tmp")
    Image.fromarray(pixels).save(tmp, format="PNG")
    os.replace(tmp, path)


def make_validation_tiles(key_path: Path) -> None:
    """N3: one raw red tile per interior lacuna of every image, under random
    codes; the key goes to key_path, which must be outside the repository."""
    import csv
    import secrets

    if inside_repo(key_path):
        raise SystemExit(f"refused: the key path {key_path} is inside the repository")
    TILES_DIR.mkdir(parents=True, exist_ok=True)
    if key_path.is_file():
        with open(key_path, newline="") as f:
            key = list(csv.DictReader(f))
        print(f"using the existing key ({len(key)} tiles)")
    else:
        if list(TILES_DIR.glob("T*.png")):
            raise SystemExit("refused: tiles exist but the key is missing; their key cannot be rebuilt")
        entries = []
        for p in image_paths():
            d = image_data(short(p))
            for lid in d["interior_ids"]:
                cx, cy = bbox_centre(d, lid)
                entries.append({"image": d["short"], "lacuna_id": lid, "centre_x": cx, "centre_y": cy})
        secrets.SystemRandom().shuffle(entries)
        key = [{"code": f"T{k + 1:03d}", **e} for k, e in enumerate(entries)]
        key_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = key_path.with_name(key_path.name + ".tmp")
        with open(tmp, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=KEY_COLUMNS, lineterminator="\n")
            w.writeheader()
            w.writerows(key)
        os.replace(tmp, key_path)
        print(f"key written outside the repository ({len(key)} tiles)")
    data, written = {}, 0
    for row in key:
        out = TILES_DIR / f"{row['code']}.png"
        if out.is_file():
            continue
        name = row["image"]
        if name not in data:
            data[name] = image_data(name)
        write_tile_png(out, tile_pixels(data[name], int(row["lacuna_id"])))
        written += 1
    template = TILES_DIR / "annotation_template.csv"
    if not template.is_file():
        lines = ["code,hand_roots,hand_notes"] + [f"{r['code']},," for r in sorted(key, key=lambda r: r["code"])]
        tmp = template.with_name(template.name + ".tmp")
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.replace(tmp, template)
    readme = TILES_DIR / "README.md"
    if not readme.is_file():
        tmp = readme.with_name(readme.name + ".tmp")
        tmp.write_text(TILES_README, encoding="utf-8")
        os.replace(tmp, readme)
    print(f"{written} tiles written, {len(key) - written} existed; {TILES_DIR.relative_to(ROOT)}")


def figure_display_variants(name: str) -> None:
    """P8: the overview, network and gallery of one image with the image's own
    display window, PNG only, in per_image/<image>/display_variants/."""
    d = image_data(name)
    name = d["short"]
    win = image_window(d)
    folder = PER_IMAGE / name / "display_variants"
    write_json(folder / "display_window.json",
               {"image": name, "lo": win[0], "hi": win[1], "lo_8bit": win[0] * 255, "hi_8bit": win[1] * 255,
                "percentiles": list(WINDOW_PERCENTILES),
                "note": "Display window of this image only: the 1st and 99.8th percentile of its red channel. "
                        "Display only; no measurement uses it. The main figures use the fixed dataset window "
                        "(figures_out/display_window.json)."})
    figure_image(name, window=win, stem=folder / "overview_image_window")
    figure_network(name, window=win, stem=folder / "network_image_window")
    figure_gallery(name, window=win, stem=folder / "gallery_image_window")


FIG02_IMAGE = "543-2"


def copy_fig02() -> None:
    """Fig02 is a copy of the network figure of 543-2 (per_image/543-2/network)."""
    import shutil

    src = PER_IMAGE / FIG02_IMAGE / "network"
    for ext in ("png", "pdf"):
        a = src.with_name(f"{src.name}.{ext}")
        b = fig_stem("Fig02").with_name(f"Fig02_network_overlay_{FIG02_IMAGE}.{ext}")
        b.parent.mkdir(parents=True, exist_ok=True)
        if b.is_file() and b.read_bytes() == a.read_bytes():
            continue
        tmp = b.with_name(b.name + ".tmp")
        shutil.copyfile(a, tmp)
        os.replace(tmp, b)
        print(b.relative_to(ROOT), "written")


def _selftest_n0() -> None:
    """N0 checks on every image: the data equal results/, the vermillion
    pixels equal ring_length_r30_px per interior lacuna, the dots equal
    roots_count, and the vector skeleton covers exactly the skeleton."""
    for p in image_paths():
        d = image_data(short(p))
        n_ring = int((d["classes"] == CLS_RING).sum())
        n_rest = int((d["classes"] == CLS_REST).sum())
        print(f"{d['short']}: {len(d['interior_ids'])} interior, {len(d['edge_ids'])} edge, "
              f"{len(d['rejected'])} rejected >= {REJECTED_MIN_DRAW_PX2} px2, canal-marked {d['canal_ids']}; "
              f"skeleton {int(d['skeleton'].sum())} px = ring {n_ring} + rest {n_rest}; "
              f"{len(d['segments']['segs'])} segments, {d['segments']['lone']} lone px; checks PASS")


# F1 per-image figure -------------------------------------------------------------------

INSET_MARGIN_PX = 16
INSET_ZOOM = 3.0


def choose_inset_cell(out: dict) -> tuple[int, str]:
    """The interior lacuna whose roots count is closest to the image median
    over interior lacunae; ties go to the smallest id."""
    interior = [(r["lacuna_id"], c["roots_count"]) for r, c in zip(out["lacuna_rows"], out["cell_rows"])
                if not r["on_border"]]
    med = float(np.median([n for _i, n in interior]))
    best = min(interior, key=lambda t: (abs(t[1] - med), t[0]))
    return best[0], f"interior median roots {med:g}; lacuna {best[0]} has {best[1]} roots (closest, ties to smallest id)"


INSET_OVERRIDES = ROOT / "figures" / "inset_overrides.csv"


def inset_override(name: str) -> int | None:
    """The lacuna id set for an image in figures/inset_overrides.csv (columns
    image, lacuna_id), or None. The file is empty (header only) by default."""
    import csv

    if not INSET_OVERRIDES.is_file():
        return None
    with open(INSET_OVERRIDES, newline="") as f:
        for row in csv.DictReader(f):
            if row.get("image", "").strip() == name and row.get("lacuna_id", "").strip():
                return int(row["lacuna_id"])
    return None


def choose_overview_inset(d: dict) -> tuple[int, dict]:
    """The overview inset: among interior lacunae whose bounding box is at
    least INSET_FRAME_MARGIN_PX from the frame (the network figure's rule),
    the roots closest to the interior median, then the area closest to the
    interior median area, then the smallest id."""
    roots = {c["lacuna_id"]: c["roots_count"] for c in d["cell_rows"]}
    areas = {r["lacuna_id"]: r["area_px2"] for r in d["lacuna_rows"]}
    med_r = float(np.median([roots[i] for i in d["interior_ids"]]))
    med_a = float(np.median([areas[i] for i in d["interior_ids"]]))
    eligible = [i for i in d["interior_ids"] if frame_margin(d, i) >= INSET_FRAME_MARGIN_PX]
    pool = eligible or list(d["interior_ids"])
    best = min(pool, key=lambda i: (abs(roots[i] - med_r), abs(areas[i] - med_a), i))
    return best, {"rule": f"interior lacunae with the bounding box at least {INSET_FRAME_MARGIN_PX} px from the "
                          "frame; roots closest to the interior median, then area closest to the interior median "
                          "area, then the smallest id"
                          + ("" if eligible else "; no lacuna was eligible, so all interior lacunae were used"),
                  "interior_median_roots": med_r, "interior_median_area_px2": med_a, "eligible": eligible,
                  "inset": {"lacuna_id": best, "roots": roots[best], "area_px2": areas[best],
                            "frame_margin_px": frame_margin(d, best)}}


def figure_image(name: str, cell: int | None = None, low_cut: bool = False, window=None,
                 stem: Path | None = None) -> None:
    """The per-image overview (F1): (A) red channel; (B) kept lacunae with
    numbers ("c": in a flagged canal region) and the rejected lacuna-scale
    candidates, grey dashed with their reason; (C) the skeleton with the
    inset box; and the inset lacuna at 3x. With low_cut, objects kept only at
    0.8 t_hi are added to B (dotted), written to a separate file."""
    d = image_data(name)
    name = d["short"]
    fig_name = "overview" + ("_low_cut_layer" if low_cut else "")
    stem = stem or PER_IMAGE / name / fig_name
    if done_at(stem, exts_for(window)):
        print(stem.relative_to(ROOT), "exists, skipped")
        return
    if cell is not None:
        log = {"rule": f"set with -c {cell}", "inset": {"lacuna_id": cell}}
    elif inset_override(name) is not None:
        cell = inset_override(name)
        log = {"rule": f"set in {INSET_OVERRIDES.relative_to(ROOT).as_posix()}", "inset": {"lacuna_id": cell}}
    else:
        cell, log = choose_overview_inset(d)
    if cell not in d["interior_ids"]:
        raise ValueError(f"{name}: inset lacuna {cell} is not an interior lacuna")
    if not low_cut and window is None:
        update_inset_log(name, "overview", log)
    print(f"{fig_name}: inset lacuna {cell} ({log['rule']})")

    # Inset crop: a square around the lacuna's bounding box plus a margin.
    ys, xs = np.nonzero(d["lacuna_id_map"] == cell)
    side = int(max(ys.max() - ys.min(), xs.max() - xs.min()) + 1 + 2 * INSET_MARGIN_PX)
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    H, W = d["lacuna_id_map"].shape
    x0 = int(np.clip(round(cx - side / 2), 0, W - side))
    y0 = int(np.clip(round(cy - side / 2), 0, H - side))

    # Layout in mm: three square panels and an inset column at 3x the
    # panel scale, filling 180 mm; count line, legend and caption below.
    margin, gap = 1.0, 2.5
    panel = (FIG_WIDTH_MM - 2 * margin - 3 * gap) / (3 + INSET_ZOOM * side / W)
    inset = INSET_ZOOM * side / W * panel
    items = lacuna_legend_items(d, rejected=True, low_cut=low_cut) + [
        {"kind": "line", "colour": PALETTE["ring"], "lw": 1.2, "label": "skeleton within 30 px of an interior lacuna"},
        {"kind": "line", "colour": PALETTE["skeleton"], "alpha": SKELETON_ALPHA, "lw": 1.2,
         "label": "rest of the skeleton"},
        {"kind": "dot", "colour": PALETTE["root"], "label": "root of an interior lacuna"},
        {"kind": "line", "colour": "white", "lw": 0.6, "ls": (0, (3, 2)), "label": "30 px ring of the inset lacuna"},
        {"kind": "box", "colour": PALETTE["box"], "label": "inset region"}]
    top, count_h, cap_h = 5.0, 5.0, 7.5
    legend_h = legend_height(items, FIG_WIDTH_MM - 2 * margin)
    bottom = cap_h + legend_h + count_h
    fig_h = bottom + panel + top
    fig = plt.figure(figsize=(FIG_WIDTH_MM * MM, fig_h * MM))
    axA = mm_axes(fig, margin, bottom, panel, panel, FIG_WIDTH_MM, fig_h)
    axB = mm_axes(fig, margin + panel + gap, bottom, panel, panel, FIG_WIDTH_MM, fig_h)
    axC = mm_axes(fig, margin + 2 * (panel + gap), bottom, panel, panel, FIG_WIDTH_MM, fig_h)
    axI = mm_axes(fig, margin + 3 * (panel + gap), bottom + panel - inset, inset, inset, FIG_WIDTH_MM, fig_h)

    raw = windowed_with(d["channel"], window)
    image_axes(axA, raw)
    axA.set_title(f"{name}, red channel", pad=2)
    scale_bar(axA, W)

    show_image(axB, raw)
    draw_lacunae(axB, d, numbers=True, number_size=FONT_SIZE - 2)
    draw_rejected(axB, d)
    low = draw_low_cut(axB, d) if low_cut else 0
    axB.set_title("lacunae and rejected candidates", pad=2)
    axB.text(0.0, -0.02, count_line(d), transform=axB.transAxes, ha="left", va="top", fontsize=FONT_SIZE - 0.5)

    # C: the network overlay of the network figure at small size. Every
    # skeleton pixel is drawn, not only the threads attached to counted cells.
    over = overlay_image(d, window)
    show_image(axC, over)
    draw_skeleton(axC, d["segments"], lw=0.25)
    draw_lacunae(axC, d, lw=0.5)
    n_dots = draw_roots(axC, d, d["interior_ids"], size=1.2, edge_lw=0.15)
    if n_dots != sum(c["roots_count"] for c in d["cell_rows"] if c["lacuna_id"] in d["interior_ids"]):
        raise AssertionFailed(f"{name}: {n_dots} root dots in C differ from results/")
    axC.set_title("skeleton, all pixels, and roots", pad=2)
    axC.add_patch(Rectangle((x0 - 0.5, y0 - 0.5), side, side, fill=False, ec=PALETTE["box"], lw=0.8, zorder=6))

    show_image(axI, over[y0:y0 + side, x0:x0 + side], x0, y0, interpolation="nearest")
    draw_skeleton(axI, d["segments"], window=(x0, x0 + side, y0, y0 + side), lw=0.4)
    draw_lacunae(axI, d, lw=V2_OUTLINE_PT)
    for cc in ring_contours(d, cell):
        axI.plot(cc[:, 0], cc[:, 1], color="white", lw=0.5, ls=(0, (3, 2)), zorder=4.5)
    cellrow = next(c for c in d["cell_rows"] if c["lacuna_id"] == cell)
    if draw_roots(axI, d, [cell], size=6.0, edge_lw=0.3) != cellrow["roots_count"]:
        raise AssertionFailed(f"{name} L{cell}: inset dots differ from roots_count")
    axI.set_xlim(x0 - 0.5, x0 + side - 0.5)
    axI.set_ylim(y0 + side - 0.5, y0 - 0.5)
    axI.set_title(f"L{cell}, 3x", pad=2)
    axI.text(0.0, -0.04, f"{cellrow['roots_count']} roots (dots)\nring 30: {cellrow['ring_length_r30_px']} px",
             transform=axI.transAxes, ha="left", va="top", linespacing=1.2, fontsize=FONT_SIZE - 1.5)

    for ax, letter in ((axA, "A"), (axB, "B"), (axC, "C")):
        panel_letter(fig, ax, letter)
    legend_strip(fig, margin, cap_h, FIG_WIDTH_MM - 2 * margin, legend_h, FIG_WIDTH_MM, fig_h, items)
    cap = ("White and vermillion lines in C are all skeleton pixels, not only the threads attached to counted cells.\n"
           "Dim out-of-plane cells are not detected and are not drawn. "
           + (f"Dotted: {low} object{'s' if low != 1 else ''} kept only at 0.8 times t_hi (not the default output). "
              if low_cut else "")
           + (FIXED_WINDOW_NOTE if window is None else IMAGE_WINDOW_NOTE) + " Pre-validation, pixel units.")
    fig.text(margin / FIG_WIDTH_MM, 1.5 / fig_h, cap, ha="left", va="bottom", fontsize=FONT_SIZE - 0.5)
    save_to(fig, stem, exts_for(window))
    print(stem.relative_to(ROOT), "written")


def draw_rejected(ax, d: dict, lw: float = V2_OUTLINE_PT, letters: bool = True, fs: float = FONT_SIZE - 2) -> None:
    """Rejected lacuna-scale candidates (at least REJECTED_MIN_DRAW_PX2) as
    grey dashed outlines with the one-letter reason beside them: A aspect,
    S solidity, a area."""
    labels = d["labels"]
    H, W = labels.shape
    for r in d["rejected"]:
        for c in region_contours(labels == r["label"]):
            ax.plot(c[:, 0], c[:, 1], color=PALETTE["rejected"], lw=lw, ls=(0, (2.5, 1.5)), zorder=3.5,
                    path_effects=[patheffects.withStroke(linewidth=lw + 0.9, foreground="black")])
        if letters:
            r0, c0, r1, c1 = r["bbox"]
            tx, ha = (c1 + 4, "left") if c1 + 30 < W else (c0 - 4, "right")
            ty = float(np.clip((r0 + r1) / 2, 16, H - 16))
            ax.text(tx, ty, r["letter"], color=PALETTE["rejected"], ha=ha, va="center", fontsize=fs,
                    fontweight="bold", path_effects=halo(1.2), zorder=6)


LOW_CUT_SCALE = 0.8


def low_cut_objects(d: dict) -> np.ndarray:
    """Label image of the objects that the lacuna stage keeps at 0.8 t_hi and
    that overlap no lacuna kept at the default cut (option -r only)."""
    lac = lacunae.analyse_image(d["path"], d["t_hi"] * LOW_CUT_SCALE)
    out = np.zeros(lac["labels"].shape, dtype=np.int32)
    k = 0
    for region, _b in lac["kept"]:
        rr, cc = region.coords[:, 0], region.coords[:, 1]
        if (d["lacuna_id_map"][rr, cc] > 0).any():
            continue
        k += 1
        out[rr, cc] = k
    return out


def draw_low_cut(ax, d: dict) -> int:
    lab = low_cut_objects(d)
    for k in range(1, int(lab.max()) + 1):
        for c in region_contours(lab == k):
            ax.plot(c[:, 0], c[:, 1], color=PALETTE["low_cut"], lw=0.8, ls=(0, (0.8, 1.2)), zorder=3.6,
                    path_effects=[patheffects.withStroke(linewidth=1.7, foreground="black")])
    return int(lab.max())


def lacuna_legend_items(d: dict, rejected: bool = True, low_cut: bool = False, canal: bool | None = None) -> list:
    items = [
        {"kind": "outline", "colour": PALETTE["interior"], "label": "interior lacuna (in per-cell means)"},
        {"kind": "outline", "colour": PALETTE["edge"], "label": "lacuna touching the frame (not in per-cell means)"},
    ]
    if rejected:
        items.append({"kind": "outline", "colour": PALETTE["rejected"], "ls": (0, (2.5, 1.5)),
                      "label": "rejected candidate: A aspect, S solidity, a area"})
    if low_cut:
        items.append({"kind": "outline", "colour": PALETTE["low_cut"], "lw": 0.8, "ls": (0, (0.8, 1.2)),
                      "label": "kept only at 0.8 times t_hi"})
    if (d["canal_ids"] if canal is None else canal):
        items.append({"kind": "text", "text": "c", "colour": PALETTE["interior"],
                      "label": "inside a flagged canal region, may be vascular"})
    return items


# F2 contact sheet ----------------------------------------------------------------

def contact_count_lines(d: dict, three: bool = False) -> str:
    """The count line in two lines (three for a very small panel)."""
    n_int, n_edge, n_rej = len(d["interior_ids"]), len(d["edge_ids"]), len(d["rejected"])
    return (f"{n_int} interior lacunae used in per-cell means\n"
            f"({n_edge} touching the frame,{chr(10) if three else ' '}"
            f"{n_rej} rejected candidate{'s' if n_rej != 1 else ''})")


def draw_canal_marks(ax, d: dict, fs: float = FONT_SIZE - 2) -> None:
    """A "c" beside each kept lacuna in a flagged canal region, for panels
    that show no lacuna numbers."""
    idm = d["lacuna_id_map"]
    for row in d["lacuna_rows"]:
        lid = row["lacuna_id"]
        if lid not in d["canal_ids"]:
            continue
        colour = PALETTE["edge"] if row["on_border"] else PALETTE["interior"]
        cols = np.nonzero((idm == lid).any(axis=0))[0]
        tx, ha = (cols.max() + 8, "left") if cols.max() + 60 < idm.shape[1] else (cols.min() - 8, "right")
        ty = float(np.clip(row["centroid_row_px"], 30, idm.shape[0] - 30))
        ax.text(tx, ty, "c", color=colour, ha=ha, va="center", fontsize=fs, fontweight="bold",
                path_effects=halo(1.2), zorder=6)


def figure_contact(key_path: Path | None = None, rejected: bool = False) -> None:
    """All images, 2 rows by 4 columns, raw with thin outlines ("c" beside
    a lacuna in a flagged canal region) and the count lines under each, one
    display window. With rejected, the rejected candidates are drawn too.
    With a blinding key, panels are labelled with the codes and ordered by
    code."""
    import csv

    # Figure ids (figures v2, P3): Fig01 main; S02 with rejected candidates; S03 coded.
    if key_path:
        fig_name = "S03_contact_sheet_coded" + ("_with_rejected_candidates" if rejected else "")
    else:
        fig_name = "S02_contact_sheet_with_rejected_candidates" if rejected else "Fig01_contact_sheet"
    if done(fig_name):
        print(fig_name, "exists, skipped")
        return
    paths = image_paths()
    labels = {p: short(p) for p in paths}
    if key_path:
        with open(key_path, newline="") as f:
            code_of = {row["original_name"]: row["code"] for row in csv.DictReader(f)}
        labels = {p: code_of[p.name] for p in paths}
        paths = sorted(paths, key=lambda p: labels[p])
    n_cols, n_rows = 4, int(np.ceil(len(paths) / 4))
    data = {p: image_data(short(p)) for p in paths}
    any_canal = any(data[p]["canal_ids"] for p in paths)
    items = lacuna_legend_items(data[paths[0]], rejected=rejected, canal=any_canal)
    margin, gap, text_h, top, cap_h = 1.0, 2.0, 8.0, 5.0, 5.0
    legend_h = legend_height(items, FIG_WIDTH_MM - 2 * margin)
    panel = (FIG_WIDTH_MM - 2 * margin - (n_cols - 1) * gap) / n_cols
    fig_h = top + n_rows * (panel + text_h) + (n_rows - 1) * 3.5 + legend_h + cap_h
    fig = plt.figure(figsize=(FIG_WIDTH_MM * MM, fig_h * MM))
    for i, p in enumerate(paths):
        r, c = divmod(i, n_cols)
        d = data[p]
        x = margin + c * (panel + gap)
        y = fig_h - top - (r + 1) * panel - r * (text_h + 3.5)
        ax = mm_axes(fig, x, y, panel, panel, FIG_WIDTH_MM, fig_h)
        show_image(ax, windowed(d["channel"]))
        draw_lacunae(ax, d, lw=0.6)
        draw_canal_marks(ax, d)
        if rejected:
            draw_rejected(ax, d, lw=0.6, fs=FONT_SIZE - 2.5)
        ax.set_title(labels[p], pad=1.5, fontsize=FONT_SIZE, fontweight="bold")
        ax.text(0.5, -0.02, contact_count_lines(d), transform=ax.transAxes, ha="center", va="top",
                fontsize=FONT_SIZE - 1.5, linespacing=1.15)
        if i == 0:
            scale_bar(ax, d["lacuna_id_map"].shape[1])
    legend_strip(fig, margin, cap_h, FIG_WIDTH_MM - 2 * margin, legend_h, FIG_WIDTH_MM, fig_h, items)
    fig.text(margin / FIG_WIDTH_MM, 1.2 / fig_h, "Dim out-of-plane cells are not detected and are not drawn. "
             "Fixed display window for all panels. Pre-validation, pixel units.",
             ha="left", va="bottom", fontsize=FONT_SIZE - 0.5)
    save(fig, fig_name)
    print(fig_name, "written")


# F3 lacuna cut sensitivity --------------------------------------------------------

THRESHOLD_IMAGES = ["542_z06", "543-2", "682_z29"]
THRESHOLD_SCALES = [0.8, 0.9, 1.0, 1.1, 1.2]


def figure_thresholds() -> None:
    """Rows: three images. Columns: the lacuna cut t_hi at 0.8 to 1.2 times
    the image's own cut (1.0, the default, boxed). Outlines, canal marks and
    count lines. The defaults are not changed; the scaled cut is passed to
    the lacuna stage."""
    from skimage import measure

    fig_name = "Fig03_threshold_sensitivity"
    if done(fig_name):
        print(fig_name, "exists, skipped")
        return
    items = [{"kind": "outline", "colour": PALETTE["interior"], "label": "interior lacuna (in per-cell means)"},
             {"kind": "outline", "colour": PALETTE["edge"], "label": "lacuna touching the frame (not in per-cell means)"},
             {"kind": "frame", "label": "default cut"}]
    items.append({"kind": "text", "text": "c", "colour": PALETTE["interior"],
                  "label": "inside a flagged canal region, may be vascular"})
    margin, gap, text_h, top, left, cap_h = 1.0, 1.5, 9.0, 5.0, 6.0, 4.5
    legend_h = legend_height(items, FIG_WIDTH_MM - 2 * margin)
    n_cols = len(THRESHOLD_SCALES)
    panel = (FIG_WIDTH_MM - left - margin - (n_cols - 1) * gap) / n_cols
    fig_h = top + len(THRESHOLD_IMAGES) * (panel + text_h) + legend_h + cap_h
    fig = plt.figure(figsize=(FIG_WIDTH_MM * MM, fig_h * MM))
    log = {}
    for r, name in enumerate(THRESHOLD_IMAGES):
        path = path_of(name)
        _display, channel = lacunae.load_channel(path)
        _mask, t_hi = lacunae.multiotsu_lacuna_mask(channel)
        raw = windowed(channel)
        flagged = image_data(name)["flagged"]
        for c, scale in enumerate(THRESHOLD_SCALES):
            lac = lacunae.analyse_image(path, t_hi * scale) if scale != 1.0 else lacunae.analyse_image(path)
            id_map = np.zeros(lac["labels"].shape, dtype=np.int32)
            for lid, (region, _b) in enumerate(lac["kept"], start=1):
                id_map[lac["labels"] == region.label] = lid
            kept_labels = {region.label for region, _b in lac["kept"]}
            n_rej = sum(1 for rg in measure.regionprops(lac["labels"])
                        if rg.label not in kept_labels and rg.area >= REJECTED_MIN_DRAW_PX2)
            areas = np.bincount(id_map.ravel(), minlength=len(lac["rows"]) + 1)
            inside = np.bincount(id_map[flagged].ravel(), minlength=len(lac["rows"]) + 1)
            canal = [rr["lacuna_id"] for rr in lac["rows"]
                     if inside[rr["lacuna_id"]] / areas[rr["lacuna_id"]] >= CANAL_MARK_MIN_SHARE]
            dd = {"lacuna_id_map": id_map, "lacuna_rows": lac["rows"], "canal_ids": canal,
                  "interior_ids": [rr["lacuna_id"] for rr in lac["rows"] if not rr["on_border"]],
                  "edge_ids": [rr["lacuna_id"] for rr in lac["rows"] if rr["on_border"]],
                  "rejected": [None] * n_rej}
            x = left + c * (panel + gap)
            y = fig_h - top - (r + 1) * panel - r * text_h
            ax = mm_axes(fig, x, y, panel, panel, FIG_WIDTH_MM, fig_h)
            image_axes(ax, raw)
            draw_outlines(ax, id_map, lac["rows"], lw=0.6)
            draw_canal_marks(ax, dd, fs=FONT_SIZE - 2.5)
            ax.text(0.5, -0.02, contact_count_lines(dd, three=True), transform=ax.transAxes, ha="center", va="top",
                    fontsize=FONT_SIZE - 2.0, linespacing=1.15)
            if scale == 1.0:
                for sp in ax.spines.values():
                    sp.set_linewidth(2.0)
                    sp.set_edgecolor("black")
            if r == 0:
                ax.set_title(r"$t_\mathrm{hi}$" + f" \u00d7 {scale:g}" + (" (default)" if scale == 1.0 else ""), pad=2)
            if c == 0:
                ax.text(-0.06, 0.5, name, transform=ax.transAxes, rotation=90, ha="right", va="center",
                        fontsize=FONT_SIZE + 1)
            if r == 0 and c == 0:
                scale_bar(ax, id_map.shape[1])
            log[f"{name} x{scale:g}"] = {"t_hi": lac["t_hi"], "lacuna_count": lac["lacuna_count"],
                                         "interior": lac["interior_lacuna_count"],
                                         "touching_frame": len(dd["edge_ids"]), "rejected_candidates": n_rej,
                                         "canal_marked": canal}
    legend_strip(fig, margin, cap_h, FIG_WIDTH_MM - 2 * margin, legend_h, FIG_WIDTH_MM, fig_h, items)
    fig.text(margin / FIG_WIDTH_MM, 1.2 / fig_h, "Dim out-of-plane cells are not detected and are not drawn. "
             "Fixed display window for all panels. Pre-validation, pixel units.", ha="left", va="bottom",
             fontsize=FONT_SIZE - 0.5)
    write_json(fig_stem(fig_name).with_name(f"{fig_name}_counts.json"), log)
    save(fig, fig_name)
    print(fig_name, "written")


# F5 switch examples ----------------------------------------------------------------

SWITCH_CASES = [
    ("543_3", 877, 545, 60, "NARROW_CRUMB_RULE", True, "narrow crumb rule"),
    ("542_z06", 783, 581, 60, "FILL_ENCLOSED_HOLES_MAX_PX2", 200, "hole fill (up to 200 px²)"),
]


def switched_output(path: Path, switch: str, value) -> dict:
    """canaliculi.analyse_image with one switch on, the rest default, in the
    form the v2 drawing code takes; ring pixels and root dots are checked
    against that run's own numbers."""
    old = getattr(config, switch)
    setattr(config, switch, value)
    try:
        res = canaliculi.analyse_image(path)
    finally:
        setattr(config, switch, old)
    return state_data(res, lacunae.load_channel(path)[1], short(path))


def state_data(res: dict, channel: np.ndarray, name: str) -> dict:
    """One pipeline run (any setting) as the dict the v2 drawing code takes."""
    lac_rows, cell_rows = res["lacunae"]["rows"], res["rows"]
    d = {"short": name, "channel": channel, "lacuna_id_map": res["lacuna_id_map"], "skeleton": res["skeleton"],
         "lacuna_rows": lac_rows, "cell_rows": cell_rows, "flagged": res["flagged"],
         "interior_ids": [r["lacuna_id"] for r in lac_rows if not r["on_border"]],
         "edge_ids": [r["lacuna_id"] for r in lac_rows if r["on_border"]], "rejected": [], "canal_ids": []}
    d["roots_xy"] = {str(r["lacuna_id"]): root_clusters(res["graph"], r["lacuna_id"]) for r in cell_rows}
    d.update(ring_classes(d["skeleton"], d["lacuna_id_map"], d["interior_ids"]))
    for cr in cell_rows:
        i = cr["lacuna_id"]
        if int(d["ring_count"][i]) != cr["ring_length_r30_px"] or len(d["roots_xy"][str(i)]) != cr["roots_count"]:
            raise AssertionFailed(f"{name} lacuna {i}: drawn ring or roots differ from the run")
    d["segments"] = skeleton_segments(d["skeleton"], d["classes"])
    return d


def figure_switches() -> None:
    """Two rows (one per switch): raw crop | switch off | switch on, in the
    network overlay style: outline, skeleton (vermillion within 30 px of an
    interior lacuna), the lacuna's roots and its dashed 30 px ring."""
    fig_name = "S01_switch_examples"
    if done(fig_name):
        print(fig_name, "exists, skipped")
        return
    items = [{"kind": "outline", "colour": PALETTE["interior"], "label": "interior lacuna"},
             {"kind": "line", "colour": PALETTE["ring"], "lw": 1.2, "label": "skeleton within 30 px of an interior lacuna"},
             {"kind": "line", "colour": PALETTE["skeleton"], "alpha": SKELETON_ALPHA, "lw": 1.2,
              "label": "rest of the skeleton"},
             {"kind": "dot", "colour": PALETTE["root"], "label": "root of the lacuna shown"},
             {"kind": "line", "colour": "white", "lw": 0.6, "ls": (0, (3, 2)), "label": "its 30 px ring"}]
    margin, gap, text_h, top, left, cap_h = 1.0, 3.0, 9.0, 5.0, 2.0, 8.0
    panel = 45.0
    width = left + 3 * panel + 2 * gap + margin
    legend_h = legend_height(items, width - 2 * margin)
    fig_h = top + len(SWITCH_CASES) * (panel + text_h) + legend_h + cap_h
    fig = plt.figure(figsize=(width * MM, fig_h * MM))
    log = {}
    for r, (name, x, y, half, switch, value, label) in enumerate(SWITCH_CASES):
        off = image_data(name)
        on = switched_output(off["path"], switch, value)
        x0, y0, side = x - half, y - half, 2 * half
        view = (x0, x0 + side, y0, y0 + side)
        y_ax = fig_h - top - (r + 1) * panel - r * text_h
        for c, (title, data) in enumerate(((f"{name} ({x},{y}), red channel", None), (f"{label} off (default)", off),
                                            (f"{label} on", on))):
            ax = mm_axes(fig, left + c * (panel + gap), y_ax, panel, panel, width, fig_h)
            if data is None:
                show_image(ax, windowed(off["channel"])[y0:y0 + side, x0:x0 + side], x0, y0, interpolation="nearest")
                scale_bar_at(ax, 20)
            else:
                show_image(ax, overlay_image(data)[y0:y0 + side, x0:x0 + side], x0, y0, interpolation="nearest")
                draw_skeleton(ax, data["segments"], window=view, lw=0.5)
                lid = int(data["lacuna_id_map"][y, x]) or int(data["lacuna_id_map"][y0:y0 + side, x0:x0 + side].max())
                draw_lacunae(ax, data, lw=0.8, only=[lid])
                for cc in ring_contours(data, lid):
                    ax.plot(cc[:, 0], cc[:, 1], color="white", lw=0.6, ls=(0, (3, 2)), zorder=4.5)
                n_dots = draw_roots(ax, data, [lid], size=14.0, edge_lw=0.4)
                row = next(rr for rr in data["lacuna_rows"] if rr["lacuna_id"] == lid)
                cell = next(cr for cr in data["cell_rows"] if cr["lacuna_id"] == lid)
                if n_dots != cell["roots_count"] or int(data["ring_interior_count"][lid]) != cell["ring_length_r30_px"]:
                    raise AssertionFailed(f"{name} {title}: drawn values differ from the run")
                ax.set_xlim(x0 - 0.5, x0 + side - 0.5)
                ax.set_ylim(y0 + side - 0.5, y0 - 0.5)
                ax.text(0.5, -0.03, f"{row['area_px2']:.0f} px², {cell['roots_count']} roots, "
                        f"ring 30: {cell['ring_length_r30_px']} px", transform=ax.transAxes, ha="center", va="top")
                log[f"{name} {title}"] = {"area_px2": row["area_px2"], "roots": cell["roots_count"],
                                          "ring30": cell["ring_length_r30_px"]}
            ax.set_title(title, pad=2)
            if c == 0:
                panel_letter(fig, ax, "AB"[r])
    legend_strip(fig, margin, cap_h, width - 2 * margin, legend_h, width, fig_h, items)
    fig.text(margin / width, 1.2 / fig_h, "Middle and right: the image at 85% with the overlay. Each switch is off by "
             "default.\nFixed display window. Pre-validation, pixel units.", ha="left", va="bottom",
             fontsize=FONT_SIZE - 0.5)
    write_json(fig_stem(fig_name).with_name(f"{fig_name}_values.json"), log)
    save(fig, fig_name)
    print(fig_name, "written")


# F4 per-field plot -------------------------------------------------------------------

FIELD_PANELS = [
    ("roots_per_cell", "roots per cell", "roots"),
    ("roots_per_100px_perimeter", "roots per 100 px perimeter", "roots / 100 px"),
    ("ring30_per_cell", "ring length 30 px per cell", "px"),
    ("ring_density_r30", "ring density 30 px", r"px$^{-1}$"),
    ("field_density", "field length density", r"px$^{-1}$"),
]

# Overnight report 6.1: 682_z08 is alone in its field by the data-derived
# grouping (4 of its 10 lacunae matched with 682_z23, 15 times chance), so it
# is probably the same field as 682_z23 and 682_z29 at another depth. Option
# -m of the fields command merges it into their field in a second figure; the
# grouping of field-summary itself is not changed.
MERGE_IMAGE, MERGE_WITH = "682_z08", "682_z23"

# Per-image values checked against the pipeline: the summary table of
# results/ for the three columns it has, and the mean over interior lacunae
# of the cached default run for the two normalised columns.
SUMMARY_COLUMN = {"roots_per_cell": "roots per cell", "ring30_per_cell": "ring length 30 px per cell (px)",
                  "field_density": "field length density (px^-1)"}
CELL_COLUMN = {"roots_per_100px_perimeter": "roots_per_100px_perimeter", "ring_density_r30": "ring_density_r30"}


def check_field_values(rows: list, summary_rows: dict) -> None:
    """Every image value drawn must equal the pipeline number (rule 11)."""
    for r in rows:
        name = SHORT.get(r["image"], r["image"])
        for key, col in SUMMARY_COLUMN.items():
            if abs(float(r[key]) - float(summary_rows[r["image"]][col])) > 1e-9:
                raise AssertionFailed(f"{name} {key}: {r[key]} drawn, {summary_rows[r['image']][col]} in results/")
        meta = json.loads((CACHE2 / f"{name}.json").read_text(encoding="utf-8"))
        cells = [c for c in meta["cell_rows"] if not c["on_border"]]
        for key, col in CELL_COLUMN.items():
            mean = float(np.mean([c[col] for c in cells]))
            if abs(float(r[key]) - mean) > 1e-4 * max(abs(mean), 1e-12) + 1e-8:
                raise AssertionFailed(f"{name} {key}: {r[key]} drawn, {mean} from the pipeline run")


def place_labels(ys: list, min_gap: float) -> list:
    """Label heights (data units) at least min_gap apart, as close as
    possible to ys, in the same order."""
    order = np.argsort(ys)
    out = np.array(ys, dtype=float)
    placed = []
    for k in order:
        y = out[k]
        if placed and y < placed[-1] + min_gap:
            y = placed[-1] + min_gap
        out[k] = y
        placed.append(y)
    shift = (np.array(ys)[order] - out[order]).mean()
    return list(out + shift)


def figure_fields(field_dir: Path, merged: bool = False) -> None:
    """One panel per measure, y from zero: x is the field (groups derived
    from the data by field-summary), dots are images with their short name,
    a bar marks the field mean, n is the number of images. An image alone in
    its field is an open diamond. With merged, 682_z08 joins the field of
    682_z23 (Fig04_per_field_merged). No statistical test."""
    import csv

    fig_name = "Fig04_per_field" + ("_merged" if merged else "")
    if done(fig_name):
        print(fig_name, "exists, skipped")
        return
    with open(field_dir / "field_images.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    with open(config.RESULTS_DIR / "summary_table.csv", newline="") as f:
        summary_rows = {r["image"]: r for r in csv.DictReader(f)}
    with open(field_dir / "field_summary.csv", newline="") as f:
        field_means = {r["field"]: r for r in csv.DictReader(f)}
    check_field_values(rows, summary_rows)
    # field-summary names fields F1, F2, ...; figures call them Field 1, Field 2, ... so that no field name
    # looks like a figure name.
    field_of = {SHORT.get(r["image"], r["image"]): r["field"] for r in rows}
    alone = {n for n, fid in field_of.items() if list(field_of.values()).count(fid) == 1}
    if merged:
        field_of[MERGE_IMAGE] = field_of[MERGE_WITH]
    fields = sorted(set(field_of.values()), key=lambda v: int(v[1:]))
    field_name = {fid: f"Field {int(fid[1:])}" for fid in fields}
    members = {fid: [n for n, f in field_of.items() if f == fid] for fid in fields}
    values = {SHORT.get(r["image"], r["image"]): r for r in rows}

    n_cols = 3
    left, gap, right, bottom, top, row_gap = 13.0, 13.0, 2.0, 25.0, 8.0, 16.0
    w = (FIG_WIDTH_MM - left - right - (n_cols - 1) * gap) / n_cols
    h = 40.0
    n_rows = int(np.ceil(len(FIELD_PANELS) / n_cols))
    fig_h = bottom + n_rows * h + (n_rows - 1) * row_gap + top
    fig = plt.figure(figsize=(FIG_WIDTH_MM * MM, fig_h * MM))
    log = {}
    for i, (key, title, unit) in enumerate(FIELD_PANELS):
        rr, cc = divmod(i, n_cols)
        ax = mm_axes(fig, left + cc * (w + gap), bottom + (n_rows - 1 - rr) * (h + row_gap), w, h, FIG_WIDTH_MM, fig_h)
        top_val = max(float(values[n][key]) for n in values)
        ax.set_ylim(0, top_val * 1.18)
        min_gap = top_val * 1.18 * 0.075
        for j, fid in enumerate(fields):
            names = sorted(members[fid], key=lambda n: float(values[n][key]))
            vals = [float(values[n][key]) for n in names]
            offsets = np.linspace(-0.12, 0.12, len(vals)) if len(vals) > 1 else [0.0]
            mean = float(np.mean(vals))
            if not merged:
                ref = float(field_means[fid][f"{key}_mean"])
                if abs(mean - ref) > 1e-6 * max(abs(ref), 1e-12):
                    raise AssertionFailed(f"{field_name[fid]} {key}: mean {mean} drawn, {ref} in field_summary.csv")
            log[f"{field_name[fid]} {key}"] = {"images": names, "values": vals, "mean": mean}
            ax.plot([j - 0.22, j + 0.22], [mean] * 2, color=PALETTE["field_mean"], lw=1.6, zorder=2)
            label_y = place_labels(vals, min_gap)
            for x, v, ly, n in zip(np.array(offsets) + j, vals, label_y, names):
                if n in alone:
                    ax.scatter([x], [v], s=16, marker="D", facecolors="white", edgecolors="black", linewidths=0.8,
                               zorder=3)
                else:
                    ax.scatter([x], [v], s=9, c="black", zorder=3, linewidths=0)
                # Label right of the mean bar, joined to its dot by a thin leader.
                ax.plot([x, j + 0.25], [v, ly], color="0.6", lw=0.3, zorder=1)
                ax.text(j + 0.27, ly, n, fontsize=FONT_SIZE - 2.5, ha="left", va="center", color="0.25", zorder=4)
        ax.set_xticks(range(len(fields)))
        ax.set_xticklabels([f"{field_name[fid]}\nn={len(members[fid])}" for fid in fields])
        ax.set_xlim(-0.45, len(fields) - 0.2)
        ax.set_title(title, pad=3)
        ax.set_ylabel(unit, labelpad=1)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(length=2, pad=1)
        if key in ("field_density", "ring_density_r30"):
            ax.ticklabel_format(axis="y", style="plain")
            ax.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%.3f"))
        panel_letter(fig, ax, "ABCDE"[i], dx=-0.06)
    legend_strip(fig, 2.0, 11.5, FIG_WIDTH_MM - 4.0, 4.5, FIG_WIDTH_MM, fig_h, dark=False, items=[
        {"kind": "marker", "label": "image (mean over its interior lacunae)"},
        {"kind": "marker", "marker": "D", "face": "white", "s": 14,
         "label": "682_z08, alone in its field by field-summary" + (", merged here by hand" if merged else "")},
        {"kind": "bar", "colour": PALETTE["field_mean"], "label": "field mean"}])
    groups = "; ".join(f"{field_name[fid]}: {' + '.join(members[fid])}" for fid in fields)
    if merged:
        note = (f"{MERGE_IMAGE} (open diamond) is merged by hand into the field of 682_z23 and 682_z29 (option -m); "
                "field-summary keeps it alone, and the merged means are computed here, not by field-summary.")
    else:
        note = (f"{MERGE_IMAGE} (open diamond) is alone in its field by the data-derived grouping, probably the same "
                "field as 682_z23 and 682_z29 at another depth.")
    fig.text(0.01, 0.01, "Fields from field-summary (lacuna centroids matched across images). " + groups + ". " + note
             + " n: images per field. All y axes start at zero. Pre-validation, pixel units, no test.",
             ha="left", va="bottom", fontsize=FONT_SIZE - 1, wrap=True)
    write_json(fig_stem(fig_name).with_name(f"{fig_name}_values.json"), log)
    save(fig, fig_name)
    print(fig_name, "written")


THUMBS = OUT / "_thumbs"
THUMB_WIDTH_PX = 600
IMAGE_ORDER = ["543-2", "543_3", "543_z13", "542_z06", "542_z18", "682_z08", "682_z23", "682_z29"]

# (file stem relative to figures_out/, what it shows, display window)
INDEX_MAIN = [
    ("main/Fig01_contact_sheet", "All 8 sections with the kept lacunae (cyan interior, yellow frame edge), canal marks "
     "\"c\" and the count lines.", "fixed"),
    ("main/Fig02_network_overlay_543-2", "Network overlay of 543-2: raw; overlay with vermillion ring 30 px skeleton, "
     "white rest, magenta roots; three lacunae at 3x. A copy of per_image/543-2/network.", "fixed"),
    ("main/Fig03_threshold_sensitivity", "Kept lacunae and count lines at 0.8 to 1.2 times the lacuna cut t_hi, three "
     "sections; the default is framed.", "fixed"),
    ("main/Fig04_per_field", "Roots, roots per 100 px perimeter, ring 30 px, ring density 30 px and field density by "
     "field; y from zero; 682_z08 open diamond.", "none (no image)"),
    ("main/Fig04_per_field_merged", "The same with 682_z08 merged by hand into Field 4 (option -m).", "none (no image)"),
]
INDEX_SUPPLEMENT = [
    ("supplement/S01_switch_examples", "The narrow crumb rule (543_3) and the hole fill (542_z06), off and on, in the "
     "network overlay style.", "fixed"),
    ("supplement/S02_contact_sheet_with_rejected_candidates", "The contact sheet with the rejected lacuna-scale "
     "candidates (grey dashed; A aspect, S solidity, a area).", "fixed"),
    ("supplement/S03_contact_sheet_coded", "The contact sheet labelled with blinding codes (a blinding test).", "fixed"),
]


def thumb_name(rel_stem: str) -> str:
    """_thumbs/ name: the figure id, or the kind followed by the image."""
    parts = rel_stem.split("/")
    if parts[0] == "per_image":
        return f"{parts[-1]}_{parts[1]}.png"
    return f"{parts[-1]}.png"


def make_thumb(rel_stem: str) -> str:
    """A 600 px wide PNG of figures_out/<rel_stem>.png in _thumbs/, redrawn
    only when the figure is newer. Returns written, skipped or missing."""
    from PIL import Image

    src = OUT / f"{rel_stem}.png"
    dst = THUMBS / thumb_name(rel_stem)
    if not src.is_file():
        return "missing"
    if dst.is_file() and dst.stat().st_mtime >= src.stat().st_mtime:
        return "skipped"
    THUMBS.mkdir(parents=True, exist_ok=True)
    im = Image.open(src).convert("RGB")
    w, h = im.size
    im = im.resize((THUMB_WIDTH_PX, max(1, round(h * THUMB_WIDTH_PX / w))), Image.LANCZOS)
    tmp = dst.with_name(dst.name + ".tmp")
    # Full colour: a 256-colour palette turned the frame-edge yellow orange.
    im.save(tmp, format="PNG", optimize=True)
    os.replace(tmp, dst)
    return "written"


def index_text() -> str:
    def row(rel, what, window):
        name = rel.split("/")[-1]
        fid = name.split("_")[0] + (" merged" if name.endswith("_merged") else "")
        return (f"| {fid} | {what} | {window} | [png]({rel}.png), [pdf]({rel}.pdf) | "
                f"[![{name}](_thumbs/{thumb_name(rel)})]({rel}.png) |")

    lines = ["# Index of figures_out", "",
             "Pre-validation, pixel units. Every figure shows the default pipeline output (every switch off) unless "
             "its row says otherwise. Open first: **Fig02** (the network overlay of 543-2), then the network "
             "figure of any other image below, then Fig01 and Fig04. Captions: `figures/captions.md`. Review notes: "
             "`figures/REVIEW_V2.md`. How to regenerate: `README.md`.", "",
             "Display window: \"fixed\" is one window for the whole dataset (`display_window.json`), so brightness "
             "can be compared between images; the per-image variants in `per_image/<image>/display_variants/` use "
             "each image's own window instead.", "",
             "## Main figures", "", "| figure | what it shows | window | file | thumbnail |", "|---|---|---|---|---|"]
    lines += [row(*r) for r in INDEX_MAIN]
    lines += ["", "## Supplementary figures", "", "| figure | what it shows | window | file | thumbnail |",
              "|---|---|---|---|---|"]
    lines += [row(*r) for r in INDEX_SUPPLEMENT]
    lines += ["", "## Per image", "",
              "`overview`: raw; kept lacunae with numbers, canal marks and rejected candidates; the network overlay "
              "at small size; one inset lacuna at 3x. `network`: raw and the network overlay at full size with three "
              "lacunae at 3x. `gallery`: every interior lacuna at 3x. All three use the fixed window; "
              "`display_variants/` holds the same three with the image's own window (PNG). `inset.json` logs the "
              "inset choices; `network_check.json` and `gallery_check.json` list the drawn numbers against the "
              "pipeline numbers.", "",
              "| image | overview | network | gallery |", "|---|---|---|---|"]
    for n in IMAGE_ORDER:
        cells = []
        for kind in ("overview", "network", "gallery"):
            rel = f"per_image/{n}/{kind}"
            cells.append(f"[![{kind} {n}](_thumbs/{thumb_name(rel)})]({rel}.png) [pdf]({rel}.pdf)")
        lines.append(f"| {n} | " + " | ".join(cells) + " |")
    lines += ["", "Also: `per_image/543_3/overview_low_cut_layer` (option `-r`: objects kept only at 0.8 times "
              "t_hi, dotted light blue; not the default output).", "",
              "## Hand-count tiles", "",
              "`validation_tiles/`: 86 raw red tiles, one per interior lacuna, under random codes, for counting roots "
              "by hand without seeing the pipeline result. See `validation_tiles/README.md`. The key is outside the "
              "repository.", ""]
    return "\n".join(lines)


def make_thumbs_and_index() -> dict:
    """_thumbs/ and INDEX.md. Returns {path: written | skipped | missing}."""
    report = {}
    rels = [r[0] for r in INDEX_MAIN + INDEX_SUPPLEMENT]
    rels += [f"per_image/{n}/{k}" for n in IMAGE_ORDER for k in ("overview", "network", "gallery")]
    for rel in rels:
        report[f"_thumbs/{thumb_name(rel)}"] = make_thumb(rel)
    text = index_text()
    path = OUT / "INDEX.md"
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        report["INDEX.md"] = "skipped"
    else:
        tmp = path.with_name(path.name + ".tmp")
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
        report["INDEX.md"] = "written"
    for k, v in report.items():
        if v != "skipped":
            print(k, v)
    return report


DEFAULT_FIELD_DIR = ROOT / "results_experiments" / "fixes" / "B3_field_summary"


def figure_all(tiles_key: Path | None = None, blind_key: Path | None = None,
               field_dir: Path = DEFAULT_FIELD_DIR) -> int:
    """O4: regenerate the whole figures_out/ tree in its folders. Every step
    skips outputs that exist; delete a file to redraw it. Prints one row per
    output: written, skipped, failed or missing. Returns 1 if any step failed."""
    def pair(stem):
        return [stem.with_name(stem.name + ".png"), stem.with_name(stem.name + ".pdf")]

    names = [short(p) for p in image_paths()]
    steps = [("display window", display_window, (), [OUT / "display_window.json"])]
    for n in names:
        steps.append((f"overview {n}", figure_image, (n,), pair(PER_IMAGE / n / "overview")))
    steps.append(("overview 543_3 -r", figure_image, ("543_3", None, True),
                  pair(PER_IMAGE / "543_3" / "overview_low_cut_layer")))
    for n in names:
        steps.append((f"network {n}", figure_network, (n,), pair(PER_IMAGE / n / "network")))
    steps.append(("Fig02 copy", copy_fig02, (), pair(fig_stem("Fig02").with_name(f"Fig02_network_overlay_{FIG02_IMAGE}"))))
    for n in names:
        steps.append((f"gallery {n}", figure_gallery, (n,), pair(PER_IMAGE / n / "gallery")))
    for n in names:
        folder = PER_IMAGE / n / "display_variants"
        steps.append((f"variants {n}", figure_display_variants, (n,),
                      [folder / f"{k}_image_window.png" for k in ("overview", "network", "gallery")]))
    steps += [("Fig01", figure_contact, (None, False), pair(fig_stem("Fig01_contact_sheet"))),
              ("Fig03", figure_thresholds, (), pair(fig_stem("Fig03_threshold_sensitivity"))),
              ("Fig04", figure_fields, (field_dir, False), pair(fig_stem("Fig04_per_field"))),
              ("Fig04 merged", figure_fields, (field_dir, True), pair(fig_stem("Fig04_per_field_merged"))),
              ("S01", figure_switches, (), pair(fig_stem("S01_switch_examples"))),
              ("S02", figure_contact, (None, True), pair(fig_stem("S02_contact_sheet_with_rejected_candidates")))]
    s03 = pair(fig_stem("S03_contact_sheet_coded"))
    if blind_key is not None:
        steps.append(("S03", figure_contact, (blind_key, False), s03))
    tiles = sorted(TILES_DIR.glob("T*.png")) + [TILES_DIR / "annotation_template.csv", TILES_DIR / "README.md"]
    if tiles_key is not None:
        steps.append(("validation tiles", make_validation_tiles, (tiles_key,), tiles))

    def stamp(paths):
        return {p: p.stat().st_mtime_ns if p.is_file() else None for p in paths}

    rows, failed = [], 0
    for label, func, args, paths in steps:
        before = stamp(paths)
        code = run("O4", func, *args)
        after = stamp(paths)
        for p in paths:
            if code:
                status = "failed"
            elif after[p] is None:
                status = "missing"
            else:
                status = "written" if before[p] != after[p] else "skipped"
            rows.append((label, p, status))
        failed += bool(code)
    if blind_key is None:
        rows += [("S03", p, "kept (needs -b KEY)" if p.is_file() else "missing (needs -b KEY)") for p in s03]
    if tiles_key is None:
        rows += [("validation tiles", TILES_DIR, f"kept, {len(list(TILES_DIR.glob('T*.png')))} tiles "
                  "(needs -k KEY to redraw)")]
    thumbs_before = stamp(sorted(THUMBS.glob("*.png")) + [OUT / "INDEX.md"])
    report = make_thumbs_and_index()
    for path_str, status in report.items():
        rows.append(("thumbs and INDEX", OUT / path_str, status))
    del thumbs_before

    width = max(len(r[0]) for r in rows)
    print(f"\n{'step':<{width}}  {'status':<10}  file")
    for label, p, status in rows:
        rel = p.relative_to(ROOT).as_posix() if p.is_absolute() else str(p)
        print(f"{label:<{width}}  {status:<10}  {rel}")
    counts = {}
    for _l, _p, st in rows:
        key = st.split(" ")[0].rstrip(",")
        counts[key] = counts.get(key, 0) + 1
    print("\nsummary: " + ", ".join(f"{v} {k}" for k, v in sorted(counts.items())))
    return 1 if failed else 0


# Command line ----------------------------------------------------------------------------

def run(item: str, func, *args) -> int:
    try:
        func(*args)
        return 0
    except Exception:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        (LOG_DIR / f"{item}.txt").write_text(traceback.format_exc(), encoding="utf-8")
        traceback.print_exc()
        return 1


def main() -> int:
    set_style()
    p = argparse.ArgumentParser(description="Publication figures (pre-validation, px).")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("window", help="Compute the fixed display window.")
    q = sub.add_parser("image", help="Per-image overview figure.")
    g = q.add_mutually_exclusive_group(required=True)
    g.add_argument("-i", dest="image", help="Image short name, for example 543-2.")
    g.add_argument("-a", dest="all", action="store_true", help="All images.")
    q.add_argument("-c", dest="cell", type=int, default=None, help="Lacuna id for the inset (default: the rule).")
    q.add_argument("-r", dest="low_cut", action="store_true",
                   help="Also draw objects kept only at 0.8 t_hi (dotted), into a separate file. Off by default.")
    q = sub.add_parser("contact", help="Contact sheet of all images (Fig01; S02 with -r; S03 with -b).")
    q.add_argument("-r", dest="rejected", action="store_true", help="Also draw the rejected candidates.")
    q.add_argument("-b", dest="blind", action="store_true", help="Label with blinding codes instead of names.")
    q.add_argument("-k", dest="key", type=Path, default=None, help="Blinding key (needed with -b).")
    sub.add_parser("thresholds", help="Lacuna cut sensitivity figure (Fig03).")
    q = sub.add_parser("fields", help="Per-field plot (Fig04).")
    q.add_argument("-f", dest="field_dir", type=Path, required=True, help="Output folder of field-summary.")
    q.add_argument("-m", dest="merged", action="store_true",
                   help="Merge 682_z08 into the field of 682_z23 and 682_z29 (Fig04_per_field_merged).")
    sub.add_parser("switches", help="Crumb rule and hole fill, off and on (S01).")
    sub.add_parser("check", help="v2 drawing data against results/ for every image (ring px, roots, skeleton).")
    q = sub.add_parser("network", help="Network overlay per image (v2): raw, overlay, three insets.")
    g = q.add_mutually_exclusive_group(required=True)
    g.add_argument("-i", dest="image", help="Image short name, for example 543-2.")
    g.add_argument("-a", dest="all", action="store_true", help="All images.")
    q.add_argument("-c", dest="cells", default=None, help="Three lacuna ids for the insets, as ID1,ID2,ID3.")
    q = sub.add_parser("gallery", help="Cell gallery per image (v2): one 3x tile per interior lacuna.")
    g = q.add_mutually_exclusive_group(required=True)
    g.add_argument("-i", dest="image", help="Image short name, for example 543-2.")
    g.add_argument("-a", dest="all", action="store_true", help="All images.")
    q = sub.add_parser("variants", help="Per-image figures with the image's own display window (PNG).")
    g = q.add_mutually_exclusive_group(required=True)
    g.add_argument("-i", dest="image", help="Image short name, for example 543-2.")
    g.add_argument("-a", dest="all", action="store_true", help="All images.")
    sub.add_parser("thumbs", help="Thumbnails in _thumbs/ and figures_out/INDEX.md.")
    q = sub.add_parser("all", help="Regenerate the whole figures_out/ tree; prints what was written or skipped.")
    q.add_argument("-k", dest="tiles_key", type=Path, default=None,
                   help="Key of the hand-count tiles (outside the repository); without it the tiles are kept.")
    q.add_argument("-b", dest="blind_key", type=Path, default=None,
                   help="Blinding key for S03 (outside the repository); without it S03 is kept.")
    q.add_argument("-f", dest="field_dir", type=Path, default=DEFAULT_FIELD_DIR,
                   help="Output folder of field-summary (default: results_experiments/fixes/B3_field_summary).")
    q = sub.add_parser("tiles", help="Hand-count tiles (raw red, random codes); key outside the repository.")
    q.add_argument("-k", dest="key", type=Path, required=True, help="Key path, outside the repository.")
    args = p.parse_args()
    if args.cmd == "check":
        return run("N0", _selftest_n0)
    if args.cmd == "all":
        return figure_all(args.tiles_key, args.blind_key, args.field_dir)
    if args.cmd == "thumbs":
        return run("O1", make_thumbs_and_index)
    if args.cmd == "tiles":
        return run("N3", make_validation_tiles, args.key)
    if args.cmd == "variants":
        names = [short(x) for x in image_paths()] if args.all else [args.image]
        return max(run("P8", figure_display_variants, n) for n in names)
    if args.cmd == "gallery":
        names = [short(x) for x in image_paths()] if args.all else [args.image]
        return max(run("N2", figure_gallery, n) for n in names)
    if args.cmd == "network":
        names = [short(x) for x in image_paths()] if args.all else [args.image]
        cells = [int(v) for v in args.cells.split(",")] if args.cells else None
        code = max(run("N1", figure_network, n, cells) for n in names)
        if FIG02_IMAGE in names and cells is None:
            code = max(code, run("N1", copy_fig02))
        return code
    if args.cmd == "window":
        return run("F0", lambda: print(display_window()))
    if args.cmd == "image":
        names = [short(x) for x in image_paths()] if args.all else [args.image]
        return max(run("F1", figure_image, n, args.cell, args.low_cut) for n in names)
    if args.cmd == "contact":
        if args.blind and not args.key:
            print("-b needs the blinding key: -k KEY")
            return 2
        return run("F2", figure_contact, args.key if args.blind else None, args.rejected)
    if args.cmd == "thresholds":
        return run("F3", figure_thresholds)
    if args.cmd == "fields":
        return run("P4", figure_fields, args.field_dir, args.merged)
    if args.cmd == "switches":
        return run("F5", figure_switches)
    return 1


if __name__ == "__main__":
    sys.exit(main())
