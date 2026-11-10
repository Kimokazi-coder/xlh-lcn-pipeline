# How to read the results

**Pre-validation.** Nothing here is checked against manual counts yet, the
animal mapping is not confirmed, and the POL definition is a working one, to
be confirmed by Dr. Murshed.

**The pictures.** Each group (WT, WT_HP, Hyp_RD, Hyp_HP) has one folder per
image, `results/<group>/<image>/`, with three folders:

- `non_ai_run/`: the method itself.
- `ai_judges/`: the same pipeline with the AI judges on (below).
- `comparison/`: the two side by side.

Each run has one folder per feature (`1_lacunae/`, `2_canaliculi/`,
`3_pols/`, `4_quantification/`, with every file of that feature) and a
`summary/` folder with the four things to look at first:

1. `<image>_lacunae_outlines.png`: every lacuna the pipeline found,
   outlined in green on the original image.
2. `<image>_canaliculi_verification.png`: the canaliculi it traced, each
   lacuna's threads in their own colour.
3. `<image>_key_numbers.png` (and `.csv`): the main numbers of the image.
4. `<image>_pols_explained.png`: the POL footprints, each lacuna as
   outlined, with its id and area in um2, and beside it in plain words what
   we are looking for. Colours: **green** normal size, **yellow** larger than
   2 times the WT median lacuna (an enlarged lacuna, a candidate POL),
   **cyan** a cluster of merged lacunae, **grey** touching the frame (area
   cut, not measured). Areas shaded **grey** are excluded: a saturated band at
   a tissue border or a very large bright structure, not analysed. The bar is
   10 um.

In `comparison/`, each picture shows the non-AI run, the AI run and a third
panel with only what the AI changed (**red** removed, **blue** added,
**yellow** merged or cluster flag changed), for the lacunae, the canaliculi
and the POLs, and `<image>_compare_numbers.png` puts the key numbers of both
runs side by side with the difference. `results/<group>/0_key_results/` still
holds the three key pictures of every image of the group in one place (non-AI
run).

**The numbers.** One file, `results/SUMMARY.xlsx`. Its sheet **Read me**
says in one line what every column means. **Per group**, **Per animal** and
**Per image** hold the same columns at three levels; **Statistics** holds the
genotype by diet models. The numbers that matter most:

- `share_above_2x_WT_median`: the share of lacunae that are enlarged.
- `area_um2_p90`: the 90th percentile of lacunar area (the large end).
- `pol_area_per_analysed_area`: the share of the analysed field taken by
  lacunar space.
- `area_um2_median`, and for the canaliculi `roots_per_lacuna` and
  `field_length_density_um_per_um2`.
- In **Statistics**, the animal-level rows: `estimate` is the genotype by
  diet interaction, `ci_low` to `ci_high` its 95% interval, and
  `what_it_says` the result in plain words. There are 3 animals per group, so
  read the interval, not the p value.

The full statistics are in `results/summary/STATISTICS.md`.

**The AI judges (a second, optional reading).** The `non_ai_run/` folders
are the method itself. The `ai_judges/` folders are the same pipeline with
two AI judges on: an AI model looked at every outline the pipeline drew and
said which are real lacunae (keeping enlarged lacunae and clusters, rejecting
fragments, bands, tissue and saturated border pieces), and then, the POL
judge, looked closely at every large lacuna, every cluster and every pair of
lacunae closer than 3 um: it joined lacunae that are pieces of one body,
flagged clusters, and removed a few more pieces that are no lacuna. Neither
draws an outline itself, and the canaliculi are traced by the normal method
around the lacunae they kept. The sheet **Judge on vs off** of
`SUMMARY.xlsx` puts the runs side by side for the development images, per
group (column "lacuna and POL judges on"): in plain words, the judges remove
many more outlines in the Hyp groups, mostly band, tissue and saturated
border pieces and fragments, so the POL area per analysed area falls most in
Hyp. Its column "both judges on" is a third judge, of the canaliculi, whose
results are no longer in these folders (`docs/METHODS.md` 32). Some group
differences are small enough that the judges change their direction (see
`docs/METHODS.md` sections 29.4 and 30). The judges are not validated: read
them as a check on how much the result depends on which outlines count, not
as the result.
