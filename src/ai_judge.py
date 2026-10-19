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
# How a segment is drawn (step 2). A segment the pipeline traced and a lacuna
# owns is drawn in that lacuna's colour, so the judge sees what the tracing
# already says; one that nobody owns is WHITE; one the permissive cut found and
# the pipeline does not have is RED. Only the segments that need a decision
# carry a number.
SEGMENT_NEW_COLOUR = (255, 60, 60)
SEGMENT_UNOWNED_COLOUR = (255, 255, 255)
# A number is not placed on top of any of these.
LABEL_AVOIDS = (SEGMENT_NEW_COLOUR, SEGMENT_UNOWNED_COLOUR)
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


def scrub(text: str) -> str:
    """Never let a key reach a file. The SDK does not put the key in its error
    messages, and this makes that a guarantee rather than a belief."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key and len(key) > 8:
        text = text.replace(key, "(redacted)")
    return text


def canonical_json(obj) -> str:
    """One spelling for anything that gets hashed."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def strip_comments(text: str) -> str:
    """Drop every html comment, which is how src/judge_prompt.md and
    docs/judge_examples.md carry notes to the reader that are not sent."""
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()



# What the judge is shown (step 1)
#
# Every segment in a lacuna's crop, and the new ones the zone of the hole
# proposes. A segment is a BRANCH of a skeleton, the piece between two
# junctions, which is the same split the candidates used from the start.
#
# Three KINDS, by what the pipeline has:
#   owned    traced by the pipeline and owned by a lacuna
#   unowned  traced and owned by nobody
#   new      not traced at all: what the permissive cut inside the zone of the
#            hole finds beyond the mask the pipeline kept
#
# and four CLASSES, which are the cases the judge is actually asked about:
#   a  an unowned segment
#   b  a new segment from the permissive cut inside the zone of the hole
#   c  a segment that touches a body that does not own it
#   d  a segment owned by a lacuna that is NOT the nearest lacuna to it by
#      straight distance, where that nearest lacuna is within REACH of it
#
# A segment is NUMBERED, which is what asks the judge for a decision, exactly
# when it falls in one of those four classes. A segment in none of them needs no
# decision and is drawn as context, in its owner's colour.

def reach_px(extents, lacuna_id: int) -> float:
    """How far the judge looks for one lacuna: that lacuna's OWN zone of the
    hole (the pipeline's zone, METHODS section 19) plus the minimum segment
    length, which is the floor the pipeline already applies to a thread no
    lacuna owns. Nothing new is defined here.

    A lacuna is a CANDIDATE for a segment when its body lies within this reach
    of the segment, and that one test decides class d, which candidates a
    numbered segment is offered, and which unowned segments are asked about at
    all. An unowned segment with no lacuna within reach is left to the pipeline:
    no body in the picture could be named as its owner, so the only answer it
    could be given is the one the pipeline already has."""
    return float(extents[lacuna_id]) + MIN_SEGMENT_PX

def _junctions(skel: np.ndarray) -> np.ndarray:
    """Skeleton pixels with three or more skeleton neighbours. Removing them
    splits a skeleton into its branches, which is what a segment is."""
    neighbours = ndi.convolve(skel.astype(np.uint8), np.ones((3, 3), dtype=np.uint8),
                              mode="constant", cval=0) - skel
    return skel & (neighbours >= 3)


def _branch_labels(skeleton: np.ndarray) -> np.ndarray:
    """Every branch of a skeleton with its own label: the junction pixels are
    taken out, and what is left is labelled. The junctions themselves are 0 and
    act as the glue between branches, exactly as in the first version."""
    pieces = skeleton & ~_junctions(skeleton)
    return ndi.label(pieces, structure=np.ones((3, 3), dtype=np.uint8))[0]


def _majority(values: np.ndarray) -> int:
    if values.size == 0:
        return 0
    counts = np.bincount(values[values >= 0])
    return int(np.argmax(counts)) if counts.size else 0


def body_gap_maps(state: dict) -> dict:
    """{lacuna id: (window, the straight distance from that body inside it)}.

    One distance transform per lacuna, in a window padded by as far as the judge
    ever looks from that body (`reach_px`, never less than the pipeline's
    contact reach). A pixel outside the window is further from that body than
    anything this module asks about, so it needs no number, and the window keeps
    the measurement cheap on an image of a hundred lacunae."""
    shape = state["shape"]
    lacuna_id_map = state["lacuna_id_map"]
    extents = state["zone_extents_px"]
    maps = {}
    for lacuna_id in range(1, state["n_lacunae"] + 1):
        body = lacuna_id_map == lacuna_id
        if not body.any():
            continue
        pad = max(reach_px(extents, lacuna_id), float(canaliculi.CONTACT_REACH_PX))
        window = canaliculi._body_window(body, shape, pad)
        r_lo, r_hi, c_lo, c_hi = window
        maps[lacuna_id] = (window,
                           ndi.distance_transform_edt(~body[r_lo:r_hi, c_lo:c_hi]))
    return maps


def gaps_to_bodies(gap_maps: dict, labels: np.ndarray, count: int) -> list:
    """For every labelled segment, {lacuna id: the straight gap in px from that
    segment to that body}, for every body whose window the segment reaches.

    Measured with one `ndi.minimum` per lacuna over the whole label image, so
    the cost is one pass per lacuna and not one per segment per lacuna."""
    out = [{} for _ in range(count + 1)]
    for lacuna_id, (window, gap) in gap_maps.items():
        r_lo, r_hi, c_lo, c_hi = window
        sub = labels[r_lo:r_hi, c_lo:c_hi]
        present = np.unique(sub)
        present = present[present > 0]
        if not present.size:
            continue
        for label, value in zip(present, ndi.minimum(gap, sub, index=present)):
            out[int(label)][int(lacuna_id)] = float(value)
    return out


def permissive_mask(state: dict) -> tuple:
    """(mask, what was used). The pipeline's own mask plus everything inside a
    zone of the hole that the response reaches once it is put on the footing of
    the tissue beyond the hole and the cut is lowered to
    config.AI_CANDIDATE_CUT_FRACTION of the low cut.

    The ZONE and the GAIN are the pipeline's own (METHODS section 19,
    canaliculi.hole_zone_owner and canaliculi.hole_zone_gains), not a second
    copy of them: the experiment lowers the cut inside that zone and changes
    nothing else. The pipeline's exclusions still hold, so no candidate can sit
    inside a body, in its buffer, or in a flagged vascular structure under the
    high cut."""
    response, high = state["response"], state["high_cut"]
    low = high * canaliculi.HYSTERESIS_LOW_FRACTION
    floor = low * config.AI_CANDIDATE_CUT_FRACTION
    zone_owner = state["zone_owner"]
    boosted = canaliculi.boost_in_zones(response, state["lacuna_id_map"], zone_owner,
                                        state["zone_extents_px"], state["zone_gains"])
    buffered = morphology.dilation(state["lacuna_mask"],
                                   morphology.disk(canaliculi.LACUNA_DILATION_PX))
    allowed = ~buffered & (state["lacuna_id_map"] == 0)
    if state["flagged"].any():
        allowed &= ~(state["flagged"] & (response < high))
    extra = (zone_owner > 0) & (boosted >= floor) & allowed
    return state["candidate_final"] | extra, {
        "low_cut": round(float(low), 8),
        "candidate_floor": round(float(floor), 8),
        "cut_fraction": config.AI_CANDIDATE_CUT_FRACTION,
        "zone_px": int((zone_owner > 0).sum()),
        "added_px": int((extra & ~state["candidate_final"]).sum()),
    }


def image_candidates(state: dict) -> dict:
    """Every segment the judge is shown for every lacuna, and the cases that
    hold them. Deterministic: no network and no judge.

    One pass over the image builds the segments, then each lacuna's crop picks
    up the ones it holds. A segment that needs a decision is numbered in the
    case whose crop holds it and whose lacuna it concerns; a segment that
    touches two bodies is numbered in both of their cases, and if the two
    answers disagree the assembly leaves it alone and says so."""
    shape = state["shape"]
    skeleton = state["skeleton_final"]
    owner_map = state["owner_map"]
    zone_owner = state["zone_owner"]
    lacuna_id_map = state["lacuna_id_map"]
    n_lacunae = state["n_lacunae"]
    structure = np.ones((3, 3), dtype=np.uint8)

    permissive, cut = permissive_mask(state)
    new_skeleton = morphology.skeletonize(permissive)
    # New LINE, not new mask: a pixel of the permissive skeleton that the
    # pipeline's own skeleton does not already run along, inside a zone.
    near_traced = ndi.distance_transform_edt(~skeleton) <= 1.0
    new_lines = new_skeleton & ~near_traced & (zone_owner > 0)

    traced_labels = _branch_labels(skeleton)
    new_labels, _n_new = ndi.label(new_lines, structure=structure)
    dist_to_lacuna, nearest_id, _index = canaliculi.nearest_lacuna_map(lacuna_id_map)

    # The straight distance from every body, out to as far as the judge looks.
    # It answers three questions at once: which bodies a segment TOUCHES (the
    # pipeline's own contact reach), which lacunae are CANDIDATES for it (within
    # `reach_px`), and in what order, which is by that distance.
    gap_maps = body_gap_maps(state)
    extents = state["zone_extents_px"]

    segments = []
    for kind, labels in (("traced", traced_labels), ("new", new_labels)):
        count = int(labels.max())
        if not count:
            continue
        objects = ndi.find_objects(labels)
        gaps_by_label = gaps_to_bodies(gap_maps, labels, count)
        for index in range(1, count + 1):
            box = objects[index - 1]
            if box is None:
                continue
            piece = labels[box] == index
            rows, cols = np.nonzero(piece)
            rows = rows + box[0].start
            cols = cols + box[1].start
            if rows.size < MIN_SEGMENT_PX:
                continue
            owner = _majority(owner_map[rows, cols]) if kind == "traced" else 0
            gaps = gaps_by_label[index]
            touches = sorted(i for i, gap in gaps.items()
                             if gap <= canaliculi.CONTACT_REACH_PX)
            # Every lacuna whose body lies within its own zone of the hole plus
            # the minimum segment length of this segment: the candidates the
            # judge can be offered for it, nearest first.
            pool = sorted((i for i, gap in gaps.items() if gap <= reach_px(extents, i)),
                          key=lambda i: (gaps[i], i))
            # The nearest body by STRAIGHT distance, which is not the same
            # question as who owns it: class d is exactly where the two differ.
            nearest_at = int(np.argmin(dist_to_lacuna[rows, cols]))
            nearest = int(nearest_id[rows[nearest_at], cols[nearest_at]])
            # The zone this segment lies in, which is the lacuna whose hole it
            # is part of, and which is again not who owns it.
            zone_lacuna = _majority(zone_owner[rows, cols])
            home = zone_lacuna or owner or nearest
            seg = {
                "segment_id": f"{kind[0]}{index:05d}",
                "kind": kind if kind == "new" else ("owned" if owner else "unowned"),
                "rows": rows,
                "cols": cols,
                "px": int(rows.size),
                "length_um": round(config.um(int(rows.size)), 4),
                "owner_lacuna_id": int(owner),
                "touches": [int(i) for i in touches],
                "zone_lacuna_id": int(zone_lacuna),
                "home_lacuna_id": int(home),
                "nearest_lacuna_id": nearest,
                "nearest_gap_px": round(float(dist_to_lacuna[rows, cols].min()), 3),
                "gap_px": {int(i): round(float(gaps[i]), 3) for i in pool},
                "candidate_pool": [int(i) for i in pool],
                "label": len(segments) + 1,
            }
            seg["classes"] = segment_classes(seg)
            segments.append(seg)

    # The territory of every segment: which mask pixel belongs to which centre
    # line, so that a verdict acts on the mask its segment is the centre line of
    # and on nothing else.
    territory_seed = np.zeros(shape, dtype=np.int32)
    for seg in segments:
        territory_seed[seg["rows"], seg["cols"]] = seg["label"]
    other_lines = (skeleton | new_lines) & (territory_seed == 0)
    territory_seed[other_lines] = len(segments) + 1
    index = ndi.distance_transform_edt(territory_seed == 0, return_distances=False,
                                       return_indices=True)
    territory = np.where(permissive, territory_seed[index[0], index[1]], 0)

    cases = []
    for lacuna_id in range(1, n_lacunae + 1):
        body = lacuna_id_map == lacuna_id
        if not body.any():
            continue
        rows, cols = np.nonzero(body)
        centroid = [round(float(cols.mean()), 1), round(float(rows.mean()), 1)]
        window = crop_window(shape, centroid, int(config.AI_CROP_PX))
        cases.append(build_case(state, segments, lacuna_id, centroid, window, "lacuna"))
    cases += left_over_cases(state, segments, cases)
    number_cases(cases)

    counts = segment_counts(segments)
    asked = {entry["segment_id"] for case in cases for entry in case["decide"]}
    counts["numbered"] = len(asked)
    # The one number that says whether anything was left out: a segment in one
    # of the four classes that no case could ask about, because its candidates
    # do not fit one picture. It keeps the pipeline's own decision and is never
    # guessed at.
    counts["needs_a_decision_but_no_case_could_ask"] = sum(
        1 for seg in segments if seg["classes"] and seg["segment_id"] not in asked)
    return {
        "shape": shape,
        "segments": segments,
        "cases": cases,
        "territory": territory,
        "permissive": permissive,
        "new_lines": new_lines,
        "cut": dict(cut, min_segment_px=MIN_SEGMENT_PX,
                    max_segments_per_case=config.AI_MAX_SEGMENTS_PER_CASE,
                    crop_sizes_px=crop_sizes()),
        "counts": counts,
        "geometry_sha256": geometry_hash(cases, segments),
    }


# The four classes of the brief. A segment can fall in more than one: c sits on
# top of a or d, and a segment in two classes is asked in two cases, which is
# the one place two answers can disagree.
CLASSES = {
    "a": "an unowned segment, with at least one lacuna within reach of it",
    "b": "a new segment from the permissive cut inside the zone of the hole",
    "c": "a segment that touches a body that does not own it",
    "d": ("a segment owned by a lacuna that is not the nearest lacuna to it by straight "
          "distance, where that nearest lacuna's body lies within its own zone of the hole "
          "plus the minimum segment length"),
}


def segment_classes(seg: dict) -> list:
    """Which of the four classes a segment falls in, which is also what decides
    whether it is numbered at all.

    a and b and d are exclusive of each other by construction: a has no owner, b
    is not traced, d has an owner. c can sit on top of a or of d."""
    classes = []
    if seg["kind"] == "unowned" and seg["candidate_pool"]:
        classes.append("a")
    if seg["kind"] == "new":
        classes.append("b")
    if seg["kind"] != "new" and any(i != seg["owner_lacuna_id"] for i in seg["touches"]):
        classes.append("c")
    if (seg["kind"] == "owned" and seg["nearest_lacuna_id"]
            and seg["nearest_lacuna_id"] != seg["owner_lacuna_id"]
            and seg["nearest_lacuna_id"] in seg["candidate_pool"]):
        classes.append("d")
    return classes


def entry_candidates(seg: dict, lacuna_id: int) -> list:
    """The candidate lacunae a numbered segment is offered in ONE case, in
    order, at most two: "the first candidate, the second candidate, or none".

    Two of them can never be dropped, because without them the question has no
    sensible answer: the lacuna whose case this is, which is the body the
    segment was numbered against, and the lacuna that owns the segment now, so
    that the judge can always leave ownership where it is. Anything else comes
    from the candidate pool, nearest body first, and the two are then ordered by
    straight distance so that the FIRST candidate is always the nearer one."""
    gaps = seg["gap_px"]
    must = [i for i in (lacuna_id, seg["owner_lacuna_id"]) if i]
    order = sorted(set(must) | set(seg["candidate_pool"]),
                   key=lambda i: (gaps.get(i, float("inf")), i))
    keep = [i for i in order if i in must]
    for i in order:
        if len(keep) >= 2:
            break
        if i not in keep:
            keep.append(i)
    keep = keep[:2]
    return sorted(keep, key=lambda i: (gaps.get(i, float("inf")), i))


def segment_counts(segments: list) -> dict:
    """What the judge is shown, by kind and by class, over the whole image: for
    every class the segments, the pixels and how many lacunae are involved,
    which is what step 1 of the brief asks to be reported per image.

    A lacuna counts as involved in a class when it is a candidate for at least
    one segment of that class, so it is the number of cells whose ownership the
    class could change."""
    counts = {"owned": 0, "unowned": 0, "new": 0, "touching_two_bodies": 0,
              "needs_a_decision": 0, "in_two_classes": 0,
              "unowned_with_no_lacuna_in_reach": 0,
              "traced_in_a_zone": 0, "traced_in_a_zone_its_lacuna_does_not_own": 0,
              "traced_owned_by_another_than_the_body_it_touches": 0}
    classes = {name: {"segments": 0, "px": 0, "lacunae": set()} for name in CLASSES}
    for seg in segments:
        counts[seg["kind"]] += 1
        if len(seg["touches"]) > 1:
            counts["touching_two_bodies"] += 1
        if seg["classes"]:
            counts["needs_a_decision"] += 1
        if len(seg["classes"]) > 1:
            counts["in_two_classes"] += 1
        if seg["kind"] == "unowned" and not seg["candidate_pool"]:
            counts["unowned_with_no_lacuna_in_reach"] += 1
        for name in seg["classes"]:
            classes[name]["segments"] += 1
            classes[name]["px"] += seg["px"]
            classes[name]["lacunae"] |= set(seg["candidate_pool"])
            if seg["owner_lacuna_id"]:
                classes[name]["lacunae"].add(seg["owner_lacuna_id"])
        if seg["kind"] == "new":
            continue
        if seg["zone_lacuna_id"]:
            counts["traced_in_a_zone"] += 1
            if seg["owner_lacuna_id"] != seg["zone_lacuna_id"]:
                counts["traced_in_a_zone_its_lacuna_does_not_own"] += 1
        if any(i != seg["owner_lacuna_id"] for i in seg["touches"]):
            counts["traced_owned_by_another_than_the_body_it_touches"] += 1
    counts["classes"] = {name: {"segments": c["segments"], "px": c["px"],
                                "lacunae": len(c["lacunae"])}
                         for name, c in classes.items()}
    return counts


def asked_classes(seg: dict, lacuna_id: int) -> list:
    """Which of a segment's classes are put to the judge in the case of this
    lacuna. Each class is asked against ONE body, so that a segment is numbered
    once per body it is in question with and never twice in one picture:

      a  against the lacuna whose crop it belongs to (its zone, else the
         nearest body)
      b  the same
      c  against the body it touches that does not own it
      d  against the nearest body, the one that does not own it

    The case the brief calls two cases disagreeing is a segment asked in two of
    these at once, which is class c on top of class a or d."""
    out = []
    if "a" in seg["classes"] and seg["home_lacuna_id"] == lacuna_id:
        out.append("a")
    if "b" in seg["classes"] and seg["home_lacuna_id"] == lacuna_id:
        out.append("b")
    if ("c" in seg["classes"] and lacuna_id in seg["touches"]
            and seg["owner_lacuna_id"] != lacuna_id):
        out.append("c")
    if "d" in seg["classes"] and seg["nearest_lacuna_id"] == lacuna_id:
        out.append("d")
    return out


def build_case(state: dict, segments: list, lacuna_id: int, centroid: list, window: tuple,
               kind: str) -> dict:
    """One picture's worth: every segment with a pixel in this window, split
    into the ones that need a decision and the ones that are context.

    A segment needs a decision in this case when it falls in one of the four
    classes against THIS body (`asked_classes`), and it can only be asked here
    if the picture can name both of its candidates: a candidate body with no
    pixel in the crop, or beyond the sixth colour, has no name the judge could
    answer with, so the segment is left to a case of its own instead of being
    asked a question it cannot answer."""
    r_lo, r_hi, c_lo, c_hi = window
    named = case_colours(state, lacuna_id, window)
    nameable = set(named["colours"].values())
    decide, context, unnameable = [], [], []
    for seg in segments:
        inside = ((seg["rows"] >= r_lo) & (seg["rows"] < r_hi)
                  & (seg["cols"] >= c_lo) & (seg["cols"] < c_hi))
        if not inside.any():
            continue
        px_in_crop = int(inside.sum())
        entry = {"segment_id": seg["segment_id"], "label": seg["label"], "kind": seg["kind"],
                 "owner_lacuna_id": seg["owner_lacuna_id"], "touches": seg["touches"],
                 "px": seg["px"], "px_in_crop": px_in_crop, "length_um": seg["length_um"]}
        classes = asked_classes(seg, lacuna_id)
        if not classes:
            context.append(entry)
            continue
        candidates = entry_candidates(seg, lacuna_id)
        whole = bool(inside.all())
        if not whole or not set(candidates) <= nameable:
            # Not askable here: either the segment runs out of the picture or a
            # candidate body is not in it. Counted, drawn as context, and given
            # a case of its own by `left_over_cases`.
            unnameable.append(entry)
            context.append(entry)
            continue
        entry["classes"] = classes
        entry["candidates"] = candidates
        entry["question"] = "real and owner" if seg["kind"] == "new" else "owner"
        decide.append(entry)
    decide.sort(key=lambda s: -s["px_in_crop"])
    over = decide[int(config.AI_MAX_SEGMENTS_PER_CASE):]
    decide = decide[:int(config.AI_MAX_SEGMENTS_PER_CASE)]
    context += over
    return {
        "lacuna_id": lacuna_id,
        "kind": kind,
        "centroid_xy": centroid,
        "window": [int(r_lo), int(r_hi), int(c_lo), int(c_hi)],
        "crop_px": int(r_hi - r_lo),
        "colours": named["colours"],
        "bodies_with_no_colour": named["unnameable"],
        "decide": decide,
        "context": context,
        "segments_not_offered": len(over),
        "segments_not_askable_here": [e["segment_id"] for e in unnameable],
    }


def crop_sizes() -> list:
    """The crop sizes a case may use, smallest first: the pipeline's own crop,
    doubled until it reaches the rendered width. Every size is a whole divisor
    of the rendered width, so a picture is always enlarged by a whole number of
    pixels and nothing is ever interpolated. A bigger crop costs magnification,
    not tokens: the picture is the same size whichever is used."""
    sizes, size = [], int(config.AI_CROP_PX)
    while size <= int(config.AI_CROP_RENDER_PX):
        sizes.append(size)
        size *= 2
    return sizes


def left_over_cases(state: dict, segments: list, cases: list) -> list:
    """Step 3, now also carrying class d: the segments no lacuna case can ask
    about, each given a case of its own.

    Two things put a segment here. A zone can reach further than half a crop, so
    a segment can lie outside the crop of the lacuna it belongs to; and the two
    candidate bodies of a class d segment can be further apart than one crop, so
    the lacuna's own crop cannot show them both. Either way the segment was
    counted and left unjudged, which is a blind spot and not a neutral outcome.

    Each one now gets the SMALLEST crop that holds the segment and the bodies of
    both its candidates (`crop_sizes`), centred on all three, and any other
    left-over segment that falls inside that crop is numbered in the same call,
    so one extra call can clear several."""
    asked = {entry["segment_id"] for case in cases for entry in case["decide"]}
    # In scope: every segment that falls in one of the four classes and is not
    # asked about anywhere yet. A segment in no class is not asked about at all,
    # here or in a lacuna's case: that includes the unowned tracing with no
    # lacuna within reach, which no body in a picture could be given.
    left = [seg for seg in segments if seg["segment_id"] not in asked and seg["classes"]]
    bodies = {}
    for lacuna_id in range(1, state["n_lacunae"] + 1):
        rows, cols = np.nonzero(state["lacuna_id_map"] == lacuna_id)
        if rows.size:
            bodies[lacuna_id] = (int(rows.min()), int(rows.max()),
                                 int(cols.min()), int(cols.max()))
    extra = []
    covered: set = set()
    for seg in sorted(left, key=lambda s: (-s["px"], s["segment_id"])):
        if seg["segment_id"] in covered:
            continue
        # The case is centred on the segment and both of its candidates, and
        # takes the first crop size that holds all of them.
        against = seg["nearest_lacuna_id"] if "d" in seg["classes"] else seg["home_lacuna_id"]
        wanted = [i for i in entry_candidates(seg, against) if i in bodies]
        boxes = [(int(seg["rows"].min()), int(seg["rows"].max()),
                  int(seg["cols"].min()), int(seg["cols"].max()))]
        boxes += [bodies[i] for i in wanted]
        r_lo = min(b[0] for b in boxes)
        r_hi = max(b[1] for b in boxes)
        c_lo = min(b[2] for b in boxes)
        c_hi = max(b[3] for b in boxes)
        centroid = [round((c_lo + c_hi) / 2.0, 1), round((r_lo + r_hi) / 2.0, 1)]
        sizes = crop_sizes()
        size = next((s for s in sizes if s > r_hi - r_lo and s > c_hi - c_lo), sizes[-1])
        window = crop_window(state["shape"], centroid, size)
        case = build_case(state, segments, against, centroid, window, "left over")
        # Only the segments still left over are asked about here: everything
        # else in this crop has been asked about in its own lacuna's case, or in
        # an earlier left-over case whose crop also held it. Two left-over crops
        # overlap readily, and a segment asked twice would be two answers that
        # can disagree over nothing.
        done = asked | covered
        keep = [e for e in case["decide"] if e["segment_id"] not in done]
        case["context"] += [e for e in case["decide"] if e["segment_id"] in done]
        case["decide"] = keep
        if not keep:
            # The bodies do not fit even the largest crop, so this segment
            # cannot be shown with both its candidates. Counted, never guessed.
            continue
        covered |= {e["segment_id"] for e in keep}
        extra.append(case)
    return extra


def number_cases(cases: list) -> None:
    """Number the segments that need a decision, in reading order, so the
    numbers in a picture run roughly top to bottom. Each case numbers from 1."""
    for index, case in enumerate(cases, start=1):
        case["case_id"] = f"case_{index:04d}"
        for number, entry in enumerate(
                sorted(case["decide"], key=lambda e: (e["label"],)), start=1):
            entry["n"] = number


def geometry_hash(cases: list, segments: list) -> str:
    """A hash of what the judge is asked about: every case, every numbered
    segment and its pixels. The decision file carries it and the pipeline
    refuses to apply a decision file whose candidates are not the ones it has
    just computed, so a verdict can never land on a segment it was not given
    for."""
    by_label = {seg["label"]: seg for seg in segments}
    parts = []
    for case in cases:
        rows = []
        for entry in sorted(case["decide"], key=lambda e: e["n"]):
            seg = by_label[entry["label"]]
            rows.append([entry["n"], entry["kind"], entry["owner_lacuna_id"],
                         entry["question"], entry["classes"], entry["candidates"],
                         (seg["rows"].astype(np.int64) * 100000
                          + seg["cols"].astype(np.int64)).tolist()])
        parts.append([case["case_id"], case["lacuna_id"], case["window"], rows])
    return sha256_text(canonical_json(parts))


# The state the candidates are made from

def state_from_base(net: dict, lac: dict, image_path: Path, channel, display=None) -> dict:
    """Everything the candidates need, from a network result produced with the
    judge switch OFF. That result is the pipeline as it stands, so the judge is
    never asked about a tracing it has already changed."""
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
        # The pipeline's own zone of the hole and its radial gain (METHODS
        # section 19). The judge lowers the cut inside that zone and defines
        # nothing of its own.
        "zone_owner": net["zone_owner"],
        "zone_extents_px": net["zone_extents_px"],
        "zone_gains": net["zone_gains"],
        "hole_width_px": net["hole_width_px"],
        # What the pipeline traced and who owns it.
        "candidate_final": net["candidate"],
        "skeleton_final": net["skeleton"],
        "owner_map": net["owner_map"],
    }


def pipeline_state(image_path: Path) -> dict:
    """Run one image through the pipeline with the switch forced OFF, and keep
    what the candidates need."""
    saved = config.AI_JUDGE_ENABLED
    config.AI_JUDGE_ENABLED = False
    try:
        lac = lacunae.analyse_image(image_path)
        display, channel = lacunae.load_channel(image_path)
        net = canaliculi.analyse_network(image_path, lac, channel)
    finally:
        config.AI_JUDGE_ENABLED = saved
    return state_from_base(net, lac, image_path, channel, display)


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
        # Keep a clear gap between two numbers, not merely no overlap: a 2 drawn
        # hard against a 1 reads as 21, which names a segment that is not there.
        pad = DIGIT_SCALE * 2
        if any(not (box[2] + pad < other[0] or box[0] - pad > other[2]
                    or box[3] + pad < other[1] or box[1] - pad > other[3])
               for other in taken):
            continue
        patch = canvas[box[0]:box[2], box[1]:box[3]]
        # Never put a number on top of a segment of any kind: it would hide the
        # very thing it names.
        if patch.size and bool(any((patch == np.array(colour, dtype=np.uint8)).all(axis=-1).any()
                                   for colour in LABEL_AVOIDS)):
            continue
        best = box
        break
    taken.append(best)
    return best[0], best[1]


def case_colours(state: dict, lacuna_id: int, window) -> dict:
    """Which cell body is outlined in which colour: the body the case is about
    is yellow, the other bodies with pixels in the crop take the remaining
    colours by increasing lacuna id. Returns {colour name: lacuna id} plus the
    ids that got no name."""
    r_lo, r_hi, c_lo, c_hi = window
    ids = np.unique(state["lacuna_id_map"][r_lo:r_hi, c_lo:c_hi])
    others = sorted(int(i) for i in ids if i > 0 and int(i) != lacuna_id)
    colours = {OWNER_COLOURS[0][0]: int(lacuna_id)}
    spare = [name for name, _rgb in OWNER_COLOURS[1:]]
    for name, other in zip(spare, others):
        colours[name] = other
    return {"colours": colours, "unnameable": others[len(spare):]}


def case_picture(state: dict, candidates: dict, case: dict) -> tuple:
    """The two panels, as png bytes, and what was drawn on them.

    Left: the raw crop, stretched and enlarged, nothing drawn. Right: the same
    with every body outlined in its colour and every segment drawn:

      a segment the pipeline traced and a lacuna owns   that lacuna's colour
      a segment the pipeline traced that nobody owns    white
      a segment the permissive cut found and the
        pipeline does not have                          red

    Only the segments that need a decision carry a number. The rest are there so
    that the judge can see what the tracing already says around them."""
    r_lo, r_hi, c_lo, c_hi = case["window"]
    # Whole pixels only, and never below 1: a crop of the rendered width is
    # drawn at its own size and a smaller one is enlarged to fill it.
    factor = max(1, int(config.AI_CROP_RENDER_PX // max(1, (r_hi - r_lo))))

    id_crop = state["lacuna_id_map"][r_lo:r_hi, c_lo:c_hi]
    gray = stretch_to_gray(state["channel"][r_lo:r_hi, c_lo:c_hi], id_crop > 0)
    panel = _enlarge(np.stack([gray] * 3, axis=-1), factor)
    right = panel.copy()

    named = {"colours": case["colours"], "unnameable": case["bodies_with_no_colour"]}
    rgb_of = dict(OWNER_COLOURS)
    by_label = {seg["label"]: seg for seg in candidates["segments"]}
    id_of_colour = {lacuna_id: name for name, lacuna_id in named["colours"].items()}

    def draw(entry, colour):
        seg = by_label[entry["label"]]
        inside = ((seg["rows"] >= r_lo) & (seg["rows"] < r_hi)
                  & (seg["cols"] >= c_lo) & (seg["cols"] < c_hi))
        if not inside.any():
            return None
        rows = (seg["rows"][inside] - r_lo) * factor
        cols = (seg["cols"][inside] - c_lo) * factor
        for d_row in range(factor):
            for d_col in range(factor):
                right[rows + d_row, cols + d_col] = colour
        return {"row": int(rows.min()), "col": int(cols[np.argmin(rows)])}

    def colour_of(entry, numbered=False):
        if entry["kind"] == "new":
            # Not traced by the pipeline, numbered or not: red says so, and for
            # a numbered one that is the whole of the real-or-artifact question.
            return SEGMENT_NEW_COLOUR
        if numbered or entry["kind"] == "unowned":
            # A NUMBERED segment the pipeline traced is drawn in WHITE, whoever
            # owns it now, because its owner is the question. The owner is not
            # hidden by that: it is one of the candidate colours the case text
            # names for that number, and the tracing around it is still drawn in
            # that owner's colour as context.
            return SEGMENT_UNOWNED_COLOUR
        name = id_of_colour.get(entry["owner_lacuna_id"])
        return rgb_of[name] if name else UNNAMEABLE_COLOUR

    # Context first, so a numbered segment is never hidden under one.
    for entry in case["context"]:
        draw(entry, colour_of(entry))
    for name, lacuna_id in named["colours"].items():
        outline = segmentation.find_boundaries(id_crop == lacuna_id, mode="outer")
        right[_enlarge(outline, factor)] = rgb_of[name]
    for lacuna_id in named["unnameable"]:
        outline = segmentation.find_boundaries(id_crop == lacuna_id, mode="outer")
        right[_enlarge(outline, factor)] = UNNAMEABLE_COLOUR

    drawn = []
    for entry in sorted(case["decide"], key=lambda e: e["n"]):
        at = draw(entry, colour_of(entry, numbered=True))
        if at is None:
            continue
        drawn.append({"n": entry["n"], "segment_id": entry["segment_id"],
                      "kind": entry["kind"], "question": entry["question"],
                      "candidates": entry["candidates"], "classes": entry["classes"],
                      "row": at["row"], "col": at["col"]})
    taken: list = []
    for item in drawn:
        row, col = _place_label(right, taken, str(item["n"]), item["row"], item["col"], factor)
        _draw_digits(right, str(item["n"]), row, col)

    gap = np.full((panel.shape[0], PANEL_GAP_PX, 3), PANEL_GAP_COLOUR, dtype=np.uint8)
    canvas = np.concatenate([panel, gap, right], axis=1)
    buffer = io.BytesIO()
    Image.fromarray(canvas).save(buffer, format="PNG")
    return buffer.getvalue(), {
        "window_rows": [int(r_lo), int(r_hi)],
        "window_cols": [int(c_lo), int(c_hi)],
        "crop_px": int(r_hi - r_lo),
        "enlargement": int(factor),
        "panel_px": [int(canvas.shape[1]), int(canvas.shape[0])],
        "colours": named["colours"],
        "bodies_with_no_colour": named["unnameable"],
        "segments_drawn": [item["n"] for item in drawn],
        # Per number: what it is asked, and the colours of its candidates. It is
        # what the case text states and what the answer is validated against, so
        # the two can never drift apart.
        "questions": {item["n"]: {
            "question": item["question"],
            "classes": item["classes"],
            "candidate_colours": [id_of_colour[i] for i in item["candidates"]
                                  if i in id_of_colour],
        } for item in drawn},
        "kinds_drawn": {k: sum(1 for item in drawn if item["kind"] == k)
                        for k in ("new", "unowned", "owned", "other")},
        "context_drawn": len(case["context"]),
        "numbers_not_drawn": [e["n"] for e in case["decide"]
                              if e["n"] not in {item["n"] for item in drawn}],
    }


def case_user_text(case: dict, drawn: dict) -> str:
    """The only text that changes from case to case. It carries no file name, no
    path and no group: the numbers in the picture, what each one is asked, and
    the candidate colours each one may be answered with.

    The candidates are named here and nowhere else. They are the two cells the
    segment could start from, nearer one first, and the only owners its answer
    may name: "the first candidate, the second candidate, or none"."""
    names = [name for name, _rgb in OWNER_COLOURS if name in drawn["colours"]]
    numbers = drawn["segments_drawn"]
    lines = []
    for n in numbers:
        ask = drawn["questions"][n]
        pair = " or ".join(f'"{c}"' for c in ask["candidate_colours"]) or "no candidate"
        if ask["question"] == "real and owner":
            lines.append(f"  {n}: drawn in red, the pipeline has not traced it. Is it a real "
                         f"thread or glow texture, and which cell does it start from: "
                         f"{pair}, or \"none\"?")
        else:
            lines.append(f"  {n}: drawn in white, the pipeline has traced it. Which cell does "
                         f"it start from: {pair}, or \"none\"?")
    extra = ""
    if drawn["bodies_with_no_colour"]:
        extra = (" One or more further bodies are outlined in grey. No number's candidates are"
                 " ever grey, so a grey body is context only.")
    return (f"This case has {len(numbers)} numbered segment(s). The square of tissue is "
            f"{drawn['crop_px']} px across, enlarged {drawn['enlargement']}x. The bodies "
            f"outlined are: {', '.join(names)}, with yellow in the middle.{extra}\n\n"
            + "\n".join(lines)
            + "\n\nAnswer for every number, and for each one name only a colour offered for "
              "that number or \"none\", in one json object.")


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
    anthropic = _sdk()
    client = anthropic.Anthropic()
    sent = dict(payload)
    thinking_fallback = False
    try:
        message = client.messages.create(**sent)
    except (anthropic.BadRequestError, TypeError) as error:
        # The one negotiation this code does: if the model refuses the thinking
        # setting, or the installed SDK is too old to know it, it is dropped
        # once and the log records that the request went out at the model's
        # default instead.
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


def _sdk():
    """The official Anthropic SDK, imported on use with an error a person can
    act on. It is not in the pinned requirements because no pipeline number
    depends on it (docs/EXPERIMENT_AI.md)."""
    try:
        import anthropic  # noqa: PLC0415 (deliberate: only a real call needs it)
    except ImportError as error:
        raise RuntimeError(
            "a real call needs the Anthropic SDK, which is not installed here: "
            "pip install anthropic (on this venv's Python 3.9 that resolves to the "
            "last 0.x release, which is what this code is written against)") from error
    return anthropic


def count_tokens(payload: dict) -> int:
    """The exact input token count of a request, from the API's own counter.
    Free, but still a network call, so it runs only when external calls are
    allowed and only when a dry run is asked for it."""
    client = _sdk().Anthropic()
    fields = {"model": payload["model"], "system": payload["system"],
              "messages": payload["messages"]}
    return int(client.messages.count_tokens(**fields).input_tokens)


def stub_answerer():
    """A stand-in judge for the self-test: no network, no key, no cost.

    It reads the case text for the numbers and each number's candidates, and
    answers by a fixed rule that is meaningless biologically and is meant to be:

      a RED number (real or artifact, and whose): odd is real and goes to its
      first candidate, even is an artifact;
      a WHITE number (whose only): the LAST candidate offered, which for a class
      d segment is the cell that does not own it now, so a verdict MOVES
      ownership and the shortest path has something to redo.

    What the self-test checks is the machinery: that a picture becomes a
    request, an answer becomes verdicts, a log becomes the same verdicts again
    on replay, and that the switch then edits the mask and moves a network. It
    deliberately returns unreadable json on some calls, so that the retry and
    the unjudged path are exercised too: every third case is broken once and
    recovers, every seventh is broken twice and stays unjudged.

    Returns a fresh callable with its own counter, so a self-test run is the
    same every time."""
    seen: dict = {}

    def answer(payload: dict) -> dict:
        text = payload["messages"][0]["content"][1]["text"]
        asked = []
        for line in text.splitlines():
            match = re.match(r"\s*(\d+): drawn in (red|white)", line)
            if not match:
                continue
            colours = [c for c in re.findall(r'"([a-z]+)"', line) if c != "none"]
            asked.append((int(match.group(1)), match.group(2), colours))
        key = text[:80]
        index = seen.setdefault(key, len(seen) + 1)
        attempts = seen[("tries", key)] = seen.get(("tries", key), 0) + 1
        broken = (index % 7 == 0) or (index % 3 == 0 and attempts == 1)
        if broken:
            body = "I looked at the picture and here is what I think, in prose."
        else:
            items = []
            for number, colour, colours in asked:
                if colour == "red":
                    real = bool(number % 2)
                    items.append({"n": number, "verdict": "real" if real else "artifact",
                                  "owner": (colours[0] if colours else "none") if real
                                           else "none",
                                  "why": "self-test, no judgement was made"})
                else:
                    items.append({"n": number, "owner": colours[-1] if colours else "none",
                                  "why": "self-test, no judgement was made"})
            body = json.dumps({"segments": items})
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


def parse_answer(text: str, numbers: list, colours: dict, questions: dict) -> tuple:
    """(answer, why it was refused). Strict: the json must name every number in
    the picture exactly once, name no other, and use only the words the prompt
    allows FOR THAT NUMBER. Anything else is refused whole, because a half-read
    answer is a judgement nobody made.

    The owner a number may be given is one of its own two candidates or "none",
    and nothing else: naming a cell that was never offered for that segment is
    not a judgement of the question that was asked.

    `verdict` is asked for, and read, only where the question is "real and
    owner", which is a segment the pipeline has not traced. For a segment the
    pipeline HAS traced the only question is the owner, so the verdict is "real"
    by what the pipeline already did and a verdict in the answer is recorded and
    ignored rather than acted on: nothing the judge says can delete tracing the
    pipeline made."""
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
        ask = questions.get(number, {})
        allowed_owners = set(ask.get("candidate_colours", ())) | {"none"}
        owner = str(item.get("owner", "none")).strip().lower()
        if owner not in allowed_owners:
            return None, (f"segment {number} has owner {item.get('owner')!r}, which is not one "
                          f"of {sorted(allowed_owners)}")
        said = str(item.get("verdict", "")).strip().lower()
        if ask.get("question") == "real and owner":
            if said not in VERDICTS:
                return None, f"segment {number} has verdict {item.get('verdict')!r}"
            verdict = said
            if verdict == "artifact":
                owner = "none"
        else:
            verdict = "real"
        why = str(item.get("why", "")).strip()
        seen[number] = {"n": number, "verdict": verdict, "owner": owner,
                        "owner_lacuna_id": colours.get(owner), "why": why[:300],
                        "verdict_asked_for": ask.get("question") == "real and owner",
                        "verdict_in_the_answer": said or None}
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
              "invalid_attempts": 0, "call_errors": 0, "refusals": 0,
              "replay_request_mismatches": 0, "replay_picture_mismatches": 0,
              "segments": 0, "segments_real": 0,
              "segments_artifact": 0, "segments_unjudged": 0,
              "segments_given_an_owner": 0, "segments_given_no_owner": 0,
              "segments_asked_an_owner_only": 0, "segments_asked_real_and_owner": 0,
              "owner_moved_by_a_verdict": 0, "owner_left_where_it_was": 0,
              "verdicts_sent_where_none_was_asked": 0, "stopped_on_cost": False}
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
            "case_kind": case["kind"],
            "centroid_xy": case["centroid_xy"],
            "window": case["window"],
            "segments_offered": len(case["decide"]),
            "segments_not_offered": case["segments_not_offered"],
            "context_segments": len(case["context"]),
            "picture": picture.relative_to(config.PROJECT_ROOT).as_posix(),
            "colours": drawn["colours"],
            "bodies_with_no_colour": drawn["bodies_with_no_colour"],
            "kinds_drawn": drawn["kinds_drawn"],
            "answer_valid": False,
            "attempts": 0,
            "invalid_reasons": [],
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "cost_usd": 0.0,
            "segments": [{"n": seg["n"], "segment_id": seg["segment_id"], "kind": seg["kind"],
                          "classes": seg["classes"], "question": seg["question"],
                          "candidates": seg["candidates"],
                          "candidate_colours": drawn["questions"].get(
                              seg["n"], {}).get("candidate_colours", []),
                          "px": seg["px"], "length_um": seg["length_um"],
                          "owner_lacuna_id_before": seg["owner_lacuna_id"],
                          "touches": seg["touches"],
                          "verdict": "unjudged", "owner": "none", "owner_lacuna_id": None,
                          "why": ""}
                         for seg in sorted(case["decide"], key=lambda e: e["n"])],
        }
        # Every numbered segment is drawn, because a case is built from the
        # segments its own crop holds; this stays as a guard and is reported.
        record_case["segments_not_drawn"] = len(drawn["numbers_not_drawn"])
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
                check = {
                    "attempt": attempt,
                    "written_at": logged.get("written_at"),
                    "request_sha256": logged.get("request_sha256"),
                    "request_matches": logged.get("request_sha256") == request_sha,
                    "picture_matches": logged.get("picture_sha256") == sha256_bytes(png),
                }
                record["replay_of"] = check
                record_case.setdefault("replay_checks", []).append(check)
                totals["replay_request_mismatches"] += int(not check["request_matches"])
                totals["replay_picture_mismatches"] += int(not check["picture_matches"])
                response = logged.get("response") or {}
                record["response"] = response
                record["cost_usd"] = float(logged.get("cost_usd", 0.0))
            else:
                if answerer is None:
                    allowed, why = external_calls_allowed()
                    if not allowed:
                        raise RuntimeError(f"a real call was asked for but {why}")
                try:
                    response = (answerer or call_anthropic)(payload)
                except Exception as error:  # noqa: BLE001
                    # A call that fails is one bad attempt and not the end of
                    # the image: it is logged, retried once like any other bad
                    # answer, and the case is left unjudged if it fails again.
                    reason = scrub(f"the call failed, {type(error).__name__}: {error}")
                    record.update({"response": None, "valid": False, "parsed": None,
                                   "invalid_reason": reason, "cost_usd": 0.0})
                    write_log(label, record)
                    totals["attempts"] += 1
                    totals["invalid_attempts"] += 1
                    totals["call_errors"] += 1
                    record_case["attempts"] = attempt
                    record_case["invalid_reasons"].append(f"attempt {attempt}: {reason}")
                    continue
                record["response"] = response
                totals["refusals"] += int(response.get("stop_reason") == "refusal")
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
                                           drawn["colours"], drawn["questions"])
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
                            "owner_lacuna_id": item["owner_lacuna_id"], "why": item["why"],
                            "verdict_in_the_answer": item["verdict_in_the_answer"]})
                if not item["verdict_asked_for"] and item["verdict_in_the_answer"]:
                    totals["verdicts_sent_where_none_was_asked"] += 1
        else:
            totals["cases_unjudged"] += 1
        for seg in record_case["segments"]:
            totals["segments"] += 1
            totals[f"segments_{seg['verdict']}"] += 1
            totals["segments_asked_an_owner_only" if seg["question"] == "owner"
                   else "segments_asked_real_and_owner"] += 1
            if seg["verdict"] == "unjudged":
                continue
            if seg["owner_lacuna_id"]:
                totals["segments_given_an_owner"] += 1
                totals["owner_moved_by_a_verdict" if seg["owner_lacuna_id"]
                       != seg["owner_lacuna_id_before"] else "owner_left_where_it_was"] += 1
            else:
                totals["segments_given_no_owner"] += 1
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


def apply_to_base(image_path: Path, candidate: np.ndarray, base: dict, lac: dict,
                  channel: np.ndarray) -> dict:
    """The switch. Returns the edited candidate mask, the pixels the judge took
    away, and where it says ownership belongs.

    `base` is the network result of a run with the switch OFF, which is the
    pipeline as it stands and what the judge was shown. The candidates are
    rebuilt from it and must hash to what the decision file was written for.

    The edit is the smallest one that can express the verdicts:
      a segment judged REAL that the pipeline does not have adds the mask its
      centre line is the centre line of;
      a segment judged ARTIFACT takes that mask away, whether the pipeline
      traced it or not;
      a segment judged REAL that the pipeline already has is left where it is,
      and only its owner can change;
      everything else, including a segment with no valid answer, one that was
      never offered, and one whose two answers disagree, is left exactly as the
      pipeline had it.
    So with no verdicts at all the mask comes back unchanged, and the switch
    changes a number only where the judge actually answered.

    The owner the judge names is not written anywhere by hand: it becomes a zero
    weight attachment from that cell to the nearest node of the segment, the
    same zero weight the contact rule uses, and the pipeline's own ownership
    then decides everything else (canaliculi.attach_judged_segments)."""
    label = lacunae.image_label(image_path)
    decisions = read_decisions(label)
    state = state_from_base(base, lac, image_path, channel)
    candidates = image_candidates(state)
    if decisions["geometry_sha256"] != candidates["geometry_sha256"]:
        raise ValueError(
            f"the judge decision file for {label} was written for different candidates "
            f"(geometry {decisions['geometry_sha256'][:12]}, now "
            f"{candidates['geometry_sha256'][:12]}). Rerun the judge for this image.")

    # One verdict per SEGMENT, not per case: a segment that touches two bodies
    # is numbered in both of their cases, and two answers that disagree are no
    # answer at all.
    verdicts: dict = {}
    conflicts = set()
    for case in decisions["cases"]:
        for item in case["segments"]:
            if item["verdict"] == "unjudged":
                continue
            key = item["segment_id"]
            seen = verdicts.get(key)
            if seen is None:
                verdicts[key] = item
            elif (seen["verdict"], seen["owner_lacuna_id"]) != (item["verdict"],
                                                                item["owner_lacuna_id"]):
                conflicts.add(key)
    for key in conflicts:
        verdicts.pop(key, None)

    territory = candidates["territory"]
    add = np.zeros(candidate.shape, dtype=bool)
    remove = np.zeros(candidate.shape, dtype=bool)
    judged = np.zeros(candidate.shape, dtype=bool)
    attach: dict = {}
    counts = {"real": 0, "artifact": 0, "unjudged": 0, "conflicting": len(conflicts),
              "added_px": 0, "removed_px": 0, "attached_segments": 0,
              "real_new": 0, "real_traced": 0, "artifact_new": 0, "artifact_traced": 0}
    for seg in candidates["segments"]:
        item = verdicts.get(seg["segment_id"])
        if item is None:
            counts["unjudged"] += 1
            continue
        verdict = item["verdict"]
        counts[verdict] += 1
        counts[f"{verdict}_{'new' if seg['kind'] == 'new' else 'traced'}"] += 1
        judged |= territory == seg["label"]
        if verdict == "real":
            if seg["kind"] == "new":
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
    # Where the judge's own edit lies: inside a zone of the hole, or on a
    # segment the pipeline traced outside one. Both are reported, because the
    # second is new in this version and the first was the only one before it.
    zone = state["zone_owner"] > 0
    counts["edited_px_outside_the_zones"] = int(((add | remove) & ~zone).sum())
    # The invariant of the whole design: the judge's edit lands on the segments
    # it was given and nowhere else. 0 by construction, measured so that a
    # mistake in the territory map cannot pass unseen.
    counts["edited_px_outside_the_judged_segments"] = int(((add | remove) & ~judged).sum())
    edited = (candidate | add) & ~remove
    return {
        "candidate": edited,
        "add": add,
        "remove": remove,
        "zone_owner": state["zone_owner"],
        "attach": attach,
        "counts": counts,
        "geometry_sha256": candidates["geometry_sha256"],
        "decisions_written_at": decisions["written_at"],
        "model": decisions["model"],
        "zone_px": int(zone.sum()),
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
