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
