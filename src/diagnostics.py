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
    validate-network  roots and Sholl crossings against blind hand counts
                      (and the skeleton against traced threads); -s self-test
    lacuna-candidates every object the lacuna threshold produced, with the
                      features that might tell a lacuna from a speck
    shape-picture     draw what the report-only shape measures count: the
                      axis-aligned runs, the skeleton on a cycle
    survey            what the pipeline does to every image before anything is
                      changed: lacunae, rejected candidates and why, owned,
                      unowned and pruned skeleton, attachments across a gap
                      with no signal, faint ridge signal, unattached pieces
    diagnose-untraced why a thread or a blob is missing from the result: the
                      faint ridge signal and unowned skeleton near a lacuna,
                      and the rule that rejected a blob with no outline

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
    python src/diagnostics.py unblind -s CODED_RESULTS/all_images/summary_all_images.csv -k KEY.csv -o UNBLINDED.csv
    python src/diagnostics.py sensitivity -d data/WT -o OUT_FOLDER
    python src/diagnostics.py field-summary -d data/WT -o OUT_FOLDER [-r RESULTS_FOLDER]
    python src/diagnostics.py network-sweep -d data/WT -o OUT_FOLDER
    python src/diagnostics.py validate-network -a ANNOTATION.csv -k KEY_OUTSIDE_REPO.csv -r RESULTS -o OUT
    python src/diagnostics.py validate-network -s
    python src/diagnostics.py survey -d data/WT -o results/survey
    python src/diagnostics.py diagnose-untraced -i "data/WT/543_3.tif" -o results/diagnosis \
        --lacunae 1,7 --blobs "40,290;480,460;285,855;820,155"
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import networkx as nx
import numpy as np
from scipy import ndimage as ndi
from skimage import measure, morphology, segmentation

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canaliculi  # noqa: E402
import lacunae  # noqa: E402
import quantification  # noqa: E402

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

# The quick check that the default pipeline still gives what it gave. Fixed on
# 2026-10-14, after the four lacuna rules of config section g. 543-2 is one of
# the images the acceptance test holds still, so these moved only with the
# canalicular changes, not with the lacuna ones. Means are over interior lacunae, rounded
# to 2 decimals. The third number was "gap bridges added", which no longer
# exists; roots per cell takes its place, being a headline measure that does not
# depend on ownership and the one a manual count will be compared against.
REFERENCE_VALUES = [
    ("edges per interior cell (mean edge_count)", 127.0),
    ("mean edge length, px (interior mean of mean_edge_length_px)", 17.44),
    ("roots per interior cell (mean roots_count)", 3.58),
]


def cmd_reference_check(args) -> int:
    result = quantification.analyse_image(args.image)
    s = result["summary"]
    measured = [
        round(s["edge_count"]["mean"], 2),
        round(s["mean_edge_length_px"]["mean"], 2),
        round(s["roots_count"]["mean"], 2),
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

LACUNA_SHAPE_KEYS = [f for f in quantification.shape_columns() if f != "lacuna_id"]
LACUNA_SUMMARY_KEYS = [f for f, _u in quantification.LACUNA_SUMMARY_METRICS]
CELL_KEYS = [f for f, _u, _k in quantification.CELL_METRICS]


def result_json(root: Path, label: str, kind: str = "quantification") -> Path:
    """The quantification json of one image in a results folder: every measured
    number of that image, in results/<label>/5_quantification/."""
    return quantification.quant_path(root, label, ".json")


def summary_csv(root: Path) -> Path:
    """The cross-image table of a results folder."""
    return quantification.summary_path(root, ".csv")


def numbers_from_results(root: Path, label: str) -> dict:
    """The canonical numbers of one image in a results folder."""
    q = json.load(open(result_json(root, label)))
    per_lacuna = {}
    for row in q["lacunae"]:
        per_lacuna[str(row["lacuna_id"])] = {k: row[k] for k in LACUNA_SHAPE_KEYS + CELL_KEYS}
    return {
        "lacuna_count": q["lacuna_count"],
        "interior_lacuna_count": q["interior_lacuna_count"],
        "lacunae_summary": {k: q["lacuna_shape_summary"][k] for k in LACUNA_SUMMARY_KEYS},
        "canaliculi_summary": {k: q["summary"][k] for k in CELL_KEYS},
        "field": dict(q["field"]),
        "per_lacuna": per_lacuna,
    }


def load_numbers(folder: Path) -> dict:
    """{image label: canonical numbers} for a results folder. A folder
    holding numbers.json (a saved reference snapshot) is read as is."""
    out = {}
    for sub in sorted(p for p in folder.iterdir() if p.is_dir()):
        if result_json(folder, sub.name).is_file():
            out[sub.name] = numbers_from_results(folder, sub.name)
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
        result = quantification.analyse_image(path)
        per_cell = owned_thread_distances(result)
        lac_rows = result["rows"]
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
    result = quantification.analyse_image(args.image)
    roots = {m["lacuna_id"]: m["roots_count"] for m in result["rows"]}
    rows = [
        [m["lacuna_id"], f"({m['centroid_col_px']:.0f},{m['centroid_row_px']:.0f})", f"{m['area_px2']:.0f}",
         f"{m['solidity']:.3f}", f"{m['aspect_ratio']:.2f}", roots[m["lacuna_id"]], "yes" if m["on_border"] else ""]
        for m in result["rows"]
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
        result = quantification.analyse_image(path)
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

REGRESSION_DIR = config.PROJECT_ROOT / ".cache" / "regression"
PROVENANCE_KEY = "provenance"


def regression_allowlist() -> dict:
    """Fields allowed to exist only in the regenerated output, because they
    were appended after results/ was made. Any other new field fails the
    regression. Json paths start with the file kind ("lacunae" or
    "canaliculi", since file names now carry the image label) and use "[*]"
    for a list index."""
    per_cell = [m[0] for m in quantification.NORMALISED_METRICS + quantification.NETWORK_V2_METRICS]
    json_fields = {"canaliculi:normalised_measures[*]", "canaliculi:network_v2_measures[*]",
                   "canaliculi:image_label", "lacunae:image_label"}
    for f in per_cell:
        json_fields.add(f"canaliculi:lacunae[*].{f}")
        for stat in ("mean", "median", "sd"):
            json_fields.add(f"canaliculi:summary.{f}.{stat}")
    for key in getattr(canaliculi, "FIELD_V2_KEYS", []):
        json_fields.add(f"canaliculi:field.{key}")
    for key in getattr(canaliculi, "PARAMETERS_V2_KEYS", []):
        json_fields.add(f"canaliculi:parameters.{key}")
    for key in ("narrow_crumb_rule", "fill_enclosed_holes_max_px2", "band_filter_min_opening_share",
                "fast_lacuna_stage"):
        json_fields.add(f"lacunae:parameters.{key}")
    json_fields = {f"quantification:{p.split(':', 1)[1]}" for p in json_fields}
    n_ref = quantification.SUMMARY_COLUMNS.index("field length density (px^-1)") + 1
    return {"json": json_fields, "summary_table": set(quantification.SUMMARY_COLUMNS[n_ref:])}


def regression_settings(overrides: dict) -> dict:
    """{file kind: {field path: value this run requires}}. Such a field records
    the state of a switch, not a measurement: `parameters.fast_lacuna_stage` is
    the FAST_LACUNA_STAGE switch itself, so the run with the switch on writes
    True where results/ holds False. It is checked against this run's switch
    and not compared with results/. Nothing else is exempt."""
    fast = bool(overrides.get("FAST_LACUNA_STAGE", config.FAST_LACUNA_STAGE))
    return {"quantification": {"parameters.lacunae.fast_lacuna_stage": fast}}


def print_allowlist(allow: dict) -> None:
    print("New fields allowed (appended after results/ was made; counted, not compared):")
    for path in sorted(allow["json"]):
        print(f"  json  {path}")
    for col in quantification.SUMMARY_COLUMNS:
        if col in allow["summary_table"]:
            print(f"  table {col}")
    print()


def _regenerate_one(job: tuple) -> dict:
    """Detect and measure one image and write its quantification json. Returns
    the row the cross-image table needs (small, so it can cross processes)."""
    image_path, out_root, overrides = job
    for name, value in overrides.items():
        setattr(config, name, value)
    image_path = Path(image_path)
    result = quantification.analyse_image(image_path)
    label = lacunae.image_label(image_path)
    quantification.save_json(result, result_json(Path(out_root), label))
    return {"row": quantification.summary_row(result)}


def regenerate(images: list, out_root: Path, overrides: dict | None = None, workers: int = 8) -> None:
    """Regenerate json outputs and the summary table for `images` into
    `out_root`, with the config attributes in `overrides` set in each worker."""
    from concurrent.futures import ProcessPoolExecutor

    out_root.mkdir(parents=True, exist_ok=True)
    jobs = [(str(p), str(out_root), dict(overrides or {})) for p in images]
    with ProcessPoolExecutor(max_workers=max(1, min(workers, len(jobs)))) as ex:
        results = list(ex.map(_regenerate_one, jobs))
    quantification.write_summary_rows([r["row"] for r in results], out_root)


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


def compare_json(ref_path: Path, new_path: Path, allowed: set | None = None, kind: str = "",
                 settings: dict | None = None) -> tuple:
    """(fields compared, differences, number of fields only in the new file).
    With `allowed` (allowlist paths of this file kind), a new field outside it
    is a difference. `settings` ({field path: required value}, from
    regression_settings) names the fields that record a switch of this run:
    each is checked against that value, not compared with the reference, and a
    wrong value is a difference."""
    import re

    ref = json.load(open(ref_path))
    new = json.load(open(new_path))
    ref.pop(PROVENANCE_KEY, None)
    new.pop(PROVENANCE_KEY, None)
    fr, fn = flatten_all(ref), flatten_all(new)
    diffs = []
    for path, required in (settings or {}).items():
        fr.pop(path, None)
        got = fn.pop(path, "<missing>")
        if not _equal(got, required):
            diffs.append((path, f"<switch is {required} in this run>", got))
    for k, v in fr.items():
        if k not in fn:
            diffs.append((k, v, "<missing>"))
        elif not _equal(v, fn[k]):
            diffs.append((k, v, fn[k]))
    extra = set(fn) - set(fr)
    if allowed is not None:
        index = re.compile(r"\[[0-9]+\]")
        for k in sorted(extra):
            if kind + ":" + index.sub("[*]", k) not in allowed:
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
    settings = regression_settings(overrides)
    table, ok, total, shown = [], True, 0, []
    for p in images:
        name = lacunae.image_label(p)
        n_all, d_all, x_all = 0, [], 0
        # One file per image holds every measured number, so it is compared once.
        kind = "quantification"
        r, nw = result_json(ref, name), result_json(out_root, name)
        if not r.is_file():
            d_all.append((r.name, "<no reference file>", ""))
        else:
            n, d, x = compare_json(r, nw, allow["json"], kind, settings.get(kind))
            n_all += n
            x_all += x
            d_all += [(f"{r.name}:{k}", a, b) for k, a, b in d]
        total += n_all
        passed = not d_all
        ok &= passed
        shown += [(name, *d) for d in d_all[:5]]
        table.append([name, n_all, len(d_all), x_all, "PASS" if passed else "FAIL"])
    summ = compare_summary(summary_csv(ref), summary_csv(out_root))
    s_cells = sum(n for n, _d in summ["rows"].values())
    s_diffs = [(img, *d) for img, (_n, ds) in summ["rows"].items() for d in ds]
    s_diffs += [(summary_csv(ref).name, col, "<not in results/>", "unexpected new column")
                for col in summ["extra_columns"] if col not in allow["summary_table"]]
    ok &= not s_diffs
    total += s_cells
    print_table(["image", "json fields compared", "differ", "new fields (not compared)", "result"], table,
                title=f"Regression, {label}: {out_root} against {ref} (tolerance 0, provenance ignored)\n")
    for s_kind, fields in settings.items():
        for path, required in fields.items():
            print(f"setting field checked against this run's switch, not compared with results/: "
                  f"{s_kind} {path} must be {required} in every {s_kind} json.")
    print(f"\n{summary_csv(ref).name}: {s_cells} cells compared, {len(s_diffs)} differ"
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
# names (the overnight report, tag archive-2026-10-13), every image regenerated into an ignored
# folder, and every change against results/ listed. Nothing is tuned here.

SWITCH_CHECK_DIR = config.PROJECT_ROOT / ".cache" / "switch_check"
SWITCHES_ON = [
    ("NARROW_CRUMB_RULE", True),
    ("FILL_ENCLOSED_HOLES_MAX_PX2", 200),
    ("BAND_FILTER_MIN_OPENING_SHARE", 0.515),
]
# The band-wall filter has no recommended value (the canaliculi v2 report, tag archive-2026-10-13,
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


def lacuna_changes(ref_root: Path, new_root: Path, label: str) -> tuple[list, dict]:
    """Per-lacuna changes of one image between two results folders, matched
    by centroid; and the headline values of both runs."""
    def load(root):
        q = json.load(open(result_json(root, label)))
        rows = [{"x": r["centroid_col_px"], "y": r["centroid_row_px"], "area": r["area_px2"],
                 "border": r["on_border"], "roots": r["roots_count"], "ring30": r["ring_length_r30_px"]}
                for r in q["lacunae"]]
        head = {"lacuna_count": q["lacuna_count"], "interior_count": q["interior_lacuna_count"],
                "roots_per_cell": q["summary"]["roots_count"]["mean"],
                "ring30_per_cell": q["summary"]["ring_length_r30_px"]["mean"],
                "field_density": q["field"]["canalicular_length_density_per_px"]}
        return rows, head

    ref, head_ref = load(ref_root)
    new, head_new = load(new_root)
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
            changes, head = lacuna_changes(args.ref, out, lacunae.image_label(p))
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
                        ("field_density", "field density"), ("lacuna_count", "lacuna count")]


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
    result = quantification.analyse_image(Path(path_str), t_hi, t_lo)
    s = result["summary"]
    row = {"image": lacunae.clean_name(Path(path_str)), "setting": label,
           "t_hi": result["lacunae"]["t_hi"], "t_lo": result["t_lo"],
           "lacuna_count": result["lacunae"]["lacuna_count"],
           "interior_count": result["lacunae"]["interior_lacuna_count"],
           "roots_per_cell": s["roots_count"]["mean"], "ring30_per_cell": s["ring_length_r30_px"]["mean"],
           "field_density": result["field"]["canalicular_length_density_per_px"]}
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
    label = lacunae.image_label(image_path)
    root = Path(results_dir) if results_dir else None
    if root and result_json(root, label).is_file():
        q = json.load(open(result_json(root, label)))
        rows, summary, field = q["lacunae"], q["summary"], q["field"]
    else:
        config.FAST_LACUNA_STAGE = True
        result = quantification.analyse_image(image_path)
        rows, summary, field = result["rows"], result["summary"], result["field"]
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
             "shift; two images are linked when the matched share of the smaller image lies above the largest gap",
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
# One-at-a-time sensitivity of the network stage (the canaliculi v2 report, tag archive-2026-10-13,
# S1). The lacuna stage runs once per image (fast stage, identical labels) and is
# cached; only the network stage reruns. Each parameter of src/canaliculi.py is
# set to a low and a high value (about -30% and +30%, or the nearest sensible
# integer steps) with everything else at its default; the network cut t_lo is
# scaled 0.8 to 1.2 as in sensitivity. No default changes and no value is
# recommended.

NETWORK_SWEEP = [
    ("TOPHAT_RADIUS_PX", (4, 6)),
    ("HYSTERESIS_LOW_FRACTION", (0.525, 0.975)),
    ("PRUNE_SPUR_LEN_PX", (3, 5)),
    ("ROOT_MERGE_DIST_PX", (6.0, 10.0)),
    ("LACUNA_ATTACH_REACH_PX", (7, 13)),
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
    rows = quantification.measurements_for(kept, config.CSV_FLOAT_PRECISION)
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
        result = quantification.analyse_network(image_path, lac, channel, t_lo)
    finally:
        # A worker process runs many jobs: put the default back, so no setting
        # leaks into the next job.
        if saved is not None:
            setattr(canaliculi, param, saved)
    row = {"image": lacunae.clean_name(image_path), "parameter": param or "default",
           "value": value, "t_lo": result["t_lo"]}
    for key, _label, (block, field) in SWEEP_MEASURES:
        if block == "field":
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
             "lower Otsu cut.", "",
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


# validate-network ------------------------------------------------------------------
# The validation harness (the canaliculi v2 report, tag archive-2026-10-13, V1; docs/NETWORK_TUNING_
# PROTOCOL.md). Hand counts of the blinded tiles are joined to the pipeline
# output through the key, which must lie outside the repository; unblinding
# happens only here and only in the output tables. Optional: hand-traced thread
# masks against the pipeline skeleton. -s runs a self-test on synthetic data in
# the git-ignored cache. Nothing is written under results/.

ANNOTATION_COLUMNS = ("code", "hand_roots")
KEY_COLUMNS = ("code", "image", "lacuna_id")
VALIDATION_MEASURES = ("roots_count", "sholl_crossings_r10", "sholl_crossings_r20")
TRACE_TOLERANCE_PX = 3.0
VALIDATE_SELFTEST_DIR = config.PROJECT_ROOT / ".cache" / "validate_selftest"


def _label_from(name: str) -> str:
    """The image label (results/ folder name) from a clean or a short name."""
    return lacunae.image_label(name)


def _clean_from_label(label: str) -> str:
    """The cleaned name of a label (the label itself when it is not in the table)."""
    return {v: k for k, v in config.IMAGE_LABELS.items()}.get(label, label)


def _read_csv_columns(path: Path, needed: tuple) -> list[dict]:
    import csv

    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    missing = [c for c in needed if not rows or c not in rows[0]]
    if missing:
        raise ValueError(f"{path.name}: missing column(s) {', '.join(missing)}")
    return rows


def agreement(pipe: list, hand: list) -> dict:
    """Agreement statistics of paired counts (pipeline minus hand)."""
    from scipy.stats import spearmanr

    a, b = np.asarray(pipe, dtype=float), np.asarray(hand, dtype=float)
    n = int(a.size)
    if n == 0:
        return {"n": 0}
    d = a - b
    sd = float(d.std(ddof=1)) if n >= 2 else None
    rho = None
    if n >= 3 and np.ptp(a) > 0 and np.ptp(b) > 0:
        rho = float(spearmanr(a, b)[0])
    bias = float(d.mean())
    return {"n": n, "bias": bias, "sd_diff": sd,
            "loa_low": bias - 1.96 * sd if sd is not None else None,
            "loa_high": bias + 1.96 * sd if sd is not None else None,
            "mae": float(np.abs(d).mean()), "share_equal": float((d == 0).mean()),
            "share_within_1": float((np.abs(d) <= 1).mean()), "spearman_rho": rho}


def trace_scores(skeleton: np.ndarray, trace: np.ndarray, region: np.ndarray | None = None) -> dict:
    """Precision, recall and F1 of a skeleton against a traced mask with a
    TRACE_TOLERANCE_PX tolerance: a skeleton pixel is a hit if a traced pixel
    lies within the tolerance (precision), and the reverse (recall). With
    `region`, both are restricted to it."""
    from scipy import ndimage as ndi

    sk, tr = skeleton.astype(bool), trace.astype(bool)
    if region is not None:
        sk, tr = sk & region, tr & region
    d_tr = ndi.distance_transform_edt(~tr) if tr.any() else np.full(tr.shape, np.inf)
    d_sk = ndi.distance_transform_edt(~sk) if sk.any() else np.full(sk.shape, np.inf)
    tp_p = int((sk & (d_tr <= TRACE_TOLERANCE_PX)).sum())
    tp_r = int((tr & (d_sk <= TRACE_TOLERANCE_PX)).sum())
    precision = tp_p / int(sk.sum()) if sk.any() else None
    recall = tp_r / int(tr.sum()) if tr.any() else None
    f1 = (2 * precision * recall / (precision + recall)) if precision and recall else None
    return {"skeleton_px": int(sk.sum()), "trace_px": int(tr.sum()), "precision": precision, "recall": recall,
            "f1": f1}


def _results_lacunae(folder: Path) -> dict:
    """{image label: the per-lacuna rows} of a results folder. One row per
    lacuna holds the shape and the network measures together."""
    out = {}
    for sub in sorted(p for p in folder.iterdir() if p.is_dir()):
        qj = result_json(folder, sub.name)
        if qj.is_file():
            out[sub.name] = json.load(open(qj))["lacunae"]
    return out


def run_validation(annotation: Path, key: Path, results: Path, out: Path, trace_dir: Path | None = None,
                   boxes: Path | None = None, label: str = "") -> dict:
    """The harness itself. Returns the overall statistics and trace scores."""
    import csv

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if _inside(key, config.PROJECT_ROOT):
        raise PermissionError("the key path is inside the repository; keep the key outside it")
    ann = _read_csv_columns(annotation, ANNOTATION_COLUMNS)
    keyrows = {r["code"]: r for r in _read_csv_columns(key, KEY_COLUMNS)}
    data = _results_lacunae(results)
    inputs = [{"image": n, "xy": [(r["centroid_col_px"], r["centroid_row_px"]) for r in rows]}
              for n, rows in data.items()]
    groups, _pairs, _cut = field_groups(inputs) if len(inputs) > 1 else ([[n] for n in data], [], 0.0)
    field_of = {n: f"Field {i}" for i, g in enumerate(groups, start=1) for n in g}
    joined, skipped = [], 0
    for a in ann:
        if a["hand_roots"].strip() == "":
            skipped += 1
            continue
        k = keyrows.get(a["code"])
        if k is None:
            raise ValueError(f"code {a['code']} is not in the key")
        image = _label_from(k["image"])
        cells = data[image]
        lid = int(k["lacuna_id"])
        cell = next(c for c in cells if c["lacuna_id"] == lid)
        row = {"code": a["code"], "image": image, "field": field_of.get(image, ""), "lacuna_id": lid,
               "on_border": cell["on_border"], "hand_roots": int(a["hand_roots"])}
        for m in VALIDATION_MEASURES:
            row[m] = cell.get(m)
        joined.append(row)
    out.mkdir(parents=True, exist_ok=True)
    stats = []
    for scope, key_fn in (("all", lambda r: "all"), ("image", lambda r: r["image"]), ("field", lambda r: r["field"])):
        for group in sorted({key_fn(r) for r in joined}):
            sub = [r for r in joined if key_fn(r) == group]
            for m in VALIDATION_MEASURES:
                pairs = [(r[m], r["hand_roots"]) for r in sub if r[m] is not None]
                s = agreement([p for p, _h in pairs], [h for _p, h in pairs])
                stats.append({"scope": scope, "group": group, "measure": m, **s})
    with open(out / "validation_per_lacuna.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(joined[0].keys()) if joined else ["code"])
        w.writeheader()
        w.writerows(joined)
    cols = ["scope", "group", "measure", "n", "bias", "sd_diff", "loa_low", "loa_high", "mae", "share_equal",
            "share_within_1", "spearman_rho"]
    with open(out / "validation_stats.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows([{c: s.get(c) for c in cols} for s in stats])

    trace_rows = []
    if trace_dir is not None:
        from skimage.io import imread

        box_rows = _read_csv_columns(boxes, ("image", "x0", "y0", "x1", "y1")) if boxes else None
        for image in sorted(data):
            clean = _clean_from_label(image)
            tpath = next((trace_dir / f"{n}.png" for n in (image, clean) if (trace_dir / f"{n}.png").is_file()), None)
            spath = lacunae.result_path(results, image, config.SECTION_CANALICULI, config.SUFFIX_CANALICULI_SKELETON)
            if tpath is None or not spath.is_file():
                continue
            tr = imread(tpath)
            tr = (tr[..., :3].max(axis=-1) if tr.ndim == 3 else tr) > 127
            sk = imread(spath) > 127
            if tr.shape != sk.shape:
                raise ValueError(f"trace {tpath.name} is {tr.shape}, the skeleton is {sk.shape}")
            region = None
            if box_rows is not None:
                mine = [b for b in box_rows if _label_from(b["image"]) == image]
                if not mine:
                    continue
                region = np.zeros(sk.shape, bool)
                for b in mine:
                    region[int(b["y0"]):int(b["y1"]) + 1, int(b["x0"]):int(b["x1"]) + 1] = True
            trace_rows.append({"image": image, "boxes": "yes" if region is not None else "whole image",
                               **trace_scores(sk, tr, region)})
        if trace_rows:
            with open(out / "validation_trace.csv", "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(trace_rows[0].keys()))
                w.writeheader()
                w.writerows(trace_rows)

    # Bland-Altman, one PNG with one panel per measure.
    fig, axes = plt.subplots(1, len(VALIDATION_MEASURES), figsize=(12, 4))
    for ax, m in zip(axes, VALIDATION_MEASURES):
        pairs = np.array([(r[m], r["hand_roots"]) for r in joined if r[m] is not None], dtype=float).reshape(-1, 2)
        s = next(x for x in stats if x["scope"] == "all" and x["measure"] == m)
        if pairs.size:
            mean, diff = pairs.mean(axis=1), pairs[:, 0] - pairs[:, 1]
            ax.scatter(mean, diff, s=12, c="black", alpha=0.6, linewidths=0)
            ax.axhline(s["bias"], color="#0072B2", lw=1.2)
            if s.get("sd_diff") is not None:
                for v in (s["loa_low"], s["loa_high"]):
                    ax.axhline(v, color="#D55E00", lw=1.0, ls="--")
            ax.set_title(f"{m} vs hand roots (n = {s['n']})", fontsize=9)
        else:
            ax.set_title(f"{m}: no values in this results folder", fontsize=9)
        ax.set_xlabel("mean of pipeline and hand")
        ax.set_ylabel("pipeline minus hand")
    fig.suptitle(f"{label}Bland-Altman: bias (blue), limits of agreement (dashed). Pre-validation, pixel units.",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(out / "validation_bland_altman.png", dpi=150)
    plt.close(fig)

    lines = [f"# {label}Network validation", "",
             f"Pre-validation, pixel units. Hand counts: {len(joined)} lacunae joined ({skipped} codes not counted yet). "
             "Pipeline minus hand; bias = mean difference; limits of agreement = bias plus and minus 1.96 SD.", "",
             "| scope | group | measure | n | bias | SD | LoA low | LoA high | MAE | equal | within 1 | Spearman |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]

    def fmt(v, p=3):
        return "" if v is None else (f"{v:.{p}f}" if isinstance(v, float) else str(v))

    for s in stats:
        lines.append(f"| {s['scope']} | {s['group']} | {s['measure']} | {s.get('n', 0)} | {fmt(s.get('bias'))} | "
                     f"{fmt(s.get('sd_diff'))} | {fmt(s.get('loa_low'))} | {fmt(s.get('loa_high'))} | "
                     f"{fmt(s.get('mae'))} | {fmt(s.get('share_equal'))} | {fmt(s.get('share_within_1'))} | "
                     f"{fmt(s.get('spearman_rho'))} |")
    if trace_rows:
        lines += ["", f"## Skeleton against traced threads (tolerance {TRACE_TOLERANCE_PX:g} px)", "",
                  "| image | region | skeleton px | traced px | precision | recall | F1 |", "|---|---|---|---|---|---|---|"]
        for t in trace_rows:
            lines.append(f"| {t['image']} | {t['boxes']} | {t['skeleton_px']} | {t['trace_px']} | {fmt(t['precision'])} | "
                         f"{fmt(t['recall'])} | {fmt(t['f1'])} |")
    lines += ["", "Files: validation_per_lacuna.csv, validation_stats.csv"
              + (", validation_trace.csv" if trace_rows else "") + ", validation_bland_altman.png.", ""]
    (out / "validation.md").write_text("\n".join(lines), encoding="utf-8")
    overall = {s["measure"]: s for s in stats if s["scope"] == "all"}
    return {"overall": overall, "trace": trace_rows, "joined": len(joined)}


def _selftest_validation(workers: int) -> int:
    """Synthetic data in the git-ignored cache: a fresh pipeline run (fast
    lacuna stage), hand counts equal to the pipeline roots plus fixed-seed
    noise, a key outside the repository (system temp folder), and traces equal
    to the skeleton shifted by 1 px with 5% of the pixels removed."""
    import csv
    import shutil
    import tempfile
    from concurrent.futures import ProcessPoolExecutor

    from skimage.io import imsave

    base = VALIDATE_SELFTEST_DIR
    pipe = base / "pipeline"
    images = lacunae.image_paths(argparse.Namespace(image=None, dir=DEFAULT_IMAGE_DIR))
    if not all(lacunae.result_path(pipe, lacunae.image_label(p), config.SECTION_CANALICULI,
                                   config.SUFFIX_CANALICULI_SKELETON).is_file() for p in images):
        with ProcessPoolExecutor(max_workers=max(1, min(workers, len(images)))) as ex:
            list(ex.map(_selftest_pipeline_one, [(str(p), str(pipe)) for p in images]))
    data = _results_lacunae(pipe)
    rng = np.random.default_rng(0)
    rows = []
    for image, (_lac, cells) in sorted(data.items()):
        for c in cells:
            if c["on_border"]:
                continue
            noise = int(rng.choice([-1, 0, 1], p=[0.2, 0.6, 0.2]))
            rows.append({"image": image, "lacuna_id": c["lacuna_id"],
                         "hand_roots": max(0, c["roots_count"] + noise)})
    order = rng.permutation(len(rows))
    tmp_key_dir = Path(tempfile.mkdtemp(prefix="lcn_selftest_key_"))
    key = tmp_key_dir / "selftest_key.csv"
    ann = base / "annotation.csv"
    with open(key, "w", newline="") as fk, open(ann, "w", newline="") as fa:
        wk, wa = csv.writer(fk), csv.writer(fa)
        wk.writerow(["code", "image", "lacuna_id"])
        wa.writerow(["code", "hand_roots", "hand_notes"])
        for k, i in enumerate(order, start=1):
            wk.writerow([f"T{k:03d}", rows[i]["image"], rows[i]["lacuna_id"]])
            wa.writerow([f"T{k:03d}", rows[i]["hand_roots"], "SELFTEST SYNTHETIC"])
    traces = base / "traces"
    traces.mkdir(parents=True, exist_ok=True)
    for image in data:
        sk = imread_bool(lacunae.result_path(pipe, image, config.SECTION_CANALICULI, config.SUFFIX_CANALICULI_SKELETON))
        tr = np.zeros_like(sk)
        tr[1:, :] = sk[:-1, :]
        rr, cc = np.nonzero(tr)
        drop = rng.random(rr.size) < 0.05
        tr[rr[drop], cc[drop]] = False
        imsave(traces / f"{image}.png", (tr * 255).astype(np.uint8),
               check_contrast=False)
    boxes = base / "boxes.csv"
    with open(boxes, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["image", "x0", "y0", "x1", "y1"])
        w.writerow(["543-2", 100, 100, 400, 400])
        w.writerow(["682_z08", 500, 500, 900, 900])
    refused = False
    try:
        run_validation(ann, base / "inside_key.csv", pipe, base / "refusal_test")
    except PermissionError:
        refused = True
    res_all = run_validation(ann, key, pipe, base / "out_whole", traces, None, "SELFTEST SYNTHETIC: ")
    res_box = run_validation(ann, key, pipe, base / "out_boxes", traces, boxes, "SELFTEST SYNTHETIC: ")
    shutil.rmtree(tmp_key_dir, ignore_errors=True)
    roots = res_all["overall"]["roots_count"]
    f1s = [t["f1"] for t in res_all["trace"]]
    # Negative control: one image's skeleton against another image's trace.
    names = sorted(data)
    wrong = trace_scores(imread_bool(lacunae.result_path(pipe, names[0], config.SECTION_CANALICULI,
                                                         config.SUFFIX_CANALICULI_SKELETON)),
                         imread_bool(traces / f"{names[-1]}.png"))["f1"]
    checks = [("a key inside the repository is refused", refused, "refused"),
              ("lacunae joined", res_all["joined"] == len(rows), f"{res_all['joined']} of {len(rows)}"),
              ("roots bias near 0 (|bias| < 0.2)", abs(roots["bias"]) < 0.2, f"{roots['bias']:+.3f}"),
              ("roots share within 1 = 1", roots["share_within_1"] == 1.0, f"{roots['share_within_1']:.3f}"),
              ("roots Spearman above 0.8", roots["spearman_rho"] > 0.8, f"{roots['spearman_rho']:.3f}"),
              ("F1 near 0.9 to 1 on every image (>= 0.9)", min(f1s) >= 0.9, f"{min(f1s):.3f} to {max(f1s):.3f}"),
              ("negative control: another image's trace gives F1 below 0.7", wrong < 0.7, f"{wrong:.3f}"),
              ("boxes restrict the trace comparison to 2 images", len(res_box["trace"]) == 2,
               f"{len(res_box['trace'])} images")]
    print("SELFTEST SYNTHETIC: validate-network on synthetic hand counts and traces "
          f"(outputs in {base}; nothing under results/)\n")
    print_table(["check", "value", "result"], [[c, v, "PASS" if ok else "FAIL"] for c, ok, v in checks])
    ok = all(c[1] for c in checks)
    print(f"\n{'PASS' if ok else 'FAIL'}: validate-network self-test, {sum(c[1] for c in checks)} of {len(checks)} checks.")
    return 0 if ok else 1


def imread_bool(path: Path) -> np.ndarray:
    from skimage.io import imread

    a = imread(path)
    return (a[..., :3].max(axis=-1) if a.ndim == 3 else a) > 127


def _selftest_pipeline_one(job: tuple) -> bool:
    path_str, out = job
    config.FAST_LACUNA_STAGE = True
    path = Path(path_str)
    result = quantification.analyse_image(path)
    lacunae.write_outputs(result["lacunae"], Path(out))
    canaliculi.write_outputs(result, Path(out))
    quantification.save_json(result, result_json(Path(out), lacunae.image_label(path)))
    return True


def cmd_validate_network(args) -> int:
    if args.selftest:
        return _selftest_validation(args.workers)
    for name, value in (("-a", args.annotation), ("-k", args.key), ("-r", args.results), ("-o", args.out)):
        if value is None:
            print(f"validate-network needs {name} (or -s for the self-test).")
            return 2
    if _inside(args.key, config.PROJECT_ROOT):
        print("Refused: the key path is inside the repository. Keep the key outside it.")
        return 2
    res = run_validation(args.annotation, args.key, args.results, args.out, args.trace, args.boxes)
    print((args.out / "validation.md").read_text(encoding="utf-8"))
    return 0 if res["joined"] else 1


# diagnose-untraced ---------------------------------------------------------------
# Why a thread or a blob is not in the result. DIAGNOSIS ONLY: it reads the
# pipeline's own functions, changes no parameter and writes nothing into the
# pipeline's own folders. Two parts, matching the two ways something goes
# missing: the canalicular stage did not trace it, or the lacuna stage did not
# keep it.

# Pixels this far from a lacuna body count as "near" it.
UNTRACED_RADIUS_PX = 150
# The region picture is drawn at 1:1 and again at this upscale, nearest
# neighbour, so a one-pixel skeleton is visible without inventing a pixel.
UNTRACED_ZOOM = 4
# Colours of the two skeleton classes in the region pictures.
OWNED_COLOUR = (0, 255, 0)
UNOWNED_COLOUR = (255, 0, 255)
PRUNED_COLOUR = (255, 215, 0)


def _upscale(image, factor: int):
    return image.repeat(factor, axis=0).repeat(factor, axis=1)


def untraced_detection(image_path: Path) -> dict:
    """Everything both parts need, from the pipeline's own functions, in one
    pass: the lacuna stage, the ridge response with its two cuts, and the
    network before and after the length prune."""
    lac = lacunae.analyse_image(image_path)
    display, channel = lacunae.load_channel(image_path)
    lacuna_mask, lacuna_id_map = canaliculi.build_lacuna_maps(lac["labels"], lac["kept"])
    flagged = canaliculi.flagged_structures(channel)
    preprocessed = canaliculi.preprocess_channel(channel)
    # network_candidate_mask returns the ridge response it thresholded, so the
    # response here is the one the pipeline actually used.
    _candidate, high_cut, response = canaliculi.network_candidate_mask(
        preprocessed, lacuna_mask, flagged)
    net = canaliculi.analyse_network(image_path, lac, channel)
    return {
        "label": lacunae.image_label(image_path),
        "lac": lac, "display": display, "channel": channel,
        "lacuna_id_map": lacuna_id_map, "lacuna_mask": lacuna_mask,
        "flagged": flagged, "preprocessed": preprocessed,
        "response": response,
        "high_cut": float(high_cut),
        "low_cut": float(high_cut) * canaliculi.HYSTERESIS_LOW_FRACTION,
        "skeleton": net["skeleton"],
        "skeleton_before_prune": net["skeleton_before_length_prune"],
        "owner_map": net["owner_map"],
        "graph": net["graph"], "owner": net["owner"], "node_dist": net["node_dist"],
        "length_prune": net["length_prune"],
        "t_hi": float(lac["t_hi"]),
    }


def untraced_lacuna_report(d: dict, lacuna_id: int, radius_px: int) -> dict:
    """One lacuna: the faint ridge signal near it, the skeleton it did not get,
    and (when it owns a detached network) the rule that gave it that network."""
    body = d["lacuna_id_map"] == lacuna_id
    assert body.any(), f"no lacuna with id {lacuna_id}"
    gap = ndi.distance_transform_edt(~body)
    near = gap <= radius_px

    response, low, high = d["response"], d["low_cut"], d["high_cut"]
    skel, before, owner_map = d["skeleton"], d["skeleton_before_prune"], d["owner_map"]
    # Faint ridge signal: a real response that never reached the low cut, so
    # hysteresis could not grow into it from anywhere.
    faint = near & (response >= 0.5 * low) & (response < low)
    rows, cols = np.nonzero(body)
    centroid = (float(cols.mean()), float(rows.mean()))

    owned_here = near & skel & (owner_map > 0)
    mine = near & skel & (owner_map == lacuna_id)
    unowned = near & skel & (owner_map == 0)
    pruned = near & before & ~skel

    out = {
        "lacuna_id": lacuna_id,
        "centroid_xy": [round(centroid[0], 1), round(centroid[1], 1)],
        "body_px": int(body.sum()),
        "radius_px": radius_px,
        "cuts": {
            "high_cut": round(high, 8), "low_cut": round(low, 8),
            "half_of_low_cut": round(0.5 * low, 8),
            "rule": "hysteresis on the ridge response: keep above the high cut, "
                    "and above the low cut where connected to it",
        },
        "ridge_response_near": {
            "pixels_in_region": int(near.sum()),
            "between_half_and_one_low_cut": int(faint.sum()),
            "at_or_above_low_cut": int((near & (response >= low)).sum()),
            "at_or_above_high_cut": int((near & (response >= high)).sum()),
            "what_it_means": "a pixel between 0.5 and 1.0 of the low cut carries ridge "
                             "signal that no threshold could reach, so it cannot be traced",
        },
        "skeleton_near": {
            "total_px": int((near & skel).sum()),
            "owned_by_this_lacuna_px": int(mine.sum()),
            "owned_by_any_lacuna_px": int(owned_here.sum()),
            "unowned_px": int(unowned.sum()),
            "removed_by_the_50um_prune_px": int(pruned.sum()),
        },
    }

    # Distance from the body to the nearest owned pixel, and to its own.
    for name, mask in (("nearest_pixel_owned_by_this_lacuna_px", skel & (owner_map == lacuna_id)),
                       ("nearest_pixel_owned_by_any_lacuna_px", skel & (owner_map > 0)),
                       ("nearest_skeleton_pixel_px", skel)):
        out[name] = round(float(gap[mask].min()), 4) if mask.any() else None

    # The owned skeleton as connected pieces. A lacuna whose network really
    # touches it owns one piece reaching its buffer; a lacuna handed a network
    # across empty space owns a large piece several px clear of the body.
    # On the WHOLE frame, not the region: clipping at the region edge would cut a
    # component into fragments and misstate its size.
    pieces_label = morphology.label(skel & (owner_map == lacuna_id), connectivity=2)
    pieces = []
    for i in range(1, int(pieces_label.max()) + 1):
        m = pieces_label == i
        pieces.append({"piece": i, "px": int(m.sum()),
                       "nearest_px_to_body": round(float(gap[m].min()), 4)})
    pieces.sort(key=lambda q: -q["px"])
    out["owned_pieces"] = {
        "measured_on": "the whole frame, so a piece is a true connected component",
        "count": len(pieces),
        "pieces": pieces,
        "largest_piece_px": pieces[0]["px"] if pieces else 0,
        "largest_piece_nearest_px_to_body": pieces[0]["nearest_px_to_body"] if pieces else None,
        "what_it_means": ("if the largest piece does not reach the lacuna buffer, the lacuna was "
                          "handed that network by the attachment reach and not by a traced thread"),
    }

    # The attachment rule, which is what hands a lacuna a network across a gap.
    attach = []
    for node, cell in d["owner"].items():
        if cell != lacuna_id or not d["graph"].has_node(node):
            continue
        r, c = node
        g = float(gap[r, c])
        if g <= canaliculi.LACUNA_ATTACH_REACH_PX:
            piece = int(pieces_label[r, c])
            attach.append({"node_xy": [int(c), int(r)],
                           "gap_to_body_px": round(g, 4),
                           "piece": piece,
                           "piece_px": int((pieces_label == piece).sum()) if piece else 0,
                           "gap_is_empty_space": bool(g > 1.5)})
    attach.sort(key=lambda a: a["gap_to_body_px"])
    out["ownership_rule"] = {
        "rule": ("canaliculi.attach_lacunae links the lacuna to every skeleton graph node "
                 f"within LACUNA_ATTACH_REACH_PX = {canaliculi.LACUNA_ATTACH_REACH_PX} px of its body "
                 "whose nearest lacuna is this one, with the gap as the edge weight. "
                 "canaliculi.assign_by_connectivity then runs one multi-source Dijkstra, so every "
                 "node reachable through the skeleton goes to the lacuna whose path is shortest. "
                 "Reachability is through the SKELETON, so once one node is attached the whole "
                 "connected component beyond it is owned, however far it runs, until the "
                 "config.MAX_CANALICULUS_LENGTH_UM prune cuts it back."),
        "attach_gap_px": canaliculi.LACUNA_ATTACH_REACH_PX,
        "attached_nodes": len(attach),
        "attached_nodes_detail": attach,
        "node_that_brought_the_largest_piece": max(
            (a for a in attach if a["piece_px"]), key=lambda a: a["piece_px"], default=None),
    }
    return out


def untraced_blob_report(d: dict, x: int, y: int) -> dict:
    """One blob with no outline: its intensity against the lacuna cut, its size,
    and the exact rule in src/lacunae.py that rejected it.

    The rules are replayed in the order src/lacunae.py applies them, so the rule
    named is the first one the object fails, which is the one that rejected it."""
    channel, t_hi = d["channel"], d["t_hi"]
    labels = d["lac"]["labels"]
    kept_labels = {region.label for region, _b in d["lac"]["kept"]}
    rows, cols = channel.shape

    # The mask the lacuna stage builds, replayed with the pipeline's function.
    mask, _t = lacunae.multiotsu_lacuna_mask(channel, t_hi)
    above = channel >= t_hi

    # Which object is here. The label image is the one the pipeline kept, so a
    # label at this point means the blob did become a candidate region.
    label_here = int(labels[y, x])
    if label_here == 0:
        # Nearest labelled object within a short reach, in case the point is a
        # few pixels off the blob's centre.
        near = labels[max(0, y - 15):y + 16, max(0, x - 15):x + 16]
        vals = [v for v in np.unique(near) if v]
        label_here = int(vals[0]) if len(vals) == 1 else 0

    region = None
    if label_here:
        for r in measure.regionprops(labels):
            if r.label == label_here:
                region = r
                break

    # The blob's footprint, for intensity and area. Above the cut where it
    # reaches it; otherwise the connected component of the point at the cut the
    # blob's own peak would need, which is a DIAGNOSTIC probe and no part of the
    # method: it only describes how far below the cut the blob sits.
    disc = np.zeros_like(above)
    yy, xx = np.ogrid[:rows, :cols]
    disc[(yy - y) ** 2 + (xx - x) ** 2 <= 30 ** 2] = True
    peak = float(channel[disc].max())

    if region is not None:
        foot = labels == region.label
        footprint = "the candidate region the lacuna stage built"
    elif above[y, x]:
        foot = morphology.label(above)
        foot = foot == foot[y, x]
        footprint = "the connected component of this point above the lacuna cut"
    else:
        probe = morphology.label(channel >= 0.5 * t_hi)
        lab = probe[y, x]
        foot = (probe == lab) if lab else disc
        footprint = ("the connected component of this point at HALF the lacuna cut, a "
                     "diagnostic probe only, because the blob never reaches the cut")

    area_px = int(foot.sum())
    verdict, detail = None, None
    if region is not None and region.label in kept_labels:
        verdict, detail = "kept", "this blob IS a detected lacuna"
    elif region is not None:
        # filter_regions, in its own order.
        max_area = lacunae.MAX_AREA_FRACTION_OF_IMAGE * rows * cols
        minor, major = region.axis_minor_length, region.axis_major_length
        aspect = (major / minor) if minor > 0 else float("inf")
        if region.area < lacunae.MIN_AREA_PX2:
            verdict = "minimum area"
            detail = (f"lacunae.filter_regions: area {region.area} px2 < MIN_AREA_PX2 "
                      f"{lacunae.MIN_AREA_PX2}")
        elif region.area > max_area:
            verdict = "maximum area"
            detail = (f"lacunae.filter_regions: area {region.area} px2 > "
                      f"MAX_AREA_FRACTION_OF_IMAGE {lacunae.MAX_AREA_FRACTION_OF_IMAGE} "
                      f"of the frame ({max_area:.0f} px2)")
        elif region.solidity < lacunae.MIN_SOLIDITY:
            verdict = "solidity"
            detail = (f"lacunae.filter_regions: solidity {region.solidity:.4f} < MIN_SOLIDITY "
                      f"{lacunae.MIN_SOLIDITY}")
        elif aspect > lacunae.MAX_ASPECT_RATIO:
            verdict = "aspect ratio"
            detail = (f"lacunae.filter_regions: aspect {aspect:.4f} > MAX_ASPECT_RATIO "
                      f"{lacunae.MAX_ASPECT_RATIO}")
        else:
            verdict, detail = "unclear", "it passes every filter but is not in kept"
    elif not above[y, x]:
        verdict = "threshold"
        detail = (f"lacunae.multiotsu_lacuna_mask: intensity {float(channel[y, x]):.6f} at this "
                  f"point and peak {peak:.6f} within 30 px are below the lacuna cut t_hi "
                  f"{t_hi:.6f}, so the blob never enters the mask and no later rule sees it")
    elif not mask[y, x]:
        verdict = "despeckle opening"
        detail = (f"lacunae.multiotsu_lacuna_mask: above t_hi but removed by the opening with "
                  f"radius DESPECKLE_OPENING_RADIUS_PX = {lacunae.DESPECKLE_OPENING_RADIUS_PX} px")
    else:
        verdict = "threshold"
        detail = "in the mask but no labelled object survived here"

    # Which detected lacuna owns the nearest owned thread to this blob.
    owner_map, skel = d["owner_map"], d["skeleton"]
    owned = skel & (owner_map > 0)
    nearest_owner = None
    if owned.any():
        oy, ox = np.nonzero(owned)
        dd = np.hypot(oy - y, ox - x)
        i = int(dd.argmin())
        cell = int(owner_map[oy[i], ox[i]])
        body = d["lacuna_id_map"] == cell
        br, bc = np.nonzero(body)
        nearest_owner = {
            "lacuna_id": cell,
            "distance_to_that_thread_px": round(float(dd[i]), 2),
            "thread_pixel_xy": [int(ox[i]), int(oy[i])],
            "that_lacuna_centroid_xy": [round(float(bc.mean()), 1), round(float(br.mean()), 1)],
        }

    return {
        "point_xy": [x, y],
        "intensity": {
            "at_the_point": round(float(channel[y, x]), 6),
            "peak_within_30px": round(peak, 6),
            "mean_over_footprint": round(float(channel[foot].mean()), 6),
            "lacuna_cut_t_hi": round(t_hi, 6),
            "peak_over_cut": round(peak / t_hi, 4),
            "footprint": footprint,
        },
        "size": {
            "area_px2": area_px,
            "area_um2": round(area_px * config.PIXEL_SIZE_UM_ACQUIRED ** 2, 4),
            "min_area_px2": lacunae.MIN_AREA_PX2,
            "min_area_um2": round(lacunae.MIN_AREA_PX2 * config.PIXEL_SIZE_UM_ACQUIRED ** 2, 4),
        },
        "became_a_candidate_region": region is not None,
        "rejected_by": verdict,
        "rule": detail,
        "nearest_owned_thread": nearest_owner,
    }


def untraced_region_picture(d: dict, lacuna_id: int, radius_px: int, out_dir: Path) -> list:
    """The raw channel of the region with EVERY skeleton pixel drawn on it:
    owned green, unowned magenta, and what the length prune removed gold. Saved
    at 1:1 and at UNTRACED_ZOOM times nearest neighbour."""
    from skimage.io import imsave

    body = d["lacuna_id_map"] == lacuna_id
    gap = ndi.distance_transform_edt(~body)
    near = gap <= radius_px
    rows, cols = np.nonzero(near)
    r0, r1 = int(rows.min()), int(rows.max()) + 1
    c0, c1 = int(cols.min()), int(cols.max()) + 1

    canvas = d["display"][r0:r1, c0:c1].copy()
    if canvas.ndim == 2:
        canvas = np.stack([canvas] * 3, axis=-1)
    canvas = canvas.astype(np.uint8)
    sub = lambda m: m[r0:r1, c0:c1]
    skel, owner_map = d["skeleton"], d["owner_map"]
    canvas[sub(d["skeleton_before_prune"] & ~skel)] = PRUNED_COLOUR
    canvas[sub(skel & (owner_map == 0))] = UNOWNED_COLOUR
    canvas[sub(skel & (owner_map > 0))] = OWNED_COLOUR
    # The lacuna outline, so the body is unmistakable.
    canvas[sub(segmentation.find_boundaries(body, mode="outer"))] = (0, 255, 255)

    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    stem = f"{d['label']}_lacuna{lacuna_id}_region"
    for name, image in ((f"{stem}.png", canvas),
                        (f"{stem}_x{UNTRACED_ZOOM}.png", _upscale(canvas, UNTRACED_ZOOM))):
        path = out_dir / name
        imsave(path, image, check_contrast=False)
        written.append(path)
    return written


def untraced_blob_picture(d: dict, blobs: list, out_dir: Path) -> Path:
    """The whole frame with every blob circled and labelled with what was
    measured there."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12, 12), dpi=120)
    ax.imshow(d["display"])
    for region, _b in d["lac"]["kept"]:
        ax.contour(d["lacuna_id_map"] == 0, levels=[0.5], colors="none")
    ax.contour(d["lacuna_id_map"] > 0, levels=[0.5], colors="#00ffff", linewidths=0.8)
    for i, b in enumerate(blobs, start=1):
        x, y = b["point_xy"]
        ax.add_patch(plt.Circle((x, y), 45, fill=False, color="#ffd700", lw=1.6))
        text = (f"{i}  ({x},{y})\n"
                f"peak {b['intensity']['peak_within_30px']:.3f} / cut "
                f"{b['intensity']['lacuna_cut_t_hi']:.3f} = "
                f"{b['intensity']['peak_over_cut']:.2f}\n"
                f"area {b['size']['area_px2']} px2 = {b['size']['area_um2']:.1f} um2\n"
                f"rejected by: {b['rejected_by']}")
        ax.annotate(text, (x, y), xytext=(x + 55, y + 55), color="#ffd700", fontsize=7.5,
                    bbox=dict(boxstyle="round,pad=0.3", fc="black", ec="#ffd700", alpha=0.75))
    ax.set_title(f"{d['label']}: four blobs with no lacuna outline. Cyan: the "
                 f"{len(d['lac']['kept'])} detected lacunae. Diagnosis only, no rule changed.",
                 fontsize=10)
    ax.set_axis_off()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{d['label']}_blobs_no_outline.png"
    fig.savefig(path, bbox_inches="tight", metadata={"CreationDate": None})
    plt.close(fig)
    return path


def cmd_diagnose_untraced(args) -> int:
    lacuna_ids = [int(v) for v in args.lacunae.split(",")] if args.lacunae else []
    blobs = []
    if args.blobs:
        for part in args.blobs.split(";"):
            x, y = part.split(",")
            blobs.append((int(x), int(y)))

    d = untraced_detection(args.image)
    out_dir = args.out
    report = {
        "status": "diagnosis only: no parameter, threshold or rule was changed",
        "image": args.image.name,
        "image_label": d["label"],
        "lacunae_detected_now": len(d["lac"]["kept"]),
        "lacuna_cut_t_hi": round(d["t_hi"], 6),
        "ridge_high_cut": round(d["high_cut"], 8),
        "ridge_low_cut": round(d["low_cut"], 8),
        "length_prune": d["length_prune"],
        "part1_canaliculi": [],
        "part2_lacuna_detection": [],
        "pictures": [],
    }

    for lacuna_id in lacuna_ids:
        r = untraced_lacuna_report(d, lacuna_id, args.radius)
        report["part1_canaliculi"].append(r)
        for p in untraced_region_picture(d, lacuna_id, args.radius, out_dir):
            report["pictures"].append(p.as_posix())

    for x, y in blobs:
        report["part2_lacuna_detection"].append(untraced_blob_report(d, x, y))
    if blobs:
        report["pictures"].append(
            untraced_blob_picture(d, report["part2_lacuna_detection"], out_dir).as_posix())

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{d['label']}_diagnosis.json"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, indent=2, default=float)

    print(f"{d['label']}: {len(d['lac']['kept'])} lacunae detected now; "
          f"lacuna cut t_hi {d['t_hi']:.6f}; ridge high cut {d['high_cut']:.8f}, "
          f"low cut {d['low_cut']:.8f}")
    for r in report["part1_canaliculi"]:
        s, g = r["skeleton_near"], r["ridge_response_near"]
        print(f"\n  lacuna {r['lacuna_id']} at {r['centroid_xy']}, within {r['radius_px']} px:")
        print(f"    faint ridge signal (0.5 to 1.0 of the low cut): "
              f"{g['between_half_and_one_low_cut']} px")
        print(f"    skeleton {s['total_px']} px: owned by it {s['owned_by_this_lacuna_px']}, "
              f"owned by any {s['owned_by_any_lacuna_px']}, unowned {s['unowned_px']}, "
              f"pruned by the 50 um limit {s['removed_by_the_50um_prune_px']}")
        pc = r["owned_pieces"]
        print(f"    nearest pixel it owns: {r['nearest_pixel_owned_by_this_lacuna_px']} px from "
              f"the body; attached nodes within "
              f"{r['ownership_rule']['attach_gap_px']} px: {r['ownership_rule']['attached_nodes']}")
        print(f"    owned skeleton in {pc['count']} piece(s); largest {pc['largest_piece_px']} px, "
              f"nearest {pc['largest_piece_nearest_px_to_body']} px from the body")
        bringer = r["ownership_rule"]["node_that_brought_the_largest_piece"]
        if bringer:
            print(f"    the largest piece came in through the node at "
                  f"(x={bringer['node_xy'][0]}, y={bringer['node_xy'][1]}) across a "
                  f"{bringer['gap_to_body_px']} px gap"
                  + ("  <- empty space, no thread there" if bringer["gap_is_empty_space"] else ""))
    for i, b in enumerate(report["part2_lacuna_detection"], start=1):
        n = b["nearest_owned_thread"]
        print(f"\n  blob {i} at {b['point_xy']}: peak {b['intensity']['peak_within_30px']:.4f} vs "
              f"cut {b['intensity']['lacuna_cut_t_hi']:.4f} "
              f"({b['intensity']['peak_over_cut']:.2f}x), "
              f"area {b['size']['area_px2']} px2 = {b['size']['area_um2']:.1f} um2")
        print(f"    rejected by: {b['rejected_by']}  ({b['rule']})")
        if n:
            print(f"    nearest owned thread belongs to lacuna {n['lacuna_id']} "
                  f"at {n['that_lacuna_centroid_xy']}, {n['distance_to_that_thread_px']} px away")
    print(f"\nreport -> {path}")
    for p in report["pictures"]:
        print(f"picture -> {p}")
    return 0


# survey -------------------------------------------------------------------------
# What the pipeline is doing to every image, before anything is changed.
# MEASUREMENT ONLY: it calls the pipeline's own functions, changes no parameter
# and writes nothing the pipeline reads. Six questions per image: how many
# lacunae, what was rejected and by which rule, how the skeleton divides into
# owned, unowned and pruned, how many lacuna attachments cross a gap with no
# signal in it, how much ridge signal sits below the cut near a lacuna, and how
# long the unattached skeleton components are.

# The fraction of the low cut a path must carry to count as having signal. This
# is a MEASUREMENT here, not a rule: nothing in the pipeline uses it yet. 0.7 is
# the fraction the old gap bridging required.
SURVEY_SIGNAL_FRACTION = 0.7
# Faint ridge signal is counted between this fraction of the low cut and the cut.
SURVEY_FAINT_FLOOR = 0.5
# How far from a lacuna body counts as near it.
SURVEY_NEAR_PX = 150
# Length bands for the unattached components, in micrometres.
SURVEY_LENGTH_BANDS_UM = (1.0, 2.5, 5.0, 10.0, 25.0)


def survey_path_min(signal, r0, c0, r1, c1) -> float:
    """The dimmest value of `signal` along the straight line between two points,
    sampled about once per pixel. The minimum, not the mean: one background
    pixel breaks a thread however bright its ends."""
    steps = max(2, int(round(float(np.hypot(r1 - r0, c1 - c0)))) + 1)
    rows, cols = np.linspace(r0, r1, steps), np.linspace(c0, c1, steps)
    return float(ndi.map_coordinates(signal, [rows, cols], order=1, mode="nearest").min())


def survey_rejections(lac: dict) -> dict:
    """Every candidate region the lacuna stage built, and the first rule in
    lacunae.filter_regions it fails, which is the rule that rejected it."""
    labels = lac["labels"]
    rows, cols = labels.shape
    max_area = lacunae.MAX_AREA_FRACTION_OF_IMAGE * rows * cols
    kept_labels = {r.label for r, _b in lac["kept"]}
    counts = {"kept": 0, "minimum area": 0, "maximum area": 0, "solidity": 0, "aspect ratio": 0}
    rejected = []
    for region in measure.regionprops(labels):
        if region.label in kept_labels:
            counts["kept"] += 1
            continue
        minor, major = region.axis_minor_length, region.axis_major_length
        aspect = (major / minor) if minor > 0 else float("inf")
        if region.area < lacunae.MIN_AREA_PX2:
            why = "minimum area"
        elif region.area > max_area:
            why = "maximum area"
        elif region.solidity < lacunae.MIN_SOLIDITY:
            why = "solidity"
        elif aspect > lacunae.MAX_ASPECT_RATIO:
            why = "aspect ratio"
        else:
            why = "unclear"
        counts[why] = counts.get(why, 0) + 1
        cy, cx = region.centroid
        rejected.append({"centroid_xy": [round(float(cx), 1), round(float(cy), 1)],
                         "area_px2": int(region.area),
                         "area_um2": round(region.area * config.PIXEL_SIZE_UM_ACQUIRED ** 2, 3),
                         "solidity": round(float(region.solidity), 4),
                         "aspect": round(float(aspect), 4) if np.isfinite(aspect) else None,
                         "rejected_by": why})
    rejected.sort(key=lambda r: -r["area_px2"])
    return {"counts": counts, "rejected": rejected}


def survey_image(image_path: Path) -> dict:
    """One image, every question, from the pipeline's own functions."""
    lab = lacunae.image_label(image_path)
    lac = lacunae.analyse_image(image_path)
    _display, channel = lacunae.load_channel(image_path)
    lacuna_mask, lacuna_id_map = canaliculi.build_lacuna_maps(lac["labels"], lac["kept"])
    flagged = canaliculi.flagged_structures(channel)
    preprocessed = canaliculi.preprocess_channel(channel)
    _cand, ridge_high, response = canaliculi.network_candidate_mask(
        preprocessed, lacuna_mask, flagged)
    ridge_low = ridge_high * canaliculi.HYSTERESIS_LOW_FRACTION
    # The preprocessed channel's own cuts, for the second signal measure.
    _strict, intensity_high = canaliculi.total_signal_mask(preprocessed)
    intensity_low = intensity_high * canaliculi.HYSTERESIS_LOW_FRACTION

    net = canaliculi.analyse_network(image_path, lac, channel)
    skel, owner_map = net["skeleton"], net["owner_map"]
    pruned = net["skeleton_before_length_prune"] & ~skel

    dist, indices = ndi.distance_transform_edt(lacuna_id_map == 0, return_indices=True)
    nearest_id = lacuna_id_map[indices[0], indices[1]]

    # Attachments the pipeline makes now, and what signal lies on each path. The
    # rule in force is distance alone, so every one of these was accepted.
    attachments = []
    for node in net["graph"].nodes():
        if canaliculi._is_cell_node(node):
            continue
        r, c = node
        gap = float(dist[r, c])
        if gap > canaliculi.LACUNA_ATTACH_REACH_PX:
            continue
        if int(nearest_id[r, c]) < 1:
            continue
        sr, sc = int(indices[0, r, c]), int(indices[1, r, c])
        attachments.append({
            "gap_px": round(gap, 4),
            "min_intensity": survey_path_min(preprocessed, sr, sc, r, c),
            "min_response": survey_path_min(response, sr, sc, r, c),
        })
    need_i = SURVEY_SIGNAL_FRACTION * intensity_low
    need_r = SURVEY_SIGNAL_FRACTION * ridge_low
    empty_i = sum(1 for a in attachments if a["min_intensity"] < need_i)
    empty_r = sum(1 for a in attachments if a["min_response"] < need_r)

    # Faint ridge signal near a lacuna: real response that never reached the low
    # cut, so hysteresis could not grow into it from anywhere.
    near = dist <= SURVEY_NEAR_PX
    faint = near & (response >= SURVEY_FAINT_FLOOR * ridge_low) & (response < ridge_low)

    # Unattached skeleton: components no lacuna owns, by length.
    unowned = skel & (owner_map == 0)
    comp = morphology.label(unowned, connectivity=2)
    bands = {}
    comp_lengths = []
    for i in range(1, int(comp.max()) + 1):
        n = int((comp == i).sum())
        comp_lengths.append(n)
    for n in comp_lengths:
        um = n * config.PIXEL_SIZE_UM_ACQUIRED
        name = f"under {SURVEY_LENGTH_BANDS_UM[0]:g} um"
        for lo, hi in zip(SURVEY_LENGTH_BANDS_UM, SURVEY_LENGTH_BANDS_UM[1:]):
            if lo <= um < hi:
                name = f"{lo:g} to {hi:g} um"
        if um >= SURVEY_LENGTH_BANDS_UM[-1]:
            name = f"{SURVEY_LENGTH_BANDS_UM[-1]:g} um and over"
        b = bands.setdefault(name, {"components": 0, "px": 0})
        b["components"] += 1
        b["px"] += n

    return {
        "image_label": lab,
        "lacunae_detected": len(lac["kept"]),
        "cuts": {
            "lacuna_t_hi": round(float(lac["t_hi"]), 6),
            "ridge_high": round(float(ridge_high), 8),
            "ridge_low": round(float(ridge_low), 8),
            "preprocessed_high": round(float(intensity_high), 8),
            "preprocessed_low": round(float(intensity_low), 8),
        },
        "candidate_regions": survey_rejections(lac),
        "skeleton": {
            "total_px": int(skel.sum()),
            "owned_px": int((skel & (owner_map > 0)).sum()),
            "unowned_px": int(unowned.sum()),
            "unowned_fraction": round(float(unowned.sum()) / max(1, int(skel.sum())), 4),
            "pruned_by_50um_px": int(pruned.sum()),
        },
        "attachments": {
            "total": len(attachments),
            "rule_now": f"distance alone, within {canaliculi.LACUNA_ATTACH_REACH_PX} px",
            "signal_fraction_tested": SURVEY_SIGNAL_FRACTION,
            "no_signal_by_preprocessed_intensity": empty_i,
            "no_signal_by_ridge_response": empty_r,
            "required_min_intensity": round(need_i, 8),
            "required_min_response": round(need_r, 8),
            "path_min_intensity_median": round(float(np.median(
                [a["min_intensity"] for a in attachments])), 8) if attachments else None,
            "path_min_response_median": round(float(np.median(
                [a["min_response"] for a in attachments])), 8) if attachments else None,
        },
        "faint_ridge_near_lacunae": {
            "floor_fraction": SURVEY_FAINT_FLOOR,
            "px_in_region": int(near.sum()),
            "px_between_floor_and_low_cut": int(faint.sum()),
        },
        "unattached_components": {
            "count": len(comp_lengths),
            "px": int(unowned.sum()),
            "longest_px": max(comp_lengths) if comp_lengths else 0,
            "by_length": bands,
        },
    }


def cmd_survey(args) -> int:
    images = images_from(args)
    rows = [survey_image(p) for p in images]
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / "survey.json"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"status": "measurement only, nothing in the pipeline was changed",
                   "images": rows}, f, indent=2, default=float)

    print_table(
        ["image", "lacunae", "skeleton px", "owned", "unowned", "unowned %", "pruned 50um"],
        [[r["image_label"], r["lacunae_detected"], r["skeleton"]["total_px"],
          r["skeleton"]["owned_px"], r["skeleton"]["unowned_px"],
          f'{100 * r["skeleton"]["unowned_fraction"]:.1f}%', r["skeleton"]["pruned_by_50um_px"]]
         for r in rows], title="Skeleton, per image")

    whys = ["kept", "minimum area", "solidity", "aspect ratio", "maximum area"]
    print_table(["image"] + whys,
                [[r["image_label"]] + [r["candidate_regions"]["counts"].get(w, 0) for w in whys]
                 for r in rows], title="Candidate regions, and the rule that rejected each")

    print_table(["image", "attachments", "no signal (intensity)", "no signal (response)",
                 "median path min intensity", "required"],
                [[r["image_label"], r["attachments"]["total"],
                  r["attachments"]["no_signal_by_preprocessed_intensity"],
                  r["attachments"]["no_signal_by_ridge_response"],
                  f'{r["attachments"]["path_min_intensity_median"]:.5f}',
                  f'{r["attachments"]["required_min_intensity"]:.5f}'] for r in rows],
                title=f"Attachments crossing a gap with no signal, at "
                      f"{SURVEY_SIGNAL_FRACTION} of the low cut")

    print_table(["image", "faint ridge px near lacunae", "region px", "share"],
                [[r["image_label"], r["faint_ridge_near_lacunae"]["px_between_floor_and_low_cut"],
                  r["faint_ridge_near_lacunae"]["px_in_region"],
                  f'{100 * r["faint_ridge_near_lacunae"]["px_between_floor_and_low_cut"] / max(1, r["faint_ridge_near_lacunae"]["px_in_region"]):.1f}%']
                 for r in rows],
                title=f"Ridge response between {SURVEY_FAINT_FLOOR} and 1.0 of the low cut, "
                      f"within {SURVEY_NEAR_PX} px of a lacuna")

    band_names = [f"under {SURVEY_LENGTH_BANDS_UM[0]:g} um"] + \
                 [f"{lo:g} to {hi:g} um" for lo, hi in
                  zip(SURVEY_LENGTH_BANDS_UM, SURVEY_LENGTH_BANDS_UM[1:])] + \
                 [f"{SURVEY_LENGTH_BANDS_UM[-1]:g} um and over"]
    print_table(["image", "components", "px"] + band_names,
                [[r["image_label"], r["unattached_components"]["count"],
                  r["unattached_components"]["px"]]
                 + [r["unattached_components"]["by_length"].get(b, {}).get("px", 0)
                    for b in band_names] for r in rows],
                title="Unattached skeleton components, px by component length")

    print(f"\nsurvey -> {path}")
    return 0


# shape-picture ------------------------------------------------------------------
# What the report-only shape measures count, drawn on the image. DIAGNOSIS ONLY.
# Axis-aligned runs are the thing to look at: a canaliculus has no reason to run
# perfectly along a row or a column, so a skeleton that does is following the
# pixel grid or the banding in the image rather than the tissue.

STRAIGHT_RUN_COLOUR = (0, 128, 255)   # blue: on an axis-aligned run
LOOP_COLOUR = (255, 0, 0)             # red: on a cycle, not a bridge
PLAIN_COLOUR = (0, 255, 0)            # green: ordinary skeleton


def shape_picture(image_path: Path, out_dir: Path) -> Path:
    """The skeleton over the raw image: axis-aligned runs in blue, skeleton on a
    cycle in red, the rest green, lacunae outlined cyan. Every skeleton pixel is
    drawn, one pixel wide."""
    import networkx as nx
    from skimage.io import imsave

    lab = lacunae.image_label(image_path)
    lac = lacunae.analyse_image(image_path)
    display, channel = lacunae.load_channel(image_path)
    net = canaliculi.analyse_network(image_path, lac, channel)
    skel, graph = net["skeleton"], net["graph"]

    canvas = display.copy()
    if canvas.ndim == 2:
        canvas = np.stack([canvas] * 3, axis=-1)
    canvas = canvas.astype(np.uint8)
    canvas[skel] = PLAIN_COLOUR

    # Skeleton lying on a cycle: every real edge that is not a bridge, painted
    # through the pixel paths the graph kept.
    real = canaliculi.real_subgraph(graph)
    on_cycle = np.zeros_like(skel)
    if real.number_of_edges():
        bridges = {frozenset(e) for e in nx.bridges(real)}
        for u, v in real.edges():
            if frozenset((u, v)) in bridges:
                continue
            for node in (u, v):
                r, c = node
                on_cycle[max(0, r - 1):r + 2, max(0, c - 1):c + 2] = True
        on_cycle &= skel
    canvas[on_cycle] = LOOP_COLOUR
    canvas[quantification.straight_run_mask(skel)] = STRAIGHT_RUN_COLOUR
    canvas[segmentation.find_boundaries(net["lacuna_id_map"] > 0, mode="outer")] = (0, 255, 255)

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{lab}_network_shape.png"
    imsave(path, canvas, check_contrast=False)
    return path


def cmd_shape_picture(args) -> int:
    rows = []
    for image_path in images_from(args):
        path = shape_picture(image_path, args.out)
        lab = lacunae.image_label(image_path)
        lac = lacunae.analyse_image(image_path)
        _d, channel = lacunae.load_channel(image_path)
        net = canaliculi.analyse_network(image_path, lac, channel)
        shape = quantification.network_shape_measures(net["skeleton"], net["graph"], 4)
        rows.append([lab, shape["skeleton_px"], shape["straight_run_px"],
                     shape["straight_run_fraction"], shape["rectangle_count"],
                     shape["loop_count"], shape["loop_edge_share"]])
        print(f"picture -> {path.as_posix()}", flush=True)
    print_table(["image", "skeleton px", "axis-aligned px", "straight run fraction",
                 "rectangles", "loops", "loop edge share"], rows,
                title="Network shape, report only: nothing here filters or prunes")
    return 0


# lacuna-candidates --------------------------------------------------------------
# Every object the lacuna threshold produced, with the features that might tell a
# real lacuna from a speck. MEASUREMENT ONLY: it calls the pipeline's own
# functions, changes no parameter and writes nothing the pipeline reads.
#
# The question it exists to answer is which feature separates the lacunae the eye
# finds from everything else, so a rule can be chosen on the data rather than on
# one image.

# Candidates smaller than this are not worth tabulating: they are thresholding
# specks by any reading. This is a floor for the TABLE, not for the pipeline.
CANDIDATE_MIN_AREA_PX2 = 100

# The ring just outside an object, used for "brighter than its surroundings":
# from this far out to this far out, so the ring sits off the object's own edge.
CANDIDATE_RING_INNER_PX = 2
CANDIDATE_RING_OUTER_PX = 6


def candidate_features(label_image, channel, region, kept_labels: set, t_hi: float) -> dict:
    """One candidate's features. `contrast` is the mean inside over the mean in a
    ring just outside, which asks whether the object glows above its own
    background rather than above the image's."""
    piece = label_image[region.slice] == region.label
    ring = (morphology.dilation(piece, morphology.disk(CANDIDATE_RING_OUTER_PX))
            & ~morphology.dilation(piece, morphology.disk(CANDIDATE_RING_INNER_PX)))
    sub = channel[region.slice]
    around = float(sub[ring].mean()) if ring.any() else 0.0
    minor, major = region.axis_minor_length, region.axis_major_length
    aspect = (major / minor) if minor > 0 else float("inf")
    rows, cols = label_image.shape
    min_row, min_col, max_row, max_col = region.bbox
    on_border = bool(min_row == 0 or min_col == 0 or max_row == rows or max_col == cols)
    return {
        "x": round(float(region.centroid[1]), 1),
        "y": round(float(region.centroid[0]), 1),
        "area_px2": int(region.area),
        "area_um2": round(region.area * config.PIXEL_SIZE_UM_ACQUIRED ** 2, 3),
        "aspect": round(float(aspect), 4) if np.isfinite(aspect) else None,
        "solidity": round(float(region.solidity), 4),
        "peak": round(float(region.intensity_max), 4),
        "mean": round(float(region.intensity_mean), 4),
        "ring_mean": round(around, 4),
        "contrast": round(float(region.intensity_mean) / around, 4) if around > 0 else None,
        "peak_over_cut": round(float(region.intensity_max) / t_hi, 4) if t_hi else None,
        "on_border": on_border,
        "kept": bool(region.label in kept_labels),
    }


def cmd_lacuna_candidates(args) -> int:
    rows = []
    for image_path in images_from(args):
        label = lacunae.image_label(image_path)
        lac = lacunae.analyse_image(image_path)
        _display, channel = lacunae.load_channel(image_path)
        labels = lac["labels"]
        kept_labels = {r.label for r, _b in lac["kept"]}
        for region in measure.regionprops(labels, intensity_image=channel):
            if region.area < CANDIDATE_MIN_AREA_PX2:
                continue
            rows.append({"image": label,
                         **candidate_features(labels, channel, region, kept_labels,
                                              float(lac["t_hi"]))})
        print(f"  {label}: {sum(1 for r in rows if r['image'] == label)} candidates "
              f"at or above {CANDIDATE_MIN_AREA_PX2} px2", flush=True)

    args.out.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys())
    csv_path = args.out / "lacuna_candidates.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    json_path = args.out / "lacuna_candidates.json"
    with open(json_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"status": "measurement only, nothing in the pipeline was changed",
                   "min_area_px2": CANDIDATE_MIN_AREA_PX2,
                   "ring_px": [CANDIDATE_RING_INNER_PX, CANDIDATE_RING_OUTER_PX],
                   "candidates": rows}, f, indent=2, default=float)

    kept = [r for r in rows if r["kept"]]
    rej = [r for r in rows if not r["kept"]]
    print(f"\n{len(rows)} candidates at or above {CANDIDATE_MIN_AREA_PX2} px2: "
          f"{len(kept)} kept, {len(rej)} rejected")
    for name in ("contrast", "peak_over_cut", "area_px2", "aspect", "solidity"):
        k = np.array([r[name] for r in kept if r[name] is not None], float)
        j = np.array([r[name] for r in rej if r[name] is not None], float)
        print(f"  {name:14s} kept p10 {np.percentile(k,10):7.3f} p50 {np.median(k):7.3f}   "
              f"rejected p50 {np.median(j):7.3f} p90 {np.percentile(j,90):7.3f}")
    print(f"\ntable -> {csv_path}")
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
                   help="Where to regenerate (default: .cache/regression, git-ignored).")
    p.add_argument("-r", dest="ref", type=Path, default=config.RESULTS_DIR, help="Reference folder (default: results/).")
    p.add_argument("-w", dest="workers", type=int, default=8, help="Parallel processes (default 8).")
    p.set_defaults(func=cmd_regression)

    p = sub.add_parser("switch-check", help="Each switch on alone: what changes against results/.")
    add_images_arguments(p)
    p.add_argument("-o", dest="out", type=Path, default=SWITCH_CHECK_DIR,
                   help="Where to regenerate (default: .cache/switch_check, git-ignored).")
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

    p = sub.add_parser("lacuna-candidates",
                       help="Feature table of every lacuna candidate (measurement only).")
    p.add_argument("-d", dest="dir", type=Path, default=DEFAULT_IMAGE_DIR,
                   help="Folder of .tif images.")
    p.add_argument("-i", dest="image", type=Path, default=None, help="One .tif image instead.")
    p.add_argument("-o", dest="out", type=Path, required=True, help="Output folder.")
    p.set_defaults(func=cmd_lacuna_candidates)

    p = sub.add_parser("shape-picture",
                       help="Draw what the report-only shape measures count.")
    p.add_argument("-d", dest="dir", type=Path, default=DEFAULT_IMAGE_DIR,
                   help="Folder of .tif images.")
    p.add_argument("-i", dest="image", type=Path, default=None, help="One .tif image instead.")
    p.add_argument("-o", dest="out", type=Path, required=True, help="Output folder.")
    p.set_defaults(func=cmd_shape_picture)

    p = sub.add_parser("survey",
                       help="What the pipeline does to every image (measurement only).")
    p.add_argument("-d", dest="dir", type=Path, default=DEFAULT_IMAGE_DIR,
                   help="Folder of .tif images.")
    p.add_argument("-i", dest="image", type=Path, default=None, help="One .tif image instead.")
    p.add_argument("-o", dest="out", type=Path, required=True, help="Output folder.")
    p.set_defaults(func=cmd_survey)

    p = sub.add_parser("diagnose-untraced",
                       help="Why a thread or a blob is missing from the result (diagnosis only).")
    p.add_argument("-i", dest="image", type=Path, required=True, help="One .tif image.")
    p.add_argument("-o", dest="out", type=Path, required=True, help="Output folder.")
    p.add_argument("--lacunae", default="", help="Lacuna ids to diagnose, as ID1,ID2.")
    p.add_argument("--blobs", default="",
                   help="Blobs with no outline, as X,Y;X,Y in the 1024 px frame.")
    p.add_argument("--radius", type=int, default=UNTRACED_RADIUS_PX,
                   help=f"How far from a lacuna body counts as near (default {UNTRACED_RADIUS_PX} px).")
    p.set_defaults(func=cmd_diagnose_untraced)

    p = sub.add_parser("validate-network", help="Pipeline roots and Sholl crossings against blind hand counts.")
    p.add_argument("-a", dest="annotation", type=Path, default=None, help="Annotation CSV (code, hand_roots).")
    p.add_argument("-k", dest="key", type=Path, default=None,
                   help="Key CSV of the tiles (code, image, lacuna_id), outside the repository.")
    p.add_argument("-r", dest="results", type=Path, default=None, help="Pipeline output folder (results layout).")
    p.add_argument("-o", dest="out", type=Path, default=None, help="Output folder for the tables and the plot.")
    p.add_argument("-t", dest="trace", type=Path, default=None,
                   help="Folder of hand-traced masks (PNG, white = thread, named by the image name).")
    p.add_argument("-b", dest="boxes", type=Path, default=None,
                   help="Boxes CSV (image, x0, y0, x1, y1): compare traces only inside these boxes.")
    p.add_argument("-s", dest="selftest", action="store_true", help="Self-test on synthetic data in the cache.")
    p.add_argument("-w", dest="workers", type=int, default=8, help="Parallel processes for the self-test run.")
    p.set_defaults(func=cmd_validate_network)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
