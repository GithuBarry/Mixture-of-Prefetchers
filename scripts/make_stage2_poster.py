#!/usr/bin/env python3
"""Build a portrait poster PDF from the final MoP report artifacts."""

from __future__ import annotations

import textwrap
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/pdf/mop_openevolve_poster.pdf"
FIG = ROOT / "report/figures"
ICON = ROOT / "report/assets/material_symbols"
ICON_CACHE = ROOT / "output/pdf/icon_cache"

PAGE_W = 24 * inch
PAGE_H = 36 * inch

BLACK = colors.HexColor("#000000")
WHITE = colors.HexColor("#ffffff")
LIGHTGREY = colors.HexColor("#d9d9d9")
ORANGE = colors.HexColor("#fe6100")
PINK = colors.HexColor("#dc267f")
PURPLE = colors.HexColor("#785ef0")
BLUE = colors.HexColor("#648fff")
DARKBLUE = colors.HexColor("#3f6fd1")


def draw_wrapped(c: canvas.Canvas, text: str, x: float, y: float, width: float, size: float, leading: float, color=BLACK) -> float:
    c.setFillColor(color)
    c.setFont("Helvetica", size)
    avg_char = size * 0.52
    chars = max(20, int(width / avg_char))
    for paragraph in text.split("\n"):
        lines = textwrap.wrap(paragraph, chars) or [""]
        for line in lines:
            c.drawString(x, y, line)
            y -= leading
    return y


def _rgb(color: colors.Color) -> tuple[int, int, int]:
    return (int(color.red * 255), int(color.green * 255), int(color.blue * 255))


def icon_variant(name: str, color: colors.Color) -> Path:
    ICON_CACHE.mkdir(parents=True, exist_ok=True)
    rgb = _rgb(color)
    out = ICON_CACHE / f"{name}_{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}.png"
    if out.exists():
        return out
    src = Image.open(ICON / f"{name}.png").convert("RGBA")
    alpha = src.getchannel("A")
    img = Image.new("RGBA", src.size, (*rgb, 0))
    img.putalpha(alpha)
    img.save(out)
    return out


def draw_icon(c: canvas.Canvas, name: str, x: float, y: float, size: float, color=DARKBLUE) -> None:
    icon_path = icon_variant(name, color)
    c.drawImage(ImageReader(str(icon_path)), x, y, width=size, height=size, mask="auto")


def draw_inline_icon_text(
    c: canvas.Canvas,
    icon: str,
    title: str,
    body: str,
    x: float,
    y: float,
    width: float,
    color: colors.Color,
    title_size: float = 15,
    body_size: float = 12.5,
) -> float:
    draw_icon(c, icon, x, y - 19, 24, color=color)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", title_size)
    c.drawString(x + 34, y, title)
    return draw_wrapped(c, body, x + 34, y - 19, width - 34, body_size, body_size + 4) - 4


def draw_section_title(c: canvas.Canvas, title: str, x: float, y: float, width: float, icon: str, color=PINK) -> float:
    draw_icon(c, icon, x, y - 23, 31, color=color)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(x + 43, y - 1, title)
    c.setStrokeColor(color)
    c.setLineWidth(3)
    c.line(x + 43, y - 10, x + min(width, 318), y - 10)
    return y - 34


def draw_bullets(c: canvas.Canvas, items: list[str], icons: list[str], x: float, y: float, width: float, size: float = 14) -> float:
    c.setFont("Helvetica", size)
    palette = [DARKBLUE, PINK, PURPLE, ORANGE, BLUE]
    for idx, (item, icon) in enumerate(zip(items, icons, strict=True)):
        draw_icon(c, icon, x, y - 5, 22, color=palette[idx % len(palette)])
        y = draw_wrapped(c, item, x + 34, y, width - 34, size, size + 4)
        y -= 7
    return y


def draw_image(c: canvas.Canvas, path: Path, x: float, y: float, width: float, height: float) -> None:
    c.drawImage(str(path), x, y, width=width, height=height, preserveAspectRatio=True, anchor="c", mask="auto")


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT), pagesize=(PAGE_W, PAGE_H))
    c.setTitle("Mixture-of-Prefetchers OpenEvolve Poster")
    c.setAuthor("Mixture-of-Prefetchers project")

    margin = 0.75 * inch
    gap = 0.45 * inch
    col_w = (PAGE_W - 2 * margin - gap) / 2
    left = margin
    right = margin + col_w + gap

    # Header
    c.setFillColor(WHITE)
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    c.setFillColor(colors.HexColor("#f7f9ff"))
    c.rect(0, PAGE_H - 1.85 * inch, PAGE_W, 1.85 * inch, stroke=0, fill=1)
    draw_icon(c, "rocket_launch", margin, PAGE_H - 1.25 * inch, 44, color=PINK)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 46)
    c.drawString(margin + 62, PAGE_H - 0.95 * inch, "Mixture-of-Prefetchers")
    c.setFont("Helvetica", 20)
    c.drawString(margin + 62, PAGE_H - 1.35 * inch, "A compact L2-cache router tuned by OpenEvolve")
    c.setStrokeColor(PINK)
    c.setLineWidth(7)
    c.line(margin, PAGE_H - 1.58 * inch, PAGE_W - margin, PAGE_H - 1.58 * inch)

    # Purpose strip.
    purpose_y = PAGE_H - 2.35 * inch
    purpose_gap = 0.22 * inch
    purpose_w = (PAGE_W - 2 * margin - 3 * purpose_gap) / 4
    draw_inline_icon_text(c, "compare_arrows", "Trace behavior shifts", "The stronger L2C prefetcher changes by workload, so one fixed expert leaves performance unused.", margin, purpose_y, purpose_w, DARKBLUE)
    draw_inline_icon_text(c, "route", "Route cheaply", "MoP observes short epoch counters, then chooses how much budget each expert receives.", margin + purpose_w + purpose_gap, purpose_y, purpose_w, PINK)
    draw_inline_icon_text(c, "tune", "Let search tune policy", "OpenEvolve adjusts compact routing constants while the simulator and evaluation protocol stay fixed.", margin + 2 * (purpose_w + purpose_gap), purpose_y, purpose_w, PURPLE)
    draw_inline_icon_text(c, "fact_check", "Show the evidence", "Every plot uses prefetcher off as 1.000x and labels the best expert as a reference line.", margin + 3 * (purpose_w + purpose_gap), purpose_y, purpose_w, ORANGE)

    y_left = PAGE_H - 4.65 * inch
    y_left = draw_section_title(c, "What We Built On Athena", left, y_left, col_w, "memory")
    y_left = draw_inline_icon_text(
        c,
        "account_tree",
        "Contribution over Athena",
        "Athena provides the simulator, cache hierarchy, L2C prefetchers, and existing comparison baselines. "
        "Our work adds a two-prefetcher routing layer, epoch-level expert counters, fixed train and heldout trace protocol, "
        "an OpenEvolve evaluator, and reproducible ledgers and plots.",
        left,
        y_left,
        col_w,
        DARKBLUE,
        15,
        13,
    )
    y_left -= 14
    y_left = draw_bullets(
        c,
        [
            "Expert pair: Athena MLOP + SPP+PPF at L2C.",
            "MoP-V1: manual one-epoch probe router.",
            "MoP-V2: OpenEvolve-tuned MoP-V1 with evolved budget, score weights, and close-score tie margin.",
            "OpenEvolve could change only a compact policy dictionary. Trace split, baselines, parser, metrics, expert pair, cache level, and simulator internals stayed fixed.",
        ],
        ["hub", "route", "tune", "rule"],
        left,
        y_left,
        col_w,
    )

    y_right = PAGE_H - 4.65 * inch
    y_right = draw_section_title(c, "Evaluation Protocol", right, y_right, col_w, "dataset", color=PURPLE)
    y_right = draw_bullets(
        c,
        [
            "All performance numbers use disabled prefetching as 1.000x.",
            "Best expert is computed per trace as max(MLOP, SPP+PPF), then geomeaned.",
            "Official split: 17 training traces and 7 heldout traces.",
            "OpenEvolve search used training traces only. Heldout traces were evaluated after policy selection.",
            "The simulator holds the retired-instruction window fixed, so IPC movement is effectively cycle movement.",
        ],
        ["speed", "track_changes", "dataset", "shield", "cycle"],
        right,
        y_right,
        col_w,
    )

    # Figure row 1
    fig1_y = PAGE_H - 15.85 * inch
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(BLACK)
    draw_icon(c, "bar_chart", left, fig1_y + 6.60 * inch, 28, color=PINK)
    c.setFillColor(BLACK)
    c.drawString(left + 38, fig1_y + 6.78 * inch, "Before and after OpenEvolve")
    draw_image(c, FIG / "stage2_pre_post_geomean.png", left, fig1_y + 0.55 * inch, col_w, 5.95 * inch)
    draw_wrapped(
        c,
        "Caption: bars compare disabled prefetching, each single expert, the manual MoP-V1 router, the OpenEvolve-tuned MoP-V2 router, and the best expert reference on the same heldout and training-validation surfaces.",
        left,
        fig1_y + 0.30 * inch,
        col_w,
        11,
        14,
        colors.HexColor("#333333"),
    )
    draw_icon(c, "monitoring", right, fig1_y + 6.60 * inch, 28, color=PURPLE)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(right + 38, fig1_y + 6.78 * inch, "Search trajectory by model")
    draw_image(c, FIG / "stage2_scale_model_comparison.png", right, fig1_y + 0.55 * inch, col_w, 5.95 * inch)
    draw_wrapped(
        c,
        "Caption: faint points are generated candidates. Solid traces show best-so-far weighted evaluator score, which combines speedup, percent of best expert, weaker-expert coverage, and tail-loss penalties.",
        right,
        fig1_y + 0.30 * inch,
        col_w,
        11,
        14,
        colors.HexColor("#333333"),
    )

    # Figure row 2 spans the page.
    fig2_y = 5.90 * inch
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 18)
    draw_icon(c, "analytics", left, fig2_y + 11.88 * inch, 28, color=DARKBLUE)
    c.setFillColor(BLACK)
    c.drawString(left + 38, fig2_y + 12.05 * inch, "Heldout trace profile")
    draw_wrapped(
        c,
        "Caption: each row is a heldout trace. Bars use disabled prefetching as 1.000x. MLOP and SPP+PPF sit above the MoP bars so the reader can see when the two experts disagree and where the router lands.",
        left + 38,
        fig2_y + 11.78 * inch,
        PAGE_W - 2 * margin - 38,
        11,
        14,
        colors.HexColor("#333333"),
    )
    draw_image(c, FIG / "stage2_heldout_trace_profile.png", left, fig2_y, PAGE_W - 2 * margin, 11.15 * inch)

    # Bottom synthesis.
    bottom_y = 2.1 * inch
    c.setStrokeColor(LIGHTGREY)
    c.setLineWidth(1.2)
    c.line(margin, bottom_y + 1.2 * inch, PAGE_W - margin, bottom_y + 1.2 * inch)

    c.setFont("Helvetica-Bold", 17)
    c.setFillColor(BLACK)
    draw_icon(c, "insights", left, bottom_y + 0.62 * inch, 26, color=PINK)
    c.setFillColor(BLACK)
    c.drawString(left + 34, bottom_y + 0.85 * inch, "Takeaway")
    draw_wrapped(
        c,
        "For MLOP + SPP+PPF, MoP-V2 improves over the manual MoP-V1 router on training-split validation, "
        "stays positive on heldout by the disabled-prefetching baseline, and keeps the best expert as a separate oracle-style reference.",
        left + 34,
        bottom_y + 0.55 * inch,
        col_w - 34,
        13,
        17,
    )

    c.setFont("Helvetica-Bold", 17)
    draw_icon(c, "fact_check", right, bottom_y + 0.62 * inch, 26, color=PURPLE)
    c.setFillColor(BLACK)
    c.drawString(right + 34, bottom_y + 0.85 * inch, "Auditability")
    draw_wrapped(
        c,
        "Candidate ledgers record 374 attempts, including 306 valid scored rows and 68 fail-closed rows. "
        "The detailed naming map, raw result paths, CI policy, and rebuild commands live in report/writing_logistics.md.",
        right + 34,
        bottom_y + 0.55 * inch,
        col_w - 34,
        13,
        17,
    )

    c.setFillColor(BLACK)
    c.setFont("Helvetica", 10)
    c.drawString(margin, 0.55 * inch, "Source: report/stage2_final_report.md. Figures rebuild from raw simulator summaries. Portrait poster generated by scripts/make_stage2_poster.py.")

    c.showPage()
    c.save()
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
