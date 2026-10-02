# Canaliculi v2 progress

base SHA: 867338079ce8a9c97cd69c1551ca42e68fb1bebb (origin/publication-fixes tip; tag before-canaliculi-v2)
last update: 2026-10-03 03:40
next action: V2 docs/NETWORK_TUNING_PROTOCOL.md

Status values: TODO, DONE, PARTIAL, FAILED, SKIPPED. The commit SHA is the commit that holds the
item's code and outputs. UNPUSHED after an id means its push failed and is retried at the next commit.

| id | description | status | commit SHA | note |
|---|---|---|---|---|
| 0.1 | Branch canaliculi-v2, tag before-canaliculi-v2, this file | DONE | 3d8cc0b | branch from origin/publication-fixes 8673380; tag pushed |
| C0 | docs/CANALICULI_AUDIT.md, stage by stage map | DONE | cdccb5a | 10 stages (what, names, origin, flaws F1 to F7) and a table of where each item of this branch acts |
| C1 | Attached ring length (appended columns) | DONE | e61c6c7 | ring_attached_length_r30/r60_px appended (rows, summary, xlsx, summary table); attached <= ring asserted; pooled share 0.729 at 30 px (per cell 0.367 to 0.954), 0.547 at 60 px; regression allowlist added (unexpected new fields fail) and printed; crops reviewed |
| C2 | Chain code length (appended columns) | DONE | 84103ec | ring_length_w_r30/r60_px and field_length_density_w_per_px appended; mixed adjacency so the asserted L gives 198 (Decisions needed); self-checks 99, 99 sqrt(2), 198 PASS; weighted/pixel 1.117 to 1.134 for field density, diagonal links 33 to 36%; image order unchanged |
| C3 | Sholl crossings (appended columns) | DONE | b836a2c | sholl_crossings_r10/r20/r30 appended (band [r-0.75, r+0.75) of the nearest-lacuna partition, 8-connected components); non-negative integers asserted; Spearman with roots 0.898, 0.718, 0.534 and with area 0.646, 0.655, 0.559; r30 below r10 in 3 of 86 cells; crops reviewed in two rounds |
| C4 | Field density without flagged; optional ROI option | DONE | 5b8ed0e | field_density_without_flagged_per_px (equals overnight 5.1 to rounding: -1.6 to +1.1%, 0 in the 543 images) and field_density_in_roi_per_px (None without -m); -m DIR on src/canaliculi.py, masks by clean or short name, wrong size refused; self-test through the command line with synthetic masks PASS; no ROI by default, draft not used |
| B1 | Straight band-wall filter, switch BAND_LINE_FILTER (off) | DONE | c20704f | evidence first (L 40 to 300): the 542_z06 line is straight only in pieces; touches the canal mask only at L 40, where 66 other objects touch too; length gap L 95 to 100 catches 103 of ~380 px at 65.01 px from the mask; NOT separable as intended: switch off, BAND_LINE_MIN_LEN_PX and BAND_LINE_REACH_PX None (refuses to run), no recommended value; two evidence settings run (L97/66: -103 px, 542_z06 only, density -0.29%; L40/0: -4164 px in 5 images); crops two rounds; switch-check extended |
| S1 | Subcommand network-sweep | DONE | 5a4d9ad | network-sweep -d -o -w: lacuna stage once per image (fast, cached), network stage per setting via the new canaliculi.analyse_network (pure split, regression PASS); 9 parameters low/high (+ gap 0, t_lo 0.8 to 1.2); first run had settings leaking between jobs in a worker, fixed (restore per job, checked at job start) and rerun; t_lo rows equal the overnight grid; reading: mask and cut move all, graph params move only roots and attached ring, bridging under 1.5% on headline measures, Sholl more robust than roots |
| S2 | Bridging audit | DONE | fda3eb5 | S2_bridges.csv: 143 bridges (endpoints, gap, angle, min and mean signal; 543-2 has 21 as the reference check); gap px 0.12 to 0.26% of the skeleton; without bridging: roots -1.35 to 0%, ring 30 0 to +0.36%, field density +0.11 to +0.23%, Sholl 10 unchanged; one crop sheet per image, two review rounds; bridging parameters unchanged |
| V1 | Subcommand validate-network and self-test | DONE | | -a -k -r -o, optional -t -b, -s; key outside the repo enforced; stats per lacuna, image, field; Bland-Altman PNG; trace precision, recall, F1 at 3 px; self-test 8 of 8 PASS (bias -0.023, F1 1.000, negative control 0.257, key refusal); outputs only in the cache |
| V2 | docs/NETWORK_TUNING_PROTOCOL.md | TODO | | |
| R1 | Checks and switch comments | TODO | | |
| R2 | INDEX, docs/CANALICULI_V2_REPORT.md, links, ALL DONE | TODO | | |
