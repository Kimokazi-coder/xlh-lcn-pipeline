# Report: bias audit of the frozen method (2026-11-06)

**Pre-validation.** Every class below is an AI reviewer's single look at a
crop (the `image-reviewer` subagent, Sonnet, Read, Glob and Grep only), on the
27 development images, in DEV mode. No held-out image or output was opened,
printed or summarized. Progress: [`../../PROGRESS_AUDIT.md`](../../PROGRESS_AUDIT.md).

## The two audits, per group

| group | band rule: removed | of them real lacuna | band or tissue | unsure | rescue off: real lacunae lost | of detected | lost share |
| - | - | - | - | - | - | - | - |
| WT | 0 | 0 | 0 | 0 | 4 | 71 | 5.6% |
| WT_HP | 2 | 0 | 2 | 0 | 1 | 85 | 1.2% |
| Hyp_RD | 7 | 0 | 7 | 0 | 6 | 150 | 4.0% |
| Hyp_HP | 8 | 0 | 6 | 2 | 0 | 149 | 0.0% |

- **Cap (300 um2 band rule): not biased.** No real lacuna removed
  ([`CAP_AUDIT.md`](CAP_AUDIT.md)). The two unsure are in Hyp_HP 701_z26c1-2,
  one a 214.5 um2 "diffuse mass, could be an enlarged lacuna or tissue".
- **Dim loss (rescue rules off): biased by the test.** The lost share differs
  by 5.6 points (WT against Hyp_HP), over the limit of 5; 5.2 points if unsure
  counts as real ([`DIM_AUDIT.md`](DIM_AUDIT.md)). It rests on 4 WT objects.

## Whether the method changed, and why

**No; the method stays at `method-freeze-v1`, so there is no
`method-freeze-v2` and no final rerun.** The brief's fix for the dim loss is
a rescue rule that brings the real lacunae back without the fragments of loop
round 1. Over the 57 rescued objects, no rule of one to three bounds on
brightness, contrast, background, shape, glow footprint or distance to the
nearest lacuna does that (`diagnostics.py dim-rule-search`): with no fragment
back it returns 3 of 11, by thresholds chosen on the same objects the test
counts, and 10 of 11 only with 8 fragments. A rule fitted only to pass the
test would make the test meaningless, so none was added. The options are in
[`FIX_LOG.md`](FIX_LOG.md).

## Final lacunar size per group

Development images only (the held-out images were not read), measured
lacunae (not touching the frame), from `results/<group>/3_pols/` of the frozen
method:

| group | images | n | median (um2) | 90th percentile (um2) |
| - | - | - | - | - |
| WT | 6 | 62 | 39.86 | 69.83 |
| WT_HP | 7 | 70 | 30.26 | 61.54 |
| Hyp_RD | 7 | 128 | 38.07 | 87.71 |
| Hyp_HP | 7 | 113 | 24.25 | 95.39 |

`results/summary/pols_lacunar_size_by_group.csv` pools every image, held out
included, and was not read for this report.

## Leftovers done

- `reference-check` runs on the WT development image 543_3: 166.40 / 23.19 /
  7.70 with the frozen method (543-2 is held out).
- The AI judge sets moved by `git mv` (1009 files, `MOVE_MAP.csv`) into the
  sections: `results/<group>/<section>/ai_judge/` (log in
  `1_lacunae/ai_judge/ai_log/`), for WT `results/WT/<section>/ai_judge_canaliculi/`
  (log, `compare/`, records in `2_canaliculi/ai_judge_canaliculi/`; not
  `2_canaliculi/ai_judge/`, where its 56 file names collide with the lacuna
  judge's). A README in each says it predates `method-freeze-v1`. The writers
  use `config.result_set_root`; `dry_run/` and `review/` stay in
  `results/archive/ai_judge/`.
- The venv launcher hang: twice it followed a removal of USB storage (an eject
  vetoed by running programs, Kernel-PnP event 225; on 2026-11-05 also a USB
  drive dropping off, NTFS events 140 and 98). The repository and the venv are
  on the USB drive F:. Documented with the workaround in the README, "Running it".
- `results/README.md`, `docs/START_HERE.md` and `docs/METHODS.md` (sections 13,
  25, 26) updated.

**Checks after the changes** (DEV mode): regression PASS, both runs, 4738
numbers over the 6 development WT images; reference-check PASS 3 of 3;
holdout-check 13 of 13; pols self-test 12 of 12; ai-judge stub 15 of 15;
ai-lacuna-judge stub 26 of 27 (the known cap check, as before). The first
regression run failed only because a DEV run makes no row for the two held-out
WT images and the committed table, from the FINAL run, has them; in DEV mode it
now leaves those rows out unread. **A slip:** reading that failed log showed
the summary row of the held-out image 543-2 (its lacuna count and network
means). Nothing was changed because of it, and no held-out picture was opened.
The layout check fails only on the old untracked per-image folders in
`results/WT/` on this machine.

## Still wrong

The dim loss is uneven and stays so until you choose (FIX_LOG.md). The
band rule's two unsure Hyp_HP objects. The AI judge sets do not match the
current detection until rerun. The loop's open problems remain: fragments,
band pieces under 300 um2, splits, missed dim bodies. All of it rests on an AI
reviewer, not on manual counts.
