# Cap v2 review, part A (WT, WT_HP, Hyp_RD)

Pre-validation. The image-reviewer subagent (Sonnet, Read, Glob and Grep
only), 2026-11-06, blind: it saw only the crops in `../cap_v2/` and was not
told what either rule decided. Development images only, DEV mode.

| crop | class | cluster | reason |
| - | - | - | - |
| 682_z08_obj11.png | not a lacuna | - | saturated bloom along the frame edge |
| 872_wt_hp_z03_obj44.png | not a lacuna | - | saturated band, irregular blob, no compact body |
| 872_wt_hp_z03_obj45.png | not a lacuna | - | long saturated band |
| 872_wt_hp_z04_obj479.png | not a lacuna | - | dim diffuse patch below the band, no cell body |
| 872_wt_hp_z06_obj170.png | unsure | - | elongated bright blob beside a band, could be a lacuna |
| 535_z13c1-2_obj50.png | lacuna | unsure | large irregular bright body with a tail, maybe two |
| 535_z27c1-2_obj67.png | lacuna | yes | large mass with two or three lobes |
| 535_z27c1-2_obj109.png | lacuna | yes | two bodies joined, round one at top right |
| 535_z27c1-2_obj141.png | not a lacuna | - | diffuse glow cut by the frame edge, no cell body |
| 536-63x_Hyp_RD_z03c1-2_obj104.png | not a lacuna | - | large saturated tissue at the frame edge |
| 536-63x_Hyp_RD_z03c1-2_obj105.png | not a lacuna | - | saturated tissue mass at the frame edge |
| 536-63x_Hyp_RD_z03c1-2_obj121.png | not a lacuna | - | large saturated wedge of tissue at the frame edge |
| 536-63x_Hyp_RD_z08c1-2_obj110.png | not a lacuna | - | saturated tissue edge along the frame |
| 536-63x_Hyp_RD_z15c1-2_obj81.png | not a lacuna | - | saturated tissue edge along the frame |
| I534_z11c1-2_obj10.png | not a lacuna | - | long saturated band |
| I534_z11c1-2_obj56.png | unsure | unsure | large irregular mass at the frame edge, maybe merged lacunae |
| I534_z11c1-2_obj93.png | lacuna | no | single bright enlarged body with canaliculi |
| I534_z11c1-2_obj306.png | not a lacuna | - | saturated tissue mass at the frame edge |
| I534_z25c1-2_obj4.png | not a lacuna | - | saturated band at the frame edge |
| I534_z25c1-2_obj34.png | unsure | unsure | large irregular bright mass cut by the frame edge |
| I534_z25c1-2_obj204.png | not a lacuna | - | saturated border tissue with ragged edge |
| I534_z25c1-2_obj229.png | lacuna | no | small dim body in a gap above the bright tissue |
