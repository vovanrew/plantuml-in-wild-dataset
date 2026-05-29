#!/usr/bin/env python3
"""
Figure 1: Type Distribution Bar Chart

Creates an publication-quality horizontal bar chart showing PlantUML diagram type distribution.
"""

import json
import sys
import matplotlib.pyplot as plt
import matplotlib as mpl
from pathlib import Path

OUTPUT_PNG = Path(__file__).parent / "fig1_type_distribution.png"
OUTPUT_TIFF = Path(__file__).parent / "fig1_type_distribution.tif"
OUTPUT_PDF = Path(__file__).parent / "fig1_type_distribution.pdf"

# Publication figure specifications
DPI_PNG = 600
DPI_TIFF = 1000  # Data in Brief line-drawing requirement
FIGURE_WIDTH_MM = 180
FIGURE_WIDTH_INCHES = FIGURE_WIDTH_MM / 25.4
FIGURE_HEIGHT_INCHES = 4.5

# Colors
UML_COLOR = "#4A90A4"
NON_UML_COLOR = "#808080"

def load_type_distribution(data_path):
    """Load only the statistics.type_distribution section from JSON."""
    with open(data_path, 'r') as f:
        data = json.load(f)
    return data['statistics']['type_distribution']

def transform_data(type_dist):
    """
    Apply transformations:
    1. Merge artifact into deployment
    2. Rename non-uml to Non-UML
    3. Capitalize type names
    """
    # Merge artifact into deployment
    if 'artifact' in type_dist:
        type_dist['deployment'] = type_dist.get('deployment', 0) + type_dist.pop('artifact')

    # Rename non-uml to Non-UML
    if 'non-uml' in type_dist:
        type_dist['Non-UML'] = type_dist.pop('non-uml')

    # Capitalize type names (except Non-UML which is already formatted)
    transformed = {}
    for key, value in type_dist.items():
        if key == 'Non-UML':
            transformed[key] = value
        else:
            transformed[key.capitalize()] = value

    return transformed

def create_chart(type_dist):
    """Create publication-quality horizontal bar chart."""
    # Sort by count ascending (smallest at top)
    sorted_items = sorted(type_dist.items(), key=lambda x: x[1])
    types = [item[0] for item in sorted_items]
    counts = [item[1] for item in sorted_items]

    # Calculate total for percentages
    total = sum(counts)

    # Set up matplotlib for publication
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
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <uml_metadata.json>", file=sys.stderr)
        sys.exit(1)
    data_path = sys.argv[1]

    # 1. Load JSON (only statistics section)
    print("Loading type distribution data...")
    type_dist = load_type_distribution(data_path)

    # 2. Apply transformations
    print("Applying transformations...")
    type_dist = transform_data(type_dist)

    # 3. Create chart
    print("Creating horizontal bar chart...")
    fig, total = create_chart(type_dist)

    # 4. Save in three formats.
    # PNG (600 DPI) is kept for the standalone-article manuscript
    # (manuscript_tex/manuscript.tex \includegraphics reference).
    # TIFF (1000 DPI, LZW) is for embedding in the DiB .docx
    # manuscript and meets the journal's line-drawing resolution
    # requirement (full-page-width 7480 px minimum).
    # PDF is the vector format uploaded as the separate artwork
    # file at DiB submission (matplotlib embeds fonts by default).
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

    # Print verification info
    print(f"\nVerification:")
    print(f"  - PNG output : {OUTPUT_PNG} ({DPI_PNG} DPI)")
    print(f"  - TIFF output: {OUTPUT_TIFF} ({DPI_TIFF} DPI, LZW)")
    print(f"  - PDF output : {OUTPUT_PDF} (vector)")
    print(f"  - Number of types: {len(type_dist)}")
    print(f"  - Total diagrams: {total:,}")

    # Print type breakdown
    print(f"\nType breakdown:")
    for t, c in sorted(type_dist.items(), key=lambda x: -x[1]):
        pct = (c / total) * 100
        print(f"  {t}: {c:,} ({pct:.1f}%)")

if __name__ == "__main__":
    main()
