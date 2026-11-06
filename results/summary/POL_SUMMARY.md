# POL summary: lacunar size, all four groups

**Superseded numbers.** This text and its table were written on 2026-11-05
before the review loop, with the lacuna stage of commit 0b0be38. The lacuna
stage changed after it (tag `method-freeze-v1`, `results/archive/REVIEW_LOOP.md`)
and `pols_lacunar_size_by_group.csv` was made again with the frozen method on
every image; the numbers quoted below were not updated and are those of the
old method. The problems listed under "Problems found" are the ones the loop
worked on.

**This is lacunar size, not a measured lesion boundary.** It is the area of
each lacuna as the lacuna stage outlined it, set against the WT median. No
lesion zone around a lacuna is measured or drawn, and nothing here calls a
lacuna a periosteocytic lesion (POL). It is a candidate POL measure, pending
Dr. Murshed's definition of a POL for these images. Pre-validation: no area
here has been checked against a manual measurement.

## Per group

Measured lacunae only: those not touching the frame and of a class with an
area. Area in um2 at 0.13 um/px; ratio is the area over the WT median lacunar
area, 36.73 um2 (the 88 measured WT lacunae pooled). Source:
[`pols_lacunar_size_by_group.csv`](pols_lacunar_size_by_group.csv); per image,
`results/<group>/3_pols/pols_all_images.csv`.

| group | images | measured lacunae | flagged, not measured | mean area (um2) | median area (um2) | median ratio to WT median | mean ratio to WT median |
| - | - | - | - | - | - | - | - |
| WT | 8 | 88 | 20 | 39.36 | 36.73 | 1.00 | 1.07 |
| WT_HP | 9 | 91 | 30 | 37.39 | 29.41 | 0.80 | 1.02 |
| Hyp_RD | 9 | 200 | 77 | 42.63 | 33.59 | 0.91 | 1.16 |
| Hyp_HP | 9 | 184 | 103 | 37.30 | 18.47 | 0.50 | 1.02 |

No statistical test was made, and the groups are not compared here beyond
this table.

## Problems found

Every picture was checked twice
([`../archive/POL_VISUAL_CHECK.md`](../archive/POL_VISUAL_CHECK.md)):
- **Automatically, 35 of 35 pass**
  ([`../archive/POL_PICTURE_CHECK.csv`](../archive/POL_PICTURE_CHECK.csv)):
  colour lies only inside lacuna masks, the number of filled lacunae equals
  the measured rows, every printed area equals its table value, and the image
  is unchanged elsewhere.
- **By eye, 10 images OK and 25 with detection problems** (WT 3 of 8, WT_HP 5
  of 9, Hyp_RD 8 of 9, Hyp_HP 9 of 9). Nothing was fixed. What recurs:
  - pieces of saturated bands, the bone surface or soft tissue measured as
    lacunae, some of them large (for example Hyp_HP 701_z19c1-2 id 11,
    304.9 um2, a blob in a soft tissue mass; WT_HP 872_wt_hp_z03 id 12, a
    band piece, 189.7 um2);
  - many small fragments of about 7 to 10 um2 measured as lacunae, above all
    in Hyp_RD and Hyp_HP;
  - lacunae split into two or more ids, in every group, WT included
    (682_z08, 682_z29);
  - large irregular shapes that may be two lacunae merged, or tissue;
  - dim out-of-focus bodies not outlined (missed), in WT_HP 877;
  - overlapping labels in some pictures (drawing only, no number affected).

**What this does to the table.** Small fragments pull a group's median down
and band and tissue pieces push its upper tail up. So the low Hyp_HP median
(18.47 um2, half the WT median) and the high upper values of the groups other
than WT come partly from detection errors and cannot be read as lacunar
enlargement. The lacuna stage was shaped on the 8 WT images; on the other
groups it is not validated.

## Before this can be a POL measure

A definition of a POL in these images, from Dr. Murshed: what boundary a lesion
has, and whether size is the measure at all. Then a lacuna stage that holds on
the groups other than WT, checked against manual outlines, so that bands,
tissue and fragments are not counted as lacunae.
