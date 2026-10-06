"""Every parameter of the experimental canalicular method, in one place.

Each length is written in micrometres and converted to pixels with the pixel
size of this branch, so the method is stated in physical units and the pixel
values follow from them. **Pixel size 0.13 um/px, rounded, unconfirmed per
image.** Pre-validation: nothing here has been checked against manual counts.

The micrometre values are chosen so that the pixel values of the current method
come back exactly at 0.13 um/px, which keeps the two methods comparable. Where a
value is a share or an angle it has no unit and is not converted.

Provenance of each value is in the comment above it. "Current method" means the
value src/canaliculi.py uses, with its own provenance in docs/METHODS.md
section 2; no value here was taken from the literature, and no literature value
is ever used as a threshold.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import config

# Every output of this branch carries this label.
PIXEL_LABEL = "pixel size 0.13 um/px, rounded, unconfirmed"

# The tuning set of the current method (docs/METHODS.md section 2). Any new
# value is chosen on these three images only; the other five confirm it once.
TUNING_IMAGES = ("542_z06", "543-2", "682_z29")
HELD_OUT_IMAGES = ("542_z18", "543_3", "543_z13", "682_z08", "682_z23")


@dataclass(frozen=True)
class Params:
    """Parameters in micrometres. Use px() and px_int() to get pixels."""

    # Acquisition record, rounded, not confirmed per image. The z step of
    # 0.44 um is not used: these are single 2D sections.
    # The value lives in config.py so this branch has one source of truth.
    pixel_size_um: float = config.PIXEL_SIZE_UM_CANAL_PHYSICAL

    # Ridge scales. The canalicular half width measured for the top-hat radius
    # is p50 3.0 px and p99 4.2 px (docs/METHODS.md section 2), which is 0.39
    # and 0.55 um at this pixel size. A Sato filter responds to a tube whose
    # radius is near sigma, so the range spans the measured half widths, with
    # one step between them. Confocal blur widens a thread beyond its true
    # size, so these scales describe the image, not the canaliculus.
    sigma_um: tuple = (0.39, 0.468, 0.546)

    # Hysteresis on the ridge response. The high cut is the lower of the
    # response's own three-class multi-Otsu cuts, exactly as the current method
    # does on the flattened intensity, so no literature number enters. The low
    # cut is this share of it: the current method's value, carried over
    # unchanged so that only the response being thresholded differs.
    hysteresis_low_fraction: float = 0.75

    # Lacuna buffer: current method 2 px, so the lacuna rim cannot read as a
    # thread stub.
    lacuna_buffer_um: float = 0.26

    # Mask fragments below this area are thresholding noise: current method
    # 8 px^2.
    min_object_area_um2: float = 0.1352

    # Gap bridging, all from the current method: longest gap 10 px, the walk
    # back that estimates a thread's direction 5 px. The angle and the signal
    # rule are shares and are kept as they are.
    max_bridge_gap_um: float = 1.3
    direction_walk_um: float = 0.65
    max_bridge_angle_deg: float = 40.0
    min_bridge_signal_fraction: float = 0.7

    # Graph cleanup, from the current method: spurs below 4 px are thresholding
    # noise, internal edges below 6 px are thread crossings.
    prune_spur_um: float = 0.52
    min_internal_edge_um: float = 0.78

    # Ownership and roots, from the current method: a skeleton node within
    # 10 px of a lacuna body attaches to it, and attachment points closer than
    # 8 px count as one root.
    lacuna_attach_gap_um: float = 1.3
    root_merge_um: float = 1.04

    # Ring radii, from the current method: 30 and 60 px, so the ring measures of
    # the two methods are the same measure.
    ring_radii_um: tuple = (3.9, 7.8)

    # Vascular canals, from the current method: an opening of 8 px erases every
    # canaliculus, the flagged region is dilated by 4 px, and a broad object is
    # flagged only if it spans at least 0.45 of the frame and its major axis is
    # at least 420 px.
    broad_opening_um: float = 1.04
    vascular_dilation_um: float = 0.52
    vascular_min_span_fraction: float = 0.45
    vascular_min_major_axis_um: float = 54.6

    # Width sampling: the percentiles reported beside the median.
    width_percentiles: tuple = (10, 90)

    # No random choice is made anywhere in this method. The seed is recorded so
    # that a later change cannot introduce one unnoticed.
    random_seed: int = 0

    def px(self, um: float) -> float:
        """Micrometres to pixels, rounded to 6 decimals so that a value meant to
        be a whole number of pixels comes back as one."""
        return round(um / self.pixel_size_um, 6)

    def px_int(self, um: float) -> int:
        """Micrometres to a whole number of pixels."""
        return int(round(um / self.pixel_size_um))

    def area_px2(self, um2: float) -> int:
        """Square micrometres to whole square pixels."""
        return int(round(um2 / self.pixel_size_um ** 2))

    def um(self, px: float) -> float:
        """Pixels to micrometres."""
        return round(px * self.pixel_size_um, 6)

    def sigmas_px(self) -> list:
        return [self.px(s) for s in self.sigma_um]

    def ring_radii_px(self) -> list:
        return [self.px(r) for r in self.ring_radii_um]

    def table(self) -> list:
        """(name, value in um, value in px, what it is) for every parameter, for
        the report and the json. A share or an angle has no pixel value."""
        rows = [
            ("pixel_size_um", self.pixel_size_um, None, "um per pixel, rounded, unconfirmed"),
            ("sigma_um", list(self.sigma_um), self.sigmas_px(), "ridge scales"),
            ("hysteresis_low_fraction", self.hysteresis_low_fraction, None, "share of the high cut"),
            ("lacuna_buffer_um", self.lacuna_buffer_um, self.px_int(self.lacuna_buffer_um), "buffer around a lacuna"),
            ("min_object_area_um2", self.min_object_area_um2, self.area_px2(self.min_object_area_um2),
             "smallest mask fragment, area"),
            ("max_bridge_gap_um", self.max_bridge_gap_um, self.px(self.max_bridge_gap_um), "longest gap bridged"),
            ("direction_walk_um", self.direction_walk_um, self.px_int(self.direction_walk_um),
             "walk back for the thread direction"),
            ("max_bridge_angle_deg", self.max_bridge_angle_deg, None, "degrees"),
            ("min_bridge_signal_fraction", self.min_bridge_signal_fraction, None, "share of the cut"),
            ("prune_spur_um", self.prune_spur_um, self.px(self.prune_spur_um), "shortest kept spur"),
            ("min_internal_edge_um", self.min_internal_edge_um, self.px(self.min_internal_edge_um),
             "shortest kept internal edge"),
            ("lacuna_attach_gap_um", self.lacuna_attach_gap_um, self.px(self.lacuna_attach_gap_um), "attach distance"),
            ("root_merge_um", self.root_merge_um, self.px(self.root_merge_um), "root cluster distance"),
            ("ring_radii_um", list(self.ring_radii_um), self.ring_radii_px(), "ring radii"),
            ("broad_opening_um", self.broad_opening_um, self.px_int(self.broad_opening_um),
             "opening that finds broad structures"),
            ("vascular_dilation_um", self.vascular_dilation_um, self.px_int(self.vascular_dilation_um),
             "dilation of the flagged region"),
            ("vascular_min_span_fraction", self.vascular_min_span_fraction, None, "share of the frame"),
            ("vascular_min_major_axis_um", self.vascular_min_major_axis_um,
             self.px(self.vascular_min_major_axis_um), "smallest flagged major axis"),
            ("width_percentiles", list(self.width_percentiles), None, "percentiles reported"),
            ("random_seed", self.random_seed, None, "no random choice is made"),
        ]
        return rows

    def as_dict(self) -> dict:
        return {"pixel_size_label": PIXEL_LABEL, **asdict(self)}


DEFAULT = Params()
