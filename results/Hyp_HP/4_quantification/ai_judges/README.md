# 4_quantification/ai_judges: Hyp_HP

Every measured number of Hyp_HP for the AI judges run (AI lacuna and POL
judges on), the whole group. Pre-validation: no verdict of a judge is checked
against a manual count.

- `quantification_all_images.csv`, `.xlsx`, `.pdf`: one row per image.

Each image's own numbers are in its folder, `<image>/ai_judges/4_quantification/`
(`<image>_quantification.json`, `.xlsx`, `.pdf`), its key numbers in
`<image>/ai_judges/summary/`, and the comparison with the non-AI run in
`<image>/comparison/`. The AI lacuna judge said which outlines of the lacuna
stage are lacunae and the AI POL judge joined split pieces, set the cluster
flag and removed what is no lacuna (docs/METHODS.md 29 and 30); the
canaliculi are traced by the normal method around those lacunae. Made from the
judges' logs, offline, by `LCN_HOLDOUT_MODE=FINAL python src/diagnostics.py
ai-lacuna-run --with-pol-judge`. Held-out images are in it, judged as part of
the method, but their judge outputs were not opened or reviewed
(docs/HOLDOUT.md).
