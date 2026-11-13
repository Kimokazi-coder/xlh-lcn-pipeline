"""Build results/slides/lcn_update.pptx, the lab update deck (5 slides)."""
import csv
import json
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent / "results"
OUT = ROOT / "slides" / "lcn_update.pptx"
UM_PER_PX = 0.13
SEED = 42
GROUPS = ["WT", "WT_HP", "Hyp_RD", "Hyp_HP"]
ACCENT = RGBColor(0x0B, 0x72, 0x85)
INK = RGBColor(0x22, 0x22, 0x22)
GREY = RGBColor(0x66, 0x66, 0x66)
FONT = "Calibri"
SW, SH = 13.333, 7.5


def images(group):
    return sorted(p.name for p in (ROOT / group).iterdir()
                  if p.is_dir() and (p / "non_ai_run").is_dir())


def pick(group, offset=0):
    return random.Random(SEED + offset).choice(images(group))


def crop_picture(path, dest):
    """Crop a pols_outlines picture to the image panel, dropping the legend and title."""
    im = Image.open(path).convert("RGB")
    dark = np.asarray(im).astype(int).sum(axis=2) < 600
    cols = dark.mean(axis=0) > 0.3
    rows = dark.mean(axis=1) > 0.3
    x0 = int(np.argmax(cols))
    x1 = x0
    while x1 < len(cols) and cols[x1]:
        x1 += 1
    y0 = int(np.argmax(rows))
    y1 = len(rows) - int(np.argmax(rows[::-1]))
    im.crop((x0, y0, x1, y1)).save(dest)
    return dest


def compare_figure(csv_path, dest):
    """Large-type version of the compare_numbers table, same csv, fewer rows."""
    keep = {"n_lacunae": "Lacunae found",
            "area_um2_median": "Median area (µm²)",
            "share_above_2x_WT_median": "Enlarged (>2x WT)",
            "roots_per_lacuna": "Canaliculi per lacuna",
            "field_length_density_um_per_um2": "Length (µm/µm²)"}
    rows = [r for r in csv.DictReader(open(csv_path, encoding="utf8"))
            if r["column"] in keep]
    im = Image.new("RGB", (1250, 780), "white")
    d = ImageDraw.Draw(im)

    def font(n, bold=False):
        return ImageFont.truetype("calibrib.ttf" if bold else "calibri.ttf", n)

    xs = (20, 680, 940)
    for x, h in zip(xs[1:], ("Method", "AI judges")):
        d.text((x, 30), h, font=font(60, True), fill=(11, 114, 133))
    y = 160
    for r in rows:
        d.text((xs[0], y), keep[r["column"]], font=font(60), fill=(34, 34, 34))
        for x, k in zip(xs[1:], ("non_ai_run", "ai_judges")):
            v = float(r[k])
            if "share" in r["column"]:
                t = f"{v * 100:.0f}%"
            elif r["column"] == "n_lacunae":
                t = f"{v:.0f}"
            else:
                t = f"{v:.2f}" if v < 1 else f"{v:.1f}"
            d.text((x, y), t, font=font(64, True), fill=(34, 34, 34))
        y += 120
    im.save(dest)
    return dest


def text(slide, x, y, w, h, s, size, color=INK, bold=False, align=PP_ALIGN.LEFT):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, m, 0)
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = s
    r.font.size, r.font.bold, r.font.name = Pt(size), bold, FONT
    r.font.color.rgb = color
    return tb


def fit(slide, path, x, y, w, h):
    iw, ih = Image.open(path).size
    s = min(w / iw, h / ih)
    pw, ph = iw * s, ih * s
    slide.shapes.add_picture(str(path), Inches(x + (w - pw) / 2),
                             Inches(y + (h - ph) / 2), Inches(pw), Inches(ph))


def base(prs, title):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    text(slide, 0.5, 0.3, SW - 1, 0.7, title, 34, INK, bold=True)
    bar = slide.shapes.add_shape(1, Inches(0.5), Inches(1.05), Inches(1.2), Inches(0.06))
    bar.fill.solid()
    bar.fill.fore_color.rgb = ACCENT
    bar.line.fill.background()
    return slide


def numbers(group, image):
    d = ROOT / group / image / "non_ai_run"
    q = json.load(open(d / "4_quantification" / f"{image}_quantification.json"))
    n = q["lacuna_count"]
    area_um2 = q["field"]["analysed_area_px2"] * UM_PER_PX ** 2
    return {
        "n": n,
        "density": n / area_um2 * 1000,
        "length": q["summary"]["ring_length_r30_px"]["mean"] * UM_PER_PX,
        "roots": q["summary"]["roots_count"]["mean"],
    }


def group_slide(prs, group):
    image = pick(group)
    base_dir = ROOT / group / image
    summ = base_dir / "non_ai_run" / "summary"
    panels = [
        ("Lacunae", summ / f"{image}_lacunae_outlines.png"),
        ("Canaliculi", summ / f"{image}_canaliculi_verification.png"),
        ("Comparison of numbers", compare_figure(
            base_dir / "comparison" / f"{image}_compare_numbers.csv",
            OUT.parent / f"{group}_{image}_compare_numbers_large.png")),
    ]
    slide = base(prs, f"{group}: {image}")
    gap, margin = 0.25, 0.5
    w = (SW - 2 * margin - 2 * gap) / 3
    for i, (label, path) in enumerate(panels):
        x = margin + i * (w + gap)
        fit(slide, path, x, 1.5, w, 4.3)
        text(slide, x, 5.9, w, 0.4, label, 18, GREY, align=PP_ALIGN.CENTER)
    v = numbers(group, image)
    cap = (f"{v['n']} lacunae   |   {v['density']:.2f} per 1000 µm²   |   "
           f"{v['length']:.0f} µm canalicular length per lacuna   |   "
           f"{v['roots']:.1f} canaliculi per lacuna")
    text(slide, margin, 6.55, SW - 2 * margin, 0.5, cap, 18, ACCENT, bold=True,
         align=PP_ALIGN.CENTER)
    slide.notes_slide.notes_text_frame.text = (
        f"This is one {group} image, {image}, shown three ways. Left, the lacunae "
        "the pipeline found; middle, the canaliculi it traced from each lacuna; "
        "right, the key numbers of the method run next to the run with AI judges. "
        "Nothing is validated against manual counts yet.")
    return group, image, v


def pol_slide(prs):
    slide = base(prs, "POLs: enlarged lacunar space")
    picks = [("Hyp_RD", pick("Hyp_RD")), ("Hyp_HP", pick("Hyp_HP"))]
    w, gap, margin = 4.0, 0.3, 0.5
    rows = {}
    for g in ("Hyp_RD", "Hyp_HP"):
        for r in csv.DictReader(open(ROOT / g / "3_pols" / "pols_all_images.csv")):
            rows[(g, r["image"])] = r
    for i, (g, image) in enumerate(picks):
        x = margin + i * (w + gap)
        path = crop_picture(
            ROOT / g / image / "non_ai_run" / "3_pols" / f"{image}_pols_outlines.png",
            OUT.parent / f"{g}_{image}_pols_outlines_crop.png")
        fit(slide, path, x, 1.4, w, 3.9)
        r = rows[(g, image)]
        text(slide, x, 5.4, w, 0.4, f"{g}: {image}", 16, GREY, align=PP_ALIGN.CENTER)
        text(slide, x, 5.8, w, 0.4,
             f"{float(r['share_above_2x_WT_median']) * 100:.0f}% enlarged, "
             f"POL area {float(r['pol_area_per_analysed_area']) * 100:.1f}%",
             16, ACCENT, bold=True, align=PP_ALIGN.CENTER)
    x = margin + 2 * (w + gap)
    tw = SW - margin - x
    text(slide, x, 1.4, tw, 0.4, "What counts as a POL", 20, ACCENT, bold=True)
    text(slide, x, 1.85, tw, 1.2,
         "An enlarged, dye-filled lacunar space: a lacuna above 2x the WT "
         "median area (36.8 µm²).", 18)
    text(slide, x, 3.25, tw, 0.4, "Measured", 20, ACCENT, bold=True)
    text(slide, x, 3.7, tw, 1.7,
         "POL area per analysed area\nShare of lacunae above 2x WT\n"
         "Lacuna area vs WT median", 18)
    text(slide, x, 5.6, tw, 0.4, "Unvalidated, no ground truth yet", 16, GREY)
    text(slide, margin, 6.6, SW - 2 * margin, 0.5,
         "Question for the group: how do we define the POL boundary?", 22, INK,
         bold=True, align=PP_ALIGN.CENTER)
    slide.notes_slide.notes_text_frame.text = (
        "Yellow outlines are lacunae above twice the WT median area, our working "
        "candidate POLs; green are normal size and grey touch the frame. The "
        "footprint is the lacuna outline itself, so the boundary is only as good "
        "as that definition. This is the open question I want input on.")
    return picks


def main():
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(SW), Inches(SH)
    for g in GROUPS:
        print(group_slide(prs, g))
    print(pol_slide(prs))
    prs.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    main()
