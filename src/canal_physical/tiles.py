"""Raw tiles for a blind hand trace.

Nothing any method produced is drawn on these. They are the raw image only, so a
trace made from them cannot be influenced by what the pipeline or the experiment
found. The scoring is not built here: these are the tiles and the instructions.

**Pixel size 0.13 um/px, rounded, unconfirmed per image.** Pre-validation.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

import lacunae

# A tile is this many pixels square, which is 26 um at 0.13 um/px: wide enough to
# hold several threads and the space between them, small enough to trace by hand.
TILE_SIDE_PX = 200
# The tile is upscaled by this for comfortable tracing. Nearest neighbour, so no
# pixel is invented.
TRACE_UPSCALE = 4

# Which image and which of its chosen tiles each trace tile is centred on. The
# first three are the images where the two methods disagree most; the fourth is a
# control, an image whose disagreement is among the smallest.
TILE_SOURCES = [
    ("542_z18", 1, "largest skeleton disagreement of the eight"),
    ("682_z08", 1, "second largest disagreement"),
    ("543-2", 1, "smallest disagreement of the three tuning images"),
    ("543_z13", 1, "control: among the smallest disagreements"),
]


def centred_box(centre_row: int, centre_col: int, shape: tuple, side: int = TILE_SIDE_PX) -> tuple:
    """A tile of `side` pixels centred as asked, slid back inside the frame when
    the centre is near an edge. Returns (row, col, side, was it clipped)."""
    half = side // 2
    row = int(centre_row) - half
    col = int(centre_col) - half
    clipped = False
    if row < 0 or col < 0 or row + side > shape[0] or col + side > shape[1]:
        clipped = True
        row = max(0, min(row, shape[0] - side))
        col = max(0, min(col, shape[1] - side))
    return row, col, side, clipped


def zoom_centre(canal_physical_dir: Path, label: str, index: int) -> tuple:
    """The centre of one of the tiles the first comparison chose, read from its
    json. The boxes are not chosen again here."""
    path = canal_physical_dir / label / f"{label}_canal_physical.json"
    boxes = json.loads(path.read_text(encoding="utf-8"))["zoom_boxes"]
    box = next(b for b in boxes if b["index"] == index)
    return box["row"] + box["side_px"] // 2, box["col"] + box["side_px"] // 2


def upscale(image: np.ndarray, factor: int) -> np.ndarray:
    return image.repeat(factor, axis=0).repeat(factor, axis=1)


def write_tiles(image_paths: dict, canal_physical_dir: Path, out_dir: Path, params) -> list:
    """Write every trace tile and the table that describes them."""
    from skimage.io import imsave

    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for label, index, why in TILE_SOURCES:
        path = image_paths[label]
        display, _channel = lacunae.load_channel(path)
        centre_row, centre_col = zoom_centre(canal_physical_dir, label, index)
        row, col, side, clipped = centred_box(centre_row, centre_col, display.shape[:2])
        tile = display[row:row + side, col:col + side]
        name = f"{label}_tile"
        imsave(out_dir / f"{name}_raw.png", tile.astype(np.uint8), check_contrast=False)
        imsave(out_dir / f"{name}_raw.tif", tile.astype(np.uint8), check_contrast=False)
        imsave(out_dir / f"{name}_raw_x{TRACE_UPSCALE}.png", upscale(tile, TRACE_UPSCALE).astype(np.uint8),
               check_contrast=False)
        rows.append({
            "tile": name,
            "image_label": label,
            "image_file": path.name,
            "from_zoom_box": index,
            "why": why,
            "row_px": row,
            "col_px": col,
            "side_px": side,
            "side_um": round(side * params.pixel_size_um, 4),
            "centre_row_px": centre_row,
            "centre_col_px": centre_col,
            "clipped_at_frame_edge": clipped,
            "upscaled_copy": f"{name}_raw_x{TRACE_UPSCALE}.png",
            "pixel_size_label": "pixel size 0.13 um/px, rounded, unconfirmed",
        })
    with open(out_dir / "tiles.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows


TOLERANCE_PX = (2, 3)


def write_instructions(rows: list, out_dir: Path, params) -> None:
    """tiles_README.md: how to trace these by hand, in ImageJ, without seeing any
    method output."""
    tolerances = " and ".join(f"{t} px ({round(t * params.pixel_size_um, 2)} um)" for t in TOLERANCE_PX)
    lines = [
        "# Raw tiles for a blind hand trace",
        "",
        "**Pixel size 0.13 um/px, rounded, unconfirmed per image.** Pre-validation.",
        "",
        "These tiles are the raw image and nothing else. No mask, no skeleton and no result of any",
        "method is drawn on them, so a trace made here cannot be steered by what any method found.",
        "**Do not open any figure from `results_experiments/` or any file under `results/` while you",
        "trace.** That is the whole point of tracing blind.",
        "",
        "## The tiles",
        "",
        "| tile | image | at row, column | side | centred on | clipped at the frame edge |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| `{r['tile']}` | {r['image_label']} | {r['row_px']}, {r['col_px']} | "
                     f"{r['side_px']} px ({r['side_um']} um) | zoom box {r['from_zoom_box']}, "
                     f"{r['why']} | {'yes' if r['clipped_at_frame_edge'] else 'no'} |")
    lines += [
        "",
        "A tile whose centre would fall near the frame edge is slid back inside the frame, so every tile",
        "is a full square. The table says which ones that happened to.",
        "",
        "Each tile comes three ways:",
        "",
        "- `<tile>_raw.png` and `<tile>_raw.tif`: the tile at its own size, 8 bit, in the same display",
        "  window the pipeline draws on. The tif is there because ImageJ opens it without any colour",
        "  management of its own.",
        f"- `<tile>_raw_x{TRACE_UPSCALE}.png`: the same tile enlarged {TRACE_UPSCALE} times by nearest neighbour, which is",
        "  easier to draw on. Nothing is invented by the enlargement: each original pixel becomes a block",
        f"  of {TRACE_UPSCALE} by {TRACE_UPSCALE}.",
        "",
        "## How to trace, in ImageJ",
        "",
        f"Trace on the enlarged copy if you prefer, but **save the trace at the tile's own size**",
        "(200 by 200 px), because that is what the scoring will read.",
        "",
        "1. **Open the tile.** File > Open, choose `<tile>_raw.tif`.",
        "2. **Make the blank layer.** Image > Duplicate to keep the original safe, then make the drawing",
        "   canvas: File > New > Image, Type 8-bit, Fill with Black, Width 200, Height 200, Slices 1.",
        "   Name it `<tile>_trace`.",
        "3. **Put them side by side.** Window > Tile, so you can see the raw tile while you draw on the",
        "   blank one. If you traced on the enlarged copy, make the blank image 800 by 800 instead and",
        "   scale it back down at the end with Image > Scale, 0.25, interpolation None.",
        "4. **Set the pencil.** Double click the Pencil tool in the toolbar and set Line width to 1.",
        "   Set the drawing colour to white: Edit > Options > Colors, Foreground white.",
        "5. **Draw one line along the middle of each canaliculus you can see**, on the blank image, at the",
        "   same place it has on the raw tile. One stroke per thread. Follow the thread's centre, not its",
        "   edge. Where two threads cross, draw both and let them cross.",
        "6. **Leave out anything you are not sure is a thread.** A missed faint thread and an invented one",
        "   are both errors, and there is no prize for finding more.",
        "7. **Do not trace inside a lacuna** (the large bright bodies) and do not trace the lacuna outline.",
        "8. **Save.** File > Save As > PNG, into this folder, named `<tile>_trace.png`. White lines on a",
        "   black background, 8 bit, the same size as the tile.",
        "",
        "## What will be done with it",
        "",
        f"A thread in the trace and a thread in a method's skeleton will be counted as the same thread when",
        f"they lie within {tolerances} of each other. Both tolerances will be reported, because the answer",
        "depends on which you accept and you should see that dependence rather than one number.",
        "",
        "The scoring is **not** built yet. Nothing in this folder scores anything, so the trace cannot be",
        "tuned against while it is being made.",
        "",
        "## What this cannot settle",
        "",
        "A hand trace is a judgement, not a ground truth. It is made from the same 2D section, with the",
        "same optical blur, by one person who can also miss a thread or invent one. It is a second opinion",
        "formed without seeing the methods, which is worth having and is not the same as being right.",
    ]
    with open(out_dir / "tiles_README.md", "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
