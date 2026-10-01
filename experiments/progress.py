"""Update experiments/PROGRESS.md.

Usage (from the repo root):
    python experiments/progress.py init
    python experiments/progress.py set ID STATUS [--sha SHA] [--note TEXT]
    python experiments/progress.py next ID "what is left in it"
    python experiments/progress.py show

STATUS is one of TODO, DONE, PARTIAL, FAILED, SKIPPED. `set` also stamps
the "last update" line. Every write is atomic.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import EXP_DIR, write_text  # noqa: E402

PROGRESS = EXP_DIR / "PROGRESS.md"
STATUSES = {"TODO", "DONE", "PARTIAL", "FAILED", "SKIPPED"}

ITEMS = [
    ("0.1", "Branch, experiments/README.md and PROGRESS.md"),
    ("0.2", "Default-result cache on all 8 images, and timing"),
    ("1.1", "TIFF tags of all 8 images"),
    ("1.2", "2D FFT peaks and row and column banding, raw and preprocessed"),
    ("1.3", "Axis-aligned skeleton runs; 682_z08 lattice crops; where the lattice comes from"),
    ("2.1", "Which stage rejects the visibly missed bodies"),
    ("2.2", "t_hi and t_lo against image brightness statistics"),
    ("2.3", "Quick sensitivity, both cuts x0.9 and x1.1, on 3 images"),
    ("3.1", "Crumb loss audit: kept lacuna against its pre-watershed component"),
    ("3.2", "Saddle audit: straight line against widest path"),
    ("3.3", "Band objects: minor axis, flagged overlap, solidity"),
    ("3.4", "Tails and serrated edges: opening r 2, 3, 4 (lacuna level)"),
    ("3.5", "Unfilled holes up to 200 px^2 (lacuna level)"),
    ("4.1", "Size confound: ring area, in-frame fraction, normalised measures"),
    ("5.1", "Field density three ways"),
    ("5.2", "Green and blue channels; draft bone ROI"),
    ("5.3", "542_z06 vertical trace near x 525, y 590 to 900"),
    ("6.1", "Repeatability across matched cells; field groups from data"),
    ("7.1", "Draft docs/OVERNIGHT_REPORT.md"),
    ("1.4", "Notch filter variant"),
    ("2.4", "Full threshold sensitivity grid on all 8 images"),
    ("3.6", "Network-level effect of variants 3.1 to 3.5"),
    ("3.7", "Before and after crops for the worst cases"),
    ("5.4", "ROI overlays for all 8 images; per-image ROI support"),
    ("7.2", "Final report, METHODS section, checks, ALL DONE"),
]

HEADER = "| id | description | status | commit SHA | note |"
SEP = "|---|---|---|---|---|"


def now() -> str:
    return time.strftime("%Y-%m-%d %H:%M")


def parse() -> tuple[list[str], list[list[str]]]:
    lines = PROGRESS.read_text(encoding="utf-8").splitlines()
    top, rows = [], []
    in_table = False
    for line in lines:
        if line.strip() == HEADER:
            in_table = True
            continue
        if in_table and line.strip() == SEP:
            continue
        if in_table and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            rows.append(cells)
        elif not in_table:
            top.append(line)
    return top, rows


def render(top: list[str], rows: list[list[str]]) -> str:
    out = list(top)
    out.append(HEADER)
    out.append(SEP)
    for r in rows:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out) + "\n"


def set_top(top: list[str], key: str, value: str) -> list[str]:
    pat = re.compile(rf"^{re.escape(key)}:")
    for i, line in enumerate(top):
        if pat.match(line):
            top[i] = f"{key}: {value}"
            return top
    top.insert(2, f"{key}: {value}")
    return top


def cmd_init(_args) -> None:
    if PROGRESS.exists():
        print("PROGRESS.md exists; not overwritten.")
        return
    top = [
        "# Overnight progress",
        "",
        f"last update: {now()}",
        "next action: 0.1 create the branch, README and this file.",
        "",
        "Status values: TODO, DONE, PARTIAL, FAILED, SKIPPED. The commit SHA is the commit that holds the",
        "item's code and outputs. UNPUSHED after an id means its push failed and is retried at the next commit.",
        "",
    ]
    rows = [[i, d, "TODO", "", ""] for i, d in ITEMS]
    write_text(PROGRESS, render(top, rows))


def cmd_set(args) -> None:
    if args.status not in STATUSES:
        raise SystemExit(f"bad status {args.status}")
    top, rows = parse()
    for r in rows:
        if r[0] == args.id or r[0] == args.id + " UNPUSHED":
            r[2] = args.status
            if args.sha is not None:
                r[3] = args.sha
            if args.note is not None:
                r[4] = args.note.replace("|", "/")
            break
    else:
        raise SystemExit(f"no row {args.id}")
    top = set_top(top, "last update", now())
    write_text(PROGRESS, render(top, rows))


def cmd_next(args) -> None:
    top, rows = parse()
    top = set_top(top, "last update", now())
    top = set_top(top, "next action", f"{args.id} {args.text}")
    write_text(PROGRESS, render(top, rows))


def cmd_unpushed(args) -> None:
    top, rows = parse()
    for r in rows:
        base = r[0].replace(" UNPUSHED", "")
        if base == args.id:
            r[0] = base + (" UNPUSHED" if args.on else "")
    write_text(PROGRESS, render(top, rows))


def cmd_show(_args) -> None:
    print(PROGRESS.read_text(encoding="utf-8"))


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").set_defaults(func=cmd_init)
    s = sub.add_parser("set")
    s.add_argument("id")
    s.add_argument("status")
    s.add_argument("--sha")
    s.add_argument("--note")
    s.set_defaults(func=cmd_set)
    n = sub.add_parser("next")
    n.add_argument("id")
    n.add_argument("text")
    n.set_defaults(func=cmd_next)
    u = sub.add_parser("unpushed")
    u.add_argument("id")
    u.add_argument("--off", dest="on", action="store_false")
    u.set_defaults(func=cmd_unpushed)
    sub.add_parser("show").set_defaults(func=cmd_show)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
