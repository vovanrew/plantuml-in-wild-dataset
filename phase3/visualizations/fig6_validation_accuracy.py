#!/usr/bin/env python3
"""
Figure 6: Per-Type Validation Accuracy

Creates an publication-quality grouped bar chart showing manual validation
accuracy for classification, element counts, and connection counts
across UML diagram types.

Timing diagrams are included for classification only (element/connection
extraction is not supported for timing diagrams).
"""

import json
import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent / "fig6_validation_accuracy.png"

# Publication figure specifications
DPI = 600
FIGURE_WIDTH_MM = 180
FIGURE_WIDTH_INCHES = FIGURE_WIDTH_MM / 25.4
FIGURE_HEIGHT_INCHES = FIGURE_WIDTH_INCHES * 0.55
FONT_FAMILY = 'Arial'
MIN_FONT_SIZE = 8

# Colors — maximally distinct, colorblind-safe
COLOR_CLASSIFICATION = '#4A90A4'  # teal (dataset theme)
COLOR_ELEMENTS = '#E07B39'       # orange
COLOR_CONNECTIONS = '#8B5CA0'    # purple


def load_data(data_path):
    with open(data_path, 'r') as f:
        return json.load(f)


def create_chart(data):
    plt.rcParams.update({
        'font.family': FONT_FAMILY,
        'font.size': MIN_FONT_SIZE,
    })

    cls = data['classification']
    elem = data['elements']
    conn = data['connections']

    # All 9 types for classification; 8 (no timing) for elements/connections
    all_types = cls['types']
    elem_types = list(elem['per_type'].keys())

    cls_acc = np.array([cls['per_type'][t]['accuracy'] * 100 for t in all_types])
    elem_acc = np.array([elem['per_type'][t]['accuracy'] * 100 if t in elem['per_type'] else np.nan
                         for t in all_types])
    conn_acc = np.array([conn['per_type'][t]['accuracy'] * 100 if t in conn['per_type'] else np.nan
                         for t in all_types])

    labels = [t.capitalize() for t in all_types]
    x = np.arange(len(all_types))
    bar_width = 0.25

    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH_INCHES, FIGURE_HEIGHT_INCHES))

    # Draw all three groups as full arrays — NaN entries produce no bar
    ax.bar(x - bar_width, cls_acc, bar_width,
           color=COLOR_CLASSIFICATION, label='Classification', edgecolor='white', linewidth=0.5)
    ax.bar(x, elem_acc, bar_width,
           color=COLOR_ELEMENTS, label='Elements', edgecolor='white', linewidth=0.5)
    ax.bar(x + bar_width, conn_acc, bar_width,
           color=COLOR_CONNECTIONS, label='Connections', edgecolor='white', linewidth=0.5)

    # Axes
    ax.set_ylabel('Accuracy (%)', fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=8)
    ax.set_ylim(65, 105)
    ax.set_yticks([70, 80, 90, 100])

    # Reference line at 100%
    ax.axhline(y=100, color='gray', linewidth=0.5, linestyle='--', zorder=0)

    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Legend
    ax.legend(loc='lower left', fontsize=8, framealpha=0.9,
              edgecolor='gray')

    # Overall accuracy annotations
    ax.annotate(
        f"Overall: Class. {cls['overall_accuracy']:.1%}, "
        f"Elem. {elem['overall_accuracy']:.1%}, "
        f"Conn. {conn['overall_accuracy']:.1%}",
        xy=(0.99, 0.02), xycoords='axes fraction',
        ha='right', va='bottom', fontsize=8,
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                 edgecolor='gray', alpha=0.9))

    plt.tight_layout()
    return fig


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <validation_summary.json>", file=sys.stderr)
        sys.exit(1)

    data = load_data(sys.argv[1])

    print("Per-type accuracy:")
    for t in data['classification']['types']:
        cls_a = data['classification']['per_type'][t]['accuracy']
        elem_a = data['elements']['per_type'].get(t, {}).get('accuracy')
        conn_a = data['connections']['per_type'].get(t, {}).get('accuracy')
        elem_s = f"{elem_a:.1%}" if elem_a is not None else "n/a"
        conn_s = f"{conn_a:.1%}" if conn_a is not None else "n/a"
        print(f"  {t:>12}: cls={cls_a:.1%}  elem={elem_s}  conn={conn_s}")

    fig = create_chart(data)

    print(f"Saving to {OUTPUT_PATH} at {DPI} DPI...")
    fig.savefig(OUTPUT_PATH, dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)

    if OUTPUT_PATH.exists():
        size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
        print(f"Output file size: {size_mb:.2f} MB")


if __name__ == "__main__":
    main()
