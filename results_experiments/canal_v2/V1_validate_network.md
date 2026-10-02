# V1 Validation harness: validate-network

Pre-validation, pixel units. `python src/diagnostics.py validate-network` compares the pipeline with blind hand
counts once they exist. Nothing has been counted yet, so this file holds the usage and the self-test only.

## Inputs

- `-a ANNOTATION.csv`: columns `code`, `hand_roots` (and optionally `hand_notes`); one row per tile. Rows with an
  empty `hand_roots` are skipped and counted as not yet done. The template is `figures_out/validation_tiles/
  annotation_template.csv` on branch figures-v2; the command does not depend on that file.
- `-k KEY.csv`: columns `code`, `image`, `lacuna_id` (the tiles key; `image` may be the short or the clean name).
  The key must lie outside the repository; the command refuses a key inside it. Unblinding happens only inside
  this command and only in its output tables.
- `-r RESULTS`: a pipeline output folder in the results layout. For the Sholl columns, run the pipeline of this
  branch (the committed `results/` predates them; those rows are then left empty).
- `-o OUT`: output folder.
- Optional `-t TRACES`: hand-traced masks, PNG, white = thread, the size of the image, named by the short or the
  clean image name. Optional `-b BOXES.csv` (`image, x0, y0, x1, y1`, inclusive): compare only inside the boxes.

## Outputs

`validation_per_lacuna.csv` (the joined table), `validation_stats.csv` and `validation.md` (per measure:
n, bias = mean of pipeline minus hand, SD of the differences, limits of agreement = bias plus and minus 1.96 SD,
mean absolute error, share exactly equal, share within one, Spearman correlation; over all lacunae, per image
and per field, fields from the centroid matching of `field-summary`), `validation_bland_altman.png` (one panel
each for `roots_count`, `sholl_crossings_r10` and `sholl_crossings_r20` against `hand_roots`), and with `-t`
`validation_trace.csv` (precision, recall and F1 of the skeleton against the trace at a 3 px tolerance: a
skeleton pixel is a hit if a traced pixel lies within 3 px, and the reverse for recall).

## Self-test (`-s`)

Synthetic data in `results_experiments/_cache/validate_selftest/` (git-ignored): a fresh pipeline run of the 8
images (fast lacuna stage), hand counts equal to the pipeline roots plus fixed-seed noise of -1, 0 or +1
(probabilities 0.2, 0.6, 0.2), a key in the system temporary folder (outside the repository, deleted after),
and traces equal to the skeleton shifted down by 1 px with 5% of the pixels removed. Every output there is
labelled SELFTEST SYNTHETIC. Result:

```
SELFTEST SYNTHETIC: validate-network on synthetic hand counts and traces (outputs in F:\lcn-quant\results_experiments\_cache\validate_selftest; nothing under results/)

check                                                       value           result
----------------------------------------------------------  --------------  ------
a key inside the repository is refused                      refused         PASS  
lacunae joined                                              86 of 86        PASS  
roots bias near 0 (|bias| < 0.2)                            -0.023          PASS  
roots share within 1 = 1                                    1.000           PASS  
roots Spearman above 0.8                                    0.972           PASS  
F1 near 0.9 to 1 on every image (>= 0.9)                    1.000 to 1.000  PASS  
negative control: another image's trace gives F1 below 0.7  0.257           PASS  
boxes restrict the trace comparison to 2 images             2 images        PASS  

PASS: validate-network self-test, 8 of 8 checks.
```

The Sholl crossings are compared with hand roots too. In the self-test the hand counts are built from the roots,
so the Sholl rows show only their offset from roots (bias +0.95 at 10 px, +4.5 at 20 px), not an agreement.
