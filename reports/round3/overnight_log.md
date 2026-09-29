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
