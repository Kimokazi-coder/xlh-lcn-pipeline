# Figures v2 progress

ALL DONE

base SHA: 867338079ce8a9c97cd69c1551ca42e68fb1bebb (publication-fixes tip)
last update: 2026-10-02 21:40
next action: none. Every item is done; see docs/FIGURES_V2_REPORT.md.

Status values: TODO, DONE, PARTIAL, FAILED, SKIPPED. The commit SHA is the commit that holds the
item's code and outputs. UNPUSHED after an id means its push failed and is retried at the next commit.

| id | description | status | commit SHA | note |
|---|---|---|---|---|
| 0.1 | Branch figures-v2 and this file | DONE | 33bb648 | branch from publication-fixes 8673380 |
| N0 | Shared drawing code: palette, vector skeleton, ring classifier, legend strip | DONE | b70e6f7 | PALETTE, skeleton_segments (8-neighbour forward segments, 3 to 10 lone px per image drawn as 1 px dashes), ring_classes (canaliculi.nearest_lacuna_map, same rule), legend_strip, image_data cache checked against results/; make_figures.py check PASS on all 8 |
| N1 | Network overlay figure per image (543-2 first, then 7) | DONE | 46e73db | per_image/<image>/network.png and .pdf for all 8, inset.json, network_check.json; vermillion px = ring_length_r30_px and dots = roots_count asserted per lacuna; 0.3 pt full field, 0.5 pt insets; two review rounds (count line, letter corners); comparison with the old verification image in figures/REVIEW_V2.md |
| N2 | Cell gallery per image | DONE | 380d0e9 | per_image/<image>/gallery.png and .pdf for all 8 (one page each, 8 to 13 tiles), gallery_check.json; dots = roots_count and vermillion px = ring_length_r30_px asserted per tile; 257 mm wide at true 3x; two review rounds (legend rows, c key) |
| N3 | Hand-count validation tiles | DONE | 08d0a14 | 86 raw red tiles T001 to T086 in random order (system random source), annotation_template.csv, README.md; key outside the repo at F:/lcn-quant-keys/validation_tiles_key.csv; in-repo key path refused; PNG pixel data only; pixels equal the raw files |
| P1 | Rejected candidates in overview and contact sheet | DONE | 241bb60 | overview panel B and F2_contact_sheet_rejected (S02 in O1) draw rejected pieces >= 150 px2 grey dashed with A/S/a; 543_3 (40,310) A, 542_z06 (230,300) S, (5,930) a as expected; count line in the P6 wording; -r layer (0.8 t_hi) to a separate file, made for 543_3; captions say dim out-of-plane cells are not drawn; plain contact sheet keeps kept lacunae only (Decisions needed) |
| P2 | One colour per meaning in every figure | DONE | 9179f71 | palette constants (edge #F0E442, roots magenta, inset box white); F5 redrawn in the network overlay style with asserted dots and ring px (values unchanged); legends inside F1, F2, F3, F4, F5; captions.md rewritten with a colour table; one review round, no defect |
| P3 | Names: Field 1 to 4, Fig01 and S01 ids | DONE | ad8b4bc | git mv to Fig01, Fig03, Fig04, S01, S02, S03 (flat until O1); Fig02 copied from per_image/543-2/network; Field 1 to 4 in Fig04 (two-row layout so labels fit) and captions; METHODS section 9 names updated; FIXES_REPORT and REVIEW.md keep the old names (they record the earlier state) |
| P4 | Per-field plot: zero axes, labels, 682_z08 diamond, -m merged | DONE | 5d9811c | y from zero, image labels with leaders, 682_z08 open diamond with the caption sentence, -m writes Fig04_per_field_merged; dots asserted against results/summary_table.csv and the default run, bars against field_summary.csv; two review rounds |
| P5 | Skeleton panel of the overview in the N1 style | DONE | 5fdc27e | panel C and the inset in the network overlay style (dots asserted), caption line states all skeleton pixels are drawn; captions.md updated; two review rounds |
| P6 | Count line and canal mark "c" | DONE | 8bee8d7 | count line in overview, network, gallery header, contact sheets, Fig03 (per cut, with rejected counts); c marks 8 lacunae incl. 682_z08 L1 top edge, 542_z06 (555,149), 682_z23 (363,7); classification unchanged; two review rounds |
| P7 | Inset rule with frame margin and overrides file | DONE | c93151e | eligibility as N1 (bbox >= 60 px from the frame), roots closest to the median, then area closest to the median area, then smallest id; figures/inset_overrides.csv header only, read when present (tested); logged in per_image/<image>/inset.json; 543-2 inset L4 (edge) to L6 |
| P8 | Per-image display window variants | DONE | 215a978 | variants command: overview, network, gallery with the image's own 1st and 99.8th percentile window into per_image/<image>/display_variants/ (PNG only, Decisions needed) with the note in the figure; main per-image figures keep the fixed window and state it; captions.md window section; two review rounds |
| O1 | Reorganize figures_out/ with README and INDEX | DONE | c7118fe | git mv into main/, supplement/, per_image/<image>/overview; stale F1_*_inset.json removed; script paths updated (fig_stem); thumbs command writes _thumbs/ (600 px, full colour) and INDEX.md; README.md by hand; every command finds its outputs |
| O2 | results_experiments/INDEX.md | DONE | 3d7eb65 | question to file map with one-line answers for task0 to task6 and fixes/; every linked path checked to exist; folders not renamed |
| O3 | docs/START_HERE.md and README pointer | DONE | 3c58af0 | one page: what the pipeline is, folders, reading order, the three branches (nothing merged into main, merging is Karim's decision), switch table with defaults, commands; README gains one line at the top (2 added lines, nothing else changed) |
| O4 | make_figures.py all | DONE | 9797375 | all [-k TILES_KEY] [-b BLIND_KEY] [-f FIELD_DIR] regenerates every output in its folder, then thumbs and INDEX.md, and prints step, status (written, skipped, kept, failed, missing) and file; on the full tree 122 skipped and 3 kept without keys; after deleting one gallery PNG only that gallery and its thumbnail were written |
| 7.1 | docs/FIGURES_V2_REPORT.md, METHODS section, checks, ALL DONE | DONE | becb291 | report with before and after, the 8 points, assertions, weak points, blocked items, Decisions needed; METHODS section 10; reference-check, regression (2 runs), src and results guards all passed before the push; links pinned to becb291 added in the next commit |
