"""Experimental canalicular method, branch canal-physical.

An experiment, not the pipeline. It changes one idea of the current canalicular
method, the quantity that is thresholded, and reports the two side by side so the
difference can be judged. Nothing here is used by src/lacunae.py,
src/canaliculi.py, src/quantification.py or src/diagnostics.py, and nothing
outside results_experiments/canal_physical/ is written.

**Pixel size 0.13 um/px, rounded, unconfirmed per image**
(config.PIXEL_SIZE_UM_CANAL_PHYSICAL). Pre-validation: no number here has been
checked against a manual count. This package does not claim the new method is
better.

Modules, one job each:
    params         every parameter, in micrometres, converted to pixels
    preprocess     background flattening (the current method's, by import)
    ridge          multiscale ridge detection, the one idea that changes
    skeleton       mask, skeleton, gap bridging, graph cleanup, ownership
    metrics        measures, taken by src/quantification.py for both methods
    plausibility   published ranges, for reporting only, never for tuning
    compare        side-by-side figures and the comparison tables
    run            entry point
"""
import sys as _sys
from pathlib import Path as _Path

_ROOT = _Path(__file__).resolve().parents[2]
for _extra in (str(_ROOT), str(_ROOT / "src")):
    if _extra not in _sys.path:
        _sys.path.insert(0, _extra)
