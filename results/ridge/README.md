# The canalicular experiment on the physical scale

**pixel size 0.13 um/px, confirmed for all 8 images.** Pre-validation: no number here has been checked against a
manual count. **No variant is called better than another**, and nothing was tuned to improve
any result or to approach any published value.

## Why this exists

At 0.13 um/px a canaliculus of 0.2 to 0.4 um is about 1.5 to 3 px across, and about
2.5 to 4 px once the optics have blurred it. The masks of the current method have a median
distance transform width of 6.0 px (0.78 um) and the first ridge variants 7.4 px, so both are
roughly twice that. The scales of those first variants came from a half width measured on the
already inflated mask, which is circular: the mask set the scale and the scale set the mask.

Here every scale is set in micrometres from the pixel size, and the width is measured on the
image rather than on the mask.

## Variants

Fixed before the first run, all reported, none chosen afterwards. The lacunae, the vascular
handling, the graph cleanup, the ownership and the ring radii are the current method's in every
one, so only the named difference can move a number.

**P5 is listed first because it is the preferred variant by eye. That is a visual preference,
not a validated result.** No variant is called better than another by any number below.

| variant | what | sigmas (um) | sigmas (px) | low cut | bridging |
|---|---|---|---|---|---|
| P5 | ridge, sigmas 0.17, 0.21, 0.26 um, gap bridging off | 0.17, 0.21, 0.26 | 1.308, 1.615, 2.0 | 0.75 | no |
| A | current method, as is | | | 0.75 | yes |
| P2 | ridge, sigmas 0.17, 0.21, 0.26 um, gap bridging on | 0.17, 0.21, 0.26 | 1.308, 1.615, 2.0 | 0.75 | yes |

P5 and P2 carry the same scales and the same cut: they differ by the bridging switch and
nothing else, so the difference between their numbers is the effect of bridging alone.
The response of `skimage.filters.sato` is already scale normalised, which was checked on
synthetic ridges rather than assumed: the raw response peaks at about 0.6 times the full width
at half maximum and follows the width, while multiplying by the scale squared a second time
makes the largest candidate win whatever the structure.

## The new measures

- **`width_fwhm_*`**: the width measured **on the image**. At every usable skeleton pixel the
  flattened intensity is sampled along the normal to the thread, and the width is the full width
  at half maximum of that profile. Bridged pixels, pixels off the mask, the lacuna buffer, the
  vascular mask and junction pixels are left out. **It includes the optical blur**, so it is an
  apparent width in the image and an **upper bound on the diameter**, not the diameter. No point
  spread function is computed or subtracted anywhere: the numerical aperture, the emission
  wavelength and the pinhole are unknown.
- **`width_dt_*`**: the older measure, twice the distance transform of the mask, reported beside
  it. It can only ever return the width of the mask it is given.
- **`contrast_snr` and `low_contrast_fraction`**: the intensity at a skeleton pixel minus the
  median intensity 4 to 6 px away along the normal on both sides, divided by the noise, where the
  noise is 1.4826 times the median absolute deviation of the flattened image over pixels outside
  the lacunae, the vascular regions and **that variant's own mask**. The same definition is used
  for every variant including A, which the earlier support measure was not: that one used the
  current method's own threshold and so favoured the current method. It is kept as
  `legacy_unsupported_fraction` only so the earlier tables can still be followed.
- **`straight_run_fraction`** is unchanged, and **`straight_run_fraction_smoothed`** is the same
  after each branch path is smoothed with a 5 point moving average, which removes most of the
  effect of drawing a thin line on a pixel grid. A one pixel skeleton contains straight runs by
  its nature and the current method already scores about 0.22, so only the differences between
  variants carry meaning.
- Everything else is measured by `src/quantification.py`, the same code for every variant.

## Figures

The skeleton is drawn **one pixel wide**, never thickened, on an image upscaled by nearest
neighbour so a one pixel line stays visible. Owned threads take their lacuna's colour, the
pipeline's own colours; everything the ownership did not reach is light grey, so **nothing is
hidden**. This is the opposite of the pipeline's verification style, which thickens the skeleton
and draws only what is owned.

| file | what |
|---|---|
| `comparison_all_images.csv` and `.xlsx` | the comparison table: every measure, every image, every variant, with the summary of means and the notes |
| `comparison_summary.csv` | the means over the images and the change from A |
| `<label>/<label>_compare.png` | P5, then A, then P2 side by side, 2x |

The comparison is written as an indexed png with the skeleton colours
held in reserved palette slots, so **every skeleton colour is exact** and only the background is
quantised. A plain quantisation was measured first and moved all 14 overlay colours, which would
have made the colours meaningless. The background error is a mean of about 1 level out of 255.

## How it was run

```
python src/canal_physical/physical.py --dir data/WT
```

Commit `f9c64381ec332f1d1ce983d4057ff713205758df`, tracked files clean: False. Config hash `4026503a93d224d7`.

## Every length, in micrometres and pixels

| parameter | um | px | what |
|---|---|---|---|
| `pixel_size_um` | 0.13 |  | um per pixel, acquisition record |
| `sigma_um` | [0.39, 0.468, 0.546] | [3.0, 3.6, 4.2] | ridge scales |
| `hysteresis_low_fraction` | 0.75 |  | share of the high cut |
| `lacuna_buffer_um` | 0.26 | 2 | buffer around a lacuna |
| `min_object_area_um2` | 0.1352 | 8 | smallest mask fragment, area |
| `max_bridge_gap_um` | 1.3 | 10.0 | longest gap bridged |
| `direction_walk_um` | 0.65 | 5 | walk back for the thread direction |
| `max_bridge_angle_deg` | 40.0 |  | degrees |
| `min_bridge_signal_fraction` | 0.7 |  | share of the cut |
| `prune_spur_um` | 0.52 | 4.0 | shortest kept spur |
| `min_internal_edge_um` | 0.78 | 6.0 | shortest kept internal edge |
| `lacuna_attach_gap_um` | 1.3 | 10.0 | attach distance |
| `root_merge_um` | 1.04 | 8.0 | root cluster distance |
| `ring_radii_um` | [3.9, 7.8] | [30.0, 60.0] | ring radii |
| `broad_opening_um` | 1.04 | 8 | opening that finds broad structures |
| `vascular_dilation_um` | 0.52 | 4 | dilation of the flagged region |
| `vascular_min_span_fraction` | 0.45 |  | share of the frame |
| `vascular_min_major_axis_um` | 54.6 | 420.0 | smallest flagged major axis |
| `width_percentiles` | [10, 90] |  | percentiles reported |
| `random_seed` | 0 |  | no random choice is made |
| `tophat_radius` (flattening) | 0.65 | 5 | unchanged from the current method |
| `smooth_sigma` (flattening) | 0.104 | 0.8 | unchanged from the current method |

## Mean over the images

| measure | P5 | A | P2 |
|---|---|---|---|
| `width_fwhm_median_um` | 0.6351 | 0.6368 | 0.6352 |
| `width_dt_median_um` | 0.6006 | 0.7853 | 0.6006 |
| `low_contrast_fraction` | 0.04019 | 0.02063 | 0.04053 |
| `contrast_snr_median` | 7.882 | 9.955 | 7.877 |
| `straight_run_fraction` | 0.2365 | 0.221 | 0.2375 |
| `straight_run_fraction_smoothed` | 0.1931 | 0.1872 | 0.194 |
| `rectangle_count` | 0 | 0 | 0 |
| `connected_to_lacuna_fraction` | 0.4557 | 0.336 | 0.48 |
| `junction_count` | 733.6 | 529.8 | 738.8 |
| `thread_end_fraction` | 0.6927 | 0.7641 | 0.6869 |
| `field_length_density_um_per_um2` | 0.3232 | 0.3008 | 0.3237 |
| `roots_per_cell` | 7.965 | 7.545 | 7.965 |
| `skeleton_px` | 4.289e+04 | 3.992e+04 | 4.295e+04 |
| `n_bridges` | 0 | 18.12 | 19.62 |
| `legacy_unsupported_fraction` | 0.09118 | 0.06798 | 0.09214 |

## Versions

```
python: 3.9.10
numpy: 2.0.2
scipy: 1.13.1
scikit-image: 0.24.0
networkx: 3.2.1
skan: 0.13.1
matplotlib: 3.9.4
openpyxl: 3.1.5
pillow: 11.3.0
```

## Images

- 542_z06 (`542 WT  2_z06c1-2.tif`)
- 542_z18 (`542 WT  2_z18c1-2.tif`)
- 543-2 (`543-2.tif`)
- 543_3 (`543_3.tif`)
- 543_z13 (`543_z13c1-2.tif`)
- 682_z08 (`682_z08c1-2.tif`)
- 682_z23 (`682_z23c-2.tif`)
- 682_z29 (`682_z29c1-3.tif`)
