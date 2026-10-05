# Hand-count tiles

Pre-validation, pixel units. One tile per interior lacuna of the 8 WT sections: a 240 x 240 px crop of
the raw red channel (8-bit, the values of the image file, no display window), centred on the centre of
the lacuna's bounding box, zero padded (black) where the crop leaves the frame. There is no outline,
skeleton, root dot or number on any tile, and the PNG files hold pixel data only (no file name or text
in any metadata).

**Purpose.** These tiles are for counting roots by hand without seeing the pipeline result. Count the
roots (distinct canalicular threads leaving the lacuna surface) of the lacuna at the centre of each tile
and enter the number in `annotation_template.csv` (columns code, hand_roots, hand_notes). Do not open
`figures_out/per_image/` or `results/` while counting.

**Codes.** The tiles are named T001, T002 and so on in a random order drawn from the operating system's
random source, so the order cannot be rebuilt from this repository. The key (code, image, lacuna id,
centre x and y) stays outside the repository, at the path given with `-k` when the tiles were made; the
command refuses a key path inside the repository. Join the key to the filled template to compare the
hand counts with `roots_count` in `results/<image>/canaliculi_measurements.json`.

**Limits.** The tiles hide the pipeline result, not the image: a tile can be matched to its section by
appearance. A neighbouring lacuna can be partly visible at a tile edge; only the centre lacuna is
counted.

Regenerate (the key path must be outside the repository):
`python -u figures/make_figures.py tiles -k PATH_OUTSIDE_REPO/validation_tiles_key.csv`
With an existing key the tiles are rebuilt from it; without one, a new random order is drawn.
