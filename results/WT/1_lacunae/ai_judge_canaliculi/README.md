# AI thread judge: lacuna detection of WT

**Made with the detector before `method-freeze-v1`. It does not match the
current results of `results/WT/` until it is rerun.** Pre-validation, not
validated: no verdict has been checked against a manual trace.

The files beside this README are the lacuna detection files of the pipeline run with the
AI thread judge on (`config.AI_JUDGE_ENABLED`, off by default): where who owns a
thread was a judgement call, the judge's verdict became a zero weight
attachment. The judge was run once, on 2026-10-19; this set was made from its
log with the detector of that day, before the review loop of 2026-11-05.

Moved here from `results/WT/5_archive/ai_judge/canaliculi_judge/` on
2026-11-06 (`results/archive/MOVE_MAP.csv`); records written before the move
still name the old paths. The judge's other folders: `results/WT/1_lacunae/ai_judge_canaliculi/`,
`results/WT/2_canaliculi/ai_judge_canaliculi/`, `results/WT/4_quantification/ai_judge_canaliculi/`.
Rerun, offline, from the log: `python src/diagnostics.py ai-run`, then
`ai-compare` and `compare-methods` (docs/EXPERIMENT_AI.md).
