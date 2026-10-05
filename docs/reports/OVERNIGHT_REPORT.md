# Overnight report, 2026-10-01

**Pre-validation, pixel units.** Branch `overnight-fixes`, started from `main` at 677ccd6. The
pipeline was not changed: `src/` and `config.py` are identical to `main`, and
`python src/diagnostics.py reference-check` passed (62.33 edges per cell, 27.41 px, 21 bridges)
before every push. Every variant is an experiment in `experiments/` with outputs in
`results_experiments/<task>/`. There is no ground truth, so nothing here says a variant is more
accurate: each result says what changes and by how much, with crops to judge by eye. Recommendations
are labelled as such; pipeline defaults are Karim's decision. Coordinates are (x, y) = (column, row),
as `lacuna-table` prints them.

## Summary

- **The 682_z08 lattice is in the raw data** and is most likely tissue. The only periodic artefacts are
  pixel scale (2 and 4 px along x, 0.1 to 0.2 grey levels); removing them changes no headline measure
  by more than 1.4%.
- **The visibly missed bodies are not lost at the threshold** but at a shape or area filter.
- **The two Otsu cuts matter most.** Scaling t_lo by 10% moves field density by about 4 to 5%, and
  scaling t_hi by 10% moves roots per cell by about 8% (median). **One pooled cut for all images
  reverses the order of the fields** for field density and roots per cell.
- **One real defect in the lacuna stage**: in 543_3 (877,545) a dropped middle crumb splits a cell and
  a thread is traced through the gap. A narrow rule (crumbs inside the convex hull) fixes it and
  changes nothing else.
- **Roots per cell and ring 30 px rise with lacuna size**, between images (rho 0.84 and 0.88) and within
  every image. Roots per 100 px of perimeter and ring density remove this.
- **The 8 images are sections of 3 or 4 fields.** Field density repeats within a field to 2 to 3%.
  Per-cell values of one cell differ by 14 to 40% between sections, partly because each section cuts
  the cell differently.
- **Field density is the most robust headline measure** against every lacuna variant (at most 0.7%)
  and every denominator tested (at most 4.5%), but it follows t_lo almost one to one.

## What each variant changes in the headline measures

Percent change against the default, range over the 8 images (median in brackets where given). Per-cell
values are means over interior lacunae, as the pipeline reports them.

| variant (task) | roots per cell | ring 30 px per cell | field density |
|---|---|---|---|
| notch filter, both stages (1.4) | -0.9 to +1.4% | -0.1 to +0.3% | -0.03 to +0.05% |
| t_hi x 0.9 (2.4) | -1.1 to +19.7% (+7.5) | +2.0 to +11.1% (+5.5) | -0.5 to +0.1% |
| t_hi x 1.1 (2.4) | -25.8 to +1.2% (-9.1) | -12.4 to +1.8% (-8.2) | -0.2 to +0.3% |
| t_lo x 0.9 (2.4) | 0 to +9.5% (+1.9) | +2.4 to +6.3% (+4.4) | +3.5 to +5.7% (+5.1) |
| t_lo x 1.1 (2.4) | -6.8 to -1.6% (-4.3) | -5.3 to -3.4% (-4.3) | -4.8 to -3.6% (-4.4) |
| both cuts x 0.8 (2.4) | +1.0 to +47.9% (+26.2) | +4.8 to +39.3% (+24.3) | +6.8 to +11.7% (+10.4) |
| both cuts x 1.2 (2.4) | -51.0 to -15.0% (-19.6) | -22.5 to -12.5% (-19.6) | -9.2 to -6.2% (-8.4) |
| one pooled cut for all images (2.4) | -40.3 to +37.8% | -29.1 to +23.8% | -19.7 to +17.6% |
| crumbs join the re-merge (3.6) | -3.8 to +6.4% | -3.4 to +7.3% | -0.09 to 0% |
| crumbs inside the hull only (3.6b) | -1.6 to 0% (543_3 only) | -0.3 to 0% | 0% |
| widest-path re-merge (3.6) | 0 to +10.0% (682_z29, 542_z06) | 0 to +10.0% | 0 to +0.10% |
| band filter (3.6) | 0 to +4.5% (542_z06 only) | 0 to +4.3% | 0 to +0.12% |
| opening r = 2 (3.6) | -6.5 to +2.2% | -5.8 to +0.3% | -0.02 to +0.15% |
| opening r = 3 (3.6) | -8.1 to 0% | -12.0 to -1.3% | -0.02 to +0.52% |
| opening r = 4 (3.6) | -8.8 to -0.8% | -10.0 to -1.8% | +0.02 to +0.67% |
| holes up to 200 px^2 filled (3.6) | 0% | 0% | +0.01% (542_z06 only) |
| canal mask out of skeleton and area (5.1) | | | -1.6 to +1.1% |
| draft bone ROI (5.1) | | | 0 to +3.1% |
| canal mask and ROI (5.1) | | | -0.6 to +4.5% |
| 542_z06 vertical line removed (5.3) | | | -1.1% (542_z06 only) |

Lacuna counts: unchanged by the notch, the hole fill and t_lo; changed by t_hi in every image under some
scale (from -31% to +50% at 0.8); by the broad crumb rule (+2 in total), the widest path (-2), the band
filter (-2) and the opening (-3 at r = 3, -5 at r = 4).

## 0. Setup and timing

`experiments/task0_cache.py` (`build`, `verify`, `fastcheck`); outputs `results_experiments/task0/`.

- Default results of all 8 images are cached in `results_experiments/_cache/default/` (not committed)
  with a hash of `src/lacunae.py` and `src/canaliculi.py`; a change in either rebuilds the cache.
- The experiments' copies of the pipeline steps reproduce the pipeline exactly on all 8 images
  (`verify.csv`, `fast_copies_check.csv`, also at scaled cuts).
- Timing, one process: 8.7 s (543-2) to 77.5 s (542_z06) per image, 275 s for all 8 (540 s with the
  cache step). The lacuna stage is the slow part: `watershed_split` and `merge_shallow_splits` loop
  over every component with full-frame arrays. Bounding-box copies give identical labels in 0.2 s, so
  pass 2 ran in minutes and no grid was cut.

## 1. Acquisition artefact

`experiments/task1_artefact.py 1.1` to `1.4`; outputs `results_experiments/task1/`.

**1.1 TIFF tags** (`1.1_tiff_tags.md`). All 8 files are 8-bit RGB exports without microscope metadata.
7 were written by ImageJ 1.54p without resolution tags; 542_z06 is RGBA with LZW and a generic 300 dpi,
from another program. Red histograms are not combed; green is empty.

**1.2 FFT and banding** (`1.2_fft.md`). No peak at lattice scale stands above noise: the strongest bins
between periods of 2 and 64 px are 17 to 30 times their local spectrum, against about 18 expected from
noise ($\log_2 N$ for $N$ tested bins). Two pixel-scale artefacts are in all 8 raw images: alternating
columns (period 2 px along x, 290 to 870 times the local spectrum, 0.10 grey levels) and period 4 px
along x (10 to 30 times, 0.15 grey levels). None along y. Row profiles show no consistent banding.

**1.3 Axis-aligned runs** (`1.3_axis_runs.md`, crops `1.3_682_z08_lattice_and_control.png`,
`1.3_682_z08_zoom.png`). Runs of 8 px or more along x or y hold 20 to 24% of the skeleton in every
image; diagonal runs 1.6 to 2.6%. The box x 0 to 380, y 0 to 250 reaches 0.33 in 682_z08 and 0.35 and
0.36 in 682_z23 and 682_z29, against 0.21 to 0.23 outside it. In the raw crop the horizontal threads
are visible, wavy and uneven. Their orientations form broad peaks, with no spike at exactly 0 or 90
degrees. **Conclusion: the lattice is in the raw data, is not made by the preprocessing or the
instrument, and is most likely tissue.** What the horizontal threads are cannot be settled in 2D.

**1.4 Notch filter** (`1.4_notch.md`). Gaussian notches at the two x peaks remove them (left at 0.0 to
1.4 times the local spectrum) while changing no pixel by more than 0.17 grey levels. 0.4 to 1.1% of
skeleton pixels move; density changes by at most 0.05%, roots per cell by at most 1.4% (2 images),
ring 30 by at most 0.3%, lacuna counts not at all, bridges by 1 or 2. The lattice stays (axis-run
share 0.333 to 0.330). A null result.

## 2. Thresholds

`experiments/task2_thresholds.py 2.1`, `2.1s`, `2.2`, `2.3`, `2.4`; outputs `results_experiments/task2/`.

**2.1 Missed bodies** (`2.1_missed_bodies.md`, `2.1_scaled_cut.md`, crops `2.1_crops/`). None is lost
at the cut.

| case | lost at | value | limit |
|---|---|---|---|
| 543_3 (40,310) | aspect | 6.03 | 6.0 |
| 542_z06 (230,300) | solidity | 0.452 | 0.5 |
| 542_z06 (5,930) | area | 301 px^2 | 400 |

543_3: the body and the broad streak below it form one object. 542_z06 (230,300): a long curved body
with a forked stub. 542_z06 (5,930): cut by the frame edge. 543_3 passes at 0.8 and 0.9 times t_hi;
542_z06 (230,300) splits into two kept objects at 1.1 and 1.2; no single scale recovers all three.

**2.2 Cuts against brightness** (`2.2_cuts_vs_brightness.md`). t_hi (0.523 to 0.647) follows the bright
tail (Spearman 0.98 with the saturated fraction, 0.73 with the 99th percentile), not the mean or
median. t_lo is 0.18 to 0.20 of the preprocessed 99th percentile in every image; in raw units it varies
2.7 fold (0.027 to 0.071).

**2.3 Quick sensitivity** (`2.3_quick_sensitivity.md`) on 542_z06, 543-2, 682_z29 with both cuts scaled
together: roots +6.6 to +31.1% at 0.9 and -7.8 to -12.1% at 1.1; ring 30 +5.5 to +18.0% and -3.0 to
-14.1%; density +3.5 to +5.4% and -3.5 to -4.6%; counts change in 542_z06 (16 to 13) and 682_z29
(13 to 11).

**2.4 Full grid** (`2.4_grid.md`, `2.4_grid.csv`). On all 8 images, each cut alone and both together.
- t_lo moves field density almost one to one (+11.1% median at 0.8, -8.2% at 1.2), ring lengths nearly
  as much, roots less, and no lacuna.
- t_hi moves lacuna count and area (median area +29.9% at 0.8, -24.7% at 1.2) and, through the size of
  the bodies, roots (+18.7% / -12.7%) and ring 30 (+11.7% / -10.7%); density stays within 1.2%.
- Lacuna counts change in every image under some t_hi scale (542_z06 16 to 11 at 0.8, 682_z08 10 to 15).
- Bridges are the least stable output (-79% to +86% for 10% changes of t_lo).
- **A pooled network cut** (one value in raw units for all images) is 1.54 to 1.61 times the default in
  the 543 images and 0.60 to 0.71 times in the 542 images. Field density becomes 0.036 in the 543
  images (from 0.044 to 0.045) and 0.038 to 0.041 in the 542 images (from 0.034): **the ordering of
  the fields flips**. Roots per cell flips too (543: 7.6, 6.9, 6.7 to 5.8, 4.1, 5.0; 542: 8.6, 8.3 to
  11.3, 11.4). Which cut is right depends on whether equal raw intensity means equal signal in every
  image, which needs the acquisition settings.

## 3. Lacuna audits

`experiments/task3_lacunae.py 3.0` to `3.7` and `3.6b`; outputs `results_experiments/task3/`.

**3.1 Crumb loss** (`3.1_crumb_loss.md`). 93 of 98 kept lacunae keep their whole pre-watershed
component. 4 miss more than 3%: 542_z06 (555,149) (band object, 64%), 542_z06 (106,67) (leaked outline,
42%), 542_z18 (938,990) (32%) and 543_3 (877,545) (8%), all through pieces dropped for area. 542_z06
(909,17) loses 23 px^2 that the 4-connected watershed never labels.

**3.2 Saddle audit** (`3.2_saddle_audit.md`). The re-merge tests only 15 pairs over all 8 images. The
widest path flips 3 pair tests and 2 final states: the 542_z06 band pair (the merged object then fails a
filter) and 682_z29 (100,835), the split the 0.35 cut was calibrated to keep (straight 0.000, widest
0.559). 543_3 (875,545) merges either way. The 682_z08 points (435,545) and (555,520) are two separate
components at the cut (the brightest path between them dips to half of t_hi), so the re-merge never
sees them.

**3.3 Band objects** (`3.3_band_objects.md`). Minor axis, flagged overlap and solidity do not separate
542_z06 (555,149) and 682_z23 (363,7). The share of area left after an r = 5 opening does: 0.207 and
0.348 against 0.681 for the next kept lacuna. Flagged overlap is 0 or 1 for every kept lacuna, and 6
ordinary lacunae lie fully inside a canal mask.

**3.4 Opening** (`3.4_opening.md`). Median area loss 0.5, 1.2 and 1.8% at r = 2, 3, 4; none lost. The
largest loss, 543_3 (877,545) at 47%, revealed the gap defect: its kept mask is two lobes with a 6-row
band missing, because the 124 px^2 middle piece was too small for the re-merge test and was dropped;
the skeleton has 8 px inside the band. Serrated outlines lose up to 21% of perimeter for 6% of area.

**3.5 Holes** (`3.5_holes.md`). Only 542_z06 (783,581): 146 px^2, area +4.3%, solidity 0.829 to 0.865,
no skeleton inside.

**3.6 Network-level effect** (`3.6_variants.md`, `3.6_variants.csv`; numbers in the table above).
- The broad crumb rule fixes the 543_3 gap but also grows 542_z18 (936,998) and the leaked outline, and
  admits two new objects: 682_z29 (862,728), a dim elongated body (the archived D8 object), and
  682_z23 (74,8) at the frame edge.
- The widest path makes 682_z29 (100,835) one cell and removes the 542_z06 band object.
- The band filter rejects exactly the two band objects in all 8 images.
- The opening touches almost every cell and acts mainly through lacuna size.
- The hole fill changes one cell and no network measure.

**3.6b A narrower crumb rule** (`3.6b_crumbs_inside_hull.md`), added after 3.6. A dropped piece joins a
kept lacuna only if it touches that one lacuna and lies inside its convex hull. Over the 8 images, 4
dropped pieces touch a kept lacuna, with inside-hull shares 0.000, 0.000, 0.009 and 1.000. The rule
joins only the 543_3 crumb: the cell becomes whole (1344 to 1468 px^2), the thread through the gap
goes, roots 6 to 5, ring 30 277 to 269 px. Nothing else changes in any image.

**3.7 Crops** (`3.7_crops.md`, `3.7_crops/`). The opening does not remove the tails and lobes of the
named cases (543-2 (40,300) and (265,95), 543_3 (920,200)), because they are wider than the disk, and
it makes 543_3 (877,545) worse (one lobe dropped, skeleton through the other half). The serration of
the 682 cells is the bases of the canaliculi included in the outline. Removing the 542_z06 band object
lets the skeleton trace the band wall in its place. 682_z29 (100,835) reads as one elongated cell by
eye.

## 4. Size confound

`experiments/task4_size.py 4.1`; outputs `results_experiments/task4/` (`4.1_size_confound.md`).

Across the 8 images, roots per cell against median lacuna area gives Spearman $\rho = 0.838$
(p = 0.009) and ring 30 px $\rho = 0.881$ (p = 0.004), as Karim estimated. Per lacuna (86 interior)
$\rho$ is 0.69 and 0.68, positive within all 8 images. The ring area $A_{30}$ tracks lacuna area at
$\rho = 0.94$: a bigger body has a longer boundary and a larger ring.

| measure | pooled $\rho$ | within-image median $\rho$ | between images $\rho$ | CV across images |
|---|---|---|---|---|
| roots | 0.69 | 0.50 | 0.84 | 0.184 |
| roots per 100 px perimeter | -0.13 | -0.04 | -0.24 | 0.119 |
| ring 30 px | 0.68 | 0.61 | 0.88 | 0.147 |
| ring density $L_{30} / A_{30}$ | 0.03 | 0.13 | -0.02 | 0.085 |

Both normalised forms remove the size dependence and spread less across images. 85 of 86 interior
cells have at least 0.9 of their 30 px annulus inside the frame, so the frame plays no part. Images
repeat cells (6.1), so the p-values are optimistic. Whether the size effect is biology or measurement
is not settled by this.

## 5. Density denominator and bone ROI

`experiments/task5_density.py 5.2`, `5.1`, `5.3`, `5.4` (5.2 before 5.1); outputs
`results_experiments/task5/`.

**5.2 Other channels and the ROI draft** (`5.2_roi_draft.md`, panels `5.2_channel_panels/`). Green is
empty. Blue holds a weak copy of the red structures (lacunae 1.5 to 2.3 times the matrix), brighter
canal regions, purple regions (lower right of 542_z06 and 542_z18, edges of 682_z08) and no-tissue
corners in the 682 images (blue 3 to 6 grey levels). Draft rule after sigma 10 smoothing: blue < 7.5 is
no tissue (in a dip shared by the 682 images); blue over red > 0.72 is purple (no gap exists; anchored
on the 543 images, which show no purple). Masks `roi_draft/`.

**5.1 Field density three ways** (`5.1_density_three_ways.md`).

| image | current | without canal mask | in draft ROI | both |
|---|---|---|---|---|
| 542_z06 | 0.03465 | -0.4% | +1.0% | +0.7% |
| 542_z18 | 0.03407 | -0.2% | +0.5% | +0.3% |
| 543-2 | 0.04470 | 0 | 0 | 0 |
| 543_3 | 0.04514 | 0 | 0 | 0 |
| 543_z13 | 0.04380 | 0 | 0 | 0 |
| 682_z08 | 0.03465 | +1.1% | +3.1% | +4.5% |
| 682_z23 | 0.03830 | -0.6% | +0.9% | +0.4% |
| 682_z29 | 0.03748 | -1.6% | +1.0% | -0.6% |

The canal masks remove 3 to 7% of the area at about the field's own skeleton density. The ROI removes
0 to 4.2%, mostly empty corners. The ordering of the images does not change.

**5.3 542_z06 vertical line** (`5.3_542_z06_trace.md`, crop `5.3_542_z06_trace.png`). In x 515 to 541,
y 590 to 900: 382 skeleton px, 1.1% of the image's skeleton, in 310 of 311 rows. The canal mask covers
only its top 60 rows. Removing it lowers field density by 1.1%. By eye a thin straight line, most likely
the band's wall.

**5.4 Overlays for all 8** (`5.4_roi_overlays.md`, `5.4_roi_overlays/`). The draft keeps 95.9 to 100%
of each field. It misses the weaker purple patches at the lower right of 682_z23 and 682_z29 (ratio
0.6 to 0.77). Hand-edited masks placed in `roi_edited/<image>.png` replace the draft in the
experiments (`roi_edited/README.txt`; self-test passed).

## 6. Repeatability

`experiments/task6_repeat.py 6.1`; outputs `results_experiments/task6/` (`6.1_repeatability.md`).

Centroid matching within 25 px at zero shift gives the groups 542_z06 + 542_z18, 543-2 + 543_3 + 543_z13
and 682_z23 + 682_z29 (77 to 92% of lacunae matched, chance 0.2 to 0.4 matches), with 682_z08 alone
(4 of its 10 matched with 682_z23, 15 times chance: probably the same field, deeper).

| measure | per matched cell, median relative difference | within a field, image-level range over mean |
|---|---|---|
| field density | | 1.7 to 3.0% |
| ring 60 px | 0.14 | 2.9 to 13.1% |
| ring 30 px | 0.25 | 1.2 to 12.4% |
| roots | 0.40 | 4.1 to 19.3% |
| owned length | 0.86 | 1.6 to 22.7% |
| edge count | 0.86 | 3.7 to 28.8% |

The same cell's area differs by 40% between sections, so part of every per-cell difference is true
content, not error. Field density is the most repeatable; the ownership measures the least.

## Recommendations

**These are recommendations only. No default was changed.**

1. **Keep the image-relative cuts, but do not compare fields on them alone.** A pooled cut reverses the
   field ordering (2.4). Before any between-field or genotype comparison, get the acquisition settings
   (gain, laser power, pinhole, bit depth) from the confocal record, and report the t_lo and pooled-cut
   sensitivity next to the result.
2. **Adopt the narrow crumb rule (3.6b) behind a switch.** It fixes a visible defect in one cell and
   changes nothing else in these images. Do not adopt the broad crumb rule (3.6), which admits new
   objects.
3. **Adopt the hole fill up to 200 px^2 behind a switch if a hole rule is wanted.** It affects one cell
   (+4.3% area) and no network measure. Check it on Hyp fields first, as round 3 said.
4. **Do not adopt the opening.** It does not remove the tails it was meant for, it breaks two-lobe
   masks, and it moves every cell mainly through size.
5. **Do not adopt the widest-path re-merge yet.** It changes 2 objects; one of them (682_z29 (100,835))
   needs a by-eye decision first.
6. **Band objects**: if they are to be excluded, the opening-share filter (0.515, in the gap from 0.348
   to 0.681) removes exactly them; expect the band wall to be traced in their place (density +0.1%).
7. **Report roots per 100 px of perimeter and ring density at 30 px beside roots per cell and ring 30 px.**
   The raw forms carry lacuna size (4.1).
8. **Treat the field as the unit.** Average sections within a field; do not pool the 8 images as
   independent (6.1).
9. **Field density is the most robust headline measure** here (repeatable, insensitive to lacuna
   variants and denominators), with the caveat of recommendation 1.
10. **The notch filter, the canal-mask denominator and the ROI** are not needed for the current measures
    (at most 1.4%, 1.6% and 3.1%). Use the ROI only after hand editing.

## Decisions needed

1. **What the horizontal threads of the 682 lattice are** (1.3). They are counted now.
2. **Image-relative or pooled cuts** (2.2, 2.4), and the acquisition record needed to decide.
3. **The missed bodies** (2.1): accept them, or change the aspect limit (543_3 fails by 0.03), the
   solidity limit, or the frame-edge rule.
4. **The narrow crumb rule** (3.6b): adopt behind a switch or not.
5. **682_z29 (100,835)** (3.2, 3.7): one cell or two. The 0.35 calibration assumed two.
6. **682_z08 (435,545) and (555,520)** (3.2): one cell partly out of the plane, or two.
7. **The band objects** (3.3): exclude or keep; together with D4 for Dr. Murshed.
8. **Dim objects such as 682_z29 (862,728)** (3.6): whether lacunae partly outside the focal plane
   count (the open D4 question).
9. **Per-cell normalisation** (4.1): which form is the outcome.
10. **The bone ROI** (5.2, 5.4): the no-tissue rule sits in a gap, the purple rule does not. Edit the
    masks or drop the purple rule.
11. **The 542_z06 vertical line** (5.3): band wall or canaliculus. It is counted now.
12. **The unit of analysis** (6.1): fields or images; and whether 682_z08 belongs to the 682 field.
13. **Raw files** (1.1): the original confocal files would give bit depth, pixel size and settings.
14. **New dependencies**: none were needed. matplotlib and pandas are already installed with skan.

## How to rerun

Every number above comes from a file under `results_experiments/`. `experiments/README.md` explains the
scripts and how to resume; `archive/branch-runs/PROGRESS.md` lists every sub-item with its commit. Each script
skips outputs that already exist, so delete an output to recompute it, for example
`python -u experiments/task2_thresholds.py 2.4`.

## Final commit and links

Final content commit: `fd41c2a8904aa128d354876fd03e05e5a25cff4d` (the last commit that changed any result, script or report text; the
commit after it only adds this list, and the next one marks PROGRESS.md done). Every link below is
pinned to it, so it shows exactly what this report describes.

- [docs/OVERNIGHT_REPORT.md](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/docs/OVERNIGHT_REPORT.md)
- [experiments/PROGRESS.md](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/experiments/PROGRESS.md)
- [results_experiments/task1/1.2_fft.md](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task1/1.2_fft.md)
- [results_experiments/task1/1.3_axis_runs.md](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task1/1.3_axis_runs.md)
- [results_experiments/task1/1.4_notch.csv](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task1/1.4_notch.csv)
- [results_experiments/task2/2.1_missed_bodies.md](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task2/2.1_missed_bodies.md)
- [results_experiments/task2/2.2_cuts_vs_brightness.csv](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task2/2.2_cuts_vs_brightness.csv)
- [results_experiments/task2/2.4_grid.csv](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task2/2.4_grid.csv)
- [results_experiments/task2/2.4_grid.md](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task2/2.4_grid.md)
- [results_experiments/task3/3.1_crumb_loss.csv](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task3/3.1_crumb_loss.csv)
- [results_experiments/task3/3.2_saddle_pairs.csv](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task3/3.2_saddle_pairs.csv)
- [results_experiments/task3/kept_lacunae_measures.csv](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task3/kept_lacunae_measures.csv)
- [results_experiments/task3/3.4_opening.csv](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task3/3.4_opening.csv)
- [results_experiments/task3/3.6_variants.csv](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task3/3.6_variants.csv)
- [results_experiments/task3/3.6b_crumbs_inside_hull.csv](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task3/3.6b_crumbs_inside_hull.csv)
- [results_experiments/task4/4.1_per_lacuna.csv](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task4/4.1_per_lacuna.csv)
- [results_experiments/task4/4.1_correlations.csv](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task4/4.1_correlations.csv)
- [results_experiments/task5/5.1_density_three_ways.csv](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task5/5.1_density_three_ways.csv)
- [results_experiments/task5/5.2_channels.csv](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task5/5.2_channels.csv)
- [results_experiments/task6/6.1_pair_matches.csv](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task6/6.1_pair_matches.csv)
- [results_experiments/task6/6.1_matched_cells.csv](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task6/6.1_matched_cells.csv)
- [results_experiments/task6/6.1_stability.csv](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task6/6.1_stability.csv)
- [results_experiments/task1/1.3_682_z08_lattice_and_control.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task1/1.3_682_z08_lattice_and_control.png)
- [results_experiments/task1/1.3_682_z08_zoom.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task1/1.3_682_z08_zoom.png)
- [results_experiments/task2/2.1_crops/543_3_x40_y310.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task2/2.1_crops/543_3_x40_y310.png)
- [results_experiments/task2/2.1_crops/542_z06_x230_y300.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task2/2.1_crops/542_z06_x230_y300.png)
- [results_experiments/task2/2.1_crops/542_z06_x5_y930.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task2/2.1_crops/542_z06_x5_y930.png)
- [results_experiments/task3/3.7_crops/543_3_x877_y545.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task3/3.7_crops/543_3_x877_y545.png)
- [results_experiments/task3/3.7_crops/543_3_x877_y545_inside_hull.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task3/3.7_crops/543_3_x877_y545_inside_hull.png)
- [results_experiments/task3/3.7_crops/682_z29_x100_y835.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task3/3.7_crops/682_z29_x100_y835.png)
- [results_experiments/task3/3.7_crops/542_z06_x570_y100.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task3/3.7_crops/542_z06_x570_y100.png)
- [results_experiments/task3/3.7_crops/682_z29_x862_y728.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task3/3.7_crops/682_z29_x862_y728.png)
- [results_experiments/task3/3.7_crops/543-2_x40_y300.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task3/3.7_crops/543-2_x40_y300.png)
- [results_experiments/task3/3.7_crops/682_z08_x210_y434.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task3/3.7_crops/682_z08_x210_y434.png)
- [results_experiments/task5/5.3_542_z06_trace.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task5/5.3_542_z06_trace.png)
- [results_experiments/task5/5.4_roi_overlays/682_z08_roi_overlay.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task5/5.4_roi_overlays/682_z08_roi_overlay.png)
- [results_experiments/task5/5.4_roi_overlays/542_z06_roi_overlay.png](https://raw.githubusercontent.com/Kimokazi-coder/xlh-lcn-pipeline/fd41c2a8904aa128d354876fd03e05e5a25cff4d/results_experiments/task5/5.4_roi_overlays/542_z06_roi_overlay.png)
