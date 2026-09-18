# lcn-quant

Quantification of the osteocyte lacuno-canalicular network (LCN) from 2D bone
images.

## What it does

Takes calibrated 2D images of stained bone sections — one channel carrying the
LCN signal — and turns them into per-image and per-lacuna measurements:

- lacunar segmentation (count, area, density, shape)
- canalicular signal extracted around the lacunae
- calibrated output in physical units (µm, µm²), written as CSV
- QC overlays so every segmentation can be checked by eye

All measurements depend on the pixel size recorded in `config.py`. Set it from
the image metadata before running anything.

## Repository layout

```
data/        input images (git-ignored, not redistributed)
results/     generated masks, overlays, CSVs, figures (git-ignored)
src/         pipeline code
config.py    all analysis parameters
```

`data/` and `results/` are excluded from version control, as is any `code_key`
file — the blinding key that maps coded specimen IDs to experimental groups
must stay out of the repository.

## Configuration

Every tunable lives in [config.py](config.py): channel selection, pixel size,
pre-processing, threshold method, and object-size filters. Sizes there are
given in microns and converted to pixels by the pipeline, so the settings stay
valid across objectives. An analysis run is fully described by `config.py` plus
the contents of `data/`.

## Status

Scaffolding only. Configuration and repository structure are in place; the
pipeline code in `src/` is not written yet.
