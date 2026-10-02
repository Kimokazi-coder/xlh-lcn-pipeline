# B1 evidence: straight runs of the skeleton

Pre-validation, px, (x, y) = (column, row). Default run of every image. For each line length L, the
straight-run pixels are the pixels of the skeleton widened to 3 px (3 x 3 dilation) that lie under a
one-pixel line of L px fitting entirely inside it, at any of 24 orientations (7.5 degree steps). They
are grouped into 8-connected straight objects. Length is the largest Feret diameter; orientation is 0
along x and 90 along y. "skeleton px on runs" counts skeleton px lying on the run pixels; "within 2 px"
counts skeleton px within 2 px of the object, which is what the filter removes. L is the Euclidean
length of the line. The 542_z06 line is every object with pixels in the corridor x 515 to 541,
y 590 to 900 (overnight report 5.3). All objects: `B1_straight_runs.csv`.

## The line against everything else, by L

| L | 542_z06 line: objects | line: longest px | line: skeleton px on runs | line: skeleton px within 2 px | line: min distance to flagged | other objects | others: longest px | others within 20 px of flagged | those: longest px |
|---|---|---|---|---|---|---|---|---|---|
| 40.0 | 3.0 | 139.0 | 221.0 | 267.0 | 0.0 | 1322.0 | 192.5 | 87.0 | 123.3 |
| 60.0 | 2.0 | 130.0 | 114.0 | 203.0 | 37.0 | 103.0 | 121.2 | 7.0 | 121.2 |
| 80.0 | 1.0 | 130.0 | 75.0 | 132.0 | 37.0 | 7.0 | 91.7 | 1.0 | 91.7 |
| 85.0 | 1.0 | 102.0 | 30.0 | 103.0 | 65.0 | 3.0 | 96.6 | 1.0 | 96.6 |
| 90.0 | 1.0 | 102.0 | 30.0 | 103.0 | 65.0 | 1.0 | 90.8 | 1.0 | 90.8 |
| 95.0 | 1.0 | 102.0 | 30.0 | 103.0 | 65.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| 100.0 | 1.0 | 102.0 | 30.0 | 103.0 | 65.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| 105.0 | 0.0 | 0.0 | 0.0 | 0.0 |  | 0.0 | 0.0 | 0.0 | 0.0 |
| 110.0 | 0.0 | 0.0 | 0.0 | 0.0 |  | 0.0 | 0.0 | 0.0 | 0.0 |
| 115.0 | 0.0 | 0.0 | 0.0 | 0.0 |  | 0.0 | 0.0 | 0.0 | 0.0 |
| 120.0 | 0.0 | 0.0 | 0.0 | 0.0 |  | 0.0 | 0.0 | 0.0 | 0.0 |
| 140.0 | 0.0 | 0.0 | 0.0 | 0.0 |  | 0.0 | 0.0 | 0.0 | 0.0 |
| 160.0 | 0.0 | 0.0 | 0.0 | 0.0 |  | 0.0 | 0.0 | 0.0 | 0.0 |
| 200.0 | 0.0 | 0.0 | 0.0 | 0.0 |  | 0.0 | 0.0 | 0.0 | 0.0 |
| 250.0 | 0.0 | 0.0 | 0.0 | 0.0 |  | 0.0 | 0.0 | 0.0 | 0.0 |
| 300.0 | 0.0 | 0.0 | 0.0 | 0.0 |  | 0.0 | 0.0 | 0.0 | 0.0 |


## The longest other straight objects at each L (top 8)

| L | image | x | y | x0 | y0 | x1 | y1 | length_px | orientation_deg | skeleton_px | dist_to_flagged_px | touches_flagged |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 40 | 543-2 | 835 | 192 | 824 | 98 | 848 | 288 | 192.5 | 83.6 | 181 |  | False |
| 40 | 543_z13 | 942 | 52 | 868 | 2 | 1015 | 82 | 168.2 | 148.9 | 124 |  | False |
| 40 | 543-2 | 822 | 944 | 746 | 909 | 899 | 959 | 161.9 | 170.1 | 149 |  | False |
| 40 | 543-2 | 768 | 847 | 690 | 834 | 844 | 857 | 155.9 | 172.4 | 126 |  | False |
| 40 | 542_z18 | 936 | 455 | 877 | 411 | 999 | 480 | 141.0 | 35.3 | 111 | 238.6 | False |
| 40 | 543-2 | 808 | 603 | 732 | 582 | 865 | 619 | 137.5 | 163.7 | 104 |  | False |
| 40 | 682_z23 | 529 | 241 | 468 | 183 | 595 | 304 | 137.4 | 141.4 | 168 | 63.1 | False |
| 40 | 543_z13 | 134 | 746 | 94 | 688 | 200 | 770 | 134.0 | 36.1 | 102 |  | False |
| 60 | 542_z06 | 580 | 70 | 567 | 9 | 590 | 127 | 121.2 | 100.5 | 95 | 0.0 | True |
| 60 | 682_z23 | 99 | 105 | 43 | 100 | 158 | 112 | 116.4 | 174.1 | 79 | 0.0 | True |
| 60 | 682_z29 | 96 | 449 | 50 | 445 | 142 | 453 | 93.1 | 177.3 | 34 | 235.7 | False |
| 60 | 543_z13 | 618 | 323 | 583 | 302 | 654 | 343 | 82.9 | 150.0 | 32 |  | False |
| 60 | 543_3 | 773 | 660 | 733 | 660 | 813 | 660 | 81.0 | 0.0 | 17 |  | False |
| 60 | 543-2 | 853 | 382 | 815 | 377 | 894 | 388 | 80.8 | 172.3 | 70 |  | False |
| 60 | 543_z13 | 900 | 54 | 858 | 53 | 937 | 54 | 80.0 | 179.9 | 65 |  | False |
| 60 | 543-2 | 832 | 171 | 827 | 131 | 837 | 208 | 78.6 | 82.5 | 56 |  | False |
| 80 | 682_z23 | 90 | 105 | 45 | 100 | 135 | 111 | 91.7 | 172.4 | 72 | 7.3 | False |
| 80 | 543_3 | 773 | 660 | 733 | 660 | 813 | 660 | 81.0 | 0.0 | 17 |  | False |
| 80 | 543-2 | 856 | 382 | 816 | 377 | 895 | 387 | 80.6 | 172.4 | 46 |  | False |
| 80 | 543_z13 | 898 | 54 | 858 | 54 | 937 | 54 | 80.0 | 0.0 | 54 |  | False |
| 80 | 543_z13 | 618 | 323 | 584 | 303 | 652 | 343 | 79.8 | 149.9 | 19 |  | False |
| 80 | 543-2 | 832 | 167 | 827 | 128 | 837 | 206 | 79.6 | 82.4 | 35 |  | False |
| 80 | 543_z13 | 162 | 765 | 123 | 760 | 201 | 770 | 79.6 | 7.6 | 32 |  | False |
| 85 | 682_z23 | 89 | 105 | 42 | 100 | 137 | 111 | 96.6 | 172.7 | 67 | 5.4 | False |
| 85 | 543-2 | 788 | 846 | 747 | 835 | 829 | 857 | 85.9 | 165.0 | 38 |  | False |
| 85 | 543-2 | 832 | 167 | 827 | 125 | 837 | 209 | 85.6 | 82.6 | 36 |  | False |
| 90 | 682_z23 | 88 | 106 | 43 | 100 | 132 | 112 | 90.8 | 172.4 | 51 | 10.2 | False |


## Reading and decision

- The 542_z06 line is straight only in pieces at a 3 px tolerance: its longest straight object is 139 px, and the skeleton within 2 px of its straight objects (what the filter would remove) is 267 px at L 40 (of the 382 px in the corridor) and 132 px at L 80.
- Its straight part touches the flagged mask only at L 40. At that L, 66 other straight objects touch a flagged mask in 5 images.
- A gap in L exists: other objects survive up to L 90, the line up to L 100, nothing at L 105. In that gap (L 95, 100) the line's straight object has 103 skeleton px within 2 px and lies 65.0 px from the flagged mask (65.01 px unrounded): it does not continue the canal region.
- **Decision.** The band wall is not separable as intended: no (L, reach) removes the line as a continuation
  of the canal mask without removing other threads. `BAND_LINE_FILTER` stays off, and no value is
  recommended (`BAND_LINE_MIN_LEN_PX` and `BAND_LINE_REACH_PX` stay None). What the filter does at the two
  evidence settings is in `B1_filter.md`.
