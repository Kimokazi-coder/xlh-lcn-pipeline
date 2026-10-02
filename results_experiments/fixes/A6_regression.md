# A6 Subcommand regression

`python src/diagnostics.py regression` regenerates all 8 images with the current config, in 8
parallel processes, into `results_experiments/_cache/regression/` (git-ignored), then compares every
field of `lacunae.json` and `canaliculi_measurements.json` and every cell of `summary_table.csv` with
`results/` at tolerance 0. The `provenance` block (A1) is ignored. Fields that exist only in the new
output are counted as "new fields (not compared)", because `results/` has nothing to compare them with.
Options: `-o` output folder, `-r` reference folder, `-w` processes, `--image`/`--dir` as elsewhere.

First run, 2026-10-02, before any other change to the pipeline: PASS, 3861 numbers compared over 8
images (536, 439, 488, 401, 455, 471, 512, 479 json fields and 80 summary cells), 0 differ, 2 min 8 s.

The comparison functions also caught two planted differences: one roots_count changed by 1 in a copy
of `results/543-2/canaliculi_measurements.json`, and one field density changed in the last digit in a
copy of `results/summary_table.csv`.

The pre-push check `experiments/check_and_push_fixes.sh` runs it before every push.
