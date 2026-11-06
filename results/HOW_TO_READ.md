# How to read the results

**Pre-validation.** Nothing here is checked against manual counts yet, the
animal mapping is not confirmed, and the POL definition is a working one, to
be confirmed by Dr. Murshed.

**The pictures.** Each group (WT, WT_HP, Hyp_RD, Hyp_HP) has a folder
`results/<group>/0_key_results/` with three pictures per image, sorted by
image:

1. `<image>_1_lacunae_outlines.png`: every lacuna the pipeline found,
   outlined in green on the original image.
2. `<image>_2_canaliculi_verification.png`: the canaliculi it traced, each
   lacuna's threads in their own colour.
3. `<image>_3_pols_outlines.png`: the POL footprints, each lacuna as
   outlined, with its id and area in um2. Colours: **green** normal size,
   **yellow** larger than 2 times the WT median lacuna (an enlarged lacuna, a
   candidate POL), **cyan** a cluster of merged lacunae, **grey** touching the
   frame (area cut, not measured). Areas shaded **grey** are excluded: a
   saturated band at a tissue border or a very large bright structure, not
   analysed. The bar is 10 um.

They are copies; the originals stay in the sections `1_lacunae/`,
`2_canaliculi/` and `3_pols/` beside them.

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
