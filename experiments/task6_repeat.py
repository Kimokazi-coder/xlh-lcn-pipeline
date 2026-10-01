"""Task 6.1: repeatability across images. Ownership is not changed.

    python -u experiments/task6_repeat.py 6.1

Lacunae are matched between every pair of images by centroid, one to one
(mutual nearest neighbours) within 25 px, with no shift or registration.
Field groups are derived from the match counts, not from file names. For
matched cells: roots, ring 30 px, ring 60 px, owned length and edge count,
with absolute and relative differences; and field density per image.

Outputs in results_experiments/task6/. PRE-VALIDATION, PIXEL units,
(x, y) = (column, row).
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402

OUT = C.OUT_ROOT / "task6"
MATCH_RADIUS_PX = 25  # from the task text
MEASURES = ["roots_count", "ring_length_r30_px", "ring_length_r60_px", "owned_length_px", "edge_count"]
SHAPE = ["area_px2", "aspect_ratio", "solidity"]


def table(d) -> pd.DataFrame:
    rows = []
    for l, c in zip(d["lacuna_rows"], d["cell_rows"]):
        rows.append({"lacuna_id": l["lacuna_id"], "x": l["centroid_col_px"], "y": l["centroid_row_px"],
                     "on_border": l["on_border"], **{k: l[k] for k in SHAPE}, **{k: c[k] for k in MEASURES}})
    return pd.DataFrame(rows)


def mutual_matches(a: pd.DataFrame, b: pd.DataFrame, radius: float) -> list[tuple[int, int, float]]:
    pa, pb = a[["x", "y"]].to_numpy(), b[["x", "y"]].to_numpy()
    if len(pa) == 0 or len(pb) == 0:
        return []
    dist = np.hypot(pa[:, None, 0] - pb[None, :, 0], pa[:, None, 1] - pb[None, :, 1])
    out = []
    for i in range(len(pa)):
        j = int(np.argmin(dist[i]))
        if dist[i, j] <= radius and int(np.argmin(dist[:, j])) == i:
            out.append((i, j, float(dist[i, j])))
    return out


def item_6_1() -> None:
    data = {C.short(p): C.load(p) for p in C.IMAGE_PATHS}
    tabs = {k: table(v) for k, v in data.items()}
    names = list(tabs)

    # Pairwise match counts, and the chance level for comparison: the
    # expected number of a's centroids that land within the radius of one of
    # b's by chance, n_a * n_b * pi r^2 / field area.
    pair_rows = []
    for a, b in itertools.combinations(names, 2):
        m = mutual_matches(tabs[a], tabs[b], MATCH_RADIUS_PX)
        na, nb = len(tabs[a]), len(tabs[b])
        dx = [tabs[b].iloc[j].x - tabs[a].iloc[i].x for i, j, _ in m]
        dy = [tabs[b].iloc[j].y - tabs[a].iloc[i].y for i, j, _ in m]
        pair_rows.append({"image_a": a, "image_b": b, "n_a": na, "n_b": nb, "matches": len(m),
                          "match_fraction_of_smaller": len(m) / min(na, nb),
                          "chance_expected": na * nb * np.pi * MATCH_RADIUS_PX ** 2 / (1024 * 1024),
                          "median_distance_px": float(np.median([t[2] for t in m])) if m else float("nan"),
                          "median_dx_px": float(np.median(dx)) if m else float("nan"),
                          "median_dy_px": float(np.median(dy)) if m else float("nan")})
    pairs = pd.DataFrame(pair_rows)
    C.write_csv(OUT / "6.1_pair_matches.csv", pairs)

    # Field groups: connected components of the graph whose edges are the
    # pairs with a match fraction above the largest gap in the sorted
    # fractions (printed in the report with the gap).
    fr = np.sort(pairs.match_fraction_of_smaller.to_numpy())
    gaps = np.diff(fr)
    k = int(np.argmax(gaps))
    cut = (fr[k] + fr[k + 1]) / 2
    linked = pairs[pairs.match_fraction_of_smaller > cut]
    parent = {n: n for n in names}

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x

    for _, r in linked.iterrows():
        parent[find(r.image_a)] = find(r.image_b)
    groups: dict = {}
    for n in names:
        groups.setdefault(find(n), []).append(n)
    group_list = sorted(groups.values(), key=lambda g: g[0])

    # Matched cells within each group, all pairs of images.
    cell_rows = []
    for g in group_list:
        for a, b in itertools.combinations(g, 2):
            for i, j, dist in mutual_matches(tabs[a], tabs[b], MATCH_RADIUS_PX):
                ra, rb = tabs[a].iloc[i], tabs[b].iloc[j]
                row = {"group": "+".join(g), "image_a": a, "image_b": b, "id_a": int(ra.lacuna_id),
                       "id_b": int(rb.lacuna_id), "xy_a": f"({ra.x:.0f},{ra.y:.0f})", "xy_b": f"({rb.x:.0f},{rb.y:.0f})",
                       "distance_px": dist, "both_interior": (not ra.on_border) and (not rb.on_border)}
                for mname in SHAPE + MEASURES:
                    va, vb = float(ra[mname]), float(rb[mname])
                    row[f"{mname}_a"] = va
                    row[f"{mname}_b"] = vb
                    row[f"{mname}_absdiff"] = abs(va - vb)
                    mean = (va + vb) / 2
                    row[f"{mname}_reldiff"] = abs(va - vb) / mean if mean else float("nan")
                cell_rows.append(row)
    cells = pd.DataFrame(cell_rows)
    C.write_csv(OUT / "6.1_matched_cells.csv", cells)

    inter = cells[cells.both_interior]
    stab = []
    for mname in SHAPE + MEASURES:
        a, b = inter[f"{mname}_a"].to_numpy(), inter[f"{mname}_b"].to_numpy()
        rho = spearmanr(a, b)[0] if len(a) > 3 else float("nan")
        stab.append({"measure": mname, "pairs": len(a),
                     "median_abs_diff": float(np.median(inter[f"{mname}_absdiff"])),
                     "median_rel_diff": float(np.median(inter[f"{mname}_reldiff"])),
                     "p90_rel_diff": float(np.quantile(inter[f"{mname}_reldiff"], 0.9)),
                     "spearman_a_vs_b": rho})
    stab = pd.DataFrame(stab)
    C.write_csv(OUT / "6.1_stability.csv", stab)

    per_pair = inter.groupby(["image_a", "image_b"]).agg(
        matched=("id_a", "size"),
        roots_rel=("roots_count_reldiff", "median"), ring30_rel=("ring_length_r30_px_reldiff", "median"),
        ring60_rel=("ring_length_r60_px_reldiff", "median"), owned_rel=("owned_length_px_reldiff", "median"),
        edges_rel=("edge_count_reldiff", "median"), area_rel=("area_px2_reldiff", "median")).reset_index()

    dens = []
    for g in group_list:
        vals = {n: data[n]["field"]["canalicular_length_density_per_px"] for n in g}
        for n in g:
            dens.append({"group": "+".join(g), "image": n, "field_density": vals[n],
                         "lacuna_count": data[n]["lacuna_count"],
                         "group_mean_density": float(np.mean(list(vals.values()))),
                         "rel_diff_from_group_mean": (vals[n] - np.mean(list(vals.values()))) / np.mean(list(vals.values()))})
    dens = pd.DataFrame(dens)
    C.write_csv(OUT / "6.1_field_density_by_group.csv", dens)

    pairs_sorted = pairs.sort_values("match_fraction_of_smaller", ascending=False)
    md = ["# 6.1 Repeatability across images", "",
          "Pre-validation, px. Lacunae are matched between every pair of images by centroid, one to one",
          f"(mutual nearest neighbours) within {MATCH_RADIUS_PX} px, with no shift. chance_expected is the",
          "number of matches expected by chance from two random sets of the same sizes. Ownership is the",
          "pipeline's, unchanged.", "",
          "## Pairwise matches", "",
          C.md_table(pairs_sorted, floatfmt="{:.3g}"), "",
          f"Sorted match fractions: {', '.join(f'{v:.2f}' for v in fr)}. The largest gap is between "
          f"{fr[k]:.2f} and {fr[k + 1]:.2f}; pairs above {cut:.2f} are linked.", "",
          "## Field groups derived from the matches", ""]
    for g in group_list:
        md.append(f"- {' + '.join(g)}")
    md += ["", "## Stability of each measure over matched cells (both interior)", "",
           "rel_diff is |a - b| / mean(a, b) for one matched cell seen in two images.", "",
           C.md_table(stab, floatfmt="{:.3f}"), "",
           "Median relative difference per image pair:", "",
           C.md_table(per_pair, floatfmt="{:.3f}"), "",
           "## Field density per image within each group", "",
           C.md_table(dens, floatfmt="{:.4f}"), "",
           "Every matched pair with its values is in `6.1_matched_cells.csv`.", ""]
    C.write_text_once(OUT / "6.1_repeatability.md", "\n".join(md))
    print("\n".join(md))


ITEMS = {"6.1": item_6_1}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    item = sys.argv[1]
    ok = C.run_item(item, ITEMS[item])
    sys.exit(0 if ok else 1)
