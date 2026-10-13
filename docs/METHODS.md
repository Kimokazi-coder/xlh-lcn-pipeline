# Methods

How the pipeline works, where every parameter value came from, what it
cannot do yet, and the decisions behind its current shape.

**Status: pre-validation.** No output has been checked against manual
(ImageJ) counts.

**Units.** The pixel size is 0.13 um/px, from the confocal acquisition record,
confirmed for all 8 images and rounded to two decimals. The pipeline reports
px and px² all the same: `PIXEL_SIZE_UM` is deliberately `None`, because it is
recorded in every result's parameters block and switches every scale bar to
micrometres, so setting it would change the recorded values and a fresh run
would no longer equal `results/` at tolerance 0. Convert with 0.13 um/px where
a physical length is wanted; the experimental ridge method (section 7) works in
micrometres throughout.

**Data: 8 wild-type (WT) confocal optical sections** (`data/WT/`, red channel,
1024 x 1024 px). No Hyp or Hyp;Enpp1 image has been processed, and
periosteocytic lesions (POLs) are not measured.

## 1. Pipeline steps

Detection and quantification are separate scripts. `src/lacunae.py` and
`src/canaliculi.py` find, trace and draw, and save what they found;
`src/quantification.py` measures that and writes every number. No measure is
computed in two places.

### Feature 1: lacunae, detection (`src/lacunae.py`)

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

It writes the outlines picture and the lacuna label image (0 outside a kept
lacuna, its 1..N id inside), which is what the measures are taken from.

### Feature 2: canalicular network, detection (`src/canaliculi.py`)

Adapted from the OCY pipeline (Kollmannsberger et al., New J. Phys. 2017,
github.com/phi-max/OCY_connectomics) where marked. OCY works on 3D stacks;
these are single 2D sections, which drives every departure.

1. **Flatten the background** (OCY): a light Gaussian, a white top-hat, and
   subtraction of the histogram mode, so thin threads stay thin instead of
   fusing into ribbons.
2. **Ridge filter** (not in OCY): the Sato tubeness of the flattened image over
   sigmas 3.0, 3.6 and 4.2 px, as the maximum across the scales
   (`canaliculi.RIDGE_SIGMAS_PX`). A canaliculus is detected because it is a
   thin bright ridge, not because it is bright. Sato rather than Frangi: both
   are Hessian based, and Sato's tubeness keeps one response per scale without
   Frangi's second shape term, which is tuned for blob rejection and would add
   two more constants with no evidence here.
3. **Threshold the RESPONSE with hysteresis**: the high cut is the response's
   own lower multi-Otsu cut; dim pixels down to 0.75 of it are kept only where
   they connect to bright ones.
4. **Vascular canals**: broad bright structures are found on the raw channel
   (an opening that erases every canaliculus, then a shape gate far above
   lacuna size). Inside them hysteresis may not add anything. Nothing is
   removed. This stops a vessel wall from being traced as a canaliculus.
5. **Mask and skeleton**: remove the lacuna bodies plus a 2 px buffer and
   specks under 8 px², then reduce to one-pixel centre lines. **There is no gap
   bridging**: a gap is left as a gap.
6. **Graph and cleanup** (OCY): spurs under 4 px are pruned, internal edges
   under 6 px (thread crossings) are collapsed, degree-2 chains merged, all
   repeated until nothing changes.
7. **Ownership** (OCY, with one departure): each lacuna is attached to skeleton
   nodes within 20 px of its body **that have ridge signal all the way to it**
   (section 8). One multi-source shortest-path run then gives every reachable
   node to the cell it connects to through the network, and each edge to the
   owner of its nearer end.
8. **The 50 um length limit** (section 7): every skeleton pixel further than
   that from the surface of its owning lacuna, measured along the network, is
   pruned, and ownership is rebuilt on what is left.
It writes the mask, the skeleton, the verification picture, the vascular mask and
the cleaned graph with its ownership.

This is **one** method and there is no switch for another. It was variant D of
the ablation that compared it against the older intensity threshold, which is
preserved at the git tag `archive-2026-10-13`. **No variant was validated against
a manual count, so choosing this one is not a validated result.**

### Quantification (`src/quantification.py`)

Reads the label image, the masks and the graph above, and measures them
(section 3). Per lacuna: area, major and minor axis, aspect ratio,
eccentricity, solidity, orientation, centroid, the frame-edge flag, and every
network measure. Per image: the counts, the interior statistics and the field
measures. It writes `results/<label>/5_quantification/` (json, xlsx and a plain
pdf) and the one cross-image table,
`results/all_images/quantification/quantification_all_images.csv`, `.xlsx` and
`.pdf`. Every statistic is over interior lacunae only, as before.

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
| network | ridge sigmas | 3.0, 3.6, 4.2 px | they bracket the measured thread half widths (p50 3.0, p99 4.2 px) with one step between; a Sato filter answers to a tube whose radius is near sigma. Measured on this data, never from a published value, and NOT validated |
| network | top-hat radius | 5 px | measured thread half-widths p50 3.0, p99 4.2 px; by eye r = 4 fragments and r = 6 fuses threads |
| network | hysteresis low cut | 0.75 × high cut | carried over unchanged from the intensity method, where it was the one setting inside guards fixed in advance; 0.5 failed. One value after one failure, not a sweep: the weakest provenance here |
| network | lacuna buffer | 2 px | keeps the lacuna rim from reading as a thread stub |
| network | speck removal | < 8 px² | small enough to keep a short real thread |
| canals | opening radius | 8 px | erases threads (width p99 8.5 px), keeps broad objects |
| canals | shape gate | span ≥ 0.45 of the image and major axis ≥ 420 px | clean gap between lacuna-scale objects (span ≤ 0.23, axis ≤ 211 px) and canals (span ≥ 0.58); WT only |
| canals | dilation | 4 px | network density returns to baseline 4 px from the canal edge |
| graph | spur pruning | < 4 px | thresholding noise |
| graph | crossing collapse | < 6 px | one thread width; OCY's ratio would remove half of all internal edges |
| graph | attach distance | 10 px | every lacuna attaches (largest nearest gap 7 px); 5 px left 28 of 98 unattached |
| roots | merge distance | 8 px | one thread width |
| rings | radii | 30 and 60 px | 30 px from the round 2 local-density work; 60 px is twice that, about two thirds of the median lacuna length (89 px) |
| limits | maximum canalicular length | 50 um = 385 px | the outer end of the reported lacuna-to-lacuna spacing in mouse cortical bone, so a thread longer than this from one cell body is not one canaliculus. A plausibility bound from the literature, NOT validated on this data and never tuned to improve a result |
| limits | reported length range | 25 to 50 um | report only, acted on by nothing; the range the literature reports for canalicular length |
| ownership | attach reach | 2.6 um = 20 px | was 10 px while attachment went by distance alone. With the signal test deciding, a longer reach cannot cross empty space, and contact threads sat 10 to 20 px out. 25 px was tried and changed no guard number, so the shorter value stands |
| ownership | attach minimum signal | 0.7 of the response's low cut | the fraction the old gap bridging required of a gap, measured the same way: the MINIMUM along the path, not the mean |

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
| **canalicular width** (`width_median_px`, `ring_width_mean_r30_px`) | image, lacuna | **headline**, new | local full width of a thread: 2 x the Euclidean distance transform of the canalicular mask at each skeleton pixel |

**Canalicular width.** At every skeleton pixel the distance transform of the
mask gives the distance to the nearest pixel outside the thread, so twice it is
the local full width in px. The width is measured only where there is real
signal under the skeleton, which every mask pixel now has, since nothing is
drawn into the mask that the threshold did not put there. Left out are the
lacuna buffer and the vascular mask with its
dilation, because a broad bright canal is not a canaliculus. Per image the mean,
median, p10 and p90 and the number of pixels used; per lacuna the mean over its
own 30 px ring, with the ownership rule of `ring_length_r30_px`. On these 8 WT
sections the median is 6.0 px in seven images and 6.3 px in 542_z06, which
matches the thread half width measured for the top-hat radius (section 2: p50
3.0 px, p99 4.2 px).

**What the width cannot do yet.** The threads are only about 2 to 6 px wide, so
the measure sits close to the pixel grid and is quantised in steps of about 1 px;
a median of exactly 6.0 px in seven of eight images is that quantisation, not a
real agreement to three digits. It moves with the threshold, because a lower cut
makes every thread wider, so it carries the provenance of the hysteresis low cut
(the weakest in section 2). It is **not validated**: no manual width measurement
exists for these images.

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
- **Canalicular width is quantised and threshold dependent** (section 3), and
  no manual width measurement exists to check it against.

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
| 2026-09-30 | Final cleanup: the code keeps only the default path; alternatives (v3 and hybrid detectors, adjacent-pair merge, reach cap, ridge and other preprocessing, other assignment and counting methods, exclusion mask) are preserved at the git tag `archive-2026-10-13`. Headline measures fixed as roots per cell, ring length 30 px and field length density. |
| 2026-10-13 | ONE canalicular method: the ridge method with gap bridging off, ablation variant D, at sigmas 3.0, 3.6 and 4.2 px. The intensity threshold, gap bridging, the band-wall filter and every other variant are deleted and live at the tag. |
| 2026-10-13 | The 50 um length limit is adopted, measured along the network, and prunes. Two report-only limits are added beside it. Nothing about any of them is validated. |
| 2026-10-13 | The repository keeps only what the pipeline, the figures and the checks use. Earlier experiments, reports and analyses live at the tag `archive-2026-10-13`. |

## 6. Open questions

1. Validation against manual counts (roots per cell is the per-cell number
   to compare). Nothing in this pipeline has been validated: not the ridge
   scales, not the 50 um limit, not a single measure.
2. Whether lacunae lying partly outside the focal plane should count.
3. The two thin objects on vascular bands: exclude or keep.
4. Whether the thesis's primary outcome is per field or per cell.

## 7. The biological limits

Fixed in `config.py`, written in micrometres, identical for every image, and
converted once with `PIXEL_SIZE_UM_ACQUIRED` = 0.13 um/px, so the micrometre
value is the parameter and the pixel value follows from it.

| limit | micrometres | pixels | effect |
|---|---|---|---|
| `MAX_CANALICULUS_LENGTH_UM` | 50 | 385 | **prunes the skeleton** |
| `CANALICULUS_LENGTH_RANGE_UM` | 25 to 50 | 192 to 385 | report only |

**Source, and what it is not.** Both figures are what the osteocyte literature
reports for mouse cortical bone: 50 um is the outer end of the reported
lacuna-to-lacuna spacing, so a thread running further than that from one cell
body is not one canaliculus but a tracing error or a thread belonging to a lacuna
outside the section. They are used as plausibility bounds. **Neither has been
checked against a manual count on this data**, neither was chosen by looking at
what it did to a result, and no literature value is ever used as a threshold that
tunes an outcome.

### (a) The length limit, which prunes

Every skeleton pixel further than 385 px from a lacuna surface, measured **along
the network**, is removed, and ownership is rebuilt on what is left.

The distance is a geodesic distance on the skeleton itself
(`skimage.graph.MCP_Geometric`, in `canaliculi.network_distance_map`): a path may
travel only along skeleton pixels and across the lacuna buffer that separates a
thread from the body it belongs to, a diagonal step costs the square root of 2,
and every lacuna body is a source at distance 0, so the shortest path decides
which lacuna a thread is measured from, which is the rule ownership already uses.
It is deliberately independent of the network graph and its cleanup, so the limit
is enforced on the same quantity the report measures.

A pixel that **no** lacuna reaches within the limit is **not** pruned: there is
no owning lacuna to measure a length from, so the limit says nothing about it and
it stays in the skeleton, unowned.

Pruning can cut a path and leave what lay behind it reachable only by a longer
way round, which can push another pixel past the limit, so the prune repeats to a
fixed point. On these 8 images one round settles it.

What it removes, as skeleton px and total chain-code length:

| image | px before | px after | removed | um before | um after |
|---|---|---|---|---|---|
| 542_z06 | 38921 | 37752 | 1169 (3.0%) | 5726.0 | 5555.1 |
| 542_z18 | 37595 | 34260 | 3335 (8.9%) | 5532.1 | 5036.9 |
| 543-2 | 45028 | 35034 | 9994 (22.2%) | 6676.3 | 5185.3 |
| 543_3 | 46104 | 35500 | 10604 (23.0%) | 6829.1 | 5250.8 |
| 543_z13 | 44036 | 36701 | 7335 (16.7%) | 6511.3 | 5419.5 |
| 682_z08 | 37407 | 32768 | 4639 (12.4%) | 5464.6 | 4792.3 |
| 682_z23 | 42338 | 34205 | 8133 (19.2%) | 6231.2 | 5033.2 |
| 682_z29 | 40390 | 29332 | 11058 (27.4%) | 5923.0 | 4311.3 |
| **all 8** | **331819** | **275552** | **56267 (17.0%)** | | |

### (b) Report only, acted on by nothing

In the `biological_limits` block of each image's json and the sheet of the same
name in its xlsx.

- **Per-thread length against the 25 to 50 um range.** A thread is the run from a
  lacuna surface to a thread tip, by the same geodesic measure the limit prunes
  on, so the two cannot disagree. Reported as the share inside the range, below
  it and above it, with the median and the percentiles. The comparison is made in
  whole pixels against the bounds as applied, because 385 px is 50.05 um and
  comparing a micrometre length against 50.00 would put a thread the prune kept
  just outside the range.
- **Roots per lacuna**, over interior lacunae.
- **The apparent width.** Twice the distance transform of the mask at each
  sampled skeleton pixel. It **includes the optical blur**, which widens a thread
  beyond its true size, and no point spread function is subtracted because the
  numerical aperture, the emission wavelength and the pinhole are unknown. It is
  therefore an **upper bound on the diameter**, not the diameter, and the json
  says so in the block itself.

## 8. Ownership by signal, not by distance

A lacuna owns a thread only if there is a thread between them.

The rule was distance alone: any skeleton graph node within 10 px of a lacuna
body was linked to it, whatever lay in between, and the multi-source Dijkstra
then handed that lacuna the whole connected component beyond the node. A survey
of all 8 images (`python src/diagnostics.py survey`) found this is not rare:
**about half of every image's attachments cross a gap with no signal in it**, 39
to 120 per image. On 543_3 one such attachment handed lacuna 7 a 1214 px network
across 8.5 px of empty space.

So an attachment must now show evidence. The straight path from the nearest point
of the lacuna surface to the node is sampled about once per pixel, and its
**dimmest** point must reach `config.LACUNA_ATTACH_MIN_SIGNAL_FRACTION` of the
ridge response's own low cut. The minimum, not the mean, because one
background-level pixel breaks a thread however bright its two ends are. Because
the test asks for evidence instead of trusting proximity, the reach is longer,
`config.LACUNA_ATTACH_REACH_UM` = 2.6 um = 20 px, which recovers contact threads
that were just out of the old range.

**Why the ridge response and not the flattened intensity.** Both were measured
before choosing. The top-hat flattening removes the lacuna body, so it digs a
trough around every lacuna, and a path leaving a surface crosses that trough: on
the flattened intensity the median path minimum sits *on* the 0.7 threshold in
seven of eight images, so the test cuts through the middle of the population and
refuses real contacts along with empty space. Implemented that way it cost 10 to
16% of the owned length on four images and left lacuna 7 owning 9 px. On the
response, which is what the method actually thresholds, the same fraction selects
a much smaller and more specific set.

**What it cost, and what it did not.** The skeleton is untouched: this step moves
pixels between owned and unowned and changes no detection. Owned length per cell
falls 0.1 to 5.5% on seven images, and 11.9% on 543_3, which is over the 10%
guard. That image is where the rule bites hardest and the loss is the rule
working: lacuna 7's 1214 px network really does sit across empty space, so no
constant that still demands signal can give it back. A longer reach was tried
(25 px) and changed the figure not at all. The loss is carried into section 9,
which exists to recover real dim threads, and the guard is judged on the result
of both.

**Not validated.** No hand count chose the reach or the fraction.

## 9. Normalised per-cell measures

Appended after all existing columns of the per-lacuna rows and of the
cross-image table, as interior means. No existing column changes name, order or
value. They answer the size dependence found earlier: roots and ring length rise
with lacuna area.

| column | definition |
|---|---|
| `perimeter_px` | regionprops perimeter of the lacuna, $P$ |
| `ring_area_r30_px2`, `ring_area_r60_px2` | $A_r$: pixels of the nearest-lacuna partition within $r$ px of the body, lacunae excluded |
| `in_frame_fraction_r30`, `in_frame_fraction_r60` | in-frame share of the full $r$ px annulus around this lacuna alone |
| `ring_density_r30`, `ring_density_r60` | $L_r / A_r$, with $L_r$ the ring length (px$^{-1}$) |
| `roots_per_100px_perimeter` | $100 \cdot \text{roots} / P$ |

Added later: ring attached length 30 / 60 px (the ring length pixels in threads
reaching within 10 px of the lacuna, passing threads left out); ring length and
field length density weighted with chain code lengths ($\sqrt{2}$ per diagonal
step); Sholl crossings at 10 / 20 / 30 px, the skeleton components crossing a
1.5 px band at that distance, computed without the graph.

## 10. Switches (all off by default)

In `config.py`; each comment names its evidence. They all act on the **lacuna**
stage: the canalicular method has no switch, because there is only one method.
With all off, `results/` is reproduced exactly
(`python src/diagnostics.py regression`).

- `NARROW_CRUMB_RULE` (False): after the filters, a dropped watershed piece joins a kept lacuna if it
  touches only that lacuna and at least half of it lies inside the lacuna's convex hull
  (`lacunae.CRUMB_INSIDE_HULL_MIN` = 0.5, in a gap from 0.009 to 1.000 over 4 pieces).
- `FILL_ENCLOSED_HOLES_MAX_PX2` (0): holes fully enclosed by one kept lacuna, up to this size, are filled.
- `BAND_FILTER_MIN_OPENING_SHARE` (None): kept objects keeping less than this share of their area after
  an opening with a 5 px disk are rejected (0.515 sits in a gap that rests on two objects).
- `FAST_LACUNA_STAGE` (False): bounding-box versions of the watershed split and the re-merge; identical
  labels, 15 to 25 times faster. It changes speed, not output.
`python src/diagnostics.py switch-check` shows what each one changes on a folder.

## 11. Checks (`src/diagnostics.py`)

- `reference-check`: 109.25 edges per cell, 24.11 px mean edge length and 6.00 roots per cell on
  543-2. The third number was the gap bridge count, which no longer exists; roots per cell replaces it,
  being a headline measure that does not depend on ownership.
- `regression`: regenerate every image into an ignored folder and compare every json and summary number
  with `results/` at tolerance 0 (provenance ignored), with and without the fast stage.
- `switch-check`: each switch on alone; every lacuna whose area, roots or ring 30 px change.
- `fast-check`: fast against original lacuna stage, labels pixel for pixel at $t_\mathrm{hi}$ 0.8 to 1.2.
- `blind` / `unblind`: coded copies (pixel data only), key outside the repository; join a key to a table.
- `sensitivity`: both Otsu cuts scaled 0.8 to 1.2, alone, together and pooled; percent changes of roots
  per cell, ring 30 px, field density, lacuna count and bridges.
- `field-summary`: fields from lacuna centroid matching (25 px), per-field means; the field is the unit.
- `network-sweep`: one network parameter at a time at a low and a high value. The three bridging
  parameters went with gap bridging.
- `validate-network`: roots and Sholl crossings against the blind hand counts, and the skeleton against
  the traced threads. The tiles to trace are in `manual_trace/`; what may be tuned afterwards is fixed
  in advance in `docs/NETWORK_TUNING_PROTOCOL.md`.

Every json output carries a `provenance` block (git commit, dirty flag, library
versions, config hash), and `requirements.txt` pins the versions.

## 12. Figures

`figures/make_figures.py` writes PNG (300 dpi) and PDF (embedded TrueType fonts)
into `results/` (map: `results/README.md`). One display window for the whole
dataset (1st and 99.8th percentile of the pooled red channel); interior lacunae
cyan, frame-edge lacunae yellow; scale bars in pixels. Captions:
`figures/captions.md`; review notes: `figures/REVIEW.md` and
`figures/REVIEW_V2.md`, which also list the defects still unfixed.

- **Per-image overview** (`<label>_figure_overview`), the contact sheet (Fig01),
  the lacuna-cut sensitivity figure (Fig03), the per-field plot (Fig04) and the
  switch examples (S01).
- **Network overlay** (`<label>_figure_network`, and `all_images/figures/main/Fig02`
  for 543-2). The skeleton is drawn as vector segments between the centres of
  8-connected neighbouring pixels, so the drawn set is exactly the skeleton. A
  skeleton pixel is vermillion if it lies in the 30 px ring of an interior
  lacuna by the pipeline's own rule, white otherwise; roots are magenta dots at
  the root cluster centres. Per interior lacuna the vermillion pixels equal
  `ring_length_r30_px` and the dots equal `roots_count` (asserted).
- **Gallery and hand-count tiles.** Every interior lacuna in a 240 px tile at 3x
  (`<label>_figure_cell_gallery`), and the same crops of the raw red channel
  under random codes for counting roots by hand (`results/validation_tiles/`,
  key outside the repository).
- **Rejected candidates** (at least 150 px²) carry the filter that rejected
  them, one colour per meaning; "c" marks a lacuna inside a flagged canal
  region; insets sit at least 60 px from the frame.
- **Regenerate** with `python -u figures/make_figures.py all`; `check` compares
  the drawing data with `results/`. Every figure it draws is reproducible, so
  none is tracked. The pipeline's own stage pictures under `1_lacunae/` and
  `2_canaliculi/` are tracked: the skeleton png is an input to
  `validate-network`.

## 13. History

Earlier experiments, reports and analyses are preserved at the git tag
`archive-2026-10-13`, which is the repository as it was before the 2026-10-13
cleanup. Checking out that tag reproduces any earlier analysis. `main` is the
only branch.
