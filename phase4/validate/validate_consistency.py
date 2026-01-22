#!/usr/bin/env python3
"""
Cross-validate PlantUML diagram classifications against detected elements.

Identifies misclassifications by comparing the classified diagram type
with the actual elements found in each diagram. Generates a full per-file
validation report with consistency scores, flags, and suggested corrections.

Usage:
    python3 validate_consistency.py --input analysis_complete.json
    python3 validate_consistency.py --input analysis_complete.json --output validation_report.json
    python3 validate_consistency.py --input analysis_complete.json --severity-filter error --only-inconsistent
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Optional tqdm for progress bar
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

# =============================================================================
# CONSTANTS
# =============================================================================

VERSION = "1.0.0"

# Expected elements per diagram type
# - primary: Elements that should be present for this diagram type
# - allowed: Elements that are acceptable but not primary
# - forbidden: Elements that indicate misclassification
EXPECTED_ELEMENTS = {
    'sequence': {
        'primary': ['participant', 'actor', 'boundary', 'control', 'entity',
                    'database', 'collections', 'queue'],
        'allowed': ['box'],
        'forbidden': ['class', 'interface', 'enum', 'abstract class', 'state',
                      'usecase', 'component', 'node', 'artifact']
    },
    'class': {
        'primary': ['class', 'abstract class', 'interface', 'enum',
                    'annotation', 'struct', 'protocol', 'exception', 'metaclass'],
        'allowed': ['package', 'namespace', 'rectangle'],
        'forbidden': ['participant', 'actor', 'state', 'usecase',
                      'node', 'artifact', 'component']
    },
    'usecase': {
        'primary': ['actor', 'usecase'],
        'allowed': ['rectangle', 'package'],
        'forbidden': ['class', 'interface', 'participant', 'state',
                      'component', 'node', 'artifact']
    },
    'component': {
        'primary': ['component', 'interface'],
        'allowed': ['package', 'folder', 'frame', 'cloud', 'database',
                    'node', 'rectangle'],
        'forbidden': ['class', 'participant', 'actor', 'state', 'usecase']
    },
    'deployment': {
        'primary': ['node', 'artifact', 'cloud', 'database', 'storage',
                    'file', 'folder', 'frame', 'component'],
        'allowed': ['rectangle', 'package', 'card', 'agent', 'stack'],
        'forbidden': ['class', 'participant', 'actor', 'usecase', 'state']
    },
    'state': {
        'primary': ['state'],
        'allowed': ['rectangle', 'partition'],
        'forbidden': ['class', 'participant', 'actor', 'usecase',
                      'component', 'node', 'artifact']
    },
    'activity': {
        'primary': ['partition'],
        'allowed': ['rectangle', 'group'],
        'forbidden': ['class', 'participant', 'state', 'usecase',
                      'component', 'node', 'artifact']
    },
    'object': {
        'primary': ['object', 'map', 'json'],
        'allowed': ['package', 'rectangle', 'diamond'],
        'forbidden': ['class', 'interface', 'participant', 'actor',
                      'state', 'usecase', 'component', 'node']
    },
    'timing': {
        'primary': ['participant'],
        'allowed': [],
        'forbidden': ['class', 'interface', 'actor', 'state', 'usecase',
                      'component', 'node', 'artifact']
    }
}

# Severity ordering for filtering
SEVERITY_ORDER = {'error': 3, 'warning': 2, 'info': 1}


# =============================================================================
# CORE VALIDATION FUNCTIONS
# =============================================================================

def calculate_consistency_score(
    primary_type: str,
    elements: Dict[str, int]
) -> float:
    """
    Calculate consistency score (0.0 - 1.0) based on element alignment.

    Scoring weights:
    - Element alignment (40%): primary + allowed elements / total
    - Forbidden penalty (40%): penalize forbidden elements
    - Primary presence (20%): bonus for having primary elements

    Args:
        primary_type: Classified diagram type
        elements: Dictionary mapping element type to count

    Returns:
        Consistency score between 0.0 and 1.0
    """
    # Handle unclassified diagrams (library files, sprites, etc.)
    # These have no features detected, so 0 elements is expected and consistent
    if primary_type == 'unclassified':
        total_elements = sum(elements.values())
        return 1.0 if total_elements == 0 else 0.3

    if primary_type not in EXPECTED_ELEMENTS:
        return 0.0

    expected = EXPECTED_ELEMENTS[primary_type]
    total_elements = sum(elements.values())

    if total_elements == 0:
        # No elements - score depends on diagram type
        # Activity diagrams use flow syntax (:action;, start/stop, swimlanes)
        # rather than declared elements, so 0 elements is expected
        if primary_type == 'activity':
            return 0.9
        # State diagrams often have no declared elements
        elif primary_type == 'state':
            return 0.5
        else:
            return 0.3

    # Calculate element counts by category
    primary_count = sum(elements.get(e, 0) for e in expected['primary'])
    allowed_count = sum(elements.get(e, 0) for e in expected['allowed'])
    forbidden_count = sum(elements.get(e, 0) for e in expected['forbidden'])

    # Alignment score: primary + allowed vs total
    alignment_score = (primary_count + allowed_count) / total_elements

    # Forbidden penalty: any forbidden elements significantly reduce score
    forbidden_penalty = 1.0 - min(1.0, forbidden_count / max(1, total_elements))

    # Primary presence bonus: having at least one primary element
    primary_presence = 1.0 if primary_count > 0 else 0.5

    # Weighted combination
    score = (
        alignment_score * 0.4 +
        forbidden_penalty * 0.4 +
        primary_presence * 0.2
    )

    return round(score, 4)


def infer_type_from_elements(elements: Dict[str, int]) -> Tuple[str, float]:
    """
    Suggest correct diagram type based on element composition.

    Args:
        elements: Dictionary mapping element type to count

    Returns:
        Tuple of (suggested_type, confidence)
    """
    if not elements:
        return ('unknown', 0.0)

    total = sum(elements.values())
    scores: Dict[str, float] = {}

    for dtype, expected in EXPECTED_ELEMENTS.items():
        primary_count = sum(elements.get(e, 0) for e in expected['primary'])
        forbidden_count = sum(elements.get(e, 0) for e in expected['forbidden'])

        # Score based on primary element ratio minus forbidden penalty
        score = (primary_count / total) - (forbidden_count / total * 0.5)
        scores[dtype] = max(0, score)

    if max(scores.values()) == 0:
        return ('unknown', 0.0)

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    # Normalize confidence
    total_score = sum(scores.values())
    confidence = best_score / total_score if total_score > 0 else 0.0

    return (best_type, round(confidence, 4))


def detect_flags(
    primary_type: str,
    confidence: float,
    elements: Dict[str, int],
    consistency_score: float,
    suggested_type: str,
    suggestion_confidence: float
) -> List[Dict[str, Any]]:
    """
    Detect validation flags based on analysis results.

    Args:
        primary_type: Classified diagram type
        confidence: Classification confidence
        elements: Element counts
        consistency_score: Calculated consistency score
        suggested_type: Inferred type from elements
        suggestion_confidence: Confidence of type inference

    Returns:
        List of flag dictionaries with code, severity, and details
    """
    flags = []
    total_elements = sum(elements.values())

    # NO_ELEMENTS check
    # Skip for activity diagrams - they use flow syntax rather than declared elements
    # Skip for unclassified - these are library/sprite files with no diagram content
    if total_elements == 0:
        if primary_type not in ('activity', 'unclassified'):
            flags.append({
                'code': 'NO_ELEMENTS',
                'severity': 'warning',
                'details': f'No elements detected for {primary_type} diagram'
            })
        return flags  # Can't do further element analysis

    expected = EXPECTED_ELEMENTS.get(primary_type, {})

    # FORBIDDEN_ELEMENTS check
    forbidden = expected.get('forbidden', [])
    found_forbidden = {e: c for e, c in elements.items() if e in forbidden}
    if found_forbidden:
        flags.append({
            'code': 'FORBIDDEN_ELEMENTS',
            'severity': 'error',
            'details': f'Found forbidden elements: {found_forbidden}'
        })

    # MISSING_PRIMARY_ELEMENTS check
    primary = expected.get('primary', [])
    primary_count = sum(elements.get(e, 0) for e in primary)
    if primary_count == 0 and primary:
        primary_preview = primary[:3]
        flags.append({
            'code': 'MISSING_PRIMARY_ELEMENTS',
            'severity': 'warning',
            'details': f'No primary elements ({primary_preview}...) found'
        })

    # TYPE_MISMATCH check
    if suggested_type != primary_type and suggested_type != 'unknown' and suggestion_confidence > 0.5:
        flags.append({
            'code': 'TYPE_MISMATCH',
            'severity': 'error',
            'details': f'Elements suggest {suggested_type} (conf: {suggestion_confidence:.2f}) not {primary_type}'
        })

    # HIGH_CONFIDENCE_MISMATCH check
    if confidence >= 0.7 and consistency_score < 0.5:
        flags.append({
            'code': 'HIGH_CONFIDENCE_MISMATCH',
            'severity': 'error',
            'details': f'High classification confidence ({confidence:.2f}) but low consistency ({consistency_score:.2f})'
        })

    # LOW_CONFIDENCE check
    if confidence < 0.5:
        flags.append({
            'code': 'LOW_CONFIDENCE',
            'severity': 'info',
            'details': f'Classification confidence {confidence:.2f} below 0.5 threshold'
        })

    # MULTI_TYPE_AMBIGUOUS check - only if no other serious flags
    error_flags = [f for f in flags if f['severity'] == 'error']
    if consistency_score < 0.7 and len(error_flags) == 0:
        flags.append({
            'code': 'MULTI_TYPE_AMBIGUOUS',
            'severity': 'info',
            'details': 'Elements not strongly aligned with any single type'
        })

    return flags


# =============================================================================
# PROCESSING FUNCTIONS
# =============================================================================

def validate_file(entry: Dict[str, Any], threshold: float) -> Dict[str, Any]:
    """
    Validate a single file entry from analysis_complete.json.

    Args:
        entry: File entry containing primary_type, confidence, elements
        threshold: Minimum consistency score to consider valid

    Returns:
        Validation result dictionary
    """
    primary_type = entry.get('primary_type', '')
    confidence = entry.get('confidence', 0.0)
    elements = entry.get('elements', {})

    # Handle None confidence (non-UML diagrams)
    if confidence is None:
        confidence = 0.0

    # Calculate metrics
    consistency_score = calculate_consistency_score(primary_type, elements)
    suggested_type, suggestion_confidence = infer_type_from_elements(elements)

    # Detect flags
    flags = detect_flags(
        primary_type, confidence, elements,
        consistency_score, suggested_type, suggestion_confidence
    )

    # Determine if consistent
    has_error_flags = any(f['severity'] == 'error' for f in flags)
    is_consistent = consistency_score >= threshold and not has_error_flags

    return {
        'primary_type': primary_type,
        'confidence': confidence,
        'elements': elements,
        'total_elements': sum(elements.values()),
        'consistency_score': consistency_score,
        'suggested_type': suggested_type,
        'suggestion_confidence': suggestion_confidence,
        'flags': flags,
        'is_consistent': is_consistent
    }


def build_confusion_matrix(results: Dict[str, Dict]) -> Dict[str, Dict[str, int]]:
    """
    Build confusion matrix: classified type vs suggested type.

    Args:
        results: Validation results dictionary

    Returns:
        Nested dict: {classified_type: {suggested_type: count}}
    """
    matrix: Dict[str, Dict[str, int]] = {}

    for filename, result in results.items():
        classified = result['primary_type']
        suggested = result['suggested_type']

        if not classified:
            continue

        if classified not in matrix:
            matrix[classified] = {}
        matrix[classified][suggested] = matrix[classified].get(suggested, 0) + 1

    return matrix


def generate_statistics(
    results: Dict[str, Dict],
    threshold: float,
    start_time: datetime,
    end_time: datetime
) -> Dict[str, Any]:
    """
    Generate summary statistics from validation results.

    Args:
        results: Validation results dictionary
        threshold: Consistency threshold used
        start_time: Processing start time
        end_time: Processing end time

    Returns:
        Statistics dictionary
    """
    total = len(results)
    consistent_count = sum(1 for r in results.values() if r['is_consistent'])

    # Count flags
    by_flag: Dict[str, int] = {}
    by_severity: Dict[str, int] = {'error': 0, 'warning': 0, 'info': 0}

    for result in results.values():
        for flag in result['flags']:
            by_flag[flag['code']] = by_flag.get(flag['code'], 0) + 1
            by_severity[flag['severity']] += 1

    # Average consistency score
    avg_score = sum(r['consistency_score'] for r in results.values()) / total if total > 0 else 0

    # Processing time
    duration = end_time - start_time
    processing_time = str(duration).split('.')[0]

    return {
        'total_files': total,
        'consistent': consistent_count,
        'inconsistent': total - consistent_count,
        'consistency_rate': round(consistent_count / total, 4) if total > 0 else 0,
        'by_flag': dict(sorted(by_flag.items(), key=lambda x: -x[1])),
        'by_severity': by_severity,
        'confusion_matrix': build_confusion_matrix(results),
        'average_consistency_score': round(avg_score, 4),
        'processing_time': processing_time
    }


def process_analysis(input_path: Path, threshold: float) -> Dict[str, Any]:
    """
    Main processing function - validate all files in analysis_complete.json.

    Args:
        input_path: Path to analysis_complete.json
        threshold: Minimum consistency score to consider valid

    Returns:
        Complete validation output dictionary
    """
    start_time = datetime.now()

    print(f"Loading analysis from {input_path}...", file=sys.stderr)
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    source_results = data.get('results', {})
    print(f"Found {len(source_results)} files to validate", file=sys.stderr)

    validation_results: Dict[str, Dict] = {}

    # Progress iterator
    if HAS_TQDM:
        iterator = tqdm(source_results.items(), desc="Validating", file=sys.stderr)
    else:
        iterator = source_results.items()
        print("Processing...", file=sys.stderr)

    for idx, (filename, entry) in enumerate(iterator):
        validation_results[filename] = validate_file(entry, threshold)

        # Progress update without tqdm
        if not HAS_TQDM and (idx + 1) % 10000 == 0:
            print(f"Processed {idx + 1}/{len(source_results)} files...", file=sys.stderr)

    end_time = datetime.now()

    return {
        'metadata': {
            'version': VERSION,
            'timestamp': datetime.now().isoformat(),
            'source_file': str(input_path),
            'total_validated': len(validation_results),
            'validation_threshold': threshold
        },
        'statistics': generate_statistics(validation_results, threshold, start_time, end_time),
        'validation_results': validation_results
    }


# =============================================================================
# CLI
# =============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Cross-validate diagram classifications against detected elements",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 validate_consistency.py --input analysis_complete.json
  python3 validate_consistency.py --input analysis_complete.json --output validation_report.json
  python3 validate_consistency.py --input analysis_complete.json --consistency-threshold 0.6
  python3 validate_consistency.py --input analysis_complete.json --severity-filter error --only-inconsistent

Output:
  JSON file with per-file validation results and summary statistics including:
  - Consistency score per file (0.0-1.0)
  - Suggested type when elements don't match classification
  - Validation flags (TYPE_MISMATCH, FORBIDDEN_ELEMENTS, etc.)
  - Confusion matrix (classified type vs suggested type)
        """
    )

    parser.add_argument(
        "--input", "-i",
        type=Path,
        required=True,
        help="Path to analysis_complete.json"
    )

    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("validation_report.json"),
        help="Output JSON file (default: validation_report.json)"
    )

    parser.add_argument(
        "--consistency-threshold", "-t",
        type=float,
        default=0.5,
        help="Minimum consistency score to consider valid (default: 0.5)"
    )

    parser.add_argument(
        "--severity-filter",
        choices=['error', 'warning', 'info', 'all'],
        default='all',
        help="Only include files with flags of this severity or higher"
    )

    parser.add_argument(
        "--only-inconsistent",
        action="store_true",
        help="Only output files flagged as inconsistent"
    )

    args = parser.parse_args()

    # Validate input file
    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Process validation
    print("=" * 60, file=sys.stderr)
    print("PlantUML Classification Validation", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"Input: {args.input}", file=sys.stderr)
    print(f"Output: {args.output}", file=sys.stderr)
    print(f"Threshold: {args.consistency_threshold}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    output = process_analysis(args.input, args.consistency_threshold)

    # Filter results if requested
    if args.only_inconsistent:
        output['validation_results'] = {
            k: v for k, v in output['validation_results'].items()
            if not v['is_consistent']
        }
        output['metadata']['filtered'] = 'only_inconsistent'

    if args.severity_filter != 'all':
        min_severity = SEVERITY_ORDER[args.severity_filter]
        output['validation_results'] = {
            k: v for k, v in output['validation_results'].items()
            if any(SEVERITY_ORDER[f['severity']] >= min_severity for f in v['flags'])
        }
        output['metadata']['severity_filter'] = args.severity_filter

    # Write output
    print(f"\nWriting results to {args.output}...", file=sys.stderr)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Print summary
    stats = output['statistics']
    print("\n" + "=" * 60, file=sys.stderr)
    print("Validation Summary", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"Total files: {stats['total_files']}", file=sys.stderr)
    print(f"Consistent: {stats['consistent']} ({stats['consistency_rate']*100:.1f}%)", file=sys.stderr)
    print(f"Inconsistent: {stats['inconsistent']}", file=sys.stderr)
    print(f"\nFlags by severity:", file=sys.stderr)
    for severity in ['error', 'warning', 'info']:
        count = stats['by_severity'].get(severity, 0)
        print(f"  {severity}: {count}", file=sys.stderr)
    print(f"\nFlags by type:", file=sys.stderr)
    for flag_code, count in stats['by_flag'].items():
        print(f"  {flag_code}: {count}", file=sys.stderr)
    print(f"\nAverage consistency score: {stats['average_consistency_score']:.4f}", file=sys.stderr)
    print(f"Processing time: {stats['processing_time']}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)


if __name__ == "__main__":
    main()
