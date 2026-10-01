"""Task 0.2: the default-result cache and timing.

    python -u experiments/task0_cache.py build    # cache all 8 images, one after another, timed
    python -u experiments/task0_cache.py verify   # check that common.lacuna_stage and
                                                  # common.network_stage repeat the pipeline exactly

Outputs:
    results_experiments/_cache/default/<image>.npz and .json   (never committed)
    results_experiments/task0/timing.json
    results_experiments/task0/verify.csv
    results_experiments/task0/coordinates.md   (x, y) = (col, row) check

PRE-VALIDATION, PIXEL units.
"""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402

OUT = C.OUT_ROOT / "task0"


def cmd_build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    timing_path = OUT / "timing.json"
    timing = json.loads(timing_path.read_text()) if timing_path.is_file() else {}
    t_all = time.time()
    built = 0
    for p in C.IMAGE_PATHS:
        if C.cache_ok(p):
            print(f"{C.short(p)}: cache ok, skipped")
            continue
        t0 = time.time()
        meta = C.build_cache(p)
        dt = time.time() - t0
        built += 1
        timing.setdefault("per_image", {})[C.short(p)] = {
            "full_pipeline_s": meta["seconds_full_pipeline"],
            "full_pipeline_plus_cache_s": round(dt, 2),
        }
        print(f"{C.short(p)}: pipeline {meta['seconds_full_pipeline']:.1f} s, with cache {dt:.1f} s")
    if built == len(C.IMAGE_PATHS):
        timing["all_8_sequential_s"] = round(time.time() - t_all, 2)
    timing["note"] = ("One process, images one after another, on this machine (20 logical cores). "
                      "full_pipeline_s is canaliculi.analyse_image alone; the cache step adds the "
                      "recomputed intermediates and the write.")
    C.write_json(timing_path, timing)
    print(json.dumps(timing, indent=2))


def _verify_one(path_str: str) -> dict:
    p = Path(path_str)
    d = C.load(p)
    t0 = time.time()
    lac = C.lacuna_stage(d["channel"])
    t_lac = time.time() - t0
    lac_same = (lac["rows"] == d["lacuna_rows"]) and np.array_equal(lac["labels"], d["labels"])
    t0 = time.time()
    net = C.network_stage(d["channel"], lac["labels"], lac["kept"])
    t_net = time.time() - t0
    cell_same = net["cell_rows"] == d["cell_rows"]
    skel_same = bool(np.array_equal(net["skeleton"], d["skeleton"]))
    dens_same = round(net["density"], C.PRECISION + 4) == d["field"]["canalicular_length_density_per_px"]
    # Same again from the cached preprocessed channel, flagged mask and
    # hysteresis mask, the shortcut the variant runs use.
    net2 = C.network_stage(d["channel"], d["labels"], d["kept"], preprocessed=d["preprocessed"],
                           flagged=d["flagged"], signal=d["signal"], t_lo=d["t_lo"])
    cached_same = net2["cell_rows"] == d["cell_rows"] and bool(np.array_equal(net2["skeleton"], d["skeleton"]))
    return {
        "image": C.short(p),
        "lacuna_rows_identical": bool(lac_same),
        "cell_rows_identical": bool(cell_same),
        "skeleton_identical": skel_same,
        "density_identical": bool(dens_same),
        "bridges_identical": len(net["bridges"]) == d["n_bridges"],
        "shortcut_from_cache_identical": bool(cached_same),
        "lacuna_stage_s": round(t_lac, 2),
        "network_stage_s": round(t_net, 2),
    }


def cmd_verify() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "verify.csv"
    if path.is_file():
        print(path.read_text())
        return
    with ProcessPoolExecutor(max_workers=8) as ex:
        rows = list(ex.map(_verify_one, [str(p) for p in C.IMAGE_PATHS]))
    df = pd.DataFrame(rows)
    C.write_csv(path, df)
    print(df.to_string(index=False))

    # Coordinate convention check against the pipeline's own lacuna-table:
    # it prints "at (x,y)" as (centroid_col_px, centroid_row_px).
    d = C.load("543-2")
    lines = ["# Coordinate check", "",
             "`python src/diagnostics.py lacuna-table` prints `at (x,y)` from `centroid_col_px` and",
             "`centroid_row_px` in that order (src/diagnostics.py, cmd_lacuna_table). The cached rows for",
             "543-2 give the same pairs, so (x, y) = (column, row) throughout.", "",
             "| lacuna | centroid_col_px (x) | centroid_row_px (y) | lacuna-table prints |", "|---|---|---|---|"]
    for r in d["lacuna_rows"]:
        lines.append(f"| {r['lacuna_id']} | {r['centroid_col_px']:.1f} | {r['centroid_row_px']:.1f} | "
                     f"({r['centroid_col_px']:.0f},{r['centroid_row_px']:.0f}) |")
    C.write_text(OUT / "coordinates.md", "\n".join(lines) + "\n")


def _fast_one(args) -> dict:
    """Fast copies against the pipeline functions for one image at one
    scale of t_hi."""
    import lacunae
    from scipy import ndimage as ndi
    path_str, scale = args
    p = Path(path_str)
    d = C.load(p)
    if scale == 1.0:
        mask = d["topmask"]
        ws_ref, lab_ref = d["ws_labels"], d["labels"]
    else:
        mask = C.lacuna_mask_at(d["channel"], d["t_hi"] * scale)
        ws_ref = lacunae.watershed_split(mask)
        lab_ref = lacunae.merge_shallow_splits(ws_ref, mask, ndi.distance_transform_edt(mask))
    t0 = time.time()
    ws = C.watershed_fast(mask)
    lab = C.merge_fast(ws, mask, ndi.distance_transform_edt(mask))
    return {"image": C.short(p), "t_hi_scale": scale,
            "watershed_identical": bool(np.array_equal(ws, ws_ref)),
            "merge_identical": bool(np.array_equal(lab, lab_ref)),
            "fast_s": round(time.time() - t0, 2)}


def cmd_fastcheck() -> None:
    path = OUT / "fast_copies_check.csv"
    if path.is_file():
        print(path.read_text())
        return
    jobs = [(str(p), 1.0) for p in C.IMAGE_PATHS]
    jobs += [(str(C.image_path(n)), s) for n in ("542_z06", "543-2", "682_z29") for s in (0.9, 1.1)]
    with ProcessPoolExecutor(max_workers=8) as ex:
        rows = list(ex.map(_fast_one, jobs))
    df = pd.DataFrame(rows)
    C.write_csv(path, df)
    print(df.to_string(index=False))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    item = "0.2"
    ok = C.run_item(item, {"build": cmd_build, "verify": cmd_verify, "fastcheck": cmd_fastcheck}[cmd])
    sys.exit(0 if ok else 1)
