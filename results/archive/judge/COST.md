# Cost of the AI judge rerun (dry run, 2026-11-09)

Pre-validation. Both judges were run live on one development image per group (the first
in name order), the canaliculi judge on the lacunae the lacuna judge accepted, DEV mode.
Every number below is from the token counts the API reported, priced at the pinned
model's list price (`claude-sonnet-5-5`, $2.00 input and $10.00 output per million tokens). Logs and run records:
`results/archive/judge/dry_run/`; made by `python src/diagnostics.py judge-cost`.

| group | image | lacuna judge: calls, tokens in / out, USD | canaliculi judge: calls, tokens in / out, USD | USD for the image | images in group | group estimate USD |
| - | - | - | - | - | - | - |
| WT | 542_z06 | 1, 5,245 / 2,108, $0.0316 | 19, 70,397 / 5,616, $0.1969 | $0.2285 | 8 | $1.83 |
| WT_HP | 872_wt_hp_z03 | 1, 5,246 / 827, $0.0188 | 11, 45,620 / 8,042, $0.1717 | $0.1904 | 9 | $1.71 |
| Hyp_RD | 535_z13c1-2 | 1, 5,245 / 2,218, $0.0327 | 15, 59,704 / 8,195, $0.2014 | $0.2340 | 9 | $2.11 |
| Hyp_HP | 548_hyp_HP_z08c1-2 | 1, 5,243 / 2,207, $0.0326 | 20, 75,646 / 7,292, $0.2242 | $0.2568 | 9 | $2.31 |

- Spent on this dry run: **$0.9097**.
- Estimate for all 35 images (per group, the dry-run image's cost times the group's images): **$7.96**, about 601 calls; at 1.5 times, $11.94.
- Budget (BUDGET_USD of the brief): $50. The estimate at 1.5 times is **within it**, so the full run goes ahead.
- Time: the canaliculi judge's calls ran one after another, about 0.6 h for all 35 images at the dry run's pace, plus the lacuna and network stages of each image.
- One image per group stands for eight or nine, so this is an estimate. The full run stops by itself if the running total reaches the budget.
