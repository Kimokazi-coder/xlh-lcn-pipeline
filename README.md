## Repository map

**Status:** pre-validation, pixel units, wild-type (WT) images only.

| folder | what it holds |
|---|---|
| `src/` | the pipeline: `lacunae.py` (feature 1), `canaliculi.py` (feature 2), `diagnostics.py` (every check, as subcommands) |
| `config.py` | paths, shared settings and the switches (all off by default) |
| `data/` | the input images (`data/WT/`, 8 sections) |
| `results/` | the default pipeline output and the reference that `regression` checks; everything per image and all figures, see [`results/README.md`](results/README.md) |
| `results_experiments/` | experiments and checks; map: `results_experiments/INDEX.md` |
| `figures/` | the figure code, captions and review notes |
| `docs/` | method, start page and tuning protocol; the reports are in `docs/reports/` |
| `experiments/` | the scripts behind `results_experiments/` |
| `archive/` | history and earlier analyses, not used by the code |

Run the pipeline, from the repository root:

```
python src/lacunae.py --dir data/WT          # feature 1: lacunae
python src/canaliculi.py --dir data/WT       # feature 2: canaliculi and the summary table
python -u figures/make_figures.py all        # every figure, into results/
```

Check it:

```
python src/diagnostics.py reference-check    # must PASS: 62.33 / 27.41 / 21 on 543-2
python src/diagnostics.py regression         # every number against results/, tolerance 0
```

More: [docs/START_HERE.md](docs/START_HERE.md), [docs/METHODS.md](docs/METHODS.md), [docs/reports/](docs/reports/).

New here? Read [docs/START_HERE.md](docs/START_HERE.md) first: folders, reading order, history, switches and commands on one page.

# lcn-quant

Quantification of the osteocyte lacuno-canalicular network (LCN) in 2D
confocal optical sections of mouse bone. Feature 1 detects and measures the
lacunae. Feature 2 segments the canalicular network, reduces it to a
one-pixel skeleton and measures it per lacuna and per field.

**Pre-validation, pixel units.** No number here has been checked against
manual (ImageJ) counts yet. The images carry no micron calibration, so
lengths are in px and areas in px². The data are 8 wild-type (WT) sections;
no Hyp images have been processed.

## Running it

Python 3.9 with numpy, scipy, scikit-image, networkx, skan, openpyxl and
tifffile (tested with numpy 2.0.2, scipy 1.13.1, scikit-image 0.24.0,
networkx 3.2.1, skan 0.13.1, openpyxl 3.1.5, tifffile 2024.8.30). Run every
command from the repository root.

| | on a folder | on one image |
|---|---|---|
| Feature 1: lacunae | `python src/lacunae.py --dir data/WT` | `python src/lacunae.py --image "data/WT/543-2.tif"` |
| Feature 2: canaliculi | `python src/canaliculi.py --dir data/WT` | `python src/canaliculi.py --image "data/WT/543-2.tif"` |

Each command writes to `results/<label>/1_lacunae/` or `2_canaliculi/` (`--out`
picks another folder). A folder run of feature 2 also writes
`results/all_images/summary_all_images.xlsx` and `.csv`. The layout and the
label of each image: `results/README.md`.

To check the pipeline, run `python src/diagnostics.py reference-check`. It
must print PASS for 62.33 edges per cell, 27.41 px mean edge length and 21
gap bridges on image 543-2. `python src/diagnostics.py --help` lists the
other diagnostics, among them `compare-outputs`, `reach`, `lacuna-table` and `sanity`.

## Folder map

```
src/lacunae.py       feature 1: lacuna detection, counting and measurement
src/canaliculi.py    feature 2: canalicular network, skeleton and measurements
src/diagnostics.py   every diagnostic, as subcommands
config.py            paths and shared settings
data/WT/             the 8 input images
results/             one folder per image, all_images/ and validation_tiles/; see results/README.md
docs/METHODS.md      the method, every parameter and its origin, limitations, decisions
archive/             history and earlier analyses, not needed to run the pipeline
CLEANUP_LOG.md       what the 2026-09-30 cleanup did
```

## Measures

**Headline measures.** None of them depends on which cell owns which thread.
- **Roots per cell**: distinct canalicular threads leaving each lacuna's surface.
- **Ring length 30 px**: skeleton px within 30 px of each lacuna, each pixel
  counted for its nearest lacuna.
- **Field length density**: all skeleton px divided by the analysed field
  area, in px⁻¹.

**Also reported:** lacuna count and interior count (lacunae not touching the
frame; every per-cell mean uses these), area and shape per lacuna, and ring
length at 60 px.

**Not headline measures:** owned length, edge count and mean edge length.
They assign each thread to one cell through the network with no distance
limit, and owned threads reach up to 864 px from their cell, so every output
labels them ownership-dependent. Edge count is a network parameter, not
"canaliculi per cell".

## Results

`results/all_images/summary_all_images.xlsx` (and `.csv`) has one row per image.
Per-lacuna numbers are in `results/<label>/1_lacunae/<label>_lacunae_results.xlsx`
and `results/<label>/2_canaliculi/<label>_canaliculi_results.xlsx`.

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

One overlay per feature, for image 543-2:
- Feature 1, kept lacunae outlined in green:
  [`results/543-2/1_lacunae/543-2_lacunae_outlines.png`](results/543-2/1_lacunae/543-2_lacunae_outlines.png)
- Feature 2, the network figure:
  [`results/543-2/3_publication_figures/543-2_figure_network.png`](results/543-2/3_publication_figures/543-2_figure_network.png).
  The verification picture, each lacuna and the threads it owns in one colour,
  is
  [`results/543-2/2_canaliculi/543-2_canaliculi_verification.png`](results/543-2/2_canaliculi/543-2_canaliculi_verification.png).
  Its colours show an ownership of threads with no distance limit, so they are
  not a headline measure.

## Still open

1. **Validation** against manual (ImageJ) counts. Roots per cell is the
   per-cell number to compare.
2. **Lacunae partly outside the focal plane**: whether they should count.
   A breadth-based detector finds 31 to 290% more objects per image, but
   they are dimmer and include vascular canal.
3. **Two thin kept objects on vascular bands**, probably not lacunae:
   542_z06 at (555,149) and 682_z23 at (363,7). Both are counted now.

Method, parameters, limitations and decisions: [docs/METHODS.md](docs/METHODS.md).

## Checks, switches and figures

```
python src/diagnostics.py regression                 # every number against results/, tolerance 0
python src/diagnostics.py switch-check               # what each switch in config.py changes
python src/diagnostics.py sensitivity -d data/WT -o OUT
python src/diagnostics.py field-summary -d data/WT -o OUT
python src/diagnostics.py blind -s data/WT -o CODED -k KEY_OUTSIDE_REPO.csv
python src/canaliculi.py --dir data/WT -o OTHER_FOLDER   # -o: any output folder; default results/
python -u figures/make_figures.py image -a           # figures into results/<label>/3_publication_figures/
```

The switches in `config.py` (`NARROW_CRUMB_RULE`, `FILL_ENCLOSED_HOLES_MAX_PX2`,
`BAND_FILTER_MIN_OPENING_SHARE`, `FAST_LACUNA_STAGE`, `BAND_LINE_FILTER`) are all off, so the default output is unchanged.
Outputs also carry normalised per-cell columns and a provenance block. Details:
[docs/reports/FIXES_REPORT.md](docs/reports/FIXES_REPORT.md) and [docs/METHODS.md](docs/METHODS.md) section 9.
