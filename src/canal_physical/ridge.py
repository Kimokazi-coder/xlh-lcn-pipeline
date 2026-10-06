"""Multiscale ridge detection: the one idea this method changes.

The current method thresholds the flattened intensity. This one thresholds a
ridge response instead, so a pixel is kept because it sits on a thin bright line,
not because it is bright. Everything else, the flattening before it and the
skeleton, bridging, cleanup and ownership after it, is the current method's code,
imported and unchanged.

**Pixel size 0.13 um/px, rounded, unconfirmed per image.** Pre-validation.

Why Sato rather than Frangi: both are Hessian based, and Sato's tubeness keeps a
single response per scale without Frangi's second shape term, which is tuned for
blobs against tubes in 3D. With one idea changed at a time, the simpler filter is
the one to start with. Frangi is available in the same scikit-image version if it
is worth a second look; the tuning log records what was tried.

The filter is deterministic: no random choice, no seed used.
"""
from __future__ import annotations

import numpy as np
from skimage import filters


def ridge_response(flattened: np.ndarray, params, sigmas_px: tuple | None = None) -> np.ndarray:
    """Sato tubeness of the flattened channel, taken over the parameter's
    scales and returned as the maximum across them.

    `flattened` is the output of the current method's background flattening, so
    the two methods see the same image. black_ridges is False because the
    canaliculi are bright on a dark background. The response has no physical
    unit; only its own histogram is used to threshold it, never a literature
    value."""
    sigmas = list(sigmas_px) if sigmas_px else params.sigmas_px()
    assert all(s > 0 for s in sigmas), sigmas
    response = filters.sato(flattened.astype(np.float64), sigmas=sigmas,
                            black_ridges=False, mode="reflect")
    return np.nan_to_num(response, nan=0.0, posinf=0.0, neginf=0.0)


def response_summary(response: np.ndarray, params, sigmas_px: tuple | None = None) -> dict:
    """What the response looks like, for the per-image json. Reporting only."""
    finite = response[np.isfinite(response)]
    sigmas = list(sigmas_px) if sigmas_px else params.sigmas_px()
    return {
        "sigmas_px": sigmas,
        "sigmas_um": [params.um(s) for s in sigmas],
        "response_min": float(finite.min()) if finite.size else None,
        "response_max": float(finite.max()) if finite.size else None,
        "response_median": float(np.median(finite)) if finite.size else None,
        "filter": "skimage.filters.sato, bright ridges, maximum over the scales",
    }
