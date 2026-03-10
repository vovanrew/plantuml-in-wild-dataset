#!/usr/bin/env python3
"""
Recompute line count aggregate statistics from per-record content_lines.

Run after any dataset modification (removing/adding files) to refresh
lines_count_statistics and lines_count_distribution without re-reading .puml files.

Usage:
    python3 aggregate_lines.py -i uml_metadata.json -o uml_metadata.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List


def compute_statistics(values: List[float]) -> Dict[str, float]:
    if not values:
        return {'min': 0, 'max': 0, 'mean': 0, 'median': 0, 'q1': 0, 'q3': 0}

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


def main():
    parser = argparse.ArgumentParser(
        description='Recompute line count aggregate statistics from per-record data'
    )
    parser.add_argument('-i', '--input', type=Path, required=True, help='Input classification JSON')
    parser.add_argument('-o', '--output', type=Path, required=True, help='Output JSON (can be same as input)')
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading: {args.input}")
    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)

    classifications = data.get('classifications', {})
    stats = data.setdefault('statistics', {})

    all_lines = [c['content_lines'] for c in classifications.values() if 'content_lines' in c]

    if all_lines:
        stats['lines_count_statistics'] = compute_statistics(all_lines)
        stats['lines_count_distribution'] = {
            '1-10': sum(1 for v in all_lines if 1 <= v <= 10),
            '11-100': sum(1 for v in all_lines if 11 <= v <= 100),
            '101-1000': sum(1 for v in all_lines if 101 <= v <= 1000),
            '1001+': sum(1 for v in all_lines if v > 1000)
        }

    ls = stats.get('lines_count_statistics', {})
    print(f"Records with content_lines: {len(all_lines)}")
    print(f"Lines: min={ls.get('min')}, median={ls.get('median')}, mean={ls.get('mean')}, max={ls.get('max')}")
    print(f"Distribution: {stats.get('lines_count_distribution', {})}")

    print(f"\nSaving: {args.output}")
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print("Done!")


if __name__ == '__main__':
    main()
