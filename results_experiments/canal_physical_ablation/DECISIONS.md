# Decisions and open questions, canalicular ablation

Branch `canal-physical-ablation`, from `canal-physical`, not merged. **Pixel size
0.13 um/px, rounded, unconfirmed per image.** Pre-validation: no number here has
been checked against a manual count.

This is a diagnosis. No variant is called better than another, and nothing was
tuned to improve any result. Everything below is either an assumption I had to
make or a point the brief did not decide.

## Open questions for you

### 1. The committed workbook on branch `canal-physical` is corrupt

`results_experiments/canal_physical/comparison_all_images.xlsx` cannot be opened:
`openpyxl` and Excel both reject it. The reproducibility rewrite I added in that
task lost its regular expression group reference, so it replaced the whole
opening tag of `docProps/core.xml` instead of only the timestamp inside it, and
the file is not well formed XML. The determinism check did not catch it because
both runs produced the same malformed bytes.

The bug is fixed in `src/canal_physical/run.py` on this branch, with a check that
the workbook opens as well as being byte identical across runs. The broken file
itself is on `canal-physical`, which this brief forbids me to touch, so it is
left alone. Its `.csv` and `.pdf` are sound and hold the same numbers. **Tell me
if you want me to go back to that branch and regenerate it.**

### 2. `rectangle_count` finds almost nothing, and that is a real result

Across 8 images it is 0 for the current method and 0.2 per image for the ridge
method as defined: an independent four-node loop of the cleaned graph whose four
sides are axis-aligned. Both the measure and its opposite were checked on
synthetic shapes first, so the zero is not a broken measure: a synthetic
axis-aligned rectangle is counted and a skewed one is not.

What the figures show is not closed rectangles but **open right-angle corners and
long straight runs**, which `straight_run_fraction` does count. If you want the
corners counted as well, say so and I will add a corner measure; I did not add
one because the variant and measure list was fixed in advance.

### 3. How much of the straight running is in the images themselves

`experiments/task1_artefact.py` on an earlier branch already recorded
axis-aligned skeleton runs and banding in these images, 682_z08 in particular.
This ablation shows the ridge filter raises the axis-aligned share, but it does
not separate how much of the underlying banding is in the acquisition. Comparing
against the notch-filtered variant from that experiment would answer it, and is
outside this brief.

### 4. The variants are a fixed list, so there is no held-out confirmation

The brief states the list is the entire search, so no tuning set and no held-out
set applies. That also means none of these settings has been confirmed on data
that did not choose it, because none of them was chosen by data at all.

### 5. The output is large

About 144 MB in total, mostly the 56 full-size verification images (7 variants
times 8 images, about 1.5 MB each) that section 4 asks for. Every individual file
is well under the 5 MB limit; the largest is 1.8 MB. Say the word if you want the
per-variant verification images pruned to A and C only, which would cut it to
about 50 MB.

## Assumptions I made

- **Bridging is turned off by assembling the stage from the pipeline's own lower
  level pieces**, never by editing a pipeline function: `build_lacuna_maps`,
  `flagged_structures`, `preprocess_channel`, `network_candidate_mask`,
  `skeletonize`, and then `nearest_lacuna_map` and `build_ownership`, with
  `find_bridges` and `apply_bridges` simply not called. Variant A does not use
  that path at all: it calls `canaliculi.analyse_network`, so the reference is the
  pipeline itself and not a copy of it.
- **Variant A is checked twice over**: its measures must equal
  `results/<label>/5_quantification/` at tolerance 0, and its verification image
  must be pixel identical to the committed one. Both pass on all 8 images, which
  is what makes the other six comparable.
- **The artifact cut is the image's own**, taken once per image from the
  flattened intensity with `canaliculi.total_signal_mask`, and every variant of
  that image is judged against that same cut. Using each variant's own cut would
  have made the variants incomparable.
- **`unsupported` means not above the cut**, the exact complement of the rule the
  current method uses to call a pixel signal (`img > t_lo`), so a pixel is never
  counted as supported by one rule and unsupported by the other.
- **The verification images are drawn by the pipeline's own function.**
  `canaliculi.save_verification` and `canaliculi.lacuna_colors` are imported and
  called; nothing is reimplemented. The lacunae are identical in every variant, so
  a cell keeps its colour across all seven.
- **The zoom tiles are the ones the earlier run chose**, read from
  `results_experiments/canal_physical/<label>/<label>_canal_physical.json` and not
  chosen again, so the two folders show the same places.
- **The verification style hides most of the skeleton.** It draws owned skeleton
  only, and it hides more of the current method's skeleton than of the ridge
  method's, because only about a third of the current method's length is connected
  to a lacuna against about seven tenths of the ridge method's. The panels named
  `_variants_` draw the whole skeleton, which is the fair view of what each
  variant traced. This is stated in README.md as the brief asks.
- **Determinism.** No step makes a random choice. Timestamps are suppressed in
  every png and pdf, and the workbook is rewritten with fixed dates, so two runs
  give identical bytes.

## What this folder does not claim

It does not claim any variant is better. It reports what each switch changed.
`git switch canal-physical` leaves this branch behind with no trace, and nothing
on `main`, `quant-split` or `canal-physical` depends on it.
