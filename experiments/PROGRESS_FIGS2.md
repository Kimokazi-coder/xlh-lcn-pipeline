# Figures v2 progress

base SHA: 867338079ce8a9c97cd69c1551ca42e68fb1bebb (publication-fixes tip)
last update: 2026-10-02 15:05
next action: N2 cell gallery per image

Status values: TODO, DONE, PARTIAL, FAILED, SKIPPED. The commit SHA is the commit that holds the
item's code and outputs. UNPUSHED after an id means its push failed and is retried at the next commit.

| id | description | status | commit SHA | note |
|---|---|---|---|---|
| 0.1 | Branch figures-v2 and this file | DONE | 33bb648 | branch from publication-fixes 8673380 |
| N0 | Shared drawing code: palette, vector skeleton, ring classifier, legend strip | DONE | b70e6f7 | PALETTE, skeleton_segments (8-neighbour forward segments, 3 to 10 lone px per image drawn as 1 px dashes), ring_classes (canaliculi.nearest_lacuna_map, same rule), legend_strip, image_data cache checked against results/; make_figures.py check PASS on all 8 |
| N1 | Network overlay figure per image (543-2 first, then 7) | DONE | | per_image/<image>/network.png and .pdf for all 8, inset.json, network_check.json; vermillion px = ring_length_r30_px and dots = roots_count asserted per lacuna; 0.3 pt full field, 0.5 pt insets; two review rounds (count line, letter corners); comparison with the old verification image in figures/REVIEW_V2.md |
| N2 | Cell gallery per image | TODO | | |
| N3 | Hand-count validation tiles | TODO | | |
| P1 | Rejected candidates in overview and contact sheet | TODO | | |
| P2 | One colour per meaning in every figure | TODO | | |
| P3 | Names: Field 1 to 4, Fig01 and S01 ids | TODO | | |
| P4 | Per-field plot: zero axes, labels, 682_z08 diamond, -m merged | TODO | | |
| P5 | Skeleton panel of the overview in the N1 style | TODO | | |
| P6 | Count line and canal mark "c" | TODO | | |
| P7 | Inset rule with frame margin and overrides file | TODO | | |
| P8 | Per-image display window variants | TODO | | |
| O1 | Reorganize figures_out/ with README and INDEX | TODO | | |
| O2 | results_experiments/INDEX.md | TODO | | |
| O3 | docs/START_HERE.md and README pointer | TODO | | |
| O4 | make_figures.py all | TODO | | |
| 7.1 | docs/FIGURES_V2_REPORT.md, METHODS section, checks, ALL DONE | TODO | | |
