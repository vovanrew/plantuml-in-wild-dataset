#!/usr/bin/env python3
"""
Figure 5: Classification Confusion Matrix

Creates an publication-quality heatmap showing LLM classification accuracy
across 9 UML diagram types (270 samples, 30 per type).
"""

import json
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent / "fig5_confusion_matrix.png"

# Publication figure specifications
DPI = 600
FIGURE_WIDTH_MM = 180
FIGURE_WIDTH_INCHES = FIGURE_WIDTH_MM / 25.4
FIGURE_HEIGHT_INCHES = FIGURE_WIDTH_INCHES * 0.85
FONT_FAMILY = 'Arial'
MIN_FONT_SIZE = 8

# Colors
CMAP_COLOR = '#4A90A4'


def load_data(data_path):
    with open(data_path, 'r') as f:
        data = json.load(f)
    return data['classification']


def build_matrix(classification):
    types = classification['types']
    n = len(types)
    matrix = np.zeros((n, n), dtype=int)

    for i, classified in enumerate(types):
        row = classification['confusion_matrix'].get(classified, {})
        for j, actual in enumerate(types):
            matrix[i, j] = row.get(actual, 0)

    return matrix, types


def create_chart(matrix, types, overall_accuracy):
    plt.rcParams.update({
        'font.family': FONT_FAMILY,
        'font.size': MIN_FONT_SIZE,
    })

    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH_INCHES, FIGURE_HEIGHT_INCHES))

    # Custom colormap: white → theme blue
    cmap = mcolors.LinearSegmentedColormap.from_list(
        'custom', ['#FFFFFF', CMAP_COLOR], N=256)

    im = ax.imshow(matrix, cmap=cmap, aspect='equal', vmin=0, vmax=30)

    # Capitalize labels
    labels = [t.capitalize() for t in types]
    ax.set_xticks(range(len(types)))
    ax.set_yticks(range(len(types)))
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    ax.set_yticklabels(labels, fontsize=8)

    ax.set_xlabel('Expert Label', fontsize=10)
    ax.set_ylabel('LLM Label', fontsize=10)

    # Annotate cells
    for i in range(len(types)):
        for j in range(len(types)):
            val = matrix[i, j]
            if val == 0:
                continue
            # White text on dark cells, black on light
            color = 'white' if val > 15 else 'black'
            fontweight = 'bold' if i == j else 'normal'
            ax.text(j, i, str(val), ha='center', va='center',
                    fontsize=9, color=color, fontweight=fontweight)

    # Colorbar
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('Count', fontsize=9)
    cbar.ax.tick_params(labelsize=8)

    # Overall accuracy annotation
    ax.annotate(f'Overall: {overall_accuracy:.1%}',
                xy=(0.99, 0.01), xycoords='axes fraction',
                ha='right', va='bottom', fontsize=9,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                         edgecolor='gray', alpha=0.9))

    plt.tight_layout()
    return fig


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <validation_summary.json>", file=sys.stderr)
        sys.exit(1)

    classification = load_data(sys.argv[1])
    matrix, types = build_matrix(classification)

    print("Confusion matrix:")
    for i, t in enumerate(types):
        print(f"  {t:>12}: {matrix[i].tolist()}")

    fig = create_chart(matrix, types, classification['overall_accuracy'])

    print(f"Saving to {OUTPUT_PATH} at {DPI} DPI...")
    fig.savefig(OUTPUT_PATH, dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)

    if OUTPUT_PATH.exists():
        size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
        print(f"Output file size: {size_mb:.2f} MB")


if __name__ == "__main__":
    main()
