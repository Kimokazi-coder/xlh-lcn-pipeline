# Cost of the AI POL judge (dry run, 2026-11-09)

Pre-validation. The POL judge was run live on one development image per group (the first in name order), on the lacunae the lacuna judge accepted, DEV mode; every number is from the token counts the API reported, at `claude-sonnet-5-5` list price. The case counts of every development image come from the offline dry run (nothing sent). Logs and run records: `results/archive/judge/dry_run_pols/`; made by `python src/diagnostics.py judge-cost --pols`.

| group | image | cases | calls | input tokens | output tokens | USD | USD per case | development images | their cases | images in group | group estimate USD |
| - | - | - | - | - | - | - | - | - | - | - | - |
| WT | 542_z06 | 2 | 2 | 5232 | 165 | 0.01211 | 0.00606 | 6 | 5 | 8 | 0.0404 |
| WT_HP | 876_z89c1-2 | 1 | 1 | 2362 | 78 | 0.0055 | 0.0055 | 7 | 8 | 9 | 0.0566 |
| Hyp_RD | 535_z13c1-2 | 3 | 4 | 9565 | 687 | 0.026 | 0.00867 | 7 | 26 | 9 | 0.2897 |
| Hyp_HP | 548_hyp_HP_z08c1-2 | 7 | 7 | 18232 | 796 | 0.04442 | 0.00635 | 7 | 25 | 9 | 0.204 |

- Spent on this dry run: **$0.0880**.
- Estimate for all 35 images (per group, the cost per case of the dry-run image times the cases of the group's development images, scaled to all its images): **$0.59**, about 82 calls; at 1.5 times, $0.89.
- Budget for the POL judge: $10. The estimate at 1.5 times is **within it**, so the full run goes ahead.
- The full run stops by itself if what it spends reaches the budget.
