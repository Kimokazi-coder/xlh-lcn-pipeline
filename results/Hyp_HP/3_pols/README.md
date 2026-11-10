# 3_pols: Hyp_HP

Candidate POL measure: lacunar size, pending definition, the non-AI run. Pre-validation: no lesion is called here.

The working POL definition (docs/METHODS.md 24.0, to be confirmed by Dr.
Murshed): a periosteocytic lesion is the enlarged, dye-filled lacunar space,
and its footprint is the lacuna as the lacuna stage outlined it. Each image's
own POL files are in its folder, `<image>/non_ai_run/3_pols/`:

- `<image>_pols_outlines.png`: every lacuna outlined on the original image
  with its id and area in um2: green normal size, yellow above 2 x the WT
  median lacunar area (enlarged), cyan a cluster, grey touching the frame
  (not measured); excluded regions shaded grey.
- `<image>_pols_lacunar_size.png`: each measured lacuna filled with the colour
  of its ratio to the WT median.
- `<image>_pols_lacunar_size.csv`: id, area_um2, ratio_to_WT_median, flag,
  cluster.

The same picture with a plain explanation beside it is
`<image>/non_ai_run/summary/<image>_pols_explained.png`. Here, for the whole
group:

- `pols_all_images.csv` and `.xlsx`: per image, the size statistics and the
  POL metrics.
- `contact_sheet.png`, `contact_sheet_outlines.png`: every picture, small.

The ratios are against the WT median lacunar area (36.79 um2, every
measured WT lacuna pooled). Across groups:
`results/summary/pols_lacunar_size_by_group.csv`. Made by
`python src/pols.py all`.
