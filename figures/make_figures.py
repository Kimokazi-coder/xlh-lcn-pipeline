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


def panel_letter(fig, ax, letter: str) -> None:
    bb = ax.get_position()
    fig.text(bb.x0, bb.y1 + 0.01, letter, fontsize=LETTER_SIZE, fontweight="bold", va="bottom", ha="left")


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
    args = p.parse_args()
    if args.cmd == "window":
        return run("F0", lambda: print(display_window()))
    if args.cmd == "image":
        names = [short(x) for x in image_paths()] if args.all else [args.image]
        return max(run("F1", figure_image, n, args.cell) for n in names)
    return 1


if __name__ == "__main__":
    sys.exit(main())
