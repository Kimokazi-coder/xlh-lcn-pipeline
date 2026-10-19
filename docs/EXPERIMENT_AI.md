# Experiment: an AI judge for the threads around a lacuna

**Status: EXPERIMENT. Branch `exp-ai-layer` only. Not merged, not validated, not used for any
result.** `main` is untouched. With `config.AI_JUDGE_ENABLED = False`, which is how this branch
ships, every pipeline output is byte for byte what `main` produces: checked after merging main at
commit ac199fa, `reference-check` PASS at 161.00 / 21.63 / 8.50 and `regression` PASS over 6,800
numbers at tolerance 0.

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

The rules are in `src/judge_prompt.md`, which is the one fixed prompt used for every image:

1. A thread that visibly touches an osteocyte belongs to it.
2. A thread belongs to the osteocyte it starts from, even where it later joins a network another
   osteocyte also reaches. That a different cell can be reached the long way round through the
   network is not evidence, because that is the very thing the pipeline gets wrong.
3. Not every dendrite belongs to an osteocyte, so "none" is a valid owner.
4. Threads in the glow around a body are often faint and are still real.
5. Glow texture and noise are artifacts.

`docs/judge_examples.md` holds rules 1 to 3 again in the words of the brief, and is loaded into the
prompt automatically, after the rules and before the case, on every call for every image. Karim adds
worked examples under them; nothing else is needed to make them take effect. Both files have their
sha256 written into every log record, so a changed prompt or a changed set of examples is visible in
the log for ever after.

## Step 1: what the judge is shown, and the four classes

A **segment** is a BRANCH of a skeleton, the piece between two junctions, at least 10 px long
(1.3 um, the floor the pipeline already applies to a thread no lacuna owns). Within each lacuna's
crop, every segment is shown, and they are of three **kinds**, which is what the pipeline has:

- **owned**: the pipeline traced it and a lacuna owns it;
- **unowned**: the pipeline traced it and nobody owns it;
- **new**: the pipeline does not have it. It is what a permissive cut finds inside that lacuna's
  **zone of the hole**: the pipeline's own zone and its own radial gain (METHODS section 19), with
  the cut lowered to `config.AI_CANDIDATE_CUT_FRACTION` = 0.5 of the low cut. The experiment
  lowers that cut and defines nothing of its own: `src/ai_judge.py` no longer measures an empty
  width or a contrast ratio, because the pipeline measures both.

What the judge is **asked** about is not the kind but the **class**, and there are four:

| class | what it is |
| --- | --- |
| **a** | an unowned segment, with at least one lacuna within reach of it |
| **b** | a new segment from the permissive cut inside the zone of the hole |
| **c** | a segment that touches a body that does not own it |
| **d** | a segment owned by a lacuna that is **not** the nearest lacuna to it by straight distance, where that nearest lacuna's body lies within its own zone of the hole plus 10 px |

A segment is numbered, which is what asks the judge for a decision, exactly when it falls in one of
those four classes. Class **d** is what this round adds, and it is the case the experiment is now
about: ownership goes by shortest path through the skeleton, so a whole connected network can go to
one lacuna that reaches it through a single thread while another lacuna sits closer to where those
threads start and has no skeleton path to them.

**Within reach** is one test, used for class d, for which candidates a numbered segment is offered,
and for which unowned segments are asked about at all: *a lacuna is a candidate for a segment when
its body lies within that lacuna's own zone of the hole plus 10 px of the segment.* The zone is the
pipeline's (METHODS section 19) and the 10 px is the minimum segment length the pipeline already
applies, so the rule introduces no number of its own.

Measured over the 8 images (`python src/diagnostics.py ai-candidates --dir data/WT -o
results/ai_dry_run`). Each class cell is **segments / pixels / lacunae involved**, where a lacuna
counts as involved when it is a candidate for at least one segment of that class, so it is the
number of cells whose ownership the class could move:

| image | segments | owned | unowned | new | a | b | c | d | numbered | calls |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 542_z06 | 1,334 | 1,040 | 248 | 46 | 43 / 1,195 / 15 | 46 / 789 / 16 | 0 / 0 / 0 | 19 / 612 / 11 | 108 | 24 |
| 542_z18 | 1,356 | 978 | 332 | 46 | 49 / 1,257 / 13 | 46 / 657 / 11 | 0 / 0 / 0 | 23 / 620 / 8 | 118 | 19 |
| 543-2 | 1,485 | 1,234 | 201 | 50 | 11 / 345 / 8 | 50 / 1,000 / 12 | 0 / 0 / 0 | 27 / 742 / 10 | 88 | 16 |
| 543_3 | 1,427 | 1,178 | 168 | 81 | 28 / 630 / 12 | 81 / 1,903 / 13 | 0 / 0 / 0 | 54 / 1,458 / 12 | 163 | 23 |
| 543_z13 | 1,463 | 1,101 | 314 | 48 | 17 / 530 / 7 | 48 / 781 / 11 | 0 / 0 / 0 | 18 / 596 / 10 | 83 | 15 |
| 682_z08 | 1,259 | 937 | 283 | 39 | 26 / 799 / 8 | 39 / 557 / 10 | 0 / 0 / 0 | 7 / 188 / 5 | 72 | 12 |
| 682_z23 | 1,377 | 1,048 | 283 | 46 | 52 / 1,353 / 12 | 46 / 802 / 11 | 0 / 0 / 0 | 22 / 540 / 9 | 120 | 17 |
| 682_z29 | 1,307 | 972 | 272 | 63 | 40 / 1,116 / 11 | 63 / 1,112 / 13 | 0 / 0 / 0 | 40 / 933 / 12 | 143 | 19 |
| **all 8** | **11,008** | **8,488** | **2,101** | **419** | **266 / 7,225 / 86** | **419 / 7,601 / 97** | **0 / 0 / 0** | **210 / 5,689 / 77** | **895** | **145** |

**895 segments are numbered over the 8 images, in 145 calls.** Of them 476 are asked an owner only
(classes a and d) and 419 are asked real or artifact as well (class b).

Three things that number says, and each is a measurement and not a choice:

- **Class c is empty on all 8 images**, as is the count of segments touching two bodies. Main's
  contact rule (a lacuna is offered every node that touches it, the nearer surface winning, METHODS
  section 19) leaves nothing there for a judge to correct. The machinery stays, because the class is
  real and an image outside these 8 may hold one, but on these images it asks nothing.
- **Class d is not empty: 210 segments, 5,689 px, and it involves 77 of the 108 lacunae.** The two
  candidate bodies lie a median 126 px apart and up to 334 px apart, which is why a case may need a
  bigger crop than a lacuna's own (below).
- **1,835 of the 2,101 unowned segments have no lacuna within reach and are not asked about at
  all.** Nothing is lost by that: no body in their picture could be named as their owner, so the
  only answer they could be given is the one the pipeline already has. It is also what keeps the
  cost of the run where it is.

## Step 2: the question

One call per case. The picture is two panels side by side:

- **left**, the raw crop, 256 px of image data (512 px where a case needs the bigger crop),
  brightness stretched between the 1st and 99th percentile of the crop **outside the bodies**,
  enlarged by whole pixels to 512 px. Nothing is interpolated.
- **right**, the same panel with every body outlined in its colour (the body in the middle is
  always **yellow**, the others cyan, magenta, orange, green, blue, and a seventh body grey) and
  **every segment drawn**.

How a segment is drawn says what it is:

| | drawn |
| --- | --- |
| numbered, and the pipeline traced it (classes a, c, d) | **white** |
| numbered, and the pipeline does not have it (class b) | **red** |
| context, traced and owned | **its owner's colour** |
| context, traced and owned by nobody | white |
| context, not traced | red |

A numbered traced segment is white **whoever owns it now**, because its owner is exactly what is in
question. That hides nothing: its current owner is one of the two candidate colours the case text
names for that number, and the rest of that cell's tracing is still drawn in its colour all around,
which is the context the judge needs to see where a thread starts.

**The question, per number, is one of two.** The case text lists every number with its
**candidates**: the one or two cells it could start from, the nearer one first.

- a **white** number: *which cell does this thread start from: the first candidate, the second
  candidate, or none?* The pipeline traced it, so it is real and the judge is not asked whether it
  is. **Nothing the judge says can delete tracing the pipeline made.**
- a **red** number: *is it a real thread or glow texture, and which cell does it start from?*

An answer may name **only a colour offered for that number**, or `none`. A colour that is in the
picture but not offered for that number is context, not an answer. Validation is strict and
per number: a failure is retried once, and a case that fails twice leaves every segment of it
**unjudged**, which means the pipeline's own decision stands.

Over the 8 images that is 895 numbered segments of 11,008 drawn, about 6 numbers per call: 476
asked an owner only and 419 asked real or artifact as well.

The three rules the brief asks for in words are in `docs/judge_examples.md`, which is loaded into
the prompt after the rules and before the case, on every call for every image: **(1)** a thread that
visibly touches an osteocyte belongs to that osteocyte; **(2)** a thread belongs to the osteocyte it
starts from, even if it later joins a network that another osteocyte also reaches; **(3)** not every
dendrite belongs to an osteocyte, so "none" is a valid answer. Both files' sha256 go into every log
record, so a changed prompt or a changed set of rules is visible in the log for ever after.

## Step 3: the segments one lacuna's crop cannot show

A numbered segment can only be asked about in a picture that shows it **and both of its
candidates**: a candidate body with no pixel in the crop has no name the judge could answer with.
Two things put a segment outside its own lacuna's crop. A zone can reach further than half a crop;
and the two candidate bodies of a class d segment lie a median 126 px and up to 334 px apart, which
one 256 px crop often cannot hold. Either way the segment would be counted and left unjudged, which
is a blind spot and not a neutral outcome.

**Each one now gets a call of its own**, with the **smallest crop that holds the segment and both
candidate bodies**, centred on all three, and any other left-over segment inside that crop is
numbered in the same call, so one extra call can clear several. The crop sizes are the pipeline's
own crop doubled until it reaches the rendered width: 256 px enlarged 2x, or 512 px at its own size.
Every size divides the rendered width exactly, so a picture is still enlarged by a whole number of
pixels and nothing is ever interpolated, and **a bigger crop costs magnification, not tokens**,
because the picture that goes out is the same size either way.

On the 8 images this costs **37 extra calls**: 145 for 108 lacunae, of which 125 are 256 px crops
and 20 are 512 px. The number that says whether anything was left out is
`needs_a_decision_but_no_case_could_ask`, which must be 0, and is on all 8 images. A segment that
two left-over crops both hold is numbered in the earlier one only, because a segment asked twice
would be two answers that can disagree over nothing.

## Step 4: the assembly

Behind `config.AI_JUDGE_ENABLED`, default off. With it on, `canaliculi.analyse_network` runs the
whole network stage **once with the judge off**, which is what main produces and what the judge was
shown, rebuilds the candidates from it, checks the geometry hash against the decision file, and then
edits the mask:

- a segment judged **real** that the pipeline does not have adds the mask its centre line is the
  centre line of;
- a segment judged **artifact** takes that mask away. Only a class b segment can be judged artifact,
  because only a class b number is asked the question, so **nothing the judge says can delete
  tracing the pipeline made**;
- a segment judged real that the pipeline already has stays where it is, and only its owner can
  change;
- everything else, including an unjudged segment, one never offered, and one whose two answers
  disagree, is left exactly as the pipeline had it.

So with no verdicts at all the mask comes back unchanged. A segment numbered in two cases that gets
two different answers is **left alone and counted**, because two answers that disagree are no answer.

**How a verdict is used.** The owner the judge names is not written into any result by hand, and
nothing is reassigned. It becomes a **zero weight attachment from that cell to the END of the
segment nearest that cell**, the same zero weight the contact rule uses, and then the pipeline's own
multi source shortest path assignment, the 50 um cap and the quantification run unchanged.

The end, not the nearest pixel, is the point: the path has to enter the thread where the thread
starts, or it enters halfway along and measures the thread from its middle. With the attachment
there, the two cells' paths meet somewhere along the network and **the shortest path splits it
between them**, which is the whole aim. The network stays connected, nothing is cut, and the old
owner keeps whatever the shortest path still gives it.

A segment the judge calls real with owner `none` joins the skeleton with no attachment: **the judge
can grant ownership and never veto it.**

The detection record carries what the verdicts moved, measured against the run with the switch off
that the judge was shown: `attached_segments`, how many of those went
`attached_to_another_cell`, and then `ownership_moved_px`, `newly_owned_px` and
`no_longer_owned_px`. Those last three are not the judge writing anywhere; they are what the
shortest path did once the attachment was in the graph.

The judge's edit lands on the segments it was given and nowhere else, which the detection record
carries as a number (`ai_judge.counts.edited_px_outside_the_judged_segments`, 0). It is no longer
confined to the zones, because an unowned segment the judge calls an artifact may lie outside one;
how much of the edit lies outside a zone is reported beside it.

An image with the switch on and no decision file is an error and not a silent pass, because a
summary table must never mix judged and unjudged images.

## The dry run, which always comes first

`python src/diagnostics.py ai-dry-run --dir data/WT -o results/ai_dry_run --pictures 543-2,543_3`,
rerun on 2026-10-16 with the new candidates. Nothing is sent.

| image | lacunae | calls | of those, left over | numbered segments | input tokens | output tokens | cost USD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 542_z06 | 19 | 19 | 0 | 208 | 37,643 | 7,660 | 0.1519 |
| 542_z18 | 13 | 13 | 0 | 186 | 25,783 | 6,770 | 0.1193 |
| 543-2 | 12 | 12 | 0 | 130 | 23,763 | 4,790 | 0.0954 |
| 543_3 | 13 | 13 | 0 | 148 | 25,750 | 5,440 | 0.1059 |
| 543_z13 | 11 | 11 | 0 | 153 | 21,816 | 5,575 | 0.0994 |
| 682_z08 | 11 | 11 | 0 | 170 | 21,833 | 6,170 | 0.1054 |
| 682_z23 | 14 | 14 | 0 | 221 | 27,799 | 8,015 | 0.1357 |
| 682_z29 | 15 | 16 | 1 | 215 | 31,750 | 7,845 | 0.1420 |
| **all 8** | **108** | **109** | **1** | **1,431** | **216,137** | **52,265** | **0.95** |

**Estimated $0.95 for all 8 images, $1.91 if every single call had to be retried**, against the $5
ceiling of `config.MAX_COST_USD`. 543-2 alone is $0.095 for 12 calls. The previous version of the
candidates cost $0.80 for 108 calls and 1,099 segments; what grew is the answer, not the picture.

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

Ten checks, all passing on 2026-10-16: the answers validate, a bad answer is retried, a case that
never validates stays unjudged rather than guessed, replay gives the same verdicts, every request is
logged with its hash, no key and no image bytes are in the log, the switch changes the mask, **the
judge edits only the segments it was given**, the pipeline runs to the end with the switch on, and
an image with no decision file is refused rather than passed over.

On 543-2 the stub's arbitrary verdicts keep 21 new segments, refuse 21, and drop 36 the pipeline had
traced, which moves 1,407 px of mask in and 9,607 px out and exercises every path including the one
that removes tracing.

Quantification was then run on 543-2 with the switch on and those stub verdicts, into `.cache/`: it
writes its json as usual, and the record carries the `ai_judge` block (verdicts applied, pixels
added and removed, the geometry hash, the model and when the decisions were written), so no result
file can be mistaken for one the pipeline made alone. **The numbers it gives are meaningless**, for
the same reason the stub's verdicts are, and they are not reported here as anything else.

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

## Steps 5 and 6: the real run is waiting

**No real call has been made. `results/ai_log/` holds no answers.** On 2026-10-15, and again
on 2026-10-16 when the candidates were rebuilt, neither
`ALLOW_EXTERNAL_API` nor `ANTHROPIC_API_KEY` was set, in this session, in the Windows user
environment or in the machine environment, and there is no `.env`. The judge therefore refuses to
call out, which is the design:

```
> python src/diagnostics.py ai-judge --image "data/WT/543-2.tif"
Refused: a real run needs a connection and ALLOW_EXTERNAL_API is not set to 1.
Set ALLOW_EXTERNAL_API=1 and ANTHROPIC_API_KEY, or run with --replay.
```

Everything that does not need the network has been built and run: the candidates on all 8 images,
the pictures, the dry run with its cost, the whole chain end to end against a stub judge, and the
switch through the pipeline to quantification.

**To make the real run on 543-2 happen** (PowerShell, in this repository, the key in the session
only and never in a file):

```powershell
$env:ALLOW_EXTERNAL_API = "1"
$env:ANTHROPIC_API_KEY  = "sk-ant-..."
pip install anthropic
python src/diagnostics.py ai-dry-run --image "data/WT/543-2.tif"   # always first
python src/diagnostics.py ai-judge   --image "data/WT/543-2.tif"
```

Use `$env:` and not `setx`: `setx` writes the key into the Windows registry, where it outlives the
session. In Git Bash the same two lines are `export ALLOW_EXTERNAL_API=1` and
`export ANTHROPIC_API_KEY=sk-ant-...`.

That run will cost about $0.10 for 12 calls, refuse to start if its own estimate is above
`config.MAX_COST_USD`, and stop if the running total passes it. It writes the log, the pictures and
the decision file under `results/ai_log/543-2/`. **The other 7 images are not run**: the brief says
543-2 first and then a review.

## How to run it

```
# Deterministic, no network, no judge: what the judge would be asked about.
python src/diagnostics.py ai-candidates --dir data/WT -o results/ai_dry_run

# What a real run would cost, with the pictures for two images.
python src/diagnostics.py ai-dry-run --dir data/WT -o results/ai_dry_run --pictures 543-2,543_3

# The whole chain with a stub judge, no network and no key.
python src/diagnostics.py ai-judge --image "data/WT/543-2.tif" --self-test

# A real run on one image (needs both environment variables, see above).
python src/diagnostics.py ai-judge --image "data/WT/543-2.tif"

# The same run again, offline, from the log.
python src/diagnostics.py ai-judge --image "data/WT/543-2.tif" --replay

# The pipeline with the judge applied: set config.AI_JUDGE_ENABLED = True and run
# the pipeline as usual. It needs a decision file for every image it is given.
```

The SDK is needed only for a real call: `pip install anthropic`. On this venv's Python 3.9 pip
resolves to the last 0.x release, and the code uses only what 0.x and 1.x share.
