# The canalicular experiment on the physical scale

**pixel size 0.13 um/px, rounded, unconfirmed.** Pre-validation: no number here has been checked against a
manual count. Branch `canal-physical-v2`. **No variant is called better than another**, and
nothing was tuned to improve any result or to approach any published value.

## Why this exists

At 0.13 um/px a canaliculus of 0.2 to 0.4 um is about 1.5 to 3 px across, and about
2.5 to 4 px once the optics have blurred it. The masks of the current method have a median
distance transform width of 6.0 px (0.78 um) and the first ridge variants 7.4 px, so both are
roughly twice that. The scales of those first variants came from a half width measured on the
already inflated mask, which is circular: the mask set the scale and the scale set the mask.

Here every scale is set in micrometres from the pixel size, or chosen from the image itself, and
the width is measured on the image rather than on the mask.

## Variants

Fixed before the first run, all reported, none chosen afterwards. The lacunae, the vascular
handling, the graph cleanup, the ownership and the ring radii are the current method's in every
one, so only the named difference can move a number.

| variant | what | sigmas (um) | sigmas (px) | low cut | bridging |
|---|---|---|---|---|---|
| A | current method, as is | | | 0.75 | yes |
| P1 | ridge, sigmas 0.13, 0.17, 0.21 um | 0.13, 0.17, 0.21 | 1.0, 1.308, 1.615 | 0.75 | yes |
| P2 | ridge, sigmas 0.17, 0.21, 0.26 um (primary) | 0.17, 0.21, 0.26 | 1.308, 1.615, 2.0 | 0.75 | yes |
| P3 | ridge, one scale per image chosen from the image | chosen per image | chosen per image | 0.75 | yes |
| P4 | P2 with the low cut at 0.9 of the high cut | 0.17, 0.21, 0.26 | 1.308, 1.615, 2.0 | 0.9 | yes |
| P5 | P2 with gap bridging off | 0.17, 0.21, 0.26 | 1.308, 1.615, 2.0 | 0.75 | no |
| N | P2 on the notch filtered image | 0.17, 0.21, 0.26 | 1.308, 1.615, 2.0 | 0.75 | yes |

### The scale P3 chose, per image

| image | sigma (um) | sigma (px) | at the edge of the search range |
|---|---|---|---|
| 542_z06 | 0.334 | 2.5692 | yes |
| 542_z18 | 0.334 | 2.5692 | yes |
| 543-2 | 0.334 | 2.5692 | yes |
| 543_3 | 0.334 | 2.5692 | yes |
| 543_z13 | 0.334 | 2.5692 | yes |
| 682_z08 | 0.334 | 2.5692 | yes |
| 682_z23 | 0.334 | 2.5692 | yes |
| 682_z29 | 0.334 | 2.5692 | yes |

P3 searches 0.1 to 0.35 um in steps of 0.026 um (0.2 px) and takes the scale whose response is largest,
as the median over the strongest 2% of pixels outside the lacunae and the vascular
regions. The response of `skimage.filters.sato` is already scale normalised, which was checked on
synthetic ridges rather than assumed: the raw response peaks at about 0.6 times the full width at
half maximum and follows the width, while multiplying by the scale squared a second time makes
the largest candidate win whatever the structure. Full tables are in each image's json.

### The notch filter

Variant N runs. `experiments/task1_artefact.py` is imported and its `notch` is called
unchanged; nothing in that file is edited. It removes:

- a period of 2 px, which is 0.26 um, along x, constant along y
- a period of 4 px, which is 0.52 um, along x, constant along y
- a period of 4 px, which is 0.52 um, along x, constant along y

These are the two stripe frequencies that stand above the noise in every image, per
`results_experiments/task1/1.4_notch.md`. Each is removed with a Gaussian notch one bin
wide.

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
| `<label>/<label>_v2_raw.png` | the raw image, 3x, scale bar |
| `<label>/<label>_v2_A.png` | the current method, full size, 3x |
| `<label>/<label>_v2_P2.png` | the primary new variant, full size, 3x |
| `<label>/<label>_v2_compare_A_P2.png` and `.pdf` | both side by side in one file, 2x |
| `<label>/<label>_v2_tile<i>_variants.png` | one tile, raw then every variant, 8x |
| `<label>/<label>_v2_tile<i>_width_check.png` | the normals the width was sampled along |
| `<label>/pipeline_style/` | the pipeline's own picture for A and the primary variant |
| `trace_tiles/` | raw tiles for a blind hand trace, with instructions |

The full size panels and the comparison are written as indexed png with the skeleton colours
held in reserved palette slots, so **every skeleton colour is exact** and only the background is
quantised. A plain quantisation was measured first and moved all 14 overlay colours, which would
have made the colours meaningless. The background error is a mean of about 1 level out of 255.

## How it was run

```
python src/canal_physical/physical.py --dir data/WT
```

Commit `ac7f4c8b8f3b7fa6319bb965ab990e30704bc87c`, tracked files clean: True. Config hash `dc534babadca48a8`.

## Every length, in micrometres and pixels

| parameter | um | px | what |
|---|---|---|---|
| `pixel_size_um` | 0.13 |  | um per pixel, rounded, unconfirmed |
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
| `tophat_radius` (flattening) | 0.65 | 5 | unchanged from the current method; see DECISIONS.md |
| `smooth_sigma` (flattening) | 0.104 | 0.8 | unchanged from the current method |

## Mean over the 8 images

| measure | A | P1 | P2 | P3 | P4 | P5 | N |
|---|---|---|---|---|---|---|---|
| `width_fwhm_median_um` | 0.6368 | 0.6314 | 0.6352 | 0.6409 | 0.6362 | 0.6351 | 0.6352 |
| `width_dt_median_um` | 0.7853 | 0.5353 | 0.6006 | 0.7465 | 0.5814 | 0.6006 | 0.6006 |
| `low_contrast_fraction` | 0.02063 | 0.05829 | 0.04053 | 0.03504 | 0.02528 | 0.04019 | 0.04044 |
| `contrast_snr_median` | 9.955 | 7.299 | 7.877 | 8.756 | 7.724 | 7.882 | 7.877 |
| `straight_run_fraction` | 0.221 | 0.2267 | 0.2375 | 0.247 | 0.2318 | 0.2365 | 0.2376 |
| `straight_run_fraction_smoothed` | 0.1872 | 0.1797 | 0.194 | 0.2038 | 0.1921 | 0.1931 | 0.1939 |
| `rectangle_count` | 0 | 0.25 | 0 | 0 | 0 | 0 | 0 |
| `connected_to_lacuna_fraction` | 0.336 | 0.4655 | 0.48 | 0.5373 | 0.4341 | 0.4557 | 0.48 |
| `junction_count` | 529.8 | 791.2 | 738.8 | 705.9 | 608.6 | 733.6 | 738.1 |
| `thread_end_fraction` | 0.7641 | 0.6959 | 0.6869 | 0.6671 | 0.716 | 0.6927 | 0.6871 |
| `field_length_density_um_per_um2` | 0.3008 | 0.3358 | 0.3237 | 0.3106 | 0.3029 | 0.3232 | 0.3236 |
| `roots_per_cell` | 7.545 | 8.279 | 7.965 | 7.508 | 7.483 | 7.965 | 7.965 |
| `skeleton_px` | 3.992e+04 | 4.456e+04 | 4.295e+04 | 4.122e+04 | 4.019e+04 | 4.289e+04 | 4.294e+04 |
| `n_bridges` | 18.12 | 21.25 | 19.62 | 21 | 85.12 | 0 | 19.38 |
| `legacy_unsupported_fraction` | 0.06798 | 0.1018 | 0.09214 | 0.08723 | 0.06008 | 0.09118 | 0.09202 |

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
