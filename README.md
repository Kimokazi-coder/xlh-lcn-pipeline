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
data/        input images (git-ignored, not redistributed)
results/     generated masks, overlays, tables, diagnostics
src/         pipeline code
config.py    shared configuration (paths, channel selection, output settings)
PROGRESS.md  current state, known issues, what is and is not validated
```

`data/` is excluded from version control, as is any `code_key` file — the
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

## Where to look first

`PROGRESS.md` is the authoritative record of what exists, what is known to be
wrong, and what is still unvalidated. Read it before trusting any output here.
