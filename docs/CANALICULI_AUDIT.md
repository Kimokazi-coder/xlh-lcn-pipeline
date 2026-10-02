# Canaliculi audit: a stage by stage map of src/canaliculi.py

**Pre-validation, pixel units.** Branch `canaliculi-v2`, base 8673380. This page maps each stage of the
network part of the pipeline: what it does, which names control it, where each value came from
(`docs/METHODS.md` section 2 and the comments in `src/canaliculi.py`), and which of the known flaws it
touches. It is the reference for the later items of this branch. The parameters are module constants at
the top of `src/canaliculi.py`; `config.py` holds only the shared settings and the switches.

The known flaws, numbered for reference below:

| flaw | what |
|---|---|
| F1 | 542_z06: a straight bright line continues the vascular band below its canal mask (x 515 to 541, y 590 to 900, 382 skeleton px, 1.1% of the skeleton) and is counted as canaliculus |
| F2 | ring length counts every skeleton pixel within 30 px, including threads that only pass by |
| F3 | skeleton length is a pixel count: a diagonal step counts 1, not $\sqrt{2}$ (up to 29% short) |
| F4 | the network cut t_lo moves field density almost one to one and ring lengths nearly as much |
| F5 | bridges change by tens of percent for a 10% change of the cut; bridging was derived on WT only |
| F6 | roots depend on the graph cleanup, the 10 px attach gap and the 8 px merge distance, and carry lacuna size |
| F7 | ownership measures are unstable across sections of one field (out of scope) |

## 1. Flattening

**What it does.** `preprocess_unnormalised` and `preprocess_channel`: a light Gaussian, a white top-hat
(keeps what is narrower than the disk) and subtraction of the histogram mode, then division by the
maximum, so the image runs from 0 to 1.

**Names.** `SMOOTH_SIGMA_PX` = 0.8; `TOPHAT_RADIUS_PX` = 5.

**Origin.** Sigma below the thread width, as in OCY_main.m. Top-hat radius from measured thread
half-widths (p50 3.0, p99 4.2 px) and by eye at r = 4, 5, 6 on 542_z06 and 543-2 (4 fragments, 6 fuses).

**Flaws.** F4: the division by each image's own maximum makes every later cut image relative. The
top-hat radius sets which structures can become threads at all, so it reaches every network measure.

## 2. Hysteresis

**What it does.** `total_signal_mask` and `hysteresis_mask`: the strict cut t_lo is the lower
three-class multi-Otsu cut of the flattened image; pixels down to 0.75 t_lo are kept only where they
connect to pixels above t_lo.

**Names.** `HYSTERESIS_LOW_FRACTION` = 0.75; t_lo is computed per image (the sensitivity diagnostics
can pass it).

**Origin.** 0.75 was the one setting inside two guards fixed in advance (total length at most 1.20 times
and loops at most max(1.5 times, +50)) after 0.5 failed: one value after one failure, not a sweep, the
weakest provenance of any default.

**Flaws.** F4 directly: t_lo moves field density about +11% at 0.8 and -8% at 1.2 (overnight 2.4).
F1: hysteresis grows dim pixels along the band wall wherever growth is not blocked.

## 3. Canal blocking

**What it does.** `flagged_structures`: an opening with a large disk on the raw channel keeps only broad
objects; objects spanning a large share of the image with a long major axis are flagged and dilated.
Inside the flagged region hysteresis may not add pixels (only strict-cut pixels stay) and no bridge may
start, end or pass. Nothing is removed.

**Names.** `BROAD_OPENING_RADIUS_PX` = 8; `FLAGGED_MIN_SPAN_FRACTION` = 0.45;
`FLAGGED_MIN_MAJOR_AXIS_PX` = 420; `FLAGGED_DILATION_PX` = 4.

**Origin.** Radius 8 erases every canaliculus (width p99 8.5 px). The span and axis gates sit in a clean
gap between lacuna-scale objects (span at most 0.23, axis at most 211 px) and canals (span at least
0.58); WT only. The dilation is where network density returns to baseline (4 px).

**Flaws.** F1: in 542_z06 the flagged region covers only the top 60 rows of the line (90 of its 382
skeleton px lie inside it), so the wall below is grown and traced like a canaliculus. The flagged mask
also decides the "c" mark of the figures; it fully covers five ordinary-looking lacunae.

## 4. Network mask and skeleton

**What it does.** `network_candidate_mask` removes the lacuna bodies plus a 2 px buffer and specks
under 8 px²; `skimage.morphology.skeletonize` reduces the rest to one-pixel centre lines.

**Names.** `LACUNA_DILATION_PX` = 2; `MIN_THREAD_OBJECT_PX2` = 8.

**Origin.** The buffer keeps the bright rim of a lacuna from reading as a thread stub; 8 px² is small
enough to keep a short real thread.

**Flaws.** F3: every later length is a count of these pixels. The skeleton itself is never pruned: the
spur pruning of stage 6 acts on the graph only, so ring lengths and field density include spurs.

## 5. Gap bridging

**What it does.** `find_bridges` and `apply_bridges`: a thread end is joined to the nearest pixel of
another skeleton component if the gap is short, points within an angle of the thread's own direction and
holds signal along its whole length; the bridged mask is skeletonized again. No bridge may touch a
lacuna or a flagged region. Not in OCY (in 3D a thread leaving one plane continues in the next).

**Names.** `MAX_BRIDGE_GAP_PX` = 10; `MAX_BRIDGE_ANGLE_DEG` = 40; `MIN_BRIDGE_SIGNAL_FRACTION` = 0.7
(of t_lo); `DIRECTION_WALK_PX` = 5.

**Origin.** Measured on the pooled gaps of the 8 WT images (phase 0(c)): the minimum signal along a gap
falls from 0.886 of the cut at 5 to 8 px to 0.568 at 11 to 15 px; 21% of endpoint pairs lie under 20
degrees and 17.8% at 20 to 40; 93.5% of 5 to 8 px gaps reach 0.7.

**Flaws.** F5: the bridge count is the least stable output (-79% to +86% for 10% changes of t_lo,
overnight 2.4), and the signal test is relative to t_lo, so bridging follows F4. Bridges add skeleton
pixels, so they reach ring lengths, roots and field density.

## 6. Graph and cleanup

**What it does.** `build_network_graph` turns the skeleton into a weighted graph with skan (nodes are
junction and end pixels, edges are branches); `clean_network_graph` prunes short spurs, collapses short
internal edges (thread crossings) and merges degree-2 chains, repeated until nothing changes.

**Names.** `PRUNE_SPUR_LEN_PX` = 4; `MIN_INTERNAL_EDGE_LEN_PX` = 6; `GRAPH_CLEANUP_MAX_ITER` = 20.

**Origin.** Spurs under 4 px are thresholding noise. The crossing collapse is one thread width
(about 6 px); OCY's own ratio would remove half of all internal edges. Parallel edges keep the shorter
length (1.3% of branches).

**Flaws.** F6: the nodes left after cleanup are what stage 8 attaches to a lacuna, so the cleanup
reaches the root count. Ring lengths and field density do not use the graph.

## 7. Ownership

**What it does.** `attach_lacunae` adds one virtual node per lacuna, linked to every skeleton node
within 10 px of its body; `assign_by_connectivity` runs one multi-source shortest-path search, and each
edge goes to the owner of its nearer end. There is no distance limit.

**Names.** `LACUNA_ATTACH_GAP_PX` = 10.

**Origin.** The smallest node-to-body gap per lacuna runs p50 2.24, p95 5.00, max 7.00 px, so 10 attaches
every lacuna (5 left 28 of 98 unattached).

**Flaws.** F7: owned length, edge count and mean edge length move with sections and caps; they are
labelled ownership-dependent and are out of scope here.

## 8. Roots

**What it does.** `cell_root_count`: the skeleton nodes attached to a lacuna (within 10 px of its body)
are clustered by single linkage at 8 px; each cluster is one root.

**Names.** `LACUNA_ATTACH_GAP_PX` = 10; `ROOT_MERGE_DIST_PX` = 8.

**Origin.** 8 px is one canalicular width (p50 6.0, p99 8.5 px), so two attachment points that close
cannot be separate threads.

**Flaws.** F6: a junction of a thread that only passes within 10 px of the body is also attached and can
count as a root; the count depends on which nodes survive the cleanup; a bigger body has a longer
boundary and more roots (Spearman 0.84 across images, overnight 4.1).

## 9. Rings

**What it does.** `nearest_lacuna_map` gives each pixel its distance to the lacuna masks and its nearest
lacuna (a Euclidean partition); `ring_lengths` counts the skeleton pixels within 30 px (and 60 px) of the
masks, each for its nearest lacuna. Graph and ownership are not used.

**Names.** `RING_RADII_PX` = (30, 60).

**Origin.** 30 px from the round 2 local-density work; 60 px is twice that, about two thirds of the
median lacuna length (89 px).

**Flaws.** F2: a thread passing through the ring without touching the cell counts in full. F3: pixel
counts. F4: the ring holds whatever the cut lets through. Ring length also carries lacuna size (Spearman
0.88 across images); the appended ring densities $L_r / A_r$ remove that.

## 10. Field density

**What it does.** `field_metrics`: all skeleton pixels divided by the analysed area (the image minus the
lacunae). It uses no graph and no ownership.

**Names.** None of its own: it inherits stages 1 to 5.

**Origin.** Per-field length density, the most repeatable measure across sections (1.7 to 3.0% within
a field, overnight 6.1).

**Flaws.** F1 (the band wall is 1.1% of 542_z06's skeleton), F3 (pixel count), F4 (follows t_lo almost one
to one) and F5 (bridged pixels). The canal masks and the no-tissue corners stay in the denominator (at
most 1.6% and 3.1%, overnight 5.1).

## Where the items of this branch act

| item | stage | flaw |
|---|---|---|
| C1 attached ring length | 9 | F2 |
| C2 chain code length | 9, 10 | F3 |
| C3 Sholl crossings | a new per-cell count outside stages 6 to 8 | F6 |
| C4 density without flagged, in an ROI | 10 | F1 (partly), denominator |
| B1 straight band-wall filter (switch, off) | between 5 and 6 | F1 |
| S1 network sweep | 1, 2, 5, 6, 8 | F4, F5, F6 |
| S2 bridging audit | 5 | F5 |
| V1 validation harness | all, against hand counts | all |
