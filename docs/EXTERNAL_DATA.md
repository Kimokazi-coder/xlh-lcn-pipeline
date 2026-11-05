# External data for the final validation

**Status: pre-validation. Nothing here is used to tune or choose anything.**
Downloaded on 2026-11-05 into `../external_data/` (on this machine
`F:/external_data/`), outside the repository and never committed. Code from
these sources is never copied into `src/` and never run by the pipeline.

## Summary

| source | what it is | usable manual lacuna labels |
| - | - | - |
| Zenodo 291852 | raw 3D confocal stacks, mouse and sheep bone | **no** |
| OCY_connectomics (GitHub) | MATLAB analysis code for those stacks | **no** |
| OsteocyteNetworkConnectivityAnalysis (GitHub) | PyTorch code and one trained model | **no** (no images, no labels in the repository) |
| TINA (Bitbucket) | Python tool for 3D network analysis | **no** (its test folder is empty) |

**None of the four contains manual outlines, centres or counts of lacunae.**
So none of them can serve as ground truth for the lacuna stage. The Zenodo
stacks are real LCN images and could be run through the pipeline for a
qualitative look, but they are 3D at another pixel size and stain, and there
is nothing to score the result against.

## Zenodo record 291852

- Source: https://zenodo.org/records/291852, DOI 10.5281/zenodo.291852. Data for
  Kollmannsberger et al., "The small world of osteocytes: connectomics of the
  lacuno-canalicular network in bone", New J. Phys. 19 (2017) 073019,
  doi 10.1088/1367-2630/aa764b (arXiv 1702.04117).
- Downloaded: 2026-11-05, `zenodo_291852/Data.zip`.
- Licence: CC BY 4.0 (record metadata).
- Size: 438,402,761 bytes zipped, 774.8 MB unzipped, 2684 entries.
- Checksum: MD5 `819584e6fb82501efe9c6197cf375d6f` (equal to the record's),
  SHA-256 `63b99de3c553f55df655887dbf983ce1865f50307b6c12e908a67b32fd27f657`.
- Content: 20 stacks, 5 each of mouse cross section, mouse longitudinal,
  sheep cross section, sheep longitudinal (`Data/mouse_cs/1` to `5`, and so on),
  2640 single-slice TIFFs (two channels per slice, `ch00` and `ch01`), and 20
  `Thumbs.db` files (Windows thumbnail caches, ignored). No label, mask or
  table file.
- Imaging, from the TIFF metadata and the paper: Rhodamine-6G stain (paper,
  protocol cited there); Leica confocal (metadata `TCSNTV`; the paper says
  Leica DM IRBE), objective PL APO 100x/1.40 oil; 512 x 512 px, 0.195 um per
  px in x and y, 0.2 um z step; 51 sections (10 um) per stack, 101 sections
  (20 um) for 6 of the mouse stacks; 8 bit. **3D**, while our images are 2D
  sections at 0.13 um per px. Which of the two channels is the fluorescence is
  not stated in the metadata read.
- Labels: none. The paper segments cell lacunae automatically ("a modified 3D
  watershed algorithm") and publishes no manual annotation.

## OCY_connectomics

- Source: https://github.com/phi-max/OCY_connectomics, cloned 2026-11-05 into
  `OCY_connectomics_code/repo`, commit `5335402955cfe73a1b95477d73bf3ccd13501203`
  (2018-02-02).
- Licence: GPL-3.0 (LICENSE file).
- Size: 179,079 bytes, 28 tracked files.
- What it is: MATLAB scripts that threshold, skeletonize and analyse the Zenodo
  stacks (needs MATLAB, Skeleton3D, Skel2Graph3D, MatlabBGL). Not run here.
- Labels: none. Its outputs (cell masks, graphs) are computed, not manual, and
  are not part of the Zenodo record.

## OsteocyteNetworkConnectivityAnalysis

- Source: https://github.com/sdvetter/OsteocyteNetworkConnectivityAnalysis,
  cloned 2026-11-05 into `OsteocyteNetworkConnectivityAnalysis/repo`, commit
  `93df6c50d4e06050b822974e28629ee570897393` (2026-01-13). Paper: Vetter et al.,
  PLOS Comput. Biol. 22 (2026) e1013914, doi 10.1371/journal.pcbi.1013914
  (CC BY 4.0).
- Licence: MIT (LICENSE file).
- Size: 15,483,068 bytes, 7 tracked files, among them the trained model
  `attentionunet_lowlr.pth`, SHA-256
  `37831da869ee913b2141c20312263b0ab2133f86874c1db8e62880fa0da21f9d`. The model
  file is a pickle and was not loaded.
- What it is: an Attention U-Net (MONAI, PyTorch) that segments osteocytes and
  dendrites in 2D confocal images, and a notebook for the connectivity
  analysis. Its training script expects osteocyte and dendrite label masks
  (512 x 512 px) in a `training_data/` folder that the repository does not
  contain.
- Imaging: confocal laser scanning microscopy of cleared mouse bone (paper);
  stain and pixel size were not found, because the full text on PMC could not
  be read (it served a browser check) and the record page does not give them.
- Labels: the paper used manual labels for training, but **they are not in the
  repository**, and no data link was found. They might be asked for from the
  authors.

## TINA (Tool for Image and Network Analysis)

- Source: https://bitbucket.org/refelix/tina (the address on the Wurzburg
  group's page), cloned 2026-11-05 into `TINA/repo`, commit
  `a2de3dd1ff4fffe945c6a845b8901b3458b6c9b2` (2017-07-03, the only commit).
- Licence: **MIT** in the repository's `licence.md` (Copyright 2015 Felix
  Repp). The brief expected BSD; the README mentions BSD only for its `lib/`
  folder.
- Size: 4,407,489 bytes, 287 tracked files.
- What it is: Python 2 scripts (bare `print` statements) for 3D OLCN analysis in human osteons
  (thresholding, external skeletonization, NetworkX graphs), from F. Repp's
  PhD at the MPIKG. Not run here.
- Data and labels: none. `test/` and `thinvox/` hold only a `spacer.txt`; the
  README says to contact the authors for data.
