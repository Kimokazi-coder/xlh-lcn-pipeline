"""One-time reorganization of results/canaliculi/ -- MOVES FILES ONLY.

canaliculi_v1.py writes per-image outputs to
results/canaliculi/<image_stem_with_underscores>/. A run with the default
settings (ASSIGNMENT_METHOD="graph", PREPROCESS_MODE="tophat",
COUNT_MODE="edge") writes unsuffixed filenames; a comparison run using
--method / --preprocess / --count-mode suffixes every filename (_euclidean,
_pre-none, _count-path, and combinations). Over several comparison runs
that leaves the default outputs buried among a dozen variants.

This script pushes every non-default file down one level, so each image
folder shows the current default result at the top and keeps the
comparison runs alongside it:

    results/canaliculi/<image>/
        verification.png          <- default run, kept at top level
        canaliculi_mask.png
        skeleton.png
        measurements.xlsx
        measurements.json
        all_method_results/       <- everything else moved here
            verification_euclidean.png
            measurements_pre-none.json
            ...

Safety rules, in order of importance:
  * Nothing is ever deleted or overwritten. Files are moved, never copied
    then removed.
  * If any planned destination already exists, the whole run aborts
    before moving anything and reports the collisions.
  * Directories are never touched -- an existing subfolder inside an
    image folder is left exactly as it is, contents included.
  * Only results/canaliculi/ is touched. Nothing outside it, nothing in
    data/.
  * Idempotent: running it again after a successful run finds nothing to
    do, because the five names kept at the top level are never moved.

Usage:
    python diagnostics/tools/tidy_canaliculi_results.py --dry-run   # print the plan only
    python diagnostics/tools/tidy_canaliculi_results.py             # actually move
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import config  # noqa: E402

CANALICULI_DIR = config.CANALICULI_DIR

# Subfolder that non-default (suffixed) outputs are moved into. Must match
# canaliculi_v1.COMPARISON_SUBDIR, which is where new comparison runs write.
COMPARISON_SUBDIR = "all_method_results"

# The five files a default run produces. These, and only these, stay at
# the top level of an image folder; every other FILE there is moved.
KEEP_AT_TOP_LEVEL = frozenset(
    {
        "verification.png",
        "canaliculi_mask.png",
        "skeleton.png",
        "measurements.xlsx",
        "measurements.json",
    }
)


def plan_moves(root: Path) -> list[tuple[Path, Path]]:
    """Every (source, destination) pair this run would perform, in a
    stable order. Only files directly inside an image folder are
    considered -- subfolders are skipped entirely, contents and all."""
    moves: list[tuple[Path, Path]] = []
    for image_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for entry in sorted(image_dir.iterdir()):
            if entry.is_dir():
                continue  # pre-existing subfolder, leave it alone
            if entry.name in KEEP_AT_TOP_LEVEL:
                continue
            moves.append((entry, image_dir / COMPARISON_SUBDIR / entry.name))
    return moves


def find_collisions(moves: list[tuple[Path, Path]]) -> list[tuple[Path, Path]]:
    """Planned moves whose destination already exists. Checked for the
    whole plan up front so a collision aborts before anything has moved,
    rather than halfway through."""
    return [(src, dst) for src, dst in moves if dst.exists()]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Move non-default canaliculi outputs into per-image "
        f"{COMPARISON_SUBDIR}/ subfolders. Moves only; never deletes or overwrites."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print every planned move and exit without touching anything.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=CANALICULI_DIR,
        help=f"Directory of per-image output folders (default: {CANALICULI_DIR}).",
    )
    args = parser.parse_args()

    if not args.root.is_dir():
        raise NotADirectoryError(f"No such directory: {args.root}")

    moves = plan_moves(args.root)
    if not moves:
        print(f"Nothing to move -- every file under {args.root} is already in place.")
        return

    collisions = find_collisions(moves)
    if collisions:
        print(f"ABORTED: {len(collisions)} destination(s) already exist. Nothing was moved.")
        for src, dst in collisions:
            print(f"  {src.relative_to(args.root)}  ->  {dst.relative_to(args.root)}  [EXISTS]")
        print("\nResolve these by hand (rename or relocate the existing file), then re-run.")
        raise SystemExit(1)

    label = "PLANNED" if args.dry_run else "MOVED"
    current_dir = None
    for src, dst in moves:
        if src.parent != current_dir:
            current_dir = src.parent
            print(f"\n{current_dir.relative_to(args.root)}/")
        if not args.dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
        print(f"  [{label}] {src.name}  ->  {COMPARISON_SUBDIR}/{dst.name}")

    n_dirs = len({src.parent for src, _dst in moves})
    print(f"\n{len(moves)} file(s) across {n_dirs} image folder(s).")
    if args.dry_run:
        print("Dry run -- nothing was moved. Re-run without --dry-run to apply.")


if __name__ == "__main__":
    main()
