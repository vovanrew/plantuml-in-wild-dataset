#!/usr/bin/env python3
"""
Recompute element/connection aggregate statistics from per-record data.

Refreshes elements_statistics, connections_statistics, their distributions,
type totals, and extraction_error_distribution.

Usage:
    python3 aggregate_elements.py -i uml_metadata.json -o uml_metadata.json
"""

import argparse
import json
import sys
from collections import Counter
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


def compute_distribution(values: List[int]) -> Dict[str, int]:
    return {
        '0': sum(1 for v in values if v == 0),
        '1-10': sum(1 for v in values if 1 <= v <= 10),
        '11-100': sum(1 for v in values if 11 <= v <= 100),
        '101-1000': sum(1 for v in values if 101 <= v <= 1000),
        '1001+': sum(1 for v in values if v > 1000)
    }


def main():
    parser = argparse.ArgumentParser(
        description='Recompute element/connection aggregate statistics from per-record data'
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

    all_elements = []
    all_connections = []
    elements_type_totals = Counter()
    connections_type_totals = Counter()
    error_distribution = Counter()
    extraction_ok = 0
    extraction_err = 0

    for c in classifications.values():
        err = c.get('extraction_error')
        if err:
            error_distribution[err] += 1
            extraction_err += 1
            continue

        extraction_ok += 1

        if 'elements_total' in c:
            all_elements.append(c['elements_total'])
            for etype, count in c.get('elements', {}).items():
                elements_type_totals[etype] += count

        if 'connections_total' in c:
            all_connections.append(c['connections_total'])
            for ctype, count in c.get('connections', {}).items():
                connections_type_totals[ctype] += count

    # Update statistics
    if all_elements:
        stats['elements_statistics'] = compute_statistics(all_elements)
        stats['elements_distribution'] = compute_distribution(all_elements)
        stats['elements_type_totals'] = dict(elements_type_totals.most_common())

    if all_connections:
        stats['connections_statistics'] = compute_statistics(all_connections)
        stats['connections_distribution'] = compute_distribution(all_connections)
        stats['connections_type_totals'] = dict(connections_type_totals.most_common())

    if error_distribution:
        stats['extraction_error_distribution'] = dict(error_distribution.most_common())
    elif 'extraction_error_distribution' in stats:
        del stats['extraction_error_distribution']

    meta['extraction_successful'] = extraction_ok
    meta['extraction_errored'] = extraction_err

    # Print summary
    print(f"Extraction: {extraction_ok} ok, {extraction_err} errors")
    if all_elements:
        es = stats['elements_statistics']
        print(f"Elements: min={es['min']}, median={es['median']}, mean={es['mean']}, max={es['max']}")
        print(f"Elements distribution: {stats['elements_distribution']}")
    if all_connections:
        cs = stats['connections_statistics']
        print(f"Connections: min={cs['min']}, median={cs['median']}, mean={cs['mean']}, max={cs['max']}")
        print(f"Connections distribution: {stats['connections_distribution']}")
    if error_distribution:
        print(f"Extraction errors: {dict(error_distribution.most_common())}")

    print(f"\nSaving: {args.output}")
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print("Done!")


if __name__ == '__main__':
    main()
