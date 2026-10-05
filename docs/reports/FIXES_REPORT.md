# Publication fixes report, 2026-10-02

**Pre-validation, pixel units.** Branch `publication-fixes`, started from `overnight-fixes` (ef04398).
This session turned the findings of `docs/reports/OVERNIGHT_REPORT.md` into the pipeline behind switches that
are **off by default**, added diagnostics as subcommands of `src/diagnostics.py`, and made publication
figures. **No default changed**: with every switch off the pipeline reproduces `results/` exactly.
Before every push, `reference-check` passed (62.33 edges per cell, 27.41 px, 21 bridges), `regression`
passed (3861 numbers at tolerance 0, with the original and with the fast lacuna stage), and
`git status results/` was clean. Nothing was written into `results/`. There is no ground truth, so
nothing here claims to be more accurate, and no threshold was retuned. Which switches to turn on is
Karim's decision.

## Summary

- **Safety net.** `regression` regenerates all 8 images and compares 3861 numbers with `results/` at
  tolerance 0; it catches planted differences and now guards every change.
- **Three fixes from the overnight report, each behind a switch that is off:** the narrow crumb rule, the
  enclosed-hole fill and the band filter. `switch-check` shows each changes exactly the objects the
  overnight report predicted, and nothing else.
- **A fast lacuna stage** (switch, off) gives identical labels in 0.1 s instead of 22 to 79 s per image
  (453 s at a low cut). All 8 images regenerate in 8 s instead of 125 s.
- **Normalised measures** (perimeter, ring areas, in-frame fractions, ring densities $L_r / A_r$, roots
  per 100 px of perimeter) are appended as new columns; existing columns are unchanged.
- **Provenance** (git commit, dirty flag, library versions, config hash) in every json output, and a
  pinned `requirements.txt`.
- **New subcommands:** `regression`, `switch-check`, `fast-check`, `blind`, `unblind`, `sensitivity`,
  `field-summary`. Blinding passed a leak test: no original name in any output or log of a coded run,
  and the unblinded numbers equal the normal run.
- **Figures:** per-image figures for all 8 images, a contact sheet (also coded), a threshold sensitivity
  figure, a per-field plot and a supplementary figure of two switches, all with one fixed display window,
  embedded fonts and captions.

## What each item did

**A2 Output folder** (`results_experiments/fixes/A2_output_option.md`). `-o DIR` is a short name for the
existing `--out DIR` of both features; the default stays `results/`, and a folder run writes the summary
table into the same folder. A check run into the ignored cache matched `results/543-2` exactly.

**A6 Regression** (`A6_regression.md`). `python src/diagnostics.py regression` regenerates all 8 images
in parallel into `results_experiments/_cache/regression/` (git-ignored) and compares every json field
and every summary cell with `results/` at tolerance 0, ignoring the provenance block and counting new
fields separately. It passed before any other change, and caught a changed root count and a changed
last digit of a density planted in copies of the reference. Since A5 it runs twice: the current config,
then the same with `FAST_LACUNA_STAGE` on.

**A1 Provenance** (`A1_provenance.md`). Every `lacunae.json` and `canaliculi_measurements.json` ends with
`provenance`: `git_commit`, `git_dirty` (tracked files only), versions of python, numpy, scipy,
scikit-image, skan, networkx and pandas, and `config_hash` over every non-path setting of `config.py`
(listed in `config_hash_covers`). No timestamps. `requirements.txt` pins the installed versions of the
eleven packages the code uses, with Python 3.9.10 in a comment.

**A3 Normalised measures** (`docs/METHODS.md` section 9). Eight columns appended after all existing ones
in the per-lacuna rows and the `per_lacuna` sheet, and as interior means in the summary table:
`perimeter_px`, `ring_area_r30_px2`, `ring_area_r60_px2`, `in_frame_fraction_r30`,
`in_frame_fraction_r60`, `ring_density_r30`, `ring_density_r60`, `roots_per_100px_perimeter`. Defined as
in `experiments/task4_size.py`; all 784 per-lacuna values equal that script's. Regression PASS.

**A4 Switches and switch-check** (`A4_switch_check.md`). Three switches in `config.py`, all off, each
with a comment naming its evidence. `python src/diagnostics.py switch-check` turns each on alone,
regenerates all 8 images and lists every lacuna whose area, roots or ring 30 px change. The result
equals the overnight report's expectation in every case (table below). Nothing was adjusted.

**A5 Fast lacuna stage** (`A5_fast_stage.md`, `A5_fast_check.csv`). `FAST_LACUNA_STAGE` (off) selects
bounding-box versions of the watershed split and the shallow-split re-merge, ported from the overnight
experiments. `python src/diagnostics.py fast-check` compares the labels pixel for pixel on all 8 images
at $t_\mathrm{hi}$ scaled 0.8, 0.9, 1.0, 1.1 and 1.2: 40 of 40 identical. Timing: the lacuna stage takes
0.1 to 0.3 s instead of 9 to 453 s; 542_z06 runs in 2.8 s instead of 70.2 s; all 8 images regenerate
in 8 s instead of 125 s. Regression passes with it on.

**B1 Blinding** (`B1_blinding.md`). `blind -s SRC -o OUT -k KEY` copies the images as S001.tif,
S002.tif, ... in a random order, pixel data only, and writes the key (code, original name, folder,
seed, whether a constant alpha channel was dropped). It refuses a key path inside the repository, an
existing key, or a non-empty output folder, and prints no original name. A constant alpha channel is
dropped because it marked the one RGBA file (542_z06); after that all coded copies have the same shape
and tag set. `unblind -s SUMMARY -k KEY -o OUT` joins the key to a summary table. Test on the 8 WT
images: both features run on the coded folder from the command line; 76 output files and logs (json,
csv, every xlsx part, png text, tif tags, file paths) searched for 25 name terms: 0 found; after
unblinding, 128 summary cells and 4837 json fields equal the normal run. Script:
`experiments/fixes_b1_blind_test.py`. `.gitignore` gained `code_key*` and `*_key.csv`.

**B2 Sensitivity** (`B2_sensitivity.md`, `.csv`). `sensitivity -d DIR -o OUT` scales each image's
$t_\mathrm{hi}$ alone, $t_\mathrm{lo}$ alone and both by 0.8, 0.9, 1.1 and 1.2, and adds one pooled
cut over the folder ($t_\mathrm{hi}$ median, $t_\mathrm{lo}$ median in raw units), using the fast
stage. It writes the percent changes of roots per cell, ring 30 px, field density, lacuna count and
bridges. On the 8 WT images every value equals the overnight grid, in 32 s for 128 runs. The cuts are
passed through new optional arguments of `analyse_image`, which the pipeline never passes.

**B3 Field summary** (`B3_field_summary/`). `field-summary -d DIR -o OUT [-r RESULTS]` matches lacuna
centroids within 25 px between every pair of images, links pairs above the largest gap in the matched
shares and at or above 0.5, and writes per-field means of roots per cell, roots per 100 px perimeter,
ring 30 px, ring densities and field density, stating that the field is the unit. WT result: F1 542_z06
+ 542_z18, F2 543-2 + 543_3 + 543_z13, F3 682_z08, F4 682_z23 + 682_z29, as in the overnight report.

**Figures** (`figures/make_figures.py`, outputs `figures_out/`, review `figures/REVIEW.md`, captions
`figures/captions.md`).
- F0 shared style: one display window for the dataset (1st and 99.8th percentile of the pooled red
  channel, 20 to 255 grey levels); Arial 7 to 9 pt at 180 mm; TrueType fonts embedded in the PDF; PNG
  at 300 dpi; interior lacunae cyan, frame-edge lacunae yellow, 0.6 to 0.8 pt; skeleton white over the
  image dimmed to 60%; roots as yellow dots; scale bars in px.
- F1 per-image figures for all 8 images: raw; outlines, numbers and counts; skeleton with a 3x inset of
  one lacuna chosen by rule (roots closest to the interior median, ties to the smallest id), roots as
  dots. Option `-c` sets the lacuna.
- F2 contact sheet of all 8 images with counts; `-b -k KEY` labels with codes.
- F3 lacuna counts at $t_\mathrm{hi}$ 0.8 to 1.2 for 542_z06, 543-2 and 682_z29, the default boxed.
- F4 roots, roots per 100 px perimeter, ring 30 px, ring density 30 px and field density by field, dots
  for images, bar for the field mean, no test.
- F5 supplementary: the crumb rule and the hole fill, off and on.
- F6 every PNG reviewed at 1000 px; defects fixed in up to two rounds (label placement, a missing glyph,
  overlapping text, footers). Remaining notes are in `figures/REVIEW.md`.

## The switches

All are in `config.py` and off by default. With all off, `results/` is reproduced exactly.

| switch | default | recommended value if wanted | what changes on the 8 WT images (switch-check) | evidence |
|---|---|---|---|---|
| `NARROW_CRUMB_RULE` | False | True | only 543_3 (877,545): area 1344 to 1468 px², roots 6 to 5, ring 30 277 to 269 px; the thread traced through its gap goes | overnight 3.1, 3.4, 3.6b; F5 panel A |
| `FILL_ENCLOSED_HOLES_MAX_PX2` | 0 | 200 | only 542_z06 (783,581): +146 px²; no network measure moves | overnight 3.5, 3.6; F5 panel B |
| `BAND_FILTER_MIN_OPENING_SHARE` | None | 0.515 | removes 542_z06 (555,149) and 682_z23 (363,7); 542_z06 roots per cell +4.5%; the band wall is traced in their place | overnight 3.3, 3.6, 3.7 (the gap rests on 2 objects) |
| `FAST_LACUNA_STAGE` | False | True | nothing (identical labels and numbers); 15 to 25 times faster | A5, fast-check, regression |

**How to turn one on and regenerate**, without touching `results/`:

1. Set the value in `config.py`, for example `NARROW_CRUMB_RULE = True`.
2. `python src/canaliculi.py --dir data/WT -o results_switched` (and `python src/lacunae.py --dir data/WT
   -o results_switched` for the lacuna files). The `parameters` and `provenance` blocks record the
   setting.
3. `python src/diagnostics.py switch-check` lists what each switch changes against `results/`.
4. `python src/diagnostics.py regression` will now FAIL against `results/` for any switch that changes
   numbers; that is expected. If a switch is adopted, regenerate `results/` deliberately in its own
   commit, and the new `results/` becomes the reference.

## What remains blocked

- **Calibration.** No µm/px value exists; `PIXEL_SIZE_UM` stays None and every output is in pixels.
  The raw confocal files or the acquisition record would give it (the TIFFs are 8-bit exports without
  metadata).
- **Ground truth.** No manual (ImageJ) counts yet; roots per cell is the number to compare first.
- **POL definition.** No Hyp images and no periosteocytic lesion measure; the hole rule and the band
  filter must be checked on Hyp fields before use there.
- **Animal IDs and acquisition settings.** The fields cannot be linked to animals, and gain, laser power
  and pinhole are unknown, which is what decides between image-relative and pooled cuts (overnight 2.4,
  `sensitivity`).
- **Repository visibility.** Images, results and figures are pushed; whether the repository is public
  or private decides whether unpublished images are exposed, and whether the blinding key patterns
  matter beyond this machine.

## Decisions needed

1. **Which switches to turn on**: narrow crumb rule, hole fill (200 px²), band filter (0.515). Each is
   ready and documented; none is on.
2. **`FAST_LACUNA_STAGE` as the default.** It changes no number, but it is a default change, so it stays
   off until Karim decides.
3. **Key-file ignore patterns.** `.gitignore` now ignores `code_key*` and `*_key.csv`, as this session's
   brief asked. The 2026-09-30 policy had removed every code_key exclusion so that a key would be
   pushed; the two rules conflict, and the newer one was followed. Confirm.
4. **Blinding drops a constant alpha channel** in the coded copies (542_z06 only). The pipeline never
   reads it, but it is a change to the copied data; the key records it.
5. **The field-summary guard** (at least half of the smaller image's lacunae must match) and whether
   682_z08 belongs to the 682 field (4 of 10 lacunae matched with 682_z23).
6. **Image-relative or pooled cuts** for between-field comparisons (overnight 2.4); the sensitivity
   output should accompany any comparison until this is settled.
7. **Per-cell outcome**: roots per cell or roots per 100 px of perimeter and ring density (both now in
   every output).
8. **Unit of analysis**: the field (now 3 or 4 fields), not the image.
9. **Figures.** The one-pixel skeleton is shown as it is, which renders thin at column width; it was
   not thickened for display. The committed `figures_out/` holds 13 figures as PNG and PDF plus small json logs (about 22 MB).
10. **No new dependencies** were needed. `requirements.txt` lists matplotlib and pandas, which the
    figures and experiments use and which were already installed with skan.
11. **Order of work.** F1b, F2 and F5 were done while the B1 coded run was in progress, before B1 was
    committed; every item was still checked and pushed on its own.

## Final commit and links

Final content commit: `57bcc7ee16a6abab1b1b99c19ee78b17f2f51279`. It is the last commit that changed any code, figure, table or report
text; the commit after it only adds this list, and the next one marks PROGRESS_FIXES.md done. Every
link below is pinned to it.

- [docs/FIXES_REPORT.md](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/docs/FIXES_REPORT.md)
- [experiments/PROGRESS_FIXES.md](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/experiments/PROGRESS_FIXES.md)
- [figures/captions.md](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures/captions.md)
- [figures/REVIEW.md](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures/REVIEW.md)
- [figures_out/display_window.json](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/display_window.json)
- [results_experiments/fixes/A4_switch_check.md](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/results_experiments/fixes/A4_switch_check.md)
- [results_experiments/fixes/A5_fast_stage.md](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/results_experiments/fixes/A5_fast_stage.md)
- [results_experiments/fixes/A5_fast_check.csv](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/results_experiments/fixes/A5_fast_check.csv)
- [results_experiments/fixes/A6_regression.md](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/results_experiments/fixes/A6_regression.md)
- [results_experiments/fixes/B1_blinding.md](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/results_experiments/fixes/B1_blinding.md)
- [results_experiments/fixes/B2_sensitivity.md](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/results_experiments/fixes/B2_sensitivity.md)
- [results_experiments/fixes/B2_sensitivity.csv](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/results_experiments/fixes/B2_sensitivity.csv)
- [results_experiments/fixes/B3_field_summary/field_summary.md](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/results_experiments/fixes/B3_field_summary/field_summary.md)
- [results_experiments/fixes/B3_field_summary/field_summary.csv](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/results_experiments/fixes/B3_field_summary/field_summary.csv)
- [results_experiments/fixes/B3_field_summary/field_images.csv](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/results_experiments/fixes/B3_field_summary/field_images.csv)
- [figures_out/F1_542_z06.pdf](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F1_542_z06.pdf)
- [figures_out/F1_542_z06.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F1_542_z06.png)
- [figures_out/F1_542_z18.pdf](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F1_542_z18.pdf)
- [figures_out/F1_542_z18.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F1_542_z18.png)
- [figures_out/F1_543-2.pdf](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F1_543-2.pdf)
- [figures_out/F1_543-2.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F1_543-2.png)
- [figures_out/F1_543_3.pdf](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F1_543_3.pdf)
- [figures_out/F1_543_3.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F1_543_3.png)
- [figures_out/F1_543_z13.pdf](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F1_543_z13.pdf)
- [figures_out/F1_543_z13.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F1_543_z13.png)
- [figures_out/F1_682_z08.pdf](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F1_682_z08.pdf)
- [figures_out/F1_682_z08.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F1_682_z08.png)
- [figures_out/F1_682_z23.pdf](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F1_682_z23.pdf)
- [figures_out/F1_682_z23.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F1_682_z23.png)
- [figures_out/F1_682_z29.pdf](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F1_682_z29.pdf)
- [figures_out/F1_682_z29.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F1_682_z29.png)
- [figures_out/F2_contact_sheet.pdf](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F2_contact_sheet.pdf)
- [figures_out/F2_contact_sheet.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F2_contact_sheet.png)
- [figures_out/F2_contact_sheet_coded.pdf](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F2_contact_sheet_coded.pdf)
- [figures_out/F2_contact_sheet_coded.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F2_contact_sheet_coded.png)
- [figures_out/F3_threshold_sensitivity.pdf](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F3_threshold_sensitivity.pdf)
- [figures_out/F3_threshold_sensitivity.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F3_threshold_sensitivity.png)
- [figures_out/F4_per_field.pdf](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F4_per_field.pdf)
- [figures_out/F4_per_field.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F4_per_field.png)
- [figures_out/F5_switch_examples.pdf](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F5_switch_examples.pdf)
- [figures_out/F5_switch_examples.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/57bcc7ee16a6abab1b1b99c19ee78b17f2f51279/figures_out/F5_switch_examples.png)
