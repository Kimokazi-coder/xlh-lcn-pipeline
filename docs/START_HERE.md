# Start here

**What this is.** lcn-quant measures the osteocyte lacuno-canalicular network in 2D confocal sections of
mouse bone (red channel). Feature 1 finds the lacunae. Feature 2 traces the canalicular network as a
one-pixel skeleton. A third step measures both, per lacuna and per field: detection and quantification
are separate scripts, and every measured number comes from the quantification step. The headline
measures are roots per cell, ring length 30 px, field length density and the canalicular width.
Everything is **pre-validation**: nothing has been compared with manual counts yet, and no parameter or
limit has been tuned against one. The data are 8 wild-type sections, which are sections of 3 or 4 fields.

**Units.** The pixel size is 0.13 um/px, from the acquisition record, confirmed for all 8 images and
rounded to two decimals (`config.PIXEL_SIZE_UM_ACQUIRED`). Every biological limit is written in
micrometres and converted with it. The measures stay in px and px², because `config.PIXEL_SIZE_UM` is
deliberately `None`: it is recorded in every result's parameters block and switches every scale bar to
micrometres, so setting it would change the recorded values and a fresh run would no longer equal
`results/` at tolerance 0. Convert with 0.13 um/px where a physical length is wanted.

## The one canalicular method

A canaliculus is found because it is a thin bright **ridge**, not because it is bright. The flattened
channel goes through a **Sato ridge filter at sigmas 3.0, 3.6 and 4.2 px**, the response is thresholded
with hysteresis at a low cut of 0.75, the lacuna bodies and small specks are removed, and the result is
skeletonized. **There is no gap bridging.**

Inside each lacuna's own **zone**, and nowhere else, the response is then multiplied by that lacuna's
**contrast gain** and the same cuts are applied again: one global cut empties a ring around every body,
27.4 px wide at the median, because a thread's contrast there runs at a third to two thirds of normal.
The zone is that lacuna's own **hole**, its empty width measured on the global cut skeleton plus one
thread half width, capped at 8 um, and never a fixed width, because that zone is what widens in Hyp
bone. The gain is the response just beyond the zone over the response inside it, read at the distance
each pixel sits at, because the loss is a trough deepest at the body (METHODS sections 18 and 19).
Mask that did not exist before is kept only if it is 10 um long and three times longer than wide.

A lacuna owns what **touches** it, within 6 px, with no test, and every body a node touches is offered
it, the nearer surface winning; beyond that it owns a thread only where there is **signal all the way
to it**, not merely because it is close. A **second dimmer pass** continues the threads it owns into response down to half the low cut, no
more than 5 px past where the confident skeleton stopped. The **50 um length limit** prunes what runs too
far. Dim thread-shaped structure that no lacuna owns is kept separately as **unattached**: in the field
density, never per lacuna. Every value is in `config.py`; METHODS sections 8 and 9 say where each came
from and what it cost.

This was variant D of the ablation that compared it against the older intensity threshold; that
comparison is at the git tag `archive-2026-10-13`. **No variant was validated against a manual count, so
choosing this one is not a validated result.**

## The biological limits

In `config.py`, in micrometres, fixed and identical for every image. **Neither is validated against this
data**; both figures are what the literature reports for mouse cortical bone, used as plausibility bounds
and never as thresholds tuned to improve a result.

| limit | value | effect |
|---|---|---|
| `MAX_CANALICULUS_LENGTH_UM` | 50 um (385 px) | **prunes** the skeleton |
| `CANALICULUS_LENGTH_RANGE_UM` | 25 to 50 um | report only |

The length limit measures **along the network** from the surface of the owning lacuna, as a geodesic
distance on the skeleton, and prunes what lies beyond. A pixel no lacuna reaches within the limit is not
pruned; it stays, unowned. On these 8 images it removes 1.7 to 20.4% of the skeleton it is applied to, 9.8% over all of them, counting what the final prune removes against what it leaves (`length_prune.removed_px` of each run). The glow zone of METHODS section 18 lowered this: a thread that could not reach a body within 50 um along the network was being deleted, and the zone joins it to the body it belongs to.
Report only, in each image's `biological_limits` json block and xlsx sheet: per-thread length against the
25 to 50 um range, roots per lacuna, and the apparent width, which **includes the optical blur** and is
an upper bound rather than a diameter.

## Lacunae

Four rules in `config.py` find lacunae the plain area, solidity and frame filters
miss: a **dim** sub-area body (big enough, compact, and crucially **not**
saturated), an object the **frame cuts** at a scaled area floor, a large ragged
body with a **thick process**, and a **merge** of one osteocyte that a thin dark
band split in two. A measurement of all 173 candidates over the 8 images chose
every value; notably "brighter than its surroundings" turned out to run backwards
and is not used for this. METHODS section 9 has the detail.

Lacunae found this way are the classes **dim** and **out_of_focus**: counted and
owning their threads, but carrying no area or shape measure.

## What each folder holds

| folder | contents |
|---|---|
| `src/` | `lacunae.py` and `canaliculi.py` (detection), `quantification.py` (every measure), `diagnostics.py` (every check, as subcommands) |
| `config.py` | paths, the biological limits, shared settings and the switches (all off) |
| `data/WT/` | the 8 input images |
| `results/` | the pipeline output: one folder per image, `all_images/` and `validation_tiles/`; the reference for every check; guide: `results/README.md` |
| `manual_trace/` | four raw tiles for the blind hand trace that will produce the ground truth |
| `figures/` | the figure code (`make_figures.py`), captions and review notes |
| `docs/` | this page, `METHODS.md` and `NETWORK_TUNING_PROTOCOL.md` |

Earlier experiments, the older intensity-threshold method, the ablation that chose this one and every
earlier report are preserved at the git tag `archive-2026-10-13` and are not in the working tree. `main`
is the only branch.

## What to read, in this order

1. `README.md`: how to run the pipeline, the method, the limits, the measures and the results table.
2. `docs/METHODS.md`: every step and parameter with its origin, limitations and decisions.
3. `docs/NETWORK_TUNING_PROTOCOL.md`: what may be tuned once hand counts exist, fixed in advance.
4. `results/README.md`, to find a figure or a result.

## The switches

In `config.py`. They all act on the **lacuna** stage, they are all off by default, and with all off the
pipeline gives `results/` exactly.

| switch | default | what it does when on |
|---|---|---|
| `NARROW_CRUMB_RULE` | `False` | a dropped watershed piece rejoins the one kept lacuna it touches if at least half of it lies inside that lacuna's convex hull (changes only 543_3 (877,545)) |
| `FILL_ENCLOSED_HOLES_MAX_PX2` | `0` | fills holes enclosed by one kept lacuna up to this size (200 changes only 542_z06 (783,581)) |
| `BAND_FILTER_MIN_OPENING_SHARE` | `None` | rejects kept objects keeping less than this share of their area after a 5 px opening (0.515 removes the two band objects) |
| `FAST_LACUNA_STAGE` | `False` | bounding-box versions of two lacuna steps: identical labels, 15 to 25 times faster |

## Commands

From the repository root, with the project's Python (3.9, the venv):

```
python src/lacunae.py --dir data/WT                      # feature 1 detection (-o DIR for another folder)
python src/canaliculi.py --dir data/WT                   # feature 2 detection
python src/quantification.py --dir data/WT               # every measure and both tables
python src/diagnostics.py reference-check                # must PASS: 161.00 / 21.63 / 8.50 on 543-2
python src/diagnostics.py regression                     # every number against results/, tolerance 0
python src/diagnostics.py switch-check                   # what each switch changes
python -u figures/make_figures.py all                    # every figure, into results/
python -u figures/make_figures.py check                  # drawn numbers against results/
python src/diagnostics.py survey -d data/WT -o results/survey     # what it does to every image (not tracked)
python src/diagnostics.py shape-picture -d data/WT -o results/network_shape   # not tracked
python src/validate_manual.py                            # score against a hand tracing
```

Do not write a new `results/` unless a switch is adopted on purpose; `results/` is the reference that
`regression` compares with.
