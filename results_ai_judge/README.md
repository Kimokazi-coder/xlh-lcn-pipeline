# results_ai_judge

**The second of two labelled result sets: the pipeline with the AI judge
switch on. EXPERIMENT. NOT VALIDATED: no verdict here has been checked against
a manual trace, and which of the two methods is used is a choice still
pending.** The deterministic method is `results/`, which this folder never
writes to. Both methods are described in `docs/METHODS.md`, and the judge in
`docs/EXPERIMENT_AI.md`.

Everything is in `WT/`: the judge was run on the WT group only, and no other
group has a judge set. Made by one command, offline, from the decision files in
`WT/ai_log/`:

```
python src/diagnostics.py ai-run --dir data/WT
```

It turns `config.AI_JUDGE_ENABLED` on for that one process only (`config.py`
ships with it off), runs detection, canaliculi and quantification exactly as
`src/lacunae.py`, `src/canaliculi.py` and `src/quantification.py` do, and
proves by hashing that nothing under `results/` and nothing in `WT/ai_log/`
changed.

| path | what it is |
| --- | --- |
| `WT/<label>/1_lacunae/`, `WT/<label>/2_canaliculi/`, `WT/<label>/5_quantification/` | the same per-image layout as `results/WT/`, with the judge's verdicts applied |
| `WT/all_images/quantification/` | the cross-image table of this set |
| `WT/ai_run.json` | the run's record, with the proof that `results/` and `WT/ai_log/` are byte identical afterwards |
| `WT/ai_log/<label>/` | the judge log: every request and answer, one json per attempt, and the decision file the run applied |
| `WT/ai_log/<label>/pictures/` | **the case pictures that were actually sent**, byte for byte |
| `WT/replay.txt` | `python src/diagnostics.py ai-judge --dir data/WT --replay`: the log rerun offline, identical verdicts on all 8 images |
| `WT/compare/` | judge off against judge on, per image, made by `python src/diagnostics.py ai-compare --dir data/WT`: the verification and skeleton pictures side by side, a picture of what changed hands, and `REPORT.md` |
| `WT/roots_before_and_after_the_fix.md` | roots per lacuna with the judge on, before and after the roots fix |

**Paths inside the records.** The folders moved into `WT/` on 2026-10-20. The run records written
before that, `WT/ai_run.json`, `WT/replay.txt`, the decision files and the files of `WT/compare/`
other than `compare_methods*`, are left as written and name the paths as they were then:
`results/<label>/` is now `results/WT/<label>/`, and `results_ai_judge/<name>` and
`results/ai_log/` are now `results_ai_judge/WT/<name>` and `results_ai_judge/WT/ai_log/`.
`compare_methods*` was made again after the move, with the same numbers.

There is no `3_publication_figures/` here. The publication figures are made
for `results/WT/` only, by `figures/make_figures.py`; drawing them for a method
that has not been chosen and not been validated would put an unvalidated
method into figures.

The judge run itself was made once, on 2026-10-19: 143 calls to the pinned
`claude-sonnet-5-5`, $1.60, one unreadable answer retried and recovered, no
segment left unjudged. External API use was approved on 2026-10-15 by Karim.
