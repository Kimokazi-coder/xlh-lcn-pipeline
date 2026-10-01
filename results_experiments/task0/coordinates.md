# Coordinate check

`python src/diagnostics.py lacuna-table` prints `at (x,y)` from `centroid_col_px` and
`centroid_row_px` in that order (src/diagnostics.py, cmd_lacuna_table). The cached rows for
543-2 give the same pairs, so (x, y) = (column, row) throughout.

| lacuna | centroid_col_px (x) | centroid_row_px (y) | lacuna-table prints |
|---|---|---|---|
| 1 | 271.2 | 88.1 | (271,88) |
| 2 | 919.0 | 207.8 | (919,208) |
| 3 | 340.8 | 257.4 | (341,257) |
| 4 | 38.8 | 297.0 | (39,297) |
| 5 | 364.6 | 394.3 | (365,394) |
| 6 | 745.5 | 472.2 | (746,472) |
| 7 | 484.8 | 459.4 | (485,459) |
| 8 | 877.6 | 550.3 | (878,550) |
| 9 | 193.3 | 642.8 | (193,643) |
| 10 | 634.0 | 728.3 | (634,728) |
| 11 | 480.1 | 787.2 | (480,787) |
| 12 | 288.0 | 859.5 | (288,859) |
