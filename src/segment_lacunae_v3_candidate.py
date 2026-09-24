"""CANDIDATE lacuna segmentation v3. v3-RAW, pre-validation, NOT default.

segment_lacunae_v2 detects lacunae by BRIGHTNESS: the top class of a
3-class multi-Otsu cut on the red channel. That makes membership depend on
a lacuna being among the brightest things in its own field, which is a
property of the staining and the optical section, not of the cell.

This module detects them by BREADTH instead: open the raw channel with a
disk too large for any canaliculus to contain, so only broad objects
survive, then threshold the opened image on its own histogram. A lacuna is
the only thing in these fields that is both bright and broad, so breadth
carries the signal that brightness was standing in for.

Everything AFTER detection is v2's, imported rather than copied:
    seg2.watershed_split       separate fused blobs by thickness
    seg2.merge_shallow_splits  undo spurious watershed cuts
    seg2.filter_regions        area / solidity / aspect / on_border
Using v2's own filters unchanged is deliberate: it makes a v2-vs-v3
comparison a comparison of DETECTION, with everything downstream held
constant. It also means v3 inherits v2's TEST_MIN_SOLIDITY, so an object
rejected there for shape is rejected here too.

STATUS: nothing here is validated. canaliculi_v1.LACUNA_SOURCE defaults to
"v2" and this module is only reached when that is explicitly overridden.
Whether a lacuna lying partly outside the focal plane should be counted at
all is a scientific decision, not a coding one -- this module surfaces the
objects the two detectors disagree about; it does not adjudicate them.

Usage:
    python src/segment_lacunae_v3_candidate.py --dir data/WT
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from skimage import measure, morphology

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from count_lacunae import load_channel  # noqa: E402
import segment_lacunae_v2 as seg2  # noqa: E402

# Radius (px) of the disk that opens the raw channel. An opening with this
# disk deletes anything narrower than 2R+1 px across, so R sets the
# narrowest lacuna v3 can see, and every canaliculus must fall below it.
#
# PROVENANCE. Two measurements bracket it:
#   * Canalicular widths, pooled over all 8 WT images post-top-hat, are
#     p50 ~6.0 and p99 ~8.5 px full width. R must exceed ~4 for every
#     canaliculus to be erased.
#   * The narrowest v2-kept lacuna has a minor axis of about 17 px, and the
#     rejected elongated object at (230,300) in 542_z06 is about the same.
#     R must stay below ~8 for objects that thin to survive at all.
# Phase 0(e) counted broad objects BEFORE any filtering (58-180 per image
# at R=8, 14-31 at R=17). Those counts change once v2's own filters run, so
# the value here comes from a sweep over the TUNING SET ONLY (ground rule
# 9) with those filters applied, objects kept per image against v2's count:
#     v2:      16 / 12 / 13
#     R=6:     45 / 106 / 79     R=8:  25 / 66 / 65
#     R=10:    23 / 25 / 33      R=12: 21 / 28 / 24     R=17: 15 / 20 / 14
# R=17 lands closest to v2's counts, but that is the wrong objective:
# matching v2 is not the goal, since the whole premise is that v2 may be
# missing objects. The binding constraint is the other one -- the
# obliquely-sectioned lacuna at (230,300) in 542_z06 survives detection at
# R<=12 and is ERASED at R=17. R=12 is the largest radius that still sees
# it, and it roughly halves R=8's over-detection.
#
# At R=12 that object is recovered with solidity 0.952, against 0.452 under
# v2. That is the mechanism this module is for: the broad opening resolves
# a thin curved object into a compact one, so it passes v2's UNCHANGED
# solidity filter. v3 recovers it without anyone touching TEST_MIN_SOLIDITY.
BROAD_OPENING_RADIUS_PX = 12

# Small holes inside a detected object are filled before watershed, the
# same step and threshold v2 applies in multiotsu_lacuna_mask, so an
# unstained nucleus does not split one lacuna into a ring.
FILL_HOLES_BELOW_PX2 = 20

# Two kept objects count as the same lacuna when their intersection covers
# at least this fraction of the SMALLER one. 0.5 is a containment test, not
# a shape-agreement test: it asks whether one detection sits inside the
# other, which is the relationship v2 and v3 actually have on a shared
# lacuna.
MATCH_OVERLAP_MIN = 0.5

V3_DIR = config.RESULTS_DIR / "count_v3_candidate"


def broad_lacuna_mask(channel: np.ndarray) -> tuple[np.ndarray, float]:
    """Detect lacunae as BROAD bright objects. Returns (mask, threshold).

    The threshold comes from the opened image's own histogram, per image,
    with no global intensity constant -- the same adaptive principle v2
    uses, applied to a different quantity."""
    from canaliculi_v1 import total_signal_mask

    opened = morphology.opening(channel, morphology.disk(BROAD_OPENING_RADIUS_PX))
    mask, threshold = total_signal_mask(opened)
    mask = morphology.remove_small_holes(mask, area_threshold=FILL_HOLES_BELOW_PX2)
    return mask, threshold


def segment_image(image_path: Path):
    """Same signature and return shape as seg2.segment_image, so the two
    are interchangeable behind canaliculi_v1.LACUNA_SOURCE."""
    display, channel = load_channel(image_path)
    mask, threshold = broad_lacuna_mask(channel)
    labels = seg2.watershed_split(mask)
    distance = ndi.distance_transform_edt(mask)
    labels = seg2.merge_shallow_splits(labels, mask, distance)
    kept = seg2.filter_regions(labels)
    return display, labels, kept, threshold


def compare_to_v2(image_path: Path) -> dict:
    """Which objects the two detectors agree and disagree about.

    Matching is by pixel overlap of the kept bodies, measured against the
    SMALLER of the two objects. That asymmetry is deliberate and was a
    correction: v3's broad opening systematically dilates a detection, so
    a v3 object typically ENCLOSES the v2 object on the same lacuna. Scored
    as "what fraction of the v3 object lies in v2's mask" those pairs fall
    below any sensible cut and get miscounted as disagreements -- the first
    run of this comparison reported 14-39 "v3-only" objects per image, and
    the overlay showed most of them were cyan rings drawn around green
    ones, i.e. the same lacuna twice. Scoring against the smaller object
    asks the right question: does one detection sit inside the other."""
    _d2, v2_labels, v2_kept, _t2 = seg2.segment_image(image_path)
    _d3, v3_labels, v3_kept, _t3 = segment_image(image_path)

    v2_mask = np.isin(v2_labels, [r.label for r, _ob in v2_kept])
    v3_mask = np.isin(v3_labels, [r.label for r, _ob in v3_kept])

    def entry_for(region, on_border, overlap):
        return {
            "x": float(region.centroid[1]),
            "y": float(region.centroid[0]),
            "area": float(region.area),
            "solidity": float(region.solidity),
            "on_border": bool(on_border),
            "overlap": overlap,
        }

    # Pair up kept objects by best mutual overlap, scored against the
    # smaller of the pair (see the docstring).
    v3_regions = [(r, ob, set(map(tuple, r.coords))) for r, ob in v3_kept]
    matched_v3: set[int] = set()
    v2_only, shared_v2 = [], []
    for region, on_border in v2_kept:
        v2_pixels = set(map(tuple, region.coords))
        best_i, best_score = None, 0.0
        for i, (v3_region, _ob3, v3_pixels) in enumerate(v3_regions):
            inter = len(v2_pixels & v3_pixels)
            if inter == 0:
                continue
            score = inter / min(len(v2_pixels), len(v3_pixels))
            if score > best_score:
                best_i, best_score = i, score
        if best_score >= MATCH_OVERLAP_MIN and best_i is not None:
            matched_v3.add(best_i)
            shared_v2.append(entry_for(region, on_border, best_score))
        else:
            v2_only.append(entry_for(region, on_border, best_score))

    v3_only = [
        entry_for(r, ob, 0.0)
        for i, (r, ob, _px) in enumerate(v3_regions)
        if i not in matched_v3
    ]

    return {
        "image": image_path.stem,
        "v2_count": len(v2_kept),
        "v3_count": len(v3_kept),
        "shared": len(shared_v2),
        "v2_only": v2_only,
        "v3_only": v3_only,
        "v2_mask": v2_mask,
        "v3_mask": v3_mask,
    }


def save_comparison_overlay(display_uint8: np.ndarray, comparison: dict, out_path: Path) -> None:
    """Three colours: v2-only red, v3-only cyan, shared by both green."""
    from skimage import segmentation
    from skimage.io import imsave

    v2_mask, v3_mask = comparison["v2_mask"], comparison["v3_mask"]
    vis = display_uint8.copy()
    for mask, colour in (
        (v2_mask & ~v3_mask, [255, 0, 0]),
        (v3_mask & ~v2_mask, [0, 255, 255]),
        (v2_mask & v3_mask, [0, 255, 0]),
    ):
        if mask.any():
            vis[segmentation.find_boundaries(mask, mode="outer")] = colour
    out_path.parent.mkdir(parents=True, exist_ok=True)
    imsave(out_path, vis, check_contrast=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="v3-CANDIDATE lacuna segmentation by breadth (pre-validation, not default)."
    )
    parser.add_argument("--dir", type=Path, required=True)
    args = parser.parse_args()

    print(f"v3 candidate: broad opening r={BROAD_OPENING_RADIUS_PX}px, then v2's watershed/merge/filters")
    print(f'{"image":22s} {"v2":>4s} {"v3":>4s} {"shared":>7s} {"v2-only":>8s} {"v3-only":>8s}')
    for path in sorted(args.dir.glob("*.tif")):
        comparison = compare_to_v2(path)
        display, _channel = load_channel(path)
        save_comparison_overlay(
            display, comparison, V3_DIR / path.stem.replace(" ", "_") / "v2_vs_v3.png"
        )
        print(
            f'{path.stem[:22]:22s} {comparison["v2_count"]:4d} {comparison["v3_count"]:4d} '
            f'{comparison["shared"]:7d} {len(comparison["v2_only"]):8d} {len(comparison["v3_only"]):8d}'
        )


if __name__ == "__main__":
    main()
