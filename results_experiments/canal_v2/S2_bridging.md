# S2 Bridging audit

Pre-validation, px, (x, y) = (column, row). Every bridge of the default run: the two endpoints, the gap
length, the angle between the thread and the gap, and the signal along the gap as a fraction of t_lo
(the minimum is the pipeline's test, at least 0.7; the mean is computed here). The bridging parameters
are not changed. 145 bridges over 8 images; all bridges: `S2_bridges.csv`.

## Bridges per image

| image | bridges | gap_median | gap_max | angle_median | min_signal_median | mean_signal_median | gap_px | gap px share of skeleton % |
|---|---|---|---|---|---|---|---|---|
| 542_z06 | 17 | 5.657 | 9.000 | 12.530 | 0.722 | 0.836 | 73 | 0.209 |
| 542_z18 | 14 | 5.242 | 8.062 | 22.210 | 0.720 | 0.837 | 59 | 0.172 |
| 543-2 | 21 | 4.123 | 9.000 | 11.310 | 0.720 | 0.890 | 76 | 0.166 |
| 543_3 | 14 | 5.192 | 8.062 | 12.675 | 0.720 | 0.836 | 59 | 0.127 |
| 543_z13 | 19 | 4.000 | 6.708 | 11.310 | 0.721 | 0.826 | 53 | 0.118 |
| 682_z08 | 24 | 4.736 | 8.062 | 12.210 | 0.720 | 0.864 | 90 | 0.255 |
| 682_z23 | 19 | 4.000 | 8.944 | 12.530 | 0.714 | 0.783 | 65 | 0.166 |
| 682_z29 | 17 | 5.385 | 8.246 | 14.040 | 0.718 | 0.988 | 76 | 0.198 |


## What depends on bridging

The share of each measure that bridging adds: (default minus the run with no bridging, from the network
sweep S1, MAX_BRIDGE_GAP_PX = 0) over the default, per image. Negative means the measure is larger
without bridges.

| image | bridges | roots per cell: share from bridging % | ring 30 px: share from bridging % | field density: share from bridging % | ring attached 30 px: share from bridging % | Sholl 10 px: share from bridging % | Sholl 30 px: share from bridging % |
|---|---|---|---|---|---|---|---|
| 542_WT_2_z06c1-2 | 17 | -0.89 | +0.15 | +0.19 | +0.14 | +0.00 | +0.00 |
| 542_WT_2_z18c1-2 | 14 | -1.10 | +0.15 | +0.16 | +0.87 | +0.00 | +0.61 |
| 543-2 | 21 | +0.00 | +0.00 | +0.15 | +0.00 | +0.00 | +0.00 |
| 543_3 | 14 | +0.00 | +0.04 | +0.11 | +0.00 | +0.00 | +0.00 |
| 543_z13c1-2 | 19 | -1.35 | +0.00 | +0.11 | +0.00 | +0.00 | +0.00 |
| 682_z08c1-2 | 24 | +0.00 | +0.00 | +0.23 | +0.00 | +0.00 | +0.00 |
| 682_z23c-2 | 19 | +0.00 | +0.06 | +0.15 | +0.00 | +0.00 | +0.00 |
| 682_z29c1-3 | 17 | +0.00 | +0.36 | +0.19 | +0.72 | +0.00 | +0.00 |


Over the 8 images: roots per cell -1.35 to +0.00% (median +0.00%); ring 30 px +0.00 to +0.36% (median +0.05%); field density +0.11 to +0.23% (median +0.15%); ring attached 30 px +0.00 to +0.87% (median +0.00%); Sholl 10 px +0.00 to +0.00% (median +0.00%); Sholl 30 px +0.00 to +0.61% (median +0.00%).

Bridging adds a few px per gap: the gap pixels are 0.12 to 0.26% of the skeleton. Its effect on roots comes through connectivity: a bridged thread can reach a lacuna
node, or two attachment points can merge. Ring 30 px and field density follow the added pixels.

## Crops

`S2_bridges_<image>.png`: one tile per bridge, a 48 px square at 4x centred on the gap; skeleton white,
the bridge pixels sky blue (the gap as drawn into the mask before re-skeletonization).
