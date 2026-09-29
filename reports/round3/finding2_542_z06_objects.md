# Finding 2: two kept objects in 542_z06

2026-09-29. **Pre-validation, pixel units.** Read-only diagnostic; no default
or pipeline output changed. Numbers: `finding2_542_z06_objects.txt` (same
folder). Crops: `results/diagnostics/round3/finding2/` (raw | outlines, target
cyan, flagged band tinted blue | default skeleton). Full per-lacuna table:
`results/diagnostics/round3/finding2/kept_population.json`. Re-run with
`src/inspect_kept_lacunae.py`.

Population: all 98 kept v2 lacunae over the 8 WT images. Roots are counted
on the current default canaliculi graph, the way `COUNT_MODE="roots"` counts
them.

## Summary

| | id 2 at (555,149) | id 3 at (106,67) | population median |
|---|---|---|---|
| area px² | **445 (1st of 98)** | 556 (9th) | 2132 |
| solidity | 0.767 (18th) | **0.527 (2nd)** | 0.886 |
| aspect ratio | 4.94 (96th) | 1.73 (10th) | 2.81 |
| relative intensity | 0.864 (10th) | 0.954 (24th) | 1.000 |
| thickness px | **10.2 (1st)** | 17.2 (9th) | 32.4 |
| area kept after r=5 opening | **0.207 (1st)** | 0.701 (5th) | 0.967 |
| roots | 4 (9th) | 5 (20th) | 7 |
| distance to flagged band px | **0 (inside it)** | 410 | 302 |

Ranks count from the bottom. "Area kept after r=5 opening" is the fraction
of the object that survives an opening with `TOPHAT_RADIUS_PX`, the disk
(11 px across) that the canaliculi top-hat uses to define "broader than any
canaliculus".

## id 2 at (555,149): most likely a piece of the vascular band, not a lacuna

- It lies entirely inside the flagged vascular band (distance 0).
- It is the thinnest kept object in the dataset: 10.2 px, against a measured
  canaliculus width of at most about 8 px. Every other kept lacuna is at
  least 12.8 px thick, and the p10 is 18 px.
- 79% of it disappears under the canaliculus-width opening. No other kept
  object loses more than 65%.
- In the raw crop there is no separate compact body at that position, only a
  bright stretch of the band wall.

It passes v2 only because each measure sits just inside its limit: area 445
against 400, aspect 4.94 against 6.0.

**Consequences if it is a false positive.** It adds 1 to the 542_z06 lacuna
count (16). It acts as a cell in the canaliculi graph, owning threads
through its 4 roots. And it is lacuna-scale, so the exclusion safety margin
protects a 50 px disk of the band around it. That last point was not
measured here.

**A second object has the same signature**: 682_z23 id 2 at (363,7). It is
inside a flagged band (distance 0), 12.8 px thick, keeps 0.348 after the
opening, and touches the image border. I have not looked at it by eye.

## id 3 at (106,67): a real lacuna with a leaked outline, not a loop

- In the raw crop there is a compact, bright body at the top of the outline,
  and relative intensity 0.954 is ordinary for a lacuna.
- The outline continues down and to the left into the thick start of the
  canalicular loop. That tail is the "hook". The loop itself is not in the
  mask, and the object encloses no hole.
- The tail is what gives it the second-lowest solidity in the dataset
  (0.527). The r=5 opening keeps 70% of the area, i.e. it removes a
  thread-width appendage of about 30%.
- Its 5 roots are close to the median (7), as expected for a real cell.

**Consequences.** Counting it is correct. Its shape measures are biased:
area is inflated by roughly 30%, and solidity and eccentricity describe the
body plus the tail.

## Options (none built, no default changed)

1. **id 2 type, thread-scale objects.** Reject a kept object whose
   area-kept-after-opening is below about 0.5. On this data that cuts
   exactly the two band objects: the kept values run 0.207, 0.348, then
   0.681 and up. The threshold rests on 2 objects, so it would go behind a
   switch, default off.
2. **id 3 type, leaked outlines.** Measure lacuna shape on the opened body
   (r=5) instead of the raw mask, as an additional column rather than a
   replacement, so the effect on the area distribution can be seen first.
3. Leave both as they are and record them as known cases.
