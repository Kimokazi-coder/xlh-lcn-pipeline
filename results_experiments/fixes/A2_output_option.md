# A2 Output-directory option

`-o DIR` is now a short name for the existing `--out DIR` of `src/lacunae.py` and `src/canaliculi.py`
(both use `lacunae.add_input_arguments`). The default stays `results/`. The summary writer already
writes to the same folder, so a folder run of `src/canaliculi.py` puts `summary_table.csv` and `.xlsx`
there.

Check, 2026-10-02, into the git-ignored `results_experiments/_cache/a2_check/`:

- `python src/lacunae.py --image data/WT/543-2.tif -o .../lac` wrote `lac/543-2/` only.
- `python src/canaliculi.py --dir .../in -o .../can` (a folder holding a copy of 543-2.tif) wrote
  `can/543-2/` and `can/summary_table.csv` and `.xlsx`.
- `lacunae.json` and `canaliculi_measurements.json` are identical to `results/543-2/`; the summary row
  is identical to the 543-2 row of `results/summary_table.csv`.
- `git status results/` was clean afterwards.
