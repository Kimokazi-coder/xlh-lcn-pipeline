"""Diagnostics for the LCN pipeline, one subcommand each.

Read-only: nothing here writes pipeline outputs. PRE-VALIDATION, PIXEL units.

Subcommands:
    reference-check   run 543-2 and check the three regression numbers
    compare-outputs   compare two results folders number by number
    reach             how far through the network each cell's owned threads
                      reach (median, p90, max per cell)
    lacuna-table      per-lacuna area, solidity, aspect ratio and roots for
                      one image
    sanity            pooled edge-length and node-degree shape checks against
                      what a real canalicular network looks like
    regression        regenerate every image with the current config into an
                      ignored folder and compare every json and summary number
                      with results/ at tolerance 0
    switch-check      turn each switch of config.py on alone, regenerate every
                      image and list what changes against results/
    fast-check        the fast lacuna stage against the original one: identical
                      labels at t_hi scaled 0.8 to 1.2, and the timing

Usage (from the repo root):
    python src/diagnostics.py reference-check
    python src/diagnostics.py compare-outputs results OTHER_FOLDER
    python src/diagnostics.py reach --dir data/WT
    python src/diagnostics.py lacuna-table --image "data/WT/543-2.tif"
    python src/diagnostics.py sanity --dir data/WT
    python src/diagnostics.py regression
    python src/diagnostics.py switch-check
    python src/diagnostics.py fast-check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import networkx as nx
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canaliculi  # noqa: E402
import lacunae  # noqa: E402

DEFAULT_IMAGE_DIR = config.DATA_DIR / "WT"


def print_table(header: list[str], rows: list[list], title: str | None = None) -> None:
    """Plain fixed-width table."""
    cells = [[str(h) for h in header]] + [[str(c) for c in row] for row in rows]
    widths = [max(len(r[i]) for r in cells) for i in range(len(header))]
    if title:
        print(title)
    line = "  ".join("-" * w for w in widths)
    print("  ".join(h.ljust(w) for h, w in zip(cells[0], widths)))
    print(line)
    for row in cells[1:]:
        print("  ".join(c.ljust(w) for c, w in zip(row, widths)))


def add_images_arguments(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--image", type=Path, help="One .tif image.")
    group.add_argument("--dir", type=Path, help=f"A folder of .tif images (default: {DEFAULT_IMAGE_DIR}).")


def images_from(args) -> list[Path]:
    if args.image is None and args.dir is None:
        args.dir = DEFAULT_IMAGE_DIR
    return lacunae.image_paths(args)


# reference-check ---------------------------------------------------------------

REFERENCE_IMAGE = DEFAULT_IMAGE_DIR / "543-2.tif"

# The regression check for the default pipeline, fixed on 2026-09-28 when
# hysteresis and gap bridging became the defaults (before that it was 37.00
# and 29.43 px with no bridges). Means are over interior lacunae, rounded to
# 2 decimals.
REFERENCE_VALUES = [
    ("edges per interior cell (mean edge_count)", 62.33),
    ("mean edge length, px (interior mean of mean_edge_length_px)", 27.41),
    ("gap bridges added", 21),
]


def cmd_reference_check(args) -> int:
    result = canaliculi.analyse_image(args.image)
    s = result["summary"]
    measured = [
        round(s["edge_count"]["mean"], 2),
        round(s["mean_edge_length_px"]["mean"], 2),
        len(result["bridges"]),
    ]
    rows, ok = [], True
    for (name, expected), value in zip(REFERENCE_VALUES, measured):
        passed = value == expected
        ok &= passed
        rows.append([name, expected, value, "PASS" if passed else "FAIL"])
    print_table(["quantity", "expected", "measured", "result"], rows,
                title=f"Reference check on {args.image.name} (pre-validation, px)")
    print(f"\n{'PASS' if ok else 'FAIL'}: {sum(r[3] == 'PASS' for r in rows)} of {len(rows)} reference numbers match.")
    return 0 if ok else 1


# compare-outputs ---------------------------------------------------------------

LACUNA_SHAPE_KEYS = [f for f in lacunae.LACUNA_MEASUREMENT_FIELDS if f != "lacuna_id"]
LACUNA_SUMMARY_KEYS = [f for f, _u in lacunae.LACUNA_SUMMARY_METRICS]
CELL_KEYS = [f for f, _u, _k in canaliculi.CELL_METRICS]


def numbers_from_results(image_dir: Path) -> dict:
    """The canonical numbers of one image folder in the results layout."""
    lac = json.load(open(image_dir / "lacunae.json"))
    can = json.load(open(image_dir / "canaliculi_measurements.json"))
    per_lacuna = {}
    for lrow, crow in zip(lac["lacunae"], can["lacunae"]):
        row = {k: lrow[k] for k in LACUNA_SHAPE_KEYS}
        row.update({k: crow[k] for k in CELL_KEYS})
        per_lacuna[str(lrow["lacuna_id"])] = row
    if len(lac["lacunae"]) != len(can["lacunae"]):
        per_lacuna["row_count_mismatch"] = [len(lac["lacunae"]), len(can["lacunae"])]
    return {
        "lacuna_count": lac["lacuna_count"],
        "interior_lacuna_count": lac["interior_lacuna_count"],
        "n_bridges": can["n_bridges"],
        "lacunae_summary": {k: lac["summary"][k] for k in LACUNA_SUMMARY_KEYS},
        "canaliculi_summary": {k: can["summary"][k] for k in CELL_KEYS},
        "field": dict(can["field"]),
        "per_lacuna": per_lacuna,
    }


def load_numbers(folder: Path) -> dict:
    """{image folder name: canonical numbers} for a results folder. A folder
    holding numbers.json (a saved reference snapshot) is read as is."""
    out = {}
    for sub in sorted(p for p in folder.iterdir() if p.is_dir()):
        if (sub / "lacunae.json").is_file() and (sub / "canaliculi_measurements.json").is_file():
            out[sub.name] = numbers_from_results(sub)
        elif (sub / "numbers.json").is_file():
            out[sub.name] = json.load(open(sub / "numbers.json"))
    return out


def flatten(value, prefix: str = "") -> dict:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
        return out
    return {prefix: value}


def same(a, b, tolerance: float) -> bool:
    numeric = (int, float)
    if isinstance(a, bool) or isinstance(b, bool) or not isinstance(a, numeric) or not isinstance(b, numeric):
        return a == b
    return abs(a - b) <= tolerance


def cmd_compare_outputs(args) -> int:
    a, b = load_numbers(args.a), load_numbers(args.b)
    if not a or not b:
        print(f"No comparable image folders found in {args.a if not a else args.b}.")
        return 1

    rows, differences, ok = [], [], True
    for name in sorted(set(a) | set(b)):
        if name not in a or name not in b:
            ok = False
            rows.append([name, 0, 0, 0, "-", "-", f"only in {'A' if name in a else 'B'}"])
            continue
        fa, fb = flatten(a[name]), flatten(b[name])
        keys = sorted(set(fa) | set(fb))
        missing = [k for k in keys if k not in fa or k not in fb]
        compared = [k for k in keys if k in fa and k in fb]
        differ = [k for k in compared if not same(fa[k], fb[k], args.tolerance)]
        numeric = [abs(fa[k] - fb[k]) for k in compared
                   if isinstance(fa[k], (int, float)) and isinstance(fb[k], (int, float))
                   and not isinstance(fa[k], bool) and not isinstance(fb[k], bool)]
        max_diff = max(numeric) if numeric else 0.0
        status = "MATCH" if not differ and not missing else "DIFFER"
        ok &= status == "MATCH"
        rows.append([name, len(compared), len(compared) - len(differ), len(differ), len(missing), f"{max_diff:g}", status])
        differences += [(name, k, fa.get(k, "<missing>"), fb.get(k, "<missing>")) for k in missing + differ]

    print_table(["image", "compared", "equal", "differ", "missing", "max abs diff", "result"], rows,
                title=f"A = {args.a}\nB = {args.b}\ntolerance = {args.tolerance:g}\n")
    if differences:
        print(f"\nFirst {min(len(differences), args.show)} of {len(differences)} differences:")
        print_table(["image", "number", "A", "B"], [list(d) for d in differences[:args.show]])
    total = sum(r[1] for r in rows if isinstance(r[1], int))
    print(f"\n{'MATCH' if ok else 'DIFFER'}: {total} numbers compared over {len(rows)} images.")
    return 0 if ok else 1


# reach -------------------------------------------------------------------------

def owned_thread_distances(result: dict) -> dict:
    """{cell id: [graph distance (px) from the cell to the far end of each
    owned thread]}. The owning cell reaches a thread at the nearer end's
    node_dist (which includes the attachment gap); the far end lies one edge
    length further along it."""
    G, node_dist = result["graph"], result["node_dist"]
    out: dict = {}
    for edge, cell in result["edge_owner"].items():
        u, v = tuple(edge)
        entry = min(node_dist.get(u, np.inf), node_dist.get(v, np.inf))
        out.setdefault(cell, []).append(entry + float(G[u][v]["weight"]))
    return out


def cmd_reach(args) -> int:
    rows, pooled = [], []
    for path in images_from(args):
        result = canaliculi.analyse_image(path)
        per_cell = owned_thread_distances(result)
        lac_rows = result["lacunae"]["rows"]
        for m in lac_rows:
            d = np.array(per_cell.get(m["lacuna_id"], []))
            pooled += d.tolist()
            rows.append([
                lacunae.clean_name(path), m["lacuna_id"],
                f"({m['centroid_col_px']:.0f},{m['centroid_row_px']:.0f})",
                "yes" if m["on_border"] else "", d.size,
                f"{np.median(d):.1f}" if d.size else "-",
                f"{np.percentile(d, 90):.1f}" if d.size else "-",
                f"{d.max():.1f}" if d.size else "-",
            ])
    print_table(["image", "cell", "at (x,y)", "border", "owned threads", "median px", "p90 px", "max px"], rows,
                title="Graph distance from each cell to the far end of each thread it owns "
                      "(pre-validation, px; ownership has no distance cap)\n")
    p = np.array(pooled)
    if p.size:
        print(f"\nPOOLED over {len(rows)} cells and {p.size} owned threads: median {np.median(p):.1f} px, "
              f"p90 {np.percentile(p, 90):.1f} px, max {p.max():.1f} px")
    return 0


# lacuna-table -----------------------------------------------------------------

def cmd_lacuna_table(args) -> int:
    result = canaliculi.analyse_image(args.image)
    roots = {m["lacuna_id"]: m["roots_count"] for m in result["rows"]}
    rows = [
        [m["lacuna_id"], f"({m['centroid_col_px']:.0f},{m['centroid_row_px']:.0f})", f"{m['area_px2']:.0f}",
         f"{m['solidity']:.3f}", f"{m['aspect_ratio']:.2f}", roots[m["lacuna_id"]], "yes" if m["on_border"] else ""]
        for m in result["lacunae"]["rows"]
    ]
    print_table(["lacuna", "at (x,y)", "area px^2", "solidity", "aspect", "roots", "border"], rows,
                title=f"Kept lacunae in {args.image.name} (pre-validation, px)\n")
    return 0


# sanity -----------------------------------------------------------------------
# Literature shape of a real canalicular network: branch points are
# overwhelmingly 3-way, and the canaliculi between them are mostly short, so
# edge lengths are right-skewed. Modelled on OCY_get_network_params.m
# (n.dist_edge, n.hbz, n.mean_deg, n.t_nodes). Shape checks only: with no
# um/px calibration no absolute length can be compared with a published one.
SANITY_EDGE_LEN_BINS_PX = (5, 10, 20, 40, 80, 160)
SANITY_MIN_DEG3_FRACTION_OF_JUNCTIONS = 0.8
SANITY_MIN_SKEW_RATIO = 1.2  # mean / median of edge length
# In a connected tree-like network, thread ends are a minority of nodes.
SANITY_MAX_DEG1_FRACTION = 0.5


def cmd_sanity(args) -> int:
    all_lengths, owned_lengths, all_degrees = [], [], []
    tree_nodes = junction_nodes = 0
    rows = []
    for path in images_from(args):
        result = canaliculi.analyse_image(path)
        real = canaliculi.real_subgraph(result["graph"])
        edge_owner = result["edge_owner"]
        for u, v, w in real.edges(data="weight"):
            all_lengths.append(float(w))
            if frozenset((u, v)) in edge_owner:
                owned_lengths.append(float(w))
        clustering = nx.clustering(real)
        for node in real.nodes():
            degree = real.degree(node)
            all_degrees.append(degree)
            if degree >= 3:
                junction_nodes += 1
                if degree == 3 and clustering[node] == 0:
                    tree_nodes += 1
        f = result["field"]
        rows.append([lacunae.clean_name(path), real.number_of_nodes(), real.number_of_edges(), len(edge_owner),
                     nx.number_connected_components(real), f["skeleton_component_count"],
                     f"{f['canalicular_length_density_per_px']:.5f}"])
    print_table(["image", "nodes", "edges", "owned edges", "graph components", "skeleton components",
                 "length density px^-1"], rows, title="Network sanity report (pre-validation, px)\n")

    lines = []
    for label, lengths in (("all edges", all_lengths), ("cell-owned edges", owned_lengths)):
        arr = np.array(lengths, dtype=float)
        if arr.size:
            q = np.percentile(arr, [10, 50, 90])
            lines.append([label, arr.size, f"{arr.mean():.1f}", f"{q[0]:.1f}", f"{q[1]:.1f}", f"{q[2]:.1f}"]
                         + [f"{100 * (arr >= b).mean():.1f}%" for b in SANITY_EDGE_LEN_BINS_PX])
    print()
    print_table(["edge lengths", "n", "mean", "p10", "median", "p90"] + [f">={b}px" for b in SANITY_EDGE_LEN_BINS_PX],
                lines)

    lengths = np.array(owned_lengths or all_lengths, dtype=float)
    deg = np.array(all_degrees, dtype=int)
    junctions = deg[deg >= 3]
    skew = float(lengths.mean() / np.median(lengths)) if lengths.size else 0.0
    deg3 = float((junctions == 3).mean()) if junctions.size else 0.0
    deg1 = float((deg == 1).mean()) if deg.size else 0.0
    checks = [
        ["edge lengths right-skewed (mean/median)", f"{skew:.2f}", f">= {SANITY_MIN_SKEW_RATIO}",
         "OK" if skew >= SANITY_MIN_SKEW_RATIO else "FLAG"],
        ["junctions that are degree 3", f"{100 * deg3:.1f}%", f">= {100 * SANITY_MIN_DEG3_FRACTION_OF_JUNCTIONS:.0f}%",
         "OK" if deg3 >= SANITY_MIN_DEG3_FRACTION_OF_JUNCTIONS else "FLAG"],
        ["nodes that are thread ends (degree 1)", f"{100 * deg1:.1f}%", f"<= {100 * SANITY_MAX_DEG1_FRACTION:.0f}%",
         "OK" if deg1 <= SANITY_MAX_DEG1_FRACTION else "FLAG"],
    ]
    print()
    print_table(["shape check", "value", "want", "result"], checks)
    print(f"\nTree-like junctions (degree 3, clustering 0, OCY n.t_nodes): {tree_nodes} of {junction_nodes}.")
    print("A FLAG on thread ends is expected in 2D sections: threads leaving the focal plane end in the image.")
    return 0


# regression ---------------------------------------------------------------------
# Regenerates every image with the current config, in parallel processes, into
# a git-ignored folder, and compares the numbers with results/ at tolerance 0.
# With every switch off it must PASS: that is the proof that a code change left
# the default outputs unchanged. The provenance block of the json files (code
# and library versions) is ignored. Fields that exist only in the new output
# (columns appended later) are counted but not compared, because results/ has
# nothing to compare them with.

REGRESSION_DIR = config.PROJECT_ROOT / "results_experiments" / "_cache" / "regression"
PROVENANCE_KEY = "provenance"


def _regenerate_one(job: tuple) -> dict:
    """Run both features on one image and write the two json files. Returns
    what the summary table needs (small, so it can cross processes)."""
    image_path, out_root, overrides = job
    for name, value in overrides.items():
        setattr(config, name, value)
    image_path = Path(image_path)
    result = canaliculi.analyse_image(image_path)
    out_dir = Path(out_root) / lacunae.clean_name(image_path)
    lacunae.save_json(result["lacunae"], out_dir / "lacunae.json")
    canaliculi.save_json(result, out_dir / "canaliculi_measurements.json")
    lac = result["lacunae"]
    return {
        "image_path": image_path,
        "lacunae": {k: lac[k] for k in ("lacuna_count", "interior_lacuna_count", "summary")},
        "summary": result["summary"],
        "field": result["field"],
    }


def regenerate(images: list, out_root: Path, overrides: dict | None = None, workers: int = 8) -> None:
    """Regenerate json outputs and the summary table for `images` into
    `out_root`, with the config attributes in `overrides` set in each worker."""
    from concurrent.futures import ProcessPoolExecutor

    out_root.mkdir(parents=True, exist_ok=True)
    jobs = [(str(p), str(out_root), dict(overrides or {})) for p in images]
    with ProcessPoolExecutor(max_workers=max(1, min(workers, len(jobs)))) as ex:
        results = list(ex.map(_regenerate_one, jobs))
    canaliculi.write_summary_table(results, out_root)


def flatten_all(value, prefix: str = "") -> dict:
    """Flatten nested dicts and lists into {path: leaf}."""
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            out.update(flatten_all(v, f"{prefix}.{k}" if prefix else str(k)))
        return out
    if isinstance(value, list):
        out = {}
        for i, v in enumerate(value):
            out.update(flatten_all(v, f"{prefix}[{i}]"))
        if not value:
            out[prefix] = []
        return out
    return {prefix: value}


def _equal(a, b) -> bool:
    """Tolerance 0. Numbers compare as numbers, everything else exactly."""
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if a != a and b != b:  # both NaN
            return True
        return a == b
    return a == b


def compare_json(ref_path: Path, new_path: Path) -> tuple:
    """(fields compared, differences, number of fields only in the new file)."""
    ref = json.load(open(ref_path))
    new = json.load(open(new_path))
    ref.pop(PROVENANCE_KEY, None)
    new.pop(PROVENANCE_KEY, None)
    fr, fn = flatten_all(ref), flatten_all(new)
    diffs = []
    for k, v in fr.items():
        if k not in fn:
            diffs.append((k, v, "<missing>"))
        elif not _equal(v, fn[k]):
            diffs.append((k, v, fn[k]))
    return len(fr), diffs, len(set(fn) - set(fr))


def compare_summary(ref_path: Path, new_path: Path) -> dict:
    """Every column of the reference summary table, by name, row by image."""
    import csv

    def rows(path):
        with open(path, newline="") as f:
            r = list(csv.reader(f))
        return r[0], {row[0]: dict(zip(r[0], row)) for row in r[1:] if row}

    hr, rr = rows(ref_path)
    hn, rn = rows(new_path)
    out = {}
    for image, row in rr.items():
        diffs = []
        new_row = rn.get(image)
        for col in hr:
            a = row[col]
            b = None if new_row is None else new_row.get(col)
            if b is None:
                diffs.append((col, a, "<missing>"))
                continue
            try:
                same_value = float(a) == float(b)
            except ValueError:
                same_value = a == b
            if not same_value:
                diffs.append((col, a, b))
        out[image] = (len(hr), diffs)
    extra = [c for c in hn if c not in hr]
    return {"rows": out, "extra_columns": extra, "missing_rows": [i for i in rn if i not in rr]}


def run_regression(images: list, ref: Path, out_root: Path, overrides: dict, workers: int, label: str) -> bool:
    regenerate(images, out_root, overrides, workers)
    table, ok, total, shown = [], True, 0, []
    for p in images:
        name = lacunae.clean_name(p)
        n_all, d_all, x_all = 0, [], 0
        for fname in ("lacunae.json", "canaliculi_measurements.json"):
            r, nw = ref / name / fname, out_root / name / fname
            if not r.is_file():
                d_all.append((fname, "<no reference file>", ""))
                continue
            n, d, x = compare_json(r, nw)
            n_all += n
            x_all += x
            d_all += [(f"{fname}:{k}", a, b) for k, a, b in d]
        total += n_all
        passed = not d_all
        ok &= passed
        shown += [(name, *d) for d in d_all[:5]]
        table.append([name, n_all, len(d_all), x_all, "PASS" if passed else "FAIL"])
    summ = compare_summary(ref / "summary_table.csv", out_root / "summary_table.csv")
    s_cells = sum(n for n, _d in summ["rows"].values())
    s_diffs = [(img, *d) for img, (_n, ds) in summ["rows"].items() for d in ds]
    ok &= not s_diffs
    total += s_cells
    print_table(["image", "json fields compared", "differ", "new fields (not compared)", "result"], table,
                title=f"Regression, {label}: {out_root} against {ref} (tolerance 0, provenance ignored)\n")
    print(f"\nsummary_table.csv: {s_cells} cells compared, {len(s_diffs)} differ"
          + (f"; new columns not compared: {', '.join(summ['extra_columns'])}" if summ["extra_columns"] else ""))
    for d in (shown + s_diffs)[:20]:
        print("  DIFF", *d)
    print(f"\nrun result: {'PASS' if ok else 'FAIL'}, {label}, {total} numbers compared over {len(images)} images.")
    return ok


def cmd_regression(args) -> int:
    """Two runs: the current config, then the same with FAST_LACUNA_STAGE on,
    which must give the same numbers."""
    import time

    images = images_from(args)
    results = []
    for label, overrides, out in (("current config", {}, args.out),
                                  ("FAST_LACUNA_STAGE on", {"FAST_LACUNA_STAGE": True}, args.out / "fast_stage")):
        t0 = time.time()
        ok = run_regression(images, args.ref, out, overrides, args.workers, label)
        print(f"time: {time.time() - t0:.0f} s\n")
        results.append(ok)
    ok = all(results)
    print(f"{'PASS' if ok else 'FAIL'}: regression, {len(results)} runs (current config; FAST_LACUNA_STAGE on), "
          f"{sum(results)} passed.")
    return 0 if ok else 1


# switch-check -------------------------------------------------------------------
# Each switch of config.py turned on alone, at the value the overnight report
# names (docs/OVERNIGHT_REPORT.md), every image regenerated into an ignored
# folder, and every change against results/ listed. Nothing is tuned here.

SWITCH_CHECK_DIR = config.PROJECT_ROOT / "results_experiments" / "_cache" / "switch_check"
SWITCHES_ON = [
    ("NARROW_CRUMB_RULE", True),
    ("FILL_ENCLOSED_HOLES_MAX_PX2", 200),
    ("BAND_FILTER_MIN_OPENING_SHARE", 0.515),
]
MATCH_PX = 10.0  # a lacuna in two runs is the same object if the centroids lie this close


def lacuna_changes(ref_dir: Path, new_dir: Path) -> tuple[list, dict]:
    """Per-lacuna changes between two output folders of one image, matched by
    centroid; and the headline values of both runs."""
    def load(d):
        lac = json.load(open(d / "lacunae.json"))
        can = json.load(open(d / "canaliculi_measurements.json"))
        rows = []
        for lr, cr in zip(lac["lacunae"], can["lacunae"]):
            rows.append({"x": lr["centroid_col_px"], "y": lr["centroid_row_px"], "area": lr["area_px2"],
                         "border": lr["on_border"], "roots": cr["roots_count"], "ring30": cr["ring_length_r30_px"]})
        head = {"lacuna_count": lac["lacuna_count"], "interior_count": lac["interior_lacuna_count"],
                "roots_per_cell": can["summary"]["roots_count"]["mean"],
                "ring30_per_cell": can["summary"]["ring_length_r30_px"]["mean"],
                "field_density": can["field"]["canalicular_length_density_per_px"], "bridges": can["n_bridges"]}
        return rows, head

    ref, head_ref = load(ref_dir)
    new, head_new = load(new_dir)
    used, changes = set(), []
    for r in ref:
        best, bd = None, MATCH_PX
        for j, n in enumerate(new):
            d = float(np.hypot(r["x"] - n["x"], r["y"] - n["y"]))
            if j not in used and d <= bd:
                best, bd = j, d
        if best is None:
            changes.append(f"removed: lacuna at ({r['x']:.0f},{r['y']:.0f}), {r['area']:.0f} px^2"
                           + (", frame edge" if r["border"] else ""))
            continue
        used.add(best)
        n = new[best]
        parts = [f"{k} {r[k]:g} to {n[k]:g}" for k in ("area", "roots", "ring30") if r[k] != n[k]]
        if parts:
            changes.append(f"changed: lacuna at ({r['x']:.0f},{r['y']:.0f}): " + ", ".join(parts))
    for j, n in enumerate(new):
        if j not in used:
            changes.append(f"new: lacuna at ({n['x']:.0f},{n['y']:.0f}), {n['area']:.0f} px^2")
    return changes, {"before": head_ref, "after": head_new}


def cmd_switch_check(args) -> int:
    images = images_from(args)
    lines = ["# switch-check", "",
             "Pre-validation, px. Each switch of config.py on alone, all others off, every image",
             f"regenerated into {args.out} and compared with {args.ref}. Lacunae are matched by centroid",
             f"within {MATCH_PX:g} px; a lacuna is listed when its area, roots or ring 30 px change.", ""]
    for name, value in SWITCHES_ON:
        out = args.out / f"{name}={value}"
        regenerate(images, out, {name: value}, args.workers)
        lines += [f"## {name} = {value}", ""]
        any_change = False
        for p in images:
            n = lacunae.clean_name(p)
            changes, head = lacuna_changes(args.ref / n, out / n)
            moved = {k: (head["before"][k], head["after"][k]) for k in head["before"]
                     if head["before"][k] != head["after"][k]}
            if not changes and not moved:
                continue
            any_change = True
            lines.append(f"- **{n}**")
            lines += [f"  - {c}" for c in changes]
            if moved:
                lines.append("  - image values: " + "; ".join(f"{k} {a} to {b}" for k, (a, b) in moved.items()))
        if not any_change:
            lines.append("No change in any image.")
        lines.append("")
    text = "\n".join(lines)
    print(text)
    (args.out / "switch_check.md").write_text(text, encoding="utf-8")
    return 0


# fast-check ---------------------------------------------------------------------
# The bounding-box lacuna stage (config.FAST_LACUNA_STAGE) against the
# original functions: labels after the watershed and after the re-merge must
# be identical, at the default cut and at t_hi scaled 0.8 to 1.2.

FAST_CHECK_SCALES = (0.8, 0.9, 1.0, 1.1, 1.2)


def _fast_check_one(path_str: str) -> list:
    import time

    image_path = Path(path_str)
    _display, channel = lacunae.load_channel(image_path)
    _mask, t_hi = lacunae.multiotsu_lacuna_mask(channel)
    rows = []
    for scale in FAST_CHECK_SCALES:
        mask, _t = lacunae.multiotsu_lacuna_mask(channel, t_hi * scale)
        distance = ndi_distance(mask)
        t0 = time.time()
        ws = lacunae.watershed_split(mask)
        merged = lacunae.merge_shallow_splits(ws, mask, distance)
        t_slow = time.time() - t0
        t0 = time.time()
        ws_f = lacunae.watershed_split_fast(mask)
        merged_f = lacunae.merge_shallow_splits_fast(ws_f, mask, distance)
        t_fast = time.time() - t0
        rows.append([lacunae.clean_name(image_path), scale, bool(np.array_equal(ws, ws_f)),
                     bool(np.array_equal(merged, merged_f)), round(t_slow, 1), round(t_fast, 2)])
    return rows


def ndi_distance(mask):
    from scipy import ndimage as ndi

    return ndi.distance_transform_edt(mask)


def cmd_fast_check(args) -> int:
    from concurrent.futures import ProcessPoolExecutor

    images = images_from(args)
    with ProcessPoolExecutor(max_workers=max(1, min(args.workers, len(images)))) as ex:
        rows = [r for part in ex.map(_fast_check_one, [str(p) for p in images]) for r in part]
    print_table(["image", "t_hi scale", "watershed identical", "re-merge identical", "original s", "fast s"], rows,
                title="Fast lacuna stage against the original (labels compared pixel for pixel)\n")
    ok = all(r[2] and r[3] for r in rows)
    slow, fast = sum(r[4] for r in rows), sum(r[5] for r in rows)
    print(f"\nTotal time over {len(rows)} runs: original {slow:.0f} s, fast {fast:.1f} s "
          f"(each run in its own process, {args.workers} in parallel).")
    print(f"\n{'PASS' if ok else 'FAIL'}: fast-check, {sum(r[2] and r[3] for r in rows)} of {len(rows)} identical.")
    if args.csv:
        import csv
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with open(args.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["image", "t_hi_scale", "watershed_identical", "remerge_identical", "original_s", "fast_s"])
            w.writerows(rows)
    return 0 if ok else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="LCN pipeline diagnostics (read-only, pre-validation, px).")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("reference-check", help="Run 543-2 and check 62.33 / 27.41 / 21.")
    p.add_argument("--image", type=Path, default=REFERENCE_IMAGE, help=argparse.SUPPRESS)
    p.set_defaults(func=cmd_reference_check)

    p = sub.add_parser("compare-outputs", help="Compare two results folders number by number.")
    p.add_argument("a", type=Path, help="First results folder (or a saved numbers snapshot).")
    p.add_argument("b", type=Path, help="Second results folder (or a saved numbers snapshot).")
    p.add_argument("--tolerance", type=float, default=0.0, help="Largest allowed absolute difference (default 0: exact).")
    p.add_argument("--show", type=int, default=20, help="How many differences to list.")
    p.set_defaults(func=cmd_compare_outputs)

    p = sub.add_parser("reach", help="Owned path distance per cell: median, p90, max.")
    add_images_arguments(p)
    p.set_defaults(func=cmd_reach)

    p = sub.add_parser("lacuna-table", help="Per-lacuna area, solidity, aspect and roots for one image.")
    p.add_argument("--image", type=Path, required=True)
    p.set_defaults(func=cmd_lacuna_table)

    p = sub.add_parser("sanity", help="Pooled edge-length and node-degree shape checks.")
    add_images_arguments(p)
    p.set_defaults(func=cmd_sanity)

    p = sub.add_parser("regression", help="Regenerate every image and compare with results/ at tolerance 0.")
    add_images_arguments(p)
    p.add_argument("-o", dest="out", type=Path, default=REGRESSION_DIR,
                   help="Where to regenerate (default: results_experiments/_cache/regression, git-ignored).")
    p.add_argument("-r", dest="ref", type=Path, default=config.RESULTS_DIR, help="Reference folder (default: results/).")
    p.add_argument("-w", dest="workers", type=int, default=8, help="Parallel processes (default 8).")
    p.set_defaults(func=cmd_regression)

    p = sub.add_parser("switch-check", help="Each switch on alone: what changes against results/.")
    add_images_arguments(p)
    p.add_argument("-o", dest="out", type=Path, default=SWITCH_CHECK_DIR,
                   help="Where to regenerate (default: results_experiments/_cache/switch_check, git-ignored).")
    p.add_argument("-r", dest="ref", type=Path, default=config.RESULTS_DIR, help="Reference folder (default: results/).")
    p.add_argument("-w", dest="workers", type=int, default=8, help="Parallel processes (default 8).")
    p.set_defaults(func=cmd_switch_check)

    p = sub.add_parser("fast-check", help="Fast lacuna stage against the original: identical labels, timing.")
    add_images_arguments(p)
    p.add_argument("-c", dest="csv", type=Path, default=None, help="Also write the table to this CSV file.")
    p.add_argument("-w", dest="workers", type=int, default=8, help="Parallel processes (default 8).")
    p.set_defaults(func=cmd_fast_check)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
