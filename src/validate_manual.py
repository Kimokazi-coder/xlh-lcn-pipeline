"""Score the pipeline against a manual tracing.

This is the gate the whole project is pre-validation against. Nothing here is a
measure of the pipeline's own: it compares what the pipeline traced with what a
person traced by hand, and reports where the two differ.

    python src/validate_manual.py                      # all 8 images
    python src/validate_manual.py -i data/WT/543_3.tif  # one image
    python src/validate_manual.py -m manual_trace -o results/validation

It runs with no manual tracing present and says so, so it can sit in a check
sequence from the day it is written.

What it reads, from manual_trace/ (the format is in manual_trace/README.md):

    <label>_manual.png          a binary mask, white where a canaliculus runs
    <label>_manual_lacunae.csv  header x,y: one row per lacuna centre

What it reports, per image:

    skeleton precision  the share of the pipeline's skeleton within the
                        tolerance of some hand-traced pixel: how much of what it
                        drew is really there
    skeleton recall     the share of the hand tracing within the tolerance of
                        some pipeline pixel: how much of what is there it drew
    f1                  their harmonic mean
    lacunae             matched, missed (hand-marked, nothing detected) and
                        extra (detected, nothing hand-marked)

The tolerance is 2 px, which is 0.26 um at this pixel size: a hand trace and a
skeleton of the same thread will not agree pixel for pixel, and a thread is about
6 px wide, so a 2 px slack compares the same structure without letting a
neighbouring thread count as a match.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canaliculi  # noqa: E402
import lacunae  # noqa: E402

# How far apart two tracings of the same thread may be and still count as the
# same thread, in pixels. 2 px is 0.26 um. A thread is about 6 px wide, so this
# forgives the disagreement between a hand line and a skeleton without letting
# the next thread over count as a match.
SKELETON_TOLERANCE_PX = 2

# How far a hand-marked lacuna centre may be from a detected lacuna and still be
# the same cell, when the point does not fall inside the detected body. 25 px is
# 3.25 um, well under the spacing between neighbouring lacunae.
LACUNA_MATCH_TOLERANCE_PX = 25

MANUAL_DIR = Path("manual_trace")


def manual_mask_path(manual_dir: Path, label: str) -> Path:
    return manual_dir / f"{label}_manual.png"


def manual_points_path(manual_dir: Path, label: str) -> Path:
    return manual_dir / f"{label}_manual_lacunae.csv"


def read_manual_points(path: Path) -> list[tuple[float, float]]:
    """[(x, y), ...] from a two column csv with an x,y header."""
    if not path.is_file():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for row in rows:
        keys = {k.strip().lower(): v for k, v in row.items() if k}
        if "x" in keys and "y" in keys:
            out.append((float(keys["x"]), float(keys["y"])))
    return out


def score_skeleton(pipeline: np.ndarray, manual: np.ndarray, tolerance_px: int) -> dict:
    """Precision, recall and f1 of the pipeline skeleton against a hand tracing,
    where a pixel counts as matched if some pixel of the other tracing lies
    within `tolerance_px`."""
    n_pipeline, n_manual = int(pipeline.sum()), int(manual.sum())
    if n_pipeline == 0 or n_manual == 0:
        return {"pipeline_px": n_pipeline, "manual_px": n_manual,
                "precision": None, "recall": None, "f1": None}
    near_manual = ndi.distance_transform_edt(~manual) <= tolerance_px
    near_pipeline = ndi.distance_transform_edt(~pipeline) <= tolerance_px
    precision = float((pipeline & near_manual).sum()) / n_pipeline
    recall = float((manual & near_pipeline).sum()) / n_manual
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"pipeline_px": n_pipeline, "manual_px": n_manual,
            "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}


def score_lacunae(lacuna_id_map: np.ndarray, points: list, tolerance_px: int) -> dict:
    """Hand-marked lacuna centres against detected lacunae.

    A point matches the lacuna whose body contains it; failing that, the nearest
    lacuna within the tolerance. Each detected lacuna can be claimed once, so two
    points on one body leave one of them missed rather than both matched."""
    ids = [int(v) for v in np.unique(lacuna_id_map) if v]
    centroids = {}
    for lacuna_id in ids:
        rows, cols = np.nonzero(lacuna_id_map == lacuna_id)
        centroids[lacuna_id] = (float(cols.mean()), float(rows.mean()))

    rows_n, cols_n = lacuna_id_map.shape
    taken, matched, missed = {}, [], []
    for x, y in points:
        xi, yi = int(round(x)), int(round(y))
        hit = 0
        if 0 <= yi < rows_n and 0 <= xi < cols_n:
            hit = int(lacuna_id_map[yi, xi])
        if not hit:
            best, best_d = 0, float("inf")
            for lacuna_id, (cx, cy) in centroids.items():
                d = float(np.hypot(cx - x, cy - y))
                if d < best_d:
                    best, best_d = lacuna_id, d
            hit = best if best_d <= tolerance_px else 0
        if hit and hit not in taken:
            taken[hit] = (x, y)
            matched.append({"lacuna_id": hit, "point_xy": [round(x, 1), round(y, 1)]})
        else:
            missed.append({"point_xy": [round(x, 1), round(y, 1)],
                           "why": "already matched to another point" if hit else "no lacuna here"})
    extra = [{"lacuna_id": i, "centroid_xy": [round(centroids[i][0], 1), round(centroids[i][1], 1)]}
             for i in ids if i not in taken]
    return {"hand_marked": len(points), "detected": len(ids), "matched": len(matched),
            "missed": len(missed), "extra": len(extra),
            "missed_points": missed, "extra_lacunae": extra}


def validate_image(image_path: Path, manual_dir: Path) -> dict | None:
    """One image, or None if it has no hand tracing yet."""
    from skimage.io import imread

    label = lacunae.image_label(image_path)
    mask_path = manual_mask_path(manual_dir, label)
    points_path = manual_points_path(manual_dir, label)
    if not mask_path.is_file() and not points_path.is_file():
        return None

    lac = lacunae.analyse_image(image_path)
    _display, channel = lacunae.load_channel(image_path)
    net = canaliculi.analyse_network(image_path, lac, channel)

    out = {"image_label": label, "tolerance_px": SKELETON_TOLERANCE_PX,
           "tolerance_um": round(config.um(SKELETON_TOLERANCE_PX), 4)}
    if mask_path.is_file():
        manual = np.asarray(imread(mask_path))
        if manual.ndim == 3:
            manual = manual[..., :3].max(axis=-1)
        manual = manual > 127
        if manual.shape != net["skeleton"].shape:
            raise ValueError(f"{mask_path} is {manual.shape}, the image is {net['skeleton'].shape}")
        out["skeleton"] = score_skeleton(net["skeleton"], manual, SKELETON_TOLERANCE_PX)
    else:
        out["skeleton"] = {"note": "no mask for this image"}
    out["lacunae"] = (score_lacunae(net["lacuna_id_map"], read_manual_points(points_path),
                                    LACUNA_MATCH_TOLERANCE_PX)
                      if points_path.is_file() else {"note": "no lacuna points for this image"})
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Score the pipeline against a manual tracing (pre-validation gate).")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-i", dest="image", type=Path, help="One .tif image.")
    group.add_argument("-d", dest="dir", type=Path, default=config.DATA_DIR / "WT",
                       help="A folder of .tif images (default data/WT).")
    parser.add_argument("-m", dest="manual", type=Path, default=MANUAL_DIR,
                        help=f"Where the hand tracings are (default {MANUAL_DIR}).")
    parser.add_argument("-o", dest="out", type=Path, default=None,
                        help="Write the report here as json.")
    args = parser.parse_args()

    images = [args.image] if args.image else sorted(args.dir.glob("*.tif"))
    results = []
    for image_path in images:
        scored = validate_image(image_path, args.manual)
        if scored is not None:
            results.append(scored)

    if not results:
        print("no manual masks yet")
        print(f"  looked in {args.manual}/ for <label>_manual.png and "
              f"<label>_manual_lacunae.csv")
        print(f"  the format is in {args.manual}/README.md")
        return 0

    header = ["image", "skeleton precision", "recall", "f1", "lacunae matched", "missed", "extra"]
    rows = []
    for r in results:
        s, l = r["skeleton"], r["lacunae"]
        rows.append([r["image_label"],
                     s.get("precision", "-"), s.get("recall", "-"), s.get("f1", "-"),
                     l.get("matched", "-"), l.get("missed", "-"), l.get("extra", "-")])
    width = [max(len(str(x)) for x in [h] + [row[i] for row in rows])
             for i, h in enumerate(header)]
    print("Pipeline against the manual tracing "
          f"(tolerance {SKELETON_TOLERANCE_PX} px = {config.um(SKELETON_TOLERANCE_PX):g} um)")
    print("  ".join(h.ljust(w) for h, w in zip(header, width)))
    print("  ".join("-" * w for w in width))
    for row in rows:
        print("  ".join(str(v).ljust(w) for v, w in zip(row, width)))

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        path = args.out / "validation_against_manual.json"
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"tolerance_px": SKELETON_TOLERANCE_PX, "images": results}, f, indent=2,
                      default=float)
        print(f"\nreport -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
