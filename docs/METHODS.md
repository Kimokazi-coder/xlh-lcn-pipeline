# Methods

How the pipeline works, where every parameter value came from, what it
cannot do yet, and the decisions behind its current shape. Condensed on
2026-09-30 from the project's running notes (PROGRESS.md,
DECISIONS_NEEDED.md and the round reports), which are kept in `archive/`.

**Status: pre-validation.** No output has been checked against manual
(ImageJ) counts. **Units: pixels.** The images carry no usable micron
calibration (7 of 8 have no resolution tags; one reports a generic 300 DPI),
so `PIXEL_SIZE_UM` is `None` and nothing is converted. **Data: 8 wild-type
(WT) confocal optical sections** (`data/WT/`, red channel, 1024 x 1024 px).
No Hyp or Hyp;Enpp1 image has been processed, and periosteocytic lesions
(POLs) are not measured.

## 1. Pipeline steps

### Feature 1: lacunae (`src/lacunae.py`)

1. Take the red channel of the image as a float in [0, 1].
2. Split the channel's own histogram into three classes (multi-Otsu:
   background, canalicular network, lacunae) and keep the brightest class.
   Fill holes up to 20 px², remove single-pixel specks.
3. Separate touching bodies by thickness: seeds at each blob's distance
   maxima, then a marker-controlled watershed.
4. Re-merge watershed pieces whose dividing saddle is shallow, so an
   elongated lacuna is not cut in two.
5. Keep objects of 400 px² or more, with solidity at least 0.5 and aspect
   ratio at most 6. Objects touching the frame edge are kept and flagged;
   they count, but all statistics use interior lacunae only.

Per lacuna: area, major and minor axis, aspect ratio, eccentricity,
solidity, orientation, centroid.

### Feature 2: canalicular network (`src/canaliculi.py`)

Adapted from the OCY pipeline (Kollmannsberger et al., New J. Phys. 2017,
github.com/phi-max/OCY_connectomics) where marked. OCY works on 3D stacks;
these are single 2D sections, which drives every departure.

1. **Flatten the background** (OCY): a light Gaussian, a white top-hat, and
   subtraction of the histogram mode, so thin threads stay thin instead of
   fusing into ribbons.
2. **Threshold with hysteresis**: the high cut is the image's own lower
   multi-Otsu cut; dim pixels down to 0.75 of it are kept only where they
   connect to bright ones.
3. **Vascular canals**: broad bright structures are found on the raw
   channel (an opening that erases every canaliculus, then a shape gate far
   above lacuna size). Inside them, hysteresis and gap bridging may not
   add anything. Nothing is removed. This stops a vessel wall from being
   traced as a canaliculus.
4. **Mask and skeleton**: remove the lacuna bodies plus a 2 px buffer and
   specks under 8 px², then reduce to one-pixel centre lines.
5. **Gap bridging** (not in OCY): join a thread end to the nearest other
   thread only if the gap is at most 10 px, points within 40 degrees of the
   thread's direction, and holds signal of at least 0.7 of the threshold at
   every point. Bridges may not touch a lacuna or a vascular structure.
6. **Graph and cleanup** (OCY): spurs under 4 px are pruned, internal edges
   under 6 px (thread crossings) are collapsed, degree-2 chains merged, all
   repeated until nothing changes.
7. **Ownership** (OCY): each lacuna is attached to skeleton nodes within
   10 px of its body. One multi-source shortest-path run gives every
   reachable node to the cell it connects to through the network, and each
   edge to the owner of its nearer end. There is no distance limit.
8. **Measures**, per lacuna and per field (section 3).

## 2. Parameters and where each value came from

"Tuning set" means 542_z06, 543-2 and 682_z29; the other five images were
held out and used to confirm.

| step | parameter | value | origin |
|---|---|---|---|
| lacunae | hole fill | ≤ 20 px² | carried over from the first counter; fills 70 of 71 raw holes in kept lacunae (all ≤ 10 px²) |
| lacunae | seed prominence | 0.3 of each blob's peak | initial value, not tuned; over-splits are re-merged |
| lacunae | saddle re-merge | ratio ≥ 0.35 | between the 3 splits confirmed wrong by eye (≥ 0.364) and one true two-lobe split (0.000) |
| lacunae | minimum area | 400 px² | widest gap (346 to 429 px²) above a pile-up of specks in the pooled area distribution (n = 177) |
| lacunae | minimum solidity | 0.5 | sanity limit; kept lacunae bottom out at 0.525, only two rejected lacuna-scale objects lie in 0.35 to 0.5 |
| lacunae | maximum aspect ratio | 6.0 | sanity limit; kept lacunae top out at 5.76 |
| lacunae | maximum area | 5% of the field | sanity cap; largest kept lacuna is 0.9% |
| network | Gaussian sigma | 0.8 px | below thread width, as in OCY_main.m |
| network | top-hat radius | 5 px | measured thread half-widths p50 3.0, p99 4.2 px; by eye r = 4 fragments and r = 6 fuses threads |
| network | hysteresis low cut | 0.75 × high cut | the one setting (with bridging) inside guards fixed in advance, on tuning and held-out images; 0.5 failed. One value after one failure, not a sweep: the weakest provenance here |
| network | lacuna buffer | 2 px | keeps the lacuna rim from reading as a thread stub |
| network | speck removal | < 8 px² | small enough to keep a short real thread |
| canals | opening radius | 8 px | erases threads (width p99 8.5 px), keeps broad objects |
| canals | shape gate | span ≥ 0.45 of the image and major axis ≥ 420 px | clean gap between lacuna-scale objects (span ≤ 0.23, axis ≤ 211 px) and canals (span ≥ 0.58); WT only |
| canals | dilation | 4 px | network density returns to baseline 4 px from the canal edge |
| bridging | maximum gap | 10 px | signal in gaps drops sharply beyond about 10 px |
| bridging | maximum angle | 40° | keeps the two leading bins of the measured angle distribution |
| bridging | minimum signal | 0.7 of threshold | 93.5% of 5 to 8 px gaps pass, 29.9% of 11 to 15 px gaps |
| graph | spur pruning | < 4 px | thresholding noise |
| graph | crossing collapse | < 6 px | one thread width; OCY's ratio would remove half of all internal edges |
| graph | attach distance | 10 px | every lacuna attaches (largest nearest gap 7 px); 5 px left 28 of 98 unattached |
| roots | merge distance | 8 px | one thread width |
| rings | radii | 30 and 60 px | 30 px from the round 2 local-density work; 60 px is twice that, about two thirds of the median lacuna length (89 px) |

Parameters live as documented constants at the top of `src/lacunae.py`
and `src/canaliculi.py`, each with a longer provenance comment.

## 3. Measures

| measure | level | kind | meaning |
|---|---|---|---|
| lacuna count, interior count | image | headline context | kept lacunae; interior ones do not touch the frame |
| area, axes, aspect, eccentricity, solidity | lacuna | reported | v2 shape measures |
| **roots per cell** (`roots_count`) | lacuna | **headline** | distinct threads leaving the lacuna surface; closest to a count by eye |
| **ring length 30 px** (`ring_length_r30_px`) | lacuna | **headline** | skeleton px within 30 px of the body, each px counted for its nearest lacuna |
| ring length 60 px (`ring_length_r60_px`) | lacuna | reported | the same at 60 px |
| **field length density** | image | **headline** | all skeleton px / analysed area (field minus lacunae), px⁻¹ |
| owned length, edge count, mean edge length | lacuna | ownership-dependent | from graph ownership; network descriptors only |

**Why these are the headline measures.** Between the earlier default
segmentation and the current one (compared on 2026-09-24, adopted on
2026-09-28), edge count per cell moved +78% while roots per cell moved +11%
and length density +13%. When ownership was capped at 225 to
325 px, and even at 100 px, roots, ring lengths and field density did not
move at all, while owned length moved 7.5% across 225 to 325 px and 39% at
100 px. A measure that swings with an unvalidated choice cannot carry a
genotype comparison. **Edge count is not "canaliculi per cell"**: it is an
OCY network parameter, and a tree with T tips has about 2T - 1 edges.

## 4. Known limitations

- **Not validated.** Comparison with manual (ImageJ) counts is the next gate.
- **Pixel units only**, until the acquisition record gives a µm/px value.
- **2D sections of a 3D network.** Threads that leave the focal plane end
  in the image: 76% of skeleton graph nodes are thread ends (python
  src/diagnostics.py sanity), and only about a third of skeleton length is
  graph-connected to any lacuna. Per-field and
  ring measures are preferred for this reason.
- **Ownership is unbounded.** Owned threads end a median 105 px from their
  cell and up to 864 px; 46 of 98 cells own threads more than 200 px away.
- **Lacunae partly outside the focal plane** are mostly not counted. A
  breadth-based detector finds 5 to 29 more objects per image (31 to 290%),
  but they are half as bright and include vascular canal; whether they
  count is open.
- **Known odd objects, recorded and not corrected:** two thin kept objects
  on vascular bands that are probably not lacunae (542_z06 at (555,149)
  and 682_z23 at (363,7)); one outline that leaks into a canalicular loop
  (542_z06 at (106,67), area about 30% high); one lacuna with an unfilled
  146 px² interior hole (542_z06 at (783,581), area 4.3% low).
- **Vascular canals are not removed**, only prevented from growing. An
  automatic exclusion was built and tested; on these images it removed
  mostly ordinary network (density inside canals 0.85 to 1.43 times the
  field), so it was not adopted.
- **Thresholds derived on WT only.** Canal and lacuna gates must be
  re-checked on Hyp fields before use there.
- **Small approximations:** parallel graph edges (1.3% of branches) keep
  only the shorter length; ring lengths count skeleton pixels, so a
  diagonal step counts 1 px.

## 5. Decisions made

| date | decision |
|---|---|
| 2026-09-22 | Top-hat preprocessing, graph cleanup and OCY-style ownership replace a raw threshold and nearest-lacuna assignment. |
| 2026-09-24 | Candidate fragmentation settings judged on two guards fixed before running (length ≤ 1.20x, loops ≤ max(1.5x, +50)), never on owned fraction alone. |
| 2026-09-28 | Hysteresis 0.75 with gap bridging becomes the default; 543-2 reference becomes 62.33 / 27.41 / 21 bridges. Block growth in vascular structures becomes the default. Exclusion stays off. Input images are committed. |
| 2026-09-28 | Local normalization not built: the one sparse lacuna was not in a dim region. |
| 2026-09-29 | Hybrid detector's connectivity override not adopted (3 of 4 examined additions were mesh). Detection stays v2. |
| 2026-09-29 | Thin band objects, the leaked outline and the unfilled hole recorded as known cases; nothing changed. |
| 2026-09-29 | Reach measured; a reach cap and ownership-free measures (roots, ring lengths) built; the cap left off. |
| 2026-09-30 | Final cleanup: the code keeps only the default path; alternatives (v3 and hybrid detectors, adjacent-pair merge, reach cap, ridge and other preprocessing, other assignment and counting methods, exclusion mask) are preserved in `archive/`. Headline measures fixed as roots per cell, ring length 30 px and field length density. |

## 6. Open questions

1. Validation against manual counts (roots per cell is the per-cell number
   to compare).
2. Whether lacunae lying partly outside the focal plane should count.
3. The two thin objects on vascular bands: exclude or keep.
4. Whether the thesis's primary outcome is per field or per cell.

## 7. History

`archive/` holds every earlier script, report and result, and the git tag
`archive-before-cleanup` marks the repository as it was before this
cleanup. Checking out that tag reproduces any earlier analysis.

## 8. Overnight experiments (2026-10-01)

Branch `overnight-fixes`. Experiments only: nothing in `src/` uses them and no default changed.
Report: `docs/reports/OVERNIGHT_REPORT.md`; outputs in `results_experiments/<task>/`.

- `experiments/task0_cache.py`: cache of the default results, timing, and checks that the copied steps reproduce the pipeline.
- `experiments/task1_artefact.py`: TIFF tags, FFT and banding, axis-aligned skeleton runs (682_z08 lattice), notch filter.
- `experiments/task2_thresholds.py`: why visible bodies are missed, the cuts against brightness, sensitivity grid of both cuts and a pooled cut.
- `experiments/task3_lacunae.py`: crumb loss, saddle audit (straight line against widest path), band objects, opening, holes, their network-level effect, a narrower crumb rule, crops.
- `experiments/task4_size.py`: size dependence of roots and ring lengths, and normalised forms.
- `experiments/task5_density.py`: green and blue channels, draft bone ROI, field density three ways, the 542_z06 vertical line.
- `experiments/task6_repeat.py`: field groups from centroid matches and repeatability across sections.

## 9. Additions on branch publication-fixes (2026-10-02)

Pre-validation, pixel units. With every switch off, the pipeline reproduces `results/` exactly
(`python src/diagnostics.py regression`).

### Normalised per-cell measures (appended columns)

Appended after all existing columns of the per-lacuna rows (`canaliculi_measurements.json` and the
`per_lacuna` sheet) and of `summary_table.csv` and `.xlsx` (as interior means). No existing column
changes name, order or value. They answer the size dependence found overnight (roots and ring length
rise with lacuna area; `docs/reports/OVERNIGHT_REPORT.md`, task 4.1).

| column | definition |
|---|---|
| `perimeter_px` | regionprops perimeter of the lacuna, $P$ |
| `ring_area_r30_px2`, `ring_area_r60_px2` | $A_r$: pixels of the nearest-lacuna partition within $r$ px of the body, lacunae excluded |
| `in_frame_fraction_r30`, `in_frame_fraction_r60` | in-frame share of the full $r$ px annulus around this lacuna alone |
| `ring_density_r30`, `ring_density_r60` | $L_r / A_r$, with $L_r$ the ring length (px$^{-1}$) |
| `roots_per_100px_perimeter` | $100 \cdot \text{roots} / P$ |

Definitions as in `experiments/task4_size.py`; the 784 per-lacuna values of the 8 WT images equal
that script's values to the stored digits.

### Switches (all off by default)

In `config.py`; each comment names its evidence. With all off, `results/` is reproduced exactly.

- `NARROW_CRUMB_RULE` (False): after the filters, a dropped watershed piece joins a kept lacuna if it
  touches only that lacuna and at least half of it lies inside the lacuna's convex hull
  (`lacunae.CRUMB_INSIDE_HULL_MIN` = 0.5, in a gap from 0.009 to 1.000 over 4 pieces).
- `FILL_ENCLOSED_HOLES_MAX_PX2` (0): holes fully enclosed by one kept lacuna, up to this size, are filled.
- `BAND_FILTER_MIN_OPENING_SHARE` (None): kept objects keeping less than this share of their area after
  an opening with a 5 px disk are rejected (0.515 sits in a gap that rests on two objects).
- `FAST_LACUNA_STAGE` (False): bounding-box versions of the watershed split and the re-merge; identical
  labels, 15 to 25 times faster.

`python src/diagnostics.py switch-check` shows what each changes on a folder.

### New subcommands of `src/diagnostics.py`

- `regression`: regenerate every image into an ignored folder and compare every json and summary number
  with `results/` at tolerance 0 (provenance ignored), with and without the fast stage.
- `switch-check`: each switch on alone; every lacuna whose area, roots or ring 30 px change.
- `fast-check`: fast against original lacuna stage, labels pixel for pixel at $t_\mathrm{hi}$ 0.8 to 1.2.
- `blind` / `unblind`: coded copies (pixel data only) with the key outside the repository; join a key to
  a summary table.
- `sensitivity`: both Otsu cuts scaled 0.8 to 1.2, alone and together, and one pooled cut; percent
  changes of roots per cell, ring 30 px, field density, lacuna count and bridges.
- `field-summary`: fields from lacuna centroid matching (25 px), per-field means; the field is the unit.

Every json output also carries a `provenance` block (git commit, dirty flag, library versions, config
hash), and `requirements.txt` pins the versions.

### Figures

`figures/make_figures.py` writes PNG (300 dpi) and PDF (embedded TrueType fonts) to `figures_out/`: a
per-image figure for each image (now `per_image/<image>/overview`), a contact sheet (now Fig01), a
lacuna-cut sensitivity figure (now Fig03), a per-field plot (now Fig04) and a supplementary figure of two
switches (now S01); they were called F1 to F5 on branch publication-fixes and were renamed on branch
figures-v2 (section 10), so that no figure name looks like a field name. One display window for the whole
dataset (1st and 99.8th percentile of the pooled red channel); interior lacunae cyan, frame-edge
lacunae yellow; skeleton white over the image at 60%; scale bars in pixels. Captions:
`figures/captions.md`; review notes: `figures/REVIEW.md`.

## 10. Figures v2 (branch figures-v2, 2026-10-02)

Pre-validation, pixel units. Figures only: `src/`, `config.py` and `results/` are unchanged. Report:
`docs/reports/FIGURES_V2_REPORT.md`; map of the figures: `figures_out/INDEX.md`.

- **Network overlay** (`figures_out/per_image/<image>/network`, `main/Fig02` for 543-2). The skeleton
  is drawn as vector segments between the centres of 8-connected neighbouring pixels, so the drawn set
  is exactly the skeleton. A skeleton pixel is vermillion if it lies in the 30 px ring of an interior
  lacuna by the pipeline's own rule (distance to the lacuna masks at most 30 px, nearest lacuna from
  `canaliculi.nearest_lacuna_map`), white otherwise; roots are magenta dots at the root cluster
  centres. Per interior lacuna, the vermillion pixels equal `ring_length_r30_px` and the dots equal
  `roots_count` (asserted).
- **Gallery and hand-count tiles.** Every interior lacuna in a 240 px tile at 3x
  (`per_image/<image>/gallery`), and the same crops of the raw red channel under random codes for
  counting roots by hand (`figures_out/validation_tiles/`, key outside the repository).
- **Figure fixes.** Rejected lacuna-scale candidates (at least 150 px²) are drawn with the filter that
  rejects them; one colour per meaning; figure ids Fig01 to Fig04 and S01 to S03 and fields Field 1 to
  Field 4; the per-field plot from zero with 682_z08 marked; count lines with interior, frame-edge and
  rejected counts; "c" for a lacuna inside a flagged canal region; insets at least 60 px from the frame;
  a fixed display window, with per-image window variants for display only.
- **Regenerate** with `python -u figures/make_figures.py all`; `check` compares the drawing data with
  `results/`.
