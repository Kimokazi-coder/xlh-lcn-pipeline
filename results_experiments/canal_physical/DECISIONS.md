# Decisions and open questions

Branch `canal-physical`, created from `quant-split`, not merged, nothing on it
required by `main`. **Pixel size 0.13 um/px, rounded, unconfirmed per image.**
Pre-validation: no number on this branch has been checked against a manual count.

Everything below is either an assumption I had to make or a point the brief did
not decide. Nothing here was guessed silently.

## Open questions for you

### 1. `PIXEL_SIZE_UM` is a separate constant, not the pipeline's own

The brief asks for `PIXEL_SIZE_UM = 0.13` in `config.py`, and also that
`python src/diagnostics.py regression` pass at tolerance 0 while `results/` and
`src/diagnostics.py` stay untouched. Those cannot all hold at once:

- `pixel_size_um` is recorded in the parameters block of every result, by
  `lacunae.parameters()` and `canaliculi.parameters()`. It reaches
  `parameters.lacunae.pixel_size_um` and `parameters.canaliculi.pixel_size_um` in
  each `<label>_quantification.json`, and the regression compares those fields at
  tolerance 0 against `results/`, where they are `null`. Setting the global would
  fail the regression on all 8 images.
- `figures/make_figures.py` switches every scale bar from pixels to micrometres
  when it is set, so the committed figures would no longer match a fresh run.

So `config.py` gained `PIXEL_SIZE_UM_CANAL_PHYSICAL = 0.13` and `PIXEL_SIZE_UM`
stays `None`. The experiment reads the new constant, the pipeline's recorded
output and figures are unchanged, and the regression still passes (verified after
the edit: 2 runs, 5170 numbers each, 0 differ). The brief's own wording, "keep the
existing None behavior reachable", points the same way.

**If you want the global flipped instead, say so**: the regression will then fail
on those two recorded fields per image until `results/` is regenerated, which this
brief forbids.

### 2. Adding any constant to `config.py` changes the recorded config hash

`lacunae.config_hash()` covers every upper-case setting, so the hash moved from
`be57b3fa7ae5d298` to `dc534babadca48a8`. The hash lives in the provenance block,
which the regression ignores, and `results/` is not regenerated on this branch, so
the committed files keep the `quant-split` hash. Nothing fails; the two differ on
purpose and this is the record of why.

### 3. Is 0.13 um/px the same for every image?

The brief says it is rounded and must be confirmed per image. Every micrometre
number here moves linearly with it and the areal density moves with its square, so
a 5% error in the pixel size is a 5% error in every length and 10% in the areal
density. The comparison between the two methods does not depend on it at all,
because both use the same value.

### 4. One TIFF resolution tag disagrees with 0.13 um/px

`542 WT  2_z06c1-2.tif` carries XResolution and YResolution of 300 per inch, which
is 84.67 um/px: 650 times the value in use, and it would make the 1024 px frame
8.7 cm wide. It is the generic 300 DPI placeholder that `docs/METHODS.md` already
records, not a microscope calibration. The other seven images carry no resolution
tag at all. The brief says to stop and report a tag that disagrees, so it is
reported here and in the run output, and the tag is treated as absent.

### 5. The lacuna labels come from running the lacuna stage, not from a file

The brief says to reuse the labels and not to re-segment. `src/lacunae.py` on this
branch does save a label image, but only into `results/`, and this experiment may
not write there and should not depend on a folder being up to date. So the labels
come from calling `lacunae.analyse_image`, the same code with the same parameters,
which gives the same labels. No new segmentation was written. Say the word if you
would rather they be read from `results/<label>/1_lacunae/`.

### 6. Which ridge filter

I started with Sato tubeness, the simpler of the two Hessian filters, to change
one idea at a time. Frangi is available in the same scikit-image version. The
tuning log records what was tried; tell me if you want Frangi compared too.

### 7. Areal density is not the literature's construction

The published 0.5 to 0.9 canaliculi per um^2 counts canaliculi crossing a cut
face. I report the skeleton length density in um per um^2, the closest quantity
this pipeline produces, and label it as a different construction. If you have the
exact definition from the source, I will match it.

## Assumptions I made

- **One idea changes.** The flattening, the lacuna buffer, the vascular handling,
  the bridging rule with its angle and signal tests, the graph cleanup, the
  ownership and the ring radii are the current method's own code, imported and
  called unchanged. The single difference is the quantity that is thresholded: a
  multiscale ridge response instead of the flattened intensity.
- **Both methods are measured by `src/quantification.py`**, the same function with
  the same code, so a difference in a number is a difference in the skeleton and
  never in the measuring. `metrics.py` only builds the input dict, converts to
  micrometres, and adds the three network-shape measures the comparison asks for
  that the pipeline does not report (thread-end fraction, share of skeleton length
  connected to a lacuna, median edge length).
- **Every length is stated in micrometres and converts back to the current
  method's pixel value** at 0.13 um/px: bridge 1.3 um = 10 px, spur 0.52 um =
  4 px, crossing 0.78 um = 6 px, attach 1.3 um = 10 px, root merge 1.04 um = 8 px,
  rings 3.9 and 7.8 um = 30 and 60 px, vascular major axis 54.6 um = 420 px,
  lacuna buffer 0.26 um = 2 px, speck 0.1352 um^2 = 8 px^2.
  `skeleton.check_parameters_match_current` asserts all 12 against the constants
  in `src/canaliculi.py`, so the imported functions and this package cannot
  disagree quietly. A tuned value that no longer matches needs its own code path.
- **The cuts still come from the image.** The high cut is the lower of the ridge
  response's own three-class multi-Otsu cuts, the rule the current method applies
  to intensity. The low cut is 0.75 of it, carried over. No literature value is
  used as a threshold anywhere, and nothing in `plausibility.py` feeds a parameter.
- **The ridge scales follow a measurement, not a target.** The canalicular half
  width measured for the top-hat radius is p50 3.0 px and p99 4.2 px
  (`docs/METHODS.md` section 2), so the chosen scales span that range with one
  step between them. Four other candidate sets were run on the tuning set and are
  in `tuning_log.csv`.
- **Tuning discipline.** Candidates were run on 542_z06, 543-2 and 682_z29 only.
  The other five images were not used to choose anything.
- **The zoom crops are chosen by rule, not by eye**: tiles of 13 um ranked by the
  absolute difference in skeleton pixel count between the two methods, taken in
  order without overlap, ties broken by position. The rule is recorded with the
  figures and the boxes are drawn on the full image.
- **Determinism.** No step makes a random choice. The one seeded thing in the
  project, the per-lacuna overlay colours, uses `config.RANDOM_SEED`, unchanged.
  The run is executed twice and the outputs compared.

## What this branch does not claim

It does not claim the new method is better. The comparison table and the zoom
crops are there to be judged. `git switch quant-split` leaves this branch behind
with no trace.
