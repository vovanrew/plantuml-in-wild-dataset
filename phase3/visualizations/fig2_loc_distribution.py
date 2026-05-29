#!/usr/bin/env python3
"""
Figure 2: LOC (Lines of Code) Distribution Histogram

Creates an publication-quality histogram showing diagram size distribution
by lines of code for the Data paper.
"""

import json
import sys
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from pathlib import Path

# Publication figure specifications
DPI_PNG = 600
DPI_TIFF = 1000  # Data in Brief line-drawing requirement
FIGURE_WIDTH_MM = 180
FIGURE_WIDTH_INCHES = FIGURE_WIDTH_MM / 25.4
FIGURE_HEIGHT_INCHES = FIGURE_WIDTH_INCHES * 0.6  # Aspect ratio for histogram
FONT_FAMILY = 'Arial'
MIN_FONT_SIZE = 8
BAR_COLOR = '#4A90A4'

# Paths
OUTPUT_PNG = Path(__file__).parent / 'fig2_loc_distribution.png'
OUTPUT_TIFF = Path(__file__).parent / 'fig2_loc_distribution.tif'
OUTPUT_PDF = Path(__file__).parent / 'fig2_loc_distribution.pdf'


def load_data(data_path):
    """Load pre-computed LOC distribution and median from JSON."""
    with open(data_path, 'r') as f:
        data = json.load(f)

    median = data['statistics']['lines_count_statistics']['median']
    distribution = data['statistics']['lines_count_distribution']

    return distribution, median


def create_histogram(distribution, median):
    """Create publication-quality histogram."""
    # Set up matplotlib with publication figure specs
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
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <uml_metadata.json>", file=sys.stderr)
        sys.exit(1)
    data_path = sys.argv[1]

    print("Loading data...")
    distribution, median = load_data(data_path)

    print(f"Lines count distribution: {distribution}")
    print(f"Median: {median} lines")
    print(f"Total diagrams: {sum(distribution.values()):,}")

    print("\nCreating histogram...")
    fig = create_histogram(distribution, median)

    print(f"Saving PNG to {OUTPUT_PNG}...")
    fig.savefig(OUTPUT_PNG, dpi=DPI_PNG, format='png', bbox_inches='tight',
                facecolor='white', edgecolor='none')
    print(f"Saving TIFF to {OUTPUT_TIFF}...")
    fig.savefig(OUTPUT_TIFF, dpi=DPI_TIFF, format='tiff', bbox_inches='tight',
                facecolor='white', edgecolor='none',
                pil_kwargs={'compression': 'tiff_lzw'})
    print(f"Saving PDF to {OUTPUT_PDF}...")
    fig.savefig(OUTPUT_PDF, format='pdf', bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)

    print("Done!")

    # Verification
    print("\nOutputs:")
    for path in (OUTPUT_PNG, OUTPUT_TIFF, OUTPUT_PDF):
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            print(f"  {path.name}: {size_mb:.2f} MB")


if __name__ == '__main__':
    main()
