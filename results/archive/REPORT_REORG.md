# Report: one layout for all four groups (2026-11-04 and 05)

**What moved.** 1877 result files by `git mv`, so history follows each one,
and two code files: `src/pols.py` became `src/pol_ring_proxy.py` and
`figures/make_figures.py` became `src/make_figures.py`. Every group, WT, WT_HP,
Hyp_RD and Hyp_HP, now has `results/<group>/` with exactly five sections,
1_lacunae, 2_canaliculi, 3_pols, 4_quantification, 5_archive, every file named
`<image>_...` and no folder per image. `results_ai_judge/`,
`results_ai_lacunae/` and `figures/` are gone: the judges are in each group's
`5_archive/ai_judge/` and in `archive/ai_judge/`, the figure notes in
`docs/figures/`. Every move is in [`MOVE_MAP.csv`](MOVE_MAP.csv) (1879 rows).

**What was generated, for which group.**
- All four groups: `1_lacunae/contact_sheet.png`; `3_pols/`, now the
  candidate POL measure, lacunar size, pending definition (picture and table
  per image, group table, contact sheet, README); and
  `results/summary/pols_lacunar_size_by_group.csv`.
- WT_HP, Hyp_RD, Hyp_HP: the publication figures, same code and settings and
  the WT display window: per image the network figure (2_canaliculi), overview
  and cell gallery (4_quantification); per group Fig01 to Fig04, S01, S02. The
  images WT chose by hand are chosen by a rule in `src/make_figures.py`.
- WT: nothing regenerated.

**What was checked.**
- Every moved file has its blob of 3a69e66, all 685 tables (json, xlsx, csv)
  among them, so every value is unchanged; nothing was lost. Six docs were
  edited after the move for the new paths (three figure notes, three judge
  READMEs).
- `python src/diagnostics.py layout-check`: PASS, 4 of 4 groups.
- `python -u src/make_figures.py -g G check`: PASS on every image of WT_HP,
  Hyp_RD, Hyp_HP. `python src/pols.py check`: PASS. `python
  src/pol_ring_proxy.py check`: PASS, 35 of 35 at the archive paths.
- Every relative link in every README and in `docs/`: 63 of 63 resolve.
- Tracked top level: README.md, config.py, requirements.txt, .gitignore,
  src/, docs/, data/, results/ and nothing else.
- Self-tests: pols 9/9, pol_ring_proxy 18/18, validate-network 8/8 (it could
  not run before; two fixes), ai-judge stub 15/15; the ai-lacuna-judge stub
  fails one check (the cap over all 35 cached images) exactly as at 3a69e66.
- Regression: FAIL at every phase, the same as the untouched commit 3a69e66
  on this machine: 6 WT images differ in
  `parameters.canaliculi.network_threshold_t_lo` in the last digits only. No
  phase added a difference; 6800 numbers and 312 table cells otherwise equal.

**What is not done.**
- Why the last digits of that one threshold differ on this machine (library
  build or CPU) is not found, so the regression does not pass here.
- Lacunar size is a candidate, not a POL definition. On the groups other than
  WT the lacuna stage also keeps bands and fragments, which lower a group's
  median (Hyp_HP 18.5 um2 against WT 36.7 um2).
- Hyp_HP's S01 crumb rule row changes a ring length (172 to 175 px), not an
  outline: the largest qualifying change in that group, but hard to see.
- Records written before the move (judge logs, run records, the ring proxy
  reports) still name the paths they were written with.
- `docs/judge_examples*.md` keep their HTML comment markers: they are judge
  prompt inputs, and a change would change the logged prompt hashes.
