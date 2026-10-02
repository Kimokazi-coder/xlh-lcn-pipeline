# A5 Fast lacuna stage

`config.FAST_LACUNA_STAGE` (default False) selects `lacunae.watershed_split_fast` and
`lacunae.merge_shallow_splits_fast`, ported from `experiments/common.py`: the same steps done inside
each component's bounding box (plus a 1 px margin for the watershed seeds), same pieces, same order,
same saddle test.

**Identical labels.** `python src/diagnostics.py fast-check` compares the label images after the
watershed and after the re-merge, pixel for pixel, on all 8 images at t_hi scaled 0.8, 0.9, 1.0, 1.1
and 1.2: 40 of 40 identical (`A5_fast_check.csv`, log `experiments/logs/A5_fast_check_run.log`).

**Regression with the switch on.** `regression` now runs twice: the current config, then the same
with FAST_LACUNA_STAGE on. Both PASS, 3861 numbers each (`experiments/logs/A5_regression_run.log`).

**Timing** (this machine, 20 logical cores):

| what | original stage | fast stage |
|---|---|---|
| lacuna stage, one image at the default cut | 21.6 to 78.5 s | 0.11 to 0.15 s |
| lacuna stage, 40 runs at five cuts (sum) | 4233 s | 6.0 s |
| full pipeline, 542_z06, one process | 70.2 s | 2.8 s |
| regenerate all 8 images, 8 processes | 125 s | 8 s |

The original stage slows down sharply at lower cuts (452.9 s for 542_z06 at 0.8 t_hi), because a lower
cut makes more components and each one costs a full-frame pass.
