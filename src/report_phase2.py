"""READ-ONLY Phase 2 comparison: fragmentation-reduction settings.

Runs the canaliculi pipeline under several PREPROCESS_MODE /
THRESHOLD_MODE / GAP_BRIDGING combinations and reports the guard metrics
for each, on the tuning and held-out sets separately. Changes no default;
writes only reports and crops.

GUARDS, fixed in writing before any setting was run (see
DECISIONS_NEEDED.md D0):
  G1 total skeleton length  FLAG if > 1.20x the default
  G2 loop count (E-V+C)     FLAG if > max(1.5x default, default + 50)
Owned length fraction, components per 10k and degree-1 fraction are
SECONDARY readouts. Phase 0(c) found only 21% of endpoint-to-neighbour
angles are under 20 degrees, so most nearest neighbours are parallel
threads; fusing them raises the owned fraction and looks like success.
Owned fraction alone can never justify a setting.

The lacuna segmentation is identical across settings, so it is computed
once per image and reused -- it is 7.5 of the 9.5 seconds an image costs.

Usage:
    python src/report_phase2.py --dir data/WT
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
from skimage import measure, morphology
from skimage.io import imsave

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from count_lacunae import load_channel  # noqa: E402
import canaliculi_v1 as can  # noqa: E402
import exclusion_mask as excl  # noqa: E402
import gap_bridging as gb  # noqa: E402
import segment_lacunae_v2 as seg2  # noqa: E402
import diagnose_canaliculi_v2 as diag  # noqa: E402

TUNING_IMAGE_STEMS = diag.TUNING_IMAGE_STEMS
CROP_SIZE_PX = diag.CROP_SIZE_PX
OUT_DIR = config.RESULTS_DIR / "diagnostics" / "phase2"

# Guard thresholds. See the module docstring and DECISIONS_NEEDED.md D0.
GUARD_LENGTH_RATIO = 1.20
GUARD_LOOP_RATIO = 1.50
GUARD_LOOP_FLOOR = 50

# (label, preprocess, threshold_mode, gap_bridging). Run in the order the
# brief sets: hysteresis alone, ridge alone, ridge+hysteresis, then
# bridging on top of the best of those.
# (label, preprocess, threshold_mode, gap_bridging, overrides)
# `overrides` temporarily sets canaliculi_v1 module constants for that
# setting only, and is restored afterwards -- this is how the gentler
# hysteresis variant is tested without touching any default.
SETTINGS = [
    ("default", "tophat", "multiotsu_low", False, {}),
    ("hysteresis", "tophat", "hysteresis", False, {}),
    ("hyst-0.75", "tophat", "hysteresis", False, {"HYSTERESIS_LOW_FRACTION": 0.75}),
    ("ridge", "ridge", "multiotsu_low", False, {}),
    ("ridge+hyst", "ridge", "hysteresis", False, {}),
    ("default+bridge", "tophat", "multiotsu_low", True, {}),
    ("ridge+bridge", "ridge", "multiotsu_low", True, {}),
    ("hyst0.75+bridge", "tophat", "hysteresis", True, {"HYSTERESIS_LOW_FRACTION": 0.75}),
]


def image_state(path: Path) -> dict:
    """Everything that does not depend on the setting, computed once."""
    display, channel = load_channel(path)
    _d2, labels, kept, _t_hi = seg2.segment_image(path)
    lacuna_mask, lacuna_id_map = can.build_lacuna_maps(labels, kept)
    dist_to_lacuna, nearest_id = can.nearest_lacuna_map(lacuna_id_map)
    flagged, _info = excl.auto_exclusion(channel, labels)
    return {
        "path": path,
        "stem": path.stem,
        "display": display,
        "channel": channel,
        "labels": labels,
        "kept": kept,
        "lacuna_mask": lacuna_mask,
        "lacuna_id_map": lacuna_id_map,
        "dist_to_lacuna": dist_to_lacuna,
        "nearest_id": nearest_id,
        "flagged": flagged,
    }


def run_setting(state: dict, preprocess: str, threshold_mode: str, bridging: bool) -> dict:
    """One setting on one image: mask, skeleton, graph and guard metrics."""
    channel = state["channel"]
    candidate, t_lo = can.canaliculi_candidate_mask(
        channel, state["lacuna_mask"], preprocess, threshold_mode
    )
    skeleton = morphology.skeletonize(candidate)

    n_bridges = 0
    if bridging:
        preprocessed = can.preprocess_channel(channel, preprocess)
        bridges = gb.find_bridges(skeleton, preprocessed, t_lo, state["lacuna_mask"])
        n_bridges = len(bridges)
        if bridges:
            candidate = gb.apply_bridges(candidate, bridges)
            skeleton = morphology.skeletonize(candidate)

    cell_ids = list(range(1, len(state["kept"]) + 1))
    G, _skel_obj = can.build_network_graph(skeleton)
    can.clean_network_graph(G, state["dist_to_lacuna"])
    can.attach_lacunae(G, state["dist_to_lacuna"], state["nearest_id"], cell_ids)
    owner, node_dist = can.assign_by_connectivity(G, cell_ids)
    edge_owner = can.assign_edges(G, owner, node_dist)

    real = can._real_subgraph(G)
    total_graph_len = float(sum(w for _u, _v, w in real.edges(data="weight")))
    owned_graph_len = 0.0
    for edge in edge_owner:
        u, v = tuple(edge)
        if real.has_edge(u, v):
            owned_graph_len += float(real[u][v]["weight"])
    degrees = np.array([real.degree(n) for n in real.nodes()], dtype=int)

    # Loops = cyclomatic number E - V + C of the real skeleton graph. A
    # forest gives 0; each fused pair of neighbouring threads adds one.
    import networkx as nx

    n_comp_graph = nx.number_connected_components(real) if real.number_of_nodes() else 0
    loops = real.number_of_edges() - real.number_of_nodes() + n_comp_graph

    comp_labels = measure.label(skeleton, connectivity=2)
    n_components = int(comp_labels.max())
    skel_px = int(skeleton.sum())

    return {
        "candidate": candidate,
        "skeleton": skeleton,
        "skel_px": skel_px,
        "n_components": n_components,
        "components_per_10k": (10000.0 * n_components / skel_px) if skel_px else 0.0,
        "loops": int(loops),
        "deg1_fraction": float((degrees == 1).mean()) if degrees.size else 0.0,
        "total_graph_len": total_graph_len,
        "owned_len_fraction": (owned_graph_len / total_graph_len) if total_graph_len else 0.0,
        "n_bridges": n_bridges,
        "owner_map": can.build_owner_pixel_map(skeleton.shape, _skel_obj, G, edge_owner, owner),
    }


def fusion_guard(state: dict, result: dict) -> dict:
    """Straight-line fusion guard: the longest skeleton component overall,
    and inside the Phase 1 flagged region, the longest component and its
    longest straight run. A setting that stitches a flagged structure's
    fragments into one long line shows up here as a jump in both."""
    comp_labels = measure.label(result["skeleton"], connectivity=2)
    regions = measure.regionprops(comp_labels)
    longest_overall = max((r.area for r in regions), default=0)

    flagged = state["flagged"]
    if not flagged.any():
        return {"longest_overall": int(longest_overall), "longest_in_flagged": 0, "longest_straight": 0.0}

    inside = result["skeleton"] & flagged
    if not inside.any():
        return {"longest_overall": int(longest_overall), "longest_in_flagged": 0, "longest_straight": 0.0}
    in_labels = measure.label(inside, connectivity=2)
    best_area, best_straight = 0, 0.0
    for region in measure.regionprops(in_labels):
        if region.area > best_area:
            best_area = int(region.area)
        best_straight = max(best_straight, diag._max_centre_distance(region.coords))
    return {
        "longest_overall": int(longest_overall),
        "longest_in_flagged": best_area,
        "longest_straight": float(best_straight),
    }


def save_setting_crops(state: dict, result: dict, origins: dict, label: str) -> None:
    out_dir = OUT_DIR / state["stem"].replace(" ", "_")
    out_dir.mkdir(parents=True, exist_ok=True)
    panel_state = {
        "channel": state["channel"],
        "candidate": result["candidate"],
        "skeleton": result["skeleton"],
        "display": state["display"],
        "lacuna_id_map": state["lacuna_id_map"],
        "kept": state["kept"],
        "owner_map": result["owner_map"],
    }
    for name, origin in origins.items():
        diag.save_crop_panel(panel_state, origin, CROP_SIZE_PX, out_dir / f"crop_{name}_{label}.png")


def pooled(rows: list[dict], key: str) -> float:
    return float(np.mean([r[key] for r in rows])) if rows else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 2 setting comparison (read-only).")
    parser.add_argument("--dir", type=Path, required=True)
    args = parser.parse_args()

    started = time.time()
    print("=" * 112)
    print("PHASE 2 COMPARISON -- v1-raw / pre-validation, PIXEL units. Read-only, no default changed.")
    print(f"GUARDS (fixed before running): G1 length > {GUARD_LENGTH_RATIO}x default;  "
          f"G2 loops > max({GUARD_LOOP_RATIO}x default, default+{GUARD_LOOP_FLOOR})")
    print("=" * 112)

    results: dict[str, dict[str, dict]] = {}
    guards: dict[str, dict[str, dict]] = {}
    for path in sorted(args.dir.glob("*.tif")):
        t0 = time.time()
        state = image_state(path)
        origins = diag.pick_crop_origins(
            {"skeleton": morphology.skeletonize(
                can.canaliculi_candidate_mask(state["channel"], state["lacuna_mask"], "tophat")[0]),
             "lacuna_mask": state["lacuna_mask"]},
            CROP_SIZE_PX,
        )
        if path.stem == "542 WT  2_z06c1-2":
            half = CROP_SIZE_PX // 2
            origins["x555_y500"] = (500 - half, 555 - half)

        results[path.stem] = {}
        guards[path.stem] = {}
        for label, preprocess, threshold_mode, bridging, overrides in SETTINGS:
            saved = {k: getattr(can, k) for k in overrides}
            for k, v in overrides.items():
                setattr(can, k, v)
            try:
                result = run_setting(state, preprocess, threshold_mode, bridging)
            finally:
                for k, v in saved.items():
                    setattr(can, k, v)
            results[path.stem][label] = {k: v for k, v in result.items() if k not in ("candidate", "skeleton", "owner_map")}
            guards[path.stem][label] = fusion_guard(state, result)
            save_setting_crops(state, result, origins, label)
        print(f"  {path.name:26s} {len(SETTINGS)} settings in {time.time() - t0:5.1f}s")

    def report(labels: list[str]) -> None:
        for set_name, is_tuning in (("TUNING", True), ("HELD-OUT", False)):
            stems = [s for s in results if (s in TUNING_IMAGE_STEMS) == is_tuning]
            print(f"\n-- {set_name} set (n={len(stems)} images)")
            print(f'{"setting":15s} {"skel_px":>9s} {"vs def":>7s} {"loops":>7s} {"vs def":>8s} '
                  f'{"comp/10k":>9s} {"deg1_f":>7s} {"owned_f":>8s} {"bridges":>7s}  guards')
            base = [results[s]["default"] for s in stems]
            base_len, base_loops = pooled(base, "skel_px"), pooled(base, "loops")
            for label in labels:
                rows = [results[s][label] for s in stems]
                length, loops = pooled(rows, "skel_px"), pooled(rows, "loops")
                len_ratio = length / base_len if base_len else 0.0
                loop_limit = max(GUARD_LOOP_RATIO * base_loops, base_loops + GUARD_LOOP_FLOOR)
                flags = []
                if length > GUARD_LENGTH_RATIO * base_len:
                    flags.append("G1-LENGTH")
                if loops > loop_limit:
                    flags.append("G2-LOOPS")
                verdict = "  ".join(flags) if flags else "ok"
                loop_ratio = f"{loops / base_loops:.2f}x" if base_loops else "n/a"
                bridges = pooled(rows, "n_bridges")
                print(f'{label:15s} {length:9.0f} {len_ratio:6.2f}x {loops:7.0f} {loop_ratio:>8s} '
                      f'{pooled(rows, "components_per_10k"):9.1f} {pooled(rows, "deg1_fraction"):7.3f} '
                      f'{pooled(rows, "owned_len_fraction"):8.3f} {bridges:7.0f}  {verdict}')

    print("\n" + "=" * 112)
    print("GUARD METRICS")
    print("=" * 112)
    report([s[0] for s in SETTINGS])

    print("\n" + "=" * 112)
    print("STRAIGHT-LINE FUSION GUARD (images with a Phase 1 flagged structure)")
    print("=" * 112)
    print(f'{"image":22s} {"setting":13s} {"longest comp":>13s} {"longest in flagged":>19s} {"longest straight":>17s}')
    for stem in guards:
        if all(g["longest_in_flagged"] == 0 for g in guards[stem].values()):
            continue
        for label in [s[0] for s in SETTINGS]:
            g = guards[stem][label]
            print(f'{stem[:22]:22s} {label:13s} {g["longest_overall"]:13d} '
                  f'{g["longest_in_flagged"]:19d} {g["longest_straight"]:17.1f}')

    print(f"\ntotal elapsed {time.time() - started:.0f}s")
    print(f"crops written under {OUT_DIR}")


if __name__ == "__main__":
    main()
