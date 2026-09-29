# Fixes round 2 — 2026-09-28

Branch `canaliculi-v2-fixes`. Everything is v-RAW, **pre-validation**, in
PIXEL units. Nothing has been checked against Mahmoud's ImageJ counts.

**The 543-2 reference check changed in Step 1** and held for every step
after it:

| | canaliculi/cell | mean edge length px | bridges |
|---|---|---|---|
| old default (to 2026-09-28) | 37.00 | 29.43 | 0 |
| **new default** | **62.33** | **27.41** | **21** |

---

## Step 1 — Phase 2 setting adopted as default

`THRESHOLD_MODE="hysteresis"`, `HYSTERESIS_LOW_FRACTION=0.75`,
`GAP_BRIDGING=True`.

Of the eight settings tested in Phase 2 this was the only one that both
passed the pre-declared guards (1.13× skeleton length against a 1.20×
limit, 2.13× loops against a max(1.5×, +50) limit) on tuning **and**
held-out sets, and cut components per 10,000 skeleton px from 225 to 169.

The edge count rose +68%. That is expected and is exactly why Phase 4
recommended against edge count as a primary outcome — it is the most
segmentation-sensitive metric measured (+77.9% pooled). Per-field metrics
and roots/cell moved 11–13% over the same change.

**Became default.** The old path stays reachable via
`--threshold-mode multiotsu_low --no-gap-bridging`. (Corrected
2026-09-29: this originally said "omitting `--gap-bridging`", which did
not turn bridging off. The `--no-gap-bridging` flag was added for this.)

`HYSTERESIS_LOW_FRACTION=0.75` remains the weakest-provenance number in the
default set: 0.5 was tried, failed both guards, 0.75 passed. One value
after one failure, not a sweep.

---

## Step 2 — no new connections along non-LCN structures

`BLOCK_GROWTH_IN_FLAGGED = True`. Inside a Phase 1 flagged structure (the
auto shape gate, taken *before* the lacuna safety margin), hysteresis may
keep only pixels already above the strict cut, and no gap bridge may start
in, end in, or cross the region.

Skeleton px inside flagged / outside flagged, blocking off → on:

| image | in flagged | outside flagged |
|---|---|---|
| 542_z06 | 1349 → **1194** | 33768 → 33770 |
| 542_z18 | 1625 → **1412** | 32917 → 32913 |
| 682_z08 | 2710 → **2239** | 33026 → 33028 |
| 682_z23 | 3221 → **2644** | 36521 → 36524 |
| 682_z29 | 3917 → **3407** | 34963 → 34961 |
| 543-2 | 0 → 0 | 45785 → 45785 |

The vertical segment in the x555_y500 crop is gone. Outside-flagged length
is unchanged to within 2–4 px out of ~33,000 (0.01%) — **not exactly
zero**: `skeletonize` is global, so removing pixels inside a region shifts
the medial axis by a pixel or two right at its boundary. 543-2, which has
no flagged structure, is bit-identical, which confirms there is no other
route by which this changes anything.

**Nothing is deleted** — every pixel the old default had is still present.
This only removes connections the *new* default would have added, which is
why it needs no exclusion justification and is independent of
`EXCLUSION_MODE` (still `"none"`).

**Became default.**

---

## Step 3 — hybrid lacuna detection

`src/segment_lacunae_hybrid.py`, `LACUNA_SOURCE="hybrid"`. Keeps every v2
lacuna; adds a v3-only object only if **all** of:

- **(a)** mean intensity ≥ 0.75 × *this image's* median v2 lacuna intensity
- **(b)** no overlap with a flagged structure
- **(c)** ≥ 4 canalicular roots attached

Both cutoffs come from non-overlapping measured distributions. Intensity,
relative to each object's own image: v2-kept (n=98) min **0.823**; v3-only
(n=122) p90 0.532, **max 0.783**. The populations do not overlap at all.
Roots: v2-kept interior (n=86) p10 = **4**, median 7.

**Result: 2 objects added across all 8 WT images, both in 542_z06.**
**(230,300) is recovered** — added at (230,303), relative intensity 0.783,
5 roots, with canaliculi visibly radiating from it in the crop.

Two qualifications the brief did not anticipate:

1. **Gate (a) decided every verdict.** In every image, the count failing
   (a) equals candidates minus additions. Test (c) — expected to be "the
   key discriminator" — never changed an outcome on WT data. It is a
   safeguard that did not bind here and may matter on Hyp fields, where
   lesions could raise the local intensity of haze. Kept, not removed.
2. **An added body is smaller than the lacuna really is** — 1241 px²
   against the 1698 px² v2 measured before rejecting it — because the r=12
   opening rounds off an elongated object. Hybrid **areas** for added
   objects understate; counts are the usable output.

**Stayed behind a switch.** `LACUNA_SOURCE="v2"` is still the default:
whether a partly-sectioned lacuna counts is the open question in
`docs/DECISIONS_NEEDED.md` D4, and it is not a coding decision.

---

## Step 4 — over-split lacunae

Searched all 8 images for pairs of v2-kept lacunae within 5 px. **Exactly
one exists:** 682_z29 labels 195+196, gap 1.0 px, union area 1649 px²,
solidity 0.773, aspect 5.01 — all inside the v2-kept range (area
445–9321, solidity 0.525–0.955, aspect 1.16–5.76). The crop shows one
continuous elongated lacuna split into two pieces meeting end to end.

`src/merge_adjacent_lacunae.py` merges it behind `MERGE_ADJACENT_PAIRS`
(**default False**). It merges exactly that one pair: 682_z29 count
13 → 12. No other image is affected. `MERGE_SADDLE_RATIO_MIN` untouched.

**The criterion is proximity plus union shape, not the saddle ratio**, and
the reason matters. `seg2.merge_shallow_splits` cannot catch this case at
all — it only compares pieces *within one pre-watershed component*, and
these two were never one component. And the saddle ratio actively misreads
it: this pair scores **0.000**, which reads as "deep neck, genuinely two
lobes, do not merge", but it is 0.000 *precisely because* the bodies are
1 px apart and disconnected, so the line between their peaks leaves the
mask. A disconnection and a deep neck are indistinguishable to that
measure and mean opposite things here. This is a thresholding break, not a
watershed over-split.

**Stayed behind a switch** — one object across the whole dataset is not
enough to move a default on.

---

## Step 5 — dim fields: measured, and deliberately not built

Step 5 was conditional (*"if they do [sit in locally dim regions], add..."*).
**The condition is not met**, so only part (a) was done.

| | n | local mask density (× image) | local raw signal (× image median) |
|---|---|---|---|
| < 3 roots | **1** | 0.392 | **1.080** |
| ≥ 3 roots | 85 | 0.779 | 1.287 |

- Only **1 of 86** interior lacunae (1.2%) has fewer than 3 roots. None has
  zero.
- **That one is not in a dim region** — local raw signal 1.080× the image
  median, i.e. normal. What is low is local *mask* density.
- Roots correlate with local mask density **+0.575**, with local raw signal
  only **+0.169**.
- Step 1 had already largely fixed this: 3 of 86 (3.5%) under the old
  default, 1 of 86 (1.2%) now. Median 7.0 roots either way.

**Not built.** `tophat_localnorm` makes dim regions threshold like bright
ones; the one remaining case is not dim, so it would not touch it. See
`docs/DECISIONS_NEEDED.md` D7 for the three conditions that would justify
revisiting.

---

## What became default, and what did not

| change | status |
|---|---|
| hysteresis + 0.75 + gap bridging | **DEFAULT** (Step 1) |
| `BLOCK_GROWTH_IN_FLAGGED` | **DEFAULT** (Step 2) |
| `LACUNA_SOURCE="hybrid"` | switch, default `"v2"` — D4 is a science decision |
| `MERGE_ADJACENT_PAIRS` | switch, default `False` — affects 1 object total |
| `tophat_localnorm` | not built — premise measured and rejected (D7) |
| `EXCLUSION_MODE` | unchanged `"none"` — D2 |
| `COUNT_MODE` | unchanged `"edge"` — but see D5, `"roots"` is the per-cell quantity |

---

## Images to look at, in order

1. `results/diagnostics/round2/step2/542_z06_x555_y500_block_off_vs_on.png`
   — blocking off | on | the flagged region. The vertical segment along the
   vascular band is what Step 2 removes.
2. `results/candidates/lacunae_hybrid/542_WT__2_z06c1-2/added_x230_y303.png`
   — the recovered (230,300) lacuna, raw | outlined. Canaliculi radiate
   from it, which is what test (c) checks.
3. `results/candidates/lacunae_hybrid/542_WT__2_z06c1-2/v2_vs_hybrid.png`
   — v2 green, additions cyan, **rejected candidates dim red** so the
   rejections can be eyeballed as easily as the acceptances.
4. `results/diagnostics/round2/step4/pair_682_z29c1-3_195_196.png`
   — the one adjacent pair, raw | the two pieces outlined.
5. `results/canaliculi/543-2/verification.png` — the current default
   output, for the reference numbers above.

## Decisions waiting

`docs/DECISIONS_NEEDED.md`, D0 to D9 (D8 and D9 were added after this
report was written). The largest is still **D4**: whether a
lacuna lying partly outside the focal plane counts. **D7** is new from this
round.
