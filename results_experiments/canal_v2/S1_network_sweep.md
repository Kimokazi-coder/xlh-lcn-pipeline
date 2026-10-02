# Network sweep

PRE-VALIDATION, pixel units. One parameter of the network stage at a time, everything else at its default, on 8 images; the lacuna stage ran once per image (fast stage) and is reused. Percent change against each image's default run: median over the images, range in brackets. No value is recommended and no default changed.

Defaults: `TOPHAT_RADIUS_PX` = 5, `HYSTERESIS_LOW_FRACTION` = 0.75, `MAX_BRIDGE_GAP_PX` = 10.0, `MAX_BRIDGE_ANGLE_DEG` = 40.0, `MIN_BRIDGE_SIGNAL_FRACTION` = 0.7, `PRUNE_SPUR_LEN_PX` = 4, `ROOT_MERGE_DIST_PX` = 8.0, `LACUNA_ATTACH_GAP_PX` = 10; t_lo is each image's own lower Otsu cut. MAX_BRIDGE_GAP_PX = 0 means no bridging.

| setting | roots per cell | ring 30 px | ring attached 30 px | ring weighted 30 px | Sholl 10 px | Sholl 20 px | Sholl 30 px | field density | bridges |
|---|---|---|---|---|---|---|---|---|---|
| TOPHAT_RADIUS_PX = 4 | -6.7 [-15.4, +4.5] | -5.1 [-8.3, -4.1] | -10.3 [-15.4, -6.9] | -5.6 [-9.0, -4.0] | -4.9 [-7.3, +2.3] | -3.0 [-6.7, -1.4] | -2.2 [-5.6, +3.4] | -4.7 [-6.7, -3.0] | -4.5 [-41.2, +107.1] |
| TOPHAT_RADIUS_PX = 6 | +1.6 [-6.6, +8.8] | +2.3 [+0.8, +3.2] | +4.7 [-2.6, +7.5] | +2.4 [+0.7, +3.6] | -1.7 [-5.8, +8.7] | +0.0 [-2.3, +1.2] | +1.5 [-4.0, +6.4] | +1.9 [+1.3, +2.4] | -13.8 [-29.2, +36.8] |
| HYSTERESIS_LOW_FRACTION = 0.525 | +7.9 [+4.8, +17.6] | +13.4 [+7.7, +15.1] | +16.8 [+7.6, +30.1] | +13.7 [+8.0, +15.6] | +11.1 [+8.1, +15.9] | +8.6 [+3.7, +12.6] | +9.3 [+4.9, +12.1] | +13.0 [+9.4, +15.5] | -100.0 [-100.0, -94.1] |
| HYSTERESIS_LOW_FRACTION = 0.975 | -9.5 [-14.3, -2.5] | -9.4 [-14.0, -6.8] | -13.1 [-20.9, -6.1] | -9.9 [-14.0, -6.9] | -12.1 [-17.4, -2.3] | -7.8 [-12.6, -2.6] | -7.6 [-10.2, -0.8] | -9.2 [-10.3, -7.4] | +562.8 [+341.2, +728.6] |
| MAX_BRIDGE_GAP_PX = 0 | +0.0 [+0.0, +1.4] | -0.0 [-0.4, +0.0] | +0.0 [-0.9, +0.0] | -0.1 [-0.4, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [-1.0, +0.0] | +0.0 [-0.6, +0.0] | -0.2 [-0.2, -0.1] | -100.0 [-100.0, -100.0] |
| MAX_BRIDGE_GAP_PX = 7 | +0.0 [+0.0, +0.9] | +0.0 [-0.3, +0.0] | +0.0 [-0.7, +0.0] | +0.0 [-0.3, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [-1.0, +0.0] | +0.0 [+0.0, +0.0] | -0.0 [-0.1, +0.0] | -15.1 [-29.4, +0.0] |
| MAX_BRIDGE_GAP_PX = 13 | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] |
| MAX_BRIDGE_ANGLE_DEG = 28 | +0.0 [+0.0, +1.4] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [-0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | -0.0 [-0.0, +0.0] | -9.4 [-23.8, -5.3] |
| MAX_BRIDGE_ANGLE_DEG = 52 | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.1] | +0.0 [+0.0, +0.6] | +0.0 [+0.0, +0.2] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +8.3 [+0.0, +14.3] |
| MIN_BRIDGE_SIGNAL_FRACTION = 0.49 | +0.0 [-1.4, +1.4] | +0.8 [+0.5, +1.5] | +2.1 [+0.4, +4.2] | +1.0 [+0.5, +1.6] | +0.9 [+0.0, +2.9] | +0.6 [+0.0, +1.6] | +1.3 [+0.0, +3.2] | +1.0 [+0.8, +1.7] | +519.0 [+370.6, +785.7] |
| MIN_BRIDGE_SIGNAL_FRACTION = 0.91 | +0.0 [+0.0, +1.4] | -0.0 [-0.4, +0.0] | +0.0 [-0.9, +0.0] | -0.1 [-0.4, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [-1.0, +0.0] | +0.0 [-0.6, +0.0] | -0.2 [-0.2, -0.1] | -100.0 [-100.0, -94.1] |
| PRUNE_SPUR_LEN_PX = 3 | +0.0 [+0.0, +3.3] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] |
| PRUNE_SPUR_LEN_PX = 5 | -3.0 [-5.4, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] |
| ROOT_MERGE_DIST_PX = 6 | +5.4 [+4.1, +16.2] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] |
| ROOT_MERGE_DIST_PX = 10 | -8.5 [-13.2, -1.1] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] |
| LACUNA_ATTACH_GAP_PX = 7 | -14.9 [-32.3, -5.0] | +0.0 [+0.0, +0.0] | -10.6 [-19.1, -2.4] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] |
| LACUNA_ATTACH_GAP_PX = 13 | +15.3 [+10.7, +25.7] | +0.0 [+0.0, +0.0] | +8.4 [+4.5, +15.1] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] | +0.0 [+0.0, +0.0] |
| t_lo scale = 0.8 | +6.2 [+2.7, +12.1] | +10.7 [+6.1, +12.2] | +11.4 [+4.6, +19.5] | +10.6 [+6.1, +12.0] | +7.5 [+4.7, +13.6] | +7.0 [+1.7, +9.6] | +8.7 [+4.9, +14.0] | +11.1 [+7.5, +12.0] | -29.2 [-52.9, +21.4] |
| t_lo scale = 0.9 | +1.9 [+0.0, +9.5] | +4.4 [+2.4, +6.3] | +4.5 [+2.8, +10.1] | +4.2 [+2.4, +6.4] | +4.2 [+1.4, +5.8] | +2.6 [-0.8, +6.7] | +4.0 [+2.3, +6.7] | +5.1 [+3.5, +5.7] | -6.5 [-20.8, +42.1] |
| t_lo scale = 1.1 | -4.3 [-6.8, -1.6] | -4.3 [-5.3, -3.4] | -5.7 [-7.9, -2.6] | -4.4 [-5.4, -3.5] | -4.5 [-9.7, +1.2] | -2.8 [-6.7, -0.9] | -2.6 [-4.2, +0.0] | -4.4 [-4.8, -3.6] | +0.3 [-78.6, +85.7] |
| t_lo scale = 1.2 | -7.4 [-13.2, -3.8] | -7.6 [-11.3, -5.3] | -9.7 [-14.9, -5.2] | -8.1 [-11.4, -5.8] | -9.7 [-13.5, -5.8] | -6.5 [-10.6, -0.9] | -5.9 [-9.1, -0.8] | -8.2 [-9.5, -6.5] | +24.8 [-29.4, +42.9] |

## Ranked by effect on each measure

For each parameter, the larger absolute median change of its settings, largest first.

- **roots per cell**: LACUNA_ATTACH_GAP_PX 15.3%, HYSTERESIS_LOW_FRACTION 9.5%, ROOT_MERGE_DIST_PX 8.5%, t_lo scale 7.4%, TOPHAT_RADIUS_PX 6.7%, PRUNE_SPUR_LEN_PX 3.0%, MAX_BRIDGE_GAP_PX 0.0%, MAX_BRIDGE_ANGLE_DEG 0.0%, MIN_BRIDGE_SIGNAL_FRACTION 0.0%
- **ring 30 px**: HYSTERESIS_LOW_FRACTION 13.4%, t_lo scale 10.7%, TOPHAT_RADIUS_PX 5.1%, MIN_BRIDGE_SIGNAL_FRACTION 0.8%, MAX_BRIDGE_GAP_PX 0.0%, MAX_BRIDGE_ANGLE_DEG 0.0%, PRUNE_SPUR_LEN_PX 0.0%, ROOT_MERGE_DIST_PX 0.0%, LACUNA_ATTACH_GAP_PX 0.0%
- **ring attached 30 px**: HYSTERESIS_LOW_FRACTION 16.8%, t_lo scale 11.4%, LACUNA_ATTACH_GAP_PX 10.6%, TOPHAT_RADIUS_PX 10.3%, MIN_BRIDGE_SIGNAL_FRACTION 2.1%, MAX_BRIDGE_GAP_PX 0.0%, MAX_BRIDGE_ANGLE_DEG 0.0%, PRUNE_SPUR_LEN_PX 0.0%, ROOT_MERGE_DIST_PX 0.0%
- **ring weighted 30 px**: HYSTERESIS_LOW_FRACTION 13.7%, t_lo scale 10.6%, TOPHAT_RADIUS_PX 5.6%, MIN_BRIDGE_SIGNAL_FRACTION 1.0%, MAX_BRIDGE_GAP_PX 0.1%, MAX_BRIDGE_ANGLE_DEG 0.0%, PRUNE_SPUR_LEN_PX 0.0%, ROOT_MERGE_DIST_PX 0.0%, LACUNA_ATTACH_GAP_PX 0.0%
- **Sholl 10 px**: HYSTERESIS_LOW_FRACTION 12.1%, t_lo scale 9.7%, TOPHAT_RADIUS_PX 4.9%, MIN_BRIDGE_SIGNAL_FRACTION 0.9%, MAX_BRIDGE_GAP_PX 0.0%, MAX_BRIDGE_ANGLE_DEG 0.0%, PRUNE_SPUR_LEN_PX 0.0%, ROOT_MERGE_DIST_PX 0.0%, LACUNA_ATTACH_GAP_PX 0.0%
- **Sholl 20 px**: HYSTERESIS_LOW_FRACTION 8.6%, t_lo scale 7.0%, TOPHAT_RADIUS_PX 3.0%, MIN_BRIDGE_SIGNAL_FRACTION 0.6%, MAX_BRIDGE_GAP_PX 0.0%, MAX_BRIDGE_ANGLE_DEG 0.0%, PRUNE_SPUR_LEN_PX 0.0%, ROOT_MERGE_DIST_PX 0.0%, LACUNA_ATTACH_GAP_PX 0.0%
- **Sholl 30 px**: HYSTERESIS_LOW_FRACTION 9.3%, t_lo scale 8.7%, TOPHAT_RADIUS_PX 2.2%, MIN_BRIDGE_SIGNAL_FRACTION 1.3%, MAX_BRIDGE_GAP_PX 0.0%, MAX_BRIDGE_ANGLE_DEG 0.0%, PRUNE_SPUR_LEN_PX 0.0%, ROOT_MERGE_DIST_PX 0.0%, LACUNA_ATTACH_GAP_PX 0.0%
- **field density**: HYSTERESIS_LOW_FRACTION 13.0%, t_lo scale 11.1%, TOPHAT_RADIUS_PX 4.7%, MIN_BRIDGE_SIGNAL_FRACTION 1.0%, MAX_BRIDGE_GAP_PX 0.2%, MAX_BRIDGE_ANGLE_DEG 0.0%, PRUNE_SPUR_LEN_PX 0.0%, ROOT_MERGE_DIST_PX 0.0%, LACUNA_ATTACH_GAP_PX 0.0%
- **bridges**: HYSTERESIS_LOW_FRACTION 562.8%, MIN_BRIDGE_SIGNAL_FRACTION 519.0%, MAX_BRIDGE_GAP_PX 100.0%, t_lo scale 29.2%, TOPHAT_RADIUS_PX 13.8%, MAX_BRIDGE_ANGLE_DEG 9.4%, PRUNE_SPUR_LEN_PX 0.0%, ROOT_MERGE_DIST_PX 0.0%, LACUNA_ATTACH_GAP_PX 0.0%

Mean over the parameters of the largest median change (a rough robustness index, lower is more robust): roots per cell 5.6%, ring 30 px 3.3%, ring attached 30 px 5.7%, ring weighted 30 px 3.4%, Sholl 10 px 3.1%, Sholl 20 px 2.1%, Sholl 30 px 2.4%, field density 3.3%, bridges 137.1%.

## Reading

Largest median change per measure within three groups of parameters (graph and attach: the spur
length, the root merge distance and the attach gap; mask and cut: the top-hat radius, the hysteresis
low fraction and the t_lo scale; bridging: gap, angle and minimum signal):

| measure | graph and attach (largest median %) | at | mask and cut (largest median %) | at  | bridging (largest median %) | at   |
|---|---|---|---|---|---|---|
| roots per cell | +15.3 | LACUNA_ATTACH_GAP_PX = 13 | -9.5 | HYSTERESIS_LOW_FRACTION = 0.975 | +0.0 |  |
| ring 30 px | +0.0 |  | +13.4 | HYSTERESIS_LOW_FRACTION = 0.525 | +0.8 | MIN_BRIDGE_SIGNAL_FRACTION = 0.49 |
| ring attached 30 px | -10.6 | LACUNA_ATTACH_GAP_PX = 7 | +16.8 | HYSTERESIS_LOW_FRACTION = 0.525 | +2.1 | MIN_BRIDGE_SIGNAL_FRACTION = 0.49 |
| ring weighted 30 px | +0.0 |  | +13.7 | HYSTERESIS_LOW_FRACTION = 0.525 | +1.0 | MIN_BRIDGE_SIGNAL_FRACTION = 0.49 |
| Sholl 10 px | +0.0 |  | -12.1 | HYSTERESIS_LOW_FRACTION = 0.975 | +0.9 | MIN_BRIDGE_SIGNAL_FRACTION = 0.49 |
| Sholl 20 px | +0.0 |  | +8.6 | HYSTERESIS_LOW_FRACTION = 0.525 | +0.6 | MIN_BRIDGE_SIGNAL_FRACTION = 0.49 |
| Sholl 30 px | +0.0 |  | +9.3 | HYSTERESIS_LOW_FRACTION = 0.525 | +1.3 | MIN_BRIDGE_SIGNAL_FRACTION = 0.49 |
| field density | +0.0 |  | +13.0 | HYSTERESIS_LOW_FRACTION = 0.525 | +1.0 | MIN_BRIDGE_SIGNAL_FRACTION = 0.49 |


- **The mask and the cut move everything.** The hysteresis low fraction and the t_lo scale move every
  length, density and count measure by about 7 to 17% at the low and high settings, and the top-hat
  radius by up to about 10%. These are the parameters that decide what the skeleton is.
- **Graph and attach parameters move only the roots and the attached ring.** Roots per cell move by up
  to 15.3% (LACUNA_ATTACH_GAP_PX = 13); ring 30 px, ring weighted, field density and the Sholl
  crossings do not move at all (largest 0.0% for the Sholl crossings), because they do not use
  the graph. The attached ring uses the attach gap by definition and moves with it.
- **Bridging matters little for the headline measures.** With no bridging (MAX_BRIDGE_GAP_PX = 0) the
  bridges go to 0, but roots per cell move by +0.0 to +1.4%,
  ring 30 px by -0.4 to +0.0% and field density by -0.2 to -0.1% over the 8 images. The bridge count itself
  is the least stable output (median +519 to +563%, six to seven times as many, at a hysteresis fraction
  of 0.975 or a minimum signal of 0.49).
- **Sholl crossings against roots.** Both respond to the mask and the cut by similar amounts (largest
  median for roots -9.5% at HYSTERESIS_LOW_FRACTION = 0.975, for Sholl 10 px -12.1% at HYSTERESIS_LOW_FRACTION = 0.975).
  The Sholl crossings are untouched by the three graph and attach parameters, while roots move by up to
  15.3% with them. So the Sholl crossings are more robust to the network parameters than
  roots, which carry the extra choices of the attach gap and the merge distance. Of all measures, the
  Sholl crossings at 20 and 30 px move least overall; the bridge count moves most, then the attached
  ring and the roots.
- No value is recommended and no default changed. Which setting is right can only be decided against
  hand counts or traced threads (docs/NETWORK_TUNING_PROTOCOL.md).
