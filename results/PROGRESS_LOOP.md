# Progress: hold-out, external data, review loop (2026-11-05)

Pre-validation. Brief of 2026-11-05, unattended run. This file says where the
run is, so it can be resumed after a crash. Logs of every command are in
`.cache/loop_logs/` (git-ignored).

| phase | state | commit or note |
| - | - | - |
| 0 sync | done | see below |
| 1 hold-out | done | data/holdout.json, docs/HOLDOUT.md, guard in config.py and src/lacunae.py, `diagnostics.py holdout-check` 13 of 13; tag holdout-locked-2026-11-05 |
| 2 external data | done | docs/EXTERNAL_DATA.md; F:/external_data/ (not committed); no source has manual lacuna labels |
| 3 reviewer | done | .claude/agents/image-reviewer.md (Read, Glob, Grep; sonnet); .gitignore tracks .claude/agents/ only |
| 4 loop | done | rounds 1 to 4 kept (258 to 153, WT 12 to 8); round 5 tried and reverted |
| 5 freeze and rerun | done | tag method-freeze-v1 (d1e0b5c); FINAL run on 35 images; regression PASS (FINAL, 8 WT) |
| report | done | results/archive/REPORT_LOOP.md |

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

## Phase 4, the loop (log: results/archive/REVIEW_LOOP.md)

- Round 0 done: baseline 258 problems (fragment 153). Tables in
  results/archive/review_loop/round0/.
- Machine note: since about 14:00 the venv launcher venv/Scripts/python.exe
  hangs 300 s at every start (cause not found; the base interpreter starts in
  1 s). Commands run the base interpreter as the venv instead:
  __PYVENV_LAUNCHER__=F:\lcn-quant\venv\Scripts\python.exe and
  "C:\Program Files\Carl Zeiss\ZeissPython\Py22042.2\env\python.exe".
- Round 1 done: rescue rules off, 258 to 225, WT 12 to 8; regression PASS on
  the 6 development WT images (default path against the --fast results).
  Round runner: the four stages per group, `-w 5 --fast`, then pols all.
- Round 2 done: fragment rule (satellite or speck), 225 to 186, WT 8 to 6;
  regression PASS.
- Round 3 done: crumb arm, 186 to 169; WT pictures identical, reviewer 6 to
  10 (noise); regression PASS. Next: band rule (blob over 300 um2).
- Round 4 done: band rule (mask region over 300 um2), 169 to 153; WT
  unchanged; regression PASS; dark-band-check 27 of 27 identical.
- Round 5 tried (faint crumb arm), WT worse object by object (one removed
  object became a missed body), total 153 to 152: reverted to round 4
  (feed1af). Loop ended. Next: docs, tag method-freeze-v1, FINAL run.
