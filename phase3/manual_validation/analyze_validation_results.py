#!/usr/bin/env python3
"""
Analyze manual validation results and compute accuracy metrics.

Reads the completed validation_sample.json and computes:
- Classification accuracy (overall, per-type, confusion matrix)
- Element count accuracy (exact match rate, per-type, error magnitude)
- Connection count accuracy (exact match rate, per-type, error analysis)

Outputs:
- Human-readable report to stdout
- JSON summary to validation_summary.json (for visualization scripts and paper)

Usage:
    python3 analyze_validation_results.py manual_validation/validation_sample.json
    python3 analyze_validation_results.py manual_validation/validation_sample.json -o validation_summary.json
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


def load_validation(path: Path) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


# ── Classification ──────────────────────────────────────────────────────────

def compute_classification_metrics(samples):
    types = sorted(set(s['classified_type'] for s in samples))

    correct = sum(1 for s in samples if s['classified_type'] == s['actual_type'])
    total = len(samples)

    # Per-type accuracy (grouped by classified_type — the sampling stratum)
    per_type = {}
    for dtype in types:
        group = [s for s in samples if s['classified_type'] == dtype]
        n_correct = sum(1 for s in group if s['classified_type'] == s['actual_type'])
        per_type[dtype] = {
            'correct': n_correct,
            'total': len(group),
            'accuracy': n_correct / len(group) if group else 0,
        }

    # Confusion matrix: confusion[classified][actual] = count
    confusion = defaultdict(lambda: defaultdict(int))
    for s in samples:
        confusion[s['classified_type']][s['actual_type']] += 1
    confusion = {k: dict(v) for k, v in confusion.items()}

    # List individual misclassifications
    misclassifications = [
        {
            'sample_id': s['sample_id'],
            'filename': s['filename'],
            'classified_type': s['classified_type'],
            'actual_type': s['actual_type'],
            'notes': s.get('notes'),
        }
        for s in samples
        if s['classified_type'] != s['actual_type']
    ]

    return {
        'overall_correct': correct,
        'overall_total': total,
        'overall_accuracy': correct / total,
        'per_type': per_type,
        'confusion_matrix': confusion,
        'types': types,
        'misclassifications': misclassifications,
    }


# ── Element / Connection accuracy (shared logic) ───────────────────────────

def _count_accuracy(samples, correct_key, tool_total_key, actual_total_key,
                    tool_detail_key, actual_detail_key):
    """Compute exact-match accuracy for either elements or connections.

    All timing diagrams (classified_type == 'timing') are excluded per
    validation methodology §4.3: timing diagrams receive classification-only
    validation.
    """
    eligible = [s for s in samples if s['classified_type'] != 'timing']

    correct = sum(1 for s in eligible if s[correct_key])
    total = len(eligible)

    # Per-type (by classified_type)
    types = sorted(set(s['classified_type'] for s in eligible))
    per_type = {}
    for dtype in types:
        group = [s for s in eligible if s['classified_type'] == dtype]
        n_correct = sum(1 for s in group if s[correct_key])
        per_type[dtype] = {
            'correct': n_correct,
            'total': len(group),
            'accuracy': n_correct / len(group) if group else 0,
        }

    # Total-count agreement (totals match even if per-type breakdown differs)
    total_agree = sum(
        1 for s in eligible
        if s[tool_total_key] == s[actual_total_key]
    )

    # Disagreement details
    errors = []
    diffs = []
    overcounts = 0
    undercounts = 0
    for s in eligible:
        if not s[correct_key]:
            diff = s[tool_total_key] - s[actual_total_key]
            if diff > 0:
                overcounts += 1
            elif diff < 0:
                undercounts += 1
            diffs.append(abs(diff))
            errors.append({
                'sample_id': s['sample_id'],
                'filename': s['filename'],
                'classified_type': s['classified_type'],
                'tool_total': s[tool_total_key],
                'actual_total': s[actual_total_key],
                'difference': diff,
                'tool_detail': s[tool_detail_key],
                'actual_detail': s[actual_detail_key],
                'notes': s.get('notes'),
            })

    mean_abs_diff = sum(diffs) / len(diffs) if diffs else 0
    median_abs_diff = sorted(diffs)[len(diffs) // 2] if diffs else 0

    return {
        'overall_correct': correct,
        'overall_total': total,
        'overall_accuracy': correct / total if total else 0,
        'excluded_timing': len(samples) - len(eligible),
        'total_agreement': total_agree,
        'total_agreement_rate': total_agree / total if total else 0,
        'per_type': per_type,
        'errors': errors,
        'overcounts': overcounts,
        'undercounts': undercounts,
        'mean_abs_difference': mean_abs_diff,
        'median_abs_difference': median_abs_diff,
    }


def compute_element_metrics(samples):
    return _count_accuracy(
        samples,
        correct_key='elements_correct',
        tool_total_key='total_elements',
        actual_total_key='actual_elements_count',
        tool_detail_key='elements',
        actual_detail_key='actual_elements',
    )


def compute_connection_metrics(samples):
    return _count_accuracy(
        samples,
        correct_key='connections_correct',
        tool_total_key='total_connections',
        actual_total_key='actual_connections_count',
        tool_detail_key='connections',
        actual_detail_key='actual_connections',
    )


# ── Report ──────────────────────────────────────────────────────────────────

def print_report(classification, elements, connections):
    print("=" * 70)
    print("MANUAL VALIDATION RESULTS")
    print("=" * 70)

    # ── 1. Classification ──
    c = classification
    print(f"\n{'─' * 70}")
    print("1. CLASSIFICATION ACCURACY")
    print(f"{'─' * 70}")
    print(f"\nOverall: {c['overall_correct']}/{c['overall_total']} "
          f"({c['overall_accuracy']:.1%})")

    print(f"\n  {'Type':<15} {'Correct':>8} {'Total':>8} {'Accuracy':>10}")
    print(f"  {'─' * 45}")
    for dtype in c['types']:
        pt = c['per_type'][dtype]
        print(f"  {dtype:<15} {pt['correct']:>8} {pt['total']:>8} "
              f"{pt['accuracy']:>10.1%}")

    if c['misclassifications']:
        print(f"\nMisclassifications ({len(c['misclassifications'])}):")
        for m in c['misclassifications']:
            print(f"  #{m['sample_id']:>3}: {m['classified_type']:>12} "
                  f"-> {m['actual_type']}")

    # Confusion matrix
    types = c['types']
    print(f"\nConfusion matrix (rows = classified, cols = actual):")
    header = f"  {'':>12}" + "".join(f"{t[:7]:>8}" for t in types)
    print(header)
    for row in types:
        line = f"  {row:>12}"
        for col in types:
            n = c['confusion_matrix'].get(row, {}).get(col, 0)
            line += f"{n:>8}" if n > 0 else f"{'·':>8}"
        print(line)

    # ── 2. Elements ──
    _print_count_section("2. ELEMENT COUNT ACCURACY", elements)

    # ── 3. Connections ──
    _print_count_section("3. CONNECTION COUNT ACCURACY", connections)

    print(f"\n{'=' * 70}")


def _print_count_section(title, metrics):
    m = metrics
    print(f"\n{'─' * 70}")
    print(title)
    print(f"{'─' * 70}")

    print(f"\nExact match: {m['overall_correct']}/{m['overall_total']} "
          f"({m['overall_accuracy']:.1%})")
    print(f"  Excluded (timing): {m['excluded_timing']}")
    print(f"  Total-count agreement: {m['total_agreement']}/{m['overall_total']} "
          f"({m['total_agreement_rate']:.1%})")

    if m['errors']:
        print(f"  Direction: {m['overcounts']} overcounts, "
              f"{m['undercounts']} undercounts")
        print(f"  Mean |Δ|: {m['mean_abs_difference']:.1f}   "
              f"Median |Δ|: {m['median_abs_difference']}")

    print(f"\n  {'Type':<15} {'Correct':>8} {'Total':>8} {'Accuracy':>10}")
    print(f"  {'─' * 45}")
    for dtype, pt in sorted(m['per_type'].items()):
        print(f"  {dtype:<15} {pt['correct']:>8} {pt['total']:>8} "
              f"{pt['accuracy']:>10.1%}")

    if m['errors']:
        print(f"\nDisagreements ({len(m['errors'])}):")
        for e in m['errors']:
            d = e['difference']
            tag = "overcount" if d > 0 else "undercount" if d < 0 else "breakdown only"
            print(f"  #{e['sample_id']:>3} ({e['classified_type']:>12}): "
                  f"tool={e['tool_total']:>4}  actual={e['actual_total']:>4}  "
                  f"Δ={d:>+4}  ({tag})")


# ── JSON summary ────────────────────────────────────────────────────────────

def build_summary(classification, elements, connections):
    """Build JSON summary for visualization scripts and paper text."""

    def _slim_errors(errors):
        return [
            {
                'sample_id': e['sample_id'],
                'classified_type': e['classified_type'],
                'tool_total': e['tool_total'],
                'actual_total': e['actual_total'],
                'difference': e['difference'],
            }
            for e in errors
        ]

    def _count_block(m):
        return {
            'overall_accuracy': m['overall_accuracy'],
            'overall_correct': m['overall_correct'],
            'overall_total': m['overall_total'],
            'excluded_timing': m['excluded_timing'],
            'total_agreement_rate': m['total_agreement_rate'],
            'per_type': m['per_type'],
            'overcounts': m['overcounts'],
            'undercounts': m['undercounts'],
            'mean_abs_difference': m['mean_abs_difference'],
            'median_abs_difference': m['median_abs_difference'],
            'error_count': len(m['errors']),
            'errors': _slim_errors(m['errors']),
        }

    return {
        'classification': {
            'overall_accuracy': classification['overall_accuracy'],
            'overall_correct': classification['overall_correct'],
            'overall_total': classification['overall_total'],
            'per_type': classification['per_type'],
            'confusion_matrix': classification['confusion_matrix'],
            'types': classification['types'],
            'misclassifications': [
                {k: v for k, v in m.items() if k != 'notes'}
                for m in classification['misclassifications']
            ],
        },
        'elements': _count_block(elements),
        'connections': _count_block(connections),
    }


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Analyze manual validation results and compute accuracy metrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to completed validation_sample.json",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Path for JSON summary (default: <input_dir>/validation_summary.json)",
    )
    args = parser.parse_args()

    data = load_validation(args.input)
    samples = data['samples']
    print(f"Loaded {len(samples)} samples "
          f"({data['metadata']['total_samples']} expected)", file=sys.stderr)

    classification = compute_classification_metrics(samples)
    elements = compute_element_metrics(samples)
    connections = compute_connection_metrics(samples)

    print_report(classification, elements, connections)

    output_path = args.output or (args.input.parent / 'validation_summary.json')
    summary = build_summary(classification, elements, connections)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nJSON summary written to {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
