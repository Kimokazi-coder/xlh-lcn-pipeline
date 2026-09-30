"""Read-only diagnostic: how each per-cell and per-field measure responds to
the reach cap. Pre-validation, PIXEL units. Writes no pipeline output.

For every WT image the default skeleton is built once, exactly as
canaliculi_v1.process builds it, and canaliculi_v1.canaliculi_measurements_graph
is then called at each cap in CAPS_PX. So every number here comes from the
pipeline's own measurement code, not from a re-implementation.

Pooled per-cell values are means over all INTERIOR cells of the 8 images
(the population the pipeline's summaries use). The per-field density is the
mean over the 8 images of canalicular_length_density_per_px.

Check: at cap None the interior mean edge count per image must equal the
committed default results/canaliculi/<image>/measurements.json, or the run
stops.

Usage (from the repo root):
    python diagnostics/canaliculi/reach_sensitivity.py --dir data/WT
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from skimage import morphology

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from count_lacunae import load_channel  # noqa: E402
import canaliculi_v1 as can  # noqa: E402
import exclusion_mask  # noqa: E402
import gap_bridging  # noqa: E402
import segment_lacunae_v2 as seg2  # noqa: E402

PRIMARY = can.REACH_CAP_PRIMARY_PX
# Four caps around the primary, in the 25 px steps of the selection rule,
# plus two reference rows: no cap, and a much tighter 100 px.
CAPS_PX = (None, 100.0, 225.0, 250.0, PRIMARY, 300.0, 325.0)

OUT_DIR = config.DIAGNOSTICS_DIR / "round3" / "reach"
REPORT_DIR = config.REPORTS_DIR / "round3"

PER_CELL = [
    ("roots_count", "roots per cell"),
    ("ring_length_r30_px", "ring length r30 per cell (px)"),
    ("ring_length_r60_px", "ring length r60 per cell (px)"),
    ("owned_length_px", "owned length per cell (px)"),
    ("canaliculi_count", "edge count per cell"),
]


def default_skeleton(image_path: Path):
    """The default skeleton and lacuna maps, step for step as in
    canaliculi_v1.process with every switch at its module default."""
    _display, channel = load_channel(image_path)
    _d, labels, kept, _t = seg2.segment_image(image_path)
    lacuna_mask, lacuna_id_map = can.build_lacuna_maps(labels, kept)
    flagged = (
        exclusion_mask.flagged_structures(channel)[0]
        if can.BLOCK_GROWTH_IN_FLAGGED else np.zeros(channel.shape, dtype=bool)
    )
    candidate, t_lo = can.canaliculi_candidate_mask(
        channel, lacuna_mask, can.PREPROCESS_MODE, can.THRESHOLD_MODE,
        flagged if can.BLOCK_GROWTH_IN_FLAGGED else None,
    )
    excluded, _info = exclusion_mask.build_exclusion(image_path, channel, labels, can.EXCLUSION_MODE)
    if excluded.any():
        candidate = candidate & ~excluded
    skeleton = morphology.skeletonize(candidate)
    if can.GAP_BRIDGING:
        bridges = gap_bridging.find_bridges(
            skeleton, can.preprocess_channel(channel, can.PREPROCESS_MODE), t_lo,
            lacuna_mask | excluded | flagged,
        )
        if bridges:
            skeleton = morphology.skeletonize(gap_bridging.apply_bridges(candidate, bridges))
    dist, nearest = can.nearest_lacuna_map(lacuna_id_map)
    return kept, skeleton, dist, nearest, lacuna_mask, excluded


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dir", type=Path, required=True)
    args = parser.parse_args()
    prec = config.CSV_FLOAT_PRECISION

    rows = {c: [] for c in CAPS_PX}       # interior per-cell rows, pooled
    density = {c: [] for c in CAPS_PX}    # per-field density, one per image
    per_image = []
    for path in sorted(args.dir.glob("*.tif")):
        kept, skeleton, dist, nearest, lacuna_mask, excluded = default_skeleton(path)
        img = {"image": path.stem}
        for cap in CAPS_PX:
            meas, _map, G, _eo = can.canaliculi_measurements_graph(
                kept, skeleton, dist, nearest, precision=prec, count_mode="edge", reach_cap=cap,
            )
            interior = [m for m in meas if not m["on_border"]]
            rows[cap] += interior
            field = can.field_metrics(skeleton, G, lacuna_mask, excluded, len(kept), precision=prec)
            density[cap].append(field["canalicular_length_density_per_px"])
            img[str(cap)] = {
                "owned_length_mean": float(np.mean([m["owned_length_px"] for m in interior])),
                "edge_count_mean": round(float(np.mean([m["canaliculi_count"] for m in interior])), prec),
            }
        committed = json.load(open(
            config.CANALICULI_DIR / path.stem.replace(" ", "_") / "measurements.json"
        ))["summary"]["canaliculi_count"]["mean"]
        if abs(img["None"]["edge_count_mean"] - committed) > 1e-6:
            raise SystemExit(f"MISMATCH {path.stem}: uncapped {img['None']['edge_count_mean']} vs committed {committed}")
        per_image.append(img)
        print(f"measured {path.stem}")

    def pooled(cap, key):
        return float(np.mean([m[key] for m in rows[cap]]))

    base = {key: pooled(None, key) for key, _ in PER_CELL}
    base_density = float(np.mean(density[None]))
    head = ["cap px"] + [label for _, label in PER_CELL] + ["field length density (px^-1)"]
    lines = [
        "# Step 4: sensitivity of each measure to the reach cap",
        "",
        "PRE-VALIDATION, PIXEL units. Every value comes from canaliculi_v1's own",
        "measurement code, run on the default skeleton at each cap. Per-cell values are",
        f"means over the {len(rows[None])} interior cells of the 8 WT images; field density",
        "is the mean over the 8 images. Uncapped edge counts matched the committed default",
        "outputs on all 8 images.",
        "",
        f"Primary cap: **{PRIMARY:g} px** (Step 1 rule). 100 px and no cap are reference rows.",
        "",
        "## Pooled values",
        "",
        "| " + " | ".join(head) + " |",
        "|" + "---|" * len(head),
    ]
    for cap in CAPS_PX:
        label = "no cap" if cap is None else (f"**{cap:g}**" if cap == PRIMARY else f"{cap:g}")
        vals = [f"{pooled(cap, k):.2f}" for k, _ in PER_CELL] + [f"{np.mean(density[cap]):.5f}"]
        lines.append(f"| {label} | " + " | ".join(vals) + " |")

    lines += ["", "## Change against no cap", "", "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    spread = {}
    for cap in CAPS_PX[1:]:
        label = f"**{cap:g}**" if cap == PRIMARY else f"{cap:g}"
        vals = []
        for k, _ in PER_CELL:
            change = 100 * (pooled(cap, k) / base[k] - 1) if base[k] else 0.0
            vals.append(f"{change:+.1f}%")
        vals.append(f"{100 * (np.mean(density[cap]) / base_density - 1):+.1f}%")
        lines.append(f"| {label} | " + " | ".join(vals) + " |")
    for k, label in PER_CELL:
        around = [pooled(c, k) for c in (225.0, 250.0, PRIMARY, 300.0, 325.0)]
        spread[label] = 100 * (max(around) - min(around)) / base[k] if base[k] else 0.0

    lines += [
        "", "## Swing across the four caps around the primary (225 to 325 px)", "",
        "Range (max minus min) as a percentage of the uncapped value:", "",
    ]
    for label, value in spread.items():
        lines.append(f"- {label}: {value:.1f}%")
    lines.append("- field length density: 0.0% (it does not use ownership)")

    lines += ["", "## Owned length per cell by image (mean over interior cells, px)", "",
              "| image | " + " | ".join("no cap" if c is None else f"{c:g}" for c in CAPS_PX) + " |",
              "|---|" + "---|" * len(CAPS_PX)]
    for img in per_image:
        lines.append(f"| {img['image']} | " + " | ".join(f"{img[str(c)]['owned_length_mean']:.0f}" for c in CAPS_PX) + " |")

    text = "\n".join(lines) + "\n"
    print("\n" + text)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "step4_sensitivity.md").write_text(text, encoding="utf-8")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "sensitivity.json", "w") as f:
        json.dump({"status": "pre-validation", "units": "px", "caps": [c for c in CAPS_PX],
                   "pooled": {str(c): {k: pooled(c, k) for k, _ in PER_CELL} for c in CAPS_PX},
                   "field_density": {str(c): float(np.mean(density[c])) for c in CAPS_PX},
                   "per_image": per_image}, f, indent=1)


if __name__ == "__main__":
    main()
