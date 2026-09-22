"""Read-only diagnostics for segment_lacunae_v2 / canaliculi_v1.

1. find_splits / debug_component: watershed over-split investigation
   (saddle depth between distance-transform peaks).
2. attach_gaps: for canaliculi_v1's "graph" assignment method, the
   minimum node-to-lacuna gap distance actually available per lacuna --
   i.e. whether LACUNA_ATTACH_GAP_PX is tight enough to leave some
   lacunae with no attachment point in the skeleton graph.

Does not modify anything -- prints tables only.

Usage:
    python src/diagnose_lacuna_splits.py --dir data/WT
    python src/diagnose_lacuna_splits.py --dir data/WT --debug-component "542 WT  2_z06c1-2.tif" 121
    python src/diagnose_lacuna_splits.py --dir data/WT --attach-gaps
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from skimage import measure, morphology

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from count_lacunae import load_channel  # noqa: E402
import segment_lacunae_v2 as seg2  # noqa: E402
import canaliculi_v1 as can1  # noqa: E402


def sample_line_min(distance: np.ndarray, r0: float, c0: float, r1: float, c1: float, n: int = 50) -> float:
    rows = np.linspace(r0, r1, n)
    cols = np.linspace(c0, c1, n)
    ri = np.clip(np.round(rows).astype(int), 0, distance.shape[0] - 1)
    ci = np.clip(np.round(cols).astype(int), 0, distance.shape[1] - 1)
    return float(distance[ri, ci].min())


def find_splits(image_path: Path) -> list[tuple]:
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


def debug_component(image_path: Path, comp_id: int) -> None:
    _display, channel = load_channel(image_path)
    mask, t_hi = seg2.multiotsu_lacuna_mask(channel)
    distance = ndi.distance_transform_edt(mask)
    components = measure.label(mask, connectivity=2)
    comp_mask = components == comp_id
    print(f"component {comp_id}: area={comp_mask.sum()}")

    labels_pre_merge = seg2.watershed_split(mask)
    raw_pieces = np.unique(labels_pre_merge[comp_mask])
    raw_pieces = raw_pieces[raw_pieces != 0]
    print(f"raw watershed pieces (pre-merge): {len(raw_pieces)}")
    for lbl in raw_pieces:
        area = int((labels_pre_merge == lbl).sum())
        substantial = area >= seg2.TEST_MIN_AREA_PX2
        print(f"  label={lbl} area={area} substantial(>= {seg2.TEST_MIN_AREA_PX2})={substantial}")

    labels_post_merge = seg2.merge_shallow_splits(labels_pre_merge, mask, distance)
    post_pieces = np.unique(labels_post_merge[comp_mask])
    post_pieces = post_pieces[post_pieces != 0]
    print(f"post-merge pieces: {len(post_pieces)} -> labels {post_pieces.tolist()}")
    for lbl in post_pieces:
        area = int((labels_post_merge == lbl).sum())
        print(f"  label={lbl} area={area}")


def attach_gaps_for_image(image_path: Path) -> list[tuple]:
    """For each lacuna, the minimum dist_to_lacuna value among all graph
    nodes (post-prune) whose nearest_id is that lacuna -- i.e. the
    closest attachment point actually available, vs. LACUNA_ATTACH_GAP_PX."""
    display, channel = load_channel(image_path)
    _display2, labels, kept, _t_hi = seg2.segment_image(image_path)

    lacuna_mask, lacuna_id_map = can1.build_lacuna_maps(labels, kept)
    candidate, _t_lo = can1.canaliculi_candidate_mask(channel, lacuna_mask, can1.PREPROCESS_MODE)
    skeleton = morphology.skeletonize(candidate)
    dist_to_lacuna, nearest_id = can1.nearest_lacuna_map(lacuna_id_map)

    G, _skel_obj = can1.build_network_graph(skeleton)
    can1.clean_network_graph(G, dist_to_lacuna)

    rows = []
    for lacuna_id in range(1, len(kept) + 1):
        gaps = [
            float(dist_to_lacuna[r, c])
            for (r, c) in G.nodes()
            if int(nearest_id[r, c]) == lacuna_id
        ]
        min_gap = min(gaps) if gaps else None
        n_candidate_nodes = len(gaps)
        attachable = min_gap is not None and min_gap <= can1.LACUNA_ATTACH_GAP_PX
        rows.append((image_path.name, lacuna_id, n_candidate_nodes, min_gap, attachable))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose lacunae over-split / canaliculi attachment gaps.")
    parser.add_argument("--dir", type=Path, required=True)
    parser.add_argument("--debug-component", nargs=2, metavar=("IMAGE_NAME", "COMP_ID"), default=None)
    parser.add_argument("--attach-gaps", action="store_true")
    args = parser.parse_args()

    if args.debug_component:
        image_name, comp_id = args.debug_component
        debug_component(args.dir / image_name, int(comp_id))
        return

    if args.attach_gaps:
        print(f"LACUNA_ATTACH_GAP_PX = {can1.LACUNA_ATTACH_GAP_PX}")
        print(f"{'image':30s} {'lacuna_id':>9s} {'n_nodes':>7s} {'min_gap':>8s} {'attachable':>10s}")
        n_total = 0
        n_unattachable = 0
        all_gaps = []
        for image_path in sorted(args.dir.glob("*.tif")):
            for row in attach_gaps_for_image(image_path):
                image, lacuna_id, n_nodes, min_gap, attachable = row
                n_total += 1
                if not attachable:
                    n_unattachable += 1
                if min_gap is not None:
                    all_gaps.append(min_gap)
                mg = "n/a" if min_gap is None else f"{min_gap:.2f}"
                print(f"{image:30s} {lacuna_id:9d} {n_nodes:7d} {mg:>8s} {str(attachable):>10s}")
        print(f"\n{n_unattachable}/{n_total} lacunae have NO attachment point within {can1.LACUNA_ATTACH_GAP_PX}px")

        arr = np.array(all_gaps)
        print(f"\nmin_gap distribution (n={arr.size}): min={arr.min():.2f} max={arr.max():.2f} "
              f"mean={arr.mean():.2f} median={np.median(arr):.2f}")
        for p in (50, 75, 90, 95, 99, 100):
            print(f"  p{p:02d} = {np.percentile(arr, p):.2f} px")
        print("  sorted: " + ", ".join(f"{g:.2f}" for g in sorted(all_gaps)))
        return

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
