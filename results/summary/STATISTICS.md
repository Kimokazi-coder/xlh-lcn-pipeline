# Statistics: genotype by diet (pre-validation)

**Pre-validation.** Every number comes from the pipeline's own detection, not yet checked against
manual counts. The animal mapping (`data/animals.csv`) is from the file names and is **not confirmed**
(column `confirmed` = no); animal 701 carries no diet label in its file names and is HP only because
its images are in `data/Hyp_HP`. To be checked with Dr. Murshed.

Mode: DEV. The held-out images are left out (DEV mode), so some animals have fewer images here than in the data set.

Design: 2 x 2, genotype (WT, Hyp) by diet (regular RD, high phosphate HP), the animal is the unit.
The question is the **interaction**: is the diet effect in Hyp different from the diet effect in WT?
The interaction below is (Hyp HP minus Hyp RD) minus (WT HP minus WT RD).

## Animals per group

| group | animals | images |
| - | - | - |
| WT | 3 (542, 543, 682) | 6 |
| WT_HP | 3 (872, 876, 877) | 7 |
| Hyp_RD | 3 (535, 536, I534) | 7 |
| Hyp_HP | 3 (548, 699, 701) | 7 |

## Per group (every measured lacuna of the group pooled)

| group | n lacunae | median (um2) | 90th percentile (um2) | above 2 x WT median | POL area per analysed area | roots per lacuna | field length density (um per um2) |
| - | - | - | - | - | - | - | - |
| WT | 62 | 39.86 | 69.83 | 3.2% | 2.9% | 11.29 | 0.294 |
| WT_HP | 68 | 31.16 | 63.85 | 7.3% | 2.8% | 11.29 | 0.352 |
| Hyp_RD | 127 | 38.43 | 88.01 | 12.6% | 6.3% | 9.43 | 0.193 |
| Hyp_HP | 111 | 24.69 | 95.62 | 15.3% | 6.0% | 8.90 | 0.205 |

## Per animal

| animal | group | images | n lacunae | median (um2) | 90th percentile (um2) | above 2 x WT median | POL area per analysed area | roots per lacuna | ring length 3.9 um (um) | field length density | width median (um) |
| - | - | - | - | - | - | - | - | - | - | - | - |
| 542 | WT | 2 | 23 | 54.94 | 78.53 | 8.7% | 3.9% | 14.22 | 64.99 | 0.302 | 1.07 |
| 543 | WT | 2 | 21 | 34.68 | 56.62 | 0.0% | 2.1% | 8.52 | 47.76 | 0.309 | 1.04 |
| 682 | WT | 2 | 18 | 34.36 | 59.61 | 0.0% | 2.6% | 10.78 | 53.92 | 0.271 | 1.04 |
| 872 | WT_HP | 3 | 36 | 25.43 | 52.31 | 0.0% | 2.9% | 11.03 | 60.57 | 0.298 | 1.04 |
| 876 | WT_HP | 2 | 15 | 33.16 | 52.09 | 0.0% | 2.1% | 11.27 | 87.72 | 0.535 | 0.78 |
| 877 | WT_HP | 2 | 17 | 46.66 | 100 | 29.4% | 3.2% | 11.88 | 53.62 | 0.236 | 1.04 |
| 535 | Hyp_RD | 2 | 36 | 36.79 | 122 | 19.4% | 6.3% | 7.83 | 31.96 | 0.176 | 1.04 |
| 536 | Hyp_RD | 3 | 48 | 46.26 | 75.38 | 6.2% | 4.7% | 10.44 | 40.34 | 0.193 | 1.04 |
| I534 | Hyp_RD | 2 | 43 | 34.41 | 85.79 | 14.0% | 9.2% | 9.63 | 35.78 | 0.216 | 1.06 |
| 548 | Hyp_HP | 3 | 50 | 25.80 | 98.59 | 22.0% | 6.0% | 9.68 | 39.79 | 0.208 | 1.04 |
| 699 | Hyp_HP | 3 | 42 | 23.84 | 54.23 | 9.5% | 5.4% | 7.43 | 37.18 | 0.151 | 0.937 |
| 701 | Hyp_HP | 1 | 19 | 25.35 | 75.54 | 10.5% | 8.0% | 10.11 | 53.66 | 0.379 | 0.78 |

## The interaction, animal level (the primary analysis)

One value per animal, least squares, y ~ genotype x diet; 95% t interval. Effects in the measure's
unit (shares in percentage points).

| measure | WT RD mean | Hyp on RD | HP in WT | interaction | 95% interval | p | what it says |
| - | - | - | - | - | - | - | - |
| median lacunar area (um2) | 41.33 | -2.17 um2 | -6.24 um2 | **-7.91 um2** | -30.77 um2 to +14.95 um2 | 0.45 | the interval includes zero: no interaction can be claimed; with 3 animals per group (8 degrees of freedom) only an interaction of about 31.68 um2 or more, either way, would be found 4 times in 5 |
| 90th percentile of lacunar area (um2) | 64.92 | +29.46 um2 | +3.27 um2 | **-21.52 um2** | -81.03 um2 to +37.99 um2 | 0.43 | the interval includes zero: no interaction can be claimed; with 3 animals per group (8 degrees of freedom) only an interaction of about 82.45 um2 or more, either way, would be found 4 times in 5 |
| share of lacunae above 2 x the WT median (share) | 2.9% | +10.3 points | +6.9 points | **-6.1 points** | -32.9 points to +20.7 points | 0.61 | the interval includes zero: no interaction can be claimed; with 3 animals per group (8 degrees of freedom) only an interaction of about 37.1 points or more, either way, would be found 4 times in 5 |
| share of lacunae above 100 um2 (share) | 1.4% | +7.9 points | +2.5 points | **-5.3 points** | -20.9 points to +10.3 points | 0.46 | the interval includes zero: no interaction can be claimed; with 3 animals per group (8 degrees of freedom) only an interaction of about 21.6 points or more, either way, would be found 4 times in 5 |
| POL area per analysed area (share) | 2.9% | +3.9 points | -0.1 points | **-0.1 points** | -3.9 points to +3.7 points | 0.95 | the interval includes zero: no interaction can be claimed; with 3 animals per group (8 degrees of freedom) only an interaction of about 5.3 points or more, either way, would be found 4 times in 5 |
| roots per lacuna (count) | 11.17 | -1.87 count | +0.219 count | **-0.448 count** | -5.11 count to +4.21 count | 0.83 | the interval includes zero: no interaction can be claimed; with 3 animals per group (8 degrees of freedom) only an interaction of about 6.46 count or more, either way, would be found 4 times in 5 |
| ring length within 3.9 um per lacuna (um) | 55.56 | -19.53 um | +11.75 um | **-4.23 um** | -33.92 um to +25.46 um | 0.75 | the interval includes zero: no interaction can be claimed; with 3 animals per group (8 degrees of freedom) only an interaction of about 41.13 um or more, either way, would be found 4 times in 5 |
| field length density (um per um2) | 0.294 | -0.0995 um per um2 | +0.062 um per um2 | **-0.0109 um per um2** | -0.276 um per um2 to +0.254 um per um2 | 0.93 | the interval includes zero: no interaction can be claimed; with 3 animals per group (8 degrees of freedom) only an interaction of about 0.367 um per um2 or more, either way, would be found 4 times in 5 |
| median canalicular width (um) | 1.05 | -0.00533 um | -0.0973 um | **-0.0289 um** | -0.295 um to +0.238 um | 0.81 | the interval includes zero: no interaction can be claimed; with 3 animals per group (8 degrees of freedom) only an interaction of about 0.369 um or more, either way, would be found 4 times in 5 |

## The interaction, mixed models

Every lacuna or every image, with animal as a random intercept, statsmodels MixedLM, REML, 95%
Wald interval. With so few animals these intervals do not correct for the small number of groups
and are too narrow. (With the image nested inside the animal as well, the per-lacuna fits were
degenerate, so the image is not modelled.)

| measure | model | units | interaction | 95% interval | p | fit usable | what it says |
| - | - | - | - | - | - | - | - |
| lacunar area (um2) | mixed, per lacuna, animal random | 368 | **-3.28 um2** | -23.52 um2 to +16.96 um2 | 0.75 | yes | the interval includes zero; 12 animals, so this interval is too narrow; read the animal-level line |
| roots per lacuna (count) | mixed, per lacuna, animal random | 368 | **-0.49 count** | -3.92 count to +2.94 count | 0.78 | no | the interval includes zero; 12 animals, so this interval is too narrow; read the animal-level line |
| ring length within 3.9 um per lacuna (um) | mixed, per lacuna, animal random | 368 | **-4.14 um** | -27.85 um to +19.58 um | 0.73 | yes | the interval includes zero; 12 animals, so this interval is too narrow; read the animal-level line |
| 90th percentile of lacunar area (um2) | mixed, per image, animal random | 27 | **-10.20 um2** | -60.02 um2 to +39.61 um2 | 0.69 | yes | the interval includes zero; 12 animals, so this interval is too narrow; read the animal-level line |
| share of lacunae above 2 x the WT median (share) | mixed, per image, animal random | 27 | **-5.7 points** | -30.2 points to +18.7 points | 0.65 | yes | the interval includes zero; the animal variance came out as zero, so the rows count as independent; 12 animals, so this interval is too narrow; read the animal-level line |
| field length density (um per um2) | mixed, per image, animal random | 27 | **-0.0168 um per um2** | -0.238 um per um2 to +0.204 um per um2 | 0.88 | yes | the interval includes zero; the animal variance came out as zero, so the rows count as independent; 12 animals, so this interval is too narrow; read the animal-level line |

## In plain words

- There are 3 animals per group. That is enough to estimate each effect and its interval, and
  not enough for a test to find anything but a large interaction: the last column says how large.
- An interval that includes zero means the data cannot tell whether the diet acts differently in
  Hyp than in WT; it does not show that it acts the same.
- The per-lacuna and per-image mixed models use many more rows, but the rows inside one animal are
  not independent, so their narrow intervals overstate the certainty.
- Everything rests on the AI-reviewed, not manually validated, lacuna detection and on the
  unconfirmed animal mapping.

Made by `python src/animal_stats.py run`; the numbers are also in `per_animal.csv`, `per_group.csv`,
`per_image.csv` and `statistics_models.csv` beside this file, and in `results/SUMMARY.xlsx`.
