# Publication fixes report, 2026-10-02

**DRAFT (pass 1).** Sections marked *pending* are filled in pass 2 and 3.

**Pre-validation, pixel units.** Branch `publication-fixes`, started from `overnight-fixes` (ef04398).
This session turns the findings of `docs/OVERNIGHT_REPORT.md` into the pipeline behind switches that
are off by default, adds subcommands, and makes publication figures. With every switch off, the
pipeline reproduces `results/` exactly: `python src/diagnostics.py regression` passed before every
push, together with `reference-check` (62.33, 27.41 px, 21 bridges) and a clean `git status results/`.
Nothing was written into `results/`.

## Pass 1

**A2 Output folder.** `-o DIR` is a short name for the existing `--out DIR` of both features; the
default stays `results/`, and a folder run writes the summary table there too. A check run into the
ignored cache gave json files and a summary row identical to `results/` for 543-2.
(`results_experiments/fixes/A2_output_option.md`)

**A6 Regression.** `python src/diagnostics.py regression` regenerates all 8 images in parallel into
`results_experiments/_cache/regression/` and compares every json field and every summary cell with
`results/` at tolerance 0, ignoring the provenance block. It passed before any other change: 3861
numbers, 0 differ, about 2 minutes. It catches planted differences. (`results_experiments/fixes/A6_regression.md`)

**F0 Figure style.** `figures/make_figures.py` holds one shared style: a display window fixed for the
whole dataset (1st and 99.8th percentile of the pooled red channel: 20 to 255 grey levels), Arial at 7
to 9 pt for a 180 mm figure, embedded TrueType fonts in the PDF, PNG at 300 dpi, interior lacunae cyan
and frame-edge lacunae yellow at 0.7 pt, the skeleton white over the image dimmed to 60%, roots as
yellow dots, a 200 px scale bar (uncalibrated).

**F1a Per-image figure, 543-2** (`figures_out/F1_543-2.png` and `.pdf`). A raw red channel; B outlines
with numbers and "n = 12 lacunae (12 interior)"; C skeleton with a 3x inset of lacuna 4, chosen by rule
(roots closest to the interior median of 7.5; 7 and 8 tie, smallest id wins), roots as dots. Review
round 1 moved the numbers beside the lacunae. (`figures/REVIEW.md`)

**A1 Provenance.** Every json output ends with a `provenance` block: git commit, dirty flag (tracked
files), versions of python, numpy, scipy, scikit-image, skan, networkx, pandas, and a hash of the
non-path config values. No timestamps. `requirements.txt` pins the installed versions.
(`results_experiments/fixes/A1_provenance.md`)

**A3 Normalised measures.** Eight columns appended to the per-lacuna rows and the summary table:
perimeter, ring area $A_{30}$ and $A_{60}$, in-frame fractions, ring density $L_r / A_r$ and roots per
100 px of perimeter. Existing columns unchanged (regression PASS); the 784 new per-lacuna values equal
those of `experiments/task4_size.py`. Documented in `docs/METHODS.md` section 9.

## Pass 2

*Pending:* A4 switches and switch-check, A5 fast lacuna stage, B1 blinding, B2 sensitivity, B3 field
summary, F1b to F6 figures.

## Decisions needed

*Pending.*
