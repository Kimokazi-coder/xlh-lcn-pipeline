# 0_key_results: Hyp_HP

Pre-validation. The three most important pictures of every image of this
group in the non-AI run, copied from each image's folder (the originals, in
`<image>/non_ai_run/`, are not changed), named so they sort by image. Each
image's folder also holds the same pictures with the AI judges on
(`<image>/ai_judges/`), a summary of each run (`summary/`) and the two runs
side by side (`<image>/comparison/`).

- `<image>_1_lacunae_outlines.png`: the lacunae the pipeline found, each
  outlined in green on the original image (from `1_lacunae/`).
- `<image>_2_canaliculi_verification.png`: the traced canalicular network on
  the original image, each lacuna's threads in its own colour (from
  `2_canaliculi/`).
- `<image>_3_pols_outlines.png`: the POL footprints (the working POL
  definition, to be confirmed by Dr. Murshed): green normal size, yellow above
  2 x the WT median lacunar area, cyan a cluster of merged lacunae, grey
  touching the frame (not measured); excluded regions shaded grey; id and
  area in um2 beside each; a 10 um scale bar (from `3_pols/`).

The numbers are in `results/SUMMARY.xlsx`; how to read it all is in
`results/HOW_TO_READ.md`. Made by `python src/key_results.py all`.
