# Excluded regions (2026-11-06)

**Pre-validation.** Finishing brief of 2026-11-06, phase 3. Decided and
tested on the 27 development images only, in DEV mode. No held-out image or
output was opened.

## The rule

The excluded region of an image (config section g9, `lacunae.excluded_region`)
is the union of the saturated border regions (255 after a 1 um closing,
connected, touching the frame, at least 100 um2: the blooming at a tissue
border, as at the top of the 699 fields) and the very large structures
(connected regions of the lacuna mask of at least 500 um2, holes filled:
vascular canals, resorption features, the bone surface, medium or soft
tissue, as at the centre of 701_z26), grown by a 3 um margin. Regions are
masked, never whole images. The numbers and where each comes from are in
[`CAP_V2.md`](CAP_V2.md) and `config.py`, section g9.

**Every area measure uses the analysed area**, the image minus the excluded
region: in `src/quantification.py` the field measures (canalicular length
density, junction density, lacunae per area and the densities beside them)
leave out the skeleton, the junctions, the unattached threads and the
lacunae inside it; the quantification json records `excluded_area_px2` and
`analysed_field_area_px2`; `src/pols.py` divides the POL area by the analysed
area. With nothing excluded every number is as before.

## The pictures

One per image, `results/<group>/1_lacunae/<image>_excluded_region.png`: the
original, the excluded region shaded grey with a white edge, the kept lacunae
outlined green, the area and share in the header, a 10 um bar; beside it
`<image>_excluded_region_mask.png`, the region that quantification reads.

| group | development images | with an excluded region | excluded share of those |
| - | - | - | - |
| WT | 6 | 0 | none |
| WT_HP | 7 | 3 (872_wt_hp_z03, z04, z06) | 11.0, 13.6, 24.0% |
| Hyp_RD | 7 | 5 (536 z03, z08, z15; I534 z11, z25) | 1.6, 5.0, 5.4, 18.4, 12.2% |
| Hyp_HP | 7 | 4 (699 z11, z20, z25; 701_z26) | 15.4, 14.0, 12.8, 24.9% |

Summed over the development images of a group, the excluded area is 0 um2
(WT), 8,621 (WT_HP), 7,555 (Hyp_RD) and 11,906 um2 (Hyp_HP), against an
analysed area of 106,326, 115,426, 116,492 and 112,140 um2.

## The test

The reviewer ([`reviews/excluded_regions.md`](reviews/excluded_regions.md))
looked at the 12 pictures with an excluded region: on 11 everything under the
grey is non-lacunar structure; on 1 (I534_z11c1-2) it is "partly" right, one
compact body sits under the grey rim at the bottom left and is "mostly
outside, borderline". No other real lacuna lies under the grey.

**What the rule does not catch** (the reviewer's "missed"): bright bands that
are not saturated, along the bone surface (the top of 872_wt_hp_z04, z06 and
I534_z25c1-2), bright patches and masses in 536 and along the bottom of the
699 fields, and the diffuse soft tissue over the right and lower half of
701_z26c1-2. They stay outlined as pieces, as before; most touch the frame
(CAP_V2.md). A dark field outside the bone (the black top of the 872 fields)
is not excluded either, so the POL area per analysed area of such an image is
lowered by empty field.
