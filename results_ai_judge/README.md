# results_ai_judge

**The second of two labelled result sets: the pipeline with the AI judge
switch on. EXPERIMENT. NOT VALIDATED: no verdict here has been checked against
a manual trace, and which of the two methods is used is a choice still
pending.** The deterministic method is `results/`, which this folder never
writes to. Both methods are described in `docs/METHODS.md`, and the judge in
`docs/EXPERIMENT_AI.md`.

Made by one command, offline, from the decision files in `ai_log/`:

```
python src/diagnostics.py ai-run --dir data/WT
```

It turns `config.AI_JUDGE_ENABLED` on for that one process only (`config.py`
ships with it off), runs detection, canaliculi and quantification exactly as
`src/lacunae.py`, `src/canaliculi.py` and `src/quantification.py` do, and
proves by hashing that nothing under `results/` and nothing in `ai_log/`
changed.

| path | what it is |
| --- | --- |
| `<label>/1_lacunae/`, `<label>/2_canaliculi/`, `<label>/5_quantification/` | the same per-image layout as `results/`, with the judge's verdicts applied |
| `all_images/quantification/` | the cross-image table of this set |
| `ai_run.json` | the run's record, with the proof that `results/` and `ai_log/` are byte identical afterwards |
| `ai_log/<label>/` | the judge log: every request and answer, one json per attempt, and the decision file the run applied |
| `ai_log/<label>/pictures/` | **the case pictures that were actually sent**, byte for byte |
| `replay.txt` | `python src/diagnostics.py ai-judge --dir data/WT --replay`: the log rerun offline, identical verdicts on all 8 images |
| `compare/` | judge off against judge on, per image, made by `python src/diagnostics.py ai-compare --dir data/WT`: the verification and skeleton pictures side by side, a picture of what changed hands, and `REPORT.md` |
| `roots_before_and_after_the_fix.md` | roots per lacuna with the judge on, before and after the roots fix |

There is no `3_publication_figures/` here. The publication figures are made
for `results/` only, by `figures/make_figures.py`; drawing them for a method
that has not been chosen and not been validated would put an unvalidated
method into figures.

The judge run itself was made once, on 2026-10-19: 143 calls to the pinned
`claude-sonnet-5-5`, $1.60, one unreadable answer retried and recovered, no
segment left unjudged. External API use was approved on 2026-10-15 by Karim.
