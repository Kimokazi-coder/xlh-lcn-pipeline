"""READ-ONLY size-bias check for the hybrid roots gate (D8). Changes nothing.

A v3 object is inflated by the r=12 opening that found it. Roots are
counted from skeleton nodes within can.LACUNA_ATTACH_GAP_PX of the BODY,
so a bigger outline reaches further out and can catch threads that merely
pass by. Before letting a roots count override the intensity gate, the two
populations have to be compared on a measure that is not inflated.

Compares, on both raw and size-corrected measures:
  * every v2-KEPT INTERIOR lacuna
  * every v3-ONLY object that passes gates (b) and (c) but FAILS (a) --
    i.e. exactly the objects an override would admit

Measures per object:
    roots            as the hybrid gate counts them, on the full body
    roots/100px      roots per 100 px of perimeter
    core_roots       roots recounted on a body shrunk to v2 scale
                     (intersected with v2's pre-filter pieces where they
                     exist, else eroded to the image's median v2 area)

Usage:
    python diagnostics/lacunae/measure_size_corrected_roots.py --dir data/WT
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from count_lacunae import load_channel  # noqa: E402
import canaliculi_v1 as can  # noqa: E402
import segment_lacunae_hybrid as hyb  # noqa: E402
import segment_lacunae_v2 as seg2  # noqa: E402


def describe(values: np.ndarray, label: str) -> None:
    if values.size == 0:
        print(f"  {label:34s} (none)")
        return
    print(
        f"  {label:34s} n={values.size:4d}  min={values.min():7.3f}  p10={np.percentile(values,10):7.3f}  "
        f"p50={np.percentile(values,50):7.3f}  p90={np.percentile(values,90):7.3f}  max={values.max():7.3f}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Size-bias check for the hybrid roots gate (read-only).")
    parser.add_argument("--dir", type=Path, required=True)
    args = parser.parse_args()

    print("=" * 104)
    print("SIZE-BIAS CHECK for the D8 roots override. v-raw / pre-validation, PIXEL units. Read-only.")
    print("=" * 104)

    v2_rows: list[tuple] = []
    cand_rows: list[tuple] = []

    for image_path in sorted(args.dir.glob("*.tif")):
        state = hyb.evaluate_candidates(image_path)
        _display, channel = load_channel(image_path)
        _d2, v2_labels, v2_kept, _t = seg2.segment_image(image_path)
        lacuna_mask, lacuna_id = can.build_lacuna_maps(v2_labels, v2_kept)
        graph, _flagged = hyb.default_skeleton_graph(image_path, channel, v2_labels, v2_kept)

        interior_areas = [r.area for r, on_border in v2_kept if not on_border]
        target_area = float(np.median(interior_areas)) if interior_areas else 0.0

        for lid, (region, on_border) in enumerate(v2_kept, start=1):
            if on_border:
                continue
            body = lacuna_id == lid
            roots = hyb.count_roots_for_body(graph, body)
            perimeter = hyb.perimeter_of(body)
            core = hyb.core_body(body, v2_labels, target_area)
            v2_rows.append(
                (
                    image_path.stem, float(region.centroid[1]), float(region.centroid[0]),
                    float(region.area), roots,
                    100.0 * roots / perimeter if perimeter > 0 else 0.0,
                    hyb.count_roots_for_body(graph, core), float(core.sum()),
                )
            )

        for candidate in state["candidates"]:
            if candidate["accepted"]:
                continue
            if not (candidate["b_not_flagged"] and candidate["c_connected"]):
                continue
            if candidate["a_bright"]:
                continue
            body = state["v3_labels"] == candidate["label"]
            perimeter = hyb.perimeter_of(body)
            core = hyb.core_body(body, v2_labels, target_area)
            cand_rows.append(
                (
                    image_path.stem, candidate["x"], candidate["y"], candidate["area"],
                    candidate["roots"],
                    100.0 * candidate["roots"] / perimeter if perimeter > 0 else 0.0,
                    hyb.count_roots_for_body(graph, core), float(core.sum()),
                    candidate["relative_intensity"],
                )
            )
        print(f"  processed {image_path.stem}")

    v2_arr = np.array([(r[3], r[4], r[5], r[6], r[7]) for r in v2_rows], dtype=float)
    cd_arr = np.array([(r[3], r[4], r[5], r[6], r[7]) for r in cand_rows], dtype=float)

    print("\n" + "=" * 104)
    print("DISTRIBUTIONS")
    print("=" * 104)
    print("\nv2-KEPT INTERIOR lacunae (the accepted population):")
    describe(v2_arr[:, 0], "body area px^2")
    describe(v2_arr[:, 1], "roots (raw)")
    describe(v2_arr[:, 2], "roots per 100px perimeter")
    describe(v2_arr[:, 3], "CORE roots (size-corrected)")
    describe(v2_arr[:, 4], "core area px^2")

    print("\nv3-ONLY candidates passing (b)+(c) but failing (a) -- what an override would admit:")
    if cd_arr.size:
        describe(cd_arr[:, 0], "body area px^2")
        describe(cd_arr[:, 1], "roots (raw)")
        describe(cd_arr[:, 2], "roots per 100px perimeter")
        describe(cd_arr[:, 3], "CORE roots (size-corrected)")
        describe(cd_arr[:, 4], "core area px^2")
        print(f"\n  size inflation: candidate median body area "
              f"{np.median(cd_arr[:,0]):.0f} px^2 vs v2-kept {np.median(v2_arr[:,0]):.0f} px^2 "
              f"({np.median(cd_arr[:,0])/np.median(v2_arr[:,0]):.2f}x)")
        print(f"  roots shrink under correction: candidates median "
              f"{np.median(cd_arr[:,1]):.1f} -> {np.median(cd_arr[:,3]):.1f} core; "
              f"v2-kept {np.median(v2_arr[:,1]):.1f} -> {np.median(v2_arr[:,3]):.1f} core")
    else:
        print("  (none)")

    print("\n" + "=" * 104)
    print("EVERY CANDIDATE (passes b+c, fails a)")
    print("=" * 104)
    print(
        f'{"image":22s} {"x":>5s} {"y":>5s} {"area":>7s} {"rel_I":>6s} {"roots":>6s} '
        f'{"r/100px":>8s} {"core_r":>7s} {"core_a":>7s}'
    )
    for row in sorted(cand_rows, key=lambda r: (r[0], -r[6])):
        print(
            f'{row[0][:22]:22s} {row[1]:5.0f} {row[2]:5.0f} {row[3]:7.0f} {row[8]:6.3f} '
            f'{row[4]:6d} {row[5]:8.2f} {row[6]:7d} {row[7]:7.0f}'
        )

    print("\n" + "=" * 104)
    print("PER-IMAGE MEDIANS of the v2-kept population (what an override would compare against)")
    print("=" * 104)
    print(f'{"image":22s} {"med roots":>10s} {"med r/100px":>12s} {"med CORE roots":>15s}')
    for stem in sorted({r[0] for r in v2_rows}):
        rows = [r for r in v2_rows if r[0] == stem]
        print(
            f'{stem[:22]:22s} {np.median([r[4] for r in rows]):10.1f} '
            f'{np.median([r[5] for r in rows]):12.2f} {np.median([r[6] for r in rows]):15.1f}'
        )


if __name__ == "__main__":
    main()
