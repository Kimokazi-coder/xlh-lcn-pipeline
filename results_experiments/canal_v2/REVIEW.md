# Visual review, canaliculi-v2

Every PNG in this folder viewed at 1000 px wide and at 100% on its densest region (rule H). Defects
found, what was changed, and what remains. At most two rounds per image. Pre-validation, pixel units.

## C1_crops.png

Three interior lacunae with the most passing length: 542_z18 L4 (874,210), 682_z23 L3 (472,61), 543_z13
L7 (874,547). Round 1: the colours separate as intended. Vermillion threads reach the outline; sky blue
threads either run past the cell inside the ring or stop more than 10 px short of the body. The crop
counts equal the pipeline column (asserted). No defect in the image.

Reading, not a defect: in 682_z23 L3 several radial threads below the cell end more than 10 px from the
body (a gap in the mask next to the bright rim) and are counted as passing. So the attached length
leaves out passing threads but also threads that are broken near the cell; it depends on the attach gap
of 10 px, the same constant as the roots.

## C3_crops.png

543-2 L6 (746,472), the 543-2 cell closest to the median roots among cells at least 100 px from the
frame, and 543-2 L4 (39,297), the cell with the largest drop from 10 to 30 px. Round 1: the first draft
picked L4 twice (it is both the median cell and the largest drop); fix: the first pick at least 100 px
from the frame, the second excluding the first. The band tint at 35% was too dim to read at 1000 px; fix:
70%. Round 2: bands, crossing pixels and outline are clear at 1000 px and 100%. The counts in the crops
equal the pipeline columns (asserted). L4 is cut by the left frame edge, which is why its crop is narrower.

## B1_crops_L97_reach66_1.png and B1_crops_L40_reach0_1.png to _5.png

Every removed skeleton component of the two evidence settings, before (removed pixels vermillion) and
after (added pixels sky blue; there is one, 3 px, in 682_z29 at L 40), canal mask magenta.

Round 1 (all six sheets at 1000 px): the crops were a fixed 90 px, so the 102 px piece of the L 97
setting was cut at both ends, and crops at the frame came out narrower, which broke the grid. A first
version of the filter cut the network mask and re-skeletonized it, which left about 660 px of new stubs
along the cut in 542_z06 (seen as 653 added components); the filter was changed to remove skeleton
pixels only (and again after bridging), as the brief describes, and the stubs are gone. Fix for the
crops: each crop sized to its component (at least 90 px, the component plus 10 px), zero padded at the
frame, 2x up to 180 px.

Round 2: the L 97 crop shows the whole straight middle of the 542_z06 line removed; the L 40 tiles are
square. What the L 40 sheets show: vertical wall pieces inside the canal masks of 542_z06 and 542_z18
(these may be band wall), and ordinary threads that only touch a canal mask, many of them the
horizontal and vertical lattice threads of 682_z08, 682_z23 and 682_z29. This is the reason no value is
recommended.
