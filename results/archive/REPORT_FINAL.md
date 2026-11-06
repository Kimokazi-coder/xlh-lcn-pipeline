# Report: finishing the pipeline (2026-11-06)

**Pre-validation.** Every rule was chosen on the 27 development images only,
in DEV mode, and checked by an AI reviewer (the `image-reviewer` subagent),
not by manual counts. The final run, at tag `method-freeze-v2`, covers all 35
images in FINAL mode; no held-out image or output was opened or reviewed.
Progress log: [`../PROGRESS_FINAL.md`](../PROGRESS_FINAL.md). Start reading at
[`../HOW_TO_READ.md`](../HOW_TO_READ.md); every number is in
[`../SUMMARY.xlsx`](../SUMMARY.xlsx).

## The POL definition (working, to be confirmed by Dr. Murshed)

The dye fills the lacuna and the unmineralized pericellular matrix together,
so a POL shows as an enlarged, irregular, dye-filled lacunar space: that space,
as the lacuna stage outlines it, is the POL footprint. No separate halo.

## What the new rules do

- **The structure rule replaces the 300 um2 cap** (config g9). Large objects
  stay lacunae unless more than half of them lies in the **excluded region**:
  saturated border regions (at least 100 um2, touching the frame, the blooming
  at the top of the 699 fields) and very large bright structures (lacuna mask
  regions of at least 500 um2, such as the centre of 701_z26), grown by 3 um.
  On the development images ([`audit/CAP_V2.md`](audit/CAP_V2.md)) no real
  lacuna over 150 um2 is removed; of the 28 objects over 150 um2 the cap had 8
  wrong, the new rule 7, all of them band pieces at the frame (no size
  measure). Merged lacunae carry the flag `cluster` and are kept.
- **Excluded regions are masked, not whole images**, and every area measure
  uses the analysed area, the image minus the excluded region
  ([`audit/EXCLUDED_REGIONS.md`](audit/EXCLUDED_REGIONS.md)): 12 of 27
  development images have one; the reviewer found no real lacuna under it on
  11 and one borderline at the rim of the twelfth.

## Final POL table (all 35 images, FINAL mode)

WT median lacunar area 36.79 um2 (every measured WT lacuna, 8 images). Measured
lacunae are inside the frame and have an area.

| group | images | lacunae (measured) | median um2 | 90th pct um2 | above 2 x WT median | above 100 um2 | clusters | POL area per analysed area |
| - | - | - | - | - | - | - | - | - |
| WT | 8 | 96 (85) | 36.8 | 66.7 | 5.9% | 1.2% | 0 | 2.8% |
| WT_HP | 9 | 103 (83) | 31.2 | 77.9 | 10.8% | 3.6% | 0 | 2.7% |
| Hyp_RD | 9 | 204 (172) | 38.5 | 87.3 | 18.0% | 8.7% | 1 | 6.9% |
| Hyp_HP | 9 | 196 (145) | 23.8 | 96.9 | 17.2% | 9.0% | 0 | 6.7% |

| animal | group | images | measured | median um2 | 90th pct um2 | above 2 x WT median | POL area per analysed area |
| - | - | - | - | - | - | - | - |
| 542 | WT | 2 | 23 | 54.9 | 78.5 | 21.7% | 3.9% |
| 543 | WT | 3 | 33 | 34.9 | 51.6 | 0.0% | 2.2% |
| 682 | WT | 3 | 29 | 31.3 | 59.4 | 0.0% | 2.6% |
| 872 | WT_HP | 3 | 36 | 25.4 | 52.3 | 0.0% | 2.9% |
| 876 | WT_HP | 3 | 22 | 32.7 | 46.3 | 0.0% | 1.9% |
| 877 | WT_HP | 3 | 25 | 46.7 | 100.5 | 36.0% | 3.3% |
| 535 | Hyp_RD | 3 | 56 | 38.1 | 118.5 | 19.6% | 6.5% |
| 536 | Hyp_RD | 3 | 48 | 46.3 | 75.4 | 16.7% | 4.7% |
| I534 | Hyp_RD | 3 | 68 | 34.1 | 87.0 | 17.6% | 9.7% |
| 548 | Hyp_HP | 3 | 50 | 25.8 | 98.6 | 26.0% | 6.0% |
| 699 | Hyp_HP | 3 | 42 | 23.8 | 54.2 | 9.5% | 5.4% |
| 701 | Hyp_HP | 3 | 53 | 23.0 | 84.0 | 15.1% | 9.1% |

## The statistics in plain words ([`../summary/STATISTICS.md`](../summary/STATISTICS.md))

Pooled per group, with no test, Hyp lacunae are larger at the large end than
WT (90th percentile 87 to 97 against 67 to 78 um2; 17 to 18% above 2 x the WT
median against 6 to 11%) and take about two and a half times the share of the
field (6.7 to 6.9% against 2.7 to 2.8%), with fewer roots per lacuna (9.2 to
9.5 against 10.7 to 11.0) and a lower canalicular density (0.19 to 0.24
against 0.30 to 0.36 um per um2). The low Hyp_HP median (23.8 um2) may come
as much from the small fragments and band pieces the detector still keeps as
from smaller lacunae; that is not checked.
**The question of the study, the genotype by diet interaction, has no answer
from these data:** at the animal level (3 animals per group, 8 degrees of
freedom) every interaction interval includes zero, for instance the share
above 2 x the WT median, -5.9 points (95% interval -40.1 to +28.4), the 90th
percentile -17.8 um2 (-78.6 to +42.9) and the POL area per analysed area
+0.05 points (-4.5 to +4.6). Only an interaction of about 47 points, 84 um2
or 6 points of field would be found 4 times in 5. The mixed models over every
lacuna or image agree and are too optimistic. n is too small for a test; the
intervals are the result.

## The final run and its checks

FINAL mode, all 35 images, at `method-freeze-v2`: lacunae, canaliculi,
quantification, field summary, every figure redrawn, 3_pols, statistics, the
key results view, SUMMARY.xlsx, group overview and QC. Regression PASS (both
runs, 8 WT images), reference-check 3 of 3, pols selftest 17 of 17, check and
check-pictures 35 of 35, statistics selftest 4 of 4, key pictures 105 of 105
equal to their originals, figure checks of all four groups, ai-judge stub 15
of 15, holdout-check 13 of 13. Two known failures: the ai-lacuna-judge stub 26
of 27 (its cap check, as before) and the layout check (old untracked
per-image folders in `results/WT/` on this machine). One fix after the tag:
the group overview's consistency check compared the json's skeleton length,
which since phase 3 leaves out the excluded region, with the whole skeleton
picture; it now counts the analysed field too (`diagnostics.py unowned_px`).
No method or measure changed.

## What is still wrong

- Unsaturated bright bands along the bone surface or the frame, bright tissue
  patches and the diffuse tissue of 701_z26 are still outlined as lacunae in
  pieces (most touch the frame, so they move counts, not sizes); dark field
  outside the bone is not excluded, which lowers the POL area per analysed
  area of such fields (872).
- The cluster flag is rough: it agreed with the reviewer on 1 of 2 clusters.
- The rescue rules stay off, so dim lacunae are lost unevenly (the audit of
  the same day, `audit/DIM_AUDIT.md`); the AI judge sets do not match the
  current detection; the rules rest on an AI reviewer, not on manual counts.
- The held-out images were run but not reviewed, as the rules require.
- Nothing is deleted, so figure files the final run did not redraw stay beside
  the new ones: the old Fig02 overlays of WT (543-2, png), WT_HP
  (877_wt_z081c1-2), Hyp_RD (I534_z25c1-2) and Hyp_HP (699_HYP_HP_z20c1-2),
  whose image the figure rule no longer picks, and the two-page cell gallery
  of 699_HYP_HP_z11c1-2, now one page. They predate `method-freeze-v2`.

## To confirm with Dr. Murshed

1. The POL definition: is the enlarged dye-filled lacunar space the POL
   footprint, with no separate halo?
2. The animal mapping of `data/animals.csv` (12 animals from the file name
   prefixes; `confirmed` = no), including whether I534 is one animal.
3. Animal 701's diet: its file names carry no diet label; it is HP only
   because its images are in `data/Hyp_HP` (535, I534, 543, 682 and 876 carry
   no diet label either).
4. The Hyp;Enpp1 images: none are in `data/`, so they are in no group or
   number here; where they belong and whether they should be added.
