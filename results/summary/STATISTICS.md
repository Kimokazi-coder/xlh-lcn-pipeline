# Statistics: genotype by diet (pre-validation)

**Pre-validation.** Every number comes from the pipeline's own detection, not yet checked against
manual counts. The animal mapping (`data/animals.csv`) is from the file names and is **not confirmed**
(column `confirmed` = no); animal 701 carries no diet label in its file names and is HP only because
its images are in `data/Hyp_HP`. To be checked with Dr. Murshed.

Mode: FINAL. Every image, the held-out ones included.

Design: 2 x 2, genotype (WT, Hyp) by diet (regular RD, high phosphate HP), the animal is the unit.
The question is the **interaction**: is the diet effect in Hyp different from the diet effect in WT?
The interaction below is (Hyp HP minus Hyp RD) minus (WT HP minus WT RD).

## Animals per group

| group | animals | images |
| - | - | - |
| WT | 3 (542, 543, 682) | 8 |
| WT_HP | 3 (872, 876, 877) | 9 |
| Hyp_RD | 3 (535, 536, I534) | 9 |
| Hyp_HP | 3 (548, 699, 701) | 9 |

## Per group (every measured lacuna of the group pooled)

| group | n lacunae | median (um2) | 90th percentile (um2) | above 2 x WT median | POL area per analysed area | roots per lacuna | field length density (um per um2) |
| - | - | - | - | - | - | - | - |
| WT | 85 | 36.79 | 66.71 | 5.9% | 2.8% | 10.69 | 0.298 |
| WT_HP | 83 | 31.21 | 77.90 | 10.8% | 2.7% | 11.02 | 0.361 |
| Hyp_RD | 172 | 38.48 | 87.26 | 18.0% | 6.9% | 9.50 | 0.193 |
| Hyp_HP | 145 | 23.83 | 96.86 | 17.2% | 6.7% | 9.18 | 0.243 |

## Per animal

| animal | group | images | n lacunae | median (um2) | 90th percentile (um2) | above 2 x WT median | POL area per analysed area | roots per lacuna | ring length 3.9 um (um) | field length density | width median (um) |
| - | - | - | - | - | - | - | - | - | - | - | - |
| 542 | WT | 2 | 23 | 54.94 | 78.53 | 21.7% | 3.9% | 14.22 | 64.99 | 0.302 | 1.07 |
| 543 | WT | 3 | 33 | 34.92 | 51.65 | 0.0% | 2.2% | 8.52 | 47.86 | 0.317 | 1.04 |
| 682 | WT | 3 | 29 | 31.32 | 59.44 | 0.0% | 2.6% | 10.38 | 52.41 | 0.276 | 1.04 |
| 872 | WT_HP | 3 | 36 | 25.43 | 52.31 | 0.0% | 2.9% | 11.03 | 60.57 | 0.298 | 1.04 |
| 876 | WT_HP | 3 | 22 | 32.70 | 46.34 | 0.0% | 1.9% | 11.00 | 85.58 | 0.533 | 0.78 |
| 877 | WT_HP | 3 | 25 | 46.66 | 100 | 36.0% | 3.3% | 11.04 | 51.20 | 0.24 | 1.04 |
| 535 | Hyp_RD | 3 | 56 | 38.12 | 118 | 19.6% | 6.5% | 8.02 | 32.79 | 0.175 | 1.04 |
| 536 | Hyp_RD | 3 | 48 | 46.26 | 75.38 | 16.7% | 4.7% | 10.44 | 40.34 | 0.193 | 1.04 |
| I534 | Hyp_RD | 3 | 68 | 34.11 | 86.97 | 17.6% | 9.7% | 10.06 | 35.81 | 0.214 | 1.07 |
| 548 | Hyp_HP | 3 | 50 | 25.80 | 98.59 | 26.0% | 6.0% | 9.68 | 39.79 | 0.208 | 1.04 |
| 699 | Hyp_HP | 3 | 42 | 23.84 | 54.23 | 9.5% | 5.4% | 7.43 | 37.18 | 0.151 | 0.937 |
| 701 | Hyp_HP | 3 | 53 | 23.02 | 84.03 | 15.1% | 9.1% | 10.09 | 52.25 | 0.399 | 0.78 |

## The interaction, animal level (the primary analysis)

One value per animal, least squares, y ~ genotype x diet; 95% t interval. Effects in the measure's
unit (shares in percentage points).

| measure | WT RD mean | Hyp on RD | HP in WT | interaction | 95% interval | p | what it says |
| - | - | - | - | - | - | - | - |
| median lacunar area (um2) | 40.39 | -0.896 um2 | -5.46 um2 | **-9.82 um2** | -33.59 um2 to +13.96 um2 | 0.37 | the interval includes zero: no interaction can be claimed; with 3 animals per group (8 degrees of freedom) only an interaction of about 32.94 um2 or more, either way, would be found 4 times in 5 |
| 90th percentile of lacunar area (um2) | 63.20 | +30.41 um2 | +3.16 um2 | **-17.83 um2** | -78.56 um2 to +42.90 um2 | 0.52 | the interval includes zero: no interaction can be claimed; with 3 animals per group (8 degrees of freedom) only an interaction of about 84.14 um2 or more, either way, would be found 4 times in 5 |
| share of lacunae above 2 x the WT median (share) | 7.2% | +10.7 points | +4.8 points | **-5.9 points** | -40.1 points to +28.4 points | 0.70 | the interval includes zero: no interaction can be claimed; with 3 animals per group (8 degrees of freedom) only an interaction of about 47.5 points or more, either way, would be found 4 times in 5 |
| share of lacunae above 100 um2 (share) | 1.4% | +6.9 points | +2.6 points | **-1.9 points** | -14.8 points to +10.9 points | 0.74 | the interval includes zero: no interaction can be claimed; with 3 animals per group (8 degrees of freedom) only an interaction of about 17.8 points or more, either way, would be found 4 times in 5 |
| POL area per analysed area (share) | 2.9% | +4.1 points | -0.2 points | **+0.0 points** | -4.5 points to +4.6 points | 0.98 | the interval includes zero: no interaction can be claimed; with 3 animals per group (8 degrees of freedom) only an interaction of about 6.3 points or more, either way, would be found 4 times in 5 |
| roots per lacuna (count) | 11.04 | -1.53 count | -0.0147 count | **-0.422 count** | -5.07 count to +4.23 count | 0.84 | the interval includes zero: no interaction can be claimed; with 3 animals per group (8 degrees of freedom) only an interaction of about 6.44 count or more, either way, would be found 4 times in 5 |
| ring length within 3.9 um per lacuna (um) | 55.09 | -18.77 um | +10.69 um | **-3.94 um** | -32.92 um to +25.05 um | 0.76 | the interval includes zero: no interaction can be claimed; with 3 animals per group (8 degrees of freedom) only an interaction of about 40.15 um or more, either way, would be found 4 times in 5 |
| field length density (um per um2) | 0.298 | -0.104 um per um2 | +0.0584 um per um2 | **+0.000391 um per um2** | -0.272 um per um2 to +0.272 um per um2 | 1.00 | the interval includes zero: no interaction can be claimed; with 3 animals per group (8 degrees of freedom) only an interaction of about 0.377 um per um2 or more, either way, would be found 4 times in 5 |
| median canalicular width (um) | 1.05 | -4.84e-17 um | -0.0973 um | **-0.0342 um** | -0.302 um to +0.233 um | 0.78 | the interval includes zero: no interaction can be claimed; with 3 animals per group (8 degrees of freedom) only an interaction of about 0.371 um or more, either way, would be found 4 times in 5 |

## The interaction, mixed models

Every lacuna or every image, with animal as a random intercept, statsmodels MixedLM, REML, 95%
Wald interval. With so few animals these intervals do not correct for the small number of groups
and are too narrow. (With the image nested inside the animal as well, the per-lacuna fits were
degenerate, so the image is not modelled.)

| measure | model | units | interaction | 95% interval | p | fit usable | what it says |
| - | - | - | - | - | - | - | - |
| lacunar area (um2) | mixed, per lacuna, animal random | 485 | **-4.49 um2** | -22.91 um2 to +13.93 um2 | 0.63 | yes | the interval includes zero; 12 animals, so this interval is too narrow; read the animal-level line |
| roots per lacuna (count) | mixed, per lacuna, animal random | 485 | **-0.509 count** | -4.31 count to +3.29 count | 0.79 | yes | the interval includes zero; 12 animals, so this interval is too narrow; read the animal-level line |
| ring length within 3.9 um per lacuna (um) | mixed, per lacuna, animal random | 485 | **-3.81 um** | -27.54 um to +19.92 um | 0.75 | yes | the interval includes zero; 12 animals, so this interval is too narrow; read the animal-level line |
| 90th percentile of lacunar area (um2) | mixed, per image, animal random | 35 | **-8.09 um2** | -54.79 um2 to +38.61 um2 | 0.73 | yes | the interval includes zero; 12 animals, so this interval is too narrow; read the animal-level line |
| share of lacunae above 2 x the WT median (share) | mixed, per image, animal random | 35 | **-6.5 points** | -36.2 points to +23.1 points | 0.67 | yes | the interval includes zero; 12 animals, so this interval is too narrow; read the animal-level line |
| field length density (um per um2) | mixed, per image, animal random | 35 | **-0.00126 um per um2** | -0.232 um per um2 to +0.23 um per um2 | 0.99 | yes | the interval includes zero; the animal variance came out as zero, so the rows count as independent; 12 animals, so this interval is too narrow; read the animal-level line |

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
