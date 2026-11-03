# POL section: progress

Pre-validation. Unattended task of 2026-10-29 (user brief "add a new POL
section"). One line per step; the last line says where to resume.

Rules of the brief: main only, commit and push after each phase, no em dash
or double hyphen, no existing default or output changed (regression before
each push), deterministic only (no AI judge, no API), general rules in src/,
everything labelled pre-validation, no Hyp;Enpp1 images (none exist).

## Phases

- [x] Phase 0, LOOK: crops in results/pols/phase0_look/, results/pols/FINDINGS.md
- [x] Phase 1, DEFINE: results/pols/DEFINITION.md
- [x] Phase 2, BUILD: src/pols.py, switch for CSV export, overlays
- [x] Phase 3, RUN: results/<group>/pols/ for WT, WT_HP, Hyp_RD, Hyp_HP;
      results/pols/summary_by_group.csv, results/pols/SUMMARY.md
- [x] Phase 4, REPORT: results/pols/REPORT.md, push, git log

## Log

- 2026-10-29: started from main 1ba3b38 (git pull: up to date).
- Phase 0 done: contact sheets of all 35 fields, crop sheets of 10 fields, profile
  tables; FINDINGS.md says POLs cannot be told apart as a separate zone (no dark ring,
  no distinct halo, no step inside the body; WT surround about 2.3 um of glow). Made
  by a scratch script (no code change allowed in phase 0); phase 2 moves it into the
  repository. Regression before push: PASS, 2 runs, 6800 numbers each.
- Phase 1 done: DEFINITION.md, a POL proxy (body plus the surround above the bone
  background): 8 sectors of 45 degrees, 3 band slab median, level background + 0.10 x
  (surface minus background), cap 8 um from the body edge, territories so two
  surrounds never share a pixel; flags edge, vessel, neighbour, incomplete, no
  contrast. Every value reused from the glow zone or chosen on no image. Regression
  before push: PASS, 2 runs.
- Phase 2 done: src/pols.py with measure (overlays always, the switch --csv for the
  two tables), summary (summary_by_group.csv, SUMMARY.md with a neighbour flag
  sensitivity table) and selftest (10 of 10 synthetic checks pass). It reads the saved
  detection only and writes only results/<group>/pols/. The phase 0 look moved into
  python src/diagnostics.py pol-look; its 16 committed files are remade byte for byte,
  plus phase0_body_core_rim.csv for FINDINGS item 4. A trial run showed the "no
  contrast" flag firing when the surface band was walled in by the vascular mask; that
  case is now "no level" (incomplete) and no contrast means surface at or below
  background. DEFINITION.md updated to match.
- Phase 3 done: measure with the switch --csv on all four groups from commit d18414a
  (run records: git_dirty False, no failed image), then summary. 35 overlays, 4 x 2
  tables, summary_by_group.csv, SUMMARY.md. Measured lacunae: WT 71 of 100 with a
  shape measure, WT_HP 55 of 113, Hyp_RD 86 of 251, Hyp_HP 27 of 250 (two Hyp_HP
  images have none). A rerun of WT gives all 11 files byte for byte.
- Phase 4 done: REPORT.md (one page; every number checked against the phase 3
  outputs), README (folder table, Still open item 7), docs/METHODS.md section 24 and
  the sentence on POLs in its introduction, results/README.md (POL proxy section).
- All phases done. Nothing to resume; the open decisions are in REPORT.md.
- 2026-11-02: QC overlay on the original image (commit 8e201df), named by coded ID;
  superseded by the layout below.

# POL as a section: progress

User brief of 2026-11-03 ("make POL a section like lacunae and canaliculi"). Rules:
main only, commit and push after each phase with the outputs, regression before
each push (PASS or FAIL in the commit message), no em dash or double hyphen, no
measurement, segmentation, flag or existing value changed, logic in src/pols.py,
no AI judge or API, everything "POL proxy, pre-validation".

## Phases

- [x] L1, CODE: src/pols.py writes results/<group>/<image>/4_pols/ (overlay,
      outlines, measured, per-lacuna csv, json) and results/<group>/all_images/pols/
      (pols_all_images.csv and .xlsx, contact_sheet.png); commands check and
      blind-review; selftest with checks of the tint and the flag letters
- [x] L2, RUN: measure with the switch --csv on all four groups, summary, check
      against the old tables (results/pols/layout_check.csv)
- [x] L3, BLIND: results/blind_review/pols/P001.png ..., key outside the repository
      (F:/lcn-quant-keys/pols_blind_review_key.csv), never committed
- [ ] L4, REMOVE: results/<group>/pols/ deleted in its own commit, after L2 verified
      the new files equal; check run again
- [ ] L5, DOCS: results/README.md, docs/METHODS.md, README.md, results/pols/
      REPORT_LAYOUT.md; push, git log

## Log

- 2026-11-03: started from main 8e201df (git pull: up to date). Two untracked test
  files of 2026-11-02 sit in results/<group>/pols/overlays/ (*_pol_overlay.png); they
  go with that folder in L4.
- L1: code written; selftest 18 of 18; a trial on a copy of WT outside the repository
  gave all five files per image, pols_all_images.csv equal byte for byte to the old
  WT_pols_per_image.csv, and every picture redrawn from its csv equal to the file.
  Regression before push: PASS, 2 runs. Committed and pushed.
- L2: measure with the switch --csv on WT, WT_HP, Hyp_RD, Hyp_HP from commit dd72608
  (35 records, git_dirty False, no failed image); summary: summary_by_group.csv
  unchanged byte for byte, SUMMARY.md changed only in the line naming its source
  table; check: PASS, 35 of 35 images, old tables compared (every per-lacuna csv
  equal to the old table's rows, every pols_all_images.csv equal byte for byte to the
  old per-image table, all three pictures equal to the pictures the csv gives),
  results/pols/layout_check.csv. 105 pictures, 140 MB. Regression before push: PASS.
- L3: blind-review wrote P001.png to P035.png into results/blind_review/pols/, byte
  copies of the measured pictures in a shuffled order from the system's random
  source, no PNG metadata; key at F:/lcn-quant-keys/pols_blind_review_key.csv,
  outside the repository, not committed. A first set was made and deleted before
  any commit, because its check printed four code to image pairs into the session;
  the committed set is a fresh draw whose pairs were never printed. Refusals checked:
  a key inside the repository, an existing key, a non-empty output folder.
  Regression before push: PASS.
  Resume: L4 (git rm results/<group>/pols/, delete the two untracked test overlays,
  run check again).
