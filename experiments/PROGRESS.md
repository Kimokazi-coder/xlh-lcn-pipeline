# Overnight progress

last update: 2026-10-01 15:51
next action: 2.3 both cuts x0.9 and x1.1 on 542_z06, 543-2, 682_z29 with the fast lacuna copies.

Status values: TODO, DONE, PARTIAL, FAILED, SKIPPED. The commit SHA is the commit that holds the
item's code and outputs. UNPUSHED after an id means its push failed and is retried at the next commit.

| id | description | status | commit SHA | note |
|---|---|---|---|---|
| 0.1 | Branch, experiments/README.md and PROGRESS.md | DONE | b74daea | branch created from main 677ccd6 |
| 0.2 | Default-result cache on all 8 images, and timing | DONE | a40e8ce | pipeline alone: 8.7 s (543-2) to 77.5 s (542_z06) per image, 275 s for all 8 in sequence (540 s with the cache step). Lacuna stage dominates (watershed and re-merge loops); network stage from cache 2 to 4 s. common.lacuna_stage and network_stage reproduce the pipeline exactly on all 8 (task0/verify.csv). (x,y)=(col,row) confirmed. |
| 1.1 | TIFF tags of all 8 images | DONE | 060adfa | all 8 are 8-bit RGB exports with no microscope metadata; 7 by ImageJ 1.54p without resolution; 542_z06 RGBA LZW 300 dpi from another program; no histogram combing |
| 1.2 | 2D FFT peaks and row and column banding, raw and preprocessed | DONE | 05c67c0 | no lattice-scale peak above the noise reference (about 18); pixel-scale artefacts in all 8 raw images: alternating columns (period 2 px, 0.10 grey levels) and period 4 px along x (0.15 grey levels); both shrink after preprocessing |
| 1.3 | Axis-aligned skeleton runs; 682_z08 lattice crops; where the lattice comes from | DONE | a65e531 | lattice is in the raw data (visible threads), not made by preprocessing; no lattice-scale period; orientations broad (no spike at 0 or 90 deg); same box elevated in all three 682 images (0.33 to 0.36 vs 0.21 to 0.23); most likely tissue; what the horizontal threads are is for Karim |
| 2.1 | Which stage rejects the visibly missed bodies | DONE | e5cbc4f | none lost at the cut: 543_3 (40,310) aspect 6.03 > 6.0 (body plus tail); 542_z06 (230,300) solidity 0.452 < 0.5; 542_z06 (5,930) area 301 < 400 at the frame edge |
| 2.2 | t_hi and t_lo against image brightness statistics | DONE | 1141c49 | t_hi 0.523 to 0.647, tracks saturated fraction (rho 0.98) and p99, not mean; t_lo is 0.18 to 0.20 of the preprocessed p99 in every image, i.e. 2.7 fold range in raw units |
| 2.3 | Quick sensitivity, both cuts x0.9 and x1.1, on 3 images | TODO |  |  |
| 3.1 | Crumb loss audit: kept lacuna against its pre-watershed component | DONE | 04b3a10 | 93 of 98 lose nothing; 4 miss > 3% of their component: 542_z06 (555,149) band object 64%, 542_z06 (106,67) leaked outline 42%, 542_z18 (938,990) 32%, 543_3 (877,545) 8%; all dropped for area; plus 23 px unlabelled by 4-connected watershed in 542_z06 (909,17) |
| 3.2 | Saddle audit: straight line against widest path | TODO |  |  |
| 3.3 | Band objects: minor axis, flagged overlap, solidity | TODO |  |  |
| 3.4 | Tails and serrated edges: opening r 2, 3, 4 (lacuna level) | TODO |  |  |
| 3.5 | Unfilled holes up to 200 px^2 (lacuna level) | TODO |  |  |
| 4.1 | Size confound: ring area, in-frame fraction, normalised measures | TODO |  |  |
| 5.1 | Field density three ways | TODO |  |  |
| 5.2 | Green and blue channels; draft bone ROI | TODO |  |  |
| 5.3 | 542_z06 vertical trace near x 525, y 590 to 900 | TODO |  |  |
| 6.1 | Repeatability across matched cells; field groups from data | TODO |  |  |
| 7.1 | Draft docs/OVERNIGHT_REPORT.md | TODO |  |  |
| 1.4 | Notch filter variant | TODO |  |  |
| 2.4 | Full threshold sensitivity grid on all 8 images | TODO |  |  |
| 3.6 | Network-level effect of variants 3.1 to 3.5 | TODO |  |  |
| 3.7 | Before and after crops for the worst cases | TODO |  |  |
| 5.4 | ROI overlays for all 8 images; per-image ROI support | TODO |  |  |
| 7.2 | Final report, METHODS section, checks, ALL DONE | TODO |  |  |
