# Excluded regions review (2026-11-06)

Pre-validation. The image-reviewer subagent (Sonnet, Read, Glob and Grep
only) looked at the excluded-region picture of each of the 12 development
images that have an excluded region (`results/<group>/1_lacunae/<image>_excluded_region.png`).
The other 15 development images have none. DEV mode; no held-out image or
output was opened.

| picture | grey ok | lacunae under grey | missed | note |
| - | - | - | - | - |
| 872_wt_hp_z03_excluded_region.png | yes | 0 | none | grey covers saturated bottom band and its margin |
| 872_wt_hp_z04_excluded_region.png | yes | 0 | bright band along top edge, outlined in pieces | bottom band shaded correctly, top surface band not shaded |
| 872_wt_hp_z06_excluded_region.png | yes | 0 | bright band along top edge, outlined in pieces (2 to 3 outlines) | large bottom band and medium shaded correctly |
| 536-63x_Hyp_RD_z03c1-2_excluded_region.png | yes | 0 | bright diffuse patch at top left, outlined as 2 to 3 pieces; large bright mass bottom right outlined | small grey at right edge is non-lacunar |
| 536-63x_Hyp_RD_z08c1-2_excluded_region.png | yes | 0 | bright patch at top left outlined as 2 pieces | grey at right edge is saturated tissue |
| 536-63x_Hyp_RD_z15c1-2_excluded_region.png | yes | 0 | none | grey at right edge is non-lacunar; dim blur top left not outlined |
| I534_z11c1-2_excluded_region.png | partly | 1, bottom left edge (dark red compact body under the grey rim at about 270,960 is mostly outside, borderline) | none | grey mostly bright blobs and border; several kept outlines are irregular |
| I534_z25c1-2_excluded_region.png | yes | 0 | bright band along top edge, outlined in pieces | bottom and top left grey fine |
| 699_HYP_HP_z11c1-2_excluded_region.png | yes | 0 | bright elongated mass along bottom left and right, outlined as large pieces | grey on top and left is saturated tissue |
| 699_HYP_HP_z20c1-2_excluded_region.png | yes | 0 | bright elongated mass along bottom outlined as large pieces; saturated body at left edge about 40,430 outlined | grey top and left is saturated tissue |
| 699_HYP_HP_z25c1-2_excluded_region.png | yes | 0 | bright saturated mass at left edge about 30,540 outlined; long bright body along bottom outlined | grey at top is saturated tissue |
| 701_z26c1-2_excluded_region.png | yes | 0 | diffuse soft tissue field, many irregular outlines (right side, lower half) look like blurred glow not lacunae | grey covers the big tissue blocks at upper left |
