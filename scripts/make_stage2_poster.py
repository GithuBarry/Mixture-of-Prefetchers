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
    title_size: float = 22,
    body_size: float = 20,
) -> float:
    draw_icon(c, icon, x, y - 22, 28, color=color)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", title_size)
    c.drawString(x + 34, y, title)
    return draw_wrapped(c, body, x + 34, y - 23, width - 34, body_size, body_size + 5) - 4


def draw_section_title(c: canvas.Canvas, title: str, x: float, y: float, width: float, icon: str, color=PINK) -> float:
    draw_icon(c, icon, x, y - 19, 32, color=color)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 32)
    c.drawString(x + 43, y - 1, title)
    c.setStrokeColor(color)
    c.setLineWidth(3)
    c.line(x + 43, y - 10, x + min(width, 318), y - 10)
    return y - 52


def draw_bullets(c: canvas.Canvas, items: list[str], icons: list[str], x: float, y: float, width: float, size: float = 24) -> float:
    c.setFont("Helvetica", size)
    palette = [DARKBLUE, PINK, PURPLE, ORANGE, BLUE]
    for idx, (item, icon) in enumerate(zip(items, icons, strict=True)):
        draw_icon(c, icon, x, y - 9, 30, color=palette[idx % len(palette)])
        y = draw_wrapped(c, item, x + 44, y, width - 44, size, size + 7)
        y -= 8
    return y


def draw_image(c: canvas.Canvas, path: Path, x: float, y: float, width: float, height: float) -> None:
    c.drawImage(str(path), x, y, width=width, height=height, preserveAspectRatio=True, anchor="c", mask="auto")


def draw_mini_table(c: canvas.Canvas, title: str, rows: list[tuple[str, str]], x: float, y: float, width: float, icon: str, color: colors.Color) -> float:
    draw_icon(c, icon, x, y - 25, 32, color=color)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(x + 44, y, title)
    y -= 34
    y -= 8
    label_w = width * 0.28
    for label, value in rows:
        c.setFillColor(color)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(x + 44, y, label)
        y = draw_wrapped(c, value, x + 44 + label_w, y, width - 44 - label_w, 22, 27, BLACK)
        y -= 8
    return y


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
    c.rect(0, PAGE_H - 2.05 * inch, PAGE_W, 2.05 * inch, stroke=0, fill=1)
    draw_icon(c, "rocket_launch", margin, PAGE_H - 1.38 * inch, 54, color=PINK)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 58)
    c.drawString(margin + 76, PAGE_H - 0.92 * inch, "Mixture-of-Prefetchers")
    c.setFont("Helvetica", 28)
    c.drawString(margin + 76, PAGE_H - 1.43 * inch, "A compact L2-cache router tuned by OpenEvolve")
    c.setStrokeColor(PINK)
    c.setLineWidth(7)
    c.line(margin, PAGE_H - 1.78 * inch, PAGE_W - margin, PAGE_H - 1.78 * inch)

    # Purpose strip.
    purpose_y = PAGE_H - 2.55 * inch
    purpose_gap = 0.22 * inch
    purpose_w = (PAGE_W - 2 * margin - 3 * purpose_gap) / 4
    draw_inline_icon_text(c, "compare_arrows", "Trace behavior shifts", "Best prefetcher changes by workload.", margin, purpose_y, purpose_w, DARKBLUE, 22, 19)
    draw_inline_icon_text(c, "route", "Route cheaply", "Observe one 500K-instruction epoch, choose the next.", margin + purpose_w + purpose_gap, purpose_y, purpose_w, PINK, 22, 19)
    draw_inline_icon_text(c, "tune", "Tune policy", "OpenEvolve edits compact routing constants.", margin + 2 * (purpose_w + purpose_gap), purpose_y, purpose_w, PURPLE, 22, 19)
    draw_inline_icon_text(c, "fact_check", "Use one baseline", "Prefetcher off is 1.000x in every plot.", margin + 3 * (purpose_w + purpose_gap), purpose_y, purpose_w, ORANGE, 22, 19)

    y_left = PAGE_H - 5.25 * inch
    y_left = draw_section_title(c, "What We Built On Athena", left, y_left, col_w, "memory")
    y_left = draw_inline_icon_text(
        c,
        "account_tree",
        "Contribution over Athena",
        "Athena provides the simulator and L2C prefetchers. We add routing, epoch counters, fixed splits, OpenEvolve search, and rebuildable plots.",
        left,
        y_left,
        col_w,
        DARKBLUE,
        23,
        21,
    )
    y_left -= 14
    y_left = draw_bullets(
        c,
        [
            "Experts: MLOP + SPP+PPF at L2C.",
            "MoP-V1: one-epoch probe router.",
            "MoP-V2: OpenEvolve-tuned router.",
        ],
        ["hub", "route", "tune"],
        left,
        y_left,
        col_w,
    )

    y_right = PAGE_H - 5.25 * inch
    y_right = draw_section_title(c, "Evaluation Protocol", right, y_right, col_w, "dataset", color=PURPLE)
    y_right = draw_bullets(
        c,
        [
            "Prefetcher off is the 1.000x baseline.",
            "Best expert = max(MLOP, SPP+PPF).",
            "Split: 17 training, 7 heldout.",
            "Epoch: 500K retired instructions.",
            "IPC tracks cycles under fixed instructions.",
        ],
        ["speed", "track_changes", "dataset", "shield", "cycle"],
        right,
        y_right,
        col_w,
    )

    table_y = PAGE_H - 11.1 * inch
    draw_mini_table(
        c,
        "Two Athena Experts",
        [
            ("MLOP", "Learns useful address offsets across multiple lookahead distances. Better on 4 of 13 validation traces."),
            ("SPP+PPF", "Tracks page signatures and delta paths, then filters candidates with a perceptron. Better on 9 of 13."),
        ],
        left,
        table_y,
        col_w,
        "hub",
        DARKBLUE,
    )
    draw_mini_table(
        c,
        "Trace Sets",
        [
            ("Official", "24 traces: SPEC, PARSEC, Ligra, secret_compute."),
            ("Training", "17 for search. Final validation used 13 available traces."),
            ("Heldout", "7 frozen traces after policy selection."),
            ("Window", "Validation 500K + 1M. Heldout 20M + 50M."),
        ],
        right,
        table_y,
        col_w,
        "table_chart",
        PURPLE,
    )

    # Figure row 1
    fig1_y = PAGE_H - 23.5 * inch
    c.setFont("Helvetica-Bold", 26)
    c.setFillColor(BLACK)
    draw_icon(c, "bar_chart", left, fig1_y + 6.60 * inch, 28, color=PINK)
    c.setFillColor(BLACK)
    c.drawString(left + 42, fig1_y + 6.80 * inch, "Before and after OpenEvolve")
    draw_image(c, FIG / "stage2_pre_post_geomean.png", left, fig1_y + 0.65 * inch, col_w, 5.6 * inch)
    draw_wrapped(
        c,
        "Caption: bars compare disabled prefetching, each single expert, the manual MoP-V1 router, the OpenEvolve-tuned MoP-V2 router, and the best expert reference on the same heldout and training-validation results.",
        left,
        fig1_y + 0.28 * inch,
        col_w,
        16,
        20,
        colors.HexColor("#333333"),
    )
    draw_icon(c, "monitoring", right, fig1_y + 6.60 * inch, 28, color=PURPLE)
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(right + 42, fig1_y + 6.80 * inch, "Search trajectory by model")
    draw_image(c, FIG / "stage2_scale_model_comparison.png", right, fig1_y + 0.65 * inch, col_w, 5.6 * inch)
    draw_wrapped(
        c,
        "Caption: faint points are generated candidates. Solid traces show best IPC seen so far. Dashed lines show the score-selected incumbent IPC.",
        right,
        fig1_y + 0.28 * inch,
        col_w,
        16,
        20,
        colors.HexColor("#333333"),
    )

    # Figure row 2 spans the page.
    fig2_y = 1.0 * inch
    c.setFillColor(BLACK)
    c.setFont("Helvetica-Bold", 26)
    draw_icon(c, "analytics", left, fig2_y + 10.68 * inch, 28, color=DARKBLUE)
    c.setFillColor(BLACK)
    c.drawString(left + 42, fig2_y + 10.85 * inch, "Heldout trace profile")
    draw_wrapped(
        c,
        "Caption: each row is a heldout trace. Bars use disabled prefetching as 1.000x. MLOP and SPP+PPF sit above the MoP bars so the reader can see when the two experts disagree and where the router lands.",
        left + 38,
        fig2_y + 10.50 * inch,
        PAGE_W - 2 * margin - 38,
        16,
        20,
        colors.HexColor("#333333"),
    )
    draw_image(c, FIG / "stage2_heldout_trace_profile.png", left, fig2_y + 0.45 * inch, PAGE_W - 2 * margin, 8.85 * inch)

    c.setFillColor(BLACK)
    c.setFont("Helvetica", 10)
    c.drawString(margin, 0.55 * inch, "Source: final report Markdown. Figures rebuild from raw simulator summaries. Portrait poster generated by scripts/make_stage2_poster.py.")

    c.showPage()
    c.save()
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
