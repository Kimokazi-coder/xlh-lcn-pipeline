# Methods

How the pipeline works, where every parameter value came from, what it
cannot do yet, and the decisions behind its current shape.

**Status: pre-validation.** No output has been checked against manual
(ImageJ) counts.

**How the rules were chosen.** Every rule and value was chosen by visual
inspection of the WT images. No parameter may be tuned on the other groups.

**Two methods, and the choice is pending.** Sections 1 to 19 describe the
**deterministic method**, the pipeline as `config.py` ships it, whose output is
`results/`, one folder per group. Section 20 describes the **AI judge method**, the same pipeline
with `config.AI_JUDGE_ENABLED` on, whose output is `results_ai_judge/WT/`. Which
the study uses has not been decided, and **neither has been validated against a
manual trace**.

**Units.** The pixel size is 0.13 um/px, from the confocal acquisition record,
confirmed for all 8 images and rounded to two decimals. The pipeline reports
px and px² all the same: `PIXEL_SIZE_UM` is deliberately `None`, because it is
recorded in every result's parameters block and switches every scale bar to
micrometres, so setting it would change the recorded values and a fresh run
would no longer equal `results/WT/` at tolerance 0. Convert with 0.13 um/px where
a physical length is wanted; the experimental ridge method (section 7) works in
micrometres throughout.

**Data: 8 wild-type (WT) confocal optical sections** (`data/WT/`, red channel,
1024 x 1024 px), the reference group of four (section 21). The other three
groups hold no image yet: no Hyp or Hyp;Enpp1 image has been processed, and
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
measures. It writes `results/WT/<label>/5_quantification/` (json, xlsx and a plain
pdf) and the one cross-image table,
`results/WT/all_images/quantification/quantification_all_images.csv`, `.xlsx` and
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
| glow zone | profile fraction | 0.10 of the surface excess | where a decaying glow stops being distinguishable from the tissue around it; the zone it gives runs 3.9 to 33.2 px over the 8 images and reaches the existing mask on 107 of 108 lacunae |
| glow zone | cut inside the zone | 0.5 of the low cut | the floor the second dim pass already uses, so "dim" has one meaning in the pipeline |
| glow zone | maximum extent | 8 um = 62 px | a cap, just past the widest empty ring measured (7.69 um), so a lacuna whose profile never falls cannot claim the image. No lacuna in the set reaches it |
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
| 2026-10-14 | The GLOW ZONE is adopted: inside each lacuna's own glow extent, measured on the raw channel, the ridge response is accepted down to half the low cut where it continues mask the global cut already produced. One global cut was emptying a ring around every body, 27.4 px wide at the median, by dropping 59.9% of everything visible there (section 18). Outside the zones the mask is unchanged. 543-2 reference becomes 146.42 / 21.99 / 7.67. Not validated. |
| 2026-10-16 | The ZONE FROM THE HOLE replaces the glow zone as what decides where the lower cut applies: each lacuna's empty width, measured on the global cut skeleton, plus one thread half width, capped at 8 um; inside it the response is multiplied by that lacuna's contrast gain, read by distance from the body because the loss is a trough, and the SAME global cuts are applied. No requirement to connect to existing mask, and a noise guard on mask that did not exist before. A lacuna is offered every node that touches it, not only the nodes it is nearest to, and a pruned spur now keeps the owner of the node it hangs off (section 19). 543-2 reference becomes 161.00 / 21.63 / 8.50. Not validated. |
| 2026-10-14 | CONTACT is adopted: a skeleton node within 6 px of a body attaches to its nearest lacuna with no signal test and at weight 0, so a lacuna that is touched owns what touches it and no neighbour can swallow it. The signal test keeps governing from 6 to 20 px and the 50 um prune is untouched. 543-2 reference becomes 128.42 / 19.53 / 5.92. Not validated. |

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

`results/contact_census/` is not tracked since 2026-10-20: regenerate with the command above. It
measures the pipeline as configured, so with the contact rule on today it draws the after state; the
tables and pictures cited in this section, before and after, are at commit `bf3b982`
(`git checkout bf3b982 -- results/contact_census`).

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

The pictures were in `results/contact_census/pictures/` (not tracked: regenerate with `python src/diagnostics.py contact -d data/WT -o results/contact_census --tag after --points "542_z06:400,940;543_3:340,250;543_3:200,635;543_3:271,79" --pictures`; as cited, at commit `bf3b982`) (green: owned by this
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

Pictures, before and after, were in `results/contact_census/pictures/` (not tracked: regenerate with `python src/diagnostics.py contact -d data/WT -o results/contact_census --tag after --points "542_z06:400,940;543_3:340,250;543_3:200,635;543_3:271,79" --pictures`; as cited, at commit `bf3b982`)
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
   (regenerate with `python src/diagnostics.py contact-handover -d data/WT -o results/contact_census`;
   not tracked, the file cited is at commit `bf3b982`):
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

### What contact cannot reach: signal beside a body that was never traced

An ownership rule can only hand out skeleton that exists. The census therefore
counts, in the same 8 px band and outside the buffered bodies, what carries
ridge response there and is not in the network mask at all. **Reported, and
deliberately not fixed here**: every number below is produced by a rule that
already exists and was chosen for its own reasons.

Two tiers, and they are not the same thing.

- **Faint**, between half the low cut and the low cut: **17,398 px** over the
  8 images, present beside almost every body. No threshold of this method can
  reach it, by construction, because hysteresis can only grow into what reaches
  the low cut somewhere. This is the tier the second, dimmer pass exists for,
  and the contact rule feeds that pass: the pass is seeded from owned skeleton,
  so a lacuna that now owns its contact thread can continue it into the faint
  tier, which is where the +0.021% of skeleton came from.
- **Above the low cut and still not in the mask**: **848 px over 51 of the 108
  lacunae**, which is 1.6% of the signal in those bands. Of those, 581 px lie
  inside a flagged vascular canal, where hysteresis is not allowed to add
  anything and only already-bright pixels survive; 226 px were removed as specks
  under 8 px2; the remaining 41 px reached the low cut with no bright pixel
  connected to them.

| image | lacunae with untraced signal | untraced px above the low cut | in a vascular canal | despeckled | faint px |
|---|---|---|---|---|---|
| 542_z06 | 12 of 19 | 179 | 113 | 62 | 3961 |
| 542_z18 | 5 of 13 | 219 | 171 | 48 | 2404 |
| 543-2 | 4 of 12 | 13 | 0 | 13 | 1894 |
| 543_3 | 6 of 13 | 26 | 0 | 6 | 1631 |
| 543_z13 | 4 of 11 | 10 | 0 | 5 | 1553 |
| 682_z08 | 6 of 11 | 182 | 125 | 46 | 2288 |
| 682_z23 | 8 of 14 | 160 | 139 | 20 | 1796 |
| 682_z29 | 6 of 15 | 59 | 33 | 26 | 1871 |
| **all 8** | **51 of 108** | **848** | **581** | **226** | **17,398** |

The lacunae it concentrates on, worst first: 542_z18 id 2 (639, 130) 190 px,
682_z08 id 1 (428, 32) 139 px, 542_z06 id 9 (573, 482) 82 px, 682_z23 id 3
(472, 61) 72 px, 682_z23 id 2 (363, 7) 52 px, 682_z29 id 1 (99, 14) 33 px. Every
one of them sits against a vascular canal, which is what the vascular rule is
for: it stops a vessel wall being traced as a canaliculus, and the price is that
a real thread crossing a canal is not traced either. 543-2, 543_3 and 543_z13,
which have no large canal beside a lacuna, lose 10 to 26 px between them, all of
it specks.

**None of this touches the four lacunae the work started from.** In their 8 px
bands, every pixel above the low cut is in the mask: 0 px untraced for all four.
What was wrong there was ownership, and ownership is what was changed.

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
(regenerate with `python src/diagnostics.py lacuna-candidates -d data/WT -o results/survey`; not
tracked, as cited at commit `bf3b982`).

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

Regenerate with `python src/diagnostics.py shape-picture -d data/WT -o results/network_shape`,
which draws them (not tracked): every skeleton pixel one pixel wide over the raw image, axis-aligned
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
With all off, `results/WT/` is reproduced exactly
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

- `reference-check`: 161.00 edges per cell, 21.63 px mean edge length and 8.50 roots per cell on
  543-2. The third number was the gap bridge count, which no longer exists; roots per cell replaces it,
  being a headline measure that does not depend on ownership.
- `regression`: regenerate every image into an ignored folder and compare every json and summary number
  with `results/WT/` at tolerance 0 (provenance ignored), with and without the fast stage.
- `switch-check`: each switch on alone; every lacuna whose area, roots or ring 30 px change.
- `fast-check`: fast against original lacuna stage, labels pixel for pixel at $t_\mathrm{hi}$ 0.8 to 1.2.
- `blind` / `unblind`: coded copies (pixel data only), key outside the repository; join a key to a table.
- `sensitivity`: both Otsu cuts scaled 0.8 to 1.2, alone, together and pooled; percent changes of roots
  per cell, ring 30 px, field density, lacuna count and bridges.
- `field-summary`: fields from lacuna centroid matching (25 px), per-field means; the field is the unit.
- `network-sweep`: one network parameter at a time at a low and a high value. The three bridging
  parameters went with gap bridging.
- `validate-network`: roots and Sholl crossings against blind hand counts, and the skeleton against
  traced threads. No hand count exists, so it has only run its self test (`-s`).
- `contact`: does each lacuna own the threads that touch it. Per named lacuna, the one rule that holds
  every touching thread away from it; per image and over the set, roots, owned px, and the skeleton
  within 8 px of a body that the body does not own. Measurement only. `--contact-reach 0` runs it with
  the contact rule off, which is how the before and after tables of section 8 are made.
- `contact-handover`: each image run twice, contact on and off, and every owned pixel followed to where
  it went: what each lacuna gained, what it lost, and whether what it lost went to a lacuna that
  touches that thread. This is where the per-lacuna 25% guard is read.
- `ridge-background`: does the skeleton follow the local background of the ridge response, which one
  global cut would make it do, rather than thread presence. The background map beside the image's own
  ownership picture, the tile density against it, and the correlation per image. Measurement only; its
  answer is section 17.
- `empty-zone`: what makes the hole in the skeleton around a lacuna. How wide it is, by angular sector;
  what the hole holds against the band immediately beyond it; and which stage of the pipeline drops each
  visible pixel inside it. Measurement only; its answer is section 18.
- `import-group`, `group-overview`, `group-qc`: copy a group's images under the import rule, the
  table of every group side by side, and the QC list of the groups other than WT (section 21).
- `glow-check`: the glow zone rule on against off, each image run twice. The skeleton inside and outside
  the zones, the empty width, roots, owned and unowned px, and the three checks the rule has to pass.
  `canaliculi.GLOW_ZONE_MAX_PX = 0` is what turns it off.

Every json output carries a `provenance` block (git commit, dirty flag, library
versions, config hash), and `requirements.txt` pins the versions.

## 14. Figures

**`make_figures.py all` passes** (2026-10-20: exit 0, every figure it makes
present and skipped, S03 waiting for its blinding key). It skips a figure whose
PNG and PDF exist, so that run did not redraw any. An earlier note here said
it failed on 96 figures because it unpacked `canaliculi.nearest_lacuna_map`
into two values; it now takes the three that function returns.

`figures/make_figures.py` writes PNG (300 dpi) and PDF (embedded TrueType fonts)
into `results/WT/` (map: `results/README.md`). One display window for the whole
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
- **Gallery.** Every interior lacuna in a 240 px tile at 3x
  (`<label>_figure_cell_gallery`).
- **Rejected candidates** (at least 150 px²) carry the filter that rejected
  them, one colour per meaning; "c" marks a lacuna inside a flagged canal
  region; insets sit at least 60 px from the frame.
- **Regenerate** with `python -u figures/make_figures.py all`; `check` compares
  the drawing data with `results/WT/`. Every figure it draws is reproducible, so
  none is tracked. The pipeline's own stage pictures under `1_lacunae/` and
  `2_canaliculi/` are tracked: the skeleton png is an input to
  `validate-network`.

## 15. Validation against a manual tracing

**Not done. No output of the pipeline has been validated against a manual
trace or a manual count**, and every number in this repository is
pre-validation.

The material that was prepared for it was removed on 2026-10-20: the scoring
script `src/validate_manual.py`, the four raw tiles for a blind hand trace in
`manual_trace/`, the 86 hand-count tiles of `results/validation_tiles/`, the
tuning protocol `docs/NETWORK_TUNING_PROTOCOL.md` and `results/RENAMES.csv`.
All of it is at commit `41c00ae`, the last that holds it. What the
scoring script measured, kept here as the record of what a validation would
report:

| it reports | what it means |
|---|---|
| skeleton precision | share of the pipeline's skeleton within 2 px of some hand-traced pixel: how much of what it drew is really there |
| skeleton recall | share of the hand tracing within 2 px of some pipeline pixel: how much of what is there it drew |
| f1 | their harmonic mean |
| lacunae matched, missed, extra | a point matches the lacuna whose body contains it, or the nearest within 25 px; each lacuna can be claimed once |

The tolerance was 2 px = 0.26 um, because a hand line and a skeleton of the
same thread never agree pixel for pixel and a thread is about 6 px wide; the
lacuna tolerance was 25 px = 3.25 um, well under the spacing between neighbours.

## 16. History

Earlier experiments, reports and analyses are preserved at the git tag
`archive-2026-10-13`, which is the repository as it was before the 2026-10-13
cleanup. Checking out that tag reproduces any earlier analysis. `main` is the
only branch.

## 17. Tests that found nothing to change

Negative results, kept because they are the reason a change was not made.

### Does one global ridge cut follow local brightness? No, not enough to act on

**The question.** The ridge response is thresholded with ONE cut per image, from
that image's own histogram. If a field is dim in one corner, a global cut could
miss real threads there while passing a mesh of them where the field is bright.
The signature would be a positive relation between the **local background of the
ridge response** and the **local skeleton density**: where the floor is higher,
more of the image clears one fixed cut.

**The test**, measurement only
(regenerate with `python src/diagnostics.py ridge-background -d data/WT -o results/ridge_background`;
not tracked, as cited at commit `bf3b982`).
The local background is the 25th percentile of the ridge response in 100 px
windows on a 50 px grid, with every lacuna body and its mask buffer left out,
smoothed over the grid and resampled to the frame. Skeleton density is counted
in 100 px tiles over the area where a thread could be traced, which is the tile
minus the bodies and their buffer. Spearman, not Pearson, is the headline,
because the relation has no reason to be linear and one bright tile should not
carry the answer.

**The gate, fixed before the numbers were seen:** proceed only if the median
Spearman rho over the 8 images is at least **+0.50** and at least **7 of 8**
images are positive.

| image | tiles | Spearman rho | p | background min, median, max | max/min | density, dimmest quarter | brightest quarter | bright/dim |
|---|---|---|---|---|---|---|---|---|
| 542_z06 | 121 | **+0.525** | 6e-10 | 0.000216, 0.000594, 0.001735 | 8.0 | 0.0334 | 0.0507 | 1.52 |
| 542_z18 | 121 | **+0.504** | 4e-09 | 0.000274, 0.000625, 0.001084 | 4.0 | 0.0262 | 0.0449 | 1.72 |
| 543-2 | 121 | +0.155 | 0.09 | 0.000763, 0.001192, 0.001946 | 2.6 | 0.0350 | 0.0396 | 1.13 |
| 543_3 | 121 | +0.191 | 0.04 | 0.000452, 0.001108, 0.001868 | 4.1 | 0.0326 | 0.0369 | 1.13 |
| 543_z13 | 121 | -0.020 | 0.83 | 0.000673, 0.000953, 0.001447 | 2.2 | 0.0408 | 0.0402 | 0.99 |
| 682_z08 | 121 | **+0.572** | 7e-12 | 0.000146, 0.000733, 0.001353 | 9.2 | 0.0156 | 0.0430 | 2.76 |
| 682_z23 | 121 | +0.143 | 0.12 | 0.000168, 0.000688, 0.001498 | 8.9 | 0.0258 | 0.0347 | 1.34 |
| 682_z29 | 121 | +0.149 | 0.10 | 0.000125, 0.000455, 0.000932 | 7.5 | 0.0261 | 0.0353 | 1.35 |

**Median rho +0.173, 7 of 8 positive, 3 of 8 at or above +0.50. The gate is not
met: WEAK.** The sign is consistent, so the effect is real and not nothing: over
the set, the brightest quarter of tiles carries 1.13 to 2.76 times the skeleton
density of the dimmest quarter. But a median rho of 0.17 is about 3% of the
variance in tile density, and a 100 px tile's density varies by a factor of ten
between neighbours at the same background (see the scatter in any picture). The
global cut is not what decides where threads are drawn. Normalizing the response
by this background would therefore be a large change to detection on weak
evidence, so **it was not made and nothing in the pipeline was touched**.

The dynamic range is not the explanation either: 682_z23 and 682_z29 have
background ratios of 8.9 and 7.5 across the frame, as wide as the three images
that do correlate, and rho of +0.14 and +0.15.

### What the same tiles say instead

Each tile was also asked what share of the skeleton in it is **owned**, because
the attach signal test is a fixed fraction of the same global cut and would be
punished by a dim corner in the same way.

| image | rho, skeleton density | rho, owned density | rho, owned fraction | owned fraction, dimmest quarter | brightest quarter |
|---|---|---|---|---|---|
| 542_z06 | +0.525 | +0.433 | +0.284 | 0.532 | 0.850 |
| 542_z18 | +0.504 | +0.374 | +0.231 | 0.516 | 0.750 |
| 543-2 | +0.155 | +0.016 | -0.143 | 0.762 | 0.586 |
| 543_3 | +0.191 | +0.091 | -0.033 | 0.633 | 0.644 |
| 543_z13 | -0.020 | -0.130 | -0.192 | 0.690 | 0.507 |
| 682_z08 | +0.572 | +0.421 | +0.143 | 0.485 | 0.637 |
| 682_z23 | +0.143 | +0.081 | +0.030 | 0.520 | 0.583 |
| 682_z29 | +0.149 | +0.141 | +0.063 | 0.550 | 0.619 |

Median rho for the owned fraction: **+0.046**, 5 of 8 positive, two images
negative at -0.14 and -0.19. Ownership does not follow local brightness at all.

**The lower left of 543_3, by quadrant.** This is the area the hypothesis was
raised on, and it is where the hypothesis fails hardest:

| quadrant of 543_3 | local background | skeleton density | owned fraction |
|---|---|---|---|
| top left | 0.001080 | 0.0327 | 0.88 |
| top right | 0.001077 | 0.0363 | 0.85 |
| bottom right | 0.001166 | 0.0366 | 0.84 |
| **bottom left** | **0.001153** | **0.0340** | **0.24** |

The lower left has the **second highest** local background of the four
quadrants, not the lowest, and its skeleton density is ordinary. What is
different there is that **76% of the skeleton it carries belongs to no lacuna**,
against 12 to 16% everywhere else in the image. The threads in the lower left of
543_3 are traced. They are not owned, which is an ownership question (section 8),
not a threshold one, and it is the same question the lacuna at (198, 635) raises:
the threads nearest it lie 7.0 px or further from its body, past the contact
reach, across paths the signal test refuses.

## 18. The hole in the skeleton around a lacuna

The skeleton stops short of the bodies. This is the measurement of why, before
anything was changed:

```
python src/diagnostics.py empty-zone -d data/WT -o results/empty_zone
```

`results/empty_zone/` is not tracked: regenerate with the command above; the files cited in this
section are at commit `bf3b982`.

**How the hole is measured.** The frame around each lacuna is cut into 180
angular sectors, and a sector's **empty width** is the smallest distance from
the body edge to a skeleton pixel lying in it; the lacuna's empty width is the
median over the sectors that answered. It is measured on the skeleton's own
pixels, because a ray marched outward runs along the corridor between two
threads and reports a hole where a thread sits 3 px to the side, which
overstated the width by up to a third when it was tried. A sector with no
skeleton within 150 px, or with another lacuna body nearer than its skeleton, is
censored.

The **hole** is the filled star between each body and its own sector widths. The
threads that bound it carry their own mask inward from their centre lines, so a
rim of mask lies inside the hole that belongs to them; the **core** is the hole
with that rim removed, every pixel more than 4 px from any skeleton (one thread
half width plus one). Everything below is measured on the core. The **control
band** is the 40 px of each sector immediately beyond the hole: the same tissue,
the same directions, the same depth of field, differing only in being past it.

### How wide the hole is

| image | lacunae | empty width px: min, median, p90, max | median um | p90 um |
|---|---|---|---|---|
| 542_z06 | 19 | 9.0, 20.1, 29.6, 55.2 | 2.61 | 3.85 |
| 542_z18 | 13 | 17.0, 27.3, 36.2, 51.6 | 3.55 | 4.71 |
| 543-2 | 12 | 17.0, 28.2, 42.8, 55.4 | 3.67 | 5.56 |
| 543_3 | 13 | 18.4, 31.5, 43.9, 59.1 | 4.10 | 5.71 |
| 543_z13 | 11 | 20.9, 26.1, 30.3, 31.9 | 3.39 | 3.94 |
| 682_z08 | 11 | 10.4, 20.0, 36.3, 38.9 | 2.60 | 4.72 |
| 682_z23 | 14 | 15.1, 30.1, 33.8, 52.7 | 3.91 | 4.39 |
| 682_z29 | 15 | 18.0, 29.1, 40.5, 54.1 | 3.79 | 5.27 |

Over all 108 lacunae: **min 9.0 px, median 27.4 px (3.56 um), p90 43.3 px, max
59.2 px (7.69 um)**. Every lacuna in the set has one. The 40 to 70 px holes are
real and are the upper end of the distribution.

### What is in the hole, against the band beyond it

| image | p99 response: core / band | p99 flattened: core / band | mask fraction: core / band | **flattened p50: core / band** |
|---|---|---|---|---|
| 542_z06 | 0.0659 / 0.2136 (31%) | 0.150 / 0.593 | 0.057 / 0.427 | **0.00000** / 0.00948 |
| 542_z18 | 0.0794 / 0.1939 (41%) | 0.203 / 0.544 | 0.058 / 0.427 | **0.00000** / 0.01143 |
| 543-2 | 0.1182 / 0.1662 (71%) | 0.332 / 0.467 | 0.119 / 0.453 | **0.00000** / 0.02464 |
| 543_3 | 0.0981 / 0.1624 (60%) | 0.278 / 0.455 | 0.096 / 0.459 | **0.00000** / 0.02566 |
| 543_z13 | 0.0746 / 0.1322 (56%) | 0.206 / 0.370 | 0.076 / 0.435 | **0.00000** / 0.01965 |
| 682_z08 | 0.0589 / 0.1762 (33%) | 0.132 / 0.486 | 0.042 / 0.396 | **0.00000** / 0.01452 |
| 682_z23 | 0.0651 / 0.1596 (41%) | 0.179 / 0.440 | 0.059 / 0.396 | **0.00000** / 0.01193 |
| 682_z29 | 0.0554 / 0.1349 (41%) | 0.141 / 0.372 | 0.047 / 0.408 | **0.00000** / 0.01117 |

Four things follow, and two of them rule out explanations.

- **The glow is not what raises the floor: the flattening removes it
  completely.** The median flattened value in the core is **exactly 0.00000 on
  every one of the 8 images**, lower than in the band beyond (0.0095 to 0.0257).
  A white top-hat returns zero wherever the image is locally flat at its 5 px
  scale, which a smooth glow is. The raw channel in the core is not brighter
  than in the band either (p50 0.153 to 0.302 against 0.176 to 0.306: equal or
  slightly lower). So the hole is not a bright background that swamps a thread.
- **Nothing is saturated.** 1 pixel in 1,048,576 over the whole set. The ceiling
  of the sensor plays no part.
- **Thread contrast there is real but weak.** The p99 of the flattened channel,
  which is where a thread shows up, is **25% to 71%** of the band's, and the
  ridge response follows it at **31% to 71%**. The mask covers 4.2 to 11.9% of
  the core against 39.6 to 45.9% of the band, about a quarter.
- So there IS something to recover, at roughly a third to two thirds of the
  amplitude the same tissue shows 40 px further out.

### Which stage removes it

Every pixel in a core with a ridge response of at least half the low cut, which
is the brief's definition of visible, attributed to the FIRST stage that drops
it:

| image | visible px in the core | below the low cut | hysteresis not connected | vascular no-growth | body buffer | despeckled | already in the mask |
|---|---|---|---|---|---|---|---|
| 542_z06 | 19886 | 12758 | 66 | 200 | 724 | 40 | 6098 |
| 542_z18 | 18027 | 11357 | 157 | 207 | 316 | 41 | 5949 |
| 543-2 | 23324 | 11155 | 223 | 0 | 154 | 13 | 11779 |
| 543_3 | 24070 | 13072 | 147 | 0 | 114 | 6 | 10731 |
| 543_z13 | 14578 | 8383 | 51 | 0 | 94 | 5 | 6045 |
| 682_z08 | 11962 | 8537 | 151 | 157 | 434 | 34 | 2649 |
| 682_z23 | 17325 | 11122 | 90 | 312 | 246 | 8 | 5547 |
| 682_z29 | 16435 | 10807 | 178 | 377 | 290 | 19 | 4764 |
| **all 8** | **145,607** | **87,191 (59.9%)** | 1,063 (0.7%) | 1,253 (0.9%) | 2,372 (1.6%) | 166 (0.1%) | 53,562 (36.8%) |

**The stage is the hysteresis low cut on the ridge response.** It takes 59.9% of
everything visible in the holes, which is **27 times** the other four stages put
together (4,854 px). The body buffer, the despeckle step and the vascular mask
are not the cause, at 1.6%, 0.1% and 0.9%.

### The 50 um prune, second and smaller

| image | skeleton in the hole before the prune | after | removed | share |
|---|---|---|---|---|
| 542_z06 | 3473 | 3222 | 251 | 7% |
| 542_z18 | 2375 | 2016 | 359 | 15% |
| 543-2 | 3427 | 2015 | 1412 | 41% |
| 543_3 | 3281 | 2054 | 1227 | 37% |
| 543_z13 | 2702 | 1959 | 743 | 27% |
| 682_z08 | 1875 | 1723 | 152 | 8% |
| 682_z23 | 2787 | 2236 | 551 | 20% |
| 682_z29 | 2885 | 2439 | 446 | 15% |

The 50 um prune removes 7 to 41% of the skeleton that does reach into a hole,
and that is why mask with no centre line within 4 px rises from 2.6 to 4.6% of
the core before the prune to 4.2 to 11.9% after. It widens the hole it finds; it
does not open it. Measured directly: the empty width taken against the skeleton
**before** the prune is the same to within a pixel on 7 of 8 images (543_3 is
the exception, 29.1 against 31.5 px), and only 683 of the 19,440 sectors in the
set are widened by it.

### What this rules out for the fix

Subtracting each lacuna's own radial glow profile before the ridge filter
**cannot work**, and the measurement says why: the top-hat already removes the
glow to a median of exactly zero. Subtracting a smooth profile from a channel
whose smooth part is already gone does not raise a thread's amplitude by
anything. What is low in the hole is the thread's own local contrast, not the
background it sits on.

What is left is the brief's second option, and it is the one the numbers
support: **inside each lacuna's own zone, accept a lower cut, seeded from the
skeleton that already exists.** 59.9% of the visible signal in the holes sits
between half the low cut and the low cut, which is exactly the tier the second
dim pass was built for (section 8); that pass cannot reach it only because it
may run 5 px past owned skeleton and the holes are 27 px wide.

Profiles for the five widest holes in the set, which is a rule and not a list of
coordinates, were in `results/empty_zone/` (not tracked: regenerate with
`python src/diagnostics.py empty-zone -d data/WT -o results/empty_zone`; as cited, at commit `bf3b982`): the neighbourhood with the hole, its
core and the control band outlined, beside the radial profiles of raw, flattened
and response with the cuts drawn on them.

### The fix: a lower cut inside each lacuna's own glow zone

The stage is the hysteresis low cut, so the fix is at that cut, and only where
the measurement says the cut is wrong.

**The zone.** Each lacuna's own **glow extent**
(`canaliculi.glow_extent_px`), measured on the **raw** channel, never on the
flattened one, because the flattening is what removes the glow. 180 rays leave
the centroid; along each one the distance is the true distance to the body, so a
concave body is measured from its real edge; the profile is the raw channel,
smoothed over 3 samples; the surface value is its mean within 1.5 px of the
edge; the local background is the median of the raw channel in the ring 70 to 90
px out with every lacuna body left out. The ray's extent is the first distance
at which the profile falls to `config.GLOW_PROFILE_FRACTION` = **0.10** of the
surface's excess above that background, and the lacuna's extent is the median
over the rays that answered, capped at `config.GLOW_ZONE_MAX_UM` = 8 um = 62 px.
A ray that leaves the frame or enters another lacuna is censored; a ray whose
surface is already at the background answers 0.

**It is never a fixed width.** That is the point. A fixed ring would be measured
on wild-type bone and then applied unchanged to the Hyp bone whose
periosteocytic lesions widen exactly this zone, which would bias the comparison
the project exists to make. Measured on the 8 WT images the extents run 3.9 to
33.2 px, a factor of 8.5 between lacunae of the same set, and no lacuna reaches
the cap.

**The cut inside it.** Inside the union of the zones, and nowhere else, the
ridge response is accepted down to `config.GLOW_ZONE_CUT_FRACTION` = **0.5** of
the low cut, under one limit: it must **connect to mask the global cut already
produced** (`canaliculi.grow_in_glow_zone`, a binary propagation seeded by that
mask). So nothing is created in open field, the lacuna bodies and their buffer
stay cut out, and inside a flagged vascular structure only already-bright pixels
survive, both exactly as in the first pass. 0.5 is the floor the second dim pass
already uses (section 8), so the pipeline has one definition of "dim" and not
two.

**Outside the zones the mask is bit for bit what it was**, which the check below
confirms on all 8 images. The 50 um cap, the contact rule and the dim pass are
untouched.

**What was rejected, and why.** Subtracting each lacuna's radial glow profile
before the ridge filter was the other option in the brief. The measurement rules
it out: the top-hat already leaves a median of exactly 0.00000 inside these
rings, lower than the tissue beyond them, so the glow is gone before the ridge
filter ever runs and there is nothing left to subtract. What is low there is the
thread's own contrast, which no background subtraction can raise.

**Not validated.** No hand count chose the fraction, the cut or the cap.

### What the glow zone does to all 8 images

Each image run twice in one process, once with `canaliculi.GLOW_ZONE_MAX_PX = 0`,
which is the pipeline as it was, and once as configured
(regenerate with `python src/diagnostics.py glow-check -d data/WT -o results/glow_zone`; not tracked,
as cited at commit `bf3b982`). Before
on the left of each arrow.

| image | glow extent px: min, median, max | zone px | mask added | skeleton inside the zones | empty width px | roots per lacuna | under 3 roots |
|---|---|---|---|---|---|---|---|
| 542_z06 | 3.9, 12.0, 18.8 | 105,463 | 5,528 | 2694 -> 3117 (+15.7%) | 20.1 -> 18.4 | 12.16 -> 12.63 | 1 -> 1 |
| 542_z18 | 10.9, 16.5, 26.0 | 117,124 | 6,031 | 2178 -> 2640 (+21.2%) | 27.3 -> 23.3 | 7.31 -> 9.00 | 1 -> 1 |
| 543-2 | 13.6, 18.4, 26.9 | 80,643 | 5,945 | 1577 -> 2122 (+34.6%) | 28.2 -> 24.6 | 5.92 -> 7.67 | 2 -> 1 |
| 543_3 | 13.0, 16.4, 26.7 | 77,068 | 4,829 | 1181 -> 1596 (+35.1%) | 31.5 -> 30.1 | 4.00 -> 5.62 | 6 -> 4 |
| 543_z13 | 11.9, 18.0, 33.2 | 75,847 | 6,150 | 1864 -> 2227 (+19.5%) | 26.1 -> 24.2 | 6.36 -> 7.46 | 0 -> 0 |
| 682_z08 | 8.1, 10.9, 19.2 | 69,687 | 2,908 | 1601 -> 1879 (+17.4%) | 20.0 -> 18.0 | 10.00 -> 11.55 | 0 -> 0 |
| 682_z23 | 10.6, 16.9, 19.5 | 78,778 | 3,956 | 1742 -> 2071 (+18.9%) | 30.1 -> 27.1 | 7.00 -> 7.86 | 1 -> 1 |
| 682_z29 | 4.7, 17.3, 21.9 | 80,986 | 4,898 | 1670 -> 2074 (+24.2%) | 29.1 -> 28.2 | 6.33 -> 7.07 | 2 -> 2 |

**The three checks.**

1. **The mask outside the zones is unchanged: PASS, bit for bit on all 8
   images.** The growth is a propagation whose mask is the old candidate plus
   pixels inside a zone, so every pixel it can add lies inside one.
   The **skeleton** outside the zones does move, by +238 to +2,835 px, and
   almost all of that is one thing: the 50 um prune now keeps thread it used to
   cut, because the zone connects that thread to a body. Per image, of the
   skeleton gained outside the zones, the prune accounts for 99 of 238, 961 of
   1102, 2045 of 2129, 1813 of 1985, 1083 of 1435, 1183 of 1256, 1858 of 1976
   and 2540 of 2835: **85 to 96%**. Nothing new was traced out there; thread that
   was already drawn stopped being thrown away.
2. **The empty zones shrink on every image: PASS.** Median empty width per
   image falls on all 8, and over the 108 lacunae from 27.4 to 24.2 px (3.56 to
   3.14 um). 84 of 108 lacunae have a smaller hole; the 11 whose hole grows are
   listed in `results/glow_zone/glow_check.json` (not tracked: regenerate with
   `python src/diagnostics.py glow-check -d data/WT -o results/glow_zone`; as cited, at commit `bf3b982`) and move by under a pixel
   except 542_z06 lacuna 14 (26.7 to 34.4 px) and 682_z29 lacuna 1 (24.2 to
   27.3 px), where a newly traced thread nearer the body in one sector pushes
   the first skeleton pixel of another sector further out.
3. **Roots per lacuna do not fall: PASS on every image**, +0.47 to +1.69 roots
   per lacuna. Per lacuna, 60 of 108 rise and 17 fall, every one of those by
   one or two roots where a new thread lands within the 8 px root merge distance
   of an existing root and the two count once, as section 3 defines them.

**Length guards, reported and not acted on** (the brief): the skeleton grows
1.7 to 9.6%, 5.5% over the set, which is inside the 25% guard the dim pass is
held to. Owned skeleton grows 6.0 to 21.7%, 12.8% over the set, and unowned
falls on every image. The unattached dim tier is unchanged to the pixel on all 8
images, as it must be, since it is computed from what no lacuna owns and the
zones are defined by lacunae.

| image | skeleton px | owned px | unowned px | 50 um prune px | unattached px |
|---|---|---|---|---|---|
| 542_z06 | 39229 -> 39890 (+1.7%) | 28803 -> 31159 (+8.2%) | 10426 -> 8731 | 787 -> 688 | 375 -> 375 |
| 542_z18 | 36688 -> 38252 (+4.3%) | 24971 -> 27573 (+10.4%) | 11717 -> 10679 | 1884 -> 923 | 372 -> 372 |
| 543-2 | 37700 -> 40374 (+7.1%) | 29417 -> 33719 (+14.6%) | 8283 -> 6655 | 8781 -> 6736 | 465 -> 465 |
| 543_3 | 35656 -> 38056 (+6.7%) | 25106 -> 30552 (+21.7%) | 10550 -> 7504 | 11572 -> 9759 | 224 -> 224 |
| 543_z13 | 41377 -> 43175 (+4.3%) | 28463 -> 31589 (+11.0%) | 12914 -> 11586 | 3848 -> 2765 | 256 -> 256 |
| 682_z08 | 35082 -> 36616 (+4.4%) | 26034 -> 27601 (+6.0%) | 9048 -> 9015 | 3566 -> 2383 | 1011 -> 1011 |
| 682_z23 | 36058 -> 38363 (+6.4%) | 24363 -> 27668 (+13.6%) | 11695 -> 10695 | 7402 -> 5544 | 560 -> 560 |
| 682_z29 | 33616 -> 36855 (+9.6%) | 23543 -> 27863 (+18.3%) | 10073 -> 8992 | 7753 -> 5213 | 513 -> 513 |

The 50 um prune falls on every image, by 11 to 51%: 44,593 px pruned over the
set before, 34,011 after. That is the clearest single sign of what the rule
does. A thread that could not reach a body within 50 um along the network was
being deleted; now the zone joins it to the body it belongs to and the limit
stops applying to it.

Before and after, skeleton and verification pictures, for the two images the
work was raised on: `results/before_after/543-2_glow_before.png` and
`_glow_after.png`, the same for 543_3, and `_glow_before_skeleton.png` and
`_glow_after_skeleton.png` beside them. The lacuna at (198, 635) on 543_3, which
owned an 11 px stub through three rounds of ownership work, owns a network in
the after picture.

**Not validated.** None of this is a hand count. The rule recovers thread the
method was throwing away, and whether that thread is real is a question only a
manual tracing can answer; none has been made.

## 19. The zone from the hole, the gain inside it, and what the hole measure can read

Section 18 lowered the cut inside each lacuna's **glow extent**. It recovered
7% of the skeleton on 543-2 and left the holes where they were: over the 108
lacunae the empty width fell only from 27.4 to 24.2 px. Two measured reasons.

- **The zone was narrower than the hole.** The glow extents run 3.9 to 33.2 px
  and the holes they are meant to fill run 9.0 to 59.2 px, median 27.4. A zone
  that stops short of the missing thread cannot recover it.
- **It could only extend mask that was already there.** `grow_in_glow_zone` is a
  propagation seeded by the global cut, so a thread whose whole run inside the
  hole is under that cut has no seed to grow from, and that is the thread the
  holes are made of.

So the zone is now measured on the hole itself, and the cut inside it is the
**same global cut** applied to a response that has been put back on the footing
of the tissue just beyond the hole. The glow extent is still measured
(`canaliculi.glow_extent_px`), because it is what section 18 documents and what
the checks read the zone against; it no longer decides where the cut applies.

```
python src/diagnostics.py hole-check -d data/WT -o results/hole_zone --pictures 543-2,543_3
```

`results/hole_zone/` is not tracked: regenerate with the command above; the file cited in this
section is at commit `bf3b982`.

### The zone

Per lacuna: its **empty width**, by the 180 sector rule of section 18
(`canaliculi.empty_width_px`), measured on the skeleton the **global cut**
produced before any zone pass, so the zone is never defined by its own output;
plus `config.HOLE_ZONE_MARGIN_UM` = 0.39 um = 3 px, one thread half width, so
the zone reaches the first thread that bounds the hole instead of stopping just
short of it; capped at `config.GLOW_ZONE_MAX_UM` = 8 um, the cap of section 18.

Zones overlap where two bodies are close. A pixel claimed by several goes to the
**nearer** of the bodies that claim it, which is the partition ownership already
uses, so every pixel has exactly one gain and none is boosted twice.

It is never a fixed width, for the reason section 18 gives: a lacuna with a
wider hole, which is what a periosteocytic lesion makes, gets a wider zone.
Measured over the 8 images the zone extents run 14 to 59 px, and **no lacuna
reaches the 8 um cap**.

### The gain, and why it is radial

Inside its own zone and nowhere else, each lacuna's ridge response is multiplied
by its own **contrast gain** and the same global cuts are then applied to it.
The gain is the `config.HOLE_GAIN_PERCENTILE` = 50th percentile of the response
in the band just beyond the zone over the same percentile inside it, which is
section 18's own measurement (31 to 71%, a gain of 1.4 to 3.2), clipped to
`config.HOLE_GAIN_MIN` = 1 so the cut inside a zone is never stricter than
outside it and to `config.HOLE_GAIN_MAX` = 3.

**One gain per lacuna does not work, and the measurement says why.** The p90 of
the ridge response by distance from the body edge on 543-2, as a multiple of the
low cut:

| distance from the body | 0 to 5 px | 5 to 10 | 10 to 15 | 15 to 20 | 20 to 25 | 25 to 30 | 30 to 40 | 40 to 50 | 50 to 70 |
|---|---|---|---|---|---|---|---|---|---|
| response p90 / low cut | 0.87 | 1.50 | 2.07 | 2.41 | 2.71 | 3.02 | 3.41 | 3.76 | 3.70 |

The loss is not flat across the hole: it is a **trough**, deepest at the body
and recovering outward to a plateau 40 px out, which is the top-hat digging
around a bright body (section 8 names the same trough in the attachment rule).
One gain of about 2 therefore over-corrects the outer half of the zone, where
the skeleton already is, and under-corrects the inner half, where the empty
width is decided. Tried first: it added 12,000 px of mask on 543-2 and moved the
empty width by nothing.

So the gain is a **radial profile**: measured in annuli
`config.HOLE_GAIN_STEP_UM` = 0.26 um = 2 px wide, smoothed over
`config.HOLE_GAIN_SMOOTH` = 3 annuli, and each pixel is multiplied by the gain
of the annulus it lies in.

**The innermost `canaliculi.HOLE_GAIN_SKIP_PX` = 6.2 px are not measured**, and
the first gain measured outside that ring is carried inward. Two reasons, both
already in the pipeline, so the number is derived and not tuned: no mask can
exist within `LACUNA_DILATION_PX` = 2 px of a body because the buffer is cut out
of it, and the top-hat leaves the body's own edge as a ridge which the Sato
filter answers at its own scale, `max(RIDGE_SIGMAS_PX)` = 4.2 px. What that ring
holds is the body, not a thread: on 542_z06 lacuna 3 the level runs 0.0445,
0.0290, 0.0134 over the first three annuli against 0.0077 in the band beyond, so
including it pinned the gain at 1 exactly where the hole is deepest. Skipping it
is what makes the profile a thread measurement, and it is what turned the root
counts of 542_z06 and 682_z08 from falling to rising.

Over the 8 images the gain at the body edge is 3.0 on 77 of the 108 lacunae and
1.9 to 3.0 per image at the median.

### The noise guard

The gain is applied with **no requirement to connect to mask the global cut
already made**, which is the point of it. That also lets the glow's own grain
cross the cut, so a component of the new mask that holds **no pixel of the mask
that was there before** is kept only if it looks like a thread: at least
`config.HOLE_NEW_MIN_LENGTH_UM` = 10 um long once skeletonized and at least
`config.HOLE_NEW_MIN_ASPECT` = 3 times longer than it is wide. These are the two
tests the unattached dim tier already applies (section 8), for the same reason:
nothing vouches for this mask, so it is accepted on its own shape alone.

**What it does, measured: 130 new components over the 8 images, 4,121 px, and
every one of them fails the length test.** A zone is at most 8 um wide, so a
piece of mask that lies inside one and touches nothing else can almost never run
10 um. The practical effect on this data is therefore that **every pixel the
rule adds is a continuation of mask the global cut already made**, and the
isolated pieces are all refused. That is a stricter outcome than the rule as
written, and it is reported here rather than tuned away.

### Ownership: a lacuna owns what touches it

`config.CONTACT_EVERY_TOUCHING_BODY`. The contact rule of section 8 offered each
node to its **nearest** lacuna only: a node 5 px from one body and 7 px from
another was offered only to the second, because it was nearest, and then refused
by the signal test. Contact is now decided by which bodies the node **touches**
(`canaliculi.touching_bodies`), and a node that touches two bodies goes to the
**nearer surface**. Beyond the contact reach nothing changes.

One more ownership fix, found by the checks and not by a rule. `prune_spurs`
removes a short terminal branch from the **graph**, but its pixels stay in the
skeleton, and they were not folded into the node they hang off, so they read as
skeleton that no lacuna owns. A stub beside a body is the commonest thing a new
thread in a hole leaves behind. The spur is now folded into its neighbour,
exactly as a collapse or a chain merge folds what it absorbs. No graph measure
moves: the spur is still out of the graph, so no edge length, degree or root
count changes. Over the 8 images it took the near-body skeleton that no lacuna
owns from 324 px to 57 px in the before run and from 353 px to 95 px in the
after run.

### What the hole measure can read: the null floor

The empty width cannot read 0 however complete the tracing is. A sector is a
**wedge** whose width grows with the radius: at 10 px from a 25 px body it is
0.35 px wide, so the first skeleton pixel inside that wedge sits further out
than the nearest skeleton pixel in any direction, and the median over 180 such
wedges is a number about the geometry as much as about the tissue.

So `hole-check` measures the floor directly: the same sector rule applied to
**40 synthetic discs** of the image's own median body size, dropped in tissue at
least 120 px from every real lacuna, where there is no body and so no hole at
all (`diagnostics.hole_null_floor`). Over the 8 images that floor is **22.0 px**,
per image 17.6 to 28.2.

The empty width after the fix is **22.4 px**, 0.4 px above that floor, from 24.2
px before. On three images it is at or below the floor of its own image. **The
hole, as this measure reads it, is as closed as the measure can read.**

### What it does to all 8 images

Before is `config.HOLE_ZONE_RULE = False` with
`config.CONTACT_EVERY_TOUCHING_BODY = False`, which is the glow zone version of
section 18 exactly; after is as configured.

| image | zone px | zone extent px: min, median, max | gain at the body edge, median | mask added px | skeleton in the zones | skeleton px | changed px |
|---|---|---|---|---|---|---|---|
| 542_z06 | 150,055 | 16, 25, 59 | 1.90 | 8,439 | 6,354 -> 6,589 | 39,964 -> 40,198 | 3,516 |
| 542_z18 | 136,149 | 21, 31, 55 | 3.00 | 8,481 | 4,963 -> 5,278 | 38,360 -> 39,183 | 3,699 |
| 543-2 | 119,134 | 20, 34, 46 | 3.00 | 9,772 | 4,637 -> 5,077 | 40,561 -> 44,105 | 6,766 |
| 543_3 | 127,224 | 22, 32, 54 | 3.00 | 10,170 | 4,448 -> 4,982 | 38,356 -> 41,269 | 6,941 |
| 543_z13 | 94,114 | 24, 29, 35 | 3.00 | 7,597 | 3,984 -> 4,276 | 43,352 -> 44,246 | 4,736 |
| 682_z08 | 90,269 | 14, 25, 49 | 2.03 | 4,550 | 3,734 -> 3,859 | 36,787 -> 36,997 | 1,856 |
| 682_z23 | 123,144 | 20, 30, 49 | 3.00 | 6,790 | 4,542 -> 5,130 | 38,480 -> 40,046 | 6,998 |
| 682_z29 | 140,603 | 23, 32, 57 | 3.00 | 8,452 | 5,095 -> 5,444 | 36,957 -> 37,663 | 4,574 |

Over the set the skeleton grows from 312,817 to 323,707 px (+3.5%), and
**39,086 px change against the glow zone version**.

| image | empty width px | null floor px | roots per lacuna | under 3 roots | owned px | 50 um prune px | unattached px | loops |
|---|---|---|---|---|---|---|---|---|
| 542_z06 | 18.36 -> 18.97 | 26.27 | 12.68 -> 13.11 | 1 -> 1 | 31,615 -> 32,887 | 690 -> 686 | 375 -> 355 | 153 -> 159 |
| 542_z18 | 23.30 -> 22.47 | 20.81 | 9.00 -> 10.23 | 1 -> 1 | 28,019 -> 29,658 | 924 -> 448 | 372 -> 372 | 146 -> 156 |
| 543-2 | 24.56 -> 23.67 | 19.23 | 7.67 -> 8.50 | 1 -> 0 | 34,260 -> 37,623 | 6,737 -> 3,560 | 465 -> 465 | 244 -> 275 |
| 543_3 | 30.08 -> 26.66 | 23.24 | 5.62 -> 6.62 | 4 -> 2 | 31,221 -> 36,517 | 9,608 -> 7,304 | 224 -> 224 | 214 -> 244 |
| 543_z13 | 24.18 -> 23.43 | 25.16 | 7.55 -> 9.27 | 0 -> 0 | 32,225 -> 34,599 | 2,785 -> 2,171 | 256 -> 256 | 210 -> 231 |
| 682_z08 | 18.00 -> 17.13 | 18.08 | 11.55 -> 11.91 | 0 -> 0 | 28,124 -> 28,414 | 2,389 -> 2,374 | 1,011 -> 1,011 | 174 -> 181 |
| 682_z23 | 27.14 -> 22.62 | 17.58 | 7.86 -> 8.93 | 1 -> 0 | 28,101 -> 32,023 | 5,542 -> 4,586 | 560 -> 560 | 183 -> 205 |
| 682_z29 | 28.16 -> 25.93 | 25.41 | 7.07 -> 7.80 | 2 -> 1 | 28,272 -> 29,408 | 5,218 -> 4,781 | 513 -> 513 | 163 -> 165 |

Owned skeleton grows from 241,837 to 261,129 px (+8.0%), roots per lacuna rise
on **every** image, lacunae under 3 roots fall from 10 to 5, and the 50 um prune
falls from 33,893 to 25,910 px (-24%): thread that could not reach a body within
50 um along the network is now joined to the body it belongs to.

The unattached dim tier is unchanged on 7 images and falls by 20 px on 542_z06,
where one piece of it is now part of a thread a lacuna owns.

### The acceptance tests

| test | result | number |
|---|---|---|
| **A** mask outside every zone bit identical | **PASS** | on all 8 images, outside the zones of both versions |
| **B** empty width median under 15 px, and 90% of lacunae within their glow extent plus 10 px | **FAIL** | 24.19 -> 22.43 px against a floor of 22.02; 74 of 108 (68.5%) within |
| **C** near-body skeleton that is not the body's own, down 80% | **FAIL** | 57 -> 78 px; the part nobody owns fell 50 -> 42, the part another lacuna owns rose 7 -> 36 |
| **D** roots per lacuna do not fall, and lacunae under 3 roots drop | **PASS** | roots rise on all 8 images; under 3 roots 10 -> 5 |
| **E** no lacuna holds more than 25% of an image's skeleton | **PASS** | largest share 18.9% |

**Why B cannot pass.** The target is below the floor of the measure. The median
empty width is 22.43 px against a null floor of 22.02 px, so what is left is the
wedge geometry and not a hole. The second half of the test fails for the same
reason: 30 of the 108 lacunae have a glow extent plus 10 px that is **below the
floor of their own image**, so no tracing can bring them inside it, and 13 of
the 34 lacunae that fail are of that kind. What a tracing can be asked for is
density, and there the hole is nearly closed: the skeleton density in the zones
is 83 to 90% of the density in the band beyond, against 76% before.

**Why C cannot pass.** The quantity was already near zero before the fix, 57 px
over 8 images against 8,011 px of near-body skeleton the bodies do own, 0.71%.
The new rule puts 14% more skeleton beside the bodies, and of the 78 px left,
**42 px is owned by nobody** (down from 50) and **36 px is owned by another
lacuna** (up from 7), all of that last on 543_3 and 682_z23 where a thread
touches two bodies. A thread has one owner in this model, so the body that does
not get it reads it as another lacuna's; the only way to zero that term is to
let two cells own the same pixels, which would double-count length in every
per-cell measure.

### Loops, report only

`loop_count` and `loop_edge_share`, per cell and per field, in every output.
Nothing deletes a loop: a loop in a canalicular network is either a real
anastomosis or two threads traced as one ring, and which it is cannot be decided
by this method. The count is the cyclomatic number, edges minus nodes plus
components; the share is the fraction of edges that are not bridges. Over the 8
images the count rises from 1,487 to 1,616 and the share of edges on a loop from
0.372 to 0.387.

### Pictures

`results/before_after/`: `<label>_hole_before.png` and `_hole_after.png` are the
verification pictures, `_hole_before_skeleton.png` and `_hole_after_skeleton.png`
the skeletons, and `_hole_after_marked.png` rings every lacuna whose hole is
still wider than 20 px, for 543-2 and 543_3. The changed pixel count against the
glow zone version is 6,766 on 543-2 and 6,941 on 543_3.

**Not validated.** No hand count chose the margin, the percentile, the clip, the
skip or the guard, and none of these numbers is a validation. Whether the thread
this rule recovers is real is a question only a manual tracing can answer; none
has been made.

## 20. The second method: the AI judge

**Status: one of two methods, the choice between them pending, NOT VALIDATED
against a manual trace.** The full write-up, with every decision and number, is
[docs/EXPERIMENT_AI.md](EXPERIMENT_AI.md); this section says what the method is
and how it differs from the deterministic one.

**What it changes.** Ownership in the deterministic method goes by the shortest
path through the skeleton (section 8). That is right for a thread its own cell
traced and wrong at a join: a whole connected network can go to a cell that
reaches it through one thread while another cell lies closer to where those
threads start and has no skeleton path to them. The AI judge method asks a
judgement where that is a judgement call, and feeds the answer to the same
shortest path step. Deterministic code still does every pixel operation; the
model only answers questions about numbered segments in a picture.

**What the judge is asked.** A segment is a branch of the skeleton, at least
1.3 um long. It is put to the judge when it falls in one of four classes:
(a) unowned, with a lacuna within reach; (b) new, a faint piece a permissive
cut finds inside a lacuna's zone of the hole (section 19) that the pipeline did
not keep; (c) touching a body that does not own it; (d) owned by a lacuna that
is not the nearest one by straight distance, where the nearest lacuna's body
lies within its own zone of the hole plus 10 px. "Within reach" is that same
test, so the method defines no number of its own. For a, c and d the question is
**which osteocyte the thread starts from: the first candidate, the second, or
none**; for b it is also **whether it is a real thread or glow texture**. Over the
8 images: 895 segments in 145 cases, class d alone 210 segments involving 77 of
the 108 lacunae.

**How a verdict is used.** A verdict naming a cell adds a **zero weight
attachment from that cell to the end of the segment nearest it**, and then the
existing multi source shortest path assignment and the 50 um cap run unchanged.
Nothing is reassigned by hand; the network stays connected and the old owner
keeps whatever the shortest path still gives it. "None" adds nothing. A segment
two cases answer differently is left alone and counted. Only a class b segment
can be added (judged real) or refused (judged artifact), so nothing the judge
says deletes tracing the pipeline made.

**Roots.** A verdict's attachment is marked `judged`. It splits the network like
any other attachment but is **not a root**: a root is counted only for an
attachment the pipeline's own contact or attach rule made, within reach of the
body (`quantification.root_points`). Before this was fixed, every verdict that
gave a cell a segment away from its body added a root, and judge-on roots rose
from 1,045 to 1,482 over the 8 images; with the fix they are 1,113. With the
switch off no edge is marked and every number is the deterministic method's.

**What it does to the numbers**, over the 8 images
(`results_ai_judge/WT/compare/compare_methods.xlsx`):

| measure | deterministic | AI judge |
| --- | --- | --- |
| roots per interior cell, pooled | 10.27 | 10.95 |
| roots, all lacunae | 1,045 | 1,113 |
| ring length r30 px per interior cell, pooled | 398.9 | 440.9 |
| field length density per px | 0.03970 | 0.04068 |
| skeleton px | 323,707 | 331,691 |
| owned px | 261,129 | 277,235 |
| unowned px | 62,578 | 54,456 |
| largest owner share, highest image | 0.189 | 0.195 |

21,373 px of tracing changed hands between cells, in 770 segments and 100 cell
pairs, as whole connected networks; no single cell takes over an image.

**Reproducibility, cost and approval.** The model is pinned
(`claude-sonnet-5-5`), no temperature is sent (the model rejects one) and
thinking is off. Every request and answer is logged with its hash in
`results_ai_judge/WT/ai_log/`, with the case pictures that were actually sent, and
the replay reruns the whole log offline to identical verdicts on all 8 images.
The real run was made once, on 2026-10-19: **143 calls, $1.60**, against a dry
run estimate of $1.19 and a ceiling of `config.MAX_COST_USD` = $5; one answer in
143 could not be read and its retry was valid, so no segment was left unjudged.
**External API use approved on 2026-10-15, approver: Karim.**

**Not established.** No verdict has been checked against a manual trace, so
nothing here says the judge's answer is better than the shortest path's. A
thread given to the wrong cell moves that cell's whole measured network, so the
cost of a wrong answer is not symmetric. A manual trace is what should decide
between the two methods, and none has been made.

## 21. Groups

**The groups.** `config.GROUPS`: WT, WT_HP, Hyp_RD and Hyp_HP; RD is regular
diet and HP high phosphorus. Each has its own folder in `data/` and in
`results/`, with the same layout inside; the AI judge set holds WT only, in
`results_ai_judge/WT/`.

**WT is the reference, and nothing is tuned on the others.** Every rule and value
in sections 1 to 19 was chosen by visual inspection of the 8 WT images. The other
groups run with exactly the same code and settings, and no parameter may be tuned
on them, so a difference between groups is measured by one fixed method. Whether
that method serves Hyp bone as well as WT is not established: it is validated on
no group (section 15).

**What goes into a group** (`python src/diagnostics.py import-group`, the image
import constants of `config.py`). A source file is copied into `data/<group>/`
under its own name only if the pipeline would read it as it reads WT: a TIFF by
content, not by name (a `.tiff` is copied as `.tif`); a pixel shape, channel count
and sample type the WT images have (1024 x 1024; 3, or 4 with alpha; uint8); and
no pixel size in the metadata that disagrees with 0.13 um/px at two decimals. A
resolution per inch is a print density, not a pixel size, and is only recorded.
Every other file is skipped and listed with the reason in
`data/image_inventory.csv`. JPEG is excluded on purpose: it is lossy, and it
stores the colour detail that carries the red channel at half resolution in each
direction (4:2:0), which changes the pixels a ridge filter of 3 to 4.2 px
measures. With WT in uncompressed TIFF, a JPEG group would differ from it by
format as well as by biology.

**State on 2026-10-20.** The source folders of the three new groups hold 27 files,
9 per group, every one a JPEG (1024 x 1024 x 3, uint8, 4:2:0, 300 dpi print
density); one, `876_z76c1-2.tif`, is a JPEG named .tif. All 27 were skipped, so
**no image of WT_HP, Hyp_RD or Hyp_HP has been processed** and those groups have
no results. No TIFF of the same name exists in the source tree. Raw z-stacks
exist for some animals (534, 535, 701, 876), but taking a plane from a stack makes
a new image rather than copying one, and it was not done.

**Running a group.** The three stages with `--dir data/<group> -o results/<group>`.
With no `-o` a stage writes to `results/<name of the input folder>/`
(`lacunae.output_root`), so no group can write into another's folder. An image
that fails in a stage is listed with the error in
`results/<group>/all_images/failed_images_<stage>.csv` and skipped, and the
others carry on; a folder with no `.tif` writes nothing.

**Across groups.** `group-overview` writes `results/group_overview.csv` and
`.xlsx`, one row per image with its group: lacuna count, interior count, roots per
cell, ring length 30 px, field length density, skeleton px, unowned px and width
median. It computes no statistic and compares no groups. Skeleton and unowned px
come from each image's saved skeleton and graph through the owner map the
pipeline builds; on WT they equal what `compare-methods` measured on the
in-memory owner maps. `group-qc` writes `results/group_qc.csv`, per image of every
group but WT: the lacuna count, the candidates of at least 150 px² the lacuna
stage rejected, by the rule that rejected each (area too small or too large,
solidity, aspect ratio; smaller specks counted apart), a flag where the count is
outside the WT range, and a rank of which outlines to look at first. The range is
the minimum and maximum lacuna count of the WT images, 11 to 19, read from
`results/WT/` when the command runs. A flag says where to look; nothing is tuned
from it.
