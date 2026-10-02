# Publication fixes progress

last update: 2026-10-02 11:47
next action: A3 normalised measures as appended columns, definitions as experiments/task4_size.py; METHODS section.

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
| A3 | Normalised measures as appended columns | TODO |  |  |
| 7.0 | Draft docs/FIXES_REPORT.md | TODO |  |  |
| A4 | Switches NARROW_CRUMB_RULE, FILL_ENCLOSED_HOLES_MAX_PX2, BAND_FILTER_MIN_OPENING_SHARE; subcommand switch-check | TODO |  |  |
| A5 | Switch FAST_LACUNA_STAGE; identical labels; timing | TODO |  |  |
| B1 | Subcommands blind and unblind; leak test | TODO |  |  |
| B2 | Subcommand sensitivity | TODO |  |  |
| B3 | Subcommand field-summary | TODO |  |  |
| F1b | Per-image figures for the other 7 images | TODO |  |  |
| F2 | Contact sheet of all 8 images | TODO |  |  |
| F3 | Threshold sensitivity figure | TODO |  |  |
| F4 | Per-field plot | TODO |  |  |
| F5 | Supplementary figure: crumb rule and hole fill | TODO |  |  |
| F6 | Self-review of every figure; captions | TODO |  |  |
| 7.1 | Final report, METHODS and README sections, checks, ALL DONE | TODO |  |  |
