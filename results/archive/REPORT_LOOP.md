# Report: hold-out, external data and the review loop (2026-11-05)

**Pre-validation.** Every count below is an AI reviewer's judgement on
pictures of the 27 development images, not a manual count; nothing is
validated. Details: [`REVIEW_LOOP.md`](REVIEW_LOOP.md), progress
[`../PROGRESS_LOOP.md`](../PROGRESS_LOOP.md).

**Synced.** The working tree was clean, so nothing was stashed. The pull
fast-forwarded 3a69e66 to 0b0be38 ("POL pass 3: POL_SUMMARY.md"), and all four
groups have sections 1_lacunae to 5_archive. Before any change: regression
PASS on this machine, self-tests pols 12/12, pol_ring_proxy 18/18,
validate-network 8/8, ai-judge stub 15/15, ai-lacuna-judge stub 26/27 (the
known cap check).

**Held-out set** (`data/holdout.json`, [`docs/HOLDOUT.md`](../../docs/HOLDOUT.md),
tag `holdout-locked-2026-11-05`). Seed 20261105, 2 per group, from the file
names only: WT 543-2, 682_z23; WT_HP 876_z82c1-2, 877_wt_z081c1-2; Hyp_RD
535_z20c1-2, I534_z19c1-2; Hyp_HP 701_z19c1-2, 701_z36c1-2. DEV mode (the
default) refuses them; `LCN_HOLDOUT_MODE=FINAL` runs them. They were not
opened, run or reviewed during the loop, and their FINAL outputs were not
opened.

**External data** ([`docs/EXTERNAL_DATA.md`](../../docs/EXTERNAL_DATA.md), in
`F:/external_data/`, not committed). Zenodo 291852 (438 MB, MD5 matches, 20
raw 3D Rhodamine stacks of mouse and sheep bone, 0.195 um/px, CC BY 4.0),
OCY_connectomics (MATLAB, GPL-3.0), OsteocyteNetworkConnectivityAnalysis
(PyTorch code and a model, MIT; its training labels are not published) and
TINA (Bitbucket, MIT, not BSD). **None has manual lacuna outlines, centres or
counts, so none can serve as ground truth.**

**The loop** (27 development images, 8 reviewers per round):

| round | rule (config section) | problems | WT |
| - | - | - | - |
| 0 | baseline | 258 | 12 |
| 1 | rescue rules off (g5) | 225 | 8 |
| 2 | fragment rule: satellite or speck (g6) | 186 | 6 |
| 3 | fragment rule: crumb (g7) | 169 | 10, pictures unchanged |
| 4 | band rule: mask region over 300 um2 (g8) | 153 | 8, pictures unchanged |
| 5 | faint crumb (g9), reverted: WT worse object by object | (152) | (10) |

**Final counts per group** (round 4, the frozen method, tag `method-freeze-v1`):

| group | images | labelled | fragment | band or tissue | split | merged | missed | other | total |
| - | - | - | - | - | - | - | - | - | - |
| WT | 6 | 71 | 5 | 1 | 0 | 0 | 1 | 1 | 8 |
| WT_HP | 7 | 85 | 5 | 11 | 1 | 0 | 5 | 2 | 24 |
| Hyp_RD | 7 | 150 | 26 | 15 | 5 | 1 | 1 | 3 | 51 |
| Hyp_HP | 7 | 149 | 36 | 22 | 6 | 1 | 0 | 5 | 70 |
| all | 27 | 455 | 72 | 49 | 12 | 2 | 7 | 11 | 153 |

**Freeze and final run.** Tag `method-freeze-v1` (d1e0b5c). Then, with
`LCN_HOLDOUT_MODE=FINAL` and the default path (not `--fast`), every image, held
out included: lacunae and canaliculi (35 of 35, no failure, 17 min),
quantification (35), 3_pols, field summaries, the publication figures of all
four groups, `results/summary/group_overview` and `group_qc`. The figures first
failed: `src/make_figures.py` could not name the cut that dropped a piece the new
rules drop; it now marks such a piece `R` (fragment or band rule), and every
figure was drawn (`make_figures check`: 35 of 35 images). Checks: **regression
PASS** in FINAL mode on all 8 WT images (both runs); holdout-check 13/13; pols
check PASS; self-tests pols 12/12, pol_ring_proxy 18/18, validate-network 8/8,
ai-judge stub 15/15, ai-lacuna-judge stub 26/27 (the known cap check; run on
543_3, its default image is held out); layout-check fails for WT only, on 8
untracked per-image folders left on this machine from before the layout change
(none of their files is in git). **One slip:** after the freeze, the tail of a
figure-check log showed two lines of held-out summary counts (lacunae and
skeleton pixels of 682_z23 and 701_z36c1-2). Nothing was changed after it, and
no held-out picture was opened. `POL_SUMMARY.md` now says its numbers predate
the loop.

**Still wrong.** Fragments (72) overlap small real lacunae in every measured
feature, so no rule separates the rest without losing accepted lacunae.
Pieces of bands under 300 um2, thin strips along the bone surface (WT_HP 872)
and diffuse tissue (Hyp_HP 701_z26) remain. Splits (one lacuna, two ids) were
never addressed. Dim out-of-focus bodies are missed (WT_HP 876 and 877, WT
543_3), more so now that the rescue rules are off. The reviewer moves by
about 4 problems per group between two looks at the same picture.
Not rerun with the new detection: the archived AI judge and ring proxy sets
(`5_archive/`, `results/archive/pols/`), and `diagnostics.py reference-check`.
On this machine the venv launcher hangs 300 s at start; commands ran the base
interpreter as the venv (`results/PROGRESS_LOOP.md`).

**Needs your decision.**
1. The four rules are now the default (the brief asked for the fix; your
   standing rule is that no default changes without asking). Keep them?
2. The band rule acts as a largest lacuna profile of 300 um2, about 8 times
   the WT median: acceptable in a study of enlarged lacunae?
3. Rescue rules off: accept losing the dim out-of-focus lacunae, or ask for a
   better rule for them?
4. The held-out sections share animals with the development sections: keep
   this section-level hold-out, or hold out whole animals?
5. Validation: nothing downloaded has labels. Manual counts or outlines on
   the held-out images (Mahmoud's ImageJ), or labels asked of Vetter et al.?
6. `diagnostics.py reference-check` uses 543-2, a held-out image; it was not
   run, and its fixed numbers predate the loop.
7. DEV stays the default mode after this task. Keep it?
