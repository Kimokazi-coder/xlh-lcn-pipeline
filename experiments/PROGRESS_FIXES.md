# Publication fixes progress

ALL DONE

last update: 2026-10-02 13:02
next action: none. Every item is done; see docs/FIXES_REPORT.md.

Status values: TODO, DONE, PARTIAL, FAILED, SKIPPED. The commit SHA is the commit that holds the
item's code and outputs. UNPUSHED after an id means its push failed and is retried at the next commit.

| id | description | status | commit SHA | note |
|---|---|---|---|---|
| 0.1 | Branch publication-fixes and this file | DONE | 506de42 | branch from overnight-fixes ef04398 |
| A2 | Output-directory option -o for both features and the summary writer | DONE | 00f5ff1 | -o added as short name for --out; folder run writes the summary there; check run into _cache identical to results/543-2 |
| A6 | Subcommand regression: regenerate all 8 and compare with results/ at tolerance 0 | DONE | a34ef0a | PASS before any other change: 3861 numbers over 8 images at tolerance 0, 2 min; catches planted differences; now part of the pre-push check |
| F0 | figures/make_figures.py with the shared style | DONE | 43e4f4b | figures/make_figures.py: Arial, 7 to 9 pt at 180 mm, fonttype 42, PNG 300 dpi plus PDF, cyan/yellow outlines 0.7 pt, white skeleton on raw at 60%, 200 px bar; window 20 to 255 of 255 (1st and 99.8th percentile pooled) |
| F1a | Per-image figure for 543-2, viewed and reviewed | DONE | ad7399f | raw, outlines with numbers and count, white skeleton with 3x inset of lacuna 4 (rule: roots closest to median 7.5, tie to smallest id); two review rounds, numbers moved beside the lacunae |
| A1 | Provenance block in every json output; requirements.txt | DONE | c0e3f3e | provenance block (git commit, dirty flag, versions, config hash) in both json outputs, no timestamps; requirements.txt pinned, Python 3.9.10 |
| A3 | Normalised measures as appended columns | DONE | 8531b3a | 8 columns appended to per-lacuna rows, per_lacuna sheet and summary table; regression PASS (existing 3861 numbers unchanged); 784 values equal experiments/task4; METHODS section 9 |
| 7.0 | Draft docs/FIXES_REPORT.md | DONE | c8deab9 | docs/FIXES_REPORT.md drafted from pass 1 |
| A4 | Switches NARROW_CRUMB_RULE, FILL_ENCLOSED_HOLES_MAX_PX2, BAND_FILTER_MIN_OPENING_SHARE; subcommand switch-check | DONE | 438a571 | NARROW_CRUMB_RULE, FILL_ENCLOSED_HOLES_MAX_PX2=0, BAND_FILTER_MIN_OPENING_SHARE=None; switch-check equals the overnight report: crumb only 543_3 (877,545), holes only 542_z06 (783,581), band only the two objects |
| A5 | Switch FAST_LACUNA_STAGE; identical labels; timing | DONE | 0c415df | bounding-box watershed and re-merge in src/lacunae.py behind FAST_LACUNA_STAGE (off); 40 of 40 identical labels at t_hi 0.8 to 1.2; regression PASS both ways; 542_z06 70.2 s to 2.8 s, all 8 regenerated in 125 s vs 8 s |
| B1 | Subcommands blind and unblind; leak test | DONE | f378c60 | blind refuses keys inside the repo; pixel data only, constant alpha dropped so all copies look alike; 0 original names in 76 outputs and logs; unblinded numbers equal the normal run (128 cells, 4837 json fields); .gitignore key patterns added |
| B2 | Subcommand sensitivity | DONE | 35c8bf1 | t_hi, t_lo, both at 0.8 to 1.2 and a pooled raw-unit cut; CSV and markdown; equals the overnight 2.4 grid; 128 runs in 32 s with the fast stage |
| B3 | Subcommand field-summary | DONE | 105535f | fields from centroid matching (25 px, largest-gap cut 0.58, guard 0.5): 542 pair, 543 triple, 682_z23+z29, 682_z08 alone, as overnight 6.1; per-field means incl. normalised measures; same result with and without -r |
| F1b | Per-image figures for the other 7 images | DONE | 7f24b11 | 7 more per-image figures, inset by rule; two review rounds (edge numbers kept inside the frame); figures use the fast lacuna stage (identical output) |
| F2 | Contact sheet of all 8 images | DONE | 45e8ee9 | 2 x 4 sheet, fixed window, 0.6 pt outlines and counts; -b -k labels with codes; two review rounds |
| F3 | Threshold sensitivity figure | DONE | d79dbd6 | 3 images x t_hi 0.8 to 1.2, default boxed, counts equal the overnight grid; two review rounds |
| F4 | Per-field plot | DONE | d79dbd6 | 5 panels (roots, roots per 100 px, ring 30, ring density 30, field density) by data-derived field, dots images, bar mean, n images; no test; two review rounds |
| F5 | Supplementary figure: crumb rule and hole fill | DONE | 45e8ee9 | 543_3 (877,545) crumb rule off/on and 542_z06 (783,581) hole fill off/on beside raw crops; values equal switch-check; two review rounds |
| F6 | Self-review of every figure; captions | DONE | 6670a44 | all 13 PNG reviewed at 1000 px (two rounds where defects were found); PDFs embed TrueType, no Type 3; captions.md with window, colours, fields, pre-validation, px, WT |
| 7.1 | Final report, METHODS and README sections, checks, ALL DONE | DONE | 57bcc7e | FIXES_REPORT final with switch table, commands, blocked items and Decisions needed; METHODS section 9 and README usage appended; links pinned to 57bcc7e added in the next commit; all checks passed before the final push |
