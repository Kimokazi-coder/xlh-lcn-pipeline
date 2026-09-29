# Progress status

_Last updated: 2026-09-29 (round 3 housekeeping). Everything below is v1-raw/v2-raw and pre-validation
against Mahmoud's ImageJ ground truth counts, unless stated otherwise._

## Features that exist

### Lacuna counting
- **`src/count_lacunae.py` (v1)** — original single-global-threshold
  (Otsu/percentile) approach. Fully wired to `config.py`. Undercounts badly
  on dense images (a lacuna fused to its canaliculi mesh gets rejected by
  the size filter). Kept for reference; not actively used right now.
- **`src/segment_lacunae_v2.py` (v2, current/active)** — multi-Otsu
  (3-class) threshold + marker-controlled watershed to separate lacunae
  from mesh by thickness instead of brightness. Fixes v1's undercounting.
  Own parameters live at the top of the file (not yet promoted into
  `config.py`): `TEST_MIN_AREA_PX2=400` (calibrated from the interior-area
  distribution across all 8 WT images — see module docstring),
  `TEST_MAX_AREA_FRACTION_OF_IMAGE=0.05`, `TEST_MIN_SOLIDITY=0.5`,
  `TEST_ASPECT_RATIO_MAX=6.0`, `SEED_PROMINENCE_FRACTION=0.3`,
  `MERGE_SADDLE_RATIO_MIN=0.35` (new, see Known Issues). Border lacunae are
  kept and flagged `on_border`, not dropped. Outputs per image under
  `results/lacunae/<image>/`: `overlay.png`, `measurements.xlsx` (summary +
  per_lacuna sheets), `measurements.json`. Per-image summary stats
  (mean/median/SD of area, axis lengths, aspect_ratio, eccentricity,
  solidity) computed over interior (non-border) lacunae only.

### Canaliculi (per-lacuna)
- **`src/canaliculi_v1.py` (v1-raw)** — builds on v2's lacuna segmentation
  (imported, not modified).

  **Network segmentation, `PREPROCESS_MODE` ("tophat" = default,
  "none" = old, kept for comparison via `--preprocess none`).** Adapted
  from the published OCY pipeline (Kollmannsberger et al., "The small
  world of osteocytes"; theirs is 3D MATLAB, this is 2D Python — the
  method is adapted, not ported, and every borrowed step is cited in
  comments):
  - light Gaussian, `SMOOTH_SIGMA_PX=0.8`, below canaliculus width
    (OCY_main.m's `smooth3(img,'gaussian',5)`);
  - white top-hat, `TOPHAT_RADIUS_PX=5` disk (OCY_thr_stack.m's
    `imtophat(img,strel('disk',25))` at their 0.2 µm/voxel);
  - histogram-mode offset subtraction, `BACKGROUND_MODE_SUBTRACT=True`
    (the 256-bin mode subtract OCY_thr_stack.m applies after its
    top-hat, bin 1 and bins 200+ zeroed);
  - then the same per-image lower multi-Otsu cut as before, minus a
    buffer around lacuna bodies, despeckled by pixel count (not
    erosion), skeletonized.
  `TOPHAT_RADIUS_PX=5` was chosen from measured thread widths, not
  guessed: post-top-hat canalicular half-widths are p50≈3.0/p99≈4.2 px
  (so real threads are ≤8 px across and a disk of diameter 11 cannot fit
  inside one), cross-checked visually at r=4/5/6 on 542_z06 and 543-2 —
  r=4 breaks threads into fragments, r=6 fuses neighbouring threads back
  into ribbons. Before this change the mask was ~24% of the field with
  ~6-10 px fused ribbons; the diffuse halo around each lacuna thresholded
  in as a solid slab and adjacent threads merged, and the skeleton of
  that branches everywhere. See `src/diagnose_canaliculi_mask.py`.

  **Skeleton graph cleanup (`clean_network_graph`)** — prune, collapse,
  re-simplify, iterated to a fixed point, the way OCY_run_Skel2Graph3D.m
  re-runs its whole condense/skeletonize/re-graph cycle until network
  length stops changing (`GRAPH_CLEANUP_MAX_ITER=20` is only a safety
  stop):
  - terminal spurs shorter than `PRUNE_SPUR_LEN_PX=4` pruned;
  - internal edges (both ends a real junction) shorter than
    `MIN_INTERNAL_EDGE_LEN_PX=6` collapsed by merging their endpoints —
    OCY's `Skel2Graph3D` `THR_BRANCH` (called with 5 in
    OCY_run_Skel2Graph3D.m) removes *all* short branches, not just
    terminal ones. In a dense 2D projection two threads that merely
    cross produce two junction nodes about a thread-width apart joined
    by a stub; that stub is the crossing, not a canaliculus. The
    surviving node is whichever endpoint is nearer a lacuna, so a merge
    can never cost a cell its attachment. The value is anchored on our
    own geometry (~6 px thread width), not on OCY's ratio, which would
    scale to ~15 px here and remove half of all internal edges; the
    pooled internal-edge length distribution is smooth with no natural
    break (p10=3.4, p25=7.8, p50=16.7 px), so this is a geometry cutoff,
    not a gap-based one;
  - degree-2 nodes dissolved into their neighbours with weights summed,
    so one uninterrupted thread is ONE edge of its true length. Pruning
    a spur off a degree-3 node leaves a degree-2 node behind, and so does
    collapsing an internal edge; OCY never sees these because
    Skel2Graph3D rebuilds the graph from the voxel skeleton each round.
  Effect (542_z06 / 543-2 / 682_z08): degree-2 nodes 91/204/109 → 0/6/0,
  degree-3 286/487/376 → 264/416/304, degree-4+ 1/1/1 → 12/36/34 (correct:
  a collapsed crossing stub merges two false degree-3 junctions into one
  real degree-4 crossing), edges 1309/1796/1506 → 1207/1562/1356, and
  **total network length conserved to within 0.3%** — it defragments
  rather than deletes.

  **Two assignment methods, `ASSIGNMENT_METHOD` ("graph" = default,
  "euclidean" = old, kept for comparison via `--method euclidean`):**
  - `"graph"` (OCY-style, Kollmannsberger et al.): the whole skeleton is
    one weighted graph; each lacuna is a virtual source node attached to
    skeleton nodes within `LACUNA_ATTACH_GAP_PX=10` of its body; a single
    multi-source shortest-path assigns every reachable node to whichever
    cell it's graph-connected to (not spatially nearest). Terminal spurs
    shorter than `PRUNE_SPUR_LEN_PX=4` are pruned first. Per cell,
    `assign_edges` then gives *every* real edge an owner (previously only
    shortest-path-tree edges had one, so loop-closing branches were owned
    by nobody and went unpainted), using OCY's rule from
    OCY_assign_dist.m: a link is reached through whichever end is nearer
    a cell.
  - `"euclidean"`: every skeleton pixel assigned to its nearest lacuna by
    Euclidean distance transform (Voronoi), no spur pruning; per-lacuna
    root-to-tip tree search (root = closest point to the lacuna;
    `MAX_ROOT_GAP_PX=15` cutoff). Always path-based, ignores `COUNT_MODE`.

  **What counts as one canaliculus, `COUNT_MODE` ("edge" = default,
  "path" = old, kept for comparison via `--count-mode path`).** Graph
  method only.
  - `"edge"` (OCY-style): one canaliculus = one graph edge between two
    nodes, exactly how OCY counts — its `link` structs *are* the
    canaliculi and every number in OCY_get_network_params.m derives from
    them. Per cell: edges owned, total length, mean edge length.
  - `"path"`: one canaliculus = one cell-to-tip path (single-source
    Dijkstra from the cell's virtual node to every reachable owned
    degree-1 tip). This re-counts the shared trunk of a branching thread
    once per tip.
  Note the finding here cuts against the expectation going in: switching
  to edge counting *raises* the count (~2×, since a tree with T tips has
  ~2T−1 edges) and is not what was inflating it. What path counting
  actually inflated was **length** — its per-cell total is 1.3–2.3× the
  length that physically exists in that cell's skeleton (ratio per image:
  1.31/1.67/2.24/1.90/2.29/1.94/1.88/1.60). Edge mode's total is the true
  owned skeleton length.

  Other parameters: `LACUNA_DILATION_PX=2`, `MIN_THREAD_OBJECT_PX2=8`.
  Outputs per image under `results/canaliculi/<image>/`: `verification.png`
  (all lacunae + canaliculi, one random-but-reproducible color per lacuna,
  drawn over the full-brightness original — `VIS_DIM_FACTOR=1.0`),
  `canaliculi_mask.png` and `skeleton.png` (new: the raw binary network
  mask and its skeleton, unannotated, so the segmentation can be checked
  directly rather than only through the colored tracing;
  `SAVE_MASK_PNG=True`), `measurements.xlsx`, `measurements.json`. Every
  filename is suffixed when a CLI switch overrides a default
  (`_<method>`, `_pre-<mode>`, `_count-<mode>`), so comparison runs never
  clobber the default outputs; all three comparison sets are currently
  regenerated against the present code for all 8 images. Border lacunae
  kept in the per-lacuna table but excluded from summary stats.

  **Sanity report** — a `--dir` run now ends with a pooled edge-length and
  node-degree report across every image processed (`--no-sanity` to skip).
  Modelled on OCY_get_network_params.m's `n.dist_edge` (cumulative edge
  length over the `link` structs), `n.hbz`/`n.mean_deg` (node degree
  excluding cells and endpoints) and `n.t_nodes` (tree-like nodes: degree
  3 with clustering coefficient 0). Reported for two populations — all
  skeleton edges/nodes, and only those the per-cell numbers are computed
  from — since a fragment not graph-connected to any lacuna inflates the
  first and never touches the second. Three literature-shape anchors are
  checked and printed OK/FLAG. They are *shape* checks only: with
  `PIXEL_SIZE_UM=None` no absolute length can be compared to a published
  micron figure.

### Exclusion of non-LCN structures (Phase 1, v1-raw)
- **`src/exclusion_mask.py` (new)** — removes vascular canals, canal edges
  and section boundaries from the canaliculi candidate mask before
  skeletonization. Wired into `canaliculi_v1.py` behind `EXCLUSION_MODE`
  (`"none"` = **default, current behaviour unchanged**, `"auto"`,
  `"manual"`, `"both"`; CLI `--exclusion`, outputs suffixed
  `_excl-<mode>`). Writes `exclusion.png` and records excluded area in
  `measurements.json`.
- **"auto" works on the RAW channel, not on skeleton geometry.** The
  obvious rule (flag long, straight, wide skeleton components) was tested
  in Phase 0(d) and flagged nothing across 6471 components from all 8 WT
  images: `canaliculi_v1`'s top-hat deletes anything broader than
  2·`TOPHAT_RADIUS_PX`+1 px, so a broad structure never reaches the
  canaliculi mask as a broad object. Before the top-hat it is plainly
  detectable — the 542_z06 structure is one 27496 px² object spanning 63%
  of the image height.
- **Shape gate** (both required, and on the 8 WT images they select the
  same 5 objects): span ≥ `EXCLUSION_MIN_SPAN_FRACTION=0.45` of an image
  dimension AND major axis ≥ `EXCLUSION_MIN_MAJOR_AXIS_PX=420`. Derived
  from the pooled v2 lacuna distribution: the largest lacuna-scale object
  across all 8 images (kept **or** rejected, n=103) spans 0.23 of a
  dimension with a 210.6 px major axis. Observed spans sort as 0.80, 0.73,
  0.63, 0.62, 0.58, then 0.37, 0.35, 0.34 — a clean gap the cutoff sits
  inside.
- **Lacuna safety margin is absolute.** No pixel within
  `LACUNA_SAFETY_MARGIN_PX=50` of a lacuna-scale v2 object (kept or
  rejected) is ever excluded, by `"auto"` or by a hand-drawn mask. In Hyp
  mice, periosteocytic lesions are broad bright regions around lacunae and
  are what this thesis measures; a rule that removes broad bright regions
  would delete them preferentially in the mutant genotypes and bias the
  comparison toward the hypothesis. 50 px is an **initial value, not yet
  tuned** — it cannot be derived from WT images, which have no lesions to
  measure. Verified across all 8 images: **0 excluded pixels inside the
  margin**.
- **`src/report_exclusion.py` (new, read-only)** — per-image excluded
  area, flagged objects, the safety-margin violation count, and the
  inside-vs-outside density comparison below.

### Diagnostics (read-only, no pipeline effect)
- **`src/inspect_tif_metadata.py`** — checked all 8 WT `.tif` files for
  embedded pixel-size/resolution metadata. Result: none usable (7 of 8 have
  no resolution tags at all; the 1 that does has a generic 300 DPI /
  ~84.7 µm/px value that's implausible for confocal and almost certainly a
  software default, not a real calibration). `PIXEL_SIZE_UM` stays `None`.
- **`src/diagnose_canaliculi_mask.py`** — read-only, sizes the canalicular
  mask preprocessing. Reports the distance-transform half-width
  distribution inside the candidate mask (what the top-hat structuring
  element must be larger than and the Gaussian sigma must stay below) and
  mask area fraction / component count with and without a candidate
  top-hat radius. Used to pick `TOPHAT_RADIUS_PX`.
- **`src/diagnose_lacuna_splits.py`** — (a) finds lacunae watershed split
  into two pieces and scores how real the split is (saddle depth between
  the two distance-transform peaks vs. the peaks themselves); (b)
  `--attach-gaps`: for canaliculi_v1's graph method, the minimum
  node-to-lacuna gap actually available per lacuna, vs.
  `LACUNA_ATTACH_GAP_PX` -- used to find and size-fix the attachment-gap
  bug above.

## Known issues

1. **RESOLVED (as of this update): watershed over-splitting some elongated
   lacunae** (user-reported, seen in 542 WT 2_z06c1-2 — 3 lacunae each
   rendered as two colors/territories). Root cause: a single smoothly
   elongated lacuna can have two comparable-height distance-transform
   peaks with no real neck between them, so watershed still cuts it in
   two. Fix in v2: `merge_shallow_splits()` re-merges any group of
   substantial pieces from the same pre-watershed component whose pairwise
   saddle is shallow relative to both peaks (union-find over pairwise
   links, not just a simple pair check -- one of the 3 bad cases actually
   had 3 raw pieces, only 2 of which passed the later shape filters, which
   the first version of this fix missed). `MERGE_SADDLE_RATIO_MIN=0.35`,
   calibrated so all 3 user-confirmed-bad cases (ratio >= 0.364) merge
   while the one case that looks like a genuine two-lobe separation (ratio
   0.000, 682_z29c1-3 component 174) stays split. Verified via
   `src/diagnose_lacuna_splits.py --dir data/WT` (down to that single
   expected remaining split) and visually on `results/count/542_WT__2_z06c1-2/overlay.png`
   (every lacuna now one clean outline). `results/count/` and
   `results/canaliculi/` both regenerated against the fix. Net effect:
   542_z06c1-2 total count 20 -> 16 (4 fewer -- 3 confirmed pairs plus the
   3-piece case counted as an extra merge).
2. **RESOLVED (as of this update): canaliculi per-lacuna assignment was
   Euclidean-nearest (straight-line Voronoi), not real network ownership**
   — reworked to graph-connectivity (OCY-style) assignment; see above.
   Visually confirmed on 542_WT__2_z06c1-2 and 543-2 (both methods run,
   overlays compared side by side): the euclidean overlay fills the whole
   field edge-to-edge with straight-boundary territories; the graph
   overlay shows each cell's color following a real branching/dendritic
   pattern with visible unclaimed gaps between neighbors — the qualitative
   signature the fix was meant to produce.
   Found and fixed a real bug along the way: the initial
   `LACUNA_ATTACH_GAP_PX=5` guess left 28/98 lacunae (29%) across all 8
   images with no attachment point at all (0 canaliculi silently), while
   a few well-attached neighbors absorbed tips that should have been
   unreachable. The min-gap distribution across all 98 lacunae was smooth
   (2.24–11.18px, no natural break), so `LACUNA_ATTACH_GAP_PX=10` was
   chosen as a coverage target (97/98 attached) rather than a gap-based
   cutoff — see `src/diagnose_lacuna_splits.py --attach-gaps`.
   Also fixed: `total_signal_mask` now uses strict `>` instead of `>=`.
3. **PARTLY RESOLVED (as of this update): canaliculi counts were too
   high and the tracing did not follow the real threads.** Root cause was
   the network segmentation, not the counting: thresholding the raw
   channel turned ~3–5 px threads into ~6–10 px fused ribbons covering
   ~24% of the field, and skeletonizing a ribbon branches everywhere. The
   OCY-style top-hat preprocessing (see above) fixed that, and the graph
   cleanup removed the remaining crossing artifacts and length
   fragmentation. Per-image mean canaliculi/cell, path-counted, went
   26–73 → 8–22; under the new default (edge-counted, post-cleanup) it is
   13.6–42.3 with mean edge length 27.9–38.1 px.

   The sanity report's junction-quality anchor is independent evidence
   the segmentation change was the right one: with the old preprocessing
   only 74.0% of junctions are degree-3 and mean junction degree is
   3.348, with 9.6% of nodes degree-4+; with the top-hat preprocessing
   that is 91.8% degree-3, mean junction degree 3.084, 1.5% degree-4+.
   The fused-ribbon skeleton was manufacturing spurious high-order
   junctions.

   A side effect worth recording: with thread signal now surviving right
   up against the lacuna boundaries, `LACUNA_ATTACH_GAP_PX=10` has gone
   from sitting *inside* the min-gap distribution (max 11.18 px, 1/98
   lacunae unattached) to clearing it with room to spare — max min-gap is
   now 7.00 px (p50 2.24, p95 5.00) and **0/98 lacunae are unattached**
   (`diagnose_lacuna_splits.py --attach-gaps`).

   Still not validated against a ground-truth count, and no µm/px scale
   exists, so whether the absolute numbers are "right" is still open —
   see Pending validation.

4. **NEW / OPEN: the skeleton is fragmented — 82% of nodes are degree-1
   thread ends and each image has ~640–700 connected components.** This is
   the one sanity anchor that FLAGs, and it is the main remaining signal
   that the segmentation is not yet finished. Consequences: only ~2,400
   of ~11,500 skeleton edges (21%) are graph-connected to any lacuna and
   therefore countable at all; the rest are orphan fragments that no cell
   can own.

   Two contributions, not yet separated:
   - *Physically real.* These are 2D optical sections through a 3D
     network. A canaliculus that dives out of the focal plane genuinely
     ends in this slice. OCY never faced this — they worked on 3D stacks,
     which is also why their pipeline has no gap-bridging step to copy.
   - *Artifact.* Threads also drop below threshold in dim stretches and
     break where they should be continuous.

   Note the old fused-ribbon mask scored *better* on this one metric
   (59% degree-1) — but that connectivity was false, achieved by merging
   unrelated threads through blobs, which is exactly what the degree-3
   anchor above exposes. Not fixed here: bridging gaps (e.g. a directional
   closing along the local thread orientation, or a ridge-following
   linker) is a new method step beyond the four fixes in scope, and
   choosing a bridge length without ground truth risks re-introducing the
   false connectivity that was just removed. Flagged for a decision.

5. **OPEN (Phase 1): auto-exclusion is defensible but of limited value,
   and two Phase 0 claims turned out to be wrong.** `EXCLUSION_MODE` stays
   `"none"` pending review. Three findings:
   - *Flagged structures do not clearly inflate the canaliculi mask.*
     Canaliculi-mask density inside the flagged structure vs outside it,
     over the 5 images that have one: 1.13, 1.03, 0.85, 1.25, 1.43
     (skeleton density 1.27, 1.18, 0.97, 1.44, 1.48). Two of five are at
     or below 1. So excluding a flagged structure removes mask pixels at
     roughly the field's own density — largely real canaliculi — except in
     682_z29 and 682_z23, where there is a genuine ~1.4× excess.
   - *Phase 0(d)'s "the structure's thin edges survive the top-hat" was
     wrong.* Measured directly, canaliculi-mask density in rings outward
     from the 542_z06 structure is 0.70×, 0.96×, 1.09×, 1.01×, 1.01× the
     far-field baseline — at baseline from ~4 px out, with no elevated
     edge response to cover. `EXCLUSION_DILATION_PX` is therefore 4, not
     the larger margin that inference implied; a larger value would delete
     ordinary canaliculi.
   - *The safety margin makes "auto" nearly a no-op in lacuna-dense
     fields,* which is the correct trade but should be understood. Excluded
     fraction per image: 0.50%, 2.28%, 0%, 0%, 0%, 5.03%, 3.46%, 6.22%. In
     542_z06 the margin suppresses 29106 of 34365 flagged px² (85%), so
     only two slivers of the vertical structure are removed. Auto mode is
     effective mainly where a structure runs through lacuna-free ground
     (a field edge), not where it threads between cells.
   The three 543_* images have no flagged structure at all.

6. **The second RGB channel is NOT a usable exclusion source** (checked,
   as asked, before offering it). The green channel is empty (mean 0.7–1.0
   of 255). Blue correlates +0.34 to +0.49 with red, i.e. it largely
   mirrors it. Blue exceeds red on 0.00–0.15% of pixels, never forming a
   coherent region. Decisively, the blue/red **ratio** is not elevated on
   the flagged structures: lift 0.81, 0.80, 1.06, 0.92, 0.88 — four of
   five below 1 — and the high-ratio region overlaps the flagged structure
   by 0.9%. The purple appearance is constant blue bleed-through becoming
   visible where red is dim, not a distinct tissue marker. No switch was
   added. Evidence in `results/diagnostics/canaliculi_v2/_channel_evidence/`.

7. **Parallel edges are collapsed.** `nx.Graph` holds no parallel edges,
   so where two separate branches join the same pair of nodes (a small
   loop) only the shorter weight is kept, though both branches' pixels are
   recorded and still drawn. Affects 1.3% of branches across the 8 WT
   images. Noted rather than fixed — a `MultiGraph` would complicate every
   shortest-path step downstream for a ~1% effect.
8. **v1 (`count_lacunae.py`) and v2 disagree** and v1 is not being kept in
   sync with v2's fixes. Not deleted yet: v2's own loader function is
   imported from v1's file (`from count_lacunae import load_channel`), so
   removing v1 requires a small refactor first (move that loader to a
   shared module).
9. **KNOWN CASE, left as is (2026-09-29): thread-scale kept objects on
   flagged bands.** 542_z06 id 2 at (555,149) and 682_z23 id 2 at (363,7)
   pass every v2 filter but look like vascular-band wall or band-edge
   thread, not lacunae. Both are inside a flagged band, and they are the two
   thinnest kept objects (10.2 and 12.8 px). They are also the only kept
   objects losing more than 65% of their area to an opening with the
   top-hat disk (they keep 0.207 and 0.348, next is 0.681). Each adds 1 to
   its image's lacuna count and acts as a cell in the canaliculi graph.
   682_z23 id 2 touches the frame edge, so it is already out of the summary
   stats. To be raised with Dr. Murshed together with D4. Evidence:
   `reports/round3/finding2_542_z06_objects.md`.
10. **KNOWN CASE, left as is (2026-09-29): leaked lacuna outline.** 542_z06
    id 3 at (106,67) is a real lacuna whose v2 outline runs into the thick
    start of an attached canalicular loop. The count is right, but its area
    is inflated by about 30% and its solidity (0.527, 2nd lowest of 98)
    describes body plus tail. Same report as 9.
11. **KNOWN CASE, left as is (2026-09-29): unfilled hole in a kept
    lacuna.** 542_z06 id 12 at (783,581) has an enclosed 146 px^2 hole, a
    real dim oval in the raw image, left open because v2 fills holes of
    20 px^2 or less only. It is the only such hole in the 98 kept lacunae
    (the other 70 raw-cut holes are at most 10 px^2). Area is understated by
    4.3% and solidity reads 0.829 instead of 0.865. No canaliculi effect.
    No hole rule is built: any rule is to be designed together with the POL
    measurement plan (finding 6) before it runs on Hyp fields. Evidence:
    `reports/round3/finding3_542_z06_hole.md`.

## Output reorganization, 2026-09-28

`src/reorganize_outputs.py` (move-only, idempotent, aborts before touching
anything if a destination exists) moved 65 files into a layout where the
CURRENT DEFAULT result sits at the top of each folder and everything else
sits one level down: `results/count/` -> `results/lacunae/`,
`results/count_v3_candidate/` -> `results/candidates/lacunae_v3/`,
`results/diagnostics/canaliculi_v2/` split into `diagnostics/phase0/` and
`diagnostics/phase1/`, text reports to `reports/phase0_1/`, planning notes
to `docs/`. Output paths are now constants in `config.py`
(`CANALICULI_DIR`, `LACUNAE_DIR`, `CANDIDATES_DIR`, `DIAGNOSTICS_DIR`,
`REPORTS_DIR`, `DOCS_DIR`); no script hard-codes one.

**EXCEPTION TO THE "do not modify segment_lacunae_v2.py" RULE.** One line
in that file was changed, with explicit approval:

    COUNT_DIR = config.RESULTS_DIR / "count"   ->   COUNT_DIR = config.LACUNAE_DIR

That is a PATH CONSTANT ONLY. No segmentation, watershed, merge, filter or
measurement logic was touched, and the module's behaviour and numbers are
unchanged — only where it writes. Without it the next v2 run would have
recreated `results/count/` and undone the reorganization.

**RESOLVED 2026-09-28.** The stale docstring was then fixed with explicit
approval: two comment/docstring lines in that file now say
`results/lacunae/` instead of `results/count/`. Verified comment-only by
parsing the file before and after, stripping every docstring, and
confirming the two ASTs are identical -- so no statement, expression or
constant in the module changed.

Verified after the move: 543-2 canaliculi 62.33 / 27.41 (unchanged), and
v2 lacunae now write to `results/lacunae/543-2`.

## Fixes round 2, 2026-09-28 (branch `canaliculi-v2-fixes`)

Full write-up: `reports/round2/fixes_round2.md`. Steps 1-2 changed
defaults; Steps 3-4 added switches that stay OFF; Step 5 was measured and
deliberately not built (see DECISIONS_NEEDED.md D7).

### Step 1 (done) — Phase 2 setting adopted as default
`THRESHOLD_MODE="hysteresis"`, `HYSTERESIS_LOW_FRACTION=0.75`,
`GAP_BRIDGING=True` are now the DEFAULTS, on the Phase 2 guard comparison
plus a visual check of the crops confirming the added connections follow
real dim threads.

**Reference check for 543-2 has therefore CHANGED:**

| | canaliculi/cell | mean edge length px | bridges |
| --- | --- | --- | --- |
| old default (to 2026-09-28) | 37.00 | 29.43 | 0 |
| **new default (from 2026-09-28)** | **62.33** | **27.41** | **21** |

Use **62.33 / 27.41** as the regression check from now on. The old
`multiotsu_low` path is still available via `--threshold-mode
multiotsu_low` and `GAP_BRIDGING` via `--no-gap-bridging` (added
2026-09-29; before that, omitting `--gap-bridging` still bridged), so the
old numbers remain reproducible: 543-2 gives 37.00 / 29.43 / 0 bridges.

Note the edge count rose 37.00 -> 62.33 (+68%). That is expected and is
exactly why Phase 4 recommended against edge count as a primary outcome:
it is the most segmentation-sensitive metric measured (+77.9% pooled). The
per-field metrics and roots/cell moved by ~11-13% over the same change.
`HYSTERESIS_LOW_FRACTION=0.75` remains the weakest-provenance number in
the default set -- one value tried after one failure, not a sweep.

### Steps 2-5 (done, 2026-09-28)
- **Step 2** `BLOCK_GROWTH_IN_FLAGGED=True` (DEFAULT): inside a flagged
  non-LCN structure, hysteresis keeps only already-strict pixels and no
  gap bridge may start, end or cross. Deletes nothing. Skeleton px inside
  flagged dropped 11-18% per affected image; outside unchanged to within
  2-4 px of ~33,000.
- **Step 3** `src/segment_lacunae_hybrid.py`, `LACUNA_SOURCE="hybrid"`
  (NOT default): v2 plus v3-only objects passing intensity, not-flagged
  and >=4-roots gates. Adds 2 objects over 8 images; **(230,300) in
  542_z06 is recovered**. Gate (a) decided every verdict, so gate (c)
  never bound on WT data.
- **Step 4** `src/merge_adjacent_lacunae.py`, `MERGE_ADJACENT_PAIRS`
  (NOT default): merges lacuna pieces split by a thresholding break.
  Exactly one pair exists across all 8 images (682_z29, 13 -> 12).
  Deliberately does NOT use the saddle ratio, which misreads a
  disconnection as a deep neck. `MERGE_SADDLE_RATIO_MIN` untouched.
- **Step 5** measured only. 1 of 86 interior lacunae has <3 roots, and it
  is NOT in a dim region (local raw 1.080x the image median).
  `tophat_localnorm` deliberately not built -- see DECISIONS_NEEDED.md D7.

## Round 3 housekeeping, 2026-09-29 (branch `canaliculi-v2-fixes`)

- **Hybrid roots override OFF** (`OVERRIDE_ON_ROOTS = False`), per D9.
  Hybrid adds 2 objects over 8 WT images, both in 542_z06: (230,303) and
  (224,351). With the override on it added 22.
- **Stale default outputs regenerated.** `results/canaliculi/<image>/` for
  7 of 8 images still held output from 2026-09-22, before hysteresis,
  bridging and block-growth existed. Only 543-2 had been re-run. All 8 now
  reflect the current defaults. Mean edge count per cell changed, for
  example, 542_z06 20.15 to 30.85, 543_3 23.78 to 47.11, 682_z29 13.55 to
  26.18. Any figure read from those folders before this date for those 7
  images came from the old pipeline.
- **`--no-gap-bridging` added.** The old default is reproducible again.
- 543-2 reference check after each commit: 62.33 / 27.41 / 21 bridges.

## Overnight autonomous run, 2026-09-24

Branch `canaliculi-v2-fixes`. **No default switch value was changed.** The
543-2 default check (37.00 canaliculi/cell, 29.43 px mean edge length) was
re-run after every phase and held throughout.

### Phase 2 (done, 2026-09-24 ~16:15) — fragmentation settings
New NON-DEFAULT switches in `canaliculi_v1.py`: `PREPROCESS_MODE` gains
`"ridge"` and `"tophat+ridge"` (`RIDGE_FILTER="sato"`,
`RIDGE_SIGMAS_PX=(1,2,3,4)` spanning the measured canalicular half-width
range); `THRESHOLD_MODE` = `"multiotsu_low"` (default) or `"hysteresis"`
(`HYSTERESIS_LOW_FRACTION`, both cuts derived per image from its own
histogram); `GAP_BRIDGING` (default False) implemented in the new
`src/gap_bridging.py`, with all three limits taken from the Phase 0(c)
distributions.

Eight settings x 8 images. Guards G1 (length > 1.20x) and G2 (loops >
max(1.5x, +50)) were fixed in writing before running — see
DECISIONS_NEEDED.md D0. **Five settings failed a guard, three passed.** The
guards mattered: `ridge+hyst` scores best on every secondary readout
(owned fraction 0.976, 11.2 components per 10k) while fusing the field into
single objects (loops 13 to 504; longest component 708 to 36,051 px in
542_z06). Recommendation and full table in DECISIONS_NEEDED.md D1; nothing
applied.

### Phase 3 (done, 2026-09-24 ~18:10) — lacuna-side candidate
`src/segment_lacunae_v3_candidate.py` (NEW, non-default) detects lacunae by
BREADTH (morphological opening of the raw channel, r=12) instead of
brightness, importing v2's watershed/merge/filters unchanged so the
comparison isolates detection. `LACUNA_SOURCE` switch added, default
`"v2"`. `segment_lacunae_v2.py` untouched; `TEST_MIN_SOLIDITY` untouched.
The (230,300) rejection is explained (a thin CURVED body, aspect 5.90 —
an erosion test rules out attached roots). v3 recovers it at solidity
0.952. v3 finds essentially all v2 objects plus 5–29 per image, but those
extras are half as bright (mean intensity p50 0.378 vs 0.827) and include
the vascular canal. See DECISIONS_NEEDED.md D3, D4.

### Phase 4 (done, 2026-09-24 ~19:40) — robust measurements
Per-field metrics (`field_metrics`) now in a `"field"` sheet of
measurements.xlsx and a `"field"` block in the JSON, plus in the sanity
report. `COUNT_MODE="roots"` added (non-default): one canaliculus = one
thread leaving the lacuna surface, attachment points merged below
`ROOT_MERGE_DIST_PX=8`.

**Key result — which outcomes survive a change of segmentation.** Pooled
over 8 WT images, default vs the Phase 2 recommendation: canalicular
length density +13.3%, median component length +8.1%, **roots/cell
+11.2%**, but **edge count/cell +77.9%**. An outcome that swings 78% on an
unvalidated preprocessing choice cannot carry a genotype comparison. See
DECISIONS_NEEDED.md D5.

## Planned next

- **Phase 2 must be judged on the guard metrics, not on owned fraction.**
  Phase 0(c) found that the angle between a thread's local direction and
  the vector to its nearest different component is only mildly peaked
  toward 0 degrees (21% under 20 deg, 8.5% above 100 deg), so many nearest
  neighbours are PARALLEL threads, not continuations of the same one.
  Hysteresis thresholding and gap bridging will both raise the owned
  length fraction by fusing neighbouring threads, which looks like success
  and is not. Judge them primarily on total skeleton length (must not jump
  sharply) and on the number of loops/cycles in the skeleton graph (must
  not jump), with owned fraction as a secondary readout only.

## Pending validation

- **Nothing here has been checked against Mahmoud's ImageJ ground-truth
  counts.** All thresholds/cutoffs so far (`TEST_MIN_AREA_PX2`,
  `MERGE_SADDLE_RATIO_MIN`, canaliculi parameters, etc.) were derived from
  looking at the data's own distributions/geometry, not from matching a
  known-correct count. This is the next real gate before anything here is
  "final."
- `PIXEL_SIZE_UM` is `None` (confirmed no usable calibration exists in the
  files) — everything is in pixel units. Getting a real µm/px value
  requires the confocal acquisition record, not the image files.
- None of v2's or canaliculi_v1's parameters have been promoted into
  `config.py` yet — by design, until validated. That includes every
  parameter added in this update (`PREPROCESS_MODE`, `TOPHAT_RADIUS_PX`,
  `SMOOTH_SIGMA_PX`, `BACKGROUND_MODE_SUBTRACT`, `COUNT_MODE`,
  `MIN_INTERNAL_EDGE_LEN_PX`, `GRAPH_CLEANUP_MAX_ITER`, the `SANITY_*`
  anchors), all of which are file-level constants in `canaliculi_v1.py`.
- **The sanity report is not validation.** It checks the *shape* of the
  edge-length and node-degree distributions against what a real LCN
  should look like (mostly short canaliculi, mostly 3-way branch points).
  Passing those anchors says the network is structurally plausible; it
  says nothing about whether the counts match Mahmoud's ImageJ numbers.
