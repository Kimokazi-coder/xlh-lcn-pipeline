# Results

Everything the pipeline and the figure code produce, for the four groups of
`config.GROUPS`: WT (8 images, the reference), WT_HP, Hyp_RD and Hyp_HP (9
each). Pre-validation: no number here has been checked against a manual count.
The pipeline reports pixels (0.13 um/px); `3_pols/`, the summaries,
`SUMMARY.xlsx` and the statistics report um.

**Start here:** [HOW_TO_READ.md](HOW_TO_READ.md) (half a page), then any
image's folder: its `non_ai_run/summary/`, its `ai_judges/summary/` and its
`comparison/`. Every number is in one file, [SUMMARY.xlsx](SUMMARY.xlsx). The
statistics: [summary/STATISTICS.md](summary/STATISTICS.md).

## Layout

Since 2026-11-10 every image has a folder of its own (`docs/METHODS.md` 32):

```
results/
  README.md          this page
  HOW_TO_READ.md     where the pictures are and which numbers matter
  SUMMARY.xlsx       every number in one file: Read me, Per group, Per animal, Per image, Statistics, Judge on vs off
  summary/           every table that sets the groups side by side, and STATISTICS.md
  WT/  WT_HP/  Hyp_RD/  Hyp_HP/
    <image>/                 one folder per image
      non_ai_run/            the method itself
        1_lacunae/           the lacuna stage
        2_canaliculi/        the network stage, and the network figure
        3_pols/              the POL footprints (working definition) and lacunar size
        4_quantification/    every measured number, the overview and the cell gallery
        summary/             the key pictures and numbers of this run
      ai_judges/             the same pipeline with the AI lacuna and POL judges on
        1_lacunae/ ...       the same five folders, with the judges' logs in
                             1_lacunae/ai_log/ and 3_pols/ai_log/
      comparison/            the two runs side by side, and what the AI changed
    0_key_results/           copies of the three key pictures of every image (non-AI run)
    1_lacunae/               the group's contact sheet
    3_pols/                  the group's POL tables and contact sheets (ai_judges/: the same, AI run)
    4_quantification/        the group table and the group figures Fig01 to Fig04, S01, S02
                             (ai_judges/: the group table of the AI run)
```

Every file keeps its image's short label in its name, `<image>_...`
(`config.IMAGE_LABELS` for WT, the cleaned file name for the other groups),
so a file copied out of its folder still says which image it is. What belongs
to the whole group stays in the group folder, in the section it belongs to.

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

## What each image folder holds

The same files in both runs, `non_ai_run/` and `ai_judges/` (the network
figure, the overview and the cell gallery are drawn for the non-AI run only).

**1_lacunae/**, written by `src/lacunae.py`: `<image>_lacunae_outlines.png`
(the image with the kept lacunae outlined), `<image>_lacuna_labels.png` (16
bit, 0 outside a lacuna, its id 1..N inside; every lacuna measure is taken from
it), `<image>_lacunae_detection.json` (what the stage did, with its
parameters), `<image>_excluded_region.png` (the excluded region shaded grey on
the original, with the kept lacunae in green: saturated border regions and very
large bright structures, with a 3 um margin, config section g9) and
`<image>_excluded_region_mask.png` (the same region, 0 or 255, which
quantification reads). In `ai_judges/`, `ai_log/` holds what the AI lacuna
judge was shown and what it said.

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
`<image>_pols_lacunar_size.png` (each measured lacuna filled by its area
relative to the WT median, one colour scale for every group, colour bar in
um2, flagged lacunae outlined grey) and `<image>_pols_lacunar_size.csv` (id,
area_um2, ratio_to_WT_median, flag, cluster). In `ai_judges/`, `ai_log/` holds
what the AI POL judge was shown and what it said. No lesion is called here.

**4_quantification/**, written by `src/quantification.py` and the figure
script: `<image>_quantification.json`, `.xlsx` and `.pdf` (every measured
number of the image), and in the non-AI run `<image>_figure_cell_gallery` and
`<image>_figure_overview` (`.png`, `.pdf`, with their checks and
`<image>_figure_inset_choice.json`).

**summary/**, written by `python src/key_results.py samples`: copies of the
lacunae outlines and the canaliculi verification picture,
`<image>_key_numbers.png` and `.csv` (the main numbers of the run: lacunae,
median and 90th percentile area, share enlarged, POL area per analysed area,
clusters, roots, canalicular length) and `<image>_pols_explained.png` (the POL
outlines with a panel of plain text beside them: what we are looking for and
how to read the picture).

**comparison/**, written by the same command: `<image>_compare_lacunae.png`,
`_compare_canaliculi.png` and `_compare_pols.png` (the non-AI run, the AI run
and a third panel with only what the AI changed: red removed, blue added,
yellow merged or cluster flag changed), and `<image>_compare_numbers.png` and
`.csv` (each key number in both runs and the difference).

**Working POL definition (2026-11-06; to be confirmed by Dr. Murshed).** In
rhodamine confocal images the dye fills the lacuna and the unmineralized
pericellular matrix around the osteocyte together, so a periosteocytic lesion
shows as an enlarged, irregular, dye-filled lacunar space: that space is the
POL footprint. No separate halo is visible around it (the look of 2026-10-29,
`results/archive/pols/FINDINGS.md`, in git at commit `2933666`), so the
footprint is the lacuna as the lacuna stage outlines it, and the POL
measures are measures of that outline: its area, against the WT median, and
the share of the analysed area it covers. Status: working definition, not
confirmed.

**The AI judges run** (`docs/METHODS.md` 29 and 30): the AI lacuna judge said
which outlines of the lacuna stage are lacunae, and the AI POL judge joined
pieces of one body, set the cluster flag and removed what is no lacuna. Neither
draws a boundary, and the canaliculi are traced by the normal method around
the lacunae they kept. Made from the judges' logs, offline. The canaliculi
judge's set, made on the lacunae before the POL judge, is not part of this
layout (in git history at commit `e915329`). Not validated.

## The group folders

**0_key_results/**, written by `src/key_results.py all`: for every image,
copies of `<image>_1_lacunae_outlines.png`, `<image>_2_canaliculi_verification.png`
and `<image>_3_pols_outlines.png` from the image's `non_ai_run/`, and a
README. `python src/key_results.py check` compares every copy with its
original.

**1_lacunae/**: `contact_sheet.png`, every outlines picture of the group,
small. **3_pols/**: `pols_all_images.csv` and `.xlsx` (per image n, mean,
median, 90th percentile of area and ratio, and the POL metrics),
`contact_sheet.png`, `contact_sheet_outlines.png` and `README.md`; the same
for the AI run in `3_pols/ai_judges/`. **4_quantification/**:
`quantification_all_images.csv`, `.xlsx` and `.pdf` (one row per image), the
group figures `Fig01` to `Fig04`, `S01` and `S02` with their value files, and
`display_window.json`; the AI run's group table in `4_quantification/ai_judges/`.
Contact sheets leave the held-out images out.

**summary/**: `group_overview.csv` and `.xlsx` (every image of every group,
one row each), `group_qc.csv` (QC list of the groups other than WT),
`pols_lacunar_size_by_group.csv` (lacunar size and the POL metrics per group),
`pols_by_animal.csv` (the same per animal of `data/animals.csv`), and from
`src/animal_stats.py`: `STATISTICS.md` (the genotype by diet statistics in
plain words), `per_group.csv`, `per_animal.csv`, `per_image.csv` and
`statistics_models.csv`.

Deleted, in git history: `5_archive/` in every group (2026-11-09,
`docs/METHODS.md` 28) and `archive/`, the records of no one group (2026-11-10,
`docs/METHODS.md` 31, every file at commit `2933666`).

## How to regenerate

From the repository root, with the project's Python. For one group, `G` one of
WT, WT_HP, Hyp_RD, Hyp_HP:

```
python src/lacunae.py -d data/G                 # <image>/non_ai_run/1_lacunae
python src/canaliculi.py -d data/G              # <image>/non_ai_run/2_canaliculi
python src/quantification.py -d data/G          # <image>/non_ai_run/4_quantification and the group table
python src/diagnostics.py field-summary -d data/G -r results/G -o .cache/field_summary/G
python -u src/make_figures.py -g G all          # the figures
python src/pols.py measure -d data/G            # <image>/non_ai_run/3_pols and the group's 3_pols/
```

For WT the field summary goes to `.cache/field_summary` (no group folder).
Across groups:

```
python src/pols.py all                          # 3_pols of every group, summary/pols_lacunar_size_by_group.csv, pols_by_animal.csv
LCN_HOLDOUT_MODE=FINAL python src/diagnostics.py ai-lacuna-run --with-pol-judge   # every image's ai_judges/, from the judges' logs
LCN_HOLDOUT_MODE=FINAL python src/pols.py all --set ai_judges                    # every image's ai_judges/3_pols
python src/animal_stats.py run                  # summary/STATISTICS.md and the per group, animal, image tables
python src/key_results.py all                   # <group>/0_key_results/ and SUMMARY.xlsx
LCN_HOLDOUT_MODE=FINAL python src/key_results.py samples                         # every image's summary/ and comparison/
python src/diagnostics.py group-overview        # summary/group_overview.csv and .xlsx
python src/diagnostics.py group-qc              # summary/group_qc.csv
python src/diagnostics.py layout-check          # this layout, every group
python src/diagnostics.py regression            # every WT number against results/WT/, tolerance 0
python -u src/make_figures.py -g G check        # drawn numbers against results/G/
```

`results/WT/` is the reference `regression` compares with, so regenerate it
only on purpose. Option `-o OTHER_FOLDER` writes the same layout elsewhere.
Each figure is skipped when its png and pdf exist; delete them to redraw.
`key_results.py samples` in FINAL mode measures every run against the same
WT median as the pictures and `SUMMARY.xlsx`.

Method and parameters: [docs/METHODS.md](../docs/METHODS.md). Where to start:
[docs/START_HERE.md](../docs/START_HERE.md).
