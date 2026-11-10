# Both AI judges on: the canalicular network (WT)

Pre-validation, not validated: no verdict of either judge has been checked against a manual count. Made on 2026-11-09 with the method at tag `method-freeze-v2` and the judge rerun of that day (docs/METHODS.md section 29). The deterministic results beside this folder are not changed by it.

The network of WT with the AI canaliculi (thread) judge: shown a crop around each lacuna with the candidate threads numbered, it said which are real and which cell they start from; run on the lacunae the lacuna judge accepted. Its log, every request and answer with the pictures that were sent and the decision file of each image, is in `ai_log/` here.

Made from the logs, offline: `LCN_HOLDOUT_MODE=FINAL python src/diagnostics.py ai-run -a --with-lacuna-judge`. The calls: `ai-judge -d data/<group> --with-lacuna-judge`. Held-out images are in the set, judged as part of the method, but their judge outputs were not opened, reviewed or summarized (docs/HOLDOUT.md). The comparison with the judge off, on the development images, is in the sheet "Judge on vs off" of `results/SUMMARY.xlsx`.
