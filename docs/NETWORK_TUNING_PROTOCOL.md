# Network tuning protocol

**Status: no tuning has been done, and none is allowed yet.** This page fixes, before any hand count
exists, how a parameter of the canalicular network stage (`src/canaliculi.py`) may be tuned once ground
truth exists. Writing it down first keeps the choice of a value from being fitted to the data it is
judged on. Pixel units throughout; pre-validation until the held-out result below is reported.

## 1. When tuning is allowed

Tuning is forbidden until blind hand counts exist for enough lacunae to cover every field used (section 4).
Until then every default stays as it is, every switch stays off, and only additive measures may be added.
The hand counts must be made without seeing any pipeline output (section 9).

## 2. What may be tuned, and the grid

Only the network parameters of the sweep (`python src/diagnostics.py network-sweep`, results in
`results_experiments/canal_v2/S1_network_sweep.md`), each over the values of that sweep plus the default:

| parameter (in `src/canaliculi.py`) | default | grid |
|---|---|---|
| `TOPHAT_RADIUS_PX` | 5 | 4, 5, 6 |
| `HYSTERESIS_LOW_FRACTION` | 0.75 | 0.525, 0.75, 0.975 |
| `MAX_BRIDGE_GAP_PX` | 10 | 0, 7, 10, 13 |
| `MAX_BRIDGE_ANGLE_DEG` | 40 | 28, 40, 52 |
| `MIN_BRIDGE_SIGNAL_FRACTION` | 0.7 | 0.49, 0.7, 0.91 |
| `PRUNE_SPUR_LEN_PX` | 4 | 3, 4, 5 |
| `ROOT_MERGE_DIST_PX` | 8 | 6, 8, 10 |
| `LACUNA_ATTACH_GAP_PX` | 10 | 7, 10, 13 |
| network cut $t_\mathrm{lo}$ scale | 1.0 | 0.8, 0.9, 1.0, 1.1, 1.2 |

One parameter at a time first; a joint search only over the parameters that moved a metric by more than
its noise (the spread of the metric between sections of one field). The grid and every result go into the
repository before anything is chosen. A value outside the grid needs a new protocol entry first.

**The lacuna stage is tuned separately** (its own counts of lacunae and outlines), and never together with
the network parameters: the network measures depend on the lacunae, so a joint search would trade one
stage's errors against the other's.

## 3. The metrics, fixed in advance

1. **Mean absolute error of roots per cell** against the hand roots (`validate-network`, `mae` of
   `roots_count`). The primary metric.
2. **Bias** of roots (mean of pipeline minus hand), reported beside it; a small error with a large bias is
   not acceptable.
3. **F1 of the skeleton** against hand-traced threads at a 3 px tolerance (`validate-network -t`), where
   traces exist.

The Sholl crossings at 10 and 20 px are reported beside roots in every run but are not tuned on.

## 4. The split: whole fields

The unit is the field, not the image or the cell: sections of one field repeat the same cells
(overnight report 6.1). **Whole fields are held out**; cells or images of one field are never on both
sides of the split. With the 3 or 4 WT fields that exist now, at most one field can be held out, which
leaves 2 or 3 to tune on; that is too few to tune more than one or two parameters. **The new images
(Hyp, Hyp;Enpp1, more WT) change this design**: once there are at least 6 fields, hold out at least 2,
chosen before tuning, balanced across genotypes, and listed in the repository.

## 5. The decision rule, written before looking

On the tuning fields only:

1. Compute the primary metric for the default and for every grid value.
2. Keep the default unless a value lowers the mean absolute error of roots by more than the noise
   (the spread between sections of one field) **and** keeps the absolute bias at or below the default's.
3. Among the values that pass, take the one closest to the default.
4. Where a value changes the skeleton, require that the skeleton F1 does not fall.

The rule is fixed now; it is not adjusted after any result is seen.

## 6. The held-out result

The chosen values are run once on the held-out fields and the metrics are reported, whatever they are. If
the held-out result is worse than the default on the held-out fields, the default stays and both results
are reported. The held-out fields are not used again for tuning.

## 7. What goes into the repository

The grid, the tuning and held-out field lists, every metric of every grid value, the chosen values with
the rule step that chose them, and the held-out result, under `results_experiments/`, with a new
`regression` reference only if a default is changed deliberately, in its own commit.

## 8. Hyp before use

Values tuned on WT are checked on Hyp images before they are used there (the canal and lacuna gates were
derived on WT only; Hyp fields have periosteocytic lesions and different textures). A check is the held-out
procedure of section 6 on Hyp fields.

## 9. Ground truth: how to make it

**Blind hand counts.** Use the tiles in `results/validation_tiles/`: 240 px crops of
the raw red channel, one per interior lacuna, named T001, T002 and so on in a random order, with no outline
or number. For each tile, count the roots (distinct threads leaving the surface of the centre lacuna) and
write the number in `annotation_template.csv` (`code, hand_roots, hand_notes`). Do not open
any other folder of `results/` while counting. Ideally two people count independently, and their
agreement is reported first; it bounds what any pipeline can reach. The key stays outside the repository
until the counts are complete.

**Traced threads.** In ImageJ, open the red channel, trace threads with the segmented line tool inside
chosen boxes, add each line to the ROI manager, then draw the lines into a black image of the same size
(Edit, Draw, line width 1) and save it as PNG, white = thread. Name the file by the short image name
(`543-2.png`, `682_z08.png`) or the clean name. Record the traced boxes in `BOXES.csv` (`image, x0, y0, x1,
y1`, inclusive, pixels) so that untraced areas are not counted as misses. Choose the boxes before looking at
the pipeline skeleton.

**Running the comparison.**
`python src/diagnostics.py validate-network -a ANNOTATION.csv -k KEY_OUTSIDE_REPO.csv -r RESULTS -o OUT [-t TRACES -b BOXES.csv]`.
`python src/diagnostics.py validate-network -s` checks the harness on synthetic data.
