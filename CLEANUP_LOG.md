# Cleanup log, 2026-09-30

**Paths.** Written before the results layout of 2026-10-05, which moved every result and figure into `results/` (guide: [results/README.md](results/README.md); every old and new path: [results/RENAMES.csv](results/RENAMES.csv)). Links pinned to a commit keep the old paths.

The repository was reduced to two feature files, one diagnostics file,
clean results and one guide, with everything else moved to `archive/`.
Every step's check passed, so nothing was reverted. Outputs are
pre-validation and in pixel units.

## Safety net

Annotated tags, pushed before any change, on the state of every branch:
`archive-before-cleanup` (tip of presentation-prep, which contains all
work), plus `archive-before-cleanup-main`, `-canaliculi-v2-fixes` and
`-presentation-prep`. Checking out `archive-before-cleanup` restores the
repository exactly as it was.

Before any code changed, the default pipeline was run on all 8 images and
every number was saved in a snapshot outside the repository: lacuna
counts, per-lacuna shape, roots, ring lengths, owned length, edge count,
field metrics and bridges, 1960 numbers in all. 543-2 with
`--no-reach-cap` read 62.33 / 27.41 px / 21 bridges.

## What was done

| step | commits | check |
|---|---|---|
| 1. Default path merged into `src/lacunae.py` and `src/canaliculi.py` | 908b818 | 1960 of 1960 numbers identical to the snapshot at tolerance 0; 32 of 32 output images pixel-identical; 543-2 reads 62.33 / 27.41 / 21 |
| 2. `src/diagnostics.py`: reference-check, compare-outputs, reach, lacuna-table, sanity | 35fbb18 | each run once; compare-outputs also caught a planted difference (exit code 1) |
| `config.py` pruned to the paths and settings the code reads | c9d13c3 | a full regeneration with it matched the snapshot exactly |
| 3. Outputs regenerated into `results/<image>/` plus the summary table | cf2cc7c | 1960 of 1960 numbers identical to the snapshot |
| 3. Old results folders moved to `archive/results_old/` | 0cdc8ee | 772 renames, nothing deleted |
| 4. Old scripts moved to `archive/src/` and `archive/diagnostics/` | 0c7b516 | 26 renames; reference-check passes without them |
| 4. Reports, PROGRESS.md, DECISIONS_NEEDED.md, old README moved | 465bb56 | 25 renames |
| 5. New `README.md` and `docs/METHODS.md` | 2c70a85 | README about 700 words |
| 6. `.gitignore` reduced to venv, caches and .DS_Store | 906fbf9 | tree clean |
| 6. All branches merged into main and pushed | fast-forward | every branch and tag on GitHub matches the local ref |

Final check on main: `reference-check` PASS 3 of 3; `compare-outputs`
of `results/` against the snapshot MATCH on 1960 numbers. A fresh clone
from GitHub ran both features on 543-2: all JSON and PNG outputs were
byte-identical to the committed ones. The xlsx files differed only in
their save timestamps: their cell contents were identical. The reference
check passed inside the clone.

## What was archived

Everything below keeps its folder structure under `archive/`, moved with
`git mv` so each file's history follows it:
- `src/`: the 9 scripts the new files were built from or that held
  alternatives (v2, canaliculi_v1, gap_bridging, exclusion_mask,
  count_lacunae, v3 and hybrid detectors, adjacent-pair merge,
  presentation builder)
- `diagnostics/`: 17 diagnostic and tool scripts
- `reports/`: every round's reports, including the round 3 overnight log
  and summary
- `docs/`: PROGRESS.md and DECISIONS_NEEDED.md
- `results_old/`: the old lacunae, canaliculi, candidates, diagnostics and
  presentation folders (PIPELINE_NOTE.md is in `results_old/presentation/`)
- `README_before_cleanup.md`, and `config_before_cleanup.py` (a copy of
  the configuration before pruning)

## Repository size

| | before | after |
|---|---|---|
| tracked files | 833 files, 337.6 MB | 907 files, 363.5 MB (archive 314.5, results 25.8, data 23.1, code and docs under 0.2) |
| local `.git` | 245 MB | 245 MB |
| fresh clone `.git` | not measured | 241 MB |

The history barely grew because most regenerated images are byte-identical
to archived ones, and git stores identical content once. No file is near
GitHub's 100 MB limit (the largest is 3.0 MB), so Git LFS was not needed.

## Deviations, skipped items and notes

- **No file deleted.** 109 groups of byte-identical tracked files (250
  redundant copies) exist, all inside `archive/` or pairing an archived
  output with its new copy. They were kept: git stores each content once,
  so deleting them saves no space, and archived reports cite them by path.
  `git ls-files -s | sort` lists them by blob hash.
- **No `bridges.png`.** The results layout lists five canaliculi files, so
  the bridge overlay is no longer written. Each bridge (ends, gap, angle,
  signal) is recorded in `canaliculi_measurements.json` instead.
- **The sanity report moved** from the end of a canaliculi folder run into
  `python src/diagnostics.py sanity`.
- **Renamed output keys**, with units: for example `area_px2`,
  `edge_count` (was canaliculi_count), `mean_edge_length_px`. The
  duplicate `total_length_px` column was dropped: it always equalled
  `owned_length_px`. Values are unchanged.
- **`.claude/settings.local.json` is not tracked.** The repository's
  `.gitignore` does not exclude it; the user's global git ignore file does
  (`C:\Users\aahmed\.config\git\ignore`), which was left alone because it
  applies to every repository. `git add -f .claude/settings.local.json`
  would add it. `.claude/settings.json` is tracked.
- **code_key:** no such file exists. With the rule gone, one placed in the
  repository would be committed by `git add -A`.
- An Excel lock file (`~$summary_table.xlsx`) seen at the start was never
  staged and disappeared once Excel closed.
- Temporary files: the snapshot and the fresh clone were deleted. A folder
  for a planted-difference test of compare-outputs was also deleted. Other
  working files (including the Step 1 verification output) remain in the
  session's temporary folder outside the repository.
