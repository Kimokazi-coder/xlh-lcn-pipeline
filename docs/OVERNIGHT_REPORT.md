# Overnight report, 2026-10-01

**DRAFT (pass 1).** Sections marked *pending* are filled in pass 2.

**Pre-validation, pixel units.** Branch `overnight-fixes`. The pipeline was not changed: `src/` and
`config.py` are identical to `main`, and `python src/diagnostics.py reference-check` passed (62.33,
27.41 px, 21 bridges) before every push. Every variant here is an experiment in `experiments/`,
with outputs in `results_experiments/<task>/`. There is no ground truth, so no variant is called more
accurate. Each result says what changes and by how much. Coordinates are (x, y) = (column, row),
as `lacuna-table` prints them.

## Summary

- **The 682_z08 lattice is in the raw data** and is most likely tissue (threads along and across the
  lamellae), not an instrument pattern. The only periodic artefacts are at 2 and 4 px along x and
  0.1 to 0.2 grey levels in size.
- **The visibly missed bodies are not lost at the threshold.** They fail a shape or area filter
  (aspect 6.03, solidity 0.452, area 301 px^2 at the frame edge).
- **The headline measures move several percent when the cuts move 10%**: roots per cell 7 to 31%,
  ring 30 px 3 to 18%, field density 3.5 to 5.4%.
- **One real defect found in the lacuna stage**: in 543_3 (877,545) a 124 px^2 middle piece is
  dropped between two merged halves, leaving a gap through the cell with a traced thread in it.
- **Roots per cell and ring 30 px rise with lacuna size** (rho 0.84 and 0.88 across images, positive
  within every image). Roots per 100 px of perimeter and ring density remove this.
- **The 8 images are sections of 3 or 4 fields.** Field density repeats within a field to 2 to 3%;
  per-cell values of the same cell differ by 14 to 40% between sections, partly because each section
  cuts the cell differently.

## 0. Setup and timing

- Default results of all 8 images are cached in `results_experiments/_cache/default/` (not committed),
  with a hash of `src/lacunae.py` and `src/canaliculi.py`.
- Copies of the pipeline steps used by the experiments reproduce the pipeline exactly on all 8 images
  (`results_experiments/task0/verify.csv`, `fast_copies_check.csv`).
- Timing, one process: 8.7 s (543-2) to 77.5 s (542_z06) per image, 275 s for all 8. The lacuna stage
  is the slow part: `watershed_split` and `merge_shallow_splits` loop over every component with
  full-frame arrays. Bounding-box copies give identical labels in about 0.2 s. The network stage from
  cached inputs takes 2 to 4 s.

## 1. Acquisition artefact

Files: `results_experiments/task1/`. Script: `experiments/task1_artefact.py`.

**1.1 TIFF tags.** All 8 files are 8-bit RGB exports with no microscope metadata. 7 were written by
ImageJ 1.54p without resolution tags. 542_z06 is RGBA with LZW compression and a generic 300 dpi,
from a different program. Red histograms are not combed. Green is empty.

**1.2 FFT and banding.** No lattice-scale peak stands above noise: between periods of 2 and 64 px the
strongest bins are 17 to 30 times their local spectrum, against about 18 expected from noise alone
($\log_2 N$ for $N$ tested bins). Two pixel-scale artefacts are present in all 8 raw images:
alternating columns (period 2 px along x, 290 to 870 times the local spectrum, 0.10 grey levels) and
a period of 4 px along x (10 to 30 times, 0.15 grey levels). Nothing comparable along y. The Gaussian
and top-hat reduce both to 0.03 to 0.07 grey-level equivalents. Row profiles show no consistent banding.

**1.3 Axis-aligned runs.** Runs of 8 px or more along x or y hold 20 to 24% of the skeleton in every
image, diagonal runs 1.6 to 2.6%. The 682_z08 box (x 0 to 380, y 0 to 250) reaches 0.33, and the
same box reaches 0.35 and 0.36 in 682_z23 and 682_z29, against 0.21 to 0.23 outside it. In the raw
crop the horizontal threads are visible, wavy and uneven in brightness. Their orientations form broad
peaks about 15 degrees wide, with no spike at exactly 0 or 90 degrees. **Conclusion: the lattice is in
the raw data and is not made by preprocessing or by the instrument. It is most likely tissue.** What
the horizontal threads are (canaliculi along the lamellae or another linear structure) cannot be
settled in 2D. Crops: `1.3_682_z08_lattice_and_control.png`, `1.3_682_z08_zoom.png`.

**1.4 Notch filter.** *Pending.*

## 2. Thresholds

Files: `results_experiments/task2/`. Script: `experiments/task2_thresholds.py`.

**2.1 Missed bodies.** None is lost at the cut.

| case | lost at | value | limit |
|---|---|---|---|
| 543_3 (40,310) | aspect | 6.03 | 6.0 |
| 542_z06 (230,300) | solidity | 0.452 | 0.5 |
| 542_z06 (5,930) | area | 301 px^2 | 400 |

543_3: body and the broad streak below it form one object. 542_z06 (230,300): long curved body with
a forked stub. 542_z06 (5,930): cut by the frame edge. At other cuts (`2.1_scaled_cut.md`): 543_3
passes at 0.8 and 0.9 times t_hi; 542_z06 (230,300) is split into two kept objects at 1.1 and 1.2,
which by eye is one body. No single scale recovers all three.

**2.2 Cuts against brightness.** t_hi (0.523 to 0.647) follows the bright tail: Spearman 0.98 with the
saturated fraction, 0.73 with the 99th percentile, not related to the mean or median. t_lo is 0.18 to
0.20 of the preprocessed 99th percentile in every image; in raw units it varies 2.7 fold (0.027 to
0.071). Both cuts are image relative by design.

**2.3 Quick sensitivity** (542_z06, 543-2, 682_z29, both cuts scaled together):

| measure | x 0.9 | x 1.1 |
|---|---|---|
| roots per cell | +6.6 to +31.1% | -7.8 to -12.1% |
| ring 30 px per cell | +5.5 to +18.0% | -3.0 to -14.1% |
| field density | +3.5 to +5.4% | -3.5 to -4.6% |
| median lacuna area | +11 to +23% | -9 to -24% |
| lacuna count | 542_z06 16 to 13 | 682_z29 13 to 11 |

**2.4 Full grid.** *Pending.*

## 3. Lacuna audits

Files: `results_experiments/task3/`. Script: `experiments/task3_lacunae.py`.

**3.1 Crumb loss.** 93 of 98 kept lacunae keep their whole pre-watershed component. 4 miss more than
3%: 542_z06 (555,149) (band object, 64% of its component dropped), 542_z06 (106,67) (leaked outline,
42%), 542_z18 (938,990) (32%), 543_3 (877,545) (8%). All dropped pieces were removed for area. One more
lacuna loses 23 px^2 because the watershed floods with 4-connectivity.

**3.2 Saddle audit.** Only 15 pairs are tested by the re-merge over all 8 images. The widest path
inside the mask flips 3 pair tests and 2 final states: the 542_z06 band pair (the merged object then
fails a filter, 16 to 15 objects) and 682_z29 (100,835), the split the 0.35 cut was calibrated to keep
(straight 0.000, widest 0.559; 13 to 12). 543_3 (875,545) merges either way (0.910 / 0.979). The
682_z08 points (435,545) and (555,520) are two separate components at the cut; the brightest path
between them dips to half of t_hi, so the re-merge never sees them.

**3.3 Band objects.** Minor axis, flagged overlap and solidity do not separate 542_z06 (555,149) and
682_z23 (363,7) from the other kept lacunae. The share of area left after an opening with the
top-hat disk (r = 5) does: 0.207 and 0.348, against 0.681 for the next. Flagged overlap is 0 or 1 for
every kept lacuna; 8 lie fully inside the canal mask, 6 of them ordinary.

**3.4 Opening, r = 2, 3, 4.** Median area loss 0.5, 1.2 and 1.8%; no lacuna disappears. The biggest
loss is 543_3 (877,545), 47% at r = 2: its kept mask is two lobes with a 6-row band missing, because
the 124 px^2 middle piece is too small to enter the re-merge and is dropped. The skeleton has 8 px
inside that band. Others: the leaked outline (22 to 27%), the band objects, two thin objects, and
serrated outlines (682_z08 (210,434) loses 21% of its perimeter for 6% of its area at r = 3).

**3.5 Holes up to 200 px^2.** Only 542_z06 (783,581): 146 px^2, area +4.3%, solidity 0.829 to 0.865,
no skeleton inside.

**3.6 Network-level effect of the variants.** *Pending.*

**3.7 Before and after crops.** *Pending.*

## 4. Size confound

Files: `results_experiments/task4/`. Script: `experiments/task4_size.py`.

Across the 8 images, roots per cell against median lacuna area gives Spearman $\rho = 0.838$
(p = 0.009) and ring 30 px gives $\rho = 0.881$ (p = 0.004). Per lacuna (86 interior) $\rho$ is 0.69 and
0.68, and positive within all 8 images. The ring area $A_{30}$ tracks lacuna area at $\rho = 0.94$.

| measure | pooled $\rho$ | within-image median $\rho$ | between images $\rho$ | CV across images |
|---|---|---|---|---|
| roots | 0.69 | 0.50 | 0.84 | 0.184 |
| roots per 100 px perimeter | -0.13 | -0.04 | -0.24 | 0.119 |
| ring 30 px | 0.68 | 0.61 | 0.88 | 0.147 |
| ring density $L_{30} / A_{30}$ | 0.03 | 0.13 | -0.02 | 0.085 |

Both normalised forms remove the size dependence. 85 of 86 interior cells have at least 0.9 of their
30 px annulus in the frame, so the frame plays no part. The images repeat cells (6.1), so the p-values
are optimistic. Whether the size effect is biology or measurement is not settled by this.

## 5. Density denominator and bone ROI

Files: `results_experiments/task5/`. Script: `experiments/task5_density.py`.

**5.2 Other channels and the ROI draft** (done before 5.1). Green is empty. Blue holds a weak copy of
the red structures (lacunae 1.5 to 2.3 times the matrix), brighter canal regions, purple regions
(lower right of 542_z06 and 542_z18, edges of 682_z08) and no-tissue corners in the 682 images (blue
3 to 6 grey levels). Draft ROI: smoothed blue < 7.5 is no tissue (in a dip shared by the 682 images);
smoothed blue over red > 0.72 is purple (no gap exists; anchored on the 543 images). It removes 0 to
4.2% of a field and no kept lacuna. Masks in `roi_draft/`, overlays in `5.2_roi_overlays/`.

**5.1 Field density three ways.**

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

The canal masks remove 3 to 7% of the area at about the field's own density. The ordering of the
images does not change.

**5.3 542_z06 vertical trace** (x 515 to 541, y 590 to 900): 382 skeleton px, 1.1% of the image's
skeleton, in 310 of 311 rows. The canal mask covers only its top. Removing it lowers field density by
1.1%. By eye it is a thin straight line, most likely the band's wall.

**5.4 ROI overlays for all 8.** *Pending.*

## 6. Repeatability

Files: `results_experiments/task6/`. Script: `experiments/task6_repeat.py`.

Matching centroids within 25 px at zero shift gives the groups 542_z06 + 542_z18, 543-2 + 543_3 +
543_z13 and 682_z23 + 682_z29 (77 to 92% of lacunae matched), with 682_z08 alone (4 of 10 matched
with 682_z23, 15 times chance; probably the same field deeper).

| measure | per matched cell, median relative difference | within a field, image-level range over mean |
|---|---|---|
| field density | | 1.7 to 3.0% |
| ring 60 px | 0.14 | 2.9 to 13.1% |
| ring 30 px | 0.25 | 1.2 to 12.4% |
| roots | 0.40 | 4.1 to 19.3% |
| owned length | 0.86 | 1.6 to 22.7% |
| edge count | 0.86 | 3.7 to 28.8% |

The same cell's area also differs by 40% between sections, so part of every per-cell difference is
true content. Field density is the most repeatable measure; the ownership measures the least.

## Decisions needed

1. **What the horizontal threads of the 682 lattice are** (1.3): canaliculi along the lamellae, or
   something else. They are counted now.
2. **The missed bodies** (2.1): accept the losses, or change the aspect limit (543_3 fails by 0.03),
   the solidity limit, or the frame-edge rule. No threshold was changed.
3. **The 543_3 (877,545) gap** (3.4): the dropped middle crumb splits a cell and lets a thread run
   through it. The crumb variant tested in 3.6 addresses it.
4. **682_z29 (100,835)** (3.2): one cell or two. The widest-path saddle merges it, the straight line
   keeps it split, and the 0.35 calibration assumed two.
5. **The band objects** (3.3): only the opening share separates them, on 2 objects. Exclude or keep.
6. **Per-cell normalisation** (4.1): roots per cell, or roots per 100 px of perimeter and ring density,
   depending on whether a size effect is wanted in the outcome.
7. **The bone ROI** (5.2): the no-tissue rule sits in a gap; the purple rule does not. Edit the masks
   or drop the purple rule.
8. **The 542_z06 vertical line** (5.3): likely band wall; it is counted now.
9. **The unit of analysis** (6.1): the 8 images are 3 or 4 fields. Per-field means over sections, or
   per image. Is 682_z08 part of the 682 field?
10. **Raw files** (1.1): the TIFFs are 8-bit exports without metadata. The original confocal files
    would give bit depth and pixel size.

## Files

Every number above comes from a file under `results_experiments/`. `experiments/PROGRESS.md` lists
each sub-item with its commit. `experiments/README.md` explains how to rerun or resume.
