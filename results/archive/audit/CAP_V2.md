# Cap v2: the structure rule replaces the 300 um2 band rule (2026-11-06)

**Pre-validation.** Finishing brief of 2026-11-06, phase 2. Every class below
is an AI reviewer's single blind look at a crop (the `image-reviewer`
subagent, Sonnet, Read, Glob and Grep only), on the 27 development images, in
DEV mode. No held-out image or output was opened, printed or summarized.

## Why

The band rule of `method-freeze-v1` (config section g8) dropped every object
whose region of the lacuna mask is larger than 300 um2. That is in effect a
largest lacuna of 300 um2, about 8 WT median lacunae, so an enlarged or merged
lacunar space larger than that, which is exactly what a periosteocytic lesion
can look like, was dropped too. The brief: keep large objects as lacunae
unless a general rule shows they are band, saturated border or tissue, and
flag merged clusters instead of removing them.

## The new rule (config section g9)

An image's **excluded region** is the union of

- **saturated border regions**: saturated pixels (255, after a 1 um closing)
  forming a connected region that touches the frame and covers at least
  100 um2, the blooming at a tissue border (the top of the 699 fields);
- **very large structures**: connected regions of the lacuna mask (the top
  class of the cut) of at least 500 um2, holes filled, such as a vascular
  canal, a resorption feature, the bone surface, the medium or soft tissue
  (the centre of 701_z26);

both grown by a 3 um margin, the halo of their glow. A kept object with more
than half its area in the excluded region is dropped. Every other object is
kept, whatever its size. `STRUCTURE_RULE = False` turns it off; the old rule
is still there (`BAND_BLOB_RULE = True` restores it exactly). Where each
number comes from is in `config.py`, section g9; in short:

| setting | value | from the development images |
| - | - | - |
| saturated border region, least area | 100 um2 | the largest frame-touching saturated region inside a lacuna cut by the frame is 67.6 um2; band and bloom regions reach 105 to 1104 um2 |
| closing of the saturated pixels | 1 um | as in the cap audit |
| very large structure, least area | 500 um2 | every mask region of 657 um2 or more is band, bloom, medium or tissue (11 regions); the largest holding an accepted object is 253 um2 |
| margin | 3 um | by 3 um the brightness has fallen at least 79% of the way from a saturated edge to its level 10 to 15 um out, on all 8 images that have one |
| share of an object in the region | over 0.5 | an object counts where most of it lies; an initial value |

**The cluster flag** (a flag, never a filter): a kept lacuna is flagged
`cluster` when shaving 1.5 um off its outline leaves two or more cores of at
least 3 um2 each, two lacuna bodies joined by a neck narrower than 3 um. It is
the column `cluster` of the per-lacuna tables of `4_quantification/` and
`3_pols/`.

## Before and after

`python src/diagnostics.py cap-v2-audit` (measures and blind crops in
[`cap_v2/`](cap_v2/), table [`cap_v2.csv`](cap_v2.csv)) takes, on every
development image, the objects the filters keep with both rules off: every
one over 150 um2 (28), and every smaller one the new rule removes (10).
"Before" is the 300 um2 band rule, "after" the structure rule, each applied to
the same objects. `python src/diagnostics.py cap-v2-tally` joins the
reviewer's classes ([`reviews/cap_v2_a.md`](reviews/cap_v2_a.md),
[`reviews/cap_v2_b.md`](reviews/cap_v2_b.md)) and writes
[`cap_v2_tally.csv`](cap_v2_tally.csv). Kept correctly: kept and called a
lacuna; removed correctly: removed and called not a lacuna; wrong: the other
two cases; unsure: the reviewer was unsure.

Objects over 150 um2:

| group | n | before: kept correctly | removed correctly | wrong | unsure | after: kept correctly | removed correctly | wrong | unsure |
| - | - | - | - | - | - | - | - | - | - |
| WT | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 1 | 0 |
| WT_HP | 2 | 0 | 2 | 0 | 0 | 0 | 2 | 0 | 0 |
| Hyp_RD | 14 | 4 | 5 | 3 | 2 | 4 | 5 | 3 | 2 |
| Hyp_HP | 11 | 1 | 4 | 4 | 2 | 1 | 5 | 3 | 2 |
| all | 28 | 5 | 11 | 8 | 4 | 5 | 12 | 7 | 4 |

The 10 objects of 150 um2 or less that the new rule removes (the band rule
kept 7 of them and removed 3): before, 1 kept correctly, 3 removed correctly,
5 wrong, 1 unsure; after, 8 removed correctly, 1 wrong, 1 unsure.

**No real lacuna over 150 um2 is removed, before or after.** The five large
lacunae the reviewer accepted (Hyp_RD 535_z13c1-2 50, 535_z27c1-2 67 and 109,
I534_z11c1-2 93; Hyp_HP 548_hyp_HP_z14c1-2 69, 153 to 201 um2) are kept by
both rules. On these images no accepted lacuna is larger than 300 um2, so the
two rules agree on every real lacuna; the difference is what a larger lesion
would meet: the new rule has no size limit on an object outside a structure.

What changed, object by object:

- Removed now, kept before, called not a lacuna: Hyp_RD I534_z11c1-2 10 (a
  long saturated band); Hyp_HP 699_HYP_HP_z20c1-2 64 (a bright mass cut by the
  frame); and among the small ones the saturated tissue pieces
  536-63x_Hyp_RD_z03c1-2 104 and 105, 699_HYP_HP_z11c1-2 10, 699_HYP_HP_z20c1-2
  14 and WT_HP 872_wt_hp_z04 479. Also removed now: Hyp_RD I534_z25c1-2 34
  (unsure, a large mass cut by the frame).
- Kept now, removed before: Hyp_RD I534_z25c1-2 4 (181 um2, a saturated band
  at the frame). Its saturated part is in two regions of 58.6 and 57.6 um2,
  under the 100 um2 limit, and its mask region (304 um2) is under 500.
- **Removed now, wrongly:** Hyp_RD I534_z25c1-2 229, a 9.6 um2 "small dim body
  in a gap above the bright tissue", 73% inside the margin of a saturated
  border band. WT_HP 872_wt_hp_z06c1-2 170 (21.5 um2) is unsure.

## Still wrong after

All 7 wrong objects over 150 um2 are kept band or tissue pieces, and **all 7
touch the frame**: WT 682_z08 11 (a bloom at the frame whose saturated part,
94.8 um2, is just under the limit); Hyp_RD I534_z25c1-2 4, 535_z27c1-2 141,
536-63x_Hyp_RD_z03c1-2 121; Hyp_HP 699_HYP_HP_z11c1-2 135,
699_HYP_HP_z25c1-2 51, 701_z26c1-2 59. A lacuna touching the frame carries no
size measure (its area is cut), so they move the lacuna counts and the network
ownership, not any lacunar size or POL number. Six of the seven were kept by
the 300 um2 rule too. Unsure: Hyp_RD I534_z11c1-2 56 and I534_z25c1-2 34
(large masses at the frame, "maybe merged lacunae"), Hyp_HP 699_HYP_HP_z11c1-2
123 (an elongated streak) and 701_z26c1-2 54 (a blurred mass, likely tissue).

No saturation rule can catch the rest: 535_z27c1-2 141, 699_HYP_HP_z11c1-2 135
and 701_z26c1-2 59 hold little or no saturated pixel. No further rule was
added for them, so the test above is not fitted to its own objects.

## The cluster flag

4 of the 38 reviewed objects are flagged; the reviewer called 1 of them a
cluster (535_z27c1-2 67, "a large mass with two or three lobes"). The other 3
are band pieces at the frame (two removed, one kept). The reviewer called 2
objects clusters, and the flag finds 1 of them (it misses 535_z27c1-2 109, two
bodies joined by a wide neck); it was unsure for 4 more. So the flag is
rough: it finds lobes joined by a narrow neck only. It changes no number.

## Files

`cap_v2.csv`, `cap_v2_tally.csv`, `cap_v2/<group>/<image>_obj<N>.png` (left
the original, right the object outlined in cyan, 10 um bar),
`reviews/cap_v2_a.md` and `reviews/cap_v2_b.md`. The exploration that chose
the numbers ran from throwaway scripts in the git-ignored `.cache/explore/`.
