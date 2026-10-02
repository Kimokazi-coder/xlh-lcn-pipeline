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

## BAND_LINE_FILTER on, evidence setting L 97 px, reach 66 px (not a recommendation)

- **542_WT_2_z06c1-2**
  - image values: field_density 0.03465004 to 0.03454796

## BAND_LINE_FILTER on, evidence setting L 40 px, reach 0 px (not a recommendation)

- **542_WT_2_z06c1-2**
  - changed: lacuna at (555,149): roots 4 to 2, ring30 177 to 118
  - changed: lacuna at (573,482): ring30 391 to 315
  - image values: roots_per_cell 8.6154 to 8.4615; ring30_per_cell 361.4615 to 351.0769; field_density 0.03465004 to 0.03418128
- **542_WT_2_z18c1-2**
  - changed: lacuna at (639,130): roots 19 to 17, ring30 574 to 486
  - image values: roots_per_cell 8.2727 to 8.0909; ring30_per_cell 357.0909 to 349.0909; field_density 0.03407276 to 0.03372235
- **682_z08c1-2**
  - changed: lacuna at (428,32): roots 10 to 9, ring30 368 to 323
  - image values: field_density 0.03464652 to 0.03395294
- **682_z23c-2**
  - changed: lacuna at (107,13): roots 4 to 3, ring30 136 to 108
  - changed: lacuna at (472,61): ring30 294 to 272
  - image values: ring30_per_cell 283.3636 to 281.3636; field_density 0.03829817 to 0.03743478
- **682_z29c1-3**
  - changed: lacuna at (99,13): ring30 187 to 150
  - image values: field_density 0.03748464 to 0.03577884; bridges 17 to 18
