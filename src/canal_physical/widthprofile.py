"""Thread width measured on the image, not on the mask.

The distance transform of a mask can only return the width of that mask, so if
the mask is too fat the width is too large and nothing in the measurement can
show it. This module measures the width on the flattened image itself: at every
usable skeleton pixel it samples the intensity along the normal to the thread and
takes the full width at half maximum of that profile.

**The FWHM includes the optical blur of the microscope.** It is an apparent width
in the image and an upper bound on the true canalicular diameter, not the
diameter itself. It is not validated against any manual measurement. The
objective's numerical aperture, the emission wavelength and the pinhole are
unknown, so no theoretical point spread function is computed anywhere and none is
subtracted.

**Pixel size 0.13 um/px, rounded, unconfirmed per image.** Pre-validation.

Method, per skeleton pixel:

1. Pixels that cannot give a clean profile are left out first: pixels gap
   bridging drew (no signal under them), pixels off the thresholded mask, pixels
   inside the lacuna buffer, pixels inside the vascular mask with its dilation,
   and junction pixels (three or more skeleton neighbours), where two threads
   cross and a single normal is meaningless.
2. The local direction is the principal axis of the skeleton pixels within
   DIRECTION_RADIUS_PX, taken as the eigenvector of their covariance matrix. This
   is a principal component analysis of the skeleton point set, done in closed
   form for the 2 by 2 case so it can run on every pixel at once. The normal is
   perpendicular to it.
3. The flattened image is sampled along that normal from -PROFILE_HALF_PX to
   +PROFILE_HALF_PX in steps of PROFILE_STEP_PX, by bilinear interpolation.
4. The baseline is the lower of the two profile minima, one on each side. The
   peak is the profile maximum within PEAK_WINDOW_PX of the centre. The width is
   the distance between the two points where the profile crosses the half way
   level between baseline and peak, each found by linear interpolation between
   the two samples that straddle it.
5. A pixel fails when the peak is not above the baseline, or when either crossing
   is not found inside the window. The failure fraction is reported.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

# Radius (px) of the neighbourhood whose principal axis gives the local thread
# direction. 3 px is about 0.39 um: long enough to average the pixel grid away,
# short enough that a curving thread is still straight across it.
DIRECTION_RADIUS_PX = 3

# The profile runs this far either side of the skeleton pixel. 6 px is about
# 0.78 um, wider than any thread seen here, so the background is reached on both
# sides even for the fattest mask.
PROFILE_HALF_PX = 6.0

# Sampling step along the normal. 0.25 px keeps the interpolation error of a
# crossing far below the 0.3 px the synthetic check allows.
PROFILE_STEP_PX = 0.25

# The peak is looked for this close to the centre, so a neighbouring thread
# inside the window cannot be taken for this one.
PEAK_WINDOW_PX = 1.5

# The background for the contrast measure is taken from this band on both sides.
BACKGROUND_INNER_PX = 4.0
BACKGROUND_OUTER_PX = 6.0

# A skeleton pixel with a contrast to noise ratio below this counts as low
# contrast. 2 is the conventional "visible above the noise" line and is used here
# only to summarise, never to threshold an image.
LOW_CONTRAST_SNR = 2.0

NEIGHBOUR_OFFSETS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

# The median of the positive half of a centred normal distribution, in units of
# its standard deviation. Used to recover the noise from a background that the
# flattening has clipped at zero.
HALF_NORMAL_MEDIAN = 0.6744897501960817
MIN_NOISE_PIXELS = 1000


def junction_mask(skeleton: np.ndarray) -> np.ndarray:
    """Skeleton pixels with three or more skeleton neighbours, where a single
    thread direction has no meaning."""
    count = np.zeros(skeleton.shape, dtype=np.int16)
    for dr, dc in NEIGHBOUR_OFFSETS:
        count += np.roll(np.roll(skeleton, dr, axis=0), dc, axis=1).astype(np.int16)
    return skeleton & (count >= 3)


def local_normals(skeleton: np.ndarray, rows: np.ndarray, cols: np.ndarray) -> tuple:
    """Unit normals at the given skeleton pixels, from the principal axis of the
    skeleton points around each one.

    The covariance of the neighbouring skeleton coordinates is built from running
    sums, so every pixel is handled in the same few array operations rather than
    one at a time. For a symmetric 2 by 2 matrix the principal eigenvector has a
    closed form, which avoids an eigen decomposition per pixel."""
    disk = np.zeros((2 * DIRECTION_RADIUS_PX + 1,) * 2, dtype=float)
    yy, xx = np.ogrid[-DIRECTION_RADIUS_PX:DIRECTION_RADIUS_PX + 1,
                      -DIRECTION_RADIUS_PX:DIRECTION_RADIUS_PX + 1]
    disk[yy * yy + xx * xx <= DIRECTION_RADIUS_PX ** 2] = 1.0

    mask = skeleton.astype(float)
    r_index, c_index = np.indices(skeleton.shape, dtype=float)
    n = ndi.convolve(mask, disk, mode="constant")
    sum_r = ndi.convolve(mask * r_index, disk, mode="constant")
    sum_c = ndi.convolve(mask * c_index, disk, mode="constant")
    sum_rr = ndi.convolve(mask * r_index * r_index, disk, mode="constant")
    sum_cc = ndi.convolve(mask * c_index * c_index, disk, mode="constant")
    sum_rc = ndi.convolve(mask * r_index * c_index, disk, mode="constant")

    n_at = np.maximum(n[rows, cols], 1.0)
    mean_r = sum_r[rows, cols] / n_at
    mean_c = sum_c[rows, cols] / n_at
    var_r = sum_rr[rows, cols] / n_at - mean_r * mean_r
    var_c = sum_cc[rows, cols] / n_at - mean_c * mean_c
    cov = sum_rc[rows, cols] / n_at - mean_r * mean_c

    # Principal eigenvector of [[var_r, cov], [cov, var_c]], in closed form.
    half_trace = 0.5 * (var_r + var_c)
    root = np.sqrt(np.maximum((0.5 * (var_r - var_c)) ** 2 + cov * cov, 0.0))
    top = half_trace + root
    dir_r = cov
    dir_c = top - var_r
    # Where the covariance vanishes the axis is along one of the image axes.
    flat = np.abs(cov) < 1e-12
    dir_r = np.where(flat, np.where(var_r >= var_c, 1.0, 0.0), dir_r)
    dir_c = np.where(flat, np.where(var_r >= var_c, 0.0, 1.0), dir_c)
    length = np.hypot(dir_r, dir_c)
    length[length == 0] = 1.0
    dir_r, dir_c = dir_r / length, dir_c / length
    # The normal is the direction turned by a quarter turn.
    return -dir_c, dir_r


def sample_profiles(image: np.ndarray, rows: np.ndarray, cols: np.ndarray,
                    normal_r: np.ndarray, normal_c: np.ndarray, offsets: np.ndarray) -> np.ndarray:
    """Bilinear samples of `image` at each pixel, along its normal, at `offsets`.
    Returns one row per pixel."""
    sample_r = rows[:, None] + normal_r[:, None] * offsets[None, :]
    sample_c = cols[:, None] + normal_c[:, None] * offsets[None, :]
    flat = ndi.map_coordinates(image, [sample_r.ravel(), sample_c.ravel()], order=1, mode="nearest")
    return flat.reshape(sample_r.shape)


def _crossings(profiles: np.ndarray, offsets: np.ndarray, half_level: np.ndarray,
               centre: int) -> tuple:
    """Where each profile falls below its half way level, left and right of the
    centre, by linear interpolation between the straddling samples. NaN when a
    profile never falls below it inside the window."""
    n_pixels, n_samples = profiles.shape
    above = profiles >= half_level[:, None]
    left = np.full(n_pixels, np.nan)
    right = np.full(n_pixels, np.nan)

    # Walking outward from the centre, the first sample that is not above the
    # level ends the peak on that side.
    for side, out in ((-1, left), (1, right)):
        step = range(centre - 1, -1, -1) if side < 0 else range(centre + 1, n_samples)
        found = np.zeros(n_pixels, dtype=bool)
        previous = np.full(n_pixels, centre)
        for i in step:
            crossing_here = (~above[:, i]) & (~found)
            if crossing_here.any():
                j = previous[crossing_here]
                y1 = profiles[crossing_here, j]
                y2 = profiles[crossing_here, i]
                level = half_level[crossing_here]
                span = np.where(y1 == y2, 1.0, y1 - y2)
                frac = np.clip((y1 - level) / span, 0.0, 1.0)
                out[crossing_here] = offsets[j] + frac * (offsets[i] - offsets[j])
                found |= crossing_here
            previous = np.where(above[:, i] & ~found, i, previous)
            if found.all():
                break
    return left, right


def measure(flattened: np.ndarray, skeleton: np.ndarray, usable: np.ndarray) -> dict:
    """Width and contrast at every usable skeleton pixel.

    `usable` is the skeleton pixels the caller allows (see the module docstring
    for what is excluded). Returns the per-pixel arrays and their positions, so a
    figure can draw the normals that were sampled."""
    rows, cols = np.nonzero(usable)
    out = {"rows": rows, "cols": cols, "n_candidates": int(usable.sum())}
    if rows.size == 0:
        out.update({"width_px": np.array([]), "ok": np.array([], dtype=bool),
                    "normal_r": np.array([]), "normal_c": np.array([]),
                    "peak": np.array([]), "baseline": np.array([])})
        return out

    normal_r, normal_c = local_normals(skeleton, rows, cols)
    offsets = np.arange(-PROFILE_HALF_PX, PROFILE_HALF_PX + 0.5 * PROFILE_STEP_PX, PROFILE_STEP_PX)
    centre = int(np.argmin(np.abs(offsets)))
    profiles = sample_profiles(flattened, rows, cols, normal_r, normal_c, offsets)

    near = np.abs(offsets) <= PEAK_WINDOW_PX
    peak = profiles[:, near].max(axis=1)
    left_side = offsets < 0
    right_side = offsets > 0
    baseline = np.minimum(profiles[:, left_side].min(axis=1), profiles[:, right_side].min(axis=1))
    height = peak - baseline
    half_level = baseline + 0.5 * height

    left, right = _crossings(profiles, offsets, half_level, centre)
    width = right - left
    ok = (height > 0) & np.isfinite(left) & np.isfinite(right) & (width > 0)

    out.update({"width_px": width, "ok": ok, "normal_r": normal_r, "normal_c": normal_c,
                "peak": peak, "baseline": baseline, "offsets": offsets, "profiles": profiles})
    return out


def contrast(flattened: np.ndarray, rows: np.ndarray, cols: np.ndarray, normal_r: np.ndarray,
             normal_c: np.ndarray, noise: float) -> np.ndarray:
    """Contrast to noise at each skeleton pixel: the intensity at the pixel minus
    the median intensity of the band from BACKGROUND_INNER_PX to
    BACKGROUND_OUTER_PX along the normal on both sides, divided by the noise.

    The background band is taken on both sides so that a thread beside a brighter
    structure is not judged against that structure alone."""
    if rows.size == 0:
        return np.array([])
    band = np.arange(BACKGROUND_INNER_PX, BACKGROUND_OUTER_PX + 0.25, 0.5)
    offsets = np.concatenate([-band[::-1], band])
    background = np.median(sample_profiles(flattened, rows, cols, normal_r, normal_c, offsets), axis=1)
    centre = ndi.map_coordinates(flattened, [rows.astype(float), cols.astype(float)], order=1,
                                 mode="nearest")
    return (centre - background) / noise if noise > 0 else np.full(rows.shape, np.nan)


def noise_level(flattened: np.ndarray, exclude: np.ndarray) -> float:
    """The noise of the flattened image: 1.4826 times the median absolute
    deviation over the pixels outside `exclude`, which is the robust estimate of
    a standard deviation. The caller excludes the lacunae, the vascular regions
    and the thresholded mask of the variant being measured, so the estimate comes
    from background only and is made the same way for every variant."""
    values = flattened[~exclude]
    if values.size == 0:
        return 0.0
    # The flattening subtracts the histogram mode and clips at zero, so on these
    # images more than half of the background is exactly 0 and both the median
    # and the median absolute deviation of the background are 0. A plain robust
    # estimate therefore returns no noise at all. What survives the clipping is
    # the positive half of the noise, and for a symmetric distribution clipped at
    # its centre the median of the positive half is 0.6745 times the standard
    # deviation, which gives the estimate back.
    positive = values[values > 0]
    if positive.size >= MIN_NOISE_PIXELS:
        return float(np.median(positive) / HALF_NORMAL_MEDIAN)
    median = float(np.median(values))
    return float(1.4826 * np.median(np.abs(values - median)))


def summarise(width_px: np.ndarray, ok: np.ndarray, n_candidates: int, pixel_size_um: float,
              precision: int = 4) -> dict:
    """Median, p10 and p90 of the width in px and um, with how many pixels were
    used and what share failed."""
    good = width_px[ok] if width_px.size else np.array([])
    out = {
        "width_fwhm_pixels_used": int(good.size),
        "width_fwhm_candidates": int(n_candidates),
        "width_fwhm_failure_fraction": (round(1.0 - good.size / n_candidates, precision)
                                        if n_candidates else None),
    }
    if good.size == 0:
        for name in ("median", "p10", "p90"):
            out[f"width_fwhm_{name}_px"] = None
            out[f"width_fwhm_{name}_um"] = None
        return out
    for name, value in (("median", float(np.median(good))), ("p10", float(np.percentile(good, 10))),
                        ("p90", float(np.percentile(good, 90)))):
        out[f"width_fwhm_{name}_px"] = round(value, precision)
        out[f"width_fwhm_{name}_um"] = round(value * pixel_size_um, precision + 2)
    return out
