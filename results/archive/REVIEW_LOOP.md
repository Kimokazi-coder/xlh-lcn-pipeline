# The review loop: lacuna detection on the development images

**Pre-validation.** The judge of this loop is an AI image reviewer (a Claude
Code subagent on Sonnet, `.claude/agents/image-reviewer.md`), not a person and
not a manual count. Its counts say what it saw in the pictures; they are not
validated, and they move a little from one look to the next.

Brief of 2026-11-05. The 27 development images of all four groups (WT 6,
WT_HP 7, Hyp_RD 7, Hyp_HP 7); the 8 held-out images (docs/HOLDOUT.md) are
never run, shown or reviewed here. Each round: one general rule in
`src/lacunae.py` (set in `config.py`, physical units at 0.13 um/px, no image
named), against the most frequent problem; rerun lacunae, canaliculi,
quantification and 3_pols on the development images; the reviewer on all 27;
the counts before and after. Stop when a round does not lower the total, or
when WT gets worse (then the change is reverted). At most 5 rounds.

## How the reviewer works and how it is counted

- 8 reviewers per round, 2 per group, each given 3 or 4 images; for each image
  it opens `1_lacunae/<label>_lacunae_outlines.png` and
  `3_pols/<label>_pols_lacunar_size.png` and returns one row per problem.
  Their tables are kept verbatim in `review_loop/round<N>/`.
- Counting (`python src/diagnostics.py review-tally review_loop/round<N>`):
  a fragment, band or tissue piece or other row counts once per id it lists
  (each id is one wrong object); a split or merged row counts once (one lacuna
  drawn wrongly); a missed row counts once.
- In this session the agent definition could not be loaded as its own agent
  type (Claude Code reads agent definitions at session start), so each
  reviewer ran as a general-purpose agent on Sonnet given that definition's
  instructions, told to use only Read, Glob and Grep. The tool limit held by
  instruction, not by the harness.

## Round 0, the baseline (the method of 0b0be38)

Pictures as committed before this loop. `review_loop/round0/tally.csv`:

| group | images | lacunae labelled | fragment | band or tissue piece | split | merged | missed | other | total |
| - | - | - | - | - | - | - | - | - | - |
| WT | 6 | 82 | 8 | 2 | 1 | 0 | 0 | 1 | 12 |
| WT_HP | 7 | 97 | 12 | 11 | 2 | 0 | 6 | 2 | 33 |
| Hyp_RD | 7 | 210 | 75 | 28 | 5 | 0 | 1 | 1 | 110 |
| Hyp_HP | 7 | 207 | 58 | 29 | 9 | 2 | 0 | 5 | 103 |
| all | 27 | 596 | 153 | 70 | 17 | 2 | 7 | 9 | 258 |

Most frequent: fragment (153 of 258).

## Round 1: the rescue rules off (config.LACUNA_RESCUE_RULES = False)

**Problem attacked:** fragment (153 of 258).

**What the round 0 pictures showed.** Every object of the 27 images was
measured (area, width as the diameter of the largest inscribed disk, shape,
brightness) and joined to the reviewer's verdict. The four rescue rules that
add lacunae below the 6.76 um2 (400 px) area floor, out of focus (f), dim
(g1), frame (g2) and thick process (g3), admitted 55 objects: 53 called
fragments, 2 accepted (both small pieces cut by the frame, in WT). All but one
are 2.5 to 6.5 um2 and 1.1 to 2.5 um wide; the accepted lacunae are 36.8 um2
and 4.2 um wide at the median. Ordinary objects, by contrast, overlap: no
area or width floor on them separates fragments from accepted lacunae without
losing many of the latter (a width floor of 2.0 um alone would drop 14
accepted lacunae, 3 in WT).

**Rule.** `config.LACUNA_RESCUE_RULES = False` (section g5): the four rescue
rules no longer add objects, so every lacuna clears the same area, solidity
and aspect rules. True restores them exactly.

**Also in this round, changing no number:** `-w` (parallel images) and
`--fast` (the bounding-box watershed of config.FAST_LACUNA_STAGE, for that
run only) on `src/lacunae.py` and `src/canaliculi.py`; the dark-band merge
works in a window around each pair (identical labels; `diagnostics.py
dark-band-check`). The loop rounds run with `--fast`; Phase 5 runs the
default path.

**Counts, round 0 to round 1** (`review_loop/round1/tally.csv`):

| group | lacunae labelled | fragment | band or tissue piece | split | merged | missed | other | total |
| - | - | - | - | - | - | - | - | - |
| WT | 82 to 75 | 8 to 2 | 2 to 2 | 1 to 1 | 0 to 0 | 0 to 1 | 1 to 2 | **12 to 8** |
| WT_HP | 97 to 93 | 12 to 9 | 11 to 14 | 2 to 1 | 0 to 0 | 6 to 5 | 2 to 2 | **33 to 31** |
| Hyp_RD | 210 to 189 | 75 to 45 | 28 to 26 | 5 to 5 | 0 to 1 | 1 to 1 | 1 to 1 | **110 to 79** |
| Hyp_HP | 207 to 185 | 58 to 65 | 29 to 32 | 9 to 5 | 2 to 0 | 0 to 0 | 5 to 5 | **103 to 107** |
| all | 596 to 542 | 153 to 121 | 70 to 74 | 17 to 12 | 2 to 1 | 7 to 7 | 9 to 10 | **258 to 225** |

**WT:** better, 12 to 8. The 8 objects removed are the WT rescue objects
(542_z06 3, 542_z18 1, 543_3 2, 682_z08 1, 682_z29 1). One new "missed" in
542_z06 (an elongated body at about 230,300) may be the thick-process object
the round 0 reviewer had called a fragment; the reviewer is not fully
consistent between looks.

**Hyp_HP** rose by 4 although it lost 22 objects: the reviewer flagged more of
the ordinary objects it had passed in round 0 (701_z26c1-2: 22 to 32). Read
the counts as accurate to a few problems per group.

**Kept.** Total down 33, WT not worse.

## Round 2: the fragment rule (config.FRAGMENT_RULE, section g6)

**Problem attacked:** fragment (121 of 225).

**What the round 1 pictures showed.** The remaining fragments were ordinary
objects: crumbs of glow or thread with their own id right beside a lacuna,
and specks. A small object touching or nearly touching a much larger lacuna
was a problem 28 times and accepted 0 times; small objects that are also
thin were mostly fragments.

**Rule.** A kept object is dropped as a fragment when it is a SATELLITE (at
most 17 um2, within 1 um of a kept lacuna at least twice its area) or a SPECK
(at most 8 um2 and at most 2.0 um wide). Judged on the whole labelled region.
The satellite is dropped, not joined, so its neighbour's area is not inflated
by glow. Predicted on the round 1 pictures: 44 problems and 1 accepted object
dropped; the run dropped 45 objects (WT 3, WT_HP 5, Hyp_RD 19, Hyp_HP 18).

**Counts, round 1 to round 2** (`review_loop/round2/tally.csv`):

| group | lacunae labelled | fragment | band or tissue piece | split | merged | missed | other | total |
| - | - | - | - | - | - | - | - | - |
| WT | 75 to 71 | 2 to 2 | 2 to 1 | 1 to 0 | 0 to 0 | 1 to 1 | 2 to 2 | **8 to 6** |
| WT_HP | 93 to 88 | 9 to 3 | 14 to 13 | 1 to 1 | 0 to 0 | 5 to 3 | 2 to 1 | **31 to 21** |
| Hyp_RD | 189 to 170 | 45 to 33 | 26 to 24 | 5 to 7 | 1 to 1 | 1 to 1 | 1 to 0 | **79 to 66** |
| Hyp_HP | 185 to 167 | 65 to 47 | 32 to 36 | 5 to 6 | 0 to 0 | 0 to 0 | 5 to 4 | **107 to 93** |
| all | 542 to 496 | 121 to 85 | 74 to 74 | 12 to 14 | 1 to 1 | 7 to 5 | 10 to 7 | **225 to 186** |

**WT:** better, 8 to 6. The three objects dropped are the band sliver of
542_z06, a thread sliver of 682_z29 and the smaller piece of the split
lacuna of 682_z29 (its split is gone; the remaining piece was not flagged).
Regression on the 6 development WT images: PASS, both runs.

**Kept.** Total down 39, WT not worse.

## Round 3: a third arm of the fragment rule, the crumb (section g7)

**Problem attacked:** fragment (85 of 186).

**What the round 2 pictures showed.** The remaining fragments overlap with
small accepted lacunae in size and width: most cuts on those cost 2 to 4
accepted WT lacunae. A search over two- and three-feature rules (requiring no
accepted WT lacuna lost) found one clean one: small and ragged.

**Rule.** A CRUMB, at most 10 um2 and with solidity under 0.80, is dropped as
a fragment. Predicted: 22 fragments, 1 band piece and 1 accepted object (a
WT_HP object of 8.4 um2 at solidity 0.78); no WT object. The run dropped 24
objects (WT 0, WT_HP 1, Hyp_RD 13, Hyp_HP 10).

**Counts, round 2 to round 3** (`review_loop/round3/tally.csv`):

| group | lacunae labelled | fragment | band or tissue piece | split | merged | missed | other | total |
| - | - | - | - | - | - | - | - | - |
| WT | 71 to 71 | 2 to 4 | 1 to 1 | 0 to 0 | 0 to 0 | 1 to 3 | 2 to 2 | **6 to 10** |
| WT_HP | 88 to 87 | 3 to 4 | 13 to 12 | 1 to 1 | 0 to 0 | 3 to 4 | 1 to 3 | **21 to 24** |
| Hyp_RD | 170 to 157 | 33 to 23 | 24 to 25 | 7 to 5 | 1 to 1 | 1 to 1 | 0 to 5 | **66 to 60** |
| Hyp_HP | 167 to 157 | 47 to 30 | 36 to 35 | 6 to 10 | 0 to 0 | 0 to 0 | 4 to 0 | **93 to 75** |
| all | 496 to 472 | 85 to 61 | 74 to 73 | 14 to 16 | 1 to 1 | 5 to 8 | 7 to 10 | **186 to 169** |

**WT: unchanged by this round, and the reviewer's count rose anyway.** The
rule dropped no WT object, and every WT picture and table the reviewer reads
(the 6 outlines pictures, the 6 3_pols pictures and their tables) is byte
for byte the one of round 2; only the provenance fields of the jsons changed.
The count went from 6 to 10 because the reviewer, looking at the same
pictures, now called two dim bodies of 543_3 missed and two unchanged small
objects fragments. So the change did not make WT worse and is kept. This
measures the reviewer's noise: about plus or minus 4 problems on 6 identical
WT images. From this round on, "WT worse" is judged object by object: a round
makes WT worse only if it removes or changes WT objects the reviewer had
accepted.

**Kept.** Total down 17; WT not changed.

## Round 4: the band rule (config.BAND_BLOB_RULE, section g8)

**Problem attacked:** band or tissue piece (73 of 169).

**What the round 3 pictures showed.** A saturated band, the bone surface or
soft tissue is one large bright region of the lacuna mask, and the watershed
cuts it into lacuna-sized pieces. Measured on the mask the pipeline uses (the
cut after its hole fill and opening), every object lying in a region larger
than 300 um2 was a band or tissue piece (17 of 17); the largest accepted
lacuna is 200.9 um2 and is its own region. At 250 um2 the rule would also
drop a 32.8 um2 lacuna fused in the mask to a band.

**Rule.** A kept object is dropped when its region of the lacuna mask is
larger than 300 um2. Predicted: 17 band pieces, no accepted object, no WT
object. The run dropped 17 (WT 0, WT_HP 2, Hyp_RD 7, Hyp_HP 8). **Caution:**
this acts as a largest lacuna profile of 300 um2, about 8 times the WT median;
a real lacuna larger than that, or fused in the mask to a band, is dropped
too. In a POL study that is the side to watch.

**Counts, round 3 to round 4** (`review_loop/round4/tally.csv`):

| group | lacunae labelled | fragment | band or tissue piece | split | merged | missed | other | total |
| - | - | - | - | - | - | - | - | - |
| WT | 71 to 71 | 4 to 5 | 1 to 1 | 0 to 0 | 0 to 0 | 3 to 1 | 2 to 1 | **10 to 8** |
| WT_HP | 87 to 85 | 4 to 5 | 12 to 11 | 1 to 1 | 0 to 0 | 4 to 5 | 3 to 2 | **24 to 24** |
| Hyp_RD | 157 to 150 | 23 to 26 | 25 to 15 | 5 to 5 | 1 to 1 | 1 to 1 | 5 to 3 | **60 to 51** |
| Hyp_HP | 157 to 149 | 30 to 36 | 35 to 22 | 10 to 6 | 0 to 1 | 0 to 0 | 0 to 5 | **75 to 70** |
| all | 472 to 455 | 61 to 72 | 73 to 49 | 16 to 12 | 1 to 2 | 8 to 7 | 10 to 11 | **169 to 153** |

**WT:** unchanged by this round again (no WT object dropped, pictures
identical); the reviewer's count moved 10 to 8 on the same pictures. The
fragment count rose 61 to 72 though no fragment-like object was added: the
reviewer moved objects between categories and flagged objects it had passed.
Its noise is now about the size of one rule's effect.

**Also checked:** `diagnostics.py dark-band-check --watershed` on all 27
development images: the fast watershed and the windowed dark-band merge give
identical labels on 27 of 27 (the merge took up to 2646 s per image on the
full frame, about 1 s in the window).

**Kept.** Total down 16; WT not changed.
