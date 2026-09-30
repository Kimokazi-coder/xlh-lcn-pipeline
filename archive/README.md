# archive/

History and earlier analyses, **not needed to run the pipeline**. Nothing
in `src/` imports anything here.

Everything was moved here with `git mv` on 2026-09-30, keeping its folder
structure, so `git log --follow <file>` still shows each file's full history.

| folder | what it holds |
|---|---|
| `src/` | the scripts the pipeline was built from (segment_lacunae_v2, canaliculi_v1, gap_bridging, exclusion_mask, count_lacunae) and the alternatives that were built but not adopted (v3 and hybrid lacuna detectors, adjacent-pair merge, presentation builder) |
| `diagnostics/` | the one-off diagnostic and measurement scripts from each round of work |
| `reports/` | text and markdown reports, one folder per round (phase 0 to 4, overnight, round 2, round 3) |
| `docs/` | the running notes: PROGRESS.md and DECISIONS_NEEDED.md (decisions D0 to D9) |
| `results_old/` | every output produced before the cleanup, in its original layout |
| `README_before_cleanup.md`, `config_before_cleanup.py` | the repository guide and configuration as they were before the cleanup |

**Running an archived script.** They expect the old layout (for example
`src/canaliculi_v1.py` imported by path, and old entries in `config.py`),
so they will not run from here. Check out the tag instead:

```
git checkout archive-before-cleanup
```

That tag marks the whole repository as it was before the cleanup, and
every script runs there as it did at the time.

The current method, parameters and decisions are summarised in
`docs/METHODS.md` at the repository root.
