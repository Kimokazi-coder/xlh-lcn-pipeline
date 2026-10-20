# Results

**The deterministic method.** This is one of two labelled result sets: everything the pipeline and the
figure code produce with `config.AI_JUDGE_ENABLED` off, as `config.py` ships, per image and for all
images together, in one folder per group (`results/<group>/`, the groups of `config.GROUPS`). `WT/`,
the reference group, is the reference `python src/diagnostics.py regression` compares with. The second
set, the same pipeline with the AI judge switch on, is [`../results_ai_judge/`](../results_ai_judge/README.md),
for WT only, with the same per-image layout; which method is used is a choice still pending, and neither is validated
against a manual trace.

Made by, from the repository root: `python src/lacunae.py --dir data/WT`, `python src/canaliculi.py --dir
data/WT`, `python src/quantification.py --dir data/WT` and `python -u figures/make_figures.py all`, which
write `WT/` (see How to regenerate).
**Pre-validation**: no number here has been checked against manual counts. **Pixel units**: the pixel
size is 0.13 um/px (acquisition record, all 8 images, rounded to two decimals), but the pipeline reports
px, px² and px⁻¹ so that a fresh run still equals this folder at tolerance 0.
The thresholds are image-relative: each image's cuts come from its own histogram. The data are 8 wild-type
(WT) sections. Method and parameters: [docs/METHODS.md](../docs/METHODS.md); where to start:
[docs/START_HERE.md](../docs/START_HERE.md).

**Detection and quantification are separate.** `src/lacunae.py` and `src/canaliculi.py` find, trace and
draw, and save what they found in `1_lacunae/` and `2_canaliculi/`. `src/quantification.py` reads that and
writes every measured number, in `5_quantification/` and in the one cross-image table. No number is
computed in two places.

**What is tracked.** Everything in the layout below, the figures included: `python -u
figures/make_figures.py all` redraws any figure that is missing and skips the ones that exist. The stage
pictures in `1_lacunae/` and `2_canaliculi/` are committed, because the skeleton png is an input to
`python src/diagnostics.py validate-network`. The diagnostic and archive folders that commands write
here are not tracked; see Not tracked at the end.

## Layout

```
results/
  README.md                   this guide
  WT/                         one folder per group; WT, the reference group, is the only one with images
    all_images/
      quantification/         quantification_all_images.csv, .xlsx and .pdf: one row per image
      figures/main/           Fig01 to Fig04
      figures/supplement/     S01 and S02
      figures/display_window.json
    <label>/                  one folder per image: 542_z06, 542_z18, 543-2, 543_3, 543_z13, 682_z08, 682_z23, 682_z29
      1_lacunae/              detection: <label>_lacunae_outlines.png, <label>_lacuna_labels.png,
                              <label>_lacunae_detection.json
      2_canaliculi/           detection: <label>_canaliculi_mask.png, _skeleton.png, _verification.png,
                              _vascular_mask.png, _graph.pickle,
                              <label>_canaliculi_detection.json
      3_publication_figures/  <label>_figure_network, _figure_cell_gallery, _figure_overview (png and pdf),
                              <label>_figure_network_checks.json, _figure_cell_gallery_checks.json,
                              _figure_inset_choice.json
      5_quantification/       every measured number: <label>_quantification.json, .xlsx and .pdf
```

Inside a group folder every path below is the same. The label is the short image name. The table from
the image file name to the label is
`IMAGE_LABELS` in `config.py`; the folder and file names are defined there too.

## What each file holds

Paths in this section are inside a group folder, `results/<group>/`.

Measured numbers, all of them in `5_quantification/`:

- `<label>_quantification.json`: the counts, the interior statistics of every per-lacuna measure, the
  field block, the width block, one row per lacuna with its shape and its network measures together, the
  parameters of both detection stages, and a provenance block.
- `<label>_quantification.xlsx`: the same as the sheets `per_image`, `field`, `width`, `per_lacuna` and
  `notes`.
- `<label>_quantification.pdf`: the same to read, as plain text tables, with a histogram of lacuna areas
  and a histogram of canalicular width.
- `all_images/quantification/quantification_all_images.csv`, `.xlsx` and `.pdf`: one row per image. This
  is the only cross-image table; it replaced `summary_all_images` and keeps its columns, in the same
  order, with the width columns appended.

Detection, in `1_lacunae/` and `2_canaliculi/`:

- `<label>_lacunae_outlines.png`: the image with the kept lacunae outlined in green.
- `<label>_lacuna_labels.png`: the label image, 16-bit, 0 outside a kept lacuna and its 1..N id inside.
  Every lacuna measure is taken from this.
- `<label>_canaliculi_mask.png`: the network mask (white) before it is reduced to a skeleton.
- `<label>_canaliculi_skeleton.png`: the one-pixel skeleton of the network.
- `<label>_canaliculi_verification.png`: each kept lacuna outlined, and the threads it owns drawn 5 px
  wide, every cell in its own colour, over the full-brightness original. It is there to check the tracing
  against the real threads underneath. Its colours assign each thread to one cell through the network with
  no distance limit, so they are not one of the headline measures; the network figure shows the measured
  pixels instead.
- `<label>_canaliculi_vascular_mask.png`: the broad bright structures (vascular canals and their edges),
  already dilated. Nothing is removed from the image; hysteresis and bridging may not grow into them.
- REMOVED: `<label>_canaliculi_bridged_pixels.png`. Gap bridging went with the intensity method, so
  nothing is drawn into the mask that the threshold did not put there.
  (was: the pixels gap bridging added. They had no signal under them,
  so the width measure leaves them out.
- `<label>_canaliculi_graph.pickle`: the cleaned skeleton graph with edge lengths, the node owner, its
  distance through the network and the edge owner.
- `<label>_lacunae_detection.json` and `<label>_canaliculi_detection.json`: what each stage did, with no
  measured value in them: the parameters, the cuts it computed, the bridges it added, and provenance.

Figures, in `3_publication_figures/`:

- `<label>_figure_network.png` and `.pdf`: orange is skeleton within 30 px of an interior lacuna, white is the
  rest, magenta dots are roots, cyan outlines are interior lacunae and yellow are lacunae touching the frame;
  three lacunae are shown at 3x below.
- `<label>_figure_cell_gallery.png` and `.pdf`: every interior lacuna at the same scale, with its roots and the
  dashed contour of its 30 px ring.
- `<label>_figure_overview.png` and `.pdf`: the red channel, the kept lacunae with their numbers and the
  rejected candidates, the network at small size, and one lacuna at 3x.
- `<label>_figure_network_checks.json` and `<label>_figure_cell_gallery_checks.json`: per lacuna the drawn
  root dots and ring pixels against the pipeline numbers (they are equal).
- `<label>_figure_inset_choice.json`: which lacunae the insets show and the rule that chose them.
- `all_images/figures/display_window.json`: the fixed display window used by every main figure.

## Per image

Cross-image table: [xlsx](WT/all_images/quantification/quantification_all_images.xlsx) [csv](WT/all_images/quantification/quantification_all_images.csv) [pdf](WT/all_images/quantification/quantification_all_images.pdf).

| image | network figure | 5_quantification | 1_lacunae | 2_canaliculi | 3_publication_figures |
|---|---|---|---|---|---|
| **543-2** | <img src="WT/543-2/3_publication_figures/543-2_figure_network.png" width="340" alt="network figure 543-2"> | [xlsx](WT/543-2/5_quantification/543-2_quantification.xlsx) [json](WT/543-2/5_quantification/543-2_quantification.json) [pdf](WT/543-2/5_quantification/543-2_quantification.pdf) | [outlines png](WT/543-2/1_lacunae/543-2_lacunae_outlines.png) [label image](WT/543-2/1_lacunae/543-2_lacuna_labels.png) [record](WT/543-2/1_lacunae/543-2_lacunae_detection.json) | [mask](WT/543-2/2_canaliculi/543-2_canaliculi_mask.png) [skeleton](WT/543-2/2_canaliculi/543-2_canaliculi_skeleton.png) [verification](WT/543-2/2_canaliculi/543-2_canaliculi_verification.png) [vascular](WT/543-2/2_canaliculi/543-2_canaliculi_vascular_mask.png) [graph](WT/543-2/2_canaliculi/543-2_canaliculi_graph.pickle) [record](WT/543-2/2_canaliculi/543-2_canaliculi_detection.json) | [network png](WT/543-2/3_publication_figures/543-2_figure_network.png) [pdf](WT/543-2/3_publication_figures/543-2_figure_network.pdf) [cell gallery png](WT/543-2/3_publication_figures/543-2_figure_cell_gallery.png) [pdf](WT/543-2/3_publication_figures/543-2_figure_cell_gallery.pdf) [overview png](WT/543-2/3_publication_figures/543-2_figure_overview.png) [pdf](WT/543-2/3_publication_figures/543-2_figure_overview.pdf) [network checks](WT/543-2/3_publication_figures/543-2_figure_network_checks.json) [gallery checks](WT/543-2/3_publication_figures/543-2_figure_cell_gallery_checks.json) [inset choice](WT/543-2/3_publication_figures/543-2_figure_inset_choice.json) |
| **543_3** | <img src="WT/543_3/3_publication_figures/543_3_figure_network.png" width="340" alt="network figure 543_3"> | [xlsx](WT/543_3/5_quantification/543_3_quantification.xlsx) [json](WT/543_3/5_quantification/543_3_quantification.json) [pdf](WT/543_3/5_quantification/543_3_quantification.pdf) | [outlines png](WT/543_3/1_lacunae/543_3_lacunae_outlines.png) [label image](WT/543_3/1_lacunae/543_3_lacuna_labels.png) [record](WT/543_3/1_lacunae/543_3_lacunae_detection.json) | [mask](WT/543_3/2_canaliculi/543_3_canaliculi_mask.png) [skeleton](WT/543_3/2_canaliculi/543_3_canaliculi_skeleton.png) [verification](WT/543_3/2_canaliculi/543_3_canaliculi_verification.png) [vascular](WT/543_3/2_canaliculi/543_3_canaliculi_vascular_mask.png) [graph](WT/543_3/2_canaliculi/543_3_canaliculi_graph.pickle) [record](WT/543_3/2_canaliculi/543_3_canaliculi_detection.json) | [network png](WT/543_3/3_publication_figures/543_3_figure_network.png) [pdf](WT/543_3/3_publication_figures/543_3_figure_network.pdf) [cell gallery png](WT/543_3/3_publication_figures/543_3_figure_cell_gallery.png) [pdf](WT/543_3/3_publication_figures/543_3_figure_cell_gallery.pdf) [overview png](WT/543_3/3_publication_figures/543_3_figure_overview.png) [pdf](WT/543_3/3_publication_figures/543_3_figure_overview.pdf) [network checks](WT/543_3/3_publication_figures/543_3_figure_network_checks.json) [gallery checks](WT/543_3/3_publication_figures/543_3_figure_cell_gallery_checks.json) [inset choice](WT/543_3/3_publication_figures/543_3_figure_inset_choice.json) |
| **543_z13** | <img src="WT/543_z13/3_publication_figures/543_z13_figure_network.png" width="340" alt="network figure 543_z13"> | [xlsx](WT/543_z13/5_quantification/543_z13_quantification.xlsx) [json](WT/543_z13/5_quantification/543_z13_quantification.json) [pdf](WT/543_z13/5_quantification/543_z13_quantification.pdf) | [outlines png](WT/543_z13/1_lacunae/543_z13_lacunae_outlines.png) [label image](WT/543_z13/1_lacunae/543_z13_lacuna_labels.png) [record](WT/543_z13/1_lacunae/543_z13_lacunae_detection.json) | [mask](WT/543_z13/2_canaliculi/543_z13_canaliculi_mask.png) [skeleton](WT/543_z13/2_canaliculi/543_z13_canaliculi_skeleton.png) [verification](WT/543_z13/2_canaliculi/543_z13_canaliculi_verification.png) [vascular](WT/543_z13/2_canaliculi/543_z13_canaliculi_vascular_mask.png) [graph](WT/543_z13/2_canaliculi/543_z13_canaliculi_graph.pickle) [record](WT/543_z13/2_canaliculi/543_z13_canaliculi_detection.json) | [network png](WT/543_z13/3_publication_figures/543_z13_figure_network.png) [pdf](WT/543_z13/3_publication_figures/543_z13_figure_network.pdf) [cell gallery png](WT/543_z13/3_publication_figures/543_z13_figure_cell_gallery.png) [pdf](WT/543_z13/3_publication_figures/543_z13_figure_cell_gallery.pdf) [overview png](WT/543_z13/3_publication_figures/543_z13_figure_overview.png) [pdf](WT/543_z13/3_publication_figures/543_z13_figure_overview.pdf) [network checks](WT/543_z13/3_publication_figures/543_z13_figure_network_checks.json) [gallery checks](WT/543_z13/3_publication_figures/543_z13_figure_cell_gallery_checks.json) [inset choice](WT/543_z13/3_publication_figures/543_z13_figure_inset_choice.json) |
| **542_z06** | <img src="WT/542_z06/3_publication_figures/542_z06_figure_network.png" width="340" alt="network figure 542_z06"> | [xlsx](WT/542_z06/5_quantification/542_z06_quantification.xlsx) [json](WT/542_z06/5_quantification/542_z06_quantification.json) [pdf](WT/542_z06/5_quantification/542_z06_quantification.pdf) | [outlines png](WT/542_z06/1_lacunae/542_z06_lacunae_outlines.png) [label image](WT/542_z06/1_lacunae/542_z06_lacuna_labels.png) [record](WT/542_z06/1_lacunae/542_z06_lacunae_detection.json) | [mask](WT/542_z06/2_canaliculi/542_z06_canaliculi_mask.png) [skeleton](WT/542_z06/2_canaliculi/542_z06_canaliculi_skeleton.png) [verification](WT/542_z06/2_canaliculi/542_z06_canaliculi_verification.png) [vascular](WT/542_z06/2_canaliculi/542_z06_canaliculi_vascular_mask.png) [graph](WT/542_z06/2_canaliculi/542_z06_canaliculi_graph.pickle) [record](WT/542_z06/2_canaliculi/542_z06_canaliculi_detection.json) | [network png](WT/542_z06/3_publication_figures/542_z06_figure_network.png) [pdf](WT/542_z06/3_publication_figures/542_z06_figure_network.pdf) [cell gallery png](WT/542_z06/3_publication_figures/542_z06_figure_cell_gallery.png) [pdf](WT/542_z06/3_publication_figures/542_z06_figure_cell_gallery.pdf) [overview png](WT/542_z06/3_publication_figures/542_z06_figure_overview.png) [pdf](WT/542_z06/3_publication_figures/542_z06_figure_overview.pdf) [network checks](WT/542_z06/3_publication_figures/542_z06_figure_network_checks.json) [gallery checks](WT/542_z06/3_publication_figures/542_z06_figure_cell_gallery_checks.json) [inset choice](WT/542_z06/3_publication_figures/542_z06_figure_inset_choice.json) |
| **542_z18** | <img src="WT/542_z18/3_publication_figures/542_z18_figure_network.png" width="340" alt="network figure 542_z18"> | [xlsx](WT/542_z18/5_quantification/542_z18_quantification.xlsx) [json](WT/542_z18/5_quantification/542_z18_quantification.json) [pdf](WT/542_z18/5_quantification/542_z18_quantification.pdf) | [outlines png](WT/542_z18/1_lacunae/542_z18_lacunae_outlines.png) [label image](WT/542_z18/1_lacunae/542_z18_lacuna_labels.png) [record](WT/542_z18/1_lacunae/542_z18_lacunae_detection.json) | [mask](WT/542_z18/2_canaliculi/542_z18_canaliculi_mask.png) [skeleton](WT/542_z18/2_canaliculi/542_z18_canaliculi_skeleton.png) [verification](WT/542_z18/2_canaliculi/542_z18_canaliculi_verification.png) [vascular](WT/542_z18/2_canaliculi/542_z18_canaliculi_vascular_mask.png) [graph](WT/542_z18/2_canaliculi/542_z18_canaliculi_graph.pickle) [record](WT/542_z18/2_canaliculi/542_z18_canaliculi_detection.json) | [network png](WT/542_z18/3_publication_figures/542_z18_figure_network.png) [pdf](WT/542_z18/3_publication_figures/542_z18_figure_network.pdf) [cell gallery png](WT/542_z18/3_publication_figures/542_z18_figure_cell_gallery.png) [pdf](WT/542_z18/3_publication_figures/542_z18_figure_cell_gallery.pdf) [overview png](WT/542_z18/3_publication_figures/542_z18_figure_overview.png) [pdf](WT/542_z18/3_publication_figures/542_z18_figure_overview.pdf) [network checks](WT/542_z18/3_publication_figures/542_z18_figure_network_checks.json) [gallery checks](WT/542_z18/3_publication_figures/542_z18_figure_cell_gallery_checks.json) [inset choice](WT/542_z18/3_publication_figures/542_z18_figure_inset_choice.json) |
| **682_z08** | <img src="WT/682_z08/3_publication_figures/682_z08_figure_network.png" width="340" alt="network figure 682_z08"> | [xlsx](WT/682_z08/5_quantification/682_z08_quantification.xlsx) [json](WT/682_z08/5_quantification/682_z08_quantification.json) [pdf](WT/682_z08/5_quantification/682_z08_quantification.pdf) | [outlines png](WT/682_z08/1_lacunae/682_z08_lacunae_outlines.png) [label image](WT/682_z08/1_lacunae/682_z08_lacuna_labels.png) [record](WT/682_z08/1_lacunae/682_z08_lacunae_detection.json) | [mask](WT/682_z08/2_canaliculi/682_z08_canaliculi_mask.png) [skeleton](WT/682_z08/2_canaliculi/682_z08_canaliculi_skeleton.png) [verification](WT/682_z08/2_canaliculi/682_z08_canaliculi_verification.png) [vascular](WT/682_z08/2_canaliculi/682_z08_canaliculi_vascular_mask.png) [graph](WT/682_z08/2_canaliculi/682_z08_canaliculi_graph.pickle) [record](WT/682_z08/2_canaliculi/682_z08_canaliculi_detection.json) | [network png](WT/682_z08/3_publication_figures/682_z08_figure_network.png) [pdf](WT/682_z08/3_publication_figures/682_z08_figure_network.pdf) [cell gallery png](WT/682_z08/3_publication_figures/682_z08_figure_cell_gallery.png) [pdf](WT/682_z08/3_publication_figures/682_z08_figure_cell_gallery.pdf) [overview png](WT/682_z08/3_publication_figures/682_z08_figure_overview.png) [pdf](WT/682_z08/3_publication_figures/682_z08_figure_overview.pdf) [network checks](WT/682_z08/3_publication_figures/682_z08_figure_network_checks.json) [gallery checks](WT/682_z08/3_publication_figures/682_z08_figure_cell_gallery_checks.json) [inset choice](WT/682_z08/3_publication_figures/682_z08_figure_inset_choice.json) |
| **682_z23** | <img src="WT/682_z23/3_publication_figures/682_z23_figure_network.png" width="340" alt="network figure 682_z23"> | [xlsx](WT/682_z23/5_quantification/682_z23_quantification.xlsx) [json](WT/682_z23/5_quantification/682_z23_quantification.json) [pdf](WT/682_z23/5_quantification/682_z23_quantification.pdf) | [outlines png](WT/682_z23/1_lacunae/682_z23_lacunae_outlines.png) [label image](WT/682_z23/1_lacunae/682_z23_lacuna_labels.png) [record](WT/682_z23/1_lacunae/682_z23_lacunae_detection.json) | [mask](WT/682_z23/2_canaliculi/682_z23_canaliculi_mask.png) [skeleton](WT/682_z23/2_canaliculi/682_z23_canaliculi_skeleton.png) [verification](WT/682_z23/2_canaliculi/682_z23_canaliculi_verification.png) [vascular](WT/682_z23/2_canaliculi/682_z23_canaliculi_vascular_mask.png) [graph](WT/682_z23/2_canaliculi/682_z23_canaliculi_graph.pickle) [record](WT/682_z23/2_canaliculi/682_z23_canaliculi_detection.json) | [network png](WT/682_z23/3_publication_figures/682_z23_figure_network.png) [pdf](WT/682_z23/3_publication_figures/682_z23_figure_network.pdf) [cell gallery png](WT/682_z23/3_publication_figures/682_z23_figure_cell_gallery.png) [pdf](WT/682_z23/3_publication_figures/682_z23_figure_cell_gallery.pdf) [overview png](WT/682_z23/3_publication_figures/682_z23_figure_overview.png) [pdf](WT/682_z23/3_publication_figures/682_z23_figure_overview.pdf) [network checks](WT/682_z23/3_publication_figures/682_z23_figure_network_checks.json) [gallery checks](WT/682_z23/3_publication_figures/682_z23_figure_cell_gallery_checks.json) [inset choice](WT/682_z23/3_publication_figures/682_z23_figure_inset_choice.json) |
| **682_z29** | <img src="WT/682_z29/3_publication_figures/682_z29_figure_network.png" width="340" alt="network figure 682_z29"> | [xlsx](WT/682_z29/5_quantification/682_z29_quantification.xlsx) [json](WT/682_z29/5_quantification/682_z29_quantification.json) [pdf](WT/682_z29/5_quantification/682_z29_quantification.pdf) | [outlines png](WT/682_z29/1_lacunae/682_z29_lacunae_outlines.png) [label image](WT/682_z29/1_lacunae/682_z29_lacuna_labels.png) [record](WT/682_z29/1_lacunae/682_z29_lacunae_detection.json) | [mask](WT/682_z29/2_canaliculi/682_z29_canaliculi_mask.png) [skeleton](WT/682_z29/2_canaliculi/682_z29_canaliculi_skeleton.png) [verification](WT/682_z29/2_canaliculi/682_z29_canaliculi_verification.png) [vascular](WT/682_z29/2_canaliculi/682_z29_canaliculi_vascular_mask.png) [graph](WT/682_z29/2_canaliculi/682_z29_canaliculi_graph.pickle) [record](WT/682_z29/2_canaliculi/682_z29_canaliculi_detection.json) | [network png](WT/682_z29/3_publication_figures/682_z29_figure_network.png) [pdf](WT/682_z29/3_publication_figures/682_z29_figure_network.pdf) [cell gallery png](WT/682_z29/3_publication_figures/682_z29_figure_cell_gallery.png) [pdf](WT/682_z29/3_publication_figures/682_z29_figure_cell_gallery.pdf) [overview png](WT/682_z29/3_publication_figures/682_z29_figure_overview.png) [pdf](WT/682_z29/3_publication_figures/682_z29_figure_overview.pdf) [network checks](WT/682_z29/3_publication_figures/682_z29_figure_network_checks.json) [gallery checks](WT/682_z29/3_publication_figures/682_z29_figure_cell_gallery_checks.json) [inset choice](WT/682_z29/3_publication_figures/682_z29_figure_inset_choice.json) |

## The measures

The headline measures are roots per cell, ring length 30 px, the per-field length density and the
canalicular width. Definitions, origins and limits: [docs/METHODS.md](../docs/METHODS.md) section 3.
`owned_length_px`, `edge_count` and `mean_edge_length_px` depend on which cell owns which thread, with no
distance limit, so every output labels them ownership-dependent.

### Canalicular width, added with this layout

- `width_mean_px`, `width_median_px`, `width_p10_px`, `width_p90_px`, `width_pixels_used` (per image) and
  `ring_width_mean_r30_px` (per lacuna, over its own 30 px ring): twice the Euclidean distance transform
  of the canalicular mask at each skeleton pixel, so the local full width of a thread, in px.
- Measured only where there is real signal under the skeleton. The pixels gap bridging added, the lacuna
  buffer and the dilated vascular mask are left out.
- The threads are only about 2 to 6 px wide, so the width sits close to the pixel grid and is quantised in
  steps of about 1 px. It moves with the threshold, because a lower cut widens every thread. It is **not
  validated** against any manual width measurement.

### Columns added earlier

The existing columns and values have never changed. From `docs/METHODS.md` (section 9), per lacuna, and as
interior means in the cross-image table:

- `perimeter_px`: regionprops perimeter of the lacuna, $P$.
- `ring_area_r30_px2`, `ring_area_r60_px2`: $A_r$, pixels of the nearest-lacuna partition within $r$ px of
  the body, lacunae excluded.
- `in_frame_fraction_r30`, `in_frame_fraction_r60`: in-frame share of the full $r$ px annulus around this
  lacuna alone.
- `ring_density_r30`, `ring_density_r60`: $L_r / A_r$, with $L_r$ the ring length (px⁻¹).
- `roots_per_100px_perimeter`: $100 \cdot \text{roots} / P$.

`docs/METHODS.md` does not define the next columns yet; their definitions are those of
the canaliculi v2 report, tag `archive-2026-10-13` (section "New columns"):

- `ring_attached_length_r30_px`, `ring_attached_length_r60_px`: ring length pixels (same pixel set as
  `ring_length_rR_px`) in 8-connected components of the ring that reach within 10 px of the lacuna.
- `ring_length_w_r30_px`, `ring_length_w_r60_px`: chain code length of the ring, 1 per orthogonal link and
  $\sqrt{2}$ per diagonal link.
- `sholl_crossings_r10`, `sholl_crossings_r20`, `sholl_crossings_r30`: 8-connected skeleton components inside
  the band $[R - 0.75, R + 0.75)$ px from the lacuna, in its nearest-lacuna partition.
- `field_length_density_w_per_px` (field): chain code length of the skeleton over the analysed area.
- `field_density_without_flagged_per_px` (field): skeleton px outside the flagged canal mask over the
  analysed area outside it.
- `field_density_in_roi_per_px` (field): skeleton px inside a bone ROI over the analysed area inside it; only
  with the `-m` option of `src/quantification.py`, empty otherwise.
- `image_label`: the short image name used in the folder and file names.

## Figures for all images

In `WT/all_images/figures/` (fixed display window for the dataset):

- Fig01_contact_sheet: All 8 WT sections with the kept lacunae, the canal marks and the count lines. [png](WT/all_images/figures/main/Fig01_contact_sheet.png) [pdf](WT/all_images/figures/main/Fig01_contact_sheet.pdf)
- Fig02_network_overlay_543-2: Network overlay of 543-2, a copy of its network figure. [png](WT/all_images/figures/main/Fig02_network_overlay_543-2.png) [pdf](WT/all_images/figures/main/Fig02_network_overlay_543-2.pdf)
- Fig03_threshold_sensitivity: Lacuna count against the lacuna threshold, three sections at 0.8 to 1.2 times the cut. [png](WT/all_images/figures/main/Fig03_threshold_sensitivity.png) [pdf](WT/all_images/figures/main/Fig03_threshold_sensitivity.pdf)
- Fig04_per_field: Per-cell and per-field measures by field, y axes from zero. [png](WT/all_images/figures/main/Fig04_per_field.png) [pdf](WT/all_images/figures/main/Fig04_per_field.pdf)
- Fig04_per_field_merged: The same with 682_z08 merged by hand into Field 4. [png](WT/all_images/figures/main/Fig04_per_field_merged.png) [pdf](WT/all_images/figures/main/Fig04_per_field_merged.pdf)
- S01_switch_examples: Two optional switches, off (default) and on. [png](WT/all_images/figures/supplement/S01_switch_examples.png) [pdf](WT/all_images/figures/supplement/S01_switch_examples.pdf)
- S02_contact_sheet_with_rejected_candidates: The contact sheet with the rejected lacuna-scale candidates. [png](WT/all_images/figures/supplement/S02_contact_sheet_with_rejected_candidates.png) [pdf](WT/all_images/figures/supplement/S02_contact_sheet_with_rejected_candidates.pdf)

Captions: [figures/captions.md](../figures/captions.md).

## How to regenerate

From the repository root, with the project's Python, in this order:

```
python src/lacunae.py --dir data/WT          # 1_lacunae of every image
python src/canaliculi.py --dir data/WT       # 2_canaliculi of every image
python src/quantification.py --dir data/WT   # 5_quantification and the cross-image table
python -u figures/make_figures.py all        # every figure of WT; existing figures are skipped
python src/diagnostics.py reference-check    # must PASS: 161.00 / 21.63 / 8.50 on 543-2
python src/diagnostics.py regression         # every number against results/WT/, tolerance 0
```

The first three write `results/WT/`: with no `-o`, a run writes to `results/<name of the input
folder>/`. `results/WT/` is the reference that `regression` compares with, so regenerate it only on
purpose. The option `-o OTHER_FOLDER` writes the same layout into another folder.

## Not tracked

These folders were removed from the repository on 2026-10-20. They are diagnostics and history, not
results; each is written again when its command reruns, and `.gitignore` keeps it out of git when that
happens. Each command measures the pipeline **as configured today**, so where a folder recorded a state
before a rule changed, the files exactly as the docs cite them are at commit `bf3b982`
(`git checkout bf3b982 -- results/<folder>`).

| folder | what it was | regenerate with |
| --- | --- | --- |
| `<group>/<label>/4_archive_not_used/` | the per-image brightness variants of the figures, and the low-cut overview layer of 543_3 | `python -u figures/make_figures.py all` |
| `<group>/all_images/archive_not_used/` | the coded contact sheet used to test blinding (S03); already absent before this cleanup | `python -u figures/make_figures.py all -b KEY` |
| `diagnosis_543_3/` | why one thread or blob was missing, on 543_3 | `python src/diagnostics.py diagnose-untraced -i "data/WT/543_3.tif" -o results/diagnosis_543_3 --lacunae 1,7 --blobs "40,290;480,460;285,855;820,155"` |
| `ai_dry_run/` | what a judge run would cost, and the pictures it would send | `python src/diagnostics.py ai-dry-run --dir data/WT -o results/ai_dry_run --pictures all` and `python src/diagnostics.py ai-candidates --dir data/WT -o results/ai_dry_run` |
| `ridge_background/` | the local background of the ridge response | `python src/diagnostics.py ridge-background -d data/WT -o results/ridge_background` |
| `empty_zone/` | the empty ring around each lacuna, measured | `python src/diagnostics.py empty-zone -d data/WT -o results/empty_zone` |
| `contact_census/` | does each lacuna own the threads that touch it, before and after the contact rule | `python src/diagnostics.py contact -d data/WT -o results/contact_census --tag after --points "542_z06:400,940;543_3:340,250;543_3:200,635;543_3:271,79" --pictures` and `python src/diagnostics.py contact-handover -d data/WT -o results/contact_census` |
| `network_shape/` | what the report-only shape measures count, drawn | `python src/diagnostics.py shape-picture -d data/WT -o results/network_shape` |
| `survey/` | what the pipeline does to every image, and the lacuna candidates | `python src/diagnostics.py survey -d data/WT -o results/survey` and `python src/diagnostics.py lacuna-candidates -d data/WT -o results/survey` |
| `glow_zone/` | the glow zone rule, on against off | `python src/diagnostics.py glow-check -d data/WT -o results/glow_zone` |
| `hole_zone/` | the hole zone rule, checked | `python src/diagnostics.py hole-check -d data/WT -o results/hole_zone --pictures 543-2,543_3` |
