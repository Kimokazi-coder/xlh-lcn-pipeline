# POL section: report

**Pre-validation**, 2026-10-29. Deterministic only (no AI judge, no API). Groups WT, WT_HP,
Hyp_RD, Hyp_HP; no Hyp;Enpp1 images exist. Nothing existing changed: the regression passed
before every push.

**Built.** `src/pols.py`: `measure` reads the saved lacuna label image and vascular mask (no
detection is rerun) and writes only `results/<group>/pols/`: an overlay per field (body green,
outer boundary magenta) and, with the switch `--csv`, a per-lacuna and a per-image table.
`summary` writes `summary_by_group.csv` and [SUMMARY.md](SUMMARY.md); `selftest` passes 10 of
10 synthetic checks. `python src/diagnostics.py pol-look` remakes the phase 0 look.

**The look:** [FINDINGS.md](FINDINGS.md). **POLs cannot be told apart in these images**: no
dark ring, no separate halo, no step inside the body; around every body, in every group, one
smooth fall to the bone background, about 2.3 um wide in WT.

**So the definition is a proxy** ([DEFINITION.md](DEFINITION.md)): the body as detected, plus,
in each of 8 sectors and within the lacuna's own territory, the surround until it falls to a
tenth of its height above the bone background (at most 8 um). Unreliable if flagged: edge,
vessel, neighbour (surrounds touch), incomplete, no contrast.

**Observed** (descriptive, no test; the mean over images of the per-image mean of the measured
lacunae; SDs in SUMMARY.md):

| group | measured | body um2 | outer um2 | POL ratio | halo width um |
| - | - | - | - | - | - |
| WT | 71 of 100 | 42.1 | 139.8 | 3.99 | 2.32 |
| WT_HP | 55 of 113 | 39.1 | 153.1 | 5.07 | 2.55 |
| Hyp_RD | 86 of 251 | 50.7 | 148.3 | 4.17 | 2.00 |
| Hyp_HP | 27 of 250 | 46.3 | 214.3 | 8.70 | 3.00 |

Measured Hyp bodies are somewhat larger than WT; the surround is not wider (Hyp_RD 2.00 um,
WT 2.32). Hyp_HP's larger outer area and ratio come from the 699 and 701 fields, which FINDINGS
judged unusable and which give 0 to 3 measured lacunae each (ratio 13.1 on one lacuna, 23.9 on
two); the three 548 fields alone give outer 172.3 um2, ratio 4.26, halo 1.57 um.

**What looks wrong.**
1. The halo width is the glow: it follows the network stage's glow extent (Spearman 0.88 over
   the measured lacunae) and is 2.3 um in WT, which has no lesions.
2. The neighbour flag hits 55% of Hyp_RD and 75% of Hyp_HP lacunae (9% of WT), so the measured
   Hyp lacunae are the isolated ones. Some touching pairs look like one lacuna that the lacuna
   stage split in two (536_z08: 13/14, 21/22, 23/24, 26/27).
3. In Hyp the lacuna stage keeps saturated surfaces and soft tissue blobs as lacunae (536_z08
   #17, the 701 fields); they are flagged only where the vascular mask covers them.
4. A 45 degree sector that runs along bright matrix adds a wedge to the outer area (542_z06
   #15, 536_z08 #12, 548_z14 #11), which also makes the max halo width noisy.

**Needs your decision.**
1. Keep this proxy at all? The images cannot separate a lesion. Alternatives: imaging that sees
   mineral (backscatter SEM, qBEI), or report lacuna area and roots per cell only.
2. Do the 701 fields, and the top of the 699 fields, leave the study (FINDINGS table)?
3. Should "neighbour" stay strict (any touch) or allow a short shared border?
4. Fix the over-split Hyp lacunae upstream? That is a rule shaped on Hyp, which the standing
   rule (tune on WT only) forbids without your say.

**Three weakest points.**
1. Nothing in the image separates a lesion from glow, staining, focus or brightness, so a
   difference, or its absence, says nothing about POLs.
2. The measured Hyp lacunae are few and selected: 27 in Hyp_HP (11%), two images with none.
3. The body is the WT-shaped lacuna mask on JPEG-decoded pixels; 0.13 um/px is confirmed for
   WT only.
