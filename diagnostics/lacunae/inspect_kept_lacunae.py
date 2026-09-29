"""Read-only diagnostic: measure chosen kept v2 lacunae against the whole
kept population. Pre-validation, PIXEL units. Changes nothing in the
pipeline and writes no default output.

Written for finding 2 of the 2026-09-29 visual review (542_z06: the kept
object near (555,145) beside the vascular band, and the hook-shaped object
near (100,65) that may be a canalicular loop), but it takes any image and
any points.

For EVERY kept v2 lacuna in every image under --dir it computes:
    area, solidity, aspect_ratio, eccentricity   v2's own shape measures
    rel_intensity   mean raw intensity / this image's median kept-lacuna
                    intensity (the same normalisation hybrid gate (a) uses)
    thickness_px    2 x the maximum of the object's distance transform,
                    i.e. the widest disk that fits inside it. A real
                    canaliculus is at most ~8 px across (post-top-hat
                    half-width p99 ~4.2 px, see canaliculi_v1
                    TOPHAT_RADIUS_PX), so a loop of thread cannot be much
                    thicker than that, while a lacuna body is.
    open_kept_frac  fraction of the object left after an opening with a
                    disk of canaliculi_v1.TOPHAT_RADIUS_PX (5 px, 11 px
                    across), the same disk that defines "broader than any
                    canaliculus" in the top-hat. A thread-scale object
                    vanishes (near 0); a body with a thread-width appendage
                    loses only the appendage.
    holes           number of enclosed holes (pieces minus Euler number). A
                    closed canalicular loop would enclose one.
    roots           distinct canalicular roots, counted exactly as
                    COUNT_MODE="roots" counts them on the CURRENT DEFAULT
                    canaliculi graph (attach_lacunae + cell_root_lengths)
    dist_flagged_px distance from the object to the nearest Phase 1 flagged
                    non-LCN structure (0 = touching or overlapping); None
                    if the image has no flagged structure

Each requested object is then placed in the pooled population (rank and
percentile per measure), and a crop is saved: raw | v2 outlines (target
cyan, other lacunae green) with the flagged region tinted blue | the
default skeleton in white.

Usage (one line):
    python diagnostics/lacunae/inspect_kept_lacunae.py --dir data/WT
        --target "542 WT  2_z06c1-2" 555,145 --target "542 WT  2_z06c1-2" 100,65
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from skimage import measure, morphology, segmentation
from skimage.io import imsave

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from count_lacunae import load_channel  # noqa: E402
import canaliculi_v1 as can  # noqa: E402
import exclusion_mask as excl  # noqa: E402
import segment_lacunae_hybrid as hy  # noqa: E402
import segment_lacunae_v2 as seg2  # noqa: E402

OUT_DIR = config.DIAGNOSTICS_DIR / "round3" / "finding2"
REPORT_DIR = config.REPORTS_DIR / "round3"

# Half-size (px) of the saved crops. Cosmetic only.
CROP_HALF_PX = 90

MEASURES = [
    "area", "solidity", "aspect_ratio", "eccentricity",
    "rel_intensity", "thickness_px", "open_kept_frac", "holes", "roots", "dist_flagged_px",
]


def measure_image(image_path: Path) -> tuple[list[dict], dict]:
    """Every kept v2 lacuna in one image, with the measures above."""
    display, channel = load_channel(image_path)
    _d, labels, kept, _t = seg2.segment_image(image_path)
    lacuna_mask, lacuna_id_map = can.build_lacuna_maps(labels, kept)

    # The current default skeleton graph, built the way hybrid gate (c)
    # builds it, then attached and counted the way COUNT_MODE="roots" does.
    G, flagged = hy.default_skeleton_graph(image_path, channel, labels, kept)
    if flagged is None:
        flagged, _objs = excl.flagged_structures(channel)
    dist_to_lacuna, nearest_id = can.nearest_lacuna_map(lacuna_id_map)
    cell_ids = list(range(1, len(kept) + 1))
    can.attach_lacunae(G, dist_to_lacuna, nearest_id, cell_ids)

    dist_to_flagged = ndi.distance_transform_edt(~flagged) if flagged.any() else None
    intensities = [float(channel[r.coords[:, 0], r.coords[:, 1]].mean()) for r, _b in kept]
    median_intensity = float(np.median(intensities)) if intensities else 0.0

    rows = []
    for lid, (region, on_border) in enumerate(kept, start=1):
        body = lacuna_id_map == lid
        minr, minc, maxr, maxc = region.bbox
        local = np.pad(body[minr:maxr, minc:maxc], 1)
        rows.append({
            "image": image_path.stem,
            "lacuna_id": lid,
            "x": float(region.centroid[1]),
            "y": float(region.centroid[0]),
            "on_border": bool(on_border),
            "area": float(region.area),
            "solidity": float(region.solidity),
            "aspect_ratio": float(region.axis_major_length / region.axis_minor_length)
            if region.axis_minor_length > 0 else float("inf"),
            "eccentricity": float(region.eccentricity),
            "rel_intensity": intensities[lid - 1] / median_intensity if median_intensity else 0.0,
            "thickness_px": 2.0 * float(ndi.distance_transform_edt(local).max()),
            # holes = pieces minus Euler number; a label can hold more than
            # one piece, so "1 - Euler" alone can go negative.
            "holes": int(
                measure.label(local, connectivity=2).max() - measure.euler_number(local, connectivity=2)
            ),
            "open_kept_frac": float(
                morphology.opening(local, morphology.disk(can.TOPHAT_RADIUS_PX)).sum() / local.sum()
            ),
            "roots": len(can.cell_root_lengths(G, lid)),
            "dist_flagged_px": float(dist_to_flagged[body].min()) if dist_to_flagged is not None else None,
        })

    context = {
        "display": display,
        "lacuna_id_map": lacuna_id_map,
        "flagged": flagged,
        "skeleton": _default_skeleton(image_path, channel, labels, kept),
    }
    return rows, context


def _default_skeleton(image_path: Path, channel: np.ndarray, labels, kept) -> np.ndarray:
    """The default skeleton as a pixel image, for the crop only. Read from
    the regenerated default output rather than rebuilt, so the crop shows
    exactly what results/canaliculi/<image>/skeleton.png shows."""
    from skimage.io import imread

    path = config.CANALICULI_DIR / image_path.stem.replace(" ", "_") / "skeleton.png"
    return imread(path) > 0 if path.is_file() else np.zeros(channel.shape, dtype=bool)


def save_crop(context: dict, row: dict, out_path: Path) -> None:
    """raw | outline over raw, flagged region tinted | default skeleton."""
    display = context["display"]
    h, w = display.shape[:2]
    r0 = int(np.clip(row["y"] - CROP_HALF_PX, 0, max(h - 2 * CROP_HALF_PX, 0)))
    c0 = int(np.clip(row["x"] - CROP_HALF_PX, 0, max(w - 2 * CROP_HALF_PX, 0)))
    sl = (slice(r0, r0 + 2 * CROP_HALF_PX), slice(c0, c0 + 2 * CROP_HALF_PX))

    raw = display[sl].copy()
    outlined = raw.copy()
    flagged = context["flagged"][sl]
    if flagged.any():
        outlined[flagged] = (0.6 * outlined[flagged] + 0.4 * np.array([0, 90, 255])).astype(np.uint8)
    others = segmentation.find_boundaries(context["lacuna_id_map"][sl] > 0, mode="outer")
    outlined[others] = [0, 160, 0]
    mine = segmentation.find_boundaries(context["lacuna_id_map"][sl] == row["lacuna_id"], mode="outer")
    outlined[mine] = [0, 255, 255]

    skel = raw.copy() // 3
    skel[morphology.dilation(context["skeleton"][sl], morphology.disk(1))] = [255, 255, 255]
    skel[mine] = [0, 255, 255]

    sep = np.full((raw.shape[0], 4, 3), 128, np.uint8)
    strip = np.hstack([raw, sep, outlined, sep, skel])
    strip = np.repeat(np.repeat(strip, 2, axis=0), 2, axis=1)  # 2x for legibility
    out_path.parent.mkdir(parents=True, exist_ok=True)
    imsave(out_path, strip, check_contrast=False)


def rank_line(value, population: np.ndarray, name: str) -> str:
    """Where one value sits in the pooled population: rank from the bottom,
    percentile, and the population's min / p10 / median / p90 / max."""
    if value is None or population.size == 0:
        return f"  {name:16s} n/a"
    below = int((population < value).sum())
    equal = int((population == value).sum())
    pct = 100.0 * (below + 0.5 * equal) / population.size
    q = np.percentile(population, [0, 10, 50, 90, 100])
    return (
        f"  {name:16s} {value:9.3f}   rank {below + 1:3d}/{population.size} from bottom "
        f"(pct {pct:5.1f})   pop min {q[0]:.3f} p10 {q[1]:.3f} med {q[2]:.3f} "
        f"p90 {q[3]:.3f} max {q[4]:.3f}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dir", type=Path, required=True)
    parser.add_argument(
        "--target", nargs=2, action="append", default=[], metavar=("IMAGE_STEM", "X,Y"),
        help="An image stem and an x,y point; the kept lacuna nearest the point is inspected.",
    )
    parser.add_argument("--report-name", default="finding2_542_z06_objects")
    args = parser.parse_args()

    all_rows: list[dict] = []
    contexts: dict = {}
    for path in sorted(args.dir.glob("*.tif")):
        rows, context = measure_image(path)
        all_rows.extend(rows)
        contexts[path.stem] = context
        print(f"measured {path.stem}: {len(rows)} kept lacunae")

    lines = [
        "Kept v2 lacunae: chosen objects against the pooled kept population.",
        "PRE-VALIDATION, PIXEL units. Read-only diagnostic; no pipeline output changed.",
        f"Population: all kept v2 lacunae over {len(contexts)} images, n={len(all_rows)} "
        f"(interior n={sum(1 for r in all_rows if not r['on_border'])}).",
        "Roots are counted on the current default canaliculi graph, as COUNT_MODE='roots'.",
        "",
    ]
    for stem, point in args.target:
        x, y = (float(v) for v in point.split(","))
        candidates = [r for r in all_rows if r["image"] == stem]
        row = min(candidates, key=lambda r: np.hypot(r["x"] - x, r["y"] - y))
        lines.append(
            f"{stem}  point ({x:.0f},{y:.0f})  ->  lacuna_id {row['lacuna_id']} at "
            f"({row['x']:.0f},{row['y']:.0f}), on_border={row['on_border']}"
        )
        for name in MEASURES:
            pop = np.array([r[name] for r in all_rows if r[name] is not None], dtype=float)
            lines.append(rank_line(row[name], pop, name))
        lines.append("")
        save_crop(
            contexts[stem], row,
            OUT_DIR / f"{stem.replace(' ', '_')}_id{row['lacuna_id']}_x{row['x']:.0f}_y{row['y']:.0f}.png",
        )

    text = "\n".join(lines)
    print("\n" + text)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / f"{args.report_name}.txt").write_text(text + "\n", encoding="utf-8")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "kept_population.json", "w") as f:
        json.dump({"status": "pre-validation", "units": "px", "lacunae": all_rows}, f, indent=1)


if __name__ == "__main__":
    main()
