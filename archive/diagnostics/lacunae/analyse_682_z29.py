"""READ-ONLY follow-up analysis on 682_z29c1-3 and the root-sparsity
question. Changes nothing; writes only a verification overlay under the
usual comparison-run location.

WHICH IMAGE, AND HOW IT WAS IDENTIFIED. The three lacunae named in the
request were located by searching all 8 WT images for kept lacunae near
each coordinate. 682_z29c1-3 matches on every count: the two outlined
cells sit 4 px from a v2-kept centroid each, 13 of its 13 kept lacunae are
horizontally elongated (so canaliculi run mostly vertically, as described),
and no kept lacuna lies within 201 px of the third coordinate, consistent
with it being unoutlined. The nearest competing field, 682_z23c-2, has a
kept lacuna only 10 px from that third coordinate, so it would have been
outlined there.

Sections:
  (a) roots and 30 px ring skeleton length per interior lacuna
  (b) the unoutlined object: in v2? in v3? does hybrid add it, and if not
      which gate rejected it, with the numbers
  (c) the Step 5 sparsity question re-done with a RELATIVE criterion
      instead of the absolute "< 3 roots"
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from count_lacunae import load_channel  # noqa: E402
import canaliculi_v1 as can  # noqa: E402
import exclusion_mask as excl  # noqa: E402
import gap_bridging as gb  # noqa: E402
import segment_lacunae_v2 as seg2  # noqa: E402
import segment_lacunae_v3_candidate as v3  # noqa: E402
import segment_lacunae_hybrid as hyb  # noqa: E402
from skimage import measure, morphology  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

TARGET = "682_z29c1-3"

# Width (px) of the band just outside a lacuna body in which canalicular
# skeleton length is measured. Same 30 px used in the earlier Step 5
# measurement, kept so the two are comparable.
RING_PX = 30

# The coordinates from the request, as (x=col, y=row).
NAMED = {"A": (490, 530), "B": (765, 905), "C_unoutlined": (860, 730)}

# How close a kept object has to be to count as "the same object".
MATCH_RADIUS_PX = 40

# (c) A lacuna is flagged as root-sparse if it falls below this fraction of
# its OWN image's median, on either measure. Relative rather than absolute
# because median roots per lacuna varies 5.0-9.0 across the 8 fields, so a
# fixed "< 3" means something different in a dense field than a sparse one.
# 0.5 is a plain "less than half the typical lacuna in its own field" --
# an INITIAL VALUE, NOT TUNED, chosen to be interpretable rather than
# fitted, since there is no ground truth to fit it against.
SPARSE_FRACTION = 0.5


def default_network(image_path: Path):
    """The CURRENT default canaliculi skeleton and its attached graph."""
    display, channel = load_channel(image_path)
    _d2, labels, kept, _t = seg2.segment_image(image_path)
    lacuna_mask, lacuna_id = can.build_lacuna_maps(labels, kept)
    flagged, _objs = excl.flagged_structures(channel)
    no_growth = flagged if can.BLOCK_GROWTH_IN_FLAGGED else None
    candidate, t_lo = can.canaliculi_candidate_mask(
        channel, lacuna_mask, can.PREPROCESS_MODE, can.THRESHOLD_MODE, no_growth
    )
    skeleton = morphology.skeletonize(candidate)
    if can.GAP_BRIDGING:
        bridges = gb.find_bridges(
            skeleton, can.preprocess_channel(channel, can.PREPROCESS_MODE),
            t_lo, lacuna_mask | flagged,
        )
        if bridges:
            skeleton = morphology.skeletonize(gb.apply_bridges(candidate, bridges))
    distance = ndi.distance_transform_edt(lacuna_mask == 0)
    graph, _skel = can.build_network_graph(skeleton)
    can.clean_network_graph(graph, distance)
    can.attach_lacunae(
        graph, distance, can.nearest_lacuna_map(lacuna_id)[1], list(range(1, len(kept) + 1))
    )
    return display, channel, labels, kept, lacuna_id, skeleton, graph


def per_lacuna(kept, lacuna_id, skeleton, graph):
    """Per lacuna: (id, on_border, roots, skeleton px in the 30 px ring)."""
    rows = []
    for lid, (_region, on_border) in enumerate(kept, start=1):
        body = lacuna_id == lid
        ring = (ndi.distance_transform_edt(~body) <= RING_PX) & ~body
        rows.append((lid, on_border, len(can.cell_root_lengths(graph, lid)), int(skeleton[ring].sum())))
    return rows


def v2_verdict(region, rows: int, cols: int) -> str:
    """Which of v2's filters rejects this object first, or KEPT. Mirrors
    segment_lacunae_v2.filter_regions' order."""
    if region.area < seg2.TEST_MIN_AREA_PX2:
        return f"REJECTED area {region.area:.0f} < {seg2.TEST_MIN_AREA_PX2}"
    if region.area > seg2.TEST_MAX_AREA_FRACTION_OF_IMAGE * rows * cols:
        return "REJECTED area > max fraction"
    if region.solidity < seg2.TEST_MIN_SOLIDITY:
        return f"REJECTED solidity {region.solidity:.3f} < {seg2.TEST_MIN_SOLIDITY}"
    minor, major = region.axis_minor_length, region.axis_major_length
    aspect = (major / minor) if minor > 0 else float("inf")
    if aspect > seg2.TEST_ASPECT_RATIO_MAX:
        return f"REJECTED aspect {aspect:.2f} > {seg2.TEST_ASPECT_RATIO_MAX}"
    return "KEPT"


def main() -> None:
    print("=" * 100)
    print(f"FOLLOW-UP on {TARGET} -- CURRENT DEFAULT. v-raw / pre-validation, PIXEL units. Read-only.")
    print("=" * 100)

    path = Path(f"data/WT/{TARGET}.tif")
    _display, channel, labels, kept, lacuna_id, skeleton, graph = default_network(path)
    rows = per_lacuna(kept, lacuna_id, skeleton, graph)
    interior = [r for r in rows if not r[1]]
    median_roots = float(np.median([r[2] for r in interior]))
    median_ring = float(np.median([r[3] for r in interior]))

    print(f"\n(a) roots and {RING_PX}px-ring skeleton length per INTERIOR lacuna")
    print(f"    image median roots = {median_roots:.1f}    image median ring skeleton = {median_ring:.0f} px")
    print(f'    {"id":>3s} {"x":>5s} {"y":>5s} {"roots":>6s} {"/med":>6s} {"ring_px":>8s} {"/med":>6s}  note')
    for lid, on_border, roots, ring in rows:
        if on_border:
            continue
        region = kept[lid - 1][0]
        x, y = region.centroid[1], region.centroid[0]
        note = ""
        for name, (tx, ty) in NAMED.items():
            if np.hypot(x - tx, y - ty) < MATCH_RADIUS_PX:
                note = f"<- {name}"
        print(
            f'    {lid:3d} {x:5.0f} {y:5.0f} {roots:6d} {roots / median_roots:6.2f} '
            f'{ring:8d} {ring / median_ring:6.2f}  {note}'
        )
    n_border = sum(1 for r in rows if r[1])
    print(f"    ({n_border} border lacunae excluded; {len(interior)} interior)")

    # --- (b) ---
    cx, cy = NAMED["C_unoutlined"]
    print(f"\n(b) the unoutlined dim elongated object at ~({cx},{cy})")
    image_rows, image_cols = labels.shape
    pre_regions = measure.regionprops(labels, intensity_image=channel)
    near_pre = [
        r for r in pre_regions
        if np.hypot(r.centroid[1] - cx, r.centroid[0] - cy) < MATCH_RADIUS_PX
    ]
    if not near_pre:
        nearest = min(pre_regions, key=lambda r: np.hypot(r.centroid[1] - cx, r.centroid[0] - cy))
        d = np.hypot(nearest.centroid[1] - cx, nearest.centroid[0] - cy)
        print(f"    v2 pre-filter mask: NOTHING within {MATCH_RADIUS_PX}px "
              f"(nearest object {d:.0f}px away). It never reached v2's t_hi cut.")
    else:
        for r in sorted(near_pre, key=lambda r: -r.area):
            minor, major = r.axis_minor_length, r.axis_major_length
            print(f"    v2 pre-filter object at ({r.centroid[1]:.0f},{r.centroid[0]:.0f}) "
                  f"area={r.area:.0f} mean_I={r.intensity_mean:.3f} solidity={r.solidity:.3f} "
                  f"aspect={(major/minor if minor>0 else np.inf):.2f}")
            print(f"        -> {v2_verdict(r, image_rows, image_cols)}")

    _d3, v3_labels, v3_kept, _t3 = v3.segment_image(path)
    near_v3 = [
        rk for rk in v3_kept
        if np.hypot(rk[0].centroid[1] - cx, rk[0].centroid[0] - cy) < MATCH_RADIUS_PX
    ]
    if near_v3:
        for region, _ob in near_v3:
            print(f"    v3: KEPT object at ({region.centroid[1]:.0f},{region.centroid[0]:.0f}) "
                  f"area={region.area:.0f} solidity={region.solidity:.3f}")
    else:
        print(f"    v3: nothing kept within {MATCH_RADIUS_PX}px either.")

    state = hyb.evaluate_candidates(path)
    near_cands = [
        c for c in state["candidates"]
        if np.hypot(c["x"] - cx, c["y"] - cy) < MATCH_RADIUS_PX
    ]
    if not near_cands:
        print("    hybrid: not even a candidate -- hybrid only ever considers v3-ONLY objects,")
        print("            so if v3 did not keep it, hybrid cannot add it.")
    for c in near_cands:
        print(f'    hybrid candidate at ({c["x"]:.0f},{c["y"]:.0f}) area={c["area"]:.0f}:')
        print(f'        (a) relative intensity {c["relative_intensity"]:.3f} '
              f'(needs >= {hyb.MIN_RELATIVE_INTENSITY}) -> {"PASS" if c["a_bright"] else "REJECT"}')
        print(f'        (b) flagged-overlap {c["on_flagged_fraction"]:.3f} '
              f'(needs 0) -> {"PASS" if c["b_not_flagged"] else "REJECT"}')
        print(f'        (c) roots {c["roots"]} '
              f'(needs >= {hyb.MIN_ROOTS}) -> {"PASS" if c["c_connected"] else "REJECT"}')
        print(f'        ACCEPTED BY HYBRID: {c["accepted"]}')

    # --- (c) ---
    print(f"\n(c) RELATIVE sparsity criterion across all 8 images")
    print(f"    flag a lacuna if roots < {SPARSE_FRACTION} x its image's median roots,")
    print(f"    OR ring skeleton length < {SPARSE_FRACTION} x its image's median ring length")
    print(f'\n    {"image":22s} {"n_int":>5s} {"med_roots":>9s} {"med_ring":>9s} '
          f'{"by roots":>9s} {"by ring":>8s} {"EITHER":>7s}')
    total = flagged_total = 0
    for image_path in sorted(Path("data/WT").glob("*.tif")):
        _d, _c, _l, kept_q, lacuna_id_q, skeleton_q, graph_q = default_network(image_path)
        rows_q = [r for r in per_lacuna(kept_q, lacuna_id_q, skeleton_q, graph_q) if not r[1]]
        if not rows_q:
            continue
        med_r = float(np.median([r[2] for r in rows_q]))
        med_g = float(np.median([r[3] for r in rows_q]))
        by_roots = sum(1 for r in rows_q if r[2] < SPARSE_FRACTION * med_r)
        by_ring = sum(1 for r in rows_q if r[3] < SPARSE_FRACTION * med_g)
        either = sum(
            1 for r in rows_q
            if r[2] < SPARSE_FRACTION * med_r or r[3] < SPARSE_FRACTION * med_g
        )
        total += len(rows_q)
        flagged_total += either
        print(f'    {image_path.stem[:22]:22s} {len(rows_q):5d} {med_r:9.1f} {med_g:9.0f} '
              f'{by_roots:9d} {by_ring:8d} {either:7d}')
    print(f'\n    POOLED: {flagged_total} of {total} interior lacunae flagged '
          f'({100 * flagged_total / total:.1f}%).')
    print(f'    For comparison, the absolute "< 3 roots" rule flagged 1 of {total} (1.2%).')

    can.process(path, output_suffix="_round2-step5b")
    print(f"\nverification overlay: results/canaliculi/{TARGET}/all_method_results/"
          "verification_round2-step5b.png")


if __name__ == "__main__":
    main()
