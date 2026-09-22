"""READ-ONLY diagnostic for sizing the canalicular-mask preprocessing
parameters in canaliculi_v1.py. Changes nothing in the pipeline.

Reports, per image and pooled over a directory:
  * the half-width (distance-transform) distribution INSIDE the raw
    candidate canaliculi mask -- i.e. how thick the real threads are, in
    px. This is what the white top-hat structuring element has to be
    comfortably LARGER than (a top-hat keeps what is smaller than its
    structuring element and flattens what is larger), and what the
    Gaussian sigma has to stay BELOW.
  * mask area fraction and connected-component count, before vs. after a
    candidate top-hat radius, so the "fewer noise blobs / fewer gaps"
    claim can be checked numerically rather than by eye.

Usage:
    python src/diagnose_canaliculi_mask.py --dir data/WT
    python src/diagnose_canaliculi_mask.py --dir data/WT --radius 12
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
import canaliculi_v1 as can  # noqa: E402
import segment_lacunae_v2 as seg2  # noqa: E402


def percentiles(values: np.ndarray, qs=(50, 75, 90, 95, 99, 100)) -> str:
    if values.size == 0:
        return "(empty)"
    return "  ".join(f"p{q}={np.percentile(values, q):.2f}" for q in qs)


def analyse(image_path: Path, radius: int) -> tuple[np.ndarray, dict]:
    _display, channel = load_channel(image_path)
    _d2, labels, kept, _t_hi = seg2.segment_image(image_path)
    lacuna_mask, _lacuna_id_map = can.build_lacuna_maps(labels, kept)

    # Raw (pre-top-hat) candidate mask: exactly what canaliculi_v1 used
    # before the preprocessing change.
    signal, _t_lo = can.total_signal_mask(channel)
    buffered = morphology.dilation(lacuna_mask, morphology.disk(can.LACUNA_DILATION_PX))
    raw = morphology.remove_small_objects(signal & ~buffered, min_size=can.MIN_THREAD_OBJECT_PX2)

    # Half-widths of the raw threads: distance transform sampled on the
    # skeleton, so each sample is one centreline pixel's half-thickness.
    dist = ndi.distance_transform_edt(raw)
    skel = morphology.skeletonize(raw)
    half_widths = dist[skel]

    tophat = morphology.white_tophat(channel, morphology.disk(radius))
    th_signal, _t = can.total_signal_mask(tophat)
    th = morphology.remove_small_objects(th_signal & ~buffered, min_size=can.MIN_THREAD_OBJECT_PX2)

    stats = {
        "lacunae": len(kept),
        "raw_area_frac": float(raw.mean()),
        "raw_components": int(measure.label(raw).max()),
        "raw_skel_px": int(skel.sum()),
        "th_area_frac": float(th.mean()),
        "th_components": int(measure.label(th).max()),
        "th_skel_px": int(morphology.skeletonize(th).sum()),
    }
    return half_widths, stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only canaliculi mask/width diagnostic.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--image", type=Path)
    group.add_argument("--dir", type=Path)
    parser.add_argument("--radius", type=int, default=can.TOPHAT_RADIUS_PX if hasattr(can, "TOPHAT_RADIUS_PX") else 12,
                        help="Candidate white top-hat disk radius (px) to test.")
    args = parser.parse_args()

    paths = [args.image] if args.image else sorted(args.dir.glob("*.tif"))
    pooled = []
    for path in paths:
        half_widths, s = analyse(path, args.radius)
        pooled.append(half_widths)
        print(f"{path.name}  lacunae={s['lacunae']}")
        print(f"    thread half-width (px):  {percentiles(half_widths)}")
        print(
            f"    raw   : area_frac={s['raw_area_frac']:.4f}  components={s['raw_components']:5d}  skel_px={s['raw_skel_px']}"
        )
        print(
            f"    tophat: area_frac={s['th_area_frac']:.4f}  components={s['th_components']:5d}  skel_px={s['th_skel_px']}  (r={args.radius})"
        )

    if len(pooled) > 1:
        allw = np.concatenate(pooled)
        print(f"\nPOOLED thread half-width over {len(pooled)} images (n={allw.size}):")
        print(f"    {percentiles(allw)}")
        print(f"    implied full width p99 = {2 * np.percentile(allw, 99):.2f} px")


if __name__ == "__main__":
    main()
