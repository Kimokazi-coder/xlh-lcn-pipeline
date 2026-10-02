# B1 The band-wall filter at the two evidence settings

Pre-validation, px, (x, y) = (column, row). `BAND_LINE_FILTER` has **no recommended value**
(`B1_straight_runs.md`); it stays off. Here it is turned on alone, every other switch off, at the two
evidence settings, and every changed skeleton component against the default run is listed. Removed
components are 8-connected pieces of default skeleton missing after the filter; added pieces are new
skeleton (bridges can change when the cut creates new thread ends).

## Setting L97_reach66: L 97 px, reach 66 px

| image | skeleton_px_removed | skeleton_px_added | roots_per_cell_pct | ring30_per_cell_pct | field_density_pct | bridges_before | bridges_after |
|---|---|---|---|---|---|---|---|
| 542_z06 | 103 | 0 | +0.00 | +0.00 | -0.29 | 17 | 17 |
| 542_z18 | 0 | 0 | +0.00 | +0.00 | +0.00 | 14 | 14 |
| 543-2 | 0 | 0 | +0.00 | +0.00 | +0.00 | 21 | 21 |
| 543_3 | 0 | 0 | +0.00 | +0.00 | +0.00 | 14 | 14 |
| 543_z13 | 0 | 0 | +0.00 | +0.00 | +0.00 | 19 | 19 |
| 682_z08 | 0 | 0 | +0.00 | +0.00 | +0.00 | 24 | 24 |
| 682_z23 | 0 | 0 | +0.00 | +0.00 | +0.00 | 19 | 19 |
| 682_z29 | 0 | 0 | +0.00 | +0.00 | +0.00 | 17 | 17 |


Removed components: 1 in 1 image(s), 103 px; in the 542_z06 corridor: 103 px. Added components: 0, 0 px.

| image | x | y | pixels | length_px | orientation_deg | in_542_z06_corridor |
|---|---|---|---|---|---|---|
| 542_z06 | 530 | 768 | 103 | 102.0 | 89.6 | True |


Crops (before: removed pixels vermillion; after: added pixels sky blue; canal mask magenta): `B1_crops_L97_reach66_1.png` to `_1.png`, every removed component.

## Setting L40_reach0: L 40 px, reach 0 px

| image | skeleton_px_removed | skeleton_px_added | roots_per_cell_pct | ring30_per_cell_pct | field_density_pct | bridges_before | bridges_after |
|---|---|---|---|---|---|---|---|
| 542_z06 | 473 | 0 | -1.79 | -2.87 | -1.35 | 17 | 17 |
| 542_z18 | 353 | 0 | -2.20 | -2.24 | -1.03 | 14 | 14 |
| 543-2 | 0 | 0 | +0.00 | +0.00 | +0.00 | 21 | 21 |
| 543_3 | 0 | 0 | +0.00 | +0.00 | +0.00 | 14 | 14 |
| 543_z13 | 0 | 0 | +0.00 | +0.00 | +0.00 | 19 | 19 |
| 682_z08 | 706 | 0 | +0.00 | +0.00 | -2.00 | 24 | 24 |
| 682_z23 | 883 | 0 | +0.00 | -0.71 | -2.25 | 19 | 19 |
| 682_z29 | 1749 | 3 | +0.00 | +0.00 | -4.55 | 17 | 18 |


Removed components: 68 in 5 image(s), 4164 px; in the 542_z06 corridor: 53 px. Added components: 1, 3 px.

| image | x | y | pixels | length_px | orientation_deg | in_542_z06_corridor |
|---|---|---|---|---|---|---|
| 682_z29 | 319 | 138 | 300 | 104.2 | 175.9 | False |
| 682_z29 | 330 | 66 | 240 | 119.0 | 154.3 | False |
| 682_z08 | 53 | 21 | 158 | 87.0 | 39.4 | False |
| 682_z29 | 213 | 99 | 128 | 124.3 | 85.8 | False |
| 682_z23 | 102 | 105 | 125 | 115.3 | 174.2 | False |
| 542_z06 | 581 | 68 | 118 | 120.0 | 100.7 | False |
| 682_z08 | 204 | 68 | 106 | 47.8 | 68.1 | False |
| 682_z23 | 331 | 152 | 104 | 57.0 | 112.4 | False |
| 682_z29 | 542 | 59 | 104 | 63.0 | 36.3 | False |
| 682_z29 | 253 | 106 | 90 | 49.6 | 80.8 | False |
| 682_z29 | 621 | 70 | 82 | 83.8 | 70.2 | False |
| 682_z29 | 592 | 133 | 76 | 75.0 | 74.6 | False |
| 682_z08 | 496 | 132 | 69 | 67.0 | 93.6 | False |
| 682_z23 | 618 | 53 | 65 | 73.8 | 58.2 | False |
| 682_z23 | 299 | 166 | 63 | 56.8 | 71.0 | False |
| 682_z29 | 198 | 112 | 62 | 58.1 | 90.8 | False |
| 682_z08 | 414 | 121 | 60 | 54.3 | 94.7 | False |
| 682_z29 | 160 | 84 | 58 | 55.1 | 88.1 | False |
| 682_z23 | 256 | 80 | 56 | 50.0 | 178.9 | False |
| 682_z29 | 514 | 94 | 55 | 55.3 | 77.2 | False |


Crops (before: removed pixels vermillion; after: added pixels sky blue; canal mask magenta): `B1_crops_L40_reach0_1.png` to `_5.png`, every removed component.

## Against the expectation

The overnight report expected about 380 skeleton px removed from 542_z06 (about 1.1% of its skeleton,
field density about -1.1%) and no change elsewhere. Nothing was adjusted to reach that. Neither evidence
setting does it:
- L 97, reach 66: 103 px removed, all in 542_z06 (the straight middle of the
  line, about a quarter of it); field density -0.29% there;
  no roots, ring 30 px or bridges change; no other image changes. It needs a reach of 66 px from the canal
  mask, which is not a continuation of the canal.
- L 40, reach 0: 4164 px removed in 5 images,
  field density -4.55 to +0.00%. Only a small part is
  the line; most removed pieces are wall pieces inside the canal masks of 542_z06 and 542_z18 and
  ordinary threads (the horizontal and vertical lattice threads of the 682 images) that touch a canal mask.

So the switch stays off, with no recommended value.
