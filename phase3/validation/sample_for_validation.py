#!/usr/bin/env python3
"""
Stratified random sampling for manual validation of LLM classification.

Selects a representative sample of diagrams (10 per type) for manual review
and exports them with metadata for validation.

Usage:
    python3 sample_for_validation.py --classifications connection_counts.json --output validation_sample/
    python3 sample_for_validation.py --classifications connection_counts.json --output validation_sample/ --per-type 10
"""

import argparse
import json
import random
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Any


def load_classifications(path: Path) -> Dict[str, Any]:
    """Load classification results JSON."""
    print(f"Loading classifications from {path}...", file=sys.stderr)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def stratified_sample(
    classifications: Dict[str, Dict],
    per_type: int,
    seed: int = 42
) -> Dict[str, List[str]]:
    """
    Perform stratified random sampling: select `per_type` files per diagram type.

    Args:
        classifications: Dictionary mapping filename to classification data
        per_type: Number of samples per diagram type
        seed: Random seed for reproducibility

    Returns:
        Dictionary mapping diagram type to list of selected filenames
    """
    random.seed(seed)

    # Group files by primary type
    by_type: Dict[str, List[str]] = {}
    for filename, data in classifications.items():
        primary_type = data.get('primary_type', 'unknown')
        if primary_type not in by_type:
            by_type[primary_type] = []
        by_type[primary_type].append(filename)

    # Sample from each type
    sampled: Dict[str, List[str]] = {}
    for dtype, files in sorted(by_type.items()):
        n_sample = min(per_type, len(files))
        sampled[dtype] = random.sample(files, n_sample)
        print(f"  {dtype}: sampled {n_sample} from {len(files)} files", file=sys.stderr)

    return sampled


def format_dict(d: Dict[str, int]) -> str:
    """Format a dict of counts as a readable string for CSV."""
    if not d:
        return ''
    return '; '.join(f'{k}: {v}' for k, v in sorted(d.items()))


def export_sample(
    sampled: Dict[str, List[str]],
    classifications: Dict[str, Dict],
    output_dir: Path,
    puml_base: Path = None,
    images_base: Path = None
):
    """
    Export sampled files with metadata for manual validation.

    Creates:
    - validation_sample.psv: Pipe-delimited file for manual review
    - validation_sample.json: Full metadata for each sample
    - puml/: Copied PUML source files (if available)
    - images/: Copied PNG images (if available)

    Args:
        sampled: Dictionary mapping type to list of filenames
        classifications: Full classification data
        output_dir: Output directory path
        puml_base: Base path to PUML files (optional)
        images_base: Base path to PNG images (optional)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (output_dir / 'puml').mkdir(exist_ok=True)
    (output_dir / 'images').mkdir(exist_ok=True)

    # Build sample records
    records = []
    sample_id = 0

    for dtype, filenames in sorted(sampled.items()):
        for filename in filenames:
            sample_id += 1
            data = classifications[filename]

            record = {
                'sample_id': sample_id,
                'filename': filename,
                'classified_type': data.get('primary_type', ''),
                'content_lines': data.get('content_lines', 0),
                'elements': data.get('elements', {}),
                'total_elements': data.get('total_elements', 0),
                'connections': data.get('connections', {}),
                'total_connections': data.get('total_connections', 0),
                # Fields to fill during manual review
                'actual_type': '',
                'elements_correct': '',
                'actual_elements': '',
                'actual_elements_count': '',
                'connections_correct': '',
                'actual_connections': '',
                'actual_connections_count': '',
            }
            records.append(record)

            # Copy PUML file if available
            if puml_base:
                puml_src = puml_base / filename
                if puml_src.exists():
                    shutil.copy2(puml_src, output_dir / 'puml' / filename)

            # Copy image file if available
            if images_base:
                img_name = filename.replace('.puml', '.png')
                img_src = images_base / img_name
                if img_src.exists():
                    shutil.copy2(img_src, output_dir / 'images' / img_name)

    # Write PSV for manual review
    psv_path = output_dir / 'validation_sample.csv'
    with open(psv_path, 'w', encoding='utf-8') as f:
        headers = ['sample_id', 'filename', 'classified_type', 'content_lines',
                   'elements', 'total_elements', 'connections', 'total_connections',
                   'actual_type', 'elements_correct', 'actual_elements',
                   'actual_elements_count', 'connections_correct',
                   'actual_connections', 'actual_connections_count']
        f.write('|'.join(headers) + '\n')
        for r in records:
            elements_str = format_dict(r['elements'])
            connections_str = format_dict(r['connections'])
            row = [
                str(r['sample_id']),
                r['filename'],
                r['classified_type'],
                str(r['content_lines']),
                elements_str,
                str(r['total_elements']),
                connections_str,
                str(r['total_connections']),
                r['actual_type'],
                r['elements_correct'],
                r['actual_elements'],
                str(r['actual_elements_count']) if r['actual_elements_count'] != '' else '',
                r['connections_correct'],
                r['actual_connections'],
                str(r['actual_connections_count']) if r['actual_connections_count'] != '' else '',
            ]
            f.write('|'.join(row) + '\n')

    # Write full JSON metadata
    json_path = output_dir / 'validation_sample.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'total_samples': len(records),
                'samples_per_type': {k: len(v) for k, v in sampled.items()},
                'seed': 42
            },
            'samples': records
        }, f, indent=2, ensure_ascii=False)

    print(f"\nExported {len(records)} samples to {output_dir}", file=sys.stderr)
    print(f"  - PSV: {psv_path}", file=sys.stderr)
    print(f"  - JSON: {json_path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Stratified sampling for manual validation of LLM classification",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--classifications", "-c",
        type=Path,
        required=True,
        help="Path to connection_counts.json"
    )

    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("validation_sample"),
        help="Output directory for samples (default: validation_sample)"
    )

    parser.add_argument(
        "--per-type", "-n",
        type=int,
        default=10,
        help="Number of samples per diagram type (default: 10)"
    )

    parser.add_argument(
        "--puml-dir",
        type=Path,
        default=None,
        help="Directory containing PUML source files (optional)"
    )

    parser.add_argument(
        "--images-dir",
        type=Path,
        default=None,
        help="Directory containing PNG images (optional)"
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)"
    )

    args = parser.parse_args()

    # Load data
    data = load_classifications(args.classifications)
    classifications = data.get('classifications', {})

    print(f"Loaded {len(classifications)} classifications", file=sys.stderr)

    # Perform stratified sampling
    print(f"\nStratified sampling ({args.per_type} per type):", file=sys.stderr)
    sampled = stratified_sample(classifications, args.per_type, args.seed)

    # Export samples
    export_sample(
        sampled,
        classifications,
        args.output,
        args.puml_dir,
        args.images_dir
    )

    # Summary
    total = sum(len(v) for v in sampled.values())
    print(f"\nTotal samples: {total}", file=sys.stderr)
    print(f"Types covered: {len(sampled)}", file=sys.stderr)
    print("\nNext steps:", file=sys.stderr)
    print("1. Review each diagram in validation_sample.psv", file=sys.stderr)
    print("2. Fill in 'actual_type' if classified_type is wrong", file=sys.stderr)
    print("3. Fill in 'elements_correct' / 'connections_correct' (Yes/No)", file=sys.stderr)
    print("4. Run analyze_validation_results.py to compute accuracy", file=sys.stderr)


if __name__ == "__main__":
    main()
