# R1 Checks

Pre-validation, pixel units. Run on 2026-10-03 at commit d446f50 (plus the uncommitted R1 config comment, a comment only), every
switch off unless stated. Commands from the repository root.

## python src/diagnostics.py reference-check

```
Reference check on 543-2.tif (pre-validation, px)
quantity                                                     expected  measured  result
-----------------------------------------------------------  --------  --------  ------
edges per interior cell (mean edge_count)                    62.33     62.33     PASS  
mean edge length, px (interior mean of mean_edge_length_px)  27.41     27.41     PASS  
gap bridges added                                            21        21        PASS  

PASS: 3 of 3 reference numbers match.
```

## python src/diagnostics.py regression (every switch off; the original and the fast lacuna stage)

The regression prints its allowlist of new fields first (73 json paths and 18 summary table columns, appended after results/ was made); any other new field fails.

```
  json  canaliculi_measurements.json:field.field_density_in_roi_per_px
  json  canaliculi_measurements.json:field.field_density_without_flagged_per_px
  json  canaliculi_measurements.json:field.field_length_density_w_per_px
  json  canaliculi_measurements.json:lacunae[*].in_frame_fraction_r30
  json  canaliculi_measurements.json:lacunae[*].in_frame_fraction_r60
  json  canaliculi_measurements.json:lacunae[*].perimeter_px
  json  canaliculi_measurements.json:lacunae[*].ring_area_r30_px2
  json  canaliculi_measurements.json:lacunae[*].ring_area_r60_px2
  json  canaliculi_measurements.json:lacunae[*].ring_attached_length_r30_px
  json  canaliculi_measurements.json:lacunae[*].ring_attached_length_r60_px
  json  canaliculi_measurements.json:lacunae[*].ring_density_r30
  json  canaliculi_measurements.json:lacunae[*].ring_density_r60
  json  canaliculi_measurements.json:lacunae[*].ring_length_w_r30_px
  json  canaliculi_measurements.json:lacunae[*].ring_length_w_r60_px
  json  canaliculi_measurements.json:lacunae[*].roots_per_100px_perimeter
  json  canaliculi_measurements.json:lacunae[*].sholl_crossings_r10
  json  canaliculi_measurements.json:lacunae[*].sholl_crossings_r20
  json  canaliculi_measurements.json:lacunae[*].sholl_crossings_r30
  json  canaliculi_measurements.json:network_v2_measures[*]
  json  canaliculi_measurements.json:normalised_measures[*]
  json  canaliculi_measurements.json:parameters.band_line_filter
  json  canaliculi_measurements.json:parameters.band_line_min_len_px
  json  canaliculi_measurements.json:parameters.band_line_reach_px
  json  canaliculi_measurements.json:parameters.band_line_remove_px
  json  canaliculi_measurements.json:summary.in_frame_fraction_r30.mean
  json  canaliculi_measurements.json:summary.in_frame_fraction_r30.median
  json  canaliculi_measurements.json:summary.in_frame_fraction_r30.sd
  json  canaliculi_measurements.json:summary.in_frame_fraction_r60.mean
  json  canaliculi_measurements.json:summary.in_frame_fraction_r60.median
  json  canaliculi_measurements.json:summary.in_frame_fraction_r60.sd
  json  canaliculi_measurements.json:summary.perimeter_px.mean
  json  canaliculi_measurements.json:summary.perimeter_px.median
  json  canaliculi_measurements.json:summary.perimeter_px.sd
  json  canaliculi_measurements.json:summary.ring_area_r30_px2.mean
  json  canaliculi_measurements.json:summary.ring_area_r30_px2.median
  json  canaliculi_measurements.json:summary.ring_area_r30_px2.sd
  json  canaliculi_measurements.json:summary.ring_area_r60_px2.mean
  json  canaliculi_measurements.json:summary.ring_area_r60_px2.median
  json  canaliculi_measurements.json:summary.ring_area_r60_px2.sd
  json  canaliculi_measurements.json:summary.ring_attached_length_r30_px.mean
  json  canaliculi_measurements.json:summary.ring_attached_length_r30_px.median
  json  canaliculi_measurements.json:summary.ring_attached_length_r30_px.sd
  json  canaliculi_measurements.json:summary.ring_attached_length_r60_px.mean
  json  canaliculi_measurements.json:summary.ring_attached_length_r60_px.median
  json  canaliculi_measurements.json:summary.ring_attached_length_r60_px.sd
  json  canaliculi_measurements.json:summary.ring_density_r30.mean
  json  canaliculi_measurements.json:summary.ring_density_r30.median
  json  canaliculi_measurements.json:summary.ring_density_r30.sd
  json  canaliculi_measurements.json:summary.ring_density_r60.mean
  json  canaliculi_measurements.json:summary.ring_density_r60.median
  json  canaliculi_measurements.json:summary.ring_density_r60.sd
  json  canaliculi_measurements.json:summary.ring_length_w_r30_px.mean
  json  canaliculi_measurements.json:summary.ring_length_w_r30_px.median
  json  canaliculi_measurements.json:summary.ring_length_w_r30_px.sd
  json  canaliculi_measurements.json:summary.ring_length_w_r60_px.mean
  json  canaliculi_measurements.json:summary.ring_length_w_r60_px.median
  json  canaliculi_measurements.json:summary.ring_length_w_r60_px.sd
  json  canaliculi_measurements.json:summary.roots_per_100px_perimeter.mean
  json  canaliculi_measurements.json:summary.roots_per_100px_perimeter.median
  json  canaliculi_measurements.json:summary.roots_per_100px_perimeter.sd
  json  canaliculi_measurements.json:summary.sholl_crossings_r10.mean
  json  canaliculi_measurements.json:summary.sholl_crossings_r10.median
  json  canaliculi_measurements.json:summary.sholl_crossings_r10.sd
  json  canaliculi_measurements.json:summary.sholl_crossings_r20.mean
  json  canaliculi_measurements.json:summary.sholl_crossings_r20.median
  json  canaliculi_measurements.json:summary.sholl_crossings_r20.sd
  json  canaliculi_measurements.json:summary.sholl_crossings_r30.mean
  json  canaliculi_measurements.json:summary.sholl_crossings_r30.median
  json  canaliculi_measurements.json:summary.sholl_crossings_r30.sd
  json  lacunae.json:parameters.band_filter_min_opening_share
  json  lacunae.json:parameters.fast_lacuna_stage
  json  lacunae.json:parameters.fill_enclosed_holes_max_px2
  json  lacunae.json:parameters.narrow_crumb_rule
  table perimeter per cell (px)
  table ring area 30 px per cell (px^2)
  table ring area 60 px per cell (px^2)
  table in-frame fraction 30 px per cell
  table in-frame fraction 60 px per cell
  table ring density 30 px per cell (px^-1)
  table ring density 60 px per cell (px^-1)
  table roots per 100 px perimeter per cell
  table ring attached length 30 px per cell (px)
  table ring attached length 60 px per cell (px)
  table ring length weighted 30 px per cell (px)
  table ring length weighted 60 px per cell (px)
  table Sholl crossings 10 px per cell
  table Sholl crossings 20 px per cell
  table Sholl crossings 30 px per cell
  table field length density weighted (px^-1)
  table field length density without flagged regions (px^-1)
  table field length density in ROI (px^-1)

Regression, current config: F:\lcn-quant\results_experiments\_cache\regression against F:\lcn-quant\results (tolerance 0, provenance ignored)

image             json fields compared  differ  new fields (not compared)  result
----------------  --------------------  ------  -------------------------  ------
542_WT_2_z06c1-2  536                   0       314                        PASS  
542_WT_2_z18c1-2  439                   0       254                        PASS  
543-2             488                   0       254                        PASS  
543_3             401                   0       224                        PASS  
543_z13c1-2       455                   0       239                        PASS  
682_z08c1-2       471                   0       224                        PASS  
682_z23c-2        512                   0       284                        PASS  
682_z29c1-3       479                   0       269                        PASS  

summary_table.csv: 80 cells compared, 0 differ; new columns not compared: perimeter per cell (px), ring area 30 px per cell (px^2), ring area 60 px per cell (px^2), in-frame fraction 30 px per cell, in-frame fraction 60 px per cell, ring density 30 px per cell (px^-1), ring density 60 px per cell (px^-1), roots per 100 px perimeter per cell, ring attached length 30 px per cell (px), ring attached length 60 px per cell (px), ring length weighted 30 px per cell (px), ring length weighted 60 px per cell (px), Sholl crossings 10 px per cell, Sholl crossings 20 px per cell, Sholl crossings 30 px per cell, field length density weighted (px^-1), field length density without flagged regions (px^-1), field length density in ROI (px^-1)

run result: PASS, current config, 3861 numbers compared over 8 images.

Regression, FAST_LACUNA_STAGE on: F:\lcn-quant\results_experiments\_cache\regression\fast_stage against F:\lcn-quant\results (tolerance 0, provenance ignored)

image             json fields compared  differ  new fields (not compared)  result
----------------  --------------------  ------  -------------------------  ------
542_WT_2_z06c1-2  536                   0       314                        PASS  
542_WT_2_z18c1-2  439                   0       254                        PASS  
543-2             488                   0       254                        PASS  
543_3             401                   0       224                        PASS  
543_z13c1-2       455                   0       239                        PASS  
682_z08c1-2       471                   0       224                        PASS  
682_z23c-2        512                   0       284                        PASS  
682_z29c1-3       479                   0       269                        PASS  

summary_table.csv: 80 cells compared, 0 differ; new columns not compared: perimeter per cell (px), ring area 30 px per cell (px^2), ring area 60 px per cell (px^2), in-frame fraction 30 px per cell, in-frame fraction 60 px per cell, ring density 30 px per cell (px^-1), ring density 60 px per cell (px^-1), roots per 100 px perimeter per cell, ring attached length 30 px per cell (px), ring attached length 60 px per cell (px), ring length weighted 30 px per cell (px), ring length weighted 60 px per cell (px), Sholl crossings 10 px per cell, Sholl crossings 20 px per cell, Sholl crossings 30 px per cell, field length density weighted (px^-1), field length density without flagged regions (px^-1), field length density in ROI (px^-1)

run result: PASS, FAST_LACUNA_STAGE on, 3861 numbers compared over 8 images.

PASS: regression, 2 runs (current config; FAST_LACUNA_STAGE on), 2 passed.
```

## python src/diagnostics.py fast-check (the fast lacuna stage on and off)

```
682_z29c1-3       1.1         True                 True                42.6        0.13  
682_z29c1-3       1.2         True                 True                25.5        0.1   

Total time over 40 runs: original 4229 s, fast 6.1 s (each run in its own process, 8 in parallel).

PASS: fast-check, 40 of 40 identical.
```

## python src/diagnostics.py switch-check (with BAND_LINE_FILTER)

Identical to `B1_switch_check.md` (compared line by line): the three earlier switches change exactly what they changed
on publication-fixes, and the band-wall filter at its two evidence settings changes what `B1_filter.md` lists.

## python src/diagnostics.py validate-network -s

```
SELFTEST SYNTHETIC: validate-network on synthetic hand counts and traces (outputs in F:\lcn-quant\results_experiments\_cache\validate_selftest; nothing under results/)

check                                                       value           result
----------------------------------------------------------  --------------  ------
a key inside the repository is refused                      refused         PASS  
lacunae joined                                              86 of 86        PASS  
roots bias near 0 (|bias| < 0.2)                            -0.023          PASS  
roots share within 1 = 1                                    1.000           PASS  
roots Spearman above 0.8                                    0.972           PASS  
F1 near 0.9 to 1 on every image (>= 0.9)                    1.000 to 1.000  PASS  
negative control: another image's trace gives F1 below 0.7  0.257           PASS  
boxes restrict the trace comparison to 2 images             2 images        PASS  

PASS: validate-network self-test, 8 of 8 checks.
```

## Also checked before every push

`git status results/` clean; `git diff 8673380 -- figures figures_out docs/METHODS.md README.md` empty
(`experiments/canal_check_and_push.sh`).
