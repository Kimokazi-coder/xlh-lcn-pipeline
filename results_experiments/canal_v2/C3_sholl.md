# C3 Sholl crossings

Pre-validation, px. New per-lacuna columns `sholl_crossings_r10`, `_r20`, `_r30` (interior means in the summary).
The band of a lacuna at radius $R$ is the part of its nearest-lacuna partition whose distance to the lacuna
masks lies in $[R - 0.75, R + 0.75)$, inside the frame.
The count is the number of 8-connected skeleton components inside the band. It uses no graph, no cleanup,
no attach gap and no ownership; it does use the skeleton, so the cuts and the bridging still reach it.

Limits: a thread running along the band counts once however long it is; a branch point inside the band
joins two threads into one component; a thread that leaves the band and comes back counts twice; near
another lacuna the band is cut by the partition, and near the frame by the frame. The band is 1.5 px wide,
wider than the longest step between neighbouring pixels ($\sqrt{2}$), so a thread cannot cross it
unseen.

All counts are non-negative integers (asserted). Interior lacunae: n = 86.

## Distribution and Spearman correlations (interior lacunae, pooled)

| crossings at | mean | median | min | max | rho with roots | p roots | rho with area | p area |
|---|---|---|---|---|---|---|---|---|
| 10 px | 8.477 | 8.000 | 2 | 21 | 0.898 | 0.000 | 0.646 | 0.000 |
| 20 px | 12.070 | 12.000 | 3 | 23 | 0.718 | 0.000 | 0.655 | 0.000 |
| 30 px | 14.163 | 14.000 | 6 | 26 | 0.534 | 0.000 | 0.559 | 0.000 |
| roots_count | 7.500 | 7.000 | 2 | 19 | 1.000 | 0.000 | 0.687 | 0.000 |


## Per image (means over interior lacunae)

| image | cells | roots | sholl_r10 | sholl_r20 | sholl_r30 | r30 below r10 |
|---|---|---|---|---|---|---|
| 542_z06 | 13 | 8.62 | 9.77 | 12.54 | 14.00 | 1 |
| 542_z18 | 11 | 8.27 | 9.36 | 13.27 | 14.82 | 1 |
| 543-2 | 12 | 7.58 | 8.58 | 12.00 | 14.58 | 1 |
| 543_3 | 9 | 6.89 | 7.78 | 13.22 | 16.00 | 0 |
| 543_z13 | 11 | 6.73 | 8.09 | 11.73 | 14.27 | 0 |
| 682_z08 | 8 | 10.00 | 10.75 | 14.25 | 16.00 | 0 |
| 682_z23 | 11 | 6.73 | 7.45 | 10.82 | 13.00 | 0 |
| 682_z29 | 11 | 5.55 | 6.27 | 9.45 | 11.45 | 0 |


## Fewer crossings further out

Crossings at 30 px below crossings at 10 px: 3 of 86 cells (3%); equal: 3; more: 80. Fewer crossings further out mean threads
that merge or end between 10 and 30 px; more mean threads that branch or enter the band from the side.

## Crops

`C3_crops.png` at 4x: 543-2 L6 (746,472); 543-2 L4 (39,297). The first is the 543-2 cell closest to the median roots among cells at least 100 px from the frame; the second has the largest drop from 10 to
30 px. Bands tinted (10 px orange, 20 px sky blue, 30 px green); white: skeleton pixels in a band; grey: other
skeleton; cyan: the lacuna. The counts in the crop equal the pipeline columns (asserted).
Per-lacuna values: `C3_sholl.csv`.
