# Experiment: an AI judge for the threads around a lacuna

**Status: EXPERIMENT. Branch `exp-ai-layer` only. Not merged, not validated, not used for any
result.** `main` is untouched. With `config.AI_JUDGE_ENABLED = False`, which is how this branch
ships, every pipeline output is byte for byte what `main` produces.

External API use approved on 2026-10-15, approver: (Karim fills in)

## The question

One global cut empties a ring of skeleton around every lacuna. METHODS section 18 measured why: a
thread's own contrast inside that glow runs at 31 to 71% of what the same tissue shows 40 px further
out, so one threshold keeps a quarter of the mask there that it keeps elsewhere. The glow zone rule
(`config.GLOW_ZONE_CUT_FRACTION`) recovers part of it by lowering the cut where the mask already
reaches. What it cannot do is tell a faint thread from the grain of the glow, because a threshold
has no way to ask that question.

This experiment asks it. A permissive tracing proposes every piece of thread-shaped signal in the
hole, and an AI judge, looking at a picture, says for each piece whether it is a real thread and
which cell it belongs to.

**Deterministic code stays the only code that touches pixels.** `src/ai_judge.py` makes the
candidates, draws the pictures, reads the answer back and hands the pipeline a set of pixels to add
and a set to drop. The judge only ever answers "real or artifact, and whose", about a numbered
segment in a picture. It never sees a file name, a path or a genotype, and it never writes a pixel.
Ownership, the 50 um cap and all quantification stay exactly where they were.

## What the judge is told

The rules, in the words of the brief, are in `src/judge_prompt.md`, which is the one fixed prompt
used for every image:

1. A thread that visibly touches an osteocyte belongs to it.
2. Threads in the glow around a body are often faint and are still real.
3. Not every dendrite belongs to an osteocyte, so "none" is a valid owner.
4. Glow texture and noise are artifacts.

`docs/judge_examples.md` starts empty and is loaded into the prompt automatically, after the rules
and before the case, on every call for every image. Karim writes the examples; nothing else is
needed to make them take effect. Both files have their sha256 written into every log record, so a
changed prompt or a changed set of examples is visible in the log for ever after.

## Step 1: the candidates

Per lacuna, in its own **empty zone** and nowhere else:

- **The zone** is the hole in the skeleton around the body, measured as the empty-zone diagnostic
  measures it: 180 angular sectors, and a sector's empty width is the smallest distance to the body
  over the skeleton pixels in it; a sector with no skeleton within 150 px, or with another body
  nearer than its skeleton, is censored. The zone runs out to each sector's own width, so it follows
  the real shape of the hole and is not a circle. It is measured on the **global cut skeleton**, the
  skeleton the ridge threshold and the glow zone rule produced before the dim pass and before the 50
  um prune: that is the skeleton that exists at the point in the pipeline where the candidates are
  made, and it depends on no ownership and on no later stage.
- **The contrast ratio** is that lacuna's own measurement of what its glow costs a thread: the p90
  of the ridge response in the 40 px band just beyond the hole over the p90 inside it. This is
  METHODS section 18's 31 to 71% measured per lacuna instead of per set. Floored at 1 so the
  candidate cut can never be stricter than the pipeline's own, capped at 3 as the brief asks.
  Measured on all 8 images it runs from 1.24 to 3.0 with a median of 2.11, and 2 of the 108 lacunae
  reach the cap, so the cap is a guard on the tail and not a setting that does the work.
- **The permissive tracing** accepts the ridge response, scaled by that ratio, down to 0.5 of the
  low cut. 0.5 is the floor the dim pass and the glow zone rule already use, so the pipeline has one
  definition of "dim" and not three. The pipeline's own exclusions still hold: bodies with their
  buffer are cut out, and inside a flagged vascular structure only already bright pixels survive.
  The mask the global cut produced is unioned in, so the permissive mask is a superset of the
  pipeline's inside the zone.
- **The segments** are what is left when that mask is skeletonized and split at its junctions. The
  skeletonization is done **once over the whole frame**, not zone by zone: the medial axis of a
  region clipped at a zone boundary runs along that boundary, which would invent threads shaped like
  the hole. Each branch is then clipped to the zone it lies in. Branches shorter than 10 px (1.3 um,
  the floor the pipeline already applies to a thread no lacuna owns) are dropped.
- **Zones belong to one lacuna.** Two zones overlap where two bodies are close, so a pixel is given
  to the nearer body, the same nearest-lacuna partition the pipeline's attachment uses. No segment
  is ever judged twice.
- **At most 40 segments** are offered in one case, the longest first, renumbered in reading order.
  The rest keep the deterministic decision and are counted as not offered. On all 8 images no case
  comes near the cap, so it has never yet bound.

The global skeleton outside the zones is untouched by all of this.

Run it: `python src/diagnostics.py ai-candidates --dir data/WT -o results/ai_dry_run`. It writes
`results/ai_dry_run/ai_candidates.json` and no pipeline output.

## Step 2: the judge

One call per lacuna. The picture is two panels side by side:

- **left**, the raw crop, 256 px of image data around the body, brightness stretched between the 1st
  and 99th percentile of the crop **outside the bodies** (with the bodies in, a bright osteocyte
  takes the top of the window and the faint threads go black), enlarged by whole pixels to 512 px so
  that a one pixel thread and a two digit number are both legible. Nothing is interpolated.
- **right**, the same panel with every body outlined in a colour and every candidate segment drawn
  in red with its number beside it. The body the case is about is always **yellow**; the others are
  cyan, magenta, orange, green, blue, handed out by increasing lacuna id. A body beyond the six is
  outlined in grey, which is not in the vocabulary, so it can never be named; the run report counts
  those cases.

Nothing else is drawn. Tracing the pipeline is already sure about is not marked, so a red segment is
a question and not a result.

The answer is one json object with, per segment number, `real` or `artifact`, the owner colour or
`none`, and one line of reasoning. Validation is strict: every number in the picture exactly once,
no number that is not in it, only the words the prompt allows. A failure is retried once with the
same request; if the second answer also fails, every segment of that case **keeps the deterministic
decision and is labelled unjudged**, which for a candidate means the pipeline's own mask stands
there. Both attempts are logged either way, and the run report gives the failure rate.

## Step 3: the assembly

Behind `config.AI_JUDGE_ENABLED`, default off. With it on, `canaliculi.analyse_network` recomputes
the candidates from the state it already holds, loads the decision file for that image, and edits
the candidate mask:

- a segment judged **real** adds the mask its centre line is the centre line of, inside its zone;
- a segment judged **artifact** takes that mask away, and the dim pass may not put it back;
- everything else, including an unjudged segment and one that was never offered, is left exactly as
  the pipeline had it.

So with no verdicts at all the mask comes back unchanged, and the switch changes a number only where
the judge actually answered. Which mask pixel belongs to which centre line is decided by nearest
centre line within the zone, so dropping a segment drops the mask it is the centre line of and
nothing else.

The owner the judge names is not written into any result by hand. It becomes a **zero weight
attachment** from that cell to the nearest node of that segment, the same zero weight the contact
rule uses, and the pipeline's own ownership, 50 um cap and quantification then run unchanged. A
segment the judge calls real with owner `none` joins the skeleton with no attachment, so the
existing rules decide whether anything owns it: **the judge can grant ownership and never veto it.**

The judge's own edit touches no pixel outside the empty zones, and the detection record carries that
as a number (`ai_judge.counts.edited_px_outside_the_zones`, 0). The mask does move outside them
afterwards, because the **dim pass** grows from the skeleton a lacuna owns and the ownership has
changed: on 543-2 with the self-test's stub verdicts that is 1,482 px against 6,045 px changed in
all. That is a pipeline stage reacting to what it was given, not the judge writing there, and the
self-test reports the two separately.

The decision file carries a sha256 of the candidate geometry, and the pipeline refuses to apply a
decision file whose candidates are not the ones it has just computed, so a verdict can never land on
a segment it was not given for. An image with the switch on and no decision file is an error and not
a silent pass, because a summary table must never mix judged and unjudged images.

`AI_JUDGE_ENABLED` is deliberately **not** in `diagnostics.SWITCHES_ON`: switch-check regenerates
all 8 images and the judge has run on 543-2 only.

## Step 4: the dry run, which always comes first

`python src/diagnostics.py ai-dry-run --dir data/WT -o results/ai_dry_run --pictures 543-2,543_3`,
run on 2026-10-15. Nothing was sent: the pictures and the requests are built, and the tokens are
estimated from them. Report: `results/ai_dry_run/ai_dry_run.json`.

| image | lacunae | calls | segments | input tokens | output tokens | cost USD |
| --- | --- | --- | --- | --- | --- | --- |
| 542_z06 | 19 | 19 | 131 | 34,754 | 4,965 | 0.1192 |
| 542_z18 | 13 | 13 | 126 | 23,799 | 4,670 | 0.0943 |
| 543-2 | 12 | 12 | 122 | 21,982 | 4,510 | 0.0891 |
| 543_3 | 13 | 13 | 190 | 23,866 | 6,910 | 0.1168 |
| 543_z13 | 11 | 11 | 100 | 20,136 | 3,720 | 0.0775 |
| 682_z08 | 11 | 11 | 110 | 20,149 | 4,070 | 0.0810 |
| 682_z23 | 14 | 14 | 153 | 25,660 | 5,635 | 0.1077 |
| 682_z29 | 15 | 15 | 167 | 27,513 | 6,145 | 0.1165 |
| **all 8** | **108** | **108** | **1,099** | **197,859** | **40,625** | **0.80** |

One call per lacuna, so 108 calls for the set and 12 for 543-2 alone. **Estimated $0.80 for all 8
images, $1.60 if every single call had to be retried, against the $5 ceiling.** 543-2 alone is
estimated at $0.089.

These are estimates and are labelled as such everywhere they are printed: text at 0.25 tokens per
character and each picture at width times height over 750 px per token, which is the rule Anthropic
documents for image input, and the answer at 35 tokens per segment plus 20. A real run logs the
token counts the API reports, and `--count-tokens` will measure the input exactly with the API's
free counter once a connection is allowed.

**A blind spot the dry run found and names: 16 of the 1,115 candidate segments (1.4%) lie in a zone
but outside their 256 px crop, so they cannot be drawn and are never asked about.** They stay
unjudged and keep the deterministic decision. The crop is the size the brief fixed, so the count is
reported rather than the crop quietly grown.

The pictures of every case for 543-2 and 543_3, exactly as the judge would see them, are in
`results/ai_dry_run/pictures/` (25 of them, one per lacuna).

## The self-test

`python src/diagnostics.py ai-judge --image "data/WT/543-2.tif" --self-test` rehearses the whole
chain on one image with a **stub judge**, no network and no key: a picture becomes a request, a stub
answer becomes verdicts, the log replays to the same verdicts, and the switch then edits the mask
and runs the rest of the pipeline on it. The stub answers by a fixed rule that means nothing
biologically (odd numbers real, even numbers artifact, some answers deliberately unreadable), so it
checks the machinery and never the judgement. Everything it writes goes to `.cache/ai_self_test`,
never to `results/`, so a rehearsal cannot leave verdicts where the pipeline could pick them up.

Ten checks, all passing on 2026-10-15: the answers validate, a bad answer is retried, a case that
never validates stays unjudged rather than guessed, replay gives the same verdicts, every request is
logged with its hash, no key and no image bytes are in the log, the switch changes the mask, the
judge edits nothing outside the zones, the pipeline runs to the end with the switch on, and an image
with no decision file is refused rather than passed over.

## Reproducibility

- **The model is pinned** in `config.AI_JUDGE_MODEL` (`claude-sonnet-5-5`), and no server side
  fallback to another model is enabled: a refusal is logged and the case stays unjudged, because a
  silent fallback would break the pin.
- **Every request and every answer is logged** to `results/ai_log/<label>/`, one json per attempt,
  with the sha256 of the canonical request, of the picture, of the prompt and of the examples. The
  picture that was sent is written beside it.
- **Replay** reruns from the log with no network: the request is rebuilt, its hash compared with the
  logged one, and the logged answer goes through the same parser, so the verdicts are reproduced and
  not copied. `python src/diagnostics.py ai-judge --image data/WT/543-2.tif --replay`.
- **Temperature.** The brief asks for 0. The pinned model **rejects any non-default temperature with
  HTTP 400**, so the request carries none and the log says so in as many words rather than claiming
  a setting that was not sent. `config.AI_JUDGE_TEMPERATURE` stays 0 and is sent to any model listed
  in `config.AI_MODELS_ACCEPTING_TEMPERATURE`, which is empty. Thinking is turned off for the same
  reason, as the one setting this model does accept for it; if the API refuses that too, the call is
  repeated once at the model's default and the log records which of the two went out.
- What makes a run reproducible is therefore **the log and the replay**, not the sampling setting.
  No language model is guaranteed to repeat itself on a fresh call, so the honest claim is the one
  the log can support: this is exactly what was asked and exactly what came back.

## Privacy, keys and cost

- The images are sent to the Anthropic API. Approved, see the line at the top of this file.
- Real calls happen **only** when `ALLOW_EXTERNAL_API=1` is set in the environment. Without it the
  code refuses to call out, and the dry run, the replay and the whole deterministic half still work.
- The key is read from `ANTHROPIC_API_KEY` by the SDK. It is never written to a file, never printed,
  and never put in a log record. `.env` is in `.gitignore`.
- The provider is `config.AI_JUDGE_PROVIDER`. Only `anthropic` is implemented, and any other value
  is refused rather than guessed at.
- `config.MAX_COST_USD = 5`. Every run estimates its cost before the first call and refuses to start
  if the estimate is above it; while it runs it adds up what the answers actually cost and stops if
  the total passes it.

## Decisions taken while building this

The brief left these open. Each was decided, and here is the reason.

| Decision | What was chosen | Why |
| --- | --- | --- |
| What "the measured empty width" is measured on | the global cut skeleton, before the dim pass and the 50 um prune | that is the skeleton in hand where the candidates are made, and it depends on no later stage and on no ownership |
| What the contrast ratio is | p90 of the ridge response in the 40 px band beyond the hole over the p90 in the hole, per lacuna | it is METHODS section 18's own measurement, per lacuna; it lands in 1.24 to 3.0, median 2.11, which is the 1.4 to 3.2 that section measured with a short tail either side |
| How a segment is defined | a branch of the permissive skeleton, split at junctions, clipped to one zone, at least 10 px | branches are what "split into numbered segments" means for a skeleton; 10 px is the floor the pipeline already uses for an unowned thread |
| Where the permissive mask is skeletonized | once over the whole frame | a mask clipped at the zone boundary has a medial axis that runs along that boundary, which would invent threads shaped like the hole |
| Segments in two zones | given to the nearer body | the pipeline's own nearest-lacuna partition; it makes double judging impossible |
| How many segments per case | at most 40, longest first | the picture has to stay readable and the answer small; nowhere near binding on these 8 images |
| What an "artifact" verdict removes | the mask whose nearest centre line is that segment, inside the zone | the smallest edit that expresses the verdict, and it leaves every unjudged segment untouched |
| What an unjudged segment does | keeps the deterministic decision | the brief says so, and for a candidate that means the pipeline's own mask stands |
| What owner `none` does | no attachment is added, the existing rules decide | the judge grants ownership and never vetoes it, so no ownership rule moves into the model |
| Temperature 0 | not sent to this model, recorded as not sent | the pinned model returns HTTP 400 for any non-default temperature |
| Prompt caching | not used | the saving over about 110 calls is a few cents and a cache write is a second price to account for |
| Server side refusal fallback | not enabled | it would break the pinned model |
| Where the fixed prompt lives | `src/judge_prompt.md` | the code loads it and hashes it; it is part of the method, like `config.py` |

## How to run it

```
# Deterministic, no network, no judge:
python src/diagnostics.py ai-candidates --dir data/WT -o results/ai_dry_run

# What a real run would cost, with the pictures for two images:
python src/diagnostics.py ai-dry-run --dir data/WT -o results/ai_dry_run --pictures 543-2,543_3

# A real run on one image (needs both environment variables):
ALLOW_EXTERNAL_API=1 ANTHROPIC_API_KEY=... python src/diagnostics.py ai-judge --image data/WT/543-2.tif

# The same run again, offline, from the log:
python src/diagnostics.py ai-judge --image data/WT/543-2.tif --replay

# The pipeline with the judge applied, which needs a decision file for the image:
# set config.AI_JUDGE_ENABLED = True, then run the pipeline as usual.
```

The SDK is needed only for a real call: `pip install anthropic`. On this venv's Python 3.9 pip
resolves to the last 0.x release, and the code uses only what 0.x and 1.x share.
