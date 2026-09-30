# Step 1: per-cell reach of owned canaliculi

PRE-VALIDATION, PIXEL units. Read-only; no pipeline output changed.
Graph distances along the skeleton from each cell (see the script docstring for
entry, exit and reach). All cells, border cells included, unless stated.

## Verification: rebuilt graph vs committed default outputs

Interior mean edge count per cell, rebuilt here vs results/canaliculi/<image>/measurements.json:

    542 WT  2_z06c1-2      rebuilt  30.8462  committed  30.8462  OK
    542 WT  2_z18c1-2      rebuilt  32.0000  committed  32.0000  OK
    543-2                  rebuilt  62.3333  committed  62.3333  OK
    543_3                  rebuilt  47.1111  committed  47.1111  OK
    543_z13c1-2            rebuilt  63.5455  committed  63.5455  OK
    682_z08c1-2            rebuilt  76.0000  committed  76.0000  OK
    682_z23c-2             rebuilt  35.0000  committed  35.0000  OK
    682_z29c1-3            rebuilt  26.1818  committed  26.1818  OK

## Exit distance per owned edge (px), per image and pooled

```
  542 WT  2_z06c1-2                  n=  460  median   75.3  p75  132.6  p90  260.8  p95  335.9  max   496.7
  542 WT  2_z18c1-2                  n=  378  median   78.4  p75  125.7  p90  169.7  p95  198.6  max   343.4
  543-2                              n=  748  median  119.2  p75  189.1  p90  301.6  p95  398.2  max   863.5
  543_3                              n=  425  median  108.9  p75  194.3  p90  286.8  p95  331.1  max   421.0
  543_z13c1-2                        n=  699  median  125.1  p75  217.4  p90  414.7  p95  553.2  max   814.1
  682_z08c1-2                        n=  637  median  113.5  p75  249.4  p90  565.1  p95  704.2  max   825.2
  682_z23c-2                         n=  437  median  101.7  p75  194.6  p90  318.7  p95  361.2  max   635.9
  682_z29c1-3                        n=  328  median  100.5  p75  172.5  p90  244.9  p95  279.9  max   377.8
  POOLED                             n= 4112  median  104.9  p75  182.3  p90  307.2  p95  448.9  max   863.5
```

Entry distance per owned edge (px), pooled:

```
  POOLED entry                       n= 4112  median   76.1  p75  153.8  p90  274.8  p95  420.1  max   855.3
```

## Cell reach (largest exit distance per cell) and cells beyond each distance

| image | cells | reach median | reach max | > 50 | > 75 | > 100 | > 150 | > 200 |
|---|---|---|---|---|---|---|---|---|
| 542 WT  2_z06c1-2 | 16 | 178.3 | 496.7 | 15 | 15 | 14 | 12 | 6 |
| 542 WT  2_z18c1-2 | 12 | 196.5 | 343.4 | 12 | 12 | 12 | 10 | 6 |
| 543-2 | 12 | 236.8 | 863.5 | 12 | 12 | 12 | 11 | 7 |
| 543_3 | 10 | 250.9 | 421.0 | 9 | 8 | 8 | 8 | 6 |
| 543_z13c1-2 | 11 | 311.8 | 814.1 | 11 | 11 | 10 | 9 | 7 |
| 682_z08c1-2 | 10 | 172.5 | 825.2 | 10 | 10 | 10 | 7 | 4 |
| 682_z23c-2 | 14 | 183.0 | 635.9 | 13 | 13 | 12 | 8 | 6 |
| 682_z29c1-3 | 13 | 160.1 | 377.8 | 13 | 12 | 12 | 7 | 4 |
| **POOLED** | 98 | 193.3 | 863.5 | **95** | **93** | **90** | **72** | **46** |

## Largest owner of skeleton length in each image

| image | cell | at (x,y) | lacuna area px2 | owned length px | share of image owned length | reach px |
|---|---|---|---|---|---|---|
| 542 WT  2_z06c1-2 | 13 | (247,723) | 4647 | 2992 | 20.8% | 497 |
| 542 WT  2_z18c1-2 | 2 | (639,130) | 5924 | 1962 | 17.4% | 276 |
| 543-2 | 11 | (480,787) | 2173 | 3948 | 19.5% | 864 |
| 543_3 | 4 | (370,389) | 2052 | 2574 | 19.9% | 421 |
| 543_z13c1-2 | 5 | (481,460) | 2267 | 4189 | 22.2% | 665 |
| 682_z08c1-2 | 4 | (210,434) | 4123 | 6470 | 41.3% | 825 |
| 682_z23c-2 | 8 | (349,558) | 980 | 3059 | 23.4% | 636 |
| 682_z29c1-3 | 4 | (220,431) | 3140 | 2207 | 21.4% | 338 |

## Owned length retained under a cap (pooled over 8 images)

Rule: an edge stays owned if its entry distance is <= the cap (kept whole).

| cap px | owned length retained |
|---|---|
| 25 | 30.4% |
| 50 | 41.9% |
| 75 | 52.6% |
| 100 | 61.8% |
| 125 | 69.5% |
| 150 | 75.6% |
| 175 | 80.3% |
| 200 | 83.3% |
| 225 | 86.0% |
| 250 | 88.6% |
| 275 | 90.8% |
| 300 | 92.0% |
| 325 | 93.4% |
| 350 | 94.3% |
| 375 | 94.9% |
| 400 | 95.5% |
| 500 | 96.8% |
| 600 | 98.3% |
| 700 | 99.3% |
| 800 | 99.9% |
| 900 | 100.0% |
| 1000 | 100.0% |

**Selection rule** (set for the overnight run): the smallest cap that leaves at least 90% of pooled owned skeleton length owned, rounded to a multiple of 25 px.

- Exact smallest cap reaching 90%: **265.1 px** (the length-weighted 90th percentile of entry distance).
- Rounded UP to the next multiple of 25 so the 90% floor still holds: **275 px**, which retains 90.8%.
  Rounding to the nearest multiple gives the same value here, so the two readings of the rule agree.

## 682_z29 cells by verification colour

| cell | colour (RGB) | lacuna area px2 | at (x,y) | owned length px | reach px |
|---|---|---|---|---|---|
| 4 | (25, 255, 96) | 3140 | (220,431) | 2207 | 338 |
| 3 | (60, 25, 255) | 446 | (449,250) | 1415 | 322 |
| 8 | (25, 202, 255) | 1399 | (182,716) | 1252 | 378 |
| 2 | (166, 25, 255) | 2213 | (921,135) | 1039 | 185 |
| 7 | (166, 255, 25) | 3781 | (55,590) | 857 | 160 |
| 6 | (255, 237, 25) | 1634 | (357,555) | 840 | 160 |
| 5 | (255, 25, 237) | 2837 | (493,532) | 800 | 261 |
| 12 | (255, 25, 131) | 2966 | (307,920) | 490 | 137 |
| 9 | (25, 96, 255) | 513 | (76,831) | 411 | 136 |
| 10 | (60, 255, 25) | 1130 | (125,842) | 405 | 125 |
| 13 | (25, 255, 202) | 1624 | (438,978) | 261 | 107 |
| 11 | (255, 25, 25) | 1244 | (761,905) | 214 | 124 |
| 1 | (255, 131, 25) | 2083 | (99,13) | 103 | 72 |

Cyan on the overlay is (25, 202, 255), cell 8.
