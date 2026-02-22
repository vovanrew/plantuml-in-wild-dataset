#!/usr/bin/env python3
"""
Analyze manual validation results from CSV and generate report for methodology.

Usage:
    python3 analyze_manual_validation.py --input manual_validation_sample_100.csv
    python3 analyze_manual_validation.py --input manual_validation_sample_100.csv --output validation_analysis.json
    python3 analyze_manual_validation.py --input manual_validation_sample_100.csv --visualize
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Tuple


def load_csv(path: Path) -> List[Dict[str, str]]:
    """Load validation CSV file."""
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    return records


def parse_boolean(value: str) -> bool | None:
    """Parse boolean values from CSV (TRUE/FALSE/N/A)."""
    value = value.strip().upper()
    if value in ('TRUE', 'YES', '1'):
        return True
    elif value in ('FALSE', 'NO', '0'):
        return False
    elif value in ('N/A', 'NA', ''):
        return None
    return None


def compute_classification_accuracy(records: List[Dict]) -> Dict[str, Any]:
    """Compute overall and per-type classification accuracy."""
    total = 0
    correct = 0
    per_type = defaultdict(lambda: {'correct': 0, 'total': 0})

    for r in records:
        classified_type = r.get('classified_type', '').strip()
        is_correct = parse_boolean(r.get('classification_correct', ''))

        if is_correct is not None:
            total += 1
            per_type[classified_type]['total'] += 1

            if is_correct:
                correct += 1
                per_type[classified_type]['correct'] += 1

    # Calculate percentages
    overall_accuracy = (correct / total * 100) if total > 0 else 0

    per_type_accuracy = {}
    for dtype, counts in sorted(per_type.items()):
        acc = (counts['correct'] / counts['total'] * 100) if counts['total'] > 0 else 0
        per_type_accuracy[dtype] = {
            'correct': counts['correct'],
            'total': counts['total'],
            'accuracy_percent': round(acc, 1)
        }

    return {
        'total_samples': total,
        'correct_classifications': correct,
        'incorrect_classifications': total - correct,
        'overall_accuracy_percent': round(overall_accuracy, 1),
        'per_type_accuracy': per_type_accuracy
    }


def compute_confusion_matrix(records: List[Dict]) -> Dict[str, Any]:
    """Compute confusion matrix for misclassifications."""
    confusion_pairs = []
    misclassifications = []

    for r in records:
        is_correct = parse_boolean(r.get('classification_correct', ''))

        if is_correct is False:
            classified = r.get('classified_type', '').strip()
            actual = r.get('correct_type', '').strip()
            filename = r.get('filename', '')
            notes = r.get('notes', '')

            misclassifications.append({
                'filename': filename,
                'classified_as': classified,
                'actual_type': actual,
                'notes': notes
            })
            confusion_pairs.append((classified, actual))

    # Count confusion pairs
    pair_counts = defaultdict(int)
    for classified, actual in confusion_pairs:
        pair_counts[(classified, actual)] += 1

    confusion_summary = [
        {'classified_as': c, 'actual_type': a, 'count': count}
        for (c, a), count in sorted(pair_counts.items(), key=lambda x: -x[1])
    ]

    return {
        'total_errors': len(misclassifications),
        'confusion_summary': confusion_summary,
        'misclassified_files': misclassifications
    }


def compute_real_world_analysis(records: List[Dict]) -> Dict[str, Any]:
    """Analyze real-world vs tutorial/learning content."""
    real_world_count = 0
    not_real_world_count = 0
    na_count = 0

    by_type = defaultdict(lambda: {'real': 0, 'not_real': 0, 'na': 0})

    for r in records:
        classified_type = r.get('classified_type', '').strip()
        is_real = r.get('is_real_world_diagram', '').strip().upper()

        if is_real in ('TRUE', 'YES', '1'):
            real_world_count += 1
            by_type[classified_type]['real'] += 1
        elif is_real in ('FALSE', 'NO', '0'):
            not_real_world_count += 1
            by_type[classified_type]['not_real'] += 1
        else:  # N/A
            na_count += 1
            by_type[classified_type]['na'] += 1

    # Calculate percentages (excluding N/A)
    classifiable = real_world_count + not_real_world_count
    real_world_percent = (real_world_count / classifiable * 100) if classifiable > 0 else 0

    # Per-type percentages
    by_type_with_percent = {}
    for dtype, counts in sorted(by_type.items()):
        type_classifiable = counts['real'] + counts['not_real']
        pct = (counts['real'] / type_classifiable * 100) if type_classifiable > 0 else None
        by_type_with_percent[dtype] = {
            'real_world': counts['real'],
            'not_real_world': counts['not_real'],
            'not_applicable': counts['na'],
            'real_world_percent': round(pct, 1) if pct is not None else None
        }

    return {
        'real_world': real_world_count,
        'not_real_world': not_real_world_count,
        'not_applicable': na_count,
        'real_world_percent': round(real_world_percent, 1),
        'by_type': by_type_with_percent
    }


def compute_logical_correctness(records: List[Dict]) -> Dict[str, Any]:
    """Analyze logical correctness of diagrams."""
    correct = 0
    incorrect = 0
    na = 0

    for r in records:
        is_logical = r.get('logically_correct', '').strip().upper()

        if is_logical in ('TRUE', 'YES', '1'):
            correct += 1
        elif is_logical in ('FALSE', 'NO', '0'):
            incorrect += 1
        else:
            na += 1

    classifiable = correct + incorrect
    correct_percent = (correct / classifiable * 100) if classifiable > 0 else 0

    return {
        'logically_correct': correct,
        'logically_incorrect': incorrect,
        'not_applicable': na,
        'logical_correctness_percent': round(correct_percent, 1)
    }


def compute_confidence_analysis(records: List[Dict]) -> Dict[str, Any]:
    """Analyze relationship between confidence and accuracy."""
    correct_confidences = []
    incorrect_confidences = []

    for r in records:
        is_correct = parse_boolean(r.get('classification_correct', ''))
        try:
            confidence = float(r.get('confidence', 0))
        except ValueError:
            continue

        if is_correct is True:
            correct_confidences.append(confidence)
        elif is_correct is False:
            incorrect_confidences.append(confidence)

    avg_correct = sum(correct_confidences) / len(correct_confidences) if correct_confidences else 0
    avg_incorrect = sum(incorrect_confidences) / len(incorrect_confidences) if incorrect_confidences else 0

    return {
        'avg_confidence_correct': round(avg_correct, 3),
        'avg_confidence_incorrect': round(avg_incorrect, 3),
        'correct_samples': len(correct_confidences),
        'incorrect_samples': len(incorrect_confidences)
    }


def categorize_errors(confusion: Dict) -> Dict[str, Any]:
    """Categorize misclassification errors into patterns."""
    categories = {
        'component_deployment_confusion': [],
        'sequence_activity_confusion': [],
        'object_overassignment': [],
        'other': []
    }

    for item in confusion.get('misclassified_files', []):
        classified = item['classified_as']
        actual = item['actual_type']

        if {classified, actual} == {'component', 'deployment'}:
            categories['component_deployment_confusion'].append(item)
        elif {classified, actual} == {'sequence', 'activity'}:
            categories['sequence_activity_confusion'].append(item)
        elif classified == 'object' and actual == 'unclassified':
            categories['object_overassignment'].append(item)
        else:
            categories['other'].append(item)

    return {
        'component_deployment_confusion': {
            'count': len(categories['component_deployment_confusion']),
            'description': "PlantUML's node/component syntax overlap causes boundary ambiguity",
            'files': categories['component_deployment_confusion']
        },
        'sequence_activity_confusion': {
            'count': len(categories['sequence_activity_confusion']),
            'description': "Step-by-step processes documented using sequence syntax",
            'files': categories['sequence_activity_confusion']
        },
        'object_overassignment': {
            'count': len(categories['object_overassignment']),
            'description': "Non-UML PlantUML extensions (ERD, JSON, Salt) misclassified as object",
            'files': categories['object_overassignment']
        },
        'other': {
            'count': len(categories['other']),
            'description': "Other misclassifications",
            'files': categories['other']
        }
    }


def generate_markdown_report(analysis: Dict) -> str:
    """Generate markdown-formatted report for methodology section."""
    md = []

    md.append("### 6.5 Classification Validation\n")

    md.append("#### 6.5.1 Manual Validation Protocol\n")
    md.append("A stratified random sample of 100 diagrams (10 per diagram type) was manually")
    md.append("reviewed by domain experts. Each diagram was evaluated on three criteria:\n")
    md.append("1. **Classification correctness**: Whether the LLM-assigned type matches the actual diagram type")
    md.append("2. **Real-world relevance**: Whether the diagram documents actual software (vs. tutorials, learning exercises, or templates)")
    md.append("3. **Logical correctness**: Whether the diagram represents valid, meaningful content (vs. placeholders with generic names)\n")

    # Classification accuracy
    acc = analysis['classification_accuracy']
    md.append("#### 6.5.2 Classification Accuracy\n")
    md.append("| Metric | Result |")
    md.append("|--------|--------|")
    md.append(f"| Total samples validated | {acc['total_samples']} |")
    md.append(f"| Correct classifications | {acc['correct_classifications']} |")
    md.append(f"| **Overall accuracy** | **{acc['overall_accuracy_percent']}%** |\n")

    md.append("**Per-Type Accuracy**:\n")
    md.append("| Type | Correct | Total | Accuracy |")
    md.append("|------|---------|-------|----------|")
    for dtype, stats in acc['per_type_accuracy'].items():
        md.append(f"| {dtype} | {stats['correct']} | {stats['total']} | {stats['accuracy_percent']}% |")
    md.append("")

    # Error analysis
    errors = analysis['error_categories']
    md.append("#### 6.5.3 Error Analysis\n")
    total_errors = acc['incorrect_classifications']
    md.append(f"The {total_errors} misclassifications fell into three categories:\n")

    if errors['component_deployment_confusion']['count'] > 0:
        md.append(f"1. **Component/Deployment confusion** ({errors['component_deployment_confusion']['count']} cases): {errors['component_deployment_confusion']['description']}")
    if errors['sequence_activity_confusion']['count'] > 0:
        md.append(f"2. **Sequence/Activity confusion** ({errors['sequence_activity_confusion']['count']} cases): {errors['sequence_activity_confusion']['description']}")
    if errors['object_overassignment']['count'] > 0:
        md.append(f"3. **Object type over-assignment** ({errors['object_overassignment']['count']} cases): {errors['object_overassignment']['description']}")
    if errors['other']['count'] > 0:
        md.append(f"4. **Other** ({errors['other']['count']} cases): {errors['other']['description']}")
    md.append("")

    # Real-world analysis
    rw = analysis['real_world_analysis']
    md.append("#### 6.5.4 Real-World Content Analysis\n")
    md.append("| Category | Count | Percentage |")
    md.append("|----------|-------|------------|")
    md.append(f"| Real-world production diagrams | {rw['real_world']} | {rw['real_world_percent']}% |")
    not_real_pct = round(100 - rw['real_world_percent'], 1)
    md.append(f"| Tutorials/learning/templates | {rw['not_real_world']} | {not_real_pct}% |")
    md.append(f"| Not applicable (sprite libraries) | {rw['not_applicable']} | — |\n")

    # Real-world by type
    md.append("**Real-world by Type**:\n")
    md.append("| Type | Real-world | Not Real-world | % Real-world |")
    md.append("|------|------------|----------------|--------------|")
    for dtype, stats in sorted(rw['by_type'].items(), key=lambda x: -(x[1]['real_world_percent'] or 0)):
        pct = f"{stats['real_world_percent']}%" if stats['real_world_percent'] is not None else "N/A"
        md.append(f"| {dtype} | {stats['real_world']} | {stats['not_real_world']} | {pct} |")
    md.append("")

    # Logical correctness
    lc = analysis['logical_correctness']
    md.append("#### 6.5.5 Logical Correctness\n")
    md.append(f"Of the {lc['logically_correct'] + lc['logically_incorrect']} classifiable diagrams, "
              f"**{lc['logical_correctness_percent']}%** ({lc['logically_correct']}) contained valid, "
              f"meaningful content rather than placeholder templates.\n")

    return '\n'.join(md)


def create_visualizations(analysis: Dict, output_dir: Path):
    """Generate MDPI-compliant visualization plots (requires matplotlib)."""
    try:
        import matplotlib.pyplot as plt
        import matplotlib as mpl
        mpl.use('Agg')  # Non-interactive backend
    except ImportError:
        print("Warning: matplotlib not installed. Skipping visualizations.", file=sys.stderr)
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    # MDPI style constants (matching fig1/fig2)
    DPI = 600
    FIGURE_WIDTH_INCHES = 180 / 25.4  # 180mm
    BAR_COLOR = '#4A90A4'
    OVERALL_LINE_COLOR = '#808080'

    mpl.rcParams.update({
        'font.family': 'Arial',
        'font.size': 8,
        'axes.labelsize': 10,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
    })

    def _save(fig, name):
        fig.savefig(output_dir / name, dpi=DPI, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close(fig)
        print(f"  Saved: {output_dir / name}", file=sys.stderr)

    def _style_ax(ax):
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    # 1. Per-type accuracy bar chart
    acc = analysis['classification_accuracy']['per_type_accuracy']
    types = list(acc.keys())
    accuracies = [acc[t]['accuracy_percent'] for t in types]

    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH_INCHES, FIGURE_WIDTH_INCHES * 0.6))
    bars = ax.bar(types, accuracies, color=BAR_COLOR, edgecolor='none')
    overall = analysis['classification_accuracy']['overall_accuracy_percent']
    ax.axhline(y=overall, color=OVERALL_LINE_COLOR, linestyle='--', linewidth=0.8)
    ax.annotate(f'Overall: {overall}%',
                xy=(0.98, overall), xycoords=('axes fraction', 'data'),
                ha='right', va='bottom', fontsize=8,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                         edgecolor='gray', alpha=0.9))
    ax.set_xlabel('Diagram Type', fontsize=10)
    ax.set_ylabel('Accuracy (%)', fontsize=10)
    ax.set_ylim(0, 105)
    _style_ax(ax)
    plt.xticks(rotation=45, ha='right')

    for bar, val in zip(bars, accuracies):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f'{val}%', ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    _save(fig, 'accuracy_by_type.png')

    # 2. Real-world distribution bar chart
    rw = analysis['real_world_analysis']
    categories = ['Real-world\nproduction', 'Tutorials/\nlearning', 'N/A\n(sprites)']
    sizes = [rw['real_world'], rw['not_real_world'], rw['not_applicable']]
    total = sum(sizes)

    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH_INCHES, FIGURE_WIDTH_INCHES * 0.6))
    bars = ax.bar(categories, sizes, color=BAR_COLOR, edgecolor='none')
    ax.set_ylabel('Number of Diagrams', fontsize=10)
    _style_ax(ax)

    for bar, count in zip(bars, sizes):
        pct = (count / total) * 100
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
                f'{count}\n({pct:.1f}%)', ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    _save(fig, 'real_world_distribution.png')

    # 3. Real-world percentage by type (horizontal bar)
    rw_by_type = analysis['real_world_analysis']['by_type']
    filtered = {k: v for k, v in rw_by_type.items() if v['real_world_percent'] is not None}
    sorted_types = sorted(filtered.keys(), key=lambda x: filtered[x]['real_world_percent'])
    percentages = [filtered[t]['real_world_percent'] for t in sorted_types]

    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH_INCHES, FIGURE_WIDTH_INCHES * 0.55))
    bars = ax.barh(sorted_types, percentages, color=BAR_COLOR, edgecolor='none', height=0.7)
    ax.axvline(x=rw['real_world_percent'], color=OVERALL_LINE_COLOR, linestyle='--', linewidth=0.8)
    ax.annotate(f'Overall: {rw["real_world_percent"]}%',
                xy=(0.98, 0.95), xycoords='axes fraction',
                ha='right', va='top', fontsize=8,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                         edgecolor='gray', alpha=0.9))
    ax.set_xlabel('Real-World Percentage (%)', fontsize=10)
    ax.set_xlim(0, 105)
    _style_ax(ax)

    for bar, val in zip(bars, percentages):
        ax.text(val + 1, bar.get_y() + bar.get_height()/2,
                f'{val}%', ha='left', va='center', fontsize=8)

    plt.tight_layout()
    _save(fig, 'real_world_by_type.png')


def main():
    parser = argparse.ArgumentParser(
        description="Analyze manual validation results and generate report",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--input", "-i",
        type=Path,
        required=True,
        help="Path to manual validation CSV file"
    )

    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=None,
        help="Output path for JSON analysis (default: prints to stdout)"
    )

    parser.add_argument(
        "--markdown", "-m",
        type=Path,
        default=None,
        help="Output path for markdown report"
    )

    parser.add_argument(
        "--visualize", "-v",
        action="store_true",
        help="Generate visualization plots (requires matplotlib)"
    )

    parser.add_argument(
        "--viz-output",
        type=Path,
        default=Path(__file__).parent.parent / "visualizations",
        help="Output directory for plots (default: phase4/visualizations)"
    )

    args = parser.parse_args()

    # Load data
    print(f"Loading validation data from {args.input}...", file=sys.stderr)
    records = load_csv(args.input)
    print(f"Loaded {len(records)} records", file=sys.stderr)

    # Compute all analyses
    print("Computing analysis...", file=sys.stderr)

    classification_accuracy = compute_classification_accuracy(records)
    confusion_matrix = compute_confusion_matrix(records)
    real_world_analysis = compute_real_world_analysis(records)
    logical_correctness = compute_logical_correctness(records)
    confidence_analysis = compute_confidence_analysis(records)
    error_categories = categorize_errors(confusion_matrix)

    analysis = {
        'metadata': {
            'source_file': str(args.input),
            'total_records': len(records)
        },
        'classification_accuracy': classification_accuracy,
        'confusion_matrix': confusion_matrix,
        'error_categories': error_categories,
        'real_world_analysis': real_world_analysis,
        'logical_correctness': logical_correctness,
        'confidence_analysis': confidence_analysis
    }

    # Output JSON
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        print(f"Analysis saved to {args.output}", file=sys.stderr)
    else:
        print(json.dumps(analysis, indent=2, ensure_ascii=False))

    # Output markdown
    if args.markdown:
        markdown_report = generate_markdown_report(analysis)
        with open(args.markdown, 'w', encoding='utf-8') as f:
            f.write(markdown_report)
        print(f"Markdown report saved to {args.markdown}", file=sys.stderr)

    # Generate visualizations
    if args.visualize:
        print(f"Generating visualizations in {args.viz_output}...", file=sys.stderr)
        create_visualizations(analysis, args.viz_output)

    # Print summary to stderr
    print("\n" + "="*60, file=sys.stderr)
    print("VALIDATION SUMMARY", file=sys.stderr)
    print("="*60, file=sys.stderr)
    print(f"Classification accuracy: {classification_accuracy['overall_accuracy_percent']}%", file=sys.stderr)
    print(f"  - Correct: {classification_accuracy['correct_classifications']}/{classification_accuracy['total_samples']}", file=sys.stderr)
    print(f"Real-world diagrams: {real_world_analysis['real_world_percent']}%", file=sys.stderr)
    print(f"  - Real-world: {real_world_analysis['real_world']}", file=sys.stderr)
    print(f"  - Tutorials/learning: {real_world_analysis['not_real_world']}", file=sys.stderr)
    print(f"Logical correctness: {logical_correctness['logical_correctness_percent']}%", file=sys.stderr)
    print("="*60, file=sys.stderr)


if __name__ == "__main__":
    main()
