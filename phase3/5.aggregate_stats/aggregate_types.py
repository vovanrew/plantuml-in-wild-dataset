#!/usr/bin/env python3
"""
Recompute type distribution and classification aggregate statistics.

Refreshes type_distribution, total_files, uml/non_uml counts, mixed_type,
truncated, and classify_errored from per-record data.

Usage:
    python3 aggregate_types.py -i uml_metadata.json -o uml_metadata.json
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description='Recompute type distribution and classification aggregates from per-record data'
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
    meta = data.setdefault('metadata', {})

    type_counts = Counter()
    mixed_type_count = 0
    truncated_count = 0
    classify_errored = 0

    for c in classifications.values():
        pt = c.get('primary_type')
        if pt:
            type_counts[pt] += 1
        if c.get('secondary_types'):
            mixed_type_count += 1
        if c.get('truncated'):
            truncated_count += 1
        if c.get('classify_error'):
            classify_errored += 1

    total = len(classifications)
    uml = sum(1 for c in classifications.values() if c.get('primary_type') != 'non-uml')
    non_uml = total - uml

    stats['total_files'] = total
    stats['classified'] = total
    stats['uml'] = uml
    stats['non_uml'] = non_uml
    stats['mixed_type'] = mixed_type_count
    stats['truncated'] = truncated_count
    stats['classify_errored'] = classify_errored
    stats['type_distribution'] = dict(type_counts.most_common())
    meta['total_files'] = total

    print(f"Total: {total}, UML: {uml}, non-UML: {non_uml}")
    print(f"Mixed type: {mixed_type_count}, Truncated: {truncated_count}")
    print(f"Type distribution: {stats['type_distribution']}")

    print(f"\nSaving: {args.output}")
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print("Done!")


if __name__ == '__main__':
    main()
