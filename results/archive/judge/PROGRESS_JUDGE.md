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
| 2 dry run and cost | done | canaliculi judge made group-aware (log per group, ceiling over the whole run, --with-lacuna-judge, --log-root, held-out verdicts never printed); both judges live on 542_z06, 872_wt_hp_z03, 535_z13c1-2, 548_hyp_HP_z08c1-2 (DEV): 69 calls, $0.91, no authentication error; estimate for 35 images $7.96 ($11.94 at 1.5 times), within BUDGET_USD 50: COST.md. One failed start before any call (relative --log-root path), fixed. Self-tests: ai-judge -s 15/15, ai-lacuna-judge -s 32/32 |
| 3 full run | stopped by the API's billing error, offline steps done | FINAL mode, script .cache/loop_logs/judge/phase3.sh, steps in order: lacuna (lacuna judge live, 35 images), lacunarun (ai-lacuna-run, set ai_judge), canaliculi (canaliculi judge live per group in parallel, a quarter of the remaining budget each), canalrun (ai-run -a --with-lacuna-judge, set ai_judge_canaliculi), pols (pols all --set ai_judge), checks (pols checks, both replays). Old sets git rm'd first (at tag method-freeze-v2). To resume: rerun the first step whose output is missing; a live step already done must not be rerun (it would pay again). Done: lacuna (35 of 35 images, 36 attempts, $1.08, run record results/archive/ai_judge/ai_lacuna_judge_run.json), lacunarun (rc 0, the rest of results/ and the judge logs byte identical). canaliculi STOPPED by the API at 2026-11-09 evening: 'Your credit balance is too low to access the Anthropic API' (billing, not the budget: $7.34 of $50 spent in all). Complete: WT 8/8 ($1.39), Hyp_HP 9/9 ($1.53). Incomplete: WT_HP 8/9 ($1.07; stopped in 877_wt_z087c1-2 after 6 of its cases, no decision file), Hyp_RD 6/9 ($1.36; stopped in I534_z11c1-2 after 24 cases, no decision file; I534_z19c1-2 (held out) and I534_z25c1-2 not started). No further call is made. Offline steps that need no call continue: pols --set ai_judge, ai-run for the complete groups WT and Hyp_HP, checks, compare on the development images. To finish after a credit top-up: ai-judge -i <image> --with-lacuna-judge for the 4 images (the run ceiling is what is left of the $50), then ai-run -a --with-lacuna-judge, checks, judge-compare. Offline steps done: pols all --set ai_judge (35 images); ai-run for WT and Hyp_HP (rc 0, the rest of results/ and the logs byte identical); pols check --set ai_judge PASS, check-pictures 35/35, lacuna judge replay IDENTICAL on 35, canaliculi judge replay IDENTICAL on WT 8/8 and Hyp_HP 9/9 |
| 4 compare | to do | |
| report | to do | |

Queued after this task is pushed (user message of 2026-11-09): a POL judge
(src/judge_prompt_pols.md), budget 10 USD, applied to the judge-on results
only; dry run on 1 development image per group first; then all 35 images;
update the "Judge on vs off" sheet, REPORT_JUDGE.md and HOW_TO_READ.md.
