"""B1 test: no original name in any output of a run on a coded folder, and
the unblinded numbers equal the normal run.

    python -u experiments/fixes_b1_blind_test.py KEY_PATH

Expects (made beforehand, see results_experiments/fixes/B1_blinding.md):
    results_experiments/_cache/blind/coded/          coded images (blind)
    results_experiments/_cache/blind/out/            lacunae.py and canaliculi.py run on them
    results_experiments/_cache/blind/run_*.log       the logs of those runs
    results_experiments/_cache/regression/           regression run, current config (normal names)
Writes results_experiments/_cache/blind/unblinded.csv and prints the report.
PRE-VALIDATION, PIXEL units.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import diagnostics as D  # noqa: E402

BLIND = ROOT / "results_experiments" / "_cache" / "blind"
NORMAL = ROOT / "results_experiments" / "_cache" / "regression"


def search_terms(key_rows: list) -> list:
    terms = set()
    for r in key_rows:
        name = r["original_name"]
        stem = Path(name).stem
        clean = "_".join(stem.split())
        terms |= {name, stem, clean}
        for part in re.split(r"[ _]+", stem):
            if len(part) >= 4:  # distinctive parts such as z06c1-2, 543-2, 543_3
                terms.add(part)
        terms.add(Path(r["original_folder"]).name)
    return sorted(terms)


def texts_of(path: Path) -> list:
    """(where, text) pieces to search in one output file."""
    if path.suffix == ".xlsx":
        with zipfile.ZipFile(path) as z:
            return [(f"{path}:{n}", z.read(n).decode("utf-8", "replace")) for n in z.namelist()]
    if path.suffix == ".png":
        data = path.read_bytes()
        # PNG text chunks only; image data is compressed binary.
        chunks = re.findall(rb"(?:tEXt|iTXt|zTXt)(.{0,400})", data)
        return [(str(path), c.decode("latin-1")) for c in chunks]
    if path.suffix in (".tif", ".tiff"):
        import tifffile
        with tifffile.TiffFile(path) as t:
            return [(str(path), " ".join(str(tag.value) for tag in t.pages[0].tags.values()))]
    return [(str(path), path.read_text(encoding="utf-8", errors="replace"))]


def main() -> int:
    key_path = Path(sys.argv[1])
    with open(key_path, newline="") as f:
        key = list(csv.DictReader(f))
    terms = search_terms(key)
    files = [p for p in (BLIND / "out").rglob("*") if p.is_file()]
    files += sorted(BLIND.glob("run_*.log")) + sorted((BLIND / "coded").glob("*"))
    hits = []
    for p in files:
        names_in_path = [t for t in terms if t in str(p.relative_to(BLIND))]
        hits += [(str(p), t, "file path") for t in names_in_path]
        for where, text in texts_of(p):
            for t in terms:
                pattern = r"\bWT\b" if t == "WT" else re.escape(t)
                if re.search(pattern, text):
                    hits.append((where, t, "content"))
    print(f"Searched {len(files)} files (json, xlsx parts, csv, png text chunks, tif tags, logs) for "
          f"{len(terms)} terms: {', '.join(terms)}")
    print(f"Original names found: {len(hits)}")
    for h in hits[:20]:
        print("  HIT", *h)

    # Unblind and compare with the normal run.
    out_csv = BLIND / "unblinded.csv"
    subprocess.run([sys.executable, str(ROOT / "src" / "diagnostics.py"), "unblind", "-s",
                    str(BLIND / "out" / "summary_table.csv"), "-k", str(key_path), "-o", str(out_csv)], check=True)
    with open(out_csv, newline="") as f:
        unblinded = {r["original_name"]: r for r in csv.DictReader(f)}
    with open(NORMAL / "summary_table.csv", newline="") as f:
        normal = {r["file"]: r for r in csv.DictReader(f)}
    skip = {"image", "file", "code", "original_name", "original_folder"}
    cells = diffs = 0
    for name, row in unblinded.items():
        ref = normal[name]
        for col, value in ref.items():
            if col in skip:
                continue
            cells += 1
            if row.get(col) != value:
                diffs += 1
                print("  SUMMARY DIFF", name, col, value, row.get(col))
    json_fields = json_diffs = 0
    code_of = {r["original_name"]: r["code"] for r in key}
    for name, code in code_of.items():
        clean = "_".join(Path(name).stem.split())
        for fname in ("lacunae.json", "canaliculi_measurements.json"):
            a = json.load(open(NORMAL / clean / fname))
            b = json.load(open(BLIND / "out" / code / fname))
            for d in (a, b):
                d.pop("provenance", None)
                d.pop("image", None)
            fa, fb = D.flatten_all(a), D.flatten_all(b)
            json_fields += len(fa)
            bad = [k for k in fa if k not in fb or not D._equal(fa[k], fb[k])]
            json_diffs += len(bad)
            for k in bad[:3]:
                print("  JSON DIFF", name, fname, k, fa[k], fb.get(k))
    print(f"Unblinded summary: {cells} cells compared with the normal run, {diffs} differ.")
    print(f"Per-image json: {json_fields} fields compared (image name and provenance excluded), {json_diffs} differ.")
    ok = not hits and diffs == 0 and json_diffs == 0
    print(f"{'PASS' if ok else 'FAIL'}: blinding test.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
