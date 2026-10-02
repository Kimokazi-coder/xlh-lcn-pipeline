"""C2: chain code length against the pixel count, per image.

    python -u experiments/canal_c2_length.py

Self-checks on synthetic skeletons (asserted): a horizontal line of 100 px
gives 99, a 45 degree diagonal of 100 px gives 99 sqrt(2), an L of two
100 px arms (199 px) gives 198. Then, per image of the default run: the
chain code length (src/canaliculi.py skeleton_links), the number of links,
the pixel count, and the links and their length by direction.

Outputs in results_experiments/canal_v2/: C2_chain_length.csv, .md.
PRE-VALIDATION, PIXEL units.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canal_common as K  # noqa: E402
import common as C  # noqa: E402
import canaliculi  # noqa: E402

SQRT2 = float(np.sqrt(2.0))


def selfcheck() -> list[str]:
    lines = []
    z = np.zeros((220, 220), bool)
    z[5, 5:105] = True
    cases = [("horizontal line, 100 px", z.copy(), 99.0)]
    z = np.zeros((220, 220), bool)
    z[np.arange(5, 105), np.arange(5, 105)] = True
    cases.append(("45 degree diagonal, 100 px", z.copy(), 99 * SQRT2))
    z = np.zeros((220, 220), bool)
    z[5, 5:105] = True
    z[5:105, 5] = True
    cases.append(("L shape, two arms of 100 px (199 px)", z.copy(), 198.0))
    for label, mask, expected in cases:
        got = canaliculi.chain_length(mask)
        assert abs(got - expected) < 1e-9, (label, got, expected)
        lines.append(f"| {label} | {int(mask.sum())} | {expected:.6f} | {got:.6f} | PASS |")
    return lines


def item_c2() -> None:
    checks = selfcheck()
    rows = []
    for name in K.names():
        d = K.pipeline(name)
        sk = d["skeleton"]
        links = canaliculi.skeleton_links(sk)
        w, dirn = links["weights"], links["direction"]
        n_px, n_links, length = int(sk.sum()), int(w.size), float(w.sum())
        # Every 8-neighbour pair, with no diagonal left out (for comparison).
        plain = length + SQRT2 * links["diagonal_dropped"]
        f = d["field"]
        assert abs(f["field_length_density_w_per_px"] - round(length / f["analysed_area_px2"], 8)) < 1e-12
        row = {"image": name, "skeleton_px": n_px, "links": n_links, "chain_length_px": length,
               "length_over_links": length / n_links, "length_over_px": length / n_px,
               "diagonal_links_left_out": links["diagonal_dropped"], "plain_8_link_length_px": plain}
        for k, label in (("h", "horizontal"), ("v", "vertical"), ("d", "diagonal")):
            sel = dirn == k
            row[f"{label}_links"] = int(sel.sum())
            row[f"{label}_share_of_links"] = float(sel.mean())
            row[f"{label}_share_of_length"] = float(w[sel].sum() / length)
        row["field_density_px"] = f["canalicular_length_density_per_px"]
        row["field_density_w"] = f["field_length_density_w_per_px"]
        row["density_ratio_w_over_px"] = row["field_density_w"] / row["field_density_px"]
        cr = K.interior(d["cell_rows"])
        row["ring30_w_over_px"] = (sum(c["ring_length_w_r30_px"] for c in cr) / sum(c["ring_length_r30_px"] for c in cr))
        row["ring60_w_over_px"] = (sum(c["ring_length_w_r60_px"] for c in cr) / sum(c["ring_length_r60_px"] for c in cr))
        rows.append(row)
    df = pd.DataFrame(rows)
    C.write_csv(K.OUT / "C2_chain_length.csv", df)
    under = 1 - 1 / SQRT2
    diag_share = df.diagonal_share_of_links
    md = ["# C2 Chain code length", "",
          "Pre-validation, px. New columns `ring_length_w_r30_px`, `ring_length_w_r60_px` (per lacuna, interior means in",
          "the summary) and `field_length_density_w_per_px` (field block and summary table). The skeleton is a pixel",
          "graph: a link joins two neighbouring skeleton pixels, each pair once, with weight 1 for an orthogonal and",
          r"$\sqrt{2}$ for a diagonal link. A link belongs to a region if its first pixel in raster order lies in it.",
          "A diagonal link is left out when its two pixels already share an orthogonal neighbour on the skeleton",
          "(mixed adjacency): at a corner the path runs over that neighbour, and with every 8-neighbour pair the L",
          r"below would measure $198 + \sqrt{2}$ instead of 198. The components are the same either way. The existing",
          "pixel-count columns stay as they are.", "",
          "## Self-checks (asserted)", "",
          "| skeleton | pixels | expected | measured | result |", "|---|---|---|---|---|", *checks, "",
          "## Per image", "",
          C.md_table(df[["image", "skeleton_px", "links", "chain_length_px", "length_over_links", "length_over_px",
                         "horizontal_share_of_links", "vertical_share_of_links", "diagonal_share_of_links"]],
                     floatfmt="{:.4f}"), "",
          "Length per link by direction is 1 for horizontal and vertical links and "
          rf"$\sqrt{{2}}$ = {SQRT2:.4f} for diagonal links, by definition. Share of length by direction:", "",
          C.md_table(df[["image", "horizontal_share_of_length", "vertical_share_of_length", "diagonal_share_of_length",
                         "diagonal_links_left_out", "plain_8_link_length_px"]], floatfmt="{:.4f}"), "",
          "Weighted against pixel-count measures (sums over interior lacunae for the rings):", "",
          C.md_table(df[["image", "density_ratio_w_over_px", "ring30_w_over_px", "ring60_w_over_px"]],
                     floatfmt="{:.4f}"), "",
          "## How much the pixel count underestimated", "",
          rf"A diagonal step is $\sqrt{{2}}$ px long but adds one pixel, so along a diagonal thread the pixel count is",
          rf"$1/\sqrt{{2}}$ of the length: {100 * under:.1f}% short. Horizontal and vertical threads are counted",
          f"right. Diagonal links are {100 * diag_share.min():.1f} to {100 * diag_share.max():.1f}% of all links",
          f"(median {100 * diag_share.median():.1f}%), so the weighted field density is "
          f"{df.density_ratio_w_over_px.min():.3f} to {df.density_ratio_w_over_px.max():.3f} times the pixel-count",
          f"density, and the weighted ring 30 px {df.ring30_w_over_px.min():.3f} to {df.ring30_w_over_px.max():.3f}",
          "times the pixel count. The pixel count per link is close to 1 (pixels and links differ by the number of",
          "components and loops), so the length per pixel above is the size of the bias. Across these 8 images the",
          f"bias is similar ({100 * (df.density_ratio_w_over_px.min() - 1):.1f} to "
          f"{100 * (df.density_ratio_w_over_px.max() - 1):.1f}% for field density), smallest in the three 682 images,",
          "which have the most axis-aligned links (their lattice). The ordering of the images by field density is",
          "the same with both lengths: "
          + ("yes" if list(df.sort_values("field_density_px").image) == list(df.sort_values("field_density_w").image)
             else "no") + ". Within an image the bias differs by thread angle (0 for axis-aligned, "
          f"{100 * under:.1f}% for diagonal threads), so the weighted length matters most for comparing threads or",
          "cells of different orientation.", ""]
    C.write_text(K.OUT / "C2_chain_length.md", "\n".join(md))
    print("\n".join(md))


if __name__ == "__main__":
    K.OUT.mkdir(parents=True, exist_ok=True)
    ok = C.run_item("C2", item_c2)
    sys.exit(0 if ok else 1)
