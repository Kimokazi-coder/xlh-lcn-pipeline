# AI lacuna judge: lacuna detection of WT_HP

**Made with the detector before `method-freeze-v1`. It does not match the
current results of `results/WT_HP/` until it is rerun.** Pre-validation, not
validated: no verdict has been checked against a manual count.

The files beside this README are the lacuna detection files of the pipeline run with the
AI lacuna judge on (`config.AI_LACUNA_JUDGE_ENABLED`, off by default): which
regions are lacunae was decided by the judge, every boundary is the lacuna
stage's own. The run was made from the judge's log on 2026-10-27, with the lacuna
stage of that day: the rescue rules on and no fragment or band rule (those came
with the review loop of 2026-11-05, `results/archive/REVIEW_LOOP.md`).
Its log, every request and answer with the picture that was sent and the decision
files, is in `ai_log/` here.

Moved here from `results/WT_HP/5_archive/ai_judge/lacuna_judge/` on
2026-11-06 (`results/archive/MOVE_MAP.csv`); records written before the move
still name the old paths. The judge's other folders: `results/WT_HP/1_lacunae/ai_judge/`,
`results/WT_HP/2_canaliculi/ai_judge/`, `results/WT_HP/4_quantification/ai_judge/`.
Rerun, offline, from the log: `python src/diagnostics.py ai-lacuna-run`
(docs/EXPERIMENT_AI.md, "The lacuna judge").
