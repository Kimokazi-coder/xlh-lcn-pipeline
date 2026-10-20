# Judge off against judge on, 8 images

**EXPERIMENT, branch `exp-ai-layer`. NOT VALIDATED: no verdict here has been checked against a manual trace.** Judge off is `results/<label>/`, the pipeline as it stands. Judge on is `results_ai_judge/<label>/`, the same pipeline with `config.AI_JUDGE_ENABLED` on for that run only, applying the decision files in `results_ai_judge/ai_log/`. No call was made and no key was read.

Made by `python src/diagnostics.py ai-compare --dir data/WT`. Both runs are recomputed in memory and checked against the files on disk pixel for pixel before any number is reported: the judge-off skeleton against `results/`, the judge-on skeleton against `results_ai_judge/`, the roots in memory against the judge-on jsons, and the attachments against the ones the switch made. **Every check passed.** The full numbers are in `ai_compare.json`.

## Summary

| image | given an owner | moved by a verdict | segments moved | px moved | class d alone, px | roots off | roots on, before the fix | roots on | skeleton px | owned px | unowned px | largest owner share |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 542_z06 | 50 | 6 | 24 | 973 | 667 | 249 | 289 | 262 | 40,198 to 41,330 | 32,887 to 34,131 | 7,311 to 7,199 | 0.109 to 0.106 |
| 542_z18 | 64 | 17 | 97 | 2,479 | 2,341 | 133 | 182 | 141 | 39,183 to 39,855 | 29,658 to 31,678 | 9,525 to 8,177 | 0.091 to 0.106 |
| 543-2 | 59 | 23 | 104 | 2,813 | 3,184 | 102 | 155 | 108 | 44,105 to 44,739 | 37,623 to 38,938 | 6,482 to 5,801 | 0.117 to 0.116 |
| 543_3 | 117 | 46 | 254 | 7,041 | 7,818 | 86 | 183 | 100 | 41,269 to 44,604 | 36,517 to 40,547 | 4,752 to 4,057 | 0.127 to 0.115 |
| 543_z13 | 58 | 7 | 88 | 2,518 | 2,648 | 102 | 144 | 105 | 44,246 to 44,193 | 34,599 to 35,960 | 9,647 to 8,233 | 0.118 to 0.116 |
| 682_z08 | 43 | 5 | 22 | 611 | 490 | 131 | 163 | 143 | 36,997 to 37,374 | 28,414 to 29,625 | 8,583 to 7,749 | 0.189 to 0.195 |
| 682_z23 | 76 | 11 | 75 | 2,182 | 2,029 | 125 | 182 | 132 | 40,046 to 41,329 | 32,023 to 34,771 | 8,023 to 6,558 | 0.121 to 0.119 |
| 682_z29 | 87 | 23 | 106 | 2,756 | 2,666 | 117 | 184 | 122 | 37,663 to 38,267 | 29,408 to 31,585 | 8,255 to 6,682 | 0.152 to 0.154 |
| **all 8** | **554** | **138** | **770** | **21,373** | **21,843** | **1,045** | **1,482** | **1,113** | | | | |

- **given an owner**: verdicts applied as a zero weight attachment, after conflicts (there were none). **moved by a verdict**: of those, the ones naming a different cell from the one that owned the segment.
- **segments moved** and **px moved** are the outcome: what the shortest path did once the attachments were in the graph. A segment here is a branch of the judge-on skeleton, at least the judge's minimum segment length, whose majority owner changed.
- **class d alone**: the same switch with every verdict but the class d ones left unjudged, so the pixels that change hands are the ones class d moves on its own.
- **roots**: summed over every lacuna. *roots off* and *roots on* are the quantification jsons on disk; *roots on, before the fix* is the same judge-on graph counted the old way, with a verdict's attachment counted as a root. See below.

## Roots, and the fix

A verdict is expressed as a zero weight attachment from the cell it names to the end of the segment nearest that cell, and that end can lie tens of pixels from the body. The root count used to count every node attached to a cell's virtual node, so **every such verdict added a root that is not a thread leaving the body**. The fix keeps the attachment, so the shortest path still splits the network exactly as it did, and counts a root only for an attachment the pipeline's own contact or attach rule made, which only ever attach within reach of the body (`quantification.root_points`). A verdict's own edge is marked `judged` when it is made and is left out; where the pipeline had already joined that cell to that node, the edge stays the pipeline's and stays a root. With the switch off no edge is marked, so every number is what it was.

| image | roots off | roots on, before the fix | roots on | mean per interior cell, off | on, before the fix | on |
| --- | --- | --- | --- | --- | --- | --- |
| 542_z06 | 249 | 289 | 262 | 15.1333 | 17.2667 | 15.8 |
| 542_z18 | 133 | 182 | 141 | 11.8182 | 16.1818 | 12.4545 |
| 543-2 | 102 | 155 | 108 | 8.5 | 12.9167 | 9.0 |
| 543_3 | 86 | 183 | 100 | 7.0 | 14.25 | 8.1667 |
| 543_z13 | 102 | 144 | 105 | 9.2727 | 13.0909 | 9.5455 |
| 682_z08 | 131 | 163 | 143 | 12.3333 | 15.3333 | 13.6667 |
| 682_z23 | 125 | 182 | 132 | 9.7273 | 14.0909 | 10.3636 |
| 682_z29 | 117 | 184 | 122 | 7.8462 | 12.6154 | 8.2308 |

## Per image

### 542_z06

Verdicts by class (segments, and their own px):

| class | kept by its owner | given to a segment nobody owned | moved to another cell | given no owner |
| --- | --- | --- | --- | --- |
| a | 0 (0 px) | 13 (257 px) | 0 (0 px) | 30 (938 px) |
| b | 0 (0 px) | 25 (468 px) | 0 (0 px) | 21 (321 px) |
| d | 6 (171 px) | 0 (0 px) | 6 (326 px) | 7 (115 px) |

- Ownership moves between cells: **24 segments (813 px)**, and **973 px** of tracing changed hands on the owner maps. Pairs by px: 9 to 14 (203 px), 10 to 9 (186 px), 15 to 13 (168 px), 2 to 5 (163 px), and 5 more pairs. Pairs by segments: 9 to 14 (8 segments), 2 to 5 (4 segments), 10 to 9 (4 segments), 15 to 13 (3 segments), and 4 more pairs.
- Newly owned: 1,478 px. No longer owned: 234 px.
- **Class d alone**: 12 verdicts attached, 15 segments (619 px) and 667 px changed hands. Pairs by px: 10 to 9 (186 px), 15 to 13 (168 px), 2 to 5 (163 px), 13 to 15 (85 px), and 2 more pairs.
- Class d verdicts: 6 moved to the other cell, 6 kept by their owner, 7 given no owner; pairs 10 to 9 (2), 15 to 13 (2), 7 to 19 (1), 2 to 5 (1).
- Roots, summed: 249 with the judge off, 289 with it on before the fix, 262 with it on. Per lacuna, off / on before the fix / on: 1: 7 / 7 / 7, 2: 8 / 8 / 8, 3: 14 / 14 / 14, 4: 12 / 13 / 12, 5: 10 / 13 / 10, 6: 29 / 30 / 30, 7: 16 / 18 / 17, 8: 17 / 17 / 16, 9: 6 / 9 / 7, 10: 16 / 19 / 17, 11: 24 / 28 / 27, 12: 23 / 25 / 22, 13: 20 / 23 / 20, 14: 10 / 12 / 12, 15: 8 / 11 / 9, 16: 5 / 8 / 6, 17: 17 / 23 / 20, 18: 2 / 4 / 3, 19: 5 / 7 / 5.
- Skeleton 40,198 to 41,330 px; owned 32,887 to 34,131; unowned 7,311 to 7,199; largest owner cell 6 at 0.109 to cell 6 at 0.106.
- Pictures: `results_ai_judge/compare/542_z06_verification_judge_off_on.png`, `results_ai_judge/compare/542_z06_skeleton_judge_off_on.png`, `results_ai_judge/compare/542_z06_ownership_changes.png` (red changed hands, green newly owned, blue no longer owned, grey the rest, each changed pixel widened by one so it shows).

### 542_z18

Verdicts by class (segments, and their own px):

| class | kept by its owner | given to a segment nobody owned | moved to another cell | given no owner |
| --- | --- | --- | --- | --- |
| a | 0 (0 px) | 14 (378 px) | 0 (0 px) | 35 (879 px) |
| b | 0 (0 px) | 32 (453 px) | 0 (0 px) | 14 (204 px) |
| d | 1 (11 px) | 0 (0 px) | 17 (418 px) | 5 (191 px) |

- Ownership moves between cells: **97 segments (2,050 px)**, and **2,479 px** of tracing changed hands on the owner maps. Pairs by px: 8 to 7 (834 px), 1 to 4 (454 px), 9 to 6 (429 px), 9 to 11 (234 px), and 5 more pairs. Pairs by segments: 8 to 7 (36 segments), 1 to 4 (18 segments), 9 to 6 (16 segments), 2 to 4 (9 segments), and 5 more pairs.
- Newly owned: 2,272 px. No longer owned: 252 px.
- **Class d alone**: 18 verdicts attached, 90 segments (1,895 px) and 2,341 px changed hands. Pairs by px: 8 to 7 (880 px), 1 to 4 (454 px), 9 to 6 (429 px), 9 to 11 (234 px), and 2 more pairs.
- Class d verdicts: 17 moved to the other cell, 1 kept by their owner, 5 given no owner; pairs 8 to 7 (5), 9 to 6 (4), 7 to 8 (3), 1 to 4 (2), 2 to 4 (2), 9 to 11 (1).
- Roots, summed: 133 with the judge off, 182 with it on before the fix, 141 with it on. Per lacuna, off / on before the fix / on: 1: 3 / 4 / 4, 2: 26 / 28 / 26, 3: 10 / 14 / 10, 4: 19 / 26 / 20, 5: 10 / 12 / 11, 6: 10 / 14 / 10, 7: 15 / 20 / 15, 8: 7 / 14 / 8, 9: 14 / 22 / 16, 10: 9 / 11 / 10, 11: 6 / 9 / 7, 12: 4 / 8 / 4, 13: 0 / 0 / 0.
- Skeleton 39,183 to 39,855 px; owned 29,658 to 31,678; unowned 9,525 to 8,177; largest owner cell 8 at 0.091 to cell 4 at 0.106.
- Pictures: `results_ai_judge/compare/542_z18_verification_judge_off_on.png`, `results_ai_judge/compare/542_z18_skeleton_judge_off_on.png`, `results_ai_judge/compare/542_z18_ownership_changes.png` (red changed hands, green newly owned, blue no longer owned, grey the rest, each changed pixel widened by one so it shows).

### 543-2

Verdicts by class (segments, and their own px):

| class | kept by its owner | given to a segment nobody owned | moved to another cell | given no owner |
| --- | --- | --- | --- | --- |
| a | 0 (0 px) | 9 (317 px) | 0 (0 px) | 2 (28 px) |
| b | 0 (0 px) | 24 (474 px) | 0 (0 px) | 26 (526 px) |
| d | 3 (61 px) | 0 (0 px) | 23 (667 px) | 1 (14 px) |

- Ownership moves between cells: **104 segments (2,215 px)**, and **2,813 px** of tracing changed hands on the owner maps. Pairs by px: 5 to 9 (757 px), 10 to 11 (554 px), 6 to 8 (405 px), 7 to 9 (213 px), and 9 more pairs. Pairs by segments: 5 to 9 (27 segments), 10 to 11 (21 segments), 6 to 8 (14 segments), 2 to 8 (10 segments), and 9 more pairs.
- Newly owned: 1,612 px. No longer owned: 297 px.
- **Class d alone**: 26 verdicts attached, 119 segments (2,494 px) and 3,184 px changed hands. Pairs by px: 5 to 9 (827 px), 5 to 7 (554 px), 10 to 11 (516 px), 6 to 8 (405 px), and 7 more pairs.
- Class d verdicts: 23 moved to the other cell, 3 kept by their owner, 1 given no owner; pairs 10 to 11 (9), 5 to 9 (6), 5 to 7 (2), 6 to 8 (2), 1 to 3 (1), 5 to 3 (1), 11 to 12 (1), 11 to 10 (1).
- Roots, summed: 102 with the judge off, 155 with it on before the fix, 108 with it on. Per lacuna, off / on before the fix / on: 1: 12 / 16 / 13, 2: 11 / 15 / 12, 3: 6 / 11 / 8, 4: 9 / 10 / 9, 5: 5 / 12 / 6, 6: 10 / 10 / 10, 7: 4 / 10 / 5, 8: 12 / 16 / 12, 9: 11 / 19 / 11, 10: 8 / 11 / 9, 11: 8 / 17 / 7, 12: 6 / 8 / 6.
- Skeleton 44,105 to 44,739 px; owned 37,623 to 38,938; unowned 6,482 to 5,801; largest owner cell 2 at 0.117 to cell 9 at 0.116.
- Pictures: `results_ai_judge/compare/543-2_verification_judge_off_on.png`, `results_ai_judge/compare/543-2_skeleton_judge_off_on.png`, `results_ai_judge/compare/543-2_ownership_changes.png` (red changed hands, green newly owned, blue no longer owned, grey the rest, each changed pixel widened by one so it shows).

### 543_3

Verdicts by class (segments, and their own px):

| class | kept by its owner | given to a segment nobody owned | moved to another cell | given no owner |
| --- | --- | --- | --- | --- |
| a | 0 (0 px) | 17 (344 px) | 0 (0 px) | 11 (286 px) |
| b | 0 (0 px) | 47 (1427 px) | 0 (0 px) | 34 (476 px) |
| d | 7 (213 px) | 0 (0 px) | 46 (1229 px) | 1 (16 px) |

- Ownership moves between cells: **254 segments (5,814 px)**, and **7,041 px** of tracing changed hands on the owner maps. Pairs by px: 3 to 5 (1090 px), 10 to 13 (980 px), 6 to 7 (796 px), 9 to 10 (683 px), and 16 more pairs. Pairs by segments: 3 to 5 (39 segments), 10 to 13 (36 segments), 4 to 8 (30 segments), 6 to 7 (28 segments), and 15 more pairs.
- Newly owned: 4,758 px. No longer owned: 728 px.
- **Class d alone**: 53 verdicts attached, 270 segments (6,025 px) and 7,818 px changed hands. Pairs by px: 12 to 5 (1554 px), 3 to 5 (1232 px), 10 to 13 (1084 px), 6 to 7 (810 px), and 12 more pairs.
- Class d verdicts: 46 moved to the other cell, 7 kept by their owner, 1 given no owner; pairs 10 to 13 (16), 4 to 1 (7), 4 to 8 (7), 6 to 7 (5), 3 to 5 (2), 13 to 11 (2), 9 to 10 (2), 12 to 5 (1), 7 to 6 (1), 10 to 9 (1), 4 to 5 (1), 8 to 10 (1).
- Roots, summed: 86 with the judge off, 183 with it on before the fix, 100 with it on. Per lacuna, off / on before the fix / on: 1: 7 / 15 / 7, 2: 15 / 14 / 14, 3: 8 / 10 / 8, 4: 16 / 21 / 18, 5: 5 / 14 / 7, 6: 11 / 18 / 12, 7: 5 / 13 / 6, 8: 3 / 16 / 5, 9: 5 / 9 / 6, 10: 4 / 11 / 7, 11: 2 / 12 / 2, 12: 2 / 11 / 5, 13: 3 / 19 / 3.
- Skeleton 41,269 to 44,604 px; owned 36,517 to 40,547; unowned 4,752 to 4,057; largest owner cell 3 at 0.127 to cell 7 at 0.115.
- Pictures: `results_ai_judge/compare/543_3_verification_judge_off_on.png`, `results_ai_judge/compare/543_3_skeleton_judge_off_on.png`, `results_ai_judge/compare/543_3_ownership_changes.png` (red changed hands, green newly owned, blue no longer owned, grey the rest, each changed pixel widened by one so it shows).

### 543_z13

Verdicts by class (segments, and their own px):

| class | kept by its owner | given to a segment nobody owned | moved to another cell | given no owner |
| --- | --- | --- | --- | --- |
| a | 0 (0 px) | 12 (382 px) | 0 (0 px) | 5 (148 px) |
| b | 0 (0 px) | 30 (543 px) | 0 (0 px) | 18 (238 px) |
| d | 9 (226 px) | 0 (0 px) | 7 (295 px) | 2 (75 px) |

- Ownership moves between cells: **88 segments (1,881 px)**, and **2,518 px** of tracing changed hands on the owner maps. Pairs by px: 5 to 4 (765 px), 4 to 1 (516 px), 11 to 10 (255 px), 11 to 8 (206 px), and 9 more pairs. Pairs by segments: 5 to 4 (34 segments), 4 to 1 (16 segments), 2 to 3 (7 segments), 11 to 10 (7 segments), and 8 more pairs.
- Newly owned: 2,741 px. No longer owned: 1,380 px.
- **Class d alone**: 16 verdicts attached, 88 segments (1,967 px) and 2,648 px changed hands. Pairs by px: 7 to 9 (787 px), 5 to 4 (749 px), 4 to 1 (520 px), 11 to 10 (246 px), and 4 more pairs.
- Class d verdicts: 7 moved to the other cell, 9 kept by their owner, 2 given no owner; pairs 10 to 9 (2), 1 to 4 (1), 6 to 7 (1), 11 to 10 (1), 5 to 4 (1), 7 to 9 (1).
- Roots, summed: 102 with the judge off, 144 with it on before the fix, 105 with it on. Per lacuna, off / on before the fix / on: 1: 5 / 12 / 8, 2: 11 / 17 / 11, 3: 13 / 16 / 11, 4: 4 / 7 / 5, 5: 10 / 12 / 11, 6: 5 / 8 / 6, 7: 14 / 20 / 13, 8: 10 / 14 / 10, 9: 8 / 12 / 7, 10: 10 / 14 / 11, 11: 12 / 12 / 12.
- Skeleton 44,246 to 44,193 px; owned 34,599 to 35,960; unowned 9,647 to 8,233; largest owner cell 5 at 0.118 to cell 2 at 0.116.
- Pictures: `results_ai_judge/compare/543_z13_verification_judge_off_on.png`, `results_ai_judge/compare/543_z13_skeleton_judge_off_on.png`, `results_ai_judge/compare/543_z13_ownership_changes.png` (red changed hands, green newly owned, blue no longer owned, grey the rest, each changed pixel widened by one so it shows).

### 682_z08

Verdicts by class (segments, and their own px):

| class | kept by its owner | given to a segment nobody owned | moved to another cell | given no owner |
| --- | --- | --- | --- | --- |
| a | 0 (0 px) | 14 (475 px) | 0 (0 px) | 12 (324 px) |
| b | 0 (0 px) | 22 (350 px) | 0 (0 px) | 17 (207 px) |
| d | 2 (37 px) | 0 (0 px) | 5 (151 px) | 0 (0 px) |

- Ownership moves between cells: **22 segments (483 px)**, and **611 px** of tracing changed hands on the owner maps. Pairs by px: 6 to 5 (284 px), 4 to 8 (176 px), 3 to 5 (65 px), 4 to 2 (43 px), and 1 more pairs. Pairs by segments: 6 to 5 (10 segments), 4 to 8 (7 segments), 3 to 5 (2 segments), 4 to 6 (2 segments), and 1 more pairs.
- Newly owned: 1,412 px. No longer owned: 201 px.
- **Class d alone**: 7 verdicts attached, 17 segments (372 px) and 490 px changed hands. Pairs by px: 6 to 5 (271 px), 4 to 8 (176 px), 4 to 2 (43 px).
- Class d verdicts: 5 moved to the other cell, 2 kept by their owner, 0 given no owner; pairs 6 to 5 (2), 4 to 8 (2), 4 to 2 (1).
- Roots, summed: 131 with the judge off, 163 with it on before the fix, 143 with it on. Per lacuna, off / on before the fix / on: 1: 16 / 17 / 16, 2: 13 / 15 / 14, 3: 18 / 20 / 19, 4: 19 / 24 / 24, 5: 10 / 14 / 11, 6: 9 / 12 / 9, 7: 4 / 8 / 4, 8: 15 / 20 / 18, 9: 12 / 14 / 14, 10: 9 / 12 / 8, 11: 6 / 7 / 6.
- Skeleton 36,997 to 37,374 px; owned 28,414 to 29,625; unowned 8,583 to 7,749; largest owner cell 8 at 0.189 to cell 8 at 0.195.
- Pictures: `results_ai_judge/compare/682_z08_verification_judge_off_on.png`, `results_ai_judge/compare/682_z08_skeleton_judge_off_on.png`, `results_ai_judge/compare/682_z08_ownership_changes.png` (red changed hands, green newly owned, blue no longer owned, grey the rest, each changed pixel widened by one so it shows).

### 682_z23

Verdicts by class (segments, and their own px):

| class | kept by its owner | given to a segment nobody owned | moved to another cell | given no owner |
| --- | --- | --- | --- | --- |
| a | 0 (0 px) | 23 (599 px) | 0 (0 px) | 29 (754 px) |
| b | 0 (0 px) | 31 (585 px) | 0 (0 px) | 15 (217 px) |
| d | 11 (252 px) | 0 (0 px) | 11 (288 px) | 0 (0 px) |

- Ownership moves between cells: **75 segments (1,741 px)**, and **2,182 px** of tracing changed hands on the owner maps. Pairs by px: 10 to 14 (860 px), 2 to 5 (282 px), 5 to 8 (237 px), 9 to 10 (181 px), and 11 more pairs. Pairs by segments: 10 to 14 (28 segments), 5 to 8 (9 segments), 2 to 5 (8 segments), 7 to 5 (6 segments), and 11 more pairs.
- Newly owned: 3,256 px. No longer owned: 508 px.
- **Class d alone**: 22 verdicts attached, 65 segments (1,551 px) and 2,029 px changed hands. Pairs by px: 10 to 14 (862 px), 7 to 8 (458 px), 5 to 8 (237 px), 9 to 10 (136 px), and 5 more pairs.
- Class d verdicts: 11 moved to the other cell, 11 kept by their owner, 0 given no owner; pairs 8 to 7 (3), 9 to 10 (2), 12 to 10 (2), 14 to 12 (1), 13 to 11 (1), 5 to 9 (1), 10 to 14 (1).
- Roots, summed: 125 with the judge off, 182 with it on before the fix, 132 with it on. Per lacuna, off / on before the fix / on: 1: 4 / 8 / 4, 2: 4 / 6 / 4, 3: 8 / 10 / 8, 4: 9 / 11 / 11, 5: 15 / 20 / 16, 6: 6 / 8 / 5, 7: 10 / 15 / 13, 8: 10 / 13 / 10, 9: 10 / 13 / 10, 10: 8 / 15 / 10, 11: 7 / 13 / 7, 12: 14 / 18 / 14, 13: 8 / 10 / 8, 14: 12 / 22 / 12.
- Skeleton 40,046 to 41,329 px; owned 32,023 to 34,771; unowned 8,023 to 6,558; largest owner cell 4 at 0.121 to cell 4 at 0.119.
- Pictures: `results_ai_judge/compare/682_z23_verification_judge_off_on.png`, `results_ai_judge/compare/682_z23_skeleton_judge_off_on.png`, `results_ai_judge/compare/682_z23_ownership_changes.png` (red changed hands, green newly owned, blue no longer owned, grey the rest, each changed pixel widened by one so it shows).

### 682_z29

Verdicts by class (segments, and their own px):

| class | kept by its owner | given to a segment nobody owned | moved to another cell | given no owner |
| --- | --- | --- | --- | --- |
| a | 0 (0 px) | 23 (567 px) | 0 (0 px) | 17 (549 px) |
| b | 0 (0 px) | 28 (516 px) | 0 (0 px) | 35 (596 px) |
| d | 13 (298 px) | 0 (0 px) | 23 (530 px) | 4 (105 px) |

- Ownership moves between cells: **106 segments (2,348 px)**, and **2,756 px** of tracing changed hands on the owner maps. Pairs by px: 8 to 6 (765 px), 4 to 6 (475 px), 6 to 5 (467 px), 3 to 5 (229 px), and 12 more pairs. Pairs by segments: 8 to 6 (26 segments), 4 to 6 (18 segments), 6 to 5 (17 segments), 3 to 5 (10 segments), and 12 more pairs.
- Newly owned: 2,726 px. No longer owned: 549 px.
- **Class d alone**: 36 verdicts attached, 100 segments (2,177 px) and 2,666 px changed hands. Pairs by px: 8 to 6 (765 px), 6 to 5 (475 px), 4 to 6 (421 px), 3 to 5 (248 px), and 10 more pairs.
- Class d verdicts: 23 moved to the other cell, 13 kept by their owner, 4 given no owner; pairs 3 to 5 (6), 4 to 6 (5), 7 to 8 (3), 6 to 15 (2), 6 to 8 (2), 6 to 4 (1), 6 to 5 (1), 4 to 15 (1), 9 to 12 (1), 4 to 5 (1).
- Roots, summed: 117 with the judge off, 184 with it on before the fix, 122 with it on. Per lacuna, off / on before the fix / on: 1: 4 / 7 / 4, 2: 17 / 14 / 14, 3: 6 / 8 / 6, 4: 12 / 16 / 11, 5: 7 / 20 / 11, 6: 9 / 17 / 10, 7: 11 / 13 / 11, 8: 8 / 16 / 8, 9: 9 / 14 / 9, 10: 5 / 6 / 6, 11: 5 / 9 / 5, 12: 3 / 9 / 4, 13: 9 / 16 / 11, 14: 10 / 13 / 10, 15: 2 / 6 / 2.
- Skeleton 37,663 to 38,267 px; owned 29,408 to 31,585; unowned 8,255 to 6,682; largest owner cell 2 at 0.152 to cell 2 at 0.154.
- Pictures: `results_ai_judge/compare/682_z29_verification_judge_off_on.png`, `results_ai_judge/compare/682_z29_skeleton_judge_off_on.png`, `results_ai_judge/compare/682_z29_ownership_changes.png` (red changed hands, green newly owned, blue no longer owned, grey the rest, each changed pixel widened by one so it shows).

## Cases where a body could not be named

A body beyond the sixth colour in a picture is outlined grey and has no name the judge could answer with. A number is only asked where both of its candidates have a colour, so a grey body should be context only; the last column checks that it was, number by number, from the decision files.

| image | case | kind | yellow lacuna | grey lacunae | numbered segments | both candidates named for every number |
| --- | --- | --- | --- | --- | --- | --- |
| 542_z06 | case_0023 | left over | 7 | 11, 12, 19 | 1 | yes |
| 542_z06 | case_0024 | left over | 17 | 10 | 3 | yes |
| 682_z29 | case_0019 | left over | 8 | 11, 15 | 5 | yes |
