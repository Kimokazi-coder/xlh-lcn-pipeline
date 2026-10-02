# Figure captions (draft)

Drafts for every figure in `figures_out/`. Pre-validation, pixel units, wild-type (WT) only.

## Display window

Every image panel in every figure uses one fixed display window, computed once over the whole dataset:
the 1st and 99.8th percentile of the pooled red channel of all 8 WT images, 20 to 255 grey levels of
255 (`figures_out/display_window.json`). Images are not stretched one by one, so their brightness can
be compared by eye. The window is for display only; no measurement uses it.
