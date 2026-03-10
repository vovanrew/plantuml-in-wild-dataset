#!/usr/bin/env python3
"""Sample non-UML entries for manual validation before removal.

Reads the LLM classification JSON, randomly samples N entries with
primary_type == "non-uml", and writes them to a CSV file for manual review.

Usage:
    python3 sample_non_uml.py -i classifications.json -n 100 -o non_uml_sample.csv
    python3 sample_non_uml.py -i classifications.json -n 500 -o non_uml_sample.csv --seed 42
"""

import argparse
import csv
import json
import random
import sys
from pathlib import Path


MAX_SAMPLE_SIZE = 1000
EXCLUDED_TYPE = "non-uml"


def main():
    parser = argparse.ArgumentParser(
        description="Sample non-UML entries for manual validation."
    )
    parser.add_argument(
        "-i", "--input", required=True, type=Path,
        help="Input classification JSON",
    )
    parser.add_argument(
        "-n", "--count", required=True, type=int,
        help=f"Number of entries to sample (max {MAX_SAMPLE_SIZE})",
    )
    parser.add_argument(
        "-o", "--output", required=True, type=Path,
        help="Output CSV file",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducibility",
    )
    args = parser.parse_args()

    if args.count < 1 or args.count > MAX_SAMPLE_SIZE:
        print(f"Error: count must be between 1 and {MAX_SAMPLE_SIZE}", file=sys.stderr)
        sys.exit(1)

    # Load classifications
    print(f"Loading classifications from {args.input}")
    with open(args.input) as f:
        data = json.load(f)

    classifications = data["classifications"]

    # Collect non-uml entries
    non_uml = [
        fname for fname, entry in classifications.items()
        if entry.get("primary_type") == EXCLUDED_TYPE
    ]
    print(f"Total non-uml entries: {len(non_uml)}")

    if not non_uml:
        print("No non-uml entries found.", file=sys.stderr)
        sys.exit(1)

    # Sample
    n = min(args.count, len(non_uml))
    if n < args.count:
        print(f"Warning: only {len(non_uml)} non-uml entries available, sampling all")

    random.seed(args.seed)
    sampled = sorted(random.sample(non_uml, n))

    # Write CSV
    with open(args.output, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["file_name", "is_non_uml"])
        for fname in sampled:
            writer.writerow([fname, ""])

    print(f"Wrote {n} entries to {args.output}")


if __name__ == "__main__":
    main()
