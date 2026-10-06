# Canalicular ablation: where do the straight segments come from?

**pixel size 0.13 um/px, rounded, unconfirmed.** Pre-validation: no number here has been checked against a
manual count. This is a diagnosis on branch `canal-physical-ablation`, not a new method, and
**no variant is called better than another**. Nothing was tuned to improve any result.

## The question

The ridge method of `results_experiments/canal_physical/` draws straight, right-angled runs
through dark regions where the raw image shows no thread (its zoom crops of 542_z18 and
682_z08 show it). These seven variants take the comparison apart to find which step puts them
there, and whether the extra connectivity survives without that step.

## Variants

The lacunae, the vascular handling, the graph cleanup, the ownership and the ring radii are the
same in every one, so only the named difference can move a number. The list was fixed before
the first run and every variant is reported.

| variant | what |
|---|---|
| A | current method, as is |
| B | current method, gap bridging off |
| C | ridge method, as is |
| D | ridge method, gap bridging off |
| E | ridge method, low cut 0.9 of the high cut |
| F | ridge method, bridging off, single scale 3.0 px |
| G | ridge method, bridging off, finer scales |

## Artifact measures

Each is read off the image itself. No published value is used anywhere in this folder, for any
purpose.

- **`unsupported_fraction`**: share of skeleton pixels that are **not above** the image's own
  lower multi-Otsu cut of the flattened intensity. That cut is the one the current method uses
  as its high threshold, so this is the exact complement of the pipeline's own rule for calling
  a pixel signal. A high value means the skeleton runs where the image holds no signal.
- **`straight_run_fraction`**: share of skeleton pixels inside a perfectly horizontal or
  vertical run of at least 8 px, about 1.04 um. A run is a maximal set of
  consecutive skeleton pixels along one image row or one image column; a pixel in a long run in
  either direction is counted. Diagonal and curved stretches are never counted, however long.
  A real canaliculus has no reason to follow the pixel grid over a micrometre.
- **`rectangle_count`**: independent four-node loops of the cleaned graph whose four sides are
  all axis-aligned to within 1 px. The loops come from `networkx.cycle_basis`, which gives
  one independent cycle per loop, so this counts independent loops and not every way of walking
  one.
- Everything else is measured by `src/quantification.py`, the same code for every variant.

All of them are computed on the **whole** skeleton, not only the part a verification image draws.

## Reading the verification images

The verification images are drawn by the pipeline's own `canaliculi.save_verification`, imported
and called, not reimplemented. That style draws the **owned skeleton only**: a thread that no
lacuna owns is not drawn at all, and the owned part is thickened by the pipeline's own dilation.

**This hides a large part of every skeleton, and it hides more of the current method's than of
the ridge method's.** Only about a third of the current method's skeleton length is connected to
a lacuna, against about seven tenths of the ridge method's, so the ridge picture looks busier
partly for that reason alone and not only because its skeleton is different. The zoom panels
named `_variants_` draw the whole skeleton instead, which is the fair view of what each variant
traced.

## Files

| file | what |
|---|---|
| `ablation_all_images.csv`, `.xlsx`, `.pdf` | one row per image and variant, every measure |
| `ablation_summary.csv`, `.pdf` | mean over the 8 images per variant, and the change from A |
| `<label>/verification/<label>_verification_<variant>.png` | full size 1024 x 1024, pipeline style, one per variant |
| `<label>/<label>_verification_compare.png` and `.pdf` | raw, A, C at full size, nothing drawn on top |
| `<label>/<label>_verification_compare_bridging.png` | A, B, D at full size: what bridging adds |
| `<label>/<label>_zoom<i>_variants_ABCDE.png` | the tile with the whole skeleton of A to E |
| `<label>/<label>_zoom<i>_variants_FG.png` | the same tile for F and G |
| `<label>/<label>_zoom<i>_verification_raw_A_C.png` | the same tile in verification style |
| `<label>/<label>_artifacts_zoom<i>.png` | variant C's skeleton: red not above the cut, blue axis-aligned run |
| `<label>/<label>_overview_tiles.png` | the whole image with the three tiles marked |
| `<label>/<label>_ablation.json` | every measure, the definitions, the tiles, provenance |

The three zoom tiles are the ones the `canal_physical` run chose, read from its json and not
chosen again, so the two folders show the same places.

## Mean over the 8 images

| measure | A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|---|
| `unsupported_fraction` | 0.06798 | 0.06699 | 0.121 | 0.1198 | 0.0904 | 0.09041 | 0.08882 |
| `bridged_fraction` | 0.0006067 | 0 | 0.0007291 | 0 | 0.005179 | 0 | 0 |
| `straight_run_fraction` | 0.221 | 0.2203 | 0.2635 | 0.2634 | 0.2577 | 0.25 | 0.2447 |
| `rectangle_count` | 0 | 0 | 0.25 | 0.25 | 0.125 | 0 | 0 |
| `connected_to_lacuna_fraction` | 0.336 | 0.3289 | 0.7191 | 0.7033 | 0.634 | 0.5489 | 0.5109 |
| `junction_count` | 529.8 | 526.8 | 876.1 | 871.6 | 727 | 728.9 | 723 |
| `thread_end_fraction` | 0.7641 | 0.7678 | 0.575 | 0.5817 | 0.623 | 0.6491 | 0.6747 |
| `width_median_px` | 6.041 | 6.041 | 7.408 | 7.408 | 6.768 | 6 | 5.743 |
| `field_length_density_per_px` | 0.0391 | 0.03904 | 0.04071 | 0.04064 | 0.0383 | 0.0398 | 0.04106 |
| `roots_per_cell` | 7.545 | 7.577 | 7.843 | 7.845 | 7.404 | 7.308 | 7.778 |
| `ring_length_r30_px_per_cell` | 321.5 | 321.2 | 339.2 | 338.4 | 316.1 | 320.4 | 330.6 |
| `skeleton_px` | 3.992e+04 | 3.985e+04 | 4.154e+04 | 4.148e+04 | 3.909e+04 | 4.062e+04 | 4.191e+04 |
| `n_bridges` | 18.12 | 0 | 16.25 | 0 | 70.5 | 0 | 0 |

## How it was run

```
python src/canal_physical/ablation.py --dir data/WT
```

Commit `16866b5735d26a245a320bf92a14e0546e6e2910`, tracked files clean: True. Config hash
`dc534babadca48a8`.

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

## Images

- 542_z06 (`542 WT  2_z06c1-2.tif`)
- 542_z18 (`542 WT  2_z18c1-2.tif`)
- 543-2 (`543-2.tif`)
- 543_3 (`543_3.tif`)
- 543_z13 (`543_z13c1-2.tif`)
- 682_z08 (`682_z08c1-2.tif`)
- 682_z23 (`682_z23c-2.tif`)
- 682_z29 (`682_z29c1-3.tif`)
