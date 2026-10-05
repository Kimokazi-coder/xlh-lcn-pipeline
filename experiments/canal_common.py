"""Shared helpers for the canaliculi-v2 experiments (experiments/canal_*.py).

Nothing here changes the pipeline: src/ is imported, never edited. Outputs
go to results_experiments/canal_v2/; caches to results_experiments/_cache/
canal_v2/ (git-ignored). PRE-VALIDATION, PIXEL units, (x, y) = (column, row).

The writers, image names and markdown helpers of experiments/common.py are
reused. Its default-result cache is not: it is keyed on the source of
src/canaliculi.py, which this branch extends, so this module keeps its own
cache keyed on src/lacunae.py, src/canaliculi.py and config.py.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
import canaliculi  # noqa: E402
import config  # noqa: E402
import lacunae  # noqa: E402
import quantification  # noqa: E402

OUT = C.OUT_ROOT / "canal_v2"
CACHE = C.OUT_ROOT / "_cache" / "canal_v2"
LOG_DIR = C.LOG_DIR


def src_hash() -> str:
    h = hashlib.sha256()
    for p in (C.ROOT / "src" / "lacunae.py", C.ROOT / "src" / "canaliculi.py", C.ROOT / "config.py"):
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def _key(overrides: dict | None) -> str:
    if not overrides:
        return "default"
    return "__".join(f"{k}={v}" for k, v in sorted(overrides.items()))


def pipeline(name: str, overrides: dict | None = None) -> dict:
    """canaliculi.analyse_image on one image with the fast lacuna stage
    (identical labels) and the config attributes in `overrides` set, cached.
    Returns the rows, summaries, field block, bridges and the arrays the
    experiments draw."""
    path = C.image_path(name)
    short = C.short(path)
    tag = _key(overrides)
    npz, js = CACHE / f"{short}__{tag}.npz", CACHE / f"{short}__{tag}.json"
    if npz.is_file() and js.is_file():
        meta = json.loads(js.read_text(encoding="utf-8"))
        if meta.get("src_hash") == src_hash() and meta.get("complete"):
            with np.load(npz) as z:
                meta.update({k: z[k] for k in z.files})
            meta["channel"] = lacunae.load_channel(path)[1]
            return meta
    saved = {k: getattr(config, k) for k in (overrides or {})}
    fast = config.FAST_LACUNA_STAGE
    config.FAST_LACUNA_STAGE = True
    try:
        for k, v in (overrides or {}).items():
            setattr(config, k, v)
        res = quantification.analyse_image(path)
    finally:
        config.FAST_LACUNA_STAGE = fast
        for k, v in saved.items():
            setattr(config, k, v)
    bridges = [{"from_row_col": [int(v) for v in b["from"]], "to_row_col": [int(v) for v in b["to"]],
                "gap_len_px": float(b["gap_len"]), "angle_deg": float(b["angle_deg"]),
                "min_signal_fraction": float(b["min_signal_fraction"]),
                "pixels_row": [int(v) for v in b["pixels"][0]], "pixels_col": [int(v) for v in b["pixels"][1]]}
               for b in res["bridges"]]
    meta = {"image": path.name, "short": short, "setting": tag, "src_hash": src_hash(),
            "t_hi": res["lacunae"]["t_hi"], "t_lo": res["t_lo"], "lacuna_rows": res["rows"],
            "cell_rows": res["rows"], "summary": res["summary"], "field": res["field"], "bridges": bridges,
            "complete": True}
    C.write_npz(npz, lacuna_id_map=res["lacuna_id_map"].astype(np.int32), skeleton=res["skeleton"],
                flagged=res["flagged"], candidate=res["candidate"])
    C.write_json(js, meta)
    meta.update({"lacuna_id_map": res["lacuna_id_map"].astype(np.int32), "skeleton": res["skeleton"],
                 "flagged": res["flagged"], "candidate": res["candidate"]})
    meta["channel"] = lacunae.load_channel(path)[1]
    return meta


def names() -> list[str]:
    return [C.short(p) for p in C.IMAGE_PATHS]


def interior(rows: list[dict]) -> list[dict]:
    return [r for r in rows if not r["on_border"]]
