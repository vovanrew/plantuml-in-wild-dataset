#!/usr/bin/env python3
"""
Figure 2: LOC (Lines of Code) Distribution Histogram

Creates an MDPI-compliant histogram showing diagram size distribution
by lines of code for the Data paper.
"""

import json
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from pathlib import Path

# MDPI specifications
DPI = 600
FIGURE_WIDTH_MM = 180
FIGURE_WIDTH_INCHES = FIGURE_WIDTH_MM / 25.4
FIGURE_HEIGHT_INCHES = FIGURE_WIDTH_INCHES * 0.6  # Aspect ratio for histogram
FONT_FAMILY = 'Arial'
MIN_FONT_SIZE = 8
BAR_COLOR = '#4A90A4'

# Paths
DATA_PATH = Path('/Users/vovapolischuk/indiehacker/projects/university/plantuml-data/connection_counts.json')
OUTPUT_PATH = Path(__file__).parent / 'fig2_loc_distribution.png'


def load_data():
    """Load data and compute logarithmic bins from per-file content_lines."""
    with open(DATA_PATH, 'r') as f:
        data = json.load(f)

    median = data['statistics']['lines_count_statistics']['median']

    # Compute logarithmic bins from raw per-file data
    classifications = data.get('classifications', {})
    all_lines = [c['content_lines'] for c in classifications.values() if 'content_lines' in c]

    distribution = {
        '1-10': sum(1 for val in all_lines if 1 <= val <= 10),
        '11-100': sum(1 for val in all_lines if 11 <= val <= 100),
        '101-1000': sum(1 for val in all_lines if 101 <= val <= 1000),
        '1001+': sum(1 for val in all_lines if val > 1000)
    }

    return distribution, median


def create_histogram(distribution, median):
    """Create MDPI-compliant histogram."""
    # Set up matplotlib with MDPI specs
    plt.rcParams.update({
        'font.family': FONT_FAMILY,
        'font.size': MIN_FONT_SIZE,
        'axes.labelsize': 10,
        'axes.titlesize': 10,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
    })

    # Order bins correctly (logarithmic scale)
    bin_order = ['1-10', '11-100', '101-1000', '1001+']
    counts = [distribution[b] for b in bin_order]
    total = sum(counts)

    # Create figure
    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH_INCHES, FIGURE_HEIGHT_INCHES))

    # Create bars
    x_pos = range(len(bin_order))
    bars = ax.bar(x_pos, counts, color=BAR_COLOR, edgecolor='white', linewidth=0.5)

    # Add labels above bars (count + percentage)
    for i, (bar, count) in enumerate(zip(bars, counts)):
        percentage = (count / total) * 100
        label = f'{count:,}\n({percentage:.1f}%)'
        ax.annotate(label,
                    xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    xytext=(0, 5),
                    textcoords='offset points',
                    ha='center', va='bottom',
                    fontsize=8)

    # Configure axes
    ax.set_xlabel('Lines of Code', fontsize=10)
    ax.set_ylabel('Number of Diagrams', fontsize=10)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(bin_order)

    # Format y-axis with thousands separator
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'{int(x):,}'))

    # Remove top and right spines (clean style)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Add median annotation
    # Median is 24, which falls in the "11-50" bin (index 1)
    ax.annotate(f'Median = {median} lines',
                xy=(0.98, 0.95),
                xycoords='axes fraction',
                ha='right', va='top',
                fontsize=9,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                         edgecolor='gray', alpha=0.9))

    # Adjust layout
    plt.tight_layout()

    return fig


def main():
    """Main execution."""
    print("Loading data...")
    distribution, median = load_data()

    print(f"Lines count distribution: {distribution}")
    print(f"Median: {median} lines")
    print(f"Total diagrams: {sum(distribution.values()):,}")

    print("\nCreating histogram...")
    fig = create_histogram(distribution, median)

    print(f"Saving to {OUTPUT_PATH} at {DPI} DPI...")
    fig.savefig(OUTPUT_PATH, dpi=DPI, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)

    print("Done!")

    # Verification
    if OUTPUT_PATH.exists():
        size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
        print(f"\nOutput file size: {size_mb:.2f} MB")
        print("Verification: File created successfully")


if __name__ == '__main__':
    main()
