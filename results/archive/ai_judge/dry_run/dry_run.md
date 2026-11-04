# AI lacuna judge: dry run

**EXPERIMENT, pre-validation. Nothing was sent.** What a real run of the AI lacuna judge would send and cost, made by `python src/diagnostics.py ai-lacuna-judge` (the dry run is the default). Not validated: nothing here says any verdict would be right.

- Model `claude-sonnet-5-5`, $2.00 / $10.00 per million input / output tokens.
- Candidates: every region of the lacuna stage's label image of at least 100 px2, kept and rejected, plus the dim candidates at 0.8 of each image's lacuna cut that overlap none of them; at most 60 numbered per image. With more, the cap drops from the end of this order, each tier largest first: every region the filters kept, every region they rejected of at least 300 px2, the dim candidates, the rejected regions under that area. The numbers run in reading order whatever the tier.
- One call per image: 35 calls, 1882 numbered regions.
- Estimate: 133,455 input and 66,570 output tokens, **$0.9326**; $1.8652 if every call had to be retried once; $1.2539 if it runs over as the thread judge's estimate did. Ceiling `config.AI_LACUNA_MAX_COST_USD` = $3.0.
- Images with more candidates than the cap: 23; kept lacunae left unnumbered by the cap, which keep the deterministic decision: 0; images with more kept lacunae than the cap: 0.
- How the estimate is made: input text at 0.25 tokens per character and the picture at width x height / 750.0 px per token; the answer at 35 tokens per number plus 20. Estimates, not measurements. The thread judge's real run cost 1.34 times its estimate, so read this as a floor.
- Prompt sha256 `5a639cf96a54670e`, examples sha256 `46ec9b817506a78e`.

The picture of every image, byte for byte what a run would send, is in `<group>/<image>.png` beside this file. The judge sees no file name: the request carries only the neutral image code in the table.

| group | image | image_code | lacunae (deterministic) | candidates found | numbered | numbered, kept by the filters | numbered, regions rejected by the filters | numbered, dim candidates (0.8 of the cut) | over the cap, not numbered | of those, kept lacunae | of those, rejected regions | of those, dim candidates | numbers not placed clear | estimated input tokens | estimated output tokens | estimated cost USD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WT | 542_z06 | img_9335ebdc | 19 | 87 | 60 | 19 | 3 | 38 | 27 | 0 | 13 | 14 | 0 | 3813 | 2120 | 0.0288 |
| WT | 542_z18 | img_ef5ccdb6 | 13 | 68 | 60 | 13 | 2 | 45 | 8 | 0 | 8 | 0 | 0 | 3813 | 2120 | 0.0288 |
| WT | 543-2 | img_ad1a1a86 | 12 | 27 | 27 | 12 | 2 | 13 | 0 | 0 | 0 | 0 | 0 | 3813 | 965 | 0.0173 |
| WT | 543_3 | img_1a4e2621 | 13 | 37 | 37 | 13 | 1 | 23 | 0 | 0 | 0 | 0 | 0 | 3813 | 1315 | 0.0208 |
| WT | 543_z13 | img_8aba8947 | 11 | 27 | 27 | 11 | 1 | 15 | 0 | 0 | 0 | 0 | 0 | 3813 | 965 | 0.0173 |
| WT | 682_z08 | img_7174a32e | 11 | 47 | 47 | 11 | 13 | 23 | 0 | 0 | 0 | 0 | 0 | 3813 | 1665 | 0.0243 |
| WT | 682_z23 | img_0b12aba2 | 14 | 58 | 58 | 14 | 9 | 35 | 0 | 0 | 0 | 0 | 2 | 3813 | 2050 | 0.0281 |
| WT | 682_z29 | img_b6ed8081 | 15 | 69 | 60 | 15 | 1 | 44 | 9 | 0 | 9 | 0 | 0 | 3813 | 2120 | 0.0288 |
| WT_HP | 872_wt_hp_z03 | img_d0dcd70a | 14 | 25 | 25 | 14 | 7 | 4 | 0 | 0 | 0 | 0 | 0 | 3813 | 895 | 0.0166 |
| WT_HP | 872_wt_hp_z04 | img_1927df57 | 21 | 76 | 60 | 21 | 4 | 35 | 16 | 0 | 14 | 2 | 5 | 3813 | 2120 | 0.0288 |
| WT_HP | 872_wt_hp_z06 | img_96e5a40f | 15 | 35 | 35 | 15 | 13 | 7 | 0 | 0 | 0 | 0 | 0 | 3813 | 1245 | 0.0201 |
| WT_HP | 876_z76c1-2 | img_b1a8effc | 8 | 72 | 60 | 8 | 0 | 52 | 12 | 0 | 4 | 8 | 5 | 3813 | 2120 | 0.0288 |
| WT_HP | 876_z82c1-2 | img_2183dbdf | 10 | 75 | 60 | 10 | 0 | 50 | 15 | 0 | 5 | 10 | 1 | 3813 | 2120 | 0.0288 |
| WT_HP | 876_z89c1-2 | img_73c55f34 | 14 | 119 | 60 | 14 | 2 | 44 | 59 | 0 | 24 | 35 | 0 | 3813 | 2120 | 0.0288 |
| WT_HP | 877_wt_z073c1-2 | img_ca3e4b7d | 14 | 66 | 60 | 14 | 2 | 44 | 6 | 0 | 6 | 0 | 1 | 3813 | 2120 | 0.0288 |
| WT_HP | 877_wt_z081c1-2 | img_d5472ff8 | 14 | 50 | 50 | 14 | 3 | 33 | 0 | 0 | 0 | 0 | 2 | 3813 | 1770 | 0.0253 |
| WT_HP | 877_wt_z087c1-2 | img_8ed25fa4 | 11 | 45 | 45 | 11 | 7 | 27 | 0 | 0 | 0 | 0 | 0 | 3813 | 1595 | 0.0236 |
| Hyp_RD | 535_z13c1-2 | img_7f6141d8 | 32 | 81 | 60 | 32 | 2 | 26 | 21 | 0 | 10 | 11 | 0 | 3813 | 2120 | 0.0288 |
| Hyp_RD | 535_z20c1-2 | img_040277b8 | 30 | 85 | 60 | 30 | 1 | 29 | 25 | 0 | 10 | 15 | 0 | 3813 | 2120 | 0.0288 |
| Hyp_RD | 535_z27c1-2 | img_5b6863f6 | 31 | 102 | 60 | 31 | 3 | 26 | 42 | 0 | 12 | 30 | 0 | 3813 | 2120 | 0.0288 |
| Hyp_RD | 536-63x_Hyp_RD_z03c1-2 | img_3e061e35 | 24 | 57 | 57 | 24 | 14 | 19 | 0 | 0 | 0 | 0 | 2 | 3813 | 2015 | 0.0278 |
| Hyp_RD | 536-63x_Hyp_RD_z08c1-2 | img_03ae62fe | 29 | 63 | 60 | 29 | 10 | 21 | 3 | 0 | 3 | 0 | 0 | 3813 | 2120 | 0.0288 |
| Hyp_RD | 536-63x_Hyp_RD_z15c1-2 | img_e88aa2e9 | 15 | 49 | 49 | 15 | 6 | 28 | 0 | 0 | 0 | 0 | 1 | 3813 | 1735 | 0.025 |
| Hyp_RD | I534_z11c1-2 | img_981d8b06 | 42 | 163 | 60 | 42 | 7 | 11 | 103 | 0 | 51 | 52 | 0 | 3813 | 2120 | 0.0288 |
| Hyp_RD | I534_z19c1-2 | img_c9307eb7 | 37 | 133 | 60 | 37 | 5 | 18 | 73 | 0 | 35 | 38 | 0 | 3813 | 2120 | 0.0288 |
| Hyp_RD | I534_z25c1-2 | img_898a7c63 | 37 | 115 | 60 | 37 | 6 | 17 | 55 | 0 | 33 | 22 | 0 | 3813 | 2120 | 0.0288 |
| Hyp_HP | 548_hyp_HP_z08c1-2 | img_7e105582 | 29 | 83 | 60 | 29 | 9 | 22 | 23 | 0 | 23 | 0 | 0 | 3813 | 2120 | 0.0288 |
| Hyp_HP | 548_hyp_HP_z14c1-2 | img_4ba7fa39 | 29 | 81 | 60 | 29 | 3 | 28 | 21 | 0 | 21 | 0 | 0 | 3813 | 2120 | 0.0288 |
| Hyp_HP | 548_hyp_HP_z20c1-2 | img_27daf452 | 32 | 79 | 60 | 32 | 1 | 27 | 19 | 0 | 11 | 8 | 0 | 3813 | 2120 | 0.0288 |
| Hyp_HP | 699_HYP_HP_z11c1-2 | img_f3a94933 | 30 | 71 | 60 | 30 | 13 | 17 | 11 | 0 | 11 | 0 | 0 | 3813 | 2120 | 0.0288 |
| Hyp_HP | 699_HYP_HP_z20c1-2 | img_13106fa0 | 25 | 62 | 60 | 25 | 17 | 18 | 2 | 0 | 2 | 0 | 0 | 3813 | 2120 | 0.0288 |
| Hyp_HP | 699_HYP_HP_z25c1-2 | img_bb63db29 | 17 | 45 | 45 | 17 | 13 | 15 | 0 | 0 | 0 | 0 | 1 | 3813 | 1595 | 0.0236 |
| Hyp_HP | 701_z19c1-2 | img_c8338be9 | 50 | 97 | 60 | 50 | 5 | 5 | 37 | 0 | 16 | 21 | 0 | 3813 | 2120 | 0.0288 |
| Hyp_HP | 701_z26c1-2 | img_a4c37628 | 45 | 89 | 60 | 45 | 4 | 11 | 29 | 0 | 8 | 21 | 0 | 3813 | 2120 | 0.0288 |
| Hyp_HP | 701_z36c1-2 | img_284346ef | 30 | 73 | 60 | 30 | 7 | 23 | 13 | 0 | 11 | 2 | 0 | 3813 | 2120 | 0.0288 |
