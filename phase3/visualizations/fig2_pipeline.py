#!/usr/bin/env python3
"""
Figure 2: Pipeline diagram.

Replaces the TikZ pipeline figure from manuscript.tex with a matplotlib
rendering that can be embedded directly in the Data in Brief .docx submission.
Matches the project's existing figure style: 600 DPI, Arial, 180mm width.
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUTPUT_PATH = Path(__file__).parent / "fig2_pipeline.png"

DPI = 600
FIGURE_WIDTH_MM = 180
FIGURE_WIDTH_INCHES = FIGURE_WIDTH_MM / 25.4
FIGURE_HEIGHT_INCHES = 7.5

PHASE_1_FILL = "#E8F0F8"
PHASE_2_FILL = "#E8F5E8"
PHASE_3_FILL = "#FFF1E0"

BOX_EDGE = "#444444"
BOX_FILL = "#FFFFFF"
RESULT_FILL = "#EDEDED"

ARROW_COLOR = "#444444"
EXCL_ARROW_COLOR = "#888888"
EXCL_TEXT_COLOR = "#555555"
PHASE_LABEL_COLOR = "#666666"
COUNT_TEXT_COLOR = "#222222"

BOX_W = 6.0
BOX_H = 0.85
RESULT_H = 0.95


def draw_box(ax, x, y, label, fill=BOX_FILL, bold=False):
    box = FancyBboxPatch(
        (x - BOX_W / 2, y - BOX_H / 2),
        BOX_W,
        BOX_H,
        boxstyle="round,pad=0.04,rounding_size=0.12",
        linewidth=1.0,
        edgecolor=BOX_EDGE,
        facecolor=fill,
    )
    ax.add_patch(box)
    ax.text(
        x,
        y,
        label,
        ha="center",
        va="center",
        fontsize=9,
        fontweight=("bold" if bold else "normal"),
    )


def draw_arrow(ax, x1, y1, x2, y2, count=None):
    arrow = FancyArrowPatch(
        (x1, y1),
        (x2, y2),
        arrowstyle="-|>",
        mutation_scale=12,
        linewidth=1.2,
        color=ARROW_COLOR,
        shrinkA=2,
        shrinkB=2,
    )
    ax.add_patch(arrow)
    if count is not None:
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        ax.text(
            mid_x + 0.18,
            mid_y,
            count,
            fontsize=8.5,
            color=COUNT_TEXT_COLOR,
            ha="left",
            va="center",
            bbox=dict(facecolor="white", edgecolor="none", pad=1.2),
        )


def draw_exclusion(ax, x1, y, label):
    x2 = x1 + 2.6
    arrow = FancyArrowPatch(
        (x1, y),
        (x2, y),
        arrowstyle="-|>",
        mutation_scale=8,
        linewidth=0.8,
        linestyle=(0, (4, 2)),
        color=EXCL_ARROW_COLOR,
        shrinkA=2,
        shrinkB=2,
    )
    ax.add_patch(arrow)
    ax.text(
        x2 + 0.12,
        y,
        label,
        fontsize=8.5,
        color=EXCL_TEXT_COLOR,
        ha="left",
        va="center",
    )


def draw_phase_bg(ax, y_top, y_bot, color, label):
    pad_x = 0.55
    pad_y_top = 0.95
    pad_y_bot = 0.40
    rect = FancyBboxPatch(
        (-BOX_W / 2 - pad_x, y_bot - pad_y_bot),
        BOX_W + 2 * pad_x,
        (y_top - y_bot) + pad_y_top + pad_y_bot,
        boxstyle="round,pad=0.0,rounding_size=0.20",
        linewidth=0,
        facecolor=color,
        zorder=0,
    )
    ax.add_patch(rect)
    ax.text(
        -BOX_W / 2 - pad_x + 0.18,
        y_top + pad_y_top - 0.18,
        label,
        ha="left",
        va="top",
        fontsize=9.5,
        color=PHASE_LABEL_COLOR,
        fontweight="bold",
    )


def main():
    mpl.rcParams["font.family"] = "Arial"
    mpl.rcParams["font.size"] = 9

    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH_INCHES, FIGURE_HEIGHT_INCHES))

    boxes = [
        ("src",       "WoC version V lb2fFull basemaps (128 shards)", 9.4, PHASE_1_FILL),
        ("grep",      "Extension-based identification and deduplication", 8.2, BOX_FILL),
        ("valid",     "Content validation", 7.0, BOX_FILL),
        ("split",     "Multi-diagram splitting", 5.5, BOX_FILL),
        ("compile",   "PlantUML v1.2025.9 compilation", 4.3, BOX_FILL),
        ("classify",  "LLM classification and filtering", 2.8, BOX_FILL),
        ("extract",   "Element and connection extraction", 1.6, BOX_FILL),
        ("final",     "143,427 UML diagrams", 0.4, RESULT_FILL),
    ]

    draw_phase_bg(ax, y_top=9.4, y_bot=7.0, color=PHASE_1_FILL, label="Phase 1: Data Extraction")
    draw_phase_bg(ax, y_top=5.5, y_bot=4.3, color=PHASE_2_FILL, label="Phase 2: Compilation")
    draw_phase_bg(ax, y_top=2.8, y_bot=0.4, color=PHASE_3_FILL, label="Phase 3: Classification & Analysis")

    positions = {}
    for key, label, y, fill in boxes:
        positions[key] = (0.0, y)
        bold = key == "final"
        draw_box(ax, 0.0, y, label, fill=fill, bold=bold)

    flow = [
        ("src",      "grep",     None),
        ("grep",     "valid",    "367,550"),
        ("valid",    "split",    "202,106"),
        ("split",    "compile",  "209,122"),
        ("compile",  "classify", "163,946"),
        ("classify", "extract",  "143,427"),
        ("extract",  "final",    None),
    ]
    for a, b, count in flow:
        ax_x, ax_y = positions[a]
        bx_x, bx_y = positions[b]
        draw_arrow(ax, ax_x, ax_y - BOX_H / 2, bx_x, bx_y + BOX_H / 2, count=count)

    exclusions = [
        ("valid",    "165,444 invalid"),
        ("split",    "+7,016 from splits"),
        ("compile",  "45,176 errors"),
        ("classify", "20,519 non-UML"),
    ]
    for key, label in exclusions:
        _, y = positions[key]
        draw_exclusion(ax, x1=BOX_W / 2, y=y, label=label)

    ax.set_xlim(-BOX_W / 2 - 0.8, BOX_W / 2 + 3.8)
    ax.set_ylim(-0.2, 9.95)
    ax.set_aspect("equal", adjustable="datalim")
    ax.axis("off")

    plt.tight_layout(pad=0.1)
    fig.savefig(
        OUTPUT_PATH,
        dpi=DPI,
        format="png",
        bbox_inches="tight",
        facecolor="white",
        edgecolor="none",
    )
    plt.close(fig)
    print(f"Saved {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
