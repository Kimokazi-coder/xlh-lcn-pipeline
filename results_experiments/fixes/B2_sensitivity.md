# Threshold sensitivity

PRE-VALIDATION, pixel units. Percent change against each image's default run, median over the 8 images with the range in brackets. t_hi: lacuna cut; t_lo: network strict cut.
pooled: one cut for every image, t_hi = 0.6001 (median over the folder) and t_lo =
0.0427 in raw units (median of t_lo x preprocessing peak). Per-image values: sensitivity.csv.

| setting | roots per cell | ring 30 px per cell | field density | lacuna count | bridges |
|---|---|---|---|---|---|
| t_hi x0.8 | +18.7 [-6.0, +26.2] | +11.7 [-2.9, +24.2] | -0.5 [-1.2, +0.1] | +14.8 [-31.2, +50.0] | +0.0 [-5.3, +5.9] |
| t_lo x0.8 | +6.2 [+2.7, +12.1] | +10.7 [+6.1, +12.2] | +11.1 [+7.5, +12.0] | +0.0 [+0.0, +0.0] | -29.2 [-52.9, +21.4] |
| both x0.8 | +26.2 [+1.0, +47.9] | +24.3 [+4.8, +39.3] | +10.4 [+6.8, +11.7] | +14.8 [-31.2, +50.0] | -24.8 [-52.9, +21.4] |
| t_hi x0.9 | +7.5 [-1.1, +19.7] | +5.5 [+2.0, +11.1] | -0.0 [-0.5, +0.1] | +4.5 [-18.8, +20.0] | +0.0 [-5.3, +7.1] |
| t_lo x0.9 | +1.9 [+0.0, +9.5] | +4.4 [+2.4, +6.3] | +5.1 [+3.5, +5.7] | +0.0 [+0.0, +0.0] | -6.5 [-20.8, +42.1] |
| both x0.9 | +9.2 [+2.2, +31.1] | +11.0 [+5.1, +18.0] | +5.1 [+3.5, +5.4] | +4.5 [-18.8, +20.0] | -6.0 [-25.0, +36.8] |
| t_hi x1.1 | -9.1 [-25.8, +1.2] | -8.2 [-12.4, +1.8] | +0.1 [-0.2, +0.3] | +0.0 [-15.4, +0.0] | +0.0 [+0.0, +5.3] |
| t_lo x1.1 | -4.3 [-6.8, -1.6] | -4.3 [-5.3, -3.4] | -4.4 [-4.8, -3.6] | +0.0 [+0.0, +0.0] | +0.3 [-78.6, +85.7] |
| both x1.1 | -12.8 [-27.4, +0.0] | -12.9 [-16.5, -3.0] | -4.4 [-4.7, -3.5] | +0.0 [-15.4, +0.0] | +0.3 [-78.6, +85.7] |
| t_hi x1.2 | -12.7 [-34.7, -8.8] | -10.7 [-16.2, -5.3] | +0.2 [-0.2, +0.4] | -9.5 [-20.0, +0.0] | +0.0 [-5.3, +7.1] |
| t_lo x1.2 | -7.4 [-13.2, -3.8] | -7.6 [-11.3, -5.3] | -8.2 [-9.5, -6.5] | +0.0 [+0.0, +0.0] | +24.8 [-29.4, +42.9] |
| both x1.2 | -19.6 [-51.0, -15.0] | -19.6 [-22.5, -12.5] | -8.4 [-9.2, -6.2] | -9.5 [-20.0, +0.0] | +24.8 [-29.4, +50.0] |
| t_hi pooled | -1.0 [-11.3, +16.0] | -0.1 [-5.6, +9.0] | -0.0 [-0.2, +0.2] | +0.0 [-23.1, +10.0] | +0.0 [+0.0, +5.3] |
| t_lo pooled | +0.0 [-33.9, +18.7] | +0.4 [-24.5, +16.9] | +0.1 [-19.6, +17.5] | +0.0 [+0.0, +0.0] | +0.0 [-35.3, +64.3] |
| both pooled | -4.0 [-40.3, +37.8] | -1.2 [-29.1, +23.8] | +0.3 [-19.7, +17.6] | +0.0 [-23.1, +10.0] | +2.6 [-29.4, +64.3] |

Lacuna count per image and setting:

| image | default | t_hi x0.8 | t_lo x0.8 | both x0.8 | t_hi x0.9 | t_lo x0.9 | both x0.9 | t_hi x1.1 | t_lo x1.1 | both x1.1 | t_hi x1.2 | t_lo x1.2 | both x1.2 | t_hi pooled | t_lo pooled | both pooled |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 542_WT_2_z06c1-2 | 16 | 11 | 16 | 11 | 13 | 16 | 13 | 16 | 16 | 16 | 16 | 16 | 16 | 14 | 16 | 14 |
| 542_WT_2_z18c1-2 | 12 | 13 | 12 | 13 | 12 | 12 | 12 | 12 | 12 | 12 | 11 | 12 | 11 | 12 | 12 | 12 |
| 543-2 | 12 | 13 | 12 | 13 | 12 | 12 | 12 | 12 | 12 | 12 | 11 | 12 | 11 | 12 | 12 | 12 |
| 543_3 | 10 | 14 | 10 | 14 | 12 | 10 | 12 | 9 | 10 | 9 | 8 | 10 | 8 | 10 | 10 | 10 |
| 543_z13c1-2 | 11 | 14 | 11 | 14 | 12 | 11 | 12 | 11 | 11 | 11 | 10 | 11 | 10 | 11 | 11 | 11 |
| 682_z08c1-2 | 10 | 15 | 10 | 15 | 12 | 10 | 12 | 10 | 10 | 10 | 9 | 10 | 9 | 11 | 10 | 11 |
| 682_z23c-2 | 14 | 16 | 14 | 16 | 16 | 14 | 16 | 13 | 14 | 13 | 12 | 14 | 12 | 13 | 14 | 13 |
| 682_z29c1-3 | 13 | 15 | 13 | 15 | 13 | 13 | 13 | 11 | 13 | 11 | 11 | 13 | 11 | 10 | 13 | 10 |

## Notes (B2)

`python src/diagnostics.py sensitivity -d DIR -o OUT` (options: `-w` processes). It writes
`sensitivity.csv` (every run with its cuts and values), `sensitivity.md` (this table) and one json per
run in `OUT/runs/` (a rerun skips runs that exist). It uses the fast lacuna stage (identical labels,
A5). The cuts are passed as optional arguments to `canaliculi.analyse_image` and
`lacunae.analyse_image`, which the pipeline itself never passes, so the defaults are unchanged
(regression PASS). The preprocessing was split into `preprocess_unnormalised` and the division by
the maximum, so the raw-unit peak of the pooled cut comes from the pipeline's own code.

Every value above equals the overnight grid (`results_experiments/task2/2.4_grid.md`), computed there
with copies of the pipeline steps. 128 runs took 32 s with 8 processes.
