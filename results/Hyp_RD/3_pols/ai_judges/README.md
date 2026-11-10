# 3_pols/ai_judges: Hyp_RD

Candidate POL measure: lacunar size, pending definition, the AI judges run (**AI lacuna and POL judges on**).
Pre-validation: no lesion is called here, and no verdict of a judge is
validated.

The AI lacuna judge was shown every candidate region of the lacuna stage and
said which are lacunae, keeping enlarged lacunae and clusters; the AI POL
judge then looked at every lacuna above 76.6 um2, every cluster and every
pair closer than 3 um, joined pieces of one body, set the cluster flag and
removed what is no lacuna (docs/METHODS.md 29 and 30). Neither draws a
boundary. Each image's own POL files are in its folder,
`<image>/ai_judges/3_pols/`, the same files as in the non-AI run, with the
POL judge's log in `ai_log/` there (what it was shown and what it said). The
comparison with the non-AI run is in `<image>/comparison/`. Here, for the
whole group:

- `pols_all_images.csv` and `.xlsx`: per image, the size statistics and the
  POL metrics.
- `contact_sheet.png`, `contact_sheet_outlines.png`: every picture, small.

The ratios are against the WT median of this run (36.79 um2), so
each run is measured against its own reference group. Made by
`python src/pols.py all --set ai_judges`.
