"""Publication figures for the LCN pipeline.

PRE-VALIDATION, PIXEL units. Every figure shows the default pipeline output as
it is (src/ with every switch off), unless its caption says otherwise. Nothing
here writes into results/. Outputs go to figures_out/ as PNG (300 dpi) and PDF
(fonts embedded). Coordinates are (x, y) = (column, row).

Usage (from the repo root):
    python -u figures/make_figures.py window              # the fixed display window
    python -u figures/make_figures.py image -i 543-2      # per-image figure (F1)
    python -u figures/make_figures.py image -i 543-2 -c 6 # the same, inset on lacuna 6
    python -u figures/make_figures.py image -a            # per-image figures, all 8 images
    python -u figures/make_figures.py contact             # contact sheet of all images (F2)
    python -u figures/make_figures.py contact -b -k KEY   # the same, labelled with blinding codes
    python -u figures/make_figures.py thresholds          # lacuna cut sensitivity figure (F3)
    python -u figures/make_figures.py fields -f FIELD_DIR # per-field plot from field-summary (F4)
    python -u figures/make_figures.py switches            # crumb rule and hole fill, off and on (F5)

Each output is skipped if its PNG and PDF exist; delete them to redraw.

Shared style (one place, used by every figure):
    display window   fixed for the whole dataset: the 1st and 99.8th percentile
                     of the pooled red channel of all images, the same for every
                     image and panel (figures_out/display_window.json)
    fonts            Arial (Helvetica if present, else DejaVu Sans), 7 to 9 pt
                     at 180 mm figure width; PDF fonts embedded (TrueType)
    colours          interior lacuna outlines cyan; frame-edge lacunae yellow
                     (they are left out of every per-cell mean); skeleton one
                     colour (white) over the raw image dimmed to 60%; roots as
                     yellow dots
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
INTERIOR_COLOUR = "#00FFFF"  # cyan
BORDER_COLOUR = "#FFE000"  # yellow
ROOT_COLOUR = "#FFE000"
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


def save(fig, name: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        final = OUT / f"{name}.{ext}"
        tmp = OUT / f"{name}.tmp.{ext}"
        fig.savefig(tmp, dpi=300)
        os.replace(tmp, final)
    plt.close(fig)


def done(name: str) -> bool:
    return (OUT / f"{name}.png").is_file() and (OUT / f"{name}.pdf").is_file()


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


def legend_strip(fig, x_mm: float, y_mm: float, w_mm: float, h_mm: float, fig_w: float, fig_h: float,
                 items: list, fs: float = FONT_SIZE - 1) -> None:
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
        ax.add_patch(Rectangle((x, y - sh / 2), sw, sh, facecolor="black", edgecolor="none"))
        cx = x + sw / 2
        k = it["kind"]
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
        ax.text(x + sw + pad, y, it["label"], fontsize=fs, va="center", ha="left")
        x += sw + pad + tw + gap


def save_to(fig, stem: Path) -> None:
    """Write stem.png (300 dpi) and stem.pdf atomically."""
    stem.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        final = stem.with_name(f"{stem.name}.{ext}")
        tmp = stem.with_name(f"{stem.name}.tmp.{ext}")
        fig.savefig(tmp, dpi=300)
        os.replace(tmp, final)
    plt.close(fig)


def done_at(stem: Path) -> bool:
    return stem.with_name(stem.name + ".png").is_file() and stem.with_name(stem.name + ".pdf").is_file()


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


def figure_image(name: str, cell: int | None = None) -> None:
    fig_name = f"F1_{name}"
    if done(fig_name):
        print(fig_name, "exists, skipped")
        return
    path = path_of(name)
    out = pipeline_output(path)
    if cell is None:
        cell, why = choose_inset_cell(out)
    else:
        why = f"set with -c {cell}"
    row = next(r for r in out["lacuna_rows"] if r["lacuna_id"] == cell)
    write_json(OUT / f"{fig_name}_inset.json", {"image": name, "inset_lacuna": cell, "rule": why})
    print(f"{fig_name}: inset lacuna {cell} ({why})")

    # Inset crop: a square around the lacuna's bounding box plus a margin.
    ys, xs = np.nonzero(out["lacuna_id_map"] == cell)
    side = int(max(ys.max() - ys.min(), xs.max() - xs.min()) + 1 + 2 * INSET_MARGIN_PX)
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    H, W = out["lacuna_id_map"].shape
    x0 = int(np.clip(round(cx - side / 2), 0, W - side))
    y0 = int(np.clip(round(cy - side / 2), 0, H - side))

    # Layout in mm: three square panels and an inset column at 3x the
    # panel scale, filling 180 mm.
    margin, gap = 1.0, 2.5
    panel = (FIG_WIDTH_MM - 2 * margin - 3 * gap) / (3 + INSET_ZOOM * side / W)
    inset = INSET_ZOOM * side / W * panel
    top, bottom = 5.0, 7.0
    fig_h = bottom + panel + top
    fig = plt.figure(figsize=(FIG_WIDTH_MM * MM, fig_h * MM))
    axA = mm_axes(fig, margin, bottom, panel, panel, FIG_WIDTH_MM, fig_h)
    axB = mm_axes(fig, margin + panel + gap, bottom, panel, panel, FIG_WIDTH_MM, fig_h)
    axC = mm_axes(fig, margin + 2 * (panel + gap), bottom, panel, panel, FIG_WIDTH_MM, fig_h)
    axI = mm_axes(fig, margin + 3 * (panel + gap), bottom + panel - inset, inset, inset, FIG_WIDTH_MM, fig_h)

    raw = windowed(out["channel"])
    image_axes(axA, raw)
    axA.set_title(f"{name}, red channel", pad=2)
    scale_bar(axA, W)

    image_axes(axB, raw)
    draw_outlines(axB, out["lacuna_id_map"], out["lacuna_rows"], numbers=True)
    axB.set_title("lacunae", pad=2)
    axB.text(0.5, -0.03, f"n = {out['lacuna_count']} lacunae ({out['interior_count']} interior)",
             transform=axB.transAxes, ha="center", va="top")

    sk = skeleton_rgb(out["channel"], out["skeleton"])
    image_axes(axC, sk)
    axC.set_title("skeleton (white) on the image at 60%", pad=2)
    axC.add_patch(Rectangle((x0 - 0.5, y0 - 0.5), side, side, fill=False, ec=ROOT_COLOUR, lw=0.8))

    crop = sk[y0:y0 + side, x0:x0 + side]
    axI.imshow(crop, interpolation="nearest")
    axI.set_xticks([])
    axI.set_yticks([])
    for sp in axI.spines.values():
        sp.set_edgecolor(ROOT_COLOUR)
        sp.set_linewidth(0.8)
    draw_outlines(axI, out["lacuna_id_map"][y0:y0 + side, x0:x0 + side],
                  [r for r in out["lacuna_rows"] if r["lacuna_id"] == cell], offset=(0, 0))
    pts = np.array(out["roots_xy"][str(cell)])
    if len(pts):
        axI.scatter(pts[:, 0] - x0, pts[:, 1] - y0, s=6, c=ROOT_COLOUR, edgecolors="black", linewidths=0.3, zorder=5)
    axI.set_xlim(-0.5, side - 0.5)
    axI.set_ylim(side - 0.5, -0.5)
    axI.set_title(f"lacuna {cell}, 3x", pad=2)
    roots_n = next(c["roots_count"] for c in out["cell_rows"] if c["lacuna_id"] == cell)
    axI.text(0.0, -0.04, f"{roots_n} roots (dots)", transform=axI.transAxes, ha="left", va="top")

    for ax, letter in ((axA, "A"), (axB, "B"), (axC, "C")):
        panel_letter(fig, ax, letter)
    fig.text(0.995, 0.005, "pre-validation, pixel units", ha="right", va="bottom", fontsize=FONT_SIZE - 1, color="0.35")
    save(fig, fig_name)
    print(fig_name, "written")


# F2 contact sheet ----------------------------------------------------------------

def figure_contact(key_path: Path | None = None) -> None:
    """All images, 2 rows by 4 columns, raw with thin outlines and the count
    under each, one display window. With a blinding key, panels are labelled
    with the codes and ordered by code."""
    import csv

    fig_name = "F2_contact_sheet" + ("_coded" if key_path else "")
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
    margin, gap, text_h, top, foot = 1.0, 2.0, 7.0, 2.0, 3.0
    panel = (FIG_WIDTH_MM - 2 * margin - (n_cols - 1) * gap) / n_cols
    fig_h = top + n_rows * (panel + text_h) + foot
    fig = plt.figure(figsize=(FIG_WIDTH_MM * MM, fig_h * MM))
    for i, p in enumerate(paths):
        r, c = divmod(i, n_cols)
        out = pipeline_output(p)
        x = margin + c * (panel + gap)
        y = fig_h - top - (r + 1) * panel - r * text_h
        ax = mm_axes(fig, x, y, panel, panel, FIG_WIDTH_MM, fig_h)
        image_axes(ax, windowed(out["channel"]))
        draw_outlines(ax, out["lacuna_id_map"], out["lacuna_rows"], lw=0.6)
        ax.text(0.5, -0.025, f"{labels[p]}: n = {out['lacuna_count']} ({out['interior_count']} interior)",
                transform=ax.transAxes, ha="center", va="top")
        if i == 0:
            scale_bar(ax, out["lacuna_id_map"].shape[1])
    fig.text(0.995, 0.003, "pre-validation, pixel units", ha="right", va="bottom", fontsize=FONT_SIZE - 1, color="0.35")
    save(fig, fig_name)
    print(fig_name, "written")


# F3 lacuna cut sensitivity --------------------------------------------------------

THRESHOLD_IMAGES = ["542_z06", "543-2", "682_z29"]
THRESHOLD_SCALES = [0.8, 0.9, 1.0, 1.1, 1.2]


def figure_thresholds() -> None:
    """Rows: three images. Columns: the lacuna cut t_hi at 0.8 to 1.2 times
    the image's own cut (1.0, the default, boxed). Outlines and counts. The
    defaults are not changed; the scaled cut is passed to the lacuna stage."""
    fig_name = "F3_threshold_sensitivity"
    if done(fig_name):
        print(fig_name, "exists, skipped")
        return
    margin, gap, text_h, top, left, foot = 1.0, 1.5, 5.5, 5.0, 6.0, 3.0
    n_cols = len(THRESHOLD_SCALES)
    panel = (FIG_WIDTH_MM - left - margin - (n_cols - 1) * gap) / n_cols
    fig_h = top + len(THRESHOLD_IMAGES) * (panel + text_h) + foot
    fig = plt.figure(figsize=(FIG_WIDTH_MM * MM, fig_h * MM))
    log = {}
    for r, name in enumerate(THRESHOLD_IMAGES):
        path = path_of(name)
        _display, channel = lacunae.load_channel(path)
        _mask, t_hi = lacunae.multiotsu_lacuna_mask(channel)
        raw = windowed(channel)
        for c, scale in enumerate(THRESHOLD_SCALES):
            lac = lacunae.analyse_image(path, t_hi * scale) if scale != 1.0 else lacunae.analyse_image(path)
            id_map = np.zeros(lac["labels"].shape, dtype=np.int32)
            for lid, (region, _b) in enumerate(lac["kept"], start=1):
                id_map[lac["labels"] == region.label] = lid
            x = left + c * (panel + gap)
            y = fig_h - top - (r + 1) * panel - r * text_h
            ax = mm_axes(fig, x, y, panel, panel, FIG_WIDTH_MM, fig_h)
            image_axes(ax, raw)
            draw_outlines(ax, id_map, lac["rows"], lw=0.6)
            ax.text(0.5, -0.03, f"n = {lac['lacuna_count']} ({lac['interior_lacuna_count']} interior)",
                    transform=ax.transAxes, ha="center", va="top")
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
                                         "interior": lac["interior_lacuna_count"]}
    fig.text(0.995, 0.003, "pre-validation, pixel units", ha="right", va="bottom", fontsize=FONT_SIZE - 1, color="0.35")
    write_json(OUT / f"{fig_name}_counts.json", log)
    save(fig, fig_name)
    print(fig_name, "written")


# F5 switch examples ----------------------------------------------------------------

SWITCH_CASES = [
    ("543_3", 877, 545, 60, "NARROW_CRUMB_RULE", True, "narrow crumb rule"),
    ("542_z06", 783, 581, 60, "FILL_ENCLOSED_HOLES_MAX_PX2", 200, "hole fill (up to 200 px²)"),
]


def switched_output(path: Path, switch: str, value) -> dict:
    """canaliculi.analyse_image with one switch on, the rest default."""
    old = getattr(config, switch)
    setattr(config, switch, value)
    try:
        res = canaliculi.analyse_image(path)
    finally:
        setattr(config, switch, old)
    return {"lacuna_id_map": res["lacuna_id_map"], "skeleton": res["skeleton"], "lacuna_rows": res["lacunae"]["rows"],
            "cell_rows": res["rows"]}


def figure_switches() -> None:
    """Two rows (one per switch): raw crop | switch off | switch on, outlines
    and the white skeleton over the image at 60%."""
    fig_name = "F5_switch_examples"
    if done(fig_name):
        print(fig_name, "exists, skipped")
        return
    margin, gap, text_h, top, left = 1.0, 3.0, 9.0, 5.0, 2.0
    panel = 45.0
    width = left + 3 * panel + 2 * gap + margin
    fig_h = top + len(SWITCH_CASES) * (panel + text_h)
    fig = plt.figure(figsize=(width * MM, fig_h * MM))
    log = {}
    for r, (name, x, y, half, switch, value, label) in enumerate(SWITCH_CASES):
        path = path_of(name)
        off = pipeline_output(path)
        on = switched_output(path, switch, value)
        sl = (slice(y - half, y + half), slice(x - half, x + half))
        raw = windowed(off["channel"])[sl]
        y_ax = fig_h - top - (r + 1) * panel - r * text_h
        for c, (title, data) in enumerate(((f"{name} ({x},{y}), red channel", None), (f"{label} off (default)", off),
                                            (f"{label} on", on))):
            ax = mm_axes(fig, left + c * (panel + gap), y_ax, panel, panel, width, fig_h)
            if data is None:
                image_axes(ax, raw)
                scale_bar(ax, 2 * half, length_px=20)
            else:
                image_axes(ax, skeleton_rgb(off["channel"], data["skeleton"])[sl])
                lid = int(data["lacuna_id_map"][y, x]) or int(data["lacuna_id_map"][sl].max())
                rows = [rr for rr in data["lacuna_rows"] if rr["lacuna_id"] == lid]
                draw_outlines(ax, data["lacuna_id_map"][sl], rows, lw=0.8)
                cell = next(cr for cr in data["cell_rows"] if cr["lacuna_id"] == lid)
                ax.text(0.5, -0.03, f"{rows[0]['area_px2']:.0f} px\u00b2, {cell['roots_count']} roots, "
                        f"ring 30: {cell['ring_length_r30_px']} px", transform=ax.transAxes, ha="center", va="top")
                log[f"{name} {title}"] = {"area_px2": rows[0]["area_px2"], "roots": cell["roots_count"],
                                          "ring30": cell["ring_length_r30_px"]}
            ax.set_title(title, pad=2)
            if c == 0:
                panel_letter(fig, ax, "AB"[r])
    fig.text(0.995, 0.003, "pre-validation, pixel units", ha="right", va="bottom", fontsize=FONT_SIZE - 1, color="0.35")
    write_json(OUT / f"{fig_name}_values.json", log)
    save(fig, fig_name)
    print(fig_name, "written")


# F4 per-field plot -------------------------------------------------------------------

FIELD_PANELS = [
    ("roots_per_cell", "roots per cell", "roots"),
    ("roots_per_100px_perimeter", "roots per 100 px\nperimeter", "roots / 100 px"),
    ("ring30_per_cell", "ring length 30 px\nper cell", "px"),
    ("ring_density_r30", "ring density 30 px", r"px$^{-1}$"),
    ("field_density", "field length density", r"px$^{-1}$"),
]


def figure_fields(field_dir: Path) -> None:
    """One small panel per measure: x is the field (groups derived from the
    data by field-summary), dots are images, a bar marks the field mean, and
    the number of images per field is printed. No statistical test."""
    import csv

    fig_name = "F4_per_field"
    if done(fig_name):
        print(fig_name, "exists, skipped")
        return
    with open(field_dir / "field_images.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    fields = sorted({r["field"] for r in rows}, key=lambda v: int(v[1:]))
    members = {fid: [SHORT.get(r["image"], r["image"]) for r in rows if r["field"] == fid] for fid in fields}
    n_pan = len(FIELD_PANELS)
    left, gap, right, bottom, top = 12.0, 11.0, 2.0, 12.0, 9.0
    w = (FIG_WIDTH_MM - left - right - (n_pan - 1) * gap) / n_pan
    h = 38.0
    fig_h = bottom + h + top
    fig = plt.figure(figsize=(FIG_WIDTH_MM * MM, fig_h * MM))
    for i, (key, title, unit) in enumerate(FIELD_PANELS):
        ax = mm_axes(fig, left + i * (w + gap), bottom, w, h, FIG_WIDTH_MM, fig_h)
        for j, fid in enumerate(fields):
            vals = [float(r[key]) for r in rows if r["field"] == fid and r[key] not in ("", "None")]
            if not vals:
                continue
            offsets = np.linspace(-0.12, 0.12, len(vals)) if len(vals) > 1 else [0.0]
            ax.scatter(np.array(offsets) + j, vals, s=9, c="black", zorder=3, linewidths=0)
            ax.plot([j - 0.28, j + 0.28], [np.mean(vals)] * 2, color="#0072B2", lw=1.6, zorder=2)
        ax.set_xticks(range(len(fields)))
        ax.set_xticklabels([f"{fid}\nn={len(members[fid])}" for fid in fields])
        ax.set_xlim(-0.6, len(fields) - 0.4)
        ax.set_title(title, pad=3)
        ax.set_ylabel(unit, labelpad=1)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(length=2, pad=1)
        if key in ("field_density", "ring_density_r30"):
            ax.ticklabel_format(axis="y", style="plain")
            ax.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%.3f"))
        panel_letter(fig, ax, "ABCDE"[i], dx=-0.05)
    legend = "; ".join(f"{fid}: {' + '.join(members[fid])}" for fid in fields)
    fig.text(0.01, 0.01, "Fields from field-summary (lacuna centroids matched across images). " + legend
             + ". Dots: images; bar: field mean; n: images per field. Pre-validation, pixel units, no test.",
             ha="left", va="bottom", fontsize=FONT_SIZE - 1, wrap=True)
    save(fig, fig_name)
    print(fig_name, "written")


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
    q = sub.add_parser("image", help="Per-image figure (F1).")
    g = q.add_mutually_exclusive_group(required=True)
    g.add_argument("-i", dest="image", help="Image short name, for example 543-2.")
    g.add_argument("-a", dest="all", action="store_true", help="All images.")
    q.add_argument("-c", dest="cell", type=int, default=None, help="Lacuna id for the inset (default: the rule).")
    q = sub.add_parser("contact", help="Contact sheet of all images (F2).")
    q.add_argument("-b", dest="blind", action="store_true", help="Label with blinding codes instead of names.")
    q.add_argument("-k", dest="key", type=Path, default=None, help="Blinding key (needed with -b).")
    sub.add_parser("thresholds", help="Lacuna cut sensitivity figure (F3).")
    q = sub.add_parser("fields", help="Per-field plot (F4).")
    q.add_argument("-f", dest="field_dir", type=Path, required=True, help="Output folder of field-summary.")
    sub.add_parser("switches", help="Crumb rule and hole fill, off and on (F5).")
    sub.add_parser("check", help="v2 drawing data against results/ for every image (ring px, roots, skeleton).")
    args = p.parse_args()
    if args.cmd == "check":
        return run("N0", _selftest_n0)
    if args.cmd == "window":
        return run("F0", lambda: print(display_window()))
    if args.cmd == "image":
        names = [short(x) for x in image_paths()] if args.all else [args.image]
        return max(run("F1", figure_image, n, args.cell) for n in names)
    if args.cmd == "contact":
        if args.blind and not args.key:
            print("-b needs the blinding key: -k KEY")
            return 2
        return run("F2", figure_contact, args.key if args.blind else None)
    if args.cmd == "thresholds":
        return run("F3", figure_thresholds)
    if args.cmd == "fields":
        return run("F4", figure_fields, args.field_dir)
    if args.cmd == "switches":
        return run("F5", figure_switches)
    return 1


if __name__ == "__main__":
    sys.exit(main())
