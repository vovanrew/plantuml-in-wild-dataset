#!/usr/bin/env python3
"""
Figure 1: Type Distribution Bar Chart

Creates an MDPI-compliant horizontal bar chart showing PlantUML diagram type distribution.
"""

import json
import matplotlib.pyplot as plt
import matplotlib as mpl
from pathlib import Path

# Data source path
DATA_PATH = Path("/Users/vovapolischuk/indiehacker/projects/university/plantuml-data/relationship_counts.json")
OUTPUT_PATH = Path(__file__).parent / "fig1_type_distribution.png"

# MDPI specifications
DPI = 600
FIGURE_WIDTH_MM = 180
FIGURE_WIDTH_INCHES = FIGURE_WIDTH_MM / 25.4
FIGURE_HEIGHT_INCHES = 4.5

# Colors
UML_COLOR = "#4A90A4"
NON_UML_COLOR = "#808080"

def load_type_distribution():
    """Load only the statistics.type_distribution section from JSON."""
    with open(DATA_PATH, 'r') as f:
        data = json.load(f)
    return data['statistics']['type_distribution']

def transform_data(type_dist):
    """
    Apply transformations:
    1. Merge artifact into deployment
    2. Rename unclassified to Non-UML
    3. Capitalize type names
    """
    # Merge artifact into deployment
    if 'artifact' in type_dist:
        type_dist['deployment'] = type_dist.get('deployment', 0) + type_dist.pop('artifact')

    # Rename unclassified to Non-UML
    if 'unclassified' in type_dist:
        type_dist['Non-UML'] = type_dist.pop('unclassified')

    # Capitalize type names (except Non-UML which is already formatted)
    transformed = {}
    for key, value in type_dist.items():
        if key == 'Non-UML':
            transformed[key] = value
        else:
            transformed[key.capitalize()] = value

    return transformed

def create_chart(type_dist):
    """Create MDPI-compliant horizontal bar chart."""
    # Sort by count ascending (smallest at top)
    sorted_items = sorted(type_dist.items(), key=lambda x: x[1])
    types = [item[0] for item in sorted_items]
    counts = [item[1] for item in sorted_items]

    # Calculate total for percentages
    total = sum(counts)

    # Set up matplotlib for MDPI compliance
    mpl.rcParams['font.family'] = 'Arial'
    mpl.rcParams['font.size'] = 9

    # Create figure
    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH_INCHES, FIGURE_HEIGHT_INCHES))

    # Assign colors (Non-UML gets gray, others get blue)
    colors = [NON_UML_COLOR if t == 'Non-UML' else UML_COLOR for t in types]

    # Create horizontal bars
    bars = ax.barh(types, counts, color=colors, edgecolor='none', height=0.7)

    # Add labels (count + percentage) on each bar
    for bar, count in zip(bars, counts):
        percentage = (count / total) * 100
        label = f"{count:,} ({percentage:.1f}%)"

        # Position label inside or outside bar based on bar width
        bar_width = bar.get_width()
        max_count = max(counts)

        if bar_width > max_count * 0.3:
            # Label inside bar
            ax.text(bar_width - max_count * 0.02, bar.get_y() + bar.get_height() / 2,
                    label, va='center', ha='right', fontsize=8, color='white', fontweight='bold')
        else:
            # Label outside bar
            ax.text(bar_width + max_count * 0.01, bar.get_y() + bar.get_height() / 2,
                    label, va='center', ha='left', fontsize=8, color='black')

    # Style the chart
    ax.set_xlabel('Number of Diagrams', fontsize=10)
    ax.set_xlim(0, max(counts) * 1.15)  # Add space for labels

    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Format x-axis with thousands separator
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))

    # Ensure minimum font size of 8pt for y-axis labels
    ax.tick_params(axis='y', labelsize=9)
    ax.tick_params(axis='x', labelsize=8)

    # Tight layout
    plt.tight_layout()

    return fig, total

def main():
    # 1. Load JSON (only statistics section)
    print("Loading type distribution data...")
    type_dist = load_type_distribution()

    # 2. Apply transformations
    print("Applying transformations...")
    type_dist = transform_data(type_dist)

    # 3. Create chart
    print("Creating horizontal bar chart...")
    fig, total = create_chart(type_dist)

    # 4. Save at 600 DPI
    print(f"Saving figure to {OUTPUT_PATH}...")
    fig.savefig(OUTPUT_PATH, dpi=DPI, format='png', bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)

    # Print verification info
    print(f"\nVerification:")
    print(f"  - Output file: {OUTPUT_PATH}")
    print(f"  - Number of types: {len(type_dist)}")
    print(f"  - Total diagrams: {total:,}")
    print(f"  - DPI: {DPI}")

    # Print type breakdown
    print(f"\nType breakdown:")
    for t, c in sorted(type_dist.items(), key=lambda x: -x[1]):
        pct = (c / total) * 100
        print(f"  {t}: {c:,} ({pct:.1f}%)")

if __name__ == "__main__":
    main()
