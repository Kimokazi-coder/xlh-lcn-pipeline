# manual_trace

Four raw 200 by 200 px tiles (26.0 um at 0.13 um/px), one each from 542_z18, 682_z08, 543-2 and
543_z13, chosen where the current and ridge skeletons disagreed most and least. No mask, skeleton
or result is drawn on them, so a trace made here cannot be steered by what a method found.
I trace them blind in ImageJ to build the manual ground truth the methods are scored against.
Full protocol, tile coordinates and provenance: `tiles_README.md` and `tiles.csv`.

## What to put here for the scorer

`python src/validate_manual.py` reads this folder and scores the pipeline against the tracing.
It runs happily with nothing here and prints `no manual masks yet`, so it can sit in a check
sequence from today. Two files per image, both optional and scored independently:

| file | what it is |
|---|---|
| `<label>_manual.png` | a binary mask the size of the whole image, 1024 by 1024, white (above 127) wherever a canaliculus runs, black everywhere else. One pixel wide is ideal but not required: the scorer compares with a tolerance |
| `<label>_manual_lacunae.csv` | a header line `x,y` then one row per hand-marked lacuna centre, in pixels, x across and y down, origin at the top left |

`<label>` is the short image name the pipeline uses: `542_z06`, `542_z18`, `543-2`, `543_3`,
`543_z13`, `682_z08`, `682_z23`, `682_z29`. So a full set for one image is
`543_3_manual.png` and `543_3_manual_lacunae.csv`.

An RGB png is fine, it is reduced to one channel. A mask whose size does not match the image is
an error rather than a silent rescale.

## What it reports

```
python src/validate_manual.py                        # every image that has a tracing
python src/validate_manual.py -i data/WT/543_3.tif   # one image
python src/validate_manual.py -o results/validation  # and write the json
```

- **skeleton precision**: the share of the pipeline's skeleton lying within 2 px of some
  hand-traced pixel, that is, how much of what it drew is really there.
- **skeleton recall**: the share of the hand tracing lying within 2 px of some pipeline pixel,
  that is, how much of what is there it drew.
- **f1**: their harmonic mean.
- **lacunae matched, missed and extra**: a hand-marked point matches the lacuna whose body
  contains it, or failing that the nearest lacuna within 25 px. Each detected lacuna can be
  claimed once, so two points on one body leave one of them missed rather than both matched.

The 2 px tolerance is 0.26 um. A hand line and a skeleton of the same thread never agree pixel
for pixel, and a thread is about 6 px wide, so 2 px compares the same structure without letting
the next thread over count as a match.

## The tiles above are not the whole-image masks

The four tiles are 200 by 200 px crops, for building confidence and a first score by hand. The
scorer above wants a mask the size of the whole image. Tracing one whole image is the real gate;
the tiles are the way in.
