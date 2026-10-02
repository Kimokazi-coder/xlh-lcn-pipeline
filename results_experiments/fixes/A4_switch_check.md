# switch-check

Pre-validation, px. Each switch of config.py on alone, all others off, every image
regenerated into F:\lcn-quant\results_experiments\_cache\switch_check and compared with F:\lcn-quant\results. Lacunae are matched by centroid
within 10 px; a lacuna is listed when its area, roots or ring 30 px change.

## NARROW_CRUMB_RULE = True

- **543_3**
  - changed: lacuna at (877,545): area 1344 to 1468, roots 6 to 5, ring30 277 to 269
  - image values: roots_per_cell 6.8889 to 6.7778; ring30_per_cell 313.5556 to 312.6667; field_density 0.04513983 to 0.0451375

## FILL_ENCLOSED_HOLES_MAX_PX2 = 200

- **542_WT_2_z06c1-2**
  - changed: lacuna at (783,581): area 3414 to 3560
  - image values: field_density 0.03465004 to 0.03465505

## BAND_FILTER_MIN_OPENING_SHARE = 0.515

- **542_WT_2_z06c1-2**
  - removed: lacuna at (555,149), 445 px^2
  - changed: lacuna at (635,143): ring30 200 to 201
  - image values: lacuna_count 16 to 15; interior_count 13 to 12; roots_per_cell 8.6154 to 9.0; ring30_per_cell 361.4615 to 376.9167; field_density 0.03465004 to 0.03468429
- **682_z23c-2**
  - removed: lacuna at (363,7), 448 px^2, frame edge
  - image values: lacuna_count 14 to 13; field_density 0.03829817 to 0.03834493
## Against the overnight report

| switch | expected (docs/OVERNIGHT_REPORT.md) | found |
|---|---|---|
| NARROW_CRUMB_RULE | only 543_3 (877,545): area 1344 to 1468, roots 6 to 5, ring 30 277 to 269 px | the same, nothing else |
| FILL_ENCLOSED_HOLES_MAX_PX2 = 200 | only 542_z06 (783,581), +146 px^2 | the same (3414 to 3560), nothing else |
| BAND_FILTER_MIN_OPENING_SHARE = 0.515 | only 542_z06 (555,149) and 682_z23 (363,7) | the same two removed; the neighbour 542_z06 (635,143) gains 1 px of ring 30, as the overnight 3.6 reading describes |

No difference from the expectation. Nothing was adjusted.
