# Fix log: the method is not changed

**Pre-validation.** Decisions of the audit of 2026-11-06 on the frozen method
(tag `method-freeze-v1`). No rule was changed, so no new tag was made and the
final rerun of phase 4 was not needed.

## The band rule (300 um2 cap)

Not biased by the brief's test: of the 17 objects it removes from the
development images, 0 are real lacunae, 15 band or tissue, 2 unsure
([`CAP_AUDIT.md`](CAP_AUDIT.md)). Unchanged.

## The rescue rules off

Biased by the brief's test: real lacunae lost are 5.6% in WT and 0.0% in
Hyp_HP, a spread of 5.6 points over a limit of 5 ([`DIM_AUDIT.md`](DIM_AUDIT.md)).
The fix the brief asks for is a rescue rule "narrow enough that the Phase 2
real lacunae return without bringing back the fragments of loop round 1".
**No such rule was found, so none was added.** Over the 57 rescued objects
the band rule would keep, every rule of one to three bounds on brightness,
contrast, background, shape, glow footprint and distance to the nearest
lacuna (`diagnostics.py dim-rule-search`, [`dim_rule_search.csv`](dim_rule_search.csv))
either misses most real lacunae or returns fragments with them:

- with no non-lacuna back, at most 3 of the 11 real lacunae come back, by a
  rule of three thresholds chosen on these very objects;
- 10 of 11 come back only with 8 non-lacunae.

Adding the 3-of-11 rule would bring the spread under 5 points, but only
because its thresholds were chosen on the objects the test counts, so the test
would no longer say anything. Adding a rule that returns most real lacunae
brings back the fragments loop round 1 removed. Either breaks a condition of
the brief, so the method stays as frozen and the choice goes to you.

## What you can choose

1. Keep the method (rescue off), and report the dim loss: 11 real lacunae
   among 455 detected on the development images (2.4%), more in WT and Hyp_RD
   than in Hyp_HP.
2. Turn the rescue rules back on (`config.LACUNA_RESCUE_RULES = True`): all
   11 return, with 30 non-lacunae, the state of loop round 0.
3. Accept a rule from the trade-off table, for example "over background at
   least 2.0, at least 3 um from the nearest lacuna, mean at least 160 of 255":
   10 of 11 back, 8 non-lacunae back.
4. Have the 60 crops in `dim_added/` judged by a person: the bias rests on 4
   WT objects judged once by an AI reviewer, and 16 are unsure.

## Counts before and after

No change, so the counts of loop round 4 stand for the development images
(`../REVIEW_LOOP.md`): 153 problems, WT 8, WT_HP 24, Hyp_RD 51, Hyp_HP 70.
