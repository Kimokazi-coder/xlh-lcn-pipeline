"""Experimental canalicular method, on the physical scale.

An experiment, not the pipeline. It changes one idea of the current canalicular
method, the quantity that is thresholded, and reports the variants side by side
so the difference can be judged. Nothing here is used by src/lacunae.py,
src/canaliculi.py, src/quantification.py or src/diagnostics.py, and nothing
outside results/ridge/ is written.

**Pixel size 0.13 um/px** (config.PIXEL_SIZE_UM_CANAL_PHYSICAL). Pre-validation:
no number here has been checked against a manual count. This package does not
claim the new method is better.

Three variants, reported in this order: P5 is the ridge method at sigmas 0.17,
0.21 and 0.26 um with gap bridging off, A is the current method as it stands, and
P2 is the same ridge with bridging on, so P5 and P2 differ by that one switch and
nothing else. P5 leads because it is the preferred variant visually, which is a
visual preference and not a validated result.

Modules, one job each:
    params         every parameter, in micrometres, converted to pixels
    preprocess     background flattening (the current method's, by import)
    ridge          multiscale ridge detection, the one idea that changes
    skeleton       mask, skeleton, gap bridging, graph cleanup, ownership
    metrics        measures, taken by src/quantification.py for every variant
    widthprofile   the thread width measured on the image, not on the mask
    physical       entry point: the comparison table and the figures
"""
import sys as _sys
from pathlib import Path as _Path

_ROOT = _Path(__file__).resolve().parents[2]
for _extra in (str(_ROOT), str(_ROOT / "src")):
    if _extra not in _sys.path:
        _sys.path.insert(0, _extra)
