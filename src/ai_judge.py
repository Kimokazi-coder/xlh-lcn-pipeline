"""The AI judge layer: candidates, the judge, and the assembly.

EXPERIMENT, branch exp-ai-layer. Nothing here runs unless it is asked for, and
nothing here changes a pipeline number while config.AI_JUDGE_ENABLED is False.
The experiment, and every decision taken while building it, is written up in
docs/EXPERIMENT_AI.md.

The division of labour, which is the whole point of the design:

  DETERMINISTIC CODE IS THE ONLY CODE THAT TOUCHES PIXELS. This module makes the
  candidate segments (step 1), draws the pictures, sends them, reads the answer
  back, and hands the pipeline a set of pixels to add and a set to drop (step 3).
  The judge only ever answers "real or artifact, and whose", per numbered
  segment, about a picture. It never sees a file name, a path or a genotype, and
  it never writes a pixel.

Where the parts live:

  src/judge_prompt.md      the one fixed prompt, used for every image
  docs/judge_examples.md   Karim's worked examples, loaded into the prompt
  results/ai_log/<label>/  every request and answer, the pictures that were
                           sent, the decision file and the run report
  config.py                the switch, the pinned model, the prices, the cost
                           ceiling and every number the candidate rule uses

All sizes are in PIXELS, as everywhere else in this repository.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import morphology, segmentation

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canaliculi  # noqa: E402
import lacunae  # noqa: E402


# Parameters of this module
# Everything with a biological or optical reason lives in config.py. What is
# left here is the drawing and the bookkeeping.

# The colours a cell body is outlined in, in the order they are handed out. The
# body the case is about is ALWAYS the first one, yellow; the others go to the
# neighbouring bodies in the crop by increasing lacuna id, so the mapping is
# reproducible and never depends on where the crop happens to sit. These names
# are the vocabulary the judge answers with, and src/judge_prompt.md lists the
# same six.
OWNER_COLOURS = (
    ("yellow", (255, 255, 0)),
    ("cyan", (0, 255, 255)),
    ("magenta", (255, 0, 255)),
    ("orange", (255, 150, 0)),
    ("green", (0, 220, 0)),
    ("blue", (80, 120, 255)),
)
# A body beyond the six is outlined in this grey. Grey is not in the vocabulary,
# so such a body can never be named as an owner; the case records how many there
# were and the run report adds them up, because a case with one is a case whose
# answer could not name the right cell.
UNNAMEABLE_COLOUR = (160, 160, 160)
# The candidate segments, and their numbers.
SEGMENT_COLOUR = (255, 60, 60)
NUMBER_COLOUR = (255, 255, 255)
NUMBER_HALO = (0, 0, 0)
# The gap between the two panels, in rendered px, and its colour.
PANEL_GAP_PX = 8
PANEL_GAP_COLOUR = (40, 40, 40)
# How large a digit is drawn, as a multiple of the 5 x 7 glyph below.
DIGIT_SCALE = 3

# Report only. A candidate segment counts as ALREADY TRACED when at least this
# share of its pixels lie within one pixel of the skeleton the global cut
# produced. It decides nothing: it is how the report says whether the judge was
# shown new tracing or tracing the pipeline already had.
TRACED_SHARE = 0.5

# Derived from config, once.
MIN_SEGMENT_PX = config.px_int(config.AI_MIN_SEGMENT_LENGTH_UM)

LOG_SCHEMA = "lcn-ai-judge-log-1"
DECISIONS_SCHEMA = "lcn-ai-judge-decisions-1"


# 5 x 7 digits, drawn by this module so that a number in a picture needs no
# font file and comes out byte for byte the same on any machine.
DIGIT_GLYPHS = {
    "0": (" ### ", "#   #", "#  ##", "# # #", "##  #", "#   #", " ### "),
    "1": ("  #  ", " ##  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "),
    "2": (" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"),
    "3": ("#####", "   # ", "  #  ", "   # ", "    #", "#   #", " ### "),
    "4": ("   # ", "  ## ", " # # ", "#  # ", "#####", "   # ", "   # "),
    "5": ("#####", "#    ", "#### ", "    #", "    #", "#   #", " ### "),
    "6": ("  ## ", " #   ", "#    ", "#### ", "#   #", "#   #", " ### "),
    "7": ("#####", "    #", "   # ", "  #  ", " #   ", " #   ", " #   "),
    "8": (" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "),
    "9": (" ### ", "#   #", "#   #", " ####", "    #", "   # ", " ##  "),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def canonical_json(obj) -> str:
    """One spelling for anything that gets hashed."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def strip_comments(text: str) -> str:
    """Drop every html comment, which is how src/judge_prompt.md and
    docs/judge_examples.md carry notes to the reader that are not sent."""
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()


# The empty zone of one lacuna, and what the glow costs a thread in it

def _window(body: np.ndarray, shape: tuple) -> tuple:
    """The bounding box of the body grown by config.AI_MAX_SEARCH_PX."""
    rows, cols = np.nonzero(body)
    reach = config.AI_MAX_SEARCH_PX
    return (max(0, int(rows.min()) - reach), min(shape[0], int(rows.max()) + reach + 1),
            max(0, int(cols.min()) - reach), min(shape[1], int(cols.max()) + reach + 1))


def zone_and_contrast(lacuna_id_map: np.ndarray, skeleton_global: np.ndarray,
                      response: np.ndarray, lacuna_id: int) -> dict:
    """One lacuna's EMPTY ZONE, the band just beyond it, and its CONTRAST RATIO.

    The empty width is measured exactly as the empty-zone diagnostic measures it
    (src/diagnostics.py empty-zone, METHODS section 19): the frame around the
    body is cut into config.AI_SECTORS angular sectors, and a sector's empty
    width is the smallest distance to the body over the skeleton pixels lying in
    it. A sector with no skeleton within config.AI_MAX_SEARCH_PX, or with
    another body nearer than its skeleton, is censored. The zone is the pixels
    out to each sector's own width, so it follows the real shape of the hole and
    is not a circle.

    Measured here on the GLOBAL CUT SKELETON, the skeleton the ridge threshold
    and the glow zone rule produced before the dim pass and before the 50 um
    prune. That is the skeleton that exists at the point in the pipeline where
    the candidates are made, and it depends on no ownership and on no later
    stage, so the zone is a property of the image and the lacuna alone. The
    diagnostic measures the same thing on the final skeleton, which is why the
    two numbers differ slightly and neither is wrong.

    The CONTRAST RATIO is this lacuna's own measurement of what its glow costs a
    thread: the p90 of the ridge response in the reference band just beyond the
    hole, over the p90 inside the hole. METHODS section 18 measured that as 31 to
    71% for the set, which is a ratio of 1.4 to 3.2; this is the same
    measurement per lacuna. Floored at 1 so the candidate cut can never be
    stricter than the pipeline's own, and capped at config.AI_CONTRAST_RATIO_MAX
    because past that the ratio is measuring an empty hole and not a thread in
    one.

    This function is deliberately NOT imported from src/diagnostics.py: the
    pipeline must never depend on a diagnostic. It is the same rule written for
    this use.
    """
    shape = lacuna_id_map.shape
    body = lacuna_id_map == lacuna_id
    all_bodies = lacuna_id_map > 0
    sectors = int(config.AI_SECTORS)
    rows, cols = np.nonzero(body)
    r0, c0 = float(rows.mean()), float(cols.mean())
    gap = ndi.distance_transform_edt(~body)
    r_lo, r_hi, c_lo, c_hi = _window(body, shape)

    sub_gap = gap[r_lo:r_hi, c_lo:c_hi]
    sub_skel = skeleton_global[r_lo:r_hi, c_lo:c_hi]
    sub_other = (all_bodies & ~body)[r_lo:r_hi, c_lo:c_hi]
    rr, cc = np.indices(sub_gap.shape)
    ang = np.arctan2(rr + r_lo - r0, cc + c_lo - c0) % (2.0 * np.pi)
    sector = (np.round(ang / (2.0 * np.pi) * sectors).astype(np.int64)) % sectors
    near = (sub_gap > 0) & (sub_gap <= config.AI_MAX_SEARCH_PX)

    blocked = np.full(sectors, np.inf)
    sel = near & sub_other
    np.minimum.at(blocked, sector[sel], sub_gap[sel])
    widths = np.full(sectors, np.inf)
    sel = near & sub_skel
    np.minimum.at(widths, sector[sel], sub_gap[sel])
    widths = np.where(np.isfinite(widths) & (blocked > widths), widths, np.nan)

    w = np.where(np.isfinite(widths), widths, -1.0)[sector]
    zone = np.zeros(shape, dtype=bool)
    zone[r_lo:r_hi, c_lo:c_hi] = (sub_gap > 0) & (sub_gap <= w)
    band = np.zeros(shape, dtype=bool)
    band[r_lo:r_hi, c_lo:c_hi] = ((sub_gap > w) & (sub_gap <= w + config.AI_REFERENCE_BAND_PX)
                                  & (w >= 0))
    zone &= ~all_bodies
    band &= ~all_bodies

    p90_zone = float(np.percentile(response[zone], 90)) if zone.any() else 0.0
    p90_band = float(np.percentile(response[band], 90)) if band.any() else 0.0
    if p90_zone > 0.0 and p90_band > 0.0:
        ratio = min(max(p90_band / p90_zone, 1.0), float(config.AI_CONTRAST_RATIO_MAX))
    else:
        # No hole, or nothing to compare it with: the pipeline's own cut stands.
        ratio = 1.0
    good = np.isfinite(widths)
    return {
        "lacuna_id": int(lacuna_id),
        "centroid_xy": [round(c0, 1), round(r0, 1)],
        "body_px": int(body.sum()),
        "empty_width_px": round(float(np.median(widths[good])), 3) if good.any() else None,
        "empty_width_um": (round(config.um(float(np.median(widths[good]))), 4)
                           if good.any() else None),
        "sectors_answered": int(good.sum()),
        "sectors_total": sectors,
        "zone_px": int(zone.sum()),
        "band_px": int(band.sum()),
        "response_p90_in_the_zone": round(p90_zone, 8),
        "response_p90_in_the_band_beyond": round(p90_band, 8),
        "contrast_ratio": round(ratio, 4),
        "zone": zone,
    }


# The candidates (step 1)

def _junctions(skel: np.ndarray) -> np.ndarray:
    """Skeleton pixels with three or more skeleton neighbours. Removing them
    splits the skeleton into its branches, which is what a segment is."""
    neighbours = ndi.convolve(skel.astype(np.uint8), np.ones((3, 3), dtype=np.uint8),
                              mode="constant", cval=0) - skel
    return skel & (neighbours >= 3)


def image_candidates(state: dict) -> dict:
    """Every candidate segment of one image, numbered, with the zone each came
    from. The deterministic half of the experiment: no network, no judge.

    Within each lacuna's own empty zone, and only there, the ridge response is
    accepted down to config.AI_CANDIDATE_CUT_FRACTION of the low cut after being
    scaled by that lacuna's contrast ratio. The pipeline's own exclusions still
    hold inside the zone: the lacuna bodies with their buffer are cut out, and
    inside a flagged vascular structure only already-bright pixels survive, both
    as in canaliculi.hysteresis_mask. The mask the global cut already produced is
    unioned in, so the permissive mask is a superset of the pipeline's inside the
    zone and a candidate is never a pixel the pipeline would have refused on a
    rule other than the cut.

    The permissive mask is skeletonized ONCE, over the whole frame, not zone by
    zone: the medial axis of a region clipped at a zone boundary runs along that
    boundary, which would invent threads that follow the shape of the hole. The
    skeleton is then split at its junctions, and each piece that lies in a zone,
    clipped to that zone, is one candidate segment.

    A zone belongs to ONE lacuna: zones overlap where two bodies are close, so a
    pixel is given to the nearer body, the same nearest-lacuna partition the
    pipeline's attachment uses. No segment is therefore ever judged twice.

    Segments shorter than MIN_SEGMENT_PX are dropped, and at most
    config.AI_MAX_SEGMENTS_PER_CASE are offered per case, the longest first; the
    rest are counted as not offered and keep the deterministic decision.
    Numbering is in reading order, by the top left pixel of each segment, so the
    numbers in the picture run roughly top to bottom.
    """
    shape = state["shape"]
    lacuna_id_map = state["lacuna_id_map"]
    response = state["response"]
    high_cut = state["high_cut"]
    low_cut = high_cut * canaliculi.HYSTERESIS_LOW_FRACTION
    floor = low_cut * config.AI_CANDIDATE_CUT_FRACTION
    n_lacunae = state["n_lacunae"]

    buffered = morphology.dilation(state["lacuna_mask"],
                                   morphology.disk(canaliculi.LACUNA_DILATION_PX))
    allowed = ~buffered & ~(lacuna_id_map > 0)
    if state["flagged"].any():
        allowed &= ~(state["flagged"] & (response < high_cut))

    # The nearest-lacuna partition, computed here from the body map alone so the
    # two phases of the experiment cannot disagree about it.
    _dist, nearest_id, _index = canaliculi.nearest_lacuna_map(lacuna_id_map)

    zones = {}
    zone_owner = np.zeros(shape, dtype=np.int32)
    permissive = np.zeros(shape, dtype=bool)
    for lacuna_id in range(1, n_lacunae + 1):
        z = zone_and_contrast(lacuna_id_map, state["skeleton_global"], response, lacuna_id)
        own = z["zone"] & (nearest_id == lacuna_id) & allowed
        zone_owner[own] = lacuna_id
        permissive |= own & ((response * z["contrast_ratio"] >= floor)
                             | state["candidate_global"])
        z["own_zone_px"] = int(own.sum())
        z.pop("zone")
        zones[lacuna_id] = z
    permissive |= state["candidate_global"]

    skeleton = morphology.skeletonize(permissive)
    junctions = _junctions(skeleton)
    structure = np.ones((3, 3), dtype=np.uint8)

    # Every candidate piece gets its own label; every other skeleton pixel goes
    # into one bucket, so that a mask pixel nearer a piece the judge was not
    # asked about stays with it and is never moved by a verdict.
    piece_label = np.zeros(shape, dtype=np.int32)
    cases = []
    next_label = 1
    for lacuna_id in range(1, n_lacunae + 1):
        in_zone = skeleton & ~junctions & (zone_owner == lacuna_id)
        labelled, count = ndi.label(in_zone, structure=structure)
        found = []
        if count:
            sizes = ndi.sum(np.ones_like(labelled, dtype=np.int64), labelled,
                            index=np.arange(1, count + 1)).astype(np.int64)
            for piece in range(1, count + 1):
                if sizes[piece - 1] < MIN_SEGMENT_PX:
                    continue
                rows, cols = np.nonzero(labelled == piece)
                found.append({"rows": rows, "cols": cols, "px": int(rows.size)})
        found.sort(key=lambda s: (-s["px"], int(s["rows"].min()), int(s["cols"].min())))
        offered = found[:int(config.AI_MAX_SEGMENTS_PER_CASE)]
        not_offered = found[int(config.AI_MAX_SEGMENTS_PER_CASE):]
        offered.sort(key=lambda s: (int(s["rows"].min()), int(s["cols"].min())))

        segments = []
        for number, piece in enumerate(offered, start=1):
            piece_label[piece["rows"], piece["cols"]] = next_label
            segments.append({
                "n": number,
                "label": next_label,
                "rows": piece["rows"],
                "cols": piece["cols"],
                "px": piece["px"],
                "length_um": round(config.um(piece["px"]), 4),
            })
            next_label += 1
        cases.append({
            "lacuna_id": lacuna_id,
            "case_id": f"case_{lacuna_id:04d}",
            "zone": zones[lacuna_id],
            "segments": segments,
            "segments_offered": len(segments),
            "segments_not_offered": len(not_offered),
            "px_not_offered": int(sum(s["px"] for s in not_offered)),
        })
    other = skeleton & (piece_label == 0)
    piece_label[other] = next_label  # the one bucket for everything not asked about

    # Which mask pixel belongs to which centre line: the nearest labelled
    # skeleton pixel. This is what a verdict acts on, so that dropping a segment
    # drops the mask it is the centre line of and nothing else.
    index = ndi.distance_transform_edt(piece_label == 0, return_distances=False,
                                       return_indices=True)
    territory = np.where(permissive & (zone_owner > 0), piece_label[index[0], index[1]], 0)

    # Report only: was the judge shown new tracing, or tracing the pipeline had?
    near_global = ndi.distance_transform_edt(~state["skeleton_global"]) <= 1.0
    for case in cases:
        for seg in case["segments"]:
            share = float(near_global[seg["rows"], seg["cols"]].mean())
            seg["already_traced_share"] = round(share, 4)
            seg["already_traced"] = bool(share >= TRACED_SHARE)
            seg["territory_px"] = int((territory == seg["label"]).sum())

    return {
        "shape": shape,
        "cases": cases,
        "zone_owner": zone_owner,
        "permissive": permissive,
        "permissive_skeleton": skeleton,
        "territory": territory,
        "cut": {"high": round(float(high_cut), 8), "low": round(float(low_cut), 8),
                "candidate_floor_before_scaling": round(float(floor), 8),
                "cut_fraction": config.AI_CANDIDATE_CUT_FRACTION,
                "contrast_ratio_cap": config.AI_CONTRAST_RATIO_MAX,
                "min_segment_px": MIN_SEGMENT_PX,
                "max_segments_per_case": config.AI_MAX_SEGMENTS_PER_CASE},
        "geometry_sha256": geometry_hash(cases),
    }


def geometry_hash(cases: list) -> str:
    """A hash of the candidates themselves: every segment's pixels, in order.
    The decision file carries it, and the pipeline refuses to apply a decision
    file whose candidates are not the ones it just computed, so a verdict can
    never land on a segment it was not given for."""
    parts = []
    for case in cases:
        parts.append([case["lacuna_id"], case["zone"]["empty_width_px"],
                      case["zone"]["contrast_ratio"],
                      [[seg["n"], (seg["rows"].astype(np.int64) * 100000
                                   + seg["cols"].astype(np.int64)).tolist()]
                       for seg in case["segments"]]])
    return sha256_text(canonical_json(parts))


# The state the candidates are made from

def pipeline_state(image_path: Path) -> dict:
    """Run one image through the pipeline and keep what the candidates need.

    The switch is forced OFF while this runs: the candidates are made against
    the pipeline as it is, never against a pipeline the judge has already
    changed, which would be circular. The module-override idiom is the one the
    sweep diagnostics use.
    """
    saved = config.AI_JUDGE_ENABLED
    config.AI_JUDGE_ENABLED = False
    try:
        lac = lacunae.analyse_image(image_path)
        display, channel = lacunae.load_channel(image_path)
        net = canaliculi.analyse_network(image_path, lac, channel)
    finally:
        config.AI_JUDGE_ENABLED = saved
    return {
        "image_path": image_path,
        "label": lacunae.image_label(image_path),
        "shape": tuple(net["lacuna_id_map"].shape),
        "channel": channel,
        "display": display,
        "lacuna_id_map": net["lacuna_id_map"],
        "lacuna_mask": net["lacuna_mask"],
        "n_lacunae": len(lac["kept"]),
        "response": net["ridge_response"],
        "high_cut": float(net["t_lo"]),
        "flagged": net["flagged"],
        # The global cut: the mask and the skeleton the ridge threshold and the
        # glow zone rule produced, before the dim pass and before the 50 um
        # prune. Step 1 of the experiment measures and traces against these.
        "candidate_global": net["candidate_first_pass"],
        "skeleton_global": net["skeleton_first_pass"],
        "skeleton_final": net["skeleton"],
        "owner_map": net["owner_map"],
    }


def state_from_pipeline(net: dict, lacuna_id_map: np.ndarray, lacuna_mask: np.ndarray,
                        n_lacunae: int) -> dict:
    """The same state, assembled inside canaliculi.analyse_network, where the
    arrays are already in hand. Used by the switch so that the pipeline never
    runs the pipeline again."""
    return {
        "shape": tuple(lacuna_id_map.shape),
        "lacuna_id_map": lacuna_id_map,
        "lacuna_mask": lacuna_mask,
        "n_lacunae": n_lacunae,
        "response": net["response"],
        "high_cut": float(net["high_cut"]),
        "flagged": net["flagged"],
        "candidate_global": net["candidate_global"],
        "skeleton_global": net["skeleton_global"],
    }


# The picture the judge sees (step 2)

def crop_window(shape: tuple, centre_xy: list, size: int) -> tuple:
    """A square window of `size` px of image data around a point, pushed inside
    the frame if the point is near an edge."""
    cx, cy = float(centre_xy[0]), float(centre_xy[1])
    half = size // 2
    r_lo = int(round(cy)) - half
    c_lo = int(round(cx)) - half
    r_lo = max(0, min(r_lo, shape[0] - size)) if shape[0] >= size else 0
    c_lo = max(0, min(c_lo, shape[1] - size)) if shape[1] >= size else 0
    return r_lo, min(r_lo + size, shape[0]), c_lo, min(c_lo + size, shape[1])


def stretch_to_gray(channel_crop: np.ndarray, bodies_crop: np.ndarray) -> np.ndarray:
    """The raw crop as 8 bit grey, stretched between the percentiles of
    config.AI_CROP_WINDOW_PERCENTILES taken OUTSIDE the cell bodies.

    With the bodies in, a bright osteocyte takes the top of the window and the
    faint threads the judge is asked about go black. A display stretch only: it
    changes nothing that is measured, and both panels use the same one."""
    pool = channel_crop[~bodies_crop] if (~bodies_crop).any() else channel_crop
    lo = float(np.percentile(pool, config.AI_CROP_WINDOW_PERCENTILES[0]))
    hi = float(np.percentile(pool, config.AI_CROP_WINDOW_PERCENTILES[1]))
    if not hi > lo:
        lo, hi = float(channel_crop.min()), float(channel_crop.max())
    if not hi > lo:
        hi = lo + 1e-6
    scaled = np.clip((channel_crop - lo) / (hi - lo), 0.0, 1.0)
    return (scaled * 255.0 + 0.5).astype(np.uint8)


def _enlarge(image: np.ndarray, factor: int) -> np.ndarray:
    """Whole-pixel enlargement: every pixel becomes a factor x factor block.
    Nothing is interpolated, so no structure is invented."""
    return np.repeat(np.repeat(image, factor, axis=0), factor, axis=1)


def _draw_digits(canvas: np.ndarray, text: str, row: int, col: int) -> None:
    """Draw `text` with its top left corner at (row, col), in NUMBER_COLOUR with
    a one pixel NUMBER_HALO around every glyph pixel so it reads on any
    background. Clipped at the canvas edge."""
    scale = DIGIT_SCALE
    height, width = canvas.shape[:2]
    for position, character in enumerate(text):
        glyph = DIGIT_GLYPHS.get(character)
        if glyph is None:
            continue
        base_c = col + position * (len(glyph[0]) + 1) * scale
        for gr, line in enumerate(glyph):
            for gc, pixel in enumerate(line):
                if pixel != "#":
                    continue
                r0 = row + gr * scale
                c0 = base_c + gc * scale
                r1, c1 = r0 + scale, c0 + scale
                if r1 <= 0 or c1 <= 0 or r0 >= height or c0 >= width:
                    continue
                halo = canvas[max(0, r0 - 1):min(height, r1 + 1),
                              max(0, c0 - 1):min(width, c1 + 1)]
                halo[...] = NUMBER_HALO
        for gr, line in enumerate(glyph):
            for gc, pixel in enumerate(line):
                if pixel != "#":
                    continue
                r0 = row + gr * scale
                c0 = base_c + gc * scale
                block = canvas[max(0, r0):min(height, r0 + scale),
                               max(0, c0):min(width, c0 + scale)]
                block[...] = NUMBER_COLOUR


def _text_box(text: str) -> tuple:
    """(height, width) of a drawn number, in rendered px."""
    glyph_rows, glyph_cols = 7, 5
    width = len(text) * (glyph_cols + 1) * DIGIT_SCALE - DIGIT_SCALE
    return glyph_rows * DIGIT_SCALE, width


def _place_label(canvas: np.ndarray, taken: list, text: str, row: int, col: int,
                 step: int) -> tuple:
    """Where to draw one number: the first place around its segment that is
    inside the picture, does not land on another number and does not land on a
    red segment. The numbers are the only names the segments have, so two of
    them on top of each other is an unreadable case and not a cosmetic fault.

    The order of the offsets is fixed, so the same case always gets the same
    layout."""
    height, width = canvas.shape[:2]
    box_h, box_w = _text_box(text)
    offsets = []
    for distance in (1, 2, 3):
        reach = distance * step
        offsets += [(-box_h - reach, reach), (-box_h - reach, -box_w - reach),
                    (reach, reach), (reach, -box_w - reach),
                    (-box_h // 2, box_w // 2 + reach), (-box_h // 2, -box_w - reach),
                    (-box_h - reach, -box_w // 2), (reach, -box_w // 2)]
    best = None
    for d_row, d_col in offsets:
        r0 = min(max(0, row + d_row), height - box_h - 1)
        c0 = min(max(0, col + d_col), width - box_w - 1)
        box = (r0, c0, r0 + box_h, c0 + box_w)
        if best is None:
            best = box
        if any(not (box[2] < other[0] or box[0] > other[2]
                    or box[3] < other[1] or box[1] > other[3]) for other in taken):
            continue
        patch = canvas[box[0]:box[2], box[1]:box[3]]
        if patch.size and bool((patch == np.array(SEGMENT_COLOUR, dtype=np.uint8))
                               .all(axis=-1).any()):
            continue
        best = box
        break
    taken.append(best)
    return best[0], best[1]


def case_colours(state: dict, case: dict, window: tuple) -> dict:
    """Which cell body is outlined in which colour: the body the case is about
    is yellow, the other bodies with pixels in the crop take the remaining
    colours by increasing lacuna id. Returns {colour name: lacuna id} plus the
    ids that got no name."""
    r_lo, r_hi, c_lo, c_hi = window
    ids = np.unique(state["lacuna_id_map"][r_lo:r_hi, c_lo:c_hi])
    others = [int(i) for i in ids if i > 0 and int(i) != case["lacuna_id"]]
    others.sort()
    colours = {OWNER_COLOURS[0][0]: case["lacuna_id"]}
    spare = [name for name, _rgb in OWNER_COLOURS[1:]]
    for name, lacuna_id in zip(spare, others):
        colours[name] = lacuna_id
    return {"colours": colours, "unnameable": others[len(spare):]}


def case_picture(state: dict, candidates: dict, case: dict) -> tuple:
    """The two panels, as png bytes, and what was drawn on them.

    Left: the raw crop, stretched and enlarged, nothing drawn. Right: the same,
    with every body outlined in its colour and every candidate segment drawn in
    red with its number beside it."""
    size = int(config.AI_CROP_PX)
    window = crop_window(state["shape"], case["zone"]["centroid_xy"], size)
    r_lo, r_hi, c_lo, c_hi = window
    factor = max(1, int(round(config.AI_CROP_RENDER_PX / max(1, (r_hi - r_lo)))))

    id_crop = state["lacuna_id_map"][r_lo:r_hi, c_lo:c_hi]
    gray = stretch_to_gray(state["channel"][r_lo:r_hi, c_lo:c_hi], id_crop > 0)
    panel = _enlarge(np.stack([gray] * 3, axis=-1), factor)
    right = panel.copy()

    named = case_colours(state, case, window)
    rgb_of = dict(OWNER_COLOURS)
    for name, lacuna_id in named["colours"].items():
        outline = segmentation.find_boundaries(id_crop == lacuna_id, mode="outer")
        right[_enlarge(outline, factor)] = rgb_of[name]
    for lacuna_id in named["unnameable"]:
        outline = segmentation.find_boundaries(id_crop == lacuna_id, mode="outer")
        right[_enlarge(outline, factor)] = UNNAMEABLE_COLOUR

    drawn = []
    for seg in case["segments"]:
        inside = ((seg["rows"] >= r_lo) & (seg["rows"] < r_hi)
                  & (seg["cols"] >= c_lo) & (seg["cols"] < c_hi))
        if not inside.any():
            continue
        rows = (seg["rows"][inside] - r_lo) * factor
        cols = (seg["cols"][inside] - c_lo) * factor
        for dr in range(factor):
            for dc in range(factor):
                right[rows + dr, cols + dc] = SEGMENT_COLOUR
        drawn.append({"n": seg["n"], "px_in_crop": int(inside.sum()),
                      "row": int(rows.min()), "col": int(cols[np.argmin(rows)])})
    taken: list = []
    for item in drawn:
        row, col = _place_label(right, taken, str(item["n"]), item["row"], item["col"], factor)
        _draw_digits(right, str(item["n"]), row, col)

    gap = np.full((panel.shape[0], PANEL_GAP_PX, 3), PANEL_GAP_COLOUR, dtype=np.uint8)
    canvas = np.concatenate([panel, gap, right], axis=1)
    buffer = io.BytesIO()
    Image.fromarray(canvas).save(buffer, format="PNG")
    png = buffer.getvalue()
    return png, {
        "window_rows": [int(r_lo), int(r_hi)],
        "window_cols": [int(c_lo), int(c_hi)],
        "enlargement": int(factor),
        "panel_px": [int(canvas.shape[1]), int(canvas.shape[0])],
        "colours": named["colours"],
        "bodies_with_no_colour": named["unnameable"],
        "segments_drawn": [item["n"] for item in drawn],
    }


# The prompt, the request and its hash

def load_prompt() -> dict:
    """The one fixed prompt, with Karim's examples appended. Both files are
    stripped of their html comments, and both hashes go into every log record,
    so a changed prompt is visible in the log for ever after."""
    prompt_path = Path(__file__).resolve().parent / "judge_prompt.md"
    examples_path = config.PROJECT_ROOT / "docs" / "judge_examples.md"
    prompt = strip_comments(prompt_path.read_text(encoding="utf-8"))
    examples_raw = examples_path.read_text(encoding="utf-8") if examples_path.exists() else ""
    examples = strip_comments(examples_raw)
    system = prompt if not examples else prompt + "\n\nWORKED EXAMPLES\n\n" + examples
    return {
        "system": system,
        "prompt_sha256": sha256_text(prompt),
        "examples_sha256": sha256_text(examples),
        "examples_present": bool(examples),
    }


def case_user_text(case: dict, drawn: dict) -> str:
    """The only text that changes from case to case. It carries no file name, no
    path and no group: the numbers in the picture and the colours that are in
    it, and nothing else."""
    names = [name for name, _rgb in OWNER_COLOURS if name in drawn["colours"]]
    numbers = drawn["segments_drawn"]
    listed = ", ".join(str(n) for n in numbers) if numbers else "none"
    extra = ""
    if drawn["bodies_with_no_colour"]:
        extra = (" One or more further bodies are outlined in grey; a segment that belongs to"
                 " a grey body has no colour to name, so answer owner \"none\" for it.")
    return (f"This case has {len(numbers)} candidate segment(s), numbered: {listed}. "
            f"The bodies outlined are: {', '.join(names)}, with yellow in the middle."
            f"{extra} Answer for every number, in one json object.")


def build_request(system: str, user_text: str, png: bytes) -> tuple:
    """(payload to send, the canonical record of it, its hash).

    The canonical record holds the image's hash and size instead of its bytes,
    so a log record stays small and readable while still pinning down exactly
    what was sent: the picture itself is written beside it."""
    payload = {
        "model": config.AI_JUDGE_MODEL,
        "max_tokens": int(config.AI_JUDGE_MAX_TOKENS),
        "system": system,
        "messages": [{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                         "data": base64.standard_b64encode(png).decode("ascii")}},
            {"type": "text", "text": user_text},
        ]}],
    }
    # Temperature is SENT only to a model that accepts it. The pinned model
    # rejects any non-default sampling value with HTTP 400, so for it the
    # request carries none and the record says so instead of pretending.
    if config.AI_JUDGE_MODEL in config.AI_MODELS_ACCEPTING_TEMPERATURE:
        payload["temperature"] = float(config.AI_JUDGE_TEMPERATURE)
        temperature_note = float(config.AI_JUDGE_TEMPERATURE)
    else:
        temperature_note = (f"not sent: {config.AI_JUDGE_MODEL} rejects a non-default "
                            f"temperature with HTTP 400")
    if config.AI_JUDGE_THINKING_OFF:
        payload["thinking"] = {"type": "between_tools"}
    canonical = {
        "model": payload["model"],
        "max_tokens": payload["max_tokens"],
        "temperature": temperature_note,
        "thinking": payload.get("thinking", "model default"),
        "system_sha256": sha256_text(system),
        "user_text": user_text,
        "image": {"media_type": "image/png", "sha256": sha256_bytes(png), "bytes": len(png)},
    }
    return payload, canonical, sha256_text(canonical_json(canonical))


# The call itself. The only place in this repository that talks to a network.

def external_calls_allowed() -> tuple:
    """(allowed, why not). Two independent gates, both required: the approval
    flag in the environment and a key. Neither is ever written to a file and
    the key is never printed."""
    if os.environ.get("ALLOW_EXTERNAL_API") != "1":
        return False, "ALLOW_EXTERNAL_API is not set to 1"
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False, "ANTHROPIC_API_KEY is not set"
    if config.AI_JUDGE_PROVIDER != "anthropic":
        return False, f"provider {config.AI_JUDGE_PROVIDER!r} is not implemented"
    return True, ""


def call_anthropic(payload: dict) -> dict:
    """One request to the Messages API through the official SDK. Returns the
    answer text, the token counts and what was actually sent.

    The SDK is imported here and nowhere else, so the pipeline, the dry run and
    the replay all work without it installed."""
    import anthropic  # noqa: PLC0415 (deliberate: see the docstring)

    client = anthropic.Anthropic()
    sent = dict(payload)
    thinking_fallback = False
    try:
        message = client.messages.create(**sent)
    except anthropic.BadRequestError as error:
        # The one negotiation this code does: if the pinned model refuses the
        # thinking setting, it is dropped once and the log records that the
        # request went out at the model's default instead.
        if "thinking" not in sent or "thinking" not in str(error).lower():
            raise
        sent.pop("thinking")
        thinking_fallback = True
        message = client.messages.create(**sent)
    text = "".join(block.text for block in message.content if block.type == "text")
    usage = message.usage
    return {
        "text": text,
        "id": getattr(message, "id", None),
        "model": getattr(message, "model", None),
        "stop_reason": getattr(message, "stop_reason", None),
        "thinking_fallback": thinking_fallback,
        "usage": {"input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
                  "output_tokens": int(getattr(usage, "output_tokens", 0) or 0)},
    }


def count_tokens(payload: dict) -> int:
    """The exact input token count of a request, from the API's own counter.
    Free, but still a network call, so it runs only when external calls are
    allowed and only when a dry run is asked for it."""
    import anthropic  # noqa: PLC0415

    client = anthropic.Anthropic()
    fields = {"model": payload["model"], "system": payload["system"],
              "messages": payload["messages"]}
    return int(client.messages.count_tokens(**fields).input_tokens)


def stub_answerer():
    """A stand-in judge for the self-test: no network, no key, no cost.

    It answers from the picture's own numbers with a fixed rule, odd numbers
    real and even numbers artifact, which is meaningless biologically and is
    meant to be: what the self-test checks is the machinery, that a picture
    becomes a request, an answer becomes verdicts, a log becomes the same
    verdicts again on replay, and that the switch then edits the mask. It
    deliberately returns unreadable json on some calls, so that the retry and
    the unjudged path are exercised too: every third case is broken once and
    recovers, every seventh is broken twice and stays unjudged.

    Returns a fresh callable with its own counter, so a self-test run is the
    same every time."""
    seen: dict = {}

    def answer(payload: dict) -> dict:
        text = payload["messages"][0]["content"][1]["text"]
        numbers = [int(n) for n in re.findall(r"\d+", text.split("numbered:")[1].split(".")[0])] \
            if "numbered:" in text else []
        colours = [name for name, _rgb in OWNER_COLOURS if name in text]
        key = text[:80]
        index = seen.setdefault(key, len(seen) + 1)
        attempts = seen[("tries", key)] = seen.get(("tries", key), 0) + 1
        broken = (index % 7 == 0) or (index % 3 == 0 and attempts == 1)
        if broken:
            body = "I looked at the picture and here is what I think, in prose."
        else:
            owner = colours[0] if colours else "none"
            body = json.dumps({"segments": [
                {"n": n, "verdict": "real" if n % 2 else "artifact",
                 "owner": owner if n % 2 else "none",
                 "why": "self-test, no judgement was made"} for n in numbers]})
        return {
            "text": body,
            "id": f"self-test-{index:04d}-{attempts}",
            "model": f"{config.AI_JUDGE_MODEL} (NOT CALLED: self-test stub)",
            "stop_reason": "end_turn",
            "thinking_fallback": False,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }

    return answer


def cost_usd(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * config.AI_PRICE_INPUT_USD_PER_MTOK / 1e6
            + output_tokens * config.AI_PRICE_OUTPUT_USD_PER_MTOK / 1e6)


# Reading the answer

VERDICTS = ("real", "artifact")


def parse_answer(text: str, numbers: list, colours: dict) -> tuple:
    """(answer, why it was refused). Strict: the json must name every number in
    the picture exactly once, name no other, and use only the words the prompt
    allows. Anything else is refused whole, because a half-read answer is a
    judgement nobody made."""
    if not text or not text.strip():
        return None, "the answer was empty"
    body = text.strip()
    if body.startswith("```"):
        body = re.sub(r"^```[a-zA-Z]*\s*", "", body)
        body = re.sub(r"\s*```$", "", body)
    start, end = body.find("{"), body.rfind("}")
    if start < 0 or end <= start:
        return None, "no json object in the answer"
    try:
        parsed = json.loads(body[start:end + 1])
    except json.JSONDecodeError as error:
        return None, f"the json did not parse: {error.msg}"
    if not isinstance(parsed, dict) or not isinstance(parsed.get("segments"), list):
        return None, "no segments list"
    allowed_owners = set(colours) | {"none"}
    seen = {}
    for item in parsed["segments"]:
        if not isinstance(item, dict):
            return None, "a segment entry is not an object"
        try:
            number = int(item.get("n"))
        except (TypeError, ValueError):
            return None, "a segment entry has no number"
        if number in seen:
            return None, f"segment {number} answered twice"
        if number not in numbers:
            return None, f"segment {number} is not in the picture"
        verdict = str(item.get("verdict", "")).strip().lower()
        if verdict not in VERDICTS:
            return None, f"segment {number} has verdict {item.get('verdict')!r}"
        owner = str(item.get("owner", "none")).strip().lower()
        if owner not in allowed_owners:
            return None, f"segment {number} has owner {item.get('owner')!r}"
        if verdict == "artifact":
            owner = "none"
        why = str(item.get("why", "")).strip()
        seen[number] = {"n": number, "verdict": verdict, "owner": owner,
                        "owner_lacuna_id": colours.get(owner), "why": why[:300]}
    missing = [n for n in numbers if n not in seen]
    if missing:
        return None, f"no answer for segment(s) {missing}"
    return [seen[n] for n in numbers], ""


# The log, and the replay that reads it back

# The log lives in results/ai_log/. LOG_ROOT replaces that for one process, the
# module-override idiom the sweep diagnostics use: the self-test sets it so that
# a rehearsal with a stub judge can never leave verdicts in results/ for the
# pipeline to pick up.
LOG_ROOT = None


def log_root() -> Path:
    return Path(LOG_ROOT) if LOG_ROOT else config.RESULTS_DIR / config.AI_LOG_DIR


def log_dir(label: str) -> Path:
    return log_root() / label


def log_path(label: str, case_id: str, attempt: int) -> Path:
    return log_dir(label) / f"{case_id}_attempt{attempt}.json"


def picture_path(label: str, case_id: str) -> Path:
    return log_dir(label) / "pictures" / f"{case_id}.png"


def decisions_path(label: str) -> Path:
    return log_dir(label) / f"{label}_ai_segments.json"


def write_log(label: str, record: dict) -> Path:
    path = log_path(label, record["case_id"], record["attempt"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return path


def read_log(label: str, case_id: str, attempt: int) -> dict | None:
    path = log_path(label, case_id, attempt)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


# One image, judged (step 2) or replayed

def judge_image(state: dict, candidates: dict, mode: str, out_root: Path | None = None,
                budget_usd: float | None = None, progress=None, answerer=None) -> dict:
    """Judge every case of one image, or replay every case from the log.

    mode "live"   one call per case, retried once if the answer does not
                  validate, every attempt logged.
    mode "replay" no network at all: the attempts are read back from the log,
                  the request is rebuilt and its hash compared with the logged
                  one, and the logged answer goes through the same parser, so
                  the verdicts are reproduced and not copied.

    `answerer` replaces the call for one run, which is how the self-test
    rehearses the whole chain with no network and no key. The real call is the
    default and nothing else ever passes this.

    The cost ceiling is checked before the first call and again after every
    answer; passing it stops the run where it is and says so.
    """
    label = state["label"]
    prompt = load_prompt()
    budget = float(config.MAX_COST_USD if budget_usd is None else budget_usd)
    out_root = Path(out_root) if out_root is not None else log_dir(label)
    out_root.mkdir(parents=True, exist_ok=True)

    totals = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
              "cases": 0, "cases_valid": 0, "cases_unjudged": 0, "attempts": 0,
              "invalid_attempts": 0, "segments": 0, "segments_real": 0,
              "segments_artifact": 0, "segments_unjudged": 0, "stopped_on_cost": False}
    out_cases = []
    for case in candidates["cases"]:
        totals["cases"] += 1
        png, drawn = case_picture(state, candidates, case)
        picture = picture_path(label, case["case_id"])
        picture.parent.mkdir(parents=True, exist_ok=True)
        if mode != "replay":
            picture.write_bytes(png)
        numbers = drawn["segments_drawn"]
        record_case = {
            "lacuna_id": case["lacuna_id"],
            "case_id": case["case_id"],
            "empty_width_px": case["zone"]["empty_width_px"],
            "contrast_ratio": case["zone"]["contrast_ratio"],
            "zone_px": case["zone"]["own_zone_px"],
            "segments_offered": case["segments_offered"],
            "segments_not_offered": case["segments_not_offered"],
            "picture": picture.relative_to(config.PROJECT_ROOT).as_posix(),
            "colours": drawn["colours"],
            "bodies_with_no_colour": drawn["bodies_with_no_colour"],
            "answer_valid": False,
            "attempts": 0,
            "invalid_reasons": [],
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "cost_usd": 0.0,
            "segments": [{"n": seg["n"], "px": seg["px"], "length_um": seg["length_um"],
                          "already_traced": seg["already_traced"],
                          "verdict": "unjudged", "owner": "none", "owner_lacuna_id": None,
                          "why": ""} for seg in case["segments"]],
        }
        # A segment whose pixels all fall outside the crop cannot be drawn, so
        # it is never asked about and stays unjudged. It is counted here and in
        # the dry run, because a question not asked is a blind spot and not a
        # neutral outcome.
        record_case["segments_not_drawn"] = len(case["segments"]) - len(numbers)
        if not numbers:
            for seg in record_case["segments"]:
                totals["segments"] += 1
                totals["segments_unjudged"] += 1
            out_cases.append(record_case)
            continue

        user_text = case_user_text(case, drawn)
        payload, canonical, request_sha = build_request(prompt["system"], user_text, png)
        answer = None
        for attempt in (1, 2):
            if totals["cost_usd"] >= budget:
                totals["stopped_on_cost"] = True
                break
            record = {
                "schema": LOG_SCHEMA,
                "written_at": utc_now(),
                "mode": mode,
                "image_label": label,
                "lacuna_id": case["lacuna_id"],
                "case_id": case["case_id"],
                "attempt": attempt,
                "picture": picture.relative_to(config.PROJECT_ROOT).as_posix(),
                "picture_sha256": sha256_bytes(png),
                "prompt_sha256": prompt["prompt_sha256"],
                "examples_sha256": prompt["examples_sha256"],
                "request_sha256": request_sha,
                "request": canonical,
            }
            if mode == "replay":
                logged = read_log(label, case["case_id"], attempt)
                if logged is None:
                    record_case["invalid_reasons"].append(f"attempt {attempt}: no log record")
                    break
                record["replay_of"] = {
                    "written_at": logged.get("written_at"),
                    "request_sha256": logged.get("request_sha256"),
                    "request_matches": logged.get("request_sha256") == request_sha,
                    "picture_matches": logged.get("picture_sha256") == sha256_bytes(png),
                }
                response = logged.get("response") or {}
                record["response"] = response
                record["cost_usd"] = float(logged.get("cost_usd", 0.0))
            else:
                if answerer is None:
                    allowed, why = external_calls_allowed()
                    if not allowed:
                        raise RuntimeError(f"a real call was asked for but {why}")
                response = (answerer or call_anthropic)(payload)
                record["response"] = response
                record["cost_usd"] = round(cost_usd(response["usage"]["input_tokens"],
                                                    response["usage"]["output_tokens"]), 6)
                totals["calls"] += 1
                totals["input_tokens"] += response["usage"]["input_tokens"]
                totals["output_tokens"] += response["usage"]["output_tokens"]
                totals["cost_usd"] = round(totals["cost_usd"] + record["cost_usd"], 6)
                record_case["usage"]["input_tokens"] += response["usage"]["input_tokens"]
                record_case["usage"]["output_tokens"] += response["usage"]["output_tokens"]
                record_case["cost_usd"] = round(record_case["cost_usd"] + record["cost_usd"], 6)
            totals["attempts"] += 1
            record_case["attempts"] = attempt
            parsed, why_not = parse_answer(response.get("text", ""), numbers,
                                           drawn["colours"])
            record["valid"] = parsed is not None
            record["invalid_reason"] = why_not or None
            record["parsed"] = parsed
            if mode != "replay":
                write_log(label, record)
            if parsed is None:
                totals["invalid_attempts"] += 1
                record_case["invalid_reasons"].append(f"attempt {attempt}: {why_not}")
                continue
            answer = parsed
            break

        if answer is not None:
            record_case["answer_valid"] = True
            totals["cases_valid"] += 1
            by_number = {item["n"]: item for item in answer}
            for seg in record_case["segments"]:
                item = by_number.get(seg["n"])
                if item is None:
                    continue
                seg.update({"verdict": item["verdict"], "owner": item["owner"],
                            "owner_lacuna_id": item["owner_lacuna_id"], "why": item["why"]})
        else:
            totals["cases_unjudged"] += 1
        for seg in record_case["segments"]:
            totals["segments"] += 1
            totals[f"segments_{seg['verdict']}"] += 1
        out_cases.append(record_case)
        if progress is not None:
            progress(record_case, totals)
        if totals["stopped_on_cost"]:
            break

    decisions = {
        "schema": DECISIONS_SCHEMA,
        "status": ("EXPERIMENT. Verdicts by an AI judge, not by the pipeline. "
                   "Applied only when config.AI_JUDGE_ENABLED is True."),
        "written_at": utc_now(),
        "mode": mode,
        "image_label": label,
        "provider": config.AI_JUDGE_PROVIDER,
        "model": config.AI_JUDGE_MODEL,
        "prompt_sha256": prompt["prompt_sha256"],
        "examples_sha256": prompt["examples_sha256"],
        "examples_present": prompt["examples_present"],
        "candidate_rule": candidates["cut"],
        "geometry_sha256": candidates["geometry_sha256"],
        "totals": totals,
        "cases": out_cases,
    }
    (out_root / f"{label}_ai_segments.json").write_text(
        json.dumps(decisions, indent=2) + "\n", encoding="utf-8")
    return decisions


# The assembly (step 3): what the pipeline does with the verdicts

def read_decisions(label: str) -> dict:
    path = decisions_path(label)
    if not path.exists():
        raise FileNotFoundError(
            f"config.AI_JUDGE_ENABLED is on but there is no judge decision file for {label} "
            f"at {path}. Run the judge for this image, or turn the switch off. A run with the "
            f"switch on must not mix judged and unjudged images in one summary.")
    return json.loads(path.read_text(encoding="utf-8"))


def apply_to_candidate(image_path: Path, candidate: np.ndarray, net: dict,
                       lacuna_id_map: np.ndarray, lacuna_mask: np.ndarray,
                       n_lacunae: int) -> dict:
    """The switch. Returns the edited candidate mask, the pixels the judge took
    away, and where it says ownership belongs.

    The edit is the smallest one that can express the verdicts:
      a segment judged REAL adds the mask its centre line is the centre line
      of, inside its zone;
      a segment judged ARTIFACT takes that mask away;
      everything else, including a segment with no valid answer and a segment
      that was never offered, is left exactly as the pipeline had it.
    So with no verdicts at all the mask comes back unchanged, and the switch
    changes a number only where the judge actually answered.

    The owner the judge names is not written anywhere by hand: it becomes a zero
    weight attachment from that cell to the nearest node of the segment, the
    same zero weight the contact rule uses, and the pipeline's own ownership
    then decides everything else (canaliculi.attach_judged_segments)."""
    label = lacunae.image_label(image_path)
    decisions = read_decisions(label)
    state = state_from_pipeline(net, lacuna_id_map, lacuna_mask, n_lacunae)
    candidates = image_candidates(state)
    if decisions["geometry_sha256"] != candidates["geometry_sha256"]:
        raise ValueError(
            f"the judge decision file for {label} was written for different candidates "
            f"(geometry {decisions['geometry_sha256'][:12]}, now "
            f"{candidates['geometry_sha256'][:12]}). Rerun the judge for this image.")

    by_case = {case["lacuna_id"]: case for case in decisions["cases"]}
    territory = candidates["territory"]
    add = np.zeros(candidate.shape, dtype=bool)
    remove = np.zeros(candidate.shape, dtype=bool)
    attach: dict = {}
    counts = {"real": 0, "artifact": 0, "unjudged": 0, "added_px": 0, "removed_px": 0,
              "attached_segments": 0}
    for case in candidates["cases"]:
        judged = by_case.get(case["lacuna_id"])
        if judged is None:
            counts["unjudged"] += len(case["segments"])
            continue
        verdicts = {item["n"]: item for item in judged["segments"]}
        for seg in case["segments"]:
            item = verdicts.get(seg["n"])
            verdict = (item or {}).get("verdict", "unjudged")
            counts[verdict] = counts.get(verdict, 0) + 1
            if verdict == "real":
                add |= territory == seg["label"]
                owner = item.get("owner_lacuna_id")
                if owner:
                    attach.setdefault(int(owner), []).append(
                        np.stack([seg["rows"], seg["cols"]], axis=1))
                    counts["attached_segments"] += 1
            elif verdict == "artifact":
                remove |= territory == seg["label"]
    counts["added_px"] = int((add & ~candidate).sum())
    counts["removed_px"] = int((remove & candidate).sum())
    # The invariant of step 1, measured where it is made: the judge's own edit
    # touches no pixel outside the empty zones. What the dim pass does outside
    # them afterwards is the pipeline reacting to the ownership it was given,
    # and is reported as the dim pass, not as the judge.
    counts["edited_px_outside_the_zones"] = int(((add | remove)
                                                 & (candidates["zone_owner"] == 0)).sum())
    edited = (candidate | add) & ~remove
    return {
        "candidate": edited,
        "add": add,
        "remove": remove,
        "zone_owner": candidates["zone_owner"],
        "attach": attach,
        "counts": counts,
        "geometry_sha256": candidates["geometry_sha256"],
        "decisions_written_at": decisions["written_at"],
        "model": decisions["model"],
        "zone_px": int((candidates["zone_owner"] > 0).sum()),
    }


# The estimate a dry run prints, and the gate it feeds

def estimate_case(system: str, user_text: str, png: bytes, segments: int) -> dict:
    """What one case is expected to cost, with no network. Text at
    config.AI_TOKENS_PER_CHAR tokens per character and the image by the
    documented width x height over config.AI_IMAGE_PIXELS_PER_TOKEN rule. An
    estimate, labelled as one everywhere it is printed."""
    with Image.open(io.BytesIO(png)) as image:
        width, height = image.size
    text_tokens = int(round((len(system) + len(user_text)) * config.AI_TOKENS_PER_CHAR))
    image_tokens = int(round(width * height / config.AI_IMAGE_PIXELS_PER_TOKEN))
    out_tokens = int(config.AI_OUTPUT_TOKENS_FIXED
                     + segments * config.AI_OUTPUT_TOKENS_PER_SEGMENT)
    return {
        "input_tokens": text_tokens + image_tokens,
        "text_tokens": text_tokens,
        "image_tokens": image_tokens,
        "image_px": [width, height],
        "output_tokens": out_tokens,
        "cost_usd": round(cost_usd(text_tokens + image_tokens, out_tokens), 6),
    }
