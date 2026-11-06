# Dim lacuna audit: what the rescue rules being off costs

**Pre-validation.** The classes are an AI reviewer's judgement (the
`image-reviewer` subagent, Sonnet, Read, Glob and Grep only), one look per
crop, not a manual count.

**What was audited.** Since loop round 1 the four rescue rules (out of focus
f, dim g1, frame g2, thick process g3; `config.LACUNA_RESCUE_RULES = False`)
are off. `python src/diagnostics.py dim-audit` runs the frozen detector (tag
`method-freeze-v1`) on the 27 development images with them on and lists every
lacuna found only then: [`dim_added.csv`](dim_added.csv) (the measures of the
cap audit plus contrast, local background, glow footprint and distance to the
nearest ordinary lacuna), the lacunae detected with them off per image
([`dim_detected.csv`](dim_detected.csv)), and a crop of each, raw beside
outlined, in [`dim_added/<group>/`](dim_added/). The reviewer's tables are
kept verbatim in `reviews/dim_*.md`.

## Per group

| group | added with rescue on | real lacuna | unsure | not a lacuna | detected with rescue off | real lacunae lost | lost, real or unsure |
| - | - | - | - | - | - | - | - |
| WT | 8 | 4 | 1 | 3 | 71 | **5.6%** | 7.0% |
| WT_HP | 4 | 1 | 2 | 1 | 85 | **1.2%** | 3.5% |
| Hyp_RD | 25 | 6 | 7 | 12 | 150 | **4.0%** | 8.7% |
| Hyp_HP | 23 | 0 | 6 | 17 | 149 | **0.0%** | 4.0% |
| all | 60 | 11 | 16 | 33 | 455 | 2.4% | 5.9% |

By rule, the 11 real lacunae came from f out of focus 5 (all Hyp_RD), g1 dim
4 (WT 3, WT_HP 1), g2 frame 1 (Hyp_RD) and g3 thick process 1 (WT). The 33
non-lacunae: f 7, g1 19, g2 7 (two of them band pieces of over 650 um2 that the
band rule had removed and the frame rule puts back).

## Bias test

**The lost percentage differs by 5.6 points between groups (WT 5.6%, Hyp_HP
0.0%), more than 5, so by the brief's test the dim loss is biased.** Counting
unsure as real gives 5.2 points (Hyp_RD 8.7%, WT_HP 3.5%), also above 5. The
finding rests on small numbers: 4 WT lacunae, judged once each by a reviewer
whose count moved by up to 4 between two looks at identical WT pictures in the
loop.

## Can a narrow rescue rule bring them back?

`python src/diagnostics.py dim-rule-search` tries every rule of one to three
bounds on the measured features (brightness, contrast, background, shape,
glow footprint, distance to the nearest lacuna) over the 57 rescued objects
the band rule would keep: [`dim_rule_search.csv`](dim_rule_search.csv).

| non-lacunae allowed back | real lacunae back, of 11 | best rule found |
| - | - | - |
| 0 | 3 | to lacuna at least 10 um, glow solidity at least 0.75, eccentricity at most 0.9 |
| 3 | 6 | to lacuna at least 2 um, eccentricity at most 0.7 |
| 5 | 7 | contrast at least 1.6, eccentricity at most 0.9 |
| 8 | 10 | over background at least 2.0, to lacuna at least 3 um, mean at least 160 |
| all rules on | 11 | the method before loop round 1: 30 non-lacunae back |

**No rule returns the real lacunae without returning fragments:** each real
lacuna brought back costs about one non-lacuna. The only clean rule returns 3
of 11 with three thresholds chosen on these few objects. What came out of the
decision is in [`FIX_LOG.md`](FIX_LOG.md).
