# Progress: audit of the frozen method for group bias (2026-11-06)

Pre-validation. Brief of 2026-11-06, unattended run. This file says where the
run is, so it can be resumed after a crash. Logs in `.cache/loop_logs/audit/`
(git-ignored). DEV mode throughout; held-out images and outputs are never
opened, printed or summarized.

| phase | state | note |
| - | - | - |
| 0 pull | done | already up to date at 12d4aae; the venv launcher starts in 2 s again |
| 1 cap audit | done | 17 removed (WT 0, WT_HP 2, Hyp_RD 7, Hyp_HP 8): 15 band or tissue, 2 unsure, 0 real; not biased |
| 2 dim audit | done | 60 added (11 real, 16 unsure, 33 not); lost real WT 5.6%, WT_HP 1.2%, Hyp_RD 4.0%, Hyp_HP 0.0%: spread 5.6 points, biased by the test |
| 3 fix if biased | not started | |
| 4 final rerun if changed | not started | |
| 5 leftovers | not started | |
| report | not started | |
