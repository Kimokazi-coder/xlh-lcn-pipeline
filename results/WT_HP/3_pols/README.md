# 3_pols: WT_HP

Candidate POL measure: lacunar size, pending definition. Pre-validation: no lesion is called here.

POLs (periosteocytic lesions) are enlarged lacunae, and there is no agreed
definition of one in these images yet. This section shows the one candidate
that needs no new detection: the area of each lacuna the pipeline measured, in
um2 at 0.13 um/px, and its ratio to the WT median lacunar area (every measured
WT lacuna pooled).

- `<image>_pols_lacunar_size.png`: the original image, each measured lacuna
  filled with the colour of its ratio to the WT median (one scale for every
  group, the colour bar in um2), its id and area beside it; flagged lacunae
  (touching the frame, or of a class with no area) outlined grey, not filled;
  10 um scale bar.
- `<image>_pols_lacunar_size.csv`: id, area_um2, ratio_to_WT_median, flag.
- `pols_all_images.csv` and `.xlsx`: per image, n measured, and the mean,
  median and 90th percentile of area and of ratio.
- `contact_sheet.png`: every picture of the group, small.

Across groups: `results/summary/pols_lacunar_size_by_group.csv`.
Made by `python src/pols.py all` (every group) or
`python src/pols.py measure -d data/WT_HP` (this group only).

The ring proxy this folder held before is retired, because it measured the dye
glow around every lacuna, the same width in WT, and not lesions. Its files are
in `../5_archive/pol_ring_proxy/`.
