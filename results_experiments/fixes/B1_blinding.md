# B1 Blinding

`python src/diagnostics.py blind -s SRC_DIR -o OUT_DIR -k KEY_PATH` copies every .tif/.tiff of
SRC_DIR into the empty folder OUT_DIR as S001.tif, S002.tif, ... in a random order (seed from the
system's random source, recorded in the key). Only pixel data is copied: no description, metadata or
software tag, so every copy has the same tag set. A constant fourth (alpha) channel is dropped,
because it carries no information but would mark the one image that has it (542_z06 is the only RGBA
file); the drop is recorded in the key. The key (code, original_name, original_folder, seed,
constant_alpha_dropped) is written to KEY_PATH, and the command refuses to run if KEY_PATH is inside the
repository, if the key exists already, or if OUT_DIR is not empty. No original name is printed.

`python src/diagnostics.py unblind -s SUMMARY -k KEY_PATH -o OUT` adds code, original_name and
original_folder in front of each row of a summary table from a coded run.

The pipeline itself writes only the names it is given, so on a coded folder every output and log
carries codes only.

## Test, 2026-10-02

1. A key path inside the repository was refused, and nothing was written.
2. The 8 WT images were coded into `results_experiments/_cache/blind/coded/` (git-ignored) with the key
   in the session's temporary folder outside the repository. All 8 copies: 1024 x 1024 x 3, identical
   tag sets, RGB pixels identical to the originals.
3. `python src/lacunae.py --dir .../coded -o .../out` and `python src/canaliculi.py --dir .../coded -o
   .../out` ran with the default config, logged to `run_lacunae.log` and `run_canaliculi.log`.
4. `python -u experiments/fixes_b1_blind_test.py KEY` searched 76 files (json, csv, every part of each
   xlsx, png text chunks, tif tags, both logs, all file paths) for 25 terms (every original name, stem,
   clean name, distinctive part such as z06c1-2, and the folder name WT): **0 found**.
5. Unblinded with `unblind`: 128 summary cells and 4837 per-image json fields (image name and
   provenance excluded) compared with the normal run of the same code: **0 differ**.

Log: `experiments/logs/B1_blind_test_run.log`. Result: PASS.

`.gitignore` gained `code_key*` and `*_key.csv` as a second guard for key files (listed under
Decisions needed: the 2026-09-30 policy had removed every code_key exclusion).
