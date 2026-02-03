#!/usr/bin/env python3
"""
Figure 4: Relationship Category Distribution

Creates an MDPI-compliant bar chart showing the distribution of
relationship categories in PlantUML diagrams.
"""

import json
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from pathlib import Path

# MDPI specifications
DPI = 600
FIGURE_WIDTH_MM = 180
FIGURE_WIDTH_INCHES = FIGURE_WIDTH_MM / 25.4
FIGURE_HEIGHT_INCHES = FIGURE_WIDTH_INCHES * 0.5  # Shorter for 4 bars
FONT_FAMILY = 'Arial'
MIN_FONT_SIZE = 8
BAR_COLOR = '#4A90A4'

# Paths
DATA_PATH = Path('/Users/vovapolischuk/indiehacker/projects/university/plantuml-data/relationship_counts.json')
OUTPUT_PATH = Path(__file__).parent / 'fig4_relationship_categories.png'


def load_data():
    """Load relationship category statistics from JSON."""
    with open(DATA_PATH, 'r') as f:
        data = json.load(f)

    rel_stats = data['statistics']['relationship_count_statistics']
    by_category = rel_stats['by_category']
    total_relationships = rel_stats['relationships_total']

    return by_category, total_relationships


def create_chart(by_category, total_relationships):
    """Create MDPI-compliant bar chart."""
    # Set up matplotlib with MDPI specs
    plt.rcParams.update({
        'font.family': FONT_FAMILY,
        'font.size': MIN_FONT_SIZE,
        'axes.labelsize': 10,
        'axes.titlesize': 10,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
    })

    # Sort by count (descending)
    sorted_categories = sorted(by_category.items(), key=lambda x: x[1], reverse=True)

    labels = [c[0].title() for c in sorted_categories]  # Capitalize
    counts = [c[1] for c in sorted_categories]

    # Create figure
    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH_INCHES, FIGURE_HEIGHT_INCHES))

    # Create vertical bars
    x_pos = range(len(labels))
    bars = ax.bar(x_pos, counts, color=BAR_COLOR, edgecolor='white', linewidth=0.5)

    # Add labels above bars (count + percentage)
    for bar, count in zip(bars, counts):
        percentage = (count / total_relationships) * 100
        label = f'{count:,}\n({percentage:.1f}%)'
        ax.annotate(label,
                    xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    xytext=(0, 5),
                    textcoords='offset points',
                    ha='center', va='bottom',
                    fontsize=9)

    # Configure axes
    ax.set_xlabel('Relationship Category', fontsize=10)
    ax.set_ylabel('Number of Relationships', fontsize=10)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels)

    # Format y-axis with thousands separator
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f'{int(x):,}'))

    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Add total annotation
    ax.annotate(f'Total: {total_relationships:,} relationships',
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
    by_category, total_relationships = load_data()

    print(f"Relationship categories: {len(by_category)}")
    print(f"Total relationships: {total_relationships:,}")

    for cat, count in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_relationships) * 100
        print(f"  {cat}: {count:,} ({pct:.1f}%)")

    print("\nCreating chart...")
    fig = create_chart(by_category, total_relationships)

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
