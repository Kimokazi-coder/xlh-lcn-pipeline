# Overnight log, 2026-09-29 (branch presentation-prep)

Pre-validation, pixel units. One entry per step: what ran, the check, and
anything that did not match. Not pushed, not merged.

## Before the overnight steps

The script reorganization (moves-only commit eafcdd3, comment-only commit
964fdd4) was completed on canaliculi-v2-fixes first, then presentation-prep
was branched from 964fdd4. Neither branch is pushed past 03c9f42.

Note found during that work: diagnostics/tools/tidy_canaliculi_results.py
--dry-run now plans to move the eight default bridges.png files into
all_method_results/. The tool predates bridging becoming a default. It was
not run and not changed. Do not run it without a fix.

## Step 1: reach, done

diagnostics/canaliculi/measure_reach.py. The rebuilt default graph matched
the committed default edge counts on all 8 images exactly, so the reach
numbers describe the current default outputs. Primary cap by the rule:
265.1 px exact, 275 px rounded (retains 90.8% of pooled owned length).
Report: reports/round3/step1_reach.md.

## Step 2: reach cap, done

REACH_CAP_PX = None (off by default), REACH_CAP_PRIMARY_PX = 275.
--reach-cap [PX] turns it on, --no-reach-cap forces it off. 543-2:
default 62.33 / 27.41 / 21; --no-reach-cap 62.33 / 27.41 / 21;
--reach-cap 56.58 / 27.27 / 21. Commit 58ee4fb.

## Step 3: ownership-free measures, done

roots_count, ring_length_r30_px, ring_length_r60_px and owned_length_px
added to every per_lacuna row and the interior summary. Cross-checks:
roots_count equals --count-mode roots (7.5833 on 543-2); owned_length_px
equals total_length_px in edge mode. 543-2 default unchanged. Commit
efd4a0e.

## Step 4: sensitivity, done

Uncapped edge counts matched the committed defaults on all 8 images.
Report: reports/round3/step4_sensitivity.md. Commit 64fca6c.

## Step 5: presentation outputs, done

SHOW_UNOWNED_GREY switch added (off; default verification.png
byte-identical), commit 437acd9. src/make_presentation.py wrote
results/presentation/ with the cap on; lacuna counts cross-checked against
results/lacunae/ on all 8 images; results/canaliculi/ untouched. Commit
e54575e. 543-2 after it: 62.33 / 27.41 / 21 default and --no-reach-cap;
56.58 / 27.27 / 21 with the cap.

## Nothing failed

No step stopped and no check mismatched. One procedural slip, no effect on
results: a commit with nothing to add broke a && chain and skipped one
default 543-2 check, which was then re-run (62.33 / 27.41 / 21).
