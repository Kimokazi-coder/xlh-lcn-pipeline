# Cap audit: what the 300 um2 band rule removes

**Pre-validation.** The classes are an AI reviewer's judgement (the
`image-reviewer` subagent, Sonnet, Read, Glob and Grep only), one look per
crop, not a manual count.

**What was audited.** The band rule (`config.BAND_BLOB_RULE`, section g8)
drops a kept object when its connected region of the lacuna mask is larger
than 300 um2. `python src/diagnostics.py cap-audit` runs the frozen detector
(tag `method-freeze-v1`) on the 27 development images with the rule off,
applies it to the same kept list as `src/lacunae.py` does, and lists every
object it drops: [`cap_removed.csv`](cap_removed.csv) (area, mean and maximum
brightness on 0 to 255, solidity, eccentricity, saturated share, whether the
object or the pixel ring around it touches a saturated pixel, the area of its
mask region, frame contact). A crop of each, raw beside outlined, with a 10 um
bar, is in [`cap_removed/<group>/`](cap_removed/). The reviewer's tables are
kept verbatim in [`reviews/cap_A.md`](reviews/cap_A.md) and
[`reviews/cap_B.md`](reviews/cap_B.md).

## Counts per group and class

| group | removed | real lacuna | band or tissue | unsure |
| - | - | - | - | - |
| WT | 0 | 0 | 0 | 0 |
| WT_HP | 2 | 0 | 2 | 0 |
| Hyp_RD | 7 | 0 | 7 | 0 |
| Hyp_HP | 8 | 0 | 6 | 2 |
| all | 17 | 0 | 15 | 2 |

## Bias test

**No real lacuna was removed, so by the brief's test the rule is not biased,
and it is not changed.**

The two unsure objects are both in Hyp_HP 701_z26c1-2: object 50 (44.1 um2,
"part of a brighter streak with a pink blob") and object 54 (214.5 um2, "large
diffuse red mass with faint ring structure; could be enlarged lacuna or
tissue"). Object 54 is the kind of case the rule could cost: a large Hyp body
that lies in a mask region of 779 um2. It is reported, not counted as a real
lacuna.

**What the measurements add.** 11 of the 17 touch a saturated pixel (all of
WT_HP and Hyp_RD and the two of 699_HYP_HP_z11c1-2); the 6 of 701_z26c1-2 hold
no saturated pixel at all (maximum 189 to 242). So a rule on saturation alone
would not have removed the tissue of 701_z26c1-2.
