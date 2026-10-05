# Index of results_experiments

Pre-validation, pixel units. A map from each question to the file that answers it, with the one-line
answer from `docs/OVERNIGHT_REPORT.md` (tasks 0 to 6, branch overnight-fixes) or `docs/FIXES_REPORT.md`
(folder `fixes/`, branch publication-fixes). There is no ground truth, so no answer says that a variant
is more accurate. The folder names stay as they are; scripts are in `experiments/` (`taskN_*.py`).
`_cache/` holds caches and is not committed.

## Setup and the acquisition artefact

| question | file | answer |
|---|---|---|
| Do the experiments reproduce the pipeline exactly? | `task0/verify.csv`, `task0/fast_copies_check.csv` | Yes, on all 8 images, also at scaled cuts. |
| How long does the pipeline take? | `task0/timing.json` | 8.7 to 77.5 s per image; the lacuna stage is the slow part. |
| What do the image files carry? | `task1/1.1_tiff_tags.md` | 8-bit RGB exports without microscope metadata; no pixel size. |
| Is the 682_z08 lattice an artefact of the instrument or the code? | `task1/1.2_fft.md`, `task1/1.3_axis_runs.md` | No: the lattice is in the raw data and is most likely tissue; only pixel-scale artefacts (period 2 and 4 px along x) exist. |
| Does removing those artefacts change anything? | `task1/1.4_notch.md` | No: at most 1.4% on any headline measure. |

## Thresholds

| question | file | answer |
|---|---|---|
| Why are some bright bodies not outlined? | `task2/2.1_missed_bodies.md`, crops `task2/2.1_crops/` | They are not lost at the threshold but at a filter: 543_3 (40,310) aspect, 542_z06 (230,300) solidity, 542_z06 (5,930) area. |
| Would another lacuna cut recover them? | `task2/2.1_scaled_cut.md` | No single scale of t_hi recovers all three. |
| What do the two cuts follow? | `task2/2.2_cuts_vs_brightness.md` | t_hi follows the bright tail of the histogram; t_lo is about 0.18 to 0.20 of the preprocessed 99th percentile and varies 2.7 fold in raw units. |
| Do the thresholds matter? | `task2/2.4_grid.md` (quick version `task2/2.3_quick_sensitivity.md`) | Yes, about 4 to 9 percent per 10 percent change: t_lo moves field density almost one to one, t_hi moves roots and ring 30 through lacuna size. |
| What does one pooled cut for all images do? | `task2/2.4_grid.md` | It reverses the order of the fields for field density and roots per cell. |
| The same grid as a pipeline command? | `fixes/B2_sensitivity.md`, `fixes/B2_sensitivity.csv` | `python src/diagnostics.py sensitivity` reproduces the overnight grid exactly. |

## Lacuna detection

| question | file | answer |
|---|---|---|
| Does the watershed lose parts of lacunae? | `task3/3.1_crumb_loss.md` | 93 of 98 kept lacunae keep their whole component; 4 lose more than 3%. |
| Does the re-merge use the right saddle? | `task3/3.2_saddle_audit.md` | Only 15 pairs are tested; the widest path would flip 2 final states. |
| Can the two band objects be told apart? | `task3/3.3_band_objects.md` | Yes, by the share of area left after an r = 5 opening (0.207 and 0.348 against 0.681 and up), a gap that rests on two objects. |
| Would an opening clean the outlines? | `task3/3.4_opening.md`, `task3/3.7_crops.md` | No: it does not remove the tails and breaks two-lobe masks. |
| Are there holes in kept lacunae? | `task3/3.5_holes.md` | One: 542_z06 (783,581), 146 px², area +4.3%. |
| What does each lacuna variant change in the network measures? | `task3/3.6_variants.md` | Table of percent changes; the hole fill and the narrow crumb rule change one cell each. |
| Is there a narrow fix for the 543_3 gap? | `task3/3.6b_crumbs_inside_hull.md` | Yes: crumbs inside the convex hull join; only 543_3 (877,545) changes. |
| What do the switches change? | `fixes/A4_switch_check.md` | Each switch changes exactly the objects the overnight report predicted, and nothing else. |
| Is the fast lacuna stage identical? | `fixes/A5_fast_stage.md`, `fixes/A5_fast_check.csv` | Yes, 40 of 40 label images identical, 15 to 25 times faster. |

## Per-cell measures and density

| question | file | answer |
|---|---|---|
| Is there a size confound? | `task4/4.1_size_confound.md` | Yes: roots and ring 30 rise with lacuna area (Spearman 0.84 and 0.88 across images); roots per 100 px perimeter and ring density remove it. |
| Does the denominator of field density matter? | `task5/5.1_density_three_ways.md` | Little: removing canal masks or using the draft ROI moves density by at most 4.5%; the image order does not change. |
| What do the green and blue channels hold, and can they give a bone ROI? | `task5/5.2_roi_draft.md`, `task5/5.4_roi_overlays.md` | Green is empty; blue gives a draft ROI that keeps 95.9 to 100% of each field and needs hand editing. |
| What is the vertical line in 542_z06? | `task5/5.3_542_z06_trace.md` | Most likely the band wall: 382 skeleton px (1.1%), below the canal mask; it is counted now. |

## Repeatability and fields

| question | file | answer |
|---|---|---|
| Are the 8 images independent? | `task6/6.1_repeatability.md` | No: they are sections of 3 or 4 fields; 682_z08 is probably the same field as 682_z23 and 682_z29. |
| Which measure repeats best within a field? | `task6/6.1_repeatability.md`, `task6/6.1_stability.csv` | Field density (1.7 to 3.0%); ownership measures the least. |
| Per-field means as a pipeline command? | `fixes/B3_field_summary/field_summary.md` | `python src/diagnostics.py field-summary` gives the same 4 groups and per-field means. |

## Checks and provenance (branch publication-fixes)

| question | file | answer |
|---|---|---|
| Does the pipeline still give results/ exactly? | `fixes/A6_regression.md` | Yes: `regression` compares 3861 numbers at tolerance 0. |
| Which code and settings made an output? | `fixes/A1_provenance.md` | Every json output carries a provenance block. |
| Can the images be analysed blind? | `fixes/B1_blinding.md` | Yes: `blind` and `unblind`; no original name leaks into any output. |
| Can outputs go elsewhere than results/? | `fixes/A2_output_option.md` | Yes, with `-o DIR`. |
