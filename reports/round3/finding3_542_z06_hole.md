# Finding 3: the unfilled hole in a 542_z06 lacuna

2026-09-29. **Pre-validation, pixel units.** Read-only diagnostic; no default
or pipeline output changed. Numbers: `finding3_542_z06_hole.txt` (same
folder). Crop: `results/diagnostics/round3/finding3/542_WT__2_z06c1-2_id12_hole.png`
(raw | outline cyan, hole yellow | default skeleton, hole dim yellow).
Re-run with `src/inspect_lacuna_hole.py`.

## What it is

The lacuna is **542_z06 id 12 at (783,581)**, an elongated body of
3414 px². Its mask has one enclosed hole of **146 px²**, 4.1% of the filled
outline. It is the only kept lacuna in the 8 WT images whose final mask has
a hole.

**The hole is real signal, not a segmentation fault.** The raw panel shows
a distinct dim oval inside the bright body. Intensity inside the hole is
0.523 on average (max 0.643), against 0.945 for the body. All of it is
below v2's lacuna cut t_hi = 0.647 and all of it is above the background
cut t_lo = 0.273. So it is a mid-intensity region, the same class as the
canalicular mesh, enclosed by the lacuna. What it is biologically (for
example a less-stained nucleus, or a local dip in the section) is not
something this image can settle.

## Why v2 leaves it

v2's mask step fills only holes of 20 px² or less
(`remove_small_holes(area_threshold=20)` in `multiotsu_lacuna_mask`). The
hole is already 146 px² in the raw top-class cut, and it is unchanged by
the fill step, the r=1 opening and the watershed.

Across all 98 kept lacunae, the raw cut has 71 enclosed holes. 70 are
filled by that step: 61 of 1 px², 6 of 2, 2 of 3 and one of 10. The one
left open is this 146 px² hole. There is nothing between 10 and 146 px², so
the 20 px² limit sits in a wide gap and this is a clean single outlier, not
the tail of a distribution.

## What it changes downstream

| | as measured | hole filled |
|---|---|---|
| area px² | 3414 | 3560 (+4.3%) |
| solidity | 0.829 | 0.865 |

**Canaliculi: no effect.** The default canaliculi mask and skeleton have 0
pixels inside the hole. None of the lacuna's 13 roots
(`COUNT_MODE="roots"`, default graph) attach through a node inside it.

So the hole affects only this one lacuna's area and shape: area is
understated by 146 px², and solidity by 0.036.

## Options (none built, no default changed)

1. **Fill every hole fully enclosed by a kept lacuna**, behind a new v2
   switch, default off. A hole enclosed by the lacuna is inside the cavity
   whatever its brightness, so the outline, not the stain inside it,
   defines lacunar area. On the WT data this changes exactly one object, by
   the numbers above, and nothing in the canaliculi step. This is my
   recommendation. It is a v2 change, which has needed your explicit
   approval before.
2. Raise the 20 px² limit. The gap from 10 to 146 px² would allow it, but
   any fixed limit is arbitrary and could miss a larger hole in a Hyp
   field. Option 1 avoids choosing a number.
3. Record it as a known case and change nothing, as for finding 2.

**Why this matters later.** Nothing here has been seen on a Hyp field. How
periosteocytic lesions change the inside and the surround of a lacuna in
these images is not yet known, so any hole rule should be checked against
the POL measurement plan (finding 6) before it is adopted.
