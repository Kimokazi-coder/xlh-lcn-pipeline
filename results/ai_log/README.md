# results/ai_log

**EXPERIMENT, branch `exp-ai-layer` only. See `docs/EXPERIMENT_AI.md`.**

Everything the AI judge was asked and everything it answered, one folder per
image. This folder is empty of runs because **no real call has been made yet**:
`ALLOW_EXTERNAL_API=1` and `ANTHROPIC_API_KEY` were not set, so the judge has
never been allowed to call out.

What a run writes, under `results/ai_log/<image label>/`:

| file | what it is |
| --- | --- |
| `case_NNNN_attempt1.json` | one request and one answer. The request is recorded canonically, with the picture's sha256 and size instead of its bytes, plus the sha256 of the request, of the prompt and of the examples. The answer is recorded with its token counts, its stop reason and what it cost. |
| `case_NNNN_attempt2.json` | the retry, written only when the first answer did not validate. |
| `pictures/case_NNNN.png` | the picture that was sent, byte for byte. |
| `<label>_ai_segments.json` | the decision file: every candidate segment with its verdict, its owner and the one line of reasoning, plus the sha256 of the candidate geometry the verdicts belong to. This is the only file the pipeline reads, and only when `config.AI_JUDGE_ENABLED` is on. |

The log never holds the API key, and never the image bytes inside a json
record. `NNNN` is the lacuna id, which is the only name a case has.

To rerun from the log with no network:

```
python src/diagnostics.py ai-judge --image "data/WT/543-2.tif" --replay
```

It rebuilds each request, compares its hash with the logged one, puts the
logged answer through the same parser, and reports whether the verdicts come
back the same.
