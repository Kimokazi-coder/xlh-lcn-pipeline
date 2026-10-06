"""Figures that show a one pixel skeleton as a one pixel line.

The pipeline's verification picture thickens the skeleton by a 2 px dilation and
draws only the part a lacuna owns. That is right for checking ownership, but it
hides the rest of the network and it makes every thread look wider than it is,
which is exactly what this work is trying to see. These figures do the opposite:

- the image is upscaled 3 times (8 times for a tile) with nearest neighbour, so
  nothing is smoothed and every original pixel stays a sharp block;
- the skeleton is drawn one pixel wide in that upscaled image, at the centre of
  each original pixel's block, so a thread is a thin line and not a band;
- the part a lacuna owns is drawn in that lacuna's colour, the pipeline's own
  colours from canaliculi.lacuna_colors, and the rest is drawn in light grey, so
  nothing is hidden;
- the lacunae are outlined one pixel wide.

The display window is the pipeline's own: the full brightness original that
canaliculi.save_verification draws on, untouched.

canaliculi.save_verification is not edited. It is still called, for variants A
and the primary new variant only, to keep one picture in the pipeline's own style
beside these.

**Pixel size 0.13 um/px, rounded, unconfirmed per image.** Pre-validation.
"""
from __future__ import annotations

import numpy as np
from skimage import segmentation

import canaliculi

# Nearest neighbour upscale factors.
FULL_UPSCALE = 3
TILE_UPSCALE = 8
# Every tile panel is drawn at this many dots per inch, and its size in inches is
# set so that one upscaled image pixel is one dot. Below that a one pixel
# skeleton line is resampled away, which is the whole thing these figures exist
# to show.
TILE_DPI = 200

# The scale bar, in micrometres, and how far it sits from the corner.
SCALE_BAR_UM = 10.0
SCALE_BAR_MARGIN = 0.04
SCALE_BAR_THICKNESS = 3

UNOWNED_COLOUR = (210, 210, 210)
LACUNA_OUTLINE_FALLBACK = (0, 255, 255)


def upscale(image: np.ndarray, factor: int) -> np.ndarray:
    """Nearest neighbour, so no pixel is invented and none is blurred."""
    return image.repeat(factor, axis=0).repeat(factor, axis=1)


def _centres(rows: np.ndarray, cols: np.ndarray, factor: int) -> tuple:
    """Where an original pixel's centre lands in the upscaled image."""
    return rows * factor + factor // 2, cols * factor + factor // 2


def draw_skeleton(display: np.ndarray, skeleton: np.ndarray, owner_map: np.ndarray,
                  lacuna_id_map: np.ndarray, colors: dict, factor: int) -> np.ndarray:
    """The upscaled image with the skeleton drawn one pixel wide: owned threads in
    their lacuna's colour, everything else in light grey, lacunae outlined.

    One pixel means one pixel of the original image, so a skeleton pixel fills its
    whole block in the upscaled picture. That is the thread at its true width and
    nothing more. It is not the thickening the pipeline's verification picture
    does, which dilates the skeleton into its neighbours and makes a one pixel
    thread five pixels wide. Drawing only the centre of each block was tried first
    and is worse than useless: at eight times it puts one dot per eight pixels and
    the thread reads as a faint dotted line that disappears at any viewing size."""
    canvas = upscale(display, factor).copy()

    for lacuna_id, colour in colors.items():
        edge = segmentation.find_boundaries(lacuna_id_map == lacuna_id, mode="outer")
        if edge.any():
            canvas[upscale(edge, factor)] = colour

    unowned = upscale(skeleton & (owner_map == 0), factor)
    canvas[unowned] = UNOWNED_COLOUR
    for lacuna_id, colour in colors.items():
        owned = skeleton & (owner_map == lacuna_id)
        if owned.any():
            canvas[upscale(owned, factor)] = colour
    return canvas


def add_scale_bar(canvas: np.ndarray, pixel_size_um: float, factor: int,
                  length_um: float = SCALE_BAR_UM, colour=(255, 255, 255)) -> np.ndarray:
    """A bar of `length_um` micrometres in the bottom right, drawn into the
    pixels so nothing resamples it."""
    height, width = canvas.shape[:2]
    length = int(round(length_um / pixel_size_um * factor))
    if length >= width:
        return canvas
    margin = int(round(SCALE_BAR_MARGIN * width))
    thickness = max(1, SCALE_BAR_THICKNESS * factor // 3)
    r1 = height - margin
    c1 = width - margin
    canvas[r1 - thickness:r1, c1 - length:c1] = colour
    return canvas


def save_png(canvas: np.ndarray, path, reserved: list | None = None) -> None:
    """Write the panel, as an indexed png when `reserved` colours are given.

    A plain 256 colour quantisation moves every colour it sees, including the
    skeleton colours, which are the whole point of the picture: measured on one
    panel it changed all 14 of them. So the reserved colours keep exact slots of
    their own and only the background is quantised. The background is a dark red
    image with a narrow range, so this is hard to see, and it roughly halves the
    file."""
    from skimage.io import imsave

    path.parent.mkdir(parents=True, exist_ok=True)
    canvas = canvas.astype(np.uint8)
    if not reserved:
        imsave(path, canvas, check_contrast=False)
        return

    from PIL import Image

    unique = []
    for colour in reserved:
        colour = tuple(int(v) for v in colour)
        if colour not in unique:
            unique.append(colour)
    n_background = max(2, 256 - len(unique))
    quantised = Image.fromarray(canvas).quantize(colors=n_background, method=Image.MEDIANCUT,
                                                 dither=Image.NONE)
    palette = np.array(quantised.getpalette()[:3 * n_background], dtype=np.uint8).reshape(-1, 3)
    index = np.asarray(quantised, dtype=np.uint8).copy()
    for i, colour in enumerate(unique):
        exact = (canvas == np.array(colour, dtype=np.uint8)).all(axis=-1)
        if exact.any():
            index[exact] = n_background + i
    full = np.zeros((256, 3), dtype=np.uint8)
    full[:n_background] = palette
    for i, colour in enumerate(unique):
        full[n_background + i] = colour
    out = Image.fromarray(index, mode="P")
    out.putpalette(full.reshape(-1).tolist())
    out.save(path, optimize=True)


def full_panel(display: np.ndarray, detection: dict | None, colors: dict, pixel_size_um: float,
               path, factor: int = FULL_UPSCALE) -> None:
    """One full size panel in its own file: the raw image, or one variant."""
    if detection is None:
        canvas = upscale(display, factor).copy()
    else:
        canvas = draw_skeleton(display, detection["skeleton"], detection["owner_map"],
                               detection["lacuna_id_map"], colors, factor)
    reserved = list(colors.values()) + [UNOWNED_COLOUR, (255, 255, 255)]
    save_png(add_scale_bar(canvas, pixel_size_um, factor), path, reserved)


def crop(image: np.ndarray, box: tuple) -> np.ndarray:
    row0, col0, side = box[0], box[1], box[2]
    return image[row0:row0 + side, col0:col0 + side]


def tile_row(display: np.ndarray, detections: dict, keys: list, labels: dict, box: tuple,
             colors: dict, pixel_size_um: float, title: str, path, factor: int = TILE_UPSCALE) -> None:
    """One tile, the same crop, raw then every variant, each upscaled and drawn
    with a one pixel skeleton."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import textwrap

    panels = [(upscale(crop(display, box), factor), "raw image")]
    for key in keys:
        d = detections[key]
        canvas = draw_skeleton(crop(display, box), crop(d["skeleton"], box), crop(d["owner_map"], box),
                               crop(d["lacuna_id_map"], box), colors, factor)
        panels.append((canvas, f"{key}: {labels[key]}"))

    # Each panel must be at least as many screen pixels as the upscaled tile has,
    # or matplotlib resamples it and a one pixel line disappears. The panel size
    # is therefore set from the data: side times factor pixels at TILE_DPI.
    side_px = box[2] * factor
    panel_inches = side_px / TILE_DPI
    fig, axes = plt.subplots(1, len(panels),
                             figsize=(panel_inches * len(panels), panel_inches + 0.75))
    axes = np.atleast_1d(axes)
    for ax, (image, name) in zip(axes, panels):
        ax.imshow(image, interpolation="nearest")
        ax.set_title(textwrap.fill(name, 34), fontsize=6)
        ax.set_xticks([])
        ax.set_yticks([])
        bar = SCALE_BAR_UM / pixel_size_um * factor
        if bar < side_px:
            y = side_px * 0.94
            ax.plot([side_px * 0.95 - bar, side_px * 0.95], [y, y], color="white", linewidth=1.5)
            ax.text(side_px * 0.95 - bar / 2, y * 0.985, f"{SCALE_BAR_UM:g} µm", color="white",
                    fontsize=5.5, ha="center", va="bottom")
    fig.suptitle(textwrap.fill(title, 46 * len(panels)), fontsize=7)
    fig.tight_layout(rect=(0, 0.01, 1, 0.90))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=TILE_DPI, metadata={"Software": ""})
    plt.close(fig)


def width_check_figure(display: np.ndarray, profile: dict, box: tuple, pixel_size_um: float,
                       title: str, path, n_normals: int = 20, factor: int = TILE_UPSCALE) -> None:
    """The raw tile with the sampled normals drawn, so the width measurement can
    be checked by eye: each line is the span the profile was read along."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import textwrap

    from canal_physical import widthprofile

    row0, col0, side = box[0], box[1], box[2]
    inside = ((profile["rows"] >= row0) & (profile["rows"] < row0 + side)
              & (profile["cols"] >= col0) & (profile["cols"] < col0 + side) & profile["ok"])
    index = np.flatnonzero(inside)
    if index.size > n_normals:
        index = index[np.linspace(0, index.size - 1, n_normals).astype(int)]

    fig, ax = plt.subplots(figsize=(side * factor / TILE_DPI, side * factor / TILE_DPI + 0.5))
    ax.imshow(upscale(crop(display, box), factor), interpolation="nearest")
    half = widthprofile.PROFILE_HALF_PX
    for i in index:
        r = (profile["rows"][i] - row0) * factor + factor // 2
        c = (profile["cols"][i] - col0) * factor + factor // 2
        dr, dc = profile["normal_r"][i] * half * factor, profile["normal_c"][i] * half * factor
        ax.plot([c - dc, c + dc], [r - dr, r + dr], color="#00ff66", linewidth=0.8)
        ax.plot([c], [r], marker=".", color="#ff2200", markersize=2)
    ax.set_xticks([])
    ax.set_yticks([])
    bar = SCALE_BAR_UM / pixel_size_um * factor
    y = side * factor * 0.95
    ax.plot([side * factor * 0.95 - bar, side * factor * 0.95], [y, y], color="white", linewidth=2)
    ax.text(side * factor * 0.95 - bar / 2, y * 0.99, f"{SCALE_BAR_UM:g} µm", color="white",
            fontsize=7, ha="center", va="bottom")
    fig.suptitle(textwrap.fill(title, 90), fontsize=8)
    fig.tight_layout(rect=(0, 0.01, 1, 0.94))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=TILE_DPI, metadata={"Software": ""})
    plt.close(fig)


def pipeline_style(lac: dict, display: np.ndarray, detection: dict, path) -> None:
    """The pipeline's own verification picture, by the pipeline's own function."""
    canaliculi.save_verification({
        "lacunae": lac,
        "display": display,
        "lacuna_id_map": detection["lacuna_id_map"],
        "skeleton": detection["skeleton"],
        "owner_map": detection["owner_map"],
    }, path)
