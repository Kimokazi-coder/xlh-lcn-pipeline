# Progress: the AI judge rerun at method-freeze-v2 (2026-11-09)

Pre-validation. Unattended brief of 2026-11-09: rerun the AI judge layer (lacuna
judge and canaliculi judge) on all four groups at `method-freeze-v2`, with the
lacuna judge updated to the working POL definition. This file says where the
run is, so it can be resumed after a crash. Logs in `.cache/loop_logs/judge/`
(git-ignored). DEV mode for all development work; held-out images are processed
in the FINAL run as part of the method, and their judge outputs are not opened,
reviewed or summarized. Nothing outside the repository is moved, copied or
deleted.

Budget: BUDGET_USD = 50 for both judges together (phase 2 stops if the
estimate is above it; phase 3 stops if the running total passes it).

The API key and ALLOW_EXTERNAL_API=1 are set in the Windows user environment,
not in this session's process environment (set after the editor started); the
run passes them to the Python process from the user environment. The key is
never printed, logged, written or committed.

| phase | state | note |
| - | - | - |
| 0 pull, environment | done | main up to date at 2e8624b; key and flag present (user scope) |
| 1 judge self-test | done | the failing check was "every real image over the cap" (the cache was keyed on the old settings, so no image was found); now a pass needs only that none leaves a kept lacuna unnumbered (15 of 25 cached development images over the cap, none does). The judge follows method-freeze-v2: a region with more than half its area in the excluded region is not offered and keeps the deterministic decision (the cache now holds the excluded region, schema 2); no area cap. New checks on I534_z25c1-2 (Hyp_RD, development, excluded region and 2 clusters): with every verdict yes, every numbered region is a lacuna up to the largest (181 um2), none lies mostly in the excluded region (7 not offered), both clusters stay flagged. Self-test image 543_3 (543-2 is held out). Checks: ai-lacuna-judge -s 31/31, ai-judge -s 15/15, pols selftest 19/19, animal_stats selftest 4/4, reference-check 3/3, holdout-check 13/13, regression PASS (2 runs, 6 development WT images) |
| 1B prompt, POL definition, judge-on 3_pols | done | prompt and rules in words follow the working POL definition: enlarged lacunae and clusters kept, only fragment, band, tissue and saturated border pieces rejected; every answer carries a reason code that must go with its verdict; METHODS 29.1 and 29.3, pointer in EXPERIMENT_AI. pols.py --set ai_judge writes 3_pols/ai_judge/ (same pictures, tables, POL metrics; ratios against the judge-on WT median; held-out numbers not printed); tested on the old WT set (WT rows PASS), test output removed. Checks: ai-lacuna-judge -s 32/32, pols selftest 19/19 |
| 2 dry run and cost | to do | |
| 3 full run | to do | |
| 4 compare | to do | |
| report | to do | |

Queued after this task is pushed (user message of 2026-11-09): a POL judge
(src/judge_prompt_pols.md), budget 10 USD, applied to the judge-on results
only; dry run on 1 development image per group first; then all 35 images;
update the "Judge on vs off" sheet, REPORT_JUDGE.md and HOW_TO_READ.md.
