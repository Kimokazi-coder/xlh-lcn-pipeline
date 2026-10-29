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
- [ ] Phase 4, REPORT: results/pols/REPORT.md, push, git log

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
- Resume at: phase 4 (REPORT.md drafted; README, METHODS section 24 and the results
  README edited, not yet committed).
