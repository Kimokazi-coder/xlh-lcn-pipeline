# Start here

**What this is.** lcn-quant measures the osteocyte lacuno-canalicular network in 2D confocal sections of
mouse bone (red channel). Feature 1 finds the lacunae. Feature 2 traces the canalicular network as a
one-pixel skeleton. A third step measures both, per lacuna and per field: detection and quantification
are separate scripts, and every measured number comes from the quantification step. The headline
measures are roots per cell, ring length 30 px, field length density and the canalicular width.
Everything is **pre-validation**: nothing has been compared with manual counts yet. The data are 8
wild-type sections, which are sections of 3 or 4 fields.

**Units.** The pixel size is 0.13 um/px, from the acquisition record, confirmed for all 8 images and
rounded to two decimals. The pipeline nevertheless reports px and px², because `config.PIXEL_SIZE_UM`
is deliberately `None`: it is recorded in every result's parameters block and switches every scale bar
to micrometres, so setting it would change the recorded values and a fresh run would no longer equal
`results/` at tolerance 0. Convert with 0.13 um/px where a physical length is wanted.

## What each folder holds

| folder | contents |
|---|---|
| `src/` | the pipeline: `lacunae.py` and `canaliculi.py` (detection), `quantification.py` (every measure), `diagnostics.py` (every check, as subcommands) |
| `src/canal_physical/` | the experimental ridge method, not the pipeline |
| `config.py` | paths, shared settings and the switches (all off) |
| `data/WT/` | the 8 input images |
| `results/` | the pipeline output: one folder per image, `all_images/` and `validation_tiles/`; the reference for every check; guide: `results/README.md` |
| `results/ridge/` | the ridge comparison: the tables and one side by side figure per image |
| `manual_trace/` | four raw tiles for the blind hand trace that will produce the ground truth |
| `figures/` | the figure code (`make_figures.py`), captions and review notes |
| `docs/` | this page, `METHODS.md` and `NETWORK_TUNING_PROTOCOL.md` |

Earlier experiments, reports and analyses are preserved at the git tag `archive-2026-10-13` and are not
in the working tree.

## What to read, in this order

1. `README.md`: how to run the pipeline, the measures and the results table.
2. `docs/METHODS.md`: every step and parameter with its origin, limitations and decisions.
3. `docs/NETWORK_TUNING_PROTOCOL.md`: what may be tuned once hand counts exist, fixed in advance.
4. `results/README.md`, to find a figure or a result.

## The experimental ridge method

`src/canal_physical/` thresholds a multiscale ridge response instead of the flattened intensity, with
every scale set in micrometres. Five variants, reported in this order: **P5** the ridge at 0.17, 0.21 and
0.26 um, **A** the current method as it stands, and **D**, **F** and **G**, the ablation variants restored
from the tag `archive-2026-10-13` at 3.0, 3.6, 4.2 px, at a single 3.0 px, and at 1.5, 2.0, 2.5 px. Every
ridge variant has gap bridging off, so the scales are the only thing separating them. P5 leads because it
is the preferred variant visually, which is a visual preference and is **not validated**.
`python src/canal_physical/physical.py --dir data/WT` writes the comparison into `results/ridge/`.
**Nothing about this method is validated** and no variant is called better than another by any number.

## The switches

In `config.py`. All are off by default; with all off, the pipeline gives `results/` exactly.

| switch | default | what it does when on |
|---|---|---|
| `NARROW_CRUMB_RULE` | `False` | a dropped watershed piece rejoins the one kept lacuna it touches if at least half of it lies inside that lacuna's convex hull (changes only 543_3 (877,545)) |
| `FILL_ENCLOSED_HOLES_MAX_PX2` | `0` | fills holes enclosed by one kept lacuna up to this size (200 changes only 542_z06 (783,581)) |
| `BAND_FILTER_MIN_OPENING_SHARE` | `None` | rejects kept objects keeping less than this share of their area after a 5 px opening (0.515 removes the two band objects) |
| `FAST_LACUNA_STAGE` | `False` | bounding-box versions of two lacuna steps: identical labels, 15 to 25 times faster |
| `BAND_LINE_FILTER` | `False` | removes the zone around straight skeleton runs that reach the vascular mask; no value is recommended, so it refuses to run until `BAND_LINE_MIN_LEN_PX` and `BAND_LINE_REACH_PX` are set deliberately |

## Commands

From the repository root, with the project's Python (3.9, the venv):

```
python src/lacunae.py --dir data/WT                      # feature 1 detection (-o DIR for another folder)
python src/canaliculi.py --dir data/WT                   # feature 2 detection
python src/quantification.py --dir data/WT               # every measure and both tables
python src/diagnostics.py reference-check                # must PASS: 62.33 / 27.41 / 21 on 543-2
python src/diagnostics.py regression                     # every number against results/, tolerance 0
python src/diagnostics.py switch-check                   # what each switch changes
python -u figures/make_figures.py all                    # every figure, into results/
python -u figures/make_figures.py check                  # drawn numbers against results/
python src/canal_physical/physical.py --dir data/WT      # the ridge comparison, into results/ridge/
```

Do not write a new `results/` unless a switch is adopted on purpose; `results/` is the reference that
`regression` compares with.
