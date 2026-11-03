# POL as a section: report on the layout

**POL proxy, pre-validation**, 2026-11-03. File layout and pictures only: no measure, flag or
value changed. The yellow zone is the proxy of [DEFINITION.md](DEFINITION.md), mostly optical glow
([FINDINGS.md](FINDINGS.md)), never a lesion call.

**What moved.** The old `results/<group>/pols/` held, per group, two tables, a run record and one
overlay per image. Now POL is a section of each image like `1_lacunae/` and `2_canaliculi/`:
`results/<group>/<image>/4_pols/` holds `_pols_overlay.png` (QC overlay), `_pols_measured.png` (the
review picture: band tinted on measured lacunae, flagged ones orange with their letters),
`_pols_outlines.png`, `_pols_per_lacuna.csv` (the old columns, this image's rows) and `_pols.json`.
Per group, `all_images/pols/` holds `pols_all_images.csv` and `.xlsx` (the old per-image table) and
`contact_sheet.png`. The 35 measured pictures are also in `results/blind_review/pols/` as P001 to
P035; the key is outside the repository and not committed. The old folders were removed in their
own commit (they stay in the history, last at 59d5d43), with the old grey overlays.

**What was checked** (`python src/pols.py check`, table in [layout_check.csv](layout_check.csv)):
35 of 35 images PASS with the old tables still in place. Every image has its five files; every
per-lacuna csv equals the old table's rows for that image, value for value; every
`pols_all_images.csv` equals the old per-image table byte for byte; and each picture, drawn again
from the csv read back, equals the saved file, so the flags drawn are the csv's. Every picture
equals the original off its drawing (checked on save). `summary_by_group.csv` is unchanged. The
check passes again after the removal. `selftest`: 18 of 18. Regression: PASS before every push.

**Not done, or worth knowing.**
1. The blinded set is blind only for a reviewer given that folder alone: each picture is a byte
   copy of a `4_pols` picture that is on GitHub under its image name.
2. The image labels inside `4_pols/`, as in the other sections, still carry genotype and diet
   (`548_hyp_HP_z14c1-2`).
3. `4_pols` shares the number 4 with `4_archive_not_used` (not tracked, written by the figures).
4. In dense fields the legend can cover an id, since every corner holds one (542_z06 #18, 701_z19
   #36, #37); the id is still drawn on top.
5. The pictures take 140 MB; each regeneration that changes them adds that much to the history.
6. Only a sample was looked at by eye (542_z06, 701_z19, the WT contact sheet). The decisions in
   [REPORT.md](REPORT.md) are still open.
