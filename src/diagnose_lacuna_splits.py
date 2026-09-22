"""Read-only diagnostic: find lacunae that segment_lacunae_v2's watershed
step split into two pieces, and score how "real" that split is.

For every pre-watershed connected component that ends up as exactly two
kept lacunae, this measures the saddle depth between the two pieces: the
minimum distance-transform value along the straight line connecting their
two distance-transform peaks (the two watershed seed locations). A true
two-lobe "dumbbell" (two touching cells) has a deep, narrow neck -> low
saddle value relative to the peaks. A single smoothly elongated lacuna
that merely has two comparable-height ends -> shallow saddle -> saddle
value close to the peak heights -> ratio close to 1.

(Earlier attempt used the minimum distance over the *entire* shared
boundary between the two watershed regions; that always came out ~1.0
because that boundary line's two ends necessarily touch the mask's outer
edge, an artifact unrelated to the real neck depth. This version instead
samples along the straight line between the two peaks, which is what
watershed's flood-front collision point actually depends on.)

Does not modify anything -- prints a table only.

Usage:
    python src/diagnose_lacuna_splits.py --dir data/WT
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from skimage import measure

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from count_lacunae import load_channel  # noqa: E402
import segment_lacunae_v2 as seg2  # noqa: E402


def sample_line_min(distance: np.ndarray, r0: float, c0: float, r1: float, c1: float, n: int = 50) -> float:
    rows = np.linspace(r0, r1, n)
    cols = np.linspace(c0, c1, n)
    ri = np.clip(np.round(rows).astype(int), 0, distance.shape[0] - 1)
    ci = np.clip(np.round(cols).astype(int), 0, distance.shape[1] - 1)
    return float(distance[ri, ci].min())


def find_splits(image_path: Path) -> list[tuple]:
    # Use segment_image (not watershed_split directly) so this reflects
    # merge_shallow_splits too, not just the raw pre-merge watershed output.
    _display, channel = load_channel(image_path)
    mask, _t_hi = seg2.multiotsu_lacuna_mask(channel)
    distance = ndi.distance_transform_edt(mask)
    components = measure.label(mask, connectivity=2)
    _display2, labels, kept, _t_hi2 = seg2.segment_image(image_path)

    comp_to_kept = defaultdict(list)
    for region, _on_border in kept:
        r0, c0 = region.coords[0]
        comp_id = components[r0, c0]
        comp_to_kept[comp_id].append(region)

    rows = []
    for comp_id, pieces in comp_to_kept.items():
        if len(pieces) != 2:
            if len(pieces) > 2:
                rows.append((image_path.name, int(comp_id), len(pieces), None, None, None, None))
            continue
        a, b = pieces
        mask_a = labels == a.label
        mask_b = labels == b.label
        peak_a = float(distance[mask_a].max())
        peak_b = float(distance[mask_b].max())
        ra, ca = np.unravel_index(np.argmax(np.where(mask_a, distance, -1)), distance.shape)
        rb, cb = np.unravel_index(np.argmax(np.where(mask_b, distance, -1)), distance.shape)
        saddle = sample_line_min(distance, ra, ca, rb, cb)
        ratio = saddle / min(peak_a, peak_b)
        rows.append((image_path.name, int(comp_id), 2, round(peak_a, 1), round(peak_b, 1), round(saddle, 2), round(ratio, 3)))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose lacunae over-split by watershed.")
    parser.add_argument("--dir", type=Path, required=True)
    args = parser.parse_args()

    all_rows = []
    for image_path in sorted(args.dir.glob("*.tif")):
        all_rows.extend(find_splits(image_path))

    print(f"total split components (2-piece): {sum(1 for r in all_rows if r[2] == 2)}")
    print(f"{'image':30s} {'comp':>5s} {'n':>2s} {'peakA':>7s} {'peakB':>7s} {'saddle':>7s} {'ratio':>6s}")
    for r in sorted(all_rows, key=lambda x: (x[-1] is None, x[-1] if x[-1] is not None else -1), reverse=True):
        image, comp_id, n, peak_a, peak_b, saddle, ratio = r
        pa = "n/a" if peak_a is None else f"{peak_a:.1f}"
        pb = "n/a" if peak_b is None else f"{peak_b:.1f}"
        s = "n/a" if saddle is None else f"{saddle:.2f}"
        rt = "n/a" if ratio is None else f"{ratio:.3f}"
        print(f"{image:30s} {comp_id:5d} {n:2d} {pa:>7s} {pb:>7s} {s:>7s} {rt:>6s}")


if __name__ == "__main__":
    main()
