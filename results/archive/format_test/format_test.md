# Format test: TIFF against JPEG on the WT images

**Pre-validation, pixel units. Measurement only: nothing here decides anything, and no default changed.** Made by `python src/diagnostics.py format-test --twins-src FOLDER` (steps twins, synthetic, run, report). The images and the three runs are in `.cache/format_test/`, not tracked; the tables are here, in `results/format_test/`. A difference is always JPEG minus TIFF.

## What the WT TIFFs are

The four real JPEG twins are the same fields as their WT TIFFs: the same shape, and the cross correlation of the red channels peaks at a shift of 0,0 px for 4 of 4. For 3 of them (542_z18, 543_z13, 682_z08) the decoded JPEG equals the TIFF pixel for pixel.

| image | red mean absolute difference (0-255) | red correlation at shift 0 | best shift | same field |
|---|---|---|---|---|
| 542_z06 | 0.0462 | 0.999988 | 0,0 | True |
| 542_z18 | 0.0 | 1.0 | 0,0 | True |
| 543_z13 | 0.0 | 1.0 | 0,0 | True |
| 682_z08 | 0.0 | 1.0 | 0,0 | True |

Two fingerprints of a JPEG compression on all 8 WT TIFFs: green that is not zero although the sections are red and blue, and steps in the red channel that are larger across the edges of the 8 px blocks a JPEG codes in than inside them (a ratio of 1 means no block structure; the null moves the grid by 4 px, where no edge was coded).

| image | green > 0 share | green max | red block-edge step ratio (x, y) | red null, grid moved 4 px (x, y) |
|---|---|---|---|---|
| 542_z06 | 0.3855 | 16 | 1.106, 1.084 | 1.013, 1.036 |
| 542_z18 | 0.3871 | 18 | 1.114, 1.094 | 1.015, 1.026 |
| 543-2 | 0.4161 | 15 | 1.095, 1.071 | 0.999, 1.021 |
| 543_3 | 0.4136 | 13 | 1.103, 1.070 | 0.999, 1.025 |
| 543_z13 | 0.4185 | 14 | 1.086, 1.052 | 1.003, 1.018 |
| 682_z08 | 0.3932 | 13 | 1.117, 1.121 | 1.018, 1.016 |
| 682_z23 | 0.38 | 14 | 1.125, 1.132 | 1.021, 1.012 |
| 682_z29 | 0.3768 | 13 | 1.140, 1.142 | 1.033, 1.017 |

Both fingerprints are on 8 of 8 WT TIFFs, and 3 TIFF(s) equal a decoded JPEG pixel for pixel. So the WT TIFFs hold decoded JPEG pixels. There is no uncompressed original of any WT field here, and this test therefore cannot measure what a FIRST JPEG compression does. What it measures is what a SECOND compression at the same tables does (the synthetic set) and what a different decode of the same JPEG does (the real set).

## The synthetic twins

Each WT TIFF saved as JPEG with Pillow at 4:2:0 and quality 95, the quality whose quantization tables equal the real JPEGs' (luma table first coefficient 2); tables equal on 8 of 8. Red channel against the TIFF: mean absolute difference 0.90 to 1.44 grey levels, best shift 0,0 on every image.

## The TIFF run

The WT TIFFs run again into `.cache/format_test/tiff/` equal `results/WT/` in every cell of the cross-image table: True.

## Each measure, pooled

Mean difference keeps its sign; the largest is the largest absolute difference of one pair. The SD is the sample SD of the measure over the 8 WT TIFF images, the spread between images that the format effect is read against.

### Synthetic twins, 8 pairs

| measure | pairs | mean difference | largest absolute difference | higher / lower / equal | SD over the 8 WT images | mean difference / SD |
|---|---|---|---|---|---|---|
| lacuna count | 8 | 0 | 1 | 1 / 1 / 6 | 2.61861 | +0.000 |
| roots per interior cell | 8 | -0.067125 | 1.9458 | 5 / 3 / 0 | 2.70609 | -0.025 |
| ring length 30 px per cell (px) | 8 | -1.36527 | 34.4083 | 3 / 5 / 0 | 67.8385 | -0.020 |
| field length density (px^-1) | 8 | -1.20625e-05 | 0.00119656 | 4 / 4 / 0 | 0.0024852 | -0.005 |
| skeleton px | 8 | -18.875 | 1206 | 4 / 4 / 0 | 2671.56 | -0.007 |
| unowned px | 8 | -73.125 | 1262 | 2 / 5 / 1 | 1626.54 | -0.045 |
| canalicular width median (px) | 8 | 0.030775 | 0.2462 | 1 / 0 / 7 | 0.113968 | +0.270 |
| loops per cell | 8 | -0.0648 | 2.1111 | 3 / 5 / 0 | 3.90876 | -0.017 |

Lacunae matched by centroid within 25 px (mutual nearest neighbours): 107 of 108.

| image | lacunae matched | lacuna count, difference | roots per interior cell, difference | ring length 30 px per cell (px), difference | field length density (px^-1), difference | skeleton px, difference | unowned px, difference | canalicular width median (px), difference | loops per cell, difference |
|---|---|---|---|---|---|---|---|---|---|
| 542_z06 | 19 of 19 | 1 | -1.9458 | -34.4083 | 0.00011139 | 91 | 58 | 0 | -0.7625 |
| 542_z18 | 13 of 13 | 0 | 0.6363 | -8.8182 | -0.00090581 | -921 | -230 | 0 | -0.1818 |
| 543-2 | 12 of 12 | 0 | -0.5833 | -4.3333 | -0.00077053 | -789 | -814 | 0.2462 | 0.8334 |
| 543_3 | 13 of 13 | 0 | 0.0833 | 8.3334 | -0.00070847 | -725 | -465 | 0 | -0.9166 |
| 543_z13 | 11 of 11 | 0 | -0.3636 | -4.2727 | 0.00029245 | 305 | -255 | 0 | -0.9091 |
| 682_z08 | 11 of 11 | 0 | 0.7778 | 7.6667 | 0.00114712 | 1153 | -141 | 0 | 2.1111 |
| 682_z23 | 14 of 14 | 0 | 0.4545 | -8 | -0.00045921 | -471 | 1262 | 0 | -1.5454 |
| 682_z29 | 14 of 15 | -1 | 0.4038 | 32.9102 | 0.00119656 | 1206 | 0 | 0 | 0.8525 |

### Real twins

| measure | pairs | mean difference | largest absolute difference | higher / lower / equal | SD over the 8 WT images | mean difference / SD |
|---|---|---|---|---|---|---|
| lacuna count | 4 | 0 | 0 | 0 / 0 / 4 | 2.61861 | +0.000 |
| roots per interior cell | 4 | -0.1 | 0.4 | 0 / 1 / 3 | 2.70609 | -0.037 |
| ring length 30 px per cell (px) | 4 | 1.26668 | 5.0667 | 1 / 0 / 3 | 67.8385 | +0.019 |
| field length density (px^-1) | 4 | 5.642e-05 | 0.00022568 | 1 / 0 / 3 | 0.0024852 | +0.023 |
| skeleton px | 4 | 56.75 | 227 | 1 / 0 / 3 | 2671.56 | +0.021 |
| unowned px | 4 | 460 | 1840 | 1 / 0 / 3 | 1626.54 | +0.283 |
| canalicular width median (px) | 4 | 0 | 0 | 0 / 0 / 4 | 0.113968 | +0.000 |
| loops per cell | 4 | -0.283325 | 1.1333 | 0 / 1 / 3 | 3.90876 | -0.072 |

Lacunae matched by centroid within 25 px (mutual nearest neighbours): 54 of 54.

| image | lacunae matched | lacuna count, difference | roots per interior cell, difference | ring length 30 px per cell (px), difference | field length density (px^-1), difference | skeleton px, difference | unowned px, difference | canalicular width median (px), difference | loops per cell, difference |
|---|---|---|---|---|---|---|---|---|---|
| 542_z06 | 19 of 19 | 0 | -0.4 | 5.0667 | 0.00022568 | 227 | 1840 | 0 | -1.1333 |
| 542_z18 | 13 of 13 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 543_z13 | 11 of 11 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 682_z08 | 11 of 11 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## The 8 WT images, TIFF

| image | lacuna count | roots per interior cell | ring length 30 px per cell (px) | field length density (px^-1) | skeleton px | unowned px | canalicular width median (px) | loops per cell |
|---|---|---|---|---|---|---|---|---|
| 542_z06 | 19 | 15.1333 | 485.533 | 0.0399422 | 40198 | 7311 | 8.2462 | 8.2 |
| 542_z18 | 13 | 11.8182 | 478.091 | 0.0389041 | 39183 | 9525 | 8.2462 | 10.8182 |
| 543-2 | 12 | 8.5 | 369.583 | 0.0430611 | 44105 | 6482 | 8 | 19.0833 |
| 543_3 | 13 | 7 | 325.583 | 0.0402993 | 41269 | 4752 | 8 | 17.3333 |
| 543_z13 | 11 | 9.2727 | 377.182 | 0.0430369 | 44246 | 9647 | 8 | 17.1818 |
| 682_z08 | 11 | 12.3333 | 463.111 | 0.0363541 | 36997 | 8583 | 8 | 14.2222 |
| 682_z23 | 14 | 9.7273 | 384.091 | 0.0391567 | 40046 | 8023 | 8 | 12.3636 |
| 682_z29 | 15 | 7.8462 | 312.923 | 0.036826 | 37663 | 8255 | 8 | 10.2308 |
| SD | 2.61861 | 2.70609 | 67.8385 | 0.0024852 | 2671.56 | 1626.54 | 0.113968 | 3.90876 |

## Real and synthetic twins of the same fields

| image | measure | tiff | real JPEG | synthetic JPEG | real - tiff | synthetic - tiff |
|---|---|---|---|---|---|---|
| 542_z06 | lacuna count | 19 | 19 | 20 | 0 | 1 |
| 542_z06 | roots per interior cell | 15.1333 | 14.7333 | 13.1875 | -0.4 | -1.9458 |
| 542_z06 | ring length 30 px per cell (px) | 485.533 | 490.6 | 451.125 | 5.0667 | -34.4083 |
| 542_z06 | field length density (px^-1) | 0.0399422 | 0.0401679 | 0.0400536 | 0.00022568 | 0.00011139 |
| 542_z06 | skeleton px | 40198 | 40425 | 40289 | 227 | 91 |
| 542_z06 | unowned px | 7311 | 9151 | 7369 | 1840 | 58 |
| 542_z06 | canalicular width median (px) | 8.2462 | 8.2462 | 8.2462 | 0 | 0 |
| 542_z06 | loops per cell | 8.2 | 7.0667 | 7.4375 | -1.1333 | -0.7625 |
| 542_z18 | lacuna count | 13 | 13 | 13 | 0 | 0 |
| 542_z18 | roots per interior cell | 11.8182 | 11.8182 | 12.4545 | 0 | 0.6363 |
| 542_z18 | ring length 30 px per cell (px) | 478.091 | 478.091 | 469.273 | 0 | -8.8182 |
| 542_z18 | field length density (px^-1) | 0.0389041 | 0.0389041 | 0.0379983 | 0 | -0.00090581 |
| 542_z18 | skeleton px | 39183 | 39183 | 38262 | 0 | -921 |
| 542_z18 | unowned px | 9525 | 9525 | 9295 | 0 | -230 |
| 542_z18 | canalicular width median (px) | 8.2462 | 8.2462 | 8.2462 | 0 | 0 |
| 542_z18 | loops per cell | 10.8182 | 10.8182 | 10.6364 | 0 | -0.1818 |
| 543_z13 | lacuna count | 11 | 11 | 11 | 0 | 0 |
| 543_z13 | roots per interior cell | 9.2727 | 9.2727 | 8.9091 | 0 | -0.3636 |
| 543_z13 | ring length 30 px per cell (px) | 377.182 | 377.182 | 372.909 | 0 | -4.2727 |
| 543_z13 | field length density (px^-1) | 0.0430369 | 0.0430369 | 0.0433294 | 0 | 0.00029245 |
| 543_z13 | skeleton px | 44246 | 44246 | 44551 | 0 | 305 |
| 543_z13 | unowned px | 9647 | 9647 | 9392 | 0 | -255 |
| 543_z13 | canalicular width median (px) | 8 | 8 | 8 | 0 | 0 |
| 543_z13 | loops per cell | 17.1818 | 17.1818 | 16.2727 | 0 | -0.9091 |
| 682_z08 | lacuna count | 11 | 11 | 11 | 0 | 0 |
| 682_z08 | roots per interior cell | 12.3333 | 12.3333 | 13.1111 | 0 | 0.7778 |
| 682_z08 | ring length 30 px per cell (px) | 463.111 | 463.111 | 470.778 | 0 | 7.6667 |
| 682_z08 | field length density (px^-1) | 0.0363541 | 0.0363541 | 0.0375012 | 0 | 0.00114712 |
| 682_z08 | skeleton px | 36997 | 36997 | 38150 | 0 | 1153 |
| 682_z08 | unowned px | 8583 | 8583 | 8442 | 0 | -141 |
| 682_z08 | canalicular width median (px) | 8 | 8 | 8 | 0 | 0 |
| 682_z08 | loops per cell | 14.2222 | 14.2222 | 16.3333 | 0 | 2.1111 |

## What it shows

**A second compression (synthetic twins).**

- lacuna count: higher in 1, lower in 1, equal in 6 of 8 pairs; mean change +0, largest 1; the SD between the 8 WT images is 2.619, so the mean change is +0.000 SD and the largest 0.382 SD.
- roots per interior cell: higher in 5, lower in 3 of 8 pairs; mean change -0.06713, largest 1.946; the SD between the 8 WT images is 2.706, so the mean change is -0.025 SD and the largest 0.719 SD.
- ring length 30 px per cell (px): higher in 3, lower in 5 of 8 pairs; mean change -1.365, largest 34.41; the SD between the 8 WT images is 67.84, so the mean change is -0.020 SD and the largest 0.507 SD.
- field length density (px^-1): higher in 4, lower in 4 of 8 pairs; mean change -1.206e-05, largest 0.001197; the SD between the 8 WT images is 0.002485, so the mean change is -0.005 SD and the largest 0.481 SD.
- skeleton px: higher in 4, lower in 4 of 8 pairs; mean change -18.88, largest 1206; the SD between the 8 WT images is 2672, so the mean change is -0.007 SD and the largest 0.451 SD.
- unowned px: higher in 2, lower in 5, equal in 1 of 8 pairs; mean change -73.12, largest 1262; the SD between the 8 WT images is 1627, so the mean change is -0.045 SD and the largest 0.776 SD.
- canalicular width median (px): higher in 1, equal in 7 of 8 pairs; mean change +0.03078, largest 0.2462; the SD between the 8 WT images is 0.114, so the mean change is +0.270 SD and the largest 2.160 SD.
- loops per cell: higher in 3, lower in 5 of 8 pairs; mean change -0.0648, largest 2.111; the SD between the 8 WT images is 3.909, so the mean change is -0.017 SD and the largest 0.540 SD.

The lacuna count changed in 2 of 8 pairs: 542_z06 (+1 lacuna; roots per interior cell -1.946, ring length 30 px per cell -34.41), 682_z29 (-1 lacuna; roots per interior cell +0.4038, ring length 30 px per cell +32.91). A per-cell measure is a mean over the interior lacunae, so it moves with the number of cells it is divided among as well as with the tracing.

**A different decode of the same JPEG (real twins).**

- lacuna count: identical in every pair.
- roots per interior cell: lower in 1, equal in 3 of 4 pairs; mean change -0.1, largest 0.4; the SD between the 8 WT images is 2.706, so the mean change is -0.037 SD and the largest 0.148 SD.
- ring length 30 px per cell (px): higher in 1, equal in 3 of 4 pairs; mean change +1.267, largest 5.067; the SD between the 8 WT images is 67.84, so the mean change is +0.019 SD and the largest 0.075 SD.
- field length density (px^-1): higher in 1, equal in 3 of 4 pairs; mean change +5.642e-05, largest 0.0002257; the SD between the 8 WT images is 0.002485, so the mean change is +0.023 SD and the largest 0.091 SD.
- skeleton px: higher in 1, equal in 3 of 4 pairs; mean change +56.75, largest 227; the SD between the 8 WT images is 2672, so the mean change is +0.021 SD and the largest 0.085 SD.
- unowned px: higher in 1, equal in 3 of 4 pairs; mean change +460, largest 1840; the SD between the 8 WT images is 1627, so the mean change is +0.283 SD and the largest 1.131 SD.
- canalicular width median (px): identical in every pair.
- loops per cell: lower in 1, equal in 3 of 4 pairs; mean change -0.2833, largest 1.133; the SD between the 8 WT images is 3.909, so the mean change is -0.072 SD and the largest 0.290 SD.

Against the spread between the 8 WT images, the synthetic mean changes rank, largest first: canalicular width median (px) +0.270 SD; unowned px -0.045 SD; roots per interior cell -0.025 SD; ring length 30 px per cell (px) -0.020 SD; loops per cell -0.017 SD; skeleton px -0.007 SD; field length density (px^-1) -0.005 SD; lacuna count +0.000 SD.

canalicular width median (px) takes only 2 values over the 8 WT images (8, 8.2462), so its SD is set by the pixel grid: one step between them, 0.2462, is 2.16 SD.

Limits: 8 pairs for the synthetic set and 4 for the real set, one run each; the comparison is of a second compression and of a decoder, not of a first compression, for the reason given at the top. Nothing here is validated against a manual count.
