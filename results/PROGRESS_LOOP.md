# Progress: hold-out, external data, review loop (2026-11-05)

Pre-validation. Brief of 2026-11-05, unattended run. This file says where the
run is, so it can be resumed after a crash. Logs of every command are in
`.cache/loop_logs/` (git-ignored).

| phase | state | commit or note |
| - | - | - |
| 0 sync | done | see below |
| 1 hold-out | done | data/holdout.json, docs/HOLDOUT.md, guard in config.py and src/lacunae.py, `diagnostics.py holdout-check` 13 of 13; tag holdout-locked-2026-11-05 |
| 2 external data | done | docs/EXTERNAL_DATA.md; F:/external_data/ (not committed); no source has manual lacuna labels |
| 3 reviewer | in progress | |
| 4 loop | not started | |
| 5 freeze and rerun | not started | |
| report | not started | |

## Phase 0, sync

- `git status` clean before the pull, so nothing was stashed. `git pull`
  fast-forwarded 3a69e66..0b0be38; the last commit is "POL pass 3:
  POL_SUMMARY.md, lacunar size per group and the problems found".
- `results/` has WT, WT_HP, Hyp_RD and Hyp_HP, each with 1_lacunae,
  2_canaliculi, 3_pols, 4_quantification, 5_archive. Left over on this machine
  and untracked: old per-image folders `results/WT/<label>/` from before the
  layout change (not opened, not touched).
- Regression on this machine: PASS, both runs (current config, and
  FAST_LACUNA_STAGE on), 6800 numbers over 8 images, 6 min 26 s. (The other
  laptop failed it on the last digits of one threshold.)
- Self-tests: pols 12 of 12, pol_ring_proxy 18 of 18, validate-network 8 of 8,
  ai-judge stub 15 of 15, ai-lacuna-judge stub 26 of 27 (the one known
  failure, the cap over the cached images, as at 3a69e66).

## How to resume

- Never open a held-out image or its outputs (docs/HOLDOUT.md).
- Phase 4: the last finished round is the last one logged in
  `results/archive/REVIEW_LOOP.md`; start at the next one.
