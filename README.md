# lcn-quant

Quantification of the osteocyte lacuno-canalicular network (LCN) from 2D
confocal optical sections of mouse bone.

## Status

**v1-RAW / v2-RAW, pre-validation.** The pipeline runs end to end, but none of
its output has been checked against ground truth. Mahmoud's ImageJ counts are
the intended validation and that comparison has not been done yet. Treat every
number this produces as a candidate, not a result.

Parameters for the current lacuna and canaliculi modules deliberately live as
documented module-level constants in `src/`, not in `config.py`; they move into
`config.py` once validated.

## Units

**Everything is in PIXELS.** `config.PIXEL_SIZE_UM` is `None` and there is no
micron output anywhere in the pipeline. Areas are px², lengths are px.

This is not an oversight. The `.tif` files carry no usable spatial calibration
(checked by `src/inspect_tif_metadata.py`: seven of the eight have no
resolution tags at all, and the one that does reports a generic 300 DPI value
that is implausible for confocal and is almost certainly a software default).
A real µm/px figure has to come from the confocal acquisition record, not from
the image files. Until one does, converting to microns would be inventing a
scale.

## What it does

Takes 2D images of stained bone sections — one channel carrying the LCN signal
— and produces per-image and per-lacuna measurements:

- lacunar segmentation: count, area, axis lengths, shape descriptors
- canalicular network segmentation, skeletonization and per-lacuna attribution
- QC overlays and raw masks, so every segmentation step can be checked by eye
- per-image summary statistics, written as XLSX and JSON

## Repository layout

```
data/        input images
src/         pipeline code
config.py    shared configuration (paths, channel selection, output settings)
docs/        PROGRESS.md, DECISIONS_NEEDED.md
reports/     text reports, one folder per run
results/     generated masks, overlays, tables, diagnostics (see Outputs)
```

Any `code_key` file is excluded from version control — the
blinding key mapping coded specimen IDs to experimental groups must stay out of
the repository. Most of `results/` is git-ignored; the subtrees that are
committed are listed in `.gitignore`.

## Pipeline modules

| module | what it does |
| --- | --- |
| `src/count_lacunae.py` | v1 lacuna counter, single global threshold. Superseded; kept because v2 imports its image loader. |
| `src/segment_lacunae_v2.py` | **current** lacuna segmentation: multi-Otsu + marker-controlled watershed. |
| `src/canaliculi_v1.py` | **current** canalicular segmentation, skeletonization, graph cleanup and per-lacuna attribution. |
| `src/diagnose_*.py` | read-only diagnostics. They measure the pipeline and print evidence; they change nothing. |

Run any module with `--help` for its options. Typical use:

```
python src/segment_lacunae_v2.py --dir data/WT
python src/canaliculi_v1.py --dir data/WT
```

Each module's own docstring is the reference for its parameters, what each
value is, and where that value came from.

## Configuration

`config.py` holds paths, channel selection and output settings shared across
modules. Sizes and distances in it are given in **pixels**.

Note that some entries in `config.py` belong to the superseded
`count_lacunae.py` and are not read by the current modules. `PIXEL_SIZE_UM`
stays `None` — see Units above.

## Outputs

Every path is a constant in `config.py`; no script hard-codes one. The rule
throughout is that **what the current default pipeline produces sits at the
top of its folder**, and everything else sits one level down, grouped by
what it is.

```
results/
  canaliculi/<image>/          the 5 default canaliculi files
      all_method_results/      any run with a non-default switch
  lacunae/<image>/             default lacuna outputs (was results/count/)
  candidates/
      lacunae_v3/              detectors not in use by default
  diagnostics/
      phase0/ phase1/ phase2/ phase3/   read-only measurement output,
      round2/step2/                     grouped by the run that made it
reports/
  phase0_1/  overnight/        text reports, one folder per run
docs/
  PROGRESS.md  DECISIONS_NEEDED.md
```

A non-default run never overwrites a default output: its filenames carry a
suffix naming the setting AND it writes to `all_method_results/`.

`src/reorganize_outputs.py` moved the tree into this shape on 2026-09-28.
It is move-only, aborts before touching anything if a destination exists,
and is idempotent.

## Switches

Every option below is a module-level constant in `src/canaliculi_v1.py`
with a matching CLI flag. **Defaults are marked in bold and none of them
have been validated** — they are the settings that have been looked at
most, not the settings known to be right. Any non-default run writes to
`all_method_results/` with a filename suffix naming the setting, so a
comparison can never overwrite a default output.

| switch | values | CLI |
| --- | --- | --- |
| `LACUNA_SOURCE` | **`"v2"`** · `"v3_candidate"` | `--lacuna-source` |
| `PREPROCESS_MODE` | **`"tophat"`** · `"ridge"` · `"tophat+ridge"` · `"none"` | `--preprocess` |
| `THRESHOLD_MODE` | `"multiotsu_low"` · **`"hysteresis"`** | `--threshold-mode` |
| `HYSTERESIS_LOW_FRACTION` | **`0.75`** | — |
| `GAP_BRIDGING` | `False` · **`True`** | `--gap-bridging` |
| `BLOCK_GROWTH_IN_FLAGGED` | `False` · **`True`** | `--no-block-growth` |
| `EXCLUSION_MODE` | **`"none"`** · `"auto"` · `"manual"` · `"both"` | `--exclusion` |
| `ASSIGNMENT_METHOD` | **`"graph"`** · `"euclidean"` | `--method` |
| `COUNT_MODE` | **`"edge"`** · `"path"` · `"roots"` | `--count-mode` |

`THRESHOLD_MODE="hysteresis"` + `GAP_BRIDGING=True` became the defaults on
2026-09-28, which **changed the 543-2 reference check from 37.00 / 29.43 to
62.33 / 27.41**. `BLOCK_GROWTH_IN_FLAGGED` then stops those two from adding
connections along a vascular canal; it never deletes anything.

**Parameter provenance.** Every tunable constant carries a comment saying
what it does, why that value, and where the value came from — a measured
distribution, a visual check, or an explicit "initial guess, not yet
tuned". Read the comment before changing a number. Values derived from
data were derived on a fixed tuning set (542_z06, 543-2, 682_z29) with the
other five WT images held out, so a number that was tuned says so.

**What `COUNT_MODE` means.** `"edge"` counts graph edges the cell owns.
That is an OCY-style **network parameter**, not "canaliculi per cell" — a
tree with T tips has about 2T−1 edges, so edge counts run roughly double
any per-cell canaliculus count. Do not report it under that name.
`"roots"` counts distinct threads leaving the lacuna surface and is the
per-cell quantity, closest to what a person counts by eye in ImageJ.

## Where we follow OCY, and where we depart

The method draws on the published OCY pipeline (Kollmannsberger et al.,
*New J. Phys.* 2017, github.com/phi-max/OCY_connectomics). **OCY was built
for 3D confocal stacks; our data are single 2D optical sections.** That
difference drives every departure.

Followed, with the OCY file cited at each site in the code:

- top-hat background flattening and the histogram-mode offset subtraction
  before thresholding (`OCY_thr_stack.m`), and the light Gaussian before it
  (`OCY_main.m`)
- short-branch removal and the iterate-until-stable graph cleanup
  (`OCY_run_Skel2Graph3D.m`, `Skel2Graph3D`'s `THR_BRANCH`)
- assigning a canaliculus to the cell it connects to through the network,
  reached through whichever end is nearer a cell (`OCY_assign_dist.m`)
- counting canaliculi as graph edges, and the edge-length and node-degree
  distributions in the sanity report (`OCY_get_network_params.m`)

Departed from, and why:

- **Gap bridging and ridge/hysteresis options have no OCY counterpart.** In
  a 3D stack a canaliculus leaving one plane continues in the next, so
  out-of-plane truncation does not exist for OCY. In our sections 82% of
  skeleton nodes are degree-1 thread ends.
- **Exclusion of non-LCN structures has no OCY counterpart.** Our fields
  are chosen by the microscopist and routinely contain vascular canal
  edges.
- **Parameter values are re-derived from our own images, never scaled from
  OCY's.** OCY's short-branch threshold is about 2.5× their canaliculus
  diameter; applied here that would remove half of all internal edges.

## Drawing a manual exclusion mask

Some fields contain bright structures that are not canalicular network —
vascular canals, canal edges, section boundaries. A hand-drawn mask marks
those regions so they are dropped from the canaliculi mask before
skeletonization.

To make one in Fiji:

1. Open the image and draw an ROI around the region to exclude.
2. `Edit > Selection > Create Mask`.
3. Save as PNG into `data/exclusion_masks/<image_stem>.png`, where
   `<image_stem>` is the image filename without its extension.

White (non-zero) means **exclude**. The mask must be the same pixel size as
the image — the pipeline refuses a mismatched mask rather than resampling
it, because resampling would move the boundary you drew.

**Draw these blinded to genotype.** Deciding which bright regions are "not
network" is a judgement call, and making that call differently in mutant
and wild-type fields would bias the comparison. Work from coded filenames
with the `code_key` out of reach.

Two things the pipeline does regardless of what you draw:

- No pixel within a fixed margin of a lacuna is ever excluded, by hand or
  automatically. In Hyp mice the broad bright regions around lacunae are
  periosteocytic lesions, which are what this thesis measures; removing
  them would bias the genotype comparison in the direction of the
  hypothesis.
- Every exclusion is written out as `exclusion.png` next to the other
  outputs, and the excluded area is recorded in `measurements.json`, so
  what was removed is always auditable.

## Where to look first

`docs/PROGRESS.md` is the authoritative record of what exists, what is known to be
wrong, and what is still unvalidated. Read it before trusting any output here.
