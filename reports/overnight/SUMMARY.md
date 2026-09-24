# Overnight run, 2026-09-24 — summary

Branch `canaliculi-v2-fixes`, pushed. **No default switch value was
changed.** The 543-2 default check (37.00 canaliculi/cell, 29.43 px mean
edge length) was re-run after every phase and held every time.

Everything below is v1-raw / v2-raw / v3-raw, **pre-validation**, in PIXEL
units. Nothing here has been checked against Mahmoud's ImageJ counts.

---

## 1. Completed / skipped

**Completed:** Phase 2 (ridge, hysteresis, gap bridging — 8 settings × 8
images), Phase 3 (solidity investigation + v3 candidate detector), Phase 4
(per-field metrics, roots count mode, sanity report), documentation
(README + module docstrings), and a separate README correction commit
first, as asked.

**Not done, deliberately:** `data/` was not committed — see
DECISIONS_NEEDED.md **D6**. It is 24 MB of unpublished confocal images that
`.gitignore` marks "not redistributed", and pushing them is hard to undo
while force-pushing was forbidden. Everything else is pushed, including all
221 MB of `results/`. No file exceeded 100 MB, so Git LFS was not needed.
No push failed.

**Two bugs found and fixed rather than shipped:**
- Phase 3's v2↔v3 matching scored overlap against the v3 object, which
  systematically encloses the v2 one. It reported 14–39 false
  disagreements per image until corrected to score against the smaller
  object (now 5–29 real ones).
- `save_xlsx` has a `for field, unit in SUMMARY_METRICS` loop that silently
  shadowed the new `field` parameter with a string. Renamed.

---

## 2. Phase 2 — current default vs candidates

Guards were fixed **in writing before running** (DECISIONS_NEEDED.md D0):
**G1** length > 1.20× default; **G2** loops > max(1.5× default, +50).

### Tuning set (542_z06, 543-2, 682_z29)

| setting | length | loops | comp/10k | deg1_f | owned_f | bridges | guards |
|---|---|---|---|---|---|---|---|
| default | 1.00× | 1.00× | 225.3 | 0.825 | 0.244 | 0 | ok |
| hysteresis (0.5) | 1.30× | 6.53× | 102.2 | 0.664 | 0.581 | 0 | **G1+G2** |
| **hyst-0.75** | 1.13× | 2.11× | 174.0 | 0.767 | 0.337 | 0 | ok |
| ridge | 1.19× | 8.42× | 64.2 | 0.592 | 0.773 | 0 | **G2** |
| ridge+hyst | 1.57× | 39.79× | 11.2 | 0.398 | 0.976 | 0 | **G1+G2** |
| **default+bridge** | 1.02× | 1.03× | 188.0 | 0.798 | 0.291 | 122 | ok |
| ridge+bridge | 1.21× | 8.92× | 46.3 | 0.560 | 0.837 | 79 | **G1+G2** |
| **hyst0.75+bridge** | 1.13× | 2.13× | 169.1 | 0.763 | 0.343 | 18 | ok |

### Held-out set (the other five WT images), no re-tuning

| setting | length | loops | comp/10k | deg1_f | owned_f | bridges | guards |
|---|---|---|---|---|---|---|---|
| default | 1.00× | 1.00× | 235.1 | 0.820 | 0.224 | 0 | ok |
| hysteresis (0.5) | 1.31× | 5.93× | 104.0 | 0.660 | 0.547 | 0 | **G1+G2** |
| **hyst-0.75** | 1.13× | 2.17× | 179.9 | 0.762 | 0.329 | 0 | ok |
| ridge | 1.19× | 7.26× | 63.8 | 0.589 | 0.792 | 0 | **G2** |
| ridge+hyst | 1.59× | 36.28× | 9.8 | 0.384 | 0.972 | 0 | **G1+G2** |
| **default+bridge** | 1.02× | 1.08× | 195.1 | 0.793 | 0.261 | 131 | ok |
| ridge+bridge | 1.20× | 7.75× | 45.7 | 0.556 | 0.854 | 80 | **G2** |
| **hyst0.75+bridge** | 1.13× | 2.17× | 174.7 | 0.759 | 0.337 | 19 | ok |

**The guards earned their keep.** `ridge+hyst` wins every secondary
readout — owned fraction 0.976, 11.2 components per 10k — and is the worst
setting tried: loops go 13 → 504, and the longest skeleton component goes
708 → 36,051 px in 542_z06 and 1,213 → 55,831 px in 682_z23. That is the
field fusing into single objects, exactly what Phase 0(c) predicted when it
found only 21% of endpoint-to-neighbour angles are under 20°. Judging on
owned fraction alone would have selected it.

**Recommended (not applied): `hyst0.75+bridge`.** Best fragmentation gain
among passing settings, inside both guards on tuning *and* held-out, and
bridging adds only 18 bridges on top of hysteresis against 122 on the
default — two independent mechanisms converging on the same gaps.
Conservative alternative: `default+bridge`.

---

## 3. Phase 3 — the (230,300) lacuna, and v2 vs v3

**Why it is rejected: not brightness.** It is in v2's mask (area 1698 px²,
mean intensity 0.901 vs t_hi 0.647) and fails `solidity 0.452 < 0.5`. An
erosion test rules out attached canalicular roots — solidity *falls* to
0.393 at r=1 and only reaches 0.595 at r=3 having lost 57% of the area. It
is a long, thin, **curved** body (aspect 5.90); a banana shape has low
solidity from geometry alone. Not two fused lacunae either.

Across all 8 WT images only **2** rejected objects sit in solidity
[0.35, 0.5), and the kept population bottoms out at 0.525 — so the 0.5
cutoff currently sits in a real gap. `TEST_MIN_SOLIDITY` was not touched.

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

v3 **recovers the (230,300) object at solidity 0.952**, with v2's filter
unchanged — the broad opening resolves a thin curved body into a compact
one. But v3's extras are half as bright as accepted lacunae (mean intensity
p50 **0.378 vs 0.827**), and in 542_z06 two of five sit on the vascular
canal band at x≈530–580. **v3 detects the canal as lacunae.** Not adopted.

---

## 4. Phase 4 — which outcomes survive a change of segmentation

Pooled over all 8 WT images, current default vs the Phase 2 recommendation:

| metric | default | recommended | change |
|---|---|---|---|
| canalicular length density (px⁻¹) | 0.0347 | 0.0393 | **+13.3%** |
| median component length (px) | 15.5 | 16.8 | **+8.1%** |
| **roots / cell** | 6.82 | 7.58 | **+11.2%** |
| skeleton components | 808.9 | 684.6 | −15.4% |
| junction density (px⁻²) | 0.0004 | 0.0005 | +44.5% |
| **edge count / cell** | 26.6 | 47.3 | **+77.9%** |

**The per-cell edge count nearly doubles on an unvalidated preprocessing
choice; roots/cell and length density move by about a tenth.** An outcome
that swings 78% cannot carry a genotype comparison — the difference between
two mouse lines would sit inside the uncertainty from a switch.

Note also that roots/cell lands at 6.8–7.6, a number a person could check
by eye, whereas edge count is an OCY *network* parameter (a tree with T tips
has ~2T−1 edges) and is not "canaliculi per cell".

---

## 5. Recommended default changes — **none applied**

| # | change | one-line reason |
|---|---|---|
| 1 | `THRESHOLD_MODE="hysteresis"`, `HYSTERESIS_LOW_FRACTION=0.75`, `GAP_BRIDGING=True` | Best fragmentation gain inside both pre-declared guards, on tuning and held-out. |
| 2 | Primary outcome → canalicular length density (per field) | Most stable across settings (+13.3%) and free of the per-lacuna assignment. |
| 3 | Per-cell outcome → `COUNT_MODE="roots"` | +11.2% vs edge's +77.9%, and it is what Mahmoud's ImageJ counts actually measure. |
| 4 | Keep `EXCLUSION_MODE="none"` | Flagged structures don't clearly inflate the mask; no passing Phase 2 setting changes that. |
| 5 | Keep `LACUNA_SOURCE="v2"` | v3 fixes the (230,300) case but admits the vascular canal and a dim population. |
| 6 | Leave `TEST_MIN_SOLIDITY=0.5` | The cutoff sits in a real gap; v3 is the cleaner route to the same object. |

---

## 6. Images to look at, in order

1. `results/diagnostics/phase2/542_WT__2_z06c1-2/crop_dense_ridge+hyst.png`
   — what a failing setting looks like: threads fused into sheets.
   Compare with `crop_dense_default.png` and `crop_dense_hyst0.75+bridge.png`
   in the same folder.
2. `results/diagnostics/phase3/542_z06_lacuna_230_300.png` — the rejected
   lacuna (raw | v2 mask | the object | object vs convex hull). The
   curvature driving solidity 0.452 is visible in panel 4.
3. `results/count_v3_candidate/542_WT__2_z06c1-2/v2_vs_v3.png` — green =
   both, cyan = v3-only, red = v2-only. Note the cyan blobs on the vertical
   canal band.
4. `results/count_v3_candidate/543_3/v2_vs_v3.png` — the worst
   over-detection case, 29 v3-only objects.
5. `results/canaliculi/542_WT__2_z06c1-2/all_method_results/bridges_p4-recommended-edge.png`
   — every gap bridge drawn in green, for eye-checking.
6. `results/canaliculi/682_z29c1-3/all_method_results/exclusion_excl-auto.png`
   — Phase 1 exclusion working well (cyan), carved around protected lacunae.

Text reports: `reports/overnight/phase2_report.txt`,
`phase3_report.txt`, `phase3_v2_vs_v3.txt`, `phase4_report.txt`.

---

## 7. Decisions waiting on you

**`DECISIONS_NEEDED.md`** — six entries, each with evidence, options, my
recommendation, and what I actually did (in every case: the safe option,
no default changed, nothing deleted).

- **D0** Phase 2 guard thresholds, recorded before running
- **D1** which Phase 2 setting, if any, becomes default
- **D2** whether Phase 2 changes the exclusion default
- **D3** the (230,300) solidity rejection
- **D4** whether to adopt the v3 lacuna detector
- **D5** which outcome should be primary
- **D6** `data/` deliberately not committed

The largest open question is in **D4**: whether a lacuna lying partly
outside the focal plane counts. It changes lacuna counts by 50–290% per
image and is a question about what the thesis measures, not about code.
