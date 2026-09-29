"""Read-only diagnostic: why a kept v2 lacuna has an unfilled hole, and
what the hole does downstream. Pre-validation, PIXEL units. Changes no
pipeline output and no default.

Written for finding 3 of the 2026-09-29 visual review (542_z06, the lacuna
near (785,545) with an unfilled hole in its mask).

For the target lacuna it reports:
    the hole at each v2 mask step: the raw top-class cut (channel >= t_hi),
        after remove_small_holes(area_threshold=20), after the r=1 opening,
        and in the final watershed label
    brightness inside the hole against the body, t_hi and the image's
        lower (background) multi-Otsu cut
    area and solidity with and without the hole filled
    canaliculi: default mask and skeleton pixels inside the hole, and how
        many of the lacuna's roots (COUNT_MODE="roots" attachment clusters
        on the default graph) come from nodes inside the hole

For every kept lacuna in every image it also lists enclosed holes in the
RAW top-class cut inside the object's filled outline, so the fill limit of
20 px^2 can be judged against the actual hole sizes: which holes that step
fills, and which it leaves.

Usage (one line):
    python diagnostics/lacunae/inspect_lacuna_hole.py --dir data/WT --target "542 WT  2_z06c1-2" 785,545
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from skimage import filters, measure, morphology, segmentation
from skimage.io import imread, imsave

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from count_lacunae import load_channel  # noqa: E402
import canaliculi_v1 as can  # noqa: E402
import segment_lacunae_hybrid as hy  # noqa: E402
import segment_lacunae_v2 as seg2  # noqa: E402

OUT_DIR = config.DIAGNOSTICS_DIR / "round3" / "finding3"
REPORT_DIR = config.REPORTS_DIR / "round3"

# Must match the literal in seg2.multiotsu_lacuna_mask (area_threshold=20).
# Repeated here, not imported, because v2 does not expose it as a constant.
V2_FILL_HOLES_PX2 = 20

CROP_HALF_PX = 70


def enclosed_holes(body: np.ndarray) -> np.ndarray:
    """Pixels enclosed by `body` but not part of it."""
    return ndi.binary_fill_holes(body) & ~body


def raw_hole_sizes(channel: np.ndarray, t_hi: float, body: np.ndarray) -> list[int]:
    """Areas of enclosed holes in the RAW top-class cut, inside the
    object's filled outline. These are the holes v2's fill step saw."""
    filled = ndi.binary_fill_holes(body)
    raw = (channel >= t_hi) & filled
    holes = measure.label(ndi.binary_fill_holes(raw) & ~raw, connectivity=1)
    return [int(r.area) for r in measure.regionprops(holes)]


def stage_masks(channel: np.ndarray) -> tuple[dict, float]:
    """v2's mask at each step, recomputed with v2's own constants."""
    t_hi = float(filters.threshold_multiotsu(channel, classes=3)[-1])
    raw = channel >= t_hi
    filled = morphology.remove_small_holes(raw, area_threshold=V2_FILL_HOLES_PX2)
    opened = morphology.opening(filled, morphology.disk(seg2.DESPECKLE_OPENING_RADIUS_PX))
    return {"raw cut": raw, "after fill<=20": filled, "after r=1 opening": opened}, t_hi


def save_crop(display, body, hole, skeleton, cx, cy, out_path: Path) -> None:
    """raw | outline with the hole tinted | default skeleton."""
    h, w = body.shape
    r0 = int(np.clip(cy - CROP_HALF_PX, 0, h - 2 * CROP_HALF_PX))
    c0 = int(np.clip(cx - CROP_HALF_PX, 0, w - 2 * CROP_HALF_PX))
    sl = (slice(r0, r0 + 2 * CROP_HALF_PX), slice(c0, c0 + 2 * CROP_HALF_PX))
    raw = display[sl].copy()
    marked = raw.copy()
    marked[hole[sl]] = [255, 255, 0]
    marked[segmentation.find_boundaries(body[sl], mode="outer")] = [0, 255, 255]
    skel = raw.copy() // 3
    skel[skeleton[sl]] = [255, 255, 255]
    skel[hole[sl] & ~skeleton[sl]] = [120, 120, 0]
    sep = np.full((raw.shape[0], 4, 3), 128, np.uint8)
    strip = np.hstack([raw, sep, marked, sep, skel])
    strip = np.repeat(np.repeat(strip, 3, axis=0), 3, axis=1)  # 3x for legibility
    out_path.parent.mkdir(parents=True, exist_ok=True)
    imsave(out_path, strip, check_contrast=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dir", type=Path, required=True)
    parser.add_argument("--target", nargs=2, required=True, metavar=("IMAGE_STEM", "X,Y"))
    args = parser.parse_args()
    stem, point = args.target
    x, y = (float(v) for v in point.split(","))

    lines = [
        "Unfilled hole in a kept v2 lacuna. PRE-VALIDATION, PIXEL units.",
        "Read-only diagnostic; no pipeline output or default changed.",
        "",
    ]

    # --- population: raw-cut holes inside every kept lacuna -------------
    filled_sizes: list[int] = []
    left_sizes: list[tuple] = []
    n_objects = 0
    for path in sorted(args.dir.glob("*.tif")):
        _display, channel = load_channel(path)
        _d, labels, kept, t_hi = seg2.segment_image(path)
        for lid, (region, _b) in enumerate(kept, start=1):
            n_objects += 1
            body = labels == region.label
            for size in raw_hole_sizes(channel, t_hi, body):
                (filled_sizes if size <= V2_FILL_HOLES_PX2 else left_sizes).append(
                    size if size <= V2_FILL_HOLES_PX2 else (size, path.stem, lid)
                )
            final = enclosed_holes(body)
            if final.any():
                lines.append(
                    f"final label has a hole: {path.stem} id {lid} at "
                    f"({region.centroid[1]:.0f},{region.centroid[0]:.0f}), hole area {int(final.sum())} px^2"
                )
    lines += [
        f"Population: {n_objects} kept lacunae over the 8 WT images.",
        f"Raw-cut holes inside kept lacunae: {len(filled_sizes) + len(left_sizes)} in total.",
        f"  filled by v2 (<= {V2_FILL_HOLES_PX2} px^2): {len(filled_sizes)}, sizes "
        f"{sorted(filled_sizes)}",
        f"  left open (> {V2_FILL_HOLES_PX2} px^2): {len(left_sizes)}: "
        + ", ".join(f"{s} px^2 ({img} id {i})" for s, img, i in sorted(left_sizes)),
        "",
    ]

    # --- the target lacuna ---------------------------------------------
    path = next(p for p in args.dir.glob("*.tif") if p.stem == stem)
    display, channel = load_channel(path)
    _d, labels, kept, t_hi = seg2.segment_image(path)
    lacuna_mask, lacuna_id_map = can.build_lacuna_maps(labels, kept)
    lid = 1 + int(np.argmin([np.hypot(r.centroid[1] - x, r.centroid[0] - y) for r, _b in kept]))
    region = kept[lid - 1][0]
    body = lacuna_id_map == lid
    hole = enclosed_holes(body)
    filled_body = body | hole
    t_lo = float(filters.threshold_multiotsu(channel, classes=3)[0])

    lines.append(
        f"Target: {stem} point ({x:.0f},{y:.0f}) -> lacuna_id {lid} at "
        f"({region.centroid[1]:.0f},{region.centroid[0]:.0f})"
    )
    lines.append(f"  hole area in final label: {int(hole.sum())} px^2 "
                 f"({100 * hole.sum() / filled_body.sum():.1f}% of the filled outline)")

    stages, _t = stage_masks(channel)
    for name, mask in stages.items():
        inside = mask & filled_body
        lines.append(f"  {name:20s} hole px inside outline: {int((filled_body & ~inside).sum())}")

    hole_vals = channel[hole] if hole.any() else np.array([np.nan])
    lines += [
        f"  intensity: hole mean {np.nanmean(hole_vals):.3f} (max {np.nanmax(hole_vals):.3f}), "
        f"body mean {channel[body].mean():.3f}, t_hi {t_hi:.3f}, background cut t_lo {t_lo:.3f}",
        f"  hole pixels below t_hi: {100 * np.mean(hole_vals < t_hi):.0f}%, "
        f"below t_lo: {100 * np.mean(hole_vals < t_lo):.0f}%",
    ]

    def solidity(mask):
        return float(measure.regionprops(mask.astype(int))[0].solidity)

    lines.append(
        f"  area {int(body.sum())} as measured, {int(filled_body.sum())} with hole filled "
        f"(+{100 * hole.sum() / body.sum():.1f}%); solidity {solidity(body):.3f} -> "
        f"{solidity(filled_body):.3f}"
    )

    # --- canaliculi inside the hole --------------------------------------
    out_stem = stem.replace(" ", "_")
    default_dir = config.CANALICULI_DIR / out_stem
    mask_png = imread(default_dir / "canaliculi_mask.png") > 0
    skeleton = imread(default_dir / "skeleton.png") > 0
    lines.append(
        f"  default canaliculi mask px in hole: {int((mask_png & hole).sum())}; "
        f"skeleton px in hole: {int((skeleton & hole).sum())}"
    )

    G, _flagged = hy.default_skeleton_graph(path, channel, labels, kept)
    dist_to_lacuna, nearest_id = can.nearest_lacuna_map(lacuna_id_map)
    can.attach_lacunae(G, dist_to_lacuna, nearest_id, list(range(1, len(kept) + 1)))
    roots_all = len(can.cell_root_lengths(G, lid))
    src = ("cell", lid)
    points = [n for n in G.neighbors(src) if not can._is_cell_node(n)] if G.has_node(src) else []
    in_hole = [n for n in points if hole[n]]
    G.remove_nodes_from(in_hole)
    roots_without = len(can.cell_root_lengths(G, lid))
    lines.append(
        f"  roots (COUNT_MODE='roots', default graph): {roots_all}; attachment nodes inside "
        f"the hole: {len(in_hole)}; roots with those nodes removed: {roots_without}"
    )

    save_crop(
        display, body, hole, skeleton, region.centroid[1], region.centroid[0],
        OUT_DIR / f"{out_stem}_id{lid}_hole.png",
    )
    text = "\n".join(lines)
    print(text)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "finding3_542_z06_hole.txt").write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
