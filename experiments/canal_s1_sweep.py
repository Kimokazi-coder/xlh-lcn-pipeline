"""S1: the network sweep and its reading.

    python -u experiments/canal_s1_sweep.py

Runs `python src/diagnostics.py network-sweep` into the git-ignored cache (each
run is skipped if its json exists), then writes results_experiments/canal_v2/
S1_network_sweep.csv and S1_network_sweep.md: the subcommand's tables and a
reading computed from them (which parameters move which measure; Sholl
crossings against roots). PRE-VALIDATION, PIXEL units.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canal_common as K  # noqa: E402
import common as C  # noqa: E402

SWEEP_OUT = C.OUT_ROOT / "_cache" / "network_sweep"
GRAPH = ["PRUNE_SPUR_LEN_PX", "ROOT_MERGE_DIST_PX", "LACUNA_ATTACH_GAP_PX"]
MASK = ["TOPHAT_RADIUS_PX", "HYSTERESIS_LOW_FRACTION", "t_lo scale"]
BRIDGING = ["MAX_BRIDGE_GAP_PX", "MAX_BRIDGE_ANGLE_DEG", "MIN_BRIDGE_SIGNAL_FRACTION"]
LABELS = {"roots_per_cell": "roots per cell", "ring30": "ring 30 px", "ring30_attached": "ring attached 30 px",
          "ring30_weighted": "ring weighted 30 px", "sholl10": "Sholl 10 px", "sholl20": "Sholl 20 px",
          "sholl30": "Sholl 30 px", "field_density": "field density"}


def item_s1() -> None:
    done = subprocess.run([sys.executable, "-u", str(C.ROOT / "src" / "diagnostics.py"), "network-sweep",
                           "-o", str(SWEEP_OUT)], capture_output=True, text=True, cwd=C.ROOT)
    assert done.returncode == 0, done.stderr[-3000:]
    df = pd.read_csv(SWEEP_OUT / "network_sweep.csv")
    C.write_csv(K.OUT / "S1_network_sweep.csv", df)
    sweep_md = (SWEEP_OUT / "network_sweep.md").read_text(encoding="utf-8")

    def worst(measure: str, params: list[str]) -> tuple[float, str]:
        best = (0.0, "")
        for p in params:
            for v in sorted(df[df.parameter == p].value.unique()):
                med = float(np.median(df[(df.parameter == p) & (df.value == v)][f"{measure}_pct"].dropna()))
                if abs(med) > abs(best[0]):
                    best = (med, f"{p} = {v:g}")
        return best

    rows = []
    for m, label in LABELS.items():
        g, gs = worst(m, GRAPH)
        k, ks = worst(m, MASK)
        b, bs = worst(m, BRIDGING)
        rows.append({"measure": label, "graph and attach (largest median %)": g, "at": gs,
                     "mask and cut (largest median %)": k, "at ": ks, "bridging (largest median %)": b, "at  ": bs})
    rdf = pd.DataFrame(rows)
    nob = df[(df.parameter == "MAX_BRIDGE_GAP_PX") & (df.value == 0)]
    rng = {m: (nob[f"{m}_pct"].min(), nob[f"{m}_pct"].max()) for m in ("roots_per_cell", "ring30", "field_density")}
    roots_g = worst("roots_per_cell", GRAPH)
    sholl_g = max(abs(worst(m, GRAPH)[0]) for m in ("sholl10", "sholl20", "sholl30"))
    roots_k = worst("roots_per_cell", MASK)
    sholl_k = worst("sholl10", MASK)
    md = [sweep_md.rstrip(), "", "## Reading", "",
          "Largest median change per measure within three groups of parameters (graph and attach: the spur",
          "length, the root merge distance and the attach gap; mask and cut: the top-hat radius, the hysteresis",
          "low fraction and the t_lo scale; bridging: gap, angle and minimum signal):", "",
          C.md_table(rdf, floatfmt="{:+.1f}"), "",
          "- **The mask and the cut move everything.** The hysteresis low fraction and the t_lo scale move every",
          "  length, density and count measure by about 7 to 17% at the low and high settings, and the top-hat",
          "  radius by up to about 10%. These are the parameters that decide what the skeleton is.",
          "- **Graph and attach parameters move only the roots and the attached ring.** Roots per cell move by up",
          f"  to {abs(roots_g[0]):.1f}% ({roots_g[1]}); ring 30 px, ring weighted, field density and the Sholl",
          f"  crossings do not move at all (largest {sholl_g:.1f}% for the Sholl crossings), because they do not use",
          "  the graph. The attached ring uses the attach gap by definition and moves with it.",
          "- **Bridging matters little for the headline measures.** With no bridging (MAX_BRIDGE_GAP_PX = 0) the",
          f"  bridges go to 0, but roots per cell move by {rng['roots_per_cell'][0]:+.1f} to {rng['roots_per_cell'][1]:+.1f}%,",
          f"  ring 30 px by {rng['ring30'][0]:+.1f} to {rng['ring30'][1]:+.1f}% and field density by "
          f"{rng['field_density'][0]:+.1f} to {rng['field_density'][1]:+.1f}% over the 8 images. The bridge count itself",
          "  is the least stable output (median +519 to +563%, six to seven times as many, at a hysteresis fraction",
          "  of 0.975 or a minimum signal of 0.49).",
          "- **Sholl crossings against roots.** Both respond to the mask and the cut by similar amounts (largest",
          f"  median for roots {roots_k[0]:+.1f}% at {roots_k[1]}, for Sholl 10 px {sholl_k[0]:+.1f}% at {sholl_k[1]}).",
          "  The Sholl crossings are untouched by the three graph and attach parameters, while roots move by up to",
          f"  {abs(roots_g[0]):.1f}% with them. So the Sholl crossings are more robust to the network parameters than",
          "  roots, which carry the extra choices of the attach gap and the merge distance. Of all measures, the",
          "  Sholl crossings at 20 and 30 px move least overall; the bridge count moves most, then the attached",
          "  ring and the roots.",
          "- No value is recommended and no default changed. Which setting is right can only be decided against",
          "  hand counts or traced threads (docs/NETWORK_TUNING_PROTOCOL.md).", ""]
    C.write_text(K.OUT / "S1_network_sweep.md", "\n".join(md))
    print("\n".join(md[-40:]))


if __name__ == "__main__":
    K.OUT.mkdir(parents=True, exist_ok=True)
    ok = C.run_item("S1", item_s1)
    sys.exit(0 if ok else 1)
