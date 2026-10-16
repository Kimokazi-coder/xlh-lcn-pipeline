# lcn-quant

Quantification of the osteocyte lacuno-canalicular network (LCN) in 2D confocal
optical sections of mouse bone. Feature 1 detects and measures the lacunae.
Feature 2 segments the canalicular network, reduces it to a one-pixel skeleton
and measures it per lacuna and per field.

**Status: pre-validation.** No number here has been checked against manual
(ImageJ) counts yet, and no parameter or limit has been tuned against one. The
data are 8 wild-type (WT) sections; no Hyp images have been processed.

**You are on the branch `exp-ai-layer`.** It adds one experiment on top of the
pipeline: an AI judge that decides, for every candidate thread near an
osteocyte, whether it is a real thread and which lacuna owns it
(`docs/EXPERIMENT_AI.md`, `src/ai_judge.py`). It is **off by default**
(`config.AI_JUDGE_ENABLED = False`) and with it off every output of this branch
is what `main` produces, checked by `python src/diagnostics.py regression`.
Nothing on this branch is validated and nothing from it has been merged.

**Units.** The pixel size is 0.13 um/px, from the confocal acquisition record,
confirmed for all 8 images and rounded to two decimals
(`config.PIXEL_SIZE_UM_ACQUIRED`). Every biological limit is written in
micrometres and converted with it. The measures themselves stay in px and px²:
`config.PIXEL_SIZE_UM` is deliberately `None`, because it is recorded in the
parameters block of every result and switches every scale bar to micrometres, so
setting it would change the recorded values and a fresh run would no longer equal
`results/` at tolerance 0. Convert with 0.13 um/px where a physical length is
wanted.

## The canalicular method

There is **one** method. A canaliculus is found because it is a thin bright
**ridge**, not because it is bright.

1. Flatten the background: a light Gaussian, a white top-hat and a
   histogram-mode offset subtraction.
2. Take the **Sato ridge response** of that flattened image over sigmas
   **3.0, 3.6 and 4.2 px** (`canaliculi.RIDGE_SIGMAS_PX`), as the maximum
   across the scales.
3. Threshold the response with hysteresis, the low cut at 0.75 of the high cut.
   Both cuts come from the response's own histogram. Inside vascular-canal
   structures only already-bright pixels are kept.
4. Remove the lacuna bodies plus a 2 px buffer and small specks.
5. Inside each lacuna's own **zone**, and nowhere else, multiply the response by
   that lacuna's **contrast gain** and apply the same cuts again. One global cut
   empties a ring around every body, 27.4 px wide at the median, because a
   thread's contrast there runs at a third to two thirds of normal (METHODS
   section 18). The zone is that lacuna's own **hole**, its empty width measured
   on the global cut skeleton plus one thread half width, capped at 8 um, and
   never a fixed width; the gain is the response just beyond the zone over the
   response inside it, by distance from the body, clipped to 1 and 3, because
   the loss is a trough that is deepest at the body (METHODS section 19). A
   piece of mask that did not exist before is kept only if it is at least 10 um
   long and three times longer than wide. Then skeletonize. **There is no gap
   bridging**: a gap is left as a gap.
6. Graph, cleanup, and ownership by shortest path through the network. A lacuna
   owns what **touches** it, within 6 px, with no test and before the shortest
   path assignment, and every body a node touches is offered it, the nearer
   surface winning (METHODS section 19); beyond that it attaches to a thread
   only where there is
   **signal all the way to it**, the dimmest point of the straight path from the
   lacuna surface reaching 0.7 of the response's low cut, within 20 px.
7. A **second, dimmer pass** continues the threads a lacuna owns into response
   down to half the low cut, no more than 5 px past where the owned skeleton
   already reaches, then redoes the graph and the ownership.
8. Apply the **50 um length limit** (below) and rebuild ownership.
9. Find **unattached** dim threads: thread-shaped structure no lacuna owns, kept
   only if at least 1.3 um long and three times longer than wide. Counted in the
   field density, never per lacuna.
10. Measure.

This was variant D of the ablation that compared it against the older intensity
threshold; that comparison is preserved at the git tag `archive-2026-10-13`. **No
variant was validated against a manual count, so choosing this one is not a
validated result.**

## Biological limits

Fixed in `config.py`, in micrometres, identical for every image, converted once
with 0.13 um/px. **None is validated against this data.** The figures are what
the osteocyte literature reports for mouse cortical bone, used as a plausibility
bound and never as a threshold tuned to improve a result.

| constant | value | what it does |
|---|---|---|
| `MAX_CANALICULUS_LENGTH_UM` | 50 um (385 px) | **prunes** the skeleton |
| `LACUNA_ATTACH_REACH_UM` | 2.6 um (20 px) | how far a lacuna reaches for a thread |
| `LACUNA_ATTACH_MIN_SIGNAL_FRACTION` | 0.7 of the low cut | the signal that path must carry |
| `DIM_THREAD_CUT_FRACTION` | 0.5 of the low cut | the second pass's cut |
| `DIM_THREAD_REACH_UM` | 0.65 um (5 px) | how far a dim thread may continue |
| `UNATTACHED_MIN_LENGTH_UM` | 1.3 um (10 px) | shortest unattached thread kept |
| `UNATTACHED_MIN_ASPECT` | 3.0 | how thread-shaped it must be |
| `GLOW_TRIM_WIDTH_FRACTION` | 0.5 of the body's own width | trims a glow streak before judging shape |
| `OUT_OF_FOCUS_MIN_AREA_UM2` | 2.5 um² (148 px) | smallest out-of-focus body |
| `OUT_OF_FOCUS_MAX_ASPECT` / `MIN_SOLIDITY` / `MIN_CONTRAST` | 1.5 / 0.90 / 1.5 | round, and brighter than its surroundings |
| `DIM_LACUNA_MIN_AREA_UM2` / `MIN_SOLIDITY` / `MAX_PEAK` | 2.7 um² / 0.80 / 0.82 | a dim sub-area lacuna: big enough, compact, and **not** saturated |
| `BORDER_AREA_FRACTION` / `BORDER_MIN_SOLIDITY` | 0.75 / 0.85 | an object the frame cuts: scaled area floor, stricter shape |
| `THICK_PROCESS_MIN_AREA_UM2` / `MIN_CONTRAST` / `MIN_SOLIDITY` | 16.9 um² / 2.5 / 0.40 | a large bright ragged body with a thick process |
| `MERGE_MIN_SHARED_PX` / `MERGE_MIN_DIP_FRACTION` | 150 px / 0.75 | one osteocyte split by a thin dark band becomes one again |
| `CANALICULUS_LENGTH_RANGE_UM` | 25 to 50 um | report only |

**The length limit.** No canaliculus runs further than 50 um from the surface of
the lacuna that owns it, measured **along the network**, not as a straight line.
It is a geodesic distance on the skeleton itself: a path travels only along
skeleton pixels and across the lacuna buffer, a diagonal step costs the square
root of 2, and every lacuna body is a source at distance 0, so the shortest path
decides which lacuna a thread is measured from. Everything beyond the limit is
pruned and ownership is rebuilt. A pixel that no lacuna reaches within the limit
is **not** pruned: there is no lacuna to measure a length from, so it stays,
unowned. 50 um is the outer end of the reported lacuna-to-lacuna spacing in
cortical bone, so a thread longer than that from one cell body is not one
canaliculus.

On these 8 images the limit removes 1.7 to 20.4% of the skeleton it is applied to, 9.8% over all of them, counting what the final prune removes against what it leaves (`length_prune.removed_px` of each run). The glow zone of METHODS section 18 lowered this: a thread that could not reach a body within 50 um along the network was being deleted, and the zone joins it to the body it belongs to.

**Report only**, in the `biological_limits` block of each image's json and the
sheet of the same name in its xlsx: per-thread length against the 25 to 50 um
range, roots per lacuna, and the apparent width. The apparent width **includes
the optical blur** and is therefore an **upper bound**, not a canalicular
diameter: no point spread function is subtracted, because the numerical aperture,
the emission wavelength and the pinhole are unknown.

## Repository map

| path | what it holds |
|---|---|
| `src/` | `lacunae.py` (feature 1, detection), `canaliculi.py` (feature 2, detection), `quantification.py` (every measure), `diagnostics.py` (every check, as subcommands) |
| `config.py` | paths, the biological limits, shared settings and the switches (all off by default) |
| `data/WT/` | the 8 input images |
| `results/` | the pipeline output and the reference that `regression` checks; see [`results/README.md`](results/README.md) |
| `manual_trace/` | four raw tiles for the blind hand trace that will produce the ground truth |
| `figures/` | the figure code, captions and review notes |
| `docs/` | [`START_HERE.md`](docs/START_HERE.md), [`METHODS.md`](docs/METHODS.md), [`NETWORK_TUNING_PROTOCOL.md`](docs/NETWORK_TUNING_PROTOCOL.md) |

The lacuna count now includes out-of-focus lacunae, which carry no area or shape;
see docs/METHODS.md section 9.

Earlier experiments, the older intensity-threshold method, the ablation that
chose this one and every earlier report are preserved at the git tag
`archive-2026-10-13`. `main` is the only branch.

## Running it

Python 3.9 with numpy, scipy, scikit-image, networkx, skan, openpyxl and
tifffile (tested with numpy 2.0.2, scipy 1.13.1, scikit-image 0.24.0,
networkx 3.2.1, skan 0.13.1, openpyxl 3.1.5, tifffile 2024.8.30). Run every
command from the repository root, in this order.

```
python src/lacunae.py --dir data/WT          # feature 1: find and label the lacunae
python src/canaliculi.py --dir data/WT       # feature 2: trace the network
python src/quantification.py --dir data/WT   # measure both, per image and for all images
python -u figures/make_figures.py all        # every figure, into results/
```

Detection draws and labels; quantification measures what detection saved, and
every measured number is written only by it. Detection writes
`results/<label>/1_lacunae/` and `2_canaliculi/`: the overlay, the mask, the
skeleton, the verification picture, the lacuna label image, the vascular mask,
the graph with its ownership, and a record of what it did. Quantification reads
those and writes every number into `results/<label>/5_quantification/` and, for a
folder run, `results/all_images/quantification/quantification_all_images.xlsx`,
`.csv` and `.pdf`. `-o` picks another output folder for all three commands.

Check it:

```
python src/diagnostics.py reference-check    # must PASS: 161.00 / 21.63 / 8.50 on 543-2
python src/diagnostics.py regression         # every number against results/, tolerance 0
python src/diagnostics.py switch-check       # what each switch in config.py changes
python src/diagnostics.py --help             # every other diagnostic
python src/diagnostics.py survey -d data/WT -o results/survey        # what it does to every image
python src/diagnostics.py shape-picture -d data/WT -o results/network_shape
python src/validate_manual.py                # score against a hand tracing, when one exists
```

The switches in `config.py` (`NARROW_CRUMB_RULE`, `FILL_ENCLOSED_HOLES_MAX_PX2`,
`BAND_FILTER_MIN_OPENING_SHARE`, `FAST_LACUNA_STAGE`) act on the lacuna stage and
are all off, so the default output is unchanged.

## Measures

**Headline measures.** None of them depends on which cell owns which thread.
- **Roots per cell**: distinct canalicular threads leaving each lacuna's surface.
- **Ring length 30 px**: skeleton px within 30 px of each lacuna, each pixel
  counted for its nearest lacuna.
- **Field length density**: all skeleton px divided by the analysed field area,
  in px⁻¹.
- **Canalicular width**: twice the Euclidean distance transform of the mask at
  each skeleton pixel. An apparent width that includes the blur, so an upper
  bound; it sits close to the pixel grid, moves with the threshold, and is not
  validated.

**Also reported:** lacuna count and interior count (lacunae not touching the
frame; every per-cell mean uses these), area and shape per lacuna, ring length at
60 px, and the biological limits block above.

**Lacuna classes.** Every lacuna carries a `lacuna_class`. An `ordinary` one is
measured in full. A `dim` or `out_of_focus` one is **counted and owns its
threads** but carries **no area or shape**, because what would be measured is the
blur or the frame and not the cell; the shape summary uses ordinary lacunae only.
docs/METHODS.md section 9 gives the rules and how each value was chosen.

**Not headline measures:** owned length, edge count and mean edge length. They
assign each thread to one cell through the network, so every output labels them
ownership-dependent. Edge count is a network parameter, not "canaliculi per
cell".

## Results

`results/all_images/quantification/quantification_all_images.xlsx` (and `.csv`
and `.pdf`) has one row per image. Per-lacuna numbers are in
`results/<label>/5_quantification/<label>_quantification.xlsx` (and `.json`, and
`.pdf` to read), one row per lacuna with its shape and its network measures
together.

| image | lacunae (interior) | roots per cell | ring 30 px per cell (px) | field density px⁻¹ |
|---|---|---|---|---|
| 542_WT_2_z06c1-2 | 19 (15) | 14.53 | 473.2 | 0.0396 |
| 542_WT_2_z18c1-2 | 13 (11) | 10.36 | 452.7 | 0.0380 |
| 543-2 | 12 (12) | 7.67 | 340.4 | 0.0394 |
| 543_3 | 13 (12) | 6.00 | 290.8 | 0.0372 |
| 543_z13c1-2 | 11 (11) | 7.45 | 351.2 | 0.0420 |
| 682_z08c1-2 | 11 (9) | 12.56 | 454.1 | 0.0360 |
| 682_z23c-2 | 14 (11) | 8.64 | 348.4 | 0.0375 |
| 682_z29c1-3 | 15 (13) | 7.00 | 299.6 | 0.0360 |

The figures under `results/<label>/3_publication_figures/` are regenerated by
`python -u figures/make_figures.py all` and are not tracked. The pipeline's own
stage pictures under `1_lacunae/` and `2_canaliculi/` are tracked: the skeleton
png is an input to `diagnostics.py validate-network`.

## Still open

1. **Validation** against manual (ImageJ) counts. Roots per cell is the
   per-cell number to compare. The tiles for the blind trace are in
   `manual_trace/`; the rules for tuning afterwards are fixed in advance in
   [docs/NETWORK_TUNING_PROTOCOL.md](docs/NETWORK_TUNING_PROTOCOL.md).
2. **The ridge scales and the 50 um limit are unvalidated.** The scales were
   measured on this data and the limit comes from the literature; neither has
   been checked against a hand trace.
3. **Lacunae partly outside the focal plane**: whether they should count. A
   breadth-based detector finds 31 to 290% more objects per image, but they are
   dimmer and include vascular canal.
4. **Two thin kept objects on vascular bands**, probably not lacunae: 542_z06 at
   (555,149) and 682_z23 at (363,7). Both are counted now.

Method, every parameter and its origin, limitations and decisions:
[docs/METHODS.md](docs/METHODS.md). New here:
[docs/START_HERE.md](docs/START_HERE.md).
