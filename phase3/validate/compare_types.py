#!/usr/bin/env python3
"""
Compare LLM-classified primary_type vs PlantUML compiler parsed_type.

Reads the classification JSON and a JSONL stats file (from DiagramStatsExtractor)
to compare LLM primary_type against the compiler's diagram_type. Reports
match/mismatch statistics, a confusion matrix, per-type accuracy, and
taxonomy-adjusted accuracy accounting for the compiler's coarser type system.

The PlantUML compiler uses a coarser taxonomy than the LLM:
  - compiler "component" = LLM {component, usecase, deployment}
    (all use UmlDiagramType.DESCRIPTION internally)
  - compiler "class" = LLM {class, object}
    (object diagrams are a subtype of class diagrams)
  - sequence, activity, state map 1:1

Usage:
    python3 compare_types.py -i classifications.json -s element_connection_counts.json
    python3 compare_types.py -i classifications.json -s element_connection_counts.json -o report.json
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Maps LLM primary_type to the compiler's equivalent parsed_type.
# Types not listed here have no known mapping (e.g. "timing", "unclassified").
TAXONOMY_MAP = {
    'class': 'class',
    'object': 'class',
    'sequence': 'sequence',
    'activity': 'activity',
    'state': 'state',
    'component': 'component',
    'usecase': 'component',
    'deployment': 'component',
}


def load_stats_jsonl(stats_path: Path) -> dict:
    """
    Parse JSONL file into a dict mapping filename -> diagram_type.
    """
    parsed_types = {}
    with open(stats_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                file_key = record.get('file', '')
                diagram_type = record.get('diagram_type')
                if file_key and diagram_type:
                    parsed_types[file_key] = diagram_type
            except json.JSONDecodeError:
                continue
    print(f"Loaded {len(parsed_types)} parsed types from stats JSONL")
    return parsed_types


def analyze_raw(classifications: dict) -> dict:
    """
    Raw (strict) comparison: primary_type must equal parsed_type exactly.

    Returns:
        Report section for raw comparison
    """
    matched = 0
    mismatched = 0
    skipped_no_parsed = 0
    skipped_no_primary = 0
    total = len(classifications)

    confusion = Counter()
    primary_hits = Counter()
    primary_totals = Counter()
    parsed_hits = Counter()
    parsed_totals = Counter()
    mismatch_examples = defaultdict(list)

    for filename, entry in classifications.items():
        primary = entry.get('primary_type')
        parsed = entry.get('parsed_type')

        if parsed is None:
            skipped_no_parsed += 1
            continue
        if primary is None:
            skipped_no_primary += 1
            continue

        confusion[(primary, parsed)] += 1
        primary_totals[primary] += 1
        parsed_totals[parsed] += 1

        if primary == parsed:
            matched += 1
            primary_hits[primary] += 1
            parsed_hits[parsed] += 1
        else:
            mismatched += 1
            mismatch_examples[(primary, parsed)].append(filename)

    comparable = matched + mismatched

    # Confusion matrix
    all_types = sorted(set(
        [k[0] for k in confusion.keys()] +
        [k[1] for k in confusion.keys()]
    ))
    confusion_matrix = {}
    for primary in all_types:
        row = {}
        for parsed in all_types:
            count = confusion.get((primary, parsed), 0)
            if count > 0:
                row[parsed] = count
        if row:
            confusion_matrix[primary] = row

    per_primary = {}
    for t in sorted(primary_totals.keys()):
        total_t = primary_totals[t]
        hits_t = primary_hits.get(t, 0)
        per_primary[t] = {
            'total': total_t,
            'matched': hits_t,
            'accuracy': round(hits_t / total_t * 100, 1) if total_t > 0 else 0
        }

    per_parsed = {}
    for t in sorted(parsed_totals.keys()):
        total_t = parsed_totals[t]
        hits_t = parsed_hits.get(t, 0)
        per_parsed[t] = {
            'total': total_t,
            'matched': hits_t,
            'accuracy': round(hits_t / total_t * 100, 1) if total_t > 0 else 0
        }

    top_mismatches = []
    for (primary, parsed), filenames in sorted(
        mismatch_examples.items(), key=lambda x: len(x[1]), reverse=True
    ):
        top_mismatches.append({
            'primary_type': primary,
            'parsed_type': parsed,
            'count': len(filenames),
            'examples': filenames[:3]
        })

    return {
        'summary': {
            'total': total,
            'comparable': comparable,
            'matched': matched,
            'mismatched': mismatched,
            'accuracy': round(matched / comparable * 100, 2) if comparable > 0 else 0,
            'skipped_no_parsed_type': skipped_no_parsed,
            'skipped_no_primary_type': skipped_no_primary,
        },
        'per_primary_type': per_primary,
        'per_parsed_type': per_parsed,
        'confusion_matrix': confusion_matrix,
        'top_mismatches': top_mismatches,
    }


def analyze_adjusted(classifications: dict) -> dict:
    """
    Taxonomy-adjusted comparison: maps LLM types to compiler equivalents
    before comparing, and excludes entries with no known mapping
    (e.g. "unclassified", "timing").

    Returns:
        Report section for adjusted comparison
    """
    matched = 0
    mismatched = 0
    skipped_no_parsed = 0
    skipped_unmapped = 0
    total = len(classifications)

    # Adjusted confusion: (mapped_primary, parsed) -> count
    confusion = Counter()
    # Per mapped category
    category_hits = Counter()
    category_totals = Counter()
    mismatch_examples = defaultdict(list)

    for filename, entry in classifications.items():
        primary = entry.get('primary_type')
        parsed = entry.get('parsed_type')

        if parsed is None:
            skipped_no_parsed += 1
            continue

        mapped = TAXONOMY_MAP.get(primary)
        if mapped is None:
            skipped_unmapped += 1
            continue

        confusion[(mapped, parsed)] += 1
        category_totals[mapped] += 1

        if mapped == parsed:
            matched += 1
            category_hits[mapped] += 1
        else:
            mismatched += 1
            mismatch_examples[(primary, mapped, parsed)].append(filename)

    comparable = matched + mismatched

    # Per-category accuracy
    per_category = {}
    for t in sorted(category_totals.keys()):
        total_t = category_totals[t]
        hits_t = category_hits.get(t, 0)
        per_category[t] = {
            'total': total_t,
            'matched': hits_t,
            'accuracy': round(hits_t / total_t * 100, 1) if total_t > 0 else 0,
            'llm_types': sorted([k for k, v in TAXONOMY_MAP.items() if v == t])
        }

    # Adjusted confusion matrix
    all_types = sorted(set(
        [k[0] for k in confusion.keys()] +
        [k[1] for k in confusion.keys()]
    ))
    confusion_matrix = {}
    for mapped in all_types:
        row = {}
        for parsed in all_types:
            count = confusion.get((mapped, parsed), 0)
            if count > 0:
                row[parsed] = count
        if row:
            confusion_matrix[mapped] = row

    # Top mismatches with original LLM type preserved
    top_mismatches = []
    for (primary, mapped, parsed), filenames in sorted(
        mismatch_examples.items(), key=lambda x: len(x[1]), reverse=True
    ):
        top_mismatches.append({
            'primary_type': primary,
            'mapped_to': mapped,
            'parsed_type': parsed,
            'count': len(filenames),
            'examples': filenames[:3]
        })

    return {
        'summary': {
            'total': total,
            'comparable': comparable,
            'matched': matched,
            'mismatched': mismatched,
            'accuracy': round(matched / comparable * 100, 2) if comparable > 0 else 0,
            'skipped_no_parsed_type': skipped_no_parsed,
            'skipped_unmapped_primary': skipped_unmapped,
        },
        'taxonomy_map': TAXONOMY_MAP,
        'per_category': per_category,
        'confusion_matrix': confusion_matrix,
        'top_mismatches': top_mismatches,
    }


def analyze(data: dict, parsed_types: dict) -> dict:
    """
    Full analysis: raw comparison + taxonomy-adjusted comparison.

    Injects parsed_type from the stats JSONL lookup into each classification
    entry before running analysis.
    """
    classifications = data.get('classifications', {})

    # Inject parsed_type from stats JSONL
    injected = 0
    for filename, entry in classifications.items():
        pt = parsed_types.get(filename)
        if pt is not None:
            entry['parsed_type'] = pt
            injected += 1
    print(f"Injected parsed_type for {injected} / {len(classifications)} entries")

    return {
        'raw': analyze_raw(classifications),
        'adjusted': analyze_adjusted(classifications),
    }


def print_report(report: dict):
    """Print a human-readable report to stdout."""

    # --- Raw section ---
    raw = report['raw']
    s = raw['summary']
    print("=" * 70)
    print("  RAW COMPARISON (strict type equality)")
    print("=" * 70)
    print(f"  Total entries:          {s['total']}")
    print(f"  Comparable (both set):  {s['comparable']}")
    print(f"  Matched:                {s['matched']}")
    print(f"  Mismatched:             {s['mismatched']}")
    print(f"  Accuracy:               {s['accuracy']}%")
    print(f"  Skipped (no parsed):    {s['skipped_no_parsed_type']}")
    print(f"  Skipped (no primary):   {s['skipped_no_primary_type']}")

    print("\n--- Per primary_type (LLM) accuracy ---")
    for t, info in sorted(raw['per_primary_type'].items(), key=lambda x: x[1]['total'], reverse=True):
        print(f"  {t:20s}  {info['matched']:5d} / {info['total']:5d}  ({info['accuracy']}%)")

    print("\n--- Per parsed_type (compiler) accuracy ---")
    for t, info in sorted(raw['per_parsed_type'].items(), key=lambda x: x[1]['total'], reverse=True):
        print(f"  {t:20s}  {info['matched']:5d} / {info['total']:5d}  ({info['accuracy']}%)")

    print("\n--- Confusion matrix (rows=primary_type, cols=parsed_type) ---")
    matrix = raw['confusion_matrix']
    all_cols = sorted(set(col for row in matrix.values() for col in row.keys()))
    header = f"  {'':20s}  " + "  ".join(f"{c:>8s}" for c in all_cols)
    print(header)
    print("  " + "-" * (len(header) - 2))
    for primary in sorted(matrix.keys()):
        row_vals = "  ".join(f"{matrix[primary].get(c, '.'):>8}" for c in all_cols)
        print(f"  {primary:20s}  {row_vals}")

    print("\n--- Top mismatches ---")
    for m in raw['top_mismatches'][:15]:
        examples = ", ".join(m['examples'])
        print(f"  {m['primary_type']:15s} -> {m['parsed_type']:15s}  x{m['count']:5d}   e.g. {examples}")

    # --- Adjusted section ---
    adj = report['adjusted']
    s = adj['summary']
    print()
    print("=" * 70)
    print("  ADJUSTED COMPARISON (taxonomy-mapped)")
    print("  compiler class     = LLM {class, object}")
    print("  compiler component = LLM {component, usecase, deployment}")
    print("  compiler sequence  = LLM {sequence}")
    print("  compiler activity  = LLM {activity}")
    print("  compiler state     = LLM {state}")
    print("  excluded: unclassified, timing (no compiler equivalent)")
    print("=" * 70)
    print(f"  Total entries:          {s['total']}")
    print(f"  Comparable (mapped):    {s['comparable']}")
    print(f"  Matched:                {s['matched']}")
    print(f"  Mismatched:             {s['mismatched']}")
    print(f"  Adjusted accuracy:      {s['accuracy']}%")
    print(f"  Skipped (no parsed):    {s['skipped_no_parsed_type']}")
    print(f"  Skipped (unmapped):     {s['skipped_unmapped_primary']}")

    print("\n--- Per mapped category accuracy ---")
    for t, info in sorted(adj['per_category'].items(), key=lambda x: x[1]['total'], reverse=True):
        llm_types = ", ".join(info['llm_types'])
        print(f"  {t:15s}  {info['matched']:5d} / {info['total']:5d}  ({info['accuracy']}%)  <- {llm_types}")

    print("\n--- Adjusted confusion matrix (rows=mapped LLM, cols=parsed_type) ---")
    matrix = adj['confusion_matrix']
    all_cols = sorted(set(col for row in matrix.values() for col in row.keys()))
    header = f"  {'':15s}  " + "  ".join(f"{c:>10s}" for c in all_cols)
    print(header)
    print("  " + "-" * (len(header) - 2))
    for mapped in sorted(matrix.keys()):
        row_vals = "  ".join(f"{matrix[mapped].get(c, '.'):>10}" for c in all_cols)
        print(f"  {mapped:15s}  {row_vals}")

    print("\n--- Top adjusted mismatches ---")
    for m in adj['top_mismatches'][:15]:
        examples = ", ".join(m['examples'])
        print(f"  {m['primary_type']:15s} ({m['mapped_to']:>10s}) -> {m['parsed_type']:10s}  x{m['count']:5d}   e.g. {examples}")


def main():
    parser = argparse.ArgumentParser(
        description='Compare LLM primary_type vs PlantUML compiler parsed_type',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 compare_types.py -i classifications.json -s element_connection_counts.json
  python3 compare_types.py -i classifications.json -s element_connection_counts.json -o report.json
        """
    )

    parser.add_argument(
        '-i', '--input',
        type=Path,
        required=True,
        help='Input classification JSON with primary_type'
    )

    parser.add_argument(
        '-s', '--stats',
        type=Path,
        required=True,
        help='JSONL file with diagram_type from DiagramStatsExtractor'
    )

    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Optional: save report as JSON'
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if not args.stats.exists():
        print(f"Error: Stats JSONL file not found: {args.stats}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading: {args.input}")
    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)

    parsed_types = load_stats_jsonl(args.stats)
    report = analyze(data, parsed_types)
    print_report(report)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {args.output}")


if __name__ == '__main__':
    main()
