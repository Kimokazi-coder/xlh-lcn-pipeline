# C2 Chain code length

Pre-validation, px. New columns `ring_length_w_r30_px`, `ring_length_w_r60_px` (per lacuna, interior means in
the summary) and `field_length_density_w_per_px` (field block and summary table). The skeleton is a pixel
graph: a link joins two neighbouring skeleton pixels, each pair once, with weight 1 for an orthogonal and
$\sqrt{2}$ for a diagonal link. A link belongs to a region if its first pixel in raster order lies in it.
A diagonal link is left out when its two pixels already share an orthogonal neighbour on the skeleton
(mixed adjacency): at a corner the path runs over that neighbour, and with every 8-neighbour pair the L
below would measure $198 + \sqrt{2}$ instead of 198. The components are the same either way. The existing
pixel-count columns stay as they are.

## Self-checks (asserted)

| skeleton | pixels | expected | measured | result |
|---|---|---|---|---|
| horizontal line, 100 px | 100 | 99.000000 | 99.000000 | PASS |
| 45 degree diagonal, 100 px | 100 | 140.007143 | 140.007143 | PASS |
| L shape, two arms of 100 px (199 px) | 199 | 198.000000 | 198.000000 | PASS |

## Per image

| image | skeleton_px | links | chain_length_px | length_over_links | length_over_px | horizontal_share_of_links | vertical_share_of_links | diagonal_share_of_links |
|---|---|---|---|---|---|---|---|---|
| 542_z06 | 34964 | 34350 | 39387.2511 | 1.1466 | 1.1265 | 0.4254 | 0.2206 | 0.3540 |
| 542_z18 | 34325 | 33706 | 38673.2490 | 1.1474 | 1.1267 | 0.4142 | 0.2300 | 0.3558 |
| 543-2 | 45785 | 45230 | 51910.4363 | 1.1477 | 1.1338 | 0.4366 | 0.2068 | 0.3566 |
| 543_3 | 46420 | 45846 | 52552.9460 | 1.1463 | 1.1321 | 0.4314 | 0.2154 | 0.3532 |
| 543_z13 | 45033 | 44492 | 50975.2707 | 1.1457 | 1.1320 | 0.4508 | 0.1974 | 0.3518 |
| 682_z08 | 35267 | 34613 | 39388.0539 | 1.1380 | 1.1169 | 0.2468 | 0.4202 | 0.3331 |
| 682_z23 | 39168 | 38495 | 44011.4962 | 1.1433 | 1.1237 | 0.2236 | 0.4305 | 0.3460 |
| 682_z29 | 38368 | 37719 | 42976.1985 | 1.1394 | 1.1201 | 0.2296 | 0.4339 | 0.3365 |


Length per link by direction is 1 for horizontal and vertical links and $\sqrt{2}$ = 1.4142 for diagonal links, by definition. Share of length by direction:

| image | horizontal_share_of_length | vertical_share_of_length | diagonal_share_of_length | diagonal_links_left_out | plain_8_link_length_px |
|---|---|---|---|---|---|
| 542_z06 | 0.3710 | 0.1923 | 0.4366 | 709 | 40389.9285 |
| 542_z18 | 0.3610 | 0.2004 | 0.4385 | 753 | 39738.1519 |
| 543-2 | 0.3804 | 0.1802 | 0.4394 | 1503 | 54035.9993 |
| 543_3 | 0.3763 | 0.1879 | 0.4357 | 1545 | 54737.9060 |
| 543_z13 | 0.3935 | 0.1723 | 0.4342 | 1404 | 52960.8265 |
| 682_z08 | 0.2169 | 0.3692 | 0.4139 | 963 | 40749.9416 |
| 682_z23 | 0.1955 | 0.3765 | 0.4279 | 1074 | 45530.3616 |
| 682_z29 | 0.2016 | 0.3808 | 0.4177 | 1031 | 44434.2527 |


Weighted against pixel-count measures (sums over interior lacunae for the rings):

| image | density_ratio_w_over_px | ring30_w_over_px | ring60_w_over_px |
|---|---|---|---|
| 542_z06 | 1.1265 | 1.1295 | 1.1285 |
| 542_z18 | 1.1267 | 1.1122 | 1.1255 |
| 543-2 | 1.1338 | 1.1188 | 1.1344 |
| 543_3 | 1.1321 | 1.1219 | 1.1311 |
| 543_z13 | 1.1320 | 1.1288 | 1.1309 |
| 682_z08 | 1.1169 | 1.1239 | 1.1242 |
| 682_z23 | 1.1237 | 1.1128 | 1.1205 |
| 682_z29 | 1.1201 | 1.1071 | 1.1118 |


## How much the pixel count underestimated

A diagonal step is $\sqrt{2}$ px long but adds one pixel, so along a diagonal thread the pixel count is
$1/\sqrt{2}$ of the length: 29.3% short. Horizontal and vertical threads are counted
right. Diagonal links are 33.3 to 35.7% of all links
(median 35.2%), so the weighted field density is 1.117 to 1.134 times the pixel-count
density, and the weighted ring 30 px 1.107 to 1.129
times the pixel count. The pixel count per link is close to 1 (pixels and links differ by the number of
components and loops), so the length per pixel above is the size of the bias. Across these 8 images the
bias is similar (11.7 to 13.4% for field density), smallest in the three 682 images,
which have the most axis-aligned links (their lattice). The ordering of the images by field density is
the same with both lengths: yes. Within an image the bias differs by thread angle (0 for axis-aligned, 29.3% for diagonal threads), so the weighted length matters most for comparing threads or
cells of different orientation.
