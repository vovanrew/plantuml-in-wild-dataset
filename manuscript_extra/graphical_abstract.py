#!/usr/bin/env python3
"""
Graphical abstract for UML-in-the-Wild (MDPI Data submission).

Renders a 180 x 90 mm horizontal banner (~4250 x 2125 px @ 600 DPI),
well above MDPI's 1100 x 560 px minimum.
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Rectangle

OUTPUT_PATH = Path(__file__).parent / "graphical_abstract.png"

# Canvas
W_MM, H_MM = 180, 90
DPI = 600

# Colors (phase tints aligned with manuscript Fig. 2)
PHASE1_BG = "#F0F4FA"
PHASE2_BG = "#F0FAF2"
PHASE3_BG = "#FDF6ED"
ACCENT = "#1A3A5C"
TEXT_MAIN = "#2C2C2C"
TEXT_MUTED = "#5C5C5C"
REPO_DARK = "#5A7AA8"
REPO_LIGHT = "#8FA8C8"
BOX_BORDER = "#888888"

# 9 type-pill colors (one per UML type)
PILL_COLORS = [
    "#D9534F",  # class
    "#5BC0DE",  # sequence
    "#5CB85C",  # activity
    "#F0AD4E",  # component
    "#9B59B6",  # use case
    "#1ABC9C",  # state
    "#F1C40F",  # object
    "#A0522D",  # deployment
    "#E91E63",  # timing
]

# Repo glyph positions: (x, y, shade) where shade 0 = dark, 1 = light
REPO_GLYPHS = [
    (7, 72, 0), (17, 76, 1), (28, 72, 0), (39, 77, 1), (47, 71, 0),
    (12, 64, 1), (23, 67, 0), (34, 63, 1), (44, 64, 0),
    (8, 55, 1), (19, 57, 0), (30, 53, 1), (41, 56, 0),
    (14, 47, 0), (25, 45, 1), (36, 45, 0), (46, 47, 1),
    (9, 38, 1), (20, 40, 0), (31, 36, 1), (42, 38, 0),
]


def setup_axes():
    mpl.rcParams["font.family"] = "Arial"
    mpl.rcParams["font.size"] = 9

    fig, ax = plt.subplots(figsize=(W_MM / 25.4, H_MM / 25.4))
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_xlim(0, W_MM)
    ax.set_ylim(0, H_MM)
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


def draw_phase_backgrounds(ax):
    ax.add_patch(Rectangle((0, 0), 55, H_MM, facecolor=PHASE1_BG, edgecolor="none", zorder=0))
    ax.add_patch(Rectangle((55, 0), 60, H_MM, facecolor=PHASE2_BG, edgecolor="none", zorder=0))
    ax.add_patch(Rectangle((115, 0), 65, H_MM, facecolor=PHASE3_BG, edgecolor="none", zorder=0))


def draw_column_1(ax):
    """Open-source repositories: header, scattered repo glyphs, caption."""
    ax.text(27.5, 84, "OPEN-SOURCE REPOSITORIES",
            ha="center", va="center", fontsize=9, fontweight="bold", color=TEXT_MAIN)

    for x, y, shade in REPO_GLYPHS:
        color = REPO_DARK if shade == 0 else REPO_LIGHT
        ax.add_patch(FancyBboxPatch(
            (x - 1.8, y - 1), 3.6, 2,
            boxstyle="round,pad=0,rounding_size=0.4",
            facecolor=color, edgecolor=color, linewidth=0.3,
        ))

    ax.text(27.5, 22, "504,451 candidate files",
            ha="center", va="center", fontsize=8.5, color=TEXT_MAIN)
    ax.text(27.5, 16, "via World of Code",
            ha="center", va="center", fontsize=7.5, color=TEXT_MUTED)


def draw_pipeline_box(ax, cx, cy, title, sub1, sub2):
    w, h = 44, 13
    ax.add_patch(FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0,rounding_size=0.7",
        facecolor="white", edgecolor=BOX_BORDER, linewidth=0.5,
    ))
    ax.text(cx, cy + 3.5, title, ha="center", va="center",
            fontsize=9.5, fontweight="bold", color=TEXT_MAIN)
    ax.text(cx, cy - 0.3, sub1, ha="center", va="center", fontsize=7, color=TEXT_MAIN)
    ax.text(cx, cy - 3.2, sub2, ha="center", va="center", fontsize=7, color=TEXT_MAIN)


def draw_pipeline_arrow(ax, x, y_top, y_bottom):
    ax.add_patch(FancyArrowPatch(
        (x, y_top), (x, y_bottom),
        arrowstyle="-|>", mutation_scale=8,
        color="#8C8C8C", linewidth=0.9,
    ))


def draw_column_2(ax):
    """Pipeline: header + 3 process boxes + connecting arrows."""
    ax.text(85, 84, "PIPELINE",
            ha="center", va="center", fontsize=9, fontweight="bold", color=TEXT_MAIN)

    draw_pipeline_box(ax, 85, 70, "Extract",
                      "extension match", "& content validation")
    draw_pipeline_box(ax, 85, 50, "Compile",
                      "PlantUML 1.2025.9", "→ PNG render")
    draw_pipeline_box(ax, 85, 30, "Classify",
                      "Claude Haiku 4.5", "LLM (9 types)")

    draw_pipeline_arrow(ax, 85, 70 - 13 / 2, 50 + 13 / 2)
    draw_pipeline_arrow(ax, 85, 50 - 13 / 2, 30 + 13 / 2)


def draw_column_3(ax):
    """Headline: hero count, type pills, DOI."""
    ax.text(147.5, 84, "UML DIAGRAMS",
            ha="center", va="center", fontsize=9, fontweight="bold", color=TEXT_MAIN)

    # Hero number
    ax.text(147.5, 64, "143,427",
            ha="center", va="center", fontsize=30, fontweight="bold", color=ACCENT)
    ax.text(147.5, 53, "UML diagrams",
            ha="center", va="center", fontsize=12, color=TEXT_MAIN)
    ax.text(147.5, 45,
            "PlantUML source · PNG image\n· structured metadata",
            ha="center", va="center", fontsize=7, color=TEXT_MUTED, linespacing=1.4)

    # 9 type pills
    for i, color in enumerate(PILL_COLORS):
        cx = 123.5 + i * 6
        ax.add_patch(Circle((cx, 32), 1.75,
                            facecolor=color, edgecolor="#444444", linewidth=0.3))

    ax.text(147.5, 24, "9 standard UML diagram types",
            ha="center", va="center", fontsize=7.5, color=TEXT_MUTED)
    ax.text(147.5, 16,
            "Open access · CC-BY-4.0\nDOI: 10.5281/zenodo.18952372",
            ha="center", va="center", fontsize=7, color=TEXT_MUTED, linespacing=1.5)


def main():
    fig, ax = setup_axes()
    draw_phase_backgrounds(ax)
    draw_column_1(ax)
    draw_column_2(ax)
    draw_column_3(ax)

    fig.savefig(OUTPUT_PATH, dpi=DPI, facecolor="white", edgecolor="none")
    plt.close(fig)

    px_w = int(W_MM / 25.4 * DPI)
    px_h = int(H_MM / 25.4 * DPI)
    print(f"Saved: {OUTPUT_PATH}")
    print(f"  Canvas: {W_MM} x {H_MM} mm @ {DPI} DPI = {px_w} x {px_h} px")
    print(f"  MDPI minimum: 1100 x 560 px ({'OK' if px_w >= 1100 and px_h >= 560 else 'FAIL'})")


if __name__ == "__main__":
    main()
