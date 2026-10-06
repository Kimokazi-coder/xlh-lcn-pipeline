"""The experimental method rebuilt around the physical scale.

At 0.13 um/px a canaliculus of 0.2 to 0.4 um is about 1.5 to 3 px across, and
about 2.5 to 4 px after the optical blur. The masks of the current method have a
median distance transform width of 6.0 px (0.78 um) and the first ridge variants
7.4 px, so both are roughly twice that. The scales of those first variants came
from a half width measured on the already inflated mask, which is circular
reasoning: the mask set the scale and the scale set the mask.

Here every scale is set in micrometres from the pixel size, or chosen from the
image itself, and never from the old mask and never from a published value.

**Pixel size 0.13 um/px, rounded, unconfirmed per image.** Pre-validation: no
number here has been checked against a manual count. A diagnosis and a better
founded experiment, not a claim that anything is better.

The flattening, the lacuna buffer, the vascular handling, the bridging rule, the
graph cleanup, the ownership and the ring radii stay exactly as the current
method has them, so one idea changes at a time. The top-hat radius of the
flattening is 5 px, which is 0.65 um and wider than a thread; it is reported with
every run and left alone here, and DECISIONS.md lists it as an open question.
"""
from __future__ import annotations

import csv
import json
import sys
from dataclasses import replace
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
for _extra in (str(_ROOT), str(_ROOT / "src")):
    if _extra not in sys.path:
        sys.path.insert(0, _extra)

import numpy as np  # noqa: E402
from skimage import morphology  # noqa: E402

import canaliculi  # noqa: E402
import config
import lacunae
from canal_physical import ablation, figures_v2, metrics, params as params_mod, preprocess, ridge
from canal_physical import skeleton
from canal_physical import widthprofile

PIXEL_SIZE_UM = config.PIXEL_SIZE_UM_CANAL_PHYSICAL

# (key, what it is, family, bridging, sigmas in um or None, low cut share, image source)
# "image source" is which image the ridge filter reads: the flattened channel, or
# the flattened channel after the notch filter of experiments/task1_artefact.py.
VARIANTS = [
    ("A", "current method, as is", "current", True, None, None, "flattened"),
    ("P1", "ridge, sigmas 0.13, 0.17, 0.21 um", "ridge", True, (0.13, 0.17, 0.21), 0.75, "flattened"),
    ("P2", "ridge, sigmas 0.17, 0.21, 0.26 um (primary)", "ridge", True, (0.17, 0.21, 0.26), 0.75,
     "flattened"),
    ("P3", "ridge, one scale per image chosen from the image", "ridge", True, None, 0.75, "flattened"),
    ("P4", "P2 with the low cut at 0.9 of the high cut", "ridge", True, (0.17, 0.21, 0.26), 0.90,
     "flattened"),
    ("P5", "P2 with gap bridging off", "ridge", False, (0.17, 0.21, 0.26), 0.75, "flattened"),
    ("N", "P2 on the notch filtered image", "ridge", True, (0.17, 0.21, 0.26), 0.75, "notched"),
]
VARIANT_KEYS = [v[0] for v in VARIANTS]
VARIANT_LABELS = {v[0]: v[1] for v in VARIANTS}
PRIMARY = "P2"

# P3 searches this range of scales, in micrometres, in these steps. The range
# brackets what the pixel size allows a thread to be: 0.10 um is below one pixel
# and 0.35 um is well above the published diameters, so the best scale is found
# inside the range and not at one of its ends. The step is 0.2 px.
P3_SIGMA_MIN_UM = 0.10
P3_SIGMA_MAX_UM = 0.35
P3_SIGMA_STEP_UM = 0.026
# The statistic is taken over the strongest this share of pixels, so it describes
# the threads and not the background that covers most of the frame.
P3_TOP_FRACTION = 0.02


def p3_candidates_um() -> list:
    """The scales P3 tries, in micrometres."""
    n = int(np.floor((P3_SIGMA_MAX_UM - P3_SIGMA_MIN_UM) / P3_SIGMA_STEP_UM + 1e-9)) + 1
    return [round(P3_SIGMA_MIN_UM + i * P3_SIGMA_STEP_UM, 6) for i in range(n)]


def choose_sigma_um(flattened: np.ndarray, lacuna_mask: np.ndarray, flagged: np.ndarray,
                    params) -> tuple:
    """The scale this image answers to best, and the table of what each scale gave.

    The response skimage.filters.sato returns is already scale normalised, so it
    is used as it stands. This was checked rather than assumed: on synthetic
    Gaussian ridges of known width the raw response peaks at a scale of about 0.6
    times the full width at half maximum and follows the width (1.2 px for a 2 px
    ridge, 1.8 px for 3 px, 3.6 px for 6 px), while multiplying by the scale
    squared a second time makes the response climb without bound and the largest
    candidate always wins whatever the structure (4.4 px in all three cases). The
    statistic for a scale is therefore the median raw response over the strongest
    P3_TOP_FRACTION of pixels outside the lacunae and the vascular regions, and
    the chosen scale is the one with the largest statistic.

    Nothing about a published diameter enters this choice; it is read off the
    image."""
    valid = ~(lacuna_mask | flagged)
    rows = []
    best = (None, -np.inf)
    for sigma_um in p3_candidates_um():
        sigma_px = params.px(sigma_um)
        response = ridge.ridge_response(flattened, params, (sigma_px,))
        values = response[valid]
        if values.size == 0:
            statistic = 0.0
        else:
            cut = np.percentile(values, 100.0 * (1.0 - P3_TOP_FRACTION))
            strongest = values[values >= cut]
            statistic = float(np.median(strongest)) if strongest.size else 0.0
        rows.append({"sigma_um": sigma_um, "sigma_px": round(sigma_px, 4),
                     "scale_normalised_response_median_of_top": statistic})
        if statistic > best[1]:
            best = (sigma_um, statistic)
    return best[0], rows


def notch_available() -> tuple:
    """(is it usable, what it removes, why not). The notch filter of
    experiments/task1_artefact.py is imported and called as it stands; nothing in
    that file is edited. It is skipped if it cannot be imported."""
    import sys
    from pathlib import Path

    experiments = Path(__file__).resolve().parents[2] / "experiments"
    if str(experiments) not in sys.path:
        sys.path.insert(0, str(experiments))
    try:
        import task1_artefact
    except Exception as error:  # noqa: BLE001
        return False, None, f"{type(error).__name__}: {error}"
    bins = getattr(task1_artefact, "NOTCH_BINS", None)
    if not callable(getattr(task1_artefact, "notch", None)) or bins is None:
        return False, None, "experiments/task1_artefact.py has no usable notch function"
    axis = 1024
    described = []
    for du, dv in bins:
        if du == 0:
            continue
        period_px = axis / abs(du)
        described.append({"bin": [du, dv], "period_px": round(period_px, 4),
                          "period_um": round(period_px * PIXEL_SIZE_UM, 4),
                          "direction": "along x, constant along y" if dv == 0 else "other"})
    return True, described, None


def notched(flattened: np.ndarray) -> np.ndarray:
    """The flattened image with the periodic stripes removed, by the notch filter
    of experiments/task1_artefact.py, imported and called unchanged."""
    import task1_artefact

    return task1_artefact.notch(flattened)


def build(key: str, lac: dict, channel: np.ndarray, label: str, params,
          chosen_sigma_um: float | None = None) -> dict:
    """One variant's detection. Everything except the thresholded quantity, the
    scales and the two switches is the current method's own code."""
    _k, what, family, bridging, sigmas_um, low_fraction, source = next(v for v in VARIANTS if v[0] == key)
    lacuna_mask, lacuna_id_map = canaliculi.build_lacuna_maps(lac["labels"], lac["kept"])
    flagged = preprocess.vascular_mask(channel)
    flattened = preprocess.flatten(channel)
    lacuna_parameters = {**lacunae.parameters(), "computed_threshold_t_hi": lac["t_hi"]}

    if family == "current":
        candidate, cut = canaliculi.network_candidate_mask(flattened, lacuna_mask, flagged)
        thresholded = candidate
        skel = morphology.skeletonize(candidate)
        bridges = []
        if bridging:
            bridges = canaliculi.find_bridges(skel, flattened, cut, lacuna_mask | flagged)
            if bridges:
                candidate = canaliculi.apply_bridges(candidate, bridges)
                skel = morphology.skeletonize(candidate)
        network = {"variant": key, "what": what, "thresholded_quantity": "flattened intensity",
                   "gap_bridging": bridging, "high_cut": float(cut),
                   "low_cut": float(cut) * canaliculi.HYSTERESIS_LOW_FRACTION,
                   "ridge_source_image": None}
        source_image = flattened
    else:
        if key == "P3":
            sigmas_um = (chosen_sigma_um,)
        source_image = notched(flattened) if source == "notched" else flattened
        variant_params = replace(params, hysteresis_low_fraction=low_fraction)
        sigmas_px = tuple(params.px(s) for s in sigmas_um)
        response = ridge.ridge_response(source_image, variant_params, sigmas_px)
        candidate, cut = skeleton.ridge_network_mask(response, lacuna_mask, flagged, variant_params)
        thresholded = candidate
        skel = morphology.skeletonize(candidate)
        bridges = []
        if bridging:
            bridges = canaliculi.find_bridges(skel, response, cut, lacuna_mask | flagged)
            if bridges:
                candidate = canaliculi.apply_bridges(candidate, bridges)
                skel = morphology.skeletonize(candidate)
        network = {
            "variant": key, "what": what,
            "thresholded_quantity": "multiscale ridge response (skimage.filters.sato, bright ridges)",
            "gap_bridging": bridging, "sigmas_um": list(sigmas_um),
            "sigmas_px": [round(s, 4) for s in sigmas_px],
            "hysteresis_low_fraction": low_fraction, "high_cut": float(cut),
            "low_cut": float(cut) * low_fraction,
            "ridge_source_image": "notch filtered flattened channel" if source == "notched"
            else "flattened channel",
        }

    dist_to_lacuna, nearest_id = canaliculi.nearest_lacuna_map(lacuna_id_map)
    own = canaliculi.build_ownership(lac["kept"], skel, dist_to_lacuna, nearest_id)
    detection = metrics.detection_dict(label, lacuna_id_map, candidate, candidate & ~thresholded, skel,
                                       flagged, own, len(bridges), lacuna_parameters, network)
    detection["owner_map"] = own["owner_map"]
    detection["bridges"] = bridges
    detection["flattened"] = flattened
    detection["source_image"] = source_image
    detection["lacuna_mask"] = lacuna_mask
    return detection


def reference(image_path, lac: dict, channel: np.ndarray) -> dict:
    """Variant A straight from the pipeline, so the reference is the pipeline and
    not a copy of it."""
    import quantification

    detected = canaliculi.analyse_network(image_path, lac, channel)
    detection = quantification.detection_in_memory(detected)
    detection["owner_map"] = detected["owner_map"]
    detection["bridges"] = detected["bridges"]
    detection["flattened"] = canaliculi.preprocess_channel(channel)
    detection["source_image"] = detection["flattened"]
    detection["lacuna_mask"] = detection["lacuna_id_map"] > 0
    return detection


# The measures
# Everything the pipeline already measures is measured by src/quantification.py,
# the same code for every variant. The width on the image, the contrast and the
# smoothed straight runs are added here.

def usable_for_width(detection: dict, params) -> np.ndarray:
    """The skeleton pixels a width profile may be taken at: on the thresholded
    mask, not drawn by bridging, outside the lacuna buffer, outside the vascular
    mask with its dilation, and not a junction."""
    skel = detection["skeleton"]
    buffer_px = params.px_int(params.lacuna_buffer_um)
    buffered = morphology.dilation(detection["lacuna_mask"], morphology.disk(buffer_px))
    return (skel & detection["thresholded"] & ~detection["bridged"] & ~buffered
            & ~detection["vascular"] & ~widthprofile.junction_mask(skel))


def smoothed_straight_run_fraction(skel: np.ndarray, window: int = 5,
                                   min_run: int = ablation.STRAIGHT_RUN_MIN_PX,
                                   tolerance_px: float = 0.5) -> float | None:
    """The share of skeleton path points that lie in an axis-aligned run after the
    path is smoothed.

    A one pixel line drawn on a pixel grid has to step, so a straight run counter
    on the raw pixels partly measures the grid and not the structure. Here each
    branch of the skeleton is taken as an ordered path (skan, the same library the
    pipeline uses to build its graph), the path coordinates are smoothed with a
    moving average of `window` points, and a point counts when it lies in a stretch
    of at least `min_run` consecutive smoothed points whose rows, or whose columns,
    span less than `tolerance_px`. A staircase that is really a diagonal smooths
    into a diagonal and is not counted; a genuinely straight run stays straight."""
    from skan import Skeleton

    if not skel.any():
        return None
    try:
        paths = Skeleton(skel)
    except Exception:  # noqa: BLE001  a skeleton with no branch at all
        return None
    total = marked = 0
    box = np.ones(window) / window
    for index in range(paths.n_paths):
        coords = paths.path_coordinates(index)
        n = len(coords)
        total += n
        if n < min_run:
            continue
        smooth = np.empty_like(coords, dtype=float)
        for axis in (0, 1):
            padded = np.pad(coords[:, axis].astype(float), (window // 2, window // 2), mode="edge")
            smooth[:, axis] = np.convolve(padded, box, mode="valid")[:n]
        in_run = np.zeros(n, dtype=bool)
        for start in range(0, n - min_run + 1):
            stop = start + min_run
            piece = smooth[start:stop]
            if (np.ptp(piece[:, 0]) < tolerance_px) or (np.ptp(piece[:, 1]) < tolerance_px):
                in_run[start:stop] = True
        marked += int(in_run.sum())
    return round(marked / total, 6) if total else None


def measure_variant(key: str, detection: dict, image_path, params, legacy_cut: float,
                    precision: int = 4) -> dict:
    """Every measure of one variant on one image."""
    import quantification

    measured = metrics.measure(detection, image_path, params)
    skel = detection["skeleton"]

    # Width on the image.
    usable = usable_for_width(detection, params)
    profile = widthprofile.measure(detection["flattened"], skel, usable)
    width = widthprofile.summarise(profile["width_px"], profile["ok"], profile["n_candidates"],
                                   params.pixel_size_um, precision)

    # Contrast against the noise of this variant's own background.
    exclude = detection["lacuna_mask"] | detection["vascular"] | detection["thresholded"]
    noise = widthprofile.noise_level(detection["flattened"], exclude)
    snr = widthprofile.contrast(detection["flattened"], profile["rows"], profile["cols"],
                                profile["normal_r"], profile["normal_c"], noise)
    finite = snr[np.isfinite(snr)]
    contrast = {
        "noise_level": round(noise, 8),
        "contrast_snr_median": round(float(np.median(finite)), precision) if finite.size else None,
        "contrast_snr_p10": round(float(np.percentile(finite, 10)), precision) if finite.size else None,
        "low_contrast_fraction": (round(float((finite < widthprofile.LOW_CONTRAST_SNR).mean()), precision)
                                  if finite.size else None),
        "contrast_pixels_used": int(finite.size),
    }

    # Artifact measures: the straight runs raw and smoothed, the rectangles, and
    # the legacy support measure kept only for continuity.
    artifacts = ablation.artifact_measures(detection, detection["flattened"], legacy_cut)
    artifacts["legacy_unsupported_fraction"] = artifacts.pop("unsupported_fraction")
    artifacts["legacy_unsupported_px"] = artifacts.pop("unsupported_px")
    artifacts["straight_run_fraction_smoothed"] = smoothed_straight_run_fraction(skel)

    return {"variant": key, "measured": measured, "width": width, "contrast": contrast,
            "artifacts": artifacts, "profile": profile, "usable": usable}


MEASURE_COLUMNS = [
    "image_label", "variant", "what", "pixel_size_label",
    # The width, on the image and on the mask, side by side.
    "width_fwhm_median_px", "width_fwhm_median_um", "width_fwhm_p10_px", "width_fwhm_p10_um",
    "width_fwhm_p90_px", "width_fwhm_p90_um", "width_fwhm_pixels_used", "width_fwhm_failure_fraction",
    "width_dt_median_px", "width_dt_median_um", "width_dt_p10_px", "width_dt_p90_px",
    # Support, neutral and legacy.
    "contrast_snr_median", "contrast_snr_p10", "low_contrast_fraction", "contrast_pixels_used",
    "noise_level", "legacy_unsupported_fraction",
    # Shape of the traced network.
    "straight_run_fraction", "straight_run_fraction_smoothed", "rectangle_count",
    "skeleton_px", "bridged_fraction", "n_bridges",
    # Everything the pipeline measures.
    "field_length_density_per_px", "field_length_density_um_per_um2",
    "roots_per_cell", "ring_length_r30_px_per_cell", "ring_length_r30_um_per_cell",
    "ring_length_r60_px_per_cell", "ring_length_r60_um_per_cell",
    "junction_count", "junction_density_per_um2", "thread_end_fraction",
    "connected_to_lacuna_fraction", "median_edge_length_px", "median_edge_length_um",
    "mean_edge_length_px", "mean_edge_length_um",
    "lacuna_count", "interior_lacuna_count",
    # What the variant was.
    "sigmas_um", "sigmas_px", "hysteresis_low_fraction", "gap_bridging", "ridge_source_image",
]

SUMMARY_MEASURES = [
    "width_fwhm_median_um", "width_dt_median_um", "low_contrast_fraction", "contrast_snr_median",
    "straight_run_fraction", "straight_run_fraction_smoothed", "rectangle_count",
    "connected_to_lacuna_fraction", "junction_count", "thread_end_fraction",
    "field_length_density_um_per_um2", "roots_per_cell", "skeleton_px", "n_bridges",
    "legacy_unsupported_fraction",
]


def measure_row(label: str, result: dict, detection: dict) -> list:
    """One row of v2_all_images, in MEASURE_COLUMNS order."""
    comparison = result["measured"]["comparison"]
    network = detection["canaliculi_detection"]["parameters"]
    row = {
        "image_label": label,
        "variant": result["variant"],
        "what": VARIANT_LABELS[result["variant"]],
        "pixel_size_label": params_mod.PIXEL_LABEL,
        "width_dt_median_px": comparison.get("width_median_px"),
        "width_dt_median_um": comparison.get("width_median_um"),
        "width_dt_p10_px": comparison.get("width_p10_px"),
        "width_dt_p90_px": comparison.get("width_p90_px"),
        "sigmas_um": ", ".join(str(s) for s in network.get("sigmas_um", [])) or None,
        "sigmas_px": ", ".join(str(s) for s in network.get("sigmas_px", [])) or None,
        "hysteresis_low_fraction": network.get("hysteresis_low_fraction"),
        "gap_bridging": network.get("gap_bridging"),
        "ridge_source_image": network.get("ridge_source_image"),
        **result["width"], **result["contrast"], **result["artifacts"], **comparison,
    }
    return [row.get(c) for c in MEASURE_COLUMNS]


# Running it

OUT_DIR = Path(__file__).resolve().parents[2] / "results_experiments" / "canal_physical_v2"
CANAL_PHYSICAL_DIR = Path(__file__).resolve().parents[2] / "results_experiments" / "canal_physical"
# The two panel comparison holds two full panels side by side, so it is drawn at
# a smaller upscale than the single panels to stay inside the file size budget.
COMPARE_UPSCALE = 2
# Which tiles get a width check figure.
WIDTH_FIGURE_TILES = (1, 2)


def zoom_boxes(label: str) -> list:
    """The three tiles the first comparison chose. Not chosen again here."""
    path = CANAL_PHYSICAL_DIR / label / f"{label}_canal_physical.json"
    boxes = json.loads(path.read_text(encoding="utf-8"))["zoom_boxes"]
    return [(b["row"], b["col"], b["side_px"], b["skeleton_px_difference"]) for b in boxes]


def compare_with_results(label: str, measured: dict) -> list:
    """Variant A against results/<label>/5_quantification/, at tolerance 0."""
    import quantification

    committed = json.loads(quantification.quant_path(config.RESULTS_DIR, label, ".json")
                           .read_text(encoding="utf-8"))
    diffs = []

    def walk(a, b, where):
        if isinstance(a, dict):
            for key, value in a.items():
                walk(value, (b or {}).get(key), f"{where}.{key}" if where else key)
        elif isinstance(a, list):
            for i, value in enumerate(a):
                walk(value, b[i] if isinstance(b, list) and i < len(b) else None, f"{where}[{i}]")
        else:
            if isinstance(a, bool) or isinstance(b, bool):
                same = a == b
            elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
                same = a == b or (a != a and b != b)
            else:
                same = a == b
            if not same:
                diffs.append((where, a, b))

    for key, value in (("lacuna_count", measured["lacuna_count"]),
                       ("interior_lacuna_count", measured["interior_lacuna_count"]),
                       ("n_bridges", measured["n_bridges"]),
                       ("summary", measured["summary"]), ("field", measured["field"]),
                       ("width", measured["width"]), ("lacunae", measured["rows"])):
        walk(committed.get(key), value, key)
    return diffs


def verification_matches_pipeline(label: str, path: Path) -> tuple:
    from skimage.io import imread

    committed = lacunae.result_path(config.RESULTS_DIR, label, config.SECTION_CANALICULI,
                                    config.SUFFIX_CANALICULI_VERIFICATION)
    if not committed.is_file():
        return False, f"{committed} is missing"
    a, b = np.asarray(imread(path)), np.asarray(imread(committed))
    if a.shape != b.shape or not np.array_equal(a, b):
        return False, "differs from the committed verification image"
    return True, "pixel identical"


def write_figures(label: str, display, detections: dict, results: dict, lac: dict, params,
                  out_dir: Path, compact: bool = False) -> dict:
    """Every figure of one image. Returns what the checks need.

    With `compact`, three things shrink to fit the size budget, and nothing else
    changes: the comparison is drawn at one times instead of two, its pdf is
    rasterised at a lower resolution, and the pipeline style picture of variant A
    is checked but not kept, because it is a byte for byte duplicate of
    results/<label>/2_canaliculi/<label>_canaliculi_verification.png."""
    from canal_physical import figures_v2 as fig

    folder = out_dir / label
    colors = canaliculi.lacuna_colors(len(lac["kept"]))
    caption = f"{params_mod.PIXEL_LABEL}, pre-validation"

    fig.full_panel(display, None, colors, params.pixel_size_um, folder / f"{label}_v2_raw.png")
    for key in ("A", PRIMARY):
        fig.full_panel(display, detections[key], colors, params.pixel_size_um,
                       folder / f"{label}_v2_{key}.png")

    # Two panels in one file, at a smaller upscale so the file stays in budget.
    upscale = 1 if compact else COMPARE_UPSCALE
    left = fig.draw_skeleton(display, detections["A"]["skeleton"], detections["A"]["owner_map"],
                             detections["A"]["lacuna_id_map"], colors, upscale)
    right = fig.draw_skeleton(display, detections[PRIMARY]["skeleton"], detections[PRIMARY]["owner_map"],
                              detections[PRIMARY]["lacuna_id_map"], colors, upscale)
    gap = np.zeros((left.shape[0], 8, 3), dtype=left.dtype)
    both = np.concatenate([fig.add_scale_bar(left, params.pixel_size_um, upscale), gap,
                           fig.add_scale_bar(right, params.pixel_size_um, upscale)], axis=1)
    reserved = list(colors.values()) + [fig.UNOWNED_COLOUR, (255, 255, 255)]
    compare_png = folder / f"{label}_v2_compare_A_{PRIMARY}.png"
    fig.save_png(both, compare_png, reserved)
    # The pdf embeds the picture that was just written, which already has its
    # colours reduced to a palette, rather than the full colour array. The pdf
    # has no palette of its own, so embedding the reduced version is what keeps
    # it near the size of the png instead of twice it.
    from skimage.io import imread

    save_compare_pdf(np.asarray(imread(compare_png))[..., :3], label,
                     folder / f"{label}_v2_compare_A_{PRIMARY}.pdf", caption)

    boxes = zoom_boxes(label)
    for i, box in enumerate(boxes, start=1):
        fig.tile_row(display, detections, VARIANT_KEYS, VARIANT_LABELS, box, colors,
                     params.pixel_size_um,
                     f"{label} tile {i} at row {box[0]}, column {box[1]}, "
                     f"{params.um(box[2]):g} um square. {caption}. One pixel skeleton, "
                     f"owned threads in the lacuna's colour, the rest in grey.",
                     folder / f"{label}_v2_tile{i}_variants.png")
        if i in WIDTH_FIGURE_TILES:
            fig.width_check_figure(display, results[PRIMARY]["profile"], box, params.pixel_size_um,
                                   f"{label} tile {i}: the normals the width was sampled along, "
                                   f"variant {PRIMARY}. Red dot is the skeleton pixel, green line is "
                                   f"the profile. {caption}",
                                   folder / f"{label}_v2_tile{i}_width_check.png")

    pipeline_dir = folder / "pipeline_style"
    checks = {}
    primary_path = pipeline_dir / f"{label}_verification_{PRIMARY}_pipeline_style.png"
    fig.pipeline_style(lac, display, detections[PRIMARY], primary_path)
    if compact:
        from skimage.io import imread

        fig.save_png(np.asarray(imread(primary_path)), primary_path,
                     list(colors.values()) + [(0, 255, 0), (255, 255, 255)])
    path = pipeline_dir / f"{label}_verification_A_pipeline_style.png"
    if compact:
        # Written to a temporary place, checked, and not kept: it is identical to
        # the committed one, so shipping it again would only cost space.
        import tempfile

        temporary = Path(tempfile.gettempdir()) / f"{label}_verification_A_check.png"
        fig.pipeline_style(lac, display, detections["A"], temporary)
        checks["verification"] = verification_matches_pipeline(label, temporary)
        temporary.unlink(missing_ok=True)
    else:
        fig.pipeline_style(lac, display, detections["A"], path)
        checks["verification"] = verification_matches_pipeline(label, path)
    return checks


def save_compare_pdf(image: np.ndarray, label: str, path: Path, caption: str, dpi: int = 200) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    height, width = image.shape[:2]
    fig = plt.figure(figsize=(width / dpi, height / dpi))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.imshow(image, interpolation="nearest")
    ax.set_axis_off()
    fig.text(0.01, 0.985, f"{label}: current method (left) and {PRIMARY} (right). {caption}",
             fontsize=7, color="white", va="top")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, metadata={"CreationDate": None, "Producer": "", "Creator": ""})
    plt.close(fig)


def fixed_workbook(wb, path: Path) -> None:
    """Save a workbook whose bytes depend only on its contents, and check it
    opens afterwards."""
    import datetime
    import re
    import shutil
    import zipfile

    from openpyxl import load_workbook

    stamp = datetime.datetime(1980, 1, 1)
    wb.properties.created = stamp
    wb.properties.modified = stamp
    wb.properties.creator = ""
    wb.properties.lastModifiedBy = ""
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    fixed = b"1980-01-01T00:00:00Z"
    tmp = path.with_name(path.name + ".tmp")
    with zipfile.ZipFile(path) as src, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in sorted(src.infolist(), key=lambda i: i.filename):
            data = src.read(info.filename)
            if info.filename == "docProps/core.xml":
                data = re.sub(rb"(<dcterms:(?:created|modified)[^>]*>)[^<]*", rb"\g<1>" + fixed, data)
            entry = zipfile.ZipInfo(info.filename, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = info.external_attr
            dst.writestr(entry, data)
    shutil.move(str(tmp), str(path))
    load_workbook(path)  # it must open, or this raises here rather than for the reader


def write_tables(rows: list, out_dir: Path, params) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "v2_all_images.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(MEASURE_COLUMNS)
        writer.writerows(rows)

    index = {c: i for i, c in enumerate(MEASURE_COLUMNS)}
    means = {}
    for key in VARIANT_KEYS:
        taken = [r for r in rows if r[index["variant"]] == key]
        means[key] = {}
        for name in SUMMARY_MEASURES:
            values = [r[index[name]] for r in taken
                      if isinstance(r[index[name]], (int, float)) and r[index[name]] is not None]
            means[key][name] = float(np.mean(values)) if values else None

    summary_rows = []
    for key in VARIANT_KEYS:
        for name in SUMMARY_MEASURES:
            value, base = means[key][name], means["A"][name]
            change = (round(100.0 * (value - base) / base, 2)
                      if value is not None and base not in (None, 0) else None)
            summary_rows.append([key, VARIANT_LABELS[key], name,
                                 None if value is None else round(value, 6),
                                 None if base is None else round(base, 6), change])
    with open(out_dir / "v2_summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["variant", "what", "measure", "mean_over_8_images", "variant_A_mean",
                         "percent_change_from_A"])
        writer.writerows(summary_rows)

    from openpyxl import Workbook

    wb = Workbook()
    sheet = wb.active
    sheet.title = "per_image"
    sheet.append(MEASURE_COLUMNS)
    for row in rows:
        sheet.append(row)
    s = wb.create_sheet("summary")
    s.append(["variant", "what", "measure", "mean_over_8_images", "variant_A_mean",
              "percent_change_from_A"])
    for row in summary_rows:
        s.append(row)
    notes = wb.create_sheet("notes")
    for line in notes_lines(params):
        notes.append([line])
    fixed_workbook(wb, out_dir / "v2_all_images.xlsx")
    write_pdfs(rows, summary_rows, means, out_dir, params)
    return means


def notes_lines(params) -> list:
    return [
        params_mod.PIXEL_LABEL + ".",
        "Pre-validation: no number here has been checked against a manual count.",
        "A diagnosis and a better founded experiment. No variant is called better than another.",
        "width_fwhm_*: the full width at half maximum of the intensity profile across the thread, taken",
        "  on the flattened image along the normal at each usable skeleton pixel. It INCLUDES the optical",
        "  blur, so it is an apparent width in the image and an upper bound on the diameter, not the",
        "  diameter. No point spread function is computed or subtracted: the numerical aperture, the",
        "  emission wavelength and the pinhole are unknown.",
        "width_dt_*: the older measure, twice the distance transform of the mask, kept beside it. It can",
        "  only return the width of the mask it is given.",
        "contrast_snr: the intensity at a skeleton pixel minus the median intensity 4 to 6 px away along",
        "  the normal on both sides, over the noise, where the noise is 1.4826 times the median absolute",
        "  deviation of the flattened image outside the lacunae, the vascular regions and that variant's",
        "  own mask. low_contrast_fraction is the share below 2.",
        "legacy_unsupported_fraction: the earlier measure, which used the CURRENT method's own threshold",
        "  and so favoured the current method. Kept only so the earlier tables can be followed.",
        "straight_run_fraction: share of skeleton pixels in an axis-aligned run of at least 8 px. A thin",
        "  skeleton on a pixel grid contains straight runs by its nature, and the current method already",
        "  scores about 0.22, so only differences between variants mean anything here.",
        "straight_run_fraction_smoothed: the same after each branch path is smoothed with a 5 point",
        "  moving average, which removes most of the pixel grid effect.",
    ]


def write_pdfs(rows: list, summary_rows: list, means: dict, out_dir: Path, params) -> None:
    import quantification
    from matplotlib.backends.backend_pdf import PdfPages

    header = [
        "Canalicular method rebuilt around the physical scale",
        "=" * 52,
        f"PIXEL SIZE {params.pixel_size_um} um/px. {params_mod.PIXEL_LABEL.upper()}.",
        "PRE-VALIDATION. No variant is called better than another.",
        "",
        "Variants:",
    ]
    header += [f"  {k:3s} {VARIANT_LABELS[k]}" for k in VARIANT_KEYS] + [""]

    summary_lines = ["Mean over the 8 images", "-" * 22]
    table = [[name] + ["" if means[k][name] is None else f"{means[k][name]:.4g}" for k in VARIANT_KEYS]
             for name in SUMMARY_MEASURES]
    summary_lines += quantification.text_table(["measure"] + VARIANT_KEYS, table)
    summary_lines += ["", "Change from A, per cent", "-" * 23]
    table = []
    for name in SUMMARY_MEASURES:
        row = [name]
        for k in VARIANT_KEYS:
            value, base = means[k][name], means["A"][name]
            row.append("" if value is None or base in (None, 0) else f"{100 * (value - base) / base:+.1f}")
        table.append(row)
    summary_lines += quantification.text_table(["measure"] + VARIANT_KEYS, table)
    summary_lines += [""] + notes_lines(params)

    with PdfPages(out_dir / "v2_summary.pdf", metadata={"CreationDate": None, "Producer": "",
                                                        "Creator": ""}) as pdf:
        quantification._text_pages(pdf, summary_lines, header)

    index = {c: i for i, c in enumerate(MEASURE_COLUMNS)}
    show = ["width_fwhm_median_um", "width_dt_median_um", "low_contrast_fraction",
            "straight_run_fraction", "straight_run_fraction_smoothed", "rectangle_count",
            "connected_to_lacuna_fraction", "junction_count", "field_length_density_um_per_um2",
            "roots_per_cell", "skeleton_px", "n_bridges"]
    lines = summary_lines + ["", "Every image and variant", "-" * 23]
    table = [[r[index["image_label"]], r[index["variant"]]]
             + [("" if r[index[c]] is None else f"{r[index[c]]:.4g}") for c in show] for r in rows]
    lines += quantification.text_table(["image", "v"] + show, table)
    with PdfPages(out_dir / "v2_all_images.pdf", metadata={"CreationDate": None, "Producer": "",
                                                           "Creator": ""}) as pdf:
        quantification._text_pages(pdf, lines, header)


def write_image_json(label: str, params, results: dict, detections: dict, p3: dict, checks: dict,
                     out_dir: Path) -> None:
    payload = {
        "status": "pre-validation",
        "pixel_size_label": params_mod.PIXEL_LABEL,
        "pixel_size_um": params.pixel_size_um,
        "image_label": label,
        "note": ("The experimental method rebuilt around the physical scale. Scales are set in "
                 "micrometres or chosen from the image, never from the earlier mask and never from a "
                 "published value. The width is measured on the image, not on the mask, and includes "
                 "the optical blur, so it is an upper bound on the diameter. No variant is called "
                 "better than another."),
        "variants": VARIANT_LABELS,
        "p3_scale_choice": p3,
        "measures": {k: results[k]["measured"]["comparison"] for k in results},
        "width_on_the_image": {k: results[k]["width"] for k in results},
        "contrast": {k: results[k]["contrast"] for k in results},
        "artifacts": {k: results[k]["artifacts"] for k in results},
        "parameters": {k: detections[k]["canaliculi_detection"]["parameters"] for k in detections},
        "lengths_in_um_and_px": [{"parameter": n, "um": um, "px": px, "what": w}
                                 for n, um, px, w in params.table()],
        "checks": checks,
        "provenance": {**lacunae.provenance(), "pixel_size_um": params.pixel_size_um,
                       "pixel_size_label": params_mod.PIXEL_LABEL},
    }
    path = out_dir / label / f"{label}_v2.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, default=float)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="The canalicular experiment rebuilt around the physical scale (pre-validation, "
                    "pixel size 0.13 um/px rounded and unconfirmed). Not a claim of improvement.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--image", type=Path, help="One .tif image.")
    group.add_argument("--dir", type=Path, help="A folder of .tif images.")
    parser.add_argument("-o", "--out", type=Path, default=OUT_DIR, help="Output folder.")
    parser.add_argument("--no-tiles", action="store_true", help="Skip the blind trace tiles.")
    parser.add_argument("--compact", action="store_true",
                        help="Fit the size budget: the comparison at one times with a lighter pdf, "
                             "and the pipeline style picture of variant A checked but not kept, since "
                             "it duplicates the committed one.")
    args = parser.parse_args()

    params = params_mod.DEFAULT
    usable, notch_bins, why = notch_available()
    keys = [k for k in VARIANT_KEYS if k != "N" or usable]
    print(f"Pixel size {params.pixel_size_um} um/px. {params_mod.PIXEL_LABEL}.")
    print(f"Field 1024 px = {1024 * params.pixel_size_um:g} um.")
    for key in keys:
        print(f"  {key:3s} {VARIANT_LABELS[key]}")
    if usable:
        print("  N runs: the notch filter of experiments/task1_artefact.py imports and is called "
              "unchanged. It removes "
              + "; ".join(f"period {b['period_px']:g} px = {b['period_um']:g} um {b['direction']}"
                          for b in notch_bins))
    else:
        print(f"  N skipped: {why}")
    print()

    image_paths = {lacunae.image_label(p): p for p in
                   ([args.image] if args.image else sorted(args.dir.glob("*.tif")))}
    rows, failures, p3_choices = [], [], {}
    for label, path in image_paths.items():
        lac = lacunae.analyse_image(path)
        display, channel = lacunae.load_channel(path)
        lacuna_mask, _ = canaliculi.build_lacuna_maps(lac["labels"], lac["kept"])
        flagged = preprocess.vascular_mask(channel)
        flattened = preprocess.flatten(channel)

        chosen_um, table = choose_sigma_um(flattened, lacuna_mask, flagged, params)
        at_edge = chosen_um in (p3_candidates_um()[0], p3_candidates_um()[-1])
        p3_choices[label] = {"chosen_sigma_um": chosen_um, "chosen_sigma_px": round(params.px(chosen_um), 4),
                             "at_the_edge_of_the_search_range": at_edge, "candidates": table}

        detections, results = {}, {}
        for key in keys:
            detections[key] = (reference(path, lac, channel) if key == "A"
                               else build(key, lac, channel, label, params, chosen_um))
        _m, legacy_cut = canaliculi.total_signal_mask(detections["A"]["flattened"])
        for key in keys:
            results[key] = measure_variant(key, detections[key], path, params, legacy_cut)
            rows.append(measure_row(label, results[key], detections[key]))

        diffs = compare_with_results(label, results["A"]["measured"])
        checks = write_figures(label, display, detections, results, lac, params, args.out,
                               args.compact)
        checks["variant_A_against_results"] = {"ok": not diffs, "differences": len(diffs)}
        checks["variant_A_verification"] = {"ok": checks["verification"][0],
                                            "detail": checks["verification"][1]}
        checks.pop("verification")
        if diffs:
            failures.append((label, "variant A differs from results/", len(diffs)))
        if not checks["variant_A_verification"]["ok"]:
            failures.append((label, "variant A verification image differs",
                             checks["variant_A_verification"]["detail"]))
        write_image_json(label, params, results, detections, p3_choices[label], checks, args.out)

        print(f"{label}: A against results/ {'PASS' if not diffs else f'FAIL {len(diffs)}'}; "
              f"A verification {checks['variant_A_verification']['detail']}; "
              f"P3 sigma {chosen_um} um = {params.px(chosen_um):.2f} px"
              + ("  (at the edge of the search range)" if at_edge else ""))
        for key in keys:
            w = results[key]["width"]
            a = results[key]["artifacts"]
            c = results[key]["contrast"]
            print(f"   {key:3s} fwhm {str(w['width_fwhm_median_um']):>7s} um  dt "
                  f"{str(results[key]['measured']['comparison'].get('width_median_um')):>7s} um  "
                  f"low contrast {str(c['low_contrast_fraction']):>7s}  straight "
                  f"{str(a['straight_run_fraction']):>7s} / {str(a['straight_run_fraction_smoothed']):>7s}")

    means = write_tables(rows, args.out, params)
    if not args.no_tiles:
        from canal_physical import tiles as tile_module

        all_paths = {lacunae.image_label(p): p for p in sorted(Path("data/WT").glob("*.tif"))}
        tile_rows = tile_module.write_tiles(all_paths, CANAL_PHYSICAL_DIR, args.out / "trace_tiles",
                                            params)
        tile_module.write_instructions(tile_rows, args.out / "trace_tiles", params)
    write_readme(args.out, params, image_paths, means, p3_choices, usable, notch_bins, why)

    print(f"\ntables -> {args.out / 'v2_all_images.xlsx'}, .csv, .pdf and the summary")
    if failures:
        print("FAIL:")
        for f in failures:
            print("  ", *f)
        raise SystemExit(1)
    print("PASS: variant A equals results/ at tolerance 0 and its pipeline style verification image "
          "is pixel identical")




def write_readme(out_dir: Path, params, image_paths: dict, means: dict, p3_choices: dict,
                 notch_ok: bool, notch_bins, notch_why) -> None:
    import platform
    from importlib import metadata

    versions = {"python": platform.python_version()}
    for package in ("numpy", "scipy", "scikit-image", "networkx", "skan", "matplotlib", "openpyxl",
                    "pillow"):
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = None
    prov = lacunae.provenance()
    lines = [
        "# The canalicular experiment on the physical scale",
        "",
        f"**{params_mod.PIXEL_LABEL}.** Pre-validation: no number here has been checked against a",
        "manual count. Branch `canal-physical-v2`. **No variant is called better than another**, and",
        "nothing was tuned to improve any result or to approach any published value.",
        "",
        "## Why this exists",
        "",
        f"At {params.pixel_size_um} um/px a canaliculus of 0.2 to 0.4 um is about 1.5 to 3 px across, and about",
        "2.5 to 4 px once the optics have blurred it. The masks of the current method have a median",
        "distance transform width of 6.0 px (0.78 um) and the first ridge variants 7.4 px, so both are",
        "roughly twice that. The scales of those first variants came from a half width measured on the",
        "already inflated mask, which is circular: the mask set the scale and the scale set the mask.",
        "",
        "Here every scale is set in micrometres from the pixel size, or chosen from the image itself, and",
        "the width is measured on the image rather than on the mask.",
        "",
        "## Variants",
        "",
        "Fixed before the first run, all reported, none chosen afterwards. The lacunae, the vascular",
        "handling, the graph cleanup, the ownership and the ring radii are the current method's in every",
        "one, so only the named difference can move a number.",
        "",
        "| variant | what | sigmas (um) | sigmas (px) | low cut | bridging |",
        "|---|---|---|---|---|---|",
    ]
    for key, what, family, bridging, sigmas_um, low, _source in VARIANTS:
        if key == "N" and not notch_ok:
            continue
        if family == "current":
            lines.append(f"| {key} | {what} | | | {canaliculi.HYSTERESIS_LOW_FRACTION} | "
                         f"{'yes' if bridging else 'no'} |")
        elif key == "P3":
            lines.append(f"| {key} | {what} | chosen per image | chosen per image | {low} | "
                         f"{'yes' if bridging else 'no'} |")
        else:
            lines.append(f"| {key} | {what} | {', '.join(str(s) for s in sigmas_um)} | "
                         f"{', '.join(str(round(params.px(s), 3)) for s in sigmas_um)} | {low} | "
                         f"{'yes' if bridging else 'no'} |")
    lines += [
        "",
        "### The scale P3 chose, per image",
        "",
        "| image | sigma (um) | sigma (px) | at the edge of the search range |",
        "|---|---|---|---|",
    ]
    for label, choice in p3_choices.items():
        lines.append(f"| {label} | {choice['chosen_sigma_um']} | {choice['chosen_sigma_px']} | "
                     f"{'yes' if choice['at_the_edge_of_the_search_range'] else 'no'} |")
    lines += [
        "",
        f"P3 searches {P3_SIGMA_MIN_UM} to {P3_SIGMA_MAX_UM} um in steps of {P3_SIGMA_STEP_UM} um "
        f"({round(params.px(P3_SIGMA_STEP_UM), 2)} px) and takes the scale whose response is largest,",
        f"as the median over the strongest {P3_TOP_FRACTION:.0%} of pixels outside the lacunae and the vascular",
        "regions. The response of `skimage.filters.sato` is already scale normalised, which was checked on",
        "synthetic ridges rather than assumed: the raw response peaks at about 0.6 times the full width at",
        "half maximum and follows the width, while multiplying by the scale squared a second time makes",
        "the largest candidate win whatever the structure. Full tables are in each image's json.",
        "",
        "### The notch filter",
        "",
    ]
    if notch_ok:
        lines += ["Variant N runs. `experiments/task1_artefact.py` is imported and its `notch` is called",
                  "unchanged; nothing in that file is edited. It removes:", ""]
        for b in notch_bins:
            lines.append(f"- a period of {b['period_px']:g} px, which is {b['period_um']:g} um, "
                         f"{b['direction']}")
        lines += ["", "These are the two stripe frequencies that stand above the noise in every image, per",
                  "`results_experiments/task1/1.4_notch.md`. Each is removed with a Gaussian notch one bin",
                  "wide."]
    else:
        lines += [f"Variant N is **skipped**: {notch_why}. It is an open question in DECISIONS.md."]
    lines += [
        "",
        "## The new measures",
        "",
        "- **`width_fwhm_*`**: the width measured **on the image**. At every usable skeleton pixel the",
        "  flattened intensity is sampled along the normal to the thread, and the width is the full width",
        "  at half maximum of that profile. Bridged pixels, pixels off the mask, the lacuna buffer, the",
        "  vascular mask and junction pixels are left out. **It includes the optical blur**, so it is an",
        "  apparent width in the image and an **upper bound on the diameter**, not the diameter. No point",
        "  spread function is computed or subtracted anywhere: the numerical aperture, the emission",
        "  wavelength and the pinhole are unknown.",
        "- **`width_dt_*`**: the older measure, twice the distance transform of the mask, reported beside",
        "  it. It can only ever return the width of the mask it is given.",
        "- **`contrast_snr` and `low_contrast_fraction`**: the intensity at a skeleton pixel minus the",
        "  median intensity 4 to 6 px away along the normal on both sides, divided by the noise, where the",
        "  noise is 1.4826 times the median absolute deviation of the flattened image over pixels outside",
        "  the lacunae, the vascular regions and **that variant's own mask**. The same definition is used",
        "  for every variant including A, which the earlier support measure was not: that one used the",
        "  current method's own threshold and so favoured the current method. It is kept as",
        "  `legacy_unsupported_fraction` only so the earlier tables can still be followed.",
        "- **`straight_run_fraction`** is unchanged, and **`straight_run_fraction_smoothed`** is the same",
        "  after each branch path is smoothed with a 5 point moving average, which removes most of the",
        "  effect of drawing a thin line on a pixel grid. A one pixel skeleton contains straight runs by",
        "  its nature and the current method already scores about 0.22, so only the differences between",
        "  variants carry meaning.",
        "- Everything else is measured by `src/quantification.py`, the same code for every variant.",
        "",
        "## Figures",
        "",
        "The skeleton is drawn **one pixel wide**, never thickened, on an image upscaled by nearest",
        "neighbour so a one pixel line stays visible. Owned threads take their lacuna's colour, the",
        "pipeline's own colours; everything the ownership did not reach is light grey, so **nothing is",
        "hidden**. This is the opposite of the pipeline's verification style, which thickens the skeleton",
        "and draws only what is owned.",
        "",
        "| file | what |",
        "|---|---|",
        f"| `<label>/<label>_v2_raw.png` | the raw image, {figures_v2.FULL_UPSCALE}x, scale bar |",
        f"| `<label>/<label>_v2_A.png` | the current method, full size, {figures_v2.FULL_UPSCALE}x |",
        f"| `<label>/<label>_v2_{PRIMARY}.png` | the primary new variant, full size, "
        f"{figures_v2.FULL_UPSCALE}x |",
        f"| `<label>/<label>_v2_compare_A_{PRIMARY}.png` and `.pdf` | both side by side in one file, {COMPARE_UPSCALE}x |",
        "| `<label>/<label>_v2_tile<i>_variants.png` | one tile, raw then every variant, 8x |",
        "| `<label>/<label>_v2_tile<i>_width_check.png` | the normals the width was sampled along |",
        "| `<label>/pipeline_style/` | the pipeline's own picture for A and the primary variant |",
        "| `trace_tiles/` | raw tiles for a blind hand trace, with instructions |",
        "",
        "The full size panels and the comparison are written as indexed png with the skeleton colours",
        "held in reserved palette slots, so **every skeleton colour is exact** and only the background is",
        "quantised. A plain quantisation was measured first and moved all 14 overlay colours, which would",
        "have made the colours meaningless. The background error is a mean of about 1 level out of 255.",
        "",
        "## How it was run",
        "",
        "```",
        "python src/canal_physical/physical.py --dir data/WT",
        "```",
        "",
        f"Commit `{prov['git_commit']}`, tracked files clean: {not prov['git_dirty']}. Config hash "
        f"`{prov['config_hash']}`.",
        "",
        "## Every length, in micrometres and pixels",
        "",
        "| parameter | um | px | what |",
        "|---|---|---|---|",
    ]
    for name, um, px, what in params.table():
        lines.append(f"| `{name}` | {um} | {px if px is not None else ''} | {what} |")
    lines += [
        f"| `tophat_radius` (flattening) | {round(canaliculi.TOPHAT_RADIUS_PX * params.pixel_size_um, 4)} | "
        f"{canaliculi.TOPHAT_RADIUS_PX} | unchanged from the current method; see DECISIONS.md |",
        f"| `smooth_sigma` (flattening) | {round(canaliculi.SMOOTH_SIGMA_PX * params.pixel_size_um, 4)} | "
        f"{canaliculi.SMOOTH_SIGMA_PX} | unchanged from the current method |",
        "",
        "## Mean over the 8 images",
        "",
        "| measure | " + " | ".join(k for k in VARIANT_KEYS if k != "N" or notch_ok) + " |",
        "|---" * (len([k for k in VARIANT_KEYS if k != "N" or notch_ok]) + 1) + "|",
    ]
    for name in SUMMARY_MEASURES:
        cells = []
        for key in VARIANT_KEYS:
            if key == "N" and not notch_ok:
                continue
            value = means.get(key, {}).get(name)
            cells.append("" if value is None else f"{value:.4g}")
        lines.append(f"| `{name}` | " + " | ".join(cells) + " |")
    lines += ["", "## Versions", "", "```"]
    lines += [f"{name}: {value}" for name, value in versions.items()]
    lines += ["```", "", "## Images", ""]
    lines += [f"- {label} (`{path.name}`)" for label, path in image_paths.items()]
    path = out_dir / "README.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
