# results/WT/5_archive/ai_judge/canaliculi_judge/ai_log

**EXPERIMENT, branch `exp-ai-layer` only. See `docs/EXPERIMENT_AI.md`.**

Everything the AI judge was asked and everything it answered, every file
named after its image. It holds **the real run on all 8 images, made on 2026-10-19**: 143 calls,
$1.60, one unreadable answer retried and recovered, and no segment left
unjudged. It replays offline to identical verdicts on every image
([`../replay.txt`](../replay.txt)). What the verdicts then did to the network
is in [`../compare/REPORT.md`](../compare/REPORT.md). **Not validated**: no verdict here has
been checked against a manual trace.

**Where this folder was.** The run was made when this log lived in
`results/ai_log/<label>/`; it moved to `results_ai_judge/ai_log/`, on
2026-10-20 to `results_ai_judge/WT/ai_log/<label>/`, and on 2026-11-04 here,
with one folder for every image: `<label>/case_NNNN_attemptK.json` became
`<label>_case_NNNN_attemptK.json` and `<label>/pictures/case_NNNN.png` became
`pictures/<label>_case_NNNN.png`, content unchanged
([`../../../../../archive/MOVE_MAP.csv`](../../../../../archive/MOVE_MAP.csv)). The log
records and decision files keep the `picture` paths they were written with.
They are left as written, because they are the record of what was sent, and
nothing reads the recorded path: the replay rebuilds every picture and compares its sha256 with the logged
one.

What a run writes, here, for each image `<label>`:

| file | what it is |
| - | - |
| `<label>_case_NNNN_attempt1.json` | one request and one answer. The request is recorded canonically, with the picture's sha256 and size instead of its bytes, plus the sha256 of the request, of the prompt and of the examples. The answer is recorded with its token counts, its stop reason and what it cost. |
| `<label>_case_NNNN_attempt2.json` | the retry, written only when the first answer did not validate. |
| `pictures/<label>_case_NNNN.png` | the picture that was sent, byte for byte. |
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
python src/diagnostics.py ai-judge -i "data/WT/543-2.tif" -r
```

It rebuilds each request, compares its hash with the logged one, puts the
logged answer through the same parser, and reports whether the verdicts come
back the same.
