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
7. **Ownership** (OCY, with two departures): each lacuna is attached to skeleton
   nodes near its body, by **contact** within 6 px (no test, at weight 0, so a
   lacuna that is touched owns what touches it) and beyond that only to nodes
   **that have ridge signal all the way to it**, out to 20 px (section 8). One
   multi-source shortest-path run then gives every reachable node to the cell it
   connects to through the network, and each edge to the owner of its nearer
   end.
8. **Second, dimmer pass** (section 8): continue the threads a lacuna owns into
   response down to half the low cut, no further than 5 px past where the owned
   skeleton already reaches, then redo the graph and the ownership on the grown
   mask.
9. **The 50 um length limit** (section 7): every skeleton pixel further than
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
| ownership | contact reach | 6 px = 0.78 um | the 2 px mask buffer plus one thread half width (p50 3.0 px), so it is the band in which a thread can touch a body at all. In pixels, not micrometres, because it is pixel geometry. Inside it a node attaches with no signal test and at weight 0; measured cause in section 8 |
| ownership | attach minimum signal | 0.7 of the response's low cut | the fraction the old gap bridging required of a gap, measured the same way: the MINIMUM along the path, not the mean |
| second pass | dim cut | 0.5 of the response's low cut | the floor the survey measured the faint band against |
| second pass | dim reach | 0.65 um = 5 px | how far a dim thread may continue past owned skeleton. 10 px was tried and took the skeleton past the 25% guard on four images |
| unattached | minimum length | 1.3 um = 10 px | about two thread widths, so a component must actually run somewhere before it counts |
| unattached | minimum aspect | 3.0 | a thread is long and thin; this rejects a patch of background that happens to clear the dim cut |
| lacunae | glow trim width | 0.5 of the body's own widest inscribed radius | cuts anything narrower than half the body's widest point. Only on a region the aspect rule was about to reject, so it can rescue but never lose |
| lacunae | out of focus, roundness | aspect at most 1.5, solidity at least 0.90 | a blurred body is round |
| lacunae | out of focus, contrast | mean at least 1.5x the ring outside | a body glows above its background |
| lacunae | out of focus, minimum area | 2.5 um2 = 148 px | a round core about 14 px across, far above a speck |

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

## 8. Ownership by signal, and the two dimmer tiers

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

**How the guards are read.** Two guards hold every change here: no image may gain
more than 25% of its skeleton length, and none may lose more than 10% of its
owned length. "Owned length" is read as the **total** owned skeleton of the
image, not the mean per cell. The per-cell mean moves whenever the lacuna count
moves, for a reason that has nothing to do with threads: 543_3 gains a lacuna in
section 9, so its owned length per cell falls 12.2% while the owned skeleton
itself falls only 1.6%. The total is what answers the question the guard asks,
which is whether thread was lost.

### The second, dimmer pass

A canaliculus often fades before it ends. Hysteresis can only grow into what
already reaches the low cut somewhere, so a thread that fades below it stops
dead, and the survey measured how much is lost that way: **11 to 13% of the area
within 150 px of a lacuna carries ridge response between half the low cut and the
low cut**, 85,000 to 111,000 px per image, against a whole skeleton of 29,000 to
38,000 px.

So a second pass accepts response down to `config.DIM_THREAD_CUT_FRACTION` = 0.5
of the low cut, under two limits together:

- it must **continue skeleton a lacuna already owns**, the only seed, so nothing
  is recovered in open field, and
- it may run only `config.DIM_THREAD_REACH_UM` = 0.65 um = 5 px further along the
  dim structure than that skeleton already reaches.

The second limit is what makes this a thread continuation rather than a flood. At
half the low cut the faint band is a connected mesh: on 543_3 it is two connected
components, so a seeded growth with connectivity alone and no reach swallows it
and the mask grows 35%. Everything after the pass is redone on the grown mask, so
the graph, the ownership and the 50 um limit all see one skeleton and not two.

**Choosing the reach.** 1.3 um (10 px) was tried first. It recovered owned length
per cell by 36 to 70%, but the skeleton grew past the 25% guard on four images
(543-2 +32.0%, 543_z13 +28.2%, 682_z08 +25.6%, 682_z29 +36.4%). At 0.65 um (5 px)
no image trips either guard: skeleton length runs -1.0 to +14.3% and owned length
per cell -8.0 to +28.2%. The shorter reach is the value, for every image.

**Together with the ownership rule.** Step 1 took owned length away, most of it
on 543_3, which lost 11.9% when the empty-space network was refused. This pass
gives real thread back, and 543_3 ends at -8.0%, inside the guard. The two are
judged together because they pull in opposite directions on the same quantity.

**Not validated.** No hand count chose the cut or the reach.

### Dim threads that touch no lacuna

The second pass only continues threads a lacuna already owns, so a canaliculus
whose whole run is dim, or whose lacuna lies outside the section, is still
missed. Those threads are real structure and belong in a field measure even
though no cell can claim them.

They are taken from the same dim tier, down to half the low cut, and a component
is kept only if it looks like a thread rather than a patch of background: at
least `config.UNATTACHED_MIN_LENGTH_UM` = 1.3 um = 10 px long once skeletonized,
and at least `config.UNATTACHED_MIN_ASPECT` = 3.0 times longer than it is wide.
Anything the main skeleton already touches is not this tier by definition.

The test is deliberately strict because nothing vouches for this tier: there is
no lacuna at the end of it, so it is accepted on its own shape alone. It finds
224 to 1011 px per image.

**Where it counts and where it does not.** These threads are labelled
**unattached**. They are included in the field length density, which asks how
much canalicular network the tissue holds, and they are **never** in a per-lacuna
measure, because no lacuna owns them. Both densities are reported side by side,
`canalicular_length_density_attached_per_px` and
`field_length_density_with_unattached_per_px`, so the tier can always be taken
back out. In the verification picture they are drawn in grey, under the owned
skeleton, so what the field density counts but no cell owns is visible at a
glance.

**Not validated.**

### Does a lacuna own the threads that touch it? A census

Measured before anything was changed, with the pipeline's own functions:

```
python src/diagnostics.py contact -d data/WT -o results/contact_census --tag before \
    --points "542_z06:400,940;543_3:340,250;543_3:200,635;543_3:271,79" --pictures
```

The question is narrow. Take the band 8 px wide around each lacuna body
(`diagnostics.CONTACT_CENSUS_NEAR_PX`), which is the 2 px mask buffer plus one
thread half width, so a thread whose centre line lies in it is drawn against the
body in the verification picture and a reader expects the lacuna to own it. Who
owns that skeleton?

Over the 8 images and 108 lacunae, in that band:

| | |
|---|---|
| lacunae with skeleton in the band they do not own | 92 of 108 |
| touched by unowned skeleton | 86 |
| touched by another lacuna's skeleton | 21 |
| band skeleton owned by the body it touches | 5909 px |
| band skeleton unowned | 685 px |
| band skeleton owned by another lacuna | 136 px |

So **12.2% of the skeleton that touches a body belongs to something else**, and
it is not a few bad cases: every image has it, 7 lacunae own nothing at all, and
26 of 108 have fewer than 3 roots. Widened to the 20 px attach reach
(`--tag before_reach20 --near 20`) it is 105 of 108 lacunae and 22.3% of the
touching skeleton.

| image | lacunae | roots per lacuna | under 3 roots | no roots | touched by unowned | touched by another's | band unowned px | band another's px |
|---|---|---|---|---|---|---|---|---|
| 542_z06 | 19 | 9.84 | 1 | 0 | 15 | 2 | 135 | 18 |
| 542_z18 | 13 | 5.38 | 4 | 1 | 12 | 3 | 128 | 17 |
| 543-2 | 12 | 3.58 | 7 | 2 | 10 | 5 | 69 | 39 |
| 543_3 | 13 | 2.31 | 9 | 4 | 9 | 3 | 83 | 20 |
| 543_z13 | 11 | 4.36 | 2 | 0 | 10 | 1 | 55 | 5 |
| 682_z08 | 11 | 8.00 | 0 | 0 | 9 | 2 | 69 | 16 |
| 682_z23 | 14 | 5.57 | 1 | 0 | 11 | 4 | 70 | 16 |
| 682_z29 | 15 | 5.53 | 2 | 0 | 10 | 1 | 76 | 5 |

**The four lacunae the census was opened on.** Band figures are 8 px, then
20 px, which is the attach reach.

| lacuna | roots | owns | band skeleton | its own | unowned | another lacuna's | cut by the 50 um limit |
|---|---|---|---|---|---|---|---|
| 542_z06 (400, 952) id 15 | 5 | 770 px | 47 / 146 | 44 / 115 | 3 / 31 | 0 / 0 | 9 / 38 |
| 543_3 (340, 251) id 3 | 0 | 0 px | 14 / 81 | 0 / 0 | 4 / 29 | 10 / 52 | 16 / 63 |
| 543_3 (198, 635) id 8 | 1 | 11 px | 16 / 53 | 8 / 11 | 8 / 42 | 0 / 0 | 0 / 17 |
| 543_3 (271, 79) id 1 | 2 | 158 px | 13 / 94 | 4 / 20 | 9 / 60 | 0 / 14 | 0 / 0 |

**Which rule is responsible, lacuna by lacuna.** Not one of these threads is a
tracing failure. In each 8 px band, every pixel at or above the low cut is in
the network mask: 0 px missing in all four. The threads are there, drawn, and
they belong to no one.

- **542_z06 id 15.** 8 of the 17 graph nodes within the attach reach are
  refused by the attach signal test, at path minima 0.0000 to 0.0170 against the
  0.0195 the test asks for. The nearest refused node sits 2.8 px from the body.
- **543_3 id 3**, the lacuna that had a large network before the ownership rule
  and now has none: **11 of 11** nodes within the attach reach are refused by the
  signal test, the nearest 3.0 px out with a path minimum of 0.0116 against
  0.0152. Having attached nothing, it is then a spectator: the two threads that
  touch it (3596 px and 2679 px) go to lacunae 4 and 5, which did attach.
- **543_3 id 8**, which owns a stub: 5 of its 6 nodes are refused, the nearest
  2.8 px out at 0.0144 against 0.0152, which is 5% under the line.
- **543_3 id 1**: 8 of 10 refused, the nearest 3.2 px out at 0.0092.

So one rule does nearly all of it, and it is the attach signal test, exactly
where section 8 warned the flattening would bite: the top-hat digs a trough
around every body, and a path that leaves a surface crosses that trough at its
dimmest point. On the response the trough is shallower than on the intensity,
which is why the response was chosen, but at 2 to 4 px from a body it is still
deep enough to refuse a thread that visibly touches it. The second rule, the
multi-source Dijkstra, then multiplies the damage: a lacuna that attaches
nothing cannot compete for the thread against a neighbour that did, so the
neighbour takes the whole connected component.

The pictures are in `results/contact_census/pictures/` (green: owned by this
lacuna, orange: owned by another, magenta: unowned, gold: cut by the 50 um
limit, cyan: the body).

### Contact: a lacuna owns the thread that touches it

The census above says what is wrong and which rule does it, so the rule is where
the fix goes. A skeleton node within `config.CONTACT_REACH_PX` = 6 px (0.78 um)
of a lacuna body attaches to its nearest lacuna **with no signal test**, and
attaches **at weight 0**.

Both halves matter.

- **No test**, because inside 6 px there is nothing for the test to decide. The
  mask has every body plus a 2 px buffer cut out of it, so a thread's centre line
  can never sit nearer than about 3 px to a body, and 6 px is that buffer plus
  one thread half width (p50 3.0 px). There is no room in that band for the
  empty space the test exists to refuse, while there is quite enough for the
  trough the top-hat digs around every body, which is what the test was actually
  refusing.
- **At weight 0**, because that is what puts contact *before* the shortest path
  assignment. The attachment edge carries the gap as its weight, so a lacuna
  that attaches 5 px out starts 5 px behind one that attaches at its own
  surface. A contact thread starts at the surface: there is nothing in between
  to cross. With the weight at 0 the touched lacuna reaches that node at
  distance 0, which no neighbour can beat on any path, so **a lacuna that is
  touched owns what touches it and no neighbour can swallow it**. Everything
  past that node is still decided by the same multi-source Dijkstra on the same
  network distances, and nothing else changes.

Beyond 6 px nothing changes at all: the signal test still governs, out to
`config.LACUNA_ATTACH_REACH_UM` = 20 px, and the 50 um prune is untouched.

Setting `canaliculi.CONTACT_REACH_PX` to 0 turns the rule off and reproduces the
pipeline exactly as it was, which is how the before runs below are made
(`--contact-reach 0`): checked, and every census number of the before run is
identical to the run made before the rule existed.

**The four lacunae.** Band figures are the skeleton within 8 px of the body,
then within 20 px, as its own / unowned / another lacuna's.

| lacuna | roots | owned px | 8 px band | 20 px band | cut by the 50 um limit |
|---|---|---|---|---|---|
| 542_z06 id 15 (400, 952) | 5 **6** | 770 **770** | 44/3/0 **44/3/0** | 115/31/0 **115/31/0** | 9 / 38 |
| 543_3 id 3 (340, 251) | 0 **3** | 0 **881** | 0/4/10 **16/0/0** | 0/29/52 **69/14/0** | 16 / 63 |
| 543_3 id 8 (198, 635) | 1 **2** | 11 **11** | 8/8/0 **8/7/0** | 11/42/0 **11/41/0** | 0 / 17 |
| 543_3 id 1 (271, 79) | 2 **3** | 158 **811** | 4/9/0 **7/3/0** | 20/60/14 **41/36/14** | 0 / 0 |

Pictures, before and after, in `results/contact_census/pictures/`
(`<label>_lacuna<id>_before.png` and `_after.png`, and `_x4` of each).

- **543_3 id 3**, which owned nothing: it now owns 881 px and 3 roots, and the
  two threads that touch it (3596 px and 2679 px) are shared with the
  neighbours instead of being handed to them whole. Its 8 px band went from 0 of
  14 px to 16 of 16.
- **543_3 id 1**: 158 px to 811 px, 2 roots to 3. The thread on its left, 664 px
  long and unowned before, is now its.
- **542_z06 id 15**: 5 roots to 6, owned length unchanged. Within 8 px it
  already owned 44 of 47 px before the rule, so there was little there to
  recover. What is missing beside this body is **not an ownership failure**: 38
  px within 20 px of it were cut by the 50 um length limit, and the rest sit 9 to
  20 px out across paths whose dimmest point is 0.0055 to 0.0170 against the
  0.0195 the signal test asks.
- **543_3 id 8**, the stub: 1 root to 2, owned length unchanged at 11 px. This
  one is **not fixed**, and the measurement says why. Every thread near it
  except the stub lies 7.0 px or further from the body, past the contact reach,
  and the straight paths to them carry 0.0000 to 0.0144 against the 0.0152 the
  signal test asks, 0 to 57% of it. The space between this body and those
  threads is genuinely dark, not a trough beside a bright thread. Reaching them
  would mean setting the contact reach from this one lacuna, which is the kind
  of per-image tuning this pipeline does not do.

### What the contact rule does to all 8 images

The rule is one rule for every lacuna, so it is read on every lacuna. Before is
`--contact-reach 0`, after is the configured 6 px; **bold is after**.

| image | lacunae | roots per lacuna | under 3 roots | owned px | unowned px | skeleton px | first-pass skeleton px |
|---|---|---|---|---|---|---|---|
| 542_z06 | 19 | 9.84 **12.16** | 1 **1** | 28514 **28803** +1.01% | 10710 **10426** | 39224 **39229** +0.01% | 38842 = 38842 |
| 542_z18 | 13 | 5.38 **7.31** | 4 **1** | 22862 **24971** +9.22% | 13810 **11717** | 36672 **36688** +0.04% | 37584 = 37584 |
| 543-2 | 12 | 3.58 **5.92** | 7 **2** | 29152 **29417** +0.91% | 8635 **8283** | 37787 **37700** -0.23% | 45028 = 45028 |
| 543_3 | 13 | 2.31 **4.00** | 9 **6** | 21261 **25106** +18.08% | 14339 **10550** | 35600 **35656** +0.16% | 45929 = 45929 |
| 543_z13 | 11 | 4.36 **6.36** | 2 **0** | 28210 **28463** +0.90% | 13154 **12914** | 41364 **41377** +0.03% | 44036 = 44036 |
| 682_z08 | 11 | 8.00 **10.00** | 0 **0** | 25932 **26034** +0.39% | 9149 **9048** | 35081 **35082** +0.00% | 37393 = 37393 |
| 682_z23 | 14 | 5.57 **7.00** | 1 **1** | 24002 **24363** +1.50% | 12042 **11695** | 36044 **36058** +0.04% | 42338 = 42338 |
| 682_z29 | 15 | 5.53 **6.33** | 2 **2** | 23274 **23543** +1.16% | 10299 **10073** | 33573 **33616** +0.13% | 40336 = 40336 |

Over the 8 images: roots per lacuna 5.81 to **7.61**, lacunae under 3 roots 26 to
**13**, lacunae with no roots 7 to **5**, owned skeleton 203,207 to **210,700 px**
(+3.69%), unowned 92,138 to **84,706 px** (-8.07%), unattached dim threads
unchanged at 3,776 px. In the 8 px band the census was opened on: lacunae
touched by skeleton they do not own 92 to **75**, by another lacuna's skeleton
21 to **6**, band skeleton owned by another lacuna 136 px to **8 px**, and the
share of touching skeleton that the touched body does not own 12.2% to **5.2%**.

**The four required checks.**

1. **The skeleton is unchanged.** The first-pass skeleton, which is what the
   ridge threshold traces and the only thing detection produces, is **identical
   pixel for pixel on all 8 images** (331,486 px before and after). The final
   skeleton moves by -0.23% to +0.16% (295,345 to 295,406 px, +0.021% in total),
   and that movement is not the contact rule touching detection: the second,
   dimmer pass is seeded from **owned** skeleton by design (section 8), so
   giving a lacuna the thread that touches it gives the dim pass a seed it did
   not have, the mask grows there, and the centre line of the regrown mask can
   shift by a pixel. 543-2 ends 87 px shorter because a wider mask skeletonizes
   to one line where it had two. Both directions are inside the 25% skeleton
   guard that governs the dim pass, by two orders of magnitude. **Pass, read on
   detection; the final skeleton moves because an existing rule follows
   ownership.**
2. **Total owned px does not fall.** It rises on every image, +0.39% to
   +18.08%. **Pass.**
3. **Roots per lacuna rise on every image.** 8 of 8, from +0.80 to +2.31 roots
   per lacuna. Per lacuna, 80 of 108 rise, 27 are unchanged and **one falls**,
   682_z08 id 6, from 8 to 7. It did not lose an attachment: it gained two, 14
   nodes to 16, and the new node at (457, 533) lies within the 8 px root merge
   distance of two existing roots and joins them into one. That is the roots
   measure working as defined, one thick thread counted once, not a loss.
   **Pass.**
4. **No lacuna loses more than 25% of its owned px unless it was holding
   skeleton that another lacuna touches closer.** Measured pixel by pixel
   (`python src/diagnostics.py contact-handover -d data/WT -o results/contact_census`):
   41 lacunae gained, 46 are unchanged, 21 lost. **One** passes the 25% guard,
   543-2 id 9 at -35.1%, and all 1388 px it lost went to lacunae 11 and 12,
   **both of which touch those threads** by the rule's own test, a contact
   attachment on that same connected component; 1309 of the 1388 px also lie
   nearer their new owner's body in a straight line. Its own roots rose 4 to 6.
   Over all 108 lacunae, of 7603 px that changed hands **7536 went to a lacuna
   that touches that thread**, 0 went to no one, and 67 left the skeleton with
   the dim pass. No lacuna lost skeleton to a body that does not touch it.
   **Pass, under the exception, and the exception is measured and not assumed.**

The handover is counted two ways on purpose. "Touches that thread" is the rule's
own word and is the test that matters: the taker holds that skeleton through a
contact attachment on the same component. "Nearer in a straight line" is a
second, weaker reading, reported beside it because ownership runs along the
network and not in straight lines, and the two disagree on 819 of 7536 px.

**Not validated.** No hand count chose the contact reach, and none of these
numbers is evidence that the new ownership is right, only that it is the rule
doing what the rule says.

## 9. Lacunae the filters used to miss

Two rules, both general, both applying to every image, neither raising
`MAX_ASPECT_RATIO` or lowering `MIN_AREA_PX2`.

### Trimming a glow streak before judging a shape

A bright osteocyte often carries a tail of out-of-plane glow, and the threshold
takes body and tail as one object, which makes it far more elongated than the
cell is. The aspect filter then rejects a real lacuna for the shape of its glow.

A region that fails **only** the aspect test now gets one second chance: the body
is opened with a disk of `config.GLOW_TRIM_WIDTH_FRACTION` = 0.5 of its own
widest inscribed radius, which removes anything narrower than half the body's
widest point, the largest surviving piece is taken as the body, and every filter
is applied again to it.

Only on an aspect failure, and that matters. Applied to every region instead, the
trim pushes four otherwise good lacunae below the area floor while rescuing one,
a net loss of three over the 8 images. Restricted to the regions the aspect rule
was about to reject, it can only rescue and never lose.

The fraction is of the body's **own** width, so one constant carries to a large
and a small lacuna alike. A canalicular thread is about 6 px wide and a lacuna
body 30 to 90 px across, so half the widest inscribed radius sits far above a
thread and far below a body: it cuts glow and tails, not cells.

Over the 8 images this rescues exactly one lacuna, on 543_3, whose aspect was
6.034 against a limit of 6.0 and falls to 5.68 once the streak is off. Where 6.0
sits: of the 103 candidates at or above the area floor the aspect runs p50 2.84,
p90 4.58, max 7.70, and only three sit between 5.0 and 7.0, so the cut is in a
sparse part of the distribution but a narrow one, 5.763 kept against 6.034
rejected.

### What the measurement said, and why the expected rule was wrong

Before any rule was written, every object the lacuna threshold produced at 100 px²
or more over all 8 images was tabulated with its features, 173 of them
(`python src/diagnostics.py lacuna-candidates -d data/WT -o results/survey`).

The rule everyone expects is "a missed lacuna is clearly brighter than its
surroundings". **The data says the opposite.** Measured as the mean inside over
the mean of a ring just outside, the lacunae a review found missing score **1.17
to 1.58**, while ordinary thresholding specks reach **4.87**. The test runs
backwards, and for a physical reason worth keeping in mind: a real lacuna is
ringed by its own dense canaliculi, which lift the ring it is being compared
with, while a speck sits on dark background with nothing around it.

What does separate them is that these lacunae are **dim**. A lacuna lying partly
outside the focal plane has a core that never saturates: the missed ones peak at
**0.678 to 0.792**, and the next object up in the whole pool peaks at **0.824**.
That is a clean gap, and the rule is built on it as an **upper** bound on
brightness. Contrast is kept, but only in the thick-process rule below, where a
high value is the point.

### Four rules for the lacunae the filters miss

All in `config.py` section g, all identical for every image, none of them
lowering `MIN_AREA_PX2` or raising `MAX_ASPECT_RATIO` for anything else.

| rule | test | why |
|---|---|---|
| **g1 dim sub-area** | area ≥ 2.7 um² (160 px), solidity ≥ 0.80, peak ≤ 0.82 | big enough to be a body, compact, and dim: the gap above |
| **g2 cut by the frame** | area floor × 0.75 (300 px), solidity ≥ 0.85 | the frame cuts the object, so the floor is scaled; the stricter solidity is needed, because at the scaled floor alone two objects in an image that must not change would be admitted |
| **g3 thick process** | area ≥ 16.9 um² (1000 px), contrast ≥ 2.5, solidity ≥ 0.40 | a large, bright, ragged region is a body with a thick process, not debris. One object over the 8 images qualifies; the next ragged one is a quarter of the area |
| **g4 dark band merge** | shared border ≥ 150 px, dip ≥ 0.75 of the dimmer body, and **never between two objects that are both already lacunae** | a thin dark band can split one osteocyte in two. The third condition is what stops the rule fusing two real neighbouring cells: without it two lacunae in 682_z29 merge and the count falls |

The merge runs **before** anything is filtered, so a rescued body is judged whole.

Lacunae accepted by g1 to g3 are the class **dim**, beside **out_of_focus**
below: counted, owning their threads, and carrying **no area or shape measure**,
because what would be measured is the blur or the frame and not the cell. Every
per-lacuna row says which class it is, and the shape summary uses ordinary
lacunae only.

**The acceptance test.** A review of all 8 images named what the detector should
find. It passes on every image, and the four images that had to stay still did:

| image | before | after | expected | the review's targets |
|---|---|---|---|---|
| 542_z06 | 17 | **19** | 19 | (226,311) ragged body found by g3; (4,934) frame-cut found by g2 |
| 542_z18 | 13 | 13 | 13 | unchanged |
| 543-2 | 12 | 12 | 12 | unchanged |
| 543_3 | 11 | **13** | — | (481,458) and (286,857) found by g1; the osteocyte at (877,546) that a dark band split is one 1625 px object again |
| 543_z13 | 11 | 11 | 11 | unchanged |
| 682_z08 | 10 | **11** | 11 | (977,347) found by g1 |
| 682_z23 | 14 | 14 | 14 | unchanged |
| 682_z29 | 14 | **15** | 15 | (872,724) and (846,734) merged by g4 into one 663 px lacuna |

108 lacunae over the 8 images, up from 102. **Not validated**: the review is an
eye on the images, not a hand count, and no value here was chosen against one.

### Out-of-focus lacunae

A lacuna lying partly outside the focal plane shows as a round glow whose bright
core clears the intensity cut but is far smaller than `MIN_AREA_PX2`, so the area
filter drops it. There are **1,184** such sub-area candidates over the 8 images
and nearly all are thresholding specks, so the rule has to be the most selective
one that can be justified. All four tests must pass:

| test | constant | why |
|---|---|---|
| round | aspect at most 1.5 | a blurred body is round; a speck on a thread is not |
| round | solidity at least 0.90 | a body has no ragged edge |
| brighter than its surroundings | mean at least 1.5x the ring just outside | a body glows above its background; a speck sits on a thread no dimmer than itself |
| large enough to be a body | at least 2.5 um2, about 148 px | a round core about 14 px across: two thread widths, far above the specks, small enough that a blur still reaches it |

Over the 8 images this accepts **3 candidates, at most one per image**: 542_z06
(214 px2, contrast 3.46), 542_z18 (235 px2, contrast 1.98) and 682_z29 (175 px2,
contrast 2.12). Every other combination of plausible values was tried and none
accepted more than one per image either.

They are the class **out_of_focus**: **in** the lacuna count and **in** thread
ownership, because a cell is there and its canaliculi are real, and **out** of
every area and shape measure, because the edge that would be measured is the blur
and not the cell. Their shape fields come back `None` and the shape summary skips
them; they keep their id, their centroid, their roots and their ring lengths.

**Not validated.** No hand count chose any of these values.

## 10. Network shape, report only

Four measures that ask whether the traced network looks like tissue or like the
pixel grid, and how much of it closes on itself. **Nothing here filters or
prunes**, and in particular **no loop is ever removed**: a loop may be a tracing
artefact or a real anastomosis, and these record how many there are without
deciding which.

| measure | what it is |
|---|---|
| `straight_run_fraction` | share of skeleton pixels inside a perfectly horizontal or vertical run of at least 8 px. A canaliculus has no reason to follow a row or a column, and these images carry faint axis-aligned banding, so a high share means the detector is following the grid |
| `rectangle_count` | closed loops of four graph nodes whose four sides are all axis-aligned, to one pixel of slack. A real network has no reason to close a rectangle on the grid |
| `loop_count` | independent cycles, the cyclomatic number E - V + C: how many edges would have to be cut to leave a forest |
| `loop_edge_share` | share of real edges lying on at least one cycle, which is one minus the bridge share |

The first two are restored verbatim from the ablation at tag
`archive-2026-10-13`, where they were written for exactly this question. The two
loop measures are new.

`python src/diagnostics.py shape-picture -d data/WT -o results/network_shape`
draws them: every skeleton pixel one pixel wide over the raw image, axis-aligned
runs in blue, skeleton lying on a cycle in red, the rest green, lacunae outlined
cyan.

## 11. Normalised per-cell measures

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

## 12. Switches (all off by default)

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

## 13. Checks (`src/diagnostics.py`)

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
- `contact`: does each lacuna own the threads that touch it. Per named lacuna, the one rule that holds
  every touching thread away from it; per image and over the set, roots, owned px, and the skeleton
  within 8 px of a body that the body does not own. Measurement only. `--contact-reach 0` runs it with
  the contact rule off, which is how the before and after tables of section 8 are made.
- `contact-handover`: each image run twice, contact on and off, and every owned pixel followed to where
  it went: what each lacuna gained, what it lost, and whether what it lost went to a lacuna that
  touches that thread. This is where the per-lacuna 25% guard is read.

Every json output carries a `provenance` block (git commit, dirty flag, library
versions, config hash), and `requirements.txt` pins the versions.

## 14. Figures

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

## 15. Validation against a manual tracing

The gate everything here is pre-validation against. `src/validate_manual.py`
compares what the pipeline traced with what a person traced by hand and reports
where the two differ. It is not a measure of the pipeline's own.

```
python src/validate_manual.py                        # every image that has a tracing
python src/validate_manual.py -o results/validation  # and write the json
```

It reads `manual_trace/<label>_manual.png`, a binary mask the size of the whole
image, and `manual_trace/<label>_manual_lacunae.csv`, a header `x,y` and one row
per hand-marked lacuna centre. Both are optional and scored independently, and
with neither present it prints `no manual masks yet` and returns 0, so it can sit
in a check sequence from the day it was written. The format is in
`manual_trace/README.md`.

| it reports | what it means |
|---|---|
| skeleton precision | share of the pipeline's skeleton within 2 px of some hand-traced pixel: how much of what it drew is really there |
| skeleton recall | share of the hand tracing within 2 px of some pipeline pixel: how much of what is there it drew |
| f1 | their harmonic mean |
| lacunae matched, missed, extra | a point matches the lacuna whose body contains it, or the nearest within 25 px; each lacuna can be claimed once |

The tolerance is 2 px = 0.26 um. A hand line and a skeleton of the same thread
never agree pixel for pixel, and a thread is about 6 px wide, so 2 px compares
the same structure without letting the next thread over count as a match. The
25 px lacuna tolerance is 3.25 um, well under the spacing between neighbours.

It was checked both ways before being committed: scored against the pipeline's
own skeleton and centroids it returns precision 1.0, recall 1.0 and every lacuna
matched; against a tracing deliberately broken (left half dropped, shifted 5 px,
two lacunae withheld and one invented) it returns precision 0.137, recall 0.259,
9 matched, 1 missed and 2 extra.

## 16. History

Earlier experiments, reports and analyses are preserved at the git tag
`archive-2026-10-13`, which is the repository as it was before the 2026-10-13
cleanup. Checking out that tag reproduces any earlier analysis. `main` is the
only branch.
