"""Read-only diagnostic: how far through the network each cell's owned
threads reach. Pre-validation, PIXEL units. Changes no pipeline output.

WHY. Ownership in canaliculi_v1 ("graph" method) is by multi-source
shortest path through the whole skeleton graph, with no limit on distance.
A cell attached to a large connected mesh can therefore own threads far
across the field. This measures that reach so a cap can be chosen from
data rather than guessed.

DEFINITIONS (graph distances along the skeleton, in px, measured from the
cell's virtual node, so they include the attachment gap of at most
canaliculi_v1.LACUNA_ATTACH_GAP_PX):
    entry distance  for an owned edge (thread), the smaller node_dist of
                    its two end nodes. canaliculi_v1.assign_edges gives the
                    edge to the owner of exactly that end, so this is where
                    the owning cell's path first reaches the thread.
    exit distance   entry distance + the edge's length: how far from the
                    cell the far end of the thread lies if walked from the
                    entry. An upper bound on the thread's farthest pixel.
    cell reach      the largest exit distance over a cell's owned edges.

THE CAP RULE this script evaluates, matching canaliculi_v1.apply_reach_cap:
an edge stays owned if and only if its entry distance is <= the cap. The
edge is then kept whole, so owned material can extend past the cap by at
most one edge length. "Owned length retained" at a cap is the sum of kept
edge lengths over the sum of all owned edge lengths, pooled over images.

VERIFICATION. The graph is rebuilt with the current default settings (the
same builder hybrid gate (c) uses). Before any reach number is reported,
each image's interior mean edge count per cell is compared with the
committed default results/canaliculi/<image>/measurements.json; a mismatch
aborts the run.

Usage (from the repo root):
    python diagnostics/canaliculi/measure_reach.py --dir data/WT
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from count_lacunae import load_channel  # noqa: E402
import canaliculi_v1 as can  # noqa: E402
import segment_lacunae_hybrid as hy  # noqa: E402
import segment_lacunae_v2 as seg2  # noqa: E402

OUT_DIR = config.DIAGNOSTICS_DIR / "round3" / "reach"
REPORT_DIR = config.REPORTS_DIR / "round3"

REACH_THRESHOLDS_PX = (50, 75, 100, 150, 200)
# Caps evaluated for the retention curve, in px. 25 px steps because the
# selection rule rounds to a multiple of 25.
CAP_GRID_PX = tuple(range(25, 1001, 25))
# The selection rule set by the user for the overnight run: the smallest
# cap that keeps at least this fraction of pooled owned skeleton length.
RETAIN_FRACTION = 0.90


def default_graph_state(image_path: Path) -> dict:
    """Default graph, ownership and per-edge distances for one image."""
    _display, channel = load_channel(image_path)
    _d, labels, kept, _t = seg2.segment_image(image_path)
    G, _flagged = hy.default_skeleton_graph(image_path, channel, labels, kept)
    _mask, lacuna_id_map = can.build_lacuna_maps(labels, kept)
    dist_to_lacuna, nearest_id = can.nearest_lacuna_map(lacuna_id_map)
    cell_ids = list(range(1, len(kept) + 1))
    can.attach_lacunae(G, dist_to_lacuna, nearest_id, cell_ids)
    owner, node_dist = can.assign_by_connectivity(G, cell_ids)
    edge_owner = can.assign_edges(G, owner, node_dist)

    edges = []
    for edge, cell in edge_owner.items():
        u, v = tuple(edge)
        w = float(G[u][v]["weight"])
        entry = min(node_dist.get(u, np.inf), node_dist.get(v, np.inf))
        edges.append({"cell": int(cell), "length": w, "entry": float(entry), "exit": float(entry + w)})
    return {
        "image": image_path.stem,
        "edges": edges,
        "on_border": {i: bool(b) for i, (_r, b) in enumerate(kept, start=1)},
        "areas": {i: float(r.area) for i, (r, _b) in enumerate(kept, start=1)},
        "centroids": {i: (float(r.centroid[1]), float(r.centroid[0])) for i, (r, _b) in enumerate(kept, start=1)},
    }


def verify_against_default(state: dict) -> tuple[float, float]:
    """Interior mean edge count per cell, rebuilt vs committed default."""
    counts = {i: 0 for i in state["on_border"]}
    for e in state["edges"]:
        counts[e["cell"]] += 1
    interior = [counts[i] for i, b in state["on_border"].items() if not b]
    rebuilt = round(float(np.mean(interior)), config.CSV_FLOAT_PRECISION) if interior else 0.0
    path = config.CANALICULI_DIR / state["image"].replace(" ", "_") / "measurements.json"
    committed = json.load(open(path))["summary"]["canaliculi_count"]["mean"]
    return rebuilt, committed


def dist_line(label: str, values: np.ndarray) -> str:
    if values.size == 0:
        return f"  {label:34s} none"
    q = np.percentile(values, [50, 75, 90, 95])
    return (
        f"  {label:34s} n={values.size:5d}  median {q[0]:6.1f}  p75 {q[1]:6.1f}  "
        f"p90 {q[2]:6.1f}  p95 {q[3]:6.1f}  max {values.max():7.1f}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dir", type=Path, required=True)
    args = parser.parse_args()

    states = []
    lines = [
        "# Step 1: per-cell reach of owned canaliculi",
        "",
        "PRE-VALIDATION, PIXEL units. Read-only; no pipeline output changed.",
        "Graph distances along the skeleton from each cell (see the script docstring for",
        "entry, exit and reach). All cells, border cells included, unless stated.",
        "",
        "## Verification: rebuilt graph vs committed default outputs",
        "",
        "Interior mean edge count per cell, rebuilt here vs results/canaliculi/<image>/measurements.json:",
        "",
    ]
    for path in sorted(args.dir.glob("*.tif")):
        state = default_graph_state(path)
        rebuilt, committed = verify_against_default(state)
        ok = abs(rebuilt - committed) < 1e-6
        lines.append(f"    {state['image']:22s} rebuilt {rebuilt:8.4f}  committed {committed:8.4f}  {'OK' if ok else 'MISMATCH'}")
        if not ok:
            raise SystemExit(f"MISMATCH for {state['image']}: rebuilt {rebuilt} vs committed {committed}")
        states.append(state)
        print(f"measured {state['image']}")

    lines += ["", "## Exit distance per owned edge (px), per image and pooled", "", "```"]
    all_exit, all_entry, all_len = [], [], []
    for s in states:
        exits = np.array([e["exit"] for e in s["edges"]])
        lines.append(dist_line(s["image"], exits))
        all_exit += exits.tolist()
        all_entry += [e["entry"] for e in s["edges"]]
        all_len += [e["length"] for e in s["edges"]]
    all_exit, all_entry, all_len = map(np.array, (all_exit, all_entry, all_len))
    lines.append(dist_line("POOLED", all_exit))
    lines += ["```", "", "Entry distance per owned edge (px), pooled:", "", "```",
              dist_line("POOLED entry", all_entry), "```", ""]

    lines += ["## Cell reach (largest exit distance per cell) and cells beyond each distance", "",
              "| image | cells | reach median | reach max | " + " | ".join(f"> {t}" for t in REACH_THRESHOLDS_PX) + " |",
              "|---|---|---|---|" + "---|" * len(REACH_THRESHOLDS_PX)]
    pooled_reach = []
    for s in states:
        reach = {}
        for e in s["edges"]:
            reach[e["cell"]] = max(reach.get(e["cell"], 0.0), e["exit"])
        r = np.array([reach.get(i, 0.0) for i in s["on_border"]])
        pooled_reach += r.tolist()
        lines.append(
            f"| {s['image']} | {r.size} | {np.median(r):.1f} | {r.max():.1f} | "
            + " | ".join(str(int((r > t).sum())) for t in REACH_THRESHOLDS_PX) + " |"
        )
    r = np.array(pooled_reach)
    lines.append(
        f"| **POOLED** | {r.size} | {np.median(r):.1f} | {r.max():.1f} | "
        + " | ".join(f"**{int((r > t).sum())}**" for t in REACH_THRESHOLDS_PX) + " |"
    )

    # Largest owner of length per image, the "cyan cell" kind of case.
    lines += ["", "## Largest owner of skeleton length in each image", "",
              "| image | cell | at (x,y) | lacuna area px2 | owned length px | share of image owned length | reach px |",
              "|---|---|---|---|---|---|---|"]
    for s in states:
        tot = {}
        for e in s["edges"]:
            tot[e["cell"]] = tot.get(e["cell"], 0.0) + e["length"]
        cell = max(tot, key=tot.get)
        share = tot[cell] / sum(tot.values())
        reach = max(e["exit"] for e in s["edges"] if e["cell"] == cell)
        x, y = s["centroids"][cell]
        lines.append(f"| {s['image']} | {cell} | ({x:.0f},{y:.0f}) | {s['areas'][cell]:.0f} | "
                     f"{tot[cell]:.0f} | {100 * share:.1f}% | {reach:.0f} |")

    # Retention curve and the cap rule.
    total = all_len.sum()
    retained = {c: float(all_len[all_entry <= c].sum() / total) for c in CAP_GRID_PX}
    order = np.argsort(all_entry)
    cum = np.cumsum(all_len[order]) / total
    exact = float(all_entry[order][np.searchsorted(cum, RETAIN_FRACTION)])
    chosen = next(c for c in CAP_GRID_PX if retained[c] >= RETAIN_FRACTION)
    lines += [
        "", "## Owned length retained under a cap (pooled over 8 images)", "",
        "Rule: an edge stays owned if its entry distance is <= the cap (kept whole).", "",
        "| cap px | owned length retained |", "|---|---|",
    ]
    for c in CAP_GRID_PX:
        if c <= chosen + 100 or c % 100 == 0:
            lines.append(f"| {c} | {100 * retained[c]:.1f}% |")
    lines += [
        "",
        f"**Selection rule** (set for the overnight run): the smallest cap that leaves at least "
        f"{100 * RETAIN_FRACTION:.0f}% of pooled owned skeleton length owned, rounded to a multiple of 25 px.",
        "",
        f"- Exact smallest cap reaching {100 * RETAIN_FRACTION:.0f}%: **{exact:.1f} px** "
        "(the length-weighted 90th percentile of entry distance).",
        f"- Rounded UP to the next multiple of 25 so the {100 * RETAIN_FRACTION:.0f}% floor still holds: "
        f"**{chosen} px**, which retains {100 * retained[chosen]:.1f}%.",
        (
            f"  Rounding to the nearest multiple gives the same value here, so the two readings "
            "of the rule agree."
            if int(25 * round(exact / 25)) == chosen
            else f"  Rounding to the NEAREST multiple would give {int(25 * round(exact / 25))} px, retaining "
            f"{100 * retained.get(int(25 * round(exact / 25)), float('nan')):.1f}%, below the floor, "
            "so rounding up is the reading used here."
        ),
    ]

    # Every cell of the image the problem was reported on, with the colour
    # it is drawn in on verification.png (canaliculi_v1.lacuna_colors), so
    # "the cyan cell" can be matched to an id.
    lines += ["", "## 682_z29 cells by verification colour", "",
              "| cell | colour (RGB) | lacuna area px2 | at (x,y) | owned length px | reach px |",
              "|---|---|---|---|---|---|"]
    s = next(s for s in states if s["image"].startswith("682_z29"))
    colours = can.lacuna_colors(len(s["on_border"]))
    tot, reach = {}, {}
    for e in s["edges"]:
        tot[e["cell"]] = tot.get(e["cell"], 0.0) + e["length"]
        reach[e["cell"]] = max(reach.get(e["cell"], 0.0), e["exit"])
    for cell in sorted(s["on_border"], key=lambda c: -tot.get(c, 0.0)):
        x, y = s["centroids"][cell]
        lines.append(f"| {cell} | {colours[cell]} | {s['areas'][cell]:.0f} | ({x:.0f},{y:.0f}) | "
                     f"{tot.get(cell, 0.0):.0f} | {reach.get(cell, 0.0):.0f} |")
    lines += ["", "Cyan on the overlay is (25, 202, 255), cell 8."]

    text = "\n".join(lines) + "\n"
    print("\n" + text)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "step1_reach.md").write_text(text, encoding="utf-8")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "reach_edges.json", "w") as f:
        json.dump({"status": "pre-validation", "units": "px", "chosen_cap_px": chosen,
                   "exact_cap_px": exact, "retained": retained,
                   "images": [{"image": s["image"], "edges": s["edges"]} for s in states]}, f)


if __name__ == "__main__":
    main()
