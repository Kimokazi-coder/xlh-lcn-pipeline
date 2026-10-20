# results/ai_log

**EXPERIMENT, branch `exp-ai-layer` only. See `docs/EXPERIMENT_AI.md`.**

Everything the AI judge was asked and everything it answered, one folder per
image. It holds **the real run on all 8 images, made on 2026-10-19**: 143 calls,
$1.60, one unreadable answer retried and recovered, and no segment left
unjudged. It replays offline to identical verdicts on every image
(`results/ai_run/step1_replay.txt`). What the verdicts then did to the network
is in `results/ai_run/compare/REPORT.md`. **Not validated**: no verdict here has
been checked against a manual trace.

What a run writes, under `results/ai_log/<image label>/`:

| file | what it is |
| --- | --- |
| `case_NNNN_attempt1.json` | one request and one answer. The request is recorded canonically, with the picture's sha256 and size instead of its bytes, plus the sha256 of the request, of the prompt and of the examples. The answer is recorded with its token counts, its stop reason and what it cost. |
| `case_NNNN_attempt2.json` | the retry, written only when the first answer did not validate. |
| `pictures/case_NNNN.png` | the picture that was sent, byte for byte. |
| `<label>_ai_segments.json` | the decision file: every candidate segment with its verdict, its owner and the one line of reasoning, plus the sha256 of the candidate geometry the verdicts belong to. This is the only file the pipeline reads, and only when `config.AI_JUDGE_ENABLED` is on. |

The log never holds the API key, and never the image bytes inside a json
record. A billing, credit or authentication error is logged with the key
scrubbed out of it, and then stops the run: no decision file is written for that
image and nothing is recorded as unjudged.

`NNNN` numbers the cases of one image in order. Most are one lacuna's case; the
rest are for segments that one lacuna's crop cannot show with both of their
candidate cells, and the decision file says which each one is.

To rerun from the log with no network:

```
python src/diagnostics.py ai-judge --image "data/WT/543-2.tif" --replay
```

It rebuilds each request, compares its hash with the logged one, puts the
logged answer through the same parser, and reports whether the verdicts come
back the same.
