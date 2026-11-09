# Judge on against judge off (development images, 2026-11-09)

Pre-validation; no judge verdict is validated. Development images only (27 of 35): the held-out images were judged in the full run but are not read here. Made by `python src/diagnostics.py judge-compare` (DEV mode) from the saved results of three sets: judge off (the method, tag method-freeze-v2), lacuna judge on (`<section>/ai_judge/`) and both judges on (`<section>/ai_judge_canaliculi/`, the canaliculi judge on the accepted lacunae). Group values are computed as in `results/SUMMARY.xlsx` (every measured lacuna of the group pooled); each set's share above 2 x the WT median is against the WT median of its own development images. Judge on is the lacuna judge for the lacuna measures (both judge-on sets have the same lacunae) and both judges for the canaliculi measures where that set is complete for the group; where it is not, the canaliculi measures are those of the lacuna judge set, whose threads are traced deterministically on the accepted lacunae, and the last column says so. A blank both judges on column means that set is incomplete for the group.

**The POL judge** (docs/METHODS.md 30) was applied after the lacuna judge: the lacuna judge's set is now the lacuna and POL judges on, and the column before it is the lacuna judge alone, from the table written before the POL judge (`judge_on_vs_off_before_pol_judge.csv`). The both judges on set keeps the lacunae of the lacuna judge alone.

## WT

| measure | judge off | lacuna judge alone (before the POL judge) | lacuna and POL judges on | both judges on | judge on minus off | judge on from |
| - | - | - | - | - | - | - |
| development images | 6 | 6 | 6 | 6 | 0 | lacuna and POL judges on |
| lacunae, every one (frame ones included) | 71 | 73 | 72 | 73 | 1 | lacuna and POL judges on |
| measured lacunae (inside the frame, with an area) | 62 | 61 | 61 | 61 | -1 | lacuna and POL judges on |
| median lacunar area, um2 | 39.86 | 38.31 | 38.31 | 38.31 | -1.546 | lacuna and POL judges on |
| 90th percentile of lacunar area, um2 | 69.83 | 69.85 | 69.85 | 69.85 | 0.0169 | lacuna and POL judges on |
| the WT median the share is against, um2 (development WT images of the same set) | 39.86 | 38.31 | 38.31 | 38.31 | -1.546 | lacuna and POL judges on |
| share of measured lacunae above 2 x the WT median | 0.0323 | 0.0656 | 0.0656 | 0.0656 | 0.0333 | lacuna and POL judges on |
| POL area per analysed area | 0.0287 | 0.0267 | 0.0267 | 0.0267 | -0.002 | lacuna and POL judges on |
| clusters (measured lacunae flagged cluster) | 0 | 0 | 0 | 0 | 0 | lacuna and POL judges on |
| roots per lacuna | 11.29 | 11.2 | 11.3 | 11.9 | 0.6113 | both judges on |
| ring length within 3.9 um per lacuna, um | 55.94 | 55.61 | 55.97 | 61.06 | 5.122 | both judges on |
| field length density, um per um2 | 0.2944 | 0.2903 | 0.2903 | 0.2982 | 0.0038 | both judges on |
| median canalicular width, um | 1.04 | 1.04 | 1.04 | 1.04 | 0 | both judges on |

## WT_HP

| measure | judge off | lacuna judge alone (before the POL judge) | lacuna and POL judges on | both judges on | judge on minus off | judge on from |
| - | - | - | - | - | - | - |
| development images | 7 | 7 | 7 | 7 | 0 | lacuna and POL judges on |
| lacunae, every one (frame ones included) | 83 | 78 | 77 | 78 | -6 | lacuna and POL judges on |
| measured lacunae (inside the frame, with an area) | 68 | 59 | 58 | 59 | -10 | lacuna and POL judges on |
| median lacunar area, um2 | 31.16 | 32.28 | 32.19 | 32.28 | 1.022 | lacuna and POL judges on |
| 90th percentile of lacunar area, um2 | 63.85 | 64.19 | 69.87 | 64.19 | 6.027 | lacuna and POL judges on |
| the WT median the share is against, um2 (development WT images of the same set) | 39.86 | 38.31 | 38.31 | 38.31 | -1.546 | lacuna and POL judges on |
| share of measured lacunae above 2 x the WT median | 0.0735 | 0.1017 | 0.1034 | 0.1017 | 0.0299 | lacuna and POL judges on |
| POL area per analysed area | 0.0275 | 0.0246 | 0.0246 | 0.0246 | -0.0029 | lacuna and POL judges on |
| clusters (measured lacunae flagged cluster) | 0 | 0 | 0 | 0 | 0 | lacuna and POL judges on |
| roots per lacuna | 11.29 | 11.58 | 11.79 | 12.17 | 0.8754 | both judges on |
| ring length within 3.9 um per lacuna, um | 64.82 | 67.99 | 69.2 | 73.03 | 8.209 | both judges on |
| field length density, um per um2 | 0.3524 | 0.3534 | 0.3534 | 0.3597 | 0.0073 | both judges on |
| median canalicular width, um | 1.04 | 1.04 | 1.04 | 1.04 | 0 | both judges on |

## Hyp_RD

| measure | judge off | lacuna judge alone (before the POL judge) | lacuna and POL judges on | both judges on | judge on minus off | judge on from |
| - | - | - | - | - | - | - |
| development images | 7 | 7 | 7 | 7 | 0 | lacuna and POL judges on |
| lacunae, every one (frame ones included) | 147 | 115 | 102 | 115 | -45 | lacuna and POL judges on |
| measured lacunae (inside the frame, with an area) | 127 | 106 | 93 | 106 | -34 | lacuna and POL judges on |
| median lacunar area, um2 | 38.43 | 40.5 | 47.34 | 40.5 | 8.906 | lacuna and POL judges on |
| 90th percentile of lacunar area, um2 | 88.01 | 87.41 | 87.1 | 87.41 | -0.9126 | lacuna and POL judges on |
| the WT median the share is against, um2 (development WT images of the same set) | 39.86 | 38.31 | 38.31 | 38.31 | -1.546 | lacuna and POL judges on |
| share of measured lacunae above 2 x the WT median | 0.126 | 0.1509 | 0.1505 | 0.1509 | 0.0245 | lacuna and POL judges on |
| POL area per analysed area | 0.0634 | 0.0478 | 0.0442 | 0.0478 | -0.0192 | lacuna and POL judges on |
| clusters (measured lacunae flagged cluster) | 1 | 1 | 3 | 1 | 2 | lacuna and POL judges on |
| roots per lacuna | 9.425 | 9.368 | 10.13 | 10.16 | 0.7352 | both judges on |
| ring length within 3.9 um per lacuna, um | 36.42 | 36.65 | 40.13 | 40.62 | 4.2 | both judges on |
| field length density, um per um2 | 0.1935 | 0.1913 | 0.1904 | 0.1958 | 0.0023 | both judges on |
| median canalicular width, um | 1.04 | 1.04 | 1.04 | 1.04 | 0 | both judges on |

## Hyp_HP

| measure | judge off | lacuna judge alone (before the POL judge) | lacuna and POL judges on | both judges on | judge on minus off | judge on from |
| - | - | - | - | - | - | - |
| development images | 7 | 7 | 7 | 7 | 0 | lacuna and POL judges on |
| lacunae, every one (frame ones included) | 146 | 107 | 93 | 107 | -53 | lacuna and POL judges on |
| measured lacunae (inside the frame, with an area) | 111 | 82 | 76 | 82 | -35 | lacuna and POL judges on |
| median lacunar area, um2 | 24.69 | 24 | 24.47 | 24 | -0.2197 | lacuna and POL judges on |
| 90th percentile of lacunar area, um2 | 95.62 | 85.98 | 84.47 | 85.98 | -11.15 | lacuna and POL judges on |
| the WT median the share is against, um2 (development WT images of the same set) | 39.86 | 38.31 | 38.31 | 38.31 | -1.546 | lacuna and POL judges on |
| share of measured lacunae above 2 x the WT median | 0.1532 | 0.1341 | 0.1316 | 0.1341 | -0.0216 | lacuna and POL judges on |
| POL area per analysed area | 0.06 | 0.0341 | 0.0304 | 0.0341 | -0.0296 | lacuna and POL judges on |
| clusters (measured lacunae flagged cluster) | 0 | 0 | 0 | 0 | 0 | lacuna and POL judges on |
| roots per lacuna | 8.901 | 9.293 | 9.684 | 9.902 | 1.002 | both judges on |
| ring length within 3.9 um per lacuna, um | 41.18 | 42.58 | 44.86 | 45.71 | 4.532 | both judges on |
| field length density, um per um2 | 0.2046 | 0.2029 | 0.2016 | 0.2067 | 0.002 | both judges on |
| median canalicular width, um | 1.04 | 1.04 | 1.04 | 1.04 | 0 | both judges on |

## Group contrasts: does any direction change?

Differences of the pooled group values, no statistics. A change of direction is a change of sign between judge off and judge on.

| contrast | measure | judge off | judge on | direction changes |
| - | - | - | - | - |
| Hyp_RD minus WT | n_lacunae | 76 | 30 |  |
| WT_HP minus WT | n_lacunae | 12 | 5 |  |
| Hyp_HP minus Hyp_RD | n_lacunae | -1 | -9 |  |
| interaction (Hyp_HP - Hyp_RD) - (WT_HP - WT) | n_lacunae | -13 | -14 |  |
| Hyp_RD minus WT | n | 65 | 32 |  |
| WT_HP minus WT | n | 6 | -3 | YES |
| Hyp_HP minus Hyp_RD | n | -16 | -17 |  |
| interaction (Hyp_HP - Hyp_RD) - (WT_HP - WT) | n | -22 | -14 |  |
| Hyp_RD minus WT | area_um2_median | -1.428 | 9.025 | YES |
| WT_HP minus WT | area_um2_median | -8.695 | -6.126 |  |
| Hyp_HP minus Hyp_RD | area_um2_median | -13.74 | -22.87 |  |
| interaction (Hyp_HP - Hyp_RD) - (WT_HP - WT) | area_um2_median | -5.045 | -16.74 |  |
| Hyp_RD minus WT | area_um2_p90 | 18.18 | 17.25 |  |
| WT_HP minus WT | area_um2_p90 | -5.984 | 0.0254 | YES |
| Hyp_HP minus Hyp_RD | area_um2_p90 | 7.612 | -2.63 | YES |
| interaction (Hyp_HP - Hyp_RD) - (WT_HP - WT) | area_um2_p90 | 13.6 | -2.655 | YES |
| Hyp_RD minus WT | share_above_2x_WT_median | 0.0937 | 0.0849 |  |
| WT_HP minus WT | share_above_2x_WT_median | 0.0412 | 0.0378 |  |
| Hyp_HP minus Hyp_RD | share_above_2x_WT_median | 0.0272 | -0.0189 | YES |
| interaction (Hyp_HP - Hyp_RD) - (WT_HP - WT) | share_above_2x_WT_median | -0.014 | -0.0567 |  |
| Hyp_RD minus WT | pol_area_per_analysed_area | 0.0347 | 0.0175 |  |
| WT_HP minus WT | pol_area_per_analysed_area | -0.0012 | -0.0021 |  |
| Hyp_HP minus Hyp_RD | pol_area_per_analysed_area | -0.0034 | -0.0138 |  |
| interaction (Hyp_HP - Hyp_RD) - (WT_HP - WT) | pol_area_per_analysed_area | -0.0022 | -0.0117 |  |
| Hyp_RD minus WT | n_clusters | 1 | 3 |  |
| WT_HP minus WT | n_clusters | 0 | 0 |  |
| Hyp_HP minus Hyp_RD | n_clusters | -1 | -3 |  |
| interaction (Hyp_HP - Hyp_RD) - (WT_HP - WT) | n_clusters | -1 | -3 |  |
| Hyp_RD minus WT | roots_per_lacuna | -1.865 | -1.741 |  |
| WT_HP minus WT | roots_per_lacuna | 0.0038 | 0.2679 |  |
| Hyp_HP minus Hyp_RD | roots_per_lacuna | -0.5243 | -0.2579 |  |
| interaction (Hyp_HP - Hyp_RD) - (WT_HP - WT) | roots_per_lacuna | -0.5281 | -0.5258 |  |
| Hyp_RD minus WT | ring_length_30_um | -19.52 | -20.44 |  |
| WT_HP minus WT | ring_length_30_um | 8.88 | 11.97 |  |
| Hyp_HP minus Hyp_RD | ring_length_30_um | 4.755 | 5.086 |  |
| interaction (Hyp_HP - Hyp_RD) - (WT_HP - WT) | ring_length_30_um | -4.126 | -6.881 |  |
| Hyp_RD minus WT | field_length_density_um_per_um2 | -0.1009 | -0.1024 |  |
| WT_HP minus WT | field_length_density_um_per_um2 | 0.058 | 0.0615 |  |
| Hyp_HP minus Hyp_RD | field_length_density_um_per_um2 | 0.0112 | 0.0109 |  |
| interaction (Hyp_HP - Hyp_RD) - (WT_HP - WT) | field_length_density_um_per_um2 | -0.0468 | -0.0506 |  |
| Hyp_RD minus WT | width_median_um | 0 | 0 |  |
| WT_HP minus WT | width_median_um | 0 | 0 |  |
| Hyp_HP minus Hyp_RD | width_median_um | 0 | 0 |  |
| interaction (Hyp_HP - Hyp_RD) - (WT_HP - WT) | width_median_um | 0 | 0 |  |

Contrasts whose direction changes: WT_HP minus WT, n; Hyp_RD minus WT, area_um2_median; WT_HP minus WT, area_um2_p90; Hyp_HP minus Hyp_RD, area_um2_p90; interaction (Hyp_HP - Hyp_RD) - (WT_HP - WT), area_um2_p90; Hyp_HP minus Hyp_RD, share_above_2x_WT_median.

## What the judges changed (development images, per group)

| | WT | WT_HP | Hyp_RD | Hyp_HP |
| - | - | - | - | - |
| lacunae judge off | 71 | 83 | 147 | 146 |
| numbered | 291 | 328 | 403 | 396 |
| yes | 71 | 71 | 95 | 77 |
| no | 211 | 243 | 276 | 277 |
| unsure | 9 | 14 | 32 | 42 |
| unjudged | 0 | 0 | 0 | 0 |
| not offered (excluded region) | 0 | 32 | 21 | 26 |
| removed | 2 | 10 | 32 | 49 |
| removed, fragment | 1 | 0 | 7 | 16 |
| removed, band | 0 | 9 | 10 | 8 |
| removed, tissue | 0 | 1 | 11 | 12 |
| removed, saturated_border | 1 | 0 | 4 | 13 |
| added | 4 | 5 | 0 | 10 |
| added, dim candidates | 1 | 3 | 0 | 2 |
| added, lacuna | 4 | 5 | 0 | 7 |
| added, enlarged | 0 | 0 | 0 | 3 |
| added, cluster | 0 | 0 | 0 | 0 |
| kept lacunae called lacuna | 63 | 59 | 66 | 43 |
| kept lacunae called enlarged | 4 | 7 | 27 | 24 |
| kept lacunae called cluster | 0 | 0 | 2 | 0 |
| removed enlarged (above 2 x WT median) | 0 | 0 | 3 | 7 |
| removed clusters | 0 | 0 | 0 | 0 |
| POL judge: cases | 5 | 8 | 26 | 25 |
| POL judge: pol | 4 | 7 | 10 | 12 |
| POL judge: cluster | 0 | 0 | 3 | 0 |
| POL judge: split | 2 | 2 | 18 | 11 |
| POL judge: lacuna | 0 | 0 | 4 | 4 |
| POL judge: not_lacuna | 0 | 0 | 4 | 8 |
| POL judge: unsure | 0 | 0 | 2 | 8 |
| POL judge: unjudged | 0 | 0 | 0 | 0 |
| POL judge: removed | 0 | 0 | 4 | 8 |
| POL judge: merge groups | 1 | 1 | 9 | 5 |
| POL judge: pieces merged | 2 | 2 | 18 | 11 |
| POL judge: cluster flags set | 0 | 0 | 2 | 0 |
| POL judge: cluster flags cleared | 0 | 0 | 0 | 0 |
| images the canaliculi judge finished | 6 | 7 | 7 | 7 |
| canaliculi cases | 96 | 93 | 149 | 117 |
| canaliculi cases unjudged | 0 | 0 | 0 | 0 |
| segments offered | 598 | 635 | 1140 | 733 |
| segments real | 481 | 463 | 824 | 570 |
| segments artifact | 117 | 172 | 316 | 163 |
| segments unjudged | 0 | 0 | 0 | 0 |
| owner moved by a verdict | 333 | 315 | 430 | 334 |

Removed: a lacuna the filters kept that the lacuna judge called no, by the reason it gave. Added: a region the filters rejected, or a dim candidate, that it called yes. Enlarged: above 2 x the judge-off WT median in the judge-off quantification; clusters: flagged cluster there. Per image in `judge_changes.csv`.
