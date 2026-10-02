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

## N2 cell galleries

One page per image (at most 13 interior lacunae, so no image needs a second page). Tiles are 240 px
crops at 3 output pixels per image pixel at 300 dpi (61 mm), so a row of 4 tiles makes the page 257 mm
wide, wider than a 180 mm column (listed under Decisions needed). Per tile, the magenta dots equal
`roots_count` and the vermillion pixels equal `ring_length_r30_px` (asserted;
`per_image/<image>/gallery_check.json`). Only the tile lacuna's roots are drawn, so the dots in a tile
are the number in its title; neighbouring lacunae keep their outlines and their vermillion ring.

Round 1 (543-2 at 1000 px and 100%; then all 8 at 1000 px): an empty band between the legend and the
footnote (fix: smaller strips); the second legend row ("c") overlapped the footnote in 542_z06, 682_z08
and 682_z23 (fix: a taller strip when the legend has two rows); 682_z08 showed the "c" key although no
tile carries a "c" (its canal-marked lacuna touches the frame and is not shown; fix: the key only when a
tile title has it).

Round 2: footers clear on all 8.

Remaining, left as is: in three tiles part of the ring lies outside the 240 px crop (542_z18 L2 28 px,
L9 11 px; 682_z08 L4 3 px), logged in `gallery_check.json`; every root dot lies inside its tile. Tiles
near the frame are zero padded (black), for example 543-2 L1 and L4, 542_z06 L3.

## N3 hand-count tiles

86 tiles (every interior lacuna of the 8 images), 240 x 240 px, 8-bit. Checks: a key path inside the
repository was refused before anything was written; every tile holds only the IHDR, IDAT and IEND
chunks (no text, time or dpi); six tiles compared with crops of the raw files: identical; a second run
skipped all 86. Eight tiles viewed: the centre lacuna is clear, padding is black. The order comes from
the operating system's random source, so it cannot be rebuilt from the repository. The key is at
`F:/lcn-quant-keys/validation_tiles_key.csv`, outside the repository.

## P1 rejected candidates (overview F1, contact sheets F2)

Rejected pieces of at least 150 px² after the re-merge, with the filter that rejects each by the stage
replay of `experiments/task2_thresholds.py` (verdict): 542_z06 12, 542_z18 2, 543-2 0, 543_3 4,
543_z13 1, 682_z08 10, 682_z23 6, 682_z29 7. The three named cases come out as expected: 543_3 near
(40,310) A (aspect 6.03), 542_z06 near (230,300) S (solidity 0.452), 542_z06 near (5,930) a (301 px²).

Round 1 (542_z06 overview at 1000 px and 100%): the grey dashed outlines (0.6 pt) were nearly invisible
over bright structures; only the letters showed. Fix: a thin black halo under the dashes (also under
the dotted `-r` layer). An empty band above the caption: smaller. Contact sheet with rejected
candidates: the count lines of neighbouring panels ran into each other, and the second legend row was
cut by the caption. Fix: the image name as a bold title above each panel, the two count lines below,
and every legend strip sized from its measured number of rows.

Round 2: the 542_z06 overview, the 682_z08 overview and the contact sheet with rejected candidates are
clear at 1000 px.

`-r` on 543_3 (`F1_543_3_low_cut_layer`): 4 objects are kept only at 0.8 times t_hi; three coincide with
rejected candidates (the A body at (40,310) among them). The dim star-shaped cells of 543_3 are not
found even at 0.8 times t_hi.

Remaining: in the 682 images several small "a" pieces sit along the top frame edge and their letters
crowd there. Panel C and the inset of the overview are still in the old style (P2, P5, P7).

## P2 one colour, one meaning

Changed: frame-edge yellow is Okabe-Ito #F0E442 everywhere; root dots are magenta (were yellow); the
overview inset box is white (was yellow) and the inset frame black; the switch examples (F5) use the
network overlay (raw at 85%, vermillion and white vector skeleton, magenta roots, dashed 30 px ring)
instead of the white skeleton on the image at 60%; F3, F4 and F5 have a legend inside the figure (F3 a
key for the black default frame, F4 the image dot and the blue field-mean bar). The F5 values (area,
roots, ring 30) are unchanged and equal the switch-check output; the drawn dots and vermillion pixels of
both states are asserted against each run.

Round 1 (F5, F3, F4 and the 543-2 overview at 1000 px): no overlap or clipping; every key in each
legend matches what is drawn. The F3 count lines still use the old wording (P6). Remaining: panel C of
the overview is still the old white skeleton on the image at 60% (P5).

## P3 names

Figure ids: Fig01 contact sheet, Fig02 network overlay of 543-2 (a copy of `per_image/543-2/network`),
Fig03 threshold sensitivity, Fig04 per-field plot; S01 switch examples, S02 contact sheet with rejected
candidates, S03 coded contact sheet. The flat files were renamed with `git mv`; the per-image overviews
move to `per_image/<image>/overview` in O1. Fields are Field 1 to Field 4 in Fig04 and the captions
(field-summary still writes F1 to F4 in its own csv; the figure maps them).

Round 1 (Fig04 at 1000 px): the four "Field n" tick labels ran into each other in the 25 mm panels.
Fix: two rows of panels (3 + 2), each 49 mm wide. Round 2: clear.

## P4 per-field plot

All y axes start at zero; every dot carries its short image name; 682_z08 is an open diamond; `-m`
writes `Fig04_per_field_merged` with 682_z08 in Field 4. The grouping of field-summary is not changed.
Checks: the image values equal `results/summary_table.csv` (roots, ring 30, field density) and the means
over interior lacunae of the default run (the two normalised measures, which results/ predates); the
unmerged field means equal `field_summary.csv`.

Round 1 (both at 1000 px and 100%): the image labels sat on the blue mean bars; the legend touched the
tick labels of the second row. Fix: shorter bars, labels right of the bar with a thin grey leader to
their dot (spread apart when values are close), a taller bottom margin. Round 2: clear; the legend of
the merged figure now says that 682_z08 is merged by hand.

Remaining: from zero, the field differences in field density and ring density look small, which is the
intended reading; the labels of three close values (Field 2) need their leaders to be read.
