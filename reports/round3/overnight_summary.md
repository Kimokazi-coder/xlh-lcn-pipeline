# Overnight summary, 2026-09-29: canaliculi ownership

Branch `presentation-prep`, branched from `canaliculi-v2-fixes` at 964fdd4.
**Not pushed, not merged.** Everything is pre-validation and in pixel units.
Step by step detail: `overnight_log.md`.

## In one paragraph

Unbounded ownership is real and large: owned threads end a median 105 px
from their cell but reach up to 864 px, and 46 of 98 cells own threads more
than 200 px away. A reach cap now exists as a switch, **off by default**.
By your rule its value is **275 px**. But that rule keeps 90% of owned
length by construction, so it only trims the far tail. It does not make
owned length local. **The measures that fix the problem are the
ownership-free ones:** roots per cell, ring length at 30 and 60 px, and
field length density. None of them moved at any cap tested, including
100 px. The presentation table uses only those. Owned length and edge
count stay in the files, labelled, and should not be presented as per-cell
results.

## The cap value and its rule

**Rule (yours):** the smallest cap that leaves at least 90% of owned
skeleton length owned, pooled over the 8 images, rounded to a multiple of
25 px.

**Numbers:**
- The exact point is **265.1 px**, the length-weighted 90th percentile of
  the distance at which a cell reaches each thread it owns.
- Rounding up gives **275 px**, which keeps 90.8%. Rounding to the nearest
  multiple gives the same value.
- Retained at other caps: 100 px keeps 61.8%, 200 px 83.3%, 250 px 88.6%,
  300 px 92.0%, 400 px 95.5%.

**How the cap works:**
- A thread stays owned if its cell reaches it within the cap, and it is
  kept whole.
- Nothing is reassigned: a thread beyond the cap for its nearest cell is
  beyond it for every cell.
- The cyan cell in 682_z29 is id 8 at (182,716). It owns 1252 px of
  skeleton, with a reach of 378 px.

Report: `step1_reach.md`.

## Sensitivity (Step 4)

Pooled over 86 interior cells of the 8 WT images. The per-field density is
the mean of the 8 images.

| cap px | roots per cell | ring r30 per cell px | ring r60 per cell px | owned length per cell px | edge count per cell | field density px⁻¹ |
|---|---|---|---|---|---|---|
| no cap | 7.50 | 319.81 | 904.74 | 1296.59 | 45.41 | 0.03910 |
| 100 | 7.50 | 319.81 | 904.74 | 788.73 (−39.2%) | 26.53 (−41.6%) | 0.03910 |
| 225 | 7.50 | 319.81 | 904.74 | 1110.35 (−14.4%) | 38.53 | 0.03910 |
| 250 | 7.50 | 319.81 | 904.74 | 1143.79 (−11.8%) | 39.72 | 0.03910 |
| **275** | 7.50 | 319.81 | 904.74 | 1173.57 (−9.5%) | 40.73 | 0.03910 |
| 300 | 7.50 | 319.81 | 904.74 | 1189.94 (−8.2%) | 41.36 | 0.03910 |
| 325 | 7.50 | 319.81 | 904.74 | 1208.09 (−6.8%) | 42.00 | 0.03910 |

**Stable:** roots, both ring lengths and field density, which are 0.0% at
every cap. **Swinging:** owned length and edge count, which move 7.5% of
their uncapped value across 225 to 325 px and about 40% at 100 px.

Report: `step4_sensitivity.md`.

## What changed

- **No default changed.** Every switch has its old value. `REACH_CAP_PX` is
  a new switch set to `None` (off), and `SHOW_UNOWNED_GREY` a new cosmetic
  switch set to `False` (off).
- **Output format of `canaliculi_v1` measurements** (the only change a
  default run sees):
  - four new columns per lacuna and in the summary: `roots_count`,
    `ring_length_r30_px`, `ring_length_r60_px`, `owned_length_px`
  - one new JSON parameter, `reach_cap_px` (null when off)
  - no existing column changes value
- **New CLI flags:** `--reach-cap [PX]` and `--no-reach-cap`.
- **New scripts:**
  - `diagnostics/canaliculi/measure_reach.py` (Step 1)
  - `diagnostics/canaliculi/reach_sensitivity.py` (Step 4)
  - `src/make_presentation.py` (Step 5)
- **New outputs:**
  - `results/presentation/`: 8 image folders, `summary_table.xlsx`,
    `summary_table.csv`, `PIPELINE_NOTE.md`
  - `results/diagnostics/round3/reach/`
  - 543-2 comparison runs in `results/canaliculi/543-2/all_method_results/`
    (`_cap275`, `_nocap`, `_count-roots`)

## What did not change

- `results/canaliculi/<image>/` default outputs are untouched. They were
  restored after every 543-2 check. **Note:** they therefore do not yet
  carry the four new columns. They gain them the next time the defaults are
  regenerated, which is planned together with the staleness fingerprints.
- `data/` was not touched and nothing was deleted.
- The 543-2 reference: default and `--no-reach-cap` both read 62.33 / 27.41
  / 21 bridges after every code change. With `--reach-cap` it reads 56.58 /
  27.27 / 21.

## Decisions waiting for you

1. **Push and merge.**
   - On `canaliculi-v2-fixes`: the moves-only commit eafcdd3 and the
     comment-only commit 964fdd4 are not pushed.
   - `presentation-prep` is local only.
2. **Is the 275 px cap worth adopting at all?** By your rule it trims only
   10% of owned length and leaves owned length non-local. My
   recommendation: keep the cap off by default, present only the
   ownership-free measures, and treat owned length as a network descriptor.
   A tighter cap (for example 100 px, which trims 39%) would need its own
   justification. The Step 1 data does not suggest a natural break.
3. **Ring radii 30 and 60 px.**
   - 30 comes from earlier work.
   - 60 is my choice (about two thirds of the median lacuna length).
   - Whether either should be tied to lacuna size instead is open.
4. **Regenerate the default outputs** so they carry the new columns. Due
   with the staleness check (approved, to be built after findings 1 and 5).
5. **Remaining findings.**
   - Finding 1 (543_3 split) and finding 5 (block-growth difference
     overlay) are still to do.
   - Finding 4 (reach) is covered by Steps 1 to 4 here. Confirm you
     consider it done.
6. **`diagnostics/tools/tidy_canaliculi_results.py` is out of date.** It
   would move the default `bridges.png` files if run. Fix or retire?
7. **For Dr. Murshed:**
   - D4 (partly sectioned lacunae)
   - the two band objects
   - whether per-field or per-cell measures are the primary outcome (D5)
8. **One caveat on the "about a third owned" figure.** Owned length sums
   graph edge lengths (diagonal steps count 1.41), while field skeleton
   length counts pixels (diagonal steps count 1). The fraction is
   approximate, not exact.
