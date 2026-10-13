"""Measures for both methods, taken by src/quantification.py.

Both the current mask and the new one are handed to `quantification.quantify`,
the same function with the same code, so a difference in a number is a difference
in the skeleton and never in the measuring. This module only:

- builds the detection dict that quantify reads, from arrays in memory;
- converts the measures it returns into micrometres;
- adds the three network-shape measures the comparison asks for that the
  pipeline does not report: the thread-end fraction, the share of skeleton length
  connected to a lacuna, and the median edge length;
- adds the artifact measures: the axis-aligned runs, the rectangles on the pixel
  grid, and the share of skeleton the flattened image does not support.

Conversions at s = 0.13 um/px: a length in px times s is um; an area in px^2
times s^2 is um^2; a length density in px^-1 divided by s is um of thread per
um^2 of tissue, because (px / px^2) / s = (px s) / (px s)^2.

**Pixel size 0.13 um/px.** Pre-validation: no number here has been checked
against a manual count.
"""
from __future__ import annotations

import networkx as nx
import numpy as np

import canaliculi
import quantification


def detection_dict(label: str, lacuna_id_map: np.ndarray, mask: np.ndarray, bridged: np.ndarray,
                   skeleton: np.ndarray, vascular: np.ndarray, own: dict, n_bridges: int,
                   lacuna_parameters: dict, network_parameters: dict) -> dict:
    """The dict quantification.load_detection returns, built from arrays instead
    of from files, so quantify measures either method unchanged."""
    return {
        "label": label,
        "lacuna_id_map": lacuna_id_map,
        "lacuna_mask": lacuna_id_map > 0,
        "mask": mask,
        "thresholded": mask & ~bridged,
        "bridged": bridged,
        "skeleton": skeleton,
        "vascular": vascular,
        "graph": own["graph"],
        "owner": own["owner"],
        "node_dist": own["node_dist"],
        "edge_owner": own["edge_owner"],
        "lacunae_detection": {"parameters": lacuna_parameters},
        "canaliculi_detection": {"parameters": network_parameters, "n_bridges": n_bridges},
    }


def thread_end_fraction(graph) -> float | None:
    """Share of the real graph nodes with exactly one edge. A 2D section cuts a
    3D network, so a thread that leaves the focal plane ends inside the image;
    docs/METHODS.md records 76% for the current method."""
    real = canaliculi.real_subgraph(graph)
    nodes = list(real.nodes())
    if not nodes:
        return None
    return round(sum(1 for n in nodes if real.degree(n) == 1) / len(nodes), 6)


def connected_to_lacuna_fraction(graph, owner: dict) -> float | None:
    """Share of the graph's edge length whose two ends both belong to a cell,
    that is, the share of the network that reaches a lacuna through the graph.
    The ownership has no distance limit, so this says how much is connected at
    all, not how much lies near a cell."""
    real = canaliculi.real_subgraph(graph)
    total = connected = 0.0
    for u, v, data in real.edges(data=True):
        length = float(data["weight"])
        total += length
        if owner.get(u) is not None and owner.get(v) is not None:
            connected += length
    return round(connected / total, 6) if total > 0 else None


def median_edge_length_px(graph, edge_owner: dict, n_lacunae: int) -> float | None:
    """Median length of an owned edge. The pipeline reports the mean per cell;
    the median over every owned edge is added for the comparison."""
    lengths = []
    for lacuna_id in range(1, n_lacunae + 1):
        lengths += quantification.cell_edge_lengths(graph, edge_owner, lacuna_id)
    return float(np.median(lengths)) if lengths else None


def network_shape(detection: dict, n_lacunae: int) -> dict:
    """The three measures added for this comparison."""
    graph = detection["graph"]
    return {
        "thread_end_fraction": thread_end_fraction(graph),
        "connected_to_lacuna_fraction": connected_to_lacuna_fraction(graph, detection["owner"]),
        "median_edge_length_px": median_edge_length_px(graph, detection["edge_owner"], n_lacunae),
    }


def in_um(result: dict, shape: dict, params) -> dict:
    """Every measure of the comparison in micrometres, beside its pixel value.

    Only the measures the brief lists are converted; a share, a count and a
    unitless ratio stay as they are."""
    field = result["field"]
    width = result["width"]
    interior = result["summary"]
    radii = canaliculi.RING_RADII_PX
    s = params.pixel_size_um

    def um(px):
        return params.um(px) if px is not None else None

    def mean_of(name):
        return interior.get(name, {}).get("mean")

    density_px = field.get("canalicular_length_density_per_px")
    out = {
        "field_length_density_per_px": density_px,
        # A length density in px^-1 divided by the pixel size is um per um^2.
        "field_length_density_um_per_um2": round(density_px / s, 6) if density_px is not None else None,
        "analysed_area_px2": field.get("analysed_area_px2"),
        "analysed_area_um2": round(field.get("analysed_area_px2", 0.0) * s * s, 4),
        "total_skeleton_length_px": field.get("total_skeleton_length_px"),
        "total_skeleton_length_um": um(field.get("total_skeleton_length_px")),
        "junction_count": field.get("junction_count"),
        "junction_density_per_px2": field.get("junction_density_per_px2"),
        "junction_density_per_um2": round(field["junction_density_per_px2"] / (s * s), 4)
        if field.get("junction_density_per_px2") is not None else None,
        "roots_per_cell": mean_of("roots_count"),
        "owned_length_px_per_cell": mean_of("owned_length_px"),
        "owned_length_um_per_cell": um(mean_of("owned_length_px")),
        "mean_edge_length_px": mean_of("mean_edge_length_px"),
        "mean_edge_length_um": um(mean_of("mean_edge_length_px")),
        "median_edge_length_px": shape["median_edge_length_px"],
        "median_edge_length_um": um(shape["median_edge_length_px"]),
        "width_median_px": width.get("width_median_px"),
        "width_median_um": um(width.get("width_median_px")),
        "width_p10_px": width.get("width_p10_px"),
        "width_p10_um": um(width.get("width_p10_px")),
        "width_p90_px": width.get("width_p90_px"),
        "width_p90_um": um(width.get("width_p90_px")),
        "width_pixels_used": width.get("width_pixels_used"),
        "thread_end_fraction": shape["thread_end_fraction"],
        "connected_to_lacuna_fraction": shape["connected_to_lacuna_fraction"],
        "interior_lacuna_count": result["interior_lacuna_count"],
        "lacuna_count": result["lacuna_count"],
        "n_bridges": result["n_bridges"],
    }
    for radius in radii:
        px = mean_of(f"ring_length_r{radius}_px")
        out[f"ring_length_r{radius}_px_per_cell"] = px
        out[f"ring_length_r{radius}_um_per_cell"] = um(px)
    inner = radii[0]
    px = mean_of(f"ring_width_mean_r{inner}_px")
    out[f"ring_width_mean_r{inner}_px_per_cell"] = px
    out[f"ring_width_mean_r{inner}_um_per_cell"] = um(px)
    return out


def measure(detection: dict, image_path, params) -> dict:
    """Every measure of one method on one image: the pipeline's own output, the
    three added shape measures, and the comparison row in px and um."""
    result = quantification.quantify(detection, image_path)
    shape = network_shape(detection, result["lacuna_count"])
    result["shape"] = shape
    result["comparison"] = in_um(result, shape, params)
    return result


# The columns of comparison_all_images, in order. One row per image and method.
COMPARISON_COLUMNS = [
    "image_label", "method", "pixel_size_label",
    "lacuna_count", "interior_lacuna_count", "n_bridges",
    "field_length_density_per_px", "field_length_density_um_per_um2",
    "total_skeleton_length_px", "total_skeleton_length_um",
    "roots_per_cell",
    "ring_length_r30_px_per_cell", "ring_length_r30_um_per_cell",
    "ring_length_r60_px_per_cell", "ring_length_r60_um_per_cell",
    "width_median_px", "width_median_um", "width_p10_px", "width_p10_um",
    "width_p90_px", "width_p90_um", "width_pixels_used",
    "ring_width_mean_r30_px_per_cell", "ring_width_mean_r30_um_per_cell",
    "junction_count", "junction_density_per_px2", "junction_density_per_um2",
    "thread_end_fraction", "connected_to_lacuna_fraction",
    "mean_edge_length_px", "mean_edge_length_um",
    "median_edge_length_px", "median_edge_length_um",
    "owned_length_px_per_cell", "owned_length_um_per_cell",
    "analysed_area_px2", "analysed_area_um2",
]
# The artifact measures
# Moved here unchanged when src/canal_physical/ablation.py was removed: they are
# measures, and this is where the measures live. A canaliculus has no reason to
# follow the pixel grid, so a long axis-aligned run or a closed rectangle on the
# grid is a sign of the detector and not of the tissue.

STRAIGHT_RUN_MIN_PX = 8

# Two nodes count as lying on one axis-aligned side if their rows or their columns
# differ by at most this, which allows the one pixel of slack a cleaned graph node
# can carry.
RECTANGLE_TOLERANCE_PX = 1


def unsupported_mask(skeleton: np.ndarray, flattened: np.ndarray, cut: float) -> np.ndarray:
    """Skeleton pixels the flattened image does not support: those not above the
    image's own lower multi-Otsu cut, which is the exact complement of the rule
    the current method uses to call a pixel signal (`img > t_lo`)."""
    return skeleton & ~(flattened > cut)


def straight_run_mask(skeleton: np.ndarray, min_length: int = STRAIGHT_RUN_MIN_PX) -> np.ndarray:
    """Skeleton pixels inside a perfectly horizontal or vertical run of at least
    `min_length` pixels.

    A run is a maximal set of consecutive skeleton pixels along one image row or
    one image column. A pixel that belongs to a long run in either direction is
    marked. Diagonal and curved stretches are never marked, however long, so this
    counts only structure that follows the pixel grid."""
    marked = np.zeros_like(skeleton, dtype=bool)
    for axis in (0, 1):
        work = skeleton if axis == 1 else skeleton.T
        out = np.zeros_like(work, dtype=bool)
        for i in range(work.shape[0]):
            line = work[i]
            if not line.any():
                continue
            # Run boundaries along this line.
            padded = np.concatenate(([False], line, [False]))
            edges = np.flatnonzero(padded[1:] != padded[:-1])
            for start, stop in zip(edges[0::2], edges[1::2]):
                if stop - start >= min_length:
                    out[i, start:stop] = True
        marked |= out if axis == 1 else out.T
    return marked


def rectangle_count(graph) -> int:
    """Closed loops of four nodes in the cleaned skeleton graph whose four sides
    are all axis-aligned.

    The loops come from networkx.cycle_basis, which gives one independent cycle
    per loop in the graph, so this counts independent four-node loops and not
    every way of walking one. A side counts as axis-aligned when its two nodes
    share a row or a column to within RECTANGLE_TOLERANCE_PX. A real network has
    no reason to close a rectangle on the pixel grid."""
    real = canaliculi.real_subgraph(graph)
    count = 0
    for cycle in nx.cycle_basis(real):
        if len(cycle) != 4:
            continue
        sides = list(zip(cycle, cycle[1:] + cycle[:1]))
        if all(abs(u[0] - v[0]) <= RECTANGLE_TOLERANCE_PX or abs(u[1] - v[1]) <= RECTANGLE_TOLERANCE_PX
               for u, v in sides):
            count += 1
    return count


def artifact_measures(detection: dict, flattened: np.ndarray, cut: float) -> dict:
    """The three artifact measures, over the whole skeleton, with the share of it
    that gap bridging drew."""
    skel = detection["skeleton"]
    total = int(skel.sum())
    if total == 0:
        return {"skeleton_px": 0, "unsupported_fraction": None, "bridged_fraction": None,
                "straight_run_fraction": None, "rectangle_count": 0,
                "unsupported_px": 0, "bridged_px": 0, "straight_run_px": 0}
    unsupported = unsupported_mask(skel, flattened, cut)
    straight = straight_run_mask(skel)
    bridged = skel & detection["bridged"]
    return {
        "skeleton_px": total,
        "unsupported_px": int(unsupported.sum()),
        "unsupported_fraction": round(float(unsupported.sum()) / total, 6),
        "bridged_px": int(bridged.sum()),
        "bridged_fraction": round(float(bridged.sum()) / total, 6),
        "straight_run_px": int(straight.sum()),
        "straight_run_fraction": round(float(straight.sum()) / total, 6),
        "rectangle_count": rectangle_count(detection["graph"]),
    }
