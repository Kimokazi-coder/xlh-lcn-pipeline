# Figure captions (draft)

Drafts for every figure in `figures_out/` (PNG at 300 dpi and PDF). Every caption applies these common
facts: **pre-validation** (nothing has been checked against manual counts); **pixel units** (the images
carry no spatial calibration, so lengths are px, areas px² and densities px⁻¹, and every scale bar is
in pixels); **wild type (WT) only**: 8 confocal optical sections, which `field-summary` groups into
4 fields from the data (542_z06 + 542_z18; 543-2 + 543_3 + 543_z13; 682_z23 + 682_z29; 682_z08
alone, probably the same field as 682_z23 and 682_z29 at another depth, so 3 or 4 fields). All panels
show the default pipeline output (every switch off) unless the caption says otherwise.

## Display window

Every image panel in every figure uses one fixed display window, computed once over the whole dataset:
the 1st and 99.8th percentile of the pooled red channel of all 8 WT images, 20 to 255 grey levels of
255 (`figures_out/display_window.json`). Images are not stretched one by one, so their brightness can
be compared by eye. The window is for display only; no measurement uses it.

## Colours

Cyan outline: interior lacuna (counted, and used in every per-cell mean). Yellow outline: lacuna
touching the frame edge (counted, but left out of every per-cell mean). White: canalicular skeleton,
one pixel wide, drawn over the image dimmed to 60%. Yellow dots: roots (distinct threads leaving a
lacuna surface). Yellow box: region of the inset. Black frame (F3): the default cut.

## F1_<image> (8 figures, one per image)

**Lacunae and canalicular network in one optical section.** (A) Red channel. (B) The same with the
outlines of the kept lacunae and their numbers; n = lacunae (interior). (C) Skeleton (white) over the
image dimmed to 60%. The yellow box marks the inset: one lacuna at 3x, with its roots as yellow dots.
The inset lacuna is chosen by a fixed rule: the interior lacuna whose root count is closest to the
image's interior median, ties to the smallest id (the choice is logged in `F1_<image>_inset.json`).
Scale bar 200 px (uncalibrated). Fixed display window. Pre-validation, pixel units, WT.

## F2_contact_sheet (and F2_contact_sheet_coded)

**All 8 WT sections with the kept lacunae.** Red channel with lacuna outlines (cyan interior, yellow
frame edge) and the count under each panel: n = lacunae (interior). One fixed display window for all
panels, so the brighter background of the 543 sections is real. Scale bar 200 px (uncalibrated). The
coded version labels the panels S001 to S008 from a blinding key and orders them by code; it hides
the names, not the appearance. Pre-validation, pixel units.

## F3_threshold_sensitivity

**Lacuna count against the lacuna threshold.** Rows: three sections (542_z06, 543-2, 682_z29). Columns:
the lacuna cut $t_\mathrm{hi}$ (upper three-class Otsu cut of each image's own red histogram) scaled by
0.8, 0.9, 1.0 (the default, black frame), 1.1 and 1.2. Outlines as in F2; n = lacunae (interior). A
lower cut lowers the count in 542_z06 (16 to 11; bodies fuse or fail a shape filter) and raises it in
543-2 and 682_z29 (12 to 13, 13 to 15). No default is changed. Scale bar 200 px (uncalibrated). Fixed display
window. Pre-validation, pixel units, WT. Full grid, both cuts: `results_experiments/fixes/B2_sensitivity.md`.

## F4_per_field

**Per-cell and per-field measures by field.** (A) Roots per cell. (B) Roots per 100 px of lacuna
perimeter. (C) Ring length 30 px per cell (skeleton px within 30 px of each lacuna, each pixel counted
for its nearest lacuna). (D) Ring density at 30 px, $L_{30} / A_{30}$. (E) Field length density (all
skeleton px over the field area minus lacunae). x: fields derived from the data by matching lacuna
centroids across sections (F1 542_z06 + 542_z18; F2 543-2 + 543_3 + 543_z13; F3 682_z08; F4 682_z23 +
682_z29); n = images per field. Dots: images (each the mean over its interior lacunae); bar: field
mean. Sections of one field repeat the same cells, so the field is the unit; with 4 fields no
statistical test is shown. Pre-validation, pixel units, WT.

## F5_switch_examples (supplementary)

**Two optional switches, off (default) and on.** (A) 543_3 at (877,545): with the narrow crumb rule
off, a 124 px² middle piece of the lacuna is dropped, the outline splits in two and a thread is traced
across the gap; with it on (`config.NARROW_CRUMB_RULE = True`) the piece rejoins the lacuna (1344 to
1468 px², 6 to 5 roots, ring 30 from 277 to 269 px). (B) 542_z06 at (783,581): an enclosed 146 px² hole
left open by default is filled with `config.FILL_ENCLOSED_HOLES_MAX_PX2 = 200` (3414 to 3560 px²; roots
and ring length unchanged). Left: red channel; middle and right: outline (cyan) and skeleton (white)
over the image at 60%. Scale bar 20 px (uncalibrated). Fixed display window. Both switches are off by
default; on the 8 WT images each changes only the lacuna shown (`python src/diagnostics.py
switch-check`). Pre-validation, pixel units, WT.
