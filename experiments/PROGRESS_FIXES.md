# Publication fixes progress

last update: 2026-10-02 11:35
next action: F0 figures/make_figures.py with the shared style (fixed window, fonts, colours, scale bar).

Status values: TODO, DONE, PARTIAL, FAILED, SKIPPED. The commit SHA is the commit that holds the
item's code and outputs. UNPUSHED after an id means its push failed and is retried at the next commit.

| id | description | status | commit SHA | note |
|---|---|---|---|---|
| 0.1 | Branch publication-fixes and this file | DONE | 506de42 | branch from overnight-fixes ef04398 |
| A2 | Output-directory option -o for both features and the summary writer | DONE | 00f5ff1 | -o added as short name for --out; folder run writes the summary there; check run into _cache identical to results/543-2 |
| A6 | Subcommand regression: regenerate all 8 and compare with results/ at tolerance 0 | DONE | a34ef0a | PASS before any other change: 3861 numbers over 8 images at tolerance 0, 2 min; catches planted differences; now part of the pre-push check |
| F0 | figures/make_figures.py with the shared style | TODO |  |  |
| F1a | Per-image figure for 543-2, viewed and reviewed | TODO |  |  |
| A1 | Provenance block in every json output; requirements.txt | TODO |  |  |
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
