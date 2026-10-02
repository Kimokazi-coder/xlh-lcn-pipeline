# Field summary

PRE-VALIDATION, pixel units. **The field is the unit of analysis.** Optical sections of one field
repeat the same cells, so they are not independent samples; the value of a field is the mean over
its images.

Fields derived from the data: lacunae matched one to one by centroid within 25 px, no
shift; two images are linked when the matched share of the smaller image lies above the largest gap
in the sorted shares (cut 0.58) and is at least 0.5. An image with no link is its own field.

- F1: 542_WT_2_z06c1-2 + 542_WT_2_z18c1-2 (2 images)
- F2: 543-2 + 543_3 + 543_z13c1-2 (3 images)
- F3: 682_z08c1-2 (1 image)
- F4: 682_z23c-2 + 682_z29c1-3 (2 images)

| field | images | roots per cell | roots per 100 px perimeter | ring 30 px per cell (px) | ring density 30 px (px^-1) | ring density 60 px (px^-1) | field density (px^-1) |
|---|---|---|---|---|---|---|---|
| F1 | 2 | 8.44 | 2.65 | 359.28 | 0.03088 | 0.03414 | 0.03436 |
| F2 | 3 | 7.07 | 3.20 | 307.68 | 0.03509 | 0.04354 | 0.04455 |
| F3 | 1 | 10.00 | 3.54 | 396.75 | 0.03801 | 0.04005 | 0.03465 |
| F4 | 2 | 6.14 | 2.96 | 266.82 | 0.03177 | 0.03511 | 0.03789 |

Pairs (field_pairs.csv):

| image a | image b | matches | share of smaller | linked |
|---|---|---|---|---|
| 542_WT_2_z06c1-2 | 542_WT_2_z18c1-2 | 11 | 0.92 | True |
| 543-2 | 543_z13c1-2 | 10 | 0.91 | True |
| 543-2 | 543_3 | 9 | 0.90 | True |
| 543_3 | 543_z13c1-2 | 8 | 0.80 | True |
| 682_z23c-2 | 682_z29c1-3 | 10 | 0.77 | True |
| 682_z08c1-2 | 682_z23c-2 | 4 | 0.40 | False |
| 682_z08c1-2 | 682_z29c1-3 | 1 | 0.10 | False |

Pairs not listed share no lacuna.

## Notes (B3)

`python src/diagnostics.py field-summary -d DIR -o OUT [-r RESULTS]` (options: `-w` processes). Without
`-r` it runs the pipeline (fast lacuna stage, identical labels); with `-r` it reads existing
`lacunae.json` and `canaliculi_measurements.json`. Both ways gave byte-identical CSV files here. The
groups equal those of the overnight report (6.1). 682_z08 shares 4 of its 10 lacunae with 682_z23,
below the 0.5 guard, so it stays a field of its own: whether it belongs to the 682 field is listed
under Decisions needed. Per-field values are means over the field's images of the image means
(interior cells), so each field counts once.
