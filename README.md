# lcn-quant

Quantification of the osteocyte lacuno-canalicular network (LCN) in 2D confocal
optical sections of mouse bone. Feature 1 detects and measures the lacunae.
Feature 2 segments the canalicular network, reduces it to a one-pixel skeleton
and measures it per lacuna and per field.

**Status: pre-validation.** No number here has been checked against manual
(ImageJ) counts yet. The data are 8 wild-type (WT) sections; no Hyp images have
been processed.

**Units.** The pixel size is 0.13 um/px, from the confocal acquisition record,
confirmed for all 8 images and rounded to two decimals. The pipeline still
reports lengths in px and areas in px²: `config.PIXEL_SIZE_UM` is deliberately
`None`, because it is recorded in the parameters block of every result and
switches every scale bar to micrometres, so setting it would change the recorded
values and a fresh run would no longer equal `results/` at tolerance 0. Convert
with 0.13 um/px where a physical length is wanted. The experimental ridge method
works in micrometres throughout.

## Repository map

| path | what it holds |
|---|---|
| `src/` | the pipeline: `lacunae.py` (feature 1, detection), `canaliculi.py` (feature 2, detection), `quantification.py` (every measure), `diagnostics.py` (every check, as subcommands) |
| `src/canal_physical/` | the experimental ridge method, not the pipeline (see below) |
| `config.py` | paths, shared settings and the switches (all off by default) |
| `data/WT/` | the 8 input images |
| `results/` | the pipeline output and the reference that `regression` checks; see [`results/README.md`](results/README.md) |
| `results/ridge/` | the ridge comparison: the tables and one side by side figure per image |
| `manual_trace/` | four raw tiles for the blind hand trace that will produce the ground truth |
| `figures/` | the figure code, captions and review notes |
| `docs/` | [`START_HERE.md`](docs/START_HERE.md), [`METHODS.md`](docs/METHODS.md), [`NETWORK_TUNING_PROTOCOL.md`](docs/NETWORK_TUNING_PROTOCOL.md) |

Earlier experiments, reports and analyses are not in the working tree. They are
preserved at the git tag `archive-2026-10-13`.

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
skeleton, the verification picture, the lacuna label image, the vascular and
bridged-pixel masks, the graph with its ownership, and a record of what it did.
Quantification reads those and writes every number into
`results/<label>/5_quantification/` and, for a folder run,
`results/all_images/quantification/quantification_all_images.xlsx`, `.csv` and
`.pdf`. `-o` picks another output folder for all three commands.

Check it:

```
python src/diagnostics.py reference-check    # must PASS: 62.33 / 27.41 / 21 on 543-2
python src/diagnostics.py regression         # every number against results/, tolerance 0
python src/diagnostics.py switch-check       # what each switch in config.py changes
python src/diagnostics.py --help             # every other diagnostic
```

The switches in `config.py` (`NARROW_CRUMB_RULE`, `FILL_ENCLOSED_HOLES_MAX_PX2`,
`BAND_FILTER_MIN_OPENING_SHARE`, `FAST_LACUNA_STAGE`, `BAND_LINE_FILTER`) are all
off, so the default output is unchanged.

## Measures

**Headline measures.** None of them depends on which cell owns which thread.
- **Roots per cell**: distinct canalicular threads leaving each lacuna's surface.
- **Ring length 30 px**: skeleton px within 30 px of each lacuna, each pixel
  counted for its nearest lacuna.
- **Field length density**: all skeleton px divided by the analysed field area,
  in px⁻¹.
- **Canalicular width**: twice the Euclidean distance transform of the mask at
  each skeleton pixel, so the local full width of a thread, in px. The threads
  are only about 2 to 6 px wide, so this sits close to the pixel grid, it moves
  with the threshold, and it is not validated.

**Also reported:** lacuna count and interior count (lacunae not touching the
frame; every per-cell mean uses these), area and shape per lacuna, and ring
length at 60 px.

**Not headline measures:** owned length, edge count and mean edge length. They
assign each thread to one cell through the network with no distance limit, and
owned threads reach up to 864 px from their cell, so every output labels them
ownership-dependent. Edge count is a network parameter, not "canaliculi per
cell".

## The experimental ridge method

`src/canal_physical/` thresholds a multiscale ridge response instead of the
flattened intensity, with every scale set in micrometres from the pixel size.
Three variants are run and reported side by side, in this order:

| variant | what |
|---|---|
| P5 | ridge, sigmas 0.17, 0.21 and 0.26 um, gap bridging off |
| A | the current method, as it stands |
| P2 | ridge, same scales and same cut, gap bridging on |

**P5 is listed first because it is my preferred variant visually. That is a
visual preference and it is not validated.**

P5 and P2 carry the same scales and the same cut, so they differ by that one
switch and nothing else, and the difference between their numbers is the effect
of bridging alone.

```
python src/canal_physical/physical.py --dir data/WT     # -> results/ridge/
```

**Nothing about this method is validated.** No variant has been checked against
a manual count and none is called better than another by any number; it is a
diagnosis, not a claim of improvement. Every run asserts that variant A still
equals `results/` at tolerance 0 with a pixel-identical verification image, so
the comparison rests on the pipeline itself.

`results/ridge/` holds the comparison table (`comparison_all_images.csv` and
`.xlsx`, `comparison_summary.csv`), a README recording every parameter and the
provenance, and per image `<label>/<label>_compare.png`, the three variants side
by side.

## Results

`results/all_images/quantification/quantification_all_images.xlsx` (and `.csv`
and `.pdf`) has one row per image. Per-lacuna numbers are in
`results/<label>/5_quantification/<label>_quantification.xlsx` (and `.json`, and
`.pdf` to read), one row per lacuna with its shape and its network measures
together.

| image | lacunae (interior) | median area px² | roots per cell | ring 30 px per cell (px) | field density px⁻¹ |
|---|---|---|---|---|---|
| 542_WT_2_z06c1-2 | 16 (13) | 3013 | 8.62 | 361.5 | 0.0347 |
| 542_WT_2_z18c1-2 | 12 (11) | 3684 | 8.27 | 357.1 | 0.0341 |
| 543-2 | 12 (12) | 2066 | 7.58 | 306.6 | 0.0447 |
| 543_3 | 10 (9) | 2174 | 6.89 | 313.6 | 0.0451 |
| 543_z13c1-2 | 11 (11) | 1736 | 6.73 | 302.9 | 0.0438 |
| 682_z08c1-2 | 10 (8) | 2672 | 10.00 | 396.8 | 0.0346 |
| 682_z23c-2 | 14 (11) | 1519 | 6.73 | 283.4 | 0.0383 |
| 682_z29c1-3 | 13 (11) | 1624 | 5.55 | 250.3 | 0.0375 |

The figures under `results/<label>/3_publication_figures/` are regenerated by
`python -u figures/make_figures.py all` and are not tracked. The pipeline's own
stage pictures under `1_lacunae/` and `2_canaliculi/` are tracked: the skeleton
png is an input to `diagnostics.py validate-network`.

## Still open

1. **Validation** against manual (ImageJ) counts. Roots per cell is the
   per-cell number to compare. The tiles for the blind trace are in
   `manual_trace/`; the rules for tuning afterwards are fixed in advance in
   [docs/NETWORK_TUNING_PROTOCOL.md](docs/NETWORK_TUNING_PROTOCOL.md).
2. **Lacunae partly outside the focal plane**: whether they should count. A
   breadth-based detector finds 31 to 290% more objects per image, but they are
   dimmer and include vascular canal.
3. **Two thin kept objects on vascular bands**, probably not lacunae: 542_z06 at
   (555,149) and 682_z23 at (363,7). Both are counted now.

Method, every parameter and its origin, limitations and decisions:
[docs/METHODS.md](docs/METHODS.md). New here:
[docs/START_HERE.md](docs/START_HERE.md).
