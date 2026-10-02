# Figure review

Each exported PNG is viewed at 1000 px wide (a column-width preview). Defects found, what was changed,
and what remains. At most two rounds per figure.

## F1_543-2 (per-image figure)

Inset rule: interior median roots 7.5; lacunae with 7 and 8 roots tie, so the smallest id wins:
lacuna 4 (8 roots), the cell at (39,297). Logged in `figures_out/F1_543-2_inset.json`.

Round 1:
- Panel B: the lacuna numbers are drawn on the centroid and hide the bodies they label. Fix: put each
  number beside its lacuna (right of its bounding box, or left near the right frame edge).
- Panel C: the title "skeleton" does not say the background is the raw image dimmed. Fix: a fuller title.
- Inset: legible at 1000 px; the roots (yellow dots) and the outline are visible. The cell sits at the
  left frame edge, so its box in C is at the edge too. No change.

Round 2: numbers now sit beside their lacunae and no longer hide them; the C title names the display.
Remaining, left as is: at column width the 1 px skeleton renders as thin grey-white lines in C (the
PDF holds it at 300 dpi; the inset shows it at 3x); the inset is small but legible.
PDF check: fonts embedded as TrueType (FontFile2), Arial, no Type 3 fonts.

## F1 for the other 7 images (F1b)

Inset lacunae by the rule (interior median roots, ties to the smallest id), logged in
`figures_out/F1_<image>_inset.json`: 542_z06 lacuna 7 (8 roots, median 8), 542_z18 lacuna 3 (8, median
8), 543_3 lacuna 3 (7, median 7), 543_z13 lacuna 2 (7, median 7), 682_z08 lacuna 2 (10, median 9),
682_z23 lacuna 10 (6, median 6), 682_z29 lacuna 5 (5, median 5).

Round 1 (all 7 viewed at 1000 px):
- Numbers of lacunae touching the top frame edge (682_z23 lacunae 1 and 2, 682_z29 lacuna 1, 542_z18
  lacuna 1) sat half outside the panel. Fix: every number kept at least 14 px inside the top and bottom
  edges. All 8 F1 figures redrawn with it.
- Close pairs (542_z06 lacunae 2 and 4, 682_z29 lacunae 9 and 10) stay legible. No change.
- The inset size follows the cell (3x of a square around it), so it is small for small cells
  (543_z13 lacuna 2). No change; the rule fixes the zoom, not the size.
- 543_3 lacuna 6 (877,545) shows its known gap (two outline pieces): the figure shows the default
  output as it is.

Round 2 (682_z23 viewed again): the edge numbers sit inside the frame. Nothing else found.

## F2 contact sheet

Round 1: the eight panels, outlines (0.6 pt) and counts are legible at 1000 px. The fixed display
window shows that the 543 images have a brighter background than the 542 and 682 images; that is the
data, not a display choice. Defect: the "pre-validation" footer sat almost on the last caption. Fix:
a 3 mm footer strip. Round 2: clear.

`-b -k KEY` writes `F2_contact_sheet_coded` (labels S001 to S008, ordered by code; made with the test
key of B1, which lives outside the repository). `-b` without a key is refused.

## F5 switch examples

Round 1: both cases are clear (the thread traced across the 543_3 gap disappears with the crumb rule
on; the 542_z06 hole is filled). Defects: "px^2" written literally in the row B titles, and the value
lines under the off and on panels nearly touched. Fix: "px²", shorter value lines, wider gaps.
Round 2: clear. Values (area, roots, ring 30) equal the switch-check output of A4.
