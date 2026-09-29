# LCN pipeline: what these outputs are

**Status: pre-validation.** None of these numbers has been checked against
manual (ImageJ) counts yet. **Units: pixels.** The images carry no usable
micron calibration, so every length is in px and every area in px².
**Data: 8 wild-type (WT) confocal sections.** No Hyp or Hyp;Enpp1 images
have been processed.

Built 2026-09-29 by `src/make_presentation.py` on branch
`presentation-prep`. The same pipeline defaults as `results/canaliculi/`,
with two presentation settings: the reach cap is on (275 px) and threads no
cell owns are drawn in grey.

## What is in this folder

- `summary_table.xlsx` / `.csv`: one row per image (see "The numbers" below).
- `<image>/verification.png`: the original image with each lacuna outlined
  in its own colour and the canaliculi it owns drawn in the same colour.
  **Grey threads are not counted for any cell.** They are either beyond
  the reach cap, or part of the network never connected to a lacuna.
- `<image>/canaliculi_mask.png`, `skeleton.png`: the raw network mask and
  its one-pixel centre lines, so the segmentation can be checked directly.
- `<image>/bridges.png`: where short gaps in threads were joined.
- `<image>/measurements.xlsx` / `.json`: every per-lacuna number, and the
  parameters used.

## Pipeline steps, in plain language

1. **Find the lacunae.** The red channel is split into three brightness
   levels (background, canalicular network, lacunae) using each image's own
   histogram. The brightest level gives the lacuna candidates. Touching
   blobs are separated by their shape (watershed on thickness). Objects are
   kept if they are at least 400 px², solid enough (solidity ≥ 0.5) and not
   too elongated (aspect ratio ≤ 6). Lacunae touching the frame edge are
   kept but left out of per-cell averages.
2. **Find the canalicular network.** A light blur, then a top-hat filter
   (disk radius 5 px) removes the broad background haze so that thin
   threads stand out. A two-level (hysteresis) threshold keeps dim pixels
   only where they connect to clearly bright ones. Short gaps along a
   thread (up to 10 px, in line with it, with signal in the gap) are
   joined. Along vascular canals, no new connections are added.
3. **Reduce the network to centre lines** (skeleton) and turn it into a
   graph of branch points and thread segments. Very short spurs (under
   4 px) and crossing artefacts (internal segments under 6 px) are cleaned
   up.
4. **Attach threads to cells.** Each lacuna is connected to skeleton points
   within 10 px of its outline. Each thread goes to the cell it is reached
   from first through the network. With the reach cap on, a cell does not
   take threads that it only reaches after more than 275 px of network.
5. **Measure.** See below.

## The numbers, and which to trust

| measure | what it is | depends on thread ownership? |
|---|---|---|
| roots per cell | distinct threads leaving the lacuna surface | no |
| ring length r30 / r60 | skeleton px within 30 / 60 px of each lacuna, each pixel counted for its nearest lacuna | no |
| field length density | all skeleton px divided by the analysed field area | no |
| owned length, edge count | total network owned through the graph | **yes** |

**Recommended for presentation: roots per cell, ring lengths and field
length density.** None of them depends on which cell owns which thread.
Across reach caps from 225 to 325 px, and even at 100 px, they do not
change at all. Owned length per cell swings by 7.5% across 225 to 325 px
and drops 39% at 100 px, so it is shown in the files but not in the
summary table. **Edge count is a network parameter, not "canaliculi per
cell"**: a branching tree with T tips has about 2T − 1 edges.

## Key parameters

| step | parameter | value | where it came from |
|---|---|---|---|
| lacunae | minimum area | 400 px² | gap in the pooled area distribution of 8 WT images |
| lacunae | minimum solidity / maximum aspect | 0.5 / 6.0 | sanity limits, not tuned |
| network | top-hat radius | 5 px | measured thread widths (at most about 8 px across) |
| network | hysteresis low cut | 0.75 × the high cut | the one value that passed pre-set guards; not swept |
| network | gap bridging | ≤ 10 px, ≤ 40° off-line | measured gap and angle distributions |
| graph | attach distance | 10 px | covers every lacuna's nearest thread (max gap 7 px) |
| roots | merge distance | 8 px | one thread width |
| ownership | reach cap | 275 px | smallest cap keeping ≥ 90% of owned length, rounded to 25 px |
| per cell | ring radii | 30, 60 px | 30 px used in earlier work; 60 px about two thirds of a lacuna's length |

## Known limitations

- **Not validated.** The comparison with Mahmoud's ImageJ counts is the next
  gate. Until then every number here is a candidate.
- **2D sections of a 3D network.** Threads that leave the focal plane end in
  the image, so the skeleton is fragmented. With the cap on, cells own only
  about a third of the skeleton length (26 to 40% per image). That is why
  the grey dominates the overlays and why per-field and ring measures are
  preferred.
- **Ownership is only partly fixed.** The 275 px cap trims the far tail
  (about 10% of owned length). It does not make owned length a local
  measure. Some cells still own threads well away from their body.
- **Lacunae partly outside the focal plane** are mostly not counted by the
  current detector. Whether they should count is an open science decision
  (D4), and it can change lacuna counts by 50 to 290% per image.
- **Known odd objects**: two thin kept objects that sit on vascular bands
  and are probably not lacunae (542_z06 at (555,149) and 682_z23 at
  (363,7)), one lacuna whose outline leaks into a canalicular loop
  (542_z06 at (106,67)), and one lacuna with an unfilled interior hole
  (542_z06 at (783,581)). All are recorded and none is corrected.
- **Vascular canals are not removed.** Automatic exclusion exists but is
  off, because on these images it removes mostly ordinary network.
- **Periosteocytic lesions (the Hyp phenotype) are not measured yet.** The
  pipeline has never seen a Hyp field.
