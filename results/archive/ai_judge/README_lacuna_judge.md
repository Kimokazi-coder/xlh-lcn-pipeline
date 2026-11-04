# results_ai_lacunae

**The AI lacuna judge. EXPERIMENT, pre-validation. NOT VALIDATED: no verdict
here has been checked against a manual count, and nothing here is a result of
the study.** The deterministic method is `results/`, which this folder never
writes to; the thread judge is `results_ai_judge/`, which it never writes to
either.

**What the judge does.** The lacuna stage was shaped on the 8 WT images. On the
other groups it outlines saturated bands, soft tissue patches and small
fragments as lacunae and misses dim or out-of-focus bodies. The AI lacuna judge
is shown, once per image, every candidate region the lacuna stage outlined,
numbered, and says per number whether it is an osteocyte lacuna: yes, no or
unsure. **It does not draw or change any boundary**: a lacuna it keeps has the
outline the lacuna stage drew. It runs on all four groups with the same prompt,
`src/judge_prompt_lacunae.md`, so the rule is the same everywhere, and it never
sees a file name, a group or a mouse, only a neutral image code.

The candidates are every region of the lacuna stage's label image of at least
100 px2, kept and rejected by the filters, plus the dim candidates: the regions
of the same mask at 0.8 of each image's lacuna cut that overlap none of them.
Nothing is merged or split. At most 60 per image are numbered. With more, the
cap drops from the end of this order, each tier largest first: every region the
filters kept, every region they rejected of at least 300 px2, the dim
candidates, the rejected regions under 300 px2. So every kept lacuna is
numbered unless an image has more than 60, and none has. The numbers run in
reading order, so a number does not tell the judge what the filters decided.

| path | what it is |
| --- | --- |
| `dry_run/` | what a real run would send and cost, with **every picture exactly as the judge would see it**, made by `python src/diagnostics.py ai-lacuna-judge` (the dry run is the default and sends nothing): `dry_run.md` (the report), `.json`, `.csv`, and `<group>/<image>.png` |
| `<group>/ai_log/<image>/` | every request and answer of the real run, one json per attempt with its hashes, the picture that was sent, and the decision file, made by `python src/diagnostics.py ai-lacuna-judge --live` |
| `ai_lacuna_judge_run.json` | the real run's summary: per image the verdicts, tokens and cost |
| `ai_lacuna_replay.json` | the replay of the log, offline: identical verdicts on every image, made by `python src/diagnostics.py ai-lacuna-judge --replay` |
| `<group>/<image>/`, `<group>/all_images/`, `ai_lacuna_run.json` | the pipeline with the judge's verdicts applied, the same layout as `results/<group>/`, made offline by `python src/diagnostics.py ai-lacuna-run`; the json says what it did and that `results/` and `results_ai_judge/` were byte identical afterwards |
| `review/` | a contact sheet per group with the verdicts drawn (green yes, red no, yellow unsure, grey unjudged or not numbered), and a table per image (`review.md`, `.csv`, `.json`), every region's verdict and why in `review_regions.csv`, made by `python src/diagnostics.py ai-lacuna-review` |

**State on 2026-10-27.** The dry run: 35 calls, 1,882 numbered regions, every
one of the 793 kept lacunae among them, estimated $0.93 against a ceiling of $3.
**The real run, on 2026-10-27**: 35 calls to the pinned `claude-sonnet-5-5`,
**$0.83** (147,968 input and 52,935 output tokens), no answer unreadable, retried
or refused. Verdicts: 304 yes, 1,408 no, 170 unsure, 0 unjudged. The replay
gives identical verdicts offline. With them, 7 regions are added (6 of them dim
candidates) and 352 kept lacunae are removed; the lacunae over the 35 images go
from 793 to 448. External API use approved on 2026-10-15, approver: Karim.

How a verdict is used, behind `config.AI_LACUNA_JUDGE_ENABLED` (off by
default): yes keeps a region as a lacuna even if a shape filter rejected it; no
removes it even if the filters kept it; unsure, and a region the judge was not
asked about or did not answer, keep the deterministic decision. A region the
judge added is the class `judged`: counted and owning threads, with no area or
shape measure, like the class `dim`. Every later stage runs unchanged.
