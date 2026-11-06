"""Per-animal summaries and the 2 x 2 statistics (genotype by diet).

PRE-VALIDATION. The animal is the unit: data/animals.csv maps every image to
an animal (from the file name prefix), a genotype (WT or Hyp) and a diet (RD
or HP), none of it confirmed yet. The question is the genotype by diet
interaction: does the high phosphate diet change Hyp mice differently from WT
mice?

Measures, from what the pipeline saved (no new detection):
    POL (src/pols.py, the working POL definition): lacunar area, the 90th
        percentile, the share above 2 x the WT median, the share above
        100 um2 and the POL area per analysed area, over measured lacunae
        (interior, with an area);
    canaliculi (the headline measures of src/quantification.py): roots per
        lacuna, ring length within 30 px (3.9 um) per lacuna, field length
        density and the median canalicular width, in um.

Models (statsmodels):
    animal level, the primary analysis: one value per animal, ordinary least
        squares y ~ hyp * hp, t intervals on the residual degrees of freedom;
    mixed: lacunar area, roots and ring length per lacuna, and the image
        90th percentile, share above 2 x the WT median and field density per
        image, each y ~ hyp * hp with animal as a random intercept. With 12 animals
        the Wald intervals of a mixed model are too narrow (no small-sample
        correction), so they are reported beside the animal-level ones, not
        instead of them.
hyp is 1 for Hyp, hp is 1 for the high phosphate diet; the coefficient of
hyp:hp is the interaction, the diet effect in Hyp minus the diet effect in WT.

In DEV mode the held-out images are left out (docs/HOLDOUT.md).

Usage (from the repo root):
    python src/animal_stats.py run       # tables and results/summary/STATISTICS.md
    python src/animal_stats.py selftest
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lacunae  # noqa: E402
import pols  # noqa: E402

UM = config.PIXEL_SIZE_UM_ACQUIRED
STATISTICS_MD = config.SUMMARY_ROOT / "STATISTICS.md"
PER_IMAGE_CSV = config.SUMMARY_ROOT / "per_image.csv"
PER_ANIMAL_CSV = config.SUMMARY_ROOT / "per_animal.csv"
PER_GROUP_CSV = config.SUMMARY_ROOT / "per_group.csv"
MODELS_CSV = config.SUMMARY_ROOT / "statistics_models.csv"
CELLS = [("WT", "RD"), ("WT", "HP"), ("Hyp", "RD"), ("Hyp", "HP")]
GROUP_OF = {("WT", "RD"): "WT", ("WT", "HP"): "WT_HP", ("Hyp", "RD"): "Hyp_RD", ("Hyp", "HP"): "Hyp_HP"}
# The share of the 90th percentile and the two size lines: as in src/pols.py.
P90 = 90

# Every measure: (column, plain name, unit). The order of every table.
MEASURES = [
    ("area_um2_median", "median lacunar area", "um2"),
    ("area_um2_p90", "90th percentile of lacunar area", "um2"),
    ("share_above_2x_WT_median", "share of lacunae above 2 x the WT median", "share"),
    ("share_above_100_um2", "share of lacunae above 100 um2", "share"),
    ("pol_area_per_analysed_area", "POL area per analysed area", "share"),
    ("roots_per_lacuna", "roots per lacuna", "count"),
    ("ring_length_30_um", "ring length within 3.9 um per lacuna", "um"),
    ("field_length_density_um_per_um2", "field length density", "um per um2"),
    ("width_median_um", "median canalicular width", "um"),
]


# Tables

def interior_network_rows(q: dict) -> list[dict]:
    """The per-lacuna network values of the interior lacunae of one
    quantification json, as the summary of src/quantification.py averages
    them (ordinary class, not touching the frame)."""
    return [r for r in q["lacunae"] if not r["on_border"] and r.get("lacuna_class", "ordinary") == "ordinary"]


def collect() -> tuple[list, list]:
    """(lacuna rows, image rows): every measured lacuna and every image the
    mode lets through, with its animal, genotype and diet."""
    import pandas as pd  # noqa: PLC0415

    animals = pols.animal_map()
    wt_median = pols.wt_median_um2()
    lac_rows, img_rows = [], []
    for group in config.GROUPS:
        root = config.RESULTS_ROOT / group
        for path in pols.image_files(group):
            label = lacunae.image_label(path)
            meta = animals[(group, label)]
            q = pols.quant_json(root, label)
            rows = pols.with_raw(pols.lacuna_records(root, label), wt_median)
            analysed, excluded = pols.field_areas_um2(root, label)
            base = {"group": group, "image": label, "animal": meta["animal"], "genotype": meta["genotype"],
                    "diet": meta["diet"]}
            net = {r["lacuna_id"]: r for r in interior_network_rows(q)}
            for r in rows:
                if r["flag"]:
                    continue
                n = net.get(r["id"], {})
                lac_rows.append({**base, "lacuna": r["id"], "area_um2": r["_area"], "ratio": r["_ratio"],
                                 "roots": n.get("roots_count"),
                                 "ring_length_30_um": None if n.get("ring_length_r30_px") is None
                                 else n["ring_length_r30_px"] * UM})
            field = q["field"]
            nets = list(net.values())
            img_rows.append({
                **base, **pols.stats(rows), **pols.pol_metrics(rows, analysed, excluded),
                "roots_per_lacuna": float(np.mean([r["roots_count"] for r in nets])) if nets else None,
                "ring_length_30_um": float(np.mean([r["ring_length_r30_px"] for r in nets])) * UM if nets else None,
                "field_length_density_um_per_um2": None if field["canalicular_length_density_per_px"] is None
                else field["canalicular_length_density_per_px"] / UM,
                "skeleton_length_um": field["total_skeleton_length_px"] * UM,
                "network_area_um2": field["analysed_area_px2"] * UM ** 2,
                "width_median_um": None if q["width"]["width_median_px"] is None
                else q["width"]["width_median_px"] * UM,
                "_rows": rows, "_analysed": analysed, "_excluded": excluded, "_nets": nets,
            })
    return pd.DataFrame(lac_rows), img_rows


def pooled(img_rows: list[dict], key: str) -> list[dict]:
    """Per animal (key "animal") or per group (key "group"): every measured
    lacuna of its images pooled, areas and lengths summed, the width the
    median of the image medians."""
    out = {}
    for r in img_rows:
        e = out.setdefault(r[key], {"genotype": r["genotype"], "diet": r["diet"], "group": r["group"],
                                    "animal": r["animal"] if key == "animal" else "", "images": [],
                                    "rows": [], "analysed": 0.0, "excluded": 0.0, "nets": [],
                                    "skeleton": 0.0, "network_area": 0.0, "widths": []})
        e["images"].append(r["image"])
        e["rows"] += r["_rows"]
        e["analysed"] += r["_analysed"]
        e["excluded"] += r["_excluded"]
        e["nets"] += r["_nets"]
        e["skeleton"] += r["skeleton_length_um"]
        e["network_area"] += r["network_area_um2"]
        if r["width_median_um"] is not None:
            e["widths"].append(r["width_median_um"])
    rows = []
    for name, e in out.items():
        nets = e["nets"]
        rows.append({
            key: name, **({"animal": e["animal"]} if key == "animal" else {}),
            "group": e["group"], "genotype": e["genotype"], "diet": e["diet"], "n_images": len(e["images"]),
            "images": " ".join(e["images"]), **pols.stats(e["rows"]),
            **pols.pol_metrics(e["rows"], e["analysed"], e["excluded"]),
            "roots_per_lacuna": float(np.mean([r["roots_count"] for r in nets])) if nets else None,
            "ring_length_30_um": float(np.mean([r["ring_length_r30_px"] for r in nets])) * UM if nets else None,
            "field_length_density_um_per_um2": e["skeleton"] / e["network_area"] if e["network_area"] else None,
            "width_median_um": float(np.median(e["widths"])) if e["widths"] else None,
        })
    return rows


def tables() -> dict:
    """Every table as a pandas DataFrame: lacunae, images, animals, groups."""
    import pandas as pd  # noqa: PLC0415

    lac, img_rows = collect()
    images = pd.DataFrame([{k: v for k, v in r.items() if not k.startswith("_")} for r in img_rows])
    animals = pd.DataFrame(pooled(img_rows, "animal"))
    animal_meta = pols.animal_map()
    confirmed = {a["animal"]: a["confirmed"] for a in animal_meta.values()}
    animals.insert(5, "confirmed", animals["animal"].map(confirmed))
    groups = pd.DataFrame(pooled(img_rows, "group"))
    order = {g: i for i, g in enumerate(config.GROUPS)}
    for df in (images, animals, groups):
        df.sort_values(by=["group"], key=lambda s: s.map(order), kind="stable", inplace=True)
        df.reset_index(drop=True, inplace=True)
    return {"lacunae": lac, "images": images, "animals": animals, "groups": groups}


# Models

def design(df):
    """df with hyp (1 for Hyp) and hp (1 for the high phosphate diet)."""
    df = df.copy()
    df["hyp"] = (df["genotype"] == "Hyp").astype(int)
    df["hp"] = (df["diet"] == "HP").astype(int)
    return df


def ols_fit(df, column: str) -> dict:
    """y ~ hyp * hp on one value per animal, t intervals."""
    import statsmodels.formula.api as smf  # noqa: PLC0415
    from scipy import stats as st  # noqa: PLC0415

    d = design(df[["genotype", "diet", column]].dropna()).rename(columns={column: "y"})
    d["y"] = d["y"].astype(float)
    cells = d.groupby(["genotype", "diet"]).size()
    n_per_cell = {f"{g} {di}": int(cells.get((g, di), 0)) for g, di in CELLS}
    out = {"model": "animal level, least squares", "n_units": len(d), "n_per_cell": n_per_cell}
    df_resid = len(d) - 4
    if min(n_per_cell.values()) < 1 or df_resid < 1:
        return {**out, "fit": False, "why": "too few animals: a cell is empty or no degree of freedom is left"}
    fit = smf.ols("y ~ hyp * hp", data=d).fit()
    ci = fit.conf_int()
    se = float(fit.bse["hyp:hp"])
    detectable = (st.t.ppf(0.975, df_resid) + st.t.ppf(0.80, df_resid)) * se
    return {**out, "fit": True, "df": df_resid, "estimate": float(fit.params["hyp:hp"]),
            "ci_low": float(ci.loc["hyp:hp", 0]), "ci_high": float(ci.loc["hyp:hp", 1]),
            "p": float(fit.pvalues["hyp:hp"]), "se": se, "detectable_80": float(detectable),
            "hyp_on_RD": float(fit.params["hyp"]), "hp_in_WT": float(fit.params["hp"]),
            "wt_rd_mean": float(fit.params["Intercept"])}


def mixed_fit(df, column: str, nested_image: bool) -> dict:
    """y ~ hyp * hp, animal as a random intercept, and the image inside the
    animal when nested_image. Wald intervals."""
    import statsmodels.formula.api as smf  # noqa: PLC0415

    d = design(df[["genotype", "diet", "animal", "image", column]].dropna()).rename(columns={column: "y"})
    d["y"] = d["y"].astype(float)
    level = "per lacuna" if "lacuna" in df.columns else "per image"
    out = {"model": f"mixed, {level}, animal random" + (", image inside animal" if nested_image else ""),
           "n_units": len(d), "n_animals": int(d["animal"].nunique())}
    model = smf.mixedlm("y ~ hyp * hp", d, groups=d["animal"],
                        vc_formula={"image": "0 + C(image)"} if nested_image else None)
    # The optimisers in turn: one can raise (lbfgs, "Singular matrix") where
    # another fits.
    fit, errors = None, []
    for method in ("bfgs", "lbfgs", "powell", "nm"):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                fit = model.fit(reml=True, method=method)
                break
            except Exception as exc:  # noqa: BLE001 (recorded, not hidden)
                errors.append(f"{method}: {type(exc).__name__}: {exc}")
    if fit is None:
        return {**out, "fit": False, "why": "; ".join(errors)}
    out["optimiser"] = method
    ci = fit.conf_int()
    notes = sorted({str(w.message).split("\n")[0][:80] for w in caught})
    # A Hessian that is not positive definite leaves the standard errors, and
    # so the interval, without meaning; a singular random effect means the
    # animal variance came out as zero, so the rows are treated as independent.
    unreliable = any("not positive definite" in n for n in notes) or not np.isfinite(float(fit.bse["hyp:hp"]))
    singular = any("singular" in n or "boundary" in n for n in notes)
    return {**out, "fit": True, "converged": bool(fit.converged), "reliable": not unreliable,
            "animal_variance_zero": singular, "estimate": float(fit.params["hyp:hp"]),
            "ci_low": float(ci.loc["hyp:hp", 0]), "ci_high": float(ci.loc["hyp:hp", 1]),
            "p": float(fit.pvalues["hyp:hp"]), "se": float(fit.bse["hyp:hp"]),
            "hyp_on_RD": float(fit.params["hyp"]), "hp_in_WT": float(fit.params["hp"]),
            "wt_rd_mean": float(fit.params["Intercept"]), "warnings": "; ".join(notes)}


def models(t: dict) -> list[dict]:
    """Every fit, one dict each, with the measure it is of."""
    out = []
    for column, name, unit in MEASURES:
        out.append({"measure": name, "column": column, "unit": unit, **ols_fit(t["animals"], column)})
    # Animal as the only random effect, as the brief asks: with the image
    # nested inside the animal as well, the per-lacuna fits on the development
    # images were degenerate (the Hessian not positive definite).
    for column, name, unit, frame, nested in [
            ("area_um2", "lacunar area", "um2", "lacunae", False),
            ("roots", "roots per lacuna", "count", "lacunae", False),
            ("ring_length_30_um", "ring length within 3.9 um per lacuna", "um", "lacunae", False),
            ("area_um2_p90", "90th percentile of lacunar area", "um2", "images", False),
            ("share_above_2x_WT_median", "share of lacunae above 2 x the WT median", "share", "images", False),
            ("field_length_density_um_per_um2", "field length density", "um per um2", "images", False)]:
        out.append({"measure": name, "column": column, "unit": unit, **mixed_fit(t[frame], column, nested)})
    return out


# Report

def fmt(value, unit: str = "") -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "none"
    if unit == "share":
        return f"{100 * value:.1f}%"
    if abs(value) >= 100:
        return f"{value:.0f}"
    if abs(value) >= 1:
        return f"{value:.2f}"
    return f"{value:.3g}"


def fmt_effect(value, unit: str) -> str:
    """An effect: a share in percentage points, anything else in its unit."""
    if value is None:
        return "none"
    if unit == "share":
        return f"{100 * value:+.1f} points"
    return f"{fmt(value)} {unit}".replace("  ", " ") if value < 0 else f"+{fmt(value)} {unit}"


def plain_verdict(m: dict) -> str:
    """Whether the data say anything about the interaction, in words."""
    if not m.get("fit"):
        return f"not fitted: {m.get('why')}"
    excludes_zero = m["ci_low"] > 0 or m["ci_high"] < 0
    if m["model"].startswith("animal"):
        base = ("the interval excludes zero" if excludes_zero else "the interval includes zero: no interaction "
                "can be claimed")
        lo, hi = min(m["n_per_cell"].values()), max(m["n_per_cell"].values())
        per_cell = f"{lo}" if lo == hi else f"{lo} to {hi}"
        size = abs(m["detectable_80"])
        size_text = f"{100 * size:.1f} points" if m["unit"] == "share" else f"{fmt(size)} {m['unit']}"
        return (f"{base}; with {per_cell} animals per group ({m['df']} degrees of freedom) only an interaction "
                f"of about {size_text} or more, either way, would be found 4 times in 5")
    if not m.get("reliable", True):
        return "the fit is unreliable (its standard errors have no meaning); read the animal-level line"
    zero = "; the animal variance came out as zero, so the rows count as independent" \
        if m.get("animal_variance_zero") else ""
    return ("the interval excludes zero" if excludes_zero else "the interval includes zero") + zero + \
        f"; {m['n_animals']} animals, so this interval is too narrow; read the animal-level line"


def write_markdown(t: dict, fits: list[dict], path: Path) -> None:
    animals, groups = t["animals"], t["groups"]
    mode = config.HOLDOUT_MODE
    lines = [
        "# Statistics: genotype by diet (pre-validation)",
        "",
        "**Pre-validation.** Every number comes from the pipeline's own detection, not yet checked against",
        "manual counts. The animal mapping (`data/animals.csv`) is from the file names and is **not confirmed**",
        "(column `confirmed` = no); animal 701 carries no diet label in its file names and is HP only because",
        "its images are in `data/Hyp_HP`. To be checked with Dr. Murshed.",
        "",
        f"Mode: {mode}. " + ("The held-out images are left out (DEV mode), so some animals have fewer images "
                             "here than in the data set." if mode == "DEV"
                             else "Every image, the held-out ones included."),
        "",
        "Design: 2 x 2, genotype (WT, Hyp) by diet (regular RD, high phosphate HP), the animal is the unit.",
        "The question is the **interaction**: is the diet effect in Hyp different from the diet effect in WT?",
        "The interaction below is (Hyp HP minus Hyp RD) minus (WT HP minus WT RD).",
        "",
        "## Animals per group",
        "",
        "| group | animals | images |",
        "| - | - | - |",
    ]
    for g in config.GROUPS:
        part = animals[animals["group"] == g]
        lines.append(f"| {g} | {len(part)} ({', '.join(part['animal'])}) | {int(part['n_images'].sum())} |")
    lines += ["", "## Per group (every measured lacuna of the group pooled)", "",
              "| group | n lacunae | median (um2) | 90th percentile (um2) | above 2 x WT median | "
              "POL area per analysed area | roots per lacuna | field length density (um per um2) |",
              "| - | - | - | - | - | - | - | - |"]
    for _i, r in groups.iterrows():
        lines.append(f"| {r['group']} | {r['n']} | {fmt(r['area_um2_median'])} | {fmt(r['area_um2_p90'])} | "
                     f"{fmt(r['share_above_2x_WT_median'], 'share')} | {fmt(r['pol_area_per_analysed_area'], 'share')} | "
                     f"{fmt(r['roots_per_lacuna'])} | {fmt(r['field_length_density_um_per_um2'])} |")
    lines += ["", "## Per animal", "",
              "| animal | group | images | n lacunae | median (um2) | 90th percentile (um2) | above 2 x WT median | "
              "POL area per analysed area | roots per lacuna | ring length 3.9 um (um) | field length density | "
              "width median (um) |",
              "| - | - | - | - | - | - | - | - | - | - | - | - |"]
    for _i, r in animals.iterrows():
        lines.append(f"| {r['animal']} | {r['group']} | {r['n_images']} | {r['n']} | {fmt(r['area_um2_median'])} | "
                     f"{fmt(r['area_um2_p90'])} | {fmt(r['share_above_2x_WT_median'], 'share')} | "
                     f"{fmt(r['pol_area_per_analysed_area'], 'share')} | {fmt(r['roots_per_lacuna'])} | "
                     f"{fmt(r['ring_length_30_um'])} | {fmt(r['field_length_density_um_per_um2'])} | "
                     f"{fmt(r['width_median_um'])} |")
    lines += ["", "## The interaction, animal level (the primary analysis)", "",
              "One value per animal, least squares, y ~ genotype x diet; 95% t interval. Effects in the measure's",
              "unit (shares in percentage points).", "",
              "| measure | WT RD mean | Hyp on RD | HP in WT | interaction | 95% interval | p | what it says |",
              "| - | - | - | - | - | - | - | - |"]
    for m in fits:
        if not m["model"].startswith("animal"):
            continue
        if not m.get("fit"):
            lines.append(f"| {m['measure']} | | | | | | | {plain_verdict(m)} |")
            continue
        u = m["unit"]
        lines.append(f"| {m['measure']} ({u}) | {fmt(m['wt_rd_mean'], u)} | {fmt_effect(m['hyp_on_RD'], u)} | "
                     f"{fmt_effect(m['hp_in_WT'], u)} | **{fmt_effect(m['estimate'], u)}** | "
                     f"{fmt_effect(m['ci_low'], u)} to {fmt_effect(m['ci_high'], u)} | {m['p']:.2f} | "
                     f"{plain_verdict(m)} |")
    lines += ["", "## The interaction, mixed models", "",
              "Every lacuna or every image, with animal as a random intercept, statsmodels MixedLM, REML, 95%",
              "Wald interval. With so few animals these intervals do not correct for the small number of groups",
              "and are too narrow. (With the image nested inside the animal as well, the per-lacuna fits were",
              "degenerate, so the image is not modelled.)", "",
              "| measure | model | units | interaction | 95% interval | p | fit usable | what it says |",
              "| - | - | - | - | - | - | - | - |"]
    for m in fits:
        if m["model"].startswith("animal"):
            continue
        if not m.get("fit"):
            lines.append(f"| {m['measure']} | {m['model']} | {m['n_units']} | | | | | {plain_verdict(m)} |")
            continue
        u = m["unit"]
        lines.append(f"| {m['measure']} ({u}) | {m['model']} | {m['n_units']} | **{fmt_effect(m['estimate'], u)}** | "
                     f"{fmt_effect(m['ci_low'], u)} to {fmt_effect(m['ci_high'], u)} | {m['p']:.2f} | "
                     f"{'yes' if m['converged'] and m['reliable'] else 'no'} | {plain_verdict(m)} |")
    lines += ["", "## In plain words", "",
              "- There are 3 animals per group. That is enough to estimate each effect and its interval, and",
              "  not enough for a test to find anything but a large interaction: the last column says how large.",
              "- An interval that includes zero means the data cannot tell whether the diet acts differently in",
              "  Hyp than in WT; it does not show that it acts the same.",
              "- The per-lacuna and per-image mixed models use many more rows, but the rows inside one animal are",
              "  not independent, so their narrow intervals overstate the certainty.",
              "- Everything rests on the AI-reviewed, not manually validated, lacuna detection and on the",
              "  unconfirmed animal mapping.", "",
              "Made by `python src/animal_stats.py run`; the numbers are also in `per_animal.csv`, `per_group.csv`,",
              "`per_image.csv` and `statistics_models.csv` beside this file, and in `results/SUMMARY.xlsx`.", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def models_frame(fits: list[dict]):
    import pandas as pd  # noqa: PLC0415

    rows = []
    for m in fits:
        rows.append({k: (str(v) if isinstance(v, dict) else v) for k, v in m.items()})
        rows[-1]["what_it_says"] = plain_verdict(m)
    return pd.DataFrame(rows)


def run() -> int:
    t = tables()
    fits = models(t)
    t["images"].to_csv(PER_IMAGE_CSV, index=False, lineterminator="\n")
    t["animals"].to_csv(PER_ANIMAL_CSV, index=False, lineterminator="\n")
    t["groups"].to_csv(PER_GROUP_CSV, index=False, lineterminator="\n")
    models_frame(fits).to_csv(MODELS_CSV, index=False, lineterminator="\n")
    write_markdown(t, fits, STATISTICS_MD)
    print(f"{len(t['images'])} images, {len(t['animals'])} animals -> {STATISTICS_MD}")
    for m in fits:
        if m.get("fit"):
            print(f"  {m['model'][:28]:<28} {m['measure'][:40]:<40} interaction {m['estimate']:+.4g} "
                  f"[{m['ci_low']:+.4g}, {m['ci_high']:+.4g}] p={m['p']:.2f}")
        else:
            print(f"  {m['model'][:28]:<28} {m['measure'][:40]:<40} not fitted: {m['why']}")
    return 0


def selftest() -> int:
    """Synthetic animals with a known interaction: the least squares fit
    returns it, and the mixed model returns it within its interval."""
    import pandas as pd  # noqa: PLC0415

    rng = np.random.default_rng(20261106)
    rows, lac = [], []
    for g, d in CELLS:
        for k in range(3):
            animal = f"{g}{d}{k}"
            true = 40 + (10 if g == "Hyp" else 0) + (5 if d == "HP" else 0) + (20 if (g, d) == ("Hyp", "HP") else 0)
            rows.append({"genotype": g, "diet": d, "animal": animal, "y": true + rng.normal(0, 1)})
            for i in range(2):
                for _j in range(30):
                    lac.append({"genotype": g, "diet": d, "animal": animal, "image": f"{animal}_{i}",
                                "y": true + rng.normal(0, 3)})
    checks = []
    o = ols_fit(pd.DataFrame(rows), "y")
    checks.append(("least squares finds the interaction of 20", abs(o["estimate"] - 20) < 3 and o["df"] == 8))
    checks.append(("its interval holds 20 and excludes 0", o["ci_low"] < 20 < o["ci_high"] and o["ci_low"] > 0))
    m = mixed_fit(pd.DataFrame(lac), "y", nested_image=True)
    checks.append(("the mixed model finds it too", m["fit"] and m["ci_low"] < 20 < m["ci_high"]))
    short = pd.DataFrame([r for r in rows if not (r["genotype"] == "Hyp" and r["diet"] == "HP")])
    checks.append(("an empty cell is reported, not fitted", not ols_fit(short, "y")["fit"]))
    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    ok = all(ok for _n, ok in checks)
    print(f"\n{'PASS' if ok else 'FAIL'}: {sum(ok for _n, ok in checks)} of {len(checks)} checks.")
    return 0 if ok else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Per-animal summaries and the genotype by diet statistics.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("run", help="Tables in results/summary/ and results/summary/STATISTICS.md.")
    sub.add_parser("selftest", help="Checks on synthetic animals with a known interaction.")
    args = parser.parse_args()
    sys.exit(selftest() if args.command == "selftest" else run())


if __name__ == "__main__":
    main()
