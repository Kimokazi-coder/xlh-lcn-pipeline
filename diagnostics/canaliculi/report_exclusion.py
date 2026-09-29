"""READ-ONLY Phase 1 report on the exclusion mask. Changes nothing.

For every image in a directory, builds the exclusion that
exclusion_mask.py would apply and reports what it costs and what it
catches:

  * excluded area (px^2 and % of field), and how much the lacuna safety
    margin suppressed
  * every object the shape gate flagged, with the numbers it was judged on
  * whether ANY excluded pixel lies inside the lacuna safety margin --
    this must be zero, and is the check the brief asks for
  * whether the object at (555,140) in 542_z06 falls inside the exclusion
    (reported only; nothing is removed from the lacuna list)
  * the canaliculi-mask and skeleton density INSIDE each flagged structure
    against the density outside it, which is the evidence for whether
    excluding it would remove non-LCN signal or ordinary canaliculi

Usage:
    python diagnostics/canaliculi/report_exclusion.py --dir data/WT
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from skimage import morphology

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from count_lacunae import load_channel  # noqa: E402
import canaliculi_v1 as can  # noqa: E402
import exclusion_mask as excl  # noqa: E402
import segment_lacunae_v2 as seg2  # noqa: E402

# The kept object the user asked to be checked against the exclusion, as
# (x=col, y=row) in Fiji's convention. Reported only -- Phase 1 does not
# touch the lacuna list.
CHECK_POINT_542_Z06 = (555, 140)

TUNING_IMAGE_STEMS = ("542 WT  2_z06c1-2", "543-2", "682_z29c1-3")

REPORT_DIR = config.DIAGNOSTICS_DIR / "phase1"


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 1 exclusion-mask report (read-only).")
    parser.add_argument("--dir", type=Path, required=True)
    parser.add_argument("--mode", default="auto", choices=list(excl.VALID_MODES))
    args = parser.parse_args()

    print("=" * 104)
    print(f"PHASE 1 EXCLUSION REPORT -- mode={args.mode}, v1-raw / pre-validation, PIXEL units. Read-only.")
    print(
        f"span gate >= {excl.EXCLUSION_MIN_SPAN_FRACTION}  major axis gate >= "
        f"{excl.EXCLUSION_MIN_MAJOR_AXIS_PX:.0f}px  safety margin {excl.LACUNA_SAFETY_MARGIN_PX}px  "
        f"dilation {excl.EXCLUSION_DILATION_PX}px"
    )
    print("=" * 104)
    print(
        f'{"image":22s} {"set":9s} {"excl px2":>10s} {"excl %":>7s} {"flagged px2":>12s} '
        f'{"suppressed":>11s} {"protected %":>12s} {"VIOLATIONS":>11s}'
    )

    violations_total = 0
    detail = []
    for path in sorted(args.dir.glob("*.tif")):
        display, channel = load_channel(path)
        _d2, labels, kept, _t_hi = seg2.segment_image(path)
        exclusion, info = excl.build_exclusion(path, channel, labels, args.mode)

        tag = "tuning" if path.stem in TUNING_IMAGE_STEMS else "held-out"
        violations = int(info["excluded_inside_safety_margin_px2"])
        violations_total += violations
        print(
            f'{path.stem[:22]:22s} {tag:9s} {info["excluded_area_px2"]:10.0f} '
            f'{100 * info["excluded_fraction"]:6.2f}% {info.get("flagged_area_px2", 0.0):12.0f} '
            f'{info.get("suppressed_by_margin_px2", 0.0):11.0f} '
            f'{100 * info.get("protected_fraction", 0.0):11.1f}% {violations:11d}'
        )
        detail.append((path, display, channel, labels, kept, exclusion, info))

    print(f'\nTOTAL pixels excluded inside the lacuna safety margin: {violations_total}  '
          f'(must be 0){"  OK" if violations_total == 0 else "  *** CONSTRAINT VIOLATED ***"}')

    print("\n" + "=" * 104)
    print("OBJECTS FLAGGED BY THE SHAPE GATE")
    print("=" * 104)
    print(f'{"image":22s} {"area px2":>10s} {"major px":>9s} {"aspect":>7s} {"span":>6s} {"centroid (x,y)":>16s}')
    n_objects = 0
    for path, _d, _c, _l, _k, _e, info in detail:
        for obj in info.get("objects", []):
            n_objects += 1
            centroid = "({:.0f},{:.0f})".format(obj["centroid_col"], obj["centroid_row"])
            print(
                f'{path.stem[:22]:22s} {obj["area_px2"]:10.0f} {obj["major_axis_px"]:9.1f} '
                f'{obj["aspect"]:7.2f} {obj["span_fraction"]:6.3f} {centroid:>16s}'
            )
    if n_objects == 0:
        print("  (none)")

    print("\n" + "=" * 104)
    print("WOULD EXCLUDING THESE REMOVE NON-LCN SIGNAL, OR ORDINARY CANALICULI?")
    print("=" * 104)
    print("Canaliculi-mask and skeleton density inside each flagged structure vs outside it.")
    print("A ratio near 1 means the structure carries network at the same density as the rest of")
    print("the field, i.e. the top-hat already suppressed the structure itself and excluding it")
    print("would mostly delete real canaliculi.")
    print(f'\n{"image":22s} {"mask in":>9s} {"mask out":>9s} {"ratio":>7s} {"skel in":>9s} {"skel out":>9s} {"ratio":>7s}')
    for path, _d, channel, labels, kept, exclusion, info in detail:
        if not info.get("objects"):
            continue
        lacuna_mask, _lid = can.build_lacuna_maps(labels, kept)
        candidate, _t = can.canaliculi_candidate_mask(channel, lacuna_mask, can.PREPROCESS_MODE)
        skeleton = morphology.skeletonize(candidate)
        # The structure itself, before the safety margin carved it up --
        # the question is about the structure, not about what survives.
        flagged, _fi = excl.auto_exclusion(channel, labels)
        core = flagged | (exclusion & ~flagged)
        outside = ~core & ~lacuna_mask
        if core.sum() == 0 or outside.sum() == 0:
            continue
        mi, mo = candidate[core].mean(), candidate[outside].mean()
        si, so = skeleton[core].mean(), skeleton[outside].mean()
        print(
            f'{path.stem[:22]:22s} {mi:9.4f} {mo:9.4f} {mi / mo:7.2f} '
            f'{si:9.4f} {so:9.4f} {si / so:7.2f}'
        )

    print("\n" + "=" * 104)
    print(f"NAMED CHECK: the kept object at {CHECK_POINT_542_Z06} in 542_z06 (reported only, not removed)")
    print("=" * 104)
    for path, _d, _c, labels, kept, exclusion, _info in detail:
        if path.stem != "542 WT  2_z06c1-2":
            continue
        x, y = CHECK_POINT_542_Z06
        lacuna_mask, lacuna_id_map = can.build_lacuna_maps(labels, kept)
        best, best_d = None, None
        for lacuna_id, (region, on_border) in enumerate(kept, start=1):
            d = np.hypot(region.centroid[1] - x, region.centroid[0] - y)
            if best_d is None or d < best_d:
                best, best_d = (lacuna_id, region, on_border), d
        lacuna_id, region, on_border = best
        body = lacuna_id_map == lacuna_id
        overlap = float(exclusion[body].mean()) if body.any() else 0.0
        print(
            f'  nearest kept lacuna id={lacuna_id} at '
            f'({region.centroid[1]:.0f},{region.centroid[0]:.0f}), {best_d:.0f}px from the named point'
        )
        print(f'  area={region.area:.0f}px2  on_border={on_border}')
        print(f'  fraction of its body inside the exclusion: {100 * overlap:.2f}%')
        print(
            "  -> "
            + (
                "INSIDE the exclusion region."
                if overlap > 0
                else "NOT inside the exclusion region (the safety margin protects it)."
            )
        )
    print("=" * 104)


if __name__ == "__main__":
    main()
