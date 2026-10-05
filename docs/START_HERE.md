# Start here

**What this is.** lcn-quant measures the osteocyte lacuno-canalicular network in 2D confocal sections of
mouse bone (red channel). Feature 1 finds and measures the lacunae. Feature 2 traces the canalicular
network as a one-pixel skeleton and measures it per lacuna and per field. The headline measures are
roots per cell, ring length 30 px and field length density. Everything is **pre-validation** (no
comparison with manual counts yet) and in **pixel units** (the images carry no calibration). The data
are 8 wild-type sections, which are sections of 3 or 4 fields.

## What each folder holds

| folder | contents |
|---|---|
| `src/` | the pipeline: `lacunae.py` (feature 1), `canaliculi.py` (feature 2), `diagnostics.py` (every check, as subcommands) |
| `config.py` | paths, shared settings and the switches (all off) |
| `data/WT/` | the 8 input images |
| `results/` | the default output: one folder per image and `summary_table.xlsx` / `.csv`; the reference for every check |
| `results_experiments/` | experiments and checks; map: `results_experiments/INDEX.md` |
| `experiments/` | the scripts behind `results_experiments/`, and the progress files of each run |
| `figures/` | the figure code (`make_figures.py`), captions and review notes |
| `figures_out/` | the figures; map: `figures_out/INDEX.md` |
| `docs/` | the method and the reports |
| `archive/` | earlier scripts and analyses, never used by the code |

## What to read, in this order

1. `README.md`: how to run the pipeline, the measures and the results table.
2. `docs/METHODS.md`: every step and parameter with its origin, limitations and decisions.
3. `docs/reports/OVERNIGHT_REPORT.md`: the experiments (artefact, thresholds, lacuna audits, size confound,
   density, repeatability) and the Decisions needed.
4. `docs/reports/FIXES_REPORT.md`: the switches, new checks and the first figures.
5. `docs/reports/FIGURES_V2_REPORT.md`: the new network overlay and the figure fixes.
6. `figures_out/INDEX.md` and `results_experiments/INDEX.md`, to find a figure or a result.

## History

All work was merged into `main` on 2026-10-05 by the merge commit `c8e6954`. No side branch is in use:
`canaliculi-v2` and `figures-v2` still exist on GitHub and are fully merged. The old work is kept as
tags: `archive-before-cleanup`, `archive-before-cleanup-canaliculi-v2-fixes`, `archive-before-cleanup-main`,
`archive-before-cleanup-presentation-prep`, `before-canaliculi-v2`, `main-before-merge`,
`main-before-cleanup`, `canaliculi-v2-final`, `figures-v2-final`, `publication-fixes-final` and
`overnight-fixes-final`. `main-before-merge` is `main` as it was before the merge.

## The switches

In `config.py`. All are off by default; with all off, the pipeline gives `results/` exactly.

| switch | default | what it does when on |
|---|---|---|
| `NARROW_CRUMB_RULE` | `False` | a dropped watershed piece rejoins the one kept lacuna it touches if at least half of it lies inside that lacuna's convex hull (changes only 543_3 (877,545)) |
| `FILL_ENCLOSED_HOLES_MAX_PX2` | `0` | fills holes enclosed by one kept lacuna up to this size (200 changes only 542_z06 (783,581)) |
| `BAND_FILTER_MIN_OPENING_SHARE` | `None` | rejects kept objects keeping less than this share of their area after a 5 px opening (0.515 removes the two band objects) |
| `FAST_LACUNA_STAGE` | `False` | bounding-box versions of two lacuna steps: identical labels, 15 to 25 times faster |

`PIXEL_SIZE_UM` is `None`, so every output stays in pixels. It must come from the acquisition record.

## Commands

From the repository root, with the project's Python (3.9, the venv):

```
python src/lacunae.py --dir data/WT                      # feature 1 into results/ (-o DIR for another folder)
python src/canaliculi.py --dir data/WT                   # feature 2 and the summary table
python src/diagnostics.py reference-check                # must PASS: 62.33 / 27.41 / 21 on 543-2
python src/diagnostics.py regression                     # every number against results/, tolerance 0
python src/diagnostics.py switch-check                   # what each switch changes
python -u figures/make_figures.py all                    # every figure, thumbnails and INDEX.md
python -u figures/make_figures.py check                  # drawn numbers against results/
```

Do not write a new `results/` unless a switch is adopted on purpose; `results/` is the reference that
`regression` compares with.
