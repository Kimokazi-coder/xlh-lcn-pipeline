# Figure captions (draft)

Drafts for every figure in `figures_out/` (PNG at 300 dpi and PDF). Main figures are Fig01 to Fig04,
supplementary figures S01 to S03; fields are called Field 1 to Field 4, so no field name looks like a
figure name. Every caption applies these common
facts: **pre-validation** (nothing has been checked against manual counts); **pixel units** (the images
carry no spatial calibration, so lengths are px, areas px² and densities px⁻¹, and every scale bar is
in pixels); **wild type (WT) only**: 8 confocal optical sections, which `field-summary` groups into
4 fields from the data (542_z06 + 542_z18; 543-2 + 543_3 + 543_z13; 682_z23 + 682_z29; 682_z08
alone, probably the same field as 682_z23 and 682_z29 at another depth, so 3 or 4 fields). All panels
show the default pipeline output (every switch off) unless the caption says otherwise. Dim lacunae that
lie partly outside the focal plane are not detected by the pipeline and are not drawn in any figure.

## Display window

Every image panel uses one fixed display window, computed once over the whole dataset: the 1st and
99.8th percentile of the pooled red channel of all 8 WT images, 20 to 255 grey levels of 255
(`figures_out/display_window.json`). Images are not stretched one by one, so their brightness can be
compared by eye. The window is for display only; no measurement uses it.

## Colours

One colour has one meaning in every figure. Hues are from the Okabe-Ito colour-blind safe set where
the hue was free to choose.

| colour | meaning |
|---|---|
| cyan outline | interior lacuna: counted, and used in every per-cell mean |
| yellow outline | lacuna touching the frame edge: counted, but left out of every per-cell mean |
| grey dashed outline with a letter | lacuna-scale object rejected by a filter (A aspect ratio, S solidity, a area); at least 150 px² |
| vermillion line | skeleton pixel within 30 px of an interior lacuna, the pixels counted in ring length 30 px |
| white line (70% opacity) | every other skeleton pixel, including the ring of a frame-edge lacuna |
| magenta dot, black edge | one root: a distinct thread leaving a lacuna surface |
| white dashed line | the 30 px ring of the lacuna shown in an inset or tile |
| white rectangle | the region shown in an inset |
| "c" after a lacuna number | at least half of the lacuna lies in a flagged canal region; it may be vascular (the classification is unchanged) |
| light blue dotted outline | object kept only when the lacuna cut is lowered to 0.8 times t_hi (optional layer, not the default output) |
| black frame (Fig03) | the default cut |
| blue bar (Fig04) | field mean |

## per_image/<image>/overview (8 figures, one per image)

**Lacunae, rejected candidates and the skeleton in one optical section.** (A) Red channel. (B) Kept
lacunae with their numbers ("c": in a flagged canal region) and the rejected lacuna-scale candidates
(grey dashed; A aspect, S solidity, a area). The count line gives the interior lacunae used in per-cell
means, the lacunae touching the frame and the rejected candidates. (C) The overlay of the network
figure at small size: the image at 85%, every skeleton pixel as a vector line, vermillion within 30 px
of an interior lacuna and white elsewhere, roots of interior lacunae as magenta dots. The white and
vermillion lines are all skeleton pixels, not only the threads attached to counted cells. The white box
marks the inset: one lacuna at 3x with the same overlay, its roots and the dashed contour of its 30 px
ring; the text gives its roots and ring length 30 px. Inset lacuna by a fixed rule, logged in
`per_image/<image>/inset.json`. Scale bar 200 px (uncalibrated). Fixed
display window. Pre-validation, pixel units, WT.

`per_image/543_3/overview_low_cut_layer` is the same figure with option `-r`: objects that the lacuna stage keeps only
at 0.8 times t_hi are added in light blue dotted outlines. This layer is not the default output.

## per_image/<image>/network (8 figures) and Fig02_network_overlay_543-2

`Fig02_network_overlay_543-2` is a copy of `per_image/543-2/network`.

**Network overlay.** (A) Red channel. (B) The image at 85% brightness with every skeleton pixel drawn as
a one-pixel vector line: vermillion within 30 px of an interior lacuna (the pixels counted in ring
length 30 px), white elsewhere (70% opacity); interior lacunae cyan, lacunae touching the frame
yellow; roots of interior lacunae as magenta dots. No colour stands for a cell, and no ownership is
drawn. (C to E) Three interior lacunae at 3x with the same overlay and the dashed contour of the inset
lacuna's 30 px ring (pixels within 30 px whose nearest lacuna is this one). Insets by a fixed rule
among lacunae at least 60 px from the frame: the fewest roots, the roots closest to the image median,
the most roots (`inset.json`). Titles give the pipeline's roots and ring length 30 px; the number of
vermillion pixels and of dots per lacuna equal them (asserted, `network_check.json`). Scale bars 200 px
and 50 px. Fixed display window. Pre-validation, pixel units, WT.

## per_image/<image>/gallery (8 figures)

**Every interior lacuna at the same scale.** One tile per interior lacuna: a 240 px square centred on
the lacuna (zero padded outside the frame) at 3x, with the overlay of the network figure, the tile
lacuna's roots (magenta) and the dashed contour of its 30 px ring. Title: lacuna number, roots, ring
length 30 px, area. Dots and vermillion pixels equal the pipeline numbers (asserted,
`gallery_check.json`). Lacunae touching the frame are not shown; the footnote gives how many. Scale bar
50 px. Fixed display window. Pre-validation, pixel units, WT.

## validation_tiles/ (86 tiles)

**Tiles for counting roots by hand.** One 240 px crop of the raw red channel per interior lacuna, with no
outline, skeleton, dot or number, named T001 to T086 in a random order. The key stays outside the
repository. See `figures_out/validation_tiles/README.md`.

## Fig01_contact_sheet (and S02_contact_sheet_with_rejected_candidates, S03_contact_sheet_coded)

**All 8 WT sections with the kept lacunae.** Red channel with lacuna outlines (cyan interior, yellow
frame edge; "c" beside a lacuna in a flagged canal region) and two count lines under each panel. One
fixed display window for all panels, so the brighter background of the 543 sections is real. Scale bar
200 px (uncalibrated). `S02_contact_sheet_with_rejected_candidates` adds the rejected lacuna-scale candidates (grey
dashed, with A, S or a). The coded version (`S03_contact_sheet_coded`, a blinding test) labels the panels S001 to S008 from a blinding key and
orders them by code; it hides the names, not the appearance. Pre-validation, pixel units.

## Fig03_threshold_sensitivity

**Lacuna count against the lacuna threshold.** Rows: three sections (542_z06, 543-2, 682_z29). Columns:
the lacuna cut $t_\mathrm{hi}$ (upper three-class Otsu cut of each image's own red histogram) scaled by
0.8, 0.9, 1.0 (the default, black frame), 1.1 and 1.2. Outlines as in Fig01; n = lacunae (interior). A
lower cut lowers the count in 542_z06 (16 to 11; bodies fuse or fail a shape filter) and raises it in
543-2 and 682_z29 (12 to 13, 13 to 15). No default is changed. Scale bar 200 px (uncalibrated). Fixed
display window. Pre-validation, pixel units, WT. Full grid, both cuts:
`results_experiments/fixes/B2_sensitivity.md`.

## Fig04_per_field (and Fig04_per_field_merged)

**Per-cell and per-field measures by field.** (A) Roots per cell. (B) Roots per 100 px of lacuna
perimeter. (C) Ring length 30 px per cell (skeleton px within 30 px of each lacuna, each pixel counted
for its nearest lacuna). (D) Ring density at 30 px, $L_{30} / A_{30}$. (E) Field length density (all
skeleton px over the field area minus lacunae). x: fields derived from the data by matching lacuna
centroids across sections (Field 1: 542_z06 + 542_z18; Field 2: 543-2 + 543_3 + 543_z13; Field 3:
682_z08; Field 4: 682_z23 + 682_z29); n = images per field. Black dots: images (each the mean over its
interior lacunae), labelled with the short image name; blue bar: field mean. 682_z08 (open diamond) is
alone in its field by the data-derived grouping, probably the same field as 682_z23 and 682_z29 at
another depth. All y axes start at zero. Sections of one field repeat the same cells, so the field is
the unit; with 4 fields no statistical test is shown. The dots equal `results/summary_table.csv` (roots,
ring 30, field density) and the pipeline run (the two normalised measures), and the bars equal
`field_summary.csv` (asserted; values in `Fig04_per_field_values.json`). Pre-validation, pixel units, WT.

`Fig04_per_field_merged` (option `-m`) is the same with 682_z08 merged by hand into the field of 682_z23
and 682_z29 (Field 4, n = 3). field-summary still keeps it alone; the merged means are computed in the
figure, not by field-summary.

## S01_switch_examples (supplementary)

**Two optional switches, off (default) and on.** (A) 543_3 at (877,545): with the narrow crumb rule
off, a 124 px² middle piece of the lacuna is dropped, the outline splits in two and a thread is traced
across the gap; with it on (`config.NARROW_CRUMB_RULE = True`) the piece rejoins the lacuna (1344 to
1468 px², 6 to 5 roots, ring 30 from 277 to 269 px). (B) 542_z06 at (783,581): an enclosed 146 px² hole
left open by default is filled with `config.FILL_ENCLOSED_HOLES_MAX_PX2 = 200` (3414 to 3560 px²; roots
and ring length unchanged). Left: red channel; middle and right: the image at 85% with the overlay of
the network figure (cyan outline, vermillion and white skeleton, magenta roots, dashed 30 px ring).
Scale bar 20 px (uncalibrated). Fixed display window. Both switches are off by default; on the 8 WT
images each changes only the lacuna shown (`python src/diagnostics.py switch-check`). Pre-validation,
pixel units, WT.
