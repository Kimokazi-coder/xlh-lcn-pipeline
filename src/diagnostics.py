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
    blind             copy a folder of images under random codes (S001, ...),
                      pixel data only, with the key written outside the repository
    unblind           join a blinding key to a summary table
    sensitivity       both Otsu cuts scaled 0.8 to 1.2, alone and together,
                      plus one pooled cut: percent changes of the measures
    field-summary     group images into fields by matching lacuna centroids,
                      and write per-field means (the field is the unit)
    network-sweep     one network parameter at a time at a low and a high
                      value: percent changes of the network measures

Usage (from the repo root):
    python src/diagnostics.py reference-check
    python src/diagnostics.py compare-outputs results OTHER_FOLDER
    python src/diagnostics.py reach --dir data/WT
    python src/diagnostics.py lacuna-table --image "data/WT/543-2.tif"
    python src/diagnostics.py sanity --dir data/WT
    python src/diagnostics.py regression
    python src/diagnostics.py switch-check
    python src/diagnostics.py fast-check
    python src/diagnostics.py blind -s data/WT -o CODED_FOLDER -k KEY_OUTSIDE_REPO.csv
    python src/diagnostics.py unblind -s CODED_RESULTS/summary_table.csv -k KEY.csv -o UNBLINDED.csv
    python src/diagnostics.py sensitivity -d data/WT -o OUT_FOLDER
    python src/diagnostics.py field-summary -d data/WT -o OUT_FOLDER [-r RESULTS_FOLDER]
    python src/diagnostics.py network-sweep -d data/WT -o OUT_FOLDER
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


def regression_allowlist() -> dict:
    """Fields allowed to exist only in the regenerated output, because they
    were appended after results/ was made. Any other new field fails the
    regression. Json paths use "[*]" for a list index."""
    per_cell = [m[0] for m in canaliculi.NORMALISED_METRICS + canaliculi.NETWORK_V2_METRICS]
    json_fields = {"canaliculi_measurements.json:normalised_measures[*]",
                   "canaliculi_measurements.json:network_v2_measures[*]"}
    for f in per_cell:
        json_fields.add(f"canaliculi_measurements.json:lacunae[*].{f}")
        for stat in ("mean", "median", "sd"):
            json_fields.add(f"canaliculi_measurements.json:summary.{f}.{stat}")
    for key in getattr(canaliculi, "FIELD_V2_KEYS", []):
        json_fields.add(f"canaliculi_measurements.json:field.{key}")
    for key in getattr(canaliculi, "PARAMETERS_V2_KEYS", []):
        json_fields.add(f"canaliculi_measurements.json:parameters.{key}")
    for key in ("narrow_crumb_rule", "fill_enclosed_holes_max_px2", "band_filter_min_opening_share",
                "fast_lacuna_stage"):
        json_fields.add(f"lacunae.json:parameters.{key}")
    n_ref = canaliculi.SUMMARY_COLUMNS.index("field length density (px^-1)") + 1
    return {"json": json_fields, "summary_table": set(canaliculi.SUMMARY_COLUMNS[n_ref:])}


def print_allowlist(allow: dict) -> None:
    print("New fields allowed (appended after results/ was made; counted, not compared):")
    for path in sorted(allow["json"]):
        print(f"  json  {path}")
    for col in canaliculi.SUMMARY_COLUMNS:
        if col in allow["summary_table"]:
            print(f"  table {col}")
    print()


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


def compare_json(ref_path: Path, new_path: Path, allowed: set | None = None) -> tuple:
    """(fields compared, differences, number of fields only in the new file).
    With `allowed` (allowlist paths), a new field outside it is a difference."""
    import re

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
    extra = set(fn) - set(fr)
    if allowed is not None:
        index = re.compile(r"\[[0-9]+\]")
        for k in sorted(extra):
            if new_path.name + ":" + index.sub("[*]", k) not in allowed:
                diffs.append((k, "<not in results/>", "unexpected new field"))
    return len(fr), diffs, len(extra)


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
    allow = regression_allowlist()
    table, ok, total, shown = [], True, 0, []
    for p in images:
        name = lacunae.clean_name(p)
        n_all, d_all, x_all = 0, [], 0
        for fname in ("lacunae.json", "canaliculi_measurements.json"):
            r, nw = ref / name / fname, out_root / name / fname
            if not r.is_file():
                d_all.append((fname, "<no reference file>", ""))
                continue
            n, d, x = compare_json(r, nw, allow["json"])
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
    s_diffs += [("summary_table.csv", col, "<not in results/>", "unexpected new column")
                for col in summ["extra_columns"] if col not in allow["summary_table"]]
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
    print_allowlist(regression_allowlist())
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
# The band-wall filter has no recommended value (docs/CANALICULI_V2_REPORT.md,
# B1), so it is run at the two evidence settings of B1, labelled as such:
# the only line length that separates any part of the 542_z06 line (97 px, in
# the gap from 95 to 100) with the reach that the line needs there (66 px: its
# straight piece lies 65.01 px from the canal mask), and
# the only length at which the line's straight part touches the canal mask
# (40 px, reach 0). Neither is a recommendation.
SWITCH_SETTINGS_EXTRA = [
    ("BAND_LINE_FILTER on, evidence setting L 97 px, reach 66 px (not a recommendation)",
     {"BAND_LINE_FILTER": True, "BAND_LINE_MIN_LEN_PX": 97, "BAND_LINE_REACH_PX": 66}),
    ("BAND_LINE_FILTER on, evidence setting L 40 px, reach 0 px (not a recommendation)",
     {"BAND_LINE_FILTER": True, "BAND_LINE_MIN_LEN_PX": 40, "BAND_LINE_REACH_PX": 0}),
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
    settings = [(f"{name} = {value}", {name: value}, f"{name}={value}") for name, value in SWITCHES_ON]
    settings += [(label, overrides, "__".join(f"{k}={v}" for k, v in overrides.items()))
                 for label, overrides in SWITCH_SETTINGS_EXTRA]
    for label, overrides, folder in settings:
        out = args.out / folder
        regenerate(images, out, overrides, args.workers)
        lines += [f"## {label}", ""]
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


# blind and unblind ----------------------------------------------------------------
# Blinding: the images are copied under random codes, pixel data only, so a
# person (or the pipeline) working on the coded folder cannot see which image
# is which. The pipeline itself writes only the file name it is given, so on a
# coded folder every output carries codes only. The key, the one file that
# links codes to names, must live outside the repository so it is never
# committed. Neither command prints an original name.

BLIND_PATTERNS = ("*.tif", "*.tiff")


def _inside(path: Path, folder: Path) -> bool:
    path, folder = path.resolve(), folder.resolve()
    return path == folder or folder in path.parents


def cmd_blind(args) -> int:
    import csv
    import random

    import tifffile

    src, out, key = args.src, args.out, args.key
    if _inside(key, config.PROJECT_ROOT):
        print("Refused: the key path is inside the repository. Put the key outside it, so it can never be committed.")
        return 2
    if key.exists():
        print("Refused: the key file already exists. Choose a new path; an existing key is never overwritten.")
        return 2
    files = sorted(f for pattern in BLIND_PATTERNS for f in src.glob(pattern))
    if not files:
        print("No .tif or .tiff images in the source folder.")
        return 1
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        print("Refused: the output folder is not empty.")
        return 2
    seed = random.SystemRandom().randrange(2 ** 32)
    order = list(range(len(files)))
    random.Random(seed).shuffle(order)
    key_rows = []
    for i, index in enumerate(order, start=1):
        code = f"S{i:03d}"
        data = tifffile.imread(files[index])
        # A constant fourth (alpha) channel carries no information but would
        # mark the one image that has it, so it is dropped and the drop is
        # recorded in the key. The pipeline never reads it.
        alpha_dropped = False
        if data.ndim == 3 and data.shape[-1] == 4 and (data[..., 3] == data[..., 3].flat[0]).all():
            data = data[..., :3]
            alpha_dropped = True
        extras = {}
        if data.ndim == 3 and data.shape[-1] in (3, 4):
            extras["photometric"] = "rgb"
            if data.shape[-1] == 4:
                extras["extrasamples"] = ["unassalpha"]
        else:
            extras["photometric"] = "minisblack"
        # Pixel data only: no description, no metadata, no software tag.
        tifffile.imwrite(out / f"{code}.tif", data, metadata=None, software=False, **extras)
        key_rows.append([code, files[index].name, str(files[index].parent.resolve()), seed, alpha_dropped])
    key.parent.mkdir(parents=True, exist_ok=True)
    with open(key, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["code", "original_name", "original_folder", "seed", "constant_alpha_dropped"])
        w.writerows(sorted(key_rows))
    print(f"{len(files)} images coded S001 to S{len(files):03d} into {out}. Key written to {key}.")
    return 0


def cmd_unblind(args) -> int:
    import csv

    with open(args.key, newline="") as f:
        key = {row["code"]: row for row in csv.DictReader(f)}
    with open(args.src, newline="") as f:
        rows = list(csv.reader(f))
    header, body = rows[0], [r for r in rows[1:] if r]
    out_rows, missing = [], 0
    for r in body:
        code = Path(r[0]).stem
        k = key.get(code)
        if k is None:
            missing += 1
        out_rows.append([code, k["original_name"] if k else "", k["original_folder"] if k else ""] + r)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["code", "original_name", "original_folder"] + header)
        w.writerows(out_rows)
    print(f"{len(out_rows)} rows unblinded into {args.out}; {missing} without a key entry.")
    return 0 if missing == 0 else 1


# sensitivity --------------------------------------------------------------------
# How the measures move with the two image-relative Otsu cuts: t_hi (the
# lacuna cut on the red channel) and t_lo (the network strict cut on the
# preprocessed channel; the hysteresis low cut and the bridging test follow
# it). Each image's own cut is scaled by 0.8, 0.9, 1.1 and 1.2, alone and
# together, and one pooled cut is applied to every image: the median t_hi
# over the folder, and the median t_lo in raw units (t_lo x the image's
# preprocessing peak) converted back to each image's scale. As in
# experiments/task2_thresholds.py (overnight report 2.4). Nothing is tuned;
# the defaults do not change. Runs use the fast lacuna stage, which gives
# identical labels (fast-check).

SENSITIVITY_SCALES = (0.8, 0.9, 1.1, 1.2)
SENSITIVITY_MEASURES = [("roots_per_cell", "roots per cell"), ("ring30_per_cell", "ring 30 px per cell"),
                        ("field_density", "field density"), ("lacuna_count", "lacuna count"), ("bridges", "bridges")]


def _cuts_of(path_str: str) -> dict:
    image_path = Path(path_str)
    _display, channel = lacunae.load_channel(image_path)
    _mask, t_hi = lacunae.multiotsu_lacuna_mask(channel)
    raw = canaliculi.preprocess_unnormalised(channel)
    peak = float(raw.max())
    _strict, t_lo = canaliculi.total_signal_mask(raw / peak if peak > 0 else raw)
    return {"t_hi": t_hi, "t_lo": t_lo, "peak": peak}


def _sensitivity_run(job: tuple) -> dict:
    path_str, label, t_hi, t_lo, out_path = job
    out_path = Path(out_path)
    if out_path.is_file():
        return json.loads(out_path.read_text(encoding="utf-8"))
    config.FAST_LACUNA_STAGE = True
    result = canaliculi.analyse_image(Path(path_str), t_hi, t_lo)
    s = result["summary"]
    row = {"image": lacunae.clean_name(Path(path_str)), "setting": label,
           "t_hi": result["lacunae"]["t_hi"], "t_lo": result["t_lo"],
           "lacuna_count": result["lacunae"]["lacuna_count"],
           "interior_count": result["lacunae"]["interior_lacuna_count"],
           "roots_per_cell": s["roots_count"]["mean"], "ring30_per_cell": s["ring_length_r30_px"]["mean"],
           "field_density": result["field"]["canalicular_length_density_per_px"], "bridges": len(result["bridges"])}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_name(out_path.name + ".tmp")
    tmp.write_text(json.dumps(row, indent=1), encoding="utf-8")
    tmp.replace(out_path)
    return row


def cmd_sensitivity(args) -> int:
    import csv
    from concurrent.futures import ProcessPoolExecutor

    images = lacunae.image_paths(args)
    out = args.out
    runs = out / "runs"
    with ProcessPoolExecutor(max_workers=max(1, min(args.workers, len(images)))) as ex:
        cuts = dict(zip([str(p) for p in images], ex.map(_cuts_of, [str(p) for p in images])))
    pooled_hi = float(np.median([c["t_hi"] for c in cuts.values()]))
    pooled_lo_raw = float(np.median([c["t_lo"] * c["peak"] for c in cuts.values()]))
    jobs = []
    for p in images:
        c = cuts[str(p)]
        name = lacunae.clean_name(p)
        settings = [("default", None, None)]
        for sc in SENSITIVITY_SCALES:
            settings += [(f"t_hi x{sc:g}", c["t_hi"] * sc, None), (f"t_lo x{sc:g}", None, c["t_lo"] * sc),
                         (f"both x{sc:g}", c["t_hi"] * sc, c["t_lo"] * sc)]
        lo_pooled = pooled_lo_raw / c["peak"] if c["peak"] > 0 else None
        settings += [("t_hi pooled", pooled_hi, None), ("t_lo pooled", None, lo_pooled), ("both pooled", pooled_hi, lo_pooled)]
        for label, hi, lo in settings:
            fname = label.replace(" ", "_").replace("x", "")
            jobs.append((str(p), label, hi, lo, str(runs / f"{name}__{fname}.json")))
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as ex:
        rows = list(ex.map(_sensitivity_run, jobs))
    base = {r["image"]: r for r in rows if r["setting"] == "default"}
    table = []
    for r in rows:
        b = base[r["image"]]
        row = dict(r)
        for key, _label in SENSITIVITY_MEASURES:
            row[f"{key}_pct"] = (100.0 * (r[key] - b[key]) / b[key]) if b[key] else None
        table.append(row)
    out.mkdir(parents=True, exist_ok=True)
    cols = list(table[0].keys())
    with open(out / "sensitivity.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(table)
    order = [r[1] for r in jobs[: len(jobs) // len(images)]][1:]
    lines = ["# Threshold sensitivity", "",
             "PRE-VALIDATION, pixel units. Percent change against each image's default run, median over the "
             f"{len(images)} images with the range in brackets. t_hi: lacuna cut; t_lo: network strict cut.",
             f"pooled: one cut for every image, t_hi = {pooled_hi:.4f} (median over the folder) and t_lo =",
             f"{pooled_lo_raw:.4f} in raw units (median of t_lo x preprocessing peak). Per-image values: sensitivity.csv.",
             "", "| setting | " + " | ".join(label for _k, label in SENSITIVITY_MEASURES) + " |",
             "|---|" + "---|" * len(SENSITIVITY_MEASURES)]
    for setting in order:
        sub = [r for r in table if r["setting"] == setting]
        cells = []
        for key, _label in SENSITIVITY_MEASURES:
            v = np.array([r[f"{key}_pct"] for r in sub if r[f"{key}_pct"] is not None], dtype=float)
            cells.append(f"{np.median(v):+.1f} [{v.min():+.1f}, {v.max():+.1f}]" if v.size else "")
        lines.append(f"| {setting} | " + " | ".join(cells) + " |")
    lines += ["", "Lacuna count per image and setting:", "",
              "| image | default | " + " | ".join(order) + " |", "|---|---|" + "---|" * len(order)]
    for p in images:
        name = lacunae.clean_name(p)
        by = {r["setting"]: r for r in table if r["image"] == name}
        lines.append(f"| {name} | {by['default']['lacuna_count']} | "
                     + " | ".join(str(by[s]["lacuna_count"]) for s in order) + " |")
    text = "\n".join(lines) + "\n"
    (out / "sensitivity.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


# field-summary --------------------------------------------------------------------
# Optical sections of one field repeat the same cells, so they are not
# independent samples (overnight report 6.1). Images are grouped into fields
# from the data: lacunae are matched between every pair of images by centroid,
# one to one (mutual nearest neighbours) within FIELD_MATCH_PX, with no shift.
# Two images are linked when the share of the smaller image's lacunae that
# match lies above the largest gap in the sorted shares (0 included as the
# floor) and is at least FIELD_MIN_MATCH_SHARE; linked images form a field.
# On the 8 WT images this gives the groups of the overnight report.

FIELD_MATCH_PX = 25.0  # overnight report 6.1; matched centroids sat a median 5 to 13 px apart
# A conservative guard: at least half of the smaller image's lacunae must
# match, so a few chance matches never join two fields. Not tuned: on the WT
# images the linked shares are 0.77 to 0.92 and the largest unlinked one 0.40.
FIELD_MIN_MATCH_SHARE = 0.5
FIELD_MEASURES = [
    ("roots_per_cell", "roots per cell", ("summary", "roots_count")),
    ("roots_per_100px_perimeter", "roots per 100 px perimeter", ("summary", "roots_per_100px_perimeter")),
    ("ring30_per_cell", "ring 30 px per cell (px)", ("summary", "ring_length_r30_px")),
    ("ring_density_r30", "ring density 30 px (px^-1)", ("summary", "ring_density_r30")),
    ("ring_density_r60", "ring density 60 px (px^-1)", ("summary", "ring_density_r60")),
    ("field_density", "field density (px^-1)", ("field", "canalicular_length_density_per_px")),
]


def _field_inputs(job: tuple) -> dict:
    path_str, results_dir = job
    image_path = Path(path_str)
    name = lacunae.clean_name(image_path)
    folder = Path(results_dir) / name if results_dir else None
    if folder and (folder / "lacunae.json").is_file() and (folder / "canaliculi_measurements.json").is_file():
        lac = json.load(open(folder / "lacunae.json"))
        can = json.load(open(folder / "canaliculi_measurements.json"))
        rows, summary, field = lac["lacunae"], can["summary"], can["field"]
    else:
        config.FAST_LACUNA_STAGE = True
        result = canaliculi.analyse_image(image_path)
        rows, summary, field = result["lacunae"]["rows"], result["summary"], result["field"]
    values = {}
    for key, _label, (block, field_key) in FIELD_MEASURES:
        source = summary if block == "summary" else field
        v = source.get(field_key)
        values[key] = v.get("mean") if isinstance(v, dict) else v
    return {"image": name, "xy": [(r["centroid_col_px"], r["centroid_row_px"]) for r in rows],
            "lacuna_count": len(rows), "interior_count": sum(1 for r in rows if not r["on_border"]), **values}


def _mutual_matches(a: list, b: list, radius: float) -> list:
    if not a or not b:
        return []
    pa, pb = np.array(a, dtype=float), np.array(b, dtype=float)
    dist = np.hypot(pa[:, None, 0] - pb[None, :, 0], pa[:, None, 1] - pb[None, :, 1])
    out = []
    for i in range(len(pa)):
        j = int(np.argmin(dist[i]))
        if dist[i, j] <= radius and int(np.argmin(dist[:, j])) == i:
            out.append((i, j, float(dist[i, j])))
    return out


def field_groups(inputs: list) -> tuple:
    """(groups as lists of image names, pair table, the cut used)."""
    import itertools

    names = [d["image"] for d in inputs]
    by = {d["image"]: d for d in inputs}
    pairs = []
    for a, b in itertools.combinations(names, 2):
        m = _mutual_matches(by[a]["xy"], by[b]["xy"], FIELD_MATCH_PX)
        smaller = min(len(by[a]["xy"]), len(by[b]["xy"])) or 1
        pairs.append({"image_a": a, "image_b": b, "matches": len(m), "share_of_smaller": len(m) / smaller,
                      "median_distance_px": float(np.median([t[2] for t in m])) if m else None})
    shares = sorted({0.0} | {p["share_of_smaller"] for p in pairs})
    cut = 0.0
    if len(shares) > 1:
        gaps = np.diff(shares)
        k = int(np.argmax(gaps))
        cut = (shares[k] + shares[k + 1]) / 2
    parent = {n: n for n in names}

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x

    for p in pairs:
        p["linked"] = p["share_of_smaller"] > cut and p["share_of_smaller"] >= FIELD_MIN_MATCH_SHARE
        if p["linked"]:
            parent[find(p["image_a"])] = find(p["image_b"])
    groups = {}
    for n in names:
        groups.setdefault(find(n), []).append(n)
    return sorted(groups.values(), key=lambda g: g[0]), pairs, cut


def cmd_field_summary(args) -> int:
    import csv
    from concurrent.futures import ProcessPoolExecutor

    images = lacunae.image_paths(args)
    res = str(args.results) if args.results else None
    with ProcessPoolExecutor(max_workers=max(1, min(args.workers, len(images)))) as ex:
        inputs = list(ex.map(_field_inputs, [(str(p), res) for p in images]))
    groups, pairs, cut = field_groups(inputs)
    by = {d["image"]: d for d in inputs}
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    field_rows, image_rows = [], []
    for i, g in enumerate(groups, start=1):
        fid = f"F{i}"
        row = {"field": fid, "images": " + ".join(g), "n_images": len(g)}
        for key, _label, _src in FIELD_MEASURES:
            vals = [by[n][key] for n in g if by[n][key] is not None]
            row[f"{key}_mean"] = float(np.mean(vals)) if vals else None
            row[f"{key}_min"] = float(np.min(vals)) if vals else None
            row[f"{key}_max"] = float(np.max(vals)) if vals else None
        field_rows.append(row)
        for n in g:
            image_rows.append({"field": fid, "image": n, "lacuna_count": by[n]["lacuna_count"],
                               "interior_count": by[n]["interior_count"],
                               **{key: by[n][key] for key, _l, _s in FIELD_MEASURES}})
    for fname, rows in (("field_summary.csv", field_rows), ("field_images.csv", image_rows), ("field_pairs.csv", pairs)):
        with open(out / fname, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    lines = ["# Field summary", "",
             "PRE-VALIDATION, pixel units. **The field is the unit of analysis.** Optical sections of one field",
             "repeat the same cells, so they are not independent samples; the value of a field is the mean over",
             "its images.", "",
             f"Fields derived from the data: lacunae matched one to one by centroid within {FIELD_MATCH_PX:g} px, no",
             f"shift; two images are linked when the matched share of the smaller image lies above the largest gap",
             f"in the sorted shares (cut {cut:.2f}) and is at least {FIELD_MIN_MATCH_SHARE:g}. An image with no link is its own field.", ""]
    for r in field_rows:
        lines.append(f"- {r['field']}: {r['images']} ({r['n_images']} image{'s' if r['n_images'] != 1 else ''})")
    lines += ["", "| field | images | " + " | ".join(label for _k, label, _s in FIELD_MEASURES) + " |",
              "|---|---|" + "---|" * len(FIELD_MEASURES)]
    for r in field_rows:
        cells = []
        for key, _label, _src in FIELD_MEASURES:
            m = r[f"{key}_mean"]
            cells.append("" if m is None else (f"{m:.5f}" if abs(m) < 1 else f"{m:.2f}"))
        lines.append(f"| {r['field']} | {r['n_images']} | " + " | ".join(cells) + " |")
    lines += ["", "Pairs (field_pairs.csv):", "", "| image a | image b | matches | share of smaller | linked |",
              "|---|---|---|---|---|"]
    for p in sorted(pairs, key=lambda q: -q["share_of_smaller"]):
        if p["matches"]:
            lines.append(f"| {p['image_a']} | {p['image_b']} | {p['matches']} | {p['share_of_smaller']:.2f} | {p['linked']} |")
    lines.append("")
    lines.append("Pairs not listed share no lacuna.")
    text = "\n".join(lines) + "\n"
    (out / "field_summary.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


# network-sweep ------------------------------------------------------------------
# One-at-a-time sensitivity of the network stage (docs/CANALICULI_V2_REPORT.md,
# S1). The lacuna stage runs once per image (fast stage, identical labels) and is
# cached; only the network stage reruns. Each parameter of src/canaliculi.py is
# set to a low and a high value (about -30% and +30%, or the nearest sensible
# integer steps) with everything else at its default; the network cut t_lo is
# scaled 0.8 to 1.2 as in sensitivity. No default changes and no value is
# recommended.

NETWORK_SWEEP = [
    ("TOPHAT_RADIUS_PX", (4, 6)),
    ("HYSTERESIS_LOW_FRACTION", (0.525, 0.975)),
    ("MAX_BRIDGE_GAP_PX", (0.0, 7.0, 13.0)),
    ("MAX_BRIDGE_ANGLE_DEG", (28.0, 52.0)),
    ("MIN_BRIDGE_SIGNAL_FRACTION", (0.49, 0.91)),
    ("PRUNE_SPUR_LEN_PX", (3, 5)),
    ("ROOT_MERGE_DIST_PX", (6.0, 10.0)),
    ("LACUNA_ATTACH_GAP_PX", (7, 13)),
    ("t_lo scale", (0.8, 0.9, 1.1, 1.2)),
]
SWEEP_DEFAULTS = {name: getattr(canaliculi, name) for name, _v in NETWORK_SWEEP if name != "t_lo scale"}
SWEEP_MEASURES = [
    ("roots_per_cell", "roots per cell", ("summary", "roots_count")),
    ("ring30", "ring 30 px", ("summary", "ring_length_r30_px")),
    ("ring30_attached", "ring attached 30 px", ("summary", "ring_attached_length_r30_px")),
    ("ring30_weighted", "ring weighted 30 px", ("summary", "ring_length_w_r30_px")),
    ("sholl10", "Sholl 10 px", ("summary", "sholl_crossings_r10")),
    ("sholl20", "Sholl 20 px", ("summary", "sholl_crossings_r20")),
    ("sholl30", "Sholl 30 px", ("summary", "sholl_crossings_r30")),
    ("field_density", "field density", ("field", "canalicular_length_density_per_px")),
    ("bridges", "bridges", ("bridges", None)),
]


def _sweep_lacunae(path_str: str, cache_dir: str) -> dict:
    """The lacuna stage of one image, cached as labels and kept labels."""
    from skimage import measure

    image_path = Path(path_str)
    cache = Path(cache_dir) / f"{lacunae.clean_name(image_path)}.npz"
    if not cache.is_file():
        config.FAST_LACUNA_STAGE = True
        lac = lacunae.analyse_image(image_path)
        cache.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_name(cache.name + ".tmp.npz")
        np.savez_compressed(tmp, labels=lac["labels"].astype(np.int32),
                            kept=np.array([r.label for r, _b in lac["kept"]], dtype=np.int32),
                            border=np.array([b for _r, b in lac["kept"]], dtype=bool), t_hi=lac["t_hi"])
        tmp.replace(cache)
    with np.load(cache) as z:
        labels, kept_ids, border, t_hi = z["labels"], z["kept"], z["border"], float(z["t_hi"])
    regions = {r.label: r for r in measure.regionprops(labels)}
    kept = [(regions[int(i)], bool(b)) for i, b in zip(kept_ids, border)]
    rows = lacunae.measurements_for(kept, config.CSV_FLOAT_PRECISION)
    return {"labels": labels, "kept": kept, "t_hi": t_hi, "rows": rows, "display": None,
            "lacuna_count": len(kept), "interior_lacuna_count": sum(1 for _r, b in kept if not b)}


def _sweep_lacunae_cached(path_str: str, cache_dir: str) -> bool:
    """Fill the lacuna cache of one image (returns only a flag, since the
    region objects do not cross processes)."""
    _sweep_lacunae(path_str, cache_dir)
    return True


def _sweep_run(job: tuple) -> dict:
    path_str, param, value, out_path, cache_dir = job
    out_path = Path(out_path)
    if out_path.is_file():
        return json.loads(out_path.read_text(encoding="utf-8"))
    image_path = Path(path_str)
    lac = _sweep_lacunae(path_str, cache_dir)
    channel = lacunae.load_channel(image_path)[1]
    t_lo = None
    for name, _values in NETWORK_SWEEP:
        if name != "t_lo scale" and getattr(canaliculi, name) != SWEEP_DEFAULTS[name]:
            raise RuntimeError(f"{name} is not at its default at the start of a sweep job")
    if param == "t_lo scale":
        raw = canaliculi.preprocess_unnormalised(channel)
        peak = float(raw.max())
        _m, base = canaliculi.total_signal_mask(raw / peak if peak > 0 else raw)
        t_lo = base * value
    saved = None
    if param is not None and param != "t_lo scale":
        saved = getattr(canaliculi, param)
        setattr(canaliculi, param, value)
    try:
        result = canaliculi.analyse_network(image_path, lac, channel, t_lo)
    finally:
        # A worker process runs many jobs: put the default back, so no setting
        # leaks into the next job.
        if saved is not None:
            setattr(canaliculi, param, saved)
    row = {"image": lacunae.clean_name(image_path), "parameter": param or "default",
           "value": value, "t_lo": result["t_lo"]}
    for key, _label, (block, field) in SWEEP_MEASURES:
        if block == "bridges":
            row[key] = len(result["bridges"])
        elif block == "field":
            row[key] = result["field"][field]
        else:
            row[key] = result["summary"][field]["mean"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_name(out_path.name + ".tmp")
    tmp.write_text(json.dumps(row, indent=1), encoding="utf-8")
    tmp.replace(out_path)
    return row


def cmd_network_sweep(args) -> int:
    import csv
    from concurrent.futures import ProcessPoolExecutor

    images = lacunae.image_paths(args)
    out = args.out
    runs, cache = out / "runs", out / "lacuna_cache"
    jobs = []
    for p in images:
        name = lacunae.clean_name(p)
        jobs.append((str(p), None, None, str(runs / f"{name}__default.json"), str(cache)))
        for param, values in NETWORK_SWEEP:
            for v in values:
                tag = f"{param.replace(' ', '_')}={v:g}"
                jobs.append((str(p), param, v, str(runs / f"{name}__{tag}.json"), str(cache)))
    # The lacuna stage first, once per image, so the workers only read the cache.
    with ProcessPoolExecutor(max_workers=max(1, min(args.workers, len(images)))) as ex:
        list(ex.map(_sweep_lacunae_cached, [str(p) for p in images], [str(cache)] * len(images)))
    with ProcessPoolExecutor(max_workers=max(1, args.workers)) as ex:
        rows = list(ex.map(_sweep_run, jobs))
    base = {r["image"]: r for r in rows if r["parameter"] == "default"}
    for r in rows:
        b = base[r["image"]]
        for key, _label, _src in SWEEP_MEASURES:
            r[f"{key}_pct"] = (100.0 * (r[key] - b[key]) / b[key]) if b[key] else None
    out.mkdir(parents=True, exist_ok=True)
    cols = list(rows[0].keys())
    with open(out / "network_sweep.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    settings = [(param, v) for param, values in NETWORK_SWEEP for v in values]
    table = []
    for param, v in settings:
        sub = [r for r in rows if r["parameter"] == param and r["value"] == v]
        entry = {"setting": f"{param} = {v:g}"}
        for key, _label, _src in SWEEP_MEASURES:
            vals = np.array([r[f"{key}_pct"] for r in sub if r[f"{key}_pct"] is not None], dtype=float)
            entry[key] = (float(np.median(vals)), float(vals.min()), float(vals.max())) if vals.size else None
        table.append(entry)
    defaults = {param: getattr(canaliculi, param) for param, _v in NETWORK_SWEEP if param != "t_lo scale"}
    lines = ["# Network sweep", "",
             "PRE-VALIDATION, pixel units. One parameter of the network stage at a time, everything else at its "
             f"default, on {len(images)} images; the lacuna stage ran once per image (fast stage) and is reused. "
             "Percent change against each image's default run: median over the images, range in brackets. "
             "No value is recommended and no default changed.", "",
             "Defaults: " + ", ".join(f"`{k}` = {v}" for k, v in defaults.items()) + "; t_lo is each image's own "
             "lower Otsu cut. MAX_BRIDGE_GAP_PX = 0 means no bridging.", "",
             "| setting | " + " | ".join(label for _k, label, _s in SWEEP_MEASURES) + " |",
             "|---|" + "---|" * len(SWEEP_MEASURES)]
    for e in table:
        cells = [("" if e[k] is None else f"{e[k][0]:+.1f} [{e[k][1]:+.1f}, {e[k][2]:+.1f}]")
                 for k, _l, _s in SWEEP_MEASURES]
        lines.append(f"| {e['setting']} | " + " | ".join(cells) + " |")
    lines += ["", "## Ranked by effect on each measure", "",
              "For each parameter, the larger absolute median change of its settings, largest first.", ""]
    effect = {}
    for param, values in NETWORK_SWEEP:
        for key, _label, _src in SWEEP_MEASURES:
            meds = [abs(e[key][0]) for e in table if e["setting"].startswith(param + " =") and e[key] is not None]
            effect[(param, key)] = max(meds) if meds else 0.0
    for key, label, _src in SWEEP_MEASURES:
        order = sorted((p for p, _v in NETWORK_SWEEP), key=lambda p: -effect[(p, key)])
        lines.append(f"- **{label}**: " + ", ".join(f"{p} {effect[(p, key)]:.1f}%" for p in order))
    spread = {key: float(np.mean([effect[(p, key)] for p, _v in NETWORK_SWEEP])) for key, _l, _s in SWEEP_MEASURES}
    lines += ["", "Mean over the parameters of the largest median change (a rough robustness index, lower is more "
              "robust): " + ", ".join(f"{label} {spread[key]:.1f}%" for key, label, _s in SWEEP_MEASURES) + ".", ""]
    text = "\n".join(lines) + "\n"
    (out / "network_sweep.md").write_text(text, encoding="utf-8")
    print(text)
    return 0


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

    p = sub.add_parser("blind", help="Copy images under random codes, key written outside the repository.")
    p.add_argument("-s", dest="src", type=Path, required=True, help="Folder of .tif images to code.")
    p.add_argument("-o", dest="out", type=Path, required=True, help="Empty folder for the coded copies.")
    p.add_argument("-k", dest="key", type=Path, required=True, help="Key file (CSV) to write, outside the repository.")
    p.set_defaults(func=cmd_blind)

    p = sub.add_parser("unblind", help="Join a blinding key to a summary table.")
    p.add_argument("-s", dest="src", type=Path, required=True, help="Summary table (CSV) of a coded run.")
    p.add_argument("-k", dest="key", type=Path, required=True, help="The key written by blind.")
    p.add_argument("-o", dest="out", type=Path, required=True, help="Unblinded table (CSV) to write.")
    p.set_defaults(func=cmd_unblind)

    p = sub.add_parser("sensitivity", help="Both cuts scaled 0.8 to 1.2 and one pooled cut: percent changes.")
    p.add_argument("-d", dest="dir", type=Path, default=DEFAULT_IMAGE_DIR, help="Folder of .tif images.")
    p.add_argument("-o", dest="out", type=Path, required=True, help="Output folder (CSV, markdown, per-run json).")
    p.add_argument("-w", dest="workers", type=int, default=8, help="Parallel processes (default 8).")
    p.set_defaults(func=cmd_sensitivity, image=None)

    p = sub.add_parser("field-summary", help="Group images into fields and write per-field means.")
    p.add_argument("-d", dest="dir", type=Path, default=DEFAULT_IMAGE_DIR, help="Folder of .tif images.")
    p.add_argument("-o", dest="out", type=Path, required=True, help="Output folder.")
    p.add_argument("-r", dest="results", type=Path, default=None,
                   help="Read existing outputs from this results folder instead of running the pipeline.")
    p.add_argument("-w", dest="workers", type=int, default=8, help="Parallel processes (default 8).")
    p.set_defaults(func=cmd_field_summary, image=None)

    p = sub.add_parser("network-sweep", help="One network parameter at a time, low and high: percent changes.")
    p.add_argument("-d", dest="dir", type=Path, default=DEFAULT_IMAGE_DIR, help="Folder of .tif images.")
    p.add_argument("-o", dest="out", type=Path, required=True, help="Output folder (CSV, markdown, per-run json).")
    p.add_argument("-w", dest="workers", type=int, default=8, help="Parallel processes (default 8).")
    p.set_defaults(func=cmd_network_sweep, image=None)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
