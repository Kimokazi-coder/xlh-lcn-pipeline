# experiments

Overnight experiments on the 8 WT images, started 2026-10-01 on branch
`overnight-fixes`. **Pre-validation, pixel units.** There is no ground
truth, so nothing here says a variant is more accurate. Each experiment
reports what changes and by how much, with crops to judge by eye.

The pipeline is not changed. `src/` and `config.py` stay identical to
`main`. Every script here imports the pipeline modules. Where a variant
needs a changed internal function, the script holds its own copy of that
function. Pipeline defaults are Karim's decision.

Coordinates are (x, y) = (column, row) everywhere, as printed by
`python src/diagnostics.py lacuna-table`.

## Files

| file | what it is |
|---|---|
| `PROGRESS.md` | the status of every sub-item; the source of truth for resuming |
| `common.py` | shared helpers: atomic writers, the default-result cache, pipeline stages with hooks, crop helpers |
| `progress.py` | updates `PROGRESS.md` (`init`, `set`, `next`, `show`) |
| `check_and_push.sh` | the two checks (reference-check PASS, `git diff main src config.py` empty), then the push with retries |
| `task0_cache.py` | 0.2: builds the default cache and times the runs |
| `task1_artefact.py` | 1.1 to 1.4: acquisition artefact (TIFF tags, FFT, axis-aligned runs, notch filter) |
| `task2_thresholds.py` | 2.1 to 2.4: lacuna and network thresholds |
| `task3_lacunae.py` | 3.1 to 3.7: lacuna audits and their network-level effect |
| `task4_size.py` | 4.1: size confound in the per-cell measures |
| `task5_density.py` | 5.1 to 5.4: density denominator, other channels, bone ROI draft |
| `task6_repeat.py` | 6.1: repeatability across matched cells |
| `logs/` | tracebacks of failed sub-items, `<id>.txt` |

Outputs go to `results_experiments/<task>/`. The default-result cache is in
`results_experiments/_cache/default/` and is never committed (its folder
holds a `.gitignore` with `*`).

## Running

From the repository root, with the project's Python (3.9, the venv):

```
python -u experiments/task0_cache.py              # build or check the cache
python -u experiments/task1_artefact.py 1.2       # one sub-item
python experiments/progress.py show               # where things stand
```

Every script is idempotent. It checks whether each output already exists
and is complete, and skips it if so. Each output is written to a temporary
file and renamed when done. Grids are stored per image and per setting, so a
restart continues a grid instead of starting over. The cache stores a hash
of `src/lacunae.py` and `src/canaliculi.py` and is rebuilt if either
changes.

matplotlib and pandas are used for plots and tables. Both are already
installed as dependencies of skan, so nothing new is needed.

## How to resume

1. Read `PROGRESS.md`: the "next action" line names the next sub-item.
2. `git status` and `git log -5`. Make the tree clean: commit a finished
   item, or discard a half-finished one with `git checkout -- .` for
   tracked files (untracked outputs of a half item can stay, the scripts
   skip only complete outputs).
3. Continue from the first item that is not DONE. PARTIAL items continue
   from their cached outputs. FAILED items stay failed unless the note
   says they were never retried. An item that failed twice is not tried a
   third time.
4. After each sub-item: `python experiments/progress.py set <id> DONE --sha <sha> --note "..."`,
   commit as `overnight: <id> <short description>`, then
   `bash experiments/check_and_push.sh`.
