# AI judge rerun at method-freeze-v2: report (2026-11-09)

Pre-validation. No verdict of either judge has been checked against a manual
count. All comparisons are on the 27 development images. The 8 held-out
images were judged in the full run, but their judge outputs were not opened,
reviewed or summarized. The deterministic method and its results did not
change (regression PASS).

**What was run.** The lacuna judge's prompt was rewritten for the working POL
definition: enlarged lacunae and clusters are kept, and only fragments, band
pieces, tissue pieces and saturated border pieces are rejected, each with a
reason code. A region mostly in the excluded region is no longer offered to
it. The canaliculi judge, which had run on WT only, now runs on every group,
on the lacunae the lacuna judge accepted. FINAL mode, all 35 images.
Replayed offline from the logs, the verdicts are identical for both judges on
all 35 images. Details: METHODS 29, `PROGRESS_JUDGE.md`, `COST.md`,
`JUDGE_ON_VS_OFF.md`.

**Actual cost: $8.87 of the $50 budget.**

| Item | USD |
| - | - |
| Dry run | 0.91 |
| Lacuna judge (36 calls) | 1.08 |
| Canaliculi judge (about 600 calls) | 6.88 |

The canaliculi run was stopped once by the API ("credit balance too low"),
partway through two images. After the credit top-up, those two and the two
images not yet started were run again. About $0.36 paid for answers that were
asked again. The run records missed that $0.36 at first; the code now counts
a stopped image's cost.

**What the judge changed (development images, judge off to judge on):**

| | WT | WT_HP | Hyp_RD | Hyp_HP |
| - | - | - | - | - |
| lacunae | 71 to 73 | 83 to 78 | 147 to 115 | 146 to 107 |
| removed: fragment / band / tissue / saturated border | 1 / 0 / 0 / 1 | 0 / 9 / 1 / 0 | 7 / 10 / 11 / 4 | 16 / 8 / 12 / 13 |
| added (dim candidates) | 4 (1) | 5 (3) | 0 | 10 (2) |
| enlarged lacunae removed / clusters removed | 0 / 0 | 0 / 0 | 3 / 0 | 7 / 0 |
| median area, um2 | 39.9 to 38.3 | 31.2 to 32.3 | 38.4 to 40.5 | 24.7 to 24.0 |
| 90th percentile, um2 | 69.8 to 69.9 | 63.9 to 64.2 | 88.0 to 87.4 | 95.6 to 86.0 |
| share above 2 x WT median | 3.2% to 6.6% | 7.4% to 10.2% | 12.6% to 15.1% | 15.3% to 13.4% |
| POL area per analysed area | 2.9% to 2.7% | 2.8% to 2.5% | 6.3% to 4.8% | 6.0% to 3.4% |
| clusters | 0 to 0 | 0 to 0 | 1 to 1 | 0 to 0 |
| roots per lacuna (both judges) | 11.3 to 11.9 | 11.3 to 12.2 | 9.4 to 10.2 | 8.9 to 9.9 |
| ring length within 3.9 um, um | 55.9 to 61.1 | 64.8 to 73.0 | 36.4 to 40.6 | 41.2 to 45.7 |

**Does any group result move in a different direction? Four differences
change sign.** All four are small:

- WT_HP minus WT, measured lacunae: +6 to -2.
- Hyp_RD minus WT, median area: -1.4 to +2.2 um2.
- Hyp_HP minus Hyp_RD, 90th percentile: +7.6 to -1.4 um2.
- Hyp_HP minus Hyp_RD, share above 2 x the WT median: +2.7 to -1.7 points.

**The genotype by diet interaction keeps its sign for every measure.** It
grows or shrinks, for example:

- share above 2 x the WT median: -1.4 to -5.3 points;
- POL area per analysed area: -0.2 to -1.2 points;
- 90th percentile: +13.6 to +4.2 um2.

**The Hyp effect on the regular diet keeps its direction for every POL
measure** but becomes smaller: POL area per analysed area +3.5 to +2.1
points, share above 2 x the WT median +9.4 to +8.5 points. Most of the drop
in Hyp POL area is the judge removing band, tissue and saturated border
pieces that the deterministic rules kept. Those pieces are 90% (Hyp_RD) and
80% (Hyp_HP) of the area it removed; the rest is fragments.

**What still looks wrong:**

1. **Numbers read against the wrong outline.** At least 3 of the 10 enlarged
   lacunae the judge removed have an explanation that does not fit their size.
   In 548_hyp_HP_z14c1-2, for example, it called a 165 um2 body "tiny piece".
   In the picture it was sent, that body's number sits between two outlines,
   and the judge described the body next to it. With up to 60 numbers on a
   full field, some removals of enlarged lacunae are numbering mistakes, not
   judgements. Possible fixes: put each number inside its outline or join it
   to the outline with a line, or show large candidates in their own crops.
2. **The canaliculi judge adds thread length around every lacuna in every
   group:** ring length +4 to +8 um (9 to 13%), roots +0.6 to +1.0. The
   group differences barely move, but the shift is systematic and not
   validated.
3. **A region the judge adds has no area** (class `judged`): 19 on the
   development images, 3 of them called enlarged (Hyp_HP). They count as
   lacunae but not in any size or POL area measure.
4. **Many unsure verdicts in Hyp:** 32 in Hyp_RD and 42 in Hyp_HP, against 9
   in WT. An unsure region keeps the deterministic decision, so the Hyp groups
   rest on the deterministic rules more than WT does.
5. **The share above 2 x the WT median depends on each set's own WT
   median,** which fell from 39.9 to 38.3 um2 with the judge on. That is part
   of why the WT share rises.
6. **Validation.** Nothing here is checked against manual counts. Which
   method the study reports is still open.
