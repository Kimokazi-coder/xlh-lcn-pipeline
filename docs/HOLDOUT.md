# The held-out validation set

**Status: pre-validation.** Locked on 2026-11-05, git tag
`holdout-locked-2026-11-05`. The record is [`data/holdout.json`](../data/holdout.json).

## What it is

Eight images, two per group, are kept for the final validation only. They are
not used to choose, tune or check any rule while the method is developed: they
are not processed, not displayed and not opened, and neither are their outputs.

| group | image file | label |
| - | - | - |
| WT | `543-2.tif` | 543-2 |
| WT | `682_z23c-2.tif` | 682_z23 |
| WT_HP | `876_z82c1-2.tif` | 876_z82c1-2 |
| WT_HP | `877 wt_z081c1-2.tif` | 877_wt_z081c1-2 |
| Hyp_RD | `535_z20c1-2.tif` | 535_z20c1-2 |
| Hyp_RD | `I534_z19c1-2.tif` | I534_z19c1-2 |
| Hyp_HP | `701_z19c1-2.tif` | 701_z19c1-2 |
| Hyp_HP | `701_z36c1-2.tif` | 701_z36c1-2 |

How they were drawn: for each group, `random.Random("20261105:<group>")` drew 2
of the sorted file names in `data/<group>/` (Python 3.9.10). Only the file
names were read; no image was opened to choose. The draw was made once and not
repeated or adjusted.

## How the pipeline keeps them out

`config.HOLDOUT_MODE` is `DEV` (the default) or `FINAL`. It is read from the
environment variable `LCN_HOLDOUT_MODE`, so the final run needs no edit:

    LCN_HOLDOUT_MODE=FINAL python src/lacunae.py -d data/WT

In DEV mode:
- `lacunae.load_channel`, which every stage uses to read an image, refuses a
  held-out image with `HeldOutImageError`;
- a folder run of any stage skips the held-out images and prints how many it
  skipped; naming one with `-i` is refused;
- contact sheets and group tables leave them out, so a group table made in DEV
  mode covers the development images only.

In FINAL mode every image is processed. FINAL is for the one run after the
method is frozen (tag `method-freeze-v1`).

## What a reader should know

- **Sections, not animals.** Every held-out section comes from an animal that
  also has sections in the development set (543, 682, 876, 877, 535, I534,
  701), and the sections of one stack lie a few micrometres apart, so some cells
  may appear in both. The held-out set tests the method on unseen fields, not
  on unseen animals. An animal-level hold-out would need more animals per group.
- The draw fell on `543-2`, the image of `python src/diagnostics.py
  reference-check` and the default image of two self-tests; in DEV mode those
  commands refuse it. Both Hyp_HP images come from animal 701.
- The outputs already in `results/` for the held-out images were made before
  the lock. During development they are left as they are, and the FINAL run
  replaces them.
