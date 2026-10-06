# Raw tiles for a blind hand trace

**Pixel size 0.13 um/px, rounded, unconfirmed per image.** Pre-validation.

These tiles are the raw image and nothing else. No mask, no skeleton and no result of any
method is drawn on them, so a trace made here cannot be steered by what any method found.
**Do not open any figure from `results_experiments/` or any file under `results/` while you
trace.** That is the whole point of tracing blind.

## The tiles

| tile | image | at row, column | side | centred on | clipped at the frame edge |
|---|---|---|---|---|---|
| `542_z18_tile` | 542_z18 | 150, 350 | 200 px (26.0 um) | zoom box 1, largest skeleton disagreement of the eight | no |
| `682_z08_tile` | 682_z08 | 450, 650 | 200 px (26.0 um) | zoom box 1, second largest disagreement | no |
| `543-2_tile` | 543-2 | 0, 250 | 200 px (26.0 um) | zoom box 1, smallest disagreement of the three tuning images | yes |
| `543_z13_tile` | 543_z13 | 350, 824 | 200 px (26.0 um) | zoom box 1, control: among the smallest disagreements | yes |

A tile whose centre would fall near the frame edge is slid back inside the frame, so every tile
is a full square. The table says which ones that happened to.

Each tile comes three ways:

- `<tile>_raw.png` and `<tile>_raw.tif`: the tile at its own size, 8 bit, in the same display
  window the pipeline draws on. The tif is there because ImageJ opens it without any colour
  management of its own.
- `<tile>_raw_x4.png`: the same tile enlarged 4 times by nearest neighbour, which is
  easier to draw on. Nothing is invented by the enlargement: each original pixel becomes a block
  of 4 by 4.

## How to trace, in ImageJ

Trace on the enlarged copy if you prefer, but **save the trace at the tile's own size**
(200 by 200 px), because that is what the scoring will read.

1. **Open the tile.** File > Open, choose `<tile>_raw.tif`.
2. **Make the blank layer.** Image > Duplicate to keep the original safe, then make the drawing
   canvas: File > New > Image, Type 8-bit, Fill with Black, Width 200, Height 200, Slices 1.
   Name it `<tile>_trace`.
3. **Put them side by side.** Window > Tile, so you can see the raw tile while you draw on the
   blank one. If you traced on the enlarged copy, make the blank image 800 by 800 instead and
   scale it back down at the end with Image > Scale, 0.25, interpolation None.
4. **Set the pencil.** Double click the Pencil tool in the toolbar and set Line width to 1.
   Set the drawing colour to white: Edit > Options > Colors, Foreground white.
5. **Draw one line along the middle of each canaliculus you can see**, on the blank image, at the
   same place it has on the raw tile. One stroke per thread. Follow the thread's centre, not its
   edge. Where two threads cross, draw both and let them cross.
6. **Leave out anything you are not sure is a thread.** A missed faint thread and an invented one
   are both errors, and there is no prize for finding more.
7. **Do not trace inside a lacuna** (the large bright bodies) and do not trace the lacuna outline.
8. **Save.** File > Save As > PNG, into this folder, named `<tile>_trace.png`. White lines on a
   black background, 8 bit, the same size as the tile.

## What will be done with it

A thread in the trace and a thread in a method's skeleton will be counted as the same thread when
they lie within 2 px (0.26 um) and 3 px (0.39 um) of each other. Both tolerances will be reported, because the answer
depends on which you accept and you should see that dependence rather than one number.

The scoring is **not** built yet. Nothing in this folder scores anything, so the trace cannot be
tuned against while it is being made.

## What this cannot settle

A hand trace is a judgement, not a ground truth. It is made from the same 2D section, with the
same optical blur, by one person who can also miss a thread or invent one. It is a second opinion
formed without seeing the methods, which is worth having and is not the same as being right.
