# Figure review, figures v2

Each exported PNG is viewed at 1000 px wide (a column-width preview) and as a 100% crop of its densest
region. Defects found, what was changed, and what remains. At most two rounds per figure.
Pre-validation, pixel units.

## N1 network overlay, 543-2

Insets by the rule (bounding box at least 60 px from the frame; fewest roots, roots closest to the
interior median 7.5, most roots; ties to the smallest id): L7 (2 roots), L6 (7), L2 (12). Logged in
`figures_out/per_image/543-2/inset.json`. Every interior lacuna: vermillion px equal
`ring_length_r30_px` and magenta dots equal `roots_count` (`network_check.json`).

Line widths: 0.3 pt in the full-field panel (about 1.2 device px at 300 dpi, the width of one image
pixel at that scale) and 0.5 pt in the 3x insets. Both read as crisp lines at 100%; 0.25 pt was not
needed. With round caps, the white skeleton at 70% shows no brighter beads at the joints at 100%.

Round 1:
- The count line under B ran off the right edge. Fix: right-aligned to the right edge of B.
- The inset letters C, D, E sat outside their boxes, so "C" read as belonging to box D. Fix: each letter
  inside the top left corner of its box.
- The title of B ("network overlay") did not say what is drawn. Fix: "lacunae, skeleton and roots over
  the image at 85%".

Round 2: clear. Remaining: the letter C in B sits next to the number of lacuna 5. The root dots in B are
small at 1000 px (they are legible in the insets and in the PDF).
PDF check: Arial embedded as TrueType (FontFile2), no Type 3 fonts, 2.0 MB, skeleton as vector lines.

## N1 network overlay, the other 7 images

Insets by the rule, logged in `per_image/<image>/inset.json`: 542_z06 L2, L7, L11 (4, 8, 13 roots,
median 8); 542_z18 L4, L3, L6 (7, 8, 10, median 8); 543_3 L7, L3, L4 (4, 7, 10, median 7); 543_z13 L4,
L2, L11 (3, 7, 12, median 7); 682_z08 L6, L5, L4 (5, 8, 18, median 9); 682_z23 L6, L10, L14 (5, 6, 10,
median 6); 682_z29 L11, L5, L4 (3, 5, 8, median 5). The assertions passed on all 8 images.

Round 1 (all 7 viewed at 1000 px with a 100% crop of panel B):
- 682_z08: the letter E sat on the number of lacuna 2 ("E 2"), and C crowded the number of lacuna 4.
  682_z23: E sat beside the number of lacuna 12. Fix: each letter goes to the inside corner of its box
  that is farthest from lacuna numbers and lacuna pixels.

Round 2 (all 8 redrawn): in 682_z08 the boxes C and D overlap, and each letter then sat inside the other
box. Fix: a corner inside another inset box is avoided. Redrawn and viewed again: every letter sits in
a corner of its own box (682_z08 C bottom left, D bottom right; 543_3 D top left, E top right).

Remaining, left as is:
- Inset boxes overlap when two chosen lacunae are close (542_z06 C and D, 543_3 D and E, 682_z08 C and
  D, 682_z23 D and E). The rule is fixed; `-c` can pick other lacunae.
- The inset crop is a fixed 222 px (3x), so the dashed 30 px ring of a long lacuna runs out of the inset
  (682_z08 L4, 682_z29 L4).
- The root dots in panel B are small at column width; they are clear in the insets and the PDF.
- The legend lists the frame-edge class also where an image has none (543-2, 543_z13), so every network
  figure has the same legend.
- 543_3 L6 (877,545) shows its known gap (two outline pieces); 682_z29 L9 and L10 are the known pair at
  (100,835). The figures show the default output as it is.

## N1 against the old verification images

Compared with `results/<image>/canaliculi_verification.png` (543-2 and 542_z06 side by side at the
same crop). Better: the raw structure stays visible, because the skeleton is a one-pixel vector line over
the image at 85% instead of a 5 px wide coloured band; every skeleton pixel is drawn, not only the
threads a cell owns, so the figure no longer implies an ownership claim that the headline measures do
not make; the vermillion pixels are exactly the pixels counted in ring 30 px and the magenta dots are
exactly the counted roots (asserted per lacuna), so the colours map onto the three headline measures;
one colour has one meaning, with a legend inside the figure; the insets show the 30 px ring and the
nearest-lacuna partition between close cells. Still weak: at column width the white skeleton covers the
raw threads it traces, so panel A is needed to judge the tracing; vermillion on grey is less striking
than the old saturated colours; the overlay says nothing about ownership-dependent measures (owned
length, edge count), which is intended but means the old image stays the only view of ownership; and
dim out-of-plane cells and rejected candidates are not drawn here.
