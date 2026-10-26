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
Nothing is merged or split. At most 60 per image are numbered, the largest.

| path | what it is |
| --- | --- |
| `dry_run/` | what a real run would send and cost, with **every picture exactly as the judge would see it**, made by `python src/diagnostics.py ai-lacuna-judge` (the dry run is the default and sends nothing): `dry_run.md` (the report), `.json`, `.csv`, and `<group>/<image>.png` |
| `<group>/ai_log/<image>/` | after a real run: every request and answer, one json per attempt with its hashes, the picture that was sent, and the decision file |
| `<group>/<image>/`, `<group>/all_images/` | after a real run: the pipeline with the judge's verdicts applied, the same layout as `results/<group>/`, made by `python src/diagnostics.py ai-lacuna-run` |
| `review/` | after a real run: a contact sheet per group with the verdicts drawn, and a table per image |

**State on 2026-10-26.** Only `dry_run/` exists. No real call has been made:
the two environment variables a real run needs were not set when the dry run
was made. The dry run: 35 calls, one per image, 1,882 numbered regions,
estimated $0.93 ($1.87 if every call were retried once), against a ceiling of
$3. 23 images have more than 60 candidates, and on four of them 15 kept lacunae
in all are left unnumbered by the cap and keep the deterministic decision
(701_z19c1-2 8, 701_z26c1-2 4, I534_z11c1-2 2, 535_z27c1-2 1). 24 of the 1,882
numbers could not be placed clear of every outline.

How a verdict is used, behind `config.AI_LACUNA_JUDGE_ENABLED` (off by
default): yes keeps a region as a lacuna even if a shape filter rejected it; no
removes it even if the filters kept it; unsure, and a region the judge was not
asked about or did not answer, keep the deterministic decision. A region the
judge added is the class `judged`: counted and owning threads, with no area or
shape measure, like the class `dim`. Every later stage runs unchanged.
