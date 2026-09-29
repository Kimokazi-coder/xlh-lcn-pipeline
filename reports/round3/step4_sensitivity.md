# Step 4: sensitivity of each measure to the reach cap

PRE-VALIDATION, PIXEL units. Every value comes from canaliculi_v1's own
measurement code, run on the default skeleton at each cap. Per-cell values are
means over the 86 interior cells of the 8 WT images; field density
is the mean over the 8 images. Uncapped edge counts matched the committed default
outputs on all 8 images.

Primary cap: **275 px** (Step 1 rule). 100 px and no cap are reference rows.

## Pooled values

| cap px | roots per cell | ring length r30 per cell (px) | ring length r60 per cell (px) | owned length per cell (px) | edge count per cell | field length density (px^-1) |
|---|---|---|---|---|---|---|
| no cap | 7.50 | 319.81 | 904.74 | 1296.59 | 45.41 | 0.03910 |
| 100 | 7.50 | 319.81 | 904.74 | 788.73 | 26.53 | 0.03910 |
| 225 | 7.50 | 319.81 | 904.74 | 1110.35 | 38.53 | 0.03910 |
| 250 | 7.50 | 319.81 | 904.74 | 1143.79 | 39.72 | 0.03910 |
| **275** | 7.50 | 319.81 | 904.74 | 1173.57 | 40.73 | 0.03910 |
| 300 | 7.50 | 319.81 | 904.74 | 1189.94 | 41.36 | 0.03910 |
| 325 | 7.50 | 319.81 | 904.74 | 1208.09 | 42.00 | 0.03910 |

## Change against no cap

| cap px | roots per cell | ring length r30 per cell (px) | ring length r60 per cell (px) | owned length per cell (px) | edge count per cell | field length density (px^-1) |
|---|---|---|---|---|---|---|
| 100 | +0.0% | +0.0% | +0.0% | -39.2% | -41.6% | +0.0% |
| 225 | +0.0% | +0.0% | +0.0% | -14.4% | -15.1% | +0.0% |
| 250 | +0.0% | +0.0% | +0.0% | -11.8% | -12.5% | +0.0% |
| **275** | +0.0% | +0.0% | +0.0% | -9.5% | -10.3% | +0.0% |
| 300 | +0.0% | +0.0% | +0.0% | -8.2% | -8.9% | +0.0% |
| 325 | +0.0% | +0.0% | +0.0% | -6.8% | -7.5% | +0.0% |

## Swing across the four caps around the primary (225 to 325 px)

Range (max minus min) as a percentage of the uncapped value:

- roots per cell: 0.0%
- ring length r30 per cell (px): 0.0%
- ring length r60 per cell (px): 0.0%
- owned length per cell (px): 7.5%
- edge count per cell: 7.6%
- field length density: 0.0% (it does not use ownership)

## Owned length per cell by image (mean over interior cells, px)

| image | no cap | 100 | 225 | 250 | 275 | 300 | 325 |
|---|---|---|---|---|---|---|---|
| 542 WT  2_z06c1-2 | 988 | 733 | 883 | 902 | 920 | 940 | 949 |
| 542 WT  2_z18c1-2 | 973 | 761 | 968 | 973 | 973 | 973 | 973 |
| 543-2 | 1687 | 955 | 1430 | 1476 | 1518 | 1542 | 1580 |
| 543_3 | 1435 | 856 | 1237 | 1287 | 1328 | 1347 | 1398 |
| 543_z13c1-2 | 1714 | 820 | 1433 | 1477 | 1508 | 1511 | 1527 |
| 682_z08c1-2 | 1861 | 1030 | 1422 | 1447 | 1496 | 1515 | 1532 |
| 682_z23c-2 | 1066 | 658 | 863 | 908 | 937 | 976 | 992 |
| 682_z29c1-3 | 849 | 570 | 767 | 804 | 841 | 846 | 849 |
