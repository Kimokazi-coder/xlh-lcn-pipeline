# Start here

**What this is.** lcn-quant measures the osteocyte lacuno-canalicular network in 2D confocal sections of
mouse bone (red channel). Feature 1 finds the lacunae. Feature 2 traces the canalicular network as a
one-pixel skeleton. A third step measures both, per lacuna and per field: detection and quantification
are separate scripts, and every measured number comes from the quantification step. The headline
measures are roots per cell, ring length 30 px, field length density and the canalicular width.
Everything is **pre-validation**: nothing has been compared with manual counts yet, and no parameter or
limit has been tuned against one. The data are 8 wild-type sections, which are sections of 3 or 4 fields:
the WT group, the reference. Three more groups, WT_HP, Hyp_RD and Hyp_HP, 9 sections each, run with the
same settings; their JPEGs are decoded losslessly into TIFF, and the pixels of all four groups are
JPEG-decoded (README, Groups).

**Units.** The pixel size is 0.13 um/px, from the acquisition record, confirmed for all 8 images and
rounded to two decimals (`config.PIXEL_SIZE_UM_ACQUIRED`). Every biological limit is written in
micrometres and converted with it. The measures stay in px and px², because `config.PIXEL_SIZE_UM` is
deliberately `None`: it is recorded in every result's parameters block and switches every scale bar to
micrometres, so setting it would change the recorded values and a fresh run would no longer equal
`results/WT/` at tolerance 0. Convert with 0.13 um/px where a physical length is wanted.

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
|-|-|-|
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

**Off since 2026-11-05.** The review loop turned these rescue rules off
(`config.LACUNA_RESCUE_RULES = False`, METHODS section 25): on all four groups
nearly everything they added was a fragment. The classes stay in the code and
are empty while the switch is off.

## What each folder holds

The repository holds `README.md`, `config.py`, `requirements.txt`,
`.gitignore`, and four folders:

| folder | contents |
|-|-|
| `src/` | all code: `lacunae.py` and `canaliculi.py` (detection), `quantification.py` (every measure), `pols.py` (the POL section, lacunar size), `make_figures.py` (the figures), `pol_ring_proxy.py` (the retired ring proxy), `ai_judge.py` (both AI judges), `diagnostics.py` (every check, as subcommands) |
| `config.py` | paths, the results layout, the biological limits, shared settings and the switches (all off) |
| `data/` | one folder per group: `WT/` with the 8 input images, `WT_HP/`, `Hyp_RD/`, `Hyp_HP/` with 9 each, decoded from JPEG; `image_inventory.csv` records every file |
| `results/` | every result; guide: [`results/README.md`](../results/README.md) |
| `docs/` | this page, `METHODS.md`, `EXPERIMENT_AI.md`, the judges' examples, and `docs/figures/` (captions, review notes, inset overrides) |

**Where things are in `results/`.** Each group, WT, WT_HP, Hyp_RD and Hyp_HP,
has one folder, `results/<group>/`, with the same five sections, every file in
it named after its image:

| section | holds |
|-|-|
| `1_lacunae/` | the lacunae of each image (outlines, label image, record) and a contact sheet of the group |
| `2_canaliculi/` | the network of each image (mask, skeleton, verification picture, vascular mask, graph, record) and its network figure |
| `3_pols/` | candidate POL measure: lacunar size, pending definition (a picture and a table per image, a group table, a contact sheet) |
| `4_quantification/` | every measured number per image, the group table, the overview and cell gallery figures, and the group figures Fig01 to Fig04, S01, S02 |
| `5_archive/` | what is no longer used: the retired POL ring proxy |
| `<section>/ai_judge/` | the AI lacuna judge's set in each section it writes (its log in `1_lacunae/ai_judge/ai_log/`); for WT also the AI thread judge in `<section>/ai_judge_canaliculi/`. Made before `method-freeze-v1`, so they do not match the current results until rerun (a README in each) |

Beside them, `results/summary/` holds the tables that set the groups side by
side, and `results/archive/` the old material of no one group, with the review
loop of 2026-11-05 (`REVIEW_LOOP.md`) and the bias audit of 2026-11-06
(`audit/REPORT_AUDIT.md`).

**Held-out images.** 2 images per group are kept for the final validation
(`docs/HOLDOUT.md`); in the default DEV mode no stage reads them.

Earlier experiments, the older intensity-threshold method, the ablation that chose this one and every
earlier report are preserved at the git tag `archive-2026-10-13` and are not in the working tree. `main`
is the only branch.

## What to read, in this order

1. `README.md`: how to run the pipeline, the method, the limits, the measures and the results table.
2. `docs/METHODS.md`: every step and parameter with its origin, limitations and decisions.
3. `results/README.md`, to find a figure or a result.

## The switches

In `config.py`. They all act on the **lacuna** stage, they are all off by default, and with all off the
pipeline gives `results/WT/` exactly.

| switch | default | what it does when on |
|-|-|-|
| `NARROW_CRUMB_RULE` | `False` | a dropped watershed piece rejoins the one kept lacuna it touches if at least half of it lies inside that lacuna's convex hull (changes only 543_3 (877,545)) |
| `FILL_ENCLOSED_HOLES_MAX_PX2` | `0` | fills holes enclosed by one kept lacuna up to this size (200 changes only 542_z06 (783,581)) |
| `BAND_FILTER_MIN_OPENING_SHARE` | `None` | rejects kept objects keeping less than this share of their area after a 5 px opening (0.515 removes the two band objects) |
| `FAST_LACUNA_STAGE` | `False` | bounding-box versions of two lacuna steps: identical labels, 15 to 25 times faster |

## Commands

From the repository root, with the project's Python (3.9). `G` is one of WT,
WT_HP, Hyp_RD, Hyp_HP; every command writes into `results/G/` unless it says
otherwise.

```
python src/lacunae.py -d data/G                  # 1_lacunae (-o DIR for another folder)
python src/canaliculi.py -d data/G               # 2_canaliculi
python src/quantification.py -d data/G           # 4_quantification: every measure and the group table
python -u src/make_figures.py -g G all           # figures, into 2_canaliculi and 4_quantification
python src/pols.py measure -d data/G             # 3_pols (every group at once: python src/pols.py all)
python src/diagnostics.py group-overview         # results/summary/group_overview.csv and .xlsx
python src/diagnostics.py group-qc               # results/summary/group_qc.csv
python src/diagnostics.py layout-check           # the five sections of every group, files per section
python src/diagnostics.py reference-check        # must PASS: 166.40 / 23.19 / 7.70 on 543_3
python src/diagnostics.py regression             # every WT number against results/WT/, tolerance 0
python src/diagnostics.py switch-check           # what each switch changes
python src/diagnostics.py import-group -g G -s F # copy a group's images, or say why not
python -u src/make_figures.py -g G check         # drawn numbers against results/G/
```

Before the figures of a group other than WT, its field summary:
`python src/diagnostics.py field-summary -d data/G -r results/G -o .cache/field_summary/G`.

Do not write a new `results/WT/` unless a switch is adopted on purpose; `results/WT/` is the reference that
`regression` compares with.
