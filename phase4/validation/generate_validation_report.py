#!/usr/bin/env python3
"""
Generate validation report from LLM classification results.

Computes confidence-based validation metrics without requiring element data.

Usage:
    python3 generate_validation_report.py --input final_merged_results.json --output validation_report.json
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from collections import defaultdict


def compute_statistics(classifications: Dict[str, Dict]) -> Dict[str, Any]:
    """
    Compute validation statistics from classification results.

    Args:
        classifications: Dictionary mapping filename to classification data

    Returns:
        Statistics dictionary
    """
    total = len(classifications)

    # Confidence distribution
    confidence_bins = defaultdict(int)
    confidence_sum = 0.0

    # Per-type statistics
    by_type = defaultdict(lambda: {'count': 0, 'confidence_sum': 0.0, 'high_conf': 0, 'low_conf': 0})

    # Confidence thresholds
    HIGH_CONF = 0.8
    LOW_CONF = 0.5

    for filename, data in classifications.items():
        conf = data.get('confidence', 0.0)
        if conf is None:
            conf = 0.0
        primary_type = data.get('primary_type', 'unknown')

        confidence_sum += conf

        # Bin confidence scores
        if conf >= 0.9:
            confidence_bins['0.90-1.00'] += 1
        elif conf >= 0.8:
            confidence_bins['0.80-0.89'] += 1
        elif conf >= 0.7:
            confidence_bins['0.70-0.79'] += 1
        elif conf >= 0.6:
            confidence_bins['0.60-0.69'] += 1
        elif conf >= 0.5:
            confidence_bins['0.50-0.59'] += 1
        else:
            confidence_bins['<0.50'] += 1

        # Per-type stats
        by_type[primary_type]['count'] += 1
        by_type[primary_type]['confidence_sum'] += conf
        if conf >= HIGH_CONF:
            by_type[primary_type]['high_conf'] += 1
        elif conf < LOW_CONF:
            by_type[primary_type]['low_conf'] += 1

    # Compute averages
    avg_confidence = confidence_sum / total if total > 0 else 0

    type_stats = {}
    for dtype, stats in by_type.items():
        count = stats['count']
        type_stats[dtype] = {
            'count': count,
            'percentage': round(count / total * 100, 2),
            'avg_confidence': round(stats['confidence_sum'] / count, 4) if count > 0 else 0,
            'high_confidence_count': stats['high_conf'],
            'high_confidence_pct': round(stats['high_conf'] / count * 100, 2) if count > 0 else 0,
            'low_confidence_count': stats['low_conf'],
            'low_confidence_pct': round(stats['low_conf'] / count * 100, 2) if count > 0 else 0
        }

    # Count high-confidence classifications (proxy for classification quality)
    high_conf_count = sum(1 for d in classifications.values()
                         if (d.get('confidence') or 0) >= HIGH_CONF)

    return {
        'total_files': total,
        'average_confidence': round(avg_confidence, 4),
        'high_confidence_count': high_conf_count,
        'high_confidence_rate': round(high_conf_count / total * 100, 2) if total > 0 else 0,
        'confidence_distribution': dict(sorted(confidence_bins.items())),
        'by_type': dict(sorted(type_stats.items(), key=lambda x: -x[1]['count']))
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate validation report from LLM classification results"
    )

    parser.add_argument(
        "--input", "-i",
        type=Path,
        required=True,
        help="Path to final_merged_results.json"
    )

    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("validation_report.json"),
        help="Output JSON file (default: validation_report.json)"
    )

    args = parser.parse_args()

    # Load classifications
    print(f"Loading classifications from {args.input}...", file=sys.stderr)
    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)

    classifications = data.get('classifications', {})
    print(f"Loaded {len(classifications)} classifications", file=sys.stderr)

    # Compute statistics
    stats = compute_statistics(classifications)

    # Build report
    report = {
        'metadata': {
            'version': '1.0.0',
            'timestamp': datetime.now().isoformat(),
            'source_file': str(args.input),
            'total_validated': stats['total_files']
        },
        'statistics': stats,
        'validation_summary': {
            'classification_confidence': {
                'average': stats['average_confidence'],
                'high_confidence_threshold': 0.8,
                'high_confidence_rate': f"{stats['high_confidence_rate']}%",
                'interpretation': 'Percentage of classifications with confidence >= 0.8'
            },
            'coverage': {
                'diagram_types_classified': len([t for t in stats['by_type'] if t != 'unclassified']),
                'unclassified_count': stats['by_type'].get('unclassified', {}).get('count', 0),
                'unclassified_rate': f"{stats['by_type'].get('unclassified', {}).get('percentage', 0)}%"
            }
        }
    }

    # Write report
    print(f"Writing validation report to {args.output}...", file=sys.stderr)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Print summary
    print("\n" + "=" * 60, file=sys.stderr)
    print("Validation Report Summary", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"Total files: {stats['total_files']}", file=sys.stderr)
    print(f"Average confidence: {stats['average_confidence']:.4f}", file=sys.stderr)
    print(f"High confidence (>=0.8): {stats['high_confidence_count']} ({stats['high_confidence_rate']}%)", file=sys.stderr)
    print(f"\nConfidence distribution:", file=sys.stderr)
    for bucket, count in sorted(stats['confidence_distribution'].items()):
        pct = count / stats['total_files'] * 100
        print(f"  {bucket}: {count} ({pct:.1f}%)", file=sys.stderr)
    print("=" * 60, file=sys.stderr)


if __name__ == "__main__":
    main()
