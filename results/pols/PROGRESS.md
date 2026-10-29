# POL section: progress

Pre-validation. Unattended task of 2026-10-29 (user brief "add a new POL
section"). One line per step; the last line says where to resume.

Rules of the brief: main only, commit and push after each phase, no em dash
or double hyphen, no existing default or output changed (regression before
each push), deterministic only (no AI judge, no API), general rules in src/,
everything labelled pre-validation, no Hyp;Enpp1 images (none exist).

## Phases

- [x] Phase 0, LOOK: crops in results/pols/phase0_look/, results/pols/FINDINGS.md
- [ ] Phase 1, DEFINE: results/pols/DEFINITION.md
- [ ] Phase 2, BUILD: src/pols.py, switch for CSV export, overlays
- [ ] Phase 3, RUN: results/<group>/pols/ for WT, WT_HP, Hyp_RD, Hyp_HP;
      results/pols/summary_by_group.csv, results/pols/SUMMARY.md
- [ ] Phase 4, REPORT: results/pols/REPORT.md, push, git log

## Log

- 2026-10-29: started from main 1ba3b38 (git pull: up to date).
- Phase 0 done: contact sheets of all 35 fields, crop sheets of 10 fields, profile
  tables; FINDINGS.md says POLs cannot be told apart as a separate zone (no dark ring,
  no distinct halo, no step inside the body; WT surround about 2.3 um of glow). Made
  by a scratch script (no code change allowed in phase 0); phase 2 moves it into the
  repository. Regression before push: PASS, 2 runs, 6800 numbers each.
- Resume at: phase 1 (DEFINITION.md drafted, not yet committed).
