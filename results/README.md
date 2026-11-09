# Results

Everything the pipeline and the figure code produce, for the four groups of
`config.GROUPS`: WT (8 images, the reference), WT_HP, Hyp_RD and Hyp_HP (9
each). Pre-validation: no number here has been checked against a manual count.
The pipeline reports pixels (0.13 um/px); `3_pols/`, `SUMMARY.xlsx` and the
statistics report um.

**Start here:** [HOW_TO_READ.md](HOW_TO_READ.md) (half a page), the key
pictures in `<group>/0_key_results/`, and every number in one file,
[SUMMARY.xlsx](SUMMARY.xlsx). The statistics: [summary/STATISTICS.md](summary/STATISTICS.md).

## Layout

```
results/
  README.md          this page
  HOW_TO_READ.md     where the key pictures are and which numbers matter
  SUMMARY.xlsx       every number in one file: Read me, Per group, Per animal, Per image, Statistics
  summary/           every table that sets the groups side by side, and STATISTICS.md
  WT/  WT_HP/  Hyp_RD/  Hyp_HP/
    0_key_results/     copies of the three key pictures of every image
    1_lacunae/         the lacuna stage, every image of the group side by side
    2_canaliculi/      the network stage, and the network figures
    3_pols/            the POL footprints (working definition) and lacunar size
    4_quantification/  every measured number, the group table, the figures
    5_archive/         deleted on 2026-11-09 (see below)
  archive/           old material that belongs to no one group
```

Every group folder holds these sections; `5_archive/` only when a script has
written to it again since it was deleted. Inside a section there
is no folder per image: each file is named after its image, `<image>_...`,
where `<image>` is the short label of the image (`config.IMAGE_LABELS` for WT,
the cleaned file name for the other groups).

## Each group at a glance

| group | lacunae | POL candidate | numbers | figures |
| - | - | - | - | - |
| **WT** | [contact sheet](WT/1_lacunae/contact_sheet.png) | [contact sheet](WT/3_pols/contact_sheet.png), [table](WT/3_pols/pols_all_images.csv) | [group table xlsx](WT/4_quantification/quantification_all_images.xlsx), [csv](WT/4_quantification/quantification_all_images.csv) | [Fig01](WT/4_quantification/Fig01_contact_sheet.png), [Fig03](WT/4_quantification/Fig03_threshold_sensitivity.png), [Fig04](WT/4_quantification/Fig04_per_field.png), [S01](WT/4_quantification/S01_switch_examples.png) |
| **WT_HP** | [contact sheet](WT_HP/1_lacunae/contact_sheet.png) | [contact sheet](WT_HP/3_pols/contact_sheet.png), [table](WT_HP/3_pols/pols_all_images.csv) | [group table xlsx](WT_HP/4_quantification/quantification_all_images.xlsx), [csv](WT_HP/4_quantification/quantification_all_images.csv) | [Fig01](WT_HP/4_quantification/Fig01_contact_sheet.png), [Fig03](WT_HP/4_quantification/Fig03_threshold_sensitivity.png), [Fig04](WT_HP/4_quantification/Fig04_per_field.png), [S01](WT_HP/4_quantification/S01_switch_examples.png) |
| **Hyp_RD** | [contact sheet](Hyp_RD/1_lacunae/contact_sheet.png) | [contact sheet](Hyp_RD/3_pols/contact_sheet.png), [table](Hyp_RD/3_pols/pols_all_images.csv) | [group table xlsx](Hyp_RD/4_quantification/quantification_all_images.xlsx), [csv](Hyp_RD/4_quantification/quantification_all_images.csv) | [Fig01](Hyp_RD/4_quantification/Fig01_contact_sheet.png), [Fig03](Hyp_RD/4_quantification/Fig03_threshold_sensitivity.png), [Fig04](Hyp_RD/4_quantification/Fig04_per_field.png), [S01](Hyp_RD/4_quantification/S01_switch_examples.png) |
| **Hyp_HP** | [contact sheet](Hyp_HP/1_lacunae/contact_sheet.png) | [contact sheet](Hyp_HP/3_pols/contact_sheet.png), [table](Hyp_HP/3_pols/pols_all_images.csv) | [group table xlsx](Hyp_HP/4_quantification/quantification_all_images.xlsx), [csv](Hyp_HP/4_quantification/quantification_all_images.csv) | [Fig01](Hyp_HP/4_quantification/Fig01_contact_sheet.png), [Fig03](Hyp_HP/4_quantification/Fig03_threshold_sensitivity.png), [Fig04](Hyp_HP/4_quantification/Fig04_per_field.png), [S01](Hyp_HP/4_quantification/S01_switch_examples.png) |

Across groups: [group overview](summary/group_overview.xlsx),
[group QC](summary/group_qc.csv),
[lacunar size by group](summary/pols_lacunar_size_by_group.csv).
Every file moved into this layout on 2026-11-04: [MOVE_MAP.csv](archive/MOVE_MAP.csv).

## What each section holds

**0_key_results/**, written by `src/key_results.py` (2026-11-06): for every
image, copies of `<image>_1_lacunae_outlines.png` (from `1_lacunae/`),
`<image>_2_canaliculi_verification.png` (from `2_canaliculi/`) and
`<image>_3_pols_outlines.png` (from `3_pols/`), and a README. The originals
are not changed; `python src/key_results.py check` compares every copy with
its original.

**1_lacunae/**, written by `src/lacunae.py`:
`<image>_lacunae_outlines.png` (the image with the kept lacunae outlined),
`<image>_lacuna_labels.png` (16 bit, 0 outside a lacuna, its id 1..N inside;
every lacuna measure is taken from it), `<image>_lacunae_detection.json` (what
the stage did, with its parameters), `<image>_excluded_region.png` (the
excluded region shaded grey on the original, with the kept lacunae in green:
saturated border regions and very large bright structures, with a 3 um
margin, config section g9) and `<image>_excluded_region_mask.png` (the same
region, 0 or 255, which quantification reads), and `contact_sheet.png`, every
outlines picture of the group, small.

**2_canaliculi/**, written by `src/canaliculi.py`:
`<image>_canaliculi_mask.png`, `_skeleton.png`, `_verification.png` (each
lacuna and the threads it owns in one colour), `_vascular_mask.png`,
`_unattached.png`, `_graph.pickle` and `_detection.json`; and from the figure
script, `<image>_figure_network.png` and `.pdf` with
`<image>_figure_network_checks.json` (drawn values against the pipeline).

**3_pols/**, written by `src/pols.py`: the POL footprints of the working
definition below, and lacunar size. `<image>_pols_outlines.png` (every
footprint outlined on the original: green normal size, yellow above 2 x the
WT median, cyan a cluster, grey touching the frame; excluded regions shaded
grey; id and area beside each; the image's numbers in the legend; 10 um bar),
`<image>_pols_lacunar_size.png` (each measured lacuna
filled by its area relative to the WT median, one colour scale for every
group, colour bar in um2, flagged lacunae outlined grey), `<image>_pols_lacunar_size.csv`
(id, area_um2, ratio_to_WT_median, flag, cluster), `pols_all_images.csv` and `.xlsx`
(per image n, mean, median, 90th percentile of area and ratio, and the POL
metrics: n lacunae, share above 2 x the WT median and above 100 um2, clusters,
POL area per analysed area), `contact_sheet.png`, `contact_sheet_outlines.png`
and `README.md`. No lesion is called here.

**Working POL definition (2026-11-06; to be confirmed by Dr. Murshed).** In
rhodamine confocal images the dye fills the lacuna and the unmineralized
pericellular matrix around the osteocyte together, so a periosteocytic lesion
shows as an enlarged, irregular, dye-filled lacunar space: that space is the
POL footprint. No separate halo is visible around it (the look of 2026-10-29,
`results/archive/pols/FINDINGS.md`), so the footprint is the lacuna as the
lacuna stage outlines it, and the POL measures are measures of that outline:
its area, against the WT median, and the share of the analysed area it covers.
Status: working definition, not confirmed.

**4_quantification/**, written by `src/quantification.py` and the figure script:
`<image>_quantification.json`, `.xlsx` and `.pdf` (every measured number of the
image), `quantification_all_images.csv`, `.xlsx` and `.pdf` (one row per
image, the only cross-image table), `<image>_figure_cell_gallery` and
`<image>_figure_overview` (`.png`, `.pdf`, with their checks and
`<image>_figure_inset_choice.json`), the group figures `Fig01` to `Fig04`,
`S01` and `S02` with their value files, and `display_window.json`.

**ai_judge/ in the sections** (since 2026-11-06, moved from `5_archive/`,
`archive/MOVE_MAP.csv`): the AI lacuna judge's set of the group, the same file
names as the section around it, in `1_lacunae/ai_judge/` (its log in
`ai_log/`), `2_canaliculi/ai_judge/` and `4_quantification/ai_judge/`; for WT
also the AI thread judge in `1_lacunae/ai_judge_canaliculi/`,
`2_canaliculi/ai_judge_canaliculi/` (with its log, `compare/` and run records)
and `4_quantification/ai_judge_canaliculi/`. Both were made with the detector
before `method-freeze-v1` and do not match the current results until rerun
(a README in each folder). Not validated.

**5_archive/**: deleted in every group on 2026-11-09. It held
`pol_ring_proxy/` (the retired ring proxy of the POL section: per image
overlay, measured and outlines pictures, csv and json, the group table and
contact sheet), now only in git history (for instance at tag
`method-freeze-v2`), and the untracked `not_used/` and
`variants_per_image_brightness/` of the figure script. `make_figures.py all`
and `pol_ring_proxy.py` still write here, so the folder comes back when they
run.

**summary/**: `group_overview.csv` and `.xlsx` (every image of every group,
one row each), `group_qc.csv` (QC list of the groups other than WT),
`pols_lacunar_size_by_group.csv` (lacunar size and the POL metrics per group),
`pols_by_animal.csv` (the same per animal of `data/animals.csv`), and from
`src/animal_stats.py`: `STATISTICS.md` (the genotype by diet statistics in
plain words), `per_group.csv`, `per_animal.csv`, `per_image.csv` and
`statistics_models.csv`.

**archive/**: `blind_review/` (POL ring proxy pictures under shuffled codes),
`format_test/` (TIFF against JPEG), `pols/` (the ring proxy reports: FINDINGS,
DEFINITION, SUMMARY, REPORT, REPORT_LAYOUT, PROGRESS, the phase 0 look,
layout_check), `ai_judge/` (run records of the lacuna judge, its `dry_run/`
and `review/`, and the README of each judge), `MOVE_MAP.csv` (every file moved
into this layout, old path and new path), `REPORT_REORG.md` (what the move
did) and `PROGRESS_LAYOUT.md` (its working log); `REVIEW_LOOP.md` and
`REPORT_LOOP.md` with `review_loop/` (the review loop of 2026-11-05) and
`audit/` (the bias audit of 2026-11-06: `CAP_AUDIT.md`, `DIM_AUDIT.md`,
`FIX_LOG.md`, `REPORT_AUDIT.md`, the crops and the reviewer's tables).

## How to regenerate

From the repository root, with the project's Python. For one group, `G` one of
WT, WT_HP, Hyp_RD, Hyp_HP:

```
python src/lacunae.py -d data/G                 # 1_lacunae
python src/canaliculi.py -d data/G              # 2_canaliculi
python src/quantification.py -d data/G          # 4_quantification, numbers and group table
python src/diagnostics.py field-summary -d data/G -r results/G -o .cache/field_summary/G
python -u src/make_figures.py -g G all          # the figures, in 2_canaliculi and 4_quantification
python src/pols.py measure -d data/G            # 3_pols
```

For WT the field summary goes to `.cache/field_summary` (no group folder).
Across groups:

```
python src/pols.py all                          # 3_pols of every group, summary/pols_lacunar_size_by_group.csv, pols_by_animal.csv
python src/animal_stats.py run                  # summary/STATISTICS.md and the per group, animal, image tables
python src/key_results.py all                   # <group>/0_key_results/ and SUMMARY.xlsx
python src/diagnostics.py group-overview        # summary/group_overview.csv and .xlsx
python src/diagnostics.py group-qc              # summary/group_qc.csv
python src/diagnostics.py layout-check          # this layout, files per section, every group
python src/diagnostics.py regression            # every WT number against results/WT/, tolerance 0
python -u src/make_figures.py -g G check        # drawn numbers against results/G/
```

`results/WT/` is the reference `regression` compares with, so regenerate it
only on purpose. Option `-o OTHER_FOLDER` writes the same layout elsewhere.
Each figure is skipped when its png and pdf exist; delete them to redraw.

Method and parameters: [docs/METHODS.md](../docs/METHODS.md). Where to start:
[docs/START_HERE.md](../docs/START_HERE.md).
