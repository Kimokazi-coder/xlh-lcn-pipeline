# Experiment: an AI judge for the threads around a lacuna

**Status: EXPERIMENT. Branch `exp-ai-layer` only. Not merged, not validated, not used for any
result. NOTHING IN THIS FILE IS VALIDATED.** No verdict here has been checked against a manual
trace, no number here has been compared with ground truth, and no result in `results/` was made with
any of it. What is established is that the machinery does what it says, not that what it says is
right.

`main` is untouched. With `config.AI_JUDGE_ENABLED = False`, which is how this branch ships, every
pipeline output is byte for byte what `main` produces: `reference-check` PASS at
161.00 / 21.63 / 8.50 and `regression` PASS over 6,800 numbers at tolerance 0, rechecked on
2026-10-19.

External API use approved on 2026-10-15, approver: Karim

This file holds two experiments. The first, from here to "What is established, and what is not",
is the **thread judge**: who owns a thread. The second, at the end under **"The lacuna judge"**, is
a judge of which regions are osteocyte lacunae, run on all four groups on 2026-10-27.

## The question  

Ownership goes by the shortest path through the skeleton. That is the right rule for a thread whose
own cell traced it, and the wrong one at a join: a whole connected network can go to a cell that
reaches it through one thread, while another cell lies much closer to where those threads start and
has no skeleton path to them at all. A threshold cannot see which cell a thread leaves. It has no
way to ask that question.

This experiment asks it. **An AI judge decides who owns a thread where the answer is a judgement
call, and a verdict feeds the shortest path step so that the network is split in a sensible place.**

The second question is older and is still here. One global cut empties a ring of skeleton around
every lacuna; METHODS section 18 measured why, a thread's own contrast inside that glow running at
31 to 71% of what the same tissue shows 40 px further out. A permissive tracing proposes the pieces
the cut lost, and the judge says which of them are threads and which are the grain of the glow.

**Deterministic code stays the only code that touches pixels.** `src/ai_judge.py` makes the
candidates, draws the pictures, reads the answer back and hands the pipeline a set of pixels to add,
a set to drop, and the cell each judged thread was said to start from. The judge only ever answers
about a numbered segment in a picture: *which cell does this start from*, and for a piece the
pipeline does not have, *is it a thread at all*. It never sees a file name, a path or a genotype,
and it never writes a pixel. The attachment it earns is a zero weight edge; ownership, the 50 um cap
and all quantification then run exactly where they were.

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

Measured over the 8 images (regenerate with `python src/diagnostics.py ai-candidates --dir data/WT -o
results/ai_dry_run`; not tracked since 2026-10-20, as cited at commit `bf3b982`). Each class cell is **segments / pixels / lacunae involved**, where a lacuna
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
carries as a number (`ai_judge.counts.edited_px_outside_the_judged_segments`, 0). How much of it
lies outside a zone of the hole is reported beside it.

An image with the switch on and no decision file is an error and not a silent pass, because a
summary table must never mix judged and unjudged images.

## The dry run, which always comes first

Regenerate with `python src/diagnostics.py ai-dry-run --dir data/WT -o results/ai_dry_run --pictures all`
(not tracked since 2026-10-20; as cited, at commit `bf3b982`), rerun on
2026-10-19 with the four classes. Nothing is sent.

| image | lacunae | calls | of those, left over | segments | a | b | c | d | input tokens | output tokens | cost USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 542_z06 | 19 | 24 | 5 | 108 | 43 | 46 | 0 | 19 | 68,968 | 4,260 | 0.1805 |
| 542_z18 | 13 | 19 | 6 | 118 | 49 | 46 | 0 | 23 | 55,503 | 4,510 | 0.1561 |
| 543-2 | 12 | 16 | 4 | 88 | 11 | 50 | 0 | 27 | 46,575 | 3,400 | 0.1271 |
| 543_3 | 13 | 23 | 10 | 163 | 28 | 81 | 0 | 54 | 68,037 | 6,165 | 0.1977 |
| 543_z13 | 11 | 15 | 4 | 83 | 17 | 48 | 0 | 18 | 43,668 | 3,205 | 0.1194 |
| 682_z08 | 11 | 12 | 1 | 72 | 26 | 39 | 0 | 7 | 35,067 | 2,760 | 0.0977 |
| 682_z23 | 14 | 17 | 3 | 120 | 52 | 46 | 0 | 22 | 50,085 | 4,540 | 0.1456 |
| 682_z29 | 15 | 19 | 4 | 143 | 40 | 63 | 0 | 40 | 56,417 | 5,385 | 0.1667 |
| **all 8** | **108** | **145** | **37** | **895** | **266** | **419** | **0** | **210** | **424,320** | **34,225** | **1.19** |

**Estimated $1.19 for all 8 images, $2.38 if every single call had to be retried**, against the $5
ceiling of `config.MAX_COST_USD`. 543-2 alone is $0.13 for 16 calls. 125 of the 145 calls use the
256 px crop and 20 use the 512 px one; `numbered but not drawn` is 0, as it must be.

The previous round cost $0.95 for 109 calls and 1,431 segments. There are now more calls and fewer
segments, which is the shape of the change: the unowned tracing with no cell within reach is no
longer asked about, and class d and the crops that can hold two candidate bodies are.

**The pictures of every case of all 8 images, exactly as the judge would see them, are in
`results/ai_dry_run/pictures/`** (145 of them, 18 MB; not tracked, regenerate with the command
above). They are the pictures a run would send; the ones that were actually sent are in
`results_ai_judge/WT/ai_log/<label>/pictures/`.

## The self-test

`python src/diagnostics.py ai-judge --image "data/WT/543-2.tif" --self-test` rehearses the whole
chain on one image with a **stub judge**, no network and no key: a picture becomes a request, a stub
answer becomes verdicts, the log replays to the same verdicts, and the switch then edits the mask
and runs the rest of the pipeline on it. The stub answers by a fixed rule that means nothing
biologically (odd numbers real, even numbers artifact, some answers deliberately unreadable), so it
checks the machinery and never the judgement. Everything it writes goes to `.cache/ai_self_test`,
never to `results/`, so a rehearsal cannot leave verdicts where the pipeline could pick them up.

**Thirteen checks, all passing on 2026-10-19**: the answers validate, a bad answer is retried, a
case that never validates stays unjudged rather than guessed, replay gives the same verdicts, every
request is logged with its hash, no key and no image bytes are in the log, the switch changes the
mask, the judge edits only the segments it was given, the pipeline runs to the end with the switch
on, **nothing the judge said deleted tracing the pipeline made**, **a verdict moves a network
between two owners**, **a segment two cases answer differently is left alone and counted**, and an
image with no decision file is refused rather than passed over.

The last two are the ones this round adds, and they are the two the design turns on.

- **A verdict moves a network.** The stub gives every white number to the LAST candidate it is
  offered, which for a class d segment is the cell that does not own it, so the attachment goes in
  and the shortest path has to redo the split. On 543-2: 54 segments attached, **30 of them to a
  cell that did not own them**, and **1,426 px of tracing changed hands between 14 pairs of cells**,
  the largest single move being 258 px from cell 7 to cell 5. None of that is written by the judge;
  it is what the shortest path did once the attachment was in the graph.
- **Two cases that disagree.** No segment on these 8 images is numbered in two cases, so the rule is
  exercised on a decision file written for it: one segment the stub judged is answered a second
  time, in a case of its own, with a different owner. Nothing else in the file changes and the
  geometry hash still matches, because what the judge was *asked* is the same. The switch then
  counts 1 conflicting segment and attaches **53 segments instead of 54**: that one attaches to
  neither cell and keeps the decision the pipeline made.

On 543-2 the stub's arbitrary verdicts keep 21 new segments and refuse 21, which moves 1,428 px of
mask in and 985 px out. **No traced segment is dropped, and none can be**: only a class b number is
asked whether it is real.

Quantification was then run on 543-2 with the switch on and those stub verdicts, into `.cache/`: it
writes its json as usual, and the record carries the `ai_judge` block (verdicts applied, pixels
added and removed, the geometry hash, the model and when the decisions were written), so no result
file can be mistaken for one the pipeline made alone. **The numbers it gives are meaningless**, for
the same reason the stub's verdicts are, and they are not reported here as anything else.

## Reproducibility

- **The model is pinned** in `config.AI_JUDGE_MODEL` (`claude-sonnet-5-5`), and no server side
  fallback to another model is enabled: a refusal is logged and the case stays unjudged, because a
  silent fallback would break the pin.
- **Every request and every answer is logged** to `results_ai_judge/WT/ai_log/<label>/`, one json per attempt,
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
- **A billing, credit or authentication error stops the whole run at once.** A bad answer is
  retried once and a case that never validates is left unjudged, which is right for a bad answer and
  wrong for this: a run that carried on past a spent balance would mark every remaining segment
  unjudged and write a decision file that looked like a considered result, when nothing was ever
  asked. So that error is logged, raised, and the run ends: no decision file for that image, no
  further image, and nothing recorded as unjudged. It is recognised by the SDK's own error classes
  (`AuthenticationError`, `PermissionDeniedError`) and by what the server says in a plain bad
  request, which is how a spent balance arrives, and the key is scrubbed out of the message first.
- **A run of several images watches the share of answers it cannot read.** After
  `config.AI_MIN_CALLS_BEFORE_QUALITY_GATE` = 20 calls, if more than
  `config.AI_MAX_UNJUDGED_SHARE` = 20% of the cases still have no valid answer after their one
  retry, the run stops and nothing after it is attempted. A prompt the model cannot answer should
  cost twenty calls and not a hundred and forty five.

## Decisions taken while building this

The brief left these open. Each was decided, and here is the reason.

| Decision | What was chosen | Why |
| --- | --- | --- |
| What "the measured empty width" is measured on | the global cut skeleton, before the dim pass and the 50 um prune | that is the skeleton in hand where the candidates are made, and it depends on no later stage and on no ownership |
| What the contrast ratio is | p90 of the ridge response in the 40 px band beyond the hole over the p90 in the hole, per lacuna | it is METHODS section 18's own measurement, per lacuna; it lands in 1.24 to 3.0, median 2.11, which is the 1.4 to 3.2 that section measured with a short tail either side |
| How a segment is defined | a branch of the permissive skeleton, split at junctions, clipped to one zone, at least 10 px | branches are what "split into numbered segments" means for a skeleton; 10 px is the floor the pipeline already uses for an unowned thread |
| What "within reach" means, which decides class d, the candidates and which unowned segments are asked about | the lacuna's body lies within that lacuna's own zone of the hole plus 10 px of the segment | both numbers are the pipeline's, so one rule serves three questions and the experiment defines nothing of its own |
| How many candidates a number is offered | at most two, nearest body first, and neither the case's own body nor the current owner can be dropped | the brief asks for the first candidate, the second, or none; keeping the current owner means the judge can always leave ownership where it is |
| Which case a class d segment is asked in | the case of the NEAREST body, the one that does not own it | that is the body whose vicinity the segment sits in, so its crop almost always holds the segment |
| Where a verdict's attachment lands | the end of the segment nearest the named cell | the path has to enter the thread where the thread starts; the nearest pixel would let it enter halfway along and measure the thread from its middle |
| Whether a traced segment can be judged an artifact | no: only a segment the pipeline does not have is asked whether it is real | the brief asks a, c and d for an owner only, and it means nothing the judge says can delete tracing the pipeline made |
| What an unowned segment with no lacuna within reach does | it is not asked about at all | no body in its picture could be named as its owner, so the only answer it could be given is the one the pipeline already has, and there are 1,835 of them |
| Where the permissive mask is skeletonized | once over the whole frame | a mask clipped at the zone boundary has a medial axis that runs along that boundary, which would invent threads shaped like the hole |
| Segments in two zones | given to the nearer body | the pipeline's own nearest-lacuna partition; it makes double judging impossible |
| How many segments per case | at most 40, longest first | the picture has to stay readable and the answer small; nowhere near binding on these 8 images |
| What an "artifact" verdict removes | the mask whose nearest centre line is that segment | the smallest edit that expresses the verdict, and it leaves every unjudged segment untouched |
| What an unjudged segment does | keeps the deterministic decision | the brief says so, and for a candidate that means the pipeline's own mask stands |
| What owner `none` does | no attachment is added, the existing rules decide | the judge grants ownership and never vetoes it, so no ownership rule moves into the model |
| Temperature 0 | not sent to this model, recorded as not sent | the pinned model returns HTTP 400 for any non-default temperature |
| Prompt caching | not used | the saving over about 110 calls is a few cents and a cache write is a second price to account for |
| Server side refusal fallback | not enabled | it would break the pinned model |
| Where the fixed prompt lives | `src/judge_prompt.md` | the code loads it and hashes it; it is part of the method, like `config.py` |

## Step 7: the real run, its replay, and what it did to the network

**The real run was made on 2026-10-19, 15:58 to 16:14 UTC, on all 8 images**, and its every request
and answer is in `results_ai_judge/WT/ai_log/`. From the log:

| image | calls | answers retried | cases left unjudged | input tokens | output tokens | cost USD |
| --- | --- | --- | --- | --- | --- | --- |
| 542_z06 | 23 | 0 | 0 | 85,055 | 6,598 | 0.2361 |
| 542_z18 | 19 | 0 | 0 | 71,493 | 6,588 | 0.2089 |
| 543-2 | 16 | 0 | 0 | 59,932 | 5,180 | 0.1717 |
| 543_3 | 23 | 0 | 0 | 87,831 | 9,154 | 0.2672 |
| 543_z13 | 16 | 1 | 0 | 60,189 | 5,418 | 0.1746 |
| 682_z08 | 12 | 0 | 0 | 45,129 | 4,159 | 0.1318 |
| 682_z23 | 16 | 0 | 0 | 61,129 | 6,507 | 0.1873 |
| 682_z29 | 18 | 0 | 0 | 69,407 | 8,012 | 0.2189 |
| **all 8** | **143** | **1** | **0** | **540,165** | **51,616** | **1.60** |

- Every answer came from the pinned `claude-sonnet-5-5`, and no request needed the thinking
  fallback.
- **One answer in 143 could not be read** (543_z13 `case_0004`, a red number with no verdict). It was
  retried once and the retry was valid, so **no case and no segment was left unjudged**. The quality
  gate never came near tripping.
- 3 of the 145 cases had no numbered segment once the crop was drawn and needed no call, which is
  why there are 143 calls and not 145.
- 895 segments judged: 722 real and 173 artifact. Of the 554 verdicts that named an owner, 52 left
  the segment with the cell that already owned it, 364 gave an owner to a segment nobody owned, and
  **138 moved a segment from one cell to another**.
- **The dry run estimated $1.19 and the run cost $1.60.** The estimate ran about 27% low, nearly all
  of it on input tokens (540,165 against 424,320 estimated). It stayed well inside the $5 ceiling,
  but a later estimate should be read as a floor.

**The replay reproduces it offline.** `python src/diagnostics.py ai-judge --dir data/WT --replay`
rebuilds every request and every picture, finds every hash equal to the one logged, and gets
IDENTICAL verdicts on all 8 images: 143 attempts, 0 requests and 0 pictures differing from what was
sent (`results_ai_judge/WT/replay.txt`). A replay never reads `ALLOW_EXTERNAL_API` or
`ANTHROPIC_API_KEY`; only a live run asks.

**The pipeline with the switch on** was run by `python src/diagnostics.py ai-run --dir data/WT`,
which turns `config.AI_JUDGE_ENABLED` on for that process only, runs detection, canaliculi and
quantification exactly as the three scripts do, and writes to `results_ai_judge/WT/`, the second
labelled set, a sibling of `results/WT/` with the same per-image layout (its own README says what is
in it). `config.py` still ships with the switch off. The command hashes every file under `results/`
and every file of the judge log before and after, and **both were byte identical afterwards**
(`results_ai_judge/WT/ai_run.json`).

**Judge off against judge on** is in `results_ai_judge/WT/compare/REPORT.md`, made by
`python src/diagnostics.py ai-compare --dir data/WT`, with the verification and skeleton pictures
side by side and a picture of what changed hands for every image. Both runs are recomputed and
checked against the files on disk pixel for pixel before a number is reported, and every check
passed. Over the 8 images:

- **21,373 px of tracing changed hands between cells, in 770 segments**, and they move as whole
  connected networks, which is what the design is for: the shortest path, given the attachment,
  splits the network where the two cells' paths meet. Class d on its own moves 21,843 px.
- **No single cell takes over an image**: the largest owner's share of the skeleton moves by at most
  0.015 on any image (542_z18, 0.091 to 0.106).
- Owned tracing rises and unowned falls on every image, by 1,211 to 4,030 px owned.

**Roots, and the fix.** A root is counted from the nodes attached to a cell's virtual node, and a
verdict is expressed as exactly such an attachment, at the end of the segment nearest the cell,
which can lie tens of pixels from the body. Before the fix every such verdict added a root that is
not a thread leaving the body: judge-on roots rose from 1,045 to 1,482 over the 8 images, and on
543-2 the mean per interior cell from 8.5 to 12.92.

**The fix keeps the attachment and stops counting it.** The edge a verdict makes is marked `judged`
(`canaliculi.attach_judged_segments`), it splits the network through the shortest path exactly as
before, and a root is counted only for an attachment the pipeline's own contact or attach rule made,
which only ever attach within reach of the body (`quantification.root_points`). Where the pipeline
had already joined that cell to that node, the edge stays the pipeline's and stays a root. With the
switch off no edge is marked, so every number is what it was.

| image | roots, judge off | judge on, before the fix | judge on, after the fix | mean per interior cell: off / before / after |
| --- | --- | --- | --- | --- |
| 542_z06 | 249 | 289 | 262 | 15.13 / 17.27 / 15.80 |
| 542_z18 | 133 | 182 | 141 | 11.82 / 16.18 / 12.45 |
| 543-2 | 102 | 155 | 108 | 8.50 / 12.92 / 9.00 |
| 543_3 | 86 | 183 | 100 | 7.00 / 14.25 / 8.17 |
| 543_z13 | 102 | 144 | 105 | 9.27 / 13.09 / 9.55 |
| 682_z08 | 131 | 163 | 143 | 12.33 / 15.33 / 13.67 |
| 682_z23 | 125 | 182 | 132 | 9.73 / 14.09 / 10.36 |
| 682_z29 | 117 | 184 | 122 | 7.85 / 12.62 / 8.23 |
| **all 8** | **1,045** | **1,482** | **1,113** | |

The 68 roots that remain above judge off are tracing the judge added that touches a body, which the
pipeline's own contact rule attaches like any other thread. Every lacuna is in
`results_ai_judge/WT/roots_before_and_after_the_fix.md`, and `results_ai_judge/WT/compare/REPORT.md`
recomputes the before-the-fix count from the judge-on graph itself.

The two guards a run leans on are still rehearsed in the self-test with no network: with every
answer unreadable the run stops after 20 calls, and a billing error stops it at the first case with
no decision file written.

**To run the judge again** (PowerShell, in this repository, the key in the session only and never in
a file):

```powershell
$env:ALLOW_EXTERNAL_API = "1"
$env:ANTHROPIC_API_KEY  = "sk-ant-..."
pip install anthropic
python src/diagnostics.py ai-dry-run --dir data/WT -o results/ai_dry_run   # always first
python src/diagnostics.py ai-judge   --dir data/WT                        # all 8 images
python src/diagnostics.py ai-judge   --dir data/WT --replay               # offline, same verdicts
```

Use `$env:` and not `setx`: `setx` writes the key into the Windows registry, where it outlives the
session and every process in it. The key is never read back, printed, logged or written to a file by
anything here, and it is scrubbed out of an error message before that message is logged. In Git Bash
the two lines are `export ALLOW_EXTERNAL_API=1` and `export ANTHROPIC_API_KEY=sk-ant-...`.

## How to run it

```
# Deterministic, no network, no judge: the four classes and what needs a decision.
python src/diagnostics.py ai-candidates --dir data/WT -o results/ai_dry_run

# What a real run would cost, with every case picture of every image.
python src/diagnostics.py ai-dry-run --dir data/WT -o results/ai_dry_run --pictures all

# The whole chain with a stub judge, no network and no key: 15 checks.
python src/diagnostics.py ai-judge --image "data/WT/543-2.tif" --self-test

# A real run (needs both environment variables, see above).
python src/diagnostics.py ai-judge --dir data/WT

# The same run again, offline, from the log.
python src/diagnostics.py ai-judge --dir data/WT --replay

# The pipeline with the switch on for that run only, into results_ai_judge/WT/, and
# judge off against judge on with the pictures, into results_ai_judge/WT/compare/.
python src/diagnostics.py ai-run --dir data/WT
python src/diagnostics.py ai-compare --dir data/WT

# The pipeline with the judge applied: set config.AI_JUDGE_ENABLED = True and run
# the pipeline as usual. It needs a decision file for every image it is given.
```

The SDK is needed only for a real call: `pip install anthropic`. On this venv's Python 3.9 pip
resolves to the last 0.x release, and the code uses only what 0.x and 1.x share.

## What is established, and what is not

Established, and each one measured rather than asserted:

- the four classes exist and are counted on all 8 images, class d among them with 210 segments and
  77 of the 108 lacunae;
- every segment in a class is asked about in some picture, with both of its candidates visible
  (`needs_a_decision_but_no_case_could_ask` is 0 on all 8);
- a verdict becomes an attachment and the **shortest path then moves tracing between two cells**,
  1,426 px of it on 543-2 under the stub's arbitrary answers;
- nothing the judge says can delete tracing the pipeline made;
- two answers that disagree are no answer, and the segment is left as the pipeline had it;
- the whole chain replays offline to the same verdicts, with every request hashed;
- a billing error stops the run at once, and a run whose answers cannot be read stops itself;
- the real run on all 8 images left no segment unjudged, cost $1.60, and replays offline to the same
  verdicts; with the switch on, 21,373 px of tracing change hands between cells as whole networks,
  and nothing under `results/` outside `results_ai_judge/` changes by a byte;
- with the switch off every number is `main`'s, over 6,800 of them at tolerance 0.

**Not established, and nothing here should be read as if it were.** No verdict has been checked
against a manual trace. No judgement in this design has been shown to be a better judgement than the
pipeline's. The 145 pictures say what the judge would be asked; they do not say the answer would be
right, and the cost of a wrong answer is not symmetric, because a thread given to the wrong cell
moves that cell's whole measured network. **Nothing here is validated**, nothing here has produced a
result, and none of it may be used for one until it has been checked against ground truth and that
check is written down.

# The lacuna judge

**Status: EXPERIMENT, pre-validation. NOT VALIDATED: no verdict has been checked against a manual
count, and nothing here is a result of the study.** It is behind `config.AI_LACUNA_JUDGE_ENABLED`,
which is off by default, and it writes only to `results_ai_lacunae/`. With the switch off every
number is `main`'s: `regression` PASS over 6,800 numbers at tolerance 0 in both of its runs and
`reference-check` PASS at 161.00 / 21.63 / 8.50, on 2026-10-27. METHODS section 23 is the short
version, with every decision taken where the brief left a choice open.

External API use approved on 2026-10-15, approver: Karim

## What it is for, and what it does and does not do

The lacuna stage was shaped on the 8 WT images. On the other groups it outlines saturated bands,
soft tissue and small fragments as lacunae and misses dim or out-of-focus bodies. The lacuna judge
is shown, once per image, every candidate region the lacuna stage outlined, numbered, and answers
per number whether the region inside the outline is an osteocyte lacuna: **yes, no or unsure**, with
a one line why.

What it does **not** do:

- **It never draws or changes a boundary.** Every region it can keep or drop is one the lacuna
  stage outlined itself, so a lacuna it keeps has the pipeline's own outline and nothing else.
- It never sees a file name, a group or a mouse: the request carries a neutral image code, the first
  8 hex digits of the sha256 of the image's pixels.
- It changes no parameter and tunes nothing. The prompt (`src/judge_prompt_lacunae.md`) is the same
  for every image of every group, so the rule is the same everywhere. `docs/judge_examples_lacunae.md`
  holds the rules in words and no worked example.
- It does not touch the thread stages. With the switch on, the lacunae it decided go into the
  canalicular stage and the quantification exactly as the deterministic lacunae do.
- It does not touch the thread judge (its prompt hashes are still those its real run logged), and it
  writes nothing under `results/` or `results_ai_judge/`.

## The candidates and the numbers

The candidates are every region of the lacuna stage's label image of at least
`config.AI_LACUNA_MIN_CANDIDATE_AREA_PX2` = 100 px², kept and rejected by the filters, plus the
**dim candidates**: the regions of the same mask at `config.AI_LACUNA_DIM_CUT_FRACTION` = 0.8 of the
image's own lacuna cut that overlap none of them. Nothing is merged or split.

At most `config.AI_LACUNA_MAX_NUMBERED` = 60 are numbered per image. With more, which get a number
goes by an order of priority and the cap drops from its end, each tier largest first: **every region
the filters kept**, then every region they rejected of at least
`config.AI_LACUNA_PRIORITY_REJECTED_MIN_AREA_PX2` = 300 px², then the dim candidates, then the
rejected regions under 300 px². The numbers themselves run in reading order down the picture, so a
number does not say what the filters decided. A kept lacuna is left unnumbered only on an image with
more than 60 kept lacunae; every report would print it, and there is none. A region with no number
keeps the deterministic decision.

The picture is two panels of the raw signal channel at its own pixels, unstretched: left nothing
drawn, right every numbered candidate outlined in yellow, all in the same colour whatever the filters
decided, with its number in white beside it.

## How a verdict is used

With `config.AI_LACUNA_JUDGE_ENABLED` on, the lacuna stage rebuilds the candidates from its own
result, checks their geometry hash against the decision file and then, per numbered region:

| verdict | what happens |
| --- | --- |
| yes | a lacuna, even if a shape filter rejected it; a region added this way is the class `judged`, counted and owning threads, with no area or shape measure, like the class `dim` |
| no | not a lacuna, even if the filters kept it |
| unsure | the deterministic decision stands |
| unjudged, or no number | the deterministic decision stands |

An image with no decision file, or one written for other candidates, is refused rather than passed
over, so a run never mixes judged and unjudged images.

## Guardrails, all kept from the thread judge

- The model is pinned (`claude-sonnet-5-5`), no temperature is sent (the model rejects one), and
  thinking is off.
- Every request and answer is logged with the sha256 of the request, the picture, the prompt and the
  examples, in `results_ai_lacunae/<group>/ai_log/<image>/`, with the picture that was sent.
- The dry run is the default and sends nothing. A real call needs `ALLOW_EXTERNAL_API=1` and
  `ANTHROPIC_API_KEY` in the environment of that one process. The key is never printed, logged or
  written to a file.
- A cost estimate is made before the first call and the run refuses to start above
  `config.AI_LACUNA_MAX_COST_USD` = $3 (its own ceiling; the thread judge keeps $5). The run stops
  once what the answers actually cost passes it.
- A billing, credit or authentication error stops the run at once, and the run stops if more than
  20% of the first 20 answers are unreadable after one retry.
- The replay reruns the log offline and must give identical verdicts.

**Speed.** The lacuna stage takes up to about an hour on the largest Hyp image. Its result is kept
in `.cache/ai_lacuna_candidates/`, keyed by the sha256 of the image's pixels, every non-path, non-AI
setting of `config.py`, `src/lacunae.py` and the library versions; the dry run, the live run and the
replay read it, so the stage runs once per image. Built once for the 35 images on 20 processes: 34
within 30 minutes and the last, 701_z19, at 68 minutes, its lacuna stage alone; read back, about a
second per image.

## The self-test

`python src/diagnostics.py ai-lacuna-judge -s` rehearses the whole chain on WT 543-2 with a stub judge
whose answers mean nothing biologically, no network and no key, into `.cache/ai_lacuna_self_test/`.
**27 checks, all passing on 2026-10-27**, among them: the cached lacuna stage gives byte for byte the
candidates and the picture a fresh one gives; over the cap every kept lacuna is numbered and the cap
drops from the end of the order, on the self-test image with the cap lowered and on **all 23 real
images over the cap**, up to 163 candidates; with more kept lacunae than the cap those left out are
counted and reported; a yes adds a region the filters rejected and a no removes one they kept, unsure
keeps the deterministic decision; every lacuna's boundary is one the lacuna stage drew; a region
added is class `judged`, counted and owning threads; the review's table is what the switch does in
the pipeline; and the guards (no decision file, wrong candidates, unreadable answers, a billing
error, the cost ceiling, a live run without the flag) all hold.

## The dry run

`python src/diagnostics.py ai-lacuna-judge -w 20`, in `results_ai_lacunae/dry_run/` with every picture
exactly as the judge would see it: **35 calls, 1,882 numbered regions** (793 kept by the filters,
all of the 793 kept lacunae; 196 regions they rejected; 893 dim candidates), estimated 133,455 input
and 66,570 output tokens, **$0.93**. 23 images are over the cap, and no kept lacuna is left
unnumbered.

## The real run, 2026-10-27

**Made on 2026-10-27, 16:29 to 16:35 UTC, on all 35 images of the four groups**, one call per image,
with the two environment variables set for that one process only.

- 35 calls to the pinned `claude-sonnet-5-5`, thinking off and accepted (no fallback).
- **No answer was unreadable, none was retried, none was refused**, and the run was not stopped.
- 147,968 input and 52,935 output tokens: **$0.83** ($0.8253), against the estimate of $0.93 and the
  ceiling of $3. Input ran 11% over the estimate and output 20% under it.
- 1,882 verdicts: **304 yes, 1,408 no, 170 unsure, 0 unjudged.**

The run's summary is `results_ai_lacunae/ai_lacuna_judge_run.json`.

**The replay reproduces it offline**, with neither environment variable set: every request and every
picture rebuilt hashes to what the log says was sent (35 attempts, 0 differ), and the verdicts are
IDENTICAL on all 35 images (`results_ai_lacunae/ai_lacuna_replay.json`).

## What the verdicts do

Over the 35 images (per image in `results_ai_lacunae/review/review.md`, with a contact sheet per
group; every region's verdict and why in `review_regions.csv`):

| | yes | no | unsure |
| --- | --- | --- | --- |
| regions the filters kept (793) | 297 | 352 | 144 |
| regions the filters rejected (196) | 1 | 185 | 10 |
| dim candidates (893) | 6 | 871 | 16 |

So **7 regions are added** (6 of them dim candidates) and **352 kept lacunae are removed**, on 29 of
the 35 images; the lacuna count over the 35 images goes from 793 to 448. The judge says no far more
often than yes. On the contact sheets what it removes includes the saturated bands, the bright frame
edges, soft tissue patches and small fragments it was built for, and also some large bright bodies
that look like lacunae at thumbnail size. Whether each of those calls is right is exactly what has
not been checked.

Two objects the README lists as probably not lacunae (open question 4) were both judged **no**:
542_z06 at (555,149), "thin elongated strand along line", and 682_z23 at (363,7), "thin fragment at
top edge". That agrees with the suspicion; it does not validate the judge.

**The pipeline with the verdicts** was run by `python src/diagnostics.py ai-lacuna-run -w 20`,
which turns the switch on for that process only and runs detection, canaliculi and quantification
from the decision files into `results_ai_lacunae/<group>/`, the same per-image layout as
`results/<group>/`. Its per-image counts equal the review's on all 35 images, and every quantified
lacuna count equals the review's count after. It hashed `results/` (601 files), `results_ai_judge/`
(438 files) and the judge's own log before and after, and **all were byte identical afterwards**
(`results_ai_lacunae/ai_lacuna_run.json`). The numbers it writes are those of an unvalidated
experiment and are not compared here with the deterministic ones, group by group or otherwise.

## How to run it

```
# What a real run would send and cost, with every picture. Sends nothing.
python src/diagnostics.py ai-lacuna-judge -w 20

# The whole chain with a stub judge, no network and no key: 27 checks.
python src/diagnostics.py ai-lacuna-judge -s

# A real run: needs ALLOW_EXTERNAL_API=1 and ANTHROPIC_API_KEY in the environment of this process.
python src/diagnostics.py ai-lacuna-judge --live

# The same run again, offline, from the log.
python src/diagnostics.py ai-lacuna-judge --replay -w 20

# The contact sheets and the per-image table, from the log, into results_ai_lacunae/review/.
python src/diagnostics.py ai-lacuna-review -w 20

# The pipeline with the switch on for that run only, into results_ai_lacunae/<group>/.
python src/diagnostics.py ai-lacuna-run -w 20
```

Set the two variables for one process only, and never with `setx`, which writes them into the
registry. The key is never read back, printed, logged or written to a file by anything here.

## Established, and not

Established, each one measured: the candidates, the numbering order and the picture are
deterministic and come byte for byte from the cache as from a fresh lacuna stage; every kept lacuna
was numbered on every image; the real run left no region unjudged, cost $0.83 and replays offline to
identical verdicts; the switch applies exactly the verdicts and nothing else, and with it off every
number is `main`'s.

**Not established.** No verdict has been checked against a manual count, so nothing here says a yes
or a no is right. The judge removes 352 of 793 kept lacunae; if it is wrong about them, every per
cell measure of those images moves with it. **Nothing here is validated**, and none of it may be used
for a result until it has been checked against a manual count and that check is written down.
