# Progress status

_Last updated: 2026-09-22. Everything below is v1-raw/v2-raw and pre-validation
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
  `results/count/<image>/`: `overlay.png`, `measurements.xlsx` (summary +
  per_lacuna sheets), `measurements.json`. Per-image summary stats
  (mean/median/SD of area, axis lengths, aspect_ratio, eccentricity,
  solidity) computed over interior (non-border) lacunae only.

### Canaliculi (per-lacuna)
- **`src/canaliculi_v1.py` (v1-raw)** — builds on v2's lacuna segmentation
  (imported, not modified). Canalicular network = red signal strictly
  above the *lower* multi-Otsu cut, minus a buffer around lacuna bodies,
  despeckled by pixel count (not erosion), skeletonized.
  **Two assignment methods, `ASSIGNMENT_METHOD` ("graph" = default,
  "euclidean" = old, kept for comparison via `--method euclidean`):**
  - `"graph"` (OCY-style, Kollmannsberger et al.): the whole skeleton is
    one weighted graph; each lacuna is a virtual source node attached to
    skeleton nodes within `LACUNA_ATTACH_GAP_PX=10` of its body; a single
    multi-source shortest-path assigns every reachable node to whichever
    cell it's graph-connected to (not spatially nearest). Terminal spurs
    shorter than `PRUNE_SPUR_LEN_PX=4` are pruned first. Per cell,
    single-source Dijkstra finds every reachable, owned, degree-1 tip =
    one canaliculus; length = path distance from the root (first real
    node) to the tip.
  - `"euclidean"`: every skeleton pixel assigned to its nearest lacuna by
    Euclidean distance transform (Voronoi), no spur pruning; per-lacuna
    root-to-tip tree search (root = closest point to the lacuna;
    `MAX_ROOT_GAP_PX=15` cutoff).
  Other parameters: `LACUNA_DILATION_PX=2`, `MIN_THREAD_OBJECT_PX2=8`.
  Outputs per image under `results/canaliculi/<image>/`: `verification.png`
  (all lacunae + canaliculi, one random-but-reproducible color per lacuna,
  drawn over the full-brightness original — `VIS_DIM_FACTOR=1.0`),
  `measurements.xlsx`, `measurements.json` (all suffixed `_<method>` when
  `--method` overrides the default, so comparison runs never clobber the
  default outputs). Border lacunae kept in the per-lacuna table but
  excluded from summary stats.

### Diagnostics (read-only, no pipeline effect)
- **`src/inspect_tif_metadata.py`** — checked all 8 WT `.tif` files for
  embedded pixel-size/resolution metadata. Result: none usable (7 of 8 have
  no resolution tags at all; the 1 that does has a generic 300 DPI /
  ~84.7 µm/px value that's implausible for confocal and almost certainly a
  software default, not a real calibration). `PIXEL_SIZE_UM` stays `None`.
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
3. **Canaliculi counts are lower but still not in the hoped-for range.**
   Graph + spur-pruning (`PRUNE_SPUR_LEN_PX=4`) reduced mean
   canaliculi/cell from 30–160 (euclidean) to 26–73 (graph) across the 8
   images — a real reduction, and the bimodal/attachment-failure artifact
   is gone — but this is still well above "single digits to low tens,"
   which was the expected sanity-check range going into this fix. Not
   pushed further: `PRUNE_SPUR_LEN_PX` is per the original spec, and
   raising it further wasn't something I did unilaterally -- flagged for
   the user to decide (e.g. a larger prune length, chosen the same
   data-driven way as `LACUNA_ATTACH_GAP_PX`, would be the next lever).
4. **v1 (`count_lacunae.py`) and v2 disagree** and v1 is not being kept in
   sync with v2's fixes. Not deleted yet: v2's own loader function is
   imported from v1's file (`from count_lacunae import load_channel`), so
   removing v1 requires a small refactor first (move that loader to a
   shared module).

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
  `config.py` yet — by design, until validated.
