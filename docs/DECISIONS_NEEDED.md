# Decisions needed

Questions raised during the overnight autonomous run of 2026-09-24 that need
human judgement. For each: the evidence, the options, my recommendation, and
what I actually did. **In every case I took the safe option — changed no
default and deleted nothing.**

Nothing in this file has been validated against ground truth. Everything is
v1-raw / v2-raw, pre-validation, in pixel units.

---

## D0. Phase 2 guard thresholds (written BEFORE running, for the record)

The brief requires the "jump" thresholds to be fixed in writing before any
Phase 2 setting is run, and applied consistently. They are:

**G1 — total skeleton length.** FLAG a setting if total skeleton pixels
exceed **1.20x** the current default.

*Why 20%:* reconnecting genuinely broken threads adds only the pixels inside
the gaps. Phase 0(c) measured ~1,500 endpoint-gap pairs per image with gap
lengths of 2–15 px (median ~10) against ~35,000 skeleton px. Bridging
*every* gap would add ~15,000 px, about +43%. A defensible bridging step
takes maybe a third of those, so ~+13%. A setting adding more than +20% is
therefore adding material beyond any plausible gap closure — it is admitting
new regions, not joining existing threads.

**G2 — loop count.** Loops are the cyclomatic number of the real skeleton
graph, `E - V + C`. FLAG a setting if loops exceed
**max(1.5 x default, default + 50)**.

*Why the two-part form:* the default network is close to a forest (82% of
nodes are degree-1), so its loop count is small and a pure ratio on a
near-zero base is meaningless. The absolute floor of +50 stops a jump from,
say, 3 loops to 40 being called a 13x failure; the 1.5x ratio catches growth
once the base is substantial. Fusing two neighbouring parallel threads
creates exactly one cycle, so this is the direct measure of the failure mode
Phase 0(c) warned about.

**Secondary readouts, NOT guards:** owned length fraction (should rise),
components per 10,000 skeleton px (should fall), degree-1 fraction (should
fall). Phase 0(c) found only 21% of endpoint-to-neighbour angles are under
20 degrees, so many nearest neighbours are *parallel threads*, not
continuations. Fusing them raises the owned fraction and looks like success.
Owned fraction alone can therefore never justify a setting.

---

## D1. Phase 2: which fragmentation setting, if any, should become default?

**Status: NOTHING CHANGED. `PREPROCESS_MODE="tophat"`,
`THRESHOLD_MODE="multiotsu_low"`, `GAP_BRIDGING=False` all still default.**

Eight settings were run on all 8 WT images. Guards G1/G2 were fixed before
running (D0 above). Five settings FAILED a guard; three passed.

| setting | length | loops | comp/10k | deg1_f | owned_f | bridges | guards |
|---|---|---|---|---|---|---|---|
| default | 1.00x | 1.00x | 225.3 | 0.825 | 0.244 | 0 | ok |
| hysteresis (0.5) | 1.30x | 6.53x | 102.2 | 0.664 | 0.581 | 0 | **G1+G2** |
| **hyst-0.75** | 1.13x | 2.11x | 174.0 | 0.767 | 0.337 | 0 | ok |
| ridge | 1.19x | 8.42x | 64.2 | 0.592 | 0.773 | 0 | **G2** |
| ridge+hyst | 1.57x | 39.79x | 11.2 | 0.398 | 0.976 | 0 | **G1+G2** |
| **default+bridge** | 1.02x | 1.03x | 188.0 | 0.798 | 0.291 | 122 | ok |
| ridge+bridge | 1.21x | 8.92x | 46.3 | 0.560 | 0.837 | 79 | **G1+G2** |
| **hyst0.75+bridge** | 1.13x | 2.13x | 169.1 | 0.763 | 0.343 | 18 | ok |

(tuning set; held-out agrees closely — e.g. hyst0.75+bridge 1.13x/2.17x,
default+bridge 1.02x/1.08x)

**The guards did real work.** `ridge+hyst` reaches an owned fraction of
0.976 and only 11.2 components per 10k — by the secondary readouts alone it
looks like a complete fix. It is not: loops go 13 to 504, and the longest
skeleton component goes from 708 px to 36,051 px in 542_z06 and from 1,213
to 55,831 in 682_z23. That is the whole field fusing into one object,
exactly the failure Phase 0(c) predicted when it found only 21% of
endpoint-to-neighbour angles are under 20 degrees. Had owned fraction been
the criterion, the worst setting would have won.

**Straight-line fusion guard** (longest straight run inside a Phase 1
flagged structure): the three passing settings barely move it — in 542_z06
it stays at 64.2 px for all of them, against 84.2 for ridge and 84.2 for
ridge+hyst; in 542_z18, 92.8 (default) to 96.5/103.1/96.5 for the passing
settings against 347.3 for ridge+hyst. So the passing settings do NOT
stitch flagged structures into lines.

**My recommendation: `hyst0.75+bridge`** (THRESHOLD_MODE="hysteresis" with
HYSTERESIS_LOW_FRACTION=0.75, GAP_BRIDGING=True), because:
- best fragmentation improvement of the three passing settings: components
  per 10k 225 to 169 (-25%), owned length fraction 0.244 to 0.343 (+41%),
  degree-1 fraction 0.825 to 0.763;
- it stays well inside both pre-declared guards (1.13x length, 2.13x loops
  against a 1.20x / 63-loop limit) on tuning AND held-out;
- the two mechanisms agree with each other: adding bridging on top of
  hysteresis contributes only 18 bridges, against 122 on the default,
  because hysteresis has already closed most of the same gaps. Two
  independent methods converging on the same gaps is evidence those gaps
  are real.

**Conservative alternative: `default+bridge`** — 1.02x length, 1.03x loops,
the smallest change that still helps (comp/10k 225 to 188). Choose this if
you want the minimum deviation from what has been looked at so far.

**Caveat you should weigh.** `HYSTERESIS_LOW_FRACTION=0.75` was SELECTED by
this comparison: 0.5 was tried first and failed both guards, 0.75 passes.
That is tuning on the tuning set, which the ground rules allow, and the
held-out numbers confirm it without re-tuning. But it is one value tried
after one failure, not a swept parameter, and it has no independent
provenance. Treat it as a candidate.

---

## D2. Should the exclusion default be revisited given Phase 2?

**Status: NOTHING CHANGED. `EXCLUSION_MODE="none"` still default.**

The brief asked me to record whether any Phase 2 setting stitches a flagged
structure's fragments into a long line, and if so whether the exclusion
default should be revisited.

**It does happen, but only for settings that are rejected anyway.** With
`ridge+hyst`, the longest straight run inside the flagged structure goes
from 92.8 to 347.3 px in 542_z18 and the longest component inside it from
163 to 1,580 px. With `ridge`, 195.5 px. Those settings fail G1/G2 on their
own and are not candidates.

For the three settings that pass the guards, the longest straight run
inside flagged structures moves by at most ~10 px (542_z18: 92.8 to 96.5 or
103.1; 682_z23: 103.6 to 113.7 or 126.3).

**Recommendation: leave `EXCLUSION_MODE="none"` for now.** The Phase 1
evidence against switching it on stands (flagged structures do not clearly
inflate the canaliculi mask: density ratios 1.13, 1.03, 0.85, 1.25, 1.43),
and no passing Phase 2 setting creates a new reason to turn it on. **But if
you ever adopt a ridge-based setting, revisit this** — under ridge the
flagged structures do get traced as long lines, and exclusion would then be
doing real work.

---

## D3. Why the (230,300) lacuna in 542_z06 is rejected, and what to do

**Status: NOTHING CHANGED. `TEST_MIN_SOLIDITY` is still 0.5, as instructed.**

**It is not a threshold miss.** The object IS in v2's mask — area 1698 px²,
mean intensity 0.901 against t_hi = 0.647, so comfortably bright. v2's
`filter_regions` rejects it on **solidity 0.452 < 0.5**, with aspect 5.90
also close to the 6.0 limit.

**Why its solidity is low.** Not attached canalicular roots. An erosion
test distinguishes the two causes — thin attachments erode away fast while
the body survives, so solidity should jump at small radii:

| erosion r | area kept | solidity | pieces |
|---|---|---|---|
| 0 | 100% | 0.452 | 1 |
| 1 | 80% | **0.393** | 1 |
| 2 | 61% | 0.461 | 2 |
| 3 | 43% | 0.595 | 5 |

Solidity *falls* at r=1 and only recovers at r=3 having lost 57% of the
area. So the low solidity is the object's own shape: it is a long, thin,
**curved** body (aspect 5.90), and a banana shape has low solidity by
geometry, convex hull versus body, regardless of attachments. It is not
two fused lacunae either — it stays a single piece through r=1.

Visually (`results/diagnostics/phase3/542_z06_lacuna_230_300.png`, panels:
raw | v2 mask | the object | object vs its convex hull) it reads as a
lacuna sectioned obliquely, so the section cuts a long thin slice through
it rather than a compact cross-section.

**Options.**
1. Leave `TEST_MIN_SOLIDITY=0.5`. The kept population bottoms out at
   solidity 0.525 and only two rejected objects across all 8 WT images sit
   in [0.35, 0.5) — (226,310) at 0.452 and (543,492) at 0.456 — so the
   cutoff currently sits in a real gap, not in the middle of a
   distribution. Lowering it to ~0.44 would admit both.
2. Change nothing in v2 and use v3 instead: **v3 already recovers this
   object, at solidity 0.952, without anyone touching the filter.** The
   broad opening resolves the thin curved body into a compact one, so it
   passes v2's unchanged solidity test. See D4.

**My recommendation: option 2.** It needs no change to an accepted module,
and the mechanism is the right one — the object was never un-lacuna-like,
it was thin and curved, and a detector that measures breadth sees it
correctly. But note this hinges on whether an obliquely sectioned lacuna
should be counted at all, which is D4's question and your supervisor's
call.

---

## D4. v3-candidate lacuna detection: adopt, and on what terms?

**Status: NOTHING CHANGED. `LACUNA_SOURCE = "v2"` is the default; v3 is
reachable only via `--lacuna-source v3_candidate`.**

`src/segment_lacunae_v3_candidate.py` detects lacunae by BREADTH (a
morphological opening of the raw channel, radius 12 px) instead of
BRIGHTNESS. Everything after detection is v2's own watershed, merge and
filters, imported unchanged, so this compares detectors and nothing else.

| image | v2 | v3 | shared | v2-only | v3-only |
|---|---|---|---|---|---|
| 542_z06 | 16 | 21 | 16 | 0 | 5 |
| 542_z18 | 12 | 20 | 12 | 0 | 8 |
| 543-2 | 12 | 28 | 12 | 0 | 16 |
| 543_3 | 10 | 39 | 10 | 0 | 29 |
| 543_z13 | 11 | 19 | 11 | 0 | 8 |
| 682_z08 | 10 | 27 | 9 | 1 | 18 |
| 682_z23 | 14 | 36 | 11 | 3 | 26 |
| 682_z29 | 13 | 24 | 13 | 0 | 12 |

v3 finds essentially everything v2 finds (4 v2-only objects in total, all
in 682_z08/682_z23) and adds 5–29 per image. Every differing object is
listed with its position, area, solidity and mean intensity in
`reports/overnight/phase3_report.txt`.

**The extras split cleanly by brightness**, and this is the key fact:

| population | n | area p50 | solidity p50 | **mean intensity p50** |
|---|---|---|---|---|
| v2-kept (accepted) | 98 | 2132 | 0.886 | **0.827** |
| v3-only (added) | 122 | 878 | 0.952 | **0.378** |

The added objects are less than half as bright. Within them there are two
visibly different groups — in 542_z06, (230,303) and (224,351) come in at
mean_I 0.736, close to real lacunae, while (527,289) at 7832 px² and
(535,570) sit at 0.45 **on the vascular canal band at x≈530-580**. So v3 at
r=12 is detecting the canal as lacunae, which is a real false-positive
mode, not a borderline call.

**My recommendation: do NOT adopt v3 as the default yet.** It solves the
(230,300) problem cleanly, but it currently buys that by admitting the
vascular canal and a large dim population whose status is exactly the open
scientific question. Two ways forward, both needing your judgement:
- If partially sectioned lacunae SHOULD count: v3 is the right detector,
  but it needs the Phase 1 exclusion turned on to keep the canal out — and
  that interacts with D2, because the canal is what exclusion was built
  for. This is the combination I would test next.
- If they should NOT count: stay on v2, and treat D3 as the narrow
  question of whether to admit two objects by lowering solidity to ~0.44.

**What I cannot decide for you:** whether a lacuna lying partly outside the
focal plane is a lacuna for counting purposes. It changes counts by 50-290%
per image, so it is the single largest open question in the pipeline, and
it is a question about what the thesis is measuring, not about code.

---

## D5. Which outcome should be the primary canaliculi measure?

**Status: NOTHING CHANGED. `COUNT_MODE="edge"` is still the default;
`"roots"` is available but not selected.**

Phase 4 ran every metric on all 8 WT images under BOTH the current default
and the Phase 2 recommended setting, to see which outcomes survive a change
of segmentation. Pooled over 8 images:

| metric | default | recommended | change |
|---|---|---|---|
| canalicular length density (px⁻¹) | 0.0347 | 0.0393 | **+13.3%** |
| junction density (px⁻²) | 0.0004 | 0.0005 | +44.5% |
| median component length (px) | 15.5 | 16.8 | **+8.1%** |
| skeleton components | 808.9 | 684.6 | −15.4% |
| **edge count / cell** | 26.6 | 47.3 | **+77.9%** |
| **ROOTS / cell** | 6.82 | 7.58 | **+11.2%** |

**The per-cell edge count nearly doubles when the segmentation changes,
while roots/cell moves by a ninth and length density by an eighth.** An
outcome that swings 78% on a choice nobody has validated cannot carry a
genotype comparison; the difference between two mouse lines would be buried
inside the uncertainty from a preprocessing switch.

Two further reasons not to lead with edge count:
- It is an OCY **network** parameter, not a per-cell count. A tree with T
  tips has ~2T−1 edges, so 26.6 edges/cell is not "26.6 canaliculi".
  Reporting it as canaliculi per cell would be wrong on its face.
- It is computed from the ~23% of skeleton length that is graph-connected
  to a lacuna, so it inherits all of the fragmentation problem.

**My recommendation, for your supervisor:**
1. **Primary outcome: canalicular length density (px⁻¹), per field.** Most
   stable across settings (+13.3%), uses the whole skeleton, and does not
   depend on the per-lacuna assignment at all.
2. **Secondary, per-cell: roots per lacuna.** 6.8–7.6 per cell, which is a
   plausible number a person could check by eye in ImageJ, and it moves
   only +11.2% across settings. This is the number to validate against
   Mahmoud's counts, because it is the number his counts actually measure.
3. **Report edge count as a network parameter** if at all, clearly labelled,
   never as "canaliculi per cell".

Junction density is listed above for completeness but moves +44.5% and
should not be a primary outcome.

**Still needs your supervisor, not me:** whether the primary outcome should
be per-field or per-lacuna is a question about what the thesis claims, not
about which number is most stable. I can only report that the per-field
ones are more robust.

---

## D6. `data/` — RESOLVED 2026-09-28, now committed

The overnight brief said "Commit everything: code, reports, results/ ...,
and data/." I committed everything except `data/`, and I want that visible
rather than buried.

**Why I stopped.** `data/` is 24 MB of unpublished confocal images of mouse
bone. `.gitignore` excludes it with the comment "input images (git-ignored,
**not redistributed**)", and the project's standing note is never to commit
`data/` or `code_key`. Pushing those images to GitHub publishes them: once
pushed they are in the remote history, and removing them later needs a
history rewrite, which the same brief forbids ("never force-push").

Tonight's instruction and the repo's standing rule point opposite ways, and
I could not ask which wins. Publishing unpublished research images is the
harder of the two to undo, so I took the reversible option.

**Everything else is committed and pushed**, including all of `results/`
(221 MB: overlays, crops, masks, skeletons, exclusion and comparison PNGs)
and `reports/overnight/`. No file exceeded 100 MB, so Git LFS was not
needed.

**RESOLUTION (2026-09-28).** You reaffirmed the instruction, so the 8 WT
`.tif` files are now tracked and pushed (commit `9cd6dcb`). Checked before
committing: no `code_key` anywhere under `data/`, and the largest file is
3.0 MB, so no Git LFS was needed. The `code_key` exclusion rules are
untouched and still cover any future key file, including one placed under
`data/`. The repo is now self-contained — every result in `results/` can be
regenerated from the repo alone.

Nothing here needs further action; kept for the record of why it took two
passes.

---

## D7. Round 2 Step 5: local normalization NOT built, because the premise does not hold

**Status: NOTHING ADDED. `PREPROCESS_MODE` has no `"tophat_localnorm"`, and
there is no `LOCAL_NORMALIZE` switch.**

Step 5 was conditional: *"a) First measure it... b) **If they do** [sit in
locally dim regions], add PREPROCESS option `tophat_localnorm`"*. I ran (a)
and the condition is not met, so I did not build (b).

**(a), measured over all 86 interior lacunae, 8 WT images.** For each, its
root count against the canaliculi-mask density and the raw signal in a 30 px
ring just outside its body, both normalised to that image:

| | n | local mask density (× image) | local raw signal (× image median) |
|---|---|---|---|
| < 3 roots | **1** | 0.392 | **1.080** |
| ≥ 3 roots | 85 | 0.779 | 1.287 |

- **Only 1 of 86 interior lacunae (1.2%) has fewer than 3 roots.** None has
  zero. The brief expected "some lacunae get 0 to 3 roots"; on this data
  that is one lacuna, in 543-2.
- **The one case is not in a dim region.** Its local raw signal is 1.080×
  the image median — normal brightness. What is low is the local *mask*
  density (0.392×). So the canaliculi are genuinely absent from the mask
  there despite ordinary local brightness.
- Correlation of roots with local mask density is +0.575; with local raw
  signal only **+0.169**. Roots track how much network is nearby, not how
  bright the neighbourhood is.

**Step 1 had already largely fixed this.** Under the pre-Step-1 default,
3 of 86 (3.5%) had <3 roots; under the new default, 1 of 86 (1.2%). Median
roots per interior lacuna is 7.0 either way. Adopting hysteresis + bridging
did the work that local normalization was meant to do.

**Why I did not build it anyway.** `tophat_localnorm` divides by a
large-scale local signal estimate so dim regions threshold like bright
ones. The one remaining case has *normal* local brightness, so that
transform would not touch it. Building it would add an unjustified
preprocessing option, a new sigma parameter with no provenance, and another
axis to the guard testing — to address 1.2% of lacunae by a mechanism the
measurement says is not the cause.

**My recommendation: leave it out.** Revisit if any of these change:
- the <3-roots fraction rises materially on Hyp or Hyp;Enpp1 fields, which
  are dimmer and have not been measured;
- the correlation of roots with local *raw signal* rises well above +0.169;
- you decide 1 lacuna in 86 is worth correcting anyway.

`src/measure_local_root_density.py` re-runs the measurement.

---

## D8. The hybrid intensity gate overrides strong connectivity evidence

**Status: NOTHING CHANGED. `LACUNA_SOURCE="v2"` is still the default and
the hybrid gates are unchanged. This is a correction to what I reported in
Step 3, plus a recommendation.**

In Step 3 I wrote that gate (a), relative intensity, "decided every
verdict" and that gate (c), the roots test, "never changed an outcome", and
treated that as benign. Examining 682_z29c1-3 shows it is not benign.

**The unoutlined dim elongated object at ~(860,730) in 682_z29c1-3:**

| gate | value | threshold | verdict |
|---|---|---|---|
| (a) relative intensity | **0.532** | ≥ 0.75 | **REJECT** |
| (b) flagged overlap | 0.000 | 0 | PASS |
| (c) roots attached | **7** | ≥ 4 | PASS |

**It has 7 canalicular roots. The median interior lacuna in that same
image has 5.** So an object with *more* canaliculi radiating from it than
the typical accepted lacuna in its own field is rejected purely for being
dim — which is precisely the failure mode gate (c) was designed to
prevent. Gate (a) is not a harmless first filter here; it is overriding the
evidence the brief called the key discriminator.

It is also missed three separate ways, which is worth seeing together:
- **v2 does find it**, but splits it into two pieces of 346 and 229 px²,
  both rejected on `area < TEST_MIN_AREA_PX2 = 400`. Their combined area,
  575 px², would pass.
- **`MERGE_ADJACENT_PAIRS` cannot rescue it** — that step only considers
  pairs of *kept* lacunae, and neither piece is kept.
- **v3 does find it cleanly**, as one object of 2756 px² at solidity 0.938,
  and hybrid then rejects it on brightness.

**Options.**
1. Leave as is. Costs this object and others like it in dim fields.
2. Let (c) override (a) when connectivity is clearly strong — e.g. accept
   if roots ≥ the image's median roots, regardless of intensity. On the WT
   data that would admit this object; how many others it admits has not
   been measured.
3. Lower `MIN_RELATIVE_INTENSITY`. Risky and blunt: the v2-kept/v3-only
   populations separate cleanly at 0.823/0.783, so lowering the cut to 0.53
   would admit most of the 122 dim v3-only objects, not just this one.

**My recommendation: option 2**, because it uses the discriminator that
actually distinguishes a lacuna from haze rather than the one that
correlates with it. But it needs measuring across all 8 images before
adoption, and it interacts with **D4** — whether partly-sectioned lacunae
count at all — so it should not be decided in isolation.

**Also note for D7.** The relative sparsity criterion (roots or ring
skeleton length below half the image median) flags **4 of 86** interior
lacunae, against **1 of 86** for the absolute "< 3 roots" rule. The two
sub-criteria are complementary: lacuna B at (761,905) in 682_z29 has 3
roots, which the roots test does NOT flag (3 > 0.5 × 5.0), but its ring
skeleton length of 97 px is well under half that image's median of 247, so
the ring test does. A relative criterion is the better instrument; it does
not change D7's conclusion that local normalization is the wrong fix, since
the flagged lacunae are still sparse in mask rather than dim in raw signal.

---

## D9. The D8 override is implemented — and I recommend AGAINST adopting it

**Status: implemented behind `LACUNA_SOURCE="hybrid"`, which is still NOT
the default. `LACUNA_SOURCE="v2"` unchanged. No default changed.**

This reverses the recommendation I made in D8. The size-bias check you
asked for did its job, and then the crops showed something the numbers did
not.

### The size bias was real, and it changes the motivating case

| measure | (860,730) in 682_z29 | that image's v2-kept median |
|---|---|---|
| raw roots | **7** | 5 |
| roots / 100 px perimeter | 3.11 | 2.80 |
| **CORE roots (size-corrected)** | **3** | **5** |

Its 2756 px² outline reaches 10 px further out than its 575 px² v2-scale
core, and that is where the extra 4 roots came from. **So the object that
motivated D8 FAILS the size-corrected criterion.** I have not fudged the
measure to rescue it.

The three measures disagree sharply on the 80 candidates that pass (b)+(c)
but fail (a): raw roots admits 42, roots/100px admits **79** (it
discriminates nothing, because candidates are *smaller* than v2 lacunae —
median body 1018 vs 2174 px² — so dividing by a smaller perimeter pushes
them over automatically), core roots admits 27.

### Cutoffs, all pinned to measured data

- **Roots measure:** CORE roots, recounted on a body shrunk to v2 scale
  (intersected with v2's pre-filter pieces where they exist, else eroded to
  the image's median v2 area). A no-op on the v2-kept population, so the
  two distributions stay comparable.
- **Threshold:** ≥ that image's median v2-kept core roots.
- **Intensity floor: 0.40.** Each image's raw background mode, expressed in
  relative-intensity units, runs min 0.096, mean 0.215, **max 0.333**.
  0.40 is 1.20× that worst case, so nothing at haze level can qualify
  anywhere in this dataset. It bites: two candidates at 0.336 and 0.338 —
  essentially at background — are removed, 27 → 20.

### Confirmations you asked for

| check | result |
|---|---|
| (230,300) in 542_z06 added | **YES** — via all three gates, rel_I 0.783. Unaffected by the override. |
| (860,730) in 682_z29 added | **NO** — core roots 3 < median 5 |
| nothing on a flagged structure | **CONFIRMED, 0 of 22** — gate (b) is required for the override too |

Total added: 22 (2 through all gates, **20 through the override**).

### Why I now recommend against it

I examined four of the twenty override additions. **Three are false
positives** — the outline sits on dense canalicular mesh with no lacuna
body in it at all:

- `543-2/added_x998_y149.png` — empty mesh at the frame edge; the real
  lacuna in that crop is elsewhere and already found by v2
- `682_z23c-2/added_x676_y137.png` — empty mesh, no body
- `682_z29c1-3/added_x177_y524.png` — a thread crossing, the nearest bright
  blob sits outside the outline
- `543_3/added_x42_y337.png` — a **real** lacuna, but with a badly inflated
  outline covering far more than the bright body

**The mechanism.** "Roots" counts threads passing within
`LACUNA_ATTACH_GAP_PX` of the body, not threads *emanating from* it. A
lacuna is a hub where threads terminate; a point in dense mesh is where
threads pass through. Both score high. The size correction fixes the
*outline* inflation but not this, because eroding a blob that sits in mesh
leaves a smaller blob still sitting in mesh.

**Recommendation: do not adopt.** Keep `LACUNA_SOURCE="v2"`. Adding 20
objects of which a majority look like mesh would inflate lacuna counts in
exactly the dense fields where the genotype comparison matters most.

**If you want to pursue it**, the missing test is whether threads *end* at
the object rather than pass by — e.g. requiring that a majority of
attaching branches have a degree-1 endpoint inside or adjacent to the body,
rather than continuing through. That is new method design, not a cutoff
change, and I have not built it.
