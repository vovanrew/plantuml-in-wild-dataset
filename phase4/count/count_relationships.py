#!/usr/bin/env python3
"""
PlantUML Relationship Counter - counts arrows/connections in diagrams.

Counts relationships and merges with element counts from count_elements.py.
Uses coarse categories: structural, message, flow, association.

Usage:
    python3 count_relationships.py \
        --element-counts element_counts.json \
        --puml-dir ../puml_validated/valid \
        --output analysis_complete.json
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# Try to import tqdm for progress bar
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

# Import shared preprocessing utilities
import sys as _sys
_sys.path.insert(0, str(Path(__file__).parent.parent))
from common.preprocessing import preprocess_content


# =============================================================================
# CONSTANTS
# =============================================================================

VERSION = "1.0.0"

# Category mapping by diagram type
CATEGORY_MAP = {
    'class': 'structural',
    'object': 'structural',
    'component': 'structural',
    'deployment': 'structural',
    'sequence': 'message',
    'timing': 'message',
    'state': 'flow',
    'activity': 'flow',
    'usecase': 'association',
}

# Arrow patterns for relationship detection
# Order matters - more specific patterns first
ARROW_PATTERNS = [
    # Async arrows (must be before simple arrows)
    r'-+>>',                    # ->> async
    r'<<-+',                    # <<- async reverse

    # Lost/found messages
    r'->x',                     # ->x lost
    r'x<-',                     # x<- found

    # Inheritance/realization with decorations
    r'<\|[-.][-.]?',            # <|-- <|..
    r'[-.][-.]?\|>',            # --|> ..|>

    # Composition/aggregation endpoints
    r'\*[-.][-.]?(?!>)',        # *-- (not *-->)
    r'[-.][-.]?\*',             # --*
    r'o[-.][-.]?(?!>)',         # o-- (not o-->)
    r'[-.][-.]?o(?![a-zA-Z])',  # --o (not followed by letter)

    # Dotted dependency
    r'\.\.+>',                  # ..>
    r'<\.\.+',                  # <..

    # Bidirectional
    r'<[-.][-.]?>',             # <--> <..>

    # Simple arrows (most common)
    r'<-+(?!<)',                # <-- (not <<-)
    r'-+>(?!>)',                # --> (not ->>)
]

# Compiled pattern for efficiency
ARROW_REGEX = re.compile('|'.join(f'({p})' for p in ARROW_PATTERNS))


# =============================================================================
# PREPROCESSING - uses shared module from common.preprocessing
# =============================================================================


# =============================================================================
# RELATIONSHIP COUNTING
# =============================================================================

def count_arrows(content: str) -> int:
    """
    Count all arrows/relationships in preprocessed PlantUML content.

    Args:
        content: Preprocessed PlantUML content

    Returns:
        Total count of arrows found
    """
    total = 0

    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue

        # Skip directive lines
        if line.startswith('@') or line.startswith('!'):
            continue

        # Find all arrow matches in this line
        matches = ARROW_REGEX.findall(line)
        # findall returns tuples for groups, count non-empty matches
        for match_tuple in matches:
            if any(match_tuple):
                total += 1

    return total


def count_relationships(content: str, primary_type: str) -> Dict[str, int]:
    """
    Count relationships and categorize by diagram type.

    Args:
        content: Raw PlantUML content
        primary_type: Primary diagram type from classification

    Returns:
        Dict with category -> count mapping
    """
    clean_content = preprocess_content(content)
    arrow_count = count_arrows(clean_content)

    if arrow_count == 0:
        return {}

    # Map to coarse category based on diagram type
    category = CATEGORY_MAP.get(primary_type, 'structural')

    return {category: arrow_count}


# =============================================================================
# FILE PROCESSING
# =============================================================================

def load_element_counts(path: Path) -> Dict[str, Any]:
    """Load element counts JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def read_puml_file(path: Path) -> Optional[str]:
    """Read a PlantUML file."""
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception as e:
        print(f"Warning: Could not read {path}: {e}", file=sys.stderr)
        return None


def process_files(
    element_counts_path: Path,
    puml_dir: Path,
) -> Dict[str, Any]:
    """
    Process all files and merge element counts with relationship counts.

    Args:
        element_counts_path: Path to element_counts.json
        puml_dir: Directory containing .puml files

    Returns:
        Merged results dictionary
    """
    start_time = datetime.now()

    print(f"Loading element counts from {element_counts_path}...")
    element_data = load_element_counts(element_counts_path)
    element_results = element_data.get("results", {})

    print(f"Found {len(element_results)} files in element counts")

    # Process each file
    merged_results: Dict[str, Dict] = {}
    relationship_stats: Dict[str, int] = {}
    total_relationships = 0

    files_to_process = list(element_results.items())

    print(f"Processing {len(files_to_process)} files for relationships...")

    if HAS_TQDM:
        iterator = tqdm(files_to_process, desc="Counting relationships")
    else:
        iterator = files_to_process

    for idx, (filename, elem_result) in enumerate(iterator):
        filepath = puml_dir / filename

        # Start with element data
        merged = {
            "primary_type": elem_result.get("primary_type", ""),
            "confidence": elem_result.get("confidence"),
            "diagram_types": elem_result.get("diagram_types", []),
            "elements": elem_result.get("elements", {}),
            "total_elements": elem_result.get("total_elements", 0),
        }

        # Count relationships
        if filepath.exists():
            content = read_puml_file(filepath)
            if content:
                primary_type = elem_result.get("primary_type", "class")
                rel_counts = count_relationships(content, primary_type)
                merged["relationships"] = rel_counts
                merged["total_relationships"] = sum(rel_counts.values())

                # Update statistics
                total_relationships += merged["total_relationships"]
                for cat, count in rel_counts.items():
                    relationship_stats[cat] = relationship_stats.get(cat, 0) + count
            else:
                merged["relationships"] = {}
                merged["total_relationships"] = 0
        else:
            merged["relationships"] = {}
            merged["total_relationships"] = 0
            merged["note"] = elem_result.get("note", "file not found")

        merged_results[filename] = merged

        # Progress update (if no tqdm)
        if not HAS_TQDM and (idx + 1) % 10000 == 0:
            print(f"Processed {idx + 1}/{len(files_to_process)} files...", file=sys.stderr)

    end_time = datetime.now()
    duration = end_time - start_time
    processing_time = str(duration).split('.')[0]

    # Build statistics
    statistics = {
        "total_files": len(merged_results),
        "files_with_relationships": sum(
            1 for r in merged_results.values() if r["total_relationships"] > 0
        ),
        "total_relationships": total_relationships,
        "by_category": dict(sorted(relationship_stats.items(), key=lambda x: -x[1])),
        "processing_time": processing_time,
    }

    # Copy element statistics if available
    if "statistics" in element_data:
        statistics["elements_total"] = element_data["statistics"].get("elements_total", 0)
        statistics["by_element_type"] = element_data["statistics"].get("by_element_type", {})

    return {
        "metadata": {
            "version": VERSION,
            "timestamp": datetime.now().isoformat(),
            "source_elements": str(element_counts_path),
            "puml_directory": str(puml_dir),
            "note": "Merged element counts and relationship counts"
        },
        "statistics": statistics,
        "results": merged_results
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Count relationships in PlantUML diagrams and merge with element counts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--element-counts", "-e",
        type=Path,
        required=True,
        help="Path to element_counts.json from count_elements.py"
    )

    parser.add_argument(
        "--puml-dir", "-d",
        type=Path,
        required=True,
        help="Directory containing .puml files"
    )

    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("analysis_complete.json"),
        help="Output JSON file path (default: analysis_complete.json)"
    )

    args = parser.parse_args()

    if not args.element_counts.exists():
        print(f"Error: Element counts file not found: {args.element_counts}", file=sys.stderr)
        sys.exit(1)

    if not args.puml_dir.exists():
        print(f"Error: PUML directory not found: {args.puml_dir}", file=sys.stderr)
        sys.exit(1)

    # Process files
    output = process_files(args.element_counts, args.puml_dir)

    # Write output
    print(f"\nWriting results to {args.output}...")
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Print summary
    stats = output["statistics"]
    print("\n" + "=" * 60)
    print("Analysis Complete")
    print("=" * 60)
    print(f"Total files: {stats['total_files']}")
    print(f"Files with relationships: {stats['files_with_relationships']}")
    print(f"Total relationships: {stats['total_relationships']}")
    if stats.get('elements_total'):
        print(f"Total elements: {stats['elements_total']}")
    print(f"\nRelationships by category:")
    for cat, count in stats['by_category'].items():
        print(f"  {cat}: {count}")
    print(f"\nProcessing time: {stats['processing_time']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
