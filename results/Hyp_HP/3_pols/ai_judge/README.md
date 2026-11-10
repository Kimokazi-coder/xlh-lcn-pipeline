# 3_pols/ai_judge: Hyp_HP

Candidate POL measure: lacunar size, pending definition, **with the AI lacuna judge on**. Pre-validation: no lesion is
called here, and no verdict of the judge is validated.

The same section as `3_pols/` beside this folder, made by the same code from
the lacunae the AI lacuna judge accepted (`1_lacunae/ai_judge/`,
`4_quantification/ai_judge/`): the judge was shown every candidate region of
the lacuna stage and said which are lacunae, keeping enlarged lacunae and
clusters under the working POL definition (docs/METHODS.md 24.0 and 29). It
never draws a boundary, so every footprint is the lacuna stage's own outline.
A region the judge added that the filters had rejected is the class `judged`
and has no area (flag `no_area`), like the `dim` class.

- `<image>_pols_outlines.png`: the POL footprints, as in `3_pols/`.
- `<image>_pols_lacunar_size.png` and `.csv`: lacunar size per lacuna.
- `pols_all_images.csv` and `.xlsx`: per image, the size statistics and the
  POL metrics.
- `contact_sheet.png`, `contact_sheet_outlines.png`: every picture, small.

The ratios here are against the WT median of the judge-on set
(36.79 um2), so each method is measured against its own reference
group. Made with the method at tag `method-freeze-v2` and the judge rerun of
2026-11-09 by `python src/pols.py all --set ai_judge`. The judge off against
judge on comparison is in the sheet "Judge on vs off" of
`results/SUMMARY.xlsx`.
