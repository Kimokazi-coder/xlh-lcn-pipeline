# POL, phase 1: the definition

**Pre-validation.** 2026-10-29. Written from [FINDINGS.md](FINDINGS.md), which found that
these images show no separate POL zone: no dark ring, no distinct halo, no step inside the
body, only a smooth fall from the body to the bone background, about 2.3 um wide in WT.
So what is defined here is a **POL proxy**, the bright body plus the surround that stays
above the bone background, and every output calls it that. In WT this surround is optical
glow, so the WT value is the baseline for every comparison, not zero.

Every rule is the same for every image and every group, is written in micrometres
(0.13 um/px, `config.PIXEL_SIZE_UM_ACQUIRED`) and was chosen on no image. Nothing is traced
by hand, nothing models the optics, and no AI judge or API is used.

## Inputs, all read from existing outputs

- The raw red channel, 0 to 1 (`lacunae.load_channel`).
- The lacuna label image, `results/<group>/<label>/1_lacunae/<label>_lacuna_labels.png`:
  the kept lacunae, ids 1 to N, exactly as the lacuna stage outlined them. The lacuna stage
  is not run again and not changed.
- The detection record of the same folder, for the lacunae with no shape measure (classes
  `dim` and `out_of_focus`).
- The vascular mask of the network stage,
  `results/<group>/<label>/2_canaliculi/<label>_canaliculi_vascular_mask.png`.

## Inner boundary: the body

The lacuna's own region of the label image, unchanged. Body area is its pixel count times
0.0169 um2. The images cannot separate the cell from the lacunar space or from a lesion that
takes up the stain (FINDINGS, item 4), so "body" means the bright lacuna as detected.
Lacunae of the classes `dim` and `out_of_focus` carry no area measure anywhere in the
pipeline, because their edge is blur, so they get no POL measure either; they are counted.

## Outer boundary: where the surround reaches the bone background

Per lacuna:

1. **Territory.** Every pixel belongs to the lacuna whose body is nearest to it. A lacuna's
   surround is looked for in its own territory only, so two surrounds can never claim the
   same pixel.
2. **Bands and sectors.** A pixel of the territory is placed by its distance from the body
   edge, in bands 1 px (0.13 um) wide, and by its angle about the body centroid, in
   **8 sectors of 45 degrees**. Each sector is one radial profile from the centroid.
3. **Profile.** In each sector, at each band, the median raw red of the usable pixels of that
   band and of the band on each side (a slab 3 bands, 0.39 um, deep). Usable means inside the
   frame, in the territory, outside every body and outside the vascular mask. The median,
   and sectors this wide, so that a canaliculus crossing or running along the sector cannot
   carry the profile by itself: a 45 degree sector is wide enough that one thread (about
   6 px wide) covers well under half of a band at the distances where the profile ends.
   Three bands is the smoothing the glow profile already uses
   (`canaliculi.GLOW_PROFILE_SMOOTH`), so one dark or bright band cannot end a profile.
4. **Bone background.** The median raw red in the ring **70 to 90 px (9.1 to 11.7 um)** from
   the body edge, every body and the vascular mask left out: the lacuna's own surroundings,
   beyond the widest surround allowed (step 6). The same ring the glow zone uses.
5. **Surface.** The median raw red of the territory pixels within 1.5 px of the body edge.
6. **The boundary.** In each sector, the surround ends at the first band whose smoothed
   median has fallen to background + **0.10** x (surface minus background), that is to a
   tenth of the surround's height above the bone. Its width in that sector is the distance
   of the last band above that level. 0.10 is `config.GLOW_PROFILE_FRACTION`, the pipeline's
   existing definition of where a glow ends, so there is one definition and not two.
   **Maximum plausible halo width: 8 um (62 px) from the body edge**, the cap the glow zone
   already uses (`config.GLOW_ZONE_MAX_UM`). It is a plausibility bound, not a measured POL
   size; a sector still above the level at 8 um gives no answer. The halo radius of the
   brief is measured from the body edge and not from the centroid, because bodies differ
   in size by a factor of ten.
7. **A sector that gives no answer.** A sector stops without an answer when its slab holds
   fewer than 5 usable pixels while part of it is blocked (outside the frame, in another
   lacuna's territory, or in the vascular mask; the reason recorded is whichever blocks the
   most pixels), or when it reaches 8 um still above the level. In such a sector the outer
   boundary is drawn as far as could be seen: to 8 um, clipped to the territory, the frame
   and the vascular mask. A lacuna with too few answers is flagged (below).
8. **Outer region** = body plus, in each sector, the territory pixels out to that sector's
   width. Outer area is its pixel count times 0.0169 um2.

## Measures, per lacuna

- body area (um2)
- lacuna plus POL outer area (um2)
- POL area = outer minus body (um2), and POL ratio = outer / body
- halo width: median, mean and max over the sectors that answered (um), and how many of the
  8 answered
- surface, background and level values, for checking

## Flags: unreliable

A lacuna is unreliable if any of these holds; the reasons are listed per lacuna.

- **edge**: the body touches the frame, a sector stopped at the frame, or the outer region
  reaches the frame.
- **vessel**: any pixel of the vascular mask lies within 8 um of the body edge. Soft tissue
  is flagged only where the vascular mask covers it; there is no separate soft tissue rule.
- **neighbour**: the outer region touches the outer region or the body of another lacuna, so
  the two surrounds meet with no bone background between them. Territories keep two outer
  regions from overlapping, so touching is what an overlap becomes here.
- **incomplete**: fewer than half of the 8 sectors answered, so the median width is not
  measured. This includes a lacuna with no level at all, because the band within 1.5 px of
  its body or the background ring holds fewer than 5 usable pixels (the body is walled in by
  the vascular mask, the frame or its neighbours).
- **no contrast**: the surface is not above the background, so there is no surround to
  measure.

## Per image

Counts (all lacunae, no shape class, flagged, measured) and the fraction flagged among the
lacunae with a shape measure; the mean and the median of each measure over the measured
lacunae (shape measure and no flag). Flagged lacunae are listed with their values but are
not in the means.

## Values and where they come from

None is fitted to any image; none is validated.

| value | what | source |
| - | - | - |
| 0.13 um/px | pixel size | acquisition record (`config.PIXEL_SIZE_UM_ACQUIRED`) |
| 8 sectors of 45 degrees | angular resolution of the profile | chosen: wide enough that one thread is a minority of a band, enough sectors for the two ends, two sides and four diagonals of an elongated lacuna |
| 1 px bands, 3 band slab | radial resolution and smoothing | the glow profile's own (`canaliculi.GLOW_PROFILE_SMOOTH`) |
| 70 to 90 px | background ring | the glow zone's own (`canaliculi.GLOW_BACKGROUND_BAND_PX`) |
| 1.5 px | surface band | the glow zone's own rule (`canaliculi.glow_extent_px`) |
| 0.10 | level, fraction of the height above background | `config.GLOW_PROFILE_FRACTION` |
| 8 um | maximum halo width | `config.GLOW_ZONE_MAX_UM` |
| 5 pixels | fewest usable pixels a slab median is taken over | guessed |
| half of the sectors | fewest answers for a measured lacuna | the median width needs half the sectors to answer |

## What this definition cannot do

It cannot tell a lesion from glow, staining, focus or brightness: in WT, which has no
lesions, the surround is about 2.3 um wide (FINDINGS, item 2). A lesion that takes up the
stain is inside the body, not the surround. The group comparison of the outer area and the
POL ratio is therefore a comparison of "bright lacuna plus glow", described only, and not a
measurement of POLs.
