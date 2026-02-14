#!/usr/bin/env python3
"""
PlantUML Connection Counter - counts arrows/connections in diagrams.

Counts connections and adds to existing classification data.
Uses coarse categories: structural, message, flow, association.
Preserves input JSON structure and augments classifications with connection counts.

Usage:
    python3 count_connections.py --input <json> --puml-dir <dir> --output <json>

Example:
    python3 count_connections.py \
        --input element_counts.json \
        --puml-dir ../puml_validated/valid \
        --output connection_counts.json
"""

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Dict, Any, Optional

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

VERSION = "1.2.0"

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

# Arrow patterns for connection detection
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

# Direction hints that PlantUML allows inside arrows for layout control.
# E.g., --left> means --> with a leftward hint, -right-> means -->.
# Stripping these before matching normalizes all directional variants.
DIRECTION_HINT_RE = re.compile(
    r'(?<=[-.])'
    r'(?:left|right|up|down|[lrud])'
    r'(?=[-.|>*o<])'
)


# =============================================================================
# PREPROCESSING - uses shared module from common.preprocessing
# =============================================================================


# =============================================================================
# CONNECTION COUNTING
# =============================================================================

def count_arrows(content: str) -> int:
    """
    Count all arrows/connections in preprocessed PlantUML content.

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

        # Normalize directional arrows: --left> → -->, -right-> → -->
        line = DIRECTION_HINT_RE.sub('', line)

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


def is_beta_activity(content: str) -> bool:
    """
    Check if preprocessed content uses beta activity syntax.

    Beta syntax uses :action; notation and start/stop/end keywords with
    implicit control flow. Branching and looping create connections that
    cannot be reliably counted by static analysis, so these diagrams
    are excluded from connection counting.

    Args:
        content: Preprocessed PlantUML content

    Returns:
        True if beta activity syntax is detected
    """
    for line in content.split('\n'):
        line = line.strip()
        if line in ('start', 'stop', 'end'):
            return True
        if re.match(r':.+[;|<>]\s*$', line):
            return True
    return False


def count_connections(content: str, primary_type: str) -> Dict[str, int]:
    """
    Count connections and categorize by diagram type.

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

def load_input(path: Path) -> Dict[str, Any]:
    """Load input JSON file."""
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


def aggregate_statistics(
    classifications: Dict[str, Dict],
) -> Dict[str, Any]:
    """Generate connection count statistics from classifications."""
    with_connections = sum(
        1 for c in classifications.values() if c.get("total_connections", 0) > 0
    )
    connections_total = sum(
        c.get("total_connections", 0) for c in classifications.values()
    )

    by_category: Dict[str, int] = {}
    for classification in classifications.values():
        for category, count in classification.get("connections", {}).items():
            by_category[category] = by_category.get(category, 0) + count

    by_category = dict(sorted(by_category.items(), key=lambda x: -x[1]))

    return {
        "with_connections": with_connections,
        "connections_total": connections_total,
        "by_category": by_category,
    }


def process_files(
    input_path: Path,
    puml_dir: Path,
    output_path: Path,
) -> Dict[str, Any]:
    """
    Process all files from input JSON, preserving existing structure.

    Args:
        input_path: Path to input JSON file
        puml_dir: Directory containing .puml files
        output_path: Path for output JSON file

    Returns:
        Augmented results dictionary
    """
    print(f"Loading input from {input_path}...")
    data = load_input(input_path)

    # Start with deep copy of input data to preserve all existing fields
    output = copy.deepcopy(data)

    classifications = output.get("classifications", {})

    print(f"Processing {len(classifications)} files for connections...")

    files_to_process = list(classifications.items())

    if HAS_TQDM:
        iterator = tqdm(files_to_process, desc="Counting connections")
    else:
        iterator = files_to_process

    for filename, classification in iterator:
        filepath = puml_dir / filename

        if not filepath.exists():
            classification["connections"] = {}
            classification["total_connections"] = 0
            classification["connection_count_note"] = "file not found"
            continue

        content = read_puml_file(filepath)
        if content is None:
            classification["connections"] = {}
            classification["total_connections"] = 0
            classification["connection_count_note"] = "read error"
            continue

        primary_type = classification.get("primary_type", "class")

        # Beta-syntax activity diagrams use implicit control flow from
        # branching/looping that static analysis cannot reliably count.
        # Skip these; legacy activity diagrams (using -->) are counted normally.
        if primary_type == 'activity':
            clean_content = preprocess_content(content)
            if is_beta_activity(clean_content):
                classification["connections"] = {}
                classification["total_connections"] = 0
                classification["connection_count_note"] = "beta_activity_skipped"
                continue

        # Count connections and add to existing classification
        conn_counts = count_connections(content, primary_type)
        classification["connections"] = conn_counts
        classification["total_connections"] = sum(conn_counts.values())

    # Add connection_count_statistics to existing statistics section
    conn_stats = aggregate_statistics(classifications)

    if "statistics" not in output:
        output["statistics"] = {}
    output["statistics"]["connection_count_statistics"] = conn_stats

    print(f"Writing results to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("\n=== Connection Count Summary ===")
    print(f"Total files: {len(classifications)}")
    print(f"Files with connections: {conn_stats['with_connections']}")
    print(f"Total connections: {conn_stats['connections_total']}")
    print("\nConnections by category:")
    for category, count in conn_stats['by_category'].items():
        print(f"  {category}: {count}")

    return output


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Count connections in PlantUML diagrams",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--input", "-i",
        type=Path,
        required=True,
        help="Path to input JSON file (from count_elements.py or earlier pipeline step)"
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
        default=Path("connection_counts.json"),
        help="Output JSON file path (default: connection_counts.json)"
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if not args.puml_dir.exists():
        print(f"Error: PUML directory not found: {args.puml_dir}", file=sys.stderr)
        sys.exit(1)

    process_files(args.input, args.puml_dir, args.output)


if __name__ == "__main__":
    main()
