"""EXPERIMENTAL per-lacuna canaliculi feature extraction.

STATUS: v1-RAW, pre-validation. Builds on segment_lacunae_v2's lacuna
segmentation (imported, not modified) to additionally trace the canalicular
network and attribute it to individual lacunae. Nothing here has been
checked against ground truth. Parameters below are candidates only and are
kept out of config.py until validated. Everything stays in PIXEL units --
PIXEL_SIZE_UM is None, so nothing is converted to microns.

Method:
    1. Segment lacunae with segment_lacunae_v2's multi-Otsu + watershed
       approach (imported as-is).
    2. Segment the canalicular network: red signal above background (the
       LOWER of the two multi-Otsu cuts -- background vs. everything else,
       computed per-image, same idea as v2's threshold but one level down;
       strict ">" so a pixel exactly at the cut is never included), minus
       a small buffer around the lacuna bodies, despeckled by size (not by
       erosion, which would erase 1px-wide threads), then skeletonized to
       1px centerlines.
    3. Assign every skeleton branch to a lacuna. Two methods, chosen by
       ASSIGNMENT_METHOD:
       - "graph" (default): the whole skeleton is one weighted graph
         (nodes = junction/endpoint pixels, edges = branches weighted by
         branch length). Each lacuna is attached as a virtual source node
         linked to every skeleton node within LACUNA_ATTACH_GAP_PX of its
         body. A single multi-source shortest-path run then assigns every
         reachable skeleton node to whichever cell it is graph-connected
         to via the shortest path -- i.e. by network connectivity, the
         way OCY (Kollmannsberger et al., "The small world of osteocytes")
         assigns a canaliculus to the cell it physically connects to,
         not by which cell is spatially closest in a straight line. This
         fixes the old method's straight-edged territories in dense
         fields, which could hand half of a canaliculus to the wrong
         neighbor. Terminal spurs shorter than PRUNE_SPUR_LEN_PX are
         pruned from the graph first -- these are thresholding-noise
         branches, not real canaliculi, and were inflating counts into
         the tens-to-hundreds per cell.
       - "euclidean" (old behaviour, kept for comparison): every skeleton
         pixel assigned to its nearest lacuna by a Euclidean distance
         transform (a Voronoi split), with no spur pruning.
    4. Per lacuna, count path-based canaliculi and their lengths:
       - "graph": single-source Dijkstra from that lacuna's virtual node;
         every reachable, cell-owned, degree-1 real node is a tip: one
         canaliculus. Length = path distance from the tip back to the
         root (the first real node on the path), i.e. the full path minus
         the virtual attachment edge -- so length is measured from the
         lacuna boundary outward, not from its centroid.
       - "euclidean": per-component root-to-tip tree search within that
         lacuna's owned skeleton subset (root = point closest to the
         lacuna body; a fragment farther than MAX_ROOT_GAP_PX from the
         lacuna is treated as unreachable, not one long canaliculus).

Border lacunae (on_border=True, from v2) are kept in the per-lacuna table
and drawn in the verification image, but excluded from the per-image
summary stats -- their canaliculi are truncated by the field of view.

Outputs, per image, under results/canaliculi/<image_stem_with_underscores>/:
    verification.png   original image at near-full brightness; every lacuna
                        and its owned canaliculi drawn in one unique,
                        randomly (but reproducibly) assigned color, so the
                        colored tracing can be checked directly against the
                        real red canaliculi underneath. With "graph"
                        assignment, a cell's color should visibly follow
                        its connected threads and stop at network branch
                        points, not cut the field into straight-edged
                        blocks.
    measurements.xlsx   "summary" sheet (interior-only mean/median/SD of
                         canaliculi_count and mean_canaliculus_length_px)
                         + "per_lacuna" sheet (one row per lacuna, incl.
                         border ones, flagged on_border)
    measurements.json   same data + the parameters used for this run

When --method is passed on the CLI (overriding ASSIGNMENT_METHOD for that
run only, e.g. for a before/after comparison), all three output filenames
are suffixed with "_<method>" so they never overwrite the default-method
outputs.

Usage:
    python src/canaliculi_v1.py --dir data/WT
    python src/canaliculi_v1.py --dir data/WT --method euclidean
    python src/canaliculi_v1.py --image data/WT/example.tif
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import deque
from pathlib import Path

import networkx as nx
import numpy as np
from scipy import ndimage as ndi
from skimage import filters, morphology, segmentation
from skimage.io import imsave
from skan import Skeleton, summarize

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from count_lacunae import load_channel  # noqa: E402
import segment_lacunae_v2 as seg2  # noqa: E402

# --- Candidate parameters (NOT in config.py yet -- see module docstring) ---

# Which assignment method to use. "graph" = network-connectivity (OCY-style,
# current default). "euclidean" = old nearest-distance Voronoi, kept for
# comparison -- see the module docstring and README section above.
ASSIGNMENT_METHOD = "graph"

# A skeleton node within this many px of a lacuna body is treated as
# attached to it (a graph-method "root"). This is a gap-closing tolerance
# for the LACUNA_DILATION_PX buffer already carved out around each lacuna,
# not a search radius for real canaliculi -- but the initial guess of 5
# left 28/98 lacunae (29%) across all 8 WT images with NO attachment
# point at all (see --attach-gaps in diagnose_lacuna_splits.py), which
# silently gave them 0 canaliculi while a few well-attached neighbors
# absorbed tips that should have been unreachable/theirs instead. The
# min-gap distribution across all 98 lacunae is smooth (2.24 up to 11.18
# px, no natural break to split on), so 10 is a coverage choice, not a
# gap-based one: it leaves only 1/98 lacunae unattached (the 11.18 outlier)
# instead of 28. Revisit if that single case, or the dataset changes.
LACUNA_ATTACH_GAP_PX = 10

# Terminal branches (graph method) shorter than this are treated as
# thresholding-noise spurs and pruned before counting/assignment -- this
# is what brings canaliculi_count down from the tens-to-hundreds/cell seen
# with the Euclidean method to a plausible range. Iteratively applied
# (pruning one spur can expose another).
PRUNE_SPUR_LEN_PX = 4

# Buffer (px) eroded away from the canaliculi candidate mask around each
# lacuna body, so the lacuna's own bright rim isn't mistaken for a stub of
# canaliculus right at the boundary.
LACUNA_DILATION_PX = 2

# Candidate canaliculus fragments smaller than this (px^2) are dropped as
# thresholding noise before skeletonizing. Kept deliberately small so a
# real, thin, short thread survives -- despeckling here is by pixel COUNT,
# never by erosion/opening (which would delete 1px-wide real threads).
MIN_THREAD_OBJECT_PX2 = 8

# Euclidean method only: a connected skeleton fragment whose closest point
# to a lacuna is farther than this (px) is treated as not actually
# attached to that lacuna, not as one long canaliculus.
MAX_ROOT_GAP_PX = 15

# Cosmetic only: how much the owned-skeleton pixels are dilated for
# visibility in the verification PNG. Does not affect any measurement.
VIS_SKELETON_DILATION_PX = 2

# Cosmetic only: how much the background image is shown at in the
# verification PNG. 1.0 = full-brightness original, no dimming, so the
# real red canaliculi are shown exactly as acquired underneath the colored
# tracing, for a direct check that the tracing actually matches the signal.
VIS_DIM_FACTOR = 1.0

# Cosmetic only: colors are evenly spaced around the hue wheel for maximum
# contrast, then shuffled so lacuna N and N+1 (often spatial neighbors)
# don't land on adjacent, blend-prone hues. Shuffled with config.RANDOM_SEED
# so a rerun reproduces the same color assignment (comparable across runs)
# rather than changing every time.
COLOR_SATURATION = 0.9
COLOR_VALUE = 1.0

CANALICULI_DIR = config.RESULTS_DIR / "canaliculi"


# --- Canalicular network segmentation -----------------------------------

def total_signal_mask(channel: np.ndarray) -> tuple[np.ndarray, float]:
    """Lower of the two multi-Otsu (3-class) cuts on this image's own
    histogram: background vs. everything else (mesh + lacunae). Same
    per-image-adaptive idea as v2's threshold, one level down. Strict ">"
    so a background-valued pixel exactly at the cut is never included."""
    try:
        thresholds = filters.threshold_multiotsu(channel, classes=3)
        t_lo = float(thresholds[0])
    except ValueError:
        t_lo = float(filters.threshold_otsu(channel))
    return channel > t_lo, t_lo


def build_lacuna_maps(labels: np.ndarray, kept: list[tuple]) -> tuple[np.ndarray, np.ndarray]:
    """Return (lacuna_mask, lacuna_id_map). lacuna_id_map is 0 outside any
    kept lacuna, else the lacuna's 1..N id (same numbering as v2's
    per-lacuna measurements)."""
    lacuna_id_map = np.zeros(labels.shape, dtype=np.int32)
    for lacuna_id, (region, _on_border) in enumerate(kept, start=1):
        lacuna_id_map[labels == region.label] = lacuna_id
    return lacuna_id_map > 0, lacuna_id_map


def canaliculi_candidate_mask(channel: np.ndarray, lacuna_mask: np.ndarray) -> tuple[np.ndarray, float]:
    signal, t_lo = total_signal_mask(channel)
    buffered_lacunae = morphology.dilation(lacuna_mask, morphology.disk(LACUNA_DILATION_PX))
    candidate = signal & ~buffered_lacunae
    candidate = morphology.remove_small_objects(candidate, min_size=MIN_THREAD_OBJECT_PX2)
    return candidate, t_lo


def nearest_lacuna_map(lacuna_id_map: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """For every pixel, (distance to the nearest lacuna pixel, that
    lacuna's id) -- a Euclidean Voronoi partition seeded from the lacunae.
    Used directly by the "euclidean" assignment method, and by "graph" for
    deciding which lacuna a within-gap attachment point belongs to."""
    dist, indices = ndi.distance_transform_edt(lacuna_id_map == 0, return_indices=True)
    nearest_id = lacuna_id_map[indices[0], indices[1]]
    return dist, nearest_id


def _node_key(row: float, col: float) -> tuple[int, int]:
    return (int(round(row)), int(round(col)))


# --- "euclidean" assignment (old method, kept for comparison) -----------

def trace_lacuna_canaliculi(owned_skeleton: np.ndarray, dist_to_lacuna: np.ndarray) -> list[float]:
    """Return the list of root-to-tip canaliculus lengths (px) for one
    lacuna's owned skeleton subset. Empty list if there are none."""
    if not owned_skeleton.any():
        return []

    skel_obj = Skeleton(owned_skeleton)
    branch_data = summarize(skel_obj, separator="-")
    if len(branch_data) == 0:
        return []

    lengths: list[float] = []
    for _skeleton_id, component in branch_data.groupby("skeleton-id"):
        adjacency: dict[tuple[int, int], list[tuple[tuple[int, int], float]]] = {}
        for _idx, row in component.iterrows():
            if row["branch-type"] == 3:  # isolated cycle, no defined tip
                continue
            src = _node_key(row["image-coord-src-0"], row["image-coord-src-1"])
            dst = _node_key(row["image-coord-dst-0"], row["image-coord-dst-1"])
            weight = float(row["branch-distance"])
            adjacency.setdefault(src, []).append((dst, weight))
            adjacency.setdefault(dst, []).append((src, weight))

        if not adjacency:
            continue

        root = min(adjacency, key=lambda node: dist_to_lacuna[node[0], node[1]])
        if dist_to_lacuna[root[0], root[1]] > MAX_ROOT_GAP_PX:
            continue  # this fragment never actually reaches the lacuna

        # BFS from root, summing edge weight to every other node; degree-1
        # nodes other than the root are tips (canaliculus endpoints).
        cumulative = {root: 0.0}
        queue = deque([root])
        while queue:
            node = queue.popleft()
            for neighbor, weight in adjacency[node]:
                if neighbor not in cumulative:
                    cumulative[neighbor] = cumulative[node] + weight
                    queue.append(neighbor)

        for node, path_length in cumulative.items():
            if node == root:
                continue
            if len(adjacency[node]) == 1:  # degree-1, i.e. a tip
                lengths.append(path_length)

    return lengths


def canaliculi_measurements_euclidean(
    kept: list[tuple],
    skeleton: np.ndarray,
    nearest_id: np.ndarray,
    dist_to_lacuna: np.ndarray,
    precision: int,
) -> list[dict]:
    measurements = []
    for lacuna_id, (_region, on_border) in enumerate(kept, start=1):
        owned_skeleton = skeleton & (nearest_id == lacuna_id)
        lengths = trace_lacuna_canaliculi(owned_skeleton, dist_to_lacuna)
        measurements.append(_measurement_row(lacuna_id, lengths, on_border, precision))
    return measurements


# --- "graph" assignment (network connectivity, OCY-style) ---------------

def build_network_graph(skeleton: np.ndarray):
    """One weighted graph of the whole canalicular skeleton. Nodes are
    junction/endpoint pixel coords, edges are branches weighted by branch
    length in px. Also returns the skan Skeleton object and a
    {frozenset({u, v}): branch_index} lookup, both needed later to recover
    pixel paths for visualization."""
    G = nx.Graph()
    if not skeleton.any():
        return G, None, {}

    skel_obj = Skeleton(skeleton)
    branches = summarize(skel_obj, separator="-")
    edge_branch_index: dict[frozenset, int] = {}

    for idx, b in branches.iterrows():
        if b["branch-type"] == 3:  # isolated loop, no tip
            continue
        src = _node_key(b["image-coord-src-0"], b["image-coord-src-1"])
        dst = _node_key(b["image-coord-dst-0"], b["image-coord-dst-1"])
        w = float(b["branch-distance"])
        if src == dst:
            continue
        key = frozenset((src, dst))
        if G.has_edge(src, dst):
            if w < G[src][dst]["weight"]:
                G[src][dst]["weight"] = w
                edge_branch_index[key] = idx
        else:
            G.add_edge(src, dst, weight=w)
            edge_branch_index[key] = idx

    return G, skel_obj, edge_branch_index


def prune_spurs(G: nx.Graph) -> nx.Graph:
    """Iteratively remove terminal branches shorter than PRUNE_SPUR_LEN_PX
    -- thresholding-noise spurs, not real canaliculi. Removing one spur
    can expose another (its former neighbor may now be a short spur too),
    so this repeats until nothing more qualifies."""
    changed = True
    while changed:
        changed = False
        for node in list(G.nodes()):
            if G.degree(node) == 1:
                neighbor = next(iter(G.neighbors(node)))
                if G[node][neighbor]["weight"] < PRUNE_SPUR_LEN_PX:
                    G.remove_node(node)
                    changed = True
    G.remove_nodes_from([n for n in list(G.nodes()) if G.degree(n) == 0])
    return G


def attach_lacunae(
    G: nx.Graph,
    dist_to_lacuna: np.ndarray,
    nearest_id: np.ndarray,
    cell_ids: list[int],
) -> nx.Graph:
    """Add a virtual ("cell", id) node per lacuna, linked to every skeleton
    node within LACUNA_ATTACH_GAP_PX of that lacuna's body (nearest_id
    decides WHICH lacuna a given attachment point belongs to; the link
    weight is the gap distance, so paths start at the cell boundary)."""
    for node in list(G.nodes()):
        r, c = node
        gap = float(dist_to_lacuna[r, c])
        if gap <= LACUNA_ATTACH_GAP_PX:
            lacuna_id = int(nearest_id[r, c])
            if lacuna_id in cell_ids:
                G.add_edge(("cell", lacuna_id), node, weight=gap)
    return G


def assign_by_connectivity(G: nx.Graph, cell_ids: list[int]) -> tuple[dict, dict]:
    """Multi-source Dijkstra from all cell nodes at once. Every reachable
    skeleton node is owned by the cell whose shortest graph path reaches
    it -- network connectivity, not straight-line distance. Returns
    (owner: {node_coord: cell_id}, edge_owner: {frozenset({u,v}): cell_id}
    for every edge along some node's shortest path, used to color the
    verification image by the same ownership used for measurement)."""
    sources = [("cell", i) for i in cell_ids if G.has_node(("cell", i))]
    if not sources:
        return {}, {}

    _dist, paths = nx.multi_source_dijkstra(G, sources, weight="weight")
    owner: dict = {}
    edge_owner: dict = {}
    for target, path in paths.items():
        if isinstance(target, tuple) and target and target[0] == "cell":
            continue
        source = path[0]
        if not (isinstance(source, tuple) and source and source[0] == "cell"):
            continue
        cell_id = source[1]
        owner[target] = cell_id
        for k in range(1, len(path) - 1):  # skip the virtual cell->root edge
            edge_owner.setdefault(frozenset((path[k], path[k + 1])), cell_id)
    return owner, edge_owner


def trace_cell_canaliculi(G: nx.Graph, cell_id: int, owner: dict) -> list[float]:
    """Path-based canaliculi for one cell: single-source Dijkstra from its
    virtual node; every reachable, cell-owned, degree-1 real node is one
    canaliculus, with length measured from the lacuna boundary (the root
    -- the first real node on the path) outward, i.e. the full path minus
    the virtual attachment edge."""
    src = ("cell", cell_id)
    if not G.has_node(src):
        return []

    dist, paths = nx.single_source_dijkstra(G, src, weight="weight")
    lengths = []
    for node, path in paths.items():
        if isinstance(node, tuple) and node and node[0] == "cell":
            continue
        if owner.get(node) != cell_id:
            continue  # reachable from this cell, but globally owned by another
        if G.degree(node) != 1:
            continue  # not a tip
        root = path[1] if len(path) > 1 else node
        attach_weight = G[src][root]["weight"] if G.has_edge(src, root) else 0.0
        lengths.append(dist[node] - attach_weight)
    return lengths


def build_owner_pixel_map(
    shape: tuple[int, int],
    skel_obj,
    edge_branch_index: dict,
    edge_owner: dict,
) -> np.ndarray:
    """Paint every owned branch's real pixel path with its cell id, for
    reuse by save_verification (same drawing code as the euclidean
    method's nearest_id map)."""
    owner_map = np.zeros(shape, dtype=np.int32)
    if skel_obj is None:
        return owner_map
    for edge, cell_id in edge_owner.items():
        branch_index = edge_branch_index.get(edge)
        if branch_index is None:
            continue  # a virtual cell<->root attachment edge, no pixels
        coords = skel_obj.path_coordinates(branch_index)
        rows = np.clip(coords[:, 0].astype(int), 0, shape[0] - 1)
        cols = np.clip(coords[:, 1].astype(int), 0, shape[1] - 1)
        owner_map[rows, cols] = cell_id
    return owner_map


def canaliculi_measurements_graph(
    kept: list[tuple],
    skeleton: np.ndarray,
    dist_to_lacuna: np.ndarray,
    nearest_id: np.ndarray,
    precision: int,
) -> tuple[list[dict], np.ndarray]:
    cell_ids = list(range(1, len(kept) + 1))

    G, skel_obj, edge_branch_index = build_network_graph(skeleton)
    prune_spurs(G)
    attach_lacunae(G, dist_to_lacuna, nearest_id, cell_ids)
    owner, edge_owner = assign_by_connectivity(G, cell_ids)

    measurements = []
    for lacuna_id, (_region, on_border) in enumerate(kept, start=1):
        lengths = trace_cell_canaliculi(G, lacuna_id, owner)
        measurements.append(_measurement_row(lacuna_id, lengths, on_border, precision))

    owner_map = build_owner_pixel_map(skeleton.shape, skel_obj, edge_branch_index, edge_owner)
    return measurements, owner_map


# --- Shared measurement row / summary ------------------------------------

def _measurement_row(lacuna_id: int, lengths: list[float], on_border: bool, precision: int) -> dict:
    count = len(lengths)
    total_length = float(sum(lengths))
    mean_length = total_length / count if count else 0.0
    return {
        "lacuna_id": lacuna_id,
        "canaliculi_count": count,
        "total_length_px": round(total_length, precision),
        "mean_canaliculus_length_px": round(mean_length, precision),
        "on_border": bool(on_border),
        "units": "px",
    }


SUMMARY_METRICS = [
    ("canaliculi_count", "unitless"),
    ("mean_canaliculus_length_px", "px"),
]


def summarize_interior(measurements: list[dict], precision: int) -> dict:
    interior = [m for m in measurements if not m["on_border"]]
    n = len(interior)
    stats = {"interior_lacuna_count": n, "units": "px"}
    for field, _unit in SUMMARY_METRICS:
        values = np.array([m[field] for m in interior], dtype=float)
        if n == 0:
            mean = median = sd = None
        else:
            mean = round(float(values.mean()), precision)
            median = round(float(np.median(values)), precision)
            sd = round(float(values.std(ddof=1)), precision) if n >= 2 else None
        stats[field] = {"mean": mean, "median": median, "sd": sd}
    return stats


# --- Output ---------------------------------------------------------------

def image_output_dir(image_path: Path) -> Path:
    safe_stem = image_path.stem.replace(" ", "_")
    return CANALICULI_DIR / safe_stem


def lacuna_colors(n_lacunae: int) -> dict[int, tuple[int, int, int]]:
    """One color per lacuna id (1..n_lacunae). Hues are evenly spaced for
    max contrast, then shuffled (seeded, so reruns are reproducible) so
    spatial neighbors don't get blend-prone adjacent hues."""
    import colorsys

    hues = [i / n_lacunae for i in range(n_lacunae)]
    random.Random(config.RANDOM_SEED).shuffle(hues)

    colors = {}
    for lacuna_id, hue in enumerate(hues, start=1):
        r, g, b = colorsys.hsv_to_rgb(hue, COLOR_SATURATION, COLOR_VALUE)
        colors[lacuna_id] = (int(r * 255), int(g * 255), int(b * 255))
    return colors


def save_verification(
    display_uint8: np.ndarray,
    lacuna_id_map: np.ndarray,
    skeleton: np.ndarray,
    owner_map: np.ndarray,
    lacuna_ids: list[int],
    colors: dict[int, tuple[int, int, int]],
    out_path: Path,
) -> None:
    """owner_map: int array, 0 = unowned, else the owning lacuna's id --
    either the euclidean nearest_id map or the graph method's
    build_owner_pixel_map output. Same drawing code either way."""
    vis = (display_uint8.astype(np.float32) * VIS_DIM_FACTOR).astype(np.uint8)
    for lacuna_id in lacuna_ids:
        color = colors[lacuna_id]
        boundary = segmentation.find_boundaries(lacuna_id_map == lacuna_id, mode="outer")
        vis[boundary] = color

        owned_skeleton = skeleton & (owner_map == lacuna_id)
        if owned_skeleton.any():
            owned_skeleton = morphology.dilation(owned_skeleton, morphology.disk(VIS_SKELETON_DILATION_PX))
        vis[owned_skeleton] = color

    out_path.parent.mkdir(parents=True, exist_ok=True)
    imsave(out_path, vis, check_contrast=False)


def save_xlsx(image_name: str, measurements: list[dict], stats: dict, method: str, out_path: Path) -> None:
    from openpyxl import Workbook

    wb = Workbook()

    summary = wb.active
    summary.title = "summary"
    summary.append(["image", "lacuna_count", "interior_lacuna_count", "assignment_method"])
    summary.append([image_name, len(measurements), stats["interior_lacuna_count"], method])
    summary.append([])
    summary.append(["v1-raw / pre-validation -- stats below over interior (on_border=False) lacunae only"])
    summary.append(["metric", "mean", "median", "sd", "units", "n"])
    for field, unit in SUMMARY_METRICS:
        s = stats[field]
        summary.append([field, s["mean"], s["median"], s["sd"], unit, stats["interior_lacuna_count"]])

    per_lacuna = wb.create_sheet("per_lacuna")
    fields = ["lacuna_id", "canaliculi_count", "total_length_px", "mean_canaliculus_length_px", "on_border", "units"]
    per_lacuna.append(fields)
    for m in measurements:
        per_lacuna.append([m[f] for f in fields])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)


def save_json(
    image_path: Path,
    measurements: list[dict],
    stats: dict,
    t_lo: float,
    t_hi: float,
    method: str,
    out_path: Path,
) -> None:
    payload = {
        "status": "v1-raw",
        "note": (
            "Not yet validated against ground truth. "
            + (
                "Canaliculus count/length come from network-connectivity "
                "assignment (multi-source shortest path over the skeleton "
                "graph, OCY-style) with short noise spurs pruned first."
                if method == "graph"
                else "Canaliculus count/length come from a per-lacuna "
                "Euclidean-nearest skeleton assignment, an approximation "
                "in dense fields, with no spur pruning."
            )
            + " Border lacunae are kept (on_border=true) but excluded from summary stats."
        ),
        "image": str(image_path),
        "units": "px",
        "lacuna_count": len(measurements),
        "summary": stats,
        "parameters": {
            "assignment_method": method,
            "pixel_size_um": config.PIXEL_SIZE_UM,
            "lacuna_segmentation": "segment_lacunae_v2 (multi-Otsu 3-class + watershed; see that module)",
            "total_signal_threshold_t_lo": t_lo,
            "lacuna_top_class_threshold_t_hi": t_hi,
            "lacuna_dilation_px": LACUNA_DILATION_PX,
            "min_thread_object_px2": MIN_THREAD_OBJECT_PX2,
            "lacuna_attach_gap_px": LACUNA_ATTACH_GAP_PX,
            "prune_spur_len_px": PRUNE_SPUR_LEN_PX,
            "max_root_gap_px": MAX_ROOT_GAP_PX,
        },
        "lacunae": measurements,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)


def print_summary(stats: dict) -> None:
    for field, unit in SUMMARY_METRICS:
        s = stats[field]
        mean = "n/a" if s["mean"] is None else f"{s['mean']:.2f}"
        median = "n/a" if s["median"] is None else f"{s['median']:.2f}"
        sd = "n/a" if s["sd"] is None else f"{s['sd']:.2f}"
        print(f"    {field:28s} mean={mean:>10s}  median={median:>10s}  sd={sd:>10s}  ({unit})")


def process(image_path: Path, method: str | None = None, output_suffix: str = "") -> dict:
    method = method or ASSIGNMENT_METHOD

    display, channel = load_channel(image_path)
    _display2, labels, kept, t_hi = seg2.segment_image(image_path)

    lacuna_mask, lacuna_id_map = build_lacuna_maps(labels, kept)
    candidate, t_lo = canaliculi_candidate_mask(channel, lacuna_mask)
    skeleton = morphology.skeletonize(candidate)
    dist_to_lacuna, nearest_id = nearest_lacuna_map(lacuna_id_map)

    if method == "graph":
        measurements, owner_map = canaliculi_measurements_graph(
            kept, skeleton, dist_to_lacuna, nearest_id, precision=config.CSV_FLOAT_PRECISION
        )
    elif method == "euclidean":
        measurements = canaliculi_measurements_euclidean(
            kept, skeleton, nearest_id, dist_to_lacuna, precision=config.CSV_FLOAT_PRECISION
        )
        owner_map = nearest_id
    else:
        raise ValueError(f"Unknown method: {method!r} (expected 'graph' or 'euclidean')")

    stats = summarize_interior(measurements, precision=config.CSV_FLOAT_PRECISION)

    out_dir = image_output_dir(image_path)
    colors = lacuna_colors(len(kept))
    all_ids = list(range(1, len(kept) + 1))
    save_verification(
        display, lacuna_id_map, skeleton, owner_map, all_ids, colors, out_dir / f"verification{output_suffix}.png"
    )
    save_xlsx(image_path.name, measurements, stats, method, out_dir / f"measurements{output_suffix}.xlsx")
    save_json(image_path, measurements, stats, t_lo, t_hi, method, out_dir / f"measurements{output_suffix}.json")

    mean_count = stats["canaliculi_count"]["mean"]
    mean_length = stats["mean_canaliculus_length_px"]["mean"]
    mean_count_s = "n/a" if mean_count is None else f"{mean_count:.2f}"
    mean_length_s = "n/a" if mean_length is None else f"{mean_length:.2f}"
    print(
        f"{image_path.name} [{method}]: lacunae={len(kept)}  mean_canaliculi_per_cell={mean_count_s}  "
        f"mean_canaliculus_length_px={mean_length_s}  -> {out_dir}"
    )
    print_summary(stats)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="v1-RAW experimental per-lacuna canaliculi extraction (pre-validation)."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--image", type=Path, help="Path to a single .tif image.")
    group.add_argument("--dir", type=Path, help="Directory of .tif images to process.")
    parser.add_argument(
        "--method",
        choices=["graph", "euclidean"],
        default=None,
        help="Override ASSIGNMENT_METHOD for this run; suffixes output filenames with _<method> "
        "so a comparison run never overwrites the default-method outputs.",
    )
    args = parser.parse_args()

    suffix = f"_{args.method}" if args.method else ""

    if args.image:
        if not args.image.is_file():
            raise FileNotFoundError(f"No such file: {args.image}")
        process(args.image, method=args.method, output_suffix=suffix)
    else:
        if not args.dir.is_dir():
            raise NotADirectoryError(f"No such directory: {args.dir}")
        for image_path in sorted(args.dir.glob("*.tif")):
            process(image_path, method=args.method, output_suffix=suffix)


if __name__ == "__main__":
    main()
