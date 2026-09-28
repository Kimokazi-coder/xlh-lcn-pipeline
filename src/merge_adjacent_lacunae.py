"""Post-merge of adjacent lacuna pieces. NOT default. v-raw, pre-validation.

A single lacuna can reach the kept set as TWO objects when a 1-2 px
thresholding break splits its mask. This module merges such a pair back
together, after the detector has run, without touching the detector.

WHY THIS IS NOT A SADDLE-RATIO PROBLEM, AND WHY seg2 CANNOT CATCH IT.
segment_lacunae_v2.merge_shallow_splits already re-merges watershed
over-splits, using the saddle depth between two pieces' distance-transform
peaks (MERGE_SADDLE_RATIO_MIN). It cannot catch this case, for a reason
worth being precise about: that function only compares pieces WITHIN one
pre-watershed connected component. When two pieces are separated by a real
gap in the mask they were never one component, watershed never split them,
and merge_shallow_splits never sees them.

Worse, the saddle ratio actively MISREADS this case. The only adjacent
pair in the 8 WT images scores a saddle ratio of 0.000, which reads as
"deep neck, genuinely two lobes, do not merge" -- but the ratio is 0.000
precisely BECAUSE the two bodies are disconnected, so the line between
their peaks leaves the mask. A disconnection and a deep neck are
indistinguishable to that measure and mean opposite things here. So this
module does not use the saddle ratio at all, and MERGE_SADDLE_RATIO_MIN is
left exactly as it is.

The criterion used instead is proximity plus union shape: two kept objects
whose bodies nearly touch, whose union is still lacuna-shaped, are one
lacuna.

Usage: canaliculi_v1 applies this after the lacuna source runs, when
MERGE_ADJACENT_PAIRS is True. It is False by default.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from skimage import measure, morphology

# Master switch. False = current behaviour, nothing merged.
MERGE_ADJACENT_PAIRS = False

# Two kept objects closer than this are candidates for being one lacuna.
#
# PROVENANCE. Measured over all 8 WT images: exactly ONE pair of v2-kept
# lacunae comes within 5 px of another, in 682_z29c1-3 (labels 195+196),
# and its gap is 1.0 px. Everything else is far apart, so there is no
# distribution to sit inside -- the value only has to be large enough to
# catch a thresholding break and small enough that two genuinely separate
# lacunae can never qualify. 2 px is a break; the next-nearest pair in the
# data is beyond 5 px. Raising this without re-measuring would be unsafe.
MERGE_ADJACENT_MAX_GAP_PX = 2.0

# The union must still look like one lacuna, judged against the range the
# v2-kept population actually spans across the 8 WT images (n=98):
#     area     445 - 9321 px^2
#     solidity 0.525 - 0.955
#     aspect   1.16 - 5.76
# A union that falls outside any of these is two things, not one. Taking
# the observed MAXIMUM rather than a percentile is deliberate: the question
# is "could this be a lacuna", and anything inside the observed range
# demonstrably could.
MERGE_UNION_MAX_AREA_PX2 = 9321.0
MERGE_UNION_MIN_SOLIDITY = 0.525
MERGE_UNION_MAX_ASPECT = 5.76

# Radius (px) of the closing used to bridge the gap when measuring the
# union's shape and when writing the merged body. Must exceed
# MERGE_ADJACENT_MAX_GAP_PX so the two pieces actually join; 3 is the
# smallest disk that reliably closes a 2 px gap.
MERGE_CLOSING_RADIUS_PX = 3


def find_mergeable_pairs(labels: np.ndarray, kept: list[tuple]) -> list[dict]:
    """Pairs of kept objects that are close enough AND whose union is still
    lacuna-shaped. Returns one record per pair with the numbers behind the
    verdict, so a merge can be audited."""
    found = []
    regions = [region for region, _on_border in kept]
    for i in range(len(regions)):
        for j in range(i + 1, len(regions)):
            body_a = labels == regions[i].label
            body_b = labels == regions[j].label
            gap = float(ndi.distance_transform_edt(~body_a)[body_b].min())
            if gap > MERGE_ADJACENT_MAX_GAP_PX:
                continue

            union = morphology.binary_closing(
                body_a | body_b, morphology.disk(MERGE_CLOSING_RADIUS_PX)
            )
            props = measure.regionprops(measure.label(union.astype(int)))
            if not props:
                continue
            union_region = max(props, key=lambda r: r.area)
            minor, major = union_region.axis_minor_length, union_region.axis_major_length
            aspect = (major / minor) if minor > 0 else float("inf")
            ok = (
                union_region.area <= MERGE_UNION_MAX_AREA_PX2
                and union_region.solidity >= MERGE_UNION_MIN_SOLIDITY
                and aspect <= MERGE_UNION_MAX_ASPECT
            )
            found.append(
                {
                    "label_a": int(regions[i].label),
                    "label_b": int(regions[j].label),
                    "gap_px": gap,
                    "union_area": float(union_region.area),
                    "union_solidity": float(union_region.solidity),
                    "union_aspect": float(aspect),
                    "merge": bool(ok),
                    "x": float(union_region.centroid[1]),
                    "y": float(union_region.centroid[0]),
                }
            )
    return found


def apply_merges(labels: np.ndarray, kept: list[tuple]) -> tuple[np.ndarray, list[tuple], list[dict]]:
    """Merge every qualifying pair and rebuild (labels, kept) so the two
    stay consistent. Returns the new labels, the new kept list, and the
    pair records (including the ones NOT merged, for the audit trail)."""
    pairs = find_mergeable_pairs(labels, kept)
    to_merge = [p for p in pairs if p["merge"]]
    if not to_merge:
        return labels, kept, pairs

    # Work on a label image containing ONLY the kept objects. `labels` as
    # it arrives still holds every pre-filter region -- 177 of them in
    # 682_z29 against 13 kept -- so relabelling it wholesale would
    # resurrect everything the detector's filters rejected.
    kept_labels = {region.label for region, _on_border in kept}
    merged = np.where(np.isin(labels, list(kept_labels)), labels, 0).astype(np.int32)

    for pair in to_merge:
        body = (merged == pair["label_a"]) | (merged == pair["label_b"])
        body = morphology.binary_closing(body, morphology.disk(MERGE_CLOSING_RADIUS_PX))
        # Claim only background for the closing's new pixels, so a merge
        # can never eat into a third object.
        merged[body & ((merged == 0) | (merged == pair["label_b"]))] = pair["label_a"]

    rows, cols = merged.shape
    relabelled = measure.label(merged > 0, connectivity=2)
    new_kept = []
    for region in measure.regionprops(relabelled):
        min_row, min_col, max_row, max_col = region.bbox
        on_border = min_row == 0 or min_col == 0 or max_row == rows or max_col == cols
        new_kept.append((region, on_border))
    return relabelled, new_kept, pairs
