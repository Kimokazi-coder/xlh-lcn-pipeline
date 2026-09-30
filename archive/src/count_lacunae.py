"""Count osteocyte lacunae in a single confocal image.

Pipeline (all parameters come from config.py, nothing hardcoded):

    1. Load the .tif (RGB or RGBA) and take config.CHANNEL (default: red).
    2. Threshold the channel to isolate bright lacunae
       (config.THRESHOLD_METHOD: "otsu" or "percentile").
    3. Fill small holes, then morphologically open to despeckle.
    4. Label connected components.
    5. Keep objects passing: min/max area, min solidity, max aspect ratio,
       and (optionally) exclude those touching the image border.

Everything stays in PIXEL units -- config.PIXEL_SIZE_UM is not used here.

Outputs (written to config.RESULTS_DIR, mirroring the image's subfolder
under config.DATA_DIR when it lives under one):

    <stem>_overlay.png   original image with kept lacunae outlined in green
    <stem>_lacunae.csv   one row per kept lacuna
    <stem>_params.json   exact parameter values used for this run

Usage:
    python src/count_lacunae.py --image data/WT/example.tif
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from skimage import measure, morphology, segmentation
from skimage.io import imread, imsave
from skimage.filters import threshold_otsu
from skimage.util import img_as_float, img_as_ubyte

# Make `import config` work regardless of the caller's working directory:
# config.py lives at the project root, one directory up from this file.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402


def load_channel(image_path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Load `image_path` and return (display_rgb_uint8, signal_channel_float).

    `display_rgb_uint8` is the original image, coerced to RGB uint8, for use
    as the overlay background. `signal_channel_float` is config.CHANNEL as a
    2D float array in [0, 1], with config.INVERT_SIGNAL applied if set.
    """
    raw = imread(image_path)

    if raw.ndim == 2:
        # Already single-channel.
        display = np.stack([raw] * 3, axis=-1)
        channel_2d = raw
    elif raw.ndim == 3:
        if config.CHANNEL_AXIS == 0:
            raw = np.moveaxis(raw, 0, -1)
        elif config.CHANNEL_AXIS not in (-1, 2):
            raise ValueError(f"Unsupported config.CHANNEL_AXIS: {config.CHANNEL_AXIS!r}")

        n_channels = raw.shape[-1]
        if n_channels not in (3, 4):
            raise ValueError(
                f"Expected an RGB or RGBA image, got shape {raw.shape} for {image_path}"
            )
        if config.CHANNEL is None or not (0 <= config.CHANNEL < n_channels):
            raise ValueError(
                f"config.CHANNEL={config.CHANNEL!r} is not a valid index into "
                f"an image with {n_channels} channels ({image_path})"
            )
        display = raw[..., :3]  # drop alpha for display, if present
        channel_2d = raw[..., config.CHANNEL]
    else:
        raise ValueError(f"Unsupported image ndim={raw.ndim} for {image_path}")

    display_uint8 = img_as_ubyte(display)
    channel_float = img_as_float(channel_2d)
    if config.INVERT_SIGNAL:
        channel_float = 1.0 - channel_float
    return display_uint8, channel_float


def compute_threshold(channel: np.ndarray) -> float:
    """Return the intensity cutoff for `channel`, per config.THRESHOLD_METHOD."""
    method = config.THRESHOLD_METHOD
    if method == "otsu":
        base = threshold_otsu(channel)
    elif method == "percentile":
        base = float(np.percentile(channel, config.PERCENTILE_THRESHOLD))
    else:
        raise ValueError(
            f"config.THRESHOLD_METHOD={method!r} is not implemented in "
            "count_lacunae.py (supported: 'otsu', 'percentile')"
        )
    return base * config.THRESHOLD_SCALE


def segment(channel: np.ndarray, threshold: float) -> np.ndarray:
    """Binarize, fill small holes, and morphologically open. Returns a bool mask."""
    mask = channel >= threshold

    if config.FILL_HOLES_BELOW_PX2:
        mask = morphology.remove_small_holes(mask, area_threshold=config.FILL_HOLES_BELOW_PX2)

    if config.OPENING_RADIUS_PX and config.OPENING_RADIUS_PX > 0:
        mask = morphology.opening(mask, morphology.disk(config.OPENING_RADIUS_PX))

    return mask


def filter_regions(label_image: np.ndarray) -> list:
    """Return regionprops for objects passing every configured filter."""
    rows, cols = label_image.shape
    kept = []
    for region in measure.regionprops(label_image):
        if region.area < config.MIN_OBJECT_SIZE_PX2:
            continue
        if config.MAX_OBJECT_SIZE_PX2 is not None and region.area > config.MAX_OBJECT_SIZE_PX2:
            continue
        if region.solidity < config.MIN_SOLIDITY:
            continue

        minor = region.axis_minor_length
        major = region.axis_major_length
        aspect_ratio = (major / minor) if minor > 0 else float("inf")
        if aspect_ratio > config.LACUNA_ASPECT_RATIO_MAX:
            continue

        if config.EXCLUDE_BORDER_OBJECTS:
            min_row, min_col, max_row, max_col = region.bbox
            touches_border = min_row == 0 or min_col == 0 or max_row == rows or max_col == cols
            if touches_border:
                continue

        kept.append(region)
    return kept


def save_overlay(display_uint8: np.ndarray, label_image: np.ndarray, kept: list, out_path: Path) -> None:
    """Save `display_uint8` with the boundaries of kept objects drawn in green."""
    kept_ids = {region.label for region in kept}
    kept_mask = np.isin(label_image, list(kept_ids)) if kept_ids else np.zeros_like(label_image, dtype=bool)
    boundaries = segmentation.find_boundaries(kept_mask, mode="outer")

    overlay = display_uint8.copy()
    overlay[boundaries] = [0, 255, 0]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    imsave(out_path, overlay, check_contrast=False)


def save_csv(kept: list, out_path: Path) -> None:
    precision = config.CSV_FLOAT_PRECISION
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        f.write(
            "lacuna_id,area_px2,centroid_row_px,centroid_col_px,"
            "major_axis_length_px,minor_axis_length_px,eccentricity,solidity,units\n"
        )
        for i, region in enumerate(kept, start=1):
            row, col = region.centroid
            f.write(
                f"{i},{region.area},"
                f"{round(row, precision)},{round(col, precision)},"
                f"{round(region.axis_major_length, precision)},"
                f"{round(region.axis_minor_length, precision)},"
                f"{round(region.eccentricity, precision)},"
                f"{round(region.solidity, precision)},px\n"
            )


def save_params(image_path: Path, threshold: float, total_labeled: int, kept_count: int, out_path: Path) -> None:
    params = {
        "image": str(image_path),
        "units": "px",
        "channel": config.CHANNEL,
        "channel_axis": config.CHANNEL_AXIS,
        "invert_signal": config.INVERT_SIGNAL,
        "pixel_size_um": config.PIXEL_SIZE_UM,
        "threshold_method": config.THRESHOLD_METHOD,
        "percentile_threshold": config.PERCENTILE_THRESHOLD,
        "threshold_scale": config.THRESHOLD_SCALE,
        "computed_threshold": threshold,
        "fill_holes_below_px2": config.FILL_HOLES_BELOW_PX2,
        "opening_radius_px": config.OPENING_RADIUS_PX,
        "min_object_size_px2": config.MIN_OBJECT_SIZE_PX2,
        "max_object_size_px2": config.MAX_OBJECT_SIZE_PX2,
        "min_solidity": config.MIN_SOLIDITY,
        "lacuna_aspect_ratio_max": config.LACUNA_ASPECT_RATIO_MAX,
        "exclude_border_objects": config.EXCLUDE_BORDER_OBJECTS,
        "random_seed": config.RANDOM_SEED,
        "objects_labeled_before_filtering": total_labeled,
        "lacunae_kept": kept_count,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(params, f, indent=2)


def output_stem(image_path: Path) -> Path:
    """Return the output path stem under RESULTS_DIR, mirroring image_path's
    subfolder under DATA_DIR when it lives under one, else results/<stem>."""
    image_path = image_path.resolve()
    try:
        relative = image_path.relative_to(config.DATA_DIR.resolve())
        return config.RESULTS_DIR / relative.with_suffix("")
    except ValueError:
        return config.RESULTS_DIR / image_path.stem


def main() -> None:
    parser = argparse.ArgumentParser(description="Count osteocyte lacunae in one image.")
    parser.add_argument("--image", required=True, type=Path, help="Path to a .tif image (RGB or RGBA).")
    args = parser.parse_args()

    image_path = args.image
    if not image_path.is_file():
        raise FileNotFoundError(f"No such file: {image_path}")

    display_uint8, channel = load_channel(image_path)
    threshold = compute_threshold(channel)
    mask = segment(channel, threshold)
    label_image = measure.label(mask, connectivity=2)
    total_labeled = int(label_image.max())
    kept = filter_regions(label_image)

    stem = output_stem(image_path)
    if config.SAVE_OVERLAYS:
        save_overlay(display_uint8, label_image, kept, stem.with_name(stem.name + "_overlay.png"))
    save_csv(kept, stem.with_name(stem.name + "_lacunae.csv"))
    save_params(image_path, threshold, total_labeled, len(kept), stem.with_name(stem.name + "_params.json"))

    print(f"Lacunae kept: {len(kept)} (of {total_labeled} labeled objects before filtering)")
    print(f"Threshold used ({config.THRESHOLD_METHOD}): {threshold:.4f}")
    if config.SAVE_OVERLAYS:
        print(f"Overlay saved to: {stem.with_name(stem.name + '_overlay.png')}")
    print(f"CSV saved to: {stem.with_name(stem.name + '_lacunae.csv')}")
    print(f"Params saved to: {stem.with_name(stem.name + '_params.json')}")


if __name__ == "__main__":
    main()
