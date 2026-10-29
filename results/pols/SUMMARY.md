# POL proxy: summary by group

**Pre-validation.** POL proxy, not a measurement of periosteocytic lesions: the bright lacuna body
plus the surround that stays above the bone background ([DEFINITION.md](DEFINITION.md)). In WT, which
has no lesions, the surround is optical glow ([FINDINGS.md](FINDINGS.md)). Descriptive only: no test
was run and no difference is claimed. Units um and um2 (0.13 um/px).

Each value is the mean over the group's images of the per-image mean over its measured lacunae
(shape measure and no flag), with the SD between images in brackets. Made by
`python src/pols.py summary` from `results/<group>/pols/<group>_pols_per_image.csv`.

| group | images | lacunae | with shape measure | flagged | measured | body area | outer area | POL area | POL ratio | halo width, median of sectors |
| - | - | - | - | - | - | - | - | - | - | - |
| WT | 8 (8 with a measured lacuna) | 108 | 100 | 29 (27% per image) | 71 | 42.1 (12.4) | 139.8 (30.5) | 97.8 (20.4) | 3.99 (1.14) | 2.32 (0.36) |
| WT_HP | 9 (9 with a measured lacuna) | 121 | 113 | 58 (50% per image) | 55 | 39.1 (18.8) | 153.1 (68.7) | 114.0 (51.1) | 5.07 (1.48) | 2.55 (0.61) |
| Hyp_RD | 9 (9 with a measured lacuna) | 277 | 251 | 165 (63% per image) | 86 | 50.7 (14.3) | 148.3 (44.4) | 97.6 (32.4) | 4.17 (1.32) | 2.00 (0.41) |
| Hyp_HP | 9 (7 with a measured lacuna) | 287 | 250 | 223 (89% per image) | 27 | 46.3 (29.1) | 214.3 (72.3) | 168.0 (69.1) | 8.70 (7.54) | 3.00 (1.55) |

Flagged lacunae are listed in the per-lacuna tables but are in no mean. Images with no
measured lacuna count in the images column and add nothing to the means.

## Sensitivity: the neighbour flag not applied

Not the result. The same group means (mean over images of the per-image mean) with the
neighbour flag left out and every other flag kept, because the Hyp fields are packed so densely
that this one flag decides which of their lacunae are measured.

| group | images with a measured lacuna | measured lacunae | outer area | POL area | POL ratio | halo width, median of sectors |
| - | - | - | - | - | - | - |
| WT | 8 | 78 | 136.9 | 96.1 | 3.99 | 2.31 |
| WT_HP | 9 | 74 | 148.5 | 111.7 | 5.06 | 2.55 |
| Hyp_RD | 9 | 148 | 142.4 | 95.5 | 4.21 | 2.03 |
| Hyp_HP | 9 | 73 | 161.0 | 119.7 | 6.56 | 2.51 |
