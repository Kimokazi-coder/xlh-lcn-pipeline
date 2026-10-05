# figures_out

Figures of the LCN pipeline on the 8 WT sections. **Pre-validation, pixel units**: nothing has been
checked against manual counts, and the images carry no calibration, so lengths are px and areas px².
Every figure shows the default pipeline output (every switch off) unless its caption says otherwise.
Dim lacunae that lie partly outside the focal plane are not detected and are not drawn.

**Open first:** `INDEX.md`, a table of every figure with a thumbnail. Then `main/Fig02_network_overlay_543-2`
(the network overlay), the network figure of any other image in `per_image/<image>/network`, and
`main/Fig01_contact_sheet`. Captions are in `figures/captions.md`, review notes in `figures/REVIEW_V2.md`.

## Layout

| folder or file | what it holds |
|---|---|
| `INDEX.md` | every figure: what it shows, the display window, links, thumbnail |
| `main/` | main figures Fig01 to Fig04 (PNG at 300 dpi and PDF), with their value logs |
| `supplement/` | supplementary figures S01 to S03 |
| `per_image/<image>/` | `overview`, `network` and `gallery` of one section (PNG and PDF); `inset.json` (inset choices), `network_check.json` and `gallery_check.json` (drawn numbers against the pipeline numbers); `display_variants/` |
| `per_image/<image>/display_variants/` | the same three figures with the image's own display window (PNG only) |
| `validation_tiles/` | 86 raw tiles for counting roots by hand without seeing the pipeline result; the key is outside the repository |
| `_thumbs/` | 600 px wide previews used by `INDEX.md` |
| `display_window.json` | the fixed display window of the dataset |

Every file name starts with its figure id (Fig01, S01, ...) or its kind (overview, network, gallery).
Fields are called Field 1 to Field 4, so no field name looks like a figure name.

## Display windows

The main figures and the main per-image figures use one fixed window for the whole dataset (the 1st and
99.8th percentile of the pooled red channel, 20 to 255 of 255), so brightness can be compared between
images. Only the files in `display_variants/` use each image's own window; they print "Display window:
this image only, display only". Windows are for display; no measurement uses them.

## Colours

One colour, one meaning: cyan interior lacuna; yellow lacuna touching the frame (not in per-cell means);
grey dashed rejected candidate (A aspect, S solidity, a area); vermillion skeleton within 30 px of an
interior lacuna (the ring 30 px pixels); white the rest of the skeleton; magenta dot a root; white
dashed line the 30 px ring of an inset lacuna; white box an inset region; "c" after a number: inside a
flagged canal region, may be vascular. Every figure has its legend inside it.

## How to regenerate

From the repository root, with the project's Python:

```
python -u figures/make_figures.py all     # every figure, the thumbnails and INDEX.md, with a summary table
python -u figures/make_figures.py check   # drawing data against results/ for every image
```

Each output is skipped if it exists; delete a file to redraw it. Every figure that shows roots or ring
length asserts that the drawn dots and vermillion pixels equal the pipeline numbers in `results/`.
The hand-count tiles need a key path outside the repository:
`python -u figures/make_figures.py tiles -k PATH_OUTSIDE_REPO/validation_tiles_key.csv`.
The coded contact sheet S03 needs the blinding key of `python src/diagnostics.py blind` (`contact -b -k KEY`).
