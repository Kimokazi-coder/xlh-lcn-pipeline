# Decisions and open questions

Branch `canal-physical-v2`, from `canal-physical-ablation`, with the fixed
comparison workbook cherry-picked from `canal-physical`. Not merged.
**Pixel size 0.13 um/px, rounded, unconfirmed per image.** Pre-validation: no
number here has been checked against a manual count.

A diagnosis and a better founded experiment. **No variant is called better than
another**, nothing was tuned to improve a result, and nothing was tuned to
approach a published value.

## Open questions for you

### 1. The optics are unknown, so the width cannot be turned into a diameter

The objective's **numerical aperture**, the **emission wavelength** and the
**pinhole diameter** are not recorded anywhere in this repository. Without them
no point spread function can be computed, so:

- no theoretical resolution limit is calculated here;
- nothing is deconvolved and no blur is subtracted;
- the width reported is the **apparent width in the image**, which includes the
  blur, and is therefore an **upper bound** on the true canalicular diameter.

If you can get those three numbers from the acquisition record, the measured
width can be compared with what the optics allow, and only then would a statement
about the true diameter be possible.

### 2. Does 0.13 um/px hold for every image?

It is rounded and unconfirmed per image. Every micrometre number on this branch
scales linearly with it, and the areal density with its square. The comparison
between variants does not depend on it at all, because every variant uses the
same value. One image, `542 WT  2_z18c1-2.tif`... see the earlier branch: the one
TIFF resolution tag in the dataset (on 542_z06) says 300 DPI, which is 84.67
um/px, a generic placeholder and not a calibration.

### 3. P3 never found a peak inside the range it was given

The rule is to take the scale with the largest scale-normalised response between
0.10 and 0.35 um. On **all 8 images** the response rises all the way to the top
of that range and never turns over, so P3 chose 0.334 um (2.57 px) everywhere:
the chosen value is the edge of the search, not a maximum.

What that means: the strongest ridges in the flattened image are broader than
0.35 um. It is reported as it stands. The range was fixed in the brief and was
**not** widened to manufacture an interior peak, because widening it until a
maximum appears would be choosing the answer.

The response of `skimage.filters.sato` is already scale normalised. This was
checked rather than assumed: on synthetic Gaussian ridges the raw response peaks
at about 0.6 times the full width at half maximum and tracks the width (1.2 px
for a 2 px ridge, 1.8 px for 3 px, 3.6 px for 6 px), while multiplying by the
scale squared a second time makes the largest candidate win whatever the
structure (4.4 px in all three cases). The first implementation did multiply
again, which made P3 meaningless; that is why the check exists.

### 4. The top-hat radius is wider than a thread, and was left alone

The flattening uses a white top-hat of radius 5 px, which is **0.65 um** at this
pixel size, and a Gaussian of 0.8 px (0.104 um). A top-hat whose structuring
element is wider than the structure it is meant to isolate passes that structure
through broadened, so the flattening may itself contribute to how fat the masks
are. It is **unchanged here**, because the brief changes one idea at a time and
this experiment is about the scale of the ridge filter. It is a candidate for the
next experiment, not a defect fixed quietly.

### 5. The notch filter changes almost nothing

Variant N runs: `experiments/task1_artefact.py` imports and its `notch` is called
unchanged. It removes periods of **2 px (0.26 um)** and **4 px (0.52 um)** along
x, constant along y, each with a Gaussian notch one bin wide.

Its results are the same as P2 to four decimal places on nearly every measure.
Whatever is producing the rectilinear structure, it is not the two stripe
frequencies this filter removes.

### 6. The output exceeds the size budget as specified

The figures your brief asks for come to about **83 MB**, against the 60 MB
budget; every individual file is well inside the 3 MB limit, the largest being
1.68 MB. The overage is in the full size pictures. See README.md for the exact
per-file sizes and the options for trimming.

## Assumptions I made

- **One idea changes at a time.** The flattening, the lacuna buffer, the vascular
  handling, the bridging rule, the graph cleanup, the ownership and the ring radii
  are the current method's own code in every variant.
- **Variant A is the pipeline itself**, not a copy: it calls
  `canaliculi.analyse_network`. It is checked twice over, against
  `results/<label>/5_quantification/` at tolerance 0 and by its pipeline style
  verification image being pixel identical to the committed one, on all 8 images.
- **The width is measured on the image, not on the mask.** A distance transform
  can only return the width of the mask it is given, so it cannot reveal a mask
  that is too fat. Both are reported side by side.
- **The width code was checked against synthetic lines before use**: Gaussian
  profiles of FWHM 2, 3 and 5 px, at 0 and 30 degrees, recovered within 0.13 px,
  and a one pixel line blurred by a Gaussian recovered within 0.13 px of the width
  that blur implies. The tolerance the brief sets is 0.3 px.
- **The noise estimate had to be changed for a clipped background.** The
  flattening subtracts the histogram mode and clips at zero, so on these images
  **54.9%** of background pixels are exactly 0 and both the median and the median
  absolute deviation of the background are 0: the textbook robust estimate returns
  no noise at all and every contrast becomes undefined. What survives the clipping
  is the positive half of the noise, and for a symmetric distribution clipped at
  its centre the median of the positive half is 0.6745 standard deviations, which
  recovers it. On 542_z18 that gives 0.0195 against a background standard
  deviation of 0.0178, so the two agree.
- **The same contrast definition is used for every variant including A.** The
  earlier support measure used the current method's own threshold and so favoured
  the current method; it is kept only as `legacy_unsupported_fraction` so the
  earlier tables can still be followed.
- **A skeleton pixel is drawn as one whole pixel of the original image.** Drawing
  only the centre of each upscaled block was tried first: at eight times it puts
  one dot per eight pixels and a thread reads as a faint dotted line that vanishes
  at any normal viewing size. Filling the block is the thread at its true width
  and is not the thickening the pipeline's verification picture does, which
  dilates into neighbouring pixels and makes a one pixel thread five wide.
- **The figures use an indexed png with the skeleton colours in reserved palette
  slots.** A plain 256 colour quantisation was measured first and moved all 14
  overlay colours, which would have made the colours meaningless. With the slots
  reserved every skeleton colour is exact and only the background is quantised, by
  a mean of about 1 level in 255.
- **The zoom tiles are the ones the first comparison chose**, read from its json
  and not chosen again.
- **The trace tiles carry no overlay of any kind**, and the scoring is not built,
  so a trace cannot be tuned against while it is being made. Two of the four tiles
  are slid back inside the frame because their centre is near an edge, and
  `tiles.csv` says which.
- **Determinism.** No step makes a random choice; timestamps are suppressed in
  every figure and the workbook is rewritten with fixed dates.

## What this folder does not claim

It does not claim any variant is better. It reports what each change did.
`git switch canal-physical-ablation` leaves this branch behind with no trace.
