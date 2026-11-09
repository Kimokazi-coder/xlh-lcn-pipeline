# The AI thread judge (canaliculi judge), archived

**Rerun on 2026-11-09 (method-freeze-v2).** The canaliculi judge now runs on every group, on the lacunae the lacuna judge accepted: its set is in `results/<group>/<section>/ai_judge_canaliculi/`, its log in `results/<group>/2_canaliculi/ai_judge_canaliculi/ai_log/`, its records in `results/archive/judge/` (docs/METHODS.md section 29). The text below describes the WT run of 2026-10-19 and the folders as they were then.

**Archived on 2026-11-04.** Its files are in
[`results/WT/5_archive/ai_judge/canaliculi_judge/`](../../WT/5_archive/ai_judge/canaliculi_judge/);
until then they were the folder `results_ai_judge/`, the second of two labelled
result sets: the pipeline with the AI judge switch on. **EXPERIMENT. NOT
VALIDATED:** no verdict here has been checked against a manual trace, and which
of the two methods is used is a choice still pending. The deterministic method
is the rest of `results/`, which the judge never writes to. Both methods are
described in [`docs/METHODS.md`](../../../docs/METHODS.md), and the judge in
[`docs/EXPERIMENT_AI.md`](../../../docs/EXPERIMENT_AI.md).

The judge was run on the WT group only. Made by one command, offline, from the
decision files in its `ai_log/`:

```
python src/diagnostics.py ai-run -d data/WT
```

It turns `config.AI_JUDGE_ENABLED` on for that one process only (`config.py`
ships with it off), runs detection, canaliculi and quantification exactly as
`src/lacunae.py`, `src/canaliculi.py` and `src/quantification.py` do, and
proves by hashing that nothing else under `results/` and nothing in its
`ai_log/` changed.

Paths inside `results/WT/5_archive/ai_judge/canaliculi_judge/`:

| path | what it is |
| - | - |
| `1_lacunae/`, `2_canaliculi/`, `4_quantification/` | the same section layout as `results/WT/`, with the judge's verdicts applied, every file named `<image>_...` |
| `4_quantification/quantification_all_images.*` | the cross-image table of this set |
| `ai_run.json` | the run's record, with the proof that `results/` and the log were byte identical afterwards |
| `ai_log/` | the judge log: every request and answer, one json per attempt (`<image>_case_NNNN_attemptK.json`), and the decision file each run applied (`<image>_ai_segments.json`) |
| `ai_log/pictures/` | **the case pictures that were actually sent**, byte for byte (`<image>_case_NNNN.png`) |
| `replay.txt` | the log rerun offline (`ai-judge -d data/WT` with its replay switch): identical verdicts on all 8 images |
| `compare/` | judge off against judge on, per image (`ai-compare -d data/WT`): the verification and skeleton pictures side by side, a picture of what changed hands, and `REPORT.md` |
| `roots_before_and_after_the_fix.md` | roots per lacuna with the judge on, before and after the roots fix |

**Paths inside the records.** The run records, the decision files and the
files of `compare/` are left as written and name the paths as they were then
(`results_ai_judge/WT/...`, and before 2026-10-20 `results/<label>/` and
`results/ai_log/<label>/`). Every such file now sits at the path given in
[`results/archive/MOVE_MAP.csv`](../MOVE_MAP.csv). The log files were renamed
on 2026-11-04 from `ai_log/<image>/case_NNNN_attemptK.json` to
`ai_log/<image>_case_NNNN_attemptK.json`, and the pictures likewise; their
content is unchanged.

There are no publication figures here: drawing them for a method that has not
been chosen and not been validated would put an unvalidated method into
figures.

The judge run itself was made once, on 2026-10-19: 143 calls to the pinned
`claude-sonnet-5-5`, $1.60, one unreadable answer retried and recovered, no
segment left unjudged. External API use was approved on 2026-10-15 by Karim.
