"""One-time reorganization of results/, reports/ and the loose docs at the
repo root. MOVES FILES ONLY -- nothing is deleted or overwritten.

The principle is the one already used inside results/canaliculi/<image>/:
what the CURRENT DEFAULT pipeline produces sits at the top of its folder,
and everything else -- comparison runs, superseded versions, experimental
detectors, diagnostics -- sits one level down, grouped by what it is.

Target layout:

    results/
      canaliculi/<image>/        5 default files (already correct)
          all_method_results/    non-default settings (already correct)
      lacunae/<image>/           current default lacuna outputs
      candidates/
          lacunae_v3/            experimental detector, not in use
      diagnostics/
          phase0/  phase1/  phase2/  phase3/
          round2/step2/
    reports/
      phase0_1/  overnight/      text reports, one folder per run
    docs/
      PROGRESS.md  DECISIONS_NEEDED.md      (README.md stays in the root)

Three departures from the layout as proposed, each forced by what the
inventory actually found:

  * NO archive/. It was meant to hold the superseded count_lacunae.py (v1)
    outputs. There are none: v1 writes <stem>_overlay.png and
    <stem>_lacunae.csv directly under results/, and results/ has no loose
    files at all, so v1 has never been run against this data. An empty
    archive/ would imply something is stored there.
  * results/diagnostics/canaliculi_v2/ is SPLIT, not moved. Despite the
    name it holds both Phase 0 material (per-image crops, phase0_report)
    and Phase 1 material (phase1_exclusion_report, _channel_evidence/, the
    blue-channel check that decided the second channel was not a usable
    exclusion source). Moving it whole would carry that confusion forward.
  * NO candidates/lacunae_hybrid/ and NO reports/round2/. Neither exists
    yet -- they belong to round-2 steps that have not been run. Empty
    folders are not created.

Text reports move to reports/<run>/, one folder per run: phase0_1/ for the
interactive Phase 0-1 session, overnight/ for the Phase 2-4 run. The two
Phase 0-1 reports are currently filed under results/diagnostics/, which is
the inconsistency this fixes.

Safety, in order of importance:
  * Nothing is deleted or overwritten. Files are moved, never copied then
    removed.
  * If any planned destination already exists, the whole run aborts before
    moving anything and lists the collisions.
  * data/ is never read from or written to. Asserted, not just intended.
  * src/ is never touched.
  * Idempotent: a second run finds nothing to do.

Usage:
    python src/reorganize_outputs.py --dry-run   # print the plan only
    python src/reorganize_outputs.py             # actually move
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

ROOT = config.PROJECT_ROOT

# (source, destination, why). A source that is a directory moves its whole
# tree, file by file, so a collision on any single file is caught. A source
# that does not exist is skipped silently -- that is what makes the script
# idempotent and safe to re-run.
MOVES: list[tuple[str, str, str]] = [
    (
        "results/count",
        "results/lacunae",
        "current default lacuna outputs; 'count' did not say what it held",
    ),
    (
        "results/count_v3_candidate",
        "results/candidates/lacunae_v3",
        "experimental detector, LACUNA_SOURCE='v2' is still the default",
    ),
    (
        "results/diagnostics/canaliculi_v2/_channel_evidence",
        "results/diagnostics/phase1/_channel_evidence",
        "the blue-channel check; it was Phase 1 evidence, not Phase 0",
    ),
    (
        "results/diagnostics/canaliculi_v2/phase0_report.txt",
        "reports/phase0_1/phase0_report.txt",
        "text report; reports/ is where text reports live",
    ),
    (
        "results/diagnostics/canaliculi_v2/phase1_exclusion_report.txt",
        "reports/phase0_1/phase1_exclusion_report.txt",
        "text report; reports/ is where text reports live",
    ),
    (
        "results/diagnostics/canaliculi_v2",
        "results/diagnostics/phase0",
        "what remains after the split above is the Phase 0 per-image crops",
    ),
    (
        "results/diagnostics/step2",
        "results/diagnostics/round2/step2",
        "round-2 step 2, kept apart from the Phase 1-4 numbering",
    ),
    ("PROGRESS.md", "docs/PROGRESS.md", "planning note; README.md stays in the root"),
    ("DECISIONS_NEEDED.md", "docs/DECISIONS_NEEDED.md", "planning note"),
]

# Never touched, for any reason.
FORBIDDEN_PREFIXES = ("data", "src", "venv", ".git")


def _check_not_forbidden(relative: Path, label: str) -> None:
    head = relative.parts[0] if relative.parts else ""
    if head in FORBIDDEN_PREFIXES:
        raise SystemExit(f"REFUSED: {label} path {relative} is under {head}/, which is never touched.")


def plan_moves() -> list[tuple[Path, Path, str]]:
    """Every (source_file, destination_file, why) this run would perform.

    MOVES is ordered most-specific-first and EARLIER ENTRIES WIN. That
    matters because results/diagnostics/canaliculi_v2/ is split rather than
    moved whole: three entries pull specific things out of it, and a fourth
    sweeps up what remains. Without claiming, that fourth entry would plan
    a second move for files the first three already claimed -- and because
    the whole plan is built before anything moves, the duplicate would not
    show up as a destination collision. The dry run caught exactly this."""
    moves: list[tuple[Path, Path, str]] = []
    claimed: set[Path] = set()
    for src_rel, dst_rel, why in MOVES:
        src_path, dst_path = Path(src_rel), Path(dst_rel)
        _check_not_forbidden(src_path, "source")
        _check_not_forbidden(dst_path, "destination")

        source, destination = ROOT / src_path, ROOT / dst_path
        if not source.exists():
            continue  # already moved, or never existed -- both fine
        if source.is_file():
            if source not in claimed:
                moves.append((source, destination, why))
                claimed.add(source)
            continue
        for item in sorted(source.rglob("*")):
            if item.is_file() and item not in claimed:
                moves.append((item, destination / item.relative_to(source), why))
                claimed.add(item)
    return moves


def find_collisions(moves: list[tuple[Path, Path, str]]) -> list[tuple[Path, Path]]:
    """Planned moves whose destination already exists on disk. Checked for
    the whole plan up front, so a collision aborts before anything has
    moved rather than halfway through."""
    return [(src, dst) for src, dst, _why in moves if dst.exists()]


def find_internal_conflicts(moves: list[tuple[Path, Path, str]]) -> list[tuple[Path, Path]]:
    """Two planned moves writing to the SAME destination, or reading the
    same source twice. Neither shows up as an on-disk collision, because
    the whole plan is built before anything moves, so they are checked
    separately."""
    seen_dst: dict[Path, Path] = {}
    conflicts = []
    for src, dst, _why in moves:
        if dst in seen_dst:
            conflicts.append((src, dst))
        seen_dst[dst] = src
    return conflicts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reorganize results/, reports/ and the loose root docs. "
        "Moves only; never deletes or overwrites; never touches data/ or src/."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print every planned move and exit without touching anything.",
    )
    args = parser.parse_args()

    moves = plan_moves()
    if not moves:
        print("Nothing to move -- the layout is already in place.")
        return

    conflicts = find_internal_conflicts(moves)
    if conflicts:
        print(f"ABORTED: {len(conflicts)} planned move(s) target the same destination. Nothing was moved.")
        for src, dst in conflicts:
            print(f"  {src.relative_to(ROOT)}  ->  {dst.relative_to(ROOT)}  [DUPLICATE]")
        raise SystemExit(1)

    collisions = find_collisions(moves)
    if collisions:
        print(f"ABORTED: {len(collisions)} destination(s) already exist. Nothing was moved.")
        for src, dst in collisions:
            print(f"  {src.relative_to(ROOT)}  ->  {dst.relative_to(ROOT)}  [EXISTS]")
        raise SystemExit(1)

    label = "PLANNED" if args.dry_run else "MOVED"
    current_reason = None
    for src, dst, why in moves:
        if why != current_reason:
            current_reason = why
            print(f"\n  # {why}")
        if not args.dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
        print(f"  [{label}] {src.relative_to(ROOT)}")
        print(f"        -> {dst.relative_to(ROOT)}")

    if not args.dry_run:
        # Remove directories left empty by the moves. This deletes no FILE
        # -- an empty directory is not content, and git does not track them
        # anyway. Anything still holding a file is left alone.
        for src_rel, _dst_rel, _why in MOVES:
            source = ROOT / src_rel
            if source.is_dir():
                for directory in sorted(source.rglob("*"), reverse=True):
                    if directory.is_dir() and not any(directory.iterdir()):
                        directory.rmdir()
                if not any(source.iterdir()):
                    source.rmdir()

    print(f"\n{len(moves)} file(s).")
    if args.dry_run:
        print("Dry run -- nothing was moved. Re-run without --dry-run to apply.")


if __name__ == "__main__":
    main()
