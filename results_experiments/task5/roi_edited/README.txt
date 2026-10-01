Hand-edited bone ROI masks

Put one PNG per image here, named by the short image name used in the tables
(542_z06.png, 542_z18.png, 543-2.png, 543_3.png, 543_z13.png, 682_z08.png,
682_z23.png, 682_z29.png): 1024 x 1024, white = bone (analysed), black =
excluded. A good start is the draft in ../roi_draft/<image>_roi.png.

When a mask is here, experiments/task5_density.py uses it instead of the draft
(roi_mask in that script); the roi_source column of 5.1 says which was used.
Delete results_experiments/task5/5.1_density_three_ways.* and rerun
python -u experiments/task5_density.py 5.1 to recompute. Nothing in src/ reads
these masks.
