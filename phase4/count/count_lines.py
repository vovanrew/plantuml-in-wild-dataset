#!/usr/bin/env python3
"""
Add line metrics to PlantUML classification JSON.

This script reads a classification JSON file (output from classify_with_llm.py),
counts lines for each PUML file, and adds line metrics to the JSON output.

Metrics:
- content_lines: Non-blank, non-comment lines (actual diagram content)
- comment_lines: Pure comment lines

Excludes from content_lines: blank lines, pure comment lines, multi-line comment blocks,
metadata header, @startuml/@enduml markers

Usage:
    python3 count_lines.py -i classify_result.json -d 1k_puml_sample -o output.json
"""

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from tqdm import tqdm


def remove_inline_comment(line: str) -> str:
    """
    Remove inline PlantUML comment from a single line.

    PlantUML comment rules:
    - ' starts a comment only if preceded by whitespace or at line start
    - Apostrophes inside double-quoted strings are preserved
    - Apostrophes in middle of words (Alice's) are NOT comments

    Args:
        line: Single line of PlantUML code

    Returns:
        Line with comment removed
    """
    result = []
    in_string = False
    i = 0

    while i < len(line):
        char = line[i]

        # Toggle string state on double-quote
        if char == '"':
            in_string = not in_string
            result.append(char)
            i += 1

        # Check for comment marker
        elif char == "'" and not in_string:
            # Comment rules: ' starts a comment if:
            # 1. At start of line (already handled by regex)
            # 2. Preceded by whitespace AND followed by space/tab (typical comment)
            # 3. Preceded by whitespace AND at end of line
            # Otherwise, preserve it (could be 'text' or Alice's)

            if i == 0:
                # At start of line (but this should be caught by regex already)
                break
            elif result and result[-1] in (' ', '\t'):
                # Preceded by whitespace - check what follows
                if i + 1 >= len(line):
                    # At end of line after whitespace → comment
                    while result and result[-1] in (' ', '\t'):
                        result.pop()
                    break
                elif line[i + 1] in (' ', '\t'):
                    # Followed by space/tab → comment
                    while result and result[-1] in (' ', '\t'):
                        result.pop()
                    break
                else:
                    # Preceded by space but not followed by space ('text' pattern)
                    result.append(char)
                    i += 1
            else:
                # In middle of word (e.g., "Alice's") → NOT a comment
                result.append(char)
                i += 1

        # Normal character
        else:
            result.append(char)
            i += 1

    return ''.join(result)


def count_lines(puml_content: str) -> Dict[str, int]:
    """
    Count lines for PlantUML file.

    Args:
        puml_content: Raw PlantUML file content

    Returns:
        Dictionary with line metrics:
        {
            'content_lines': int,    # Non-blank, non-comment lines
            'comment_lines': int,    # Pure comment lines
        }
    """
    lines = puml_content.split('\n')

    # Skip metadata header (first 3 lines if they're all comments)
    if len(lines) >= 3 and all(line.strip().startswith("'") for line in lines[:3]):
        lines = lines[3:]

    # Remove multi-line comments: /' ... '/
    content = '\n'.join(lines)
    content = re.sub(r"/'.*?'/", "", content, flags=re.DOTALL)
    lines = content.split('\n')

    content_lines = 0
    comment_lines = 0

    for line in lines:
        # Skip @startuml/@enduml markers
        if re.match(r'^\s*@(start|end)uml\s*$', line, re.IGNORECASE):
            continue

        # Skip blank lines
        if not line.strip():
            continue

        # Count pure comment lines
        if re.match(r"^\s*'+", line):
            comment_lines += 1
            continue

        # Has code - remove inline comment and verify content exists
        cleaned = remove_inline_comment(line)
        if cleaned.strip():
            content_lines += 1

    return {
        'content_lines': content_lines,
        'comment_lines': comment_lines
    }


def find_puml_file(filename: str, search_dirs: List[Path]) -> Optional[Path]:
    """
    Find PUML file in one of the search directories.

    Args:
        filename: Name of PUML file (e.g., "5f95f42b5b392db1c75ab9f5c6eb514ac273e89e.puml")
        search_dirs: List of directories to search

    Returns:
        Path to PUML file if found, None otherwise
    """
    for search_dir in search_dirs:
        puml_path = search_dir / filename
        if puml_path.exists():
            return puml_path
    return None


def compute_statistics(values: List[float]) -> Dict[str, float]:
    """
    Compute statistical metrics for a list of values.

    Args:
        values: List of numeric values

    Returns:
        Dictionary with min, max, mean, median, q1, q3
    """
    if not values:
        return {
            'min': 0,
            'max': 0,
            'mean': 0,
            'median': 0,
            'q1': 0,
            'q3': 0
        }

    sorted_values = sorted(values)
    n = len(sorted_values)

    return {
        'min': sorted_values[0],
        'max': sorted_values[-1],
        'mean': round(sum(values) / n, 2),
        'median': sorted_values[n // 2],
        'q1': sorted_values[n // 4],
        'q3': sorted_values[3 * n // 4]
    }


def process_json_file(input_path: Path, puml_dirs: List[Path], verbose: bool = False) -> Dict:
    """
    Process classification JSON and add line metrics.

    Args:
        input_path: Path to input JSON file
        puml_dirs: List of directories containing PUML files
        verbose: Show progress bar if True

    Returns:
        Updated JSON data with line metrics
    """
    # Load input JSON
    print(f"Loading classification JSON from: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    classifications = data.get('classifications', {})
    total_files = len(classifications)
    print(f"Found {total_files} classified diagrams")

    # Process each classification
    processed = 0
    skipped = 0
    errors = 0

    iterator = tqdm(classifications.items(), desc="Adding line metrics") if verbose else classifications.items()

    for filename, classification in iterator:
        try:
            # Find PUML file
            puml_path = find_puml_file(filename, puml_dirs)
            if not puml_path:
                skipped += 1
                if verbose:
                    print(f"Warning: PUML file not found: {filename}")
                continue

            # Read content
            content = puml_path.read_text(encoding='utf-8', errors='replace')

            # Count lines
            line_metrics = count_lines(content)

            # Add metrics to classification
            classification['content_lines'] = line_metrics['content_lines']
            classification['comment_lines'] = line_metrics['comment_lines']

            processed += 1

        except Exception as e:
            errors += 1
            if verbose:
                print(f"Error processing {filename}: {e}")

    # Update metadata
    if 'metadata' not in data:
        data['metadata'] = {}

    data['metadata']['lines_added'] = True
    data['metadata']['lines_timestamp'] = datetime.now().isoformat()
    data['metadata']['lines_processed'] = processed
    data['metadata']['lines_skipped'] = skipped
    data['metadata']['lines_errors'] = errors

    # Compute content_lines statistics
    all_content_lines = [c['content_lines'] for c in classifications.values() if 'content_lines' in c]
    if all_content_lines:
        if 'statistics' not in data:
            data['statistics'] = {}

        data['statistics']['lines_count_statistics'] = compute_statistics(all_content_lines)

        # Add content_lines distribution (logarithmic bins for right-skewed data)
        distribution = {
            '1-10': sum(1 for val in all_content_lines if 1 <= val <= 10),
            '11-100': sum(1 for val in all_content_lines if 11 <= val <= 100),
            '101-1000': sum(1 for val in all_content_lines if 101 <= val <= 1000),
            '1001+': sum(1 for val in all_content_lines if val > 1000)
        }
        data['statistics']['lines_count_distribution'] = distribution

    print(f"\nProcessing complete:")
    print(f"  Processed: {processed}")
    print(f"  Skipped (file not found): {skipped}")
    print(f"  Errors: {errors}")

    if all_content_lines:
        stats = data['statistics']['lines_count_statistics']
        print(f"\nLines Count Statistics:")
        print(f"  Min: {stats['min']}")
        print(f"  Max: {stats['max']}")
        print(f"  Mean: {stats['mean']}")
        print(f"  Median: {stats['median']}")
        print(f"  Q1: {stats['q1']}")
        print(f"  Q3: {stats['q3']}")

    return data


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Add line metrics to PlantUML classification JSON',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process 1K sample
  python3 count_lines.py -i classify_result.json -d 1k_puml_sample -o output.json

  # Process full dataset with verbose output
  python3 count_lines.py -i classify_result.json -d ../phase3/puml -o output.json -v

  # Multiple search directories
  python3 count_lines.py -i classify.json -d dir1 -d dir2 -d dir3 -o output.json
        """
    )

    parser.add_argument(
        '-i', '--input',
        type=Path,
        required=True,
        help='Input classification JSON file'
    )

    parser.add_argument(
        '-o', '--output',
        type=Path,
        required=True,
        help='Output JSON file with line metrics'
    )

    parser.add_argument(
        '-d', '--puml-dir',
        type=Path,
        action='append',
        dest='puml_dirs',
        help='Directory containing PUML files (can specify multiple times)'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show progress bar and detailed output'
    )

    args = parser.parse_args()

    # Validate input file
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Default PUML directory if none specified
    if not args.puml_dirs:
        args.puml_dirs = [Path('1k_puml_sample')]

    # Validate PUML directories
    for puml_dir in args.puml_dirs:
        if not puml_dir.exists():
            print(f"Warning: PUML directory not found: {puml_dir}", file=sys.stderr)

    # Process JSON
    try:
        data = process_json_file(args.input, args.puml_dirs, args.verbose)

        # Save output
        print(f"\nSaving output to: {args.output}")
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        print("Done!")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
