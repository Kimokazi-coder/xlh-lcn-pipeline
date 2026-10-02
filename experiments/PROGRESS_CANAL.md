# Canaliculi v2 progress

base SHA: 867338079ce8a9c97cd69c1551ca42e68fb1bebb (origin/publication-fixes tip; tag before-canaliculi-v2)
last update: 2026-10-02 23:30
next action: C3 Sholl crossings

Status values: TODO, DONE, PARTIAL, FAILED, SKIPPED. The commit SHA is the commit that holds the
item's code and outputs. UNPUSHED after an id means its push failed and is retried at the next commit.

| id | description | status | commit SHA | note |
|---|---|---|---|---|
| 0.1 | Branch canaliculi-v2, tag before-canaliculi-v2, this file | DONE | 3d8cc0b | branch from origin/publication-fixes 8673380; tag pushed |
| C0 | docs/CANALICULI_AUDIT.md, stage by stage map | DONE | cdccb5a | 10 stages (what, names, origin, flaws F1 to F7) and a table of where each item of this branch acts |
| C1 | Attached ring length (appended columns) | DONE | e61c6c7 | ring_attached_length_r30/r60_px appended (rows, summary, xlsx, summary table); attached <= ring asserted; pooled share 0.729 at 30 px (per cell 0.367 to 0.954), 0.547 at 60 px; regression allowlist added (unexpected new fields fail) and printed; crops reviewed |
| C2 | Chain code length (appended columns) | DONE | | ring_length_w_r30/r60_px and field_length_density_w_per_px appended; mixed adjacency so the asserted L gives 198 (Decisions needed); self-checks 99, 99 sqrt(2), 198 PASS; weighted/pixel 1.117 to 1.134 for field density, diagonal links 33 to 36%; image order unchanged |
| C3 | Sholl crossings (appended columns) | TODO | | |
| C4 | Field density without flagged; optional ROI option | TODO | | |
| B1 | Straight band-wall filter, switch BAND_LINE_FILTER (off) | TODO | | |
| S1 | Subcommand network-sweep | TODO | | |
| S2 | Bridging audit | TODO | | |
| V1 | Subcommand validate-network and self-test | TODO | | |
| V2 | docs/NETWORK_TUNING_PROTOCOL.md | TODO | | |
| R1 | Checks and switch comments | TODO | | |
| R2 | INDEX, docs/CANALICULI_V2_REPORT.md, links, ALL DONE | TODO | | |
