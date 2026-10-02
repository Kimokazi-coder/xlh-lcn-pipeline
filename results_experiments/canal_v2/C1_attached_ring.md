# C1 Attached ring length

Pre-validation, px. New per-lacuna columns `ring_attached_length_r30_px` and `ring_attached_length_r60_px`
(src/canaliculi.py, appended after every existing column). The ring of a lacuna is exactly the pixel set of
`ring_length_rR_px` (skeleton px within R px of the lacuna masks whose nearest lacuna is this one). Its
8-connected components are taken within that ring only. A component is attached if one of its pixels lies
within 10 px (`LACUNA_ATTACH_GAP_PX`, the constant the roots use) of the
lacuna masks. The attached length is the pixel count of attached components; the rest is passing length.
Attached is at most ring length for every lacuna (asserted in the pipeline and here).

## Share of ring length that is attached, interior lacunae

| image | interior lacunae | attached / ring 30 (sum) | per cell min | per cell median | per cell max | attached / ring 60 (sum) | ring30 mean | attached30 mean |
|---|---|---|---|---|---|---|---|---|
| 542_z06 | 13 | 0.756 | 0.530 | 0.745 | 0.875 | 0.552 | 361.462 | 273.308 |
| 542_z18 | 11 | 0.672 | 0.515 | 0.636 | 0.911 | 0.495 | 357.091 | 239.909 |
| 543-2 | 12 | 0.758 | 0.375 | 0.741 | 0.949 | 0.593 | 306.583 | 232.500 |
| 543_3 | 9 | 0.704 | 0.424 | 0.767 | 0.854 | 0.513 | 313.556 | 220.889 |
| 543_z13 | 11 | 0.676 | 0.436 | 0.636 | 0.890 | 0.518 | 302.909 | 204.636 |
| 682_z08 | 8 | 0.799 | 0.684 | 0.796 | 0.954 | 0.686 | 396.750 | 317.125 |
| 682_z23 | 11 | 0.753 | 0.367 | 0.795 | 0.932 | 0.527 | 283.364 | 213.273 |
| 682_z29 | 11 | 0.708 | 0.554 | 0.742 | 0.885 | 0.501 | 250.273 | 177.273 |


Pooled over all 86 interior lacunae: attached / ring 30 = 0.729, attached / ring 60 = 0.547. Per-cell share at 30 px ranges from 0.367 to 0.954.

Spearman correlations over interior lacunae (roots, ring 30, attached ring 30):

| measure | roots | ring30 | ring_attached_length_r30_px |
|---|---|---|---|
| roots | 1.000 | 0.825 | 0.869 |
| ring30 | 0.825 | 1.000 | 0.901 |
| ring_attached_length_r30_px | 0.869 | 0.901 | 1.000 |


## Crops

`C1_crops.png`: the 3 interior lacunae with the most passing length (one per image), raw and overlay at 3x.
Vermillion: attached ring pixels. Sky blue: passing ring pixels. Grey: other skeleton. Cyan: lacuna outline.
White dashes: edge of the 30 px ring region. Per-lacuna values: `C1_attached_ring.csv`.

Shown: 542_z18 L4 (874,210), passing 209 of 431 px; 682_z23 L3 (472,61), passing 186 of 294 px; 543_z13 L7 (874,547), passing 169 of 308 px.
