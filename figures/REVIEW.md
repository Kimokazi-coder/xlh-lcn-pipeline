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
