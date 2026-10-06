"""Side by side: the raw image, the current method and the new one.

Same crop and same display window as the existing verification images, so the
only difference a reader sees is the skeleton. A scale bar in micrometres is on
every panel. The zoom crops are chosen by a rule, not by eye: see
`zoom_boxes`.

**Pixel size 0.13 um/px, rounded, unconfirmed per image.** Pre-validation.
"""
from __future__ import annotations

import numpy as np

import canaliculi
import lacunae

# The scale bar: a round number of micrometres that is a sensible share of the
# frame. 10 um is 77 px at 0.13 um/px, about 7.5% of a 1024 px frame.
SCALE_BAR_UM = 10.0

# Zoom crops. Side in micrometres, and how many to save per image.
ZOOM_SIDE_UM = 13.0  # 100 px at 0.13 um/px
ZOOM_COUNT = 3
# The rule: the image is divided into tiles of the zoom side, the skeleton length
# of each method is counted in every tile, and the tiles with the largest
# absolute difference are taken, in order, without overlap. This is deterministic
# and does not look at how good either skeleton is, so it cannot be cherry-picked.
ZOOM_RULE = ("tiles of the zoom side, ranked by the absolute difference in skeleton pixel count between "
             "the two methods, taken in order with no overlap")


def display_window(channel: np.ndarray) -> tuple:
    """The fixed window of the existing verification images: the current method
    draws its verification picture over the full-brightness original, which is
    lacunae.load_channel's display. Here the raw panel uses the same percentile
    window the figures use for the dataset, so all three panels match."""
    low, high = np.percentile(channel, (1.0, 99.8))
    return float(low), float(high)


def windowed(channel: np.ndarray, window: tuple) -> np.ndarray:
    low, high = window
    out = np.clip((channel - low) / (high - low), 0.0, 1.0) if high > low else np.zeros_like(channel)
    return (out * 255).astype(np.uint8)


def overlay(display_uint8: np.ndarray, skeleton: np.ndarray, lacuna_id_map: np.ndarray,
            colors: dict, owner_map: np.ndarray | None = None) -> np.ndarray:
    """One method drawn in the style of the existing verification image: each
    lacuna outlined in its colour, and the skeleton it owns painted in that
    colour. Unowned skeleton is drawn in white, so a reader can see what the
    ownership did not reach."""
    from skimage import segmentation

    rgb = np.stack([display_uint8] * 3, axis=-1) if display_uint8.ndim == 2 else display_uint8.copy()
    unowned = skeleton.copy()
    if owner_map is not None:
        for lacuna_id, color in colors.items():
            painted = skeleton & (owner_map == lacuna_id)
            rgb[painted] = color
            unowned &= ~painted
    rgb[unowned] = (255, 255, 255)
    for lacuna_id, color in colors.items():
        body = lacuna_id_map == lacuna_id
        if body.any():
            rgb[segmentation.find_boundaries(body, mode="outer")] = color
    return rgb


def tile_difference(skeleton_a: np.ndarray, skeleton_b: np.ndarray, side_px: int) -> np.ndarray:
    """Per tile, the absolute difference in skeleton pixel count. Deterministic."""
    rows, cols = skeleton_a.shape
    n_r, n_c = rows // side_px, cols // side_px
    diff = np.zeros((n_r, n_c), dtype=np.int64)
    for i in range(n_r):
        for j in range(n_c):
            sl = (slice(i * side_px, (i + 1) * side_px), slice(j * side_px, (j + 1) * side_px))
            diff[i, j] = abs(int(skeleton_a[sl].sum()) - int(skeleton_b[sl].sum()))
    return diff


def zoom_boxes(skeleton_current: np.ndarray, skeleton_new: np.ndarray, params,
               count: int = ZOOM_COUNT) -> list:
    """The crops where the two skeletons differ most, by ZOOM_RULE.

    Returns [(row0, col0, side_px, difference)], highest difference first. Ties
    break by position, so the result does not depend on anything but the two
    skeletons."""
    side_px = params.px_int(ZOOM_SIDE_UM)
    diff = tile_difference(skeleton_current, skeleton_new, side_px)
    order = sorted(((int(diff[i, j]), i, j) for i in range(diff.shape[0]) for j in range(diff.shape[1])),
                   key=lambda t: (-t[0], t[1], t[2]))
    boxes = []
    for value, i, j in order:
        if len(boxes) >= count:
            break
        boxes.append((i * side_px, j * side_px, side_px, value))
    return boxes


# The figures. matplotlib is already a dependency of this project
# (requirements.txt pins 3.9.4), so nothing is added.

PANEL_TITLES = ("raw image", "current method", "experimental method")
DPI = 300
# No timestamp in any output, so two identical runs give identical bytes.
PDF_METADATA = {"CreationDate": None, "Producer": "", "Creator": ""}
PNG_METADATA = {"Software": ""}
BOX_COLOUR = (1.0, 1.0, 0.0)  # yellow, the colour the pipeline uses for a frame-edge lacuna


def _scale_bar(ax, params, extent_px: int, colour="white") -> None:
    """A bar of SCALE_BAR_UM micrometres with its label, bottom right."""
    length_px = params.px(SCALE_BAR_UM)
    pad = extent_px * 0.04
    y = extent_px - pad
    x1 = extent_px - pad
    x0 = x1 - length_px
    ax.plot([x0, x1], [y, y], color=colour, linewidth=2.0, solid_capstyle="butt")
    ax.text((x0 + x1) / 2.0, y - extent_px * 0.015, f"{SCALE_BAR_UM:g} µm",
            color=colour, ha="center", va="bottom", fontsize=6.5)


def _panel(ax, image, title: str, params, extent_px: int, boxes=None) -> None:
    ax.imshow(image, cmap=None if image.ndim == 3 else "gray", vmin=None if image.ndim == 3 else 0,
              vmax=None if image.ndim == 3 else 255, interpolation="nearest")
    ax.set_title(title, fontsize=7.5)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_linewidth(0.4)
    if boxes:
        from matplotlib.patches import Rectangle
        for n, (row0, col0, side, _value) in enumerate(boxes, start=1):
            ax.add_patch(Rectangle((col0, row0), side, side, fill=False, edgecolor=BOX_COLOUR,
                                   linewidth=0.7))
            ax.text(col0 + 2, row0 + 2, str(n), color=BOX_COLOUR, fontsize=6, ha="left", va="top")
    _scale_bar(ax, params, extent_px)


def triptych(raw_uint8, current_rgb, new_rgb, label: str, params, boxes, out_png: Path,
             out_pdf: Path, caption: str) -> None:
    """Raw, current, experimental, side by side at the same crop and window, with
    the zoom boxes marked."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    extent = raw_uint8.shape[0]
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 4.0))
    for ax, image, title in zip(axes, (raw_uint8, current_rgb, new_rgb), PANEL_TITLES):
        _panel(ax, image, title, params, extent, boxes)
    fig.suptitle(f"{label}: {caption}", fontsize=8)
    fig.tight_layout(rect=(0, 0.02, 1, 0.94))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=DPI, metadata=PNG_METADATA)
    fig.savefig(out_pdf, metadata=PDF_METADATA)
    plt.close(fig)


def zoom(raw_uint8, current_rgb, new_rgb, label: str, params, box, index: int, out_png: Path,
         caption: str) -> None:
    """The same crop of all three panels, at the box the rule chose."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    row0, col0, side, value = box
    sl = (slice(row0, row0 + side), slice(col0, col0 + side))
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 4.2))
    for ax, image, title in zip(axes, (raw_uint8, current_rgb, new_rgb), PANEL_TITLES):
        _panel(ax, image[sl], title, params, side)
    fig.suptitle(f"{label} zoom {index}: {caption}\nat row {row0}, column {col0}, "
                 f"{params.um(side):g} µm square, skeleton length differs by {value} px",
                 fontsize=7.5)
    fig.tight_layout(rect=(0, 0.02, 1, 0.88))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=DPI, metadata=PNG_METADATA)
    plt.close(fig)
