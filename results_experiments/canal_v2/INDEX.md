# Index of results_experiments/canal_v2

Pre-validation, pixel units. Outputs of branch canaliculi-v2, one line each. Report:
`docs/CANALICULI_V2_REPORT.md`; stage map: `docs/CANALICULI_AUDIT.md`; scripts: `experiments/canal_*.py`.
Caches (pipeline runs, the sweep runs, the self-test) are in `results_experiments/_cache/` and not committed.

| file | what it holds |
|---|---|
| `C1_attached_ring.md`, `.csv` | attached ring length per lacuna and per image, the share of ring length that is attached |
| `C1_crops.png` | 3 cells: attached ring pixels vermillion, passing ring pixels sky blue |
| `C2_chain_length.md`, `.csv` | chain code length against the pixel count per image, by link direction, the self-checks |
| `C3_sholl.md`, `.csv` | Sholl crossings at 10, 20, 30 px per lacuna, correlations with roots and area |
| `C3_crops.png` | 2 cells with the three bands and the skeleton pixels in them |
| `C4_density.md`, `.csv` | field density without the flagged canal regions; the self-test of the `-m` ROI option |
| `B1_straight_runs.md`, `.csv` | evidence: every straight skeleton object at line lengths 40 to 300 px, and the decision |
| `B1_filter.md` | what the band-wall filter removes at the two evidence settings, per image |
| `B1_filter_components.csv`, `B1_filter_images.csv` | every removed or added skeleton component; headline values per image |
| `B1_crops_L97_reach66_1.png` | before and after of the one component removed at L 97 px, reach 66 px |
| `B1_crops_L40_reach0_1.png` to `_5.png` | before and after of every component removed at L 40 px, reach 0 px |
| `B1_switch_check.md` | `switch-check` output with the band-wall filter at the two evidence settings |
| `S1_network_sweep.md`, `.csv` | one network parameter at a time: percent changes of every measure, ranking, reading |
| `S2_bridging.md` | bridges per image, the share of each measure that depends on bridging |
| `S2_bridges.csv` | every bridge: endpoints, gap, angle, minimum and mean signal |
| `S2_bridges_<image>.png` | one tile per bridge, bridge pixels sky blue on the skeleton |
| `V1_validate_network.md` | how to run `validate-network` and the self-test result |
| `R1_checks.md` | reference-check, regression, fast-check, switch-check and the self-test, as run at the end |
| `REVIEW.md` | visual review of every PNG here, by round |
