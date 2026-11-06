# Progress: finishing the pipeline (2026-11-06)

Pre-validation. Brief of 2026-11-06, unattended run. This file says where the
run is, so it can be resumed after a crash. Logs in `.cache/loop_logs/final2/`
(git-ignored). DEV mode for all development work; held-out images and rows are
not opened, printed or summarized before phase 7. Nothing outside the
repository is moved, copied or deleted.

| phase | state | note |
| - | - | - |
| 0 pull | done | already up to date at 8bd05f1; statsmodels 0.14.4 and patsy 1.0.3 installed into venv/ (asked for by the brief; no pip cache, temporary files in .cache/) |
| 1 POL definition | done | METHODS 24.0 and results/README.md |
| 2 replace the cap | done | structure rule (config g9) on, band rule g8 off; cluster flag; CAP_V2.md: wrong over 150 um2 8 before, 7 after, no real lacuna removed; regression against the v1 results differs only in band_blob_rule and the new fields (cluster, excluded_area_px2, analysed_field_area_px2), every measured value identical on the 6 WT development images; pols selftest 12/12, holdout-check 13/13. The committed results are still v1 until the dev rerun of phase 4 and the FINAL run of phase 7 |
| 3 excluded regions | done | excluded region = saturated border regions and very large structures with 3 um margin (config g9), masked out of every field area in quantification; picture and mask per image in 1_lacunae; dev rerun of lacunae, canaliculi and quantification (DEV mode, held-out outputs untouched, the group tables hold dev rows only until phase 7); 12 of 27 dev images have one; reviewer: no real lacuna under the grey on 11 of 12, one borderline at the rim (EXCLUDED_REGIONS.md); regression PASS both runs against the regenerated WT results |
| 4 POL metrics and picture | not started | |
| 5 animals and statistics | not started | |
| 6 key results view | not started | |
| 7 freeze and final run | not started | |
| report | not started | |
