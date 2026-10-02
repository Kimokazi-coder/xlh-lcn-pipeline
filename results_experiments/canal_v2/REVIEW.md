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
