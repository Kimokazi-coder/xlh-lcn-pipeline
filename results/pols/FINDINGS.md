# POL, phase 0: what the images show

**Pre-validation.** A look only: no rule was set and nothing in `src/` changed in this
phase. 2026-10-29. Groups WT, WT_HP, Hyp_RD, Hyp_HP; there are no Hyp;Enpp1 images.

## What was looked at

All files are in [`phase0_look/`](phase0_look/).

- `contact_<group>.png`: every field of every group, red channel on a fixed 0 to 1 window,
  kept lacunae outlined green, the network stage's vascular mask outlined magenta.
- `crops_<group>_<label>.png`: 10 fields (WT 543-2 and 542_z18; Hyp_RD 535_z13, 536_z08,
  I534_z19, I534_z11; Hyp_HP 548_z14, 699_z20, 701_z19, 701_z36). Per field, five interior
  lacunae that carry a shape measure, picked by area rank (10th, 30th, 50th, 70th and 90th
  percentile), each a 128 px crop at 4x nearest-neighbour zoom in three panels (fixed window
  0 to 1; window stretched on the non-body pixels of the crop; body outline with rings at
  1, 2, 4 and 6 um) and its radial profile: the median raw red in each 1 px (0.13 um) band of
  distance from the body edge, other bodies left out, with the quartiles shaded. The
  numbers are in `phase0_profiles.csv` (50 lacunae).
- `phase0_groupwide_profiles.csv`: the same profile for every interior lacuna with a shape
  measure in all 35 fields (563 lacunae), with the local background (median of the band 70
  to 90 px from the body, bodies and vascular mask left out) and the distance at which the
  profile has fallen to 50, 25 and 10% of its height above that background.

These were made by a scratch script outside the repository, because this phase allowed no
code change. Phase 2 moves the same code into the repository so that they can be remade.

## What is there

1. **No dark ring.** No group shows a dim or dark ring between the bright body and the bone.
   The profile falls from the body edge to the background and stays there. A dip below the
   background of more than a tenth of the profile's height occurs in 0 to 8% of lacunae per
   group (WT 2.3%, WT_HP 0%, Hyp_RD 8.0%, Hyp_HP 4.3%), at noise level, and the median dip is
   above the background in every group.
2. **No separate bright halo either.** Around every body, in every group, there is one smooth
   fall from the body edge to the bone background. Its width, to 10% of its height above the
   local background (the convention of the existing glow zone, `config.GLOW_PROFILE_FRACTION`),
   median per group: WT 2.34 um (IQR 1.95 to 2.76), WT_HP 2.60, Hyp_RD 1.95, Hyp_HP 3.25.
   Hyp_RD is narrower than WT. WT has no lesions, so a "return to background" boundary already
   lies about 2.3 um out in normal bone: that zone is the optical glow of a bright object in a
   confocal section, not a lesion.
3. **A shoulder in a minority of Hyp lacunae.** A few Hyp lacunae show a zone above the
   background before the fall ends: 699_z20 #5 (a saturated core, a grey shoulder near 0.47 out
   to about 2 um, background by 5 um), and 535_z13 #9, #20 and #23 (a plateau about 0.05 above
   the background out to 6 to 7 um). These are the only halo-like zones seen. In 536, I534 and
   548 the fall is as short as in WT.
4. **No step inside the body.** 25 to 67% of bodies per group have more than 5% saturated
   pixels, so nothing inside them can be told apart. Every one of the others is brightest in
   its core (core median over rim median, per lacuna, 0.91 to 1.69, none below 0.9): a solid blurred object, not a
   bright rim around a dim cell. The existing mask cannot be split into a cell and a zone
   around it.
5. **Where a lesion could be.** If perilacunar matrix with less mineral takes up the stain, it
   is as bright as the lacuna and lies inside the body mask (the brightest multi-Otsu class);
   if it does not, it is as dark as bone. Either way these images hold two levels and not
   three: body and bone, with the glow between them.
6. **What does differ in Hyp.** Hyp lacunae are irregular and ragged, with thick processes,
   often saturated, and packed densely (15 to 50 kept per field against 11 to 19 in WT). An
   enlarged irregular body is consistent with a lesion, but the image cannot separate the
   lesion from the lacuna. The median body area is not larger in Hyp here (WT 36.7 um2, WT_HP
   29.4, Hyp_RD 33.6, Hyp_HP 18.5 um2 over interior lacunae with a shape measure), because the
   Hyp fields also hold many small kept objects.

**Is there a clear intensity step between cell body, halo and bone?** No. There is one step,
body to bone, softened by about 2 to 3 um of glow in every group.

## Unusable fields

From the contact sheets. A visual judgment, not a rule; nothing is excluded automatically.

| group | fields | what is wrong | usable part |
| - | - | - | - |
| Hyp_HP | 701_z19, 701_z26, 701_z36 | no recognisable lamellar bone: mottled grey tissue around a large cavity holding round cells; the "lacunae" are brighter blobs in it (body median about 0.5, never saturated); the vascular mask lies within 8 um of 47 to 96% of them | none |
| Hyp_HP | 699_z11, 699_z20, 699_z25 | top third saturated bright tissue, a dark horizontal crack, a bright surface along the bottom | the middle band |
| Hyp_RD | 535_z13, 535_z20, 535_z27 | grey soft tissue patch at top right (no network), a bright diagonal band, a dark wavy band, bright bottom edge | the centre |
| Hyp_RD | I534_z11, I534_z19, I534_z25 | saturated bands along top and bottom; bodies densely packed and often saturated | the centre |
| Hyp_RD | 536_z03, 536_z08, 536_z15 | saturated surface along the right edge | most of the field; the cleanest Hyp fields |
| Hyp_HP | 548_z08, 548_z14, 548_z20 | 548_z20 has a vascular band across it | most of the field |
| WT_HP | 872_z03, 872_z04, 872_z06 | saturated band along the bottom, black outside the bone at the top | the band between |
| WT_HP | 876_z76, 876_z82, 876_z89 | dim, low contrast over the whole field | usable, faint |
| WT | 542_z06, 542_z18, 682_z08, 682_z23, 682_z29 | a vertical band (542) or a saturated top edge (682) | most of the field |

## Plain answer

**POLs cannot be told apart as a separate zone in these images.** There is no dark ring, no
separate halo and no step inside the body. What can be measured is a proxy: (a) the body
area, which in Hyp may already contain a lesion, and (b) the width of the surround above the
bone background, which in WT is optical glow. A Hyp against WT difference in (b) could come
from a lesion, from staining, focus or brightness, and nothing in these images says which.
Phase 1 defines that proxy, as the brief asks, and every output names it as a proxy.
