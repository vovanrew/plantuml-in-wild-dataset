#!/usr/bin/env python3
"""
Figure 4: Connection Type Distribution

Creates an MDPI-compliant horizontal bar chart showing the top 15
connection types used in PlantUML diagrams.
"""

import json
import sys
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from pathlib import Path

# MDPI specifications
DPI = 600
FIGURE_WIDTH_MM = 180
FIGURE_WIDTH_INCHES = FIGURE_WIDTH_MM / 25.4
FIGURE_HEIGHT_INCHES = FIGURE_WIDTH_INCHES * 0.7  # Taller for horizontal bars
FONT_FAMILY = 'Arial'
MIN_FONT_SIZE = 8
BAR_COLOR = '#4A90A4'

# Configuration
TOP_N = 15  # Show top 15 connection types

# Paths
OUTPUT_PATH = Path(__file__).parent / 'fig4_connection_categories.png'


def load_data(data_path):
    """Load connection type statistics from JSON."""
    with open(data_path, 'r') as f:
        data = json.load(f)

    by_type = data['statistics']['connections_type_totals']
    total_connections = sum(by_type.values())

    return by_type, total_connections


def create_chart(by_type, total_connections):
    """Create MDPI-compliant horizontal bar chart."""
    # Set up matplotlib with MDPI specs
    plt.rcParams.update({
        'font.family': FONT_FAMILY,
        'font.size': MIN_FONT_SIZE,
        'axes.labelsize': 10,
        'axes.titlesize': 10,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
    })

    # Sort and get top N
    sorted_types = sorted(by_type.items(), key=lambda x: x[1], reverse=True)
    top_types = sorted_types[:TOP_N]

    # Reverse for horizontal bar chart (top item at top)
    top_types = top_types[::-1]

    labels = [t[0].title() for t in top_types]  # Capitalize
    counts = [t[1] for t in top_types]

    # Create figure
    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH_INCHES, FIGURE_HEIGHT_INCHES))

    # Create horizontal bars
    y_pos = range(len(labels))
    bars = ax.barh(y_pos, counts, color=BAR_COLOR, edgecolor='white', linewidth=0.5)

    # Add labels at end of bars (count + percentage)
    for i, (bar, count) in enumerate(zip(bars, counts)):
        percentage = (count / total_connections) * 100
        label = f'{count:,} ({percentage:.1f}%)'

        # Position label inside or outside bar based on length
        if count > max(counts) * 0.3:
            ax.annotate(label,
                        xy=(count - max(counts) * 0.02, bar.get_y() + bar.get_height() / 2),
                        ha='right', va='center',
                        fontsize=8, color='white', fontweight='bold')
        else:
            ax.annotate(label,
                        xy=(count + max(counts) * 0.01, bar.get_y() + bar.get_height() / 2),
                        ha='left', va='center',
                        fontsize=8)

    # Configure axes
    ax.set_xlabel('Number of Connections', fontsize=10)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)

    # Format x-axis with thousands separator
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'{int(x):,}'))

    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Add total annotation
    ax.annotate(f'Total: {total_connections:,} connections',
                xy=(0.98, 0.02),
                xycoords='axes fraction',
                ha='right', va='bottom',
                fontsize=9,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                         edgecolor='gray', alpha=0.9))

    # Adjust layout
    plt.tight_layout()

    return fig


def main():
    """Main execution."""
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <uml_metadata.json>", file=sys.stderr)
        sys.exit(1)
    data_path = sys.argv[1]

    print("Loading data...")
    by_type, total_connections = load_data(data_path)

    print(f"Connection types: {len(by_type)}")
    print(f"Total connections: {total_connections:,}")

    for t, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_connections) * 100
        print(f"  {t}: {count:,} ({pct:.1f}%)")

    print("\nCreating chart...")
    fig = create_chart(by_type, total_connections)

    print(f"Saving to {OUTPUT_PATH} at {DPI} DPI...")
    fig.savefig(OUTPUT_PATH, dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)

    print("Done!")

    # Verification
    if OUTPUT_PATH.exists():
        size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
        print(f"\nOutput file size: {size_mb:.2f} MB")


if __name__ == '__main__':
    main()
