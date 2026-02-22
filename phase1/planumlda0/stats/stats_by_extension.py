#!/usr/bin/env python3
"""
PlantUML Statistics by File Extension
Counts valid and invalid blobs grouped by file extension.

Usage:
    python3 stats_by_extension.py valid_plantuml_content.gz invalid_blobs.txt -o stats.json
"""

import argparse
import gzip
import json
import os
from collections import Counter
from pathlib import Path


def get_extension(file_path: str) -> str:
    """Extract lowercase file extension from a path.

    Handles dotfiles like '.puml' where os.path.splitext returns no extension
    because the dot is treated as part of the basename.
    """
    basename = os.path.basename(file_path)
    _, ext = os.path.splitext(basename)
    if not ext and basename.startswith('.'):
        ext = basename
    return ext.lower() if ext else "(no extension)"


def count_extensions_gz(filepath: str) -> Counter:
    """Count extensions from a gzipped file with blob_id;file_path;... lines."""
    counts = Counter()
    with gzip.open(filepath, 'rt', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(';', 2)
            if len(parts) >= 2:
                counts[get_extension(parts[1])] += 1
    return counts


def count_extensions_txt(filepath: str) -> Counter:
    """Count extensions from a plain text file with blob_id;file_path;... lines."""
    counts = Counter()
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(';', 2)
            if len(parts) >= 2:
                counts[get_extension(parts[1])] += 1
    return counts


def main():
    parser = argparse.ArgumentParser(
        description="Count valid and invalid PlantUML blobs by file extension"
    )
    parser.add_argument(
        "valid_file",
        help="Gzipped file with valid blobs (valid_plantuml_content.gz)"
    )
    parser.add_argument(
        "invalid_file",
        help="Text file with invalid blobs (invalid_blobs.txt)"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("stats_by_extension.json"),
        help="Output JSON file (default: stats_by_extension.json)"
    )
    args = parser.parse_args()

    print(f"Reading valid blobs from: {args.valid_file}")
    valid_counts = count_extensions_gz(args.valid_file)

    print(f"Reading invalid blobs from: {args.invalid_file}")
    invalid_counts = count_extensions_txt(args.invalid_file)

    # Collect all extensions
    all_extensions = sorted(set(valid_counts.keys()) | set(invalid_counts.keys()))

    # Build per-extension stats
    by_extension = {}
    for ext in all_extensions:
        valid = valid_counts.get(ext, 0)
        invalid = invalid_counts.get(ext, 0)
        total = valid + invalid
        by_extension[ext] = {
            "valid": valid,
            "invalid": invalid,
            "total": total,
            "valid_rate": round(valid / total * 100, 1) if total > 0 else 0.0,
        }

    total_valid = sum(valid_counts.values())
    total_invalid = sum(invalid_counts.values())
    total_all = total_valid + total_invalid

    result = {
        "summary": {
            "total_valid": total_valid,
            "total_invalid": total_invalid,
            "total": total_all,
            "valid_rate": round(total_valid / total_all * 100, 1) if total_all > 0 else 0.0,
        },
        "by_extension": by_extension,
    }

    # Write output
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    # Print summary
    print(f"\n{'Extension':<16} {'Valid':>8} {'Invalid':>8} {'Total':>8} {'Valid %':>8}")
    print("-" * 52)
    for ext in all_extensions:
        s = by_extension[ext]
        print(f"{ext:<16} {s['valid']:>8,} {s['invalid']:>8,} {s['total']:>8,} {s['valid_rate']:>7.1f}%")
    print("-" * 52)
    print(f"{'TOTAL':<16} {total_valid:>8,} {total_invalid:>8,} {total_all:>8,} {result['summary']['valid_rate']:>7.1f}%")

    print(f"\nOutput written to: {args.output}")


if __name__ == "__main__":
    main()
