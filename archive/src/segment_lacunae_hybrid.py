"""CANDIDATE hybrid lacuna detection. v-RAW, pre-validation, NOT default.

v2 detects lacunae by BRIGHTNESS and misses real but dimmer ones -- the
clearest case being the obliquely sectioned lacuna at (230,300) in 542_z06,
which v2 finds but then rejects on solidity 0.452 because a thin curved
body has low solidity by geometry. v3 detects by BREADTH and recovers it,
but also adds 122 objects across the 8 WT images that are half as bright as
real lacunae, some of them sitting on the vascular canal.

This module keeps EVERY v2 lacuna and adds a v3-only object only when all
three of the tests below pass. It imports v2 and v3 rather than copying
them, so it inherits their behaviour exactly and adds only the gate.

    (a) BRIGHT ENOUGH, relative to this image's own lacunae
    (b) NOT on a flagged non-LCN structure
    (c) HAS CANALICULI RADIATING FROM IT   <- the load-bearing test

Test (c) is the one that carries the argument. A real osteocyte lacuna is
the hub of a canalicular tree; out-of-focus haze and a vascular canal edge
are not, however bright or lacuna-shaped they look. Brightness alone cannot
separate a dim real lacuna from bright haze, and shape alone cannot either
-- connectivity can.

STATUS: nothing here is validated. canaliculi_v1.LACUNA_SOURCE defaults to
"v2"; this module is reached only when that is explicitly overridden.
Whether a lacuna lying partly outside the focal plane should be counted at
all remains a scientific decision that this module does not make -- it only
makes the candidates visible and testable.

Usage:
    python src/segment_lacunae_hybrid.py --dir data/WT
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from skimage import measure, morphology, segmentation
from skimage.io import imsave

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from count_lacunae import load_channel  # noqa: E402
import canaliculi_v1 as can  # noqa: E402
import exclusion_mask as excl  # noqa: E402
import segment_lacunae_v2 as seg2  # noqa: E402
import segment_lacunae_v3_candidate as v3  # noqa: E402

# --- (a) Brightness gate --------------------------------------------------
# A v3-only object is admitted only if its mean raw intensity is at least
# this fraction of THIS IMAGE'S median v2-kept lacuna intensity. Relative,
# not absolute, because absolute brightness varies between fields (median
# v2 lacuna intensity runs 0.744 to 0.940 across the 8 WT images) and an
# absolute cut would behave differently in a dim field than a bright one --
# exactly the sensitivity v3 was meant to remove.
#
# PROVENANCE. Measured on all 8 WT images, each object's mean intensity
# divided by its own image's median v2 lacuna intensity:
#     v2-kept  (n=98):  min 0.823, p05 0.845, p10 0.883
#     v3-only  (n=122): p50 0.474, p90 0.532, MAX 0.783
# The two populations do not overlap at all: the brightest v3-only object
# (0.783) is dimmer than the faintest accepted lacuna (0.823). 0.75 sits
# below that gap, so it costs no v2 lacuna anything, while sitting far
# above the v3-only bulk (p90 = 0.532). It admits only the small bright
# tail -- in practice a couple of objects in 542_z06, including (230,300)
# at 0.783, which is the case this module exists for.
#
# Note what this implies: a cut anywhere in (0.783, 0.823) would reject
# EVERY v3-only object and make the module a no-op. 0.75 is deliberately
# just below the gap so the bright tail survives to be judged by test (c).
MIN_RELATIVE_INTENSITY = 0.75

# --- (c) Connectivity gate ------------------------------------------------
# A v3-only object is admitted only if at least this many distinct
# canalicular roots attach to it, counted exactly as COUNT_MODE="roots"
# counts them for a real lacuna (skeleton branches attaching within
# can.LACUNA_ATTACH_GAP_PX, single-linkage merged below
# can.ROOT_MERGE_DIST_PX) on the CURRENT DEFAULT canaliculi mask.
#
# PROVENANCE. Roots on the 86 v2-kept INTERIOR lacunae across the 8 WT
# images, under the current default mask: min 2, p05 4.0, p10 4.0, p25 5.0,
# median 7.0. N = 4 is the pooled p10, so an added object must be as
# well-connected as 90% of already-accepted lacunae.
#
# This deliberately errs toward NOT adding. Two of the 86 real lacunae have
# fewer than 4 roots and would fail this test, so it is not a test of
# "is a lacuna" -- it is a test of "is well enough connected that calling it
# a lacuna does not rest on brightness alone". For an ADD criterion, a false
# negative costs one missed object while a false positive contaminates the
# count, so the asymmetry is on purpose. Step 5 examines the lacunae with
# few roots as a separate problem.
MIN_ROOTS = 4

# --- D8 override: strong connectivity can outvote the intensity gate -----
# A v3-only object that FAILS gate (a) is still admitted if it is
# exceptionally well connected. Gate (a) was shown to reject objects with
# more canaliculi radiating from them than the typical accepted lacuna in
# their own field, which is the failure gate (c) exists to prevent.
#
# OFF since 2026-09-29, on the D9 finding in docs/DECISIONS_NEEDED.md: of
# four override additions examined by eye, three were dense canalicular mesh
# with no lacuna body. "Roots" counts threads passing near an object, not
# threads ending at it, so a point in dense mesh scores like a hub. With this
# False, hybrid admits only objects passing all three gates (2 on the WT set).
# The code path is kept so the D9 comparison stays reproducible.
OVERRIDE_ON_ROOTS = False

# WHICH roots measure the override uses. This is the load-bearing choice,
# because the three available measures disagree sharply -- of 80 candidates
# that pass (b) and (c) but fail (a), the number reaching their image's
# v2-kept median is:
#     raw roots            42/80   INFLATED, see below
#     roots per 100px      79/80   admits almost everything, no discrimination
#     CORE roots           27/80   size-corrected
#
# Raw roots are inflated for a v3 object: roots are counted from skeleton
# nodes within can.LACUNA_ATTACH_GAP_PX of the BODY, so a larger outline
# reaches further out and catches threads that merely pass by. Roots per
# 100 px of perimeter over-corrects in the opposite direction -- candidates
# are SMALLER than v2 lacunae (median body 1018 vs 2174 px^2), so dividing
# by a smaller perimeter pushes them above the median almost automatically,
# which is why it admits 79 of 80 and discriminates nothing.
#
# CORE roots is the direct correction: recount on a body shrunk to v2
# scale (see core_body). Applied identically to the v2-kept population,
# where it is a no-op, so the two distributions stay comparable.
OVERRIDE_ROOTS_MEASURE = "core"

# Intensity floor for the override. However well connected an object looks,
# nothing at haze level may be admitted.
#
# PROVENANCE. Each image's raw background MODE, expressed the way a
# candidate's relative intensity is (divided by that image's median v2
# lacuna intensity), across the 8 WT images: min 0.096, mean 0.215,
# MAX 0.333. That maximum is what "pure haze" looks like in the worst
# field. 0.40 is 1.20x it, so nothing at or near background level can
# qualify anywhere in this dataset. It is not a free parameter fitted to
# admit a particular object: it is pinned to the measured background.
#
# It does bite. Of the 27 candidates clearing the core-roots criterion,
# two sit at 0.336 and 0.338 -- essentially AT the worst image's background
# level -- and this floor removes them along with five others, leaving 20.
OVERRIDE_MIN_RELATIVE_INTENSITY = 0.40

HYBRID_DIR = config.CANDIDATES_DIR / "lacunae_hybrid"


# --- Size correction for the roots count ---------------------------------
# A v3 object is inflated by the r=12 opening that found it, and roots are
# counted from skeleton nodes within can.LACUNA_ATTACH_GAP_PX of the BODY.
# A larger outline therefore reaches further out and can touch threads that
# merely pass by, inflating its roots relative to a v2-sized lacuna. Any
# comparison of a v3 object's roots against the v2-kept population has to
# correct for that or it compares two different measurements.
#
# Two corrections are computed, and both are reported:
#   (i)  roots per 100 px of perimeter -- normalises by how much boundary
#        there is for a thread to attach to.
#   (ii) roots recounted on a CORE body shrunk to v2 scale, which is the
#        more direct correction: it asks what the roots count would have
#        been if the object had been outlined the way v2 outlines a lacuna.
# Both are applied identically to the v2-kept population, so the two
# distributions stay comparable.


def core_body(body: np.ndarray, v2_prefilter_labels: np.ndarray, target_area: float) -> np.ndarray:
    """Shrink an object to v2 scale, for a like-for-like roots count.

    Preferred route: intersect with whatever v2's PRE-FILTER mask found
    inside it. That is the most faithful correction available, because it
    uses v2's own idea of where the object's body is -- for the (860,730)
    object in 682_z29, v2 found two pieces of 346 and 229 px^2 inside a
    2756 px^2 v3 outline, and those pieces ARE the v2-scale body.

    Fallback, when v2 found nothing inside: erode until the area drops to
    `target_area`, the median v2-kept lacuna area in that image. Erosion is
    isotropic so it shrinks the outline without moving its centre."""
    from skimage import morphology as morph

    inside = v2_prefilter_labels[body]
    present = [lab for lab in np.unique(inside) if lab != 0]
    if present:
        core = np.isin(v2_prefilter_labels, present) & body
        if core.any():
            return core

    if body.sum() <= target_area:
        return body
    core = body
    for radius in range(1, 31):
        eroded = morph.erosion(body, morph.disk(radius))
        if not eroded.any():
            break
        core = eroded
        if core.sum() <= target_area:
            break
    return core


def perimeter_of(body: np.ndarray) -> float:
    """Perimeter in px of a boolean body, via regionprops."""
    props = measure.regionprops(body.astype(int))
    return float(props[0].perimeter) if props else 0.0


def count_roots_for_body(G, body: np.ndarray) -> int:
    """Distinct canalicular roots attaching to one object.

    Mirrors canaliculi_v1.cell_root_lengths: skeleton graph nodes within
    LACUNA_ATTACH_GAP_PX of the body, single-linkage clustered below
    ROOT_MERGE_DIST_PX so one thick thread meeting the boundary over
    several nodes counts once. Written here rather than reused because
    cell_root_lengths works off the virtual cell nodes that attach_lacunae
    adds, and these candidates are not in that graph."""
    if not body.any() or G.number_of_nodes() == 0:
        return 0
    from scipy import ndimage as ndi

    distance = ndi.distance_transform_edt(~body)
    points = [
        n
        for n in G.nodes()
        if not can._is_cell_node(n) and distance[n[0], n[1]] <= can.LACUNA_ATTACH_GAP_PX
    ]
    if not points:
        return 0

    unmerged = list(points)
    clusters = 0
    while unmerged:
        seed = unmerged.pop()
        cluster = [seed]
        changed = True
        while changed:
            changed = False
            for other in list(unmerged):
                if any(
                    np.hypot(other[0] - m[0], other[1] - m[1]) <= can.ROOT_MERGE_DIST_PX
                    for m in cluster
                ):
                    cluster.append(other)
                    unmerged.remove(other)
                    changed = True
        clusters += 1
    return clusters


def default_skeleton_graph(image_path: Path, channel: np.ndarray, v2_labels, v2_kept):
    """The CURRENT DEFAULT canaliculi skeleton graph, built from the v2
    lacuna mask. Test (c) is measured against this, not against a mask
    rebuilt per candidate, so every candidate is judged on the same network
    the pipeline actually produces."""
    lacuna_mask, _lid = can.build_lacuna_maps(v2_labels, v2_kept)
    flagged, _objs = excl.flagged_structures(channel) if can.BLOCK_GROWTH_IN_FLAGGED else (None, None)
    candidate, t_lo = can.canaliculi_candidate_mask(
        channel, lacuna_mask, can.PREPROCESS_MODE, can.THRESHOLD_MODE, flagged
    )
    skeleton = morphology.skeletonize(candidate)
    if can.GAP_BRIDGING:
        import gap_bridging as gb

        forbidden = lacuna_mask if flagged is None else (lacuna_mask | flagged)
        bridges = gb.find_bridges(
            skeleton, can.preprocess_channel(channel, can.PREPROCESS_MODE), t_lo, forbidden
        )
        if bridges:
            skeleton = morphology.skeletonize(gb.apply_bridges(candidate, bridges))
    G, _skel = can.build_network_graph(skeleton)
    from scipy import ndimage as ndi

    can.clean_network_graph(G, ndi.distance_transform_edt(lacuna_mask == 0))
    return G, flagged


def evaluate_candidates(image_path: Path) -> dict:
    """Test every v3-only object against (a), (b) and (c). Returns the
    verdicts and the numbers behind them, so a rejection can be checked."""
    display, channel = load_channel(image_path)
    _d2, v2_labels, v2_kept, t_hi = seg2.segment_image(image_path)
    _d3, v3_labels, v3_kept, _t3 = v3.segment_image(image_path)

    comparison = v3.compare_to_v2(image_path)
    v3_only_keys = {(round(e["x"], 1), round(e["y"], 1)) for e in comparison["v3_only"]}

    v2_intensities = np.array(
        [channel[r.coords[:, 0], r.coords[:, 1]].mean() for r, _ob in v2_kept]
    )
    median_v2 = float(np.median(v2_intensities)) if v2_intensities.size else 0.0

    G, flagged = default_skeleton_graph(image_path, channel, v2_labels, v2_kept)
    if flagged is None:
        flagged, _objs = excl.flagged_structures(channel)

    # The v2-kept INTERIOR population this image's override compares
    # against, measured the same size-corrected way the candidates are.
    interior = [(r, ob) for r, ob in v2_kept if not ob]
    target_area = float(np.median([r.area for r, _ob in interior])) if interior else 0.0
    _lacuna_mask, lacuna_id = can.build_lacuna_maps(v2_labels, v2_kept)
    v2_core_roots = []
    for lid, (_region, on_border) in enumerate(v2_kept, start=1):
        if on_border:
            continue
        body = lacuna_id == lid
        v2_core_roots.append(count_roots_for_body(G, core_body(body, v2_labels, target_area)))
    median_core_roots = float(np.median(v2_core_roots)) if v2_core_roots else float("inf")

    candidates = []
    for region, on_border in v3_kept:
        key = (round(region.centroid[1], 1), round(region.centroid[0], 1))
        if key not in v3_only_keys:
            continue
        coords = region.coords
        intensity = float(channel[coords[:, 0], coords[:, 1]].mean())
        relative = intensity / median_v2 if median_v2 > 0 else 0.0
        on_flagged = float(flagged[coords[:, 0], coords[:, 1]].mean())
        body = v3_labels == region.label
        roots = count_roots_for_body(G, body)

        passes_a = relative >= MIN_RELATIVE_INTENSITY
        passes_b = on_flagged == 0.0
        passes_c = roots >= MIN_ROOTS

        # D8 override: size-corrected connectivity can outvote gate (a),
        # but never gate (b), and never the haze floor.
        core = core_body(body, v2_labels, target_area)
        core_roots = count_roots_for_body(G, core)
        overrode = bool(
            OVERRIDE_ON_ROOTS
            and not passes_a
            and passes_b
            and passes_c
            and core_roots >= median_core_roots
            and relative >= OVERRIDE_MIN_RELATIVE_INTENSITY
        )
        candidates.append(
            {
                "label": int(region.label),
                "x": float(region.centroid[1]),
                "y": float(region.centroid[0]),
                "area": float(region.area),
                "on_border": bool(on_border),
                "intensity": intensity,
                "relative_intensity": relative,
                "on_flagged_fraction": on_flagged,
                "roots": roots,
                "core_roots": core_roots,
                "core_area": float(core.sum()),
                "median_core_roots": median_core_roots,
                "a_bright": passes_a,
                "b_not_flagged": passes_b,
                "c_connected": passes_c,
                "overrode_a": overrode,
                "accepted": (passes_a and passes_b and passes_c) or overrode,
            }
        )

    return {
        "image": image_path.stem,
        "display": display,
        "channel": channel,
        "v2_labels": v2_labels,
        "v2_kept": v2_kept,
        "v3_labels": v3_labels,
        "t_hi": t_hi,
        "median_v2_intensity": median_v2,
        "candidates": candidates,
    }


def segment_image(image_path: Path):
    """Same signature as seg2.segment_image, so the three detectors are
    interchangeable behind canaliculi_v1.LACUNA_SOURCE.

    The returned label image is rebuilt from scratch: v2's kept lacunae
    renumbered 1..n, then each accepted addition appended. That keeps
    `labels` and `kept` consistent with one another, which downstream code
    relies on."""
    state = evaluate_candidates(image_path)
    v2_labels, v2_kept = state["v2_labels"], state["v2_kept"]

    combined = np.zeros(v2_labels.shape, dtype=np.int32)
    kept: list[tuple] = []
    next_label = 1
    for region, on_border in v2_kept:
        combined[v2_labels == region.label] = next_label
        next_label += 1
    accepted = [c for c in state["candidates"] if c["accepted"]]
    for candidate in accepted:
        body = state["v3_labels"] == candidate["label"]
        # Never overwrite a v2 lacuna: v2 always wins a pixel dispute.
        combined[body & (combined == 0)] = next_label
        next_label += 1

    rows, cols = combined.shape
    for region in measure.regionprops(combined):
        min_row, min_col, max_row, max_col = region.bbox
        on_border = min_row == 0 or min_col == 0 or max_row == rows or max_col == cols
        kept.append((region, on_border))
    return state["display"], combined, kept, state["t_hi"]


def save_overlay(display_uint8: np.ndarray, state: dict, out_path: Path) -> None:
    """v2 lacunae green, hybrid additions cyan, rejected candidates dim
    red so a rejection can be eyeballed as easily as an acceptance."""
    vis = display_uint8.copy()
    v2_mask = np.isin(state["v2_labels"], [r.label for r, _ob in state["v2_kept"]])
    for candidate in state["candidates"]:
        body = state["v3_labels"] == candidate["label"]
        colour = [0, 255, 255] if candidate["accepted"] else [140, 0, 0]
        vis[segmentation.find_boundaries(body, mode="outer")] = colour
    if v2_mask.any():
        vis[segmentation.find_boundaries(v2_mask, mode="outer")] = [0, 255, 0]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    imsave(out_path, vis, check_contrast=False)


def save_candidate_crop(state: dict, candidate: dict, out_path: Path, size: int = 256) -> None:
    """raw | the candidate body | the default skeleton around it, so the
    (c) verdict can be checked against what is actually there."""
    channel = state["channel"]
    half = size // 2
    r0 = int(np.clip(candidate["y"] - half, 0, channel.shape[0] - size))
    c0 = int(np.clip(candidate["x"] - half, 0, channel.shape[1] - size))
    body = (state["v3_labels"] == candidate["label"])[r0:r0 + size, c0:c0 + size]
    raw = (channel[r0:r0 + size, c0:c0 + size] * 255).astype(np.uint8)
    rgb = np.stack([raw] * 3, -1)
    rgb[segmentation.find_boundaries(body, mode="outer")] = (
        [0, 255, 255] if candidate["accepted"] else [255, 0, 0]
    )
    sep = np.full((size, 4, 3), 128, np.uint8)
    strip = np.hstack([np.stack([raw] * 3, -1), sep, rgb])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    imsave(out_path, strip, check_contrast=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hybrid lacuna detection candidate (pre-validation, not default)."
    )
    parser.add_argument("--dir", type=Path, required=True)
    args = parser.parse_args()

    print("HYBRID LACUNA DETECTION -- candidate, NOT default. v-raw, pre-validation, PIXEL units.")
    print(f"Gates: (a) relative intensity >= {MIN_RELATIVE_INTENSITY} x this image's median v2 lacuna")
    print(f"       (b) no overlap with a Phase 1 flagged structure")
    print(f"       (c) >= {MIN_ROOTS} canalicular roots attached (pooled p10 of v2-kept interior lacunae)")
    print()
    print(f'{"image":22s} {"v2":>4s} {"hybrid":>7s} {"added":>6s} {"cand":>5s} '
          f'{"fail a":>7s} {"fail b":>7s} {"fail c":>7s}')

    total_added = 0
    for path in sorted(args.dir.glob("*.tif")):
        state = evaluate_candidates(path)
        cands = state["candidates"]
        accepted = [c for c in cands if c["accepted"]]
        total_added += len(accepted)
        out_dir = HYBRID_DIR / path.stem.replace(" ", "_")
        save_overlay(state["display"], state, out_dir / "v2_vs_hybrid.png")
        for candidate in accepted:
            save_candidate_crop(
                state, candidate,
                out_dir / f'added_x{candidate["x"]:.0f}_y{candidate["y"]:.0f}.png',
            )
        print(
            f'{path.stem[:22]:22s} {len(state["v2_kept"]):4d} '
            f'{len(state["v2_kept"]) + len(accepted):7d} {len(accepted):6d} {len(cands):5d} '
            f'{sum(1 for c in cands if not c["a_bright"]):7d} '
            f'{sum(1 for c in cands if not c["b_not_flagged"]):7d} '
            f'{sum(1 for c in cands if not c["c_connected"]):7d}'
        )
        for candidate in accepted:
            how = "OVERRIDE" if candidate["overrode_a"] else "all gates"
            print(
                f'      + ADDED ({candidate["x"]:.0f},{candidate["y"]:.0f}) area={candidate["area"]:.0f} '
                f'rel_I={candidate["relative_intensity"]:.3f} roots={candidate["roots"]} '
                f'core_roots={candidate["core_roots"]}/{candidate["median_core_roots"]:.1f} '
                f'border={candidate["on_border"]}  [{how}]'
            )

    print(f"\ntotal added across the run: {total_added}")
    print(f"overlays and crops under {HYBRID_DIR}")


if __name__ == "__main__":
    main()
