"""READ-ONLY derivation of the D8 override cutoffs. Changes nothing.

Two things have to be settled before an override can be written down:

  * WHICH roots measure. The size-bias check showed the raw count is
    inflated for a v3 object, so three candidate measures are compared
    here against the same per-image v2-kept median.
  * THE INTENSITY FLOOR, below which nothing qualifies however well
    connected it looks, so that pure haze can never be admitted. Derived
    from each image's own background mode rather than picked.

Usage:
    python src/derive_override_cutoffs.py --dir data/WT
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from count_lacunae import load_channel  # noqa: E402
import canaliculi_v1 as can  # noqa: E402
import segment_lacunae_hybrid as hyb  # noqa: E402
import segment_lacunae_v2 as seg2  # noqa: E402

CONFIRM = {"(230,300) 542_z06": ("542 WT  2_z06c1-2", 230, 300),
           "(860,730) 682_z29": ("682_z29c1-3", 860, 730)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Derive the D8 override cutoffs (read-only).")
    parser.add_argument("--dir", type=Path, required=True)
    args = parser.parse_args()

    print("=" * 100)
    print("D8 OVERRIDE CUTOFF DERIVATION. v-raw / pre-validation, PIXEL units. Read-only.")
    print("=" * 100)

    print("\n[1] INTENSITY FLOOR: where is 'pure haze' in relative-intensity units?")
    print("    Each image's raw background MODE, expressed the same way a candidate is")
    print("    (divided by that image's median v2 lacuna intensity). Nothing at or near")
    print("    this level carries signal, so the floor must sit clearly above it.")
    print(f'\n    {"image":22s} {"bg mode":>8s} {"med v2 I":>9s} {"bg / med v2":>12s}')
    floors = []
    per_image = {}
    for image_path in sorted(args.dir.glob("*.tif")):
        _display, channel = load_channel(image_path)
        _d2, v2_labels, v2_kept, _t = seg2.segment_image(image_path)
        intensities = [channel[r.coords[:, 0], r.coords[:, 1]].mean() for r, _ob in v2_kept]
        median_v2 = float(np.median(intensities))
        counts, edges = np.histogram(channel, bins=256, range=(0.0, 1.0))
        background = float(edges[int(np.argmax(counts))])
        ratio = background / median_v2
        floors.append(ratio)
        per_image[image_path.stem] = (median_v2, background, ratio)
        print(f'    {image_path.stem[:22]:22s} {background:8.4f} {median_v2:9.4f} {ratio:12.3f}')
    floors = np.array(floors)
    print(f"\n    background/median across the 8 images: min {floors.min():.3f}  "
          f"max {floors.max():.3f}  mean {floors.mean():.3f}")

    print("\n[2] WHICH ROOTS MEASURE, and what each admits")
    rows = []
    for image_path in sorted(args.dir.glob("*.tif")):
        state = hyb.evaluate_candidates(image_path)
        _display, channel = load_channel(image_path)
        _d2, v2_labels, v2_kept, _t = seg2.segment_image(image_path)
        lacuna_mask, lacuna_id = can.build_lacuna_maps(v2_labels, v2_kept)
        graph, _fl = hyb.default_skeleton_graph(image_path, channel, v2_labels, v2_kept)
        interior = [(r, ob) for r, ob in v2_kept if not ob]
        target_area = float(np.median([r.area for r, _ob in interior])) if interior else 0.0

        med = {"raw": [], "per100": [], "core": []}
        for lid, (_region, on_border) in enumerate(v2_kept, start=1):
            if on_border:
                continue
            body = lacuna_id == lid
            roots = hyb.count_roots_for_body(graph, body)
            perim = hyb.perimeter_of(body)
            med["raw"].append(roots)
            med["per100"].append(100.0 * roots / perim if perim > 0 else 0.0)
            med["core"].append(hyb.count_roots_for_body(graph, hyb.core_body(body, v2_labels, target_area)))
        medians = {k: float(np.median(v)) for k, v in med.items()}

        for candidate in state["candidates"]:
            if candidate["accepted"] or candidate["a_bright"]:
                continue
            if not (candidate["b_not_flagged"] and candidate["c_connected"]):
                continue
            body = state["v3_labels"] == candidate["label"]
            perim = hyb.perimeter_of(body)
            core = hyb.core_body(body, v2_labels, target_area)
            rows.append(
                {
                    "image": image_path.stem, "x": candidate["x"], "y": candidate["y"],
                    "area": candidate["area"], "rel_I": candidate["relative_intensity"],
                    "raw": candidate["roots"],
                    "per100": 100.0 * candidate["roots"] / perim if perim > 0 else 0.0,
                    "core": hyb.count_roots_for_body(graph, core),
                    "core_area": float(core.sum()),
                    "med_raw": medians["raw"], "med_per100": medians["per100"],
                    "med_core": medians["core"],
                }
            )

    for measure_name, key, medkey in (
        ("raw roots (INFLATED, for reference)", "raw", "med_raw"),
        ("roots per 100px perimeter", "per100", "med_per100"),
        ("CORE roots (size-corrected)", "core", "med_core"),
    ):
        passing = [r for r in rows if r[key] >= r[medkey]]
        print(f"\n    {measure_name}: {len(passing)} of {len(rows)} candidates reach their image median")
        for target, (stem, tx, ty) in CONFIRM.items():
            hit = [r for r in rows if r["image"] == stem and np.hypot(r["x"] - tx, r["y"] - ty) < 40]
            if hit:
                r = hit[0]
                print(f'        {target}: {r[key]:.2f} vs median {r[medkey]:.2f} -> '
                      f'{"PASSES" if r[key] >= r[medkey] else "FAILS"}')
            else:
                print(f"        {target}: not in this candidate set (already accepted by the base gates)")

    print("\n[3] CANDIDATES PASSING THE CORE-ROOTS CRITERION (before any intensity floor)")
    print(f'    {"image":22s} {"x":>5s} {"y":>5s} {"area":>7s} {"rel_I":>6s} '
          f'{"core_r":>7s} {"med":>5s} {"core_a":>7s}')
    for r in sorted([r for r in rows if r["core"] >= r["med_core"]], key=lambda r: (r["image"], -r["core"])):
        print(f'    {r["image"][:22]:22s} {r["x"]:5.0f} {r["y"]:5.0f} {r["area"]:7.0f} '
              f'{r["rel_I"]:6.3f} {r["core"]:7d} {r["med_core"]:5.1f} {r["core_area"]:7.0f}')

    print("\n[4] EFFECT OF AN INTENSITY FLOOR on that set")
    passing = [r for r in rows if r["core"] >= r["med_core"]]
    if passing:
        arr = np.array([r["rel_I"] for r in passing])
        print(f"    their relative intensities: min {arr.min():.3f}  p50 {np.median(arr):.3f}  max {arr.max():.3f}")
        for floor in (0.30, 0.35, 0.40, 0.45, 0.50):
            print(f"      floor {floor:.2f} -> {int((arr >= floor).sum())} of {len(arr)} survive")


if __name__ == "__main__":
    main()
