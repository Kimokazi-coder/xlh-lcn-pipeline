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
    contact           does each lacuna own the threads that touch it: the one
                      rule that holds every touching thread away from a named
                      lacuna, and a census of roots, owned px and touching but
                      unowned px for every lacuna of every image
    contact-handover  the contact rule on against off, pixel by pixel: what
                      each lacuna gained, what it lost, and whether what it lost
                      went to a body nearer that skeleton than its own
    ridge-background  does the skeleton follow the local background of the ridge
                      response, which one global cut would make it do, rather
                      than thread presence: the local background map, the tile
                      density against it, and the correlation per image
    empty-zone        what makes the hole in the skeleton around a lacuna: how
                      wide it is, and which stage of the pipeline drops each
                      visible pixel inside it
    glow-check        the glow zone rule on against off: the skeleton inside
                      and outside the zones, the empty width, roots, owned and
                      unowned px, and the three checks that rule has to pass
    hole-check        the zone from the hole (section 19) against the glow zone
                      version (section 18): the acceptance tests, the loops, and
                      the null floor of the empty width measured on synthetic
                      bodies in tissue with no hole at all
    ai-candidates     EXPERIMENT (branch exp-ai-layer): what the AI judge would
                      be asked about, per lacuna: the empty zone, the contrast
                      ratio in it and the candidate segments found there
    ai-dry-run        EXPERIMENT: what a real judge run would cost, per image,
                      and the pictures of the cases exactly as the judge sees
                      them. Nothing is sent
    ai-judge          EXPERIMENT: the judge itself, one call per lacuna, every
                      request and answer logged; --replay reruns from the log
                      offline and checks the verdicts come back the same
    ai-run            EXPERIMENT: detection, canaliculi and quantification with
                      the judge switch on for that run only, into results/ai_run/,
                      proving every other file under results/ is unchanged
    ai-compare        EXPERIMENT: judge off against judge on, per image: the
                      pictures side by side and what the verdicts moved

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
    python src/diagnostics.py contact -o results/contact --points "543_3:340,250" --pictures
    python src/diagnostics.py contact-handover -d data/WT -o results/contact_census
    python src/diagnostics.py ridge-background -d data/WT -o results/ridge_background
    python src/diagnostics.py empty-zone -d data/WT -o results/empty_zone
    python src/diagnostics.py glow-check -d data/WT -o results/glow_zone --pictures 543-2,543_3
    python src/diagnostics.py hole-check -d data/WT -o results/hole_zone --pictures 543-2,543_3
    python src/diagnostics.py ai-candidates --dir data/WT -o results/ai_dry_run
    python src/diagnostics.py ai-dry-run --dir data/WT -o results/ai_dry_run --pictures 543-2,543_3
    python src/diagnostics.py ai-judge --image "data/WT/543-2.tif"
    python src/diagnostics.py ai-judge --image "data/WT/543-2.tif" --replay -o .cache/ai_replay
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
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
# 2026-10-16, after the zone from the hole and its radial gain (METHODS section
# 19); before that, on 2026-10-14, they were 146.42 / 21.99 / 7.67 with the glow
# zone of section 18, and the three numbers moved with that rule and with the
# contact change beside it, not with anything in the lacuna stage. Means are
# over interior lacunae, rounded to 2 decimals. The third number was "gap
# bridges added", which no longer exists; roots per cell takes its place, being
# a headline measure that does not depend on ownership and the one a manual
# count will be compared against.
REFERENCE_VALUES = [
    ("edges per interior cell (mean edge_count)", 161.00),
    ("mean edge length, px (interior mean of mean_edge_length_px)", 21.63),
    ("roots per interior cell (mean roots_count)", 8.50),
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


# contact ------------------------------------------------------------------------
# Does a lacuna own the threads that touch it?
#
# MEASUREMENT ONLY: this calls the pipeline's own functions, changes no
# parameter and writes nothing the pipeline reads. Two parts.
#
# Part 1, named lacunae (--points): for each point given on the command line,
# the lacuna nearest it, every thread that comes within CONTACT_CENSUS_NEAR_PX
# of its body, and for each of those threads the ONE rule that keeps it from
# this lacuna: never traced, out of the attach reach, handed to another body by
# the nearest-lacuna partition, refused by the attach signal test, taken by the
# shortest path assignment, or cut by the 50 um length prune.
#
# Part 2, every lacuna of every image: roots, owned px, and the skeleton that
# touches the body without belonging to it, so the pattern part 1 shows can be
# counted over the whole set instead of described from examples.

# How close to a body counts as touching it. A MEASUREMENT here and not a rule:
# the network mask has every body plus a LACUNA_DILATION_PX buffer cut out of
# it, so the nearest a thread's centre line can sit is about 3 px, and 8 px is
# that buffer plus one thread half-width (p50 3.0 px). A thread this close is
# drawn against the body in the verification picture, which is why a reader
# expects the lacuna to own it.
CONTACT_CENSUS_NEAR_PX = 8
# A lacuna with fewer roots than this is counted in the census summary. A
# REPORTING line only: nothing in the pipeline reads it.
CONTACT_ROOTS_FLOOR = 3
# The region pictures. OWNED_COLOUR, UNOWNED_COLOUR and PRUNED_COLOUR are the
# ones diagnose-untraced uses; green is this lacuna's own skeleton here.
CONTACT_OTHER_COLOUR = (255, 140, 0)
CONTACT_BODY_COLOUR = (0, 255, 255)
CONTACT_ZOOM = 4
# Half-width of a region picture: wide enough to show the neighbouring lacuna
# whose network ends beside the body, and still legible at CONTACT_ZOOM.
CONTACT_PICTURE_RADIUS_PX = 120


def contact_detection(image_path: Path, contact_reach_px: int | None = None) -> dict:
    """One image through the pipeline's own functions, with everything both
    parts of the contact report read: the ridge response with its cuts and the
    threshold the attach test uses, the skeleton before and after the 50 um
    prune, the cleaned graph with its ownership, and the Euclidean partition
    attachment is decided on.

    `contact_reach_px` replaces canaliculi.CONTACT_REACH_PX for this run only,
    the module-override idiom the sweep diagnostics use; 0 turns the contact
    rule off, which is the behaviour before it existed. The default, None,
    leaves the pipeline exactly as it is configured."""
    saved = canaliculi.CONTACT_REACH_PX
    if contact_reach_px is not None:
        canaliculi.CONTACT_REACH_PX = int(contact_reach_px)
    try:
        lac = lacunae.analyse_image(image_path)
        display, channel = lacunae.load_channel(image_path)
        net = canaliculi.analyse_network(image_path, lac, channel)
        reach_used = canaliculi.CONTACT_REACH_PX
    finally:
        # A worker process runs several images: put the default back, so no
        # setting leaks into the next one.
        canaliculi.CONTACT_REACH_PX = saved
    high = float(net["t_lo"])
    low = high * canaliculi.HYSTERESIS_LOW_FRACTION
    dist, nearest_id, nearest_index = canaliculi.nearest_lacuna_map(net["lacuna_id_map"])
    # The hysteresis mask before the bodies and the specks were taken out of it,
    # with this image's own cut, so "not in the mask" can be split into reasons;
    # and the buffered bodies, which are what was taken out.
    signal, _cut = canaliculi.hysteresis_mask(net["ridge_response"], net["flagged"], high)
    return {
        "hysteresis_signal": signal,
        "buffered_lacunae": morphology.dilation(
            net["lacuna_mask"], morphology.disk(canaliculi.LACUNA_DILATION_PX)),
        "label": lacunae.image_label(image_path),
        "image_path": image_path,
        "contact_reach_px": reach_used,
        "lac": lac,
        "display": display,
        "n_lacunae": len(lac["kept"]),
        "lacuna_id_map": net["lacuna_id_map"],
        "lacuna_mask": net["lacuna_mask"],
        "candidate": net["candidate"],
        "candidate_first_pass": net["candidate_first_pass"],
        "response": net["ridge_response"],
        "flagged": net["flagged"],
        "high_cut": high,
        "low_cut": low,
        # The exact number attach_lacunae compares a path minimum against.
        "attach_min_signal": low * config.LACUNA_ATTACH_MIN_SIGNAL_FRACTION,
        "skeleton": net["skeleton"],
        "skeleton_first_pass": net["skeleton_first_pass"],
        "skeleton_before_prune": net["skeleton_before_length_prune"],
        "dim_pass_px": net["dim_pass_px"],
        "unattached": net["unattached"],
        "owner_map": net["owner_map"],
        "graph": net["graph"],
        "owner": net["owner"],
        "node_dist": net["node_dist"],
        "length_prune": net["length_prune"],
        "dist": dist,
        "nearest_id": nearest_id,
        "nearest_index": nearest_index,
        "net": net,
    }


def contact_body_gap(d: dict, lacuna_id: int) -> tuple:
    """(body mask, distance in px from that body to every pixel)."""
    body = d["lacuna_id_map"] == lacuna_id
    assert body.any(), f"no lacuna with id {lacuna_id} in {d['label']}"
    return body, ndi.distance_transform_edt(~body)


def contact_centroid(body: np.ndarray) -> list:
    rows, cols = np.nonzero(body)
    return [round(float(cols.mean()), 1), round(float(rows.mean()), 1)]


def contact_census_rows(d: dict, near_px: int) -> list:
    """One row per lacuna: roots, owned px, and the skeleton within `near_px` of
    its body that it does not own, split by who does."""
    skel, owner_map = d["skeleton"], d["owner_map"]
    pruned = d["skeleton_before_prune"] & ~skel
    rows = []
    for lacuna_id in range(1, d["n_lacunae"] + 1):
        body, gap = contact_body_gap(d, lacuna_id)
        near = gap <= near_px
        near_skel = near & skel
        mine = near_skel & (owner_map == lacuna_id)
        unowned = near_skel & (owner_map == 0)
        other = near_skel & (owner_map > 0) & (owner_map != lacuna_id)
        detail = {}
        if other.any():
            ids, counts = np.unique(owner_map[other], return_counts=True)
            detail = {int(i): int(c) for i, c in zip(ids, counts)}
        traced = contact_never_traced(d, near, near_px)
        rows.append({
            "image_label": d["label"],
            "lacuna_id": lacuna_id,
            "centroid_xy": contact_centroid(body),
            "on_frame_edge": bool(d["lac"]["kept"][lacuna_id - 1][1]),
            "body_px": int(body.sum()),
            "roots_count": quantification.cell_root_count(d["graph"], lacuna_id),
            "owned_px": int((owner_map == lacuna_id).sum()),
            "near_skeleton_px": int(near_skel.sum()),
            "near_owned_by_it_px": int(mine.sum()),
            "near_unowned_px": int(unowned.sum()),
            "near_owned_by_another_px": int(other.sum()),
            "near_owned_by_another_detail": detail,
            "near_pruned_by_50um_px": int((near & pruned).sum()),
            # Step 4: what the method never traced beside this body. Faint signal
            # is below every cut the method has, so no threshold can reach it;
            # signal above the low cut that is not in the mask is a tracing
            # failure of a different kind and is counted apart.
            "near_faint_px": traced["faint_half_low_to_low_cut"],
            "near_above_low_cut_not_in_mask_px":
                traced["above_low_cut_but_not_in_the_mask"]["total"],
            "near_untraced_in_a_flagged_canal_px":
                traced["above_low_cut_but_not_in_the_mask"]["inside_a_flagged_vascular_structure"],
            "near_untraced_despeckled_px":
                traced["above_low_cut_but_not_in_the_mask"]["in_the_mask_but_despeckled"],
            "near_signal_px": traced["at_or_above_high_cut"]
                + traced["between_low_and_high_cut"],
        })
    return rows


def contact_image_summary(d: dict, rows: list, near_px: int) -> dict:
    """The per-image aggregates the guards of step 3 are read on."""
    skel, owner_map = d["skeleton"], d["owner_map"]
    roots = [r["roots_count"] for r in rows]
    return {
        "image_label": d["label"],
        "lacunae": len(rows),
        "contact_reach_px": d["contact_reach_px"],
        "skeleton_px": int(skel.sum()),
        # Detection, which no ownership rule may touch.
        "first_pass_skeleton_px": int(d["skeleton_first_pass"].sum()),
        "dim_pass_px": int(d["dim_pass_px"]),
        "owned_px": int((skel & (owner_map > 0)).sum()),
        "unowned_px": int((skel & (owner_map == 0)).sum()),
        "unattached_px": int(d["unattached"].sum()),
        "pruned_by_50um_px": int(d["length_prune"]["removed_px"]),
        "roots_total": int(sum(roots)),
        "roots_per_lacuna_mean": round(float(np.mean(roots)), 3) if roots else None,
        "roots_min": int(min(roots)) if roots else None,
        "roots_max": int(max(roots)) if roots else None,
        f"lacunae_with_fewer_than_{CONTACT_ROOTS_FLOOR}_roots":
            sum(1 for v in roots if v < CONTACT_ROOTS_FLOOR),
        "lacunae_with_no_roots": sum(1 for v in roots if v == 0),
        "near_px": near_px,
        "lacunae_touched_by_unowned_skeleton": sum(1 for r in rows if r["near_unowned_px"] > 0),
        "lacunae_touched_by_another_lacunas_skeleton":
            sum(1 for r in rows if r["near_owned_by_another_px"] > 0),
        "near_unowned_px_total": int(sum(r["near_unowned_px"] for r in rows)),
        "near_owned_by_another_px_total": int(sum(r["near_owned_by_another_px"] for r in rows)),
        "near_owned_by_it_px_total": int(sum(r["near_owned_by_it_px"] for r in rows)),
        "near_faint_px_total": int(sum(r["near_faint_px"] for r in rows)),
        "near_above_low_cut_not_in_mask_px_total":
            int(sum(r["near_above_low_cut_not_in_mask_px"] for r in rows)),
        "near_untraced_in_a_flagged_canal_px_total":
            int(sum(r["near_untraced_in_a_flagged_canal_px"] for r in rows)),
        "near_untraced_despeckled_px_total":
            int(sum(r["near_untraced_despeckled_px"] for r in rows)),
        "lacunae_with_untraced_signal_above_the_low_cut":
            sum(1 for r in rows if r["near_above_low_cut_not_in_mask_px"] > 0),
    }


def contact_never_traced(d: dict, near: np.ndarray, near_px: int) -> dict:
    """How much ridge signal sits in the band around a body, and how much of it
    the method could never trace. Measured outside the buffered lacuna bodies,
    which are cut out of the mask, so the region is where a thread could be
    traced at all."""
    response, low, high = d["response"], d["low_cut"], d["high_cut"]
    region = near & ~d["buffered_lacunae"]
    signal = d["hysteresis_signal"]
    above_low = region & (response >= low)
    return {
        "region": f"within {near_px} px of the body and outside the buffered lacuna bodies",
        "px_in_region": int(region.sum()),
        "at_or_above_high_cut": int((region & (response >= high)).sum()),
        "between_low_and_high_cut": int((region & (response >= low) & (response < high)).sum()),
        "faint_half_low_to_low_cut": int((region & (response >= 0.5 * low)
                                          & (response < low)).sum()),
        "in_network_mask": int((region & d["candidate"]).sum()),
        "in_skeleton": int((region & d["skeleton"]).sum()),
        "above_low_cut_but_not_in_the_mask": {
            "total": int((above_low & ~d["candidate"]).sum()),
            "hysteresis_never_reached_it": int((above_low & ~signal).sum()),
            # Inside a vascular canal hysteresis may add nothing, so a pixel
            # between the cuts there is withheld by that rule and by no other.
            "inside_a_flagged_vascular_structure": int((above_low & ~signal
                                                        & d["flagged"]).sum()),
            "in_the_mask_but_despeckled": int((above_low & signal
                                               & ~d["candidate"]).sum()),
        },
        "what_it_means": ("a pixel between 0.5 and 1.0 of the low cut carries ridge signal no "
                          "threshold of this method can reach, so it is NEVER TRACED; one above "
                          "the low cut that is not in the mask was refused by hysteresis, the "
                          "body buffer or the speck filter"),
    }


def contact_lacuna_report(d: dict, lacuna_id: int, near_px: int, point: list | None = None) -> dict:
    """One lacuna in full: what it owns, what touches it, and the one rule
    responsible for every thread that touches it and belongs to something else."""
    body, gap = contact_body_gap(d, lacuna_id)
    near = gap <= near_px
    skel, owner_map, G = d["skeleton"], d["owner_map"], d["graph"]
    reach = canaliculi.LACUNA_ATTACH_REACH_PX

    near_skel = near & skel
    mine_near = near_skel & (owner_map == lacuna_id)
    unowned_near = near_skel & (owner_map == 0)
    other_near = near_skel & (owner_map > 0) & (owner_map != lacuna_id)
    other_detail = {}
    if other_near.any():
        ids, counts = np.unique(owner_map[other_near], return_counts=True)
        other_detail = {int(i): int(c) for i, c in zip(ids, counts)}

    # Connected components of the whole skeleton, so a piece is a true component
    # and not a fragment cut at the edge of the region.
    comp = morphology.label(skel, connectivity=2)
    node_comp = {}
    for node in G.nodes():
        if canaliculi._is_cell_node(node):
            continue
        node_comp[node] = int(comp[node[0], node[1]])

    # Every graph node within the attach reach of this body, and the one rule
    # that decides whether this lacuna gets it.
    dist_from_here = {}
    if G.has_node(("cell", lacuna_id)):
        dist_from_here = nx.single_source_dijkstra_path_length(
            G, ("cell", lacuna_id), weight="weight")
    nodes = []
    for node in G.nodes():
        if canaliculi._is_cell_node(node):
            continue
        r, c = node
        g = float(gap[r, c])
        if g > reach:
            continue
        nearest = int(d["nearest_id"][r, c])
        sr = int(d["nearest_index"][0, r, c])
        sc = int(d["nearest_index"][1, r, c])
        path_min = canaliculi.path_min_signal(d["response"], sr, sc, r, c)
        passes = path_min >= d["attach_min_signal"]
        attached = G.has_edge(("cell", lacuna_id), node)
        contact = attached and g <= d["contact_reach_px"]
        final = d["owner"].get(node)
        if final == lacuna_id:
            rule = ("owned by this lacuna, attached by contact" if contact
                    else "owned by this lacuna")
        elif nearest != lacuna_id:
            rule = (f"nearest-lacuna partition: attach_lacunae tests a node only against its "
                    f"nearest lacuna, which is lacuna {nearest} here")
        elif not attached:
            rule = (f"attach signal test: the dimmest point of the path is {path_min:.8f}, "
                    f"below the required {d['attach_min_signal']:.8f}, and {g:.1f} px is beyond "
                    f"the {d['contact_reach_px']} px contact reach")
        elif final is None:
            rule = "attached to this lacuna but the node is unowned"
        else:
            rule = (f"shortest path assignment: lacuna {final} reaches it at "
                    f"{d['node_dist'].get(node, float('inf')):.1f} px through the network, "
                    f"this lacuna at {dist_from_here.get(node, float('inf')):.1f} px")
        nodes.append({
            "node_xy": [int(c), int(r)],
            "gap_to_body_px": round(g, 4),
            "nearest_lacuna_id": nearest,
            "path_min_response": round(path_min, 8),
            "required_min_response": round(d["attach_min_signal"], 8),
            "passes_signal_test": bool(passes),
            "attached_to_this_lacuna": bool(attached),
            "attached_by": ("contact" if contact else "signal" if attached else None),
            "final_owner": final,
            "graph_px_from_this_lacuna": (round(float(dist_from_here[node]), 1)
                                          if node in dist_from_here else None),
            "graph_px_from_its_owner": (round(float(d["node_dist"][node]), 1)
                                        if node in d["node_dist"] else None),
            "component": node_comp.get(node),
            "rule": rule,
        })
    nodes.sort(key=lambda n: n["gap_to_body_px"])

    # The threads that touch the body, as components, with the rule each one is
    # held by. A component is reported when any of its pixels comes within
    # near_px of this body.
    pruned = d["skeleton_before_prune"] & ~skel
    touching = []
    for cid in sorted(set(int(v) for v in np.unique(comp[near_skel]) if v > 0)):
        m = comp == cid
        owners = {}
        if (m & (owner_map > 0)).any():
            ids, counts = np.unique(owner_map[m & (owner_map > 0)], return_counts=True)
            owners = {int(i): int(c) for i, c in zip(ids, counts)}
        comp_nodes = [n for n in nodes if n["component"] == cid]
        mine_px = int((m & (owner_map == lacuna_id)).sum())
        if mine_px:
            rule = "owned by this lacuna"
        elif not comp_nodes:
            rule = (f"out of the attach reach: no graph node of this thread lies within "
                    f"{reach} px of this body")
        elif not any(n["nearest_lacuna_id"] == lacuna_id for n in comp_nodes):
            rule = ("nearest-lacuna partition: every node of this thread near the body is "
                    "nearer another lacuna, so this lacuna was never tested against it")
        elif not any(n["attached_to_this_lacuna"] for n in comp_nodes):
            out_px = min(n["gap_to_body_px"] for n in comp_nodes
                         if n["nearest_lacuna_id"] == lacuna_id)
            rule = (f"attach signal test refused every node of this thread; the nearest lies "
                    f"{out_px} px out, beyond the {d['contact_reach_px']} px contact reach")
        elif owners:
            rule = (f"shortest path assignment: attached here, but lacuna "
                    f"{max(owners, key=owners.get)} reaches it on a shorter path")
        else:
            rule = "attached but unowned"
        touching.append({
            "component": cid,
            "px": int(m.sum()),
            "px_within_the_band": int((m & near_skel).sum()),
            "nearest_px_to_body": round(float(gap[m].min()), 4),
            "owners_px": owners,
            "owned_by_this_px": mine_px,
            "unowned_px": int((m & (owner_map == 0)).sum()),
            "nodes_within_the_attach_reach": len(comp_nodes),
            "nodes_with_this_lacuna_as_nearest": sum(
                1 for n in comp_nodes if n["nearest_lacuna_id"] == lacuna_id),
            "nodes_passing_the_signal_test": sum(
                1 for n in comp_nodes if n["passes_signal_test"]
                and n["nearest_lacuna_id"] == lacuna_id),
            "rule": rule,
        })
    touching.sort(key=lambda t: -t["px_within_the_band"])

    own_all = skel & (owner_map == lacuna_id)
    pieces = morphology.label(own_all, connectivity=2)
    piece_sizes = sorted((int((pieces == i).sum()) for i in range(1, int(pieces.max()) + 1)),
                         reverse=True)
    out = {
        "image_label": d["label"],
        "lacuna_id": lacuna_id,
        "point_xy": point,
        "point_to_body_px": (round(float(gap[point[1], point[0]]), 2) if point else None),
        "centroid_xy": contact_centroid(body),
        "body_px": int(body.sum()),
        "on_frame_edge": bool(d["lac"]["kept"][lacuna_id - 1][1]),
        "roots_count": quantification.cell_root_count(G, lacuna_id),
        "owned_px": int(own_all.sum()),
        "owned_pieces": len(piece_sizes),
        "owned_largest_piece_px": piece_sizes[0] if piece_sizes else 0,
        "nearest_owned_px_to_body": (round(float(gap[own_all].min()), 2)
                                     if own_all.any() else None),
        "band": {
            "near_px": near_px,
            "skeleton_px": int(near_skel.sum()),
            "owned_by_this_px": int(mine_near.sum()),
            "unowned_px": int(unowned_near.sum()),
            "owned_by_another_px": int(other_near.sum()),
            "owned_by_another_detail": other_detail,
            "pruned_by_the_50um_limit_px": int((near & pruned).sum()),
        },
        "never_traced": contact_never_traced(d, near, near_px),
        "threads_touching_the_body": touching,
        "nodes_within_the_attach_reach": nodes,
        "rules_in_force": {
            "attach_reach_px": reach,
            "attach_min_signal": round(d["attach_min_signal"], 8),
            "low_cut": round(d["low_cut"], 8),
            "high_cut": round(d["high_cut"], 8),
            "order": ("canaliculi.attach_lacunae links a lacuna to every graph node within "
                      "LACUNA_ATTACH_REACH_PX of its body WHOSE NEAREST LACUNA IS THIS ONE and "
                      "whose straight path carries at least attach_min_signal at its dimmest "
                      "point; canaliculi.assign_by_connectivity then runs one multi-source "
                      "Dijkstra, so a node goes to whichever attached lacuna reaches it on the "
                      "shortest path through the skeleton"),
        },
    }
    # The one sentence the whole report comes to.
    b = out["band"]
    if b["skeleton_px"] == 0:
        out["verdict"] = "no skeleton at all within the band: the threads here were never traced"
    elif b["owned_by_this_px"] == b["skeleton_px"]:
        out["verdict"] = "this lacuna owns every thread that touches it"
    else:
        parts = []
        if b["unowned_px"]:
            parts.append(f"{b['unowned_px']} px unowned")
        if b["owned_by_another_px"]:
            parts.append(f"{b['owned_by_another_px']} px owned by "
                         + ", ".join(f"lacuna {i}" for i in sorted(other_detail)))
        if b["pruned_by_the_50um_limit_px"]:
            parts.append(f"{b['pruned_by_the_50um_limit_px']} px cut by the 50 um limit")
        out["verdict"] = (f"{b['skeleton_px']} skeleton px touch this body and it owns "
                          f"{b['owned_by_this_px']}: " + "; ".join(parts))
    return out


def contact_point_lacuna(d: dict, x: int, y: int) -> int:
    """The lacuna a point names: the one it falls in, or the nearest body."""
    inside = int(d["lacuna_id_map"][y, x])
    return inside if inside > 0 else int(d["nearest_id"][y, x])


def contact_region_picture(d: dict, lacuna_id: int, radius_px: int, out_dir: Path,
                           tag: str) -> list:
    """The raw channel around one lacuna with every skeleton pixel drawn: this
    lacuna's own green, another lacuna's orange, unowned magenta, and what the
    50 um prune removed gold. 1:1 and at CONTACT_ZOOM times nearest neighbour,
    so the same crop can be put side by side before and after a rule change."""
    from skimage.io import imsave

    body, gap = contact_body_gap(d, lacuna_id)
    rows, cols = np.nonzero(gap <= radius_px)
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
    canvas[sub(skel & (owner_map > 0) & (owner_map != lacuna_id))] = CONTACT_OTHER_COLOUR
    canvas[sub(skel & (owner_map == lacuna_id))] = OWNED_COLOUR
    canvas[sub(segmentation.find_boundaries(body, mode="outer"))] = CONTACT_BODY_COLOUR

    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{d['label']}_lacuna{lacuna_id}_{tag}"
    written = []
    for name, image in ((f"{stem}.png", canvas),
                        (f"{stem}_x{CONTACT_ZOOM}.png", _upscale(canvas, CONTACT_ZOOM))):
        path = out_dir / name
        imsave(path, image, check_contrast=False)
        written.append(path)
    return written


def _contact_one(job: tuple) -> dict:
    """One image in a worker process: the census rows, the per-image summary and
    the full report for any point named on this image. Everything it returns is
    JSON-able, so the arrays stay in the worker."""
    path_str, points, near_px, picture_dir, radius_px, tag, contact_reach_px, verif_dir = job
    image_path = Path(path_str)
    d = contact_detection(image_path, contact_reach_px)
    rows = contact_census_rows(d, near_px)
    reports, pictures = [], []
    if verif_dir:
        # The pipeline's own verification picture, drawn from this run, so the
        # same picture can be made with the rule on and off.
        path = Path(verif_dir) / f"{d['label']}_{tag}.png"
        canaliculi.save_verification(d["net"], path)
        pictures.append(path.as_posix())
    for x, y in points:
        lacuna_id = contact_point_lacuna(d, int(x), int(y))
        if lacuna_id < 1:
            reports.append({"image_label": d["label"], "point_xy": [int(x), int(y)],
                            "error": "no lacuna was detected anywhere in this image"})
            continue
        reports.append(contact_lacuna_report(d, lacuna_id, near_px, [int(x), int(y)]))
        if picture_dir:
            for p in contact_region_picture(d, lacuna_id, radius_px, Path(picture_dir), tag):
                pictures.append(p.as_posix())
    return {
        "summary": contact_image_summary(d, rows, near_px),
        "rows": rows,
        "reports": reports,
        "pictures": pictures,
        "cuts": {"high_cut": round(d["high_cut"], 8), "low_cut": round(d["low_cut"], 8),
                 "attach_min_signal": round(d["attach_min_signal"], 8)},
        "contact_reach_px": d["contact_reach_px"],
    }


def contact_parse_points(text: str) -> dict:
    """"LABEL:X,Y;LABEL:X,Y" to {label: [(x, y), ...]}. The coordinates live on
    the command line and never in the code."""
    points: dict = {}
    for part in [p for p in text.split(";") if p.strip()]:
        label, _sep, xy = part.partition(":")
        x, y = xy.split(",")
        points.setdefault(label.strip(), []).append((int(x), int(y)))
    return points


def cmd_contact(args) -> int:
    from concurrent.futures import ProcessPoolExecutor

    images = images_from(args)
    points = contact_parse_points(args.points)
    unknown = set(points) - {lacunae.image_label(p) for p in images}
    if unknown:
        raise SystemExit(f"--points names images that are not in the run: {sorted(unknown)}")
    picture_dir = str(args.out / "pictures") if args.pictures else ""
    verif_dir = str(args.verification) if args.verification else ""
    if verif_dir:
        args.verification.mkdir(parents=True, exist_ok=True)
    jobs = [(str(p), points.get(lacunae.image_label(p), []), args.near,
             picture_dir, args.radius, args.tag, args.contact_reach, verif_dir) for p in images]
    workers = max(1, min(args.workers, len(jobs)))
    with ProcessPoolExecutor(max_workers=workers) as ex:
        out = list(ex.map(_contact_one, jobs))

    summaries = [o["summary"] for o in out]
    rows = [r for o in out for r in o["rows"]]
    reports = [r for o in out for r in o["reports"]]
    pictures = [p for o in out for p in o["pictures"]]

    floor_key = f"lacunae_with_fewer_than_{CONTACT_ROOTS_FLOOR}_roots"
    total = {
        "lacunae": len(rows),
        "images": len(summaries),
        "near_px": args.near,
        "roots_per_lacuna_mean": round(float(np.mean([r["roots_count"] for r in rows])), 3),
        floor_key: sum(1 for r in rows if r["roots_count"] < CONTACT_ROOTS_FLOOR),
        "lacunae_with_no_roots": sum(1 for r in rows if r["roots_count"] == 0),
        "lacunae_touched_by_unowned_skeleton": sum(1 for r in rows if r["near_unowned_px"] > 0),
        "lacunae_touched_by_another_lacunas_skeleton":
            sum(1 for r in rows if r["near_owned_by_another_px"] > 0),
        "lacunae_touched_by_skeleton_they_do_not_own":
            sum(1 for r in rows if r["near_unowned_px"] + r["near_owned_by_another_px"] > 0),
        "near_owned_by_it_px_total": sum(r["near_owned_by_it_px"] for r in rows),
        "near_unowned_px_total": sum(r["near_unowned_px"] for r in rows),
        "near_owned_by_another_px_total": sum(r["near_owned_by_another_px"] for r in rows),
        "near_faint_px_total": sum(r["near_faint_px"] for r in rows),
        "near_above_low_cut_not_in_mask_px_total":
            sum(r["near_above_low_cut_not_in_mask_px"] for r in rows),
        "near_untraced_in_a_flagged_canal_px_total":
            sum(r["near_untraced_in_a_flagged_canal_px"] for r in rows),
        "near_untraced_despeckled_px_total":
            sum(r["near_untraced_despeckled_px"] for r in rows),
        "lacunae_with_untraced_signal_above_the_low_cut":
            sum(1 for r in rows if r["near_above_low_cut_not_in_mask_px"] > 0),
    }
    total["fraction_of_touching_skeleton_not_owned_by_the_body_it_touches"] = round(
        (total["near_unowned_px_total"] + total["near_owned_by_another_px_total"])
        / max(1, total["near_owned_by_it_px_total"] + total["near_unowned_px_total"]
              + total["near_owned_by_another_px_total"]), 4)

    args.out.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "measurement only: no parameter, threshold or rule was changed",
        "tag": args.tag,
        "near_px": args.near,
        "roots_floor": CONTACT_ROOTS_FLOOR,
        "contact_reach_px": (canaliculi.CONTACT_REACH_PX if args.contact_reach is None
                             else args.contact_reach),
        "attach_reach_px": canaliculi.LACUNA_ATTACH_REACH_PX,
        "attach_min_signal_fraction": config.LACUNA_ATTACH_MIN_SIGNAL_FRACTION,
        "cuts_per_image": {o["summary"]["image_label"]: o["cuts"] for o in out},
        "all_images": total,
        "per_image": summaries,
        "per_lacuna": rows,
        "named_lacunae": reports,
        "pictures": pictures,
    }
    json_path = args.out / f"contact_{args.tag}.json"
    with open(json_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, indent=2, default=float)
    csv_cols = ["image_label", "lacuna_id", "centroid_xy", "on_frame_edge", "body_px",
                "roots_count", "owned_px", "near_skeleton_px", "near_owned_by_it_px",
                "near_unowned_px", "near_owned_by_another_px", "near_pruned_by_50um_px",
                "near_signal_px", "near_faint_px", "near_above_low_cut_not_in_mask_px",
                "near_untraced_in_a_flagged_canal_px", "near_untraced_despeckled_px"]
    csv_path = args.out / f"contact_{args.tag}_per_lacuna.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(csv_cols)
        for r in rows:
            w.writerow([r[c] if c != "centroid_xy" else f"{r[c][0]},{r[c][1]}" for c in csv_cols])

    # Part 1: the named lacunae.
    for r in reports:
        if "error" in r:
            print(f"\n{r['image_label']} point {r['point_xy']}: {r['error']}")
            continue
        b = r["band"]
        print(f"\n{r['image_label']}  lacuna {r['lacuna_id']} at {r['centroid_xy']} "
              f"(point {r['point_xy']}, {r['point_to_body_px']} px from the body), "
              f"body {r['body_px']} px"
              + ("  [touches the frame edge]" if r["on_frame_edge"] else ""))
        print(f"  roots {r['roots_count']}, owns {r['owned_px']} px in {r['owned_pieces']} "
              f"piece(s), largest {r['owned_largest_piece_px']} px, nearest owned px "
              f"{r['nearest_owned_px_to_body']} px from the body")
        print(f"  within {b['near_px']} px of the body: {b['skeleton_px']} skeleton px = "
              f"{b['owned_by_this_px']} its own + {b['unowned_px']} unowned + "
              f"{b['owned_by_another_px']} another lacuna's"
              + (f" {b['owned_by_another_detail']}" if b["owned_by_another_detail"] else "")
              + f"; {b['pruned_by_the_50um_limit_px']} px cut by the 50 um limit")
        n = r["never_traced"]
        print(f"  signal in the same band, outside the body buffers: {n['px_in_region']} px, "
              f"{n['at_or_above_high_cut']} at or above the high cut, "
              f"{n['between_low_and_high_cut']} between the cuts, "
              f"{n['faint_half_low_to_low_cut']} faint (never traceable), "
              f"{n['in_skeleton']} in the skeleton")
        print(f"  VERDICT: {r['verdict']}")
        for t in r["threads_touching_the_body"][:8]:
            print(f"    thread {t['component']}: {t['px']} px total, "
                  f"{t['px_within_the_band']} in the band, nearest {t['nearest_px_to_body']} px, "
                  f"owners {t['owners_px'] or 'none'}")
            print(f"      {t['rule']}")
        by_contact = sum(1 for n in r["nodes_within_the_attach_reach"]
                         if n["attached_by"] == "contact")
        print(f"  attachments: {by_contact} by contact, "
              f"{sum(1 for n in r['nodes_within_the_attach_reach'] if n['attached_by'] == 'signal')}"
              f" by signal, of {len(r['nodes_within_the_attach_reach'])} nodes within "
              f"{canaliculi.LACUNA_ATTACH_REACH_PX} px")
        refused = [n for n in r["nodes_within_the_attach_reach"]
                   if n["nearest_lacuna_id"] == r["lacuna_id"] and not n["attached_to_this_lacuna"]]
        if refused:
            print(f"    nodes it did not attach ({len(refused)} of "
                  f"{len(r['nodes_within_the_attach_reach'])} within "
                  f"{canaliculi.LACUNA_ATTACH_REACH_PX} px):")
            for n in refused[:6]:
                print(f"      ({n['node_xy'][0]}, {n['node_xy'][1]}) "
                      f"{n['gap_to_body_px']} px out, path minimum "
                      f"{n['path_min_response']:.8f} < {n['required_min_response']:.8f}")

    # Part 2: every lacuna of every image.
    print_table(["image", "id", "centroid", "edge", "roots", "owned px", "band px",
                 "its own", "unowned", "another's", "pruned"],
                [[r["image_label"], r["lacuna_id"], f"{r['centroid_xy'][0]:.0f},{r['centroid_xy'][1]:.0f}",
                  "yes" if r["on_frame_edge"] else "", r["roots_count"], r["owned_px"],
                  r["near_skeleton_px"], r["near_owned_by_it_px"], r["near_unowned_px"],
                  r["near_owned_by_another_px"], r["near_pruned_by_50um_px"]] for r in rows],
                title=f"\nEvery lacuna, {args.near} px band around each body "
                      f"(tag {args.tag})")
    print_table(["image", "lacunae", "skeleton px", "owned px", "unowned px", "roots/lacuna",
                 f"<{CONTACT_ROOTS_FLOOR} roots", "0 roots", "touched by unowned",
                 "touched by another's", "band unowned px", "band another's px"],
                [[s["image_label"], s["lacunae"], s["skeleton_px"], s["owned_px"],
                  s["unowned_px"], s["roots_per_lacuna_mean"], s[floor_key],
                  s["lacunae_with_no_roots"], s["lacunae_touched_by_unowned_skeleton"],
                  s["lacunae_touched_by_another_lacunas_skeleton"],
                  s["near_unowned_px_total"], s["near_owned_by_another_px_total"]]
                 for s in summaries],
                title="\nPer image")
    print(f"\nAll {total['images']} images, {total['lacunae']} lacunae: "
          f"{total['roots_per_lacuna_mean']} roots per lacuna, "
          f"{total[floor_key]} lacunae under {CONTACT_ROOTS_FLOOR} roots, "
          f"{total['lacunae_with_no_roots']} with none.")
    print(f"Lacunae with skeleton within {args.near} px of the body that they do not own: "
          f"{total['lacunae_touched_by_skeleton_they_do_not_own']} of {total['lacunae']} "
          f"({total['lacunae_touched_by_unowned_skeleton']} touched by unowned skeleton, "
          f"{total['lacunae_touched_by_another_lacunas_skeleton']} by another lacuna's).")
    print(f"Never traced in those bands: "
          f"{total['near_above_low_cut_not_in_mask_px_total']} px carry response above the low cut "
          f"and are not in the mask, over {total['lacunae_with_untraced_signal_above_the_low_cut']} "
          f"lacunae ({total['near_untraced_in_a_flagged_canal_px_total']} inside a vascular canal, "
          f"{total['near_untraced_despeckled_px_total']} removed as specks); "
          f"{total['near_faint_px_total']} px are faint (between half the low cut and the "
          f"low cut), which no threshold of this method can reach.")
    print(f"Skeleton px in those bands: {total['near_owned_by_it_px_total']} owned by the body "
          f"they touch, {total['near_unowned_px_total']} unowned, "
          f"{total['near_owned_by_another_px_total']} owned by another lacuna "
          f"({100 * total['fraction_of_touching_skeleton_not_owned_by_the_body_it_touches']:.1f}% "
          f"of touching skeleton is not owned by the body it touches).")
    print(f"\nreport -> {json_path}\ntable  -> {csv_path}")
    for p in pictures:
        print(f"picture -> {p}")
    return 0


# contact-handover ---------------------------------------------------------------
# What changed hands when the contact rule was turned on, pixel by pixel.
#
# MEASUREMENT ONLY. Each image is run twice in one process, once with
# canaliculi.CONTACT_REACH_PX = 0 (the behaviour before the rule) and once as
# configured, and every skeleton pixel one lacuna owned before is followed to
# where it went. That is what the per-lacuna guard is read on: a lacuna may lose
# owned skeleton, but only to a lacuna whose body is NEARER that skeleton than
# its own, which is the rule doing its work rather than taking something away.
#
# A pixel a lacuna owned before can go four ways, and they are counted apart:
#   to a lacuna that touches that thread    the guard's exception: the body the
#                           thread touches took it. "Touches" is the rule's own
#                           word: the taker holds that thread through a CONTACT
#                           attachment, a graph edge of weight 0, on that same
#                           connected component.
#   to a lacuna no nearer   reported beside it: the taker's body is no nearer
#                           those pixels in a straight line than the old owner's.
#                           Ownership runs along the network and not in straight
#                           lines, so this is a weaker test than the one above
#                           and the two are counted separately.
#   to no one               a loss the guard does not excuse
#   off the skeleton        the dim pass is seeded from OWNED skeleton, so more
#                           ownership means more seeds and the mask, and with it
#                           the centre line, can move by a pixel. Detection
#                           itself is unchanged: the first-pass skeleton is
#                           identical, which the contact census reports.

# A lacuna is listed in full when it loses at least this share of its owned
# skeleton. A REPORTING line; the guard itself is at 25%.
HANDOVER_LIST_LOSS = 0.05
HANDOVER_GUARD_LOSS = 0.25


def _handover_one(job: tuple) -> dict:
    path_str, near_px = job
    image_path = Path(path_str)
    before = contact_detection(image_path, 0)
    after = contact_detection(image_path, None)
    o0, o1 = before["owner_map"], after["owner_map"]
    skel1 = after["skeleton"]
    n = before["n_lacunae"]
    assert n == after["n_lacunae"], "the lacuna stage must not depend on an ownership rule"

    # Which lacuna touches which thread, in the rule's own terms: a contact
    # attachment is the graph edge of weight 0 that attach_lacunae adds inside
    # canaliculi.CONTACT_REACH_PX, and the thread is the connected component the
    # attached node lies on.
    comp1 = morphology.label(skel1, connectivity=2)
    touches = set()
    for u, v, data in after["graph"].edges(data=True):
        if canaliculi._is_cell_node(u) == canaliculi._is_cell_node(v):
            continue
        cell, node = (u, v) if canaliculi._is_cell_node(u) else (v, u)
        if float(data.get("weight", 1.0)) == 0.0:
            touches.add((int(cell[1]), int(comp1[node[0], node[1]])))

    # Distance from every pixel to each body, so "nearer" can be answered for
    # the exact pixels that changed hands.
    gaps = {i: contact_body_gap(before, i)[1] for i in range(1, n + 1)}

    rows = []
    for lacuna_id in range(1, n + 1):
        had = o0 == lacuna_id
        has = o1 == lacuna_id
        lost = had & ~has
        gained = has & ~had
        off_skeleton = int((lost & ~skel1).sum())
        to_none = int((lost & skel1 & (o1 == 0)).sum())
        to_nearer = to_farther = to_touching = 0
        takers: dict = {}
        taken = lost & skel1 & (o1 > 0)
        if taken.any():
            mine_gap = gaps[lacuna_id]
            for other in (int(v) for v in np.unique(o1[taken])):
                m = taken & (o1 == other)
                nearer = int((m & (gaps[other] < mine_gap)).sum())
                on_touched = int(sum((m & (comp1 == c)).sum()
                                     for c in (int(v) for v in np.unique(comp1[m]))
                                     if (other, c) in touches))
                px = int(m.sum())
                to_nearer += nearer
                to_farther += px - nearer
                to_touching += on_touched
                takers[other] = {"px": px, "nearer_px": nearer,
                                 "on_a_thread_it_touches_px": on_touched}
        owned0, owned1 = int(had.sum()), int(has.sum())
        rows.append({
            "image_label": before["label"],
            "lacuna_id": lacuna_id,
            "centroid_xy": contact_centroid(before["lacuna_id_map"] == lacuna_id),
            "owned_px_before": owned0,
            "owned_px_after": owned1,
            "change_px": owned1 - owned0,
            "change_pct": round(100.0 * (owned1 - owned0) / owned0, 2) if owned0 else None,
            "roots_before": quantification.cell_root_count(before["graph"], lacuna_id),
            "roots_after": quantification.cell_root_count(after["graph"], lacuna_id),
            "lost_px": int(lost.sum()),
            "lost_to_a_lacuna_that_touches_that_thread_px": to_touching,
            "lost_to_a_nearer_lacuna_px": to_nearer,
            "lost_to_a_lacuna_no_nearer_px": to_farther,
            "lost_to_no_one_px": to_none,
            "lost_off_the_skeleton_px": off_skeleton,
            "lost_to": takers,
            "gained_px": int(gained.sum()),
            "gained_from_unowned_px": int((gained & (o0 == 0)).sum()),
            "gained_from_another_lacuna_px": int((gained & (o0 > 0)).sum()),
        })
    return {
        "image_label": before["label"],
        "lacunae": n,
        "first_pass_skeleton_px_before": int(before["skeleton_first_pass"].sum()),
        "first_pass_skeleton_px_after": int(after["skeleton_first_pass"].sum()),
        "skeleton_px_before": int(before["skeleton"].sum()),
        "skeleton_px_after": int(skel1.sum()),
        "owned_px_before": int((before["skeleton"] & (o0 > 0)).sum()),
        "owned_px_after": int((skel1 & (o1 > 0)).sum()),
        "rows": rows,
    }


def cmd_contact_handover(args) -> int:
    from concurrent.futures import ProcessPoolExecutor

    images = images_from(args)
    jobs = [(str(p), args.near) for p in images]
    workers = max(1, min(args.workers, len(jobs)))
    with ProcessPoolExecutor(max_workers=workers) as ex:
        out = list(ex.map(_handover_one, jobs))
    rows = [r for o in out for r in o["rows"]]

    over = [r for r in rows if r["change_pct"] is not None
            and r["change_pct"] <= -100 * HANDOVER_GUARD_LOSS]
    unexcused = [r for r in rows
                 if r["lost_px"] - r["lost_to_a_lacuna_that_touches_that_thread_px"]
                 - r["lost_off_the_skeleton_px"] > 0]
    detection_held = all(o["first_pass_skeleton_px_before"] == o["first_pass_skeleton_px_after"]
                         for o in out)
    report = {
        "status": "measurement only: each image run twice, nothing in the pipeline was changed",
        "contact_reach_px": canaliculi.CONTACT_REACH_PX,
        "guard_loss_fraction": HANDOVER_GUARD_LOSS,
        "detection_unchanged_on_every_image": detection_held,
        "lacunae": len(rows),
        "lacunae_that_gained": sum(1 for r in rows if r["change_px"] > 0),
        "lacunae_unchanged": sum(1 for r in rows if r["change_px"] == 0),
        "lacunae_that_lost": sum(1 for r in rows if r["change_px"] < 0),
        "lacunae_past_the_guard": [f"{r['image_label']} lacuna {r['lacuna_id']}" for r in over],
        "lacunae_losing_px_to_a_body_that_does_not_touch_that_thread":
            [f"{r['image_label']} lacuna {r['lacuna_id']}" for r in unexcused],
        "lost_px_total": sum(r["lost_px"] for r in rows),
        "lost_to_a_lacuna_that_touches_that_thread_px_total":
            sum(r["lost_to_a_lacuna_that_touches_that_thread_px"] for r in rows),
        "lost_to_a_nearer_lacuna_px_total": sum(r["lost_to_a_nearer_lacuna_px"] for r in rows),
        "lost_to_no_one_px_total": sum(r["lost_to_no_one_px"] for r in rows),
        "lost_off_the_skeleton_px_total": sum(r["lost_off_the_skeleton_px"] for r in rows),
        "per_image": [{k: v for k, v in o.items() if k != "rows"} for o in out],
        "per_lacuna": rows,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / "contact_handover.json"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, indent=2, default=float)

    print_table(["image", "lacunae", "first-pass skel", "skeleton", "owned"],
                [[o["image_label"], o["lacunae"],
                  f"{o['first_pass_skeleton_px_before']} -> {o['first_pass_skeleton_px_after']}",
                  f"{o['skeleton_px_before']} -> {o['skeleton_px_after']}",
                  f"{o['owned_px_before']} -> {o['owned_px_after']}"] for o in out],
                title=f"Contact reach {canaliculi.CONTACT_REACH_PX} px against 0 px, per image")
    listed = sorted((r for r in rows if r["change_pct"] is not None
                     and r["change_pct"] <= -100 * HANDOVER_LIST_LOSS),
                    key=lambda r: r["change_pct"])
    print_table(["image", "id", "owned before", "after", "change", "roots", "lost px",
                 "to a body that touches it", "to a nearer body", "to no one",
                 "off the skeleton"],
                [[r["image_label"], r["lacuna_id"], r["owned_px_before"], r["owned_px_after"],
                  f"{r['change_pct']:+.1f}%", f"{r['roots_before']} -> {r['roots_after']}",
                  r["lost_px"], r["lost_to_a_lacuna_that_touches_that_thread_px"],
                  r["lost_to_a_nearer_lacuna_px"], r["lost_to_no_one_px"],
                  r["lost_off_the_skeleton_px"]] for r in listed],
                title=f"\nEvery lacuna losing at least {100 * HANDOVER_LIST_LOSS:.0f}% of its "
                      f"owned skeleton")
    print(f"\nDetection unchanged on every image (first-pass skeleton pixel for pixel): "
          f"{detection_held}")
    print(f"{report['lacunae_that_gained']} lacunae gained, {report['lacunae_unchanged']} "
          f"unchanged, {report['lacunae_that_lost']} lost.")
    print(f"Past the {100 * HANDOVER_GUARD_LOSS:.0f}% guard: "
          f"{report['lacunae_past_the_guard'] or 'none'}.")
    for r in over:
        print(f"  {r['image_label']} lacuna {r['lacuna_id']}: {r['lost_px']} px lost, "
              f"{r['lost_to_a_lacuna_that_touches_that_thread_px']} to a body that touches that "
              f"thread, {r['lost_to_a_nearer_lacuna_px']} to a nearer body, "
              f"{r['lost_to_no_one_px']} to no one, "
              f"{r['lost_off_the_skeleton_px']} off the skeleton; roots "
              f"{r['roots_before']} -> {r['roots_after']}; taken by {r['lost_to']}")
    print(f"Of {report['lost_px_total']} px that changed hands, "
          f"{report['lost_to_a_lacuna_that_touches_that_thread_px_total']} went to a lacuna that "
          f"touches that thread, {report['lost_to_no_one_px_total']} to no one and "
          f"{report['lost_off_the_skeleton_px_total']} off the skeleton.")
    print(f"Lacunae that lost skeleton to a body that does not touch that thread: "
          f"{report['lacunae_losing_px_to_a_body_that_does_not_touch_that_thread'] or 'none'}.")
    print(f"\nreport -> {path}")
    return 0


# ridge-background ---------------------------------------------------------------
# Does the skeleton follow local brightness instead of thread presence?
#
# MEASUREMENT ONLY, and a TEST with its decision rule fixed before it ran. The
# ridge response is thresholded with ONE cut per image, from that image's own
# histogram. If a dim corner of a field carries real threads, a global cut will
# miss them there while passing a mesh of them where the field is bright. The
# signature of that failure is a positive relation between the LOCAL BACKGROUND
# of the ridge response and the LOCAL SKELETON DENSITY: where the floor is
# higher, more of the image clears one fixed cut.
#
# The decision rule, written down before the numbers were seen:
#   proceed only if the median Spearman rho over the 8 images is at least +0.50
#   and at least 7 of the 8 images are positive. Anything less is reported as
#   weak and the work stops there.
# Spearman and not Pearson is the headline, because the relation has no reason
# to be linear and one bright tile should not carry the answer.

# The local background: the percentile of the ridge response taken in windows of
# this size, with every lacuna body and its mask buffer left out, on a grid of
# this stride, then smoothed over the grid and resampled to the full frame.
# A low percentile, because the background is what the quiet part of a window
# sits at, not what its threads do; 25 keeps enough pixels per window to be
# stable (a 100 px window holds 10,000 of them).
RIDGE_BACKGROUND_PERCENTILE = 25
RIDGE_BACKGROUND_WINDOW_PX = 100
RIDGE_BACKGROUND_STRIDE_PX = 50
# Smoothing of the grid, in grid cells, so the map is a field and not a staircase.
RIDGE_BACKGROUND_SMOOTH_CELLS = 1.0
# Tiles the density is counted in. The brief's unit, and one tile holds a few
# whole threads.
RIDGE_TILE_PX = 100
# A tile is used only if this much of it is outside the lacuna bodies and their
# buffer, which is where a thread could be traced at all.
RIDGE_TILE_MIN_AVAILABLE = 0.25
# The gate.
RIDGE_GATE_MEDIAN_RHO = 0.50
RIDGE_GATE_MIN_POSITIVE = 7


def ridge_background_map(response: np.ndarray, excluded: np.ndarray) -> np.ndarray:
    """The local background of the ridge response, same shape as the response.

    In each RIDGE_BACKGROUND_WINDOW_PX window on a RIDGE_BACKGROUND_STRIDE_PX
    grid, the RIDGE_BACKGROUND_PERCENTILE percentile of the response over the
    pixels that are not `excluded` (the lacuna bodies and their buffer, which
    carry no thread by construction). The grid is then smoothed over
    RIDGE_BACKGROUND_SMOOTH_CELLS cells and resampled to the frame, so the map
    is a slowly varying field rather than a staircase."""
    height, width = response.shape
    half = RIDGE_BACKGROUND_WINDOW_PX // 2
    centres_r = np.arange(0, height, RIDGE_BACKGROUND_STRIDE_PX)
    centres_c = np.arange(0, width, RIDGE_BACKGROUND_STRIDE_PX)
    grid = np.zeros((centres_r.size, centres_c.size), dtype=np.float64)
    usable = ~excluded
    fallback = float(np.percentile(response[usable], RIDGE_BACKGROUND_PERCENTILE)) \
        if usable.any() else 0.0
    for i, r in enumerate(centres_r):
        r0, r1 = max(0, r - half), min(height, r + half)
        for j, c in enumerate(centres_c):
            c0, c1 = max(0, c - half), min(width, c + half)
            window = response[r0:r1, c0:c1][usable[r0:r1, c0:c1]]
            grid[i, j] = (float(np.percentile(window, RIDGE_BACKGROUND_PERCENTILE))
                          if window.size else fallback)
    grid = ndi.gaussian_filter(grid, RIDGE_BACKGROUND_SMOOTH_CELLS, mode="nearest")
    # Resample the grid to the frame: the grid cell (i, j) sits at the pixel
    # (i * stride, j * stride), so the map is a bilinear interpolation of it.
    rows = np.arange(height) / RIDGE_BACKGROUND_STRIDE_PX
    cols = np.arange(width) / RIDGE_BACKGROUND_STRIDE_PX
    rr, cc = np.meshgrid(rows, cols, indexing="ij")
    return ndi.map_coordinates(grid, [rr, cc], order=1, mode="nearest")


def ridge_tiles(d: dict, background: np.ndarray) -> list:
    """One row per RIDGE_TILE_PX tile: the mean local background in it, and the
    skeleton density over the area where a thread could be traced."""
    skel = d["skeleton"]
    excluded = d["buffered_lacunae"]
    height, width = skel.shape
    height = int(height)
    width = int(width)
    rows = []
    for r0 in range(0, height, RIDGE_TILE_PX):
        for c0 in range(0, width, RIDGE_TILE_PX):
            r1, c1 = min(height, r0 + RIDGE_TILE_PX), min(width, c0 + RIDGE_TILE_PX)
            area = (r1 - r0) * (c1 - c0)
            free = int((~excluded[r0:r1, c0:c1]).sum())
            if free < RIDGE_TILE_MIN_AVAILABLE * area:
                continue
            tile = skel[r0:r1, c0:c1]
            px = int(tile.sum())
            owned = int((tile & (d["owner_map"][r0:r1, c0:c1] > 0)).sum())
            rows.append({
                "image_label": d["label"],
                "tile_xy": [c0, r0],
                "quadrant": ("top" if r0 + RIDGE_TILE_PX <= height / 2 else "bottom")
                            + " " + ("left" if c0 + RIDGE_TILE_PX <= width / 2 else "right"),
                "area_px": int(area),
                "free_px": free,
                "skeleton_px": px,
                "owned_px": owned,
                "owned_fraction": round(owned / px, 6) if px else None,
                "skeleton_density_per_free_px": round(px / free, 6),
                "owned_density_per_free_px": round(owned / free, 6),
                "skeleton_density_per_px": round(px / area, 6),
                "background": round(float(background[r0:r1, c0:c1].mean()), 10),
            })
    return rows


def _ridge_one(job: tuple) -> dict:
    path_str, out_dir = job
    from scipy import stats

    d = contact_detection(Path(path_str))
    background = ridge_background_map(d["response"], d["buffered_lacunae"])
    rows = ridge_tiles(d, background)
    x = np.array([r["background"] for r in rows], dtype=float)
    y = np.array([r["skeleton_density_per_free_px"] for r in rows], dtype=float)
    rho, rho_p = stats.spearmanr(x, y)
    r_lin, r_p = stats.pearsonr(x, y)
    # The same tiles, asked about ownership: the attach signal test is a fixed
    # fraction of the SAME global cut, so if a dim area is punished anywhere it
    # should show here as well as in the density.
    owned_y = np.array([r["owned_density_per_free_px"] for r in rows], dtype=float)
    frac = np.array([r["owned_fraction"] for r in rows if r["owned_fraction"] is not None],
                    dtype=float)
    frac_x = np.array([r["background"] for r in rows if r["owned_fraction"] is not None],
                      dtype=float)
    rho_owned, rho_owned_p = stats.spearmanr(x, owned_y)
    rho_frac, rho_frac_p = stats.spearmanr(frac_x, frac)
    quadrants = {}
    for name in sorted({r["quadrant"] for r in rows}):
        sub = [r for r in rows if r["quadrant"] == name]
        sk = sum(r["skeleton_px"] for r in sub)
        quadrants[name] = {
            "tiles": len(sub),
            "background_mean": round(float(np.mean([r["background"] for r in sub])), 10),
            "skeleton_density_per_free_px": round(sk / sum(r["free_px"] for r in sub), 6),
            "owned_fraction": round(sum(r["owned_px"] for r in sub) / sk, 4) if sk else None,
        }
    # The dimmest and brightest quarters of the tiles, which is where the
    # hypothesis says the damage is.
    order = np.argsort(x)
    quarter = max(1, len(order) // 4)
    dim, bright = order[:quarter], order[-quarter:]
    picture = ridge_background_picture(d, background, rows, Path(out_dir), float(rho))
    return {
        "image_label": d["label"],
        "tiles": len(rows),
        "spearman_rho": round(float(rho), 4),
        "spearman_p": float(rho_p),
        "pearson_r": round(float(r_lin), 4),
        "pearson_p": float(r_p),
        "background_min": round(float(x.min()), 10),
        "background_median": round(float(np.median(x)), 10),
        "background_max": round(float(x.max()), 10),
        "background_ratio_max_over_min": round(float(x.max() / x.min()), 3) if x.min() else None,
        "density_dim_quarter": round(float(y[dim].mean()), 6),
        "density_bright_quarter": round(float(y[bright].mean()), 6),
        "density_bright_over_dim": (round(float(y[bright].mean() / y[dim].mean()), 3)
                                    if y[dim].mean() else None),
        "spearman_rho_owned_density": round(float(rho_owned), 4),
        "spearman_rho_owned_fraction": round(float(rho_frac), 4),
        "spearman_p_owned_fraction": float(rho_frac_p),
        "owned_fraction_dim_quarter": round(float(np.mean(
            [rows[i]["owned_fraction"] for i in dim if rows[i]["owned_fraction"] is not None])), 4),
        "owned_fraction_bright_quarter": round(float(np.mean(
            [rows[i]["owned_fraction"] for i in bright
             if rows[i]["owned_fraction"] is not None])), 4),
        "quadrants": quadrants,
        "ridge_high_cut": round(d["high_cut"], 8),
        "ridge_low_cut": round(d["low_cut"], 8),
        "skeleton_px": int(d["skeleton"].sum()),
        "picture": picture.as_posix(),
        "rows": rows,
    }


def ridge_background_picture(d: dict, background: np.ndarray, rows: list, out_dir: Path,
                             rho: float | None = None) -> Path:
    """The local background map beside the image's own verification picture,
    with the tile density against the background under them."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    verification = d["display"].copy()
    n = d["n_lacunae"]
    colors = canaliculi.lacuna_colors(n)
    for lacuna_id in range(1, n + 1):
        color = colors[lacuna_id]
        verification[segmentation.find_boundaries(d["lacuna_id_map"] == lacuna_id,
                                                  mode="outer")] = color
        owned = d["skeleton"] & (d["owner_map"] == lacuna_id)
        if owned.any():
            verification[morphology.dilation(owned, morphology.disk(1))] = color

    fig = plt.figure(figsize=(16, 6.4), dpi=130)
    ax1 = fig.add_subplot(1, 3, 1)
    im = ax1.imshow(background, cmap="magma")
    ax1.set_title(f"{d['label']}: local background of the ridge response\n"
                  f"(p{RIDGE_BACKGROUND_PERCENTILE} in {RIDGE_BACKGROUND_WINDOW_PX} px windows, "
                  f"bodies masked)", fontsize=8)
    ax1.set_axis_off()
    fig.colorbar(im, ax=ax1, fraction=0.046)

    ax2 = fig.add_subplot(1, 3, 2)
    ax2.imshow(verification)
    ax2.set_title(f"{d['label']}: what the pipeline owns\n"
                  f"(each lacuna and the threads it owns, unowned not drawn)", fontsize=8)
    ax2.set_axis_off()

    ax3 = fig.add_subplot(1, 3, 3)
    x = [r["background"] for r in rows]
    y = [r["skeleton_density_per_free_px"] for r in rows]
    ax3.scatter(x, y, s=14, alpha=0.7, color="#1f77b4")
    ax3.set_xlabel("local background of the ridge response", fontsize=8)
    ax3.set_ylabel(f"skeleton px per free px, {RIDGE_TILE_PX} px tiles", fontsize=8)
    ax3.set_title("one point per tile"
                  + ("" if rho is None else f", Spearman rho {rho:+.3f}"), fontsize=8)
    ax3.tick_params(labelsize=7)
    fig.suptitle("Measurement only: the cut was not changed. If these rise together, one global "
                 "cut is following local brightness.", fontsize=9)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{d['label']}_ridge_background.png"
    fig.savefig(path, bbox_inches="tight", metadata={"CreationDate": None})
    plt.close(fig)
    return path


def cmd_ridge_background(args) -> int:
    from concurrent.futures import ProcessPoolExecutor

    images = images_from(args)
    args.out.mkdir(parents=True, exist_ok=True)
    jobs = [(str(p), str(args.out)) for p in images]
    with ProcessPoolExecutor(max_workers=max(1, min(args.workers, len(jobs)))) as ex:
        out = list(ex.map(_ridge_one, jobs))

    rhos = [o["spearman_rho"] for o in out]
    median_rho = float(np.median(rhos))
    positive = sum(1 for v in rhos if v > 0)
    strong = median_rho >= RIDGE_GATE_MEDIAN_RHO and positive >= RIDGE_GATE_MIN_POSITIVE
    report = {
        "status": "measurement only: no parameter, threshold or rule was changed",
        "question": ("does the skeleton follow the LOCAL BACKGROUND of the ridge response, which "
                     "one global cut would make it do, rather than thread presence"),
        "decision_rule_fixed_before_running": {
            "proceed_if_median_spearman_rho_at_least": RIDGE_GATE_MEDIAN_RHO,
            "and_images_positive_at_least": RIDGE_GATE_MIN_POSITIVE,
            "of_images": len(out),
        },
        "background": {
            "percentile": RIDGE_BACKGROUND_PERCENTILE,
            "window_px": RIDGE_BACKGROUND_WINDOW_PX,
            "stride_px": RIDGE_BACKGROUND_STRIDE_PX,
            "smooth_cells": RIDGE_BACKGROUND_SMOOTH_CELLS,
            "excluded": "every lacuna body plus the mask buffer",
        },
        "tile_px": RIDGE_TILE_PX,
        "median_spearman_rho": round(median_rho, 4),
        "images_with_positive_rho": positive,
        "result": "STRONG" if strong else "WEAK",
        "per_image": [{k: v for k, v in o.items() if k != "rows"} for o in out],
    }
    with open(args.out / "ridge_background.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, indent=2, default=float)
    with open(args.out / "ridge_background_tiles.csv", "w", encoding="utf-8", newline="") as f:
        cols = ["image_label", "tile_xy", "quadrant", "area_px", "free_px", "skeleton_px",
                "owned_px", "owned_fraction", "skeleton_density_per_free_px",
                "owned_density_per_free_px", "skeleton_density_per_px", "background"]
        w = csv.writer(f)
        w.writerow(cols)
        for o in out:
            for r in o["rows"]:
                w.writerow([r[c] if c != "tile_xy" else f"{r[c][0]},{r[c][1]}" for c in cols])

    print_table(["image", "tiles", "Spearman rho", "p", "Pearson r", "background min",
                 "median", "max", "max/min", "density dim 1/4", "bright 1/4", "bright/dim"],
                [[o["image_label"], o["tiles"], f"{o['spearman_rho']:+.3f}", f"{o['spearman_p']:.1e}",
                  f"{o['pearson_r']:+.3f}", f"{o['background_min']:.6f}",
                  f"{o['background_median']:.6f}", f"{o['background_max']:.6f}",
                  o["background_ratio_max_over_min"], f"{o['density_dim_quarter']:.4f}",
                  f"{o['density_bright_quarter']:.4f}", o["density_bright_over_dim"]]
                 for o in out],
                title=f"Local background of the ridge response against skeleton density, "
                      f"{RIDGE_TILE_PX} px tiles")
    print_table(["image", "rho, skeleton density", "rho, owned density",
                 "rho, owned fraction", "owned fraction dim 1/4", "bright 1/4"],
                [[o["image_label"], f"{o['spearman_rho']:+.3f}",
                  f"{o['spearman_rho_owned_density']:+.3f}",
                  f"{o['spearman_rho_owned_fraction']:+.3f}",
                  f"{o['owned_fraction_dim_quarter']:.3f}",
                  f"{o['owned_fraction_bright_quarter']:.3f}"] for o in out],
                title="\nThe same tiles, asked about ownership")
    print(f"\nMedian Spearman rho {median_rho:+.3f} over {len(out)} images, "
          f"{positive} of {len(out)} positive.")
    owned_rhos = [o["spearman_rho_owned_fraction"] for o in out]
    print(f"Median Spearman rho for the OWNED FRACTION of the skeleton in a tile: "
          f"{float(np.median(owned_rhos)):+.3f}, "
          f"{sum(1 for v in owned_rhos if v > 0)} of {len(out)} positive.")
    print(f"Gate fixed before running: rho at least {RIDGE_GATE_MEDIAN_RHO:+.2f} and at least "
          f"{RIDGE_GATE_MIN_POSITIVE} of {len(out)} positive.")
    print(f"RESULT: {report['result']}" + (
        ": the skeleton follows local brightness, so normalizing the response by the local "
        "background is worth doing." if strong else
        ": the relation is not strong enough to blame the global cut. The work stops here."))
    print(f"\nreport -> {args.out / 'ridge_background.json'}")
    for o in out:
        print(f"picture -> {o['picture']}")
    return 0


# empty-zone ---------------------------------------------------------------------
# Why is there a hole in the skeleton around a lacuna?
#
# MEASUREMENT ONLY. Three questions, all answered on all 8 images.
#
#   1. How wide is the hole? The frame around each lacuna is cut into
#      EMPTY_SECTORS angular sectors, and a sector's empty width is the smallest
#      distance to the body over the SKELETON PIXELS that lie in it; the
#      lacuna's empty width is the median over the sectors that answered.
#      Measured on the skeleton's own pixels, because a ray marched outward runs
#      along the corridor between two threads and reports a hole where a thread
#      sits 3 px to the side.
#
#   2. Is there anything in the hole to recover? The zone is compared with the
#      EMPTY_REFERENCE_BAND_PX band immediately beyond it in the same sectors,
#      which is the same tissue, the same directions and the same depth of
#      field, differing only in being past the hole. Raw, flattened and ridge
#      response are compared at p50, p90, p99 and max. If the hole holds thread
#      contrast like the band beyond it, something downstream is losing it; if
#      it does not, no threshold can be blamed.
#
#   3. What removes what is there? Inside the zone, every pixel that is VISIBLE
#      in the sense the brief fixed, a ridge response of at least
#      EMPTY_VISIBLE_FRACTION of the low cut, is followed through the stages in
#      the order the pipeline applies them and attributed to the FIRST stage
#      that drops it:
#        below the low cut            the hysteresis threshold, which no
#                                     connectivity can rescue
#        hysteresis, not connected    between the cuts with no bright seed
#        vascular no-growth           inside a flagged structure and under the
#                                     high cut, where hysteresis may add nothing
#        lacuna body buffer           inside the body plus LACUNA_DILATION_PX
#        despeckled                   in the mask, under MIN_THREAD_OBJECT_PX2
#        kept in the mask             not lost at all
#      The dim pass is counted separately as a rescue, and the 50 um prune on
#      the skeleton, which is where it acts.
#
# Saturation is counted too, because a thread lying on a glow that is already at
# the sensor's ceiling has no contrast left to find and no stage can be blamed
# for it. Profiles are saved for the EMPTY_PROFILE_LACUNAE widest holes in the
# set, which is a rule and not a list of coordinates.

# Angular sectors the frame around a body is cut into, 2 degrees each.
EMPTY_SECTORS = 180
# How far out a sector looks for skeleton before it is censored.
EMPTY_MAX_SEARCH_PX = 150
# The threads that bound the hole carry their own mask inward from their centre
# lines, so a rim of mask lies inside the hole that belongs to them. The CORE of
# the hole is what is left after that rim is taken off: every pixel further than
# this from any skeleton pixel. One thread half width (p50 3.0 px) plus one, so
# the rim is removed and no more.
EMPTY_RIM_PX = 4
# The control band: this much of each ray immediately beyond the hole.
EMPTY_REFERENCE_BAND_PX = 40
# "Visible in the raw image", as the brief defines it: a ridge response of at
# least this fraction of the low cut. The same floor the dim pass uses.
EMPTY_VISIBLE_FRACTION = 0.5
# A raw pixel at or above this fraction of the channel's maximum is saturated.
EMPTY_SATURATION_FRACTION = 0.99
# How many lacunae get a saved profile: the widest holes in the whole set.
EMPTY_PROFILE_LACUNAE = 5


def _empty_window(body: np.ndarray, shape: tuple) -> tuple:
    """The bounding box of the body grown by EMPTY_MAX_SEARCH_PX."""
    rows, cols = np.nonzero(body)
    return (max(0, int(rows.min()) - EMPTY_MAX_SEARCH_PX),
            min(shape[0], int(rows.max()) + EMPTY_MAX_SEARCH_PX + 1),
            max(0, int(cols.min()) - EMPTY_MAX_SEARCH_PX),
            min(shape[1], int(cols.max()) + EMPTY_MAX_SEARCH_PX + 1))


def _empty_sector_widths(sector: np.ndarray, near: np.ndarray, sub_gap: np.ndarray,
                         sub_skel: np.ndarray, blocked: np.ndarray) -> np.ndarray:
    """The smallest distance to the body over the skeleton pixels of each
    sector, nan where the sector has none or is blocked by another body."""
    widths = np.full(EMPTY_SECTORS, np.inf)
    sel = near & sub_skel
    np.minimum.at(widths, sector[sel], sub_gap[sel])
    return np.where(np.isfinite(widths) & (blocked > widths), widths, np.nan)


def empty_zone_sectors(d: dict, lacuna_id: int) -> dict:
    """One lacuna: how far out the skeleton starts in each angular sector, the
    hole that follows, and the control band immediately beyond it.

    Measured on the skeleton's OWN pixels. The frame around the body is cut into
    EMPTY_SECTORS sectors, and a sector's empty width is the smallest distance
    to the body over the skeleton pixels that lie in it. A ray marched outward
    would instead run along the corridor between two threads and report a hole
    where a thread sits 3 px to the side; this cannot, because any skeleton
    pixel in the sector ends it. A sector with no skeleton within
    EMPTY_MAX_SEARCH_PX, or with another lacuna body nearer than its skeleton,
    is censored and left out."""
    body = d["lacuna_id_map"] == lacuna_id
    rows, cols = np.nonzero(body)
    r0, c0 = float(rows.mean()), float(cols.mean())
    gap = ndi.distance_transform_edt(~body)
    shape = body.shape
    r_lo, r_hi, c_lo, c_hi = _empty_window(body, shape)

    sub_gap = gap[r_lo:r_hi, c_lo:c_hi]
    sub_skel = d["skeleton"][r_lo:r_hi, c_lo:c_hi]
    sub_other = ((d["lacuna_id_map"] > 0) & ~body)[r_lo:r_hi, c_lo:c_hi]
    rr, cc = np.indices(sub_gap.shape)
    ang = np.arctan2(rr + r_lo - r0, cc + c_lo - c0) % (2.0 * np.pi)
    sector = (np.round(ang / (2.0 * np.pi) * EMPTY_SECTORS).astype(np.int64)) % EMPTY_SECTORS
    near = (sub_gap > 0) & (sub_gap <= EMPTY_MAX_SEARCH_PX)

    blocked = np.full(EMPTY_SECTORS, np.inf)
    sel = near & sub_other
    np.minimum.at(blocked, sector[sel], sub_gap[sel])
    widths = _empty_sector_widths(sector, near, sub_gap, sub_skel, blocked)
    # The same measurement against the skeleton as it was BEFORE the 50 um
    # prune, which is the one stage after skeletonization that can delete a
    # centre line. If the hole is much smaller here, the prune is what opened it.
    before = _empty_sector_widths(
        sector, near, sub_gap,
        d["skeleton_before_prune"][r_lo:r_hi, c_lo:c_hi], blocked)

    w = np.where(np.isfinite(widths), widths, -1.0)[sector]
    zone = np.zeros(shape, dtype=bool)
    zone[r_lo:r_hi, c_lo:c_hi] = (sub_gap > 0) & (sub_gap <= w)
    reference = np.zeros(shape, dtype=bool)
    reference[r_lo:r_hi, c_lo:c_hi] = (sub_gap > w) & (sub_gap <= w + EMPTY_REFERENCE_BAND_PX) \
        & (w >= 0)
    outside = d["lacuna_id_map"] > 0
    zone &= ~outside
    reference &= ~outside
    # The core: the hole minus the mask rim of the threads that bound it.
    core = zone & (d["skeleton_distance"] > EMPTY_RIM_PX)
    good = np.isfinite(widths)
    return {
        "lacuna_id": lacuna_id,
        "centroid_xy": [round(c0, 1), round(r0, 1)],
        "body_px": int(body.sum()),
        "empty_width_px": round(float(np.median(widths[good])), 3) if good.any() else None,
        "empty_width_um": (round(config.um(float(np.median(widths[good]))), 4)
                           if good.any() else None),
        "empty_width_p10_px": (round(float(np.percentile(widths[good], 10)), 3)
                               if good.any() else None),
        "empty_width_p90_px": (round(float(np.percentile(widths[good], 90)), 3)
                               if good.any() else None),
        "empty_width_max_px": round(float(widths[good].max()), 3) if good.any() else None,
        "empty_width_before_the_prune_px": (round(float(np.nanmedian(before)), 3)
                                            if np.isfinite(before).any() else None),
        "sectors_opened_by_the_prune": int(np.sum(
            np.isfinite(before) & np.isfinite(widths) & (widths > before + 1.0))),
        "sectors_answered": int(good.sum()),
        "sectors_total": int(EMPTY_SECTORS),
        "zone_px": int(zone.sum()),
        "core_px": int(core.sum()),
        "reference_px": int(reference.sum()),
        "zone": zone,
        "core": core,
        "reference": reference,
    }


def _empty_levels(values: np.ndarray) -> dict:
    if values.size == 0:
        return {"p50": None, "p90": None, "p99": None, "max": None}
    return {"p50": round(float(np.percentile(values, 50)), 8),
            "p90": round(float(np.percentile(values, 90)), 8),
            "p99": round(float(np.percentile(values, 99)), 8),
            "max": round(float(values.max()), 8)}


def _empty_region(d: dict, region: np.ndarray) -> dict:
    """What one region holds: the levels of each image, how much of it is mask
    and skeleton, and how WIDE that mask is. The width is the point: a broad
    blob of mask yields a single centre line however much mask it is, while the
    same area as separate threads yields one line each."""
    n = max(1, int(region.sum()))
    mask = region & d["candidate"]
    width = d["mask_width"][mask]
    return {
        "raw": _empty_levels(d["channel"][region]),
        "flattened": _empty_levels(d["flattened"][region]),
        "response": _empty_levels(d["response"][region]),
        "mask_px": int(mask.sum()),
        "mask_fraction": round(float(mask.sum()) / n, 4),
        "mask_width_px": round(float(width.mean()), 3) if width.size else None,
        "mask_width_p90_px": round(float(np.percentile(width, 90)), 3) if width.size else None,
        "skeleton_px": int((region & d["skeleton"]).sum()),
        "skeleton_fraction": round(float((region & d["skeleton"]).sum()) / n, 4),
        "skeleton_per_mask_px": (round(float((region & d["skeleton"]).sum()) / int(mask.sum()), 4)
                                 if mask.any() else None),
        "saturated_px": int((region & (d["channel"] >= EMPTY_SATURATION_FRACTION
                                       * float(d["channel"].max()))).sum()),
    }


def empty_zone_stages(d: dict, zone: np.ndarray, core: np.ndarray,
                      reference: np.ndarray) -> dict:
    """What the hole holds against what the band beyond it holds, and which
    stage drops each visible pixel in it. The accounting is done on the CORE,
    which is the hole without the mask rim of the threads that bound it, since
    that rim is theirs and is in the mask already."""
    response, low, high = d["response"], d["low_cut"], d["high_cut"]
    raw, flat = d["channel"], d["flattened"]
    visible_cut = EMPTY_VISIBLE_FRACTION * low

    core_before = zone & (d["skeleton_before_prune_distance"] > EMPTY_RIM_PX)
    visible = core & (response >= visible_cut)
    below_low = visible & (response < low)
    between = visible & (response >= low) & (response < high)
    not_connected = between & ~d["hysteresis_signal"]
    in_canal = not_connected & d["flagged"]
    kept_by_hysteresis = visible & d["hysteresis_signal"]
    in_buffer = kept_by_hysteresis & d["buffered_lacunae"]
    despeckled = kept_by_hysteresis & ~d["buffered_lacunae"] & ~d["candidate_first_pass"]
    in_mask = visible & d["candidate_first_pass"]
    rescued = core & (response < low) & d["candidate"] & ~d["candidate_first_pass"]

    out = {
        "zone_px": int(zone.sum()),
        "core_px": int(core.sum()),
        "reference_px": int(reference.sum()),
        "in_the_hole_with_its_rim": _empty_region(d, zone),
        "in_the_core": _empty_region(d, core),
        "in_the_band_beyond": _empty_region(d, reference),
        "cuts": {"low": round(low, 8), "high": round(high, 8),
                 "visible": round(visible_cut, 8),
                 "saturation_level": round(EMPTY_SATURATION_FRACTION * float(raw.max()), 6)},
        "visible_px": int(visible.sum()),
        "visible_fraction_of_core": round(float(visible.sum()) / max(1, int(core.sum())), 4),
        "lost_at": {
            "below_the_low_cut": int(below_low.sum()),
            "hysteresis_not_connected": int((not_connected & ~in_canal).sum()),
            "vascular_no_growth": int(in_canal.sum()),
            "lacuna_body_buffer": int(in_buffer.sum()),
            "despeckled": int(despeckled.sum()),
        },
        "kept_in_the_mask": int(in_mask.sum()),
        "rescued_by_the_dim_pass": int(rescued.sum()),
        "skeleton_px_cut_by_the_50um_prune": int(
            (zone & d["skeleton_before_prune"] & ~d["skeleton"]).sum()),
        "skeleton_px_in_the_hole": int((zone & d["skeleton"]).sum()),
        "skeleton_px_in_the_hole_before_the_prune": int(
            (zone & d["skeleton_before_prune"]).sum()),
        # The same core taken against the skeleton as it was BEFORE the 50 um
        # prune. Mask with no centre line within EMPTY_RIM_PX is either mask the
        # skeletonization never ran a line into, or mask whose line the prune
        # deleted; the difference between these two numbers is the prune's share.
        "mask_fraction_in_the_core": _empty_region(d, core)["mask_fraction"],
        "mask_fraction_in_the_core_before_the_prune": round(float(
            (core_before & d["candidate"]).sum()) / max(1, int(core_before.sum())), 4),
    }
    for key in ("mask_fraction", "skeleton_fraction"):
        a, b = out["in_the_core"][key], out["in_the_band_beyond"][key]
        out[f"{key}_core_over_band"] = round(a / b, 4) if b else None
    return out


def empty_zone_profile(d: dict, lacuna_id: int, max_px: float) -> dict:
    """The radial profile around one lacuna: every pixel in the frame around it
    binned by its distance to the body, 1 px per bin, so each bin is a complete
    annulus and the median over a bin is a median over angles with no sampling
    in between. Other lacuna bodies are left out."""
    body = d["lacuna_id_map"] == lacuna_id
    gap = ndi.distance_transform_edt(~body)
    r_lo, r_hi, c_lo, c_hi = _empty_window(body, body.shape)
    cut = lambda m: m[r_lo:r_hi, c_lo:c_hi]
    sub_gap = cut(gap)
    usable = (sub_gap > 0) & (sub_gap <= max_px) & ~cut((d["lacuna_id_map"] > 0) & ~body)
    series = {"raw": cut(d["channel"]), "flattened": cut(d["flattened"]),
              "response": cut(d["response"])}
    mask, skel = cut(d["candidate"]), cut(d["skeleton"])
    pruned = cut(d["skeleton_before_prune"]) & ~skel
    width = cut(d["mask_width"])
    out = {k: [] for k in ("distance_px", "raw", "flattened", "flattened_p99", "response",
                           "response_p99", "mask_fraction", "skeleton_fraction",
                           "pruned_fraction", "mask_width_px")}
    for lo in np.arange(0.0, max_px, 1.0):
        sel = usable & (sub_gap >= lo) & (sub_gap < lo + 1.0)
        if not sel.any():
            continue
        out["distance_px"].append(float(lo))
        for name, values in series.items():
            out[name].append(float(np.median(values[sel])))
        out["flattened_p99"].append(float(np.percentile(series["flattened"][sel], 99)))
        out["response_p99"].append(float(np.percentile(series["response"][sel], 99)))
        out["mask_fraction"].append(float(mask[sel].mean()))
        out["skeleton_fraction"].append(float(skel[sel].mean()))
        out["pruned_fraction"].append(float(pruned[sel].mean()))
        on_mask = sel & mask
        out["mask_width_px"].append(float(width[on_mask].mean()) if on_mask.any() else 0.0)
    return out


def empty_zone_picture(d: dict, record: dict, profile: dict, out_dir: Path) -> Path:
    """The profiles of one lacuna beside its own neighbourhood, with the hole
    and the control band drawn on it."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    lacuna_id = record["lacuna_id"]
    body = d["lacuna_id_map"] == lacuna_id
    gap = ndi.distance_transform_edt(~body)
    near = gap <= (record["empty_width_px"] or 20.0) + EMPTY_REFERENCE_BAND_PX + 5
    rows, cols = np.nonzero(near)
    r0, r1 = int(rows.min()), int(rows.max()) + 1
    c0, c1 = int(cols.min()), int(cols.max()) + 1
    canvas = d["display"][r0:r1, c0:c1].copy().astype(np.uint8)
    sub = lambda m: m[r0:r1, c0:c1]
    canvas[sub(d["candidate"] & ~d["skeleton"])] = (110, 0, 110)
    canvas[sub(d["skeleton_before_prune"] & ~d["skeleton"])] = PRUNED_COLOUR
    canvas[sub(d["skeleton"])] = UNOWNED_COLOUR
    canvas[sub(d["skeleton"] & (d["owner_map"] > 0))] = OWNED_COLOUR
    # The hole and the control band as outlines, so nothing underneath is hidden.
    canvas[sub(segmentation.find_boundaries(record["zone"], mode="outer"))] = (255, 255, 255)
    canvas[sub(segmentation.find_boundaries(record["core"], mode="outer"))] = (0, 180, 255)
    canvas[sub(segmentation.find_boundaries(record["reference"], mode="outer"))] = (0, 200, 0)
    canvas[sub(segmentation.find_boundaries(body, mode="outer"))] = (0, 255, 255)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5), dpi=130)
    ax1.imshow(canvas)
    ax1.set_title(f"{d['label']} lacuna {lacuna_id} at {record['centroid_xy']}: "
                  f"empty width {record['empty_width_px']} px = {record['empty_width_um']} um\n"
                  f"white: the hole, blue: its core, green: the control band, magenta: mask, "
                  f"gold: cut by the 50 um prune, pink or green: skeleton", fontsize=8)
    ax1.set_axis_off()

    x = profile["distance_px"]
    ax2.plot(x, profile["raw"], color="#d62728", label="raw, median over rays")
    ax2.plot(x, profile["flattened"], color="#2ca02c", label="flattened, median")
    ax2.plot(x, profile["flattened_p99"], color="#2ca02c", ls="--", lw=1,
             label="flattened, p99 (a thread would be here)")
    ax2.set_xlabel("distance from the body edge (px)", fontsize=8)
    ax2.set_ylabel("intensity", fontsize=8)
    ax2.axvline(record["empty_width_px"] or 0, color="#555555", ls="--", lw=1,
                label="empty width")
    ax3 = ax2.twinx()
    ax3.plot(x, profile["response_p99"], color="#1f77b4", ls="--", lw=1,
             label="response, p99")
    ax3.plot(x, profile["response"], color="#1f77b4", label="response, median")
    ax3.axhline(d["high_cut"], color="#1f77b4", ls=":", lw=1, label="high cut")
    ax3.axhline(d["low_cut"], color="#17becf", ls="-.", lw=1, label="low cut")
    ax3.axhline(EMPTY_VISIBLE_FRACTION * d["low_cut"], color="#9467bd", ls=":", lw=1,
                label="half the low cut")
    ax3.set_ylabel("ridge response", fontsize=8)
    lines = ax2.get_lines() + ax3.get_lines()
    ax2.legend(lines, [l.get_label() for l in lines], fontsize=6, loc="upper right")
    ax2.tick_params(labelsize=7)
    ax3.tick_params(labelsize=7)
    ax2.set_title("radial profiles, over 180 rays", fontsize=8)
    ax4 = ax2.inset_axes([0.08, 0.58, 0.40, 0.38])
    ax4.plot(x, profile["mask_fraction"], color="#9467bd", lw=1, label="mask")
    ax4.plot(x, profile["skeleton_fraction"], color="#e377c2", lw=1, label="skeleton")
    ax4.plot(x, np.array(profile["mask_width_px"]) / 100.0, color="#8c564b", lw=1,
             label="mask width / 100 px")
    ax4.set_title("coverage and mask width", fontsize=6)
    ax4.tick_params(labelsize=5)
    ax4.legend(fontsize=5)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{d['label']}_lacuna{lacuna_id}_empty_zone.png"
    fig.savefig(path, bbox_inches="tight", metadata={"CreationDate": None})
    plt.close(fig)
    return path


def _empty_one(job: tuple) -> dict:
    path_str, out_dir, profile_ids = job
    d = contact_detection(Path(path_str))
    d["channel"] = lacunae.load_channel(Path(path_str))[1]
    d["flattened"] = canaliculi.preprocess_channel(d["channel"])
    # Twice the distance transform inside the mask: the local width of the mask
    # at every mask pixel.
    d["mask_width"] = 2.0 * ndi.distance_transform_edt(d["candidate"])
    d["skeleton_distance"] = ndi.distance_transform_edt(~d["skeleton"])
    d["skeleton_before_prune_distance"] = ndi.distance_transform_edt(~d["skeleton_before_prune"])
    rows, pictures = [], []
    zone_all = np.zeros(d["skeleton"].shape, dtype=bool)
    core_all = np.zeros(d["skeleton"].shape, dtype=bool)
    ref_all = np.zeros(d["skeleton"].shape, dtype=bool)
    for lacuna_id in range(1, d["n_lacunae"] + 1):
        record = empty_zone_sectors(d, lacuna_id)
        zone_all |= record["zone"]
        core_all |= record["core"]
        ref_all |= record["reference"]
        stages = empty_zone_stages(d, record["zone"], record["core"], record["reference"])
        if lacuna_id in profile_ids:
            profile = empty_zone_profile(
                d, lacuna_id, (record["empty_width_px"] or 20.0) + EMPTY_REFERENCE_BAND_PX)
            pictures.append(empty_zone_picture(d, record, profile, Path(out_dir)).as_posix())
        row = {k: v for k, v in record.items() if k not in ("zone", "core", "reference")}
        row["image_label"] = d["label"]
        row["stages"] = stages
        rows.append(row)
    ref_all &= ~zone_all
    return {
        "image_label": d["label"],
        "lacunae": d["n_lacunae"],
        "cuts": {"high": round(d["high_cut"], 8), "low": round(d["low_cut"], 8)},
        "zone_total_px": int(zone_all.sum()),
        "core_total_px": int(core_all.sum()),
        "image_stages": empty_zone_stages(d, zone_all, core_all, ref_all),
        "rows": rows,
        "pictures": pictures,
    }


def cmd_empty_zone(args) -> int:
    from concurrent.futures import ProcessPoolExecutor

    images = images_from(args)
    args.out.mkdir(parents=True, exist_ok=True)
    # Pass 1 measures; the widest holes in the whole set then get a profile, so
    # which lacunae are drawn is a rule and not a list of coordinates.
    jobs = [(str(p), str(args.out), ()) for p in images]
    workers = max(1, min(args.workers, len(jobs)))
    with ProcessPoolExecutor(max_workers=workers) as ex:
        out = list(ex.map(_empty_one, jobs))
    widest = sorted(((r["empty_width_px"] or 0.0, o["image_label"], r["lacuna_id"])
                     for o in out for r in o["rows"]), reverse=True)[:EMPTY_PROFILE_LACUNAE]
    wanted: dict = {}
    for _w, label, lacuna_id in widest:
        wanted.setdefault(label, []).append(lacuna_id)
    jobs = [(str(p), str(args.out), tuple(wanted.get(lacunae.image_label(p), ())))
            for p in images if lacunae.image_label(p) in wanted]
    with ProcessPoolExecutor(max_workers=max(1, min(workers, len(jobs)))) as ex:
        drawn = list(ex.map(_empty_one, jobs))
    pictures = [p for o in drawn for p in o["pictures"]]

    all_rows = [r for o in out for r in o["rows"]]
    widths = np.array([r["empty_width_px"] for r in all_rows
                       if r["empty_width_px"] is not None], dtype=float)
    stage_names = ["below_the_low_cut", "hysteresis_not_connected", "vascular_no_growth",
                   "lacuna_body_buffer", "despeckled"]
    totals = {k: sum(o["image_stages"]["lost_at"][k] for o in out) for k in stage_names}
    totals_visible = sum(o["image_stages"]["visible_px"] for o in out)
    totals_kept = sum(o["image_stages"]["kept_in_the_mask"] for o in out)
    report = {
        "status": "measurement only: no parameter, threshold or rule was changed",
        "question": "what makes the hole in the skeleton around a lacuna",
        "definitions": {
            "empty_width": ("the smallest distance from the body edge to a skeleton pixel in "
                            f"an angular sector, median over the {EMPTY_SECTORS} sectors that "
                            "answered"),
            "zone": "the filled star between each body and its own sector widths",
            "reference": (f"the {EMPTY_REFERENCE_BAND_PX} px of each sector immediately beyond "
                          "the hole"),
            "visible": f"ridge response of at least {EMPTY_VISIBLE_FRACTION} of the low cut",
            "stage_order": stage_names,
        },
        "empty_width_px": {
            "lacunae": int(widths.size),
            "min": round(float(widths.min()), 2), "median": round(float(np.median(widths)), 2),
            "p90": round(float(np.percentile(widths, 90)), 2),
            "max": round(float(widths.max()), 2),
        },
        "empty_width_um": {
            "min": round(config.um(float(widths.min())), 3),
            "median": round(config.um(float(np.median(widths))), 3),
            "p90": round(config.um(float(np.percentile(widths, 90))), 3),
            "max": round(config.um(float(widths.max())), 3),
        },
        "all_images": {
            "zone_px": sum(o["zone_total_px"] for o in out),
            "visible_px": totals_visible,
            "kept_in_the_mask": totals_kept,
            "lost_at": totals,
            "rescued_by_the_dim_pass": sum(o["image_stages"]["rescued_by_the_dim_pass"]
                                           for o in out),
            "skeleton_px_cut_by_the_50um_prune": sum(
                o["image_stages"]["skeleton_px_cut_by_the_50um_prune"] for o in out),
        },
        "per_image": [{k: v for k, v in o.items() if k != "rows"} for o in out],
        "per_lacuna": all_rows,
        "profiles_drawn_for_the_widest": [f"{lab} lacuna {i} ({w:.1f} px)"
                                          for w, lab, i in widest],
        "pictures": pictures,
    }
    with open(args.out / "empty_zone.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, indent=2, default=float)
    with open(args.out / "empty_zone_per_lacuna.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["image_label", "lacuna_id", "centroid_x", "centroid_y", "body_px",
                    "empty_width_px", "empty_width_um", "zone_px", "visible_px",
                    "kept_in_the_mask"] + stage_names
                   + ["core_px", "core_flattened_p99", "band_flattened_p99",
                      "core_response_p99", "band_response_p99"])
        for r in all_rows:
            s = r["stages"]
            w.writerow([r["image_label"], r["lacuna_id"], r["centroid_xy"][0], r["centroid_xy"][1],
                        r["body_px"], r["empty_width_px"], r["empty_width_um"], r["zone_px"],
                        s["visible_px"], s["kept_in_the_mask"]]
                       + [s["lost_at"][k] for k in stage_names]
                       + [r["core_px"], s["in_the_core"]["flattened"]["p99"],
                          s["in_the_band_beyond"]["flattened"]["p99"],
                          s["in_the_core"]["response"]["p99"],
                          s["in_the_band_beyond"]["response"]["p99"]])

    print_table(["image", "lacunae", "width px min", "median", "p90", "max", "median um",
                 "width before the prune", "sectors the prune opened",
                 "hole px", "core px", "mask fraction core/band"],
                [[o["image_label"], o["lacunae"],
                  f"{min(r['empty_width_px'] for r in o['rows'] if r['empty_width_px']):.1f}",
                  f"{np.median([r['empty_width_px'] for r in o['rows'] if r['empty_width_px']]):.1f}",
                  f"{np.percentile([r['empty_width_px'] for r in o['rows'] if r['empty_width_px']], 90):.1f}",
                  f"{max(r['empty_width_px'] for r in o['rows'] if r['empty_width_px']):.1f}",
                  f"{config.um(float(np.median([r['empty_width_px'] for r in o['rows'] if r['empty_width_px']]))):.2f}",
                  f"{np.median([r['empty_width_before_the_prune_px'] for r in o['rows'] if r['empty_width_before_the_prune_px']]):.1f}",
                  sum(r["sectors_opened_by_the_prune"] for r in o["rows"]),
                  o["zone_total_px"], o["core_total_px"],
                  o["image_stages"]["mask_fraction_core_over_band"]] for o in out],
                title="The hole around each lacuna, per image")
    print_table(["image", "p99 response: core", "band", "p99 flattened: core", "band",
                 "mask fraction: core", "band", "raw p50: core", "band"],
                [[o["image_label"],
                  f"{o['image_stages']['in_the_core']['response']['p99']:.6f}",
                  f"{o['image_stages']['in_the_band_beyond']['response']['p99']:.6f}",
                  f"{o['image_stages']['in_the_core']['flattened']['p99']:.5f}",
                  f"{o['image_stages']['in_the_band_beyond']['flattened']['p99']:.5f}",
                  f"{o['image_stages']['in_the_core']['mask_fraction']:.3f}",
                  f"{o['image_stages']['in_the_band_beyond']['mask_fraction']:.3f}",
                  f"{o['image_stages']['in_the_core']['raw']['p50']:.4f}",
                  f"{o['image_stages']['in_the_band_beyond']['raw']['p50']:.4f}"]
                 for o in out],
                title="\nIs there thread contrast in the hole, and what shape is it? "
                      "The hole against the band beyond it")
    print_table(["image", "visible px"] + [n.replace("_", " ") for n in stage_names]
                + ["kept in the mask", "dim pass"],
                [[o["image_label"], o["image_stages"]["visible_px"]]
                 + [o["image_stages"]["lost_at"][k] for k in stage_names]
                 + [o["image_stages"]["kept_in_the_mask"],
                    o["image_stages"]["rescued_by_the_dim_pass"]] for o in out],
                title="\nWhere a visible pixel in the hole is lost, by the first stage that drops it")
    print_table(["image", "skeleton in the hole: before the prune", "after", "removed",
                 "mask with no centre line, core: before the prune", "after"],
                [[o["image_label"],
                  o["image_stages"]["skeleton_px_in_the_hole_before_the_prune"],
                  o["image_stages"]["skeleton_px_in_the_hole"],
                  o["image_stages"]["skeleton_px_cut_by_the_50um_prune"],
                  f"{o['image_stages']['mask_fraction_in_the_core_before_the_prune']:.4f}",
                  f"{o['image_stages']['mask_fraction_in_the_core']:.4f}"] for o in out],
                title="\nWhat the 50 um prune does inside the hole")
    w = report["empty_width_px"]
    print(f"\nEmpty width over {w['lacunae']} lacunae: min {w['min']} px, median {w['median']} px, "
          f"p90 {w['p90']} px, max {w['max']} px ({report['empty_width_um']['min']} to "
          f"{report['empty_width_um']['max']} um, median {report['empty_width_um']['median']} um).")
    total = sum(totals.values()) + totals_kept
    for k in stage_names:
        print(f"  {k.replace('_', ' '):28s} {totals[k]:8d} px  "
              f"{100.0 * totals[k] / max(1, total):5.1f}% of visible")
    print(f"  {'kept in the mask':28s} {totals_kept:8d} px  "
          f"{100.0 * totals_kept / max(1, total):5.1f}% of visible")
    print(f"\nreport -> {args.out / 'empty_zone.json'}")
    for p in pictures:
        print(f"picture -> {p}")
    return 0


# glow-check ---------------------------------------------------------------------
# The glow zone rule on against off, on every image.
#
# MEASUREMENT ONLY: each image is run twice in one process, once with
# canaliculi.GLOW_ZONE_MAX_PX = 0, which turns the rule off and is the pipeline
# as it was, and once as configured. The zone used to split "inside" from
# "outside" is the one the ON run computed, so both runs are measured against
# the same regions.
#
# The three checks the work has to pass:
#   the skeleton OUTSIDE the zones is unchanged
#   the empty width shrinks on every image
#   roots per lacuna do not fall on any image


def _glow_run(image_path: Path, glow_max_px: int | None) -> dict:
    """One run of the pipeline with the glow zone cap replaced, and everything
    the check reads from it."""
    saved = canaliculi.GLOW_ZONE_MAX_PX
    if glow_max_px is not None:
        canaliculi.GLOW_ZONE_MAX_PX = int(glow_max_px)
    try:
        d = contact_detection(image_path)
    finally:
        canaliculi.GLOW_ZONE_MAX_PX = saved
    return d


def _glow_widths(d: dict) -> list:
    """The empty width of every lacuna of one run."""
    d["skeleton_distance"] = ndi.distance_transform_edt(~d["skeleton"])
    out = []
    for lacuna_id in range(1, d["n_lacunae"] + 1):
        r = empty_zone_sectors(d, lacuna_id)
        out.append(r["empty_width_px"])
    return out


def _glow_one(job: tuple) -> dict:
    path_str, out_dir, pictures_for = job
    image_path = Path(path_str)
    after = _glow_run(image_path, None)
    before = _glow_run(image_path, 0)
    zone = after["net"]["glow_zone"]
    extents = after["net"]["glow_extents_px"][1:]

    rows = []
    wa, wb = _glow_widths(after), _glow_widths(before)
    for i in range(after["n_lacunae"]):
        rows.append({
            "image_label": after["label"],
            "lacuna_id": i + 1,
            "glow_extent_px": round(float(extents[i]), 2),
            "glow_extent_um": round(config.um(float(extents[i])), 3),
            "empty_width_before_px": wb[i],
            "empty_width_after_px": wa[i],
            "roots_before": quantification.cell_root_count(before["graph"], i + 1),
            "roots_after": quantification.cell_root_count(after["graph"], i + 1),
            "owned_px_before": int((before["owner_map"] == i + 1).sum()),
            "owned_px_after": int((after["owner_map"] == i + 1).sum()),
        })

    def side(d, mask):
        skel = d["skeleton"]
        return {"skeleton_px": int((skel & mask).sum()),
                "mask_px": int((d["candidate_first_pass"] & mask).sum()),
                "first_pass_skeleton_px": int((d["skeleton_first_pass"] & mask).sum()),
                "owned_px": int((skel & mask & (d["owner_map"] > 0)).sum()),
                "unowned_px": int((skel & mask & (d["owner_map"] == 0)).sum())}

    widths_b = [w for w in wb if w is not None]
    widths_a = [w for w in wa if w is not None]
    roots_b = [r["roots_before"] for r in rows]
    roots_a = [r["roots_after"] for r in rows]
    pictures = []
    if pictures_for:
        pictures = glow_before_after_pictures(before, after, Path(out_dir))
    return {
        "image_label": after["label"],
        "lacunae": after["n_lacunae"],
        "glow_extent_px": {
            "min": round(float(np.min(extents)), 2),
            "median": round(float(np.median(extents)), 2),
            "max": round(float(np.max(extents)), 2),
            "at_the_cap": int((extents >= canaliculi.GLOW_ZONE_MAX_PX - 1e-9).sum()),
        },
        "zone_px": int(zone.sum()),
        "mask_added_in_the_zone_px": int(after["net"]["glow_zone_added_px"]),
        "inside_the_zone": {"before": side(before, zone), "after": side(after, zone)},
        "outside_the_zone": {"before": side(before, ~zone), "after": side(after, ~zone)},
        "skeleton_px": {"before": int(before["skeleton"].sum()),
                        "after": int(after["skeleton"].sum())},
        "owned_px": {"before": int((before["skeleton"] & (before["owner_map"] > 0)).sum()),
                     "after": int((after["skeleton"] & (after["owner_map"] > 0)).sum())},
        "unowned_px": {"before": int((before["skeleton"] & (before["owner_map"] == 0)).sum()),
                       "after": int((after["skeleton"] & (after["owner_map"] == 0)).sum())},
        "empty_width_px": {"before": round(float(np.median(widths_b)), 2) if widths_b else None,
                           "after": round(float(np.median(widths_a)), 2) if widths_a else None},
        "roots_per_lacuna": {"before": round(float(np.mean(roots_b)), 3),
                             "after": round(float(np.mean(roots_a)), 3)},
        "lacunae_under_3_roots": {"before": sum(1 for v in roots_b if v < CONTACT_ROOTS_FLOOR),
                                  "after": sum(1 for v in roots_a if v < CONTACT_ROOTS_FLOOR)},
        "length_prune_px": {"before": int(before["length_prune"]["removed_px"]),
                            "after": int(after["length_prune"]["removed_px"])},
        "dim_pass_px": {"before": int(before["dim_pass_px"]), "after": int(after["dim_pass_px"])},
        "unattached_px": {"before": int(before["unattached"].sum()),
                          "after": int(after["unattached"].sum())},
        "pictures": pictures,
        "rows": rows,
    }


def glow_before_after_pictures(before: dict, after: dict, out_dir: Path) -> list:
    """The skeleton and the verification picture of one image, before and after,
    into results/before_after/ (or wherever the caller asks)."""
    from skimage.io import imsave

    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for tag, d in (("glow_before", before), ("glow_after", after)):
        path = out_dir / f"{d['label']}_{tag}_skeleton.png"
        imsave(path, (d["skeleton"] * 255).astype(np.uint8), check_contrast=False)
        written.append(path.as_posix())
        path = out_dir / f"{d['label']}_{tag}.png"
        canaliculi.save_verification(d["net"], path)
        written.append(path.as_posix())
    return written


def cmd_glow_check(args) -> int:
    from concurrent.futures import ProcessPoolExecutor

    images = images_from(args)
    wanted = {s.strip() for s in args.pictures.split(",") if s.strip()}
    jobs = [(str(p), str(args.before_after), lacunae.image_label(p) in wanted) for p in images]
    with ProcessPoolExecutor(max_workers=max(1, min(args.workers, len(jobs)))) as ex:
        out = list(ex.map(_glow_one, jobs))

    # The mask outside a zone cannot change: the growth is a propagation whose
    # mask is the old candidate plus pixels inside the zones, so every pixel it
    # adds is inside one. The SKELETON outside can still move, through the two
    # later stages that depend on what the mask holds: the 50 um prune keeps
    # thread it used to cut once the zone connects it to a body, and the dim
    # pass is seeded from owned skeleton. Both are reported beside the check.
    outside_held = all(o["outside_the_zone"]["before"]["mask_px"]
                       == o["outside_the_zone"]["after"]["mask_px"] for o in out)
    outside_skeleton_held = all(o["outside_the_zone"]["before"]["skeleton_px"]
                                == o["outside_the_zone"]["after"]["skeleton_px"] for o in out)
    shrank = all(o["empty_width_px"]["after"] <= o["empty_width_px"]["before"] for o in out)
    roots_held = all(o["roots_per_lacuna"]["after"] >= o["roots_per_lacuna"]["before"]
                     for o in out)
    rows = [r for o in out for r in o["rows"]]
    report = {
        "status": "measurement only: each image run twice, nothing in the pipeline was changed",
        "glow_profile_fraction": config.GLOW_PROFILE_FRACTION,
        "glow_zone_cut_fraction": config.GLOW_ZONE_CUT_FRACTION,
        "glow_zone_max_px": canaliculi.GLOW_ZONE_MAX_PX,
        "checks": {
            "mask_outside_the_zones_unchanged": outside_held,
            "skeleton_outside_the_zones_unchanged": outside_skeleton_held,
            "empty_width_shrinks_on_every_image": shrank,
            "roots_per_lacuna_do_not_fall": roots_held,
        },
        "per_image": [{k: v for k, v in o.items() if k != "rows"} for o in out],
        "per_lacuna": rows,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    with open(args.out / "glow_check.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, indent=2, default=float)
    with open(args.out / "glow_check_per_lacuna.csv", "w", encoding="utf-8", newline="") as f:
        cols = list(rows[0].keys())
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    pct = lambda b, a: f"{100.0 * (a - b) / b:+.2f}%" if b else "n/a"
    print_table(["image", "glow extent px: min, median, max", "at the cap", "zone px",
                 "mask added"],
                [[o["image_label"],
                  f"{o['glow_extent_px']['min']}, {o['glow_extent_px']['median']}, "
                  f"{o['glow_extent_px']['max']}",
                  o["glow_extent_px"]["at_the_cap"], o["zone_px"],
                  o["mask_added_in_the_zone_px"]] for o in out],
                title="The glow zone of each image")
    print_table(["image", "mask outside the zones", "skeleton outside the zones",
                 "of which the 50 um prune kept", "dim pass px"],
                [[o["image_label"],
                  f"{o['outside_the_zone']['before']['mask_px']} -> "
                  f"{o['outside_the_zone']['after']['mask_px']}",
                  f"{o['outside_the_zone']['before']['skeleton_px']} -> "
                  f"{o['outside_the_zone']['after']['skeleton_px']} "
                  f"({o['outside_the_zone']['after']['skeleton_px'] - o['outside_the_zone']['before']['skeleton_px']:+d})",
                  f"{o['length_prune_px']['before'] - o['length_prune_px']['after']:+d}",
                  f"{o['dim_pass_px']['before']} -> {o['dim_pass_px']['after']}"] for o in out],
                title="\nWhat moves outside the zones, and why")
    print_table(["image", "skeleton inside the zones", "outside the zones",
                 "empty width px", "roots per lacuna", "under 3 roots", "owned px", "unowned px"],
                [[o["image_label"],
                  f"{o['inside_the_zone']['before']['skeleton_px']} -> "
                  f"{o['inside_the_zone']['after']['skeleton_px']} "
                  f"({pct(o['inside_the_zone']['before']['skeleton_px'], o['inside_the_zone']['after']['skeleton_px'])})",
                  f"{o['outside_the_zone']['before']['skeleton_px']} -> "
                  f"{o['outside_the_zone']['after']['skeleton_px']}",
                  f"{o['empty_width_px']['before']} -> {o['empty_width_px']['after']}",
                  f"{o['roots_per_lacuna']['before']} -> {o['roots_per_lacuna']['after']}",
                  f"{o['lacunae_under_3_roots']['before']} -> {o['lacunae_under_3_roots']['after']}",
                  f"{o['owned_px']['before']} -> {o['owned_px']['after']}",
                  f"{o['unowned_px']['before']} -> {o['unowned_px']['after']}"] for o in out],
                title="\nBefore and after, per image")
    print(f"\nMASK outside the zones unchanged:     {outside_held}")
    print(f"skeleton outside the zones unchanged: {outside_skeleton_held} "
          f"(it moves with the 50 um prune and the dim pass, both reported above)")
    print(f"empty width shrinks on every image:   {shrank}")
    print(f"roots per lacuna do not fall:         {roots_held}")
    fell = [f"{r['image_label']} lacuna {r['lacuna_id']} "
            f"({r['roots_before']} -> {r['roots_after']})"
            for r in rows if r["roots_after"] < r["roots_before"]]
    print(f"lacunae whose roots fell: {fell or 'none'}")
    grew = [f"{r['image_label']} lacuna {r['lacuna_id']} "
            f"({r['empty_width_before_px']} -> {r['empty_width_after_px']})"
            for r in rows if (r["empty_width_after_px"] or 0) > (r["empty_width_before_px"] or 0)]
    print(f"lacunae whose hole grew: {grew or 'none'}")
    print(f"\nreport -> {args.out / 'glow_check.json'}")
    for o in out:
        for p in o["pictures"]:
            print(f"picture -> {p}")
    return 0



# hole-check ---------------------------------------------------------------------
# The zone from the hole (METHODS section 19) against the glow zone version of
# section 18, on every image, with the acceptance tests of the brief.
#
# Each image is run TWICE in one process: before with
# config.HOLE_ZONE_RULE = False and config.CONTACT_EVERY_TOUCHING_BODY = False,
# which is the glow zone version exactly, and after as configured.
#
# The empty width is read against its own FLOOR, which this check measures: the
# same sector rule applied to HOLE_NULL_DISCS synthetic bodies of the image's
# own median body size, dropped in tissue at least HOLE_NULL_CLEAR_PX from every
# real lacuna, where there is no body and so no hole at all. A sector near a
# body is a thin wedge (at 10 px from a 25 px body it is 0.35 px wide), so the
# measure cannot read 0 however complete the tracing is, and the floor is what
# says how much of the number left is a hole and how much is the measure.

HOLE_NULL_DISCS = 40
HOLE_NULL_CLEAR_PX = 120
# Test C reads the skeleton this close to a body.
HOLE_BAND_PX = 8
# A hole this wide is marked in the pictures.
HOLE_MARK_PX = 20


def _hole_run(image_path: Path, new_rule: bool) -> dict:
    """One run of the pipeline, with the new rule on or off, and everything the
    check reads from it."""
    saved = (config.HOLE_ZONE_RULE, config.CONTACT_EVERY_TOUCHING_BODY)
    config.HOLE_ZONE_RULE = bool(new_rule)
    config.CONTACT_EVERY_TOUCHING_BODY = bool(new_rule)
    try:
        d = contact_detection(image_path)
    finally:
        config.HOLE_ZONE_RULE, config.CONTACT_EVERY_TOUCHING_BODY = saved
    d["widths"] = canaliculi.empty_width_px(d["lacuna_id_map"], d["skeleton"], d["n_lacunae"])
    return d


def hole_null_floor(d: dict, discs: int = HOLE_NULL_DISCS) -> dict:
    """What the empty width reads around a body that has no hole: the same
    sector rule applied to synthetic discs of this image's own median body size,
    dropped in tissue at least HOLE_NULL_CLEAR_PX from every real lacuna.

    This is the floor of the measure, not of the method. A sector is a wedge
    whose width grows with the radius, so near a body it holds very few pixels
    and the first skeleton pixel in it sits further out than the nearest
    skeleton pixel in any direction. Without this number there is no way to say
    whether an empty width of 20 px is a hole or the measure."""
    lacuna_id_map, skeleton = d["lacuna_id_map"], d["skeleton"]
    areas = [int((lacuna_id_map == i).sum()) for i in range(1, d["n_lacunae"] + 1)]
    if not areas:
        return {"discs": 0}
    radius = float(np.median([np.sqrt(a / np.pi) for a in areas]))
    far = ndi.distance_transform_edt(lacuna_id_map == 0) > HOLE_NULL_CLEAR_PX
    rows, cols = np.nonzero(far)
    edge = int(np.ceil(radius)) + canaliculi.HOLE_MAX_SEARCH_PX // 2
    keep = ((rows > edge) & (rows < lacuna_id_map.shape[0] - edge)
            & (cols > edge) & (cols < lacuna_id_map.shape[1] - edge))
    rows, cols = rows[keep], cols[keep]
    if rows.size == 0:
        return {"discs": 0}
    rng = np.random.default_rng(config.RANDOM_SEED)
    pick = rng.choice(rows.size, size=int(min(discs, rows.size)), replace=False)
    rr, cc = np.indices(lacuna_id_map.shape)
    widths = []
    for k in pick:
        disc = ((rr - rows[k]) ** 2 + (cc - cols[k]) ** 2) <= radius ** 2
        w = canaliculi.empty_width_px(disc.astype(np.int32), skeleton & ~disc, 1)
        if np.isfinite(w[1]):
            widths.append(float(w[1]))
    if not widths:
        return {"discs": 0}
    widths = np.array(widths)
    return {
        "discs": int(widths.size),
        "disc_radius_px": round(radius, 2),
        "min": round(float(widths.min()), 2),
        "p10": round(float(np.percentile(widths, 10)), 2),
        "median": round(float(np.median(widths)), 2),
        "p90": round(float(np.percentile(widths, 90)), 2),
        "max": round(float(widths.max()), 2),
    }


def hole_band_split(d: dict, near_px: int = HOLE_BAND_PX) -> dict:
    """The skeleton within `near_px` of a body, as its own, nobody's, or another
    lacuna's, summed over the lacunae of one image. Test C reads this."""
    skel, owner_map = d["skeleton"], d["owner_map"]
    mine = unowned = other = 0
    for lacuna_id in range(1, d["n_lacunae"] + 1):
        body = d["lacuna_id_map"] == lacuna_id
        if not body.any():
            continue
        r_lo, r_hi, c_lo, c_hi = canaliculi._body_window(body, skel.shape, near_px)
        gap = ndi.distance_transform_edt(~body[r_lo:r_hi, c_lo:c_hi])
        near = (gap <= near_px) & skel[r_lo:r_hi, c_lo:c_hi]
        own_here = owner_map[r_lo:r_hi, c_lo:c_hi]
        mine += int((near & (own_here == lacuna_id)).sum())
        unowned += int((near & (own_here == 0)).sum())
        other += int((near & (own_here > 0) & (own_here != lacuna_id)).sum())
    return {"own_px": mine, "unowned_px": unowned, "another_lacunas_px": other,
            "wrong_px": unowned + other, "total_px": mine + unowned + other,
            "wrong_share": round((unowned + other) / max(1, mine + unowned + other), 4)}


def hole_loops(d: dict) -> dict:
    """Loops, report only and never deleted: how many independent cycles the
    network holds and what share of its edges lie on one.

    The cycle count is the cyclomatic number of the real subgraph, edges minus
    nodes plus components, which is the number of independent loops in it. An
    edge lies on a loop when it is not a bridge: removing a bridge disconnects
    the graph, removing any other edge does not."""
    graph = canaliculi.real_subgraph(d["graph"])
    edges = graph.number_of_edges()
    nodes = graph.number_of_nodes()
    parts = nx.number_connected_components(graph) if nodes else 0
    bridges = len(list(nx.bridges(graph))) if edges else 0
    per_cell = {}
    for lacuna_id in range(1, d["n_lacunae"] + 1):
        owned = [tuple(e) for e, owner in d["net"]["edge_owner"].items() if owner == lacuna_id]
        sub = graph.edge_subgraph([e for e in owned if graph.has_edge(*e)]).copy()
        sub_edges = sub.number_of_edges()
        if not sub_edges:
            per_cell[lacuna_id] = {"loop_count": 0, "loop_edge_share": 0.0}
            continue
        sub_bridges = len(list(nx.bridges(sub)))
        per_cell[lacuna_id] = {
            "loop_count": int(sub_edges - sub.number_of_nodes()
                              + nx.number_connected_components(sub)),
            "loop_edge_share": round((sub_edges - sub_bridges) / sub_edges, 4),
        }
    return {
        "loop_count": int(edges - nodes + parts),
        "edges": int(edges),
        "loop_edge_share": round((edges - bridges) / edges, 4) if edges else 0.0,
        "per_cell": per_cell,
    }


def hole_pictures(before: dict, after: dict, out_dir: Path, mark_px: int = HOLE_MARK_PX) -> list:
    """Before and after, skeleton and verification, for one image, with every
    lacuna whose hole is still wider than `mark_px` ringed in the after
    verification picture."""
    from skimage.io import imsave

    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for tag, d in (("hole_before", before), ("hole_after", after)):
        path = out_dir / f"{d['label']}_{tag}_skeleton.png"
        imsave(path, (d["skeleton"] * 255).astype(np.uint8), check_contrast=False)
        written.append(path.as_posix())
        path = out_dir / f"{d['label']}_{tag}.png"
        canaliculi.save_verification(d["net"], path)
        written.append(path.as_posix())
    # The marked picture: the after verification with a ring at each hole that
    # is still wider than mark_px, so what is left is visible and counted.
    marked = out_dir / f"{after['label']}_hole_after_marked.png"
    from skimage.io import imread

    vis = imread(out_dir / f"{after['label']}_hole_after.png")
    vis = np.array(vis[..., :3], dtype=np.uint8, copy=True)
    rr, cc = np.indices(vis.shape[:2])
    still = []
    for lacuna_id in range(1, after["n_lacunae"] + 1):
        width = after["widths"][lacuna_id]
        if not np.isfinite(width) or width <= mark_px:
            continue
        body = after["lacuna_id_map"] == lacuna_id
        rows, cols = np.nonzero(body)
        r0, c0 = float(rows.mean()), float(cols.mean())
        radius = float(np.hypot(rows - r0, cols - c0).max()) + float(width)
        ring = np.abs(np.hypot(rr - r0, cc - c0) - radius) <= 1.0
        vis[ring] = (255, 255, 255)
        still.append({"lacuna_id": lacuna_id, "centroid_xy": [round(c0, 1), round(r0, 1)],
                      "empty_width_px": round(float(width), 2)})
    imsave(marked, vis, check_contrast=False)
    written.append(marked.as_posix())
    return written, still


def _hole_one(job: tuple) -> dict:
    path_str, out_dir, want_pictures = job
    image_path = Path(path_str)
    after = _hole_run(image_path, True)
    before = _hole_run(image_path, False)
    zone = after["net"]["glow_zone"]
    zones_either = zone | before["net"]["glow_zone"]
    n = after["n_lacunae"]
    extents = after["net"]["zone_extents_px"]
    glow = after["net"]["glow_extents_px"]

    rows = []
    for i in range(1, n + 1):
        wb, wa = before["widths"][i], after["widths"][i]
        loops_b = hole_loops_cached(before)["per_cell"].get(i, {})
        loops_a = hole_loops_cached(after)["per_cell"].get(i, {})
        rows.append({
            "image_label": after["label"],
            "lacuna_id": i,
            "centroid_xy": contact_centroid(after["lacuna_id_map"] == i),
            "glow_extent_px": round(float(glow[i]), 2),
            "zone_extent_px": round(float(extents[i]), 2),
            "hole_width_measured_px": (round(float(after["net"]["hole_width_px"][i]), 2)
                                       if np.isfinite(after["net"]["hole_width_px"][i]) else None),
            "empty_width_before_px": None if not np.isfinite(wb) else round(float(wb), 2),
            "empty_width_after_px": None if not np.isfinite(wa) else round(float(wa), 2),
            "within_glow_extent_plus_10": (bool(np.isfinite(wa) and wa <= float(glow[i]) + 10.0)),
            "roots_before": quantification.cell_root_count(before["graph"], i),
            "roots_after": quantification.cell_root_count(after["graph"], i),
            "owned_px_before": int((before["owner_map"] == i).sum()),
            "owned_px_after": int((after["owner_map"] == i).sum()),
            "loop_count_after": loops_a.get("loop_count", 0),
            "loop_edge_share_after": loops_a.get("loop_edge_share", 0.0),
            "loop_count_before": loops_b.get("loop_count", 0),
        })

    def side(d, mask):
        skel = d["skeleton"]
        return {"skeleton_px": int((skel & mask).sum()),
                "mask_px": int((d["candidate"] & mask).sum()),
                "first_pass_mask_px": int((d["candidate_first_pass"] & mask).sum()),
                "owned_px": int((skel & mask & (d["owner_map"] > 0)).sum()),
                "unowned_px": int((skel & mask & (d["owner_map"] == 0)).sum())}

    owned_after = [int((after["owner_map"] == i).sum()) for i in range(1, n + 1)]
    owned_before = [int((before["owner_map"] == i).sum()) for i in range(1, n + 1)]
    skel_after = max(1, int(after["skeleton"].sum()))
    skel_before = max(1, int(before["skeleton"].sum()))
    pictures, still = [], []
    if want_pictures:
        pictures, still = hole_pictures(before, after, Path(out_dir))
    return {
        "image_label": after["label"],
        "lacunae": n,
        "zone_px": int(zone.sum()),
        "zone_extent_px": {"min": round(float(extents[1:].min()), 2),
                           "median": round(float(np.median(extents[1:])), 2),
                           "max": round(float(extents[1:].max()), 2),
                           "at_the_cap": int((extents[1:] >= canaliculi.GLOW_ZONE_MAX_PX
                                              - 1e-9).sum())},
        "gains": after["net"]["hole_zone"]["gains"] if after["net"]["hole_zone"] else None,
        "guard": after["net"]["hole_zone"]["guard"] if after["net"]["hole_zone"] else None,
        "mask_added_in_the_zone_px": (after["net"]["hole_zone"]["added_px"]
                                      if after["net"]["hole_zone"] else 0),
        # Test A. Outside the zones of BOTH versions: the before run grew mask
        # inside its own glow zone, which is not always inside the new one, so
        # the only region where neither rule was allowed to write is the
        # complement of the union. The stricter figure, against the new zone
        # alone, is reported beside it.
        "first_pass_mask_outside_the_zones_identical": bool(
            ((before["candidate_first_pass"] & ~zones_either)
             == (after["candidate_first_pass"] & ~zones_either)).all()),
        "first_pass_mask_differs_outside_the_new_zone_px": int(
            ((before["candidate_first_pass"] & ~zone)
             != (after["candidate_first_pass"] & ~zone)).sum()),
        "glow_zone_px_outside_the_new_zone": int((before["net"]["glow_zone"] & ~zone).sum()),
        "changed_px_against_the_glow_zone_version": int(
            (before["skeleton"] != after["skeleton"]).sum()),
        "inside_the_zone": {"before": side(before, zone), "after": side(after, zone)},
        "outside_the_zone": {"before": side(before, ~zone), "after": side(after, ~zone)},
        "skeleton_px": {"before": skel_before, "after": skel_after},
        "owned_px": {"before": int((before["owner_map"] > 0).sum()),
                     "after": int((after["owner_map"] > 0).sum())},
        "length_prune_px": {"before": before["length_prune"]["removed_px"],
                            "after": after["length_prune"]["removed_px"]},
        "unattached_px": {"before": int(before["unattached"].sum()),
                          "after": int(after["unattached"].sum())},
        "empty_width_px": {
            "before": round(float(np.nanmedian(before["widths"][1:])), 2),
            "after": round(float(np.nanmedian(after["widths"][1:])), 2),
            "null_floor": hole_null_floor(after),
            "shrank": int(np.sum(np.nan_to_num(after["widths"][1:], nan=np.inf)
                                 < np.nan_to_num(before["widths"][1:], nan=np.inf))),
        },
        "roots_per_lacuna": {
            "before": round(float(np.mean([r["roots_before"] for r in rows])), 2),
            "after": round(float(np.mean([r["roots_after"] for r in rows])), 2),
            "under_3_before": int(sum(1 for r in rows if r["roots_before"] < 3)),
            "under_3_after": int(sum(1 for r in rows if r["roots_after"] < 3)),
        },
        "band_8px": {"before": hole_band_split(before), "after": hole_band_split(after)},
        "biggest_owner_share": {
            "before": round(max(owned_before) / skel_before, 4) if owned_before else 0.0,
            "after": round(max(owned_after) / skel_after, 4) if owned_after else 0.0,
        },
        "loops": {"before": {k: v for k, v in hole_loops_cached(before).items()
                             if k != "per_cell"},
                  "after": {k: v for k, v in hole_loops_cached(after).items()
                            if k != "per_cell"}},
        "rows": rows,
        "pictures": pictures,
        "holes_still_wider_than_the_mark": still,
    }


_HOLE_LOOPS_CACHE: dict = {}


def hole_loops_cached(d: dict) -> dict:
    key = id(d)
    if key not in _HOLE_LOOPS_CACHE:
        _HOLE_LOOPS_CACHE[key] = hole_loops(d)
    return _HOLE_LOOPS_CACHE[key]


def cmd_hole_check(args) -> int:
    from concurrent.futures import ProcessPoolExecutor

    images = images_from(args)
    wanted = {s.strip() for s in args.pictures.split(",") if s.strip()}
    args.out.mkdir(parents=True, exist_ok=True)
    jobs = [(str(p), str(args.before_after), lacunae.image_label(p) in wanted) for p in images]
    with ProcessPoolExecutor(max_workers=max(1, min(args.workers, len(jobs)))) as ex:
        out = list(ex.map(_hole_one, jobs))

    rows = [r for o in out for r in o["rows"]]
    widths_after = [r["empty_width_after_px"] for r in rows if r["empty_width_after_px"]]
    widths_before = [r["empty_width_before_px"] for r in rows if r["empty_width_before_px"]]
    shrank = sum(1 for r in rows
                 if r["empty_width_after_px"] and r["empty_width_before_px"]
                 and r["empty_width_after_px"] < r["empty_width_before_px"])
    within = sum(1 for r in rows if r["within_glow_extent_plus_10"])
    wrong_before = sum(o["band_8px"]["before"]["wrong_px"] for o in out)
    wrong_after = sum(o["band_8px"]["after"]["wrong_px"] for o in out)
    roots_fell = [o["image_label"] for o in out
                  if o["roots_per_lacuna"]["after"] < o["roots_per_lacuna"]["before"]]
    under3 = {"before": sum(o["roots_per_lacuna"]["under_3_before"] for o in out),
              "after": sum(o["roots_per_lacuna"]["under_3_after"] for o in out)}
    biggest = [o for o in out if o["biggest_owner_share"]["after"] > 0.25
               and o["biggest_owner_share"]["after"] > o["biggest_owner_share"]["before"]]
    floors = [o["empty_width_px"]["null_floor"].get("median") for o in out
              if o["empty_width_px"]["null_floor"].get("median")]
    tests = {
        "A_mask_outside_every_zone_identical": all(
            o["first_pass_mask_outside_the_zones_identical"] for o in out),
        "B_empty_width": {
            "median_after_px": round(float(np.median(widths_after)), 2),
            "median_before_px": round(float(np.median(widths_before)), 2),
            "target_px": 15.0,
            "null_floor_median_px": round(float(np.median(floors)), 2) if floors else None,
            "within_glow_extent_plus_10": within,
            "of_lacunae": len(rows),
            "share_within": round(within / max(1, len(rows)), 4),
            "shrank": shrank,
            "above_the_null_floor_px": (round(float(np.median(widths_after))
                                              - float(np.median(floors)), 2) if floors else None),
            "images_at_or_under_their_own_floor": [
                o["image_label"] for o in out
                if o["empty_width_px"]["null_floor"].get("median")
                and o["empty_width_px"]["after"] <= o["empty_width_px"]["null_floor"]["median"]],
            "pass": bool(float(np.median(widths_after)) < 15.0
                         and within / max(1, len(rows)) >= 0.9),
        },
        "C_contact": {
            "wrong_px_before": wrong_before,
            "wrong_px_after": wrong_after,
            "fall": round(1.0 - wrong_after / max(1, wrong_before), 4),
            "target_fall": 0.8,
            "pass": bool(wrong_after <= 0.2 * wrong_before),
        },
        "D_roots": {
            "images_where_roots_fell": roots_fell,
            "under_3_roots": under3,
            "pass": bool(not roots_fell and under3["after"] <= under3["before"]),
        },
        "E_biggest_owner": {
            "images_over_a_quarter": [
                {"image_label": o["image_label"],
                 "before": o["biggest_owner_share"]["before"],
                 "after": o["biggest_owner_share"]["after"]} for o in biggest],
            "largest_share_after": max(o["biggest_owner_share"]["after"] for o in out),
            "pass": bool(not biggest),
        },
    }
    report = {
        "status": "measurement only: each image run twice, nothing in the pipeline was changed",
        "what_before_means": ("config.HOLE_ZONE_RULE = False and "
                              "config.CONTACT_EVERY_TOUCHING_BODY = False, which is the glow "
                              "zone version of METHODS section 18"),
        "constants": {
            "hole_zone_margin_um": config.HOLE_ZONE_MARGIN_UM,
            "hole_zone_max_um": config.GLOW_ZONE_MAX_UM,
            "hole_gain_band_um": config.HOLE_GAIN_BAND_UM,
            "hole_gain_percentile": config.HOLE_GAIN_PERCENTILE,
            "hole_gain_clip": [config.HOLE_GAIN_MIN, config.HOLE_GAIN_MAX],
            "hole_gain_step_um": config.HOLE_GAIN_STEP_UM,
            "hole_gain_smooth": config.HOLE_GAIN_SMOOTH,
            "hole_new_min_length_um": config.HOLE_NEW_MIN_LENGTH_UM,
            "hole_new_min_aspect": config.HOLE_NEW_MIN_ASPECT,
            "contact_reach_px": canaliculi.CONTACT_REACH_PX,
            "contact_every_touching_body": config.CONTACT_EVERY_TOUCHING_BODY,
        },
        "tests": tests,
        "per_image": [{k: v for k, v in o.items() if k != "rows"} for o in out],
        "per_lacuna": rows,
    }
    (args.out / "hole_check.json").write_text(json.dumps(report, indent=2) + "\n",
                                              encoding="utf-8")
    print_table(["image", "zone px", "empty width", "null floor", "roots", "skeleton px",
                 "8 px wrong", "loops"],
                [[o["image_label"], o["zone_px"],
                  f'{o["empty_width_px"]["before"]} -> {o["empty_width_px"]["after"]}',
                  o["empty_width_px"]["null_floor"].get("median"),
                  f'{o["roots_per_lacuna"]["before"]} -> {o["roots_per_lacuna"]["after"]}',
                  f'{o["skeleton_px"]["before"]} -> {o["skeleton_px"]["after"]}',
                  f'{o["band_8px"]["before"]["wrong_px"]} -> {o["band_8px"]["after"]["wrong_px"]}',
                  f'{o["loops"]["before"]["loop_count"]} -> {o["loops"]["after"]["loop_count"]}']
                 for o in out],
                title="Before (glow zone version) and after (the zone from the hole)")
    b = tests["B_empty_width"]
    print(f"\nA mask outside every zone identical: {'PASS' if tests['A_mask_outside_every_zone_identical'] else 'FAIL'}")
    print(f"B empty width median {b['median_before_px']} -> {b['median_after_px']} px, "
          f"target under {b['target_px']}, null floor of the measure "
          f"{b['null_floor_median_px']}: {'PASS' if b['pass'] else 'FAIL'}")
    print(f"  within the glow extent plus 10 px: {b['within_glow_extent_plus_10']} of "
          f"{b['of_lacunae']} ({100 * b['share_within']:.1f}%), smaller hole on {b['shrank']}")
    c = tests["C_contact"]
    print(f"C skeleton within 8 px of a body that is not its own: {c['wrong_px_before']} -> "
          f"{c['wrong_px_after']} px, a fall of {100 * c['fall']:.1f}%, target 80: "
          f"{'PASS' if c['pass'] else 'FAIL'}")
    d = tests["D_roots"]
    print(f"D roots per lacuna fell on: {d['images_where_roots_fell'] or 'no image'}; "
          f"lacunae under 3 roots {d['under_3_roots']['before']} -> "
          f"{d['under_3_roots']['after']}: {'PASS' if d['pass'] else 'FAIL'}")
    e = tests["E_biggest_owner"]
    print(f"E biggest owner share, largest after: {e['largest_share_after']}: "
          f"{'PASS' if e['pass'] else 'FAIL'}")
    print(f"\nreport -> {args.out / 'hole_check.json'}")
    for o in out:
        for p in o["pictures"]:
            print(f"picture -> {p}")
        for s in o["holes_still_wider_than_the_mark"]:
            print(f"  {o['image_label']} lacuna {s['lacuna_id']} at {s['centroid_xy']}: "
                  f"hole still {s['empty_width_px']} px")
    return 0


# ai-candidates ------------------------------------------------------------------
# EXPERIMENT (branch exp-ai-layer, docs/EXPERIMENT_AI.md). What the AI judge
# would be asked about, and nothing more: the empty zone of every lacuna, the
# contrast ratio measured in it, and the candidate segments the permissive
# tracing finds there. No network, no judge, no pipeline output is written.


def _ai_candidates_one(path_str: str) -> dict:
    import ai_judge

    state = ai_judge.pipeline_state(Path(path_str))
    candidates = ai_judge.image_candidates(state)
    rows = []
    for case in candidates["cases"]:
        kinds = {"new": 0, "unowned": 0, "owned": 0}
        classes = {name: 0 for name in ai_judge.CLASSES}
        for entry in case["decide"]:
            kinds[entry["kind"]] = kinds.get(entry["kind"], 0) + 1
            for name in entry["classes"]:
                classes[name] += 1
        rows.append({
            "image_label": state["label"],
            "case_id": case["case_id"],
            "case_kind": case["kind"],
            "lacuna_id": case["lacuna_id"],
            "centroid_xy": case["centroid_xy"],
            "crop_px": case["crop_px"],
            "numbered": len(case["decide"]),
            "numbered_new": kinds["new"],
            "numbered_unowned": kinds["unowned"],
            "numbered_traced_owned": kinds["owned"],
            "numbered_by_class": classes,
            "numbered_asked_an_owner_only": sum(1 for e in case["decide"]
                                                if e["question"] == "owner"),
            "context_segments": len(case["context"]),
            "segments_not_offered": case["segments_not_offered"],
            "segments_not_askable_here": len(case["segments_not_askable_here"]),
        })
    return {
        "image_label": state["label"],
        "lacunae": state["n_lacunae"],
        "cases": len(candidates["cases"]),
        "left_over_cases": sum(1 for c in candidates["cases"] if c["kind"] == "left over"),
        "segments": len(candidates["segments"]),
        "counts": candidates["counts"],
        "cut": candidates["cut"],
        "geometry_sha256": candidates["geometry_sha256"],
        "rows": rows,
    }


def cmd_ai_candidates(args) -> int:
    from concurrent.futures import ProcessPoolExecutor

    import ai_judge

    images = images_from(args)
    args.out.mkdir(parents=True, exist_ok=True)
    jobs = [str(p) for p in images]
    workers = max(1, min(args.workers, len(jobs)))
    with ProcessPoolExecutor(max_workers=workers) as ex:
        out = list(ex.map(_ai_candidates_one, jobs))

    rows = [r for o in out for r in o["rows"]]
    scalars = [k for k in (out[0]["counts"] if out else {}) if k != "classes"]
    totals = {k: sum(o["counts"][k] for o in out) for k in scalars}
    classes = {name: {field: sum(o["counts"]["classes"][name][field] for o in out)
                      for field in ("segments", "px", "lacunae")}
               for name in ai_judge.CLASSES}
    report = {
        "status": "EXPERIMENT, measurement only: no pipeline output and no judge",
        "question": "what the AI judge is shown, and what of it needs a decision",
        "what_a_segment_is": ("a branch of a skeleton, the piece between two junctions, at "
                             f"least {out[0]['cut']['min_segment_px'] if out else 0} px long"),
        "kinds": {
            "owned": "traced by the pipeline and owned by a lacuna",
            "unowned": "traced by the pipeline and owned by nobody",
            "new": "not traced: what the permissive cut finds inside a zone of the hole",
        },
        "classes": ai_judge.CLASSES,
        "within_reach": ("a lacuna is a candidate for a segment when its body lies within that "
                         "lacuna's own zone of the hole plus the minimum segment length of the "
                         "segment; it is the pipeline's zone and no new number"),
        "numbered": ("a segment is numbered, which is what asks the judge for a decision, "
                     "exactly when it falls in one of the four classes"),
        "the_question": {"a, c, d": "which osteocyte does this thread start from",
                         "b": "is it a real thread or glow texture, and whose"},
        "lacunae_involved": ("per class, how many lacunae are a candidate for at least one "
                             "segment of it, so how many cells its answers could move"),
        "cut": out[0]["cut"] if out else {},
        "all_images": {
            "images": len(out),
            "cases": sum(o["cases"] for o in out),
            "left_over_cases": sum(o["left_over_cases"] for o in out),
            "segments": sum(o["segments"] for o in out),
            "numbers_in_all_the_pictures": sum(r["numbered"] for r in rows),
            "numbered_new": sum(r["numbered_new"] for r in rows),
            "numbered_unowned": sum(r["numbered_unowned"] for r in rows),
            "numbered_traced_owned": sum(r["numbered_traced_owned"] for r in rows),
            "numbered_asked_an_owner_only": sum(r["numbered_asked_an_owner_only"]
                                                for r in rows),
            "classes": classes,
            **totals,
        },
        "per_image": [{k: o[k] for k in ("image_label", "lacunae", "cases", "left_over_cases",
                                         "segments", "counts", "geometry_sha256")} for o in out],
        "per_case": rows,
    }
    (args.out / "ai_candidates.json").write_text(json.dumps(report, indent=2) + "\n",
                                                 encoding="utf-8")
    print_table(["image", "lacunae", "segments", "owned", "unowned", "new",
                 "a", "b", "c", "d", "numbered", "calls"],
                [[o["image_label"], o["lacunae"], o["segments"],
                  o["counts"]["owned"], o["counts"]["unowned"], o["counts"]["new"],
                  *[o["counts"]["classes"][name]["segments"] for name in "abcd"],
                  o["counts"]["numbered"], o["cases"]] for o in out],
                title="What the judge is shown, per image: kinds, then the four classes")
    print_table(["class", "what it is", "segments", "px", "lacunae"],
                [[name, ai_judge.CLASSES[name], classes[name]["segments"],
                  classes[name]["px"], classes[name]["lacunae"]] for name in "abcd"],
                title="The four classes over all the images (a lacuna counts once per image)")
    print_table(["image", *[f"{name}: segments / px / lacunae" for name in "abcd"]],
                [[o["image_label"],
                  *[f"{o['counts']['classes'][name]['segments']} / "
                    f"{o['counts']['classes'][name]['px']} / "
                    f"{o['counts']['classes'][name]['lacunae']}" for name in "abcd"]]
                 for o in out],
                title="Segments, pixels and lacunae involved per class, per image")
    a = report["all_images"]
    print(f"\nsegments: {a['segments']} over {a['images']} images, "
          f"{a['owned']} owned, {a['unowned']} owned by nobody, {a['new']} new")
    print(f"traced in a lacuna's zone: {a['traced_in_a_zone']}, of which "
          f"{a['traced_in_a_zone_its_lacuna_does_not_own']} are not owned by that lacuna")
    print(f"touching two bodies: {a['touching_two_bodies']}; traced and owned by another than "
          f"the body it touches: {a['traced_owned_by_another_than_the_body_it_touches']}")
    print(f"numbered for a decision: {a['numbered']} segments, "
          f"{a['numbers_in_all_the_pictures']} numbers over all the pictures "
          f"({a['numbered_new']} new, {a['numbered_unowned']} unowned, "
          f"{a['numbered_traced_owned']} traced and owned), of them "
          f"{a['numbered_asked_an_owner_only']} asked an owner only and "
          f"{a['numbers_in_all_the_pictures'] - a['numbered_asked_an_owner_only']} "
          f"asked real or artifact as well")
    print(f"in two classes, so asked in two cases: {a['in_two_classes']}")
    print(f"unowned with no lacuna within reach, so not asked at all: "
          f"{a['unowned_with_no_lacuna_in_reach']} (no body in a picture could be named for "
          f"them, so the only answer they could be given is the pipeline's own)")
    print(f"calls: {a['cases']}, of them {a['left_over_cases']} for segments their lacuna's "
          f"crop cannot show with both candidates")
    print(f"in a class but no case could ask: "
          f"{a['needs_a_decision_but_no_case_could_ask']} (must be 0)")
    print(f"\nreport -> {args.out / 'ai_candidates.json'}")
    return 0



# ai-dry-run ---------------------------------------------------------------------
# EXPERIMENT (branch exp-ai-layer, docs/EXPERIMENT_AI.md). What a real run would
# cost, before any run: calls per image, estimated tokens and cost for every
# image, and the pictures of the cases for the images asked for, exactly as the
# judge would see them. No network unless --count-tokens is given, and then only
# the API's free token counter.


def _ai_dry_run_one(job: tuple) -> dict:
    import ai_judge

    path_str, picture_dir, count_tokens = job
    state = ai_judge.pipeline_state(Path(path_str))
    candidates = ai_judge.image_candidates(state)
    prompt = ai_judge.load_prompt()
    rows, pictures = [], []
    for case in candidates["cases"]:
        png, drawn = ai_judge.case_picture(state, candidates, case)
        user_text = ai_judge.case_user_text(case, drawn)
        estimate = ai_judge.estimate_case(prompt["system"], user_text, png,
                                          len(drawn["segments_drawn"]))
        kinds = drawn["kinds_drawn"]
        if count_tokens:
            payload, _canonical, _sha = ai_judge.build_request(prompt["system"], user_text, png)
            estimate["input_tokens_counted"] = ai_judge.count_tokens(payload)
            estimate["cost_usd"] = round(ai_judge.cost_usd(estimate["input_tokens_counted"],
                                                           estimate["output_tokens"]), 6)
        if picture_dir:
            out = Path(picture_dir) / f"{state['label']}_{case['case_id']}.png"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(png)
            pictures.append(out.as_posix())
        rows.append({
            "image_label": state["label"],
            "lacuna_id": case["lacuna_id"],
            "case_id": case["case_id"],
            "case_kind": case["kind"],
            "crop_px": drawn["crop_px"],
            "enlargement": drawn["enlargement"],
            "segments": len(drawn["segments_drawn"]),
            "segments_by_class": {name: sum(1 for q in drawn["questions"].values()
                                            if name in q["classes"])
                                  for name in ai_judge.CLASSES},
            "segments_asked_an_owner_only": sum(1 for q in drawn["questions"].values()
                                                if q["question"] == "owner"),
            "segments_new": kinds["new"],
            "segments_unowned": kinds["unowned"],
            "segments_traced_owned": kinds["owned"] + kinds["other"],
            "context_segments": drawn["context_drawn"],
            # A segment that lies outside its lacuna's crop now gets a call
            # of its own, so this should always be 0; it is kept as a guard.
            "segments_not_drawn": len(drawn["numbers_not_drawn"]),
            "bodies_in_the_crop": len(drawn["colours"]),
            "bodies_with_no_colour": len(drawn["bodies_with_no_colour"]),
            "picture_px": drawn["panel_px"],
            "picture_bytes": len(png),
            "estimate": estimate,
        })
    return {
        "image_label": state["label"],
        "lacunae": state["n_lacunae"],
        "calls": len(rows),
        "calls_for_a_lacuna": sum(1 for r in rows if r["case_kind"] == "lacuna"),
        "calls_for_left_over_segments": sum(1 for r in rows if r["case_kind"] == "left over"),
        "segments": int(sum(r["segments"] for r in rows)),
        "geometry_sha256": candidates["geometry_sha256"],
        "rows": rows,
        "pictures": pictures,
    }


def cmd_ai_dry_run(args) -> int:
    from concurrent.futures import ProcessPoolExecutor

    import ai_judge

    images = images_from(args)
    args.out.mkdir(parents=True, exist_ok=True)
    wanted = {s.strip() for s in args.pictures.split(",") if s.strip()}
    every = "all" in wanted
    allowed, why = ai_judge.external_calls_allowed()
    if args.count_tokens and not allowed:
        print(f"--count-tokens needs a real connection and {why}; estimating offline instead.")
        args.count_tokens = False
    jobs = [(str(p),
             str(args.out / "pictures") if every or lacunae.image_label(p) in wanted else "",
             bool(args.count_tokens)) for p in images]
    workers = max(1, min(args.workers, len(jobs)))
    with ProcessPoolExecutor(max_workers=workers) as ex:
        out = list(ex.map(_ai_dry_run_one, jobs))

    rows = [r for o in out for r in o["rows"]]
    per_image = []
    for o in out:
        tokens_in = sum(r["estimate"].get("input_tokens_counted", r["estimate"]["input_tokens"])
                        for r in o["rows"])
        tokens_out = sum(r["estimate"]["output_tokens"] for r in o["rows"])
        per_image.append({
            "image_label": o["image_label"], "lacunae": o["lacunae"], "calls": o["calls"],
            "calls_for_a_lacuna": o["calls_for_a_lacuna"],
            "calls_for_left_over_segments": o["calls_for_left_over_segments"],
            "segments": o["segments"],
            "segments_by_class": {name: sum(r["segments_by_class"][name] for r in o["rows"])
                                  for name in ai_judge.CLASSES},
            "segments_asked_an_owner_only": sum(r["segments_asked_an_owner_only"]
                                                for r in o["rows"]),
            "estimated_input_tokens": int(tokens_in),
            "estimated_output_tokens": int(tokens_out),
            "estimated_cost_usd": round(ai_judge.cost_usd(tokens_in, tokens_out), 4),
        })
    total_calls = sum(p["calls"] for p in per_image)
    total_in = sum(p["estimated_input_tokens"] for p in per_image)
    total_out = sum(p["estimated_output_tokens"] for p in per_image)
    total_cost = round(ai_judge.cost_usd(total_in, total_out), 4)
    retries = round(total_cost * 2.0, 4)
    prompt = ai_judge.load_prompt()
    report = {
        "status": "EXPERIMENT, estimate only: nothing was sent",
        "question": "what a real run of the AI judge would cost",
        "model": config.AI_JUDGE_MODEL,
        "provider": config.AI_JUDGE_PROVIDER,
        "prices_usd_per_mtok": {"input": config.AI_PRICE_INPUT_USD_PER_MTOK,
                                "output": config.AI_PRICE_OUTPUT_USD_PER_MTOK},
        "max_cost_usd": config.MAX_COST_USD,
        "how_the_estimate_is_made": (
            "input text at {t} tokens per character and the image at width x height / {p} px per "
            "token, which is the rule Anthropic documents; the answer at {o} tokens per segment "
            "plus {f}. Estimates, not measurements: a real run logs what the API reports."
        ).format(t=config.AI_TOKENS_PER_CHAR, p=config.AI_IMAGE_PIXELS_PER_TOKEN,
                 o=config.AI_OUTPUT_TOKENS_PER_SEGMENT, f=config.AI_OUTPUT_TOKENS_FIXED),
        "input_tokens_counted_by_the_api": bool(args.count_tokens),
        "prompt_sha256": prompt["prompt_sha256"],
        "examples_sha256": prompt["examples_sha256"],
        "examples_present": prompt["examples_present"],
        "classes": ai_judge.CLASSES,
        "the_question": {"a, c, d": "which osteocyte does this thread start from, the first "
                                    "candidate, the second candidate, or none",
                         "b": "is it a real thread or glow texture, and whose"},
        "all_images": {
            "images": len(per_image), "calls": total_calls,
            "segments": int(sum(p["segments"] for p in per_image)),
            "segments_by_class": {name: sum(p["segments_by_class"][name] for p in per_image)
                                  for name in ai_judge.CLASSES},
            "segments_asked_an_owner_only": int(sum(p["segments_asked_an_owner_only"]
                                                    for p in per_image)),
            "cases_by_crop_px": {str(size): sum(1 for r in rows if r["crop_px"] == size)
                                 for size in sorted({r["crop_px"] for r in rows})},
            "estimated_input_tokens": int(total_in),
            "estimated_output_tokens": int(total_out),
            "estimated_cost_usd": total_cost,
            "estimated_cost_usd_if_every_call_is_retried_once": retries,
            "within_max_cost_usd": bool(retries <= config.MAX_COST_USD),
            "cases_with_a_body_that_has_no_colour": int(sum(1 for r in rows
                                                            if r["bodies_with_no_colour"])),
            "calls_for_left_over_segments":
                int(sum(p["calls_for_left_over_segments"] for p in per_image)),
            "segments_numbered_but_not_drawn":
                int(sum(r["segments_not_drawn"] for r in rows)),
        },
        "per_image": per_image,
        "per_case": rows,
        "pictures": [p for o in out for p in o["pictures"]],
    }
    (args.out / "ai_dry_run.json").write_text(json.dumps(report, indent=2) + "\n",
                                              encoding="utf-8")
    print_table(["image", "lacunae", "calls", "left over", "segments",
                 "a", "b", "c", "d", "in tokens", "out tokens", "cost USD"],
                [[p["image_label"], p["lacunae"], p["calls"],
                  p["calls_for_left_over_segments"], p["segments"],
                  *[p["segments_by_class"][name] for name in "abcd"],
                  p["estimated_input_tokens"], p["estimated_output_tokens"],
                  p["estimated_cost_usd"]] for p in per_image],
                title=f"Estimate for {config.AI_JUDGE_MODEL}, numbered segments by class")
    a = report["all_images"]
    print(f"\ntotal: {a['calls']} calls, {a['segments']} segments, "
          f"{a['estimated_input_tokens']} input and {a['estimated_output_tokens']} output tokens, "
          f"estimated ${a['estimated_cost_usd']}")
    print("by class: " + ", ".join(f"{name} {a['segments_by_class'][name]}" for name in "abcd")
          + f"; {a['segments_asked_an_owner_only']} asked an owner only and "
          f"{a['segments'] - a['segments_asked_an_owner_only']} asked real or artifact as well")
    print("crops: " + ", ".join(f"{n} cases at {size} px" for size, n
                                in a["cases_by_crop_px"].items()))
    print(f"worst case with every call retried once: ${retries}, "
          f"ceiling ${config.MAX_COST_USD}: {'within it' if a['within_max_cost_usd'] else 'ABOVE IT'}")
    print(f"calls for segments outside their lacuna's crop: "
          f"{a['calls_for_left_over_segments']}; numbered but not drawn: "
          f"{a['segments_numbered_but_not_drawn']} (must be 0)")
    if a["cases_with_a_body_that_has_no_colour"]:
        print(f"cases with a body the judge cannot name: "
              f"{a['cases_with_a_body_that_has_no_colour']}")
    print(f"\nreport -> {args.out / 'ai_dry_run.json'}")
    for picture in report["pictures"]:
        print(f"picture -> {picture}")
    return 0


# ai-judge -----------------------------------------------------------------------
# EXPERIMENT (branch exp-ai-layer, docs/EXPERIMENT_AI.md). The judge itself: one
# call per lacuna, every request and answer logged, the verdicts written to the
# image's decision file. With --replay it reruns from the log with no network
# and checks that it gets the same decisions back.


AI_SELF_TEST_DIR = config.PROJECT_ROOT / ".cache" / "ai_self_test"
AI_REPLAY_DIR = config.PROJECT_ROOT / ".cache" / "ai_replay"


def _ai_self_test(images: list) -> int:
    """The whole chain with no network and no key: a picture becomes a request,
    a stub answer becomes verdicts, the log replays to the same verdicts, and
    the switch then edits the mask and runs the rest of the pipeline on it.

    The stub answers by a fixed rule that means nothing biologically
    (ai_judge.stub_answerer), so this checks the machinery and never the
    judgement. Everything it writes goes to .cache/, which is git-ignored, and
    never to results/: a rehearsal must not leave verdicts where the pipeline
    could pick them up."""
    import ai_judge

    image_path = images[0]
    label = lacunae.image_label(image_path)
    saved_root, saved_switch = ai_judge.LOG_ROOT, config.AI_JUDGE_ENABLED
    ai_judge.LOG_ROOT = AI_SELF_TEST_DIR
    checks = []
    try:
        print(f"AI judge self-test on {label} (stub judge, nothing is sent)")
        state = ai_judge.pipeline_state(image_path)
        candidates = ai_judge.image_candidates(state)
        print(f"  {len(candidates['cases'])} cases "
              f"({sum(1 for c in candidates['cases'] if c['kind'] == 'left over')} for segments "
              f"outside a crop), {len(candidates['segments'])} segments of which "
              f"{sum(len(c['decide']) for c in candidates['cases'])} are numbered, "
              f"geometry {candidates['geometry_sha256'][:12]}")

        run = ai_judge.judge_image(state, candidates, "self-test",
                                   answerer=ai_judge.stub_answerer())
        totals = run["totals"]
        print(f"  judged: {totals['segments_real']} real, {totals['segments_artifact']} artifact, "
              f"{totals['segments_unjudged']} unjudged; "
              f"{totals['invalid_attempts']} of {totals['attempts']} attempts were bad json")
        checks.append(("the stub answered and the answers validated", totals["cases_valid"] > 0))
        checks.append(("a bad answer was retried", totals["attempts"] > totals["cases"]))
        checks.append(("a case that never validated is unjudged, not guessed",
                       totals["cases_unjudged"] > 0 and totals["segments_unjudged"] > 0))

        replay = ai_judge.judge_image(state, candidates, "replay",
                                      out_root=AI_SELF_TEST_DIR / "replay")
        same = _ai_same_decisions(run, replay)
        print(f"  replay from the log: {'identical verdicts' if same else 'DIFFERENT'}")
        checks.append(("replay gives the same verdicts", same))
        logged = [r for r in (ai_judge.read_log(label, c["case_id"], 1)
                              for c in run["cases"]) if r]
        checks.append(("every request is logged with its hash",
                       len(logged) == sum(1 for c in run["cases"] if c["attempts"]) and
                       all(r.get("request_sha256") for r in logged)))
        checks.append(("no key and no image bytes are in the log",
                       all("ANTHROPIC_API_KEY" not in json.dumps(r) and
                           "data" not in json.dumps(r.get("request", {}).get("image", {}))
                           for r in logged)))

        before = canaliculi.analyse_image(image_path)
        config.AI_JUDGE_ENABLED = True
        after = canaliculi.analyse_image(image_path)
        config.AI_JUDGE_ENABLED = saved_switch
        counts = after["ai_judge"]["counts"]
        zone = after["ai_judge"]["zone_px"]
        outside = int(((before["candidate"] != after["candidate"])
                       & (after["ai_zone_owner"] == 0)).sum())
        first_pass_same = bool((before["candidate_first_pass"]
                                == after["candidate_first_pass"]).all())
        roots_before = sum(quantification.cell_root_count(before["graph"], i + 1)
                           for i in range(len(before["lacunae"]["kept"])))
        roots_after = sum(quantification.cell_root_count(after["graph"], i + 1)
                          for i in range(len(after["lacunae"]["kept"])))
        print(f"  the switch: {counts['real']} real and {counts['artifact']} artifact "
              f"verdicts applied ({counts['real_new']} new kept, {counts['artifact_new']} new "
              f"refused, {counts['artifact_traced']} traced dropped), mask "
              f"{counts['added_px']:+d} px and {-counts['removed_px']:+d} px, "
              f"{counts['edited_px_outside_the_zones']} px of it outside a zone of the hole")
        print(f"  skeleton {int(before['skeleton'].sum())} -> {int(after['skeleton'].sum())} px, "
              f"roots {roots_before} -> {roots_after}, "
              f"owned {int((before['owner_map'] > 0).sum())} -> "
              f"{int((after['owner_map'] > 0).sum())} px")
        print(f"  ownership: {counts['attached_segments']} segments attached "
              f"({counts['attached_to_another_cell']} to a cell that did not own them), "
              f"{counts['ownership_moved_px']} px changed hands, "
              f"{counts['newly_owned_px']} px newly owned, "
              f"{counts['no_longer_owned_px']} px no longer owned")
        print(f"  outside the zones the mask then moves by {outside} px, which is the dim pass "
              f"({before['dim_pass_px']} -> {after['dim_pass_px']} px) growing from the "
              f"ownership it was given, not the judge writing there")
        checks.append(("the switch changes the mask", counts["added_px"] + counts["removed_px"] > 0))
        checks.append(("the judge edits only the segments it was given",
                       counts["edited_px_outside_the_judged_segments"] == 0 and first_pass_same))
        checks.append(("the pipeline runs to the end with the switch on",
                       after["graph"] is not None and after["owner_map"].any()))
        checks.append(("nothing the judge said deleted tracing the pipeline made",
                       counts["artifact_traced"] == 0))

        # A verdict that moves a network from one cell to the other, which is
        # what the whole experiment is for. The stub gives every white number to
        # the LAST candidate it is offered, which for a class d segment is the
        # cell that does not own it, so the attachment goes in and the shortest
        # path has to split the network. Both ends of that are checked: that an
        # attachment went to another cell, and that tracing then changed hands.
        moved = _ai_ownership_moves(before, after)
        print(f"  a verdict moves a network: {counts['attached_to_another_cell']} segments "
              f"attached to a cell that did not own them, {counts['ownership_moved_px']} px of "
              f"tracing changed hands between {len(moved)} pair(s) of cells")
        for (was, now), px in sorted(moved.items(), key=lambda kv: -kv[1])[:3]:
            print(f"    cell {was} -> cell {now}: {px} px")
        checks.append(("a verdict moves a network between two owners",
                       counts["attached_to_another_cell"] > 0
                       and counts["ownership_moved_px"] > 0 and bool(moved)))

        # Two cases that disagree about one segment. No segment on these 8
        # images is numbered in two cases, so the rule is exercised on a
        # decision file built for it: one judged segment answered a second time
        # with a different owner. The answer must be thrown away whole and the
        # segment left exactly as the pipeline had it.
        disagreed = _ai_conflict_check(image_path, label, run, after)
        print(f"  two cases that disagree about {disagreed['segment_id']}: "
              f"{disagreed['conflicting']} segment counted as conflicting, "
              f"{disagreed['attached']} segments attached against "
              f"{disagreed['attached_without_it']} with no disagreement, so that one attaches "
              f"to neither cell; {disagreed['differs_px']} px of ownership differ")
        checks.append(("a segment two cases answer differently is left alone and counted",
                       disagreed["conflicting"] == 1
                       and disagreed["attached"] == disagreed["attached_without_it"] - 1))
        try:
            ai_judge.LOG_ROOT = AI_SELF_TEST_DIR / "empty"
            config.AI_JUDGE_ENABLED = True
            canaliculi.analyse_image(image_path)
            refused = False
        except FileNotFoundError:
            refused = True
        finally:
            config.AI_JUDGE_ENABLED = saved_switch
            ai_judge.LOG_ROOT = AI_SELF_TEST_DIR
        checks.append(("an image with no decision file is refused, not passed over", refused))

        # The two guards a run of 8 images leans on, rehearsed with no network.
        # A prompt the model cannot answer must cost about 20 calls and not 145.
        ai_judge.LOG_ROOT = AI_SELF_TEST_DIR / "gate"
        gate_run = ai_judge.judge_image(state, candidates, "self-test",
                                        out_root=AI_SELF_TEST_DIR / "gate",
                                        answerer=ai_judge.unreadable_answerer(),
                                        stop_check=ai_judge.quality_gate())
        ai_judge.LOG_ROOT = AI_SELF_TEST_DIR
        gate_totals = gate_run["totals"]
        print(f"  the quality gate: every answer unreadable, stopped after "
              f"{gate_totals['calls']} calls and {gate_totals['cases']} of "
              f"{len(candidates['cases'])} cases: {gate_totals['stopped_early']}")
        checks.append(("a run whose answers cannot be read stops itself",
                       bool(gate_totals["stopped_early"])
                       and gate_totals["cases"] < len(candidates["cases"])
                       and gate_totals["calls"]
                       <= config.AI_MIN_CALLS_BEFORE_QUALITY_GATE + 2))

        # A billing, credit or authentication error stops the run at once and
        # raises: nothing is marked unjudged and no decision file is written.
        fatal = _ai_fatal_check(state, candidates)
        print(f"  a billing error: {fatal['what']}")
        checks.append(("a billing or authentication error stops the run at once",
                       fatal["raised"] and fatal["calls"] == 0
                       and not fatal["decision_file"]))
    finally:
        ai_judge.LOG_ROOT, config.AI_JUDGE_ENABLED = saved_root, saved_switch

    print()
    print_table(["check", "result"],
                [[name, "PASS" if ok else "FAIL"] for name, ok in checks])
    failed = [name for name, ok in checks if not ok]
    print(f"\n{len(checks) - len(failed)} of {len(checks)} checks pass"
          + (f"; FAILED: {failed}" if failed else ""))
    print(f"everything written went to {AI_SELF_TEST_DIR} and nothing to results/")
    return 1 if failed else 0


def cmd_ai_judge(args) -> int:
    import ai_judge

    images = images_from(args)
    if args.self_test:
        return _ai_self_test(images[:1])
    mode = "replay" if args.replay else "live"
    # Only a live run asks whether it may call out. A replay never looks at
    # either environment variable, the key least of all: it has no use for it.
    if mode == "live":
        allowed, why = ai_judge.external_calls_allowed()
        if not allowed:
            print(f"Refused: a real run needs a connection and {why}.")
            print("Set ALLOW_EXTERNAL_API=1 and ANTHROPIC_API_KEY, or run with --replay.")
            return 2

    # The quality gate, over the whole run and not one image: it stops the run
    # if too many answers cannot be read, and one counter watches every image.
    gate = ai_judge.quality_gate()
    rc = 0
    for image_path in images:
        label = lacunae.image_label(image_path)
        print(f"\n== {label} ({mode}) ==")
        state = ai_judge.pipeline_state(image_path)
        candidates = ai_judge.image_candidates(state)
        prompt = ai_judge.load_prompt()

        # The cost gate: estimate the whole image before the first call.
        estimated = 0.0
        for case in candidates["cases"]:
            png, drawn = ai_judge.case_picture(state, candidates, case)
            estimate = ai_judge.estimate_case(prompt["system"],
                                              ai_judge.case_user_text(case, drawn), png,
                                              len(drawn["segments_drawn"]))
            estimated += estimate["cost_usd"]
        estimated = round(estimated, 4)
        print(f"{len(candidates['cases'])} calls, estimated ${estimated}, "
              f"ceiling ${config.MAX_COST_USD}")
        if mode == "live" and estimated > config.MAX_COST_USD:
            print(f"Refused: the estimate ${estimated} is above config.MAX_COST_USD "
                  f"${config.MAX_COST_USD}.")
            return 2

        def show(case_record, totals):
            kept = sum(1 for s in case_record["segments"] if s["verdict"] == "real")
            print(f"  {case_record['case_id']}: {case_record['segments_offered']} segments, "
                  f"{kept} real, "
                  f"{'ok' if case_record['answer_valid'] else 'UNJUDGED'}, "
                  f"running ${totals['cost_usd']}")

        if args.out:
            out_root = Path(args.out) / label
        else:
            # A replay writes beside the log by default only when it is asked
            # to: left alone it writes to .cache/, so a real run's record of
            # what it cost is never replaced by a replay's zeros.
            out_root = (AI_REPLAY_DIR / label) if mode == "replay" else None
        try:
            decisions = ai_judge.judge_image(state, candidates, mode, out_root, progress=show,
                                             stop_check=gate if mode == "live" else None)
        except ai_judge.FatalApiError as error:
            # A billing, credit or authentication error: stop the whole run
            # here, report it, and run nothing else. Nothing is marked unjudged
            # and no decision file is written, because nothing was asked.
            print(f"\nSTOPPED: {error}")
            print("No decision file was written for this image and no further image was run.")
            return 5
        totals = decisions["totals"]
        offered = max(1, totals["segments"])
        print(f"segments: {totals['segments']} offered, "
              f"{totals['segments_real']} real ({100.0 * totals['segments_real'] / offered:.1f}%), "
              f"{totals['segments_artifact']} artifact "
              f"({100.0 * totals['segments_artifact'] / offered:.1f}%), "
              f"{totals['segments_unjudged']} unjudged")
        given = [s for c in decisions["cases"] for s in c["segments"]
                 if s["verdict"] != "unjudged" and s["owner_lacuna_id"]]
        kept_owner = sum(1 for s in given if s["owner_lacuna_id"] == s["owner_lacuna_id_before"])
        from_none = sum(1 for s in given if not s["owner_lacuna_id_before"])
        between = len(given) - kept_owner - from_none
        print(f"owners: {len(given)} segments given one: {kept_owner} the cell that already "
              f"owned it, {from_none} a segment nobody owned, {between} moved from one cell to "
              f"another; {totals['segments_given_no_owner']} given none")
        print(f"json failures: {totals['invalid_attempts']} of {totals['attempts']} attempts "
              f"({totals['call_errors']} of them a failed call, "
              f"{totals['refusals']} a refusal), "
              f"{totals['cases_unjudged']} of {totals['cases']} cases left unjudged")
        print(f"cost: ${totals['cost_usd']} for {totals['calls']} calls "
              f"({totals['input_tokens']} input, {totals['output_tokens']} output tokens)")
        if totals["stopped_early"]:
            print(f"\nSTOPPED: {totals['stopped_early']}.")
            print("The rest of this image and every image after it were not run.")
            return 6
        if totals["stopped_on_cost"]:
            print(f"STOPPED: the running total passed config.MAX_COST_USD "
                  f"${config.MAX_COST_USD}. The rest of the image was not judged.")
            rc = 3
        if mode == "replay":
            if not totals["attempts"]:
                print("replay against the log: the log holds no answers for this image yet, "
                      "so every segment is unjudged and keeps the deterministic decision")
            else:
                print(f"replay against the log: {totals['attempts']} attempts replayed, "
                      f"{totals['replay_request_mismatches']} requests and "
                      f"{totals['replay_picture_mismatches']} pictures differ from what was sent")
            live_path = ai_judge.decisions_path(label)
            if live_path.exists():
                same = _ai_same_decisions(json.loads(live_path.read_text(encoding="utf-8")),
                                          decisions)
                print(f"replay against the logged run: "
                      f"{'IDENTICAL verdicts' if same else 'DIFFERENT, see below'}")
                if not same:
                    rc = 4
    return rc


def _ai_fatal_check(state: dict, candidates: dict) -> dict:
    """A billing error on the first call must stop the run at once: it is
    raised, nothing is counted as judged or unjudged, and no decision file is
    left behind for the pipeline to pick up."""
    import ai_judge

    class BadRequestError(Exception):
        pass

    def broke(payload):
        raise BadRequestError("Your credit balance is too low to access the Anthropic API.")

    out = AI_SELF_TEST_DIR / "fatal"
    if out.exists():
        shutil.rmtree(out)
    saved = ai_judge.LOG_ROOT
    ai_judge.LOG_ROOT = out
    try:
        ai_judge.judge_image(state, candidates, "self-test", out_root=out, answerer=broke)
        what, raised = "it carried on, which it must not", False
    except ai_judge.FatalApiError as error:
        what, raised = str(error), True
    finally:
        ai_judge.LOG_ROOT = saved
    written = sorted(p.name for p in out.rglob("*_ai_segments.json"))
    return {"raised": raised, "what": what, "decision_file": written,
            "calls": len(sorted(out.rglob("*_attempt2.json")))}


def _ai_ownership_moves(before: dict, after: dict) -> dict:
    """{(the cell that owned it, the cell that owns it now): pixels}, over the
    tracing both runs own. It is what the shortest path did once the judge's
    attachments were in the graph, not anything the judge wrote."""
    was, now = before["owner_map"], after["owner_map"]
    both = (was > 0) & (now > 0) & (was != now)
    moves: dict = {}
    for a, b in zip(was[both].tolist(), now[both].tolist()):
        moves[(int(a), int(b))] = moves.get((int(a), int(b)), 0) + 1
    return moves


def _ai_conflict_check(image_path: Path, label: str, run: dict, after: dict) -> dict:
    """Two cases that answer one segment differently: the answer is thrown away
    whole and the segment is left exactly as the pipeline had it.

    No segment on these 8 images is numbered in two cases, so the rule is
    exercised on a decision file written for it: one segment the stub judged and
    gave an owner is answered a second time, in a case of its own, with a
    different owner. Nothing else in the file changes, and the geometry hash
    still matches, because what the judge was ASKED is the same.

    `after` is the run with the same verdicts and no conflict, so the difference
    between the two is exactly what dropping that one attachment did."""
    import ai_judge

    decisions = json.loads(json.dumps(run))  # a copy, so the run's own file stands
    picked = None
    for case in decisions["cases"]:
        for item in case["segments"]:
            if item["verdict"] == "real" and item["owner_lacuna_id"]:
                picked = (case, item)
                break
        if picked:
            break
    if picked is None:
        return {"conflicting": -1, "attached": -1, "attached_without_it": -1, "differs_px": -1}
    case, item = picked
    # The other answer: the same segment, real, given to a different cell. Any
    # other cell will do, because what is checked is that two answers which
    # disagree are no answer at all.
    other = dict(item, owner="cyan",
                 owner_lacuna_id=1 if item["owner_lacuna_id"] != 1 else 2)
    decisions["cases"] = decisions["cases"] + [dict(case, case_id="case_conflict",
                                                    segments=[other])]
    path = ai_judge.decisions_path(label)
    kept = path.read_text(encoding="utf-8")
    path.write_text(json.dumps(decisions, indent=2) + "\n", encoding="utf-8")
    saved = config.AI_JUDGE_ENABLED
    try:
        config.AI_JUDGE_ENABLED = True
        result = canaliculi.analyse_image(image_path)
    finally:
        config.AI_JUDGE_ENABLED = saved
        path.write_text(kept, encoding="utf-8")
    counts = result["ai_judge"]["counts"]
    return {
        "segment_id": item["segment_id"],
        "conflicting": counts["conflicting"],
        "attached": counts["attached_segments"],
        "attached_without_it": after["ai_judge"]["counts"]["attached_segments"],
        "differs_px": int((result["owner_map"] != after["owner_map"]).sum()),
    }


# ai-run -------------------------------------------------------------------------
# EXPERIMENT (branch exp-ai-layer, docs/EXPERIMENT_AI.md). The pipeline itself,
# detection, canaliculi and quantification, with config.AI_JUDGE_ENABLED on for
# this one process, into a folder of its own. config.py is not touched: the
# switch ships off and stays off. It reads only the decision files already in
# results/ai_log/, makes no call and needs no key. Every file under results/
# outside its own output folder is hashed before and after, so the run proves it
# changed nothing it was not asked to write.


AI_RUN_DIR = config.RESULTS_DIR / "ai_run"


def _tree_manifest(root: Path, exclude: Path) -> dict:
    """{path relative to root: sha256} for every file under root, leaving out
    everything under `exclude`. Byte for byte, so a changed timestamp is not a
    change and a changed byte is."""
    import hashlib

    exclude = exclude.resolve()
    out = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        resolved = path.resolve()
        if resolved == exclude or exclude in resolved.parents:
            continue
        out[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def _ai_run_detect(job: tuple) -> dict:
    """Both detection stages for one image with the switch on, written exactly
    as src/lacunae.py and src/canaliculi.py write them."""
    path_str, out_str = job
    config.AI_JUDGE_ENABLED = True
    image_path, out_root = Path(path_str), Path(out_str)
    lac = lacunae.analyse_image(image_path)
    lacunae.write_outputs(lac, out_root)
    net = canaliculi.analyse_image(image_path)
    canaliculi.write_outputs(net, out_root)
    counts = net["ai_judge"]["counts"]
    return {"image_label": lacunae.image_label(image_path),
            "skeleton_px": int(net["skeleton"].sum()),
            "ai_judge": {k: counts[k] for k in sorted(counts)}}


def cmd_ai_run(args) -> int:
    from concurrent.futures import ProcessPoolExecutor

    import ai_judge

    images = images_from(args)
    out = Path(args.out)
    results_root = config.RESULTS_DIR
    for image_path in images:
        label = lacunae.image_label(image_path)
        if not ai_judge.decisions_path(label).is_file():
            print(f"Refused: no decision file for {label} at {ai_judge.decisions_path(label)}. "
                  f"Run or replay the judge first.")
            return 2
    print(f"The pipeline with the AI judge switch on, for this process only, into {out}")
    print("Reads results/ai_log/ only. No call is made and no key is read.")
    before = _tree_manifest(results_root, out)
    print(f"results/ before: {len(before)} files hashed (leaving out {out.name}/)")

    out.mkdir(parents=True, exist_ok=True)
    jobs = [(str(p), str(out)) for p in images]
    workers = max(1, min(args.workers, len(jobs)))
    with ProcessPoolExecutor(max_workers=workers) as ex:
        detected = list(ex.map(_ai_run_detect, jobs))
    for row in detected:
        c = row["ai_judge"]
        print(f"  {row['image_label']}: detection written, skeleton {row['skeleton_px']} px, "
              f"{c['real']} real and {c['artifact']} artifact verdicts applied, "
              f"{c['attached_segments']} attached, {c['conflicting']} conflicting, "
              f"{c['ownership_moved_px']} px changed hands")

    # Quantification exactly as src/quantification.py runs it: from the files
    # detection has just written, then the cross-image table.
    config.AI_JUDGE_ENABLED = True
    quantified = []
    for image_path in images:
        label = lacunae.image_label(image_path)
        detection = quantification.load_detection(out, label)
        result = quantification.quantify(detection, image_path, None)
        quantification.write_outputs(result, out)
        quantified.append(result)
        print(f"  {label}: quantified, lacunae={result['lacuna_count']} "
              f"(interior {result['interior_lacuna_count']}), roots per cell="
              f"{result['summary']['roots_count']['mean']}")
    quantification.write_summary_table(quantified, out)
    config.AI_JUDGE_ENABLED = False

    after = _tree_manifest(results_root, out)
    changed = sorted(k for k in before if k in after and before[k] != after[k])
    gone = sorted(k for k in before if k not in after)
    new = sorted(k for k in after if k not in before)
    same = not (changed or gone or new)
    report = {
        "status": ("EXPERIMENT. The pipeline with config.AI_JUDGE_ENABLED on for this run "
                   "only, from the decision files in results/ai_log/. Not validated."),
        "written_at": ai_judge.utc_now(),
        "images": [lacunae.image_label(p) for p in images],
        "per_image": detected,
        "results_outside_this_folder": {
            "files_hashed": len(before),
            "byte_identical_afterwards": same,
            "changed": changed, "removed": gone, "added": new,
        },
    }
    (out / "ai_run.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\nresults/ after: {len(after)} files hashed; "
          + ("BYTE IDENTICAL to before" if same else
             f"CHANGED: {len(changed)} changed, {len(gone)} removed, {len(new)} added"))
    for k in (changed + gone + new)[:20]:
        print(f"  {k}")
    print(f"report -> {out / 'ai_run.json'}")
    return 0 if same else 1


# ai-compare ---------------------------------------------------------------------
# EXPERIMENT (branch exp-ai-layer, docs/EXPERIMENT_AI.md). Judge off against
# judge on, per image. Both runs are recomputed in memory and then checked
# against the files on disk pixel for pixel, judge off against results/<label>/
# and judge on against results/ai_run/<label>/, so the numbers describe exactly
# what was written. No call is made and no key is read.


AI_COMPARE_SCRATCH = config.PROJECT_ROOT / ".cache" / "ai_compare"


def _root_clusters(G: nx.Graph, cell_id: int) -> list:
    """The clusters quantification.cell_root_count counts, one per root, so a
    root can be asked where it came from. Same nodes, same single linkage, same
    merge distance."""
    src = ("cell", cell_id)
    if not G.has_node(src):
        return []
    unmerged = [n for n in G.neighbors(src) if not canaliculi._is_cell_node(n)]
    clusters = []
    while unmerged:
        cluster = [unmerged.pop()]
        changed = True
        while changed:
            changed = False
            for other in list(unmerged):
                if any(np.hypot(other[0] - m[0], other[1] - m[1]) <= canaliculi.ROOT_MERGE_DIST_PX
                       for m in cluster):
                    cluster.append(other)
                    unmerged.remove(other)
                    changed = True
        clusters.append(cluster)
    return clusters


def _owner_stats(result: dict, n_lacunae: int) -> dict:
    """Skeleton, owned and unowned px, and the largest owner's share."""
    skeleton, owner_map = result["skeleton"], result["owner_map"]
    owned = skeleton & (owner_map > 0)
    per_cell = np.bincount(owner_map[owned], minlength=n_lacunae + 1)
    top = int(np.argmax(per_cell[1:])) + 1 if per_cell[1:].any() else 0
    total = int(skeleton.sum())
    return {"skeleton_px": total, "owned_px": int(owned.sum()),
            "unowned_px": int((skeleton & (owner_map == 0)).sum()),
            "largest_owner": top, "largest_owner_px": int(per_cell[top]) if top else 0,
            "largest_owner_share": round(float(per_cell[top]) / max(1, total), 4) if top else 0.0}


def _pixel_moves(before: np.ndarray, after: np.ndarray) -> tuple:
    """(pixels that changed hands, {(was, now): pixels}) over the tracing both
    owner maps own. The same measure the detection record carries as
    ownership_moved_px."""
    both = (before > 0) & (after > 0) & (before != after)
    pairs: dict = {}
    for a, b in zip(before[both].tolist(), after[both].tolist()):
        pairs[(int(a), int(b))] = pairs.get((int(a), int(b)), 0) + 1
    return int(both.sum()), pairs


def _segment_moves(before: dict, after: dict) -> dict:
    """Segments of the judge-on skeleton whose owner changed: a branch, split at
    junctions as the judge's segments are and at least as long, whose majority
    owner on the judge-off owner map is one cell and on the judge-on map
    another. It is the outcome of the shortest path, counted in the unit the
    judge was asked about."""
    import ai_judge

    labels = ai_judge._branch_labels(after["skeleton"])
    was_map, now_map = before["owner_map"], after["owner_map"]
    moved, px, pairs = 0, 0, {}
    for index, box in enumerate(ndi.find_objects(labels), start=1):
        if box is None:
            continue
        piece = labels[box] == index
        if int(piece.sum()) < ai_judge.MIN_SEGMENT_PX:
            continue
        was = was_map[box][piece]
        now = now_map[box][piece]
        was, now = was[was > 0], now[now > 0]
        if not was.size or not now.size:
            continue
        a, b = int(np.bincount(was).argmax()), int(np.bincount(now).argmax())
        if a != b:
            moved += 1
            px += int(piece.sum())
            pairs[(a, b)] = pairs.get((a, b), 0) + 1
    return {"segments": moved, "px": px, "pairs": pairs}


def _verdict_split(decisions: dict) -> dict:
    """Per class, what the verdicts did with ownership: kept by the cell that
    already owned it, given to a segment nobody owned, moved from one cell to
    another, or given to no cell. Segments and their own pixels, and the pairs
    of cells for the moves."""
    out = {}
    for case in decisions["cases"]:
        for seg in case["segments"]:
            if seg["verdict"] == "unjudged":
                continue
            for name in seg.get("classes", []) or ["?"]:
                row = out.setdefault(name, {k: {"segments": 0, "px": 0} for k in
                                            ("kept", "from_none", "moved", "no_owner")})
                row.setdefault("pairs", {})
                was, now = seg["owner_lacuna_id_before"], seg["owner_lacuna_id"]
                if not now:
                    kind = "no_owner"
                elif now == was:
                    kind = "kept"
                elif not was:
                    kind = "from_none"
                else:
                    kind = "moved"
                    key = f"{was}->{now}"
                    row["pairs"][key] = row["pairs"].get(key, 0) + 1
                row[kind]["segments"] += 1
                row[kind]["px"] += int(seg["px"])
    return out


def _titled_pair(left: np.ndarray, right: np.ndarray, titles: tuple) -> Image.Image:
    """Two pictures side by side with a title over each and a gap between."""
    from PIL import Image, ImageDraw, ImageFont

    def rgb(a):
        a = np.asarray(a)
        return np.stack([a] * 3, axis=-1) if a.ndim == 2 else a[..., :3]

    left, right = rgb(left), rgb(right)
    gap, bar = 12, 44
    h = max(left.shape[0], right.shape[0])
    canvas = np.full((h + bar, left.shape[1] + gap + right.shape[1], 3), 30, dtype=np.uint8)
    canvas[bar:bar + left.shape[0], :left.shape[1]] = left
    canvas[bar:bar + right.shape[0], left.shape[1] + gap:] = right
    picture = Image.fromarray(canvas)
    draw = ImageDraw.Draw(picture)
    try:
        font = ImageFont.truetype("arial.ttf", 26)
    except OSError:
        font = ImageFont.load_default()
    draw.text((12, 8), titles[0], fill=(255, 255, 255), font=font)
    draw.text((left.shape[1] + gap + 12, 8), titles[1], fill=(255, 255, 255), font=font)
    return picture


def _ownership_change_picture(before: dict, after: dict) -> np.ndarray:
    """One frame: the judge-on skeleton in grey, the tracing that changed hands
    in red, newly owned in green, no longer owned in blue, and every body
    outlined in white. Each changed pixel is widened by one pixel so a
    one-pixel thread can be seen at this size; nothing else is drawn."""
    shape = after["skeleton"].shape
    was, now = before["owner_map"], after["owner_map"]
    canvas = np.zeros(shape + (3,), dtype=np.uint8)
    canvas[before["skeleton"]] = (70, 70, 70)
    canvas[after["skeleton"]] = (150, 150, 150)
    widen = morphology.disk(1)
    for mask, colour in ((((was == 0) & (now > 0)), (0, 220, 0)),
                         (((was > 0) & (now == 0)), (70, 120, 255)),
                         (((was > 0) & (now > 0) & (was != now)), (255, 40, 40))):
        canvas[morphology.dilation(mask, widen)] = colour
    canvas[segmentation.find_boundaries(after["lacuna_id_map"], mode="outer")] = (255, 255, 255)
    return canvas


def _ai_compare_one(job: tuple) -> dict:
    from PIL import Image

    import ai_judge

    path_str, compare_str, run_str = job
    image_path, compare_dir, run_root = Path(path_str), Path(compare_str), Path(run_str)
    label = lacunae.image_label(image_path)
    decisions = ai_judge.read_decisions(label)

    config.AI_JUDGE_ENABLED = False
    before = canaliculi.analyse_image(image_path)
    config.AI_JUDGE_ENABLED = True
    after = canaliculi.analyse_image(image_path)
    config.AI_JUDGE_ENABLED = False
    n = len(before["lacunae"]["kept"])

    # The comparison must describe the files on disk, not a run of its own.
    def disk(root, suffix):
        return lacunae.result_path(root, label, config.SECTION_CANALICULI, suffix)

    sk_before = quantification._read_mask(disk(config.RESULTS_DIR, config.SUFFIX_CANALICULI_SKELETON))
    sk_after = quantification._read_mask(disk(run_root, config.SUFFIX_CANALICULI_SKELETON))
    q_before = json.loads(result_json(config.RESULTS_DIR, label).read_text(encoding="utf-8"))
    q_after = json.loads(result_json(run_root, label).read_text(encoding="utf-8"))
    roots_before = {int(r["lacuna_id"]): r["roots_count"] for r in q_before["lacunae"]}
    roots_after = {int(r["lacuna_id"]): r["roots_count"] for r in q_after["lacunae"]}
    interior = {int(r["lacuna_id"]): not r.get("on_border", False) for r in q_after["lacunae"]}

    # Where every verdict attached its cell, recomputed by the same function the
    # switch used, from the judge-off run it was applied to.
    _display, channel = lacunae.load_channel(image_path)
    ai = ai_judge.apply_to_base(image_path, before["candidate_first_pass"], before,
                                before["lacunae"], channel)
    G = after["graph"]
    nodes = [node for node in G.nodes() if not canaliculi._is_cell_node(node)]
    coords = np.array(nodes, dtype=np.float64)
    judge_nodes: dict = {}
    for lacuna_id, points in ai["attach"].items():
        for point in points:
            point = np.asarray(point, dtype=np.float64)
            gaps = ((coords[:, None, :] - point[None, :, :]) ** 2).sum(axis=2).min(axis=1)
            judge_nodes.setdefault(int(lacuna_id), set()).add(nodes[int(np.argmin(gaps))])
    roots_at_a_verdict = {}
    roots_in_memory = {}
    for lacuna_id in range(1, n + 1):
        clusters = _root_clusters(G, lacuna_id)
        roots_in_memory[lacuna_id] = len(clusters)
        mine = judge_nodes.get(lacuna_id, set())
        roots_at_a_verdict[lacuna_id] = sum(1 for c in clusters if mine & set(c))
    recorded = after["ai_judge"]["counts"]
    checks = {
        "judge_off_skeleton_equals_results": bool((sk_before == before["skeleton"]).all()),
        "judge_on_skeleton_equals_ai_run": bool((sk_after == after["skeleton"]).all()),
        "roots_in_memory_equal_ai_run_json": all(roots_in_memory[i] == roots_after[i]
                                                 for i in roots_after),
        "attachments_recomputed_as_the_switch_made_them": all(
            ai["counts"][k] == recorded[k] for k in ai["counts"]),
        "every_verdict_attachment_is_an_edge_of_its_cell": all(
            G.has_edge(("cell", i), node) for i, ns in judge_nodes.items() for node in ns),
    }

    moved_px, pixel_pairs = _pixel_moves(before["owner_map"], after["owner_map"])
    segments = _segment_moves(before, after)

    # Class d on its own: the same switch with every verdict but the class d
    # ones set to unjudged, so what moves is what class d moves.
    only_d = json.loads(json.dumps(decisions))
    for case in only_d["cases"]:
        for seg in case["segments"]:
            if "d" not in seg.get("classes", []):
                seg.update({"verdict": "unjudged", "owner": "none", "owner_lacuna_id": None})
    scratch = AI_COMPARE_SCRATCH / "class_d_only"
    (scratch / label).mkdir(parents=True, exist_ok=True)
    (scratch / label / f"{label}_ai_segments.json").write_text(json.dumps(only_d) + "\n",
                                                               encoding="utf-8")
    saved_root = ai_judge.LOG_ROOT
    ai_judge.LOG_ROOT = scratch
    try:
        config.AI_JUDGE_ENABLED = True
        d_run = canaliculi.analyse_image(image_path)
    finally:
        config.AI_JUDGE_ENABLED = False
        ai_judge.LOG_ROOT = saved_root
    d_px, d_pairs = _pixel_moves(before["owner_map"], d_run["owner_map"])
    d_segments = _segment_moves(before, d_run)

    # The pictures.
    compare_dir.mkdir(parents=True, exist_ok=True)
    pictures = {}
    for kind, suffix in (("verification", config.SUFFIX_CANALICULI_VERIFICATION),
                         ("skeleton", config.SUFFIX_CANALICULI_SKELETON)):
        left = np.asarray(Image.open(disk(config.RESULTS_DIR, suffix)))
        right = np.asarray(Image.open(disk(run_root, suffix)))
        out = compare_dir / f"{label}_{kind}_judge_off_on.png"
        _titled_pair(left, right, (f"{label}  judge OFF ({kind})",
                                   f"{label}  judge ON ({kind})")).save(out)
        pictures[kind] = out.relative_to(config.PROJECT_ROOT).as_posix()
    out = compare_dir / f"{label}_ownership_changes.png"
    Image.fromarray(_ownership_change_picture(before, after)).save(out)
    pictures["ownership_changes"] = out.relative_to(config.PROJECT_ROOT).as_posix()

    unnamed = [{"case_id": c["case_id"], "case_kind": c["case_kind"],
                "yellow_lacuna_id": c["lacuna_id"], "bodies_outlined_grey": c["bodies_with_no_colour"],
                "numbered_segments": c["segments_offered"],
                "every_number_had_both_candidates_named": all(
                    len(s.get("candidate_colours", [])) == len(s.get("candidates", []))
                    for s in c["segments"])}
               for c in decisions["cases"] if c["bodies_with_no_colour"]]

    def pairs_list(pairs):
        return [{"from": a, "to": b, "count": v}
                for (a, b), v in sorted(pairs.items(), key=lambda kv: (-kv[1], kv[0]))]

    roots_rows = [{"lacuna_id": i, "interior": interior.get(i, True),
                   "roots_before": roots_before.get(i), "roots_after": roots_after.get(i),
                   "roots_after_at_a_verdict_attachment": roots_at_a_verdict[i]}
                  for i in sorted(roots_after)]
    return {
        "image_label": label,
        "lacunae": n,
        "checks": checks,
        "verdicts": {"given_an_owner": int(recorded["attached_segments"]),
                     "attached_to_another_cell": int(recorded["attached_to_another_cell"]),
                     "conflicting": int(recorded["conflicting"]),
                     "by_class": _verdict_split(decisions)},
        "ownership_moves": {"px": moved_px, "pairs_px": pairs_list(pixel_pairs),
                            "segments": segments["segments"], "segments_px": segments["px"],
                            "pairs_segments": pairs_list(segments["pairs"]),
                            "newly_owned_px": int(recorded["newly_owned_px"]),
                            "no_longer_owned_px": int(recorded["no_longer_owned_px"])},
        "class_d_only": {"attached": int(d_run["ai_judge"]["counts"]["attached_segments"]),
                         "px": d_px, "pairs_px": pairs_list(d_pairs),
                         "segments": d_segments["segments"], "segments_px": d_segments["px"],
                         "pairs_segments": pairs_list(d_segments["pairs"])},
        "roots": {"mean_per_interior_cell_before": q_before["summary"]["roots_count"]["mean"],
                  "mean_per_interior_cell_after": q_after["summary"]["roots_count"]["mean"],
                  "total_before": int(sum(v for v in roots_before.values() if v is not None)),
                  "total_after": int(sum(v for v in roots_after.values() if v is not None)),
                  "total_after_at_a_verdict_attachment": int(sum(roots_at_a_verdict.values())),
                  "per_lacuna": roots_rows},
        "before": _owner_stats(before, n),
        "after": _owner_stats(after, n),
        "bodies_not_named": unnamed,
        "pictures": pictures,
    }


def cmd_ai_compare(args) -> int:
    from concurrent.futures import ProcessPoolExecutor

    images = images_from(args)
    run_root = Path(args.run).resolve()
    compare_dir = Path(args.out).resolve()
    for p in images:
        if not result_json(run_root, lacunae.image_label(p)).is_file():
            print(f"Refused: {run_root} has no output for {lacunae.image_label(p)}. "
                  f"Run python src/diagnostics.py ai-run first.")
            return 2
    jobs = [(str(p), str(compare_dir), str(run_root)) for p in images]
    workers = max(1, min(args.workers, len(jobs)))
    with ProcessPoolExecutor(max_workers=workers) as ex:
        out = list(ex.map(_ai_compare_one, jobs))

    failed = [(o["image_label"], k) for o in out for k, ok in o["checks"].items() if not ok]
    report = {
        "status": ("EXPERIMENT. Judge off (results/<label>/) against judge on "
                   "(results/ai_run/<label>/), from the decision files in results/ai_log/. "
                   "NOT VALIDATED: no verdict has been checked against a manual trace."),
        "written_at": __import__("ai_judge").utc_now(),
        "definitions": {
            "given_an_owner": "verdicts applied as a zero weight attachment, after conflicts",
            "ownership_moves.px": ("tracing owned in both runs whose owner changed, on the owner "
                                   "maps; the shortest path's doing, not the judge's"),
            "ownership_moves.segments": ("branches of the judge-on skeleton, at least the judge's "
                                         "minimum segment length, whose majority owner changed"),
            "class_d_only": "the same switch with every verdict but the class d ones unjudged",
            "roots_after_at_a_verdict_attachment": (
                "roots of the judge-on graph that contain a node a verdict attached its cell "
                "to; a root is any node attached to the cell, so an attachment far from the "
                "body counts as one"),
            "largest_owner_share": "the largest single cell's owned px over all skeleton px",
        },
        "checks_failed": failed,
        "per_image": out,
    }
    (compare_dir / "ai_compare.json").write_text(json.dumps(report, indent=2) + "\n",
                                                 encoding="utf-8")
    (compare_dir / "REPORT.md").write_text(_ai_compare_markdown(out, failed), encoding="utf-8")

    print_table(["image", "given owner", "moved verdicts", "segments moved", "px moved",
                 "class d px", "roots before", "roots after", "of them at a verdict"],
                [[o["image_label"], o["verdicts"]["given_an_owner"],
                  sum(c["moved"]["segments"] for c in o["verdicts"]["by_class"].values()),
                  o["ownership_moves"]["segments"], o["ownership_moves"]["px"],
                  o["class_d_only"]["px"], o["roots"]["total_before"], o["roots"]["total_after"],
                  o["roots"]["total_after_at_a_verdict_attachment"]] for o in out],
                title="Judge off against judge on")
    print_table(["image", "skeleton px", "owned px", "unowned px", "largest owner share"],
                [[o["image_label"],
                  f"{o['before']['skeleton_px']} -> {o['after']['skeleton_px']}",
                  f"{o['before']['owned_px']} -> {o['after']['owned_px']}",
                  f"{o['before']['unowned_px']} -> {o['after']['unowned_px']}",
                  f"{o['before']['largest_owner_share']:.3f} (cell {o['before']['largest_owner']})"
                  f" -> {o['after']['largest_owner_share']:.3f} (cell {o['after']['largest_owner']})"]
                 for o in out])
    print(f"\nchecks against the files on disk: "
          + ("all pass" if not failed else f"FAILED {failed}"))
    print(f"report -> {compare_dir / 'REPORT.md'} and {compare_dir / 'ai_compare.json'}")
    return 1 if failed else 0


def _ai_compare_markdown(out: list, failed: list) -> str:
    """The report a person reads. Every number in it is in ai_compare.json."""
    def pairs_text(pairs, unit, top=4):
        if not pairs:
            return "none"
        shown = ", ".join(f"{p['from']} to {p['to']} ({p['count']} {unit})" for p in pairs[:top])
        return shown + (f", and {len(pairs) - top} more pairs" if len(pairs) > top else "")

    lines = [
        f"# Judge off against judge on, {len(out)} image{'s' if len(out) != 1 else ''}",
        "",
        "**EXPERIMENT, branch `exp-ai-layer`. NOT VALIDATED: no verdict here has been checked "
        "against a manual trace.** Judge off is `results/<label>/`, the pipeline as it stands. "
        "Judge on is `results/ai_run/<label>/`, the same pipeline with `config.AI_JUDGE_ENABLED` "
        "on for that run only, applying the decision files in `results/ai_log/`. No call was "
        "made and no key was read.",
        "",
        "Made by `python src/diagnostics.py ai-compare --dir data/WT`. Both runs are recomputed in "
        "memory and checked against the files on disk pixel for pixel before any number is "
        "reported: the judge-off skeleton against `results/`, the judge-on skeleton against "
        "`results/ai_run/`, the roots in memory against the judge-on jsons, and the attachments "
        "against the ones the switch made. "
        + ("**Every check passed.**" if not failed else
           "**CHECKS FAILED: " + ", ".join(f"{a} {b}" for a, b in failed) + ".**")
        + " The full numbers are in `ai_compare.json`.",
        "",
        "## Summary",
        "",
        "| image | given an owner | moved by a verdict | segments moved | px moved | class d alone, px | "
        "roots before | roots after | of them at a verdict | skeleton px | owned px | unowned px | "
        "largest owner share |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    tot = {"given": 0, "moved_v": 0, "seg": 0, "px": 0, "dpx": 0, "rb": 0, "ra": 0, "rv": 0}
    for o in out:
        moved_v = sum(c["moved"]["segments"] for c in o["verdicts"]["by_class"].values())
        b, a = o["before"], o["after"]
        lines.append(
            f"| {o['image_label']} | {o['verdicts']['given_an_owner']} | {moved_v} | "
            f"{o['ownership_moves']['segments']} | {o['ownership_moves']['px']:,} | "
            f"{o['class_d_only']['px']:,} | {o['roots']['total_before']} | "
            f"{o['roots']['total_after']} | {o['roots']['total_after_at_a_verdict_attachment']} | "
            f"{b['skeleton_px']:,} to {a['skeleton_px']:,} | {b['owned_px']:,} to {a['owned_px']:,} | "
            f"{b['unowned_px']:,} to {a['unowned_px']:,} | "
            f"{b['largest_owner_share']:.3f} to {a['largest_owner_share']:.3f} |")
        tot["given"] += o["verdicts"]["given_an_owner"]
        tot["moved_v"] += moved_v
        tot["seg"] += o["ownership_moves"]["segments"]
        tot["px"] += o["ownership_moves"]["px"]
        tot["dpx"] += o["class_d_only"]["px"]
        tot["rb"] += o["roots"]["total_before"]
        tot["ra"] += o["roots"]["total_after"]
        tot["rv"] += o["roots"]["total_after_at_a_verdict_attachment"]
    lines.append(f"| **all {len(out)}** | **{tot['given']}** | **{tot['moved_v']}** | **{tot['seg']}** | "
                 f"**{tot['px']:,}** | **{tot['dpx']:,}** | **{tot['rb']:,}** | **{tot['ra']:,}** | "
                 f"**{tot['rv']}** | | | | |")
    lines += [
        "",
        "- **given an owner**: verdicts applied as a zero weight attachment, after conflicts "
        "(there were none). **moved by a verdict**: of those, the ones naming a different cell "
        "from the one that owned the segment.",
        "- **segments moved** and **px moved** are the outcome: what the shortest path did once "
        "the attachments were in the graph. A segment here is a branch of the judge-on skeleton, "
        "at least the judge's minimum segment length, whose majority owner changed.",
        "- **class d alone**: the same switch with every verdict but the class d ones left "
        "unjudged, so the pixels that change hands are the ones class d moves on its own.",
        "- **roots**: summed over every lacuna, from the quantification jsons on disk. **of them "
        "at a verdict** counts the judge-on roots that contain a node a verdict attached its cell "
        "to; see the warning below.",
        "",
        "## Roots: read this before reading the root counts",
        "",
        "A root is counted as any skeleton node attached to the cell's virtual node, clustered at "
        f"{canaliculi.ROOT_MERGE_DIST_PX:g} px (`quantification.cell_root_count`). A verdict is "
        "expressed as exactly such an attachment, at the end of the segment nearest the cell, and "
        "that end can lie tens of pixels from the body. **So every verdict that gives a cell a "
        "segment away from its body adds a root that is not a thread leaving the body.** The rise "
        "in roots below is largely that, and the column *of them at a verdict* measures how much. "
        "That column counts a root as the verdict's when any node in its cluster is a node a "
        "verdict attached the cell to, and such a cluster can also hold a node the contact rule "
        "attached, so it is an upper bound on the roots the verdicts add, and *roots on, not at "
        "one* is a lower bound on the pipeline's own. "
        "It is a property of how the attachment is counted, not a finding about the cells, and "
        "it is left as it is here because changing how a verdict is expressed, or how a root is "
        "counted, is a design decision this report does not take.",
        "",
        "| image | roots off | roots on | of them at a verdict attachment | roots on, not at one | "
        "mean per interior cell, off | on | lacunae whose roots changed |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for o in out:
        changed = [r for r in o["roots"]["per_lacuna"] if r["roots_before"] != r["roots_after"]]
        r = o["roots"]
        lines.append(f"| {o['image_label']} | {r['total_before']} | {r['total_after']} | "
                     f"{r['total_after_at_a_verdict_attachment']} | "
                     f"{r['total_after'] - r['total_after_at_a_verdict_attachment']} | "
                     f"{r['mean_per_interior_cell_before']} | {r['mean_per_interior_cell_after']} | "
                     f"{len(changed)} of {len(r['per_lacuna'])} |")
    lines += ["", "## Per image", ""]
    for o in out:
        v = o["verdicts"]["by_class"]
        lines += [f"### {o['image_label']}", ""]
        lines.append("Verdicts by class (segments, and their own px):")
        lines.append("")
        lines.append("| class | kept by its owner | given to a segment nobody owned | moved to another "
                     "cell | given no owner |")
        lines.append("| --- | --- | --- | --- | --- |")
        for name in sorted(v):
            c = v[name]
            lines.append(f"| {name} | " + " | ".join(
                f"{c[k]['segments']} ({c[k]['px']} px)"
                for k in ("kept", "from_none", "moved", "no_owner")) + " |")
        m = o["ownership_moves"]
        d = o["class_d_only"]
        lines += [
            "",
            f"- Ownership moves between cells: **{m['segments']} segments ({m['segments_px']:,} px)**, "
            f"and **{m['px']:,} px** of tracing changed hands on the owner maps. Pairs by px: "
            f"{pairs_text(m['pairs_px'], 'px')}. Pairs by segments: "
            f"{pairs_text(m['pairs_segments'], 'segments')}.",
            f"- Newly owned: {m['newly_owned_px']:,} px. No longer owned: "
            f"{m['no_longer_owned_px']:,} px.",
            f"- **Class d alone**: {d['attached']} verdicts attached, {d['segments']} segments "
            f"({d['segments_px']:,} px) and {d['px']:,} px changed hands. Pairs by px: "
            f"{pairs_text(d['pairs_px'], 'px')}.",
            f"- Class d verdicts: "
            + (f"{v['d']['moved']['segments']} moved to the other cell, "
               f"{v['d']['kept']['segments']} kept by their owner, "
               f"{v['d']['no_owner']['segments']} given no owner; pairs "
               + (", ".join(f"{k.replace('->', ' to ')} ({n})" for k, n in sorted(v['d']['pairs'].items(),
                                                            key=lambda kv: -kv[1])) or "none")
               if "d" in v else "none") + ".",
            f"- Roots, summed: {o['roots']['total_before']} to {o['roots']['total_after']}, of "
            f"which {o['roots']['total_after_at_a_verdict_attachment']} contain a verdict's "
            f"attachment node. Mean per interior cell {o['roots']['mean_per_interior_cell_before']}"
            f" to {o['roots']['mean_per_interior_cell_after']}.",
            f"- Skeleton {o['before']['skeleton_px']:,} to {o['after']['skeleton_px']:,} px; owned "
            f"{o['before']['owned_px']:,} to {o['after']['owned_px']:,}; unowned "
            f"{o['before']['unowned_px']:,} to {o['after']['unowned_px']:,}; largest owner "
            f"cell {o['before']['largest_owner']} at {o['before']['largest_owner_share']:.3f} to "
            f"cell {o['after']['largest_owner']} at {o['after']['largest_owner_share']:.3f}.",
            f"- Pictures: `{o['pictures']['verification']}`, `{o['pictures']['skeleton']}`, "
            f"`{o['pictures']['ownership_changes']}` (red changed hands, green newly owned, "
            f"blue no longer owned, grey the rest, each changed pixel widened by one so it shows).",
            "",
        ]
    lines += ["## Cases where a body could not be named", "",
              "A body beyond the sixth colour in a picture is outlined grey and has no name the "
              "judge could answer with. A number is only asked where both of its candidates have a "
              "colour, so a grey body should be context only; the last column checks that it was, "
              "number by number, from the decision files.", "",
              "| image | case | kind | yellow lacuna | grey lacunae | numbered segments | "
              "both candidates named for every number |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
    any_unnamed = False
    for o in out:
        for c in o["bodies_not_named"]:
            any_unnamed = True
            lines.append(f"| {o['image_label']} | {c['case_id']} | {c['case_kind']} | "
                         f"{c['yellow_lacuna_id']} | {', '.join(map(str, c['bodies_outlined_grey']))} | "
                         f"{c['numbered_segments']} | "
                         f"{'yes' if c['every_number_had_both_candidates_named'] else 'NO'} |")
    if not any_unnamed:
        lines.append("| none | | | | | | |")
    lines.append("")
    return "\n".join(lines)


def _ai_same_decisions(a: dict, b: dict) -> bool:
    """Do two decision files hold the same verdicts for the same candidates?"""
    if a.get("geometry_sha256") != b.get("geometry_sha256"):
        print("  the candidates differ")
        return False
    same = True
    for case_a, case_b in zip(a["cases"], b["cases"]):
        for seg_a, seg_b in zip(case_a["segments"], case_b["segments"]):
            if (seg_a["verdict"], seg_a["owner"]) != (seg_b["verdict"], seg_b["owner"]):
                print(f"  {case_a['case_id']} segment {seg_a['n']}: "
                      f"{seg_a['verdict']}/{seg_a['owner']} against "
                      f"{seg_b['verdict']}/{seg_b['owner']}")
                same = False
    return same


def main() -> None:
    parser = argparse.ArgumentParser(description="LCN pipeline diagnostics (read-only, pre-validation, px).")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("reference-check", help="Run 543-2 and check 161.00 / 21.63 / 8.50.")
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

    p = sub.add_parser("contact",
                       help="Does each lacuna own the threads that touch it? (measurement only)")
    p.add_argument("-d", dest="dir", type=Path, default=DEFAULT_IMAGE_DIR,
                   help="Folder of .tif images.")
    p.add_argument("-i", dest="image", type=Path, default=None, help="One .tif image instead.")
    p.add_argument("-o", dest="out", type=Path, required=True, help="Output folder.")
    p.add_argument("--points", default="",
                   help="Lacunae to report in full, as LABEL:X,Y;LABEL:X,Y in the 1024 px frame "
                        "(the label is the results/ folder name). The nearest lacuna to each "
                        "point is the one reported.")
    p.add_argument("--near", type=int, default=CONTACT_CENSUS_NEAR_PX,
                   help=f"How close to a body counts as touching it (default "
                        f"{CONTACT_CENSUS_NEAR_PX} px).")
    p.add_argument("--pictures", action="store_true",
                   help="Also draw the region of each named lacuna.")
    p.add_argument("--verification", type=Path, default=None,
                   help="Also write each image's whole-frame verification picture into this "
                        "folder, named <label>_<tag>.png: the before and after picture of a rule.")
    p.add_argument("--radius", type=int, default=CONTACT_PICTURE_RADIUS_PX,
                   help=f"Half-width of those pictures (default {CONTACT_PICTURE_RADIUS_PX} px).")
    p.add_argument("--tag", default="now",
                   help="Name of this run, used in the output file names (default: now).")
    p.add_argument("--contact-reach", dest="contact_reach", type=int, default=None,
                   help=f"Replace canaliculi.CONTACT_REACH_PX for this run; 0 turns the contact "
                        f"rule off, which is the behaviour before it (default: the configured "
                        f"{canaliculi.CONTACT_REACH_PX} px).")
    p.add_argument("-w", dest="workers", type=int, default=4,
                   help="Parallel processes, one image each.")
    p.set_defaults(func=cmd_contact)

    p = sub.add_parser("contact-handover",
                       help="What changed hands when the contact rule was turned on.")
    p.add_argument("-d", dest="dir", type=Path, default=DEFAULT_IMAGE_DIR,
                   help="Folder of .tif images.")
    p.add_argument("-i", dest="image", type=Path, default=None, help="One .tif image instead.")
    p.add_argument("-o", dest="out", type=Path, required=True, help="Output folder.")
    p.add_argument("--near", type=int, default=CONTACT_CENSUS_NEAR_PX,
                   help=f"How close to a body counts as touching it (default "
                        f"{CONTACT_CENSUS_NEAR_PX} px).")
    p.add_argument("-w", dest="workers", type=int, default=4,
                   help="Parallel processes, one image each (two runs each).")
    p.set_defaults(func=cmd_contact_handover)

    p = sub.add_parser("ridge-background",
                       help="Does the skeleton follow local brightness? (measurement only)")
    p.add_argument("-d", dest="dir", type=Path, default=DEFAULT_IMAGE_DIR,
                   help="Folder of .tif images.")
    p.add_argument("-i", dest="image", type=Path, default=None, help="One .tif image instead.")
    p.add_argument("-o", dest="out", type=Path, required=True, help="Output folder.")
    p.add_argument("-w", dest="workers", type=int, default=4,
                   help="Parallel processes, one image each.")
    p.set_defaults(func=cmd_ridge_background)

    p = sub.add_parser("empty-zone",
                       help="What makes the hole in the skeleton around a lacuna? (measurement only)")
    p.add_argument("-d", dest="dir", type=Path, default=DEFAULT_IMAGE_DIR,
                   help="Folder of .tif images.")
    p.add_argument("-i", dest="image", type=Path, default=None, help="One .tif image instead.")
    p.add_argument("-o", dest="out", type=Path, required=True, help="Output folder.")
    p.add_argument("-w", dest="workers", type=int, default=4,
                   help="Parallel processes, one image each.")
    p.set_defaults(func=cmd_empty_zone)

    p = sub.add_parser("glow-check",
                       help="The glow zone rule on against off, on every image.")
    p.add_argument("-d", dest="dir", type=Path, default=DEFAULT_IMAGE_DIR,
                   help="Folder of .tif images.")
    p.add_argument("-i", dest="image", type=Path, default=None, help="One .tif image instead.")
    p.add_argument("-o", dest="out", type=Path, required=True, help="Output folder.")
    p.add_argument("--pictures", default="",
                   help="Image labels, comma separated, to write before and after skeleton and "
                        "verification pictures for.")
    p.add_argument("--before-after", dest="before_after", type=Path,
                   default=config.RESULTS_DIR / "before_after",
                   help="Where those pictures go (default: results/before_after).")
    p.add_argument("-w", dest="workers", type=int, default=4,
                   help="Parallel processes, one image each (two runs each).")
    p.set_defaults(func=cmd_glow_check)

    p = sub.add_parser("hole-check",
                       help="The zone from the hole against the glow zone version, with the "
                            "acceptance tests and the null floor of the empty width.")
    p.add_argument("-d", dest="dir", type=Path, default=DEFAULT_IMAGE_DIR,
                   help="Folder of .tif images.")
    p.add_argument("-i", dest="image", type=Path, default=None, help="One .tif image instead.")
    p.add_argument("-o", dest="out", type=Path, default=config.RESULTS_DIR / "hole_zone",
                   help="Output folder (default: results/hole_zone).")
    p.add_argument("--pictures", default="",
                   help="Image labels, comma separated, to write before and after pictures for.")
    p.add_argument("--before-after", dest="before_after", type=Path,
                   default=config.RESULTS_DIR / "before_after",
                   help="Where those pictures go (default: results/before_after).")
    p.add_argument("-w", dest="workers", type=int, default=4,
                   help="Parallel processes, one image each (two runs each).")
    p.set_defaults(func=cmd_hole_check)
    p = sub.add_parser("ai-candidates",
                       help="EXPERIMENT: what the AI judge would be asked about, per lacuna.")
    add_images_arguments(p)
    p.add_argument("-o", dest="out", type=Path,
                   default=config.RESULTS_DIR / config.AI_DRY_RUN_DIR,
                   help="Output folder (default: results/ai_dry_run).")
    p.add_argument("-w", dest="workers", type=int, default=4,
                   help="Parallel processes, one image each.")
    p.set_defaults(func=cmd_ai_candidates)

    p = sub.add_parser("ai-dry-run",
                       help="EXPERIMENT: what a real judge run would cost, and the pictures.")
    add_images_arguments(p)
    p.add_argument("-o", dest="out", type=Path,
                   default=config.RESULTS_DIR / config.AI_DRY_RUN_DIR,
                   help="Output folder (default: results/ai_dry_run).")
    p.add_argument("--pictures", default="",
                   help="Image labels, comma separated, to write every case picture for, "
                        "or 'all' for every image.")
    p.add_argument("--count-tokens", dest="count_tokens", action="store_true",
                   help="Count the input tokens with the API instead of estimating them "
                        "(free, but it is a real connection, so it needs ALLOW_EXTERNAL_API=1).")
    p.add_argument("-w", dest="workers", type=int, default=4,
                   help="Parallel processes, one image each.")
    p.set_defaults(func=cmd_ai_dry_run)

    p = sub.add_parser("ai-run",
                       help="EXPERIMENT: detection, canaliculi and quantification with the AI "
                            "judge switch on for this run only, into results/ai_run/.")
    add_images_arguments(p)
    p.add_argument("-o", dest="out", type=Path, default=AI_RUN_DIR,
                   help="Output folder (default: results/ai_run).")
    p.add_argument("-w", dest="workers", type=int, default=4,
                   help="Parallel processes, one image each.")
    p.set_defaults(func=cmd_ai_run)

    p = sub.add_parser("ai-compare",
                       help="EXPERIMENT: judge off against judge on per image, pictures and report.")
    add_images_arguments(p)
    p.add_argument("--run", type=Path, default=AI_RUN_DIR,
                   help="The judge-on output of ai-run (default: results/ai_run).")
    p.add_argument("-o", dest="out", type=Path, default=AI_RUN_DIR / "compare",
                   help="Where the pictures and the report go (default: results/ai_run/compare).")
    p.add_argument("-w", dest="workers", type=int, default=4,
                   help="Parallel processes, one image each.")
    p.set_defaults(func=cmd_ai_compare)

    p = sub.add_parser("ai-judge",
                       help="EXPERIMENT: run the AI judge on an image, or replay it from the log.")
    add_images_arguments(p)
    p.add_argument("--replay", action="store_true",
                   help="No network: rerun from results/ai_log/ and check the verdicts match.")
    p.add_argument("-s", "--self-test", dest="self_test", action="store_true",
                   help="Rehearse the whole chain on one image with a stub judge, no network "
                        "and no key, writing only to .cache/ai_self_test.")
    p.add_argument("-o", dest="out", type=Path, default=None,
                   help="Where a replay writes its decision file (default: beside the log, "
                        "which overwrites it with the same content).")
    p.set_defaults(func=cmd_ai_judge)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
