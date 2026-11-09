# Both AI judges on: lacuna detection (WT)

Pre-validation, not validated: no verdict of either judge has been checked against a manual count. Made on 2026-11-09 with the method at tag `method-freeze-v2` and the judge rerun of that day (docs/METHODS.md section 29; report `results/archive/judge/REPORT_JUDGE.md`). The deterministic results beside this folder are not changed by it.

The lacunae of the set with both judges on: the same lacunae as `1_lacunae/ai_judge/` before the POL judge (the lacuna judge decided them), written again so this set is complete on its own.

Made from the logs, offline: `LCN_HOLDOUT_MODE=FINAL python src/diagnostics.py ai-run -a --with-lacuna-judge`. The calls: `ai-judge -d data/<group> --with-lacuna-judge`. Held-out images are in the set, judged as part of the method, but their judge outputs were not opened, reviewed or summarized (docs/HOLDOUT.md). The comparison with the judge off, on the development images, is in `results/archive/judge/JUDGE_ON_VS_OFF.md` and the sheet "Judge on vs off" of `results/SUMMARY.xlsx`.
