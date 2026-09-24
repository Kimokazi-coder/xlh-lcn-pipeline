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
