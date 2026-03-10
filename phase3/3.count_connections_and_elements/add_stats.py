#!/usr/bin/env python3
"""
Add element/connection stats to PlantUML classification JSON.

This script reads a classification JSON file (enriched by count_lines.py),
joins it with JSONL output from DiagramStatsExtractor, and adds per-file
element/connection counts. Aggregate statistics are computed separately
by phase3/5.aggregate_stats/aggregate_elements.py.

Usage:
    python3 add_stats.py -i classifications_with_loc.json -s stats_results.jsonl -o output.json -v
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict
from tqdm import tqdm


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

    iterator = tqdm(classifications.items(), desc="Adding stats") if verbose else classifications.items()

    for filename, classification in iterator:
        record = stats_lookup.get(filename)

        if record is None:
            skipped += 1
            classification['elements'] = {}
            classification['elements_total'] = 0
            classification['connections'] = {}
            classification['connections_total'] = 0
            classification['extraction_error'] = 'no_stats_record'
            continue

        error = record.get('error')

        if error is not None:
            errored += 1
            classification['elements'] = record.get('elements', {})
            classification['elements_total'] = record.get('elements_total', 0)
            classification['connections'] = record.get('connections', {})
            classification['connections_total'] = record.get('connections_total', 0)
            classification['extraction_error'] = error
            continue

        matched += 1
        classification['elements'] = record.get('elements', {})
        classification['elements_total'] = record.get('elements_total', 0)
        classification['connections'] = record.get('connections', {})
        classification['connections_total'] = record.get('connections_total', 0)
        classification['extraction_error'] = None

    print(f"\nProcessing complete:")
    print(f"  Matched: {matched}")
    print(f"  Skipped (no stats record): {skipped}")
    print(f"  Errored (extractor error): {errored}")

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
