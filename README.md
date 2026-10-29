# lcn-quant

Quantification of the osteocyte lacuno-canalicular network (LCN) in 2D confocal
optical sections of mouse bone. Feature 1 detects and measures the lacunae.
Feature 2 segments the canalicular network, reduces it to a one-pixel skeleton
and measures it per lacuna and per field.

**Status: pre-validation.** No number here has been checked against manual
(ImageJ) counts yet, and no parameter or limit has been tuned against one. The
data are organised in four groups (see Groups): WT, the 8 wild-type sections
every rule was chosen on, and WT_HP, Hyp_RD and Hyp_HP with 9 sections each,
run with the same settings. The pixels of all four groups are JPEG-decoded:
the WT TIFFs were made from JPEGs, and the other groups' JPEGs are decoded into
lossless TIFF the same way.

**Two methods, and the choice between them is pending.**

- The **deterministic method** is the pipeline as `config.py` ships it. Its
  output is `results/`, one folder per group; `results/WT/` is the reference
  `python src/diagnostics.py regression` checks.
- The **AI judge method** is the same pipeline with `config.AI_JUDGE_ENABLED`
  on. Where who owns a thread is a judgement call, an AI judge looks at a
  picture and says which osteocyte the thread starts from, and for a faint
  piece the pipeline did not trace, whether it is a thread at all; the verdict
  becomes a zero weight attachment that the existing shortest path step uses to
  split the network (`docs/EXPERIMENT_AI.md`, `src/ai_judge.py`). Its output is
  `results_ai_judge/WT/`, for the WT group only. The switch is **off by default**, and with it off every
  output is the deterministic method's.

**Which method the study uses has not been decided, and neither has been
validated against a manual trace.** The judge was run once, on 2026-10-19, on
all 8 images: 143 calls to the pinned `claude-sonnet-5-5`, **$1.60** (the dry
run had estimated $1.19). Everything since replays from its log with no network.
External API use approved on 2026-10-15, approver: Karim.

**An experiment beside them: the AI lacuna judge** (`docs/EXPERIMENT_AI.md`, "The
lacuna judge", and METHODS section 23). The lacuna stage was shaped on WT and, on
the other groups, outlines saturated bands, soft tissue and fragments and misses
dim bodies. The lacuna judge is shown every candidate region the lacuna stage
outlined, numbered, once per image, and says yes, no or unsure per region; behind
`config.AI_LACUNA_JUDGE_ENABLED` (**off by default**), a yes keeps a region and a
no removes it. **It never draws or changes a boundary**, sees no file name or
group, and uses one prompt for every image of all four groups. It was run once,
on 2026-10-27, on all 35 images: 35 calls to the pinned `claude-sonnet-5-5`,
**$0.83** (estimate $0.93, ceiling $3), every answer valid; the replay gives
identical verdicts offline. It said no to 352 of the 793 lacunae the filters
kept and added 7 regions. **Not validated: no verdict has been checked against
a manual count**, and its output, `results_ai_lacunae/`, is not a result of the
study. External API use approved on 2026-10-15, approver: Karim.

## What each folder is

| folder | what it is | the one command that makes it |
|---|---|---|
| `results/` | **set 1, the deterministic method**, one folder per group: `results/WT/` holds every WT image's detection, quantification and figures, and the cross-image table; see [`results/README.md`](results/README.md) | `python src/lacunae.py --dir data/WT; python src/canaliculi.py --dir data/WT; python src/quantification.py --dir data/WT; python -u figures/make_figures.py all` (one line; the four stages run in that order) |
| `results_ai_judge/` | **set 2, the AI judge method**, WT only, in `results_ai_judge/WT/`: the same per-image layout, the judge log with the case pictures that were sent, and `compare/`; see [`results_ai_judge/README.md`](results_ai_judge/README.md) | `python src/diagnostics.py ai-run --dir data/WT` (offline, from the decision files in `results_ai_judge/WT/ai_log/`) |
| `results_ai_judge/WT/compare/` | the two sets side by side: pictures, `REPORT.md`, and `compare_methods.csv` and `.xlsx` | `python src/diagnostics.py ai-compare --dir data/WT`, then `python src/diagnostics.py compare-methods --dir data/WT` |
| `results_ai_judge/WT/ai_log/` | every request to the judge and every answer, and the decision files | `python src/diagnostics.py ai-judge --dir data/WT` (a real run: needs `ALLOW_EXTERNAL_API=1` and a key, see `docs/EXPERIMENT_AI.md`); `--replay` reruns it offline |
| `results_ai_lacunae/` | **the AI lacuna judge, an experiment, not validated**: the judge log with the pictures that were sent (`<group>/ai_log/`), the pipeline with its verdicts applied (`<group>/`, the same per-image layout), `dry_run/`, and `review/` with a contact sheet per group and a table per image; see [`results_ai_lacunae/README.md`](results_ai_lacunae/README.md) | `python src/diagnostics.py ai-lacuna-run -w 20` (offline, from the log); the log itself from `ai-lacuna-judge --live`, see `docs/EXPERIMENT_AI.md` |
| `results/pols/`, `results/<group>/pols/` | **the POL section, pre-validation**: the look (`FINDINGS.md`: POLs cannot be told apart in these images), the proxy measured instead (`DEFINITION.md`), overlays and tables per group, `SUMMARY.md` and `REPORT.md`; see [`results/README.md`](results/README.md), POL proxy | `python src/pols.py measure --dir data/WT --csv` per group, then `python src/pols.py summary` |
| `src/` | `lacunae.py` (feature 1, detection), `canaliculi.py` (feature 2, detection), `quantification.py` (every measure), `pols.py` (the POL proxy, read from the saved detection), `ai_judge.py` (both judges), `diagnostics.py` (every check, as subcommands) | |
| `config.py` | paths, the biological limits, shared settings and the switches (all off by default) | |
| `data/` | one folder per group: `WT/` with the 8 input images, and `WT_HP/`, `Hyp_RD/` and `Hyp_HP/` with 9 each, decoded from JPEG into lossless TIFF; `image_inventory.csv` lists every source file, what was done with it and the checksum of its pixels | `python src/diagnostics.py import-group --group GROUP --src SOURCE_FOLDER` |
| `results/group_overview.csv`, `.xlsx`, `results/group_qc.csv` | every group side by side, one row per image, and the QC list of the new groups (see Groups) | `python src/diagnostics.py group-overview`, `python src/diagnostics.py group-qc` |
| `figures/` | the figure code, captions and review notes | |
| `docs/` | [`START_HERE.md`](docs/START_HERE.md), [`METHODS.md`](docs/METHODS.md), [`EXPERIMENT_AI.md`](docs/EXPERIMENT_AI.md) | |

Not tracked: `.cache/` and `venv/`, and the diagnostic and archive folders that
commands write into `results/`; [`results/README.md`](results/README.md) lists
each with the command that makes it again.

**Units.** The pixel size is 0.13 um/px, from the confocal acquisition record,
confirmed for all 8 images and rounded to two decimals
(`config.PIXEL_SIZE_UM_ACQUIRED`). Every biological limit is written in
micrometres and converted with it. The measures themselves stay in px and px²:
`config.PIXEL_SIZE_UM` is deliberately `None`, because it is recorded in the
parameters block of every result and switches every scale bar to micrometres, so
setting it would change the recorded values and a fresh run would no longer equal
`results/WT/` at tolerance 0. Convert with 0.13 um/px where a physical length is
wanted.

## Groups

The images are organised by type, one folder per group in `data/` and in
`results/` (`config.GROUPS`). RD is regular diet, HP high phosphorus.

| group | what it is | images | data | results |
|---|---|---|---|---|
| `WT` | wild type: the reference group, the 8 sections every rule was chosen on | 8 | `data/WT/` | `results/WT/` |
| `WT_HP` | wild type, high phosphorus diet | 9 | `data/WT_HP/` | `results/WT_HP/` |
| `Hyp_RD` | Hyp, regular diet | 9 | `data/Hyp_RD/` | `results/Hyp_RD/` |
| `Hyp_HP` | Hyp, high phosphorus diet | 9 | `data/Hyp_HP/` | `results/Hyp_HP/` |

**Every group runs with the same settings.** The rules were chosen by visual
inspection of the WT images, and no parameter may be tuned on any other group
(`docs/METHODS.md` section 21).

**JPEG content is accepted by lossless decoding.** The new groups' source files,
the images used for the ImageJ quantification, are 27 JPEGs; one,
`876_z76c1-2.tif`, is a JPEG named .tif. Each is decoded with Pillow to the
uint8 pixels it holds and written as an uncompressed TIFF in `data/<group>/`
under its own name with `.tif`. Nothing is recompressed, resized or converted
in colour; the TIFF is read back and must equal the decoded pixels; and
`data/image_inventory.csv` records the decoder and the checksum of the pixels
of every file. Shape, channels, sample type and pixel size are still checked.

Why: the format test (`python src/diagnostics.py format-test`, report in
[`results/format_test/format_test.md`](results/format_test/format_test.md),
`docs/METHODS.md` section 22) found that the WT TIFFs themselves hold decoded
JPEG pixels at the same quantization tables. Decoding the new groups' JPEGs
puts every group through the same path. **Caution: the pixels are JPEG-decoded
in all four groups**, with the losses of that compression, and no group has an
uncompressed original. What a first compression does could not be measured,
for the same reason. The pixel size, 0.13 um/px, is confirmed for the 8 WT images only;
the 27 new images carry none in their files and are taken to share it, so every
limit written in micrometres rests on that.

Copy a group's images (the source folder is only read):

```
python src/diagnostics.py import-group --group Hyp_RD --src "SOURCE_FOLDER"
```

One command per group (the three stages on one line, in order):

```
python src/lacunae.py --dir data/WT_HP -o results/WT_HP; python src/canaliculi.py --dir data/WT_HP -o results/WT_HP; python src/quantification.py --dir data/WT_HP -o results/WT_HP
python src/lacunae.py --dir data/Hyp_RD -o results/Hyp_RD; python src/canaliculi.py --dir data/Hyp_RD -o results/Hyp_RD; python src/quantification.py --dir data/Hyp_RD -o results/Hyp_RD
python src/lacunae.py --dir data/Hyp_HP -o results/Hyp_HP; python src/canaliculi.py --dir data/Hyp_HP -o results/Hyp_HP; python src/quantification.py --dir data/Hyp_HP -o results/Hyp_HP
```

WT is made by the command in the folder table above; a run with no `-o` writes
to `results/<name of the input folder>/`. An image that fails is listed in
`results/<group>/all_images/failed_images_<stage>.csv` and skipped, and the
others carry on; a folder with no image writes nothing. Run time: the lacuna
stage takes from seconds to about an hour per image (701_z19 took 58 minutes,
the images with the most lacuna candidates are the slowest), and canaliculi.py
runs it again; Hyp_HP took about 3 hours 40 minutes in all. Then, over every
group:

```
python src/diagnostics.py group-overview   # results/group_overview.csv and .xlsx: one row per image, no statistics
python src/diagnostics.py group-qc         # results/group_qc.csv: lacuna count, rejected candidates by rule, flag outside the WT range
```

The overview holds all 35 images and the QC list the 27 of the new groups. The
publication figures are made for WT only.

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

## Repository notes

The folders are listed at the top, under What each folder is. The lacuna count now includes out-of-focus lacunae, which carry no area or shape;
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
python -u figures/make_figures.py all        # every figure, into results/WT/
```

Detection draws and labels; quantification measures what detection saved, and
every measured number is written only by it. Detection writes
`results/WT/<label>/1_lacunae/` and `2_canaliculi/`: the overlay, the mask, the
skeleton, the verification picture, the lacuna label image, the vascular mask,
the graph with its ownership, and a record of what it did. Quantification reads
those and writes every number into `results/WT/<label>/5_quantification/` and, for a
folder run, `results/WT/all_images/quantification/quantification_all_images.xlsx`,
`.csv` and `.pdf`. `-o` picks another output folder for all three commands;
without it a run writes to `results/<name of the input folder>/`, so
`--dir data/WT` writes `results/WT/`.

Check it:

```
python src/diagnostics.py reference-check    # must PASS: 161.00 / 21.63 / 8.50 on 543-2
python src/diagnostics.py regression         # every number against results/WT/, tolerance 0
python src/diagnostics.py switch-check       # what each switch in config.py changes
python src/diagnostics.py format-test --twins-src "SOURCE_FOLDER/22.04.25/wt"   # TIFF against JPEG on WT
python src/diagnostics.py --help             # every other diagnostic
python src/diagnostics.py survey -d data/WT -o results/survey        # what it does to every image (not tracked)
python src/diagnostics.py shape-picture -d data/WT -o results/network_shape   # not tracked
```

The AI judge method, offline from the decision files already in the repository:

```
python src/diagnostics.py ai-run --dir data/WT            # set 2, results_ai_judge/WT/
python src/diagnostics.py ai-judge --dir data/WT --replay # the judge log replays to the same verdicts
python src/diagnostics.py ai-compare --dir data/WT        # judge off against judge on, pictures and report
python src/diagnostics.py compare-methods --dir data/WT   # both sets side by side, csv and xlsx
```

The AI lacuna judge, offline from its log (all four groups unless `--dir` or
`--image` names fewer):

```
python src/diagnostics.py ai-lacuna-judge -w 20            # dry run: the pictures and the cost, sends nothing
python src/diagnostics.py ai-lacuna-judge -s               # self-test with a stub judge: 27 checks
python src/diagnostics.py ai-lacuna-judge --replay -w 20   # the log replays to the same verdicts
python src/diagnostics.py ai-lacuna-review -w 20           # contact sheets and the table, results_ai_lacunae/review/
python src/diagnostics.py ai-lacuna-run -w 20              # the pipeline with its verdicts, results_ai_lacunae/<group>/
```

The lacuna stage these need is cached in `.cache/ai_lacuna_candidates/` once per
image, so only the first of them waits for it.

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

`results/WT/all_images/quantification/quantification_all_images.xlsx` (and `.csv`
and `.pdf`) has one row per image. Per-lacuna numbers are in
`results/WT/<label>/5_quantification/<label>_quantification.xlsx` (and `.json`, and
`.pdf` to read), one row per lacuna with its shape and its network measures
together.

| image | lacunae (interior) | roots per cell, deterministic | AI judge | ring 30 px per cell (px), deterministic | AI judge | field density px⁻¹, deterministic | AI judge |
|---|---|---|---|---|---|---|---|
| 542_z06 | 19 (15) | 15.13 | 15.80 | 485.5 | 514.4 | 0.0399 | 0.0411 |
| 542_z18 | 13 (11) | 11.82 | 12.45 | 478.1 | 517.9 | 0.0389 | 0.0396 |
| 543-2 | 12 (12) | 8.50 | 9.00 | 369.6 | 410.2 | 0.0431 | 0.0437 |
| 543_3 | 13 (12) | 7.00 | 8.17 | 325.6 | 411.4 | 0.0403 | 0.0436 |
| 543_z13 | 11 (11) | 9.27 | 9.55 | 377.2 | 419.2 | 0.0430 | 0.0430 |
| 682_z08 | 11 (9) | 12.33 | 13.67 | 463.1 | 492.8 | 0.0364 | 0.0367 |
| 682_z23 | 14 (11) | 9.73 | 10.36 | 384.1 | 423.1 | 0.0392 | 0.0404 |
| 682_z29 | 15 (13) | 7.85 | 8.23 | 312.9 | 343.7 | 0.0368 | 0.0374 |

Interior means per cell; field density is skeleton px over analysed px. Both
sets side by side, per lacuna and with the cell pairs whose tracing changed
hands, are in `results_ai_judge/WT/compare/compare_methods.xlsx`. With the judge
on, roots per cell are counted only from the pipeline's own attachments; a
verdict's attachment splits the network but is not a root (`docs/METHODS.md`
section 20).

The figures under `results/WT/<label>/3_publication_figures/` and
`results/WT/all_images/figures/` are tracked, and
`python -u figures/make_figures.py all` redraws any that is missing. The
pipeline's own stage pictures under `1_lacunae/` and `2_canaliculi/` are
tracked too: the skeleton png is an input to `diagnostics.py validate-network`.
There are no publication figures for the AI judge set, because its method has
not been chosen.

## Still open

1. **Validation** against manual (ImageJ) counts. Roots per cell is the
   per-cell number to compare. No manual trace exists yet, and the pipeline
   has not been validated against one.
2. **The ridge scales and the 50 um limit are unvalidated.** The scales were
   measured on this data and the limit comes from the literature; neither has
   been checked against a hand trace.
3. **Lacunae partly outside the focal plane**: whether they should count. A
   breadth-based detector finds 31 to 290% more objects per image, but they are
   dimmer and include vascular canal.
4. **Two thin kept objects on vascular bands**, probably not lacunae: 542_z06 at
   (555,149) and 682_z23 at (363,7). Both are counted now.
5. **The choice between the deterministic method and the AI judge method.**
   Neither has been checked against a manual trace, and a comparison with
   manual counts is what should decide it.
6. **The AI lacuna judge's verdicts.** It says no to 352 of the 793 lacunae the
   filters kept over the four groups, including both objects of item 4, and
   some of the regions it removes look like lacunae on its contact sheets. None
   of its verdicts has been checked against a manual count.
7. **POLs.** The images show no separate lesion zone (`results/pols/FINDINGS.md`),
   so `src/pols.py` measures a proxy, the body plus the surround above the bone
   background, which in WT is optical glow. Whether to keep it, and which fields
   leave the study, are open (`results/pols/REPORT.md`).

Method, every parameter and its origin, limitations and decisions:
[docs/METHODS.md](docs/METHODS.md). New here:
[docs/START_HERE.md](docs/START_HERE.md).
