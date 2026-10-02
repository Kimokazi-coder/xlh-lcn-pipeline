# C4 Field density without the flagged regions, and an optional ROI

Pre-validation, px. New field keys (and summary table columns): `field_density_without_flagged_per_px`, the
skeleton px outside the flagged canal mask over the analysed area outside it (the mask as the pipeline uses
it, dilated by 4 px), and `field_density_in_roi_per_px`, written only with `python src/canaliculi.py ... -m
DIR` (PNG masks, white = bone, named by the clean or the short image name, as
`results_experiments/task5/roi_edited`). Without `-m` it is None: no ROI is applied by default, and the
draft ROI is not used.

## Field density without the flagged regions

| image | field_density | without_flagged | change_pct | flagged_share_of_area | flagged_share_of_skeleton | overnight_5_1_without_flagged_pct |
|---|---|---|---|---|---|---|
| 542_z06 | 0.03465 | 0.03452 | -0.38615 | 0.03041 | 0.03415 | -0.38613 |
| 542_z18 | 0.03407 | 0.03399 | -0.23617 | 0.03887 | 0.04114 | -0.23617 |
| 543-2 | 0.04470 | 0.04470 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| 543_3 | 0.04514 | 0.04514 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| 543_z13 | 0.04380 | 0.04380 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |
| 682_z08 | 0.03465 | 0.03503 | 1.09826 | 0.07366 | 0.06349 | 1.09827 |
| 682_z23 | 0.03830 | 0.03806 | -0.63154 | 0.06158 | 0.06750 | -0.63155 |
| 682_z29 | 0.03748 | 0.03688 | -1.60479 | 0.07394 | 0.08880 | -1.60479 |


Against the overnight report 5.1 column "without canal mask" (`results_experiments/task5/
5.1_density_three_ways.csv`): the largest difference over the 8 images is 1.5e-05 percentage points, which is the 8-decimal rounding of the stored densities: the pipeline column reproduces the experiment. 543-2, 543_3 and 543_z13 have no flagged region, so nothing changes there.

## Self-test of the -m option (asserted)

`src/canaliculi.py` run from the command line into the git-ignored cache with synthetic masks:

| image | mask file | mask | expected | written | plain density | result |
|---|---|---|---|---|---|---|
| 543-2 | `543-2.png` | all white | 0.04470139 | 0.04470139 | 0.04470139 | PASS |
| 682_z08 | `682_z08.png` | left half white (short name) | 0.04356184 | 0.04356184 | 0.03464652 | PASS |

Without `-m` the key is None (checked on the cached default run).
