#!/usr/bin/env python3
"""
Add element/connection stats to PlantUML classification JSON.

This script reads a classification JSON file (enriched by count_lines.py),
joins it with JSONL output from DiagramStatsExtractor, and adds per-file
element/connection counts plus aggregate statistics.

Usage:
    python3 add_stats.py -i classifications_with_loc.json -s stats_results.jsonl -o output.json -v
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from tqdm import tqdm


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


def compute_distribution(values: List[int]) -> Dict[str, int]:
    """
    Compute logarithmic distribution bins for a list of values.

    Args:
        values: List of integer values

    Returns:
        Dictionary with bin labels and counts
    """
    return {
        '0': sum(1 for v in values if v == 0),
        '1-10': sum(1 for v in values if 1 <= v <= 10),
        '11-100': sum(1 for v in values if 11 <= v <= 100),
        '101-1000': sum(1 for v in values if 101 <= v <= 1000),
        '1001+': sum(1 for v in values if v > 1000)
    }


def load_stats_jsonl(stats_path: Path, verbose: bool = False) -> Dict[str, dict]:
    """
    Parse JSONL file into a dict keyed by filename.

    Args:
        stats_path: Path to JSONL file from DiagramStatsExtractor
        verbose: Show warnings for parse errors

    Returns:
        Dictionary mapping filename to stats record
    """
    stats = {}
    line_num = 0
    parse_errors = 0

    with open(stats_path, 'r', encoding='utf-8') as f:
        for line in f:
            line_num += 1
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                file_key = record.get('file', '')
                if file_key:
                    stats[file_key] = record
            except json.JSONDecodeError as e:
                parse_errors += 1
                if verbose:
                    print(f"Warning: Failed to parse JSONL line {line_num}: {e}")

    print(f"Loaded {len(stats)} stats records from JSONL ({line_num} lines, {parse_errors} parse errors)")
    return stats


def process(input_path: Path, stats_path: Path, verbose: bool = False) -> Dict:
    """
    Process classification JSON and join with stats JSONL.

    Args:
        input_path: Path to input classification JSON
        stats_path: Path to stats JSONL file
        verbose: Show progress bar if True

    Returns:
        Updated JSON data with element/connection stats
    """
    # Load input JSON
    print(f"Loading classification JSON from: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    classifications = data.get('classifications', {})
    total_files = len(classifications)
    print(f"Found {total_files} classified diagrams")

    # Load stats JSONL
    stats_lookup = load_stats_jsonl(stats_path, verbose)

    # Join stats into classifications
    matched = 0
    skipped = 0
    errored = 0

    # Aggregate counters
    all_elements_total = []
    all_connections_total = []
    elements_type_totals = Counter()
    connections_type_totals = Counter()
    error_distribution = Counter()

    iterator = tqdm(classifications.items(), desc="Adding stats") if verbose else classifications.items()

    for filename, classification in iterator:
        record = stats_lookup.get(filename)

        if record is None:
            skipped += 1
            classification['elements'] = {}
            classification['elements_total'] = 0
            classification['connections'] = {}
            classification['connections_total'] = 0
            classification['stats_error'] = 'no_stats_record'
            continue

        error = record.get('error')

        if error is not None:
            errored += 1
            classification['elements'] = record.get('elements', {})
            classification['elements_total'] = record.get('elements_total', 0)
            classification['connections'] = record.get('connections', {})
            classification['connections_total'] = record.get('connections_total', 0)
            classification['stats_error'] = error
            error_distribution[error] += 1
            continue

        matched += 1
        elements = record.get('elements', {})
        connections = record.get('connections', {})
        elements_total = record.get('elements_total', 0)
        connections_total = record.get('connections_total', 0)

        classification['elements'] = elements
        classification['elements_total'] = elements_total
        classification['connections'] = connections
        classification['connections_total'] = connections_total
        classification['stats_error'] = None

        all_elements_total.append(elements_total)
        all_connections_total.append(connections_total)

        for etype, count in elements.items():
            elements_type_totals[etype] += count
        for ctype, count in connections.items():
            connections_type_totals[ctype] += count

    # Update metadata
    if 'metadata' not in data:
        data['metadata'] = {}

    data['metadata']['stats_added'] = True
    data['metadata']['stats_timestamp'] = datetime.now().isoformat()
    data['metadata']['stats_matched'] = matched
    data['metadata']['stats_skipped'] = skipped
    data['metadata']['stats_errored'] = errored
    data['metadata']['stats_jsonl_file'] = stats_path.name

    # Compute aggregate statistics
    if 'statistics' not in data:
        data['statistics'] = {}

    data['statistics']['elements_statistics'] = compute_statistics(all_elements_total)
    data['statistics']['connections_statistics'] = compute_statistics(all_connections_total)
    data['statistics']['elements_distribution'] = compute_distribution(all_elements_total)
    data['statistics']['connections_distribution'] = compute_distribution(all_connections_total)
    data['statistics']['elements_type_totals'] = dict(elements_type_totals.most_common())
    data['statistics']['connections_type_totals'] = dict(connections_type_totals.most_common())
    data['statistics']['stats_error_distribution'] = dict(error_distribution.most_common())

    print(f"\nProcessing complete:")
    print(f"  Matched: {matched}")
    print(f"  Skipped (no stats record): {skipped}")
    print(f"  Errored (extractor error): {errored}")

    if all_elements_total:
        stats = data['statistics']['elements_statistics']
        print(f"\nElements Statistics:")
        print(f"  Min: {stats['min']}")
        print(f"  Max: {stats['max']}")
        print(f"  Mean: {stats['mean']}")
        print(f"  Median: {stats['median']}")

    if all_connections_total:
        stats = data['statistics']['connections_statistics']
        print(f"\nConnections Statistics:")
        print(f"  Min: {stats['min']}")
        print(f"  Max: {stats['max']}")
        print(f"  Mean: {stats['mean']}")
        print(f"  Median: {stats['median']}")

    return data


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Add element/connection stats to PlantUML classification JSON',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add stats from JSONL to classification JSON
  python3 add_stats.py -i classifications_with_loc.json -s stats_results.jsonl -o output.json

  # With verbose progress
  python3 add_stats.py -i classifications_with_loc.json -s stats_results.jsonl -o output.json -v
        """
    )

    parser.add_argument(
        '-i', '--input',
        type=Path,
        required=True,
        help='Input classification JSON file (e.g., classifications_with_loc.json)'
    )

    parser.add_argument(
        '-s', '--stats',
        type=Path,
        required=True,
        help='JSONL file from DiagramStatsExtractor'
    )

    parser.add_argument(
        '-o', '--output',
        type=Path,
        required=True,
        help='Output JSON file with element/connection stats'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show progress bar and detailed output'
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if not args.stats.exists():
        print(f"Error: Stats JSONL file not found: {args.stats}", file=sys.stderr)
        sys.exit(1)

    # Process
    try:
        data = process(args.input, args.stats, args.verbose)

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
