"""Measured values beside published ranges, for reporting only.

**No value in this module is ever used to choose a parameter, a threshold or a
scale.** Every cut in this method comes from the image's own histogram. This
table exists so that a number which is far outside what the literature describes
is visible, not so that the method can be steered toward it.

What the comparison cannot tell you, and which is printed with every table:

- Count per lacuna, canalicular length, volume density and porosity are three
  dimensional quantities. A single 2D section cuts the network, so a count or a
  length measured here is not expected to match a 3D number, and no scaling
  factor is applied to pretend otherwise.
- The measured width is limited by the optical resolution of the confocal
  microscope. At a wavelength near 590 nm the lateral resolution is of the order
  of the canalicular diameter itself, so a thread is imaged wider than it is.
  The width here is a width in the image, not a true diameter.
- Several published values are human, not mouse, and some are from TEM or FIB
  rather than confocal, so the preparation and the resolution differ.
- The pixel size is 0.13 um/px, rounded and unconfirmed per image, so every
  micrometre value carries that uncertainty.

**Pixel size 0.13 um/px, rounded, unconfirmed per image.** Pre-validation.
"""
from __future__ import annotations

# (key, what it is, low, high, unit, note). The ranges are the ones named in the
# brief; the citations belong in the thesis text, not in the code.
RANGES = [
    ("width_median_um", "canalicular diameter", 0.1, 0.7, "um",
     "common 0.2 to 0.4; limited by the optical resolution, so this is a width in the image"),
    ("canalicular_length_um", "length per canaliculus", 25.0, 50.0, "um",
     "owned length per cell divided by roots per cell; a 2D section holds only part of a thread, "
     "and ownership has no distance limit"),
    ("roots_per_cell", "canaliculi per lacuna", 40.0, 115.0, "count",
     "a 3D count; a section shows the threads crossing that plane only"),
    ("areal_density_per_um2", "areal density", 0.5, 0.9, "per um^2",
     "canaliculi per um^2 of bone area"),
]

CAVEATS = [
    "Reporting only: no value below was used to choose any parameter, threshold or scale.",
    "Count per lacuna, canalicular length, volume density and porosity are 3D quantities. A single 2D",
    "section is not expected to match them, and nothing here is scaled to make it match.",
    "The width is limited by the optical resolution of the confocal microscope, so it is a width in the",
    "image and not a true canalicular diameter.",
    "Several published values are human, not mouse, and come from other preparations and resolutions.",
    "Pixel size 0.13 um/px, rounded, unconfirmed per image, so every micrometre value carries that.",
    "This is a sanity check, not a target.",
]


def areal_density_per_um2(measures: dict, params) -> float | None:
    """Canaliculi crossing a unit area, taken as the skeleton length density:
    um of thread per um^2 is numerically the number of threads crossing a 1 um
    line per um, which is what an areal density of canaliculi counts. Reported
    as a comparison only, and it is not the same construction as a count on a
    cut face."""
    return measures.get("field_length_density_um_per_um2")


def canalicular_length_um(measures: dict, params) -> float | None:
    """Length of one canaliculus, in um: the thread length a cell owns divided by
    the number of threads leaving it, both over interior cells.

    The published range is per canaliculus, not per cell, so the owned length has
    to be divided by the root count. Two things make this an approximation: a 2D
    section holds only the part of a thread that lies in the plane, which pulls
    the value down, and ownership has no distance limit, so a cell can own a
    thread that runs far away, which pulls it up. It is a comparison, not a
    measurement of a canaliculus."""
    length = measures.get("owned_length_um_per_cell")
    roots = measures.get("roots_per_cell")
    if length is None or not roots:
        return None
    return round(length / roots, 6)


def table(measures: dict, params) -> list:
    """[(what, measured, low, high, unit, inside or outside, note)] for one image
    and one method, from the comparison row that metrics.in_um builds."""
    measured = {
        "width_median_um": measures.get("width_median_um"),
        "canalicular_length_um": canalicular_length_um(measures, params),
        "roots_per_cell": measures.get("roots_per_cell"),
        "areal_density_per_um2": areal_density_per_um2(measures, params),
    }
    rows = []
    for key, what, low, high, unit, note in RANGES:
        value = measured.get(key)
        if value is None:
            verdict = "no value"
        elif low <= value <= high:
            verdict = "inside"
        else:
            verdict = "below" if value < low else "above"
        rows.append((what, value, low, high, unit, verdict, note))
    return rows
