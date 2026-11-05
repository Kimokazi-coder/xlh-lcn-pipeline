# Progress: one layout for all four groups

Resume from the first phase not marked done. Each phase is one commit on main,
pushed. The regression check is `python src/diagnostics.py regression` (WT,
tolerance 0), run with the lcn conda environment.

## Target

results/<group>/ for WT, WT_HP, Hyp_RD, Hyp_HP, each with exactly:
1_lacunae, 2_canaliculi, 3_pols, 4_quantification, 5_archive. Files flat,
named <image>_... . results/summary/ holds the cross-group tables,
results/archive/ the group-independent old material.

## Phases

| phase | what | status |
| - | - | - |
| P1 | code writes the new layout (config.py, src/, the figures script) | done |
| P2 | git mv every existing file, MOVE_MAP.csv, lacunae contact sheets | done |
| P3 | publication figures for WT_HP, Hyp_RD, Hyp_HP | done |
| P4 | 3_pols: lacunar size, all groups | done |
| P5 | docs and checks, final report | done |

## Decisions

- Per-image figures: the network figure and its checks go to 2_canaliculi;
  the cell gallery, the overview and the inset choice go to 4_quantification.
- The old ring proxy (4_pols, all_images/pols) goes to
  5_archive/pol_ring_proxy/; its code becomes src/pol_ring_proxy.py and writes
  there if ever rerun.
- The AI judges: the thread judge (results_ai_judge/WT) goes to
  results/WT/5_archive/ai_judge/canaliculi_judge/, the lacuna judge
  (results_ai_lacunae/<group>) to results/<group>/5_archive/ai_judge/lacuna_judge/.
  Their logs are flattened: one ai_log/ folder, every file named <image>_... .
  The group-independent judge files (run records, dry_run, review, the two
  READMEs) go to results/archive/ai_judge/.
- Baseline regression before any change: see below.

## Log
- 2026-11-04: python env is the conda env lcn (versions equal to the recorded
  provenance); imagecodecs was missing (one TIFF is LZW) and was installed.
- Baseline regression on the untouched commit 3a69e66, in a separate worktree:
  FAIL, before any change. 6 of 8 WT images differ in one recorded parameter,
  parameters.canaliculi.network_threshold_t_lo, in the last digits only (for
  example 0.0371566257194509 against 0.037156625719450914); the other 6800
  numbers and the whole summary table are equal; the run with
  FAST_LACUNA_STAGE on shows the same 6. Every later run is reported as the
  command prints it (FAIL) and compared with this baseline: a change added no
  difference when it shows exactly these 6 and no other.
- P1 done: code writes the new layout. Regression against a new-layout copy
  of results/WT in .cache/ref_newlayout: the 6 baseline differences, no other.
  Self-tests: pols 9/9, pol_ring_proxy 18/18, ai-judge stub 15/15,
  validate-network 8/8 (after two fixes: image discovery read per-image
  folders, and an old tuple unpacking bug), ai-lacuna-judge stub 25/26 (the
  cap check over all 35 cached images fails the same way at 3a69e66).
- P2 done: 1877 files moved with git mv (plus the 2 code renames of P1), all
  in results/archive/MOVE_MAP.csv; every moved file has the same git blob as at
  3a69e66. results_ai_judge/, results_ai_lacunae/ and figures/ are gone. Added:
  1_lacunae/contact_sheet.png and 3_pols/README.md per group. layout-check
  PASS for 4 of 4 groups; pol_ring_proxy check PASS 35 of 35 at the new paths.
  Field summaries for P3 in .cache/field_summary/<group>/.
- P3, first attempt interrupted: make_figures.py -g G all built each image's
  full pipeline run one after another (many minutes per Hyp image) and the S01
  switch search would run the full pipeline on every image. Changed: the
  switch search runs the lacuna stage first and the full pipeline only where
  the switch changes the labels. Resume: prebuild the figure cache of every
  image in parallel (8 workers, .cache/figures_v2), then run
  python -u src/make_figures.py -g G all for WT_HP, Hyp_RD, Hyp_HP. A figure
  whose png and pdf exist is skipped, so a rerun continues where it stopped.
- P4 files (3_pols of every group, results/summary/pols_lacunar_size_by_group.csv)
  are generated and checked (python src/pols.py check PASS) but are committed
  after P3. To redo: python src/pols.py all.
- P5 docs drafted while P3 caches build (uncommitted until P5): README.md,
  docs/START_HERE.md, results/README.md rewritten; docs/METHODS.md (section 24
  now lacunar size, the ring proxy retired), docs/EXPERIMENT_AI.md,
  docs/figures/*, the archived judge READMEs updated to the new paths. Short
  options added so the docs need no double hyphen: -d/-i on every stage and
  diagnostic, import-group -g/-s, ai-judge and ai-lacuna-judge -r/-l,
  format-test -t/-s, contact -p/-t/-n/-c/-P, ai-dry-run, glow-check and
  hole-check -p. docs/judge_examples*.md are left as they are: they are loaded
  into the judge prompts, and a change would change the logged prompt hashes.
- P3, second attempt: Fig03 and the S01 switch search now precompute their
  lacuna runs in parallel into .cache/figures_lacuna_runs/ (keyed by the source
  hash; a first version named the files by scale with a dot, so 0.8 and 0.9
  shared a file; fixed and the cache cleared before any figure was drawn from
  it). The machine has 8 GB of memory; 8 workers per group swapped it full, so
  the default is now 3 (LCN_FIGURE_WORKERS). Resume: python -u
  src/make_figures.py -g G all for WT_HP, Hyp_RD, Hyp_HP; everything cached or
  drawn is skipped.
- P3 done: figures for WT_HP, Hyp_RD, Hyp_HP, every per-image figure and the
  six group figures; make_figures.py check PASS on 9 of 9 images in each.
  S01: WT_HP has one row (hole fill; the crumb rule changed 876_z89c1-2 only
  outside the rule), Hyp_RD and Hyp_HP two. Fig04 labels the points of the
  groups other than WT by animal and z plane. WT unchanged.
- P4 done: 3_pols lacunar size for all four groups, pols check PASS, selftest 9/9.
- P5 done: docs rewritten, every check run (results/archive/REPORT_REORG.md).
  This file moved from results/ to results/archive/ with the final commit, so
  results/ holds only README.md, summary/, archive/ and the four groups.
