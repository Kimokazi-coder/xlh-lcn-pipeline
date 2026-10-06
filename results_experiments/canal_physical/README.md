# Experimental canalicular method, current against new

**pixel size 0.13 um/px, rounded, unconfirmed.** Pre-validation: no number here has been checked against a manual
count. This is an experiment on branch `canal-physical`; it is not the pipeline and nothing in
`src/lacunae.py`, `src/canaliculi.py`, `src/quantification.py` or `src/diagnostics.py` was changed.
No claim is made that the new method is better: the comparison table and the zoom crops are there
to be judged.

## What was run

Two methods on the same 8 WT sections, with the same lacunae, the same vascular handling, the same
bridging rule, the same graph cleanup, the same ownership and the same ring radii. They differ in
one place: the current method thresholds the flattened intensity, the experimental one thresholds a
multiscale ridge response of the same flattened image. Both are measured by
`src/quantification.py`, the same function with the same code.

```
python src/canal_physical/run.py --dir data/WT --tune    # the tuning set only, writes tuning_log.csv
python src/canal_physical/run.py --dir data/WT           # all 8 images, every output below
```

`python -m canal_physical.run --dir data/WT` works too when `src/` is on PYTHONPATH.

Commit: `f7aba4e50b72a25e238e79fe252b33a0e578da2c`, tracked files clean: True.
Config hash: `dc534babadca48a8`.
Ridge scales chosen: [3.0, 3.6, 4.2] px = [0.39, 0.468, 0.546] um.

## Versions

```
python: 3.9.10
numpy: 2.0.2
scipy: 1.13.1
scikit-image: 0.24.0
networkx: 3.2.1
skan: 0.13.1
matplotlib: 3.9.4
openpyxl: 3.1.5
```

## Parameters

Every parameter in micrometres and in pixels. The pixel values are the ones `src/canaliculi.py`
uses, asserted equal at this pixel size.

| parameter | um | px | what |
|---|---|---|---|
| `pixel_size_um` | 0.13 |  | um per pixel, rounded, unconfirmed |
| `sigma_um` | [0.39, 0.468, 0.546] | [3.0, 3.6, 4.2] | ridge scales |
| `hysteresis_low_fraction` | 0.75 |  | share of the high cut |
| `lacuna_buffer_um` | 0.26 | 2 | buffer around a lacuna |
| `min_object_area_um2` | 0.1352 | 8 | smallest mask fragment, area |
| `max_bridge_gap_um` | 1.3 | 10.0 | longest gap bridged |
| `direction_walk_um` | 0.65 | 5 | walk back for the thread direction |
| `max_bridge_angle_deg` | 40.0 |  | degrees |
| `min_bridge_signal_fraction` | 0.7 |  | share of the cut |
| `prune_spur_um` | 0.52 | 4.0 | shortest kept spur |
| `min_internal_edge_um` | 0.78 | 6.0 | shortest kept internal edge |
| `lacuna_attach_gap_um` | 1.3 | 10.0 | attach distance |
| `root_merge_um` | 1.04 | 8.0 | root cluster distance |
| `ring_radii_um` | [3.9, 7.8] | [30.0, 60.0] | ring radii |
| `broad_opening_um` | 1.04 | 8 | opening that finds broad structures |
| `vascular_dilation_um` | 0.52 | 4 | dilation of the flagged region |
| `vascular_min_span_fraction` | 0.45 |  | share of the frame |
| `vascular_min_major_axis_um` | 54.6 | 420.0 | smallest flagged major axis |
| `width_percentiles` | [10, 90] |  | percentiles reported |
| `random_seed` | 0 |  | no random choice is made |

## Output

| file | what |
|---|---|
| `<label>/<label>_triptych.png` and `.pdf` | raw, current, experimental, same crop and window, zoom boxes marked |
| `<label>/<label>_zoom_1` to `_zoom_3.png` | the three crops where the two skeletons differ most |
| `<label>/<label>_canal_physical.json` | parameters of both methods, every measure, the zoom rule, provenance |
| `comparison_all_images.csv`, `.xlsx`, `.pdf` | one row per image and method, plus the plausibility table |
| `tuning_log.csv` | every ridge scale set tried on the tuning set, and what it gave |
| `DECISIONS.md` | every assumption and every open question |

## Zoom crops

Chosen by rule, not by eye: tiles of the zoom side, ranked by the absolute difference in skeleton pixel count between the two methods, taken in order with no overlap. The boxes are drawn on the full image.

## Images

- 542_z06 (`542 WT  2_z06c1-2.tif`)
- 542_z18 (`542 WT  2_z18c1-2.tif`)
- 543-2 (`543-2.tif`)
- 543_3 (`543_3.tif`)
- 543_z13 (`543_z13c1-2.tif`)
- 682_z08 (`682_z08c1-2.tif`)
- 682_z23 (`682_z23c-2.tif`)
- 682_z29 (`682_z29c1-3.tif`)
